from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class AuthenticationAPITests(APITestCase):
    def setUp(self):
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.logout_url = '/api/auth/logout/'
        self.reset_request_url = '/api/auth/password-reset/'
        self.reset_confirm_url = '/api/auth/password-reset-confirm/'

        self.user_data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!',
        }
        self.user = User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='Password123!'
        )

    # Registration
    def test_user_registration_success(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='testuser').exists())

    # Login & Session Creation
    def test_user_login_session_creation(self):
        login_data = {
            'username': 'existinguser',
            'password': 'Password123!'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('_auth_user_id', self.client.session)

    # Logout
    def test_user_logout(self):
        self.client.force_login(self.user)
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('_auth_user_id', self.client.session)

    # Password Reset Request
    def test_password_reset_request_success(self):
        response = self.client.post(
            self.reset_request_url,
            {'email': 'existing@example.com'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Password Reset Confirm (with uidb64 and token)
    def test_password_reset_confirm_success(self):
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        payload = {
            'uidb64': uidb64,
            'token': token,
            'new_password': 'NewStrongPassword123!',
            'new_password_confirm': 'NewStrongPassword123!'
        }
        response = self.client.post(self.reset_confirm_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify password update in database
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrongPassword123!'))