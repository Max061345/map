import django_filters
from .models import Location


class LocationFilter(django_filters.FilterSet):    
    category = django_filters.NumberFilter(field_name='category_id')
    category_slug = django_filters.CharFilter(field_name='category__slug', lookup_expr='exact')
    
    author = django_filters.NumberFilter(field_name='author_id')
    author_username = django_filters.CharFilter(field_name='author__username', lookup_expr='iexact')
    
    rating = django_filters.NumberFilter(field_name='avg_rating', lookup_expr='exact')
    min_rating = django_filters.NumberFilter(field_name='avg_rating', lookup_expr='gte')
    max_rating = django_filters.NumberFilter(field_name='avg_rating', lookup_expr='lte')

    class Meta:
        model = Location
        fields = [
            'category',
            'category_slug',
            'author',
            'author_username',
            'rating',
            'min_rating',
            'max_rating',
        ]