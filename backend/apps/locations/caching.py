import hashlib
from django.core.cache import cache

LOCATIONS_LIST_CACHE_PREFIX = "locations_list"
LOCATIONS_CACHE_TIMEOUT = 60 * 15


def generate_locations_cache_key(query_params: dict) -> str:
    """
    Generates a deterministic cache key based on sorted request query parameters.
    """
    sorted_params = sorted(query_params.items())
    query_string = "&".join(f"{k}={v}" for k, v in sorted_params)
    query_hash = hashlib.md5(query_string.encode('utf-8')).hexdigest()
    return f"{LOCATIONS_LIST_CACHE_PREFIX}:{query_hash}"


def invalidate_locations_cache() -> None:
    """
    Clears all cached variations of locations list matching the pattern.
    """
    cache.delete_pattern(f"{LOCATIONS_LIST_CACHE_PREFIX}:*")