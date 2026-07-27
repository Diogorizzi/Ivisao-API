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
