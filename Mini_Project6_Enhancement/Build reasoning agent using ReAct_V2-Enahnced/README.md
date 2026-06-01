# Module 2 Demos: Reasoning and Structured Output

This folder contains two hands-on demos for advanced prompt engineering and reasoning systems.

## Demo 1: IT Helpdesk ReAct Agent

This demo shows a simple reasoning agent flow:

```text
User Question -> Thought -> Action -> Observation -> Final Answer
```

Run:

```powershell
python app.py "VPN is not working"
```

You can also run it interactively:

```powershell
python app.py
```

## Demo 2: Structured Response Generator

This demo converts an IT issue into API-ready JSON output using a fixed schema.

Run:

```powershell
python structured_response_demo.py "VPN is not working"
```

Example output:

```json
{
  "issue": "VPN is not working",
  "issue_type": "vpn",
  "priority": "medium",
  "ticket_required": false,
  "ticket_id": null,
  "recommended_steps": [
    "Check your internet connection.",
    "Confirm your VPN username and password.",
    "Verify MFA approval.",
    "Restart the VPN client.",
    "Try connecting from another network."
  ],
  "final_message": "Please try the recommended vpn troubleshooting steps. If the issue continues, an IT ticket can be created."
}
```

## Demo 3: Azure OpenAI Real LLM Call with Tools

The deterministic ReAct demo in `app.py` is unchanged. To call the real Azure OpenAI deployment, install dependencies and run:

```powershell
pip install -r requirements.txt
python azure_openai_demo.py "VPN is not working"
```

The Azure OpenAI demo can also use local tools. If the model decides it needs troubleshooting details, it can call `search_knowledge_base`. If the user asks to create a case, ticket, or incident, it can call `create_ticket`.

Example ticket prompt:

```powershell
python azure_openai_demo.py "I have VPN issue, error says Network unreachable - please create a case"
```

Expected behavior:

```text
Your ticket has been created successfully. The ticket number is INC1001...
```

The live model configuration is read from `.env`:

```text
AZURE_OPENAI_ENDPOINT=https://ajay-agent-project111-resource.openai.azure.com/openai/v1
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT_NAME=ajay-gpt-4o
AZURE_OPENAI_API_VERSION=2024-11-20
```

## Files

- `app.py`: Main ReAct flow.
- `tools.py`: Knowledge base search and ticket creation tools.
- `llm_client.py`: Shared Azure OpenAI client helper with tool-calling support.
- `azure_openai_demo.py`: Real model call demo with local helpdesk tools.
- `structured_response_demo.py`: API-ready JSON response generator.
- `APPLICATION_LOGIC.md`: Block diagrams, flowcharts, and detailed working notes.
- `requirements.txt`: Dependency note.
