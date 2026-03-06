from rest_framework import serializers
from .models import Artwork, Interaction

class ArtworkSerializer(serializers.ModelSerializer):
    """Basic artwork serializer for list views."""
    class Meta:
        model = Artwork
        fields = ['id', 'label', 'accession_no', 'date']

class ArtworkDetailSerializer(serializers.ModelSerializer):
    """Detailed artwork serializer with interaction statistics."""
    total_likes = serializers.SerializerMethodField()
    total_passes = serializers.SerializerMethodField()
    
    class Meta:
        model = Artwork
        fields = ['id', 'label', 'accession_no', 'date', 'total_likes', 'total_passes']
    
    def get_total_likes(self, obj):
        return Interaction.objects.filter(artwork=obj, action='like').count()
    
    def get_total_passes(self, obj):
        return Interaction.objects.filter(artwork=obj, action='pass').count()