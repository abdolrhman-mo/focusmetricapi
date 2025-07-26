from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReasonViewSet, FocusEntryViewSet, BulkUpdateView

app_name = 'core'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'reasons', ReasonViewSet, basename='reason')
router.register(r'entries', FocusEntryViewSet, basename='entry')

urlpatterns = [
    # Custom endpoints (must come before router to avoid conflicts)
    path('entries/bulk-update/', BulkUpdateView.as_view(), name='bulk_update'),
    
    # Router endpoints
    path('', include(router.urls)),
] 