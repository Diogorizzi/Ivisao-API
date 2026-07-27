import json
import pytest
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

    assert len(results) == 1
    assert "state_snapshot" in results[0].lower()


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


@pytest.mark.asyncio
async def test_malformed_args_yields_empty_snapshot():
    """Malformed JSON in args falls back to empty snapshot defaults."""
    encoder = EventEncoder()
    events = [
        _tool_start("tc-4", "emit_interactive_state"),
        _tool_args("tc-4", "not-valid-json"),
        _tool_end("tc-4"),
    ]

    results = []
    async for chunk in wrap_with_interactive(_stream(*events), encoder):
        results.append(chunk)

    # Still emits exactly one StateSnapshotEvent (with defaults)
    assert len(results) == 1
    assert "state_snapshot" in results[0].lower()


@pytest.mark.asyncio
async def test_interleaved_text_and_interactive_tool():
    """Text events before and after intercepted tool call pass through correctly."""
    encoder = EventEncoder()
    args = {
        "type": "single_step",
        "steps": [{"step": 1, "title": "Ok?", "type": "single_choice", "options": ["Sim", "Não"]}],
        "answers": {},
        "batch": 1,
        "total_batches": 1,
    }
    text_before = TextMessageStartEvent(type=EventType.TEXT_MESSAGE_START, message_id="m1", role="assistant")
    text_after = TextMessageEndEvent(type=EventType.TEXT_MESSAGE_END, message_id="m1")

    events = [
        text_before,
        _tool_start("tc-5", "emit_interactive_state"),
        _tool_args("tc-5", json.dumps(args)),
        _tool_end("tc-5"),
        text_after,
    ]

    results = []
    async for chunk in wrap_with_interactive(_stream(*events), encoder):
        results.append(chunk)

    # 2 text events + 1 state_snapshot = 3 total
    assert len(results) == 3
    assert "state_snapshot" in results[1].lower()
