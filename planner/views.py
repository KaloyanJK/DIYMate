import os
from openai import OpenAI
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from projects.models import Project
from .ai_instructions import AI_SYSTEM_INSTRUCTIONS, AI_USER_RULES
from .models import AIPlan

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


@login_required
def generate_plan(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)

    # PROMPT (VERY IMPORTANT)
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

    # CALL OPENAI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": AI_SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3   # reduces hallucination
    )

    # GET RESPONSE TEXT
    output = response.choices[0].message.content

    import json

    try:
        data = json.loads(output)

        # Keep only one AI plan per project by replacing any previous plan.
        AIPlan.objects.filter(project=project).delete()

        AIPlan.objects.create(
            project=project,
            materials=data["materials"],
            steps=data["steps"],
            cost=data.get("cost", 0),
            safety=data.get("safety", "")
        )

    except Exception as e:
        print("AI parsing failed:", e)

    return redirect("project_detail", pk=project.id)
