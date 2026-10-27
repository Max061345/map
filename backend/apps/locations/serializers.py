from rest_framework import serializers
from .models import Location, Review, ReviewVote, Category, Location
from decimal import Decimal



class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'created_at')
        read_only_fields = ('id', 'slug', 'created_at')

    def validate_name(self, value):
        stripped_value = value.strip()
        if not stripped_value:
            raise serializers.ValidationError("Category name cannot be empty or contain only whitespace.")

        query = Category.objects.filter(name__iexact=stripped_value)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError("A category with this name already exists.")

        return stripped_value
    

class LocationSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')
    author_id = serializers.ReadOnlyField(source='author.id')
    category_name = serializers.ReadOnlyField(source='category.name')

    class Meta:
        model = Location
        fields = (
            'id',
            'name',
            'description',
            'category',
            'category_name',
            'address',
            'latitude',
            'longitude',
            'author',
            'author_id',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'author', 'author_id', 'category_name', 'created_at', 'updated_at')

    def validate_latitude(self, value):
        if value < Decimal('-90.0') or value > Decimal('90.0'):
            raise serializers.ValidationError("Latitude must be between -90.0 and 90.0 degrees.")
        return value

    def validate_longitude(self, value):
        if value < Decimal('-180.0') or value > Decimal('180.0'):
            raise serializers.ValidationError("Longitude must be between -180.0 and 180.0 degrees.")
        return value

    def validate_name(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Location name cannot be empty.")
        return stripped


class ReviewSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')
    author_id = serializers.ReadOnlyField(source='author.id')
    likes_count = serializers.SerializerMethodField()
    dislikes_count = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            'id',
            'location',
            'author',
            'author_id',
            'rating',
            'comment',
            'likes_count',
            'dislikes_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'author', 'author_id', 'created_at', 'updated_at')

    def get_likes_count(self, obj):
        return obj.votes.filter(vote_type=ReviewVote.VoteType.LIKE).count()

    def get_dislikes_count(self, obj):
        return obj.votes.filter(vote_type=ReviewVote.VoteType.DISLIKE).count()

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be an integer between 1 and 5.")
        return value

    def validate_comment(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Comment cannot be empty.")
        return stripped

    def validate(self, attrs):
        request = self.context.get('request')
        location = attrs.get('location')
        
        if self.instance is None and request and request.user.is_authenticated:            
            if location.is_deleted:
                raise serializers.ValidationError({"location": "You cannot review a deleted location."})
            
            if Review.objects.filter(location=location, author=request.user).exists():
                raise serializers.ValidationError(
                    {"detail": "You have already submitted a review for this location."}
                )

        return attrs


class ReviewVoteSerializer(serializers.Serializer):
    vote_type = serializers.ChoiceField(
        choices=ReviewVote.VoteType.choices,
        error_messages={'invalid_choice': "Vote type must be either 'like' or 'dislike'."}
    )

    def validate(self, attrs):
        request = self.context.get('request')
        review = self.context.get('review')

        if ReviewVote.objects.filter(review=review, user=request.user).exists():
            raise serializers.ValidationError(
                {"detail": "You have already voted on this review."}
            )

        return attrs