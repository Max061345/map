from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Category Name")
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, default="", verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def all_with_deleted(self):
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted_only(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=True)


class Location(models.Model):
    name = models.CharField(max_length=255, verbose_name="Name")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    category = models.ForeignKey(
        'Category',
        on_delete=models.PROTECT,
        related_name='locations',
        verbose_name='Category'
    )

    address = models.CharField(max_length=255, verbose_name="Address")


    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name="Latitude"
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name="Longitude"
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='locations',
        verbose_name="Author"
    )

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'locations'
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        ordering = ['-created_at']

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def __str__(self):
        return self.name


class Review(models.Model):
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Location"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Author"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1, message="Rating cannot be less than 1."),
            MaxValueValidator(5, message="Rating cannot be greater than 5.")
        ],
        verbose_name="Rating"
    )
    comment = models.TextField(verbose_name="Comment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reviews'
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_at']        
        constraints = [
            models.UniqueConstraint(
                fields=['location', 'author'],
                name='unique_location_author_review'
            )
        ]

    def __str__(self):
        return f"Review by {self.author} for {self.location} ({self.rating}/5)"


class ReviewVote(models.Model):
    class VoteType(models.TextChoices):
        LIKE = 'like', 'Like'
        DISLIKE = 'dislike', 'Dislike'

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='votes',
        verbose_name="Review"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_votes',
        verbose_name="User"
    )
    vote_type = models.CharField(
        max_length=7,
        choices=VoteType.choices,
        verbose_name="Vote Type"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'review_votes'
        verbose_name = 'Review Vote'
        verbose_name_plural = 'Review Votes'        
        constraints = [
            models.UniqueConstraint(
                fields=['review', 'user'],
                name='unique_review_user_vote'
            )
        ]

    def __str__(self):
        return f"{self.user} voted {self.vote_type} on review #{self.review_id}"