from rest_framework import serializers
from .models import Reason, FocusEntry


class ReasonSerializer(serializers.ModelSerializer):
    """
    Serializer for Reason model.
    Handles CRUD operations for user-defined reasons.
    """
    
    class Meta:
        model = Reason
        fields = ['id', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate_description(self, value):
        """
        Validate that description is not empty or just whitespace.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Description cannot be empty.")
        
        # Check for reasonable length
        if len(value.strip()) > 500:
            raise serializers.ValidationError("Description cannot exceed 500 characters.")
            
        return value.strip()
    
    def create(self, validated_data):
        """
        Create a new reason associated with the current user.
        """
        user = self.context['request'].user
        return Reason.objects.create(user=user, **validated_data)


class ReasonListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for listing reasons.
    Includes usage count for better UX.
    """
    usage_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Reason
        fields = ['id', 'description', 'created_at', 'usage_count']
        read_only_fields = ['id', 'created_at', 'usage_count']
    
    def get_usage_count(self, obj):
        """
        Return the number of focus entries using this reason.
        """
        return obj.focus_entries.count()


class ReasonDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for reason with extended information.
    """
    usage_count = serializers.SerializerMethodField()
    recent_entries = serializers.SerializerMethodField()
    
    class Meta:
        model = Reason
        fields = ['id', 'description', 'created_at', 'usage_count', 'recent_entries']
        read_only_fields = ['id', 'created_at', 'usage_count', 'recent_entries']
    
    def get_usage_count(self, obj):
        """
        Return the number of focus entries using this reason.
        """
        return obj.focus_entries.count()
    
    def get_recent_entries(self, obj):
        """
        Return the 5 most recent focus entries using this reason.
        """
        recent = obj.focus_entries.order_by('-date')[:5]
        return [{'date': entry.date, 'hours': entry.hours} for entry in recent] 