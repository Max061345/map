from rest_framework import viewsets, status
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from .models import Category, Location, Review, ReviewVote
from .permissions import IsAdminOrReadOnly, IsAuthorOrAdminOrReadOnly
from .serializers import CategorySerializers, LocationSerializer, ReviewSerializer, ReviewVoteSerializer
from .services import record_location_view
from .ordering import LocationOrderingFilter
from .pagination import StandardResultsSetPagination
from .filters import LocationFilter


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializers
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class LocationViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for locations with search, filtering, ordering, pagination, and view tracking.
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