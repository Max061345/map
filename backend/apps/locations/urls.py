from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, LocationViewSet, ReviewViewSet


router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('', include(router.urls)),
]