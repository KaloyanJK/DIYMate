import json
import os
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from openai import OpenAI

from planner.ai_instructions import AI_SYSTEM_INSTRUCTIONS, AI_USER_RULES
from planner.models import AIPlan
from .forms import ProjectForm
from .models import Project

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def normalize_steps(steps):
    normalized = []
    for step in steps:
        if not isinstance(step, str):
            continue
        cleaned = re.sub(r'^\s*\d+(?:\.\d+)*\s*[-.):]?\s*', '', step).strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def save_ai_plan(project, data):
    AIPlan.objects.filter(project=project).delete()
    plan = AIPlan.objects.create(
        project=project,
        materials=data.get("materials", []),
        steps=normalize_steps(data.get("steps", [])),
        cost=data.get("cost", 0),
        safety=data.get("safety", "")
    )
    plan.updated_at = timezone.now()
    plan.save(update_fields=['updated_at'])
    return plan


@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()

            prompt = f"""
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
                "safety": "text"
            }}
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": AI_SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )

            output = response.choices[0].message.content

            try:
                data = json.loads(output)
                save_ai_plan(project, data)
            except Exception as e:
                print("AI parsing failed:", e)

            return redirect('project_detail', pk=project.id)
    else:
        form = ProjectForm()

    return render(request, 'projects/create_project.html', {'form': form})


@login_required
def project_list(request):
    projects = Project.objects.filter(user=request.user)
    return render(request, 'projects/project_list.html', {'projects': projects})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, id=pk, user=request.user)
    projects = list(Project.objects.filter(user=request.user).order_by('-created_at'))

    try:
        current_index = projects.index(project)
    except ValueError:
        current_index = -1

    previous_project = projects[current_index + 1] if current_index + 1 < len(projects) else None
    next_project = projects[current_index - 1] if current_index - 1 >= 0 else None

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'previous_project': previous_project,
        'next_project': next_project,
    })


@login_required
def edit_project(request, pk):
    project = get_object_or_404(Project, id=pk, user=request.user)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()

            prompt = f"""
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
                "safety": "text"
            }}
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": AI_SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )

            output = response.choices[0].message.content

            try:
                data = json.loads(output)
                save_ai_plan(project, data)
            except Exception as e:
                print("AI parsing failed:", e)

            return redirect('project_detail', pk=project.id)
    else:
        form = ProjectForm(instance=project)

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