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
    path('google/', GoogleOAuthView.as_view(), name='google_oauth'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='user_profile_update'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('stats/', UserStatsView.as_view(), name='user_stats'),
    path('profile/delete/', DeleteAccountView.as_view(), name='delete_account'),
] 