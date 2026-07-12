import json
import os
import re

from openai import OpenAI
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from accounts.models import Subscription
from accounts.services import consume_ai_generation_credit, get_or_create_subscription
from projects.models import Project

from .ai_instructions import AI_SYSTEM_INSTRUCTIONS
from .models import AIPlan
from .openai_client import generate_image_data_url as openai_generate_image_data_url

text_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def normalize_steps(steps):
    normalized = []
    for step in steps:
        if not isinstance(step, str):
            continue
        cleaned = re.sub(r"^\s*\d+(?:\.\d+)*\s*[-.):]?\s*", "", step).strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def build_project_context(project):
    return (
        f"title: {project.title}\n"
        f"description: {project.description}\n"
        f"dimensions: {project.dimensions}\n"
        f"budget_gbp: {project.budget}"
    )


def build_plan_prompt(project):
    return f"""
Generate a focused DIY plan as strict JSON.

PROJECT
{build_project_context(project)}

OUTPUT JSON
{{
  "materials": ["..."],
  "steps": ["..."],
  "cost": 0,
  "safety": "..."
}}

CONSTRAINTS
- 6 or fewer steps, only required actions.
- Keep each step short, practical, and build-focused.
- Keep material list realistic for budget.
- Keep safety concise.
- No extra keys.
""".strip()


def build_inspiration_prompt(project):
    return f"""
Generate style inspiration ideas as strict JSON.

PROJECT
{build_project_context(project)}

OUTPUT JSON
{{
  "generated_images": [
    {{
      "title": "...",
      "search_terms": "...",
      "notes": "..."
    }}
  ]
}}

CONSTRAINTS
- Return exactly 3 ideas.
- Pinterest-style text-only ideas (no links).
- Keep notes concise and actionable.
- No extra keys.
""".strip()


def build_drawing_prompt(project):
    return f"""
Create a clean technical blueprint drawing for this DIY project.

PROJECT
{build_project_context(project)}

CONSTRAINTS
- Technical line drawing only.
- Include labels and dimensions with units.
- Keep layout buildable and readable.
- Respect provided dimensions.
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
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": AI_SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def generate_drawing_preview(project):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None, None

    drawing_prompt = build_drawing_prompt(project)
    image_data_url = openai_generate_image_data_url(
        api_key=api_key,
        prompt=drawing_prompt,
        size="512x512",
    )
    return image_data_url, drawing_prompt


def project_has_any_drawing(plan):
    return bool(plan and (plan.temporary_drawing_data or plan.saved_drawing_data))


def can_generate_project_drawing(user, plan):
    subscription = get_or_create_subscription(user)

    if subscription.plan != Subscription.PLAN_PREMIUM:
        return False, "Image generation is available only on Premium."

    if project_has_any_drawing(plan):
        return False, "Premium includes 1 image per project. This project already has an image."

    return True, ""


@login_required
def generate_plan(request, project_id):
    if request.method != "POST":
        return redirect("project_detail", pk=project_id)

    project = get_object_or_404(Project, id=project_id, user=request.user)
    existing_plan = AIPlan.objects.filter(project=project).order_by("-created_at").first()

    if existing_plan:
        messages.info(request, "Using cached AI plan for this project.")
        return redirect("project_detail", pk=project.id)

    allowed, _, usage_message = consume_ai_generation_credit(request.user)
    if not allowed:
        messages.error(request, usage_message)
        return redirect("project_detail", pk=project.id)

    prompt = build_plan_prompt(project)
    output = generate_plan_text(prompt)

    try:
        data = parse_ai_json_output(output)
    except Exception as exc:
        print("AI parsing failed:", exc)
        messages.error(request, "AI plan generation failed. Please try again.")
        return redirect("project_detail", pk=project.id)

    steps = normalize_steps(data.get("steps", []))[:6]

    AIPlan.objects.create(
        project=project,
        materials=data.get("materials", []),
        steps=steps,
        cost=data.get("cost", 0),
        safety=data.get("safety", ""),
        generated_images=[],
        temporary_drawing_data=None,
        temporary_drawing_prompt=None,
    )

    messages.success(request, "AI plan generated. Generate drawing and inspiration only if needed.")
    return redirect("project_detail", pk=project.id)


@login_required
def generate_plan_inspirations(request, project_id):
    if request.method != "POST":
        return redirect("project_detail", pk=project_id)

    project = get_object_or_404(Project, id=project_id, user=request.user)
    plan = AIPlan.objects.filter(project=project).order_by("-created_at").first()

    if not plan:
        messages.warning(request, "Generate an AI plan first before requesting inspirations.")
        return redirect("project_detail", pk=project.id)

    if plan.generated_images:
        messages.info(request, "Using cached inspiration ideas for this project.")
        return redirect("project_detail", pk=project.id)

    allowed, _, usage_message = consume_ai_generation_credit(request.user)
    if not allowed:
        messages.error(request, usage_message)
        return redirect("project_detail", pk=project.id)

    prompt = build_inspiration_prompt(project)
    output = generate_plan_text(prompt)

    try:
        data = parse_ai_json_output(output)
        ideas = data.get("generated_images", [])[:3]
    except Exception as exc:
        print("Inspiration parsing failed:", exc)
        messages.error(request, "Could not generate inspiration ideas. Please try again.")
        return redirect("project_detail", pk=project.id)

    plan.generated_images = ideas
    plan.updated_at = timezone.now()
    plan.save(update_fields=["generated_images", "updated_at"])

    messages.success(request, "Inspiration ideas generated.")
    return redirect("project_detail", pk=project.id)


@login_required
def regenerate_plan_drawing(request, project_id):
    if request.method != "POST":
        return redirect("project_detail", pk=project_id)

    project = get_object_or_404(Project, id=project_id, user=request.user)
    plan = AIPlan.objects.filter(project=project).order_by("-created_at").first()
    if not plan:
        messages.warning(request, "Generate an AI plan first before creating a drawing.")
        return redirect("project_detail", pk=project.id)

    can_generate, limit_message = can_generate_project_drawing(request.user, plan)
    if not can_generate:
        messages.warning(request, limit_message)
        return redirect("project_detail", pk=project.id)

    try:
        temporary_drawing_data, drawing_prompt = generate_drawing_preview(project)
        if not temporary_drawing_data:
            messages.warning(request, "OpenAI did not return a drawing preview for this request. Please try again shortly.")
            return redirect("project_detail", pk=project.id)

        plan.temporary_drawing_data = temporary_drawing_data
        plan.temporary_drawing_prompt = drawing_prompt
        plan.updated_at = timezone.now()
        plan.save(update_fields=["temporary_drawing_data", "temporary_drawing_prompt", "updated_at"])
        messages.success(request, "Technical drawing generated.")
    except Exception as exc:
        print("AI image generation failed:", exc)
        messages.error(request, f"Could not generate drawing with OpenAI: {exc}")

    return redirect("project_detail", pk=project.id)


@login_required
def save_plan_drawing(request, project_id):
    if request.method != "POST":
        return redirect("project_detail", pk=project_id)

    project = get_object_or_404(Project, id=project_id, user=request.user)
    plan = AIPlan.objects.filter(project=project).order_by("-created_at").first()
    if not plan:
        messages.warning(request, "No AI plan was found for this project.")
        return redirect("project_detail", pk=project.id)

    if not plan.temporary_drawing_data:
        messages.warning(request, "There is no temporary drawing to save yet.")
        return redirect("project_detail", pk=project.id)

    plan.saved_drawing_data = plan.temporary_drawing_data
    plan.drawing_saved_at = timezone.now()
    plan.temporary_drawing_data = None
    plan.temporary_drawing_prompt = None
    plan.save(update_fields=["saved_drawing_data", "drawing_saved_at", "temporary_drawing_data", "temporary_drawing_prompt"])
    messages.success(request, "Drawing saved permanently to this AI plan.")
    return redirect("project_detail", pk=project.id)
