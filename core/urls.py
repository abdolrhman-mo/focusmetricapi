from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReasonViewSet

app_name = 'core'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'reasons', ReasonViewSet, basename='reason')

urlpatterns = [
    path('', include(router.urls)),
] 