"""
Registry do AgentOS Studio.

Registra todos os modelos disponíveis (baseado nas credenciais do .env),
ferramentas padrão e o banco de dados para que o AgentOS Studio possa
listar e usar esses componentes ao criar agentes visualmente.
"""
from __future__ import annotations

import os
from typing import Optional
from agno.registry import Registry
from src.config.llm_providers import PROVIDER_REGISTRY


def _build_models() -> list:
    """Constrói instâncias de modelo para todos os providers disponíveis."""
    models = []

    # OpenAI
    if PROVIDER_REGISTRY["openai"].is_available():
        from agno.models.openai import OpenAIChat
        api_key = os.environ.get("OPENAI_API_KEY", "")
        for model_id in [
            "gpt-5.5",
            "gpt-5.4",
            "gpt-5.4-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "o3",
            "o4-mini",
            "o3-mini",
            "gpt-4o",
            "gpt-4o-mini",
        ]:
            try:
                models.append(OpenAIChat(id=model_id, api_key=api_key))
            except Exception:
                pass

    # Anthropic
    if PROVIDER_REGISTRY["anthropic"].is_available():
        from agno.models.anthropic import Claude
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        for model_id in [
            "claude-4.8-opus",
            "claude-4.6-sonnet",
            "claude-opus-4-5",
            "claude-sonnet-4-5",
            "claude-sonnet-4",
            "claude-haiku-3-5",
            "claude-3-5-sonnet-20241022",
        ]:
            try:
                models.append(Claude(id=model_id, api_key=api_key))
            except Exception:
                pass

    # Google Gemini (opcional — requer google-genai compatível)
    if PROVIDER_REGISTRY["google"].is_available():
        try:
            from agno.models.google import Gemini
            api_key = os.environ.get("GOOGLE_API_KEY", "")
            for model_id in [
                "gemini-3.5-flash",
                "gemini-3.1-pro",
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                "gemini-2.0-flash",
                "gemini-1.5-pro",
            ]:
                try:
                    models.append(Gemini(id=model_id, api_key=api_key))
                except Exception:
                    pass
        except Exception as e:
            print(f"[Registry] Google Gemini não disponível (google-genai incompatível): {e}")

    # Groq
    if PROVIDER_REGISTRY["groq"].is_available():
        from agno.models.groq import Groq
        api_key = os.environ.get("GROQ_API_KEY", "")
        for model_id in [
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "llama-3.3-70b-versatile",
            "deepseek-r1-distill-llama-70b",
            "qwen-qwq-32b",
            "gemma2-9b-it",
        ]:
            try:
                models.append(Groq(id=model_id, api_key=api_key))
            except Exception:
                pass

    # OpenRouter
    if PROVIDER_REGISTRY["openrouter"].is_available():
        from agno.models.openrouter import OpenRouter
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        for model_id in [
            "deepseek/deepseek-r1",
            "deepseek/deepseek-chat-v3-0324",
            "google/gemini-2.5-pro",
            "anthropic/claude-sonnet-4-5",
            "meta-llama/llama-4-maverick",
            "microsoft/mai-ds-r1:free",
            "qwen/qwq-32b:free",
        ]:
            try:
                models.append(OpenRouter(id=model_id, api_key=api_key))
            except Exception:
                pass

    return models


def _build_tools() -> list:
    """Ferramentas disponíveis para seleção no Studio."""
    tools = []
    try:
        from agno.tools.duckduckgo import DuckDuckGoTools
        tools.append(DuckDuckGoTools())
    except Exception:
        pass
    try:
        from agno.tools.file import FileTools
        tools.append(FileTools())
    except Exception:
        pass
    try:
        from agno.tools.python import PythonTools
        tools.append(PythonTools())
    except Exception:
        pass
    try:
        from agno.tools.pandas import PandasTools
        tools.append(PandasTools())
    except Exception:
        pass
    return tools


def _build_dbs(studio_db) -> list:
    """DBs disponíveis no Registry (inclui o db do Studio)."""
    dbs = []
    if studio_db is not None:
        dbs.append(studio_db)
    return dbs


def build_registry(studio_db=None) -> Registry:
    """
    Constrói o Registry do AgentOS com todos os componentes disponíveis.

    Args:
        studio_db: Instância do DB (SqliteDb ou PostgresDb) usada pelo AgentOS.
                   Necessária para que o Studio salve agentes/versões.

    Returns:
        Registry instanciado e pronto para uso no AgentOS.
    """
    models = _build_models()
    tools = _build_tools()
    dbs = _build_dbs(studio_db)

    print(f"\n[Registry] {len(models)} modelos registrados")
    print(f"[Registry] {len(tools)} ferramentas registradas")
    print(f"[Registry] {len(dbs)} DBs registrados\n")

    registry = Registry(
        name="Dartha Registry",
        models=models if models else None,
        tools=tools if tools else None,
        dbs=dbs if dbs else None,
    )

    return registry
