from django.db import models
from projects.models import Project


class AIPlan(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='plans'
    )

    materials = models.JSONField()
    steps = models.JSONField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    safety = models.TextField()

    generated_images = models.JSONField(blank=True, null=True)
    temporary_drawing_data = models.TextField(blank=True, null=True)
    temporary_drawing_prompt = models.TextField(blank=True, null=True)
    saved_drawing_data = models.TextField(blank=True, null=True)
    drawing_saved_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Plan for {self.project.title}"