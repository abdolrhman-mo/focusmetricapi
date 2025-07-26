from django.urls import path
from .views import (
    GoogleOAuthView, 
    UserProfileView, 
    UserProfileUpdateView,
    LogoutView,
    UserStatsView,
    DeleteAccountView
)

app_name = 'authentication'

urlpatterns = [
    # OAuth Authentication
    path('google/', GoogleOAuthView.as_view(), name='google_oauth'),
    
    # Session Management
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # User Profile Management
    path('profile/', UserProfileView.as_view(), name='profile_get'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile_update'),
    path('profile/delete/', DeleteAccountView.as_view(), name='profile_delete'),
    
    # User Statistics
    path('stats/', UserStatsView.as_view(), name='stats'),
] 