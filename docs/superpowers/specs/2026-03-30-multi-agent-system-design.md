# Sistema Multi-Agente Escalável com Agno

**Data:** 2026-03-30
**Autor:** Claude (via Brainstorming Skill)
**Status:** Aprovado para Implementação

---

## Sumário Executivo

Este documento especifica a arquitetura de um sistema multi-agente escalável usando Agno, onde cada empresa cliente recebe sua própria instância isolada com agentes departamentais configuráveis via YAML. O objetivo é permitir que empresas repliquem e personalizem agentes facilmente, com isolamento de conhecimento por departamento e documentação otimizada para uso assistido por LLMs.

**Principais Características:**
- ✅ Configuração 100% YAML (zero código Python para criar agentes)
- ✅ Isolamento de conhecimento por departamento (ChromaDB com filtros)
- ✅ Controle granular de features, tools, skills e modelos por agente
- ✅ Documentação otimizada para Claude Code/LLMs
- ✅ Templates copiáveis para diferentes tipos de agentes
- ✅ Scripts de validação e ingestão automatizados

---

## 1. Visão Geral da Arquitetura

### 1.1 Conceito Central

Sistema de agentes departamentais configuráveis via YAML, onde cada empresa cliente tem sua própria instância isolada (deployment separado). A configuração é simples o suficiente para leigos copiarem templates, mas poderosa o suficiente para customizações avançadas.

### 1.2 Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────┐
│                   Cliente (Empresa)                  │
│  Frontend (cloud) ──> API Local (Docker/VM)         │
└─────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│              AgentOS (Dartha API V3)                 │
├─────────────────────────────────────────────────────┤
│  config/                                             │
│    ├── company.yaml      ◄── Variáveis da empresa   │
│    └── agents.yaml       ◄── Definição dos agentes  │
├─────────────────────────────────────────────────────┤
│  Factory Pattern                                     │
│    └── Lê YAMLs + Cria agentes dinamicamente        │
├─────────────────────────────────────────────────────┤
│  Agentes Instanciados:                              │
│    ├── Marketing (RAG: data/marketing/)             │
│    ├── Jurídico (RAG: data/juridico/)              │
│    ├── RH (RAG: data/rh/)                           │
│    └── ... (N agentes configurados)                 │
├─────────────────────────────────────────────────────┤
│  Recursos Compartilhados:                           │
│    ├── ChromaDB (vector DB com filtro dept)         │
│    ├── SQLite (memória + sessions)                  │
│    └── Skills Library (shared + por dept)           │
└─────────────────────────────────────────────────────┘
```

### 1.3 Princípios de Design

1. **Configuration over Code**: 90% das customizações via YAML, 10% código Python se necessário
2. **Department Isolation**: Cada agente acessa apenas o conhecimento do seu departamento
3. **Template-Driven**: Prompts reutilizam variáveis globais da empresa
4. **LLM-Assisted**: Documentação otimizada para Claude Code/outros LLMs ajudarem na criação
5. **Zero Boilerplate**: Adicionar agente = copiar bloco YAML + reiniciar API

### 1.4 Fluxo de Uso (Cliente Final)

```
1. Admin recebe pacote Dartha API (Docker/instalador)
2. Edita config/company.yaml com dados da empresa
3. Edita config/agents.yaml (copia templates)
4. Coloca documentos em data/[departamento]/
5. Roda script de ingestão (popula ChromaDB)
6. Inicia API → AgentOS auto-registra todos os agentes
7. Frontend cloud conecta na API local
```

---

## 2. Estrutura de Arquivos e Diretórios

### 2.1 Estrutura Completa

```
dartha-api-v3/
│
├── config/
│   ├── company.yaml              # Variáveis da empresa (nome, descrição, etc)
│   ├── agents.yaml               # Definição de todos os agentes
│   └── agents.example.yaml       # Template completo com exemplos comentados
│
├── data/                         # Knowledge base organizada por departamento
│   ├── marketing/
│   │   ├── campanhas/
│   │   ├── metricas/
│   │   └── branding/
│   ├── juridico/
│   │   ├── contratos/
│   │   ├── compliance/
│   │   └── jurisprudencia/
│   ├── rh/
│   ├── financeiro/
│   ├── tecnologia/
│   ├── vendas/
│   ├── operacao/
│   ├── estrategico/
│   ├── logistica/
│   ├── gestao/
│   ├── contabilidade/
│   ├── compras/
│   └── suporte/
│
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── _base.py              # create_base_agent() - já existe
│   │   ├── _factory.py           # NOVO: Lê YAML e cria agentes
│   │   ├── _config.py            # NOVO: Carrega e valida configs
│   │   └── _templates.py         # NOVO: Funções helper para templates
│   │
│   ├── skills/
│   │   ├── shared/               # Skills usadas por múltiplos agentes
│   │   │   ├── data-analysis/
│   │   │   │   └── SKILL.md
│   │   │   ├── web-research/
│   │   │   │   └── SKILL.md
│   │   │   └── document-analysis/
│   │   │       └── SKILL.md
│   │   │
│   │   ├── marketing/
│   │   │   ├── criar-campanha/
│   │   │   │   └── SKILL.md
│   │   │   ├── analisar-metricas/
│   │   │   │   └── SKILL.md
│   │   │   └── gerar-copy/
│   │   │       └── SKILL.md
│   │   │
│   │   ├── juridico/
│   │   │   ├── revisar-contrato/
│   │   │   │   └── SKILL.md
│   │   │   └── pesquisar-jurisprudencia/
│   │   │       └── SKILL.md
│   │   │
│   │   └── [outros departamentos...]/
│   │
│   ├── config/
│   │   ├── settings.py           # Já existe - adicionar company_name, etc
│   │   └── llm_providers.py      # Modificar get_model() para aceitar model_id
│   │
│   ├── knowledge/
│   │   └── base.py               # Já existe - get_knowledge_base(department)
│   │
│   ├── tools/
│   │   └── dynamic_loader.py     # Já existe - load_dynamic_tools()
│   │
│   └── app.py                    # Modificar: usar factory em vez de imports manuais
│
├── scripts/
│   ├── ingest_knowledge.py       # Script para popular ChromaDB
│   ├── validate_config.py        # NOVO: Valida agents.yaml antes do startup
│   └── generate_skills_catalog.py # NOVO: Gera docs/skills-catalog.md
│
├── docs/
│   ├── quickstart.md             # Já existe
│   ├── agent-creation-guide.md   # NOVO: Guia completo de criação de agentes
│   ├── skills-catalog.md         # NOVO: Catálogo de skills disponíveis
│   ├── deployment-guide.md       # NOVO: Como deployar para cliente
│   └── superpowers/
│       └── specs/
│           └── 2026-03-30-multi-agent-system-design.md  # Este documento
│
├── .env.example                  # Template com todas as variáveis
├── docker-compose.yml            # ChromaDB + API
└── README.md                     # Atualizar com nova estrutura
```

### 2.2 Arquivos de Configuração

#### **`config/company.yaml`**

Arquivo simples com variáveis da empresa que serão interpoladas nos prompts.

```yaml
# Informações da Empresa
company_name: "Minha Empresa"
company_description: "Uma empresa focada em soluções inteligentes."

# Configurações Globais
default_model: "gpt-5.4-mini"
default_temperature: 1.0

# Opcional: Branding (para usar em prompts)
company_values:
  - "Inovação"
  - "Excelência"
  - "Transparência"

company_tone: "profissional e amigável"
```

#### **`config/agents.yaml`**

Arquivo principal que define todos os agentes do sistema.

```yaml
# Variáveis globais (herdadas por todos)
globals:
  company_name: "{{COMPANY_NAME}}"  # Puxa do company.yaml
  company_description: "{{COMPANY_DESCRIPTION}}"
  default_model: "gpt-5.4-mini"

  # Features padrão (podem ser sobrescritas por agente)
  default_features:
    memory: true
    rag: true
    web_search: false
    add_datetime: true
    add_history: true
    num_history_runs: 10
    markdown: true
    debug_mode: false

# Definição dos agentes
agents:
  # ==================== SUPER ADMIN ====================
  - name: "Super Admin Assistant"
    department: null  # ⚡ Sem filtro = acessa TODO o RAG
    model: "gpt-5.4"
    description: "Assistente executivo com visão cross-departamental"

    features:
      memory: true
      rag: true
      web_search: true
      add_history: true
      num_history_runs: 20

    tools:
      - name: "DuckDuckGoTools"
      - name: "SmartPandasTools"
      - name: "FileTools"
        kwargs:
          base_dir: "."
      - name: "PythonTools"
        kwargs:
          base_dir: "tmp/workspace"

    skills:
      - "shared/data-analysis"
      - "shared/web-research"
      - "shared/document-analysis"

    mcps: []

    instructions:
      - "Você é o assistente executivo da {{company_name}}."
      - "{{company_description}}"
      - "Você tem acesso a TODOS os dados da empresa."
      - "Use esse privilégio com responsabilidade."

  # ==================== GENERAL ====================
  - name: "General Assistant"
    department: "geral"
    model: "gpt-5.4-mini"
    description: "Assistente geral para tarefas públicas"

    features:
      memory: true
      rag: false  # ⚡ SEM acesso ao knowledge base
      web_search: true
      add_history: true
      num_history_runs: 10

    tools:
      - name: "DuckDuckGoTools"
      - name: "SmartPandasTools"
      - name: "FileTools"
      - name: "PythonTools"

    skills:
      - "shared/data-analysis"
      - "shared/web-research"

    mcps: []

    instructions:
      - "Você é o assistente geral da {{company_name}}."
      - "{{company_description}}"
      - "Ajuda com tarefas genéricas, pesquisa web e análise de dados."
      - "Você NÃO tem acesso a documentos internos confidenciais."

  # ==================== MARKETING ====================
  - name: "Marketing Assistant"
    department: "marketing"
    model: "gpt-5.4-mini"
    description: "Especialista em campanhas, métricas e estratégia"

    features:
      memory: true
      rag: true
      web_search: true
      add_history: true
      num_history_runs: 15

    tools:
      - name: "DuckDuckGoTools"
      - name: "SmartPandasTools"
      - name: "FileTools"
      - name: "PythonTools"

    skills:
      - "shared/data-analysis"
      - "shared/web-research"
      - "marketing/criar-campanha"
      - "marketing/analisar-metricas"

    mcps: []

    instructions:
      - "Você é o assistente de Marketing da {{company_name}}."
      - "{{company_description}}"
      - "Você é especialista em criar campanhas criativas e analisar métricas."
      - "Você tem acesso exclusivo aos dados de Marketing no RAG."
      - "Use web_search para pesquisar tendências atuais de mercado."

  # ==================== JURÍDICO ====================
  - name: "Juridico Assistant"
    department: "juridico"
    model: "gpt-5.4"  # ⚡ Modelo mais caro/preciso
    description: "Especialista em contratos, compliance e pesquisa jurídica"

    features:
      memory: true
      rag: true
      web_search: true
      add_history: true
      num_history_runs: 20  # Contexto longo para contratos

    tools:
      - name: "DuckDuckGoTools"
      - name: "FileTools"
      # SEM Pandas/Python - não precisa

    skills:
      - "shared/document-analysis"
      - "juridico/revisar-contrato"
      - "juridico/pesquisar-jurisprudencia"

    mcps: []

    instructions:
      - "Você é o assistente Jurídico da {{company_name}}."
      - "{{company_description}}"
      - "Você é especialista em análise de contratos e compliance."
      - "Você tem acesso exclusivo aos documentos jurídicos no RAG."
      - "NUNCA compartilhe informações jurídicas com outros departamentos."
      - "Sempre cite fontes e referências legais nas suas análises."

  # ... (outros departamentos seguem o mesmo padrão)
```

---

## 3. Implementação dos Componentes Principais

### 3.1 Config Loading e Validação (`src/agents/_config.py`)

**Novo arquivo** que carrega e valida configurações de agentes e empresa usando Pydantic.

```python
"""
Carrega e valida configurações de agentes e empresa.
"""
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
import yaml


class AgentFeatures(BaseModel):
    """Features do Agno habilitadas para o agente"""
    memory: bool = True
    rag: bool = True
    web_search: bool = False
    add_datetime: bool = True
    add_history: bool = True
    num_history_runs: int = 10
    markdown: bool = True
    debug_mode: bool = False


class ToolConfig(BaseModel):
    """Configuração de uma tool"""
    name: str
    kwargs: Dict[str, Any] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    """Configuração completa de um agente"""
    name: str
    department: Optional[str] = None  # None = Super Admin (acessa tudo)
    description: str = ""
    model: Optional[str] = None  # None = usa default
    features: AgentFeatures
    tools: List[ToolConfig] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    mcps: List[str] = Field(default_factory=list)
    instructions: List[str] = Field(default_factory=list)

    @validator('skills')
    def validate_skills_exist(cls, skills):
        """Valida se as skills referenciadas existem"""
        skills_dir = Path("src/skills")
        for skill_path in skills:
            full_path = skills_dir / skill_path / "SKILL.md"
            if not full_path.exists():
                raise ValueError(
                    f"Skill não encontrada: {skill_path}\n"
                    f"Esperado em: {full_path}\n"
                    f"Dica: Rode 'python scripts/generate_skills_catalog.py' "
                    f"para ver skills disponíveis"
                )
        return skills


class CompanyConfig(BaseModel):
    """Configuração da empresa"""
    company_name: str
    company_description: str
    default_model: str = "gpt-5.4-mini"
    default_temperature: float = 1.0
    company_values: List[str] = Field(default_factory=list)
    company_tone: str = "profissional e amigável"


class SystemConfig(BaseModel):
    """Configuração completa do sistema"""
    company: CompanyConfig
    agents: List[AgentConfig]


def load_company_config() -> CompanyConfig:
    """Carrega config/company.yaml"""
    config_path = Path("config/company.yaml")
    if not config_path.exists():
        raise FileNotFoundError("config/company.yaml não encontrado")

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    return CompanyConfig(**data)


def load_agents_config() -> List[AgentConfig]:
    """Carrega config/agents.yaml"""
    config_path = Path("config/agents.yaml")
    if not config_path.exists():
        raise FileNotFoundError("config/agents.yaml não encontrado")

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # Merge globals com cada agente
    globals_config = data.get("globals", {})
    default_features = globals_config.get("default_features", {})

    agents = []
    for agent_data in data.get("agents", []):
        # Merge features (agent override > defaults)
        if "features" not in agent_data:
            agent_data["features"] = default_features
        else:
            merged_features = {**default_features, **agent_data["features"]}
            agent_data["features"] = merged_features

        # Model default
        if "model" not in agent_data or agent_data["model"] is None:
            agent_data["model"] = globals_config.get("default_model")

        agents.append(AgentConfig(**agent_data))

    return agents


def interpolate_template(text: str, variables: Dict[str, str]) -> str:
    """Substitui variáveis {{var}} no template"""
    for key, value in variables.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
    return text


def load_system_config() -> SystemConfig:
    """Carrega configuração completa do sistema"""
    company = load_company_config()
    agents = load_agents_config()

    # Interpola variáveis nos prompts
    template_vars = {
        "company_name": company.company_name,
        "company_description": company.company_description,
        "COMPANY_NAME": company.company_name,
        "COMPANY_DESCRIPTION": company.company_description,
    }

    for agent in agents:
        agent.instructions = [
            interpolate_template(instr, template_vars)
            for instr in agent.instructions
        ]

    return SystemConfig(company=company, agents=agents)
```

### 3.2 Agent Factory (`src/agents/_factory.py`)

**Novo arquivo** que cria agentes dinamicamente baseado em configuração YAML.

```python
"""
Factory para criar agentes dinamicamente baseado em configuração YAML.
"""
from typing import List
from pathlib import Path
from agno.agent import Agent
from agno.skills import Skills, LocalSkills

from src.agents._config import load_system_config, AgentConfig
from src.agents._base import create_base_agent
from src.config.llm_providers import get_model
from src.knowledge.base import get_knowledge_base
from src.tools.dynamic_loader import load_dynamic_tools


def create_agent_from_config(agent_config: AgentConfig) -> Agent:
    """
    Cria um agente Agno baseado na configuração YAML.

    Args:
        agent_config: Configuração validada do agente

    Returns:
        Agent instanciado e pronto para uso
    """
    # Resolve modelo (usa config do agente ou default)
    model = get_model(model_id=agent_config.model)

    # Carrega tools dinamicamente
    tools = load_dynamic_tools([t.dict() for t in agent_config.tools])

    # Configura skills
    skills_dir = Path("src/skills")
    skills = Skills(loaders=[LocalSkills(str(skills_dir))])

    # Configura knowledge base com filtro de departamento
    knowledge = None
    if agent_config.features.rag:
        knowledge = get_knowledge_base(
            department=agent_config.department,  # None = sem filtro (Super Admin)
            num_documents=5
        )

    # Cria o agente usando a base existente
    agent = create_base_agent(
        name=agent_config.name,
        user_id="system",  # Pode ser sobrescrito depois
        instructions=agent_config.instructions,
        tools=tools,
        skills=skills,
        knowledge=knowledge,
        model=model,
        markdown=agent_config.features.markdown,
        debug_mode=agent_config.features.debug_mode,
        # Features do Agno
        enable_agentic_memory=agent_config.features.memory,
        add_datetime_to_context=agent_config.features.add_datetime,
        add_history_to_context=agent_config.features.add_history,
        num_history_runs=agent_config.features.num_history_runs,
    )

    return agent


def load_all_agents() -> List[Agent]:
    """
    Carrega todos os agentes definidos em config/agents.yaml

    Returns:
        Lista de agentes instanciados
    """
    system_config = load_system_config()

    agents = []
    for agent_config in system_config.agents:
        try:
            agent = create_agent_from_config(agent_config)
            agents.append(agent)
            print(f"✅ Agente carregado: {agent_config.name} (dept: {agent_config.department or 'admin'})")
        except Exception as e:
            print(f"❌ Erro ao carregar agente {agent_config.name}: {e}")
            raise

    print(f"\n🚀 Total de {len(agents)} agentes carregados com sucesso!")
    return agents
```

### 3.3 Modificações em Arquivos Existentes

#### **`src/config/llm_providers.py`**

Modificar a função `get_model()` para aceitar `model_id` como parâmetro:

```python
def get_model(model_id: str = None):
    """
    Retorna modelo LLM configurado.

    Args:
        model_id: ID específico do modelo (ex: "gpt-5.4", "gpt-5.4-mini")
                 Se None, usa settings.DEFAULT_MODEL_ID
    """
    provider = settings.LLM_PROVIDER
    model_id = model_id or settings.DEFAULT_MODEL_ID

    if provider == "openai":
        from agno.models.openai import OpenAIChat
        return OpenAIChat(id=model_id, api_key=settings.OPENAI_API_KEY)
    elif provider == "anthropic":
        from agno.models.anthropic import Claude
        return Claude(id=model_id, api_key=settings.ANTHROPIC_API_KEY)
    elif provider == "google":
        from agno.models.google import Gemini
        return Gemini(id=model_id, api_key=settings.GOOGLE_API_KEY)
    elif provider == "groq":
        from agno.models.groq import Groq
        return Groq(id=model_id, api_key=settings.GROQ_API_KEY)
    else:
        raise ValueError(f"Provider '{provider}' não suportado")
```

#### **`src/app.py`**

Modificar para usar factory em vez de imports manuais:

```python
from agno.os import AgentOS
from src.agents._factory import load_all_agents
from src.knowledge.base import get_knowledge_base

# Carrega todos os agentes do YAML
agents = load_all_agents()

# Inicializa AgentOS
agent_os = AgentOS(
    agents=agents,
    knowledge=[get_knowledge_base()],  # Knowledge base principal
    tracing=False,
)

app = agent_os.get_app()

# ... resto do código permanece igual
```

---

## 4. Sistema de Skills

### 4.1 Estrutura de uma Skill

Cada skill é uma pasta com um único arquivo `SKILL.md` contendo instruções especializadas.

```
src/skills/
  └── [categoria]/
      └── [nome-da-skill]/
          └── SKILL.md
```

### 4.2 Exemplo Completo: `src/skills/marketing/criar-campanha/SKILL.md`

```markdown
---
name: criar-campanha
description: Cria estratégias e campanhas de marketing baseadas em objetivos e público-alvo
---

# Skill: Criar Campanha de Marketing

Use esta skill quando o usuário pedir para criar, planejar ou estruturar uma campanha de marketing.

## Quando usar

- Usuário pede "crie uma campanha para produto X"
- Quer estratégia de lançamento de produto/serviço
- Precisa de plano de marketing para evento/promoção
- Solicita ideias criativas para divulgação

## Processo

1. **Entenda o objetivo**: Pergunte sobre meta (vendas, awareness, engajamento)
2. **Defina o público-alvo**: Idade, localização, interesses, comportamento
3. **Analise dados disponíveis**: Use o RAG para buscar campanhas anteriores similares
4. **Estruture a campanha**:
   - Mensagem principal (copywriting)
   - Canais (social media, email, ads, etc)
   - Cronograma sugerido
   - Budget estimado (se aplicável)
   - KPIs para medir sucesso
5. **Use web_search** se precisar de referências atuais do mercado
6. **Documente tudo** em formato estruturado (markdown tables)

## Informações que você deve coletar

- Qual produto/serviço?
- Objetivo principal? (ex: aumentar vendas 20%, gerar leads)
- Público-alvo?
- Budget disponível?
- Prazo/duração da campanha?
- Canais preferidos?

## Exemplo de output

### Campanha: [Nome]
**Objetivo:** [Meta clara]
**Público:** [Descrição do target]
**Duração:** [Período]

#### Estratégia
1. Fase 1 - Awareness (semana 1-2)
2. Fase 2 - Consideração (semana 3-4)
3. Fase 3 - Conversão (semana 5-6)

#### Canais e Táticas
| Canal | Ação | Frequência |
|-------|------|------------|
| Instagram | Posts + Stories | 3x/semana |
| Email | Newsletter | 1x/semana |
| Ads | Google + Meta | Diário |

#### KPIs
- Impressões: X
- CTR: Y%
- Conversões: Z

## Best Practices

- Sempre baseie sugestões em dados do RAG quando disponível
- Use exemplos reais de mercado (web search) para validar ideias
- Seja específico em cronogramas e métricas
- Adapte a linguagem ao tom da empresa ({{company_tone}})
```

### 4.3 Skills Compartilhadas: `src/skills/shared/data-analysis/SKILL.md`

```markdown
---
name: data-analysis
description: Análise profunda de dados usando Pandas e Python para insights precisos
---

# Skill: Data Analysis

Use quando precisar analisar planilhas, CSVs, ou fazer cálculos complexos com dados.

## Quando usar

- Usuário envia planilha Excel/CSV
- Pede estatísticas, médias, correlações
- Quer visualizar tendências ou padrões
- Precisa de cálculos financeiros/matemáticos precisos

## Processo

1. **Carregue os dados**:
   - Excel: `create_pandas_dataframe` com `read_excel`
   - CSV: `create_pandas_dataframe` com `read_csv`

2. **Explore os dados**:
   ```python
   df.head()
   df.info()
   df.describe()
   ```

3. **Análise específica**: Use `run_dataframe_operation` ou crie scripts Python

4. **Apresente insights**: Tabelas markdown + explicações claras

## REGRAS CRÍTICAS

- ⚠️ NUNCA use `read_file` para planilhas Excel
- ⚠️ SEMPRE use `engine='openpyxl'` para .xlsx
- ⚠️ Para cálculos complexos, CRIE um script Python (mais confiável que LLM)

## Exemplo de uso

```python
# 1. Carregar Excel
create_pandas_dataframe(
    dataframe_name="vendas",
    create_using_function="read_excel",
    function_parameters={"io": "data.xlsx", "engine": "openpyxl"}
)

# 2. Analisar
run_dataframe_operation(
    dataframe_name="vendas",
    operation="groupby",
    operation_parameters={"by": "regiao"}
)
```
```

### 4.4 Script de Catálogo: `scripts/generate_skills_catalog.py`

```python
"""
Gera documentação automática de todas as skills disponíveis.
Output: docs/skills-catalog.md
"""
from pathlib import Path
import yaml


def scan_skills():
    """Escaneia src/skills/ e extrai metadata"""
    skills_dir = Path("src/skills")
    catalog = {"shared": [], "departamentos": {}}

    for category_dir in skills_dir.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith("_"):
            continue

        category = category_dir.name
        skills_list = []

        for skill_dir in category_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            # Parse frontmatter
            content = skill_md.read_text(encoding='utf-8')
            if content.startswith('---'):
                parts = content.split('---', 2)
                frontmatter = yaml.safe_load(parts[1])

                skills_list.append({
                    "name": frontmatter.get("name", skill_dir.name),
                    "description": frontmatter.get("description", ""),
                    "path": f"{category}/{skill_dir.name}",
                })

        if category == "shared":
            catalog["shared"] = skills_list
        else:
            catalog["departamentos"][category] = skills_list

    return catalog


def generate_markdown(catalog):
    """Gera arquivo markdown do catálogo"""
    md = ["# 📚 Catálogo de Skills Disponíveis\n"]
    md.append("*Auto-gerado - não edite manualmente*\n")

    # Skills compartilhadas
    md.append("## 🌐 Skills Compartilhadas (Shared)\n")
    md.append("Disponíveis para todos os agentes:\n")
    for skill in catalog["shared"]:
        md.append(f"### `{skill['path']}`")
        md.append(f"{skill['description']}\n")

    # Skills por departamento
    md.append("## 🏢 Skills por Departamento\n")
    for dept, skills in sorted(catalog["departamentos"].items()):
        md.append(f"### {dept.upper()}\n")
        for skill in skills:
            md.append(f"- **`{skill['path']}`**: {skill['description']}")
        md.append("")

    return "\n".join(md)


if __name__ == "__main__":
    catalog = scan_skills()
    markdown = generate_markdown(catalog)

    output_path = Path("docs/skills-catalog.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding='utf-8')

    print(f"✅ Catálogo gerado: {output_path}")
    print(f"   - {len(catalog['shared'])} skills compartilhadas")
    print(f"   - {len(catalog['departamentos'])} departamentos")
```

---

## 5. Scripts de Suporte

### 5.1 Script de Ingestão: `scripts/ingest_knowledge.py`

Script completo para ingerir documentos no ChromaDB com auto-detecção de departamentos.

```python
"""
Script de ingestão de documentos no ChromaDB com auto-detecção de departamentos.

Uso:
    python scripts/ingest_knowledge.py                    # Ingere tudo
    python scripts/ingest_knowledge.py --department marketing  # Só marketing
    python scripts/ingest_knowledge.py --clear            # Limpa e re-ingere
"""
import os
import argparse
from pathlib import Path
from typing import List, Dict
import chromadb
from rich.console import Console
from rich.progress import track
from rich.table import Table

from agno.knowledge.embedder.google import GeminiEmbedder
from src.config.settings import settings
from src.tools.file_parser import convert_file_to_text

console = Console()

# ChromaDB config
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "dartha_knowledge")
DATA_DIR = Path("data")


class KnowledgeIngester:
    """Gerencia ingestão de documentos no ChromaDB"""

    def __init__(self):
        self.client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        self.embedder = GeminiEmbedder(
            id="gemini-embedding-2-preview",
            api_key=settings.GOOGLE_API_KEY,
            dimensions=768,
        )

    def get_or_create_collection(self, clear: bool = False):
        """Obtém ou cria a collection no ChromaDB"""
        try:
            if clear:
                console.print(f"[yellow]Limpando collection '{CHROMA_COLLECTION}'...[/yellow]")
                self.client.delete_collection(name=CHROMA_COLLECTION)

            collection = self.client.get_or_create_collection(
                name=CHROMA_COLLECTION,
                metadata={"description": "Dartha Knowledge Base - Multi-department"}
            )
            console.print(f"[green]✓[/green] Collection '{CHROMA_COLLECTION}' pronta")
            return collection
        except Exception as e:
            console.print(f"[red]✗ Erro ao conectar ChromaDB: {e}[/red]")
            console.print("[yellow]Dica: Rode 'docker-compose up -d chroma'[/yellow]")
            raise

    def scan_data_directory(self, department_filter: str = None) -> Dict[str, List[Path]]:
        """Escaneia data/ e organiza por departamento"""
        departments = {}

        if not DATA_DIR.exists():
            console.print(f"[yellow]⚠ Diretório {DATA_DIR} não encontrado[/yellow]")
            return departments

        for dept_dir in DATA_DIR.iterdir():
            if not dept_dir.is_dir():
                continue

            # Pula pastas ocultas ou especiais
            if dept_dir.name.startswith('.') or dept_dir.name.startswith('_'):
                continue

            # Filtro de departamento específico
            if department_filter and dept_dir.name != department_filter:
                continue

            # Coleta todos os arquivos (recursivo)
            files = []
            for ext in ['*.pdf', '*.docx', '*.xlsx', '*.csv', '*.txt', '*.md', '*.pptx']:
                files.extend(dept_dir.rglob(ext))

            if files:
                departments[dept_dir.name] = files

        return departments

    def process_document(self, file_path: Path, department: str) -> Dict:
        """Processa um documento e retorna metadata + conteúdo"""
        try:
            # Converte para texto usando MarkItDown
            content_bytes = file_path.read_bytes()
            text_content = convert_file_to_text(content_bytes, file_path.name)

            if not text_content or len(text_content.strip()) < 50:
                return None  # Documento vazio ou muito pequeno

            # Chunk o conteúdo (500 palavras por chunk)
            chunks = self.chunk_text(text_content, chunk_size=500)

            return {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "department": department,
                "chunks": chunks,
                "num_chunks": len(chunks)
            }
        except Exception as e:
            console.print(f"[red]✗ Erro ao processar {file_path.name}: {e}[/red]")
            return None

    def chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """Divide texto em chunks de ~N palavras"""
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            if len(chunk.strip()) > 100:  # Mínimo 100 chars
                chunks.append(chunk)

        return chunks if chunks else [text]  # Fallback: texto inteiro

    def ingest_documents(self, departments: Dict[str, List[Path]]):
        """Ingere todos os documentos no ChromaDB"""
        collection = self.get_or_create_collection()

        stats = {
            "total_files": 0,
            "total_chunks": 0,
            "errors": 0,
            "by_department": {}
        }

        for department, files in departments.items():
            console.print(f"\n[cyan]📁 Processando departamento: {department}[/cyan]")
            dept_chunks = 0
            dept_files = 0

            for file_path in track(files, description=f"  Ingerindo {department}"):
                result = self.process_document(file_path, department)

                if not result:
                    stats["errors"] += 1
                    continue

                # Adiciona cada chunk no ChromaDB
                for idx, chunk_text in enumerate(result["chunks"]):
                    try:
                        # Gera embedding
                        embedding = self.embedder.get_embedding(chunk_text)

                        # ID único
                        doc_id = f"{department}_{file_path.stem}_{idx}"

                        # Metadata
                        metadata = {
                            "department": department,
                            "file_name": result["file_name"],
                            "file_path": result["file_path"],
                            "chunk_index": idx,
                            "total_chunks": result["num_chunks"]
                        }

                        # Adiciona ao ChromaDB
                        collection.add(
                            ids=[doc_id],
                            embeddings=[embedding],
                            documents=[chunk_text],
                            metadatas=[metadata]
                        )

                        dept_chunks += 1

                    except Exception as e:
                        console.print(f"[red]✗ Erro no chunk {idx} de {file_path.name}: {e}[/red]")
                        stats["errors"] += 1

                dept_files += 1

            stats["total_files"] += dept_files
            stats["total_chunks"] += dept_chunks
            stats["by_department"][department] = {
                "files": dept_files,
                "chunks": dept_chunks
            }

            console.print(f"  [green]✓ {dept_files} arquivos, {dept_chunks} chunks[/green]")

        return stats

    def print_summary(self, stats: Dict):
        """Imprime resumo da ingestão"""
        console.print("\n" + "="*60)
        console.print("[bold green]🎉 Ingestão Concluída![/bold green]\n")

        table = Table(title="Resumo por Departamento")
        table.add_column("Departamento", style="cyan")
        table.add_column("Arquivos", justify="right", style="green")
        table.add_column("Chunks", justify="right", style="yellow")

        for dept, data in stats["by_department"].items():
            table.add_row(dept, str(data["files"]), str(data["chunks"]))

        console.print(table)

        console.print(f"\n[bold]Total:[/bold]")
        console.print(f"  • Arquivos processados: {stats['total_files']}")
        console.print(f"  • Chunks no ChromaDB: {stats['total_chunks']}")
        console.print(f"  • Erros: {stats['errors']}")
        console.print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Ingere conhecimento no ChromaDB")
    parser.add_argument(
        "--department",
        type=str,
        help="Ingere apenas um departamento específico (ex: marketing)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Limpa a collection antes de ingerir"
    )
    args = parser.parse_args()

    console.print("[bold blue]🚀 Dartha Knowledge Ingestion[/bold blue]\n")

    # Inicializa ingester
    ingester = KnowledgeIngester()

    # Escaneia diretórios
    console.print(f"[yellow]Escaneando {DATA_DIR}/...[/yellow]")
    departments = ingester.scan_data_directory(department_filter=args.department)

    if not departments:
        console.print("[red]✗ Nenhum documento encontrado![/red]")
        console.print(f"[yellow]Adicione arquivos em {DATA_DIR}/[departamento]/[/yellow]")
        return

    console.print(f"[green]✓ Encontrados {len(departments)} departamentos[/green]")

    # Ingere documentos
    if args.clear:
        ingester.get_or_create_collection(clear=True)

    stats = ingester.ingest_documents(departments)

    # Resumo
    ingester.print_summary(stats)


if __name__ == "__main__":
    main()
```

### 5.2 Script de Validação: `scripts/validate_config.py`

```python
"""
Valida configuração antes do startup.

Uso:
    python scripts/validate_config.py
"""
from pathlib import Path
from rich.console import Console
from rich.table import Table

from src.agents._config import load_system_config

console = Console()


def validate_config():
    """Valida configuração completa do sistema"""
    console.print("[bold blue]🔍 Validando Configuração[/bold blue]\n")

    errors = []
    warnings = []

    try:
        # Carrega config
        config = load_system_config()

        console.print(f"[green]✓[/green] Empresa: {config.company.company_name}")
        console.print(f"[green]✓[/green] Modelo padrão: {config.company.default_model}")
        console.print(f"[green]✓[/green] Agentes carregados: {len(config.agents)}\n")

        # Tabela de agentes
        table = Table(title="Agentes Configurados")
        table.add_column("Nome", style="cyan")
        table.add_column("Departamento", style="yellow")
        table.add_column("Modelo", style="green")
        table.add_column("RAG", justify="center")
        table.add_column("Tools", justify="right")
        table.add_column("Skills", justify="right")

        for agent in config.agents:
            table.add_row(
                agent.name,
                agent.department or "ADMIN",
                agent.model or config.company.default_model,
                "✓" if agent.features.rag else "✗",
                str(len(agent.tools)),
                str(len(agent.skills))
            )

        console.print(table)

        # Validações específicas
        for agent in config.agents:
            # Verifica se departamento existe
            if agent.features.rag and agent.department:
                dept_path = Path(f"data/{agent.department}")
                if not dept_path.exists():
                    warnings.append(
                        f"Agente '{agent.name}': departamento '{agent.department}' "
                        f"não existe em data/"
                    )

            # Verifica skills duplicadas
            if len(agent.skills) != len(set(agent.skills)):
                warnings.append(f"Agente '{agent.name}': skills duplicadas")

        # Imprime warnings
        if warnings:
            console.print("\n[bold yellow]⚠ Avisos:[/bold yellow]")
            for warn in warnings:
                console.print(f"  • {warn}")

        # Sucesso
        if not errors:
            console.print("\n[bold green]✅ Configuração válida![/bold green]")
            return True

    except Exception as e:
        console.print(f"\n[bold red]✗ Erro na validação:[/bold red]")
        console.print(f"  {str(e)}")
        return False


if __name__ == "__main__":
    success = validate_config()
    exit(0 if success else 1)
```

### 5.3 Modificações no `start.ps1`

```powershell
# start.ps1 - Aprimorado com validação
Write-Host "🚀 Iniciando Dartha API V3..." -ForegroundColor Blue

# Valida configuração antes de iniciar
Write-Host "`n📋 Validando configuração..." -ForegroundColor Yellow
python scripts/validate_config.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Configuração inválida. Corrija os erros antes de continuar." -ForegroundColor Red
    exit 1
}

# Verifica ChromaDB
Write-Host "`n🔍 Verificando ChromaDB..." -ForegroundColor Yellow
docker-compose ps chroma | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠ ChromaDB não está rodando. Iniciando..." -ForegroundColor Yellow
    docker-compose up -d chroma
    Start-Sleep -Seconds 3
}

# Inicia API
Write-Host "`n✨ Iniciando servidor..." -ForegroundColor Green
uvicorn src.app:app --host 0.0.0.0 --port 7777 --reload
```

---

## 6. Documentação para Usuário Final

### 6.1 Guia de Criação de Agentes (`docs/agent-creation-guide.md`)

Conteúdo completo do documento:

#### **Início Rápido (3 passos)**

```markdown
## Início Rápido (3 passos)

### 1. Copie um template
Abra `config/agents.yaml` e copie o bloco de exemplo mais similar ao que você precisa.

### 2. Personalize
Edite apenas o que precisa mudar:
- `name`: Nome do agente
- `department`: Nome do departamento (deve existir pasta em `data/`)
- `instructions`: O que o agente deve fazer

### 3. Reinicie
```bash
.\start.ps1
```

Pronto! Seu agente está disponível na API.
```

#### **Anatomia de um Agente**

```yaml
- name: "Nome do Agente"              # Como aparece na API
  department: "nome_departamento"     # Pasta em data/ (ou null para admin)
  description: "Descrição curta"      # Opcional
  model: "gpt-4o-mini"               # Opcional (usa default se omitido)

  features:                           # Liga/desliga recursos do Agno
    memory: true                      # Memória de longo prazo
    rag: true                         # Busca no vector DB
    web_search: false                 # Pesquisa na internet
    add_datetime: true                # Adiciona data/hora ao contexto
    add_history: true                 # Mantém histórico de conversas
    num_history_runs: 10              # Quantas mensagens guardar
    markdown: true                    # Responde em markdown
    debug_mode: false                 # Modo debug (verbose)

  tools:                              # Ferramentas disponíveis
    - name: "DuckDuckGoTools"         # Pesquisa web
    - name: "SmartPandasTools"        # Análise de dados
    - name: "FileTools"               # Leitura de arquivos
      kwargs:
        base_dir: "."
    - name: "PythonTools"             # Executa scripts Python
      kwargs:
        base_dir: "tmp/workspace"

  skills:                             # Habilidades especializadas
    - "shared/data-analysis"
    - "marketing/criar-campanha"
    - "marketing/analisar-metricas"

  mcps: []                            # Integrações externas (avançado)

  instructions:                       # Prompt do agente
    - "Você é o assistente de {{company_name}}."
    - "Você especializa em X, Y e Z."
    - "Regras importantes..."
```

#### **Recursos Disponíveis**

**Features (Liga/Desliga)**

| Feature | O que faz | Quando usar |
|---------|-----------|-------------|
| `memory: true` | Lembra de conversas anteriores do usuário | Sempre (exceto bots simples) |
| `rag: true` | Busca em documentos do departamento | Quando precisa de conhecimento interno |
| `web_search: true` | Pesquisa na internet com DuckDuckGo | Para info atualizada/externa |
| `add_datetime: true` | Sabe data e hora atual | Útil para relatórios, agendamentos |
| `add_history: true` | Mantém contexto da conversa | Sempre (melhora qualidade) |
| `num_history_runs: N` | Quantas msgs antigas guardar | 10-15 normal, 20+ para contexto longo |
| `markdown: true` | Formata respostas em markdown | Sempre (melhor legibilidade) |
| `debug_mode: true` | Logs verbosos de execução | Só para desenvolvimento |

**Tools (Ferramentas)**

| Tool | Capacidade | Exemplo de uso |
|------|-----------|----------------|
| `DuckDuckGoTools` | Pesquisa na web | "Pesquise tendências de marketing 2026" |
| `SmartPandasTools` | Análise de planilhas/dados | "Analise esta planilha de vendas" |
| `FileTools` | Lê arquivos locais | "Leia o contrato.pdf" |
| `PythonTools` | Executa scripts Python | "Calcule juros compostos com precisão" |

⚠️ **Importante:** Quanto mais tools, mais "distraído" o agente pode ficar. Dê apenas o necessário.

**Skills (Habilidades)**

Skills são comportamentos especializados. Veja catálogo completo:
```bash
python scripts/generate_skills_catalog.py
cat docs/skills-catalog.md
```

Para adicionar skill ao agente: `"categoria/nome-da-skill"`

Exemplos:
- `"shared/data-analysis"` - Todos podem usar
- `"marketing/criar-campanha"` - Só marketing
- `"juridico/revisar-contrato"` - Só jurídico

**Models (Modelos)**

| Modelo | Custo | Velocidade | Quando usar |
|--------|-------|-----------|-------------|
| `gpt-5.4-nano` | 💰 Barato | ⚡ Muito rápido | Bots FAQ, tarefas simples |
| `gpt-5.4-mini` | 💰💰 Econômico | ⚡ Rápido | **RECOMENDADO** - padrão |
| `gpt-5.4` | 💰💰💰 Caro | 🐢 Moderado | Tarefas complexas, estratégia |

**Dica:** Use o padrão (`gpt-5.4-mini`) e só sobrescreva se realmente precisar.

#### **Tipos de Agentes (Templates)**

**🤖 Agente Completo (Super Agent)**

Quando usar: Departamentos que precisam de todos os recursos.

```yaml
- name: "Tech Lead Assistant"
  department: "tecnologia"
  model: "gpt-4o-mini"
  features:
    memory: true
    rag: true
    web_search: true
    add_datetime: true
    add_history: true
    num_history_runs: 15
  tools:
    - name: "DuckDuckGoTools"
    - name: "SmartPandasTools"
    - name: "FileTools"
    - name: "PythonTools"
  skills:
    - "shared/data-analysis"
    - "shared/web-research"
    - "tecnologia/code-review"
  instructions:
    - "Você é o Tech Lead da {{company_name}}."
    - "Especialista em arquitetura, debugging e otimização."
```

**🎯 Agente Especializado (Focused)**

Quando usar: Tarefas específicas, sem distrações.

```yaml
- name: "Juridico Assistant"
  department: "juridico"
  model: "gpt-4o"  # Mais caro, mas precisão é crítica
  features:
    memory: true
    rag: true
    web_search: true
    add_history: true
    num_history_runs: 20  # Contexto longo (contratos)
  tools:
    - name: "DuckDuckGoTools"
    - name: "FileTools"
    # SEM Pandas/Python - não precisa
  skills:
    - "shared/document-analysis"
    - "juridico/revisar-contrato"
    - "juridico/pesquisar-jurisprudencia"
  instructions:
    - "Você é o assistente Jurídico da {{company_name}}."
    - "NUNCA invente jurisprudência - sempre busque fontes."
    - "Cite leis e artigos específicos."
```

**🤷 Agente Minimalista (Simple Bot)**

Quando usar: FAQ, tarefas repetitivas simples.

```yaml
- name: "FAQ Bot"
  department: "suporte"
  model: "gpt-3.5-turbo"  # Bem barato
  features:
    memory: false  # Sem memória = mais rápido
    rag: true      # Só busca no FAQ
    web_search: false
    add_history: false
  tools: []  # ZERO tools
  skills:
    - "suporte/responder-faq"
  instructions:
    - "Você responde perguntas frequentes da {{company_name}}."
    - "Se não souber, diga: 'Vou transferir para um atendente humano.'"
```

**👑 Super Admin (Acessa Tudo)**

Quando usar: CEO, gestores que precisam visão cross-departamento.

```yaml
- name: "Super Admin Assistant"
  department: null  # ⚡ Sem filtro = vê TODO o RAG
  model: "gpt-4o"
  features:
    memory: true
    rag: true
    web_search: true
  tools:
    - name: "DuckDuckGoTools"
    - name: "SmartPandasTools"
    - name: "FileTools"
    - name: "PythonTools"
  skills:
    - "shared/data-analysis"
    - "shared/web-research"
  instructions:
    - "Você é o assistente executivo da {{company_name}}."
    - "Você tem acesso a TODOS os dados da empresa."
    - "Use esse privilégio com responsabilidade."
```

**🌐 General Assistant (Sem RAG)**

Quando usar: Tarefas genéricas sem dados sensíveis.

```yaml
- name: "General Assistant"
  department: "geral"
  model: "gpt-4o-mini"
  features:
    memory: true
    rag: false  # ⚡ SEM acesso a documentos internos
    web_search: true
  tools:
    - name: "DuckDuckGoTools"
    - name: "SmartPandasTools"
    - name: "FileTools"
    - name: "PythonTools"
  skills:
    - "shared/data-analysis"
    - "shared/web-research"
  instructions:
    - "Você é o assistente geral da {{company_name}}."
    - "Ajuda com tarefas genéricas e pesquisa web."
    - "Você NÃO tem acesso a documentos confidenciais."
```

#### **Usando Claude Code para Criar Agentes**

**Método 1: Prompt Direto**
```
Crie um novo agente para o departamento de Compras
com as seguintes características:
- Deve analisar cotações de fornecedores
- Precisa acessar planilhas e documentos
- Deve pesquisar preços na web
- Use o documento docs/agent-creation-guide.md como referência
```

**Método 2: Copiar e Modificar**
```
Copie o agente de Marketing e adapte para Recursos Humanos:
- Mude o nome e departamento
- Adicione skills de RH
- Ajuste as instruções
```

**Método 3: Template Customizado**
```
Crie um agente minimalista para Atendimento ao Cliente:
- Modelo econômico
- Só FAQ do RAG
- Sem tools complexas
- Histórico curto (5 mensagens)
```

#### **Checklist de Validação**

Antes de finalizar seu agente:

- [ ] Nome é descritivo e único?
- [ ] Department existe como pasta em `data/`?
- [ ] Features fazem sentido para o caso de uso?
- [ ] Tools são realmente necessárias?
- [ ] Skills existem? (rode `python scripts/generate_skills_catalog.py`)
- [ ] Instructions são claras e específicas?
- [ ] Model escolhido balanceia custo x qualidade?

#### **Troubleshooting**

**❌ Erro: "Skill não encontrada"**
- **Solução:** Verifique se a skill existe em `src/skills/[path]/SKILL.md`

**❌ Erro: "Department 'X' não tem documentos"**
- **Solução:**
  1. Crie pasta `data/X/`
  2. Adicione documentos
  3. Rode `python scripts/ingest_knowledge.py`

**❌ Agente não aparece na API**
- **Solução:** Reinicie o servidor (`.\start.ps1`)

**❌ Agente vê documentos de outro departamento**
- **Solução:** Verifique se `department` está correto no YAML (não pode ser vazio/nulo a menos que seja Super Admin)

### 6.2 Guia de Deployment (`docs/deployment-guide.md`)

Conteúdo completo do documento:

#### **Preparação do Pacote**

**Estrutura Limpa:**
```
dartha-api-v3/
├── config/
│   ├── company.yaml
│   └── agents.yaml
├── data/                    # Cliente adiciona documentos aqui
├── src/
├── scripts/
├── .env.example
├── docker-compose.yml
├── start.ps1
└── README.md
```

**Checklist Pré-Deploy:**
- [ ] `.env.example` atualizado com todas as variáveis necessárias
- [ ] `config/agents.example.yaml` com templates comentados
- [ ] Documentação em `docs/` completa
- [ ] Script de validação funcional: `scripts/validate_config.py`
- [ ] ChromaDB limpo (sem dados de testes)

#### **Instalação no Cliente**

**Requisitos:**
- Python 3.13+
- Docker (para ChromaDB)
- uv (gerenciador Python)

**Passo a Passo:**

1. **Copie os arquivos para o servidor do cliente**

2. **Configure variáveis de ambiente**
```bash
cp .env.example .env
# Edite .env com as API keys do cliente
```

3. **Configure a empresa**
```bash
# Edite config/company.yaml
company_name: "Acme Corp"
company_description: "Líder em soluções X"
```

4. **Configure os agentes**
```bash
# Edite config/agents.yaml
# Use os templates fornecidos
```

5. **Adicione documentos**
```bash
# Cliente coloca arquivos em data/[departamento]/
data/
  marketing/
    - campanha-2024.pdf
    - metricas.xlsx
  juridico/
    - contrato-padrao.docx
```

6. **Rode a ingestão**
```bash
python scripts/ingest_knowledge.py
```

7. **Valide a configuração**
```bash
python scripts/validate_config.py
```

8. **Inicie o sistema**
```bash
.\start.ps1
```

9. **Teste**
```
http://localhost:7777/docs
```

#### **Manutenção**

**Adicionar Novo Departamento:**
1. Crie pasta `data/[nome]/`
2. Adicione documentos
3. Edite `config/agents.yaml` - adicione agente
4. Rode `python scripts/ingest_knowledge.py`
5. Reinicie

**Atualizar Documentos:**
1. Adicione/remova arquivos em `data/`
2. Rode `python scripts/ingest_knowledge.py --clear`
3. Não precisa reiniciar API

**Trocar Modelo de IA:**
1. Edite `config/agents.yaml`
2. Mude `model:` do agente específico
3. Reinicie

#### **Troubleshooting**

**ChromaDB não conecta:**
```bash
docker-compose up -d chroma
docker-compose logs chroma
```

**API não inicia:**
```bash
# Veja logs
cat error.log

# Valide config
python scripts/validate_config.py
```

### 6.3 Catálogo de Skills (`docs/skills-catalog.md`)

Documento auto-gerado pelo script `generate_skills_catalog.py` contendo:
- Skills Compartilhadas (Shared)
- Skills por Departamento
- Descrição e path de cada skill

---

## 7. Casos de Uso Práticos

### 7.1 Exemplo: TechVibe Solutions

Empresa fictícia de tecnologia com 5 departamentos configurados:
- Super Admin (acessa tudo)
- General (sem RAG)
- Dev Assistant (tecnologia)
- Sales Assistant (vendas)
- Marketing Assistant (marketing)
- HR Assistant (rh)
- Finance Assistant (financeiro)

Cada agente configurado com:
- Tools específicas para sua função
- Skills relevantes
- Instruções customizadas
- Modelo adequado ao caso de uso (GPT-5.4 para críticos, GPT-5.4-mini para padrão)

### 7.2 Fluxo Completo: Do Zero ao Deploy

```bash
# 1. Cliente recebe o pacote
dartha-api-v3.zip

# 2. Descompacta e configura
cd dartha-api-v3
cp .env.example .env
# Edita .env com API keys

# 3. Personaliza para a empresa
code config/company.yaml

# 4. Configura agentes
code config/agents.yaml

# 5. Adiciona documentos
# Arrasta arquivos para data/[departamento]/

# 6. Ingere conhecimento
docker-compose up -d chroma
python scripts/ingest_knowledge.py

# 7. Valida
python scripts/validate_config.py

# 8. Inicia
.\start.ps1

# 9. Testa
# Acessa http://localhost:7777/docs

# 10. Produção!
```

---

## 8. Isolamento de Conhecimento

### 8.1 Como Funciona o Isolamento

O isolamento é garantido em nível de vector DB (ChromaDB):

1. **Script de ingestão** marca cada documento com metadata:
   ```python
   data/marketing/doc.pdf → {"department": "marketing"}
   data/juridico/contrato.docx → {"department": "juridico"}
   ```

2. **Factory cria agente** com knowledge filtrado:
   ```python
   # Agente de Marketing
   knowledge = get_knowledge_base(department="marketing")
   # Só busca docs com department == "marketing"
   ```

3. **Busca RAG** aplica filtro automaticamente:
   ```python
   # Código já implementado em src/knowledge/base.py
   def search(self, query: str, limit: int = 5, filters=None):
       if self._department:
           filters = {"department": {"$eq": self._department}}
       return super().search(query=query, limit=limit, filters=filters)
   ```

### 8.2 Tipos de Acesso

**Super Admin Assistant:**
- `department: null` → Acessa TODO o RAG (sem filtro)
- Para CEO/Gestores que precisam visão cross-departamento

**General Assistant:**
- `rag: false` → SEM acesso ao knowledge base
- Para tarefas genéricas/públicas sem dados sensíveis

**Agentes Departamentais:**
- `department: "marketing"` → Só vê docs de marketing
- `department: "juridico"` → Só vê docs de jurídico
- Isolamento forçado no código (não depende do prompt)

---

## 9. Checklist de Implementação

### 9.1 Novos Arquivos a Criar

- [ ] `config/company.yaml`
- [ ] `config/agents.yaml`
- [ ] `config/agents.example.yaml` (com exemplos comentados)
- [ ] `src/agents/_config.py`
- [ ] `src/agents/_factory.py`
- [ ] `src/agents/_templates.py` (se necessário)
- [ ] `scripts/validate_config.py`
- [ ] `scripts/generate_skills_catalog.py`
- [ ] `docs/agent-creation-guide.md`
- [ ] `docs/deployment-guide.md`
- [ ] Skills em `src/skills/`:
  - [ ] `shared/data-analysis/SKILL.md`
  - [ ] `shared/web-research/SKILL.md`
  - [ ] `shared/document-analysis/SKILL.md`
  - [ ] `marketing/criar-campanha/SKILL.md`
  - [ ] `marketing/analisar-metricas/SKILL.md`
  - [ ] `juridico/revisar-contrato/SKILL.md`
  - [ ] `juridico/pesquisar-jurisprudencia/SKILL.md`
  - [ ] (outros departamentos conforme necessário)

### 9.2 Arquivos a Modificar

- [ ] `src/config/llm_providers.py` - adicionar parâmetro `model_id` em `get_model()`
- [ ] `src/app.py` - usar `load_all_agents()` da factory
- [ ] `scripts/ingest_knowledge.py` - aprimorar (já existe, melhorar)
- [ ] `start.ps1` - adicionar validação
- [ ] `README.md` - atualizar com nova estrutura

### 9.3 Arquivos a Manter (Sem Alteração)

- ✅ `src/agents/_base.py` - `create_base_agent()` permanece igual
- ✅ `src/knowledge/base.py` - `DarthaHttpChromaDb` já tem filtro de department
- ✅ `src/tools/dynamic_loader.py` - `load_dynamic_tools()` já funciona
- ✅ `src/config/settings.py` - pode adicionar campos se necessário, mas não obrigatório

---

## 10. Validações e Testes

### 10.1 Testes de Validação

**Config Loader:**
- [ ] Carrega `company.yaml` corretamente
- [ ] Carrega `agents.yaml` e aplica defaults
- [ ] Interpola variáveis `{{company_name}}` nos prompts
- [ ] Valida que skills referenciadas existem
- [ ] Rejeita configs inválidas com mensagens claras

**Factory:**
- [ ] Cria agentes com todas as features configuradas
- [ ] Aplica modelo correto (específico ou default)
- [ ] Carrega tools dinamicamente
- [ ] Configura RAG com filtro de departamento correto
- [ ] Super Admin (department=null) acessa todo o RAG
- [ ] General Assistant (rag=false) não tem knowledge base

**Isolamento:**
- [ ] Marketing Agent só vê docs de marketing
- [ ] Jurídico Agent só vê docs de jurídico
- [ ] Super Admin vê todos os docs
- [ ] General Assistant não vê nenhum doc

### 10.2 Testes de Integração

- [ ] `start.ps1` valida config antes de iniciar
- [ ] AgentOS registra todos os agentes corretamente
- [ ] Frontend consegue listar todos os agentes
- [ ] Cada agente responde com seu contexto correto
- [ ] Script de ingestão marca documentos corretamente
- [ ] Catálogo de skills é gerado sem erros

---

## 11. Próximos Passos

### 11.1 Após Implementação

1. **Testar localmente** com exemplo TechVibe
2. **Criar package** de distribuição para clientes
3. **Documentar processo** de customização
4. **Criar vídeo tutorial** (opcional)

### 11.2 Melhorias Futuras (Fora do Escopo Atual)

- Interface web para editar `agents.yaml` (admin UI)
- Versionamento de configs (Git integration)
- Metrics dashboard por agente
- A/B testing de prompts
- Auto-tuning de skills baseado em feedback

---

## 12. Conclusão

Este design fornece uma arquitetura escalável, configurável e fácil de usar para criar sistemas multi-agente com isolamento de conhecimento por departamento. A abordagem baseada em YAML + Factory Pattern permite que empresas repliquem e personalizem agentes sem conhecimento profundo de Python, enquanto mantém flexibilidade total para casos avançados.

**Principais Ganhos:**
- ✅ Tempo de setup reduzido de horas para minutos
- ✅ Zero código Python para 90% dos casos de uso
- ✅ Isolamento de dados garantido em nível de infraestrutura
- ✅ Documentação otimizada para uso assistido por LLMs
- ✅ Manutenção simplificada (tudo centralizado em YAMLs)

**Status:** Aprovado para implementação via skill `writing-plans`.
