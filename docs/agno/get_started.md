> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Your First Agent

> Build and run your first agent in 20 lines of code.

In this guide, you'll build an agent that:

* Connects to an MCP server
* Stores and retrieves past conversations
* Runs as a production API

All in about 20 lines of code.

## 1. Define the Agent

Save the following code as `agno_assist.py`:

```python agno_assist.py lines theme={null}
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from agno.os import AgentOS
from agno.tools.mcp import MCPTools

agno_assist = Agent(
    name="Agno Assist",
    model=Claude(id="claude-sonnet-4-5"),
    db=SqliteDb(db_file="agno.db"),                     # session storage
    tools=[MCPTools(url="https://docs.agno.com/mcp")],  # Agno docs via MCP
    add_datetime_to_context=True,
    add_history_to_context=True,                         # include past runs
    num_history_runs=3,                                  # last 3 conversations
    markdown=True,
)

# Serve via AgentOS → streaming, auth, session isolation, API endpoints
agent_os = AgentOS(agents=[agno_assist], tracing=True)
app = agent_os.get_app()
```

<Check>
  You now have:

  * A stateful agent
  * Streaming responses
  * Per-user session isolation
  * A production-ready API
  * Tracing enabled out of the box

  No 3rd-party services required
</Check>

## 2. Run Your AgentOS

<Steps>
  <Step title="Set up your virtual environment">
    <CodeGroup>
      ```bash Mac theme={null}
      uv venv --python 3.12
      source .venv/bin/activate
      ```

      ```bash Windows theme={null}
      uv venv --python 3.12
      .venv\Scripts\activate
      ```
    </CodeGroup>
  </Step>

  <Step title="Install dependencies">
    ```bash  theme={null}
    uv pip install -U 'agno[os]' anthropic mcp
    ```
  </Step>

  <Step title="Export your Anthropic API key">
    <CodeGroup>
      ```bash Mac theme={null}
      export ANTHROPIC_API_KEY=sk-***
      ```

      ```bash Windows theme={null}
      setx ANTHROPIC_API_KEY sk-***
      ```
    </CodeGroup>
  </Step>

  <Step title="Run your AgentOS">
    ```bash  theme={null}
    fastapi dev agno_assist.py
    ```

    Your AgentOS is now running at:

    `http://localhost:7777`

    API documentation is automatically available at:

    `http://localhost:7777/docs`
  </Step>
</Steps>

You can add your own routes, middleware, or any FastAPI feature on top.

## 3. Connect to the AgentOS UI

The [AgentOS UI](https://os.agno.com) connects directly from your browser to your runtime.

It lets you test, monitor, and manage your agents in real time.

1. Open [os.agno.com](https://os.agno.com) and sign in.
2. Click **"Add new OS"** in the top navigation.
3. Select **"Local"** to connect to a local AgentOS.
4. Enter your endpoint URL (default: `http://localhost:7777`).
5. Name it something like "Development OS".
6. Click **"Connect"**.

<Frame>
  <video autoPlay muted loop controls playsInline style={{ borderRadius: "0.5rem", width: "100%", height: "auto" }}>
    <source src="https://mintcdn.com/agno-v2/aEfJPs-hg36UsUPO/videos/agent-os-connect-1.mp4?fit=max&auto=format&n=aEfJPs-hg36UsUPO&q=85&s=907888debf7f055f14e0f84405ba5749" type="video/mp4" data-path="videos/agent-os-connect-1.mp4" />
  </video>
</Frame>

You’ll see your OS with a live status indicator once connected.

## Chat with your Agent

Open Chat, select your agent, and ask:

> What is Agno?

The agent retrieves context from the Agno MCP server and responds with grounded answers.

<Frame>
  <video autoPlay muted loop controls playsInline style={{ borderRadius: "0.5rem", width: "100%", height: "auto" }}>
    <source src="https://mintcdn.com/agno-v2/aEfJPs-hg36UsUPO/videos/agno-agent-chat.mp4?fit=max&auto=format&n=aEfJPs-hg36UsUPO&q=85&s=b8ac56bfb2e9436799299fcafa746d4a" type="video/mp4" data-path="videos/agno-agent-chat.mp4" />
  </video>
</Frame>

<Tip>
  Click Sessions in the sidebar to inspect stored conversations.

  All session data is stored in your local database. No third-party tracing or hosted memory service is required.
</Tip>

## What You Just Built

In 20 lines, you built:

* A stateful agent
* Tool-augmented retrieval via MCP
* A streaming API
* Session isolation
* A production-ready runtime

You can use this exact same architecture for running multi-agent systems in production.

## Next

* [Explore the SDK →](/agents/overview)
* [Deploy AgentOS to your cloud →](/deploy/introduction)
* [Browse 2000+ code examples →](/examples/introduction)
