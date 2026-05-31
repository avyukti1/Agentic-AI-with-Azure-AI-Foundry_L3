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

## Files

- `app.py`: Main ReAct flow.
- `tools.py`: Knowledge base search and ticket creation tools.
- `structured_response_demo.py`: API-ready JSON response generator.
- `APPLICATION_LOGIC.md`: Block diagrams, flowcharts, and detailed working notes.
- `requirements.txt`: Dependency note.
