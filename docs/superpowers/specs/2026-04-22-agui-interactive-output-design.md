# AG-UI Interactive Output — Design Spec

**Date:** 2026-04-22  
**Status:** Approved  
**Scope:** Backend Agno API (Dartha-API-V3)

---

## Overview

Two features that extend the AG-UI stream to support richer output beyond plain text:

1. **HITL (Human-in-the-Loop)** — Agent pauses and emits a `StateSnapshotEvent` with structured form questions. Frontend renders real buttons/inputs. User answers are returned via `state` in the next run.
2. **Document blocks** — Agent wraps formal output in a ` ```document ` fence. Frontend detects the fence and renders an exportable document (DOCX/PDF). Zero backend code required — instructions only.

---

## Architecture

```
src/
├── tools/
│   └── interactive.py          # Tool: emit_interactive_state
├── skills/
│   └── shared/
│       └── interactive-output/
│           └── SKILL.md        # Instructions: when/how to use HITL and ```document
└── agui/
    ├── __init__.py
    └── stream_wrapper.py       # Wraps AGUI stream: intercepts tool call → StateSnapshotEvent
```

`app.py` registers the wrapper by replacing the `event_generator` in the AGUI router for all agents.

---

## Component 1 — Tool: `emit_interactive_state`

**File:** `src/tools/interactive.py`

A standard Agno/Python function tool. The agent calls it when it needs structured input. The return value is a dummy string — the real output is the `StateSnapshotEvent` emitted by the stream wrapper.

**Signature:**
```python
def emit_interactive_state(
    type: str,          # "form" | "single_step"
    steps: list,        # array of step objects (see contract below)
    answers: dict,      # accumulated answers from previous batches
    batch: int = 1,
    total_batches: int = 1
) -> str:
    return "INTERACTIVE_STATE_EMITTED"
```

Registered globally in `dynamic_loader.py` under the name `InteractiveTools` so any agent can enable it via `config/agents.yaml`.

---

## Component 2 — Stream Wrapper

**File:** `src/agui/stream_wrapper.py`

Wraps `async_stream_agno_response_as_agui_events` output without modifying the agno package. Detects `emit_interactive_state` tool calls in the event stream, buffers the args, and replaces the tool call events with a `StateSnapshotEvent`.

**Logic:**
```python
async def wrap_with_interactive(original_stream, encoder):
    buffer = {}
    async for event in original_stream:
        if is_tool_call_start(event, "emit_interactive_state"):
            buffer = {"collecting": True, "args": ""}
        elif buffer.get("collecting") and is_tool_call_chunk(event):
            buffer["args"] += event.delta
        elif buffer.get("collecting") and is_tool_call_end(event):
            args = json.loads(buffer["args"])
            yield encoder.encode(StateSnapshotEvent(snapshot={
                "interactive": True, **args
            }))
            buffer = {}
        else:
            yield event
```

The Agno `AGUI` class creates and registers routes internally, so `event_generator` cannot be replaced directly. Instead, `app.py` registers a **custom FastAPI router** for each agent that duplicates the `POST /agui/{slug}/agui` route with the wrapper injected:

```python
# app.py — after agent_os = AgentOS(...)
from src.agui.stream_wrapper import wrap_with_interactive
from agno.os.interfaces.agui.router import run_agent as agno_run_agent
from agno.os.interfaces.agui.utils import async_stream_agno_response_as_agui_events
from ag_ui.encoder import EventEncoder
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

for agent in agents:
    slug = agent.name.lower().replace(" ", "-")
    router = APIRouter()
    encoder = EventEncoder()
    _agent = agent  # capture for closure

    @router.post(f"/agui/{slug}/agui")
    async def interactive_run(run_input: RunAgentInput, _a=_agent):
        async def event_generator():
            raw = agno_run_agent(_a, run_input)
            async for chunk in wrap_with_interactive(raw, encoder):
                yield chunk
        return StreamingResponse(event_generator(), media_type="text/event-stream", ...)

    app.include_router(router)
```

Since FastAPI resolves routes in registration order, these routes are registered **after** the Agno AGUI routes, so they would be shadowed. To avoid this, the `AGUI` interfaces list is removed from `AgentOS` and the custom routes replace them entirely. The Agno `/agui/{slug}/status` endpoint is kept by registering it separately.

This avoids copying or patching any agno internals. Safe across agno version updates.

---

## Component 3 — Skill: `shared/interactive-output`

**File:** `src/skills/shared/interactive-output/SKILL.md`

Instructions added to agents via `config/agents.yaml` under `skills`. Covers two behaviors:

### HITL instructions
- Use `emit_interactive_state` when the user requests something that requires structured input: briefings, configurations, questionnaires, multi-step forms.
- Group questions in batches of 5. Never emit more than 5 steps per call.
- Read `run_input.state["answers"]` at the start of each run to check previously collected answers. If `answers` is populated, continue from where the form left off — do not repeat questions already answered.
- When all answers are collected, proceed to generate the final output without calling the tool again.
- For simple 1-2 question checks, use `type: "single_step"` instead of `"form"`.

### Document instructions
- Use a ` ```document ` fence for: reports, scripts, formal documents, contracts, presentations, any content the user may want to export.
- Trigger words: "gera um documento", "relatório", "roteiro", "exportar", "PDF", "DOCX", "apresentação".
- Write complete, publication-ready content inside the block — not a summary or outline.
- Plain conversation replies and short answers never use the document fence.

---

## Data Contract — `StateSnapshotEvent.snapshot`

### Shape 1 — Multi-question form (batches)

```json
{
  "interactive": true,
  "type": "form",
  "batch": 1,
  "total_batches": 4,
  "steps": [
    {
      "step": 1,
      "title": "Qual é a prioridade deste Reels?",
      "type": "single_choice",
      "options": ["Visualizações", "Comentários", "Compartilhamentos", "Salvamentos"]
    },
    {
      "step": 2,
      "title": "Sobre o que será o vídeo?",
      "type": "multiple_choice",
      "options": ["IA para líderes", "IA em vendas", "IA em marketing"],
      "max_selections": 2
    },
    {
      "step": 3,
      "title": "Contexto extra",
      "type": "text_input",
      "options": null,
      "placeholder": "Descreva em 1-2 frases..."
    }
  ],
  "answers": {
    "1": "Visualizações",
    "2": ["IA para líderes", "IA em marketing"]
  }
}
```

### Shape 2 — Single question

```json
{
  "interactive": true,
  "type": "single_step",
  "steps": [
    {
      "step": 1,
      "title": "Quer que eu gere a versão com ou sem grafos?",
      "type": "single_choice",
      "options": ["Com grafos", "Sem grafos", "Ambas"]
    }
  ],
  "answers": {}
}
```

### Field rules

| Field | Type | Required | Notes |
|---|---|---|---|
| `interactive` | boolean | yes | always `true` |
| `type` | string | yes | `"form"` or `"single_step"` |
| `batch` | int | if type=form | current batch number, 1-indexed |
| `total_batches` | int | if type=form | total number of batches |
| `steps` | array | yes | 1–5 items |
| `steps[].step` | int | yes | global step number, 1-indexed |
| `steps[].title` | string | yes | question text |
| `steps[].type` | string | yes | `"single_choice"` \| `"multiple_choice"` \| `"text_input"` |
| `steps[].options` | array\|null | yes | array of strings for choice types; `null` for text_input |
| `steps[].max_selections` | int | no | only for multiple_choice |
| `steps[].placeholder` | string | no | only for text_input |
| `answers` | object | yes | `{}` on first batch; accumulated `{ "step": value }` on subsequent |

### State returned by frontend (next run's `state` field)

```json
{
  "interactive": true,
  "answers": {
    "1": "Visualizações",
    "2": ["IA para líderes", "IA em marketing"],
    "3": "Foco em empresários do interior"
  }
}
```

---

## Document Block Contract

No backend changes. The agent emits markdown with a ` ```document ` fence:

````
```document
# Roteiro: Reels sobre IA para Líderes

## Hook (0–3s)
Você usa IA. Mas usa como ferramenta ou como sistema?

## Desenvolvimento (3–45s)
...

## CTA (45–60s)
Comenta SISTEMA aqui embaixo.
```
````

Frontend detects the `document` language identifier on the code fence and renders with export controls.

---

## Integration Points

### `config/agents.yaml`
Add `shared/interactive-output` to the `skills` list of any agent that should support HITL and document output. Add `InteractiveTools` to the `tools` list.

### `src/tools/dynamic_loader.py`
Register `InteractiveTools` in the tool name → class mapping.

### `src/app.py`
Replace the `event_generator` inside the AGUI router loop with the wrapped version from `src/agui/stream_wrapper.py`.

---

## Out of Scope

- Frontend rendering implementation (handled by the frontend team)
- Resume/pause of agent execution mid-stream (not supported by AG-UI protocol — each user response triggers a new run)
- Authentication or per-user state persistence (existing AgentOS session handling is sufficient)
