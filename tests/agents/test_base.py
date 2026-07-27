import pytest
from unittest.mock import Mock, patch


def test_create_base_agent_uses_agentic_rag_when_knowledge_provided():
    """
    Quando knowledge é fornecido, o agente deve ser criado com
    add_knowledge_to_context=False (Agentic RAG) e search_knowledge=True.
    O LLM decide quando buscar, não o pipeline.
    """
    mock_knowledge = Mock()

    with patch('src.agents._base.get_model') as mock_model, \
         patch('src.agents._base.get_db') as mock_db, \
         patch('src.agents._base.get_memory_manager') as mock_mem, \
         patch('src.agents._base.Agent') as mock_agent_cls:

        mock_model.return_value = Mock()
        mock_db.return_value = Mock()
        mock_mem.return_value = Mock()
        mock_agent_cls.return_value = Mock()

        from src.agents._base import create_base_agent
        create_base_agent(
            name="Test Agent",
            knowledge=mock_knowledge,
        )

        _, kwargs = mock_agent_cls.call_args
        assert kwargs.get('add_knowledge_to_context') is False, (
            "add_knowledge_to_context deve ser False para usar Agentic RAG"
        )
        assert kwargs.get('search_knowledge') is True, (
            "search_knowledge deve ser True para expor a tool ao LLM"
        )


def test_create_base_agent_without_knowledge_has_no_rag_flags():
    """
    Quando knowledge=None, os flags RAG devem seguir os defaults do Agno
    (add_knowledge_to_context=False, search_knowledge=True ainda).
    """
    with patch('src.agents._base.get_model') as mock_model, \
         patch('src.agents._base.get_db') as mock_db, \
         patch('src.agents._base.get_memory_manager') as mock_mem, \
         patch('src.agents._base.Agent') as mock_agent_cls:

        mock_model.return_value = Mock()
        mock_db.return_value = Mock()
        mock_mem.return_value = Mock()
        mock_agent_cls.return_value = Mock()

        from src.agents._base import create_base_agent
        create_base_agent(
            name="Test Agent",
            knowledge=None,
        )

        _, kwargs = mock_agent_cls.call_args
        assert kwargs.get('add_knowledge_to_context') is False
        assert kwargs.get('search_knowledge') is True
