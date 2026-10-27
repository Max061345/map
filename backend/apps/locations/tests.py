from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Category, Location, Review, ReviewVote

User = get_user_model()


class LocationsAppAPITests(APITestCase):
    def setUp(self):
        # Flush Redis cache before each test run
        cache.clear()

        # Test users
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='AdminPassword123!'
        )
        self.author_user = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='AuthorPassword123!'
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='RegularPassword123!'
        )

        # Test category
        self.category = Category.objects.create(
            name="Parks & Nature",
            description="Outdoor natural places"
        )

        # Test location instance
        self.location = Location.objects.create(
            name="Central City Park",
            description="A green area in the downtown",
            category=self.category,
            address="Main St. 1",
            latitude=Decimal("50.450100"),
            longitude=Decimal("30.523400"),
            author=self.author_user
        )

    # CATEGORY TESTS

    def test_anonymous_user_can_list_categories(self):
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_regular_user_cannot_create_category(self):
        self.client.force_login(self.regular_user)
        response = self.client.post('/api/categories/', {'name': 'New Category'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_category(self):
        self.client.force_login(self.admin_user)
        response = self.client.post('/api/categories/', {'name': 'Museums'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Category.objects.filter(name='Museums').exists())

    # LOCATION AND SOFT DELETE TESTS

    def test_authenticated_user_can_create_location(self):
        self.client.force_login(self.regular_user)
        data = {
            'name': 'Botanical Garden',
            'description': 'Rare flowers and plants',
            'category': self.category.id,
            'address': 'Garden Blvd. 12',
            'latitude': '50.412345',
            'longitude': '30.567890'
        }
        response = self.client.post('/api/locations/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author'], self.regular_user.username)

    def test_non_author_cannot_update_location(self):
        self.client.force_login(self.regular_user)
        response = self.client.patch(
            f'/api/locations/{self.location.id}/',
            {'name': 'Hacked Park Name'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_soft_delete_location(self):
        self.client.force_login(self.author_user)
        response = self.client.delete(f'/api/locations/{self.location.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verification: Record is hidden from the default manager
        self.assertFalse(Location.objects.filter(id=self.location.id).exists())

        # Verification: Record is retained in the database via all_objects
        archived_location = Location.all_objects.get(id=self.location.id)
        self.assertTrue(archived_location.is_deleted)
        self.assertIsNotNone(archived_location.deleted_at)

    # REVIEWS AND VOTING TESTS

    def test_create_review_success(self):
        self.client.force_login(self.regular_user)
        review_data = {
            'location': self.location.id,
            'rating': 5,
            'comment': 'Awesome park with clean lanes.'
        }
        response = self.client.post('/api/reviews/', review_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.count(), 1)

    def test_user_cannot_leave_duplicate_review(self):
        Review.objects.create(
            location=self.location,
            author=self.regular_user,
            rating=4,
            comment='Good'
        )
        self.client.force_login(self.regular_user)
        review_data = {
            'location': self.location.id,
            'rating': 5,
            'comment': 'Trying to post second review'
        }
        response = self.client.post('/api/reviews/', review_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_review_vote_like_and_duplicate_prevention(self):
        review = Review.objects.create(
            location=self.location,
            author=self.author_user,
            rating=5,
            comment='Must visit!'
        )
        self.client.force_login(self.regular_user)

        # First vote
        vote_response = self.client.post(
            f'/api/reviews/{review.id}/vote/',
            {'vote_type': 'like'}
        )
        self.assertEqual(vote_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ReviewVote.objects.count(), 1)

        # Duplicate vote must be rejected
        duplicate_vote_response = self.client.post(
            f'/api/reviews/{review.id}/vote/',
            {'vote_type': 'dislike'}
        )
        self.assertEqual(duplicate_vote_response.status_code, status.HTTP_400_BAD_REQUEST)

    # PANDAS

    def test_export_locations_json(self):
        response = self.client.get('/api/locations/export/?format=json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('application/json', response.headers['Content-Type'])
        self.assertIn(self.location.name, response.content.decode('utf-8'))

    def test_export_locations_csv(self):
        response = self.client.get('/api/locations/export/?format=csv')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', response.headers['Content-Type'])
        self.assertIn(self.location.name, response.content.decode('utf-8'))