from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReasonViewSet, FocusEntryViewSet, BulkUpdateView, BulkDeleteView, FeedbackViewSet, GoalViewSet, GoalActivateView, GoalDeactivateView

app_name = 'core'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'reasons', ReasonViewSet, basename='reason')
router.register(r'entries', FocusEntryViewSet, basename='entry')
router.register(r'feedback', FeedbackViewSet, basename='feedback')
router.register(r'goals', GoalViewSet, basename='goal')

urlpatterns = [
    # Custom endpoints (must come before router to avoid conflicts)
    path('entries/bulk-update/', BulkUpdateView.as_view(), name='bulk_update'),
    path('entries/bulk-delete/', BulkDeleteView.as_view(), name='bulk_delete'),
    path('goals/activate/', GoalActivateView.as_view(), name='goal_activate'),
    path('goals/deactivate/', GoalDeactivateView.as_view(), name='goal_deactivate'),
    # Router endpoints
    path('', include(router.urls)),
] 