from django.shortcuts import render
from django.http import Http404
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import Artwork, Interaction, TasteSignal, Message
from .serializers import ArtworkSerializer, ArtworkDetailSerializer, UserSerializer, MessageSerializer
from .taste import update_taste_signals, check_matches, MATCH_CHECK_INTERVAL


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
def single_artwork(request):
    """
    Get the first artwork in the database for the Gallery View.
    """
    artwork = Artwork.objects.first()
    if not artwork:
        return Response(
            {'error': 'No artworks found in the database'},
            status=status.HTTP_404_NOT_FOUND
        )
    serializer = ArtworkSerializer(artwork)
    return Response(serializer.data)

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
def liked_artworks(request):
    """Return artworks the current user has liked, paginated."""
    limit = int(request.query_params.get('limit', 20))
    offset = int(request.query_params.get('offset', 0))

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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list(request):
    """Return all users except the current user."""
    users = User.objects.exclude(id=request.user.id).values('id', 'username')
    return Response(list(users))


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conversation(request, user_id):
    """GET messages between current user and user_id. POST sends a new message."""
    try:
        other_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        messages = Message.objects.filter(
            sender=request.user, recipient=other_user
        ) | Message.objects.filter(
            sender=other_user, recipient=request.user
        )
        messages = messages.order_by('timestamp')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    text = request.data.get('text', '').strip()
    if not text:
        return Response({'error': 'text is required'}, status=status.HTTP_400_BAD_REQUEST)

    message = Message.objects.create(sender=request.user, recipient=other_user, text=text)
    serializer = MessageSerializer(message)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def artwork_list(request):
    """
    Get random artworks, excluding IDs the client has already seen this session.
    """
    limit = int(request.query_params.get('limit', 20))

    qs = Artwork.objects.all()
    exclude = request.query_params.get('exclude', '')
    if exclude:
        exclude_ids = [int(x) for x in exclude.split(',') if x.strip().isdigit()]
        qs = qs.exclude(id__in=exclude_ids)

    total = qs.count()
    artworks = qs.order_by('?')[:limit]
    serializer = ArtworkSerializer(artworks, many=True)
    return Response({
        'count': total,
        'results': serializer.data
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
