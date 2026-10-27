from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import Category
from .permissions import IsAdminOrReadOnly
from .serializers import CategorySerializers


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializers
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']