from django.contrib import admin
from .models import Reason, FocusEntry

@admin.register(Reason)
class ReasonAdmin(admin.ModelAdmin):
    list_display = ('description', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('description',)

@admin.register(FocusEntry)
class FocusEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'hours', 'reason')
    list_filter = ('user', 'date', 'reason')
    search_fields = ('user__username',)
    date_hierarchy = 'date' 