from rest_framework import serializers
from django.contrib.auth.models import User
from google.auth.transport import requests
from google.oauth2 import id_token
from core.models import Goal


class GoalSerializer(serializers.ModelSerializer):
    """Serializer for goal data in user profile."""
    
    class Meta:
        model = Goal
        fields = ['is_activated', 'hours', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile responses."""
    name = serializers.SerializerMethodField()
    goal = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'name', 'date_joined', 'goal']
        read_only_fields = ['id', 'date_joined']
    
    def get_name(self, obj):
        """Return the full name of the user."""
        return f"{obj.first_name} {obj.last_name}".strip()
    
    def get_goal(self, obj):
        """Return goal data if it exists, otherwise return None."""
        try:
            goal = obj.goal
            return GoalSerializer(goal).data
        except Goal.DoesNotExist:
            return None


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile information."""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
    
    def validate_first_name(self, value):
        """Validate first name field."""
        if not value or not value.strip():
            raise serializers.ValidationError("First name cannot be empty.")
        return value.strip()
    
    def validate_last_name(self, value):
        """Validate last name field."""
        if not value or not value.strip():
            raise serializers.ValidationError("Last name cannot be empty.")
        return value.strip()


class GoogleAuthSerializer(serializers.Serializer):
    """Serializer for Google OAuth token validation."""
    token = serializers.CharField()
    
    def validate_token(self, value):
        """Validate the Google OAuth token."""
        if not value:
            raise serializers.ValidationError("Token is required.")
        
        try:
            # This will be implemented in the view logic
            # For now, we just validate that a token is provided
            return value
        except Exception as e:
            raise serializers.ValidationError("Invalid Google token.")
    
    def validate(self, attrs):
        """Additional validation for the entire serializer."""
        token = attrs.get('token')
        
        if not token:
            raise serializers.ValidationError({
                'token': 'Google OAuth token is required.'
            })
        
        return attrs 