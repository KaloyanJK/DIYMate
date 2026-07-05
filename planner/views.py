from django.shortcuts import render, get_object_or_404, redirect
from projects.models import Project
from .models import AIPlan
from django.contrib.auth.decorators import login_required

@login_required
def generate_plan(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)

    # Fake AI response (we simulate first)
    ai_result = {
        "materials": ["Wood planks", "Screws", "Concrete"],
        "steps": [
            "Measure area",
            "Prepare ground",
            "Install base",
            "Build frame",
            "Attach boards"
        ],
        "cost": 850.00,
        "safety": "Wear gloves and eye protection"
    }

    # SAVE TO DATABASE
    AIPlan.objects.create(
        project=project,
        materials=ai_result["materials"],
        steps=ai_result["steps"],
        cost=ai_result["cost"],
        safety=ai_result["safety"]
    )

    return redirect("project_detail", pk=project.id)