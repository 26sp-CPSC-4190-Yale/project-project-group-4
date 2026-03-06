from django.shortcuts import render
from django.http import Http404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Artwork, Interaction
from .serializers import ArtworkSerializer, ArtworkDetailSerializer

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
    Get all artworks (paginated).
    """
    limit = int(request.query_params.get('limit', 20))
    offset = int(request.query_params.get('offset', 0))
    
    artworks = Artwork.objects.all()[offset:offset+limit]
    serializer = ArtworkSerializer(artworks, many=True)
    return Response({
        'count': Artwork.objects.count(),
        'limit': limit,
        'offset': offset,
        'results': serializer.data
    })
