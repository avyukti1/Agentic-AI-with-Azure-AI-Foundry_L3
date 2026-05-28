# Application-LOGIC and Agents-LOGIC

This file explains how the project works at two levels:

- **Application-LOGIC**: how the React UI, Express server, session state, document upload, and API calls work together.
- **Agents-LOGIC**: how the app selects an agent, sends the request to Azure AI Foundry, handles ReAct-style trace steps, and returns the final answer.

## 1. High-Level Block Diagram

```mermaid
flowchart LR
    User[User] --> UI[React UI<br/>src/main.jsx]
    UI --> API[Express API<br/>server/index.js]
    API --> Memory[(In-memory Maps<br/>sessions + documents)]
    API --> Azure[Azure AI Foundry<br/>AgentsClient]
    API --> PyRef[Optional Python Agent Reference<br/>server/hr-agent-reference.py]
    Azure --> API
    PyRef --> API
    API --> UI
    UI --> User
```

## 2. Application-LOGIC

### Step 1: App starts

1. `npm run dev` starts both:
   - React/Vite client on `http://127.0.0.1:5173`
   - Express server on `http://127.0.0.1:5000`
2. React loads `src/main.jsx`.
3. Express loads `server/index.js`.
4. Express reads Azure configuration from `.env`.
5. Express creates an Azure `AgentsClient` using credentials from `@azure/identity`.

### Step 2: UI loads runtime configuration

```mermaid
sequenceDiagram
    participant Browser as React Browser UI
    participant Server as Express Server

    Browser->>Server: GET /api/config
    Server-->>Browser: deployment, model version, temperature, topP, agents
    Browser->>Browser: Show runtime panel and agent list
```

The UI calls `/api/config` on page load. The server returns public runtime metadata and the configured agent portfolio:

- General agent
- HR agent
- IT agent
- ServiceNow agent

Azure credentials and secrets stay only on the server.

### Step 3: User sends a chat message

```mermaid
flowchart TD
    A[User types message] --> B[React sendMessage]
    B --> C[POST /api/chat]
    C --> D[Server validates message]
    D --> E[Resolve best agent]
    E --> F[Get uploaded document context if available]
    F --> G[Run selected agent]
    G --> H[Return answer + trace + selected agent]
    H --> I[React updates chat and trace panel]
```

React sends this payload:

```json
{
  "message": "user request",
  "agentKey": "general/hr/it/servicenow",
  "sessionId": "session-id"
}
```

The server responds with:

```json
{
  "answer": "assistant response",
  "threadId": "azure-thread-id-or-null",
  "trace": [],
  "agent": {
    "key": "hr",
    "name": "HRAgent",
    "scope": "HR policy and employee support"
  }
}
```

### Step 4: User uploads a document

```mermaid
flowchart TD
    A[Upload PDF/DOCX/TXT] --> B[React builds FormData]
    B --> C[POST /api/documents]
    C --> D{File type}
    D -->|TXT| E[Read UTF-8 text]
    D -->|PDF| F[Extract with pdf-parse]
    D -->|DOCX| G[Extract with mammoth]
    E --> H[Normalize text]
    F --> H
    G --> H
    H --> I[Store in documents Map by session + agent]
    I --> J[Return file metadata]
    J --> K[UI shows attached document]
```

The document text is stored in server memory only. When the user asks a document-related question, the server injects the extracted text into the user message as context.

### Step 5: User generates structured output

```mermaid
flowchart TD
    A[User opens Structured Output tab] --> B[Select schema]
    B --> C[Enter task]
    C --> D[POST /api/structured]
    D --> E[Server builds JSON-only prompt]
    E --> F[Run selected Azure agent]
    F --> G[Parse JSON from agent response]
    G --> H[Return API-ready JSON]
    H --> I[UI displays JSON]
```

Available schemas are:

- Service ticket
- Action plan
- Document summary

## 3. Agents-LOGIC

### Agent portfolio

The Express server builds the agent list from `.env` values:

| Agent key | Purpose |
| --- | --- |
| `general` | General reasoning |
| `hr` | HR policy and employee support |
| `it` | IT helpdesk and access support |
| `servicenow` | ServiceNow ticket guidance |

### Agent selection flow

```mermaid
flowchart TD
    A[Incoming user message] --> B{Contains HR terms?}
    B -->|Yes| HR[Select HR agent]
    B -->|No| C{Contains ServiceNow terms?}
    C -->|Yes| SN[Select ServiceNow agent]
    C -->|No| D{Contains IT terms?}
    D -->|Yes| IT[Select IT agent]
    D -->|No| G[Use currently selected UI agent]
```

The function `resolveAgentForMessage()` performs keyword-based routing:

1. HR words route to the HR agent.
2. ServiceNow/ticketing words route to the ServiceNow agent.
3. IT/helpdesk words route to the IT agent.
4. Otherwise, the server uses the agent selected in the UI.

### ReAct-style execution

The project does not expose hidden chain-of-thought. Instead, it returns a safe operational trace:

```mermaid
flowchart LR
    Reason[Reason<br/>Select agent and schema/context] --> Act[Act<br/>Create thread, add message, run agent]
    Act --> Observe[Observe<br/>Poll run status and attach document context]
    Observe --> Final[Final<br/>Return assistant answer or JSON]
```

The trace shown in the UI contains stages such as:

- `Reason`: selected agent or schema
- `Act`: created/used thread, added message, called agent
- `Observe`: run completed, document context attached
- `Final`: answer or JSON received
- `Error`: server or Azure failure details

### Normal Azure AI Foundry path

```mermaid
sequenceDiagram
    participant UI as React UI
    participant API as Express API
    participant Client as AgentsClient
    participant Foundry as Azure AI Foundry Agent

    UI->>API: POST /api/chat
    API->>API: Select agent
    API->>API: Get or create session thread
    API->>Client: client.messages.create(threadId, user message)
    API->>Client: client.runs.createAndPoll(threadId, agent.id)
    Client->>Foundry: Run agent
    Foundry-->>Client: Completed run
    API->>Client: client.messages.list(threadId)
    Client-->>API: Latest assistant message
    API-->>UI: answer + trace + selected agent
```

Important details:

1. A thread is reused per `sessionId + agentKey`.
2. Uploaded document context is added to the message when available.
3. `additionalInstructions` tells the agent to use a private Reason/Act/Observe loop and return only a concise answer.
4. The server polls until the run finishes.
5. The latest assistant message is returned to the browser.

### Optional Python agent-reference path

For HR, IT, or ServiceNow, the server can use an agent reference instead of the JavaScript `AgentsClient` thread path if these environment variables are configured:

- `AZURE_AI_HR_AGENT_REFERENCE_NAME`
- `AZURE_AI_IT_AGENT_REFERENCE_NAME`
- `AZURE_AI_SERVICENOW_AGENT_REFERENCE_NAME`

```mermaid
sequenceDiagram
    participant API as Express API
    participant Python as hr-agent-reference.py
    participant Foundry as Azure AI Foundry Responses API

    API->>API: Detect configured agent reference
    API->>Python: Spawn python and pass JSON through stdin
    Python->>Foundry: responses.create with agent_reference
    Foundry-->>Python: output_text
    Python-->>API: JSON answer through stdout
    API-->>API: Add trace and return answer
```

The Python script:

1. Reads JSON from `stdin`.
2. Uses `AIProjectClient`.
3. Gets an OpenAI-compatible client.
4. Calls `responses.create()` with `agent_reference`.
5. Prints `{ "answer": "..." }` to `stdout`.

## 4. Session and Document Memory

```mermaid
flowchart TD
    A[sessionId from React] --> B[getSessionKey]
    C[agentKey] --> B
    B --> D["sessionId:agentKey"]
    D --> E[(sessions Map<br/>Azure thread ids)]
    D --> F[(documents Map<br/>uploaded document text)]
```

The server keeps two in-memory maps:

- `sessions`: stores Azure thread IDs by `sessionId:agentKey`.
- `documents`: stores uploaded document text by `sessionId:agentKey`.

When the user clicks **New thread**, React calls:

```http
DELETE /api/session/:sessionId
```

The server deletes all thread and document entries for that session.

## 5. End-to-End Flow Summary

```mermaid
flowchart TD
    A[Start app] --> B[React requests /api/config]
    B --> C[User selects or auto-routes agent]
    C --> D{User action}
    D -->|Chat| E[POST /api/chat]
    D -->|Upload document| F[POST /api/documents]
    D -->|Structured JSON| G[POST /api/structured]
    E --> H[Resolve agent + document context]
    F --> I[Extract and store document text]
    G --> J[Build JSON-only structured prompt]
    H --> K[Azure Foundry thread or Python agent reference]
    J --> K
    K --> L[Return answer, JSON, trace, selected agent]
    L --> M[React updates conversation, JSON panel, trace, insights]
```

In short: the React app is the user workspace, Express is the secure orchestration layer, Azure AI Foundry is the reasoning backend, and the agent logic decides which specialist agent should handle each request.
