from rest_framework.filters import OrderingFilter


class LocationOrderingFilter(OrderingFilter):
    """
    Custom OrderingFilter that maps API parameter 'rating' to annotated ORM field 'avg_rating'.
    """
    ordering_fields_map = {
        'rating': 'avg_rating',
    }

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if ordering:
            mapped_ordering = []
            for term in ordering:
                desc = term.startswith('-')
                field = term.lstrip('-')
                mapped_field = self.ordering_fields_map.get(field, field)
                mapped_ordering.append(f"-{mapped_field}" if desc else mapped_field)
            return queryset.order_by(*mapped_ordering)
        return queryset