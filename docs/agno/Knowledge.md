> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Overview

> Give agents access to documents, databases, and domain expertise.

**Knowledge** gives agents access to information beyond their training data. Load files, URLs, or raw text, and agents can search this knowledge to provide accurate, contextual responses.

```python  theme={null}
from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.chroma import ChromaDb

# Create a knowledge base
knowledge = Knowledge(
    vector_db=ChromaDb(collection="docs", path="tmp/chromadb"),
)

# Load content
knowledge.insert(url="https://docs.agno.com/introduction.md")

# Create an agent that searches the knowledge base
agent = Agent(knowledge=knowledge, search_knowledge=True)
agent.print_response("What is Agno?")
```

The agent searches its knowledge base and grounds its response in the content.

## How It Works

Knowledge combines three components:

1. **Content ingestion**: Read documents from files, URLs, cloud storage, or raw text. Agno includes readers for PDF, DOCX, CSV, Markdown, and more.

2. **Chunking and embedding**: Documents are split into searchable chunks and converted to vector embeddings that capture semantic meaning.

3. **Search and retrieval**: When an agent needs information, it searches the vector database for relevant chunks and includes them in its context.

You can use **Agentic RAG** (agent decides when to search) or **Traditional RAG** (always inject context). Agentic RAG is the default and works well for most use cases.

## Why Knowledge Matters

Language models have broad general knowledge but lack context about your specific domain. Knowledge bridges this gap by providing relevant information at runtime.

**Start with your content.** Load company documentation, database schemas, product specs, support FAQs, or research papers. The agent uses this information to answer questions accurately instead of guessing.

**Then let agents learn.** Knowledge isn't read-only. Agents can save insights they discover and retrieve them later, building expertise across conversations.

```python  theme={null}
def save_learning(title: str, insight: str) -> str:
    """Save a reusable insight to the knowledge base."""
    knowledge.insert(name=title, text_content=insight)
    return f"Saved: {title}"

agent = Agent(
    knowledge=knowledge,
    search_knowledge=True,
    tools=[save_learning],  # Agent can write to knowledge
)
```

This turns agents from static systems into systems that learn over time.

## Examples

<CardGroup cols={3}>
  <Card title="Quick Start" icon="rocket" href="/knowledge/quickstart">
    Build an agent with knowledge in 5 minutes
  </Card>

  <Card title="Knowledge for Agents" icon="robot" href="/knowledge/agents/overview">
    Agentic RAG, traditional RAG, reranking
  </Card>

  <Card title="Knowledge for Teams" icon="users" href="/knowledge/teams/overview">
    Distributed search, coordinated RAG
  </Card>
</CardGroup>

## Concepts

<CardGroup cols={3}>
  <Card title="Vector DB" icon="database" href="/knowledge/concepts/vector-db">
    Store and search embeddings
  </Card>

  <Card title="Content DB" icon="table" href="/knowledge/concepts/contents-db">
    Track knowledge contents
  </Card>

  <Card title="Search & Retrieval" icon="magnifying-glass" href="/knowledge/concepts/search-and-retrieval/overview">
    Vector, keyword, and hybrid search
  </Card>

  <Card title="Readers" icon="file-lines" href="/knowledge/concepts/readers/overview">
    Ingest from various sources
  </Card>

  <Card title="Chunkers" icon="scissors" href="/knowledge/concepts/chunking/overview">
    Control document splitting
  </Card>

  <Card title="Embedders" icon="code" href="/knowledge/concepts/embedder/overview">
    Convert text to vectors
  </Card>

  <Card title="Filtering" icon="filter" href="/knowledge/concepts/filters/overview">
    Filter results by metadata
  </Card>
</CardGroup>

## Vector Stores

Agno supports 20+ vector databases, from local options like LanceDB and ChromaDB to managed services like Pinecone and Weaviate.

<Card title="All Vector Stores" icon="layer-group" href="/knowledge/vector-stores">
  See supported databases
</Card>

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Quickstart

> Build a knowledge-powered agent in under 5 minutes.

Build an agent that answers questions about your documents.

## Create an Agent with Knowledge

```python knowledge_agent.py theme={null}
from agno.agent import Agent
from agno.knowledge.embedder.google import GeminiEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.models.google import Gemini
from agno.vectordb.chroma import ChromaDb
from agno.vectordb.search import SearchType

# Create a knowledge base with ChromaDB
knowledge = Knowledge(
    vector_db=ChromaDb(
        collection="docs",
        path="tmp/chromadb",
        persistent_client=True,
        search_type=SearchType.hybrid,
        embedder=GeminiEmbedder(id="gemini-embedding-001"),
    ),
)

# Load content into the knowledge base
knowledge.insert(url="https://docs.agno.com/introduction.md", skip_if_exists=True)

# Create an agent that searches the knowledge base
agent = Agent(
    model=Gemini(id="gemini-3-flash-preview"),
    knowledge=knowledge,
    search_knowledge=True,
    markdown=True,
)

agent.print_response("What is Agno?", stream=True)
```

## Setup

<Steps>
  <Step title="Create virtual environment">
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
    uv pip install -U agno chromadb google-genai
    ```
  </Step>

  <Step title="Export your API key">
    <CodeGroup>
      ```bash Mac theme={null}
      export GOOGLE_API_KEY=your-google-api-key
      ```

      ```bash Windows theme={null}
      setx GOOGLE_API_KEY your-google-api-key
      ```
    </CodeGroup>
  </Step>

  <Step title="Run the agent">
    ```bash  theme={null}
    python knowledge_agent.py
    ```
  </Step>
</Steps>

The agent searches the knowledge base, finds relevant content, and answers based on what it found.

## Load Different Content Types

<Tabs>
  <Tab title="Files">
    ```python  theme={null}
      knowledge.insert(path="docs/product-guide.pdf")
      knowledge.insert(path="data/")  # Entire directory
    ```
  </Tab>

  <Tab title="URLs">
    ```python  theme={null}
      knowledge.insert(url="https://example.com/docs.pdf")
    ```
  </Tab>

  <Tab title="Text">
    ```python  theme={null}
      knowledge.insert(text_content="Your content here...")
    ```
  </Tab>
</Tabs>

Agno detects file types automatically and uses the appropriate reader for PDFs, DOCX, CSV, Markdown, and more.

## What's Happening

1. **Insert**: Content is chunked, embedded with Gemini, and stored in ChromaDB
2. **Query**: The agent receives your question and decides to search the knowledge base using the `search_knowledge_base` tool
3. **Response**: The agent uses the retrieved content to answer, grounding its response in your data

This is **Agentic RAG**. The agent decides when to search rather than blindly injecting context on every query.

## Next Steps

<CardGroup cols={2}>
  <Card title="Agents with Knowledge" icon="robot" href="/knowledge/agents/overview">
    Agentic RAG, traditional RAG, reranking
  </Card>

  <Card title="Teams with Knowledge" icon="users" href="/knowledge/teams/overview">
    Distributed search, coordinated RAG
  </Card>

  <Card title="Vector Stores" icon="database" href="/knowledge/vector-stores">
    PgVector, Pinecone, Weaviate, and 20+ more
  </Card>

  <Card title="Search & Retrieval" icon="magnifying-glass" href="/knowledge/concepts/search-and-retrieval/overview">
    Vector, keyword, and hybrid search
  </Card>
</CardGroup>

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Vector Databases

> Store embeddings and search for similar content.

Vector databases store content as embeddings and enable similarity search. When an agent searches the knowledge base, the query is converted to an embedding and matched against stored vectors to find relevant content.

## How It Works

<Steps>
  <Step title="Chunk">
    Documents are split into smaller pieces for more precise retrieval.
  </Step>

  <Step title="Embed">
    Each chunk is converted to a vector embedding and stored in the database.
  </Step>

  <Step title="Search">
    Queries are embedded and matched against stored vectors to find similar content.
  </Step>
</Steps>

## Hybrid Search

Many vector databases support hybrid search, combining vector similarity with keyword matching. This improves results for queries that benefit from both semantic understanding and exact term matching.

Hybrid search works by:

1. Finding semantically similar content via vector search
2. Finding keyword matches via full-text search
3. Combining results using ranked fusion

## Supported Databases

<CardGroup cols={3}>
  <Card title="Azure Cosmos DB" icon="database" iconType="duotone" href="/knowledge/vector-stores/azure_cosmos_mongodb/overview">
    MongoDB vCore vector search
  </Card>

  <Card title="Cassandra" icon="database" iconType="duotone" href="/knowledge/vector-stores/cassandra/overview">
    Distributed database with vector search
  </Card>

  <Card title="Chroma" icon="database" iconType="duotone" href="/knowledge/vector-stores/chroma/overview">
    Open-source embedding database
  </Card>

  <Card title="ClickHouse" icon="database" iconType="duotone" href="/knowledge/vector-stores/clickhouse/overview">
    Analytical database with vector search
  </Card>

  <Card title="Couchbase" icon="database" iconType="duotone" href="/knowledge/vector-stores/couchbase/overview">
    NoSQL with vector search
  </Card>

  <Card title="LanceDB" icon="database" iconType="duotone" href="/knowledge/vector-stores/lancedb/overview">
    Local, serverless, hybrid search
  </Card>

  <Card title="LangChain" icon="link" iconType="duotone" href="/knowledge/vector-stores/langchain/overview">
    Use any LangChain vector store
  </Card>

  <Card title="LightRAG" icon="lightbulb" iconType="duotone" href="/knowledge/vector-stores/lightrag/overview">
    Graph-based RAG
  </Card>

  <Card title="Milvus" icon="database" iconType="duotone" href="/knowledge/vector-stores/milvus/overview">
    Scalable vector database
  </Card>

  <Card title="MongoDB" icon="database" iconType="duotone" href="/knowledge/vector-stores/mongodb/overview">
    Atlas vector search
  </Card>

  <Card title="PgVector" icon="database" iconType="duotone" href="/knowledge/vector-stores/pgvector/overview">
    PostgreSQL extension, hybrid search
  </Card>

  <Card title="Pinecone" icon="cloud" iconType="duotone" href="/knowledge/vector-stores/pinecone/overview">
    Managed vector database
  </Card>

  <Card title="Qdrant" icon="database" iconType="duotone" href="/knowledge/vector-stores/qdrant/overview">
    High-performance vector search
  </Card>

  <Card title="Redis" icon="database" iconType="duotone" href="/knowledge/vector-stores/redis/overview">
    In-memory with vector search
  </Card>

  <Card title="SingleStore" icon="database" iconType="duotone" href="/knowledge/vector-stores/singlestore/overview">
    Real-time analytics with vectors
  </Card>

  <Card title="SurrealDB" icon="database" iconType="duotone" href="/knowledge/vector-stores/surrealdb/overview">
    Multi-model database
  </Card>

  <Card title="Upstash" icon="cloud" iconType="duotone" href="/knowledge/vector-stores/upstash/overview">
    Serverless vector search
  </Card>

  <Card title="Weaviate" icon="database" iconType="duotone" href="/knowledge/vector-stores/weaviate/overview">
    Vector search with modules
  </Card>
</CardGroup>

## Choosing a Database

<CardGroup cols={2}>
  <Card title="Local Development" icon="laptop-code" href="/knowledge/vector-stores/lancedb/overview">
    **LanceDB** or **ChromaDB** for zero-setup local development
  </Card>

  <Card title="Production" icon="server" href="/knowledge/vector-stores/pgvector/overview">
    **PgVector** if you already use PostgreSQL
  </Card>

  <Card title="Managed Service" icon="cloud" href="/knowledge/vector-stores/pinecone/overview">
    **Pinecone** or **Weaviate Cloud** for no-ops deployment
  </Card>

  <Card title="High Performance" icon="gauge" href="/knowledge/vector-stores/qdrant/overview">
    **Qdrant** or **Milvus** for large-scale search
  </Card>
</CardGroup>

## Async Support

Vector databases with async support enable non-blocking operations for better performance in production. Use `ainsert` and `asearch` methods when building async agents.

```python  theme={null}
# Async insert
await knowledge.ainsert(url="https://example.com/docs.pdf")

# Async search
results = await knowledge.asearch(query="How do I configure X?")
```

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Contents Database

> Track and manage the content you've added to your knowledge base.

Contents Database is an optional component that tracks what you've added to your knowledge base. While the vector database stores embeddings for search, Contents Database stores metadata about each piece of content: what it is, when you added it, and its processing status.

```python  theme={null}
from agno.knowledge.knowledge import Knowledge
from agno.db.postgres import PostgresDb
from agno.vectordb.pgvector import PgVector

knowledge = Knowledge(
    vector_db=PgVector(table_name="vectors", db_url=db_url),
    contents_db=PostgresDb(db_url=db_url),  # Enables content tracking
)
```

## Why Use Content DB

**Without Content DB**, you can search your knowledge base but can't see what's in it or manage individual pieces of content.

**With Content DB**, you get:

* **Visibility**: See all content that's been added, track processing status, view metadata
* **Management**: Delete specific content and automatically clean up associated vectors
* **Updates**: Edit names, descriptions, and metadata without rebuilding the knowledge base
* **Filtering**: Use [agentic filtering](/knowledge/concepts/filters/overview) to filter search results by metadata

<Note>
  Contents DB is required for [agentic filtering](/knowledge/concepts/filters/overview) and the [AgentOS Knowledge UI](/agent-os/features/knowledge-management).
</Note>

## Setup

Agno supports multiple database backends:

<Tabs>
  <Tab title="PostgreSQL">
    ```python  theme={null}
    from agno.db.postgres import PostgresDb

    contents_db = PostgresDb(
        db_url="postgresql+psycopg://user:pass@localhost:5432/db",
        knowledge_table="knowledge_contents"  # Optional custom table name
    )
    ```
  </Tab>

  <Tab title="SQLite">
    ```python  theme={null}
    from agno.db.sqlite import SqliteDb

    contents_db = SqliteDb(db_file="knowledge.db")
    ```
  </Tab>

  <Tab title="MongoDB">
    ```python  theme={null}
    from agno.db.mongo import MongoDb

    contents_db = MongoDb(
        uri="mongodb://localhost:27017",
        database="agno_db"
    )
    ```
  </Tab>

  <Tab title="In-Memory">
    ```python  theme={null}
    from agno.db.in_memory import InMemoryDb

    contents_db = InMemoryDb()  # For testing only
    ```
  </Tab>
</Tabs>

Other supported backends: [PostgreSQL](/database/providers/postgres/overview) (recommended for production), [SQLite](/database/providers/sqlite/overview) (development), [MySQL](/database/providers/mysql/overview), [MongoDB](/database/providers/mongo/overview), [Redis](/database/providers/redis/overview), [DynamoDB](/database/providers/dynamodb/overview), [Firestore](/database/providers/firestore/overview).

## Managing Content

### Add Content with Metadata

```python  theme={null}
knowledge.insert(
    name="Product Manual",
    path="docs/manual.pdf",
    metadata={"department": "engineering", "version": "2.1"}
)
```

### List Content

```python  theme={null}
contents, total_count = knowledge.get_content(
    limit=20,
    page=1,
    sort_by="created_at",
    sort_order="desc"
)

for content in contents:
    print(content.name, content.status, content.created_at)
```

### Get Content by ID

```python  theme={null}
content = knowledge.get_content_by_id(content_id)

print(content.name)         # Content name
print(content.description)  # Description
print(content.metadata)     # Custom metadata
print(content.file_type)    # File type (.pdf, .txt, etc.)
print(content.size)         # File size in bytes
print(content.status)       # Processing status
print(content.created_at)   # When it was added
print(content.updated_at)   # Last modification
```

### Delete Content

Deleting content automatically:

1. Removes the content metadata from Content DB
2. Deletes associated vectors from the vector database
3. Maintains consistency between both databases

```python  theme={null}
# Delete specific content
knowledge.remove_content_by_id(content_id)

# Delete all content
knowledge.remove_all_content()
```

### Filter by Metadata

```python  theme={null}
# Get available filter keys
valid_filters = knowledge.get_filters()

# Search with filters
results = knowledge.search(
    query="technical documentation",
    filters={"department": "engineering"}
)
```

## Schema

Content DB stores the following fields for each piece of content:

| Field            | Type | Description                                |
| ---------------- | ---- | ------------------------------------------ |
| `id`             | str  | Unique identifier                          |
| `name`           | str  | Content name                               |
| `description`    | str  | Content description                        |
| `metadata`       | dict | Custom metadata                            |
| `type`           | str  | Content type                               |
| `size`           | int  | File size in bytes                         |
| `linked_to`      | str  | ID of linked content                       |
| `access_count`   | int  | Number of times accessed                   |
| `status`         | str  | Processing status                          |
| `status_message` | str  | Status details                             |
| `created_at`     | int  | Created timestamp                          |
| `updated_at`     | int  | Updated timestamp                          |
| `external_id`    | str  | External ID for integrations like LightRAG |

## AgentOS Integration

Content DB is required for the AgentOS Knowledge UI. With it, the web interface provides:

* **Content Browser**: View all uploaded content with metadata
* **Upload Interface**: Add new content through the web UI
* **Status Monitoring**: Real-time processing status updates
* **Metadata Editor**: Update content metadata through forms
* **Search and Filtering**: Find content by metadata attributes
* **Bulk Operations**: Manage multiple content items at once

```python  theme={null}
from agno.os import AgentOS
from agno.agent import Agent

knowledge = Knowledge(
    vector_db=PgVector(table_name="vectors", db_url=db_url),
    contents_db=PostgresDb(db_url=db_url),
)

agent = Agent(name="Knowledge Agent", knowledge=knowledge)

app = AgentOS(
    id="knowledge-demo",
    agents=[agent],
)
```

See [AgentOS Knowledge Management](/agent-os/features/knowledge-management) for more details.

## Next Steps

<CardGroup cols={2}>
  <Card title="Vector DB" icon="database" href="/knowledge/concepts/vector-db">
    Understand the embedding storage layer
  </Card>

  <Card title="Filtering" icon="filter" href="/knowledge/concepts/filters/overview">
    Filter search results by metadata
  </Card>

  <Card title="AgentOS" icon="server" href="/agent-os/introduction">
    Manage knowledge through the web UI
  </Card>

  <Card title="Database Setup" icon="wrench" href="/database/overview">
    Database configuration guides
  </Card>
</CardGroup>

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Search & Retrieval

> How agents search knowledge bases to find relevant information.

When an agent needs information, it searches for relevant chunks rather than loading everything into the prompt. This keeps responses focused and efficient.

```python  theme={null}
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector
from agno.vectordb.search import SearchType

knowledge = Knowledge(
    vector_db=PgVector(
        table_name="embeddings",
        db_url=db_url,
        search_type=SearchType.hybrid,
    ),
    max_results=5,
)

results = knowledge.search("What's our return policy?")
```

## How Search Works

<Steps>
  <Step title="Query Analysis">
    The agent analyzes the user's question to understand what information would help.
  </Step>

  <Step title="Search Execution">
    The system runs vector, keyword, or hybrid search based on configuration.
  </Step>

  <Step title="Retrieval">
    The knowledge base returns the most relevant content chunks.
  </Step>

  <Step title="Response Generation">
    Retrieved information is combined with the question to generate a response.
  </Step>
</Steps>

## Search Types

### Vector Search

Finds content by meaning, not exact words. When you ask "How do I reset my password?", it finds documents about "changing credentials" even if those exact words don't appear.

```python  theme={null}
vector_db = PgVector(
    table_name="embeddings",
    db_url=db_url,
    search_type=SearchType.vector,
)
```

**Best for:** Conceptual questions where users phrase things differently than your docs.

### Keyword Search

Classic text search that matches exact words and phrases. Uses your database's full-text search or keyword matching capabilities.

```python  theme={null}
vector_db = PgVector(
    table_name="embeddings",
    db_url=db_url,
    search_type=SearchType.keyword,
)
```

**Best for:** Specific terms, product names, error codes, technical identifiers.

### Hybrid Search

Combines vector similarity with keyword matching. Usually the best choice for production.

```python  theme={null}
from agno.knowledge.reranker.cohere import CohereReranker

vector_db = PgVector(
    table_name="embeddings",
    db_url=db_url,
    search_type=SearchType.hybrid,
    reranker=CohereReranker(),  # Optional: improves result ordering
)
```

**Best for:** Most real-world applications where you want both semantic understanding and exact-match precision.

<Tip>
  Start with hybrid search and add a reranker for best results.
</Tip>

## Agentic vs Traditional RAG

**Traditional RAG** always searches with the exact user query and injects results into the prompt.

**Agentic RAG** lets the agent decide when to search, reformulate queries, and run follow-up searches if needed.

<Tabs>
  <Tab title="Traditional RAG">
    ```python  theme={null}
    # Always searches, always injects results
    results = knowledge.search(user_query)
    context = "\n\n".join([d.content for d in results])
    response = llm.generate(user_query + "\n" + context)
    ```
  </Tab>

  <Tab title="Agentic RAG">
    ```python  theme={null}
    from agno.agent import Agent

    # Agent decides when to search
    agent = Agent(
        knowledge=knowledge,
        search_knowledge=True,  # Agent calls search_knowledge_base tool when needed
    )

    agent.print_response("What's our return policy?")
    ```
  </Tab>
</Tabs>

With Agentic RAG, the agent can:

* Skip searching when it already knows the answer
* Reformulate queries for better results
* Run multiple searches to gather complete information
* Combine results from different searches

## Filtering Results

Filter searches by metadata to target specific content:

```python  theme={null}
# Add content with metadata
knowledge.insert(
    path="policies/",
    metadata={"department": "hr", "type": "policy", "year": 2024}
)

# Search with filters
results = knowledge.search(
    query="vacation policy",
    filters={"department": "hr", "type": "policy"}
)

# Use filters with agents
agent.print_response(
    "What's our vacation policy?",
    knowledge_filters={"department": "hr"}
)
```

For complex filtering with OR, NOT, and comparisons, see [Filtering](/knowledge/concepts/filters/overview).

## Custom Retrieval Logic

Override the default search behavior with a custom retriever:

```python  theme={null}
async def my_retriever(query: str, num_documents: int = 5, filters: dict = None, **kwargs):
    # Reformulate query
    expanded_query = query.replace("vacation", "paid time off PTO")

    # Run search
    docs = await knowledge.asearch(expanded_query, max_results=num_documents, filters=filters)

    return [d.to_dict() for d in docs]

agent = Agent(
    knowledge=knowledge,
    knowledge_retriever=my_retriever,
)
```

## Improving Search Quality

### Chunk Size

How you split content affects retrieval precision:

| Chunk Size              | Trade-off                          |
| ----------------------- | ---------------------------------- |
| Small (1000-3000 chars) | More precise, but may miss context |
| Default (5000 chars)    | Balanced precision and context     |
| Large (8000+ chars)     | More context, but less targeted    |
| Semantic chunking       | Splits at natural topic boundaries |

### Embedding Model

Your embedder converts text into vectors that capture meaning. The right choice depends on your content:

| Type                             | Use Case                                            |
| -------------------------------- | --------------------------------------------------- |
| General-purpose (OpenAI, Gemini) | Works well for most content                         |
| Domain-specific                  | Better for specialized fields like medical or legal |
| Multilingual                     | Required for non-English or mixed-language content  |

See [Embedders](/knowledge/concepts/embedder/overview) for available options.

### Metadata

Rich metadata enables better filtering:

```python  theme={null}
# Good: specific, consistent, filterable
metadata = {
    "department": "engineering",
    "document_type": "runbook",
    "service": "payments",
    "last_updated": "2024-01-15",
}

# Bad: vague, inconsistent
metadata = {"type": "doc", "id": "12345"}
```

### Content Structure

Well-organized content searches better:

* Use clear headings and sections
* Include relevant terminology naturally
* Add summaries at the top of long documents
* Use descriptive filenames (`hr_vacation_policy_2024.pdf` not `document1.pdf`)

### Testing

Test with real queries to validate search quality:

```python  theme={null}
test_queries = [
    "What's our vacation policy?",
    "How do I submit expenses?",
    "Remote work guidelines",
]

for query in test_queries:
    results = knowledge.search(query)
    print(f"{query} -> {results[0].content[:100]}..." if results else "No results")
```

## Next Steps

<CardGroup cols={2}>
  <Card title="Hybrid Search" icon="magnifying-glass" href="/knowledge/concepts/search-and-retrieval/hybrid-search">
    Deep dive into combining vector and keyword search
  </Card>

  <Card title="Filtering" icon="filter" href="/knowledge/concepts/filters/overview">
    Filter results by metadata
  </Card>

  <Card title="Vector DB" icon="database" href="/knowledge/concepts/vector-db">
    Storage options for embeddings
  </Card>

  <Card title="Performance Tips" icon="gauge" href="/knowledge/concepts/performance-tips">
    Optimize for speed and accuracy
  </Card>
</CardGroup>

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Hybrid Search

> Combine vector similarity with keyword matching for better retrieval accuracy.

Hybrid search combines vector similarity (semantic meaning) with keyword matching (exact terms) to get the best of both approaches. It's the recommended search type for most production use cases.

```python  theme={null}
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType

knowledge = Knowledge(
    vector_db=PgVector(
        table_name="docs",
        db_url=db_url,
        search_type=SearchType.hybrid,
    ),
)
```

## How It Works

Hybrid search runs two searches in parallel:

1. **Vector search** finds semantically similar content (meaning-based)
2. **Keyword search** finds exact term matches (text-based)
3. **Fusion** combines results using Reciprocal Rank Fusion (RRF)

The RRF algorithm merges rankings with the formula: `RRF(d) = Σ 1/(k + rank)`

This ensures documents that rank well in both searches appear at the top, while documents that only match one method still surface.

<Note>
  Not all vector databases support hybrid search or RRF.
</Note>

## When to Use Hybrid Search

| Scenario                              | Why Hybrid Helps                                   |
| ------------------------------------- | -------------------------------------------------- |
| User queries vary in phrasing         | Vector catches meaning, keywords catch exact terms |
| Technical content with specific terms | Keywords match error codes, product names exactly  |
| Mixed content types                   | Balances conceptual and precise matching           |
| Production systems                    | Best overall accuracy for diverse queries          |

Use **vector-only** if your queries are always conceptual with no specific terms.
Use **keyword-only** if you need exact matching (e.g., search by ID or code).

## Configuration

### Basic Setup

```python  theme={null}
from agno.vectordb.pgvector import PgVector, SearchType

vector_db = PgVector(
    table_name="docs",
    db_url=db_url,
    search_type=SearchType.hybrid,
)
```

### With Reranking

Add a reranker to improve result ordering after fusion:

```python  theme={null}
from agno.knowledge.reranker.cohere import CohereReranker

vector_db = PgVector(
    table_name="docs",
    db_url=db_url,
    search_type=SearchType.hybrid,
    reranker=CohereReranker(),
)
```

### RRF Constant

The `k` constant in RRF controls how much weight lower-ranked results receive. Higher values (e.g., 60) smooth out rankings; lower values make top results more dominant.

```python  theme={null}
from agno.vectordb.chroma import ChromaDb, SearchType

vector_db = ChromaDb(
    collection="docs",
    path="tmp/chromadb",
    search_type=SearchType.hybrid,
    hybrid_rrf_k=60,  # Default is 60
)
```

## Example

```python hybrid_search.py theme={null}
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge = Knowledge(
    vector_db=PgVector(
        table_name="recipes",
        db_url=db_url,
        search_type=SearchType.hybrid,
    ),
)

# Load content
knowledge.insert(
    url="https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf",
)

# Search combines semantic similarity + keyword matching
results = knowledge.search("chicken coconut soup", max_results=5)
for doc in results:
    print(doc.content[:200])
```

## Supported Vector Databases

Hybrid search is available in:

* [PgVector](/knowledge/vector-stores/pgvector/overview)
* [ChromaDB](/knowledge/vector-stores/chroma/overview)
* [LanceDB](/knowledge/vector-stores/lancedb/overview)
* [Weaviate](/knowledge/vector-stores/weaviate/overview)
* [Milvus](/knowledge/vector-stores/milvus/overview)
* [Pinecone](/knowledge/vector-stores/pinecone/overview)

Check individual vector database docs for specific hybrid search capabilities.

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Agentic RAG with Reranking

> Combine agentic search, hybrid retrieval, and reranking for high-quality responses.

This example combines three techniques for optimal retrieval:

1. **Agentic RAG**: Agent decides when to search the knowledge base
2. **Hybrid search**: Combines vector similarity with keyword matching
3. **Reranking**: Reorders results using a dedicated ranking model

```python  theme={null}
from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.cohere import CohereEmbedder
from agno.knowledge.reranker.cohere import CohereReranker
from agno.models.anthropic import Claude
from agno.vectordb.lancedb import LanceDb, SearchType

knowledge = Knowledge(
    vector_db=LanceDb(
        uri="tmp/lancedb",
        table_name="docs",
        search_type=SearchType.hybrid,
        embedder=CohereEmbedder(id="embed-v4.0"),
        reranker=CohereReranker(model="rerank-v3.5"),
    ),
)

agent = Agent(
    model=Claude(id="claude-sonnet-4-5"),
    knowledge=knowledge,
    search_knowledge=True,
)
```

## Why Combine These Techniques

| Technique     | What It Does                                             |
| ------------- | -------------------------------------------------------- |
| Agentic RAG   | Agent searches only when needed, can reformulate queries |
| Hybrid search | Catches both semantic matches and exact terms            |
| Reranking     | Uses a dedicated model to reorder results by relevance   |

Together, these provide better retrieval accuracy than any single technique alone.

## How Reranking Works

After hybrid search returns initial results, the reranker:

1. Takes the query and candidate documents
2. Scores each document for relevance using a cross-encoder model
3. Reorders results so the most relevant appear first

Cohere's `rerank-v3.5` is trained specifically for this task and significantly improves result quality.

## Example

```python agentic_rag.py theme={null}
import asyncio

from agno.agent import Agent
from agno.knowledge.embedder.cohere import CohereEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reranker.cohere import CohereReranker
from agno.models.anthropic import Claude
from agno.vectordb.lancedb import LanceDb, SearchType

# Create knowledge base with hybrid search and reranking
knowledge = Knowledge(
    vector_db=LanceDb(
        uri="tmp/lancedb",
        table_name="agno_docs",
        search_type=SearchType.hybrid,
        embedder=CohereEmbedder(id="embed-v4.0"),
        reranker=CohereReranker(model="rerank-v3.5"),
    ),
)

# Load content
asyncio.run(
    knowledge.ainsert(url="https://docs.agno.com/introduction/agents.md")
)

# Create agent with knowledge
agent = Agent(
    model=Claude(id="claude-sonnet-4-20250514"),
    knowledge=knowledge,
    search_knowledge=True,
    instructions=[
        "Search your knowledge before answering.",
        "Include sources in your response.",
    ],
    markdown=True,
)

agent.print_response("What are Agents?", stream=True)
```

## Usage

<Steps>
  <Snippet file="create-venv-step.mdx" />

  <Step title="Install dependencies">
    ```bash  theme={null}
    uv pip install -U agno anthropic cohere lancedb tantivy sqlalchemy
    ```
  </Step>

  <Step title="Export your API keys">
    ```bash  theme={null}
    export ANTHROPIC_API_KEY=your_anthropic_api_key_here
    export CO_API_KEY=your_cohere_api_key_here
    ```
  </Step>

  <Step title="Run Agent">
    ```bash  theme={null}
    python agentic_rag.py
    ```
  </Step>
</Steps>

## Configuration Options

### Different Rerankers

```python  theme={null}
# Cohere
from agno.knowledge.reranker.cohere import CohereReranker
reranker = CohereReranker(model="rerank-v3.5")

# Add to vector database
vector_db = LanceDb(
    uri="tmp/lancedb",
    table_name="docs",
    search_type=SearchType.hybrid,
    reranker=reranker,
)
```

### Adjusting Results

```python  theme={null}
knowledge = Knowledge(
    vector_db=vector_db,
    max_results=10,  # Number of results to return after reranking
)
```

## Next Steps

<CardGroup cols={2}>
  <Card title="Hybrid Search" icon="magnifying-glass" href="/knowledge/concepts/search-and-retrieval/hybrid-search">
    Learn more about combining search types
  </Card>

  <Card title="Embedders" icon="code" href="/knowledge/concepts/embedder/overview">
    Choose the right embedding model
  </Card>
</CardGroup>


Built with [Mintlify](https://mintlify.com).

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Custom Retriever

> Implement custom retrieval logic for full control over how agents search knowledge.

Custom retrievers let you implement your own search logic instead of using the default knowledge search. This is useful when you need to:

* Query external APIs or databases directly
* Implement custom ranking or filtering
* Reformulate queries before searching
* Combine multiple data sources

```python  theme={null}
from agno.agent import Agent

def knowledge_retriever(query: str, num_documents: int = 5, **kwargs) -> list[dict]:
    # Your custom retrieval logic here
    return [{"content": "..."}]

agent = Agent(
    knowledge_retriever=knowledge_retriever,
    search_knowledge=True,
)
```

## How It Works

When the agent decides to search for information:

1. The agent calls your `knowledge_retriever` function with the query
2. Your function retrieves documents however you want
3. Results are returned to the agent as a list of dictionaries
4. The agent uses the retrieved content to generate a response

## Retriever Function Signature

```python  theme={null}
from typing import Optional
from agno.agent import Agent

def knowledge_retriever(
    query: str,
    agent: Optional[Agent] = None,
    num_documents: int = 5,
    **kwargs
) -> Optional[list[dict]]:
    """
    Args:
        query: The search query from the agent
        agent: The agent instance (optional, for accessing agent state)
        num_documents: Number of documents to retrieve
        **kwargs: Additional arguments passed from the agent

    Returns:
        List of documents as dictionaries, or None if search fails
    """
    # Your logic here
    return [{"content": "..."}]
```

## Example: Direct Vector Database Query

This example bypasses the Knowledge abstraction and queries Qdrant directly:

```python custom_retriever.py theme={null}
from typing import Optional

from agno.agent import Agent
from agno.knowledge.embedder.openai import OpenAIEmbedder
from qdrant_client import QdrantClient

embedder = OpenAIEmbedder(id="text-embedding-3-small")
qdrant_client = QdrantClient(url="http://localhost:6333")

def knowledge_retriever(
    query: str, num_documents: int = 5, **kwargs
) -> Optional[list[dict]]:
    try:
        # Generate embedding for the query
        query_embedding = embedder.get_embedding(query)

        # Search Qdrant directly
        results = qdrant_client.query_points(
            collection_name="recipes",
            query=query_embedding,
            limit=num_documents,
        )

        return results.model_dump().get("points")
    except Exception as e:
        print(f"Search error: {e}")
        return None

agent = Agent(
    knowledge_retriever=knowledge_retriever,
    search_knowledge=True,
)

agent.print_response("What ingredients do I need for Massaman Gai?")
```

## Example: Query Reformulation

Expand or modify queries before searching:

```python  theme={null}
from agno.knowledge.knowledge import Knowledge

knowledge = Knowledge(vector_db=vector_db)

def knowledge_retriever(query: str, num_documents: int = 5, **kwargs) -> list[dict]:
    # Expand common terms
    expanded_query = query.replace("vacation", "vacation PTO paid time off")
    expanded_query = expanded_query.replace("WFH", "work from home remote")

    # Search with expanded query
    results = knowledge.search(expanded_query, max_results=num_documents)

    return [doc.to_dict() for doc in results]
```

## Example: Multi-Source Retrieval

Combine results from multiple knowledge bases:

```python  theme={null}
def knowledge_retriever(query: str, num_documents: int = 5, **kwargs) -> list[dict]:
    # Search multiple sources
    policy_results = policy_knowledge.search(query, max_results=3)
    faq_results = faq_knowledge.search(query, max_results=3)

    # Combine and deduplicate
    all_results = []
    seen_ids = set()

    for doc in policy_results + faq_results:
        if doc.id not in seen_ids:
            all_results.append(doc.to_dict())
            seen_ids.add(doc.id)

    return all_results[:num_documents]
```

## When to Use Custom Retrievers

| Use Case               | Why Custom Retriever                                       |
| ---------------------- | ---------------------------------------------------------- |
| Direct database access | Skip the Knowledge abstraction for performance             |
| Query expansion        | Add synonyms or related terms before searching             |
| Multi-source search    | Combine results from multiple knowledge bases              |
| External APIs          | Search third-party services (Elasticsearch, Algolia, etc.) |
| Custom ranking         | Implement domain-specific relevance scoring                |
| Conditional logic      | Apply different search strategies based on query type      |

For most use cases, the built-in [Knowledge](/knowledge/overview) search is sufficient. Use custom retrievers when you need full control over the retrieval process.

## Next Steps

<CardGroup cols={2}>
  <Card title="Search & Retrieval" icon="magnifying-glass" href="/knowledge/concepts/search-and-retrieval/overview">
    Learn about built-in search options
  </Card>

  <Card title="Filtering" icon="filter" href="/knowledge/concepts/filters/overview">
    Filter results by metadata
  </Card>
</CardGroup>


Built with [Mintlify](https://mintlify.com).

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Readers

> Convert files, URLs, and text into searchable documents.

Readers transform raw content into `Document` objects that can be chunked, embedded, and stored in your knowledge base. Each reader handles a specific format (PDF, CSV, Markdown, etc.) and extracts text and metadata.

```python  theme={null}
from agno.knowledge.reader.pdf_reader import PDFReader

reader = PDFReader(chunk=True, chunk_size=5000)
documents = reader.read("company_handbook.pdf")
```

## How Readers Work

1. **Parse**: Read the raw content using format-specific logic
2. **Extract**: Pull out text and metadata (page numbers, authors, etc.)
3. **Chunk**: Split large content into smaller pieces (if enabled)
4. **Return**: Provide a list of `Document` objects ready for embedding

```python  theme={null}
# Output structure
Document(
    content="The extracted text...",
    id="unique_id",
    name="document_name",
    meta_data={"page": 1, "source": "handbook.pdf"},
)
```

## Supported Readers

| Reader                  | Description                          |
| ----------------------- | ------------------------------------ |
| `PDFReader`             | Extract text from PDF files          |
| `DoclingReader`         | Process multiple formats via Docling |
| `TextReader`            | Plain text files                     |
| `MarkdownReader`        | Markdown files                       |
| `CSVReader`             | CSV files (rows become documents)    |
| `FieldLabeledCSVReader` | CSV rows as field-labeled text       |
| `JSONReader`            | JSON files                           |
| `PPTXReader`            | PowerPoint presentations             |
| `ArxivReader`           | Academic papers from arXiv           |
| `WikipediaReader`       | Wikipedia articles                   |
| `YouTubeReader`         | YouTube transcripts                  |
| `WebsiteReader`         | Crawl websites recursively           |
| `WebSearchReader`       | Web search results                   |
| `FirecrawlReader`       | Web scraping via Firecrawl API       |

## Using Readers with Knowledge

Pass a reader to `knowledge.insert()` to override automatic format detection:

```python  theme={null}
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.pdf_reader import PDFReader

knowledge = Knowledge(vector_db=vector_db)

# Use custom reader configuration
reader = PDFReader(chunk_size=3000, split_on_pages=True)
knowledge.insert(path="documents/", reader=reader)
```

## Auto-Selection

Agno automatically selects the right reader based on file extension or URL:

```python  theme={null}
from agno.knowledge.reader.reader_factory import ReaderFactory

# By file extension
reader = ReaderFactory.get_reader_for_extension(".pdf")  # PDFReader
reader = ReaderFactory.get_reader_for_extension(".csv")  # CSVReader

# By URL
reader = ReaderFactory.get_reader_for_url("https://youtube.com/watch?v=...")  # YouTubeReader
```

When using `knowledge.insert()`, this happens automatically.

## Configuration

### Chunking

```python  theme={null}
reader = PDFReader(
    chunk=True,           # Enable chunking (default: True)
    chunk_size=5000,      # Characters per chunk
)
```

### Format-Specific Options

```python  theme={null}
# PDF with encryption and OCR
reader = PDFReader(
    password="secret",
    read_images=True,     # OCR for images
    split_on_pages=True,  # One document per page
)

# CSV with custom encoding
reader = CSVReader(
    encoding="latin-1",
)

# Text with encoding override
reader = TextReader(
    encoding="utf-8",
)
```

### Runtime Options

Override settings when calling `read()`:

```python  theme={null}
documents = reader.read(
    "file.pdf",
    name="custom_document_name",  # Override default naming
    password="runtime_password",  # Password at read time
)
```

## Async Processing

All readers support async for better performance with I/O operations:

```python  theme={null}
import asyncio

# Single file
documents = await reader.async_read("file.pdf")

# Batch processing
tasks = [reader.async_read(file) for file in files]
all_documents = await asyncio.gather(*tasks)
```

## Custom Chunking Strategy

Override the default chunking behavior:

```python  theme={null}
from agno.knowledge.chunking.semantic_chunking import SemanticChunking

reader = PDFReader(
    chunk=True,
    chunking_strategy=SemanticChunking(),
)
```

See [Chunking](/knowledge/concepts/chunking/overview) for available strategies.

## Error Handling

Readers return an empty list when processing fails. Check logs for debugging information:

```python  theme={null}
documents = reader.read("corrupted.pdf")
if not documents:
    print("Failed to read file, check logs for details")
```

## Next Steps

<CardGroup cols={2}>
  <Card title="PDF Reader" icon="file-pdf" href="/knowledge/concepts/readers/pdf-reader">
    Extract text from PDFs
  </Card>

  <Card title="Website Reader" icon="globe" href="/knowledge/concepts/readers/website-reader">
    Crawl and index websites
  </Card>

  <Card title="Chunking" icon="scissors" href="/knowledge/concepts/chunking/overview">
    Control how content is split
  </Card>

  <Card title="Vector DB" icon="database" href="/knowledge/concepts/vector-db">
    Store processed documents
  </Card>
</CardGroup>

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Agentic Chunking

Agentic chunking is an intelligent method of splitting documents into smaller chunks by using a model to determine natural breakpoints in the text. Rather than splitting text at fixed character counts, it analyzes the content to find semantically meaningful boundaries like paragraph breaks and topic transitions.

<Steps>
  <Step title="Create a Python file">
    ```python agentic_chunking.py theme={null}
    import asyncio
    from agno.agent import Agent
    from agno.knowledge.chunking.agentic import AgenticChunking
    from agno.knowledge.knowledge import Knowledge
    from agno.knowledge.reader.pdf_reader import PDFReader
    from agno.vectordb.pgvector import PgVector

    db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

    knowledge = Knowledge(
        vector_db=PgVector(table_name="recipes_agentic_chunking", db_url=db_url),
    )

    asyncio.run(knowledge.ainsert(
        url="https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf",
        reader=PDFReader(
            name="Agentic Chunking Reader",
            chunking_strategy=AgenticChunking(),
        ),
    ))

    agent = Agent(
        knowledge=knowledge,
        search_knowledge=True,
    )

    agent.print_response("How to make Thai curry?", markdown=True)
    ```
  </Step>

  <Snippet file="create-venv-step.mdx" />

  <Step title="Install dependencies">
    ```bash  theme={null}
    uv pip install -U agno sqlalchemy psycopg pgvector
    ```
  </Step>

  <Snippet file="run-pgvector-step.mdx" />

  <Step title="Run the script">
    ```bash  theme={null}
    python agentic_chunking.py
    ```
  </Step>
</Steps>

## Custom Prompts

```python  theme={null}
AgenticChunking(
    custom_prompt="Split at major section boundaries. Keep complete clauses together.",
    max_chunk_size=3000,
)
```

<Info>
  Custom prompts override default chunking behavior and are prioritized over default instructions.
</Info>

<Tip>
  **Best Practices:**

  * Always set `max_chunk_size` when using `custom_prompt`.
  * Focus `custom_prompt` on chunking logic only.
  * The default instructions automatically handle the output format constraints.
</Tip>

See [Agentic Chunking with Custom Prompt](/examples/knowledge/chunking/agentic-chunking-custom-prompt) for a complete example.

## Agentic Chunking Params

<Snippet file="chunking-agentic.mdx" />

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Code Chunking

Code chunking splits code based on its structure, leveraging Abstract Syntax Trees (ASTs) to create contextually relevant segments. It uses the Chonkie library to identify natural code boundaries like functions, classes, and blocks. Learn more about [code chunking](https://docs.chonkie.ai/oss/chunkers/code-chunker). This preserves code semantics better than fixed-size chunking by ensuring related code stays together in the same chunk, while splitting occurs at meaningful structural boundaries.

Code chunking supports several built-in tokenizers or a custom `Tokenizer` instance.

<Steps>
  <Step title="Create a Python file">
    <CodeGroup>
      ```python Code Chunking theme={null}
      from agno.agent import Agent
      from agno.knowledge.chunking.code import CodeChunking
      from agno.knowledge.knowledge import Knowledge
      from agno.knowledge.reader.text_reader import TextReader
      from agno.vectordb.pgvector import PgVector

      db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

      knowledge = Knowledge(
          vector_db=PgVector(table_name="python_code_chunking", db_url=db_url),
      )

      knowledge.insert(
          url="https://raw.githubusercontent.com/agno-agi/agno/main/libs/agno/agno/session/workflow.py",
          reader=TextReader(
              chunking_strategy=CodeChunking(
                  tokenizer="gpt2",
                  chunk_size=500,
                  language="python",
              ),
          ),
      )

      agent = Agent(knowledge=knowledge, search_knowledge=True)
      agent.print_response("How does the Workflow class work?", markdown=True)
      ```

      ```python Code Chunking with Custom Tokenizer theme={null}
      from typing import Sequence

      from agno.agent import Agent
      from agno.knowledge.chunking.code import CodeChunking
      from agno.knowledge.knowledge import Knowledge
      from agno.knowledge.reader.text_reader import TextReader
      from agno.vectordb.pgvector import PgVector
      from chonkie.tokenizer import Tokenizer

      db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"


      class LineTokenizer(Tokenizer):
          """Custom tokenizer that counts lines of code."""

          def __init__(self):
              self.vocab = []
              self.token2id = {}

          def __repr__(self) -> str:
              return f"LineTokenizer(vocab_size={len(self.vocab)})"

          def tokenize(self, text: str) -> Sequence[str]:
              if not text:
                  return []
              return text.split("\n")

          def encode(self, text: str) -> Sequence[int]:
              encoded = []
              for token in self.tokenize(text):
                  if token not in self.token2id:
                      self.token2id[token] = len(self.vocab)
                      self.vocab.append(token)
                  encoded.append(self.token2id[token])
              return encoded

          def decode(self, tokens: Sequence[int]) -> str:
              try:
                  return "\n".join([self.vocab[token] for token in tokens])
              except Exception as e:
                  raise ValueError(
                      f"Decoding failed. Tokens: {tokens} not found in vocab."
                  ) from e

          def count_tokens(self, text: str) -> int:
              if not text:
                  return 0
              return len(text.split("\n"))


      knowledge = Knowledge(
          vector_db=PgVector(table_name="code_custom_tokenizer", db_url=db_url),
      )

      knowledge.insert(
          url="https://raw.githubusercontent.com/agno-agi/agno/main/libs/agno/agno/session/workflow.py",
          reader=TextReader(
              chunking_strategy=CodeChunking(
                  tokenizer=LineTokenizer(),
                  chunk_size=500,
                  language="python",
              ),
          ),
      )

      agent = Agent(knowledge=knowledge, search_knowledge=True)
      agent.print_response("How does the Workflow class work?", markdown=True)
      ```
    </CodeGroup>
  </Step>

  <Snippet file="create-venv-step.mdx" />

  <Step title="Install dependencies">
    ```bash  theme={null}
    uv pip install -U agno sqlalchemy psycopg pgvector "chonkie[code]" openai
    ```
  </Step>

  <Snippet file="set-openai-key.mdx" />

  <Snippet file="run-pgvector-step.mdx" />

  <Step title="Run the script">
    ```bash  theme={null}
    python code_chunking.py
    ```
  </Step>
</Steps>

## Code Chunking Params

<Snippet file="chunking-code.mdx" />

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# ChromaDB Vector Database

> Use ChromaDB as a vector database for your Knowledge Base.

## Setup

```shell  theme={null}
uv pip install chromadb
```

## Example

```python agent_with_knowledge.py theme={null}
import asyncio

from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.chroma import ChromaDb

# Create Knowledge Instance with ChromaDB
knowledge = Knowledge(
    name="Basic SDK Knowledge Base",
    description="Agno 2.0 Knowledge Implementation with ChromaDB",
    vector_db=ChromaDb(
        collection="vectors", path="tmp/chromadb", persistent_client=True
    ),
)

asyncio.run(
    knowledge.ainsert(
        name="Recipes",
        url="https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf",
        metadata={"doc_type": "recipe_book"},
    )
)

# Create and use the agent
agent = Agent(knowledge=knowledge)
agent.print_response("List down the ingredients to make Massaman Gai", markdown=True)

# Delete operations examples
vector_db = knowledge.vector_db
vector_db.delete_by_name("Recipes")
# or
vector_db.delete_by_metadata({"user_tag": "Recipes from website"})
```

### For hosted ChromaDB (Chroma Cloud)

```python  theme={null}
from chromadb.config import Settings

vector_db = ChromaDb(
    collection="vectors",
    settings=Settings(
        chroma_api_impl="chromadb.api.fastapi.FastAPI",
        chroma_server_host="your-tenant-id.api.trychroma.com",
        chroma_server_http_port=443,
        chroma_server_ssl_enabled=True,
        chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
        chroma_client_auth_credentials="your-api-key"
    )
)
```

<Card title="Async Support ⚡">
  <div className="mt-2">
    <p>
      ChromaDB also supports asynchronous operations, enabling concurrency and leading to better performance.
    </p>

    ```python async_chroma_db.py theme={null}
    # install chromadb - `pip install chromadb`

    import asyncio

    from agno.agent import Agent
    from agno.knowledge.knowledge import Knowledge
    from agno.vectordb.chroma import ChromaDb

    # Initialize ChromaDB
    vector_db = ChromaDb(collection="recipes", path="tmp/chromadb", persistent_client=True)

    # Create knowledge base
    knowledge = Knowledge(
        vector_db=vector_db,
    )

    # Create and use the agent
    agent = Agent(knowledge=knowledge)

    if __name__ == "__main__":
        # Comment out after first run
        asyncio.run(
            knowledge.ainsert(url="https://docs.agno.com/introduction/agents.md")
        )

        # Create and use the agent
        asyncio.run(
            agent.aprint_response("What is the purpose of an Agno Agent?", markdown=True)
        )
    ```

    <Tip className="mt-4">
      Use <code>ainsert()</code> and <code>aprint\_response()</code> methods with <code>asyncio.run()</code> for non-blocking operations in high-throughput applications.
    </Tip>
  </div>
</Card>

## ChromaDb Params

<Snippet file="vectordb_chromadb_params.mdx" />

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# ChromaDB

## Code

```python cookbook/08_knowledge/vector_db/chroma_db/chroma_db.py theme={null}
from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.chroma import ChromaDb

# Create Knowledge Instance with ChromaDB
knowledge = Knowledge(
    name="Basic SDK Knowledge Base",
    description="Agno 2.0 Knowledge Implementation with ChromaDB",
    vector_db=ChromaDb(
        collection="vectors", path="tmp/chromadb", persistent_client=True
    ),
)

knowledge.insert(
        name="Recipes",
        url="https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf",
        metadata={"doc_type": "recipe_book"},
    )

# Create and use the agent
agent = Agent(knowledge=knowledge)
agent.print_response("List down the ingredients to make Massaman Gai", markdown=True)

# Delete operations examples
vector_db = knowledge.vector_db
vector_db.delete_by_name("Recipes")
# or
vector_db.delete_by_metadata({"user_tag": "Recipes from website"})
```

## Usage

<Steps>
  <Snippet file="create-venv-step.mdx" />

  <Step title="Install dependencies">
    ```bash  theme={null}
    uv pip install -U chromadb pypdf openai agno
    ```
  </Step>

  <Step title="Set environment variables">
    ```bash  theme={null}
    export OPENAI_API_KEY=xxx
    ```
  </Step>

  <Step title="Run Agent">
    ```bash  theme={null}
    python cookbook/08_knowledge/vector_db/chroma_db/chroma_db.py
    ```
  </Step>
</Steps>


> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# ChromaDB Async

## Code

```python cookbook/08_knowledge/vector_db/chroma_db/async_chroma_db.py theme={null}

import asyncio

from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.chroma import ChromaDb

vector_db = ChromaDb(collection="recipes", path="tmp/chromadb", persistent_client=True)

knowledge = Knowledge(
    vector_db=vector_db,
)

agent = Agent(knowledge=knowledge)

if __name__ == "__main__":
    asyncio.run(
        knowledge.ainsert(url="https://docs.agno.com/introduction/agents.md")
    )

    asyncio.run(
        agent.aprint_response("What is the purpose of an Agno Agent?", markdown=True)
    )
```

## Usage

<Steps>
  <Snippet file="create-venv-step.mdx" />

  <Step title="Install dependencies">
    ```bash  theme={null}
    uv pip install -U chromadb pypdf openai agno
    ```
  </Step>

  <Step title="Set environment variables">
    ```bash  theme={null}
    export OPENAI_API_KEY=xxx
    ```
  </Step>

  <Step title="Run Agent">
    ```bash  theme={null}
    python cookbook/08_knowledge/vector_db/chroma_db/async_chroma_db.py
    ```
  </Step>
</Steps>


> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Chroma Hybrid Search

This example demonstrates how to use ChromaDB with hybrid search,
which combines dense vector similarity search (semantic) with
full-text search (keyword/lexical) using RRF fusion.

Hybrid search is useful when you want to:

* Combine semantic understanding with exact keyword matching
* Improve retrieval accuracy for queries with specific terms
* Handle both conceptual and lexical search needs

The RRF algorithm fuses rankings from both search methods using:

```
RRF(d) = sum(1 / (k + rank_i(d))) for each ranking i
```

## Code

```python cookbook/08_knowledge/vector_db/chroma_db/chroma_db_hybrid_search.py theme={null}
import asyncio

from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.chroma import ChromaDb
from agno.vectordb.search import SearchType

# Create Knowledge Instance with ChromaDB using Hybrid Search
knowledge = Knowledge(
    name="Thai Recipes Knowledge Base",
    description="Knowledge base for Thai recipes with hybrid search (RRF fusion)",
    vector_db=ChromaDb(
        collection="thai_recipes_hybrid",
        path="tmp/chromadb_hybrid",
        persistent_client=True,
        # Enable hybrid search - combines vector similarity with keyword matching using RRF
        search_type=SearchType.hybrid,
        # RRF (Reciprocal Rank Fusion) constant - controls ranking smoothness.
        # Higher values (e.g., 60) give more weight to lower-ranked results,
        # Lower values make top results more dominant. Default is 60 (per original RRF paper).
        hybrid_rrf_k=60,
    ),
)

# Load content into the knowledge base
asyncio.run(
    knowledge.ainsert(
        name="Thai Recipes",
        url="https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf",
        metadata={"doc_type": "recipe_book", "cuisine": "thai"},
    )
)

# Create an agent with the hybrid search knowledge base
agent = Agent(
    knowledge=knowledge,
    search_knowledge=True,
    instructions="You are a helpful Thai cooking assistant. Use the knowledge base to answer questions about Thai recipes.",
)

# Hybrid search will:
# 1. Find semantically similar documents (via dense embeddings)
# 2. Find documents containing query keywords (via FTS)
# 3. Fuse results using RRF for optimal ranking
agent.print_response("What are the ingredients for Massaman curry?", markdown=True)
```

## Usage

<Steps>
  <Snippet file="create-venv-step.mdx" />

  <Step title="Install dependencies">
    ```bash  theme={null}
    uv pip install -U chromadb openai agno
    ```
  </Step>

  <Step title="Run Agent">
    ```bash  theme={null}
    python cookbook/08_knowledge/vector_db/chroma_db/chroma_db_hybrid_search.py
    ```
  </Step>
</Steps>

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.agno.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Performance Tips

> Optimize knowledge base performance, search quality, and content loading speed.

Agno's defaults work well for most use cases. But if you're seeing slow searches, memory issues, or poor results, a few strategic changes might help.

## Quick Wins

### 1. Choose the Right Vector Database

Database choice has the biggest impact at scale:

| Database         | Use Case                           |
| ---------------- | ---------------------------------- |
| LanceDB/ChromaDB | Development, testing (zero setup)  |
| PgVector         | Production up to 1M docs, need SQL |
| Pinecone         | Managed service, auto-scaling      |

```python  theme={null}
from agno.vectordb.lancedb import LanceDb
from agno.vectordb.pgvector import PgVector

# Development
dev_db = LanceDb(table_name="docs", uri="./local_db")

# Production
prod_db = PgVector(table_name="docs", db_url=db_url)
```

### 2. Skip Already-Processed Files

The biggest speed-up when re-running ingestion:

```python  theme={null}
knowledge.insert(
    path="documents/",
    skip_if_exists=True,  # Don't reprocess existing files
)

# Batch loading with filters
knowledge.insert_many(
    paths=["docs/", "policies/"],
    skip_if_exists=True,
    include=["*.pdf", "*.md"],
    exclude=["*temp*", "*draft*"]
)
```

### 3. Use Metadata Filters

Narrow searches before search:

```python  theme={null}
# Slow: search everything
results = knowledge.search("deployment process")

# Fast: filter first, then search
results = knowledge.search(
    query="deployment process",
    filters={"department": "engineering", "type": "procedure"}
)

# Validate filters to catch typos
valid_filters, invalid_keys = knowledge.validate_filters({
    "department": "engineering",
    "invalid_key": "value"  # This gets flagged
})
```

### 4. Match Chunking to Content

| Strategy   | Speed  | Quality | Best For          |
| ---------- | ------ | ------- | ----------------- |
| Fixed Size | Fast   | Good    | Uniform content   |
| Semantic   | Slower | Best    | Complex documents |
| Recursive  | Fast   | Good    | Structured docs   |

```python  theme={null}
from agno.knowledge.chunking.fixed_size_chunking import FixedSizeChunking
from agno.knowledge.chunking.semantic_chunking import SemanticChunking

# Fast processing
FixedSizeChunking(chunk_size=5000, overlap=200)

# Better quality (slower)
SemanticChunking(similarity_threshold=0.5)
```

### 5. Use Async for Batch Operations

Process multiple sources concurrently:

```python  theme={null}
import asyncio

async def load_knowledge():
    await asyncio.gather(
        knowledge.ainsert(path="docs/hr/"),
        knowledge.ainsert(path="docs/engineering/"),
        knowledge.ainsert(url="https://company.com/api-docs"),
    )

asyncio.run(load_knowledge())
```

## Common Issues

### Irrelevant Search Results

**Causes:** Chunks too large/small, wrong chunking strategy.

**Fixes:**

* Try semantic chunking for better context
* Increase `max_results` to check if relevant results are ranked lower
* Add metadata filters to narrow scope

```python  theme={null}
# Debug search quality
results = knowledge.search("your query", max_results=10)
for doc in results:
    print(doc.content[:200])
```

### Slow Content Loading

**Causes:** Reprocessing existing files, semantic chunking on large datasets.

**Fixes:**

* Use `skip_if_exists=True`
* Switch to fixed-size chunking
* Process in batches

```python  theme={null}
# Only process new PDFs
knowledge.insert(
    path="documents/",
    include=["*.pdf"],
    exclude=["*draft*", "*backup*"],
    skip_if_exists=True,
)
```

### Memory Issues

**Causes:** Loading too many large files at once, chunk sizes too large.

**Fixes:**

* Process in smaller batches
* Reduce chunk size
* Use include/exclude patterns
* Clear outdated content with `knowledge.remove_content_by_id(content_id)`

## Advanced Optimizations

### Hybrid Search

Combine vector and keyword search:

```python  theme={null}
from agno.vectordb.pgvector import PgVector, SearchType

vector_db = PgVector(
    table_name="docs",
    db_url=db_url,
    search_type=SearchType.hybrid,
)
```

### Reranking

Improve result ordering:

```python  theme={null}
from agno.knowledge.reranker.cohere import CohereReranker

vector_db = PgVector(
    table_name="docs",
    db_url=db_url,
    reranker=CohereReranker(model="rerank-v3.5", top_n=10),
)
```

### Smaller Embedding Dimensions

Trade slight quality for faster search:

```python  theme={null}
from agno.knowledge.embedder.openai import OpenAIEmbedder

embedder = OpenAIEmbedder(
    id="text-embedding-3-large",
    dimensions=1024,  # Instead of 3072
)
```

## Monitoring

```python  theme={null}
import time

# Time searches
start = time.time()
results = knowledge.search("test query", max_results=5)
print(f"Search: {time.time() - start:.2f}s")

# Check failed content
content_list, total = knowledge.get_content()
for content in content_list:
    if content.status == "failed":
        status, message = knowledge.get_content_status(content.id)
        print(f"{content.name}: {message}")
```

## Next Steps

<CardGroup cols={2}>
  <Card title="Chunking" icon="scissors" href="/knowledge/concepts/chunking/overview">
    How chunking affects performance
  </Card>

  <Card title="Vector DB" icon="database" href="/knowledge/concepts/vector-db">
    Compare database options
  </Card>

  <Card title="Hybrid Search" icon="magnifying-glass" href="/knowledge/concepts/search-and-retrieval/hybrid-search">
    Combine vector and keyword search
  </Card>

  <Card title="Embedders" icon="brain" href="/knowledge/concepts/embedder/overview">
    Choose the right embedder
  </Card>
</CardGroup>


Built with [Mintlify](https://mintlify.com).