from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


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
