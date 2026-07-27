import json
import logging
from typing import AsyncIterator, Optional, Union

from ag_ui.core import BaseEvent, EventType, StateSnapshotEvent
from ag_ui.encoder import EventEncoder

_log = logging.getLogger(__name__)


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
    If the tool call args contain invalid JSON, a StateSnapshotEvent with empty
    defaults is emitted rather than propagating an error.
    """
    buffer: Optional[dict] = None

    async for event in original_stream:
        # Detect start of emit_interactive_state tool call
        if (
            event.type == EventType.TOOL_CALL_START
            and getattr(event, "tool_call_name", None) == "emit_interactive_state"
        ):
            buffer = {
                "tool_call_id": getattr(event, "tool_call_id", ""),
                "args": "",
            }
            continue

        # Accumulate args chunks belonging to the intercepted tool call
        if buffer is not None and event.type == EventType.TOOL_CALL_ARGS:
            if getattr(event, "tool_call_id", "") == buffer["tool_call_id"]:
                buffer["args"] += getattr(event, "delta", "")
                continue

        # On tool call end, emit the StateSnapshotEvent
        if (
            buffer is not None
            and event.type == EventType.TOOL_CALL_END
            and getattr(event, "tool_call_id", "") == buffer["tool_call_id"]
        ):
            try:
                args = json.loads(buffer["args"])
            except json.JSONDecodeError:
                _log.error("emit_interactive_state: invalid JSON args: %r", buffer["args"])
                args = {}

            _log.info(
                "emit_interactive_state received: type=%s batch=%s total=%s steps_count=%s",
                args.get("type"), args.get("batch"), args.get("total_batches"),
                len(args.get("steps") or []),
            )

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
            buffer = None
            continue

        # All other events pass through encoded
        yield encoder.encode(event)

    # After the async for loop:
    if buffer is not None:
        import logging
        logging.warning(
            "AG-UI stream ended with incomplete emit_interactive_state call (tool_call_id=%s)",
            buffer.get("tool_call_id", "unknown"),
        )
