from django.contrib import admin
from django.db.models import Count, Sum, Avg, Q
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from datetime import date, timedelta
from .models import Reason, FocusEntry, Feedback, Goal


class FocusEntryForm(ModelForm):
    """
    Custom form for FocusEntry with enhanced validation.
    """
    class Meta:
        model = FocusEntry
        fields = '__all__'
    
    def clean(self):
        """
        Enhanced validation for focus entries.
        """
        cleaned_data = super().clean()
        entry_date = cleaned_data.get('date')
        hours = cleaned_data.get('hours')
        user = cleaned_data.get('user')
        
        # Validate date is not in the future
        if entry_date and entry_date > date.today():
            raise ValidationError("Cannot create entries for future dates.")
        
        # Validate date is not too far in the past (1 year)
        if entry_date and entry_date < date.today() - timedelta(days=365):
            raise ValidationError("Cannot create entries more than 1 year in the past.")
        
        # Validate hours range
        if hours is not None:
            if hours < 0:
                raise ValidationError("Hours cannot be negative.")
            if hours > 24:
                raise ValidationError("Hours cannot exceed 24 hours per day.")
        
        # Check for duplicate entries (same user, same date)
        if user and entry_date:
            existing = FocusEntry.objects.filter(user=user, date=entry_date)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError(f"User already has an entry for {entry_date}.")
        
        return cleaned_data


class FocusEntryInline(admin.TabularInline):
    """
    Inline editing for focus entries related to a reason.
    """
    model = FocusEntry
    extra = 0
    readonly_fields = ('user', 'date', 'hours')
    fields = ('user', 'date', 'hours')
    can_delete = False
    max_num = 10  # Show only recent entries
    
    def has_add_permission(self, request, obj=None):
        return False  # Don't allow adding entries from reason admin


@admin.register(Reason)
class ReasonAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for Reason model.
    Includes usage statistics, filtering, and inline editing.
    """
    list_display = ('description', 'user', 'usage_count', 'total_hours', 'created_at', 'last_used')
    list_filter = ('user', 'created_at', 'focus_entries__date')
    search_fields = ('description', 'user__username', 'user__email')
    readonly_fields = ('usage_count', 'total_hours', 'last_used', 'created_at')
    ordering = ('-created_at',)
    
    # Inline editing
    inlines = [FocusEntryInline]
    
    # Fieldsets for better organization
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'description')
        }),
        ('Statistics', {
            'fields': ('usage_count', 'total_hours', 'last_used'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def usage_count(self, obj):
        """
        Display the number of focus entries using this reason.
        """
        count = obj.focus_entries.count()
        if count > 0:
            url = reverse('admin:core_focusentry_changelist') + f'?reason__id__exact={obj.id}'
            return format_html('<a href="{}">{} entries</a>', url, count)
        return '0 entries'
    usage_count.short_description = 'Usage Count'
    usage_count.admin_order_field = 'focus_entries_count'
    
    def total_hours(self, obj):
        """
        Display total hours from focus entries using this reason.
        """
        total = obj.focus_entries.aggregate(total=Sum('hours'))['total'] or 0
        total_value = float(total)
        return f"{total_value:.1f} hours"
        
    total_hours.short_description = 'Total Hours'
    total_hours.admin_order_field = 'focus_entries__hours__sum'
    
    def last_used(self, obj):
        """
        Display the date when this reason was last used.
        """
        last_entry = obj.focus_entries.order_by('-date').first()
        if last_entry:
            return last_entry.date
        return 'Never used'
    last_used.short_description = 'Last Used'
    last_used.admin_order_field = 'focus_entries__date'
    
    def get_queryset(self, request):
        """
        Optimize queries with annotations for statistics.
        """
        queryset = super().get_queryset(request)
        return queryset.annotate(
            focus_entries_count=Count('focus_entries'),
        ).prefetch_related('focus_entries')
    
    def has_delete_permission(self, request, obj=None):
        """
        Prevent deletion if reason is used in focus entries.
        """
        if obj and obj.focus_entries.exists():
            return False
        return super().has_delete_permission(request, obj)
    
    def get_readonly_fields(self, request, obj=None):
        """
        Make description readonly if reason is in use.
        """
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.focus_entries.exists():
            readonly_fields.append('description')
        return readonly_fields


class FocusEntryDateFilter(admin.SimpleListFilter):
    """
    Custom filter for focus entry dates.
    """
    title = _('Date Range')
    parameter_name = 'date_range'
    
    def lookups(self, request, model_admin):
        return (
            ('today', _('Today')),
            ('yesterday', _('Yesterday')),
            ('this_week', _('This Week')),
            ('last_week', _('Last Week')),
            ('this_month', _('This Month')),
            ('last_month', _('Last Month')),
            ('no_hours', _('No Hours Recorded')),
            ('with_hours', _('With Hours Recorded')),
        )
    
    def queryset(self, request, queryset):
        today = date.today()
        
        if self.value() == 'today':
            return queryset.filter(date=today)
        elif self.value() == 'yesterday':
            return queryset.filter(date=today - timedelta(days=1))
        elif self.value() == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            return queryset.filter(date__gte=start_of_week)
        elif self.value() == 'last_week':
            start_of_week = today - timedelta(days=today.weekday())
            start_of_last_week = start_of_week - timedelta(days=7)
            end_of_last_week = start_of_week - timedelta(days=1)
            return queryset.filter(date__gte=start_of_last_week, date__lte=end_of_last_week)
        elif self.value() == 'this_month':
            return queryset.filter(date__year=today.year, date__month=today.month)
        elif self.value() == 'last_month':
            if today.month == 1:
                last_month = 12
                last_year = today.year - 1
            else:
                last_month = today.month - 1
                last_year = today.year
            return queryset.filter(date__year=last_year, date__month=last_month)
        elif self.value() == 'no_hours':
            return queryset.filter(hours__isnull=True)
        elif self.value() == 'with_hours':
            return queryset.filter(hours__isnull=False)


class FocusEntryHoursFilter(admin.SimpleListFilter):
    """
    Custom filter for focus entry hours.
    """
    title = _('Hours Range')
    parameter_name = 'hours_range'
    
    def lookups(self, request, model_admin):
        return (
            ('0-2', _('0-2 hours')),
            ('2-4', _('2-4 hours')),
            ('4-6', _('4-6 hours')),
            ('6-8', _('6-8 hours')),
            ('8+', _('8+ hours')),
        )
    
    def queryset(self, request, queryset):
        if self.value() == '0-2':
            return queryset.filter(hours__gte=0, hours__lt=2)
        elif self.value() == '2-4':
            return queryset.filter(hours__gte=2, hours__lt=4)
        elif self.value() == '4-6':
            return queryset.filter(hours__gte=4, hours__lt=6)
        elif self.value() == '6-8':
            return queryset.filter(hours__gte=6, hours__lt=8)
        elif self.value() == '8+':
            return queryset.filter(hours__gte=8)
        return queryset


@admin.register(FocusEntry)
class FocusEntryAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for FocusEntry model with advanced features.
    """
    form = FocusEntryForm
    
    # Enhanced list display
    list_display = (
        'user', 'date', 'hours_display', 'reason', 'total_user_entries', 
        'user_avg_hours', 'days_since_entry'
    )
    
    # Advanced filtering
    list_filter = (
        FocusEntryDateFilter,
        FocusEntryHoursFilter,
        'user', 
        'reason', 
        'date',
        ('hours', admin.EmptyFieldListFilter),
    )
    
    # Enhanced search
    search_fields = (
        'user__username', 
        'user__email', 
        'user__first_name', 
        'user__last_name',
        'reason__description'
    )
    
    # Date hierarchy for easy navigation
    date_hierarchy = 'date'
    
    # Default ordering
    ordering = ('-date', 'user')
    
    # Items per page
    list_per_page = 50
    
    # Bulk actions
    actions = [
        'bulk_set_reason',
        'bulk_set_hours',
        'bulk_remove_reason',
        'export_selected_entries',
        'mark_as_productive_day',
    ]
    
    # Enhanced fieldsets
    fieldsets = (
        ('Entry Information', {
            'fields': ('user', 'date', 'hours'),
            'description': 'Basic focus entry information'
        }),
        ('Reason', {
            'fields': ('reason',),
            'classes': ('collapse',),
            'description': 'Optional reason for focus or distraction'
        }),
        ('Statistics', {
            'fields': ('user_avg_hours', 'total_user_entries'),
            'classes': ('collapse',),
            'description': 'User statistics (read-only)'
        }),
    )
    
    # Readonly fields
    readonly_fields = ('user_avg_hours', 'total_user_entries')
    
    def hours_display(self, obj):
        """
        Display hours with color coding and formatting.
        """
        if obj.hours is None:
            return format_html('<span style="color: #999;">No hours</span>')

        # Convert to float safely
        try:
            # Handle both regular floats and SafeString objects
            if hasattr(obj.hours, '__html__'):
                # It's a SafeString, convert to string first
                hours_str = str(obj.hours)
                # Try to extract numeric value
                import re
                match = re.search(r'(\d+\.?\d*)', hours_str)
                if match:
                    hours_value = float(match.group(1))
                else:
                    hours_value = float(hours_str)
            else:
                hours_value = float(obj.hours)
        except (ValueError, TypeError):
            return format_html('<span style="color: #999;">Invalid hours</span>')
        
        # Color coding based on hours
        if hours_value >= 8:
            color = '#28a745'  # Green for productive days
        elif hours_value >= 6:
            color = '#17a2b8'  # Blue for good days
        elif hours_value >= 4:
            color = '#ffc107'  # Yellow for moderate days
        else:
            color = '#dc3545'  # Red for low focus days
        
        # Format the hours value as string first, then use in format_html
        formatted_hours = f"{hours_value:.1f}h"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, formatted_hours
        )
    hours_display.short_description = 'Hours'
    hours_display.admin_order_field = 'hours'
    
    def total_user_entries(self, obj):
        """
        Display total entries for this user with link.
        """
        count = FocusEntry.objects.filter(user=obj.user).count()
        url = reverse('admin:core_focusentry_changelist') + f'?user__id__exact={obj.user.id}'
        return format_html('<a href="{}">{} total</a>', url, count)
    total_user_entries.short_description = 'User Total'
    total_user_entries.admin_order_field = 'user_entries_count'
    
    def user_avg_hours(self, obj):
        """
        Display average hours for this user.
        """
        avg = FocusEntry.objects.filter(user=obj.user, hours__isnull=False).aggregate(
            avg_hours=Avg('hours')
        )['avg_hours'] or 0
        
        # Ensure we have a proper float value
        try:
            avg_value = float(str(avg))
        except (ValueError, TypeError):
            avg_value = 0.0
            
        return f"{avg_value:.1f}h avg"
    user_avg_hours.short_description = 'User Avg'
    
    def days_since_entry(self, obj):
        """
        Display days since this entry was created.
        """
        days = (date.today() - obj.date).days
        if days == 0:
            return 'Today'
        elif days == 1:
            return 'Yesterday'
        else:
            return f'{days} days ago'
    days_since_entry.short_description = 'Age'
    
    def get_queryset(self, request):
        """
        Optimize queries with select_related and annotations.
        """
        queryset = super().get_queryset(request).select_related('user', 'reason')
        return queryset.annotate(
            user_entries_count=Count('user__focus_entries'),
        )
    
    # Bulk Actions
    def bulk_set_reason(self, request, queryset):
        """
        Bulk action to set reason for selected entries.
        """
        # This would typically redirect to a custom form
        # For now, we'll use a simple approach
        reason_id = request.POST.get('reason_id')
        if reason_id:
            try:
                reason = Reason.objects.get(id=reason_id)
                updated = queryset.update(reason=reason)
                self.message_user(
                    request, 
                    f'Successfully set reason "{reason.description}" for {updated} entries.',
                    messages.SUCCESS
                )
            except Reason.DoesNotExist:
                self.message_user(
                    request, 
                    'Invalid reason ID provided.',
                    messages.ERROR
                )
        else:
            self.message_user(
                request, 
                'Please provide a reason ID.',
                messages.WARNING
            )
    bulk_set_reason.short_description = "Set reason for selected entries"
    
    def bulk_set_hours(self, request, queryset):
        """
        Bulk action to set hours for selected entries.
        """
        hours = request.POST.get('hours')
        if hours:
            try:
                hours_float = float(hours)
                if 0 <= hours_float <= 24:
                    updated = queryset.update(hours=hours_float)
                    self.message_user(
                        request, 
                        f'Successfully set {hours_float} hours for {updated} entries.',
                        messages.SUCCESS
                    )
                else:
                    self.message_user(
                        request, 
                        'Hours must be between 0 and 24.',
                        messages.ERROR
                    )
            except ValueError:
                self.message_user(
                    request, 
                    'Invalid hours value provided.',
                    messages.ERROR
                )
        else:
            self.message_user(
                request, 
                'Please provide hours value.',
                messages.WARNING
            )
    bulk_set_hours.short_description = "Set hours for selected entries"
    
    def bulk_remove_reason(self, request, queryset):
        """
        Bulk action to remove reason from selected entries.
        """
        updated = queryset.update(reason=None)
        self.message_user(
            request, 
            f'Successfully removed reason from {updated} entries.',
            messages.SUCCESS
        )
    bulk_remove_reason.short_description = "Remove reason from selected entries"
    
    def mark_as_productive_day(self, request, queryset):
        """
        Bulk action to mark entries as productive (8+ hours).
        """
        updated = queryset.update(hours=8.0)
        self.message_user(
            request, 
            f'Successfully marked {updated} entries as productive days (8 hours).',
            messages.SUCCESS
        )
    mark_as_productive_day.short_description = "Mark as productive day (8h)"
    
    def export_selected_entries(self, request, queryset):
        """
        Bulk action to export selected entries (placeholder).
        """
        self.message_user(
            request, 
            f'Export functionality for {queryset.count()} entries would be implemented here.',
            messages.INFO
        )
    export_selected_entries.short_description = "Export selected entries"
    
    # Custom admin methods
    def get_readonly_fields(self, request, obj=None):
        """
        Make certain fields readonly based on context.
        """
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.date < date.today() - timedelta(days=30):
            readonly_fields.extend(['date', 'hours', 'reason'])
        return readonly_fields
    
    def has_delete_permission(self, request, obj=None):
        """
        Allow deletion but with confirmation for recent entries.
        """
        return True
    
    def save_model(self, request, obj, form, change):
        """
        Custom save logic with validation.
        """
        # Additional validation can be added here
        super().save_model(request, obj, form, change)
        
        # Show success message with context
        if change:
            self.message_user(
                request, 
                f'Focus entry for {obj.user.username} on {obj.date} updated successfully.',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request, 
                f'New focus entry for {obj.user.username} on {obj.date} created successfully.',
                messages.SUCCESS
            )


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """
    Admin interface for Feedback model.
    """
    list_display = ('user', 'rating_display', 'text_preview', 'created_at', 'has_both_fields')
    list_filter = ('rating', 'created_at', 'user')
    search_fields = ('user__username', 'user__email', 'text')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    # Fieldsets for better organization
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Feedback Content', {
            'fields': ('rating', 'text'),
            'description': 'At least one field (rating or text) is required'
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def rating_display(self, obj):
        """
        Display rating with stars.
        """
        if obj.rating is None:
            return format_html('<span style="color: #999;">No rating</span>')
        
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html(
            '<span style="color: #ffc107; font-size: 16px;">{}</span> ({})',
            stars, obj.rating
        )
    rating_display.short_description = 'Rating'
    rating_display.admin_order_field = 'rating'
    
    def text_preview(self, obj):
        """
        Display text preview with truncation.
        """
        if not obj.text:
            return format_html('<span style="color: #999;">No text</span>')
        
        preview = obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
        return format_html('<span title="{}">{}</span>', obj.text, preview)
    text_preview.short_description = 'Text Preview'
    
    def has_both_fields(self, obj):
        """
        Display whether feedback has both rating and text.
        """
        has_rating = obj.rating is not None
        has_text = obj.text and obj.text.strip()
        
        if has_rating and has_text:
            return format_html('<span style="color: #28a745;">✓ Both</span>')
        elif has_rating:
            return format_html('<span style="color: #17a2b8;">Rating only</span>')
        elif has_text:
            return format_html('<span style="color: #ffc107;">Text only</span>')
        else:
            return format_html('<span style="color: #dc3545;">Invalid</span>')
    has_both_fields.short_description = 'Type'
    
    def get_queryset(self, request):
        """
        Optimize queries with select_related.
        """
        return super().get_queryset(request).select_related('user')
    
    def has_add_permission(self, request):
        """
        Allow adding feedback through admin.
        """
        return True
    
    def has_change_permission(self, request, obj=None):
        """
        Allow editing feedback.
        """
        return True
    
    def has_delete_permission(self, request, obj=None):
        """
        Allow deleting feedback.
        """
        return True


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    """
    Admin interface for Goal model.
    """
    list_display = ('user', 'status_display', 'hours_display', 'created_at', 'updated_at')
    list_filter = ('is_activated', 'hours', 'created_at', 'user')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)
    
    # Fieldsets for better organization
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Goal Settings', {
            'fields': ('is_activated', 'hours'),
            'description': 'Configure goal activation and target hours'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        """
        Display activation status with color coding.
        """
        if obj.is_activated:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">○ Inactive</span>'
            )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'is_activated'
    
    def hours_display(self, obj):
        """
        Display hours with color coding based on target.
        """
        if obj.hours >= 8:
            color = '#28a745'  # Green for high targets
        elif obj.hours >= 6:
            color = '#17a2b8'  # Blue for moderate targets
        elif obj.hours >= 4:
            color = '#ffc107'  # Yellow for low targets
        else:
            color = '#dc3545'  # Red for very low targets
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}h/day</span>',
            color, obj.hours
        )
    hours_display.short_description = 'Target Hours'
    hours_display.admin_order_field = 'hours'
    
    def get_queryset(self, request):
        """
        Optimize queries with select_related.
        """
        return super().get_queryset(request).select_related('user')
    
    def has_add_permission(self, request):
        """
        Allow adding goals through admin.
        """
        return True
    
    def has_change_permission(self, request, obj=None):
        """
        Allow editing goals.
        """
        return True
    
    def has_delete_permission(self, request, obj=None):
        """
        Allow deleting goals.
        """
        return True 