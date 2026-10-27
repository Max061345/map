import io
import pandas as pd
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from rest_framework.renderers import BaseRenderer, BrowsableAPIRenderer, JSONRenderer


from .models import Category, Location, Review, ReviewVote
from .permissions import IsAdminOrReadOnly, IsAuthorOrAdminOrReadOnly
from .serializers import CategorySerializer, LocationSerializer, ReviewSerializer, ReviewVoteSerializer
from .services import record_location_view
from .ordering import LocationOrderingFilter
from .pagination import StandardResultsSetPagination
from .filters import LocationFilter
from .caching import (
    generate_locations_cache_key,
    invalidate_locations_cache,
    LOCATIONS_CACHE_TIMEOUT,
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class PassthroughCSVRenderer(BaseRenderer):
    media_type = 'text/csv'
    format = 'csv'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class LocationViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for locations with caching, filtering, metrics, and data export.
    """
    serializer_class = LocationSerializer
    permission_classes = [IsAuthorOrAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination

    filter_backends = [DjangoFilterBackend, SearchFilter, LocationOrderingFilter]
    filterset_class = LocationFilter
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'rating', 'avg_rating', 'popularity']
    ordering = ['-created_at']

    def get_queryset(self):
        return Location.objects.with_metrics().select_related('category', 'author')

    def list(self, request, *args, **kwargs):
        cache_key = generate_locations_cache_key(request.query_params)
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=LOCATIONS_CACHE_TIMEOUT)
        return response

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        record_location_view(request, instance)
        instance = self.get_queryset().get(pk=instance.pk)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        url_path='export',
        renderer_classes=[JSONRenderer, BrowsableAPIRenderer, PassthroughCSVRenderer],
    )
    def export(self, request):
        """
        Exports the filtered list of locations in JSON or CSV format using pandas.
        """
        export_format = request.query_params.get('format', 'json').lower()

        if export_format not in ['json', 'csv']:
            return Response(
                {"detail": "Invalid export format. Supported formats are 'json' and 'csv'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.filter_queryset(self.get_queryset())

        records = [
            {
                "id": loc.id,
                "name": loc.name,
                "description": loc.description,
                "category": loc.category.name if loc.category else None,
                "address": loc.address,
                "latitude": float(loc.latitude),
                "longitude": float(loc.longitude),
                "author": loc.author.username if loc.author else None,
                "rating": round(loc.avg_rating, 2),
                "reviews_count": loc.reviews_count,
                "views_last_7_days": loc.views_7d,
                "popularity": round(loc.popularity, 2),
                "created_at": loc.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for loc in queryset
        ]

        df = pd.DataFrame(records)

        if export_format == 'csv':
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False, encoding='utf-8')
            response = HttpResponse(csv_buffer.getvalue(), content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="locations.csv"'
            return response
        
        json_data = df.to_json(orient='records', force_ascii=False, indent=2)
        response = HttpResponse(json_data, content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="locations.json"'
        return response

class ReviewViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for location reviews and voting.
    """
    queryset = Review.objects.select_related('author', 'location').prefetch_related('votes').all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthorOrAdminOrReadOnly]
    filterset_fields = ['location', 'rating']

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def vote(self, request, pk=None):
        """
        Allows an authenticated user to like or dislike a review once.
        """
        review = self.get_object()
        serializer = ReviewVoteSerializer(
            data=request.data,
            context={'request': request, 'review': review}
        )
        serializer.is_valid(raise_exception=True)

        ReviewVote.objects.create(
            review=review,
            user=request.user,
            vote_type=serializer.validated_data['vote_type']
        )

        return Response(
            {"detail": f"Review has been successfully marked as {serializer.validated_data['vote_type']}."},
            status=status.HTTP_201_CREATED
        )