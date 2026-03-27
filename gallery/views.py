from django.shortcuts import render
from django.http import Http404
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import Artwork, Interaction
from .serializers import ArtworkSerializer, ArtworkDetailSerializer, UserSerializer


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
    """Record a like or pass for an artwork."""
    artwork_id = request.data.get('artwork_id')
    action = request.data.get('action')

    if action not in ('like', 'pass'):
        return Response({'error': 'action must be "like" or "pass"'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        artwork = Artwork.objects.get(id=artwork_id)
    except Artwork.DoesNotExist:
        return Response({'error': f'Artwork {artwork_id} not found'}, status=status.HTTP_404_NOT_FOUND)

    interaction, created = Interaction.objects.update_or_create(
        user=request.user,
        artwork=artwork,
        defaults={'action': action},
    )
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
def artwork_list(request):
    """
    Get all artworks (paginated), excluding ones the user has already interacted with.
    """
    limit = int(request.query_params.get('limit', 20))
    offset = int(request.query_params.get('offset', 0))

    qs = Artwork.objects.all()
    if request.user.is_authenticated:
        seen_ids = Interaction.objects.filter(user=request.user).values_list('artwork_id', flat=True)
        qs = qs.exclude(id__in=seen_ids)

    total = qs.count()
    artworks = qs[offset:offset+limit]
    serializer = ArtworkSerializer(artworks, many=True)
    return Response({
        'count': total,
        'limit': limit,
        'offset': offset,
        'results': serializer.data
    })
