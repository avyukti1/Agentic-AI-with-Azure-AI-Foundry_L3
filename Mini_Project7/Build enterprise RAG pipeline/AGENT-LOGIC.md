# Agent Logic

This document explains the Azure AI Foundry Agent RAG flow demonstrated by `RAG_executed.ipynb`.

The agent notebook creates a Foundry Agent, attaches Azure AI Search as a tool, starts a conversation, and calls the Responses API with an agent reference. The model answers only after using the configured search tool.

## Agent Responsibilities

1. Load project and search configuration from `.env`.
2. Connect to the Azure AI Foundry project.
3. Resolve the Azure AI Search project connection.
4. Create a Foundry Agent version.
5. Attach Azure AI Search as an agent tool.
6. Create a conversation.
7. Send the user question through the Responses API.
8. Require tool use.
9. Return a grounded answer with citations.

## High-Level Flow

```mermaid
flowchart TD
    A[Start RAG_executed.ipynb] --> B[Install and Import Packages]
    B --> C[Load .env Values]
    C --> D[Create AIProjectClient]
    D --> E[Create OpenAI-Compatible Client]
    E --> F[List Foundry Project Connections]
    F --> G{AI Search Connection Found?}
    G -- No --> X[Fix AI_SEARCH_CONNECTION_NAME or Foundry Connection]
    G -- Yes --> H[Store Search Connection ID]
    H --> I[Create Agent Version]
    I --> J[Attach Azure AI Search Tool]
    J --> K[Create Conversation]
    K --> L[Define User Question]
    L --> M[Responses API Call]
    M --> N[Tool Choice Required]
    N --> O[Agent Searches Azure AI Search]
    O --> P[Model Generates Grounded Answer]
    P --> Q[Print Agent Response]
```

## Schematic Block Diagram

```mermaid
flowchart LR
    subgraph Notebook[RAG_executed.ipynb]
        ENV[.env]
        PC[AIProjectClient]
        OAI[OpenAI-Compatible Client]
        Call[responses.create]
    end

    subgraph Foundry[Azure AI Foundry Project]
        Conn[AI Search Project Connection]
        Agent[Foundry RAG Agent]
        Conv[Conversation]
    end

    subgraph Search[Azure AI Search]
        Index[Search Index]
        Fields[id, content, title, source_file, department, security_level, chunk_id, content_vector]
    end

    subgraph Model[Azure OpenAI]
        Chat[Chat Model Deployment]
    end

    ENV --> PC
    PC --> OAI
    PC --> Conn
    PC --> Agent
    Agent --> Conn
    Conn --> Index
    Index --> Fields
    OAI --> Conv
    Call --> Conv
    Call --> Agent
    Agent --> Index
    Agent --> Chat
    Chat --> Call
```

## Wiring

| Notebook variable | Source | Used by |
| --- | --- | --- |
| `foundry_project_endpoint` | `FOUNDRY_PROJECT_ENDPOINT` | `AIProjectClient` |
| `model_deployment_name` | `MODEL_DEPLOYMENT_NAME` | Agent model |
| `ai_search_connection_name` | `AI_SEARCH_CONNECTION_NAME` | Foundry project connection lookup |
| `ai_search_index_name` | `AI_SEARCH_INDEX_NAME` | `AISearchIndexResource` |
| `connection_id` | Foundry project connection result | Agent Search tool |
| `agent` | `project_client.agents.create_version(...)` | Responses API agent reference |
| `conversation` | `openai_client.conversations.create()` | Responses API conversation |
| `user_input` | Notebook question cell | Responses API input |

## Retrieval Configuration

For the current index, use semantic retrieval:

```python
query_type = AzureAISearchQueryType.SEMANTIC
```

Why: the current Azure AI Search index has a normal vector field named `content_vector`, but it does not have an integrated vectorizer attached to the index. The Foundry Agent tool's `VECTOR_*` query types require an integrated vectorizer.

Avoid this for the current index:

```python
query_type = AzureAISearchQueryType.VECTOR_SEMANTIC_HYBRID
```

Use `VECTOR_SEMANTIC_HYBRID` only after the Azure AI Search index is recreated or updated with integrated vectorization support.

## Response API Wiring

The final response call requires tool use:

```python
response = openai_client.responses.create(
    tool_choice="required",
    conversation=conversation.id,
    input=user_input,
    extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
)
```

`tool_choice="required"` tells the runtime to call the configured agent tool before producing the answer.

The `extra_body` block tells the Responses API to use the Foundry Agent created earlier instead of making a direct model-only call.

## End-To-End Sequence

```mermaid
sequenceDiagram
    participant User
    participant Notebook as RAG_executed.ipynb
    participant Project as AIProjectClient
    participant Agent as Foundry Agent
    participant Search as Azure AI Search
    participant Model as Azure OpenAI Model
    participant Responses as Responses API

    User->>Notebook: Provide question
    Notebook->>Project: Resolve AI Search connection
    Notebook->>Project: Create agent version with Search tool
    Notebook->>Responses: responses.create with agent reference
    Responses->>Agent: Run agent
    Agent->>Search: Search configured index
    Search-->>Agent: Return relevant documents
    Agent->>Model: Send question + retrieved context
    Model-->>Agent: Generate grounded answer
    Agent-->>Responses: Return final answer
    Responses-->>Notebook: Response object
    Notebook-->>User: Print response.output_text
```

## How To Run

1. Open `RAG_executed.ipynb`.
2. Restart the kernel.
3. Run all cells from the top.
4. Confirm the agent creation cell prints the agent name, version, and ID.
5. Run the final response cell.

If the final cell still reports `vector_semantic_hybrid`, restart the kernel and rerun the agent creation cell. That error means the active in-memory agent still points to an older vector-hybrid configuration.
