# Application Logic and Working

This project contains two demos for Module 2: Advanced Prompt Engineering and Reasoning Systems.

- Demo 1: `app.py` shows the ReAct pattern.
- Demo 2: `structured_response_demo.py` shows API-ready structured JSON output.
- Shared file: `tools.py` contains reusable tool functions.

## Demo 1: ReAct Agent

The ReAct pattern means Reason + Act. The agent first thinks about the issue, chooses a tool, observes the tool result, and then gives a final answer.

### Block Diagram

```text
+----------------+
| User Question  |
+-------+--------+
        |
        v
+----------------+
| Thought        |
| Reason on task |
+-------+--------+
        |
        v
+--------------------------+
| Action                   |
| search_knowledge_base()  |
+-------+------------------+
        |
        v
+----------------+
| Observation    |
| KB result      |
+-------+--------+
        |
        v
+-------------------------------+
| Decision                      |
| KB found or ticket required?  |
+-------+-----------------------+
        |
        v
+----------------+
| Final Answer   |
+----------------+
```

### Flowchart

```text
Start
  |
  v
User enters IT issue
  |
  v
Print Thought
  |
  v
Call search_knowledge_base(issue)
  |
  v
Is KB article found?
  |
  +-- Yes --> Show troubleshooting steps --> Final Answer --> End
  |
  +-- No --> Call create_ticket(issue) --> Show ticket ID --> Final Answer --> End
```

### Step-by-Step Working

1. The user runs `python app.py`.
2. The app asks for the IT issue if no command-line input is provided.
3. The app prints the user issue.
4. The app prints a `Thought` message explaining that it should search the knowledge base.
5. The app calls `search_knowledge_base()` from `tools.py`.
6. The app prints the returned KB article as the `Observation`.
7. If a KB article is found, the app returns troubleshooting steps.
8. If no KB article is found, the app calls `create_ticket()`.
9. The app prints the ticket result as the second `Observation`.
10. The app prints the final user-facing answer.

### Example

```powershell
python app.py "VPN issue"
```

Expected behavior:

```text
Thought: Search the knowledge base
Action: search_knowledge_base
Observation: VPN Troubleshooting Steps
Final Answer: Try these steps
```

## Demo 2: Structured Response Generator

This demo returns a predictable JSON object. This is useful for APIs, automation workflows, dashboards, and integrations.

### Block Diagram

```text
+----------------+
| User Issue     |
+-------+--------+
        |
        v
+----------------+
| Classify Issue |
+-------+--------+
        |
        v
+--------------------------+
| Search KB Tool           |
| search_knowledge_base()  |
+-------+------------------+
        |
        v
+------------------+
| Build JSON Schema|
+-------+----------+
        |
        v
+----------------+
| Print JSON      |
+----------------+
```

### Flowchart

```text
Start
  |
  v
User enters IT issue
  |
  v
Classify issue as vpn, email, laptop, or unknown
  |
  v
Search knowledge base
  |
  v
Is issue unknown?
  |
  +-- Yes --> ticket_required = true --> ticket_id = INC1001 --> recommended_steps = []
  |
  +-- No --> ticket_required = false --> extract recommended_steps from KB
  |
  v
Create final JSON response
  |
  v
Print formatted JSON
  |
  v
End
```

### JSON Schema

```json
{
  "issue": "string",
  "issue_type": "vpn | email | laptop | unknown",
  "priority": "low | medium | high",
  "ticket_required": true,
  "ticket_id": "string or null",
  "recommended_steps": ["string"],
  "final_message": "string"
}
```

### Step-by-Step Working

1. The user runs `python structured_response_demo.py`.
2. The app asks for the IT issue if no command-line input is provided.
3. `classify_issue()` checks keywords and returns an issue type.
4. `search_knowledge_base()` searches the same local KB used by Demo 1.
5. `get_priority()` assigns a priority based on the issue type.
6. If the issue type is `unknown`, the app marks `ticket_required` as `true`.
7. If the issue type is known, `parse_steps()` converts the KB article into a JSON list.
8. The app creates a fixed JSON response.
9. The app prints the JSON using `json.dumps(..., indent=2)`.

### Example

```powershell
python structured_response_demo.py "VPN issue"
```

Expected output:

```json
{
  "issue": "VPN issue",
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

## Shared Tools

`tools.py` contains two reusable functions:

- `search_knowledge_base(issue)`: searches local KB content using keywords.
- `create_ticket(issue)`: returns a demo ticket number for unresolved issues.

## Why This Design Matches Module 2

- Chain-of-Thought / reasoning systems: Demo 1 prints reasoning as `Thought`.
- ReAct pattern: Demo 1 shows `Thought -> Action -> Observation -> Final Answer`.
- Tool-aware prompting: Both demos use tool functions from `tools.py`.
- Prompt orchestration pipelines: The app controls the order of reasoning, tool calls, and response generation.
- Structured output: Demo 2 returns a predictable API-ready JSON object.
