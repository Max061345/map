from django.core.cache import cache
from .models import LocationView


def get_client_ip(request) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def record_location_view(request, location) -> bool:
    """
    Increments location view count once per user/IP per hour using Redis.
    Returns True if a new view was recorded, False otherwise.
    """
    if request.user.is_authenticated:
        identifier = f"user:{request.user.id}"
    else:
        ip = get_client_ip(request)
        identifier = f"ip:{ip or 'unknown'}"

    cache_key = f"location_view_cooldown:{location.id}:{identifier}"    
    
    is_new_view = cache.add(cache_key, 1, timeout=3600)

    if is_new_view:
        LocationView.objects.create(
            location=location,
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request)
        )
        return True

    return False