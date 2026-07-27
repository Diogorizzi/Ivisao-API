from typing import Any, Dict

from agno.tools.function import Function


def _emit_interactive_state(**kwargs: Any) -> str:
    # Entrypoint receives raw kwargs from the LLM — no validation, no crashing.
    # The real work happens in stream_wrapper.py which reads the tool call args
    # directly from the AG-UI event stream before this function even runs.
    return "INTERACTIVE_STATE_EMITTED"


# Prevent agno's _wrap_callable from applying validate_call to this function.
# The check `getattr(func, "_wrapped_for_validation", False)` in agno's code
# skips wrapping when this flag is set.
_emit_interactive_state._wrapped_for_validation = True  # type: ignore


# Schema is defined manually so Agno's schema-inference code (which mishandles
# Dict[str, Any] and List[Dict] → produces broken additionalProperties:false)
# is bypassed entirely. skip_entrypoint_processing=True also prevents Pydantic's
# validate_call from wrapping the entrypoint, which was crashing when the LLM
# sent slightly non-conforming args (e.g. answers as a list instead of dict).
_STEP_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "step":    {"type": "integer", "description": "Global step number, 1-indexed across all batches."},
        "title":   {"type": "string",  "description": "Question text shown to the user."},
        "type":    {"type": "string",  "enum": ["single_choice", "multiple_choice", "text_input"]},
        "options": {
            "description": "Array of choice strings for single_choice/multiple_choice. Omit or null for text_input.",
            "anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}],
        },
        "max_selections": {
            "description": "Maximum number of selections for multiple_choice.",
            "anyOf": [{"type": "integer"}, {"type": "null"}],
        },
        "placeholder": {
            "description": "Hint text shown inside a text_input field.",
            "anyOf": [{"type": "string"}, {"type": "null"}],
        },
    },
    "required": ["step", "title", "type"],
}

_EMIT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["form", "single_step"],
            "description": (
                'Use "form" for questionnaires with 5+ questions (split into batches of 5). '
                'Use "single_step" for 1–2 quick clarifying questions.'
            ),
        },
        "steps": {
            "type": "array",
            "description": "List of questions for this batch. Max 5 items.",
            "items": _STEP_SCHEMA,
        },
        "answers": {
            "type": "object",
            "description": (
                'Answers already collected in previous batches. '
                'Keys are step numbers as strings (e.g. "1", "2"). '
                'Values are the answer string or array of strings. '
                'Pass {} on the first call.'
            ),
            "additionalProperties": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}},
                ]
            },
        },
        "batch":        {"type": "integer", "description": "Current batch number, 1-indexed. Only used when type=form."},
        "total_batches": {"type": "integer", "description": "Total number of batches planned. Only used when type=form."},
    },
    "required": ["type", "steps", "answers"],
}

emit_interactive_state = Function(
    name="emit_interactive_state",
    description=(
        "Emit an interactive form or question to the user via the AG-UI protocol. "
        "Call this BEFORE generating content whenever the request is ambiguous or "
        "depends on variables that would produce very different outputs. "
        "Do NOT call after already having enough context."
    ),
    parameters=_EMIT_SCHEMA,
    entrypoint=_emit_interactive_state,
    skip_entrypoint_processing=True,
)
