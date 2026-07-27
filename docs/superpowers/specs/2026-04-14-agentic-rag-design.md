# Agentic RAG — Busca Inteligente no Knowledge Base

**Data:** 2026-04-14
**Status:** Aprovado

## Problema

Agentes com RAG ativado buscam no ChromaDB para toda e qualquer mensagem recebida, incluindo saudações simples como "Oi". Isso ocorre porque `add_knowledge_to_context: True` em `src/agents/_base.py` instrui o Agno a injetar contexto RAG no pipeline antes de toda resposta, sem avaliar a relevância da mensagem.

Consequências:
- Latência desnecessária em mensagens que não precisam de contexto interno
- Embeddings sendo gerados e chamadas ao ChromaDB para perguntas genéricas
- Custo de inferência do embedder (Gemini) para mensagens irrelevantes

## Solução — Agentic RAG

Mudar o modo de RAG de "sempre busca" para "o LLM decide quando buscar".

O Agno suporta isso nativamente:
- `add_knowledge_to_context=True` → RAG clássico (busca automática em toda mensagem)
- `add_knowledge_to_context=False` + `search_knowledge=True` → Agentic RAG (LLM chama a tool `search_knowledge` quando julgar necessário)

## Arquitetura

### Componentes Modificados

```
src/agents/_base.py        — flag add_knowledge_to_context: True → False
config/agents.yaml          — instrução guia adicionada em agentes com rag: true
```

Nenhuma alteração em `src/knowledge/base.py`, `_factory.py`, `_config.py` ou no ChromaDB.

### Fluxo Antes

```
Usuário: "Oi"
  └─> Agno pipeline
        └─> Gera embedding da mensagem
        └─> Busca no ChromaDB
        └─> Injeta documentos no contexto
        └─> LLM responde
```

### Fluxo Depois

```
Usuário: "Oi"
  └─> Agno pipeline
        └─> LLM decide: precisa de knowledge? → NÃO
        └─> LLM responde direto

Usuário: "Qual o orçamento aprovado para Q1?"
  └─> Agno pipeline
        └─> LLM decide: precisa de knowledge? → SIM
        └─> Chama tool search_knowledge("orçamento Q1")
        └─> Agno executa busca no ChromaDB
        └─> LLM responde com contexto
```

## Mudanças Detalhadas

### 1. `src/agents/_base.py`

```python
# Linha 207 — antes
"add_knowledge_to_context": True,

# Linha 207 — depois
"add_knowledge_to_context": False,
```

`search_knowledge: True` permanece inalterado — isso garante que a tool `search_knowledge` continue disponível para o LLM.

### 2. `config/agents.yaml`

Agentes com `rag: true`: Super Admin, Marketing, Juridico, Finance, HR, Sales, Operations, IT.

Instrução a adicionar em cada um:

```yaml
instructions:
  # ... instruções existentes ...
  - "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas da empresa, documentos, políticas ou dados específicos do departamento."
```

## Comportamento Esperado

| Mensagem | Antes | Depois |
|---|---|---|
| "Oi" | Busca ChromaDB | Responde direto |
| "Qual o orçamento de Q1?" | Busca ChromaDB | Busca ChromaDB (LLM decide) |
| "O que é CLT?" | Busca ChromaDB | Responde do conhecimento geral |
| "Qual cláusula 5 do contrato X?" | Busca ChromaDB | Busca ChromaDB (LLM decide) |
| "Resuma os dados de RH de 2024" | Busca ChromaDB | Busca ChromaDB (LLM decide) |

## Escopo

- Não altera nenhuma lógica de ingestão de documentos
- Não altera filtros de departamento (multitenancy permanece intacto)
- Não altera a configuração por agente em `AgentFeatures` (sem novo campo)
- Agentes com `rag: false` não são afetados (já não possuem knowledge)
- A mudança é global para todos os agentes com RAG ativo
