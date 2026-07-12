import json
import os
import re
from datetime import timedelta
from openai import OpenAI

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from accounts.services import consume_ai_generation_credit, get_or_create_subscription
from planner.ai_instructions import AI_SYSTEM_INSTRUCTIONS, AI_USER_RULES
from planner.openai_client import generate_image_data_url as openai_generate_image_data_url
from planner.models import AIPlan
from .forms import ProjectForm
from .models import Project

text_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def normalize_steps(steps):
    normalized = []
    for step in steps:
        if not isinstance(step, str):
            continue
        cleaned = re.sub(r'^\s*\d+(?:\.\d+)*\s*[-.):]?\s*', '', step).strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def build_plan_prompt(project):
    return f"""
    {AI_SYSTEM_INSTRUCTIONS}

    {AI_USER_RULES}

    Project:
    Title: {project.title}
    Description: {project.description}
    Dimensions: {project.dimensions}
    Budget: {project.budget}

    Return ONLY structured JSON in this format:

    {{
        "materials": ["item1", "item2"],
        "steps": ["step1", "step2", "step3"],
        "cost": number,
        "safety": "text",
        "generated_images": [
            {{
                "title": "Modern compact workstation",
                "search_terms": "small workspace layout with integrated storage",
                "notes": "Use straight lines and compact shelving placements for efficient footprint."
            }}
        ]
    }}
    """


def build_drawing_prompt(project):
    return f"""
Create a technical blueprint-style DIY drawing for this project.

Project data:
- Title: {project.title}
- Description: {project.description}
- Dimensions: {project.dimensions}
- Budget: {project.budget}

Mandatory visual output requirements:
- Technical drawing style only (not painterly, not concept art, not abstract art).
- Clean linework and readable structure.
- Include labels for key components.
- Include visible measurements with units and dimension arrows.
- Keep layout simple, realistic, and buildable.
- Respect the provided project dimensions.
""".strip()


def parse_ai_json_output(output):
    output = (output or "").strip()
    if output.startswith("```"):
        output = output.strip("`")
        output = output.replace("json", "", 1).strip()
    return json.loads(output)


def generate_plan_text(prompt):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    response = text_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": AI_SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


def generate_drawing_preview(project):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None, None

    drawing_prompt = build_drawing_prompt(project)
    image_data_url = openai_generate_image_data_url(api_key=api_key, prompt=drawing_prompt)
    return image_data_url, drawing_prompt


def save_ai_plan(project, data, temporary_drawing_data=None, drawing_prompt=None):
    AIPlan.objects.filter(project=project).delete()
    plan = AIPlan.objects.create(
        project=project,
        materials=data.get("materials", []),
        steps=normalize_steps(data.get("steps", [])),
        cost=data.get("cost", 0),
        safety=data.get("safety", ""),
        generated_images=data.get("generated_images", []),
        temporary_drawing_data=temporary_drawing_data,
        temporary_drawing_prompt=drawing_prompt,
    )
    plan.updated_at = timezone.now()
    plan.save(update_fields=['updated_at'])
    return plan


@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, user=request.user)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            messages.success(request, 'Project created successfully. Generate an AI plan when you are ready.')
            return redirect('project_detail', pk=project.id)
    else:
        form = ProjectForm(user=request.user)

    return render(request, 'projects/create_project.html', {'form': form})


@login_required
def project_list(request):
    projects = Project.objects.filter(user=request.user)
    return render(request, 'projects/project_list.html', {'projects': projects})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, id=pk, user=request.user)
    subscription = get_or_create_subscription(request.user)
    projects = list(Project.objects.filter(user=request.user).order_by('-created_at'))
    latest_plan = project.plans.order_by('-created_at').first()

    # Temporary previews are short-lived by design and are discarded automatically.
    if latest_plan and latest_plan.temporary_drawing_data:
        expires_at = latest_plan.updated_at + timedelta(hours=2)
        if timezone.now() >= expires_at:
            latest_plan.temporary_drawing_data = None
            latest_plan.temporary_drawing_prompt = None
            latest_plan.save(update_fields=['temporary_drawing_data', 'temporary_drawing_prompt'])

    try:
        current_index = projects.index(project)
    except ValueError:
        current_index = -1

    previous_project = projects[current_index + 1] if current_index + 1 < len(projects) else None
    next_project = projects[current_index - 1] if current_index - 1 >= 0 else None

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'latest_plan': latest_plan,
        'previous_project': previous_project,
        'next_project': next_project,
        'subscription': subscription,
    })


@login_required
def edit_project(request, pk):
    project = get_object_or_404(Project, id=pk, user=request.user)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project, user=request.user)
        if form.is_valid():
            project = form.save()
            messages.success(request, 'Project updated successfully. Regenerate the AI plan manually if you want a refreshed version.')
            return redirect('project_detail', pk=project.id)
    else:
        form = ProjectForm(instance=project, user=request.user)

    return render(request, 'projects/edit_project.html', {
        'form': form,
        'project': project
    })


@login_required
def delete_project(request, pk):
    project = get_object_or_404(Project, id=pk, user=request.user)

    if request.method == 'POST':
        project.delete()
        return redirect('project_list')

    return render(request, 'projects/delete_project.html', {'project': project})