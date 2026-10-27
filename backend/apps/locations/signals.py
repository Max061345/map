from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .caching import invalidate_locations_cache
from .models import Location, Review


@receiver(post_save, sender=Location)
@receiver(post_delete, sender=Location)
def handle_location_change(sender, instance, **kwargs):
    """
    Invalidates the cached locations list whenever a location is
    created, updated, or deleted (including soft deletion).
    """
    invalidate_locations_cache()


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def handle_review_change(sender, instance, **kwargs):
    """
    Invalidates the cached locations list whenever a review is
    added or removed (updates rating and popularity calculations).
    """
    invalidate_locations_cache()