from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from planner.models import AIPlan
from .models import Project


class ProjectDetailTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='tester',
            email='tester@example.com',
            password='StrongPass123!',
        )
        self.project = Project.objects.create(
            user=self.user,
            title='Garden Shed',
            description='A small shed',
            dimensions='4x6',
            budget='500',
        )

    def test_project_detail_shows_ai_plan_when_available(self):
        AIPlan.objects.create(
            project=self.project,
            materials=['Wood boards', 'Screws'],
            steps=['Measure the area', 'Install the frame'],
            cost='120.50',
            safety='Wear gloves',
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('project_detail', kwargs={'pk': self.project.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI Generated Plans')
        self.assertContains(response, 'Wood boards')
        self.assertContains(response, 'Measure the area')


class ProjectListTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='tester',
            email='tester@example.com',
            password='StrongPass123!',
        )
        self.project = Project.objects.create(
            user=self.user,
            title='Garden Shed',
            description='A small shed',
            dimensions='4x6',
            budget='500',
        )

    def test_project_list_shows_latest_ai_plan_preview(self):
        AIPlan.objects.create(
            project=self.project,
            materials=['Wood boards', 'Screws'],
            steps=['Measure the area', 'Install the frame'],
            cost='120.50',
            safety='Wear gloves',
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('project_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Latest AI Plan')
        self.assertContains(response, 'Wood boards')
