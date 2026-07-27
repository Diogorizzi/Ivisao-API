# AG-UI Interactive Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add HITL (Human-in-the-Loop) via `StateSnapshotEvent` and exportable `document` blocks to all Agno agents, without modifying the agno package internals.

**Architecture:** A Python tool `emit_interactive_state` is registered on each agent. A stream wrapper in `src/agui/stream_wrapper.py` intercepts that tool call in the AG-UI event stream and replaces it with a `StateSnapshotEvent`. The Agno `AGUI` interfaces are removed from `AgentOS` and replaced by custom FastAPI routes (one per agent) that inject the wrapper. A shared skill `shared/interactive-output` teaches all agents when and how to use HITL and `document` blocks.

**Tech Stack:** Python 3.11, FastAPI, Agno SDK, ag-ui-protocol (`ag_ui`), pytest

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `src/tools/interactive.py` | `emit_interactive_state` tool function |
| Create | `src/agui/__init__.py` | Package marker |
| Create | `src/agui/stream_wrapper.py` | Intercept tool call → `StateSnapshotEvent` |
| Create | `src/agui/router.py` | Custom FastAPI router factory for all agents |
| Create | `src/skills/shared/interactive-output/SKILL.md` | Agent instructions for HITL + document blocks |
| Modify | `src/tools/dynamic_loader.py` | Register `InteractiveTools` |
| Modify | `config/agents.yaml` | Add skill + tool to all agents |
| Modify | `src/app.py` | Replace AGUI interfaces with custom router |
| Create | `tests/test_stream_wrapper.py` | Unit tests for the stream wrapper |
| Create | `tests/test_interactive_tool.py` | Unit tests for the tool function |

---

## Task 1: Tool `emit_interactive_state`

**Files:**
- Create: `src/tools/interactive.py`
- Create: `tests/test_interactive_tool.py`

- [ ] **Step 1.1 — Write the failing test**

```python
# tests/test_interactive_tool.py
import pytest
from src.tools.interactive import emit_interactive_state


def test_returns_sentinel_string():
    result = emit_interactive_state(
        type="single_step",
        steps=[{"step": 1, "title": "Qual é o tema?", "type": "single_choice", "options": ["IA", "Dados"]}],
        answers={},
    )
    assert result == "INTERACTIVE_STATE_EMITTED"


def test_accepts_form_type_with_batch():
    result = emit_interactive_state(
        type="form",
        steps=[
            {"step": 1, "title": "Q1", "type": "single_choice", "options": ["A", "B"]},
            {"step": 2, "title": "Q2", "type": "multiple_choice", "options": ["X", "Y"], "max_selections": 2},
            {"step": 3, "title": "Q3", "type": "text_input", "options": None, "placeholder": "Descreva..."},
        ],
        answers={"1": "A"},
        batch=2,
        total_batches=4,
    )
    assert result == "INTERACTIVE_STATE_EMITTED"


def test_accepts_empty_answers():
    result = emit_interactive_state(
        type="single_step",
        steps=[{"step": 1, "title": "Ok?", "type": "single_choice", "options": ["Sim", "Não"]}],
        answers={},
    )
    assert result == "INTERACTIVE_STATE_EMITTED"
```

- [ ] **Step 1.2 — Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/test_interactive_tool.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `src/tools/interactive.py` does not exist yet.

- [ ] **Step 1.3 — Create the tool**

```python
# src/tools/interactive.py
from typing import Any


def emit_interactive_state(
    type: str,
    steps: list,
    answers: dict,
    batch: int = 1,
    total_batches: int = 1,
) -> str:
    """
    Signals the AG-UI stream wrapper to emit a StateSnapshotEvent.

    The return value is intentionally ignored by the agent. The real output
    is the StateSnapshotEvent emitted by src/agui/stream_wrapper.py when it
    detects this tool call in the event stream.

    Args:
        type: "form" for multi-batch questionnaires, "single_step" for 1-2 quick questions.
        steps: List of step dicts. Each dict must have:
            - step (int): global 1-indexed step number
            - title (str): question text shown to the user
            - type (str): "single_choice" | "multiple_choice" | "text_input"
            - options (list[str] | None): choices for choice types; None for text_input
            - max_selections (int, optional): max choices for multiple_choice
            - placeholder (str, optional): hint text for text_input
        answers: Accumulated answers from previous batches, keyed by step number as string.
        batch: Current batch number (1-indexed). Only relevant when type="form".
        total_batches: Total number of batches. Only relevant when type="form".

    Returns:
        Sentinel string "INTERACTIVE_STATE_EMITTED".
    """
    return "INTERACTIVE_STATE_EMITTED"
```

- [ ] **Step 1.4 — Run test to verify it passes**

```bash
.venv/Scripts/python.exe -m pytest tests/test_interactive_tool.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 1.5 — Commit**

```bash
git add src/tools/interactive.py tests/test_interactive_tool.py
git commit -m "feat: add emit_interactive_state tool (AG-UI HITL)"
```

---

## Task 2: Stream Wrapper

**Files:**
- Create: `src/agui/__init__.py`
- Create: `src/agui/stream_wrapper.py`
- Create: `tests/test_stream_wrapper.py`

- [ ] **Step 2.1 — Write the failing tests**

```python
# tests/test_stream_wrapper.py
import json
import pytest
from unittest.mock import MagicMock
from ag_ui.core import EventType, StateSnapshotEvent, ToolCallStartEvent, ToolCallArgsEvent, ToolCallEndEvent, TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent
from ag_ui.encoder import EventEncoder
from src.agui.stream_wrapper import wrap_with_interactive


def _tool_start(tool_call_id: str, name: str) -> ToolCallStartEvent:
    return ToolCallStartEvent(
        type=EventType.TOOL_CALL_START,
        tool_call_id=tool_call_id,
        tool_call_name=name,
        parent_message_id="msg-1",
    )


def _tool_args(tool_call_id: str, delta: str) -> ToolCallArgsEvent:
    return ToolCallArgsEvent(
        type=EventType.TOOL_CALL_ARGS,
        tool_call_id=tool_call_id,
        delta=delta,
    )


def _tool_end(tool_call_id: str) -> ToolCallEndEvent:
    return ToolCallEndEvent(
        type=EventType.TOOL_CALL_END,
        tool_call_id=tool_call_id,
    )


async def _stream(*events):
    for e in events:
        yield e


@pytest.mark.asyncio
async def test_passthrough_non_interactive_events():
    """Non-interactive events pass through unchanged."""
    encoder = EventEncoder()
    text_start = TextMessageStartEvent(
        type=EventType.TEXT_MESSAGE_START,
        message_id="msg-1",
        role="assistant",
    )
    text_content = TextMessageContentEvent(
        type=EventType.TEXT_MESSAGE_CONTENT,
        message_id="msg-1",
        delta="Hello",
    )
    text_end = TextMessageEndEvent(
        type=EventType.TEXT_MESSAGE_END,
        message_id="msg-1",
    )

    results = []
    async for chunk in wrap_with_interactive(_stream(text_start, text_content, text_end), encoder):
        results.append(chunk)

    assert len(results) == 3


@pytest.mark.asyncio
async def test_intercepts_emit_interactive_state_tool_call():
    """emit_interactive_state tool call is replaced by a StateSnapshotEvent."""
    encoder = EventEncoder()
    args = {
        "type": "single_step",
        "steps": [{"step": 1, "title": "Qual é o tema?", "type": "single_choice", "options": ["IA", "Dados"]}],
        "answers": {},
        "batch": 1,
        "total_batches": 1,
    }

    events = [
        _tool_start("tc-1", "emit_interactive_state"),
        _tool_args("tc-1", json.dumps(args)),
        _tool_end("tc-1"),
    ]

    results = []
    async for chunk in wrap_with_interactive(_stream(*events), encoder):
        results.append(chunk)

    # Exactly one encoded SSE line emitted
    assert len(results) == 1
    # Must contain state_snapshot event type
    assert b"state_snapshot" in results[0].lower() or "state_snapshot" in results[0].lower()


@pytest.mark.asyncio
async def test_passthrough_other_tool_calls():
    """Other tool calls pass through unchanged."""
    encoder = EventEncoder()
    events = [
        _tool_start("tc-2", "duckduckgo_search"),
        _tool_args("tc-2", '{"query": "AI news"}'),
        _tool_end("tc-2"),
    ]

    results = []
    async for chunk in wrap_with_interactive(_stream(*events), encoder):
        results.append(chunk)

    assert len(results) == 3


@pytest.mark.asyncio
async def test_split_args_chunks():
    """Args delivered in multiple chunks are correctly reassembled."""
    encoder = EventEncoder()
    args = {
        "type": "single_step",
        "steps": [{"step": 1, "title": "Ok?", "type": "single_choice", "options": ["Sim", "Não"]}],
        "answers": {},
        "batch": 1,
        "total_batches": 1,
    }
    full = json.dumps(args)
    mid = len(full) // 2

    events = [
        _tool_start("tc-3", "emit_interactive_state"),
        _tool_args("tc-3", full[:mid]),
        _tool_args("tc-3", full[mid:]),
        _tool_end("tc-3"),
    ]

    results = []
    async for chunk in wrap_with_interactive(_stream(*events), encoder):
        results.append(chunk)

    assert len(results) == 1
```

- [ ] **Step 2.2 — Run tests to verify they fail**

```bash
.venv/Scripts/python.exe -m pytest tests/test_stream_wrapper.py -v
```

Expected: `ModuleNotFoundError` — `src/agui/stream_wrapper.py` does not exist yet.

- [ ] **Step 2.3 — Create package marker**

```python
# src/agui/__init__.py
```

(Empty file — just makes `src/agui` a Python package.)

- [ ] **Step 2.4 — Create the stream wrapper**

```python
# src/agui/stream_wrapper.py
import json
from typing import AsyncIterator, Union

from ag_ui.core import BaseEvent, EventType, StateSnapshotEvent
from ag_ui.encoder import EventEncoder


async def wrap_with_interactive(
    original_stream: AsyncIterator[BaseEvent],
    encoder: EventEncoder,
) -> AsyncIterator[Union[bytes, str]]:
    """
    Wraps the AG-UI event stream and intercepts emit_interactive_state tool calls.

    When the agent calls emit_interactive_state, the three tool call events
    (TOOL_CALL_START, TOOL_CALL_ARGS, TOOL_CALL_END) are consumed silently and
    replaced with a single encoded StateSnapshotEvent.

    All other events are encoded and yielded unchanged.
    """
    buffer: dict = {}

    async for event in original_stream:
        # Detect start of emit_interactive_state tool call
        if (
            event.type == EventType.TOOL_CALL_START
            and getattr(event, "tool_call_name", None) == "emit_interactive_state"
        ):
            buffer = {
                "collecting": True,
                "tool_call_id": getattr(event, "tool_call_id", ""),
                "args": "",
            }
            continue

        # Accumulate args chunks belonging to the intercepted tool call
        if buffer.get("collecting") and event.type == EventType.TOOL_CALL_ARGS:
            if getattr(event, "tool_call_id", "") == buffer["tool_call_id"]:
                buffer["args"] += getattr(event, "delta", "")
                continue

        # On tool call end, emit the StateSnapshotEvent
        if (
            buffer.get("collecting")
            and event.type == EventType.TOOL_CALL_END
            and getattr(event, "tool_call_id", "") == buffer["tool_call_id"]
        ):
            try:
                args = json.loads(buffer["args"])
            except json.JSONDecodeError:
                args = {}

            snapshot_event = StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                snapshot={
                    "interactive": True,
                    "type": args.get("type", "single_step"),
                    "batch": args.get("batch", 1),
                    "total_batches": args.get("total_batches", 1),
                    "steps": args.get("steps", []),
                    "answers": args.get("answers", {}),
                },
            )
            yield encoder.encode(snapshot_event)
            buffer = {}
            continue

        # All other events pass through encoded
        yield encoder.encode(event)
```

- [ ] **Step 2.5 — Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_stream_wrapper.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 2.6 — Commit**

```bash
git add src/agui/__init__.py src/agui/stream_wrapper.py tests/test_stream_wrapper.py
git commit -m "feat: add AG-UI stream wrapper for StateSnapshotEvent interception"
```

---

## Task 3: Custom AGUI Router

**Files:**
- Create: `src/agui/router.py`

This module replaces the Agno `AGUI` interface with a custom FastAPI router that injects the stream wrapper into each agent's event generator.

- [ ] **Step 3.1 — Create the custom router factory**

```python
# src/agui/router.py
import uuid
from typing import List

from ag_ui.core import EventType, RunStartedEvent, RunErrorEvent
from ag_ui.core import RunAgentInput
from ag_ui.encoder import EventEncoder
from agno.agent import Agent
from agno.os.interfaces.agui.router import run_agent as agno_run_agent
from agno.os.interfaces.agui.utils import async_stream_agno_response_as_agui_events
from agno.os.interfaces.agui.utils import validate_agui_state, convert_agui_messages_to_agno_messages
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.agui.stream_wrapper import wrap_with_interactive


_STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "*",
}


def build_agui_router(agents: List[Agent]) -> APIRouter:
    """
    Builds a single FastAPI router with POST + GET routes for every agent.

    Routes registered:
        POST /agui/{slug}/agui  — streaming run with HITL wrapper
        GET  /agui/{slug}/status — availability check
    """
    router = APIRouter(tags=["AGUI"])

    for agent in agents:
        slug = agent.name.lower().replace(" ", "-")
        _register_agent_routes(router, agent, slug)

    return router


def _register_agent_routes(router: APIRouter, agent: Agent, slug: str) -> None:
    """Register /agui/{slug}/agui and /agui/{slug}/status for a single agent."""
    encoder = EventEncoder()

    # Capture agent in closure — Python loop variable sharing requires this
    _agent = agent

    @router.post(f"/agui/{slug}/agui", name=f"agui_run_{slug}")
    async def run_with_interactive(run_input: RunAgentInput, _a: Agent = _agent):
        run_id = run_input.run_id or str(uuid.uuid4())

        async def event_generator():
            try:
                messages = convert_agui_messages_to_agno_messages(run_input.messages or [])
                session_state = validate_agui_state(run_input.state, run_input.thread_id)

                user_id = None
                if run_input.forwarded_props and isinstance(run_input.forwarded_props, dict):
                    user_id = run_input.forwarded_props.get("user_id")

                yield encoder.encode(
                    RunStartedEvent(
                        type=EventType.RUN_STARTED,
                        thread_id=run_input.thread_id,
                        run_id=run_id,
                    )
                )

                response_stream = _a.arun(
                    input=messages,
                    session_id=run_input.thread_id,
                    stream=True,
                    stream_events=True,
                    user_id=user_id,
                    session_state=session_state,
                    run_id=run_id,
                )

                raw_agui_stream = async_stream_agno_response_as_agui_events(
                    response_stream=response_stream,
                    thread_id=run_input.thread_id,
                    run_id=run_id,
                )

                async for chunk in wrap_with_interactive(raw_agui_stream, encoder):
                    yield chunk

            except Exception as exc:
                yield encoder.encode(
                    RunErrorEvent(type=EventType.RUN_ERROR, message=str(exc))
                )

        return StreamingResponse(event_generator(), media_type="text/event-stream", headers=_STREAM_HEADERS)

    @router.get(f"/agui/{slug}/status", name=f"agui_status_{slug}")
    async def get_status():
        return {"status": "available"}
```

- [ ] **Step 3.2 — Verify the module imports cleanly**

```bash
.venv/Scripts/python.exe -c "from src.agui.router import build_agui_router; print('OK')"
```

Expected: `OK`

- [ ] **Step 3.3 — Commit**

```bash
git add src/agui/router.py
git commit -m "feat: custom AGUI router factory with stream wrapper injection"
```

---

## Task 4: Register Tool in Dynamic Loader

**Files:**
- Modify: `src/tools/dynamic_loader.py`

- [ ] **Step 4.1 — Add `InteractiveTools` to the loader**

Open `src/tools/dynamic_loader.py`. The current file ends at line 36. Add the import and the new branch:

```python
# src/tools/dynamic_loader.py
from typing import List, Dict, Any
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from src.tools.smart_pandas import SmartPandasTools
from src.tools.interactive import emit_interactive_state  # NEW


def load_dynamic_tools(tools_json: List[Dict[str, Any]]) -> List[Any]:
    """
    Instancia ferramentas do Agno com base em uma lista JSON.
    Exemplo de input: [{"name": "DuckDuckGoTools"}, {"name": "SmartPandasTools"}]
    """
    agent_tools = []
    for tool_config in tools_json:
        name = tool_config.get("name")
        kwargs = tool_config.get("kwargs", {})

        if name == "DuckDuckGoTools":
            agent_tools.append(DuckDuckGoTools(**kwargs))
        elif name == "FileTools":
            from pathlib import Path
            if "base_dir" in kwargs:
                kwargs["base_dir"] = Path(kwargs["base_dir"])
            else:
                kwargs["base_dir"] = Path(".")
            agent_tools.append(FileTools(**kwargs))
        elif name == "PythonTools":
            from pathlib import Path
            if "base_dir" in kwargs:
                kwargs["base_dir"] = Path(kwargs["base_dir"])
            else:
                kwargs["base_dir"] = Path(".")
            agent_tools.append(PythonTools(**kwargs))
        elif name == "SmartPandasTools":
            agent_tools.append(SmartPandasTools(**kwargs))
        elif name == "InteractiveTools":  # NEW
            agent_tools.append(emit_interactive_state)

    return agent_tools
```

- [ ] **Step 4.2 — Verify it loads cleanly**

```bash
.venv/Scripts/python.exe -c "from src.tools.dynamic_loader import load_dynamic_tools; r = load_dynamic_tools([{'name': 'InteractiveTools'}]); print(r)"
```

Expected: `[<function emit_interactive_state at 0x...>]`

- [ ] **Step 4.3 — Commit**

```bash
git add src/tools/dynamic_loader.py
git commit -m "feat: register InteractiveTools in dynamic_loader"
```

---

## Task 5: Skill `shared/interactive-output`

**Files:**
- Create: `src/skills/shared/interactive-output/SKILL.md`

- [ ] **Step 5.1 — Create the skill**

```markdown
---
name: interactive-output
description: Quando usar formulários interativos (HITL) e blocos de documento exportável
---

# Skill: Interactive Output

## HITL — Formulários Interativos

Use a ferramenta `emit_interactive_state` quando precisar coletar input estruturado do usuário:
briefings, configurações, questionários, formulários multi-step.

**Quando NÃO usar:** perguntas simples de texto, confirmações rápidas, conversas normais.

### Como usar

1. **Leia o estado anterior** — Antes de qualquer pergunta, verifique `run_input.state`.
   Se `state` contiver `answers`, o usuário já respondeu perguntas anteriores.
   Use essas respostas para continuar de onde parou — nunca repita perguntas já respondidas.

2. **Agrupe em batches de 5** — Nunca emita mais de 5 `steps` por chamada.
   Para um formulário de 20 perguntas: 4 batches de 5 (total_batches=4).

3. **Quando todas as respostas estiverem coletadas** — Processe os dados e gere o output final.
   Não chame `emit_interactive_state` novamente.

### Tipos de step

- `single_choice` — usuário escolhe 1 opção
- `multiple_choice` — usuário escolhe N opções (use `max_selections` para limitar)
- `text_input` — usuário digita texto livre (use `placeholder` como dica)

### Exemplos

**Pergunta pontual (1-2 perguntas):**
```
emit_interactive_state(
    type="single_step",
    steps=[{
        "step": 1,
        "title": "Quer a versão com ou sem grafos?",
        "type": "single_choice",
        "options": ["Com grafos", "Sem grafos", "Ambas"]
    }],
    answers={}
)
```

**Formulário com batches (ex: batch 1 de 4):**
```
emit_interactive_state(
    type="form",
    batch=1,
    total_batches=4,
    steps=[
        {"step": 1, "title": "Qual é a prioridade?", "type": "single_choice", "options": ["Visualizações", "Vendas", "Autoridade"]},
        {"step": 2, "title": "Qual o tema?", "type": "multiple_choice", "options": ["IA para líderes", "IA em vendas"], "max_selections": 2},
        {"step": 3, "title": "Qual o público?", "type": "multiple_choice", "options": ["Empresários", "Gestores", "Equipe"], "max_selections": 2},
        {"step": 4, "title": "Qual a dor principal?", "type": "single_choice", "options": ["Perdido com ferramentas", "Sem estratégia", "Não sabe por onde começar"]},
        {"step": 5, "title": "Contexto adicional", "type": "text_input", "options": None, "placeholder": "Descreva em 1-2 frases..."}
    ],
    answers={}
)
```

---

## Documento Exportável

Use o fence ` ```document ` para qualquer output que o usuário possa querer exportar.

**Quando usar:**
- Relatórios, roteiros, contratos, apresentações
- Quando o usuário pedir: "gera um documento", "relatório", "roteiro", "exportar", "PDF", "DOCX", "apresentação"
- Qualquer output formal com mais de 3 seções

**Quando NÃO usar:** respostas de chat, explicações curtas, listas simples.

### Formato

````
```document
# Título do Documento

## Seção 1
Conteúdo completo, pronto para publicação.

## Seção 2
...
```
````

**Regras:**
- Escreva o conteúdo completo e pronto — não resumos ou esqueletos.
- Use markdown dentro do bloco normalmente.
- Não use ` ```document ` para respostas conversacionais.
```

- [ ] **Step 5.2 — Verify the skill file is recognized by the config validator**

```bash
.venv/Scripts/python.exe -c "
from pathlib import Path
p = Path('src/skills/shared/interactive-output/SKILL.md')
assert p.exists(), 'Skill file not found'
print('OK:', p)
"
```

Expected: `OK: src/skills/shared/interactive-output/SKILL.md`

- [ ] **Step 5.3 — Commit**

```bash
git add src/skills/shared/interactive-output/SKILL.md
git commit -m "feat: add interactive-output skill with HITL and document block instructions"
```

---

## Task 6: Wire Everything in `app.py`

**Files:**
- Modify: `src/app.py`

The change has two parts:
1. Remove `AGUI` interfaces from `AgentOS` (so Agno doesn't register its own routes)
2. Register the custom router from `src/agui/router.py` on the FastAPI app

- [ ] **Step 6.1 — Read the current AGUI section in `app.py`**

Lines 88–121 of `src/app.py` currently look like:

```python
from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI
from src.agents._factory import load_all_agents
from src.config.settings import settings
from src.knowledge.base import get_knowledge_base

agents = load_all_agents()

agui_interfaces = []
for agent in agents:
    agent_slug = agent.name.lower().replace(" ", "-")
    agui_interfaces.append(
        AGUI(
            agent=agent,
            prefix=f"/agui/{agent_slug}",
            tags=["AGUI", agent.name]
        )
    )

agent_os = AgentOS(
    agents=agents,
    knowledge=[get_knowledge_base()],
    interfaces=agui_interfaces,
    tracing=False,
)

app = agent_os.get_app()
```

- [ ] **Step 6.2 — Apply the change**

Replace the AGUI block with the custom router registration. The exact edit:

```python
# REMOVE this import:
# from agno.os.interfaces.agui import AGUI

# ADD this import at the top with the other agno/src imports:
from src.agui.router import build_agui_router
```

Replace the entire `agui_interfaces` block and `AgentOS(interfaces=agui_interfaces, ...)` with:

```python
agents = load_all_agents()

# AgentOS without AGUI interfaces — routes are registered manually below
# so the stream wrapper can be injected into each agent's event generator.
agent_os = AgentOS(
    agents=agents,
    knowledge=[get_knowledge_base()],
    tracing=False,
)

app = agent_os.get_app()

# Register custom AGUI routes with HITL stream wrapper
app.include_router(build_agui_router(agents))
```

The full relevant section of `src/app.py` after the edit (lines 88–124):

```python
from agno.os import AgentOS
from src.agents._factory import load_all_agents
from src.config.settings import settings
from src.knowledge.base import get_knowledge_base
from src.agui.router import build_agui_router

agents = load_all_agents()

agent_os = AgentOS(
    agents=agents,
    knowledge=[get_knowledge_base()],
    tracing=False,
)

app = agent_os.get_app()

# Register custom AGUI routes with HITL stream wrapper
app.include_router(build_agui_router(agents))

# Painel admin de gestão de knowledge
app.include_router(admin_router, prefix="/admin")
app.add_middleware(AdminAuthMiddleware)
```

- [ ] **Step 6.3 — Verify the app loads without errors**

```bash
.venv/Scripts/python.exe -c "from src.app import app; print('OK —', len([r for r in app.routes if '/agui/' in str(getattr(r, 'path', ''))]), 'AGUI routes registered')"
```

Expected: `OK — 18 AGUI routes registered` (9 agents × 2 routes each: `/agui` + `/status`)

- [ ] **Step 6.4 — Commit**

```bash
git add src/app.py
git commit -m "feat: replace Agno AGUI interfaces with custom router (HITL wrapper injected)"
```

---

## Task 7: Add Skill and Tool to `config/agents.yaml`

**Files:**
- Modify: `config/agents.yaml`

Add `shared/interactive-output` to `skills` and `InteractiveTools` to `tools` for **all 9 agents**. The cleanest approach is to add them to `globals.default_features` is not available for skills/tools, so each agent block must be updated individually.

- [ ] **Step 7.1 — Add to Super Admin Assistant**

In `config/agents.yaml`, find the `Super Admin Assistant` block. Add to its `skills` list and `tools` list:

```yaml
    skills:
      - "shared/data-analysis"
      - "shared/web-research"
      - "shared/document-analysis"
      - "shared/interactive-output"   # ADD

    tools:
      - name: "DuckDuckGoTools"
      - name: "SmartPandasTools"
      - name: "FileTools"
        kwargs:
          base_dir: "."
      - name: "PythonTools"
        kwargs:
          base_dir: "tmp/workspace"
      - name: "InteractiveTools"      # ADD
```

- [ ] **Step 7.2 — Add to all remaining agents**

Repeat the same additions (append `"shared/interactive-output"` to `skills` and add `- name: "InteractiveTools"` to `tools`) for each of the 8 remaining agents:
- General Assistant
- Marketing Assistant
- Juridico Assistant
- Finance Assistant
- HR Assistant
- Sales Assistant
- Operations Assistant
- IT Assistant

Each agent block already has a `skills:` list and a `tools:` list. Append to both.

- [ ] **Step 7.3 — Verify the config loads and all agents have the tool**

```bash
.venv/Scripts/python.exe -c "
from src.agents._config import load_agents_config
agents = load_agents_config()
for a in agents:
    has_tool = any(t.name == 'InteractiveTools' for t in a.tools)
    has_skill = 'shared/interactive-output' in a.skills
    status = 'OK' if has_tool and has_skill else 'MISSING'
    print(f'{status} | {a.name}')
"
```

Expected: All 9 lines show `OK`.

- [ ] **Step 7.4 — Verify the full app still starts**

```bash
.venv/Scripts/python.exe -c "from src.app import app; print('App loaded OK')"
```

Expected: `App loaded OK` (with agent loading logs above it).

- [ ] **Step 7.5 — Commit**

```bash
git add config/agents.yaml
git commit -m "feat: add interactive-output skill and InteractiveTools to all agents"
```

---

## Task 8: End-to-End Smoke Test

**Files:**
- No new files — manual verification against the running server.

- [ ] **Step 8.1 — Start the server**

```bash
.venv/Scripts/python.exe -m uvicorn src.app:app --host 0.0.0.0 --port 7777 --reload
```

- [ ] **Step 8.2 — Verify status endpoints respond**

```bash
curl http://localhost:7777/agui/super-admin-assistant/status
curl http://localhost:7777/agui/marketing-assistant/status
```

Expected both: `{"status": "available"}`

- [ ] **Step 8.3 — Verify existing endpoints still work**

```bash
curl http://localhost:7777/health
curl http://localhost:7777/agents
```

Expected: health `{"status":"ok"}` and agents list with 9 agents.

- [ ] **Step 8.4 — Test the HITL stream manually**

```bash
curl -X POST http://localhost:7777/agui/super-admin-assistant/agui \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "test-thread-1",
    "run_id": "test-run-1",
    "messages": [{"role": "user", "content": "Preciso criar um briefing para um Reels. Me faça as perguntas necessárias usando o formulário interativo."}],
    "state": null,
    "forwarded_props": {}
  }'
```

Expected: SSE stream that includes at least one `event: state_snapshot` line with `"interactive": true` in the data.

- [ ] **Step 8.5 — Test the document block**

```bash
curl -X POST http://localhost:7777/agui/super-admin-assistant/agui \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "test-thread-2",
    "run_id": "test-run-2",
    "messages": [{"role": "user", "content": "Gere um relatório executivo de exemplo sobre uso de IA em empresas."}],
    "state": null,
    "forwarded_props": {}
  }'
```

Expected: SSE stream with text content that includes ` ```document ` in the delta events.

- [ ] **Step 8.6 — Run the full test suite**

```bash
.venv/Scripts/python.exe -m pytest tests/test_interactive_tool.py tests/test_stream_wrapper.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 8.7 — Final commit**

```bash
git add .
git commit -m "feat: AG-UI interactive output complete — HITL + document blocks"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by |
|---|---|
| `emit_interactive_state` tool function | Task 1 |
| Stream wrapper intercepts tool call → `StateSnapshotEvent` | Task 2 |
| Custom AGUI router without patching agno internals | Task 3 |
| `InteractiveTools` registered in `dynamic_loader` | Task 4 |
| Skill `shared/interactive-output` with HITL + document instructions | Task 5 |
| `AgentOS` without AGUI interfaces + custom router in `app.py` | Task 6 |
| All 9 agents updated in `config/agents.yaml` | Task 7 |
| Snapshot shape: `interactive`, `type`, `batch`, `total_batches`, `steps`, `answers` | Task 2 + Task 3 |
| `single_choice`, `multiple_choice`, `text_input` step types | Task 5 |
| `max_selections` and `placeholder` optional fields | Task 5 |
| Batches of 5 steps max | Task 5 |
| Agent reads `run_input.state["answers"]` to continue from previous batch | Task 5 |
| `document` fence — no backend code needed | Task 5 (instructions only) |

**No gaps found.**
