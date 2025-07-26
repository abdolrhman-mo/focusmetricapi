from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import ProtectedError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Reason, FocusEntry
from .serializers import (
    ReasonSerializer, 
    ReasonListSerializer, 
    ReasonDetailSerializer
)


class ReasonViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user reasons.
    
    Provides full CRUD operations for reasons with proper user isolation.
    Users can only access and modify their own reasons.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Return reasons for the current user only.
        """
        return Reason.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'list':
            return ReasonListSerializer
        elif self.action == 'retrieve':
            return ReasonDetailSerializer
        else:
            return ReasonSerializer
    
    @swagger_auto_schema(
        operation_description="List all reasons for the authenticated user",
        responses={
            200: openapi.Response(
                description="List of user's reasons",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                            'description': openapi.Schema(type=openapi.TYPE_STRING),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            'usage_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        }
                    )
                )
            ),
            401: openapi.Response(description="Authentication required")
        }
    )
    def list(self, request, *args, **kwargs):
        """
        List all reasons for the authenticated user.
        """
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Create a new reason",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['description'],
            properties={
                'description': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Description of the reason (max 500 characters)"
                ),
            }
        ),
        responses={
            201: openapi.Response(description="Reason created successfully"),
            400: openapi.Response(description="Invalid request data"),
            401: openapi.Response(description="Authentication required")
        }
    )
    def create(self, request, *args, **kwargs):
        """
        Create a new reason for the authenticated user.
        """
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Retrieve a specific reason with detailed information",
        responses={
            200: openapi.Response(
                description="Reason details",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                        'description': openapi.Schema(type=openapi.TYPE_STRING),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'usage_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'recent_entries': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                                    'hours': openapi.Schema(type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT),
                                }
                            )
                        ),
                    }
                )
            ),
            401: openapi.Response(description="Authentication required"),
            404: openapi.Response(description="Reason not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific reason with detailed information.
        """
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update a reason",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'description': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Updated description of the reason (max 500 characters)"
                ),
            }
        ),
        responses={
            200: openapi.Response(description="Reason updated successfully"),
            400: openapi.Response(description="Invalid request data"),
            401: openapi.Response(description="Authentication required"),
            404: openapi.Response(description="Reason not found")
        }
    )
    def update(self, request, *args, **kwargs):
        """
        Update a reason (full update).
        """
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update a reason",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'description': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Updated description of the reason (max 500 characters)"
                ),
            }
        ),
        responses={
            200: openapi.Response(description="Reason updated successfully"),
            400: openapi.Response(description="Invalid request data"),
            401: openapi.Response(description="Authentication required"),
            404: openapi.Response(description="Reason not found")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a reason.
        """
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Delete a reason. Cannot delete if reason is used in focus entries.",
        responses={
            204: openapi.Response(description="Reason deleted successfully"),
            400: openapi.Response(
                description="Cannot delete - reason is used in focus entries",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'usage_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            ),
            401: openapi.Response(description="Authentication required"),
            404: openapi.Response(description="Reason not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        Delete a reason. 
        Prevents deletion if the reason is used in any focus entries.
        """
        reason = self.get_object()
        
        # Check if reason is used in any focus entries
        usage_count = reason.focus_entries.count()
        if usage_count > 0:
            return Response(
                {
                    "error": f"Cannot delete reason '{reason.description}' because it is used in {usage_count} focus entries. Please remove it from all entries first.",
                    "usage_count": usage_count
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
