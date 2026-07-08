from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Profile


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='tester',
            email='tester@example.com',
            password='StrongPass123!',
        )

    def test_user_can_sign_up(self):
        response = self.client.post(
            reverse('account_signup'),
            {
                'username': 'newuser',
                'email': 'newuser@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(get_user_model().objects.filter(username='newuser').exists())

    def test_user_can_log_in_with_username_and_password(self):
        response = self.client.post(
            reverse('account_login'),
            {
                'login': 'tester',
                'password': 'StrongPass123!',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_signup_page_renders_without_social_apps(self):
        response = self.client.get(reverse('account_signup'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Account')

    def test_profile_page_allows_updating_phone_and_address(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('edit_profile'),
            {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'updated@example.com',
                'phone_number': '1234567890',
                'address': '123 Main Street',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Test')
        self.assertEqual(self.user.last_name, 'User')
        self.assertEqual(self.user.email, 'updated@example.com')

        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.phone_number, '1234567890')
        self.assertEqual(profile.address, '123 Main Street')
