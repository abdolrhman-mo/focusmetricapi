from django.contrib import admin
from django.db.models import Count, Sum
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Reason, FocusEntry


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
        return f"{total:.1f} hours"
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


@admin.register(FocusEntry)
class FocusEntryAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for FocusEntry model.
    """
    list_display = ('user', 'date', 'hours', 'reason', 'total_user_entries')
    list_filter = ('user', 'date', 'reason', 'hours')
    search_fields = ('user__username', 'user__email', 'reason__description')
    date_hierarchy = 'date'
    ordering = ('-date', 'user')
    
    # Fieldsets for better organization
    fieldsets = (
        ('Entry Information', {
            'fields': ('user', 'date', 'hours')
        }),
        ('Reason', {
            'fields': ('reason',),
            'classes': ('collapse',)
        }),
    )
    
    def total_user_entries(self, obj):
        """
        Display total entries for this user.
        """
        count = FocusEntry.objects.filter(user=obj.user).count()
        url = reverse('admin:core_focusentry_changelist') + f'?user__id__exact={obj.user.id}'
        return format_html('<a href="{}">{} total</a>', url, count)
    total_user_entries.short_description = 'User Total'
    
    def get_queryset(self, request):
        """
        Optimize queries with select_related.
        """
        return super().get_queryset(request).select_related('user', 'reason') 