from django.urls import path
from .views import GoogleOAuthView, UserProfileView, UserProfileUpdateView

app_name = 'authentication'

urlpatterns = [
    path('google/', GoogleOAuthView.as_view(), name='google_oauth'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='user_profile_update'),
] 