from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from django.conf import settings
from google.auth.transport import requests
from google.oauth2 import id_token
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import GoogleAuthSerializer, UserSerializer, UserUpdateSerializer
import logging

logger = logging.getLogger(__name__)


class GoogleOAuthView(APIView):
    """
    Google OAuth authentication endpoint.
    
    Accepts a Google OAuth ID token, verifies it with Google,
    and returns a DRF authentication token.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Authenticate with Google OAuth token",
        request_body=GoogleAuthSerializer,
        responses={
            200: openapi.Response(
                description="Authentication successful",
                examples={
                    "application/json": {
                        "token": "drf-token-key-example",
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "first_name": "John",
                            "last_name": "Doe",
                            "name": "John Doe",
                            "date_joined": "2024-01-15T10:30:00Z"
                        },
                        "is_new_user": True
                    }
                }
            ),
            400: openapi.Response(
                description="Bad request - Invalid token",
                examples={
                    "application/json": {
                        "error": "Invalid Google token"
                    }
                }
            )
        },
        tags=['Authentication']
    )
    def post(self, request):
        """Handle Google OAuth authentication."""
        serializer = GoogleAuthSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid request data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        google_token = serializer.validated_data['token']
        
        try:
            # Verify the Google OAuth token
            user_info = self._verify_google_token(google_token)
            
            # Create or get user
            user, is_new_user = self._get_or_create_user(user_info)
            
            # Generate or get DRF token
            token, created = Token.objects.get_or_create(user=user)
            
            # Serialize user data
            user_serializer = UserSerializer(user)
            
            logger.info(f"User {user.email} authenticated successfully. New user: {is_new_user}")
            
            return Response({
                "token": token.key,
                "user": user_serializer.data,
                "is_new_user": is_new_user
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            logger.warning(f"Invalid Google token provided: {str(e)}")
            return Response(
                {"error": "Invalid Google token"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error during Google OAuth: {str(e)}")
            return Response(
                {"error": "Authentication failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _verify_google_token(self, token):
        """
        Verify Google OAuth token and extract user information.
        
        Args:
            token (str): Google OAuth ID token
            
        Returns:
            dict: User information from Google
            
        Raises:
            ValueError: If token is invalid
        """
        try:
            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(),
            )
            
            # Verify the issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Invalid issuer')
            
            return {
                'email': idinfo.get('email'),
                'first_name': idinfo.get('given_name', ''),
                'last_name': idinfo.get('family_name', ''),
                'google_id': idinfo.get('sub'),
            }
            
        except ValueError as e:
            raise ValueError(f"Invalid token: {str(e)}")
        except Exception as e:
            raise ValueError(f"Token verification failed: {str(e)}")
    
    def _get_or_create_user(self, user_info):
        """
        Get existing user or create new user from Google user info.
        
        Args:
            user_info (dict): User information from Google
            
        Returns:
            tuple: (User object, is_new_user boolean)
        """
        email = user_info['email']
        
        if not email:
            raise ValueError("No email provided by Google")
        
        try:
            # Try to get existing user
            user = User.objects.get(email=email)
            is_new_user = False
            
            # Update user info if needed
            updated = False
            if user.first_name != user_info['first_name']:
                user.first_name = user_info['first_name']
                updated = True
            if user.last_name != user_info['last_name']:
                user.last_name = user_info['last_name']
                updated = True
            
            if updated:
                user.save()
                logger.info(f"Updated user info for {email}")
            
        except User.DoesNotExist:
            # Create new user
            user = User.objects.create_user(
                username=email,  # Use email as username
                email=email,
                first_name=user_info['first_name'],
                last_name=user_info['last_name'],
                password=None  # No password for OAuth users
            )
            is_new_user = True
            logger.info(f"Created new user: {email}")
        
        return user, is_new_user


class UserProfileView(APIView):
    """
    Retrieve current authenticated user's profile information.
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get current user's profile information",
        responses={
            200: openapi.Response(
                description="Profile retrieved successfully",
                examples={
                    "application/json": {
                        "id": 1,
                        "email": "user@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "name": "John Doe",
                        "date_joined": "2024-01-15T10:30:00Z"
                    }
                }
            ),
            401: openapi.Response(
                description="Authentication required",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            )
        },
        tags=['Authentication']
    )
    def get(self, request):
        """Get current user's profile."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserProfileUpdateView(APIView):
    """
    Update current authenticated user's profile information.
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Update current user's profile information",
        request_body=UserUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Profile updated successfully",
                examples={
                    "application/json": {
                        "id": 1,
                        "email": "user@example.com",
                        "first_name": "John",
                        "last_name": "Smith",
                        "name": "John Smith",
                        "date_joined": "2024-01-15T10:30:00Z"
                    }
                }
            ),
            400: openapi.Response(
                description="Validation error",
                examples={
                    "application/json": {
                        "first_name": ["First name cannot be empty."]
                    }
                }
            ),
            401: openapi.Response(
                description="Authentication required",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            )
        },
        tags=['Authentication']
    )
    def put(self, request):
        """Update user profile (PUT - full update)."""
        serializer = UserUpdateSerializer(request.user, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            # Return full user profile after update
            user_serializer = UserSerializer(request.user)
            logger.info(f"User {request.user.email} updated profile")
            return Response(user_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Partially update current user's profile information",
        request_body=UserUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Profile updated successfully",
                examples={
                    "application/json": {
                        "id": 1,
                        "email": "user@example.com",
                        "first_name": "John",
                        "last_name": "Smith",
                        "name": "John Smith",
                        "date_joined": "2024-01-15T10:30:00Z"
                    }
                }
            ),
            400: openapi.Response(
                description="Validation error",
                examples={
                    "application/json": {
                        "first_name": ["First name cannot be empty."]
                    }
                }
            ),
            401: openapi.Response(
                description="Authentication required",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            )
        },
        tags=['Authentication']
    )
    def patch(self, request):
        """Update user profile (PATCH - partial update)."""
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            # Return full user profile after update
            user_serializer = UserSerializer(request.user)
            logger.info(f"User {request.user.email} partially updated profile")
            return Response(user_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 


class LogoutView(APIView):
    """
    Logout endpoint that invalidates the user's authentication token.
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Logout and invalidate authentication token",
        responses={
            200: openapi.Response(
                description="Successfully logged out",
                examples={
                    "application/json": {
                        "message": "Successfully logged out"
                    }
                }
            ),
            401: openapi.Response(
                description="Authentication required",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            )
        },
        tags=['Authentication']
    )
    def post(self, request):
        """Logout user by deleting their authentication token."""
        try:
            # Get the user's token and delete it
            token = Token.objects.get(user=request.user)
            token.delete()
            
            logger.info(f"User {request.user.email} logged out successfully")
            
            return Response(
                {"message": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
        except Token.DoesNotExist:
            # Token doesn't exist, but user is authenticated (shouldn't happen)
            logger.warning(f"Token not found for authenticated user {request.user.email}")
            return Response(
                {"message": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error during logout for user {request.user.email}: {str(e)}")
            return Response(
                {"error": "Logout failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserStatsView(APIView):
    """
    Retrieve user's focus tracking statistics.
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get current user's focus tracking statistics",
        responses={
            200: openapi.Response(
                description="Statistics retrieved successfully",
                examples={
                    "application/json": {
                        "total_focus_entries": 45,
                        "total_focus_hours": 180.5,
                        "current_streak": 7,
                        "longest_streak": 12,
                        "average_daily_hours": 4.2,
                        "most_used_reason": {
                            "id": "uuid-string",
                            "description": "Work focus",
                            "usage_count": 25
                        },
                        "account_created": "2024-01-15T10:30:00Z",
                        "days_since_signup": 30
                    }
                }
            ),
            401: openapi.Response(
                description="Authentication required",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            )
        },
        tags=['Authentication']
    )
    def get(self, request):
        """Get user's focus tracking statistics."""
        try:
            from django.db.models import Count, Sum, Avg
            from django.utils import timezone
            from datetime import timedelta
            from core.models import FocusEntry, Reason
            
            user = request.user
            
            # Get all focus entries for the user
            focus_entries = FocusEntry.objects.filter(user=user)
            
            # Basic statistics
            total_entries = focus_entries.count()
            total_hours = focus_entries.aggregate(Sum('hours'))['hours__sum'] or 0
            average_hours = focus_entries.aggregate(Avg('hours'))['hours__avg'] or 0
            
            # Most used reason
            most_used_reason = None
            if total_entries > 0:
                reason_usage = focus_entries.exclude(reason__isnull=True).values(
                    'reason__id', 'reason__description'
                ).annotate(
                    usage_count=Count('reason')
                ).order_by('-usage_count').first()
                
                if reason_usage:
                    most_used_reason = {
                        "id": str(reason_usage['reason__id']),
                        "description": reason_usage['reason__description'],
                        "usage_count": reason_usage['usage_count']
                    }
            
            # Calculate streaks (consecutive days with entries)
            current_streak = 0
            longest_streak = 0
            
            if total_entries > 0:
                # Get all dates with entries, ordered by date
                entry_dates = focus_entries.values_list('date', flat=True).order_by('date')
                dates_list = list(entry_dates)
                
                if dates_list:
                    # Calculate current streak (from today backwards)
                    today = timezone.now().date()
                    current_date = today
                    
                    # Check if there's an entry for today or yesterday to start streak
                    if today in dates_list or (today - timedelta(days=1)) in dates_list:
                        if today not in dates_list:
                            current_date = today - timedelta(days=1)
                        
                        while current_date in dates_list:
                            current_streak += 1
                            current_date -= timedelta(days=1)
                    
                    # Calculate longest streak
                    temp_streak = 1
                    for i in range(1, len(dates_list)):
                        if dates_list[i] - dates_list[i-1] == timedelta(days=1):
                            temp_streak += 1
                            longest_streak = max(longest_streak, temp_streak)
                        else:
                            temp_streak = 1
                    longest_streak = max(longest_streak, temp_streak)
            
            # Account information
            days_since_signup = (timezone.now().date() - user.date_joined.date()).days
            
            stats = {
                "total_focus_entries": total_entries,
                "total_focus_hours": float(total_hours),
                "current_streak": current_streak,
                "longest_streak": longest_streak,
                "average_daily_hours": round(float(average_hours), 2) if average_hours else 0,
                "most_used_reason": most_used_reason,
                "account_created": user.date_joined.isoformat(),
                "days_since_signup": days_since_signup
            }
            
            logger.info(f"Statistics retrieved for user {user.email}")
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error retrieving statistics for user {request.user.email}: {str(e)}")
            return Response(
                {"error": "Failed to retrieve statistics. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteAccountView(APIView):
    """
    Delete user account and all associated data.
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Delete current user's account and all associated data",
        responses={
            204: openapi.Response(
                description="Account deleted successfully"
            ),
            401: openapi.Response(
                description="Authentication required",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            ),
            500: openapi.Response(
                description="Server error during account deletion",
                examples={
                    "application/json": {
                        "error": "Account deletion failed. Please try again."
                    }
                }
            )
        },
        tags=['Authentication']
    )
    def delete(self, request):
        """Delete user account and all associated data."""
        try:
            user = request.user
            user_email = user.email
            
            # Django's cascade deletion will automatically delete:
            # - All FocusEntry objects (user foreign key with CASCADE)
            # - All Reason objects (user foreign key with CASCADE)  
            # - The user's Token (if it exists)
            
            user.delete()
            
            logger.info(f"User account {user_email} and all associated data deleted successfully")
            
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"Error deleting account for user {request.user.email}: {str(e)}")
            return Response(
                {"error": "Account deletion failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 