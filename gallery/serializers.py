from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Artwork, Message


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

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'sender_username', 'recipient', 'text', 'timestamp']
        read_only_fields = ['sender', 'timestamp']

