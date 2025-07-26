from rest_framework import serializers
from .models import Reason, FocusEntry
from datetime import date, timedelta


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


class FocusEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for FocusEntry model.
    Handles CRUD operations for focus tracking entries.
    """
    reason = ReasonSerializer(read_only=True)
    reason_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = FocusEntry
        fields = ['id', 'date', 'hours', 'reason', 'reason_id']
        read_only_fields = ['id']
    
    def validate_date(self, value):
        """
        Validate that the date is not in the future and not too far in the past.
        """
        today = date.today()
        
        if value > today:
            raise serializers.ValidationError("Cannot create entries for future dates.")
        
        # Allow entries up to 1 year in the past
        one_year_ago = today - timedelta(days=365)
        if value < one_year_ago:
            raise serializers.ValidationError("Cannot create entries more than 1 year in the past.")
        
        return value
    
    def validate_hours(self, value):
        """
        Validate that hours is a positive number within reasonable limits.
        """
        if value is not None:
            if value <= 0:
                raise serializers.ValidationError("Hours must be a positive number.")
            
            if value > 24:
                raise serializers.ValidationError("Hours cannot exceed 24 hours per day.")
            
            # Round to 2 decimal places for consistency
            return round(value, 2)
        
        return value
    
    def validate_reason_id(self, value):
        """
        Validate that the reason belongs to the current user.
        """
        if value is not None:
            try:
                reason = Reason.objects.get(id=value)
                if reason.user != self.context['request'].user:
                    raise serializers.ValidationError("You can only use reasons that you created.")
            except Reason.DoesNotExist:
                raise serializers.ValidationError("Invalid reason ID.")
        
        return value
    
    def validate(self, data):
        """
        Validate that the user doesn't already have an entry for this date.
        """
        user = self.context['request'].user
        entry_date = data.get('date')
        
        # Check for existing entry on the same date
        existing_entry = FocusEntry.objects.filter(user=user, date=entry_date)
        
        # If updating, exclude the current instance
        if self.instance:
            existing_entry = existing_entry.exclude(id=self.instance.id)
        
        if existing_entry.exists():
            raise serializers.ValidationError(
                f"You already have a focus entry for {entry_date}. "
                "Each user can only have one entry per date."
            )
        
        return data
    
    def create(self, validated_data):
        """
        Create a new focus entry associated with the current user.
        """
        user = self.context['request'].user
        reason_id = validated_data.pop('reason_id', None)
        
        # Set the reason if provided
        if reason_id:
            validated_data['reason'] = Reason.objects.get(id=reason_id)
        
        return FocusEntry.objects.create(user=user, **validated_data)
    
    def update(self, instance, validated_data):
        """
        Update an existing focus entry.
        """
        reason_id = validated_data.pop('reason_id', None)
        
        # Update the reason if provided
        if reason_id is not None:
            if reason_id:
                instance.reason = Reason.objects.get(id=reason_id)
            else:
                instance.reason = None
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class FocusEntryListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for listing focus entries.
    Includes minimal reason information for performance.
    """
    reason_description = serializers.CharField(source='reason.description', read_only=True)
    reason_id = serializers.UUIDField(source='reason.id', read_only=True)
    
    class Meta:
        model = FocusEntry
        fields = ['id', 'date', 'hours', 'reason_id', 'reason_description']
        read_only_fields = ['id', 'reason_id', 'reason_description']


class BulkUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk updating focus entries.
    """
    dates = serializers.ListField(
        child=serializers.DateField(),
        min_length=1,
        max_length=31,  # Limit to one month at a time
        help_text="List of dates to update (max 31 dates)"
    )
    reason_id = serializers.UUIDField(required=False, allow_null=True)
    hours = serializers.FloatField(required=False, min_value=0, max_value=24)
    
    def validate_dates(self, value):
        """
        Validate that dates are not in the future and not too far in the past.
        """
        today = date.today()
        one_year_ago = today - timedelta(days=365)
        
        for entry_date in value:
            if entry_date > today:
                raise serializers.ValidationError(f"Cannot update entries for future date: {entry_date}")
            
            if entry_date < one_year_ago:
                raise serializers.ValidationError(f"Cannot update entries for date too far in past: {entry_date}")
        
        # Check for duplicate dates
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate dates are not allowed.")
        
        return sorted(value)  # Return sorted dates for consistency
    
    def validate_reason_id(self, value):
        """
        Validate that the reason belongs to the current user.
        """
        if value is not None:
            try:
                reason = Reason.objects.get(id=value)
                if reason.user != self.context['request'].user:
                    raise serializers.ValidationError("You can only use reasons that you created.")
            except Reason.DoesNotExist:
                raise serializers.ValidationError("Invalid reason ID.")
        
        return value
    
    def validate_hours(self, value):
        """
        Validate hours if provided.
        """
        if value is not None:
            if value <= 0:
                raise serializers.ValidationError("Hours must be a positive number.")
            
            if value > 24:
                raise serializers.ValidationError("Hours cannot exceed 24 hours per day.")
            
            return round(value, 2)
        
        return value
    
    def validate(self, data):
        """
        Validate that at least one field to update is provided.
        """
        if 'reason_id' not in data and 'hours' not in data:
            raise serializers.ValidationError(
                "At least one field (reason_id or hours) must be provided for bulk update."
            )
        
        return data 