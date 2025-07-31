from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.db.models import ProtectedError
from django.db import transaction
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import date, timedelta

from .models import Reason, FocusEntry, Feedback, Goal
from .serializers import (
    ReasonSerializer, 
    ReasonListSerializer, 
    ReasonDetailSerializer,
    FocusEntrySerializer,
    FocusEntryListSerializer,
    BulkUpdateSerializer,
    BulkDeleteSerializer,
    FeedbackSerializer,
    GoalSerializer,
)


class BulkUpdateView(APIView):
    """
    View for bulk updating focus entries.
    
    Allows updating multiple focus entries at once with transaction safety.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Bulk update focus entries for multiple dates. Supports both reason_id (existing reason) and reason_text (new reason) in single atomic transaction.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['dates'],
            properties={
                'dates': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                    description="List of dates to update (max 31 dates)"
                ),
                'reason_id': openapi.Schema(
                    type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID,
                    description="Reason ID to set (optional, use for existing reasons)"
                ),
                'reason_text': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Reason text to create or find (optional, use for new reasons)"
                ),
                'hours': openapi.Schema(
                    type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT,
                    description="Hours to set (optional)"
                ),
            }
        ),
        responses={
            200: openapi.Response(
                description="Bulk update completed successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'updated_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'created_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'entries': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                                    'date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                                    'hours': openapi.Schema(type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT),
                                    'reason_id': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID, nullable=True),
                                }
                            )
                        ),
                    }
                )
            ),
            400: openapi.Response(description="Invalid request data"),
            401: openapi.Response(description="Authentication required")
        }
    )
    def post(self, request):
        """
        Bulk update focus entries for multiple dates.
        """
        serializer = BulkUpdateSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        dates = serializer.validated_data['dates']
        reason_id = serializer.validated_data.get('reason_id')
        reason_text = serializer.validated_data.get('reason_text')
        hours = serializer.validated_data.get('hours')
        
        # Get reason object if provided
        reason = None
        if reason_text:
            # Create new reason or get existing one with same text
            reason, created = Reason.objects.get_or_create(
                user=request.user,
                description=reason_text,
                defaults={'description': reason_text}
            )
        elif reason_id:
            try:
                reason = Reason.objects.get(id=reason_id, user=request.user)
            except Reason.DoesNotExist:
                return Response(
                    {'error': 'Invalid reason ID or reason does not belong to user'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        updated_count = 0
        created_count = 0
        updated_entries = []
        
        try:
            with transaction.atomic():
                for entry_date in dates:
                    # Try to get existing entry
                    entry, created = FocusEntry.objects.get_or_create(
                        user=request.user,
                        date=entry_date,
                        defaults={
                            'hours': hours,
                            'reason': reason
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        # Update existing entry
                        if hours is not None:
                            entry.hours = hours
                        if reason_id is not None or reason_text is not None:
                            entry.reason = reason
                        entry.save()
                        updated_count += 1
                    
                    # Add to response data
                    updated_entries.append({
                        'id': str(entry.id),
                        'date': entry.date.isoformat(),
                        'hours': entry.hours,
                        'reason_id': str(entry.reason.id) if entry.reason else None,
                    })
                
                return Response({
                    'message': f'Successfully processed {len(dates)} dates',
                    'updated_count': updated_count,
                    'created_count': created_count,
                    'entries': updated_entries
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response(
                {'error': f'Bulk update failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BulkDeleteView(APIView):
    """
    View for bulk deleting focus entries by IDs and/or dates.
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Bulk delete focus entries by IDs and/or dates. Only entries belonging to the authenticated user will be deleted.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                    description="List of FocusEntry IDs to delete (max 50)"
                ),
                'dates': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                    description="List of dates to delete all entries for the user (max 31)"
                ),
            },
            required=[],
        ),
        responses={
            200: openapi.Response(
                description="Bulk delete completed successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'deleted_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'deleted_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID)),
                        'not_found': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                    }
                )
            ),
            400: openapi.Response(description="Invalid request data"),
            401: openapi.Response(description="Authentication required"),
        }
    )
    def post(self, request):
        serializer = BulkDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        ids = serializer.validated_data.get('ids', [])
        dates = serializer.validated_data.get('dates', [])
        user = request.user
        deleted_ids = []
        not_found = []
        try:
            with transaction.atomic():
                # Delete by IDs
                if ids:
                    entries_by_id = list(FocusEntry.objects.filter(user=user, id__in=ids))
                    found_ids = {str(e.id) for e in entries_by_id}
                    deleted_ids.extend(found_ids)
                    not_found.extend([str(i) for i in ids if str(i) not in found_ids])
                    FocusEntry.objects.filter(user=user, id__in=found_ids).delete()
                # Delete by dates
                if dates:
                    entries_by_date = list(FocusEntry.objects.filter(user=user, date__in=dates))
                    found_dates = {str(e.date) for e in entries_by_date}
                    # Only add IDs not already deleted
                    for e in entries_by_date:
                        if str(e.id) not in deleted_ids:
                            deleted_ids.append(str(e.id))
                    not_found.extend([str(d) for d in dates if str(d) not in found_dates])
                    FocusEntry.objects.filter(user=user, date__in=dates).delete()
            return Response({
                'deleted_count': len(deleted_ids),
                'deleted_ids': deleted_ids,
                'not_found': not_found
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'Bulk delete failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FocusEntryFilter(filters.FilterSet):
    """
    Filter for FocusEntry model.
    """
    start_date = filters.DateFilter(field_name='date', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='date', lookup_expr='lte')
    reason = filters.UUIDFilter(field_name='reason__id')
    min_hours = filters.NumberFilter(field_name='hours', lookup_expr='gte')
    max_hours = filters.NumberFilter(field_name='hours', lookup_expr='lte')
    
    class Meta:
        model = FocusEntry
        fields = ['date', 'reason', 'hours']


class FocusEntryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user focus entries.
    
    Provides full CRUD operations for focus tracking with date range filtering,
    ordering, and pagination. Users can only access their own entries.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = FocusEntryFilter
    ordering_fields = ['date', 'hours', 'reason__description']
    ordering = ['-date']  # Default ordering: newest first
    page_size = 50  # Default page size
    
    def get_queryset(self):
        """
        Return focus entries for the current user only.
        Optimized with select_related and prefetch_related.
        """
        return FocusEntry.objects.filter(user=self.request.user)\
            .select_related('user', 'reason')\
            .order_by('-date')
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'list':
            return FocusEntryListSerializer
        else:
            return FocusEntrySerializer
    
    @swagger_auto_schema(
        operation_description="List all focus entries for the authenticated user",
        manual_parameters=[
            openapi.Parameter(
                'start_date', openapi.IN_QUERY, description="Filter entries from this date (YYYY-MM-DD)", 
                type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE
            ),
            openapi.Parameter(
                'end_date', openapi.IN_QUERY, description="Filter entries until this date (YYYY-MM-DD)", 
                type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE
            ),
            openapi.Parameter(
                'reason', openapi.IN_QUERY, description="Filter by reason ID", 
                type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID
            ),
            openapi.Parameter(
                'min_hours', openapi.IN_QUERY, description="Filter entries with hours >= this value", 
                type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT
            ),
            openapi.Parameter(
                'max_hours', openapi.IN_QUERY, description="Filter entries with hours <= this value", 
                type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT
            ),
            openapi.Parameter(
                'ordering', openapi.IN_QUERY, description="Order by field (prefix with - for descending)", 
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'page', openapi.IN_QUERY, description="Page number", 
                type=openapi.TYPE_INTEGER
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of user's focus entries",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'next': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        'previous': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                                    'date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                                    'hours': openapi.Schema(type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT),
                                    'reason_id': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID, nullable=True),
                                    'reason_description': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                }
                            )
                        ),
                    }
                )
            ),
            401: openapi.Response(description="Authentication required")
        }
    )
    def list(self, request, *args, **kwargs):
        """
        List all focus entries for the authenticated user with filtering and pagination.
        """
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Create a new focus entry. Supports both reason_id (existing reason) and reason_text (new reason) in single atomic transaction.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['date'],
            properties={
                'date': openapi.Schema(
                    type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE,
                    description="Entry date (YYYY-MM-DD)"
                ),
                'hours': openapi.Schema(
                    type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT,
                    description="Focus hours (0-24, optional)"
                ),
                'reason_id': openapi.Schema(
                    type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID,
                    description="Reason ID (optional, use for existing reasons)"
                ),
                'reason_text': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Reason text (optional, use for new reasons)"
                ),
            }
        ),
        responses={
            201: openapi.Response(description="Focus entry created successfully"),
            400: openapi.Response(description="Invalid request data"),
            401: openapi.Response(description="Authentication required")
        }
    )
    def create(self, request, *args, **kwargs):
        """
        Create a new focus entry for the authenticated user.
        """
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Retrieve a specific focus entry",
        responses={
            200: openapi.Response(
                description="Focus entry details",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                        'date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                        'hours': openapi.Schema(type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT),
                        'reason': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                                'description': openapi.Schema(type=openapi.TYPE_STRING),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            },
                            nullable=True
                        ),
                    }
                )
            ),
            401: openapi.Response(description="Authentication required"),
            404: openapi.Response(description="Focus entry not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific focus entry with full details.
        """
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update a focus entry (full update). Supports both reason_id (existing reason) and reason_text (new reason) in single atomic transaction.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'date': openapi.Schema(
                    type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE,
                    description="Entry date (YYYY-MM-DD)"
                ),
                'hours': openapi.Schema(
                    type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT,
                    description="Focus hours (0-24, optional)"
                ),
                'reason_id': openapi.Schema(
                    type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID,
                    description="Reason ID (optional, use for existing reasons)"
                ),
                'reason_text': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Reason text (optional, use for new reasons)"
                ),
            }
        ),
        responses={
            200: openapi.Response(description="Focus entry updated successfully"),
            400: openapi.Response(description="Invalid request data"),
            401: openapi.Response(description="Authentication required"),
            404: openapi.Response(description="Focus entry not found")
        }
    )
    def update(self, request, *args, **kwargs):
        """
        Update a focus entry (full update).
        """
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update a focus entry. Supports both reason_id (existing reason) and reason_text (new reason) in single atomic transaction.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'date': openapi.Schema(
                    type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE,
                    description="Entry date (YYYY-MM-DD)"
                ),
                'hours': openapi.Schema(
                    type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT,
                    description="Focus hours (0-24, optional)"
                ),
                'reason_id': openapi.Schema(
                    type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID,
                    description="Reason ID (optional, use for existing reasons)"
                ),
                'reason_text': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Reason text (optional, use for new reasons)"
                ),
            }
        ),
        responses={
            200: openapi.Response(description="Focus entry updated successfully"),
            400: openapi.Response(description="Invalid request data"),
            401: openapi.Response(description="Authentication required"),
            404: openapi.Response(description="Focus entry not found")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a focus entry.
        """
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Delete a focus entry",
        responses={
            204: openapi.Response(description="Focus entry deleted successfully"),
            401: openapi.Response(description="Authentication required"),
            404: openapi.Response(description="Focus entry not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        Delete a focus entry.
        """
        return super().destroy(request, *args, **kwargs)


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


class FeedbackViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user feedback.
    
    Provides creation of feedback with star rating and/or text.
    Users can only create feedback for themselves.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FeedbackSerializer
    http_method_names = ['post']  # Only allow POST for creating feedback
    
    def get_queryset(self):
        """
        Return feedback for the current user only.
        """
        return Feedback.objects.filter(user=self.request.user).order_by('-created_at')
    
    @swagger_auto_schema(
        operation_description="Create a new feedback entry with star rating and/or text. At least one field (rating or text) is required.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'rating': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Star rating from 1 to 5 (optional)"
                ),
                'text': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Feedback text content (optional, minimum 3 characters)"
                ),
            }
        ),
        responses={
            201: openapi.Response(
                description="Feedback created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                        'rating': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                        'text': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid request data",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'rating': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                        'text': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                    }
                )
            ),
            401: openapi.Response(description="Authentication required")
        }
    )
    def create(self, request, *args, **kwargs):
        """
        Create a new feedback entry for the authenticated user.
        """
        return super().create(request, *args, **kwargs)


class GoalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user goals.
    
    Provides goal status retrieval and activation/deactivation.
    Users can only access their own goals.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GoalSerializer
    http_method_names = ['get', 'post']  # Only allow GET and POST
    
    def get_queryset(self):
        """
        Return goal for the current user only.
        """
        return Goal.objects.filter(user=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Get current user's goal status",
        responses={
            200: openapi.Response(
                description="Goal status",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'is_activated': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'hours': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            ),
            401: openapi.Response(description="Authentication required")
        }
    )
    def list(self, request, *args, **kwargs):
        """
        Get current user's goal status.
        """
        goal, created = Goal.objects.get_or_create(
            user=request.user,
            defaults={'is_activated': False, 'hours': 2}
        )
        serializer = self.get_serializer(goal)
        return Response(serializer.data)


class GoalActivateView(APIView):
    """
    View for activating user goals.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Activate user's goal. Creates goal if it doesn't exist.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'hours': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Target hours per day (optional, uses existing if not provided)"
                ),
            }
        ),
        responses={
            200: openapi.Response(
                description="Goal activated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'is_activated': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'hours': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            ),
            400: openapi.Response(description="Invalid request data"),
            401: openapi.Response(description="Authentication required")
        }
    )
    def post(self, request):
        """
        Activate user's goal with optional hours parameter.
        """
        hours = request.data.get('hours')
        
        # Get or create goal
        goal, created = Goal.objects.get_or_create(
            user=request.user,
            defaults={'is_activated': False, 'hours': 2}
        )
        
        # Update hours if provided
        if hours is not None:
            if hours < 1:
                return Response(
                    {'hours': ['Hours must be at least 1.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if hours > 24:
                return Response(
                    {'hours': ['Hours cannot exceed 24 hours per day.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            goal.hours = hours
        
        # Activate goal
        goal.is_activated = True
        goal.save()
        
        serializer = GoalSerializer(goal)
        return Response(serializer.data)


class GoalDeactivateView(APIView):
    """
    View for deactivating user goals.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Deactivate user's goal (preserves hours setting)",
        responses={
            200: openapi.Response(
                description="Goal deactivated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'is_activated': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'hours': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            ),
            401: openapi.Response(description="Authentication required")
        }
    )
    def post(self, request):
        """
        Deactivate user's goal (preserves hours setting).
        """
        goal, created = Goal.objects.get_or_create(
            user=request.user,
            defaults={'is_activated': False, 'hours': 2}
        )
        
        goal.is_activated = False
        goal.save()
        
        serializer = GoalSerializer(goal)
        return Response(serializer.data)
