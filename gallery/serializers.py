from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Artwork, Interaction


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

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