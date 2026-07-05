from django.db import models
from projects.models import Project

class AIPlan(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    materials = models.JSONField()
    steps = models.JSONField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    safety = models.TextField()

    generated_images = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Plan for {self.project.title}"