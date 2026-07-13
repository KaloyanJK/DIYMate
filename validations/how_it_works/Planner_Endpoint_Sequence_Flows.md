# Planner Endpoint Sequence Flows

## Overview

These sequence flows describe how each Planner endpoint processes requests from the user interface through validation, business rules, AI generation, persistence, and final rendering.

---

# 1. Generate Plan

### Route

```text
POST /planner/generate/{project_id}/
```

### Execution Path

```text
urls.py
    ↓
views.py
    ↓
accounts services
    ↓
OpenAI
    ↓
AIPlan model
    ↓
views.py redirect
```

### Sequence Diagram

```mermaid
sequenceDiagram

    participant U as User
    participant P as Project Detail Page
    participant V as generate_plan
    participant A as Accounts Service
    participant O as OpenAI
    participant M as AIPlan

    U->>P: Click Generate Plan

    P->>V: POST /planner/generate/{project_id}/

    V->>V: Validate method
    V->>V: Validate ownership

    V->>A: consume_ai_generation_credit()

    A-->>V: Credit allowed

    V->>V: Build project prompt

    V->>O: Chat completion request

    O-->>V: JSON response

    V->>V: Parse output
    V->>V: Normalize steps

    V->>M: AIPlan.objects.create()

    M-->>V: Plan saved

    V-->>P: Redirect project detail

    P-->>U: Render plan content
```

### Flow Summary

1. Validate request method.
2. Validate project ownership.
3. Consume AI generation credit.
4. Build plan prompt from project data.
5. Request plan from OpenAI.
6. Parse and normalize output.
7. Create AIPlan record.
8. Redirect back to project detail.

---

# 2. Generate Inspirations

### Route

```text
POST /planner/generate/{project_id}/inspirations/
```

### Execution Path

```text
urls.py
    ↓
views.py
    ↓
accounts services
    ↓
OpenAI
    ↓
AIPlan model
```

### Sequence Diagram

```mermaid
sequenceDiagram

    participant U as User
    participant P as Project Detail Page
    participant V as generate_plan_inspirations
    participant A as Accounts Service
    participant O as OpenAI
    participant M as AIPlan

    U->>P: Click Generate Inspirations

    P->>V: POST inspirations

    V->>V: Validate method
    V->>V: Validate ownership
    V->>V: Validate existing AIPlan

    alt Inspirations already exist
        V-->>P: Use cached inspirations
    else Generate new inspirations
        V->>A: consume_ai_generation_credit()

        A-->>V: Allowed

        V->>V: Build inspiration prompt

        V->>O: Chat completion

        O-->>V: JSON ideas

        V->>V: Keep first 3 ideas

        V->>M: Update generated_images

        M-->>V: Saved

        V-->>P: Redirect project detail
    end
```

### Flow Summary

1. Validate request.
2. Confirm project ownership.
3. Require existing AIPlan.
4. Use cached inspiration data if available.
5. Consume AI credit.
6. Generate inspiration ideas.
7. Save first three ideas.
8. Redirect to project detail.

---

# 3. Regenerate Drawing

### Route

```text
POST /planner/generate/{project_id}/drawing/regenerate/
```

### Execution Path

```text
urls.py
    ↓
views.py
    ↓
accounts services
    ↓
openai_client.py
    ↓
AIPlan model
```

### Sequence Diagram

```mermaid
sequenceDiagram

    participant U as User
    participant P as Project Detail Page
    participant V as regenerate_plan_drawing
    participant A as Accounts Service
    participant I as openai_client.py
    participant M as AIPlan

    U->>P: Click Generate Drawing

    P->>V: POST drawing/regenerate

    V->>V: Validate method
    V->>V: Validate ownership
    V->>V: Validate AIPlan exists

    V->>A: get_or_create_subscription()

    A-->>V: Subscription

    V->>V: Premium check

    V->>V: can_generate_project_drawing()

    V->>V: Enforce one image rule

    V->>I: generate_image_data_url()

    I-->>V: Generated image

    V->>M: Save temporary_drawing_data
    V->>M: Save drawing prompt

    M-->>V: Updated

    V-->>P: Redirect project detail
```

### Flow Summary

1. Validate request and ownership.
2. Require existing AIPlan.
3. Check premium subscription.
4. Enforce one-image-per-project limit.
5. Generate image through OpenAI client.
6. Save temporary drawing data.
7. Redirect back to project detail.

---

# 4. Save Drawing

### Route

```text
POST /planner/generate/{project_id}/drawing/save/
```

### Execution Path

```text
urls.py
    ↓
views.py
    ↓
AIPlan model
```

### Sequence Diagram

```mermaid
sequenceDiagram

    participant U as User
    participant P as Project Detail Page
    participant V as save_plan_drawing
    participant M as AIPlan

    U->>P: Click Save Drawing

    P->>V: POST drawing/save

    V->>V: Validate method
    V->>V: Validate ownership
    V->>V: Validate AIPlan exists
    V->>V: Validate temporary drawing exists

    V->>M: Move temporary_drawing_data
    V->>M: Save as saved_drawing_data

    V->>M: Set drawing_saved_at

    V->>M: Clear temporary fields

    M-->>V: Persist changes

    V-->>P: Redirect project detail
```

### Flow Summary

1. Validate request.
2. Validate ownership.
3. Require existing AIPlan.
4. Require temporary drawing.
5. Move temporary drawing to permanent storage.
6. Set save timestamp.
7. Clear temporary fields.
8. Redirect to project detail.

---

# Unified Planner Flow

```mermaid
flowchart TD

    USER[User]

    USER --> DETAIL[Project Detail Template]

    DETAIL --> PLAN[Generate Plan]
    DETAIL --> INSP[Generate Inspirations]
    DETAIL --> DRAW[Generate Drawing]
    DETAIL --> SAVE[Save Drawing]

    PLAN --> PLANNER[Planner Views]
    INSP --> PLANNER
    DRAW --> PLANNER
    SAVE --> PLANNER

    PLANNER --> ACCOUNTS[Subscription & Credit Checks]

    PLANNER --> OPENAI[OpenAI APIs]

    OPENAI --> AIPLAN[AIPlan]

    AIPLAN --> DETAIL

    DETAIL --> USER
```

---

# One-Line Architecture Chain

```text
Projects UI (project_detail.html)
        ↓
Planner Endpoints
        ↓
Ownership Validation
        ↓
Accounts Subscription & Credit Enforcement
        ↓
OpenAI Generation
        ↓
AIPlan Persistence
        ↓
Redirect to Project Detail
        ↓
Updated AI Results Rendered
```