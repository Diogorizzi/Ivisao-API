> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Introduction to Skills

> Skills provide agents with structured domain expertise through instructions, scripts, and reference documentation.

Agno Skills integration, based on Anthropic's [Agent Skills specification](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview), is a way to extend your agent's capabilities by providing specific skills.

Using Skills, your agents will be able to gradually **discover, obtain and utilize** specialized knowledge and capabilities.

## What is a Skill?

A skill is a self-contained package an Agent can use to extend its capabilities in a specific domain, or to acquire a new specific capability.

All skills contain:

* **Instructions**: Detailed guidance on when and how to apply the skill (in `SKILL.md`)
* **Scripts**: Optional executable code templates the agent can run
* **References**: Optional supporting documentation (guides, cheatsheets, examples)

## Why Use Skills?

### Domain Expertise on Demand

Instead of filling the system message with instructions to cover every usecase, skills let you organize domain knowledge into focused packages.

The agent loads only what it needs, allowing you to save tokens and ultimately reduce costs.

### Reusable Knowledge Packages

Create skills once, use them across multiple agents. A code review skill can be shared between your debugging agent, PR review agent, and code generation agent.

### Progressive Discovery

Skills use lazy loading to keep context windows efficient:

1. **Browse**: The agent sees skill summaries in its system prompt
2. **Load**: When a task matches a skill, the agent loads full instructions
3. **Reference**: The agent accesses detailed documentation as needed
4. **Execute**: The agent can run scripts from the skill

## Quick Example

```python  theme={null}
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.skills import Skills, LocalSkills

# Load skills from a directory
agent = Agent(
    model=OpenAIResponses(id="gpt-5.2"),
    skills=Skills(loaders=[LocalSkills("/path/to/skills")])
)

# The agent now has access to skill tools:
# - get_skill_instructions(skill_name)
# - get_skill_reference(skill_name, reference_path)
# - get_skill_script(skill_name, script_path)
```

## Skill Structure

```
my-skill/
├── SKILL.md           # Instructions with YAML frontmatter
├── scripts/           # Optional executable scripts
│   └── helper.py
└── references/        # Optional reference documentation
    └── guide.md
```

## Learn More

<CardGroup cols={2}>
  <Card title="Creating Skills" icon="hammer" href="/skills/creating-skills">
    Learn how to create your own skills with instructions, scripts, and references
  </Card>

  <Card title="Loading Skills" icon="download" href="/skills/loading-skills">
    Learn how to load skills into your agents using LocalSkills
  </Card>
</CardGroup>

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Creating Skills

> Create skills with instructions, scripts, and reference documentation.

A skill is a directory containing a `SKILL.md` file with optional `scripts/` and `references/` subdirectories.

## Directory Structure

```
my-skill/
├── SKILL.md           # Required: Instructions with YAML frontmatter
├── scripts/           # Optional: Executable scripts
│   └── helper.py
└── references/        # Optional: Reference documentation
    └── guide.md
```

## The SKILL.md File

The `SKILL.md` file is the heart of a skill. It contains YAML frontmatter with metadata, followed by markdown instructions.

### Required Fields

```yaml  theme={null}
---
name: my-skill
description: Short description of what this skill does
---
```

* **name**: Must be lowercase, alphanumeric with hyphens only (max 64 characters)
* **description**: Brief summary shown in the agent's system prompt (max 1024 characters)

### Optional Fields

```yaml  theme={null}
---
name: code-review
description: Code review assistance with style checking and best practices
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: your-name
  tags: ["python", "code-quality"]
---
```

### Full Example

```markdown  theme={null}
---
name: code-review
description: Code review assistance with style checking and best practices
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: your-name
  tags: ["python", "code-quality"]
---

# Code Review Skill

Use this skill when reviewing code for quality, style, and best practices.

## When to Use

- User asks for code review or feedback
- User wants to improve code quality
- User needs help with refactoring

## Process

1. **Analyze Structure**: Review overall code organization
2. **Check Style**: Look for style guide violations
3. **Identify Issues**: Find bugs, security issues, performance problems
4. **Suggest Improvements**: Provide actionable recommendations

## Best Practices

- Focus on the most impactful issues first
- Explain the "why" behind suggestions
- Provide code examples for fixes
```

## Adding Scripts

Scripts are executable files the agent can run. They must have a shebang line.

### Python Script Example

Create `scripts/check_style.py`:

```python  theme={null}
#!/usr/bin/env python3
"""Check code style and return results."""

import sys

def check_style(code: str) -> dict:
    issues = []
    lines = code.split('\n')

    for i, line in enumerate(lines, 1):
        if len(line) > 100:
            issues.append(f"Line {i}: exceeds 100 characters")
        if line.endswith(' '):
            issues.append(f"Line {i}: trailing whitespace")

    return {"issues": issues, "count": len(issues)}

if __name__ == "__main__":
    # Read code from stdin or argument
    code = sys.stdin.read() if not sys.argv[1:] else sys.argv[1]
    result = check_style(code)
    print(result)
```

### Shell Script Example

Create `scripts/lint.sh`:

```bash  theme={null}
#!/bin/bash
# Run linting on provided file

if [ -z "$1" ]; then
    echo "Usage: lint.sh <file>"
    exit 1
fi

ruff check "$1" 2>&1
```

<Note>
  Scripts are executed with the skill directory as the working directory. The agent can pass arguments when executing scripts.
</Note>

## Adding References

References are documentation files the agent can load on demand.

### Example Reference

Create `references/style-guide.md`:

```markdown  theme={null}
# Python Style Guide

## Naming Conventions

- **Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`

## Line Length

- Maximum 100 characters per line
- Break long lines at logical points

## Imports

- Standard library imports first
- Third-party imports second
- Local imports third
- Alphabetize within each group
```

## Validation Rules

Skills are validated when loaded. Here are the rules:

### Name Requirements

* Maximum 64 characters
* Lowercase letters, numbers, and hyphens only
* Cannot start or end with a hyphen
* No consecutive hyphens (`--`)
* Must match the directory name

### Field Limits

| Field       | Max Length      |
| ----------- | --------------- |
| name        | 64 characters   |
| description | 1024 characters |

### Valid Licenses

Common SPDX identifiers are accepted: `MIT`, `Apache-2.0`, `GPL-3.0`, `BSD-3-Clause`, etc.

## Organizing Multiple Skills

Create a directory containing multiple skill folders:

```
skills/
├── code-review/
│   ├── SKILL.md
│   ├── scripts/
│   └── references/
├── git-workflow/
│   ├── SKILL.md
│   ├── scripts/
│   └── references/
└── testing/
    ├── SKILL.md
    └── references/
```

Load all skills at once:

```python  theme={null}
from agno.skills import Skills, LocalSkills

skills = Skills(loaders=[LocalSkills("/path/to/skills")])
```

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Loading Skills

> Load skills into agents using LocalSkills and the Skills orchestrator.

Skills are loaded using the `Skills` class with one or more `SkillLoader` instances set as loaders.

Currently, `LocalSkills` is available for loading skills from the filesystem.

## Basic Usage

```python  theme={null}
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.skills import Skills, LocalSkills

# Load skills from a directory
agent = Agent(
    model=OpenAIResponses(id="gpt-5.2"),
    skills=Skills(loaders=[LocalSkills("/path/to/skills")])
)
```

## LocalSkills Loader

The `LocalSkills` loader reads skills from the local filesystem.

### Loading from a Directory of Skills

If you have multiple skills in subdirectories:

```
skills/
├── code-review/
│   └── SKILL.md
├── git-workflow/
│   └── SKILL.md
└── testing/
    └── SKILL.md
```

```python  theme={null}
from agno.skills import Skills, LocalSkills

# Load all skills from the directory
skills = Skills(loaders=[LocalSkills("/path/to/skills")])
```

### Loading a Single Skill

If you want to load just one skill:

```python  theme={null}
from agno.skills import Skills, LocalSkills

# Load a single skill directory
skills = Skills(loaders=[LocalSkills("/path/to/skills/code-review")])
```

### Multiple Loaders

You can combine multiple loaders to load skills from different locations:

```python  theme={null}
from agno.skills import Skills, LocalSkills

skills = Skills(loaders=[
    LocalSkills("/path/to/shared-skills"),
    LocalSkills("/path/to/project-skills"),
])
```

<Note>
  If skills from different loaders have the same name, the later loader's skill will overwrite the earlier one.
</Note>

## Agent Tools

When you add skills to an agent, it automatically gets access to these tools:

| Tool                                                                | Description                        |
| ------------------------------------------------------------------- | ---------------------------------- |
| `get_skill_instructions(skill_name)`                                | Load full instructions for a skill |
| `get_skill_reference(skill_name, reference_path)`                   | Load a reference document          |
| `get_skill_script(skill_name, script_path, execute, args, timeout)` | Read or execute a script           |

### Example: Using Skill Tools

```python  theme={null}
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.skills import Skills, LocalSkills

agent = Agent(
    model=OpenAIResponses(id="gpt-5.2"),
    skills=Skills(loaders=[LocalSkills("/path/to/skills")]),
    instructions=[
        "You have access to specialized skills.",
        "Use get_skill_instructions to load full guidance when needed.",
    ],
)

# The agent will automatically use skills when relevant
agent.print_response("Review this code for best practices: def foo(): pass")
```

## System Prompt Integration

Skills metadata is automatically added to the agent's system prompt. The agent sees:

* Skill names and descriptions
* Available scripts and references
* Instructions on how to load full skill details

This allows the agent to discover and use skills without loading everything upfront.

## Reloading Skills

If your skills change at runtime, you can reload them:

```python  theme={null}
from agno.skills import Skills, LocalSkills

skills = Skills(loaders=[LocalSkills("/path/to/skills")])

# ... skills are modified on disk ...

# Reload to pick up changes
skills.reload()
```

## Error Handling

Skills are validated when loaded. If validation fails, a `SkillValidationError` is raised:

```python  theme={null}
from agno.skills import Skills, LocalSkills, SkillValidationError

try:
    skills = Skills(loaders=[LocalSkills("/path/to/skills")])
except SkillValidationError as e:
    print(f"Skill validation failed: {e}")
    print(f"Errors: {e.errors}")
```

## Complete Example

```python  theme={null}
from pathlib import Path
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.skills import Skills, LocalSkills

# Get skills directory relative to this file
skills_dir = Path(__file__).parent / "skills"

# Create agent with skills
agent = Agent(
    name="Code Assistant",
    model=OpenAIResponses(id="gpt-5.2"),
    skills=Skills(loaders=[LocalSkills(str(skills_dir))]),
    instructions=[
        "You are a helpful coding assistant with access to specialized skills."
    ],
    markdown=True,
)

if __name__ == "__main__":
    agent.print_response(
        "Review this Python function:\n\n"
        "def calc(x,y): return x+y"
    )
```
