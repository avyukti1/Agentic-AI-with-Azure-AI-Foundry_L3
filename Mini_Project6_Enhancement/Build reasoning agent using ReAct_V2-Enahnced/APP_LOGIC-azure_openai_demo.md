# Azure OpenAI Demo Application Logic

This document explains the working of `azure_openai_demo.py` and `llm_client.py`.

The original ReAct demo in `app.py` remains deterministic. This Azure OpenAI demo is a separate live-LLM demo that sends the user question to a real Azure OpenAI deployment and prints the model response.

## Files Used

- `azure_openai_demo.py`: command-line entry point for the real LLM demo.
- `llm_client.py`: reusable Azure OpenAI client helper.
- `.env`: stores Azure OpenAI endpoint, API key, deployment name, and API version.
- `requirements.txt`: lists `openai` and `python-dotenv`.

## High-Level Block Diagram

```text
+----------------------+
| User Question        |
+----------+-----------+
           |
           v
+----------------------+
| azure_openai_demo.py |
| Read CLI/input text  |
+----------+-----------+
           |
           v
+----------------------+
| ask_llm(user_input)  |
| from llm_client.py   |
+----------+-----------+
           |
           v
+----------------------+
| Load .env settings   |
| Validate config      |
+----------+-----------+
           |
           v
+----------------------+
| Build OpenAI Client  |
| Azure endpoint       |
+----------+-----------+
           |
           v
+----------------------+
| Azure OpenAI Model   |
| ajay-gpt-4o          |
+----------+-----------+
           |
           v
+----------------------+
| Model Answer         |
+----------+-----------+
           |
           v
+----------------------+
| Print in terminal    |
+----------------------+
```

## Runtime Flowchart

```text
Start
  |
  v
Run: python azure_openai_demo.py "question"
  |
  v
Does command-line question exist?
  |
  +-- Yes --> Use command-line text
  |
  +-- No --> Ask user with input("Ask the LLM:")
  |
  v
Call ask_llm(user_input)
  |
  v
Load environment variables from .env
  |
  v
Read required values:
  - AZURE_OPENAI_ENDPOINT
  - AZURE_OPENAI_API_KEY
  - AZURE_OPENAI_DEPLOYMENT_NAME
  |
  v
Read optional/default value:
  - AZURE_OPENAI_API_VERSION
  |
  v
Is endpoint using /openai/v1?
  |
  +-- Yes --> Create OpenAI(api_key, base_url)
  |
  +-- No --> Create AzureOpenAI(api_key, azure_endpoint, api_version)
  |
  v
Send chat.completions.create request
  |
  v
Receive model response
  |
  v
Return response text
  |
  v
Print answer
  |
  v
End
```

## `azure_openai_demo.py` Logic

### Purpose

`azure_openai_demo.py` is the runnable app file for the real LLM call.

It does not contain Azure OpenAI setup directly. Instead, it imports `ask_llm` from `llm_client.py`.

### Logical Steps

1. Import `argparse`.
2. Import `ask_llm` from `llm_client.py`.
3. Define `parse_args()` to read a question from the command line.
4. Join command-line words into one text question.
5. If no question is passed, ask interactively using `input()`.
6. Call `answer = ask_llm(user_input)`.
7. Print the answer returned by the real Azure OpenAI model.

### Mini Block Diagram

```text
+-------------------------------+
| azure_openai_demo.py           |
+---------------+---------------+
                |
                v
+-------------------------------+
| parse_args()                   |
| Read question from CLI         |
+---------------+---------------+
                |
                v
+-------------------------------+
| user_input                     |
| CLI text or interactive input  |
+---------------+---------------+
                |
                v
+-------------------------------+
| ask_llm(user_input)            |
+---------------+---------------+
                |
                v
+-------------------------------+
| print(answer)                  |
+-------------------------------+
```

## `llm_client.py` Logic

### Purpose

`llm_client.py` keeps all Azure OpenAI connection logic in one reusable place.

This makes the project easier to upgrade later. For example, `app.py`, a web API, or a tool-calling agent can reuse the same `ask_llm()` function.

## Environment Configuration

The file reads these values from `.env`:

```text
AZURE_OPENAI_ENDPOINT=https://ajay-agent-project111-resource.openai.azure.com/openai/v1
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=ajay-gpt-4o
AZURE_OPENAI_API_VERSION=2024-11-20
```

### Configuration Flow

```text
+----------------+
| .env file      |
+-------+--------+
        |
        v
+------------------------+
| load_dotenv()          |
+-----------+------------+
            |
            v
+------------------------+
| _get_required_env()    |
| Validate required vars |
+-----------+------------+
            |
            v
+------------------------+
| _build_client()        |
| Create SDK client      |
+------------------------+
```

## Function: `_get_required_env(name)`

### Purpose

This helper checks whether a required environment variable exists.

### Logic

1. Read the value using `os.getenv(name, "")`.
2. Strip extra spaces.
3. If the value is empty, raise a clear error.
4. Return the valid value.

### Why It Is Useful

Without this helper, missing `.env` values may create confusing SDK errors. This function fails early with a clear message such as:

```text
Missing required environment variable: AZURE_OPENAI_API_KEY
```

## Function: `_build_client()`

### Purpose

This function creates the correct SDK client for the configured Azure OpenAI endpoint.

The project supports two endpoint styles:

- New OpenAI-compatible Azure endpoint ending with `/openai/v1`
- Older Azure OpenAI SDK endpoint without `/openai/v1`

### Client Selection Flowchart

```text
Start _build_client()
  |
  v
load_dotenv()
  |
  v
Read endpoint, api_key, deployment_name
  |
  v
Read api_version or use default 2024-11-20
  |
  v
Does endpoint end with /openai/v1?
  |
  +-- Yes --> client = OpenAI(api_key=api_key, base_url=endpoint)
  |
  +-- No --> client = AzureOpenAI(
  |              api_key=api_key,
  |              azure_endpoint=endpoint,
  |              api_version=api_version
  |            )
  |
  v
Return client and deployment_name
```

### Why Two Client Types?

The configured endpoint is:

```text
https://ajay-agent-project111-resource.openai.azure.com/openai/v1
```

Because it ends with `/openai/v1`, it can use the OpenAI-compatible client:

```python
OpenAI(api_key=api_key, base_url=endpoint)
```

If a future endpoint is configured as a classic Azure endpoint, the code can use:

```python
AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)
```

## Function: `ask_llm(user_input)`

### Purpose

This is the main function used by the app.

It accepts a user question, sends it to the configured Azure OpenAI deployment, and returns the response text.

### Message Structure

The function sends two messages:

```text
System Message:
You are a helpful IT helpdesk assistant...

User Message:
The actual user issue or question
```

### LLM Call Block Diagram

```text
+---------------------+
| ask_llm(user_input) |
+----------+----------+
           |
           v
+---------------------+
| _build_client()     |
+----------+----------+
           |
           v
+-----------------------------+
| client.chat.completions     |
| .create(...)                |
+----------+------------------+
           |
           v
+-----------------------------+
| Azure OpenAI Deployment     |
| model = ajay-gpt-4o         |
+----------+------------------+
           |
           v
+-----------------------------+
| response.choices[0]         |
| .message.content            |
+----------+------------------+
           |
           v
+-----------------------------+
| Return answer text          |
+-----------------------------+
```

### Logical Steps

1. Call `_build_client()`.
2. Receive the configured SDK client and deployment name.
3. Call `client.chat.completions.create(...)`.
4. Pass the deployment name as the `model`.
5. Send a system message that sets the assistant role.
6. Send the user message.
7. Use low temperature, `0.2`, for more stable helpdesk answers.
8. Read `response.choices[0].message.content`.
9. Return the answer text to `azure_openai_demo.py`.

## End-to-End Sequence

```text
User
  |
  | python azure_openai_demo.py "VPN is not working"
  v
azure_openai_demo.py
  |
  | ask_llm("VPN is not working")
  v
llm_client.py
  |
  | load .env
  | build SDK client
  | send chat completion request
  v
Azure OpenAI
  |
  | generated answer
  v
llm_client.py
  |
  | return answer text
  v
azure_openai_demo.py
  |
  | print(answer)
  v
Terminal
```

## How To Run

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run with command-line input:

```powershell
python azure_openai_demo.py "My VPN is not connecting. What should I do?"
```

Run interactively:

```powershell
python azure_openai_demo.py
```

Then type the question when prompted.

## Expected Output

The exact response can change because it comes from a real LLM. A typical response may look like:

```text
Try restarting your VPN client, confirming your internet connection, checking your username and MFA approval, and reconnecting. If it still fails, a ticket should be created for IT support.
```

## Current Design

This demo is a real LLM call with local tool/function calling:

```text
User Question -> Azure OpenAI -> Optional Tool Call -> Tool Result -> Azure OpenAI -> Final Answer
```

The LLM can decide whether it needs to call a local tool.

Available tools:

- `search_knowledge_base(issue)`
- `create_ticket(issue)`

### Tool-Calling Block Diagram

```text
+----------------+
| User Question  |
+-------+--------+
        |
        v
+--------------------------+
| LLM Reasoning            |
| Decide next action       |
+-------+------------------+
        |
        v
+------------------------------+
| Tool Decision                |
| Search KB or create ticket?  |
+-------+----------------------+
        |
        +------------------------------+
        |                              |
        v                              v
+--------------------------+   +----------------------+
| search_knowledge_base()  |   | create_ticket()      |
+------------+-------------+   +----------+-----------+
             |                            |
             +-------------+--------------+
                           |
                           v
+--------------------------+
| Tool Observation         |
+------------+-------------+
             |
             v
+--------------------------+
| LLM Final Answer         |
+--------------------------+
```

### Tool-Calling Flowchart

```text
Start
  |
  v
User enters IT issue
  |
  v
Send issue to LLM with available tool definitions
  |
  v
Does LLM request a tool call?
  |
  +-- No --> Print final model answer --> End
  |
  +-- Yes
        |
        v
     Which tool?
        |
        +-- search_knowledge_base --> Call KB tool
        |
        +-- create_ticket ---------> Call ticket tool
        |
        v
     Send tool result back to LLM
        |
        v
     LLM creates final answer
        |
        v
     Print final answer
        |
        v
     End
```

## Difference From `app.py`

| Area | `app.py` | `azure_openai_demo.py` |
|---|---|---|
| Type | Deterministic ReAct demo | Real LLM call |
| Uses Azure OpenAI | No | Yes |
| Uses `.env` | No | Yes |
| Uses tools | Yes, local Python tools | Yes, model-selected local tools |
| Output | Predictable every time | Generated by model after optional tool results |
| Best for | Teaching ReAct pattern | Showing live LLM integration with tools |

## Why This Design Is Useful

1. The deterministic classroom demo remains simple.
2. The real LLM connection is isolated in `llm_client.py`.
3. `.env` keeps configuration separate from code.
4. The same `ask_llm()` function can be reused in later demos.
5. The model can now choose between answering directly, searching the KB, or creating a ticket.
