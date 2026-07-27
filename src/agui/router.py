import uuid
from typing import List

from ag_ui.core import EventType, RunStartedEvent, RunErrorEvent, RunAgentInput
from ag_ui.encoder import EventEncoder
from agno.agent import Agent
from agno.models.message import Message
from agno.os.interfaces.agui.utils import (
    async_stream_agno_response_as_agui_events,
    validate_agui_state,
    convert_agui_messages_to_agno_messages,
)
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.agui.stream_wrapper import wrap_with_interactive


_STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
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
    _agent = agent

    @router.post(f"/agui/{slug}/agui", name=f"agui_run_{slug}")
    async def run_with_interactive(run_input: RunAgentInput):
        run_id = run_input.run_id or str(uuid.uuid4())

        async def event_generator():
            try:
                messages = convert_agui_messages_to_agno_messages(run_input.messages or [])
                session_state = validate_agui_state(run_input.state, run_input.thread_id)

                # When the frontend submits a form, the session_state contains the
                # collected answers (answers dict is non-empty) but there is no new
                # user message — only the thread history ending with an assistant turn.
                # Without a new user message the LLM never gets a turn, so we inject
                # a trigger.  We handle two variants:
                #   A) Frontend sends empty messages + state (answers only).
                #   B) Frontend sends full history + state (last msg is from assistant).
                has_form_answers = (
                    isinstance(session_state, dict)
                    and session_state.get("interactive")
                    and bool(session_state.get("answers"))
                )
                if has_form_answers:
                    if not messages:
                        messages = [Message(role="user", content="<form_answers_submitted>")]
                    elif messages[-1].role != "user":
                        messages = messages + [Message(role="user", content="<form_answers_submitted>")]

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

                response_stream = _agent.arun(
                    input=messages,
                    session_id=run_input.thread_id,
                    stream=True,
                    stream_events=True,
                    user_id=user_id,
                    session_state=session_state,
                    add_session_state_to_context=True,
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
