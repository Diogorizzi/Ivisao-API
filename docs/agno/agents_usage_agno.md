> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Agent with Tools

> Give your agent tools to interact with external services.

Give an agent tools to interact with external services. The agent uses `HackerNewsTools` to fetch trending stories and user details.

<Steps>
  <Step title="Create a Python file">
    ```python tools.py theme={null}
    from agno.agent import Agent
    from agno.models.anthropic import Claude
    from agno.tools.hackernews import HackerNewsTools

    agent = Agent(
        model=Claude(id="claude-sonnet-4-5"),
        tools=[HackerNewsTools()],
        instructions="Write a report on the topic.",
        markdown=True,
    )

    agent.print_response("Trending AI startups on Hacker News", stream=True)
    ```
  </Step>

  <Snippet file="create-venv-step.mdx" />

  <Step title="Install dependencies">
    ```bash  theme={null}
    uv pip install -U agno anthropic
    ```
  </Step>

  <Step title="Export your Anthropic API key">
    <CodeGroup>
      ```bash Mac/Linux theme={null}
      export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
      ```

      ```bash Windows theme={null}
      $Env:ANTHROPIC_API_KEY="your_anthropic_api_key_here"
      ```
    </CodeGroup>
  </Step>

  <Step title="Run Agent">
    ```bash  theme={null}
    python tools.py
    ```
  </Step>
</Steps>
