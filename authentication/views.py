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