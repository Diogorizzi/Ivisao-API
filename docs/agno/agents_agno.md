> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# What are Agents?

> Agents are AI programs that use tools to accomplish tasks.

Agents are a stateful control loop around a stateless model. The model reasons and calls tools in a loop, guided by instructions. Add memory, knowledge, storage, human-in-the-loop, and guardrails as needed.

## Guides

<CardGroup cols={3}>
  <Card title="Build Agents" icon="wrench" iconType="duotone" href="/agents/building-agents">
    Create agents with tools and instructions.
  </Card>

  <Card title="Run Agents" icon="user-robot" iconType="duotone" href="/agents/running-agents">
    Execute agents and handle responses.
  </Card>

  <Card title="Debug Agents" icon="bug" iconType="duotone" href="/agents/debugging-agents">
    Inspect and troubleshoot agent behavior.
  </Card>
</CardGroup>

## Beyond Single Agents

| Abstraction                         | What it does                                                   |
| ----------------------------------- | -------------------------------------------------------------- |
| [**Team**](/teams/overview)         | Agents that work together                                      |
| [**Workflow**](/workflows/overview) | Orchestrate agents, teams, and functions through defined steps |

## Resources

* [Examples](/cookbook/agents/overview)
* [Reference](/reference/agents/agent)
> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Building Agents

> Start simple: a model, tools, and instructions.

To build effective agents, start simple: a model, tools, and instructions. Once that works, layer in more functionality as needed. For example, here's the simplest possible agent with access to `HackerNews`:

```python hackernews_agent.py theme={null}
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.hackernews import HackerNewsTools

agent = Agent(
    model=Claude(id="claude-sonnet-4-5"),
    tools=[HackerNewsTools()],
    instructions="Write a report on the topic. Output only the report.",
    markdown=True,
)
agent.print_response("Trending startups and products.", stream=True)
```

## Run your Agent

Use `Agent.print_response()` for development. It prints the response in a readable format in your terminal.

For production, use `Agent.run()` or `Agent.arun()`:

```python  theme={null}
from typing import Iterator
from agno.agent import Agent, RunOutputEvent, RunEvent
from agno.models.anthropic import Claude
from agno.tools.hackernews import HackerNewsTools

agent = Agent(
    model=Claude(id="claude-sonnet-4-5"),
    tools=[HackerNewsTools()],
    instructions="Write a report on the topic. Output only the report.",
    markdown=True,
)

# Stream the response
stream: Iterator[RunOutputEvent] = agent.run("Trending products", stream=True)
for chunk in stream:
    if chunk.event == RunEvent.run_content:
        print(chunk.content)
```

## Next Steps

After getting familiar with the basics, add functionality as needed:

| Task                               | Guide                                        |
| ---------------------------------- | -------------------------------------------- |
| Run agents                         | [Running agents](/agents/running-agents)     |
| Debug agents                       | [Debugging agents](/agents/debugging-agents) |
| Manage sessions                    | [Agent sessions](/sessions/overview)         |
| Handle input/output                | [Input and output](/input-output/overview)   |
| Add tools                          | [Tools](/tools/overview)                     |
| Manage context                     | [Context engineering](/context/overview)     |
| Add knowledge                      | [Knowledge](/knowledge/overview)             |
| Handle images, audio, video, files | [Multimodal](/multimodal/overview)           |
| Add guardrails                     | [Guardrails](/guardrails/overview)           |
| Cache responses during development | [Response caching](/models/cache-response)   |

# Debugging Agents

> Inspect execution flow, tool calls, and intermediate steps.

Debug mode helps you understand the flow of execution and intermediate steps:

* Inspect the messages sent to the model and the response it generates
* Trace intermediate steps and monitor metrics like token usage and execution time
* Inspect tool calls, errors, and their results

## Debug Mode

To enable debug mode:

1. Set `debug_mode=True` on your agent to enable it for all runs.
2. Set `debug_mode=True` on the `run` method to enable it for a single run.
3. Set the `AGNO_DEBUG=True` environment variable to enable debug mode globally.

```python  theme={null}
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.hackernews import HackerNewsTools

agent = Agent(
    model=Claude(id="claude-sonnet-4-5"),
    tools=[HackerNewsTools()],
    instructions="Write a report on the topic. Output only the report.",
    markdown=True,
    debug_mode=True,
    # debug_level=2, # Uncomment for more detailed logs
)

# Run agent and print response to the terminal
agent.print_response("Trending startups and products.")
```

<Tip>
  Set `debug_level=2` for more detailed logs.
</Tip>

<Frame>
  <video autoPlay muted loop playsInline style={{ borderRadius: "0.5rem", width: "100%", height: "auto" }}>
    <source src="https://mintcdn.com/agno-v2/Xc0-_OHxxYe_vtGw/videos/debug_mode.mp4?fit=max&auto=format&n=Xc0-_OHxxYe_vtGw&q=85&s=67b080deec475663e285c22130987541" type="video/mp4" data-path="videos/debug_mode.mp4" />
  </video>
</Frame>

## Interactive CLI

Agno includes a pre-built interactive CLI that runs your Agent as a command-line application. Use it to test multi-turn conversations:

```python  theme={null}
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from agno.tools.hackernews import HackerNewsTools

agent = Agent(
    model=Claude(id="claude-sonnet-4-5"),
    tools=[HackerNewsTools()],
    db=SqliteDb(db_file="tmp/data.db"),
    add_history_to_context=True,
    num_history_runs=3,
    markdown=True,
)

# Run agent as an interactive CLI app
agent.cli_app(stream=True)
```
