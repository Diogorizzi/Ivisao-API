# Agentic RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mudar agentes com RAG de "busca automática em toda mensagem" para "Agentic RAG" — onde o LLM decide quando chamar `search_knowledge` como tool.

**Architecture:** Dois arquivos alterados. Em `_base.py`, `add_knowledge_to_context` vai de `True` para `False`, mantendo `search_knowledge=True` para que o Agno exponha a tool ao LLM. Em `agents.yaml`, uma instrução guia é adicionada aos 8 agentes com `rag: true` para orientar quando usar a tool.

**Tech Stack:** Python, Agno framework, pytest, PyYAML

---

## Estrutura de Arquivos

| Arquivo | Alteração |
|---|---|
| `src/agents/_base.py` | Mudar `add_knowledge_to_context: True` → `False` |
| `config/agents.yaml` | Adicionar instrução guia nos 8 agentes com `rag: true` |
| `tests/agents/test_base.py` | Novo — testa que `add_knowledge_to_context=False` no agente criado |
| `tests/agents/test_factory.py` | Adicionar teste que verifica instrução guia nos agentes RAG |

---

## Task 1: Teste para `add_knowledge_to_context=False` em `_base.py`

**Files:**
- Create: `tests/agents/test_base.py`

- [ ] **Step 1: Criar o arquivo de teste**

```python
# tests/agents/test_base.py
import pytest
from unittest.mock import Mock, patch, call


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
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

```
pytest tests/agents/test_base.py -v
```

Esperado: `FAILED` — `add_knowledge_to_context` ainda é `True` no código atual.

- [ ] **Step 3: Alterar `src/agents/_base.py` linha 207**

Localizar o bloco em [src/agents/_base.py:199-210](src/agents/_base.py#L199-L210):

```python
    agent_params = {
        "name": name,
        "model": model,
        "db": get_db(),
        "memory_manager": get_memory_manager(),
        "enable_agentic_memory": True,
        "add_memories_to_context": True,
        # Knowledge base (ChromaDB) — RAG ativado para consultas semânticas.
        # Os arquivos de upload ainda são processados pelas ferramentas (PandasTools/FileTools).
        "knowledge": knowledge,
        "add_knowledge_to_context": False,  # Agentic RAG: LLM decide quando buscar
        "search_knowledge": True,           # Expõe a tool search_knowledge ao LLM
        "update_knowledge": False,
        ...
    }
```

A única mudança é na linha 207: `True` → `False`. O comentário deve ser atualizado conforme acima.

- [ ] **Step 4: Rodar o teste para confirmar que passa**

```
pytest tests/agents/test_base.py -v
```

Esperado: `PASSED` para ambos os testes.

- [ ] **Step 5: Rodar toda a suite de testes**

```
pytest tests/ -v
```

Esperado: todos os testes existentes continuam passando.

- [ ] **Step 6: Commit**

```bash
git add src/agents/_base.py tests/agents/test_base.py
git commit -m "feat: switch to agentic RAG (add_knowledge_to_context=False)

O LLM agora decide quando chamar search_knowledge, em vez de buscar
automaticamente no ChromaDB em toda mensagem recebida.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Instrução guia no `agents.yaml` para agentes com RAG

**Files:**
- Modify: `config/agents.yaml`
- Modify: `tests/agents/test_factory.py`

Os agentes com `rag: true` são: **Super Admin, Marketing, Juridico, Finance, HR, Sales, Operations, IT** (8 no total).

- [ ] **Step 1: Escrever o teste que verifica a instrução guia**

Adicionar ao final de `tests/agents/test_factory.py`:

```python
def test_rag_agents_have_search_knowledge_instruction(tmp_path, monkeypatch):
    """
    Agentes com rag: true devem ter a instrução guia que orienta
    o LLM a usar search_knowledge apenas para informações internas.
    """
    from src.agents._config import load_agents_config

    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    agents_yaml = """
globals:
  default_model: "gpt-4o-mini"
  default_features:
    memory: true
    rag: false

agents:
  - name: "Agente Com RAG"
    department: "marketing"
    features:
      rag: true
    instructions:
      - "Instrução existente"
      - "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas da empresa, documentos, políticas ou dados específicos do departamento."

  - name: "Agente Sem RAG"
    department: "geral"
    features:
      rag: false
    instructions:
      - "Instrução sem RAG"
"""
    (config_dir / "agents.yaml").write_text(agents_yaml)

    agents = load_agents_config()

    rag_agent = next(a for a in agents if a.name == "Agente Com RAG")
    no_rag_agent = next(a for a in agents if a.name == "Agente Sem RAG")

    rag_instruction = "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas"
    assert any(rag_instruction in instr for instr in rag_agent.instructions), (
        "Agente com RAG deve ter instrução guia para search_knowledge"
    )
    assert not any(rag_instruction in instr for instr in no_rag_agent.instructions), (
        "Agente sem RAG não deve ter instrução de search_knowledge"
    )
```

- [ ] **Step 2: Rodar o teste para confirmar que passa**

```
pytest tests/agents/test_factory.py::test_rag_agents_have_search_knowledge_instruction -v
```

Esperado: `PASSED` — o teste valida a estrutura do YAML, não o estado atual do arquivo real.

- [ ] **Step 3: Adicionar instrução nos 8 agentes com `rag: true` em `config/agents.yaml`**

A instrução a adicionar no bloco `instructions:` de cada agente com `rag: true`:

```yaml
- "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas da empresa, documentos, políticas ou dados específicos do departamento."
```

**Super Admin** — localizar `instructions:` do agente e adicionar ao final:
```yaml
    instructions:
      - "Você é o assistente executivo da {{company_name}}."
      - "{{company_description}}"
      - "Você tem acesso a TODOS os dados da empresa."
      - "Use esse privilégio com responsabilidade."
      - "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas da empresa, documentos, políticas ou dados específicos do departamento."
```

**Marketing Assistant** — adicionar ao final do bloco `instructions:`:
```yaml
    instructions:
      - "Você é o assistente de Marketing da {{company_name}}."
      - "{{company_description}}"
      - "Você é especialista em criar campanhas criativas e analisar métricas."
      - "Você tem acesso exclusivo aos dados de Marketing no RAG."
      - "Use web_search para pesquisar tendências atuais de mercado."
      - "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas da empresa, documentos, políticas ou dados específicos do departamento."
```

**Juridico Assistant** — adicionar ao final:
```yaml
    instructions:
      - "Você é o assistente jurídico da {{company_name}}."
      - "{{company_description}}"
      - "Você é especialista em análise de contratos, conformidade legal e regulamentações."
      - "Você tem acesso aos dados de Jurídico no RAG."
      - "Sempre revise contratos com atenção aos detalhes."
      - "Recomende consulta com especialistas externos quando necessário."
      - "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas da empresa, documentos, políticas ou dados específicos do departamento."
```

**Finance Assistant** — adicionar ao final:
```yaml
    instructions:
      - "Você é o assistente de Finanças da {{company_name}}."
      - "{{company_description}}"
      - "Você é especialista em análise de orçamentos, previsões e relatórios financeiros."
      - "Você tem acesso aos dados de Finanças no RAG."
      - "Mantenha a precisão em todos os cálculos e análises."
      - "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas da empresa, documentos, políticas ou dados específicos do departamento."
```

**HR Assistant** — adicionar ao final:
```yaml
    instructions:
      - "Você é o assistente de Recursos Humanos da {{company_name}}."
      - "{{company_description}}"
      - "Você é especialista em recrutamento, gestão de desempenho e desenvolvimento de pessoal."
      - "Você tem acesso aos dados de RH no RAG."
      - "Trate informações sensíveis de funcionários com total confidencialidade."
      - "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas da empresa, documentos, políticas ou dados específicos do departamento."
```

**Sales Assistant** — adicionar ao final:
```yaml
    instructions:
      - "Você é o assistente de Vendas da {{company_name}}."
      - "{{company_description}}"
      - "Você é especialista em gestão de oportunidades, análise de mercado e criação de propostas."
      - "Você tem acesso aos dados de Vendas no RAG."
      - "Foque em entender as necessidades do cliente e oferecer soluções personalizadas."
      - "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas da empresa, documentos, políticas ou dados específicos do departamento."
```

**Operations Assistant** — adicionar ao final:
```yaml
    instructions:
      - "Você é o assistente de Operações da {{company_name}}."
      - "{{company_description}}"
      - "Você é especialista em otimização de processos, eficiência operacional e qualidade."
      - "Você tem acesso aos dados de Operações no RAG."
      - "Identifique gargalos e proponha soluções de melhoria contínua."
      - "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas da empresa, documentos, políticas ou dados específicos do departamento."
```

**IT Assistant** — adicionar ao final:
```yaml
    instructions:
      - "Você é o assistente de TI da {{company_name}}."
      - "{{company_description}}"
      - "Você é especialista em infraestrutura de TI, segurança e suporte técnico."
      - "Você tem acesso aos dados de TI no RAG."
      - "Priorize segurança e disponibilidade dos sistemas."
      - "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas da empresa, documentos, políticas ou dados específicos do departamento."
```

- [ ] **Step 4: Rodar toda a suite de testes**

```
pytest tests/ -v
```

Esperado: todos os testes passando.

- [ ] **Step 5: Commit**

```bash
git add config/agents.yaml tests/agents/test_factory.py
git commit -m "feat: add search_knowledge guidance instruction to RAG agents

Orienta o LLM a usar search_knowledge apenas para perguntas sobre
informações internas, complementando a mudança para Agentic RAG.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
