from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Artwork
from .serializers import ArtworkSerializer

@api_view(['GET'])
def single_artwork(request):
    # Grab the first artwork in the database for the MVP
    artwork = Artwork.objects.first() 
    serializer = ArtworkSerializer(artwork)
    return Response(serializer.data)
