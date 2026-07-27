# Agent Creation Guide

Complete guide to creating, configuring, and deploying agents in the Dartha system.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Understanding YAML Structure](#understanding-yaml-structure)
3. [Agent Configuration Reference](#agent-configuration-reference)
4. [Agent Types & Examples](#agent-types--examples)
5. [Skills System](#skills-system)
6. [Common Patterns](#common-patterns)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Topics](#advanced-topics)

---

## Quick Start

Get up and running with your first agent in 3 steps.

### Step 1: Create Agent YAML Configuration

Create a new agent configuration file in `config/agents.yaml`:

```yaml
agents:
  - name: "My Custom Agent"
    department: "engineering"
    model: "gpt-4o-mini"
    description: "A specialized agent for custom tasks"

    features:
      memory: true
      rag: true
      web_search: false
      add_history: true
      num_history_runs: 10

    tools:
      - name: "DuckDuckGoTools"
      - name: "FileTools"

    skills:
      - "shared/data-analysis"

    instructions:
      - "You are a helpful assistant for engineering tasks."
```

### Step 2: Define Agent Capabilities

Add tools and skills your agent needs:

```yaml
tools:
  - name: "SmartPandasTools"
    kwargs:
      base_dir: "data/"

  - name: "PythonTools"
    kwargs:
      base_dir: "tmp/workspace"

skills:
  - "shared/web-research"
  - "engineering/code-analysis"
```

### Step 3: Test Agent Initialization

```bash
# Validate YAML syntax
python -m yaml config/agents.yaml

# Test agent loading
python -c "from src.agent import Agent; agent = Agent.from_config('My Custom Agent')"
```

---

## Understanding YAML Structure

The agent configuration uses a hierarchical YAML structure with globals and per-agent settings.

### Overall Structure

```yaml
# Global configuration (inherited by all agents)
globals:
  company_name: "My Company"
  default_model: "gpt-4o-mini"
  default_features:
    memory: true
    rag: true
    web_search: false
    add_datetime: true
    add_history: true
    num_history_runs: 10
    markdown: true
    debug_mode: false

# Individual agent definitions
agents:
  - name: "Agent Name"
    # agent configuration here

  - name: "Another Agent"
    # another agent configuration
```

### Configuration Hierarchy

Settings are applied in this order (top to bottom = least to most specific):

1. **Global defaults** - Applied to all agents
2. **Agent-level overrides** - Override globals for specific agent
3. **Runtime parameters** - Override everything at runtime

Example:

```yaml
globals:
  default_model: "gpt-4o-mini"  # Applies to all agents

agents:
  - name: "Fast Agent"
    model: "gpt-4o-mini"        # Uses global model

  - name: "Smart Agent"
    model: "gpt-4o"             # Overrides global model for this agent only
```

### Variable Interpolation

Use template variables with `{{VARIABLE_NAME}}` syntax:

```yaml
globals:
  company_name: "{{COMPANY_NAME}}"
  company_description: "{{COMPANY_DESCRIPTION}}"

agents:
  - name: "Company Assistant"
    instructions:
      - "You work for {{company_name}}"
      - "About us: {{company_description}}"
```

Variables are sourced from:
1. `config/company.yaml`
2. Environment variables
3. Runtime configuration

---

## Agent Configuration Reference

Complete reference for all configuration fields.

### Required Fields

#### `name` (string)
Unique identifier for the agent. Used for referencing and logging.

```yaml
name: "Marketing Assistant"
```

- Must be unique across all agents
- Used as agent ID in logs
- User-friendly name for UI display

#### `description` (string)
Brief description of agent purpose and capabilities.

```yaml
description: "Specializes in marketing campaigns, metrics analysis, and market research"
```

- Max 200 characters recommended
- Shown in agent selection UI
- Used for agent discovery/routing

#### `model` (string)
LLM model to use for this agent.

```yaml
model: "gpt-4o"  # or "gpt-4o-mini" for cost savings
```

Options:
- `gpt-4o` - Latest GPT-4 Omni (slowest, most capable)
- `gpt-4o-mini` - Smaller, faster, more cost-effective
- `inherit` - Use global default model

### Optional Fields

#### `department` (string or null)
Organizational department for RAG filtering and access control.

```yaml
department: "marketing"        # Agent accesses marketing docs in RAG
department: "geral"            # General public agent
department: null               # Super admin - accesses ALL docs
```

Special values:
- `null` - Super admin mode, full RAG access
- `"geral"` - General/public agent
- Custom department names - Match your organization structure

#### `features` (object)
Feature flags controlling agent capabilities.

```yaml
features:
  memory: true              # Persistent conversation memory
  rag: true                # Access to document knowledge base
  web_search: false        # Internet search capability
  add_datetime: true       # Include current date/time in context
  add_history: true        # Include conversation history
  num_history_runs: 10     # Number of previous interactions to include
  markdown: true           # Format responses in Markdown
  debug_mode: false        # Enable debug logging
```

Feature explanations:

- **memory**: Enable conversation context persistence. Allows agent to remember previous interactions.
  - Default: `true`
  - Use `false` for stateless agents

- **rag**: Enable Retrieval Augmented Generation. Access department-specific documents.
  - Default: `true` (inherited from globals)
  - Set to `false` for agents without doc access
  - Respects `department` field for filtering

- **web_search**: Enable internet search capability via search API.
  - Default: `false` (inherited from globals)
  - Useful for research, news, market analysis
  - May increase latency

- **add_datetime**: Automatically include current date/time in system prompt.
  - Default: `true`
  - Useful for time-sensitive tasks

- **add_history**: Include previous conversation turns in context.
  - Default: `true`
  - Improves context awareness
  - Increases token usage

- **num_history_runs**: Number of previous conversation turns to include.
  - Default: `10` (inherited from globals)
  - Higher = more context, more tokens
  - Set to `0` to disable history

- **markdown**: Format agent responses in Markdown.
  - Default: `true`
  - Improves readability and formatting

- **debug_mode**: Enable verbose debug logging.
  - Default: `false`
  - Use for troubleshooting agent behavior

#### `tools` (array of objects)
External tools/capabilities available to the agent.

```yaml
tools:
  - name: "DuckDuckGoTools"       # Web search
  - name: "SmartPandasTools"      # Data analysis
  - name: "FileTools"             # File operations
    kwargs:
      base_dir: "."
  - name: "PythonTools"           # Code execution
    kwargs:
      base_dir: "tmp/workspace"
```

Available tools:

| Tool | Purpose | When to Use |
|------|---------|------------|
| `DuckDuckGoTools` | Web search without API keys | Research, market analysis, news |
| `SmartPandasTools` | Data analysis with pandas | Data processing, analytics |
| `FileTools` | File read/write operations | Document processing, reports |
| `PythonTools` | Execute Python code | Data processing, calculations |

Tool configuration:

- `name`: Tool class name (must match implementation)
- `kwargs` (optional): Tool-specific configuration
  - `base_dir`: Working directory for file operations

#### `skills` (array of strings)
Custom skills/capabilities to enable.

```yaml
skills:
  - "shared/data-analysis"        # Shared skill
  - "shared/web-research"
  - "marketing/campaign-creation" # Department-specific skill
  - "marketing/metrics-analysis"
```

Skills are referenced by path:
- `shared/` - Available to all agents
- `{department}/` - Department-specific skills
- Skills provide domain-specific knowledge and workflows

#### `mcps` (array)
Model Context Protocol servers to connect.

```yaml
mcps:
  - "http://localhost:3000"  # Local MCP server
  - "https://api.example.com/mcp"
```

MCPs provide extended capabilities through standard protocol.

#### `instructions` (array of strings)
Custom system instructions for the agent.

```yaml
instructions:
  - "You are the executive assistant at {{company_name}}"
  - "{{company_description}}"
  - "Prioritize accuracy and professional communication"
  - "Always cite sources when using RAG documents"
```

Instructions:
- Applied as system prompt context
- Executed in order (first to last)
- Support variable interpolation
- Keep concise and specific

### Default Feature Configuration

Located in `globals.default_features`:

```yaml
globals:
  default_features:
    memory: true
    rag: true
    web_search: false
    add_datetime: true
    add_history: true
    num_history_runs: 10
    markdown: true
    debug_mode: false
```

All agents inherit these defaults unless overridden.

---

## Agent Types & Examples

Common agent configurations for different use cases.

### Type 1: Super Admin Agent

Full system access with all capabilities.

```yaml
agents:
  - name: "Executive Assistant"
    department: null              # null = access all RAG documents
    model: "gpt-4o"               # Use most capable model
    description: "Executive assistant with cross-departmental access"

    features:
      memory: true
      rag: true                   # Full RAG access (no department filter)
      web_search: true            # Can research external info
      add_history: true
      num_history_runs: 20        # More history for complex tasks

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

    instructions:
      - "You are the executive assistant for {{company_name}}"
      - "{{company_description}}"
      - "You have access to all company data and documents"
      - "Handle sensitive information with appropriate discretion"
      - "When reporting, always cite data sources"
```

Use cases:
- Executive dashboards
- Company-wide analysis
- Strategic planning
- Cross-departmental coordination

### Type 2: Department Specialist Agent

Limited access to specific department documents.

```yaml
agents:
  - name: "Marketing Specialist"
    department: "marketing"       # Access only marketing RAG docs
    model: "gpt-4o-mini"          # Cost-effective model
    description: "Expert in campaigns, metrics, and market research"

    features:
      memory: true
      rag: true                   # Limited to marketing department
      web_search: true            # Research market trends
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
      - "marketing/campaign-creation"
      - "marketing/metrics-analysis"

    instructions:
      - "You are the marketing specialist assistant"
      - "Specialize in campaign strategy, metrics analysis, and market research"
      - "Access to marketing department documents"
      - "Always base recommendations on data"
```

Use cases:
- Department-specific tasks
- Restricted data access
- Role-based workflows
- Cost-optimized operations

### Type 3: General Public Agent

Minimal capabilities for external/public interactions.

```yaml
agents:
  - name: "Public Information Agent"
    department: "geral"           # No sensitive data access
    model: "gpt-4o-mini"
    description: "Answers general questions about the company"

    features:
      memory: false               # No persistent context
      rag: false                  # No internal document access
      web_search: true            # Can search public info
      add_history: false
      num_history_runs: 0

    tools:
      - name: "DuckDuckGoTools"

    skills:
      - "shared/web-research"

    instructions:
      - "You are a public information assistant for {{company_name}}"
      - "Provide general information about the company"
      - "Do NOT share internal documents or confidential information"
      - "Direct sensitive inquiries to official company channels"
```

Use cases:
- Public-facing chatbots
- Website assistance
- Customer support
- Limited liability interactions

### Type 4: Research Agent

Specialized for data gathering and analysis.

```yaml
agents:
  - name: "Research Analyst"
    department: "research"
    model: "gpt-4o"
    description: "Conducts research, analysis, and report generation"

    features:
      memory: true
      rag: true
      web_search: true
      add_datetime: true
      add_history: true
      num_history_runs: 20       # Extended history for complex research
      markdown: true

    tools:
      - name: "DuckDuckGoTools"
      - name: "SmartPandasTools"
      - name: "FileTools"
        kwargs:
          base_dir: "reports/"
      - name: "PythonTools"
        kwargs:
          base_dir: "tmp/research"

    skills:
      - "shared/data-analysis"
      - "shared/web-research"
      - "shared/document-analysis"
      - "research/statistical-analysis"
      - "research/report-writing"

    instructions:
      - "You are a research analyst"
      - "Conduct thorough, evidence-based analysis"
      - "Use multiple sources and cross-reference findings"
      - "Generate comprehensive reports with citations"
      - "Include methodology and limitations"
```

Use cases:
- Market research
- Data analysis projects
- Report generation
- Competitive intelligence

### Type 5: Development/Operations Agent

Technical tools for engineering tasks.

```yaml
agents:
  - name: "DevOps Assistant"
    department: "engineering"
    model: "gpt-4o-mini"
    description: "Assists with deployment, monitoring, and infrastructure"

    features:
      memory: true
      rag: true                  # Access eng docs
      web_search: false
      add_history: true
      num_history_runs: 10
      debug_mode: false

    tools:
      - name: "SmartPandasTools"
      - name: "FileTools"
        kwargs:
          base_dir: "."
      - name: "PythonTools"
        kwargs:
          base_dir: "tmp/devops"

    skills:
      - "shared/data-analysis"
      - "engineering/devops"
      - "engineering/monitoring"

    instructions:
      - "You are a DevOps engineering assistant"
      - "Focus on reliability, security, and efficiency"
      - "Always create backups before infrastructure changes"
      - "Document all changes and post to runbooks"
```

Use cases:
- Infrastructure management
- Deployment automation
- System monitoring
- Incident response

---

## Skills System

Skills provide specialized knowledge and workflows to agents.

### Understanding Skills

Skills are reusable capability modules that:
- Encapsulate domain-specific knowledge
- Provide step-by-step workflows
- Can be shared across agents
- Improve consistency and quality

### Skill Naming Convention

```
{scope}/{capability}

scope:
  - shared/     - Available to all agents
  - {dept}/     - Department-specific

capability:
  - data-analysis
  - web-research
  - document-analysis
  - campaign-creation
  - metrics-analysis
```

Examples:
- `shared/data-analysis` - Data processing (available to all)
- `marketing/campaign-creation` - Create marketing campaigns (marketing only)
- `engineering/devops` - DevOps workflows (engineering only)

### Common Shared Skills

Available to all agents:

| Skill | Purpose |
|-------|---------|
| `shared/data-analysis` | Data manipulation, transformation, visualization |
| `shared/web-research` | Web search, information gathering, summarization |
| `shared/document-analysis` | Extract info from documents, summarization |

### Department-Specific Skills

Scoped to departments:

| Skill | Department | Purpose |
|-------|-----------|---------|
| `marketing/campaign-creation` | marketing | Design marketing campaigns |
| `marketing/metrics-analysis` | marketing | Analyze marketing metrics |
| `engineering/devops` | engineering | Infrastructure/deployment tasks |
| `engineering/monitoring` | engineering | System monitoring and alerting |
| `sales/lead-scoring` | sales | Qualify and score leads |

### Using Skills in Agent Config

```yaml
agents:
  - name: "Marketing Team"
    skills:
      # Shared skills (all agents can use)
      - "shared/data-analysis"
      - "shared/web-research"

      # Department-specific skills
      - "marketing/campaign-creation"
      - "marketing/metrics-analysis"
```

### Creating Custom Skills

Create a new skill file: `skills/{scope}/{skill-name}.yaml`

```yaml
# skills/marketing/lead-scoring.yaml

name: "Lead Scoring"
description: "Score and qualify sales leads based on engagement"

workflows:
  - name: "score_lead"
    steps:
      - name: "gather_data"
        prompt: "Extract lead engagement metrics"

      - name: "apply_model"
        prompt: "Apply lead scoring model to calculate score"

      - name: "generate_report"
        prompt: "Generate lead assessment report"

prompts:
  gather_data: |
    Analyze the following lead data and extract key engagement metrics...

  apply_model: |
    Using the scoring model, rate this lead on a scale of 1-100...
```

### Best Practices for Skills

1. **Keep focused** - Each skill does one thing well
2. **Be reusable** - Design for multiple agents/contexts
3. **Document workflows** - Clear step-by-step processes
4. **Include examples** - Show expected inputs/outputs
5. **Version carefully** - Track changes to shared skills

---

## Common Patterns

Practical patterns for common scenarios.

### Pattern 1: Research & Reporting

Agent configuration for gathering and reporting information.

```yaml
agents:
  - name: "Market Research Agent"
    department: "research"
    model: "gpt-4o"

    features:
      memory: true
      rag: true
      web_search: true
      num_history_runs: 20

    tools:
      - name: "DuckDuckGoTools"
      - name: "FileTools"
        kwargs:
          base_dir: "reports/"
      - name: "PythonTools"

    skills:
      - "shared/web-research"
      - "shared/data-analysis"
      - "research/report-generation"

    instructions:
      - "Conduct thorough market research"
      - "Gather data from multiple sources"
      - "Generate comprehensive reports"
```

Workflow:
1. Agent gathers data via web search
2. Uses data-analysis skill to process information
3. Uses report-generation skill to format results
4. Outputs structured report with citations

### Pattern 2: Cost-Optimized Department Agent

Minimal viable agent for department tasks.

```yaml
agents:
  - name: "Operations Assistant"
    department: "operations"
    model: "gpt-4o-mini"        # Cost-effective model

    features:
      memory: true
      rag: true
      web_search: false
      num_history_runs: 5        # Minimal history

    tools:
      - name: "FileTools"
      - name: "SmartPandasTools"

    skills:
      - "shared/data-analysis"
```

Advantages:
- Lower cost per interaction
- Reduced latency
- Sufficient for routine tasks
- Can escalate to GPT-4 when needed

### Pattern 3: High-Availability Public Agent

Optimized for public-facing deployment.

```yaml
agents:
  - name: "Support Bot"
    department: "geral"
    model: "gpt-4o-mini"

    features:
      memory: false              # Stateless
      rag: false                # No internal data
      web_search: true
      add_history: false         # Fast responses
      num_history_runs: 0

    tools:
      - name: "DuckDuckGoTools"

    skills:
      - "shared/web-research"

    instructions:
      - "Helpful and professional"
      - "Escalate sensitive issues"
```

Advantages:
- Minimal resource usage
- Fast response times
- Handles high concurrency
- Low operational overhead

### Pattern 4: Escalation Chain

Multiple agents for handling increasing complexity.

```yaml
agents:
  # Tier 1: Fast, cost-effective
  - name: "Support Tier 1"
    model: "gpt-4o-mini"
    features:
      rag: false
      web_search: true
    skills:
      - "shared/web-research"

  # Tier 2: More capable
  - name: "Support Tier 2"
    model: "gpt-4o"
    department: "support"
    features:
      rag: true
      web_search: true
    skills:
      - "shared/data-analysis"
      - "shared/document-analysis"

  # Tier 3: Human escalation
  - name: "Support Escalation"
    department: "support"
    instructions:
      - "Prepare summary for human agent"
```

Workflow:
1. Tier 1 attempts resolution
2. If insufficient, escalate to Tier 2
3. If still unresolved, escalate to human

---

## Troubleshooting

Common issues and solutions.

### Issue 1: Agent Not Found

**Error**: `Agent 'Agent Name' not found in configuration`

**Causes**:
- Agent name misspelled
- Agent not yet defined in config
- Config not reloaded

**Solutions**:
```bash
# Check agent name in config
grep -i "name:" config/agents.yaml

# Reload configuration
python -m src.agent --reload

# Validate YAML syntax
python -m yaml config/agents.yaml
```

### Issue 2: RAG Not Working (No Access to Documents)

**Symptoms**:
- Agent claims no documents available
- Queries not returning relevant documents
- "No RAG context" messages

**Causes**:
- `rag: false` in agent features
- Wrong `department` specified
- Documents not in RAG database

**Solutions**:

1. Check agent configuration:
```yaml
features:
  rag: true                 # Must be true

department: "engineering"   # Verify correct department
```

2. Verify department documents exist:
```bash
# List documents for department
ls data/rag/engineering/
```

3. Check RAG indexing:
```bash
python -c "from src.rag import RAG; rag = RAG(); print(rag.get_indexed_docs('engineering'))"
```

### Issue 3: Tools Not Available

**Error**: `Tool 'ToolName' not found`

**Causes**:
- Tool not installed
- Tool name misspelled
- Tool not in global tools list

**Solutions**:

1. Verify tool is installed:
```bash
python -c "from src.tools import DuckDuckGoTools; print('OK')"
```

2. Check tool name in config:
```yaml
tools:
  - name: "DuckDuckGoTools"   # Check exact name
```

3. List available tools:
```bash
python -c "from src.tools import AVAILABLE_TOOLS; print(AVAILABLE_TOOLS)"
```

### Issue 4: Skills Not Loading

**Error**: `Skill 'shared/data-analysis' not found`

**Causes**:
- Skill file doesn't exist
- Skill path wrong
- Skill not registered

**Solutions**:

1. Check skill file exists:
```bash
ls skills/shared/data-analysis.yaml
ls skills/{department}/{skill-name}.yaml
```

2. Verify skill path:
```yaml
skills:
  - "shared/data-analysis"    # Check path format
  - "marketing/campaigns"     # {scope}/{name}
```

3. Check skill registration:
```bash
python -c "from src.skills import AVAILABLE_SKILLS; print(AVAILABLE_SKILLS)"
```

### Issue 5: Agent Behaving Unexpectedly

**Symptoms**:
- Agent not following instructions
- Wrong department context
- Ignoring features

**Causes**:
- Configuration not reloaded
- Conflicting instructions
- Feature settings unclear

**Solutions**:

1. Enable debug mode:
```yaml
features:
  debug_mode: true     # Enable verbose logging
```

2. Check system prompt:
```bash
python -c "from src.agent import Agent; agent = Agent.from_config('Agent Name'); print(agent.system_prompt)"
```

3. Verify feature settings:
```bash
python -c "from src.agent import Agent; agent = Agent.from_config('Agent Name'); print(agent.features)"
```

### Issue 6: High Token Usage

**Symptoms**:
- Unexpectedly high costs
- Slow response times
- Token limit warnings

**Causes**:
- `num_history_runs` too high
- `add_history` always enabled
- `web_search` on for every query

**Solutions**:

1. Reduce history:
```yaml
features:
  num_history_runs: 5    # Was 20, reduce to 5
```

2. Disable history for simple tasks:
```yaml
features:
  add_history: false     # For stateless agents
```

3. Use cheaper model:
```yaml
model: "gpt-4o-mini"    # Instead of gpt-4o
```

---

## Advanced Topics

Advanced configuration and customization options.

### Topic 1: Variable Interpolation

Use variables in agent configuration to avoid repetition.

**Supported Variables**:

From `config/company.yaml`:
- `{{company_name}}`
- `{{company_description}}`
- Custom fields in company config

From environment:
- `{{ENV_VARIABLE}}`

**Example**:

```yaml
# config/company.yaml
company_name: "TechCorp Inc"
company_description: "Leading software solutions provider"
company_values:
  - "Innovation"
  - "Quality"

# config/agents.yaml
agents:
  - name: "Company Assistant"
    instructions:
      - "You work for {{company_name}}"
      - "About us: {{company_description}}"
      - "Our values: {{company_values}}"
```

**Accessing Custom Variables**:

```yaml
# Define in company.yaml
support_email: "support@example.com"
help_url: "https://help.example.com"

# Use in agent config
instructions:
  - "Contact us: {{support_email}}"
  - "Help: {{help_url}}"
```

### Topic 2: Conditional Agent Routing

Route queries to appropriate agents based on criteria.

**Pattern**: Create a routing logic layer

```yaml
routing_rules:
  - pattern: "market.*research|competitor.*analysis"
    agent: "Research Analyst"

  - pattern: "campaign.*creation|marketing.*strategy"
    agent: "Marketing Specialist"

  - pattern: "technical.*help|debug.*"
    agent: "DevOps Assistant"

  - default: "General Assistant"
```

Implementation:
```python
def route_to_agent(query: str) -> str:
    """Route query to appropriate agent based on content"""
    for rule in routing_rules:
        if re.search(rule['pattern'], query, re.IGNORECASE):
            return rule['agent']
    return routing_rules['default']
```

### Topic 3: Multi-Agent Collaboration

Configure agents to work together on complex tasks.

**Example**: Research and Report Generation

```yaml
agents:
  # Agent 1: Data Collection
  - name: "Research Collector"
    model: "gpt-4o-mini"
    features:
      web_search: true
      rag: true
    tools:
      - name: "DuckDuckGoTools"

  # Agent 2: Analysis
  - name: "Research Analyst"
    model: "gpt-4o"
    features:
      rag: true
    tools:
      - name: "SmartPandasTools"
    skills:
      - "shared/data-analysis"

  # Agent 3: Report Writing
  - name: "Report Writer"
    model: "gpt-4o-mini"
    tools:
      - name: "FileTools"
    skills:
      - "shared/document-analysis"
```

**Workflow**:
1. Research Collector gathers raw data
2. Research Analyst processes and analyzes
3. Report Writer formats into final report

### Topic 4: Load Balancing Multiple Instances

Deploy multiple agent instances for high load.

**Configuration**:

```yaml
agents:
  - name: "Support Bot"
    instances: 3              # Run 3 parallel instances
    model: "gpt-4o-mini"
    load_balancing: "round_robin"

    features:
      memory: false           # Stateless for easy scaling
```

**Deployment**:

```bash
# Start 3 agent instances
python -m src.agent --name "Support Bot" --instances 3 --port 8000

# Load balancer routes:
# Request 1 -> Instance 1 (port 8001)
# Request 2 -> Instance 2 (port 8002)
# Request 3 -> Instance 3 (port 8003)
```

### Topic 5: Custom Tool Integration

Add custom tools to agents.

**Create Custom Tool**:

```python
# src/tools/custom_tools.py

class CustomAnalysisTool:
    """Custom analysis tool for specialized tasks"""

    def __init__(self, config: dict):
        self.config = config

    def analyze(self, data: dict) -> dict:
        """Perform custom analysis"""
        return {"result": "analysis output"}

```

**Register and Use**:

```yaml
tools:
  - name: "CustomAnalysisTool"
    kwargs:
      config:
        threshold: 0.8
        model: "custom"
```

### Topic 6: Performance Optimization

Configure agents for optimal performance.

**For Speed** (latency-sensitive):

```yaml
agents:
  - name: "Fast Response Bot"
    model: "gpt-4o-mini"       # Faster inference

    features:
      memory: false             # No context loading
      add_history: false        # No history processing
      num_history_runs: 0
      web_search: false         # No API calls
```

Expected response time: <500ms

**For Quality** (accuracy-sensitive):

```yaml
agents:
  - name: "Quality-First Agent"
    model: "gpt-4o"            # More capable model

    features:
      memory: true
      add_history: true
      num_history_runs: 20     # More context
      web_search: true         # Research capability
      debug_mode: true         # Better logging
```

Expected response time: 1-3s, higher quality

**For Cost** (budget-sensitive):

```yaml
agents:
  - name: "Budget Agent"
    model: "gpt-4o-mini"       # Cheapest model

    features:
      rag: false               # No doc processing
      web_search: false
      add_history: false
      num_history_runs: 0
```

Cost per request: ~50-70% reduction

### Topic 7: Monitoring and Logging

Configure agent monitoring.

**Enable Comprehensive Logging**:

```yaml
agents:
  - name: "Production Agent"
    features:
      debug_mode: true

    logging:
      level: "INFO"
      format: "json"           # Machine-readable logs
      outputs:
        - "console"
        - "file:logs/agent.log"
        - "sentry:https://..."  # Error tracking
```

**Monitor Key Metrics**:

```python
from src.monitoring import track_metrics

# Track per agent:
# - Response time (p50, p95, p99)
# - Token usage
# - Error rate
# - Cost per request
# - Model failures/retries
```

### Topic 8: A/B Testing Agents

Compare different agent configurations.

**Setup**:

```yaml
agents:
  - name: "Control Agent"
    variant: "control"
    model: "gpt-4o-mini"
    features:
      memory: true

  - name: "Variant A Agent"
    variant: "experiment_a"
    model: "gpt-4o"
    features:
      memory: true
      web_search: true

  - name: "Variant B Agent"
    variant: "experiment_b"
    model: "gpt-4o-mini"
    features:
      memory: false
      num_history_runs: 3
```

**Analysis**:

Track metrics per variant:
- Response time
- User satisfaction
- Cost per request
- Task completion rate

---

## Conclusion

This guide covers the complete agent creation and configuration process. For additional help:

- Check `.agent/agents/` for example agent definitions
- Review `config/agents.example.yaml` for configuration templates
- Run validation: `python -m yaml config/agents.yaml`

Key takeaways:
- Agents inherit from globals, then override with local config
- RAG access controlled by `department` field
- Skills provide reusable domain knowledge
- Features enable/disable capabilities
- Tools grant external capabilities

For production deployments, consult with your DevOps team about:
- Agent scaling and load balancing
- Monitoring and alerting
- Cost optimization
- Security and access control
