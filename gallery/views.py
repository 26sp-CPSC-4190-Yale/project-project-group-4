import random

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import Artwork, Interaction, Match, Message, Production, Reference, TasteSignal
from .serializers import ArtworkSerializer, ArtworkDetailSerializer, UserSerializer, MessageSerializer
from .taste import update_taste_signals, check_matches, get_daily_artwork, MATCH_CHECK_INTERVAL

MAX_PAGE_LIMIT = 100
MAX_MESSAGE_LENGTH = 5000


def _clamp(value, lo, hi):
    try:
        return max(lo, min(int(value), hi))
    except (TypeError, ValueError):
        return lo


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user and return an auth token."""
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': serializer.data}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Authenticate a user and return an auth token."""
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user is None:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': {'id': user.id, 'username': user.username, 'email': user.email}})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Delete the user's auth token (logout)."""
    request.user.auth_token.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_interaction(request):
    """Record a like or pass for an artwork, update taste signals, and check for matches."""
    artwork_id = request.data.get('artwork_id')
    action = request.data.get('action')

    if action not in ('like', 'pass'):
        return Response({'error': 'action must be "like" or "pass"'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        artwork = Artwork.objects.get(id=artwork_id)
    except Artwork.DoesNotExist:
        return Response({'error': f'Artwork {artwork_id} not found'}, status=status.HTTP_404_NOT_FOUND)

    # Use get_or_create so we can detect re-swipes and diff the action
    interaction, created = Interaction.objects.get_or_create(
        user=request.user,
        artwork=artwork,
        defaults={'action': action},
    )

    if created:
        update_taste_signals(request.user, artwork, action)
    else:
        old_action = interaction.action
        if old_action != action:
            # Re-swipe: undo old signals, apply new ones
            update_taste_signals(request.user, artwork, old_action, undo=True)
            update_taste_signals(request.user, artwork, action)
            interaction.action = action
            interaction.save()

    # Check for matches every N swipes
    total_swipes = Interaction.objects.filter(user=request.user).count()
    if total_swipes % MATCH_CHECK_INTERVAL == 0:
        check_matches(request.user)

    return Response(
        {'artwork_id': artwork_id, 'action': action, 'created': created},
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )

@api_view(['GET'])
def artwork_detail(request, artwork_id):
    """
    Get a specific artwork by ID along with user interactions.
    """
    try:
        artwork = Artwork.objects.get(id=artwork_id)
    except Artwork.DoesNotExist:
        return Response(
            {'error': f'Artwork with id {artwork_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = ArtworkDetailSerializer(artwork)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_stats(request):
    """Return the current user's interaction stats for the profile page."""
    interactions = Interaction.objects.filter(user=request.user)
    total_likes = interactions.filter(action='like').count()
    total_passes = interactions.filter(action='pass').count()
    total = total_likes + total_passes
    like_rate = round(total_likes / total, 3) if total else 0.0
    first = (
        interactions.order_by('timestamp')
        .values_list('timestamp', flat=True)
        .first()
    )

    return Response({
        'total_likes': total_likes,
        'total_passes': total_passes,
        'like_rate': like_rate,
        'first_interaction_at': first.isoformat() if first else None,
        'date_joined': request.user.date_joined.isoformat(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def liked_artworks(request):
    """Return artworks the current user has liked, paginated."""
    limit = _clamp(request.query_params.get('limit', 20), 1, MAX_PAGE_LIMIT)
    try:
        offset = max(0, int(request.query_params.get('offset', 0)))
    except (TypeError, ValueError):
        offset = 0

    interactions = Interaction.objects.filter(
        user=request.user, action='like'
    ).select_related('artwork').order_by('-timestamp')

    total = interactions.count()
    page = interactions[offset:offset + limit]
    artworks = [i.artwork for i in page]

    serializer = ArtworkSerializer(artworks, many=True)
    return Response({
        'count': total,
        'limit': limit,
        'offset': offset,
        'results': serializer.data,
    })


def _get_match(user, other_id):
    return Match.objects.filter(
        Q(user1_id=user.id, user2_id=other_id) | Q(user1_id=other_id, user2_id=user.id)
    ).first()


def _top_facets(user_id, other_id, limit=3):
    my_sigs = {(s.facet, s.value): s.score for s in TasteSignal.objects.filter(user_id=user_id)}
    their_sigs = {(s.facet, s.value): s.score for s in TasteSignal.objects.filter(user_id=other_id)}
    shared = []
    for key in set(my_sigs) & set(their_sigs):
        facet, value = key
        avg = (my_sigs[key] + their_sigs[key]) / 2
        shared.append({'facet': facet, 'value': value, 'score': round(avg, 3)})
    shared.sort(key=lambda x: -x['score'])
    return shared[:limit]


def _batch_top_facets(my_id, other_ids, limit=3):
    """Top shared facets for multiple users in 2 queries total."""
    if not other_ids:
        return {}

    my_sigs = {(s.facet, s.value): s.score for s in TasteSignal.objects.filter(user_id=my_id)}

    other_sigs = {}
    for s in TasteSignal.objects.filter(user_id__in=other_ids):
        other_sigs.setdefault(s.user_id, {})[(s.facet, s.value)] = s.score

    result = {}
    for other_id in other_ids:
        their = other_sigs.get(other_id, {})
        shared = []
        for key in set(my_sigs) & set(their):
            facet, value = key
            avg = (my_sigs[key] + their[key]) / 2
            shared.append({'facet': facet, 'value': value, 'score': round(avg, 3)})
        shared.sort(key=lambda x: -x['score'])
        result[other_id] = shared[:limit]
    return result


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def match_list(request):
    """Return the current user's matches with status and top shared facets."""
    me = request.user
    matches = Match.objects.filter(
        Q(user1=me) | Q(user2=me)
    ).exclude(
        status=Match.STATUS_DECLINED
    ).select_related('user1', 'user2', 'requested_by')

    Match.objects.filter(user1=me, seen_by_user1=False).update(seen_by_user1=True)
    Match.objects.filter(user2=me, seen_by_user2=False).update(seen_by_user2=True)

    match_pairs = []
    other_ids = []
    for m in matches:
        other = m.user2 if m.user1_id == me.id else m.user1
        match_pairs.append((m, other))
        other_ids.append(other.id)

    facets_by_user = _batch_top_facets(me.id, other_ids)

    result = []
    for m, other in match_pairs:
        result.append({
            'user': {'id': other.id, 'username': other.username},
            'similarity': round(m.similarity, 3),
            'status': m.status,
            'requested_by_me': m.requested_by_id == me.id if m.requested_by_id else False,
            'matched_at': m.matched_at.isoformat(),
            'top_facets': facets_by_user.get(other.id, []),
        })
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def match_action(request, user_id):
    """Perform an action on a match: request, accept, or decline."""
    action = request.data.get('action')
    if action not in ('request', 'accept', 'decline'):
        return Response({'error': 'action must be request, accept, or decline'}, status=status.HTTP_400_BAD_REQUEST)

    match = _get_match(request.user, user_id)
    if not match:
        return Response({'error': 'Match not found'}, status=status.HTTP_404_NOT_FOUND)

    me = request.user

    if action == 'request':
        if match.status != Match.STATUS_PENDING:
            return Response({'error': 'Match is not in pending state'}, status=status.HTTP_400_BAD_REQUEST)
        match.status = Match.STATUS_REQUESTED
        match.requested_by = me
        match.save()

    elif action == 'accept':
        if match.status != Match.STATUS_REQUESTED or match.requested_by_id == me.id:
            return Response({'error': 'No incoming request to accept'}, status=status.HTTP_400_BAD_REQUEST)
        match.status = Match.STATUS_ACCEPTED
        match.save()

    elif action == 'decline':
        if match.status != Match.STATUS_REQUESTED or match.requested_by_id == me.id:
            return Response({'error': 'No incoming request to decline'}, status=status.HTTP_400_BAD_REQUEST)
        match.status = Match.STATUS_DECLINED
        match.save()

    return Response({'status': match.status})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def unmatch(request, user_id):
    """Unmatch and delete all messages between the two users."""
    match = _get_match(request.user, user_id)
    if not match:
        return Response({'error': 'Match not found'}, status=status.HTTP_404_NOT_FOUND)

    me = request.user
    Message.objects.filter(
        Q(sender=me, recipient_id=user_id) | Q(sender_id=user_id, recipient=me)
    ).delete()
    match.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def match_facets(request, user_id):
    """Return the top shared taste facets between the current user and another matched user."""
    match = _get_match(request.user, user_id)
    if not match:
        return Response({'error': 'Match not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(_top_facets(request.user.id, user_id))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications(request):
    """Return counts of unseen new matches and incoming message requests."""
    me = request.user

    new_matches = Match.objects.filter(
        Q(user1=me, seen_by_user1=False) | Q(user2=me, seen_by_user2=False),
        status=Match.STATUS_PENDING,
    ).count()

    pending_requests = Match.objects.filter(
        Q(user1=me) | Q(user2=me),
        status=Match.STATUS_REQUESTED,
    ).exclude(requested_by=me).count()

    return Response({'new_matches': new_matches, 'pending_requests': pending_requests})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conversation(request, user_id):
    """GET messages between current user and user_id. POST sends a new message."""
    try:
        other_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    match = _get_match(request.user, user_id)
    if not match or match.status != Match.STATUS_ACCEPTED:
        return Response({'error': 'You are not in an accepted match with this user'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        messages = Message.objects.filter(
            Q(sender=request.user, recipient=other_user) |
            Q(sender=other_user, recipient=request.user)
        ).order_by('timestamp')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    text = request.data.get('text', '').strip()
    if not text:
        return Response({'error': 'text is required'}, status=status.HTTP_400_BAD_REQUEST)
    if len(text) > MAX_MESSAGE_LENGTH:
        return Response({'error': f'Message too long (max {MAX_MESSAGE_LENGTH} chars)'}, status=status.HTTP_400_BAD_REQUEST)

    message = Message.objects.create(sender=request.user, recipient=other_user, text=text)
    serializer = MessageSerializer(message)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def artwork_list(request):
    """
    Get random artworks the user hasn't interacted with yet.
    Falls back to the full pool when all artworks have been seen.
    """
    limit = _clamp(request.query_params.get('limit', 20), 1, MAX_PAGE_LIMIT)

    seen = Interaction.objects.filter(user=request.user).values('artwork_id')
    unseen = Artwork.objects.exclude(id__in=seen)
    all_ids = list(unseen.values_list('id', flat=True))

    if not all_ids:
        all_ids = list(Artwork.objects.values_list('id', flat=True))

    sample_ids = random.sample(all_ids, min(limit, len(all_ids)))
    artworks = list(Artwork.objects.filter(id__in=sample_ids))

    serializer = ArtworkSerializer(artworks, many=True)
    return Response({
        'count': len(all_ids),
        'results': serializer.data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_taste(request):
    """Return the current user's top taste signals for debugging / profile display."""
    signals = (
        TasteSignal.objects
        .filter(user=request.user)
        .order_by('-score')[:20]
    )
    data = [
        {
            'facet': s.facet,
            'value': s.value,
            'score': round(s.score, 3),
            'likes': s.like_count,
            'passes': s.pass_count,
        }
        for s in signals
    ]
    return Response({'signals': data})


def _get_artwork_references(artwork_ids):
    """Fetch reference metadata (medium, dimensions, etc.) for a set of artworks."""
    useful_types = ('Medium', 'Dimensions', 'Culture', 'Period', 'Credit Line')
    refs = Reference.objects.filter(artwork_id__in=artwork_ids, type__in=useful_types)
    refs_by_id = {}
    for ref in refs:
        refs_by_id.setdefault(ref.artwork_id, {})[ref.type] = ref.content
    return refs_by_id


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_artwork(request):
    """Return personalized art-of-the-day candidates with rich metadata."""
    is_popular = request.query_params.get('fallback') == 'true'
    if is_popular:
        from .taste import _daily_cold_start
        artwork_ids, explanation = _daily_cold_start(request.user), []
    else:
        artwork_ids, explanation = get_daily_artwork(request.user)
        is_popular = len(explanation) == 0 and len(artwork_ids) > 0

    if not artwork_ids:
        return Response(
            {'candidates': [], 'explanation': [], 'is_popular': is_popular},
            status=status.HTTP_200_OK,
        )

    # Batch-load artworks with prefetched relations (avoids N+1)
    artworks = (
        Artwork.objects
        .filter(id__in=artwork_ids)
        .prefetch_related('classifiers', 'departments', 'places')
    )
    artwork_map = {a.id: a for a in artworks}

    # Batch-load productions with agents and nationalities
    productions = (
        Production.objects
        .filter(artwork_id__in=artwork_ids)
        .select_related('agent')
        .prefetch_related('agent__nationalities')
    )
    prods_by_artwork = {}
    for prod in productions:
        prods_by_artwork.setdefault(prod.artwork_id, []).append(prod)

    # Batch-load references
    refs = _get_artwork_references(artwork_ids)

    # Serialize in score order
    candidates = []
    for aid in artwork_ids:
        artwork = artwork_map.get(aid)
        if not artwork:
            continue

        agents = []
        for prod in prods_by_artwork.get(aid, []):
            agent = prod.agent
            nationalities = [n.descriptor for n in agent.nationalities.all()]
            agents.append({
                'name': agent.name,
                'role': prod.part,
                'nationalities': nationalities,
                'begin_date': str(agent.begin_date) if agent.begin_date else None,
                'end_date': str(agent.end_date) if agent.end_date else None,
            })

        artwork_refs = refs.get(aid, {})

        candidates.append({
            'id': artwork.id,
            'label': artwork.label,
            'date': artwork.date,
            'accession_no': artwork.accession_no,
            'agents': agents,
            'classifiers': [c.name for c in artwork.classifiers.all()],
            'departments': [d.name for d in artwork.departments.all()],
            'places': [p.label for p in artwork.places.all()],
            'medium': artwork_refs.get('Medium'),
            'dimensions': artwork_refs.get('Dimensions'),
            'culture': artwork_refs.get('Culture'),
            'period': artwork_refs.get('Period'),
            'credit_line': artwork_refs.get('Credit Line'),
        })

    return Response({
        'candidates': candidates,
        'explanation': explanation,
        'is_popular': is_popular,
    })
