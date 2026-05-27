# Agent Apps Foundry Portal

Streamlit multi-application portal integrated with auto-routed Azure AI Foundry domain agents:

- Project endpoint: `https://ajay-agent-project111-resource.services.ai.azure.com/api/projects/ajay-agent-project111`
- HR agent: `HRAgent`
- IT agent: `ITAgent`
- ServiceNow agent: `ServNowAgent`
- Deployment behind the agent: `ajay-gpt-4o`
- Model version: `2024-11-20`
- Temperature: `1`
- Top P: `1`

## Applications

- HR App: leave, onboarding, benefits, policies, and HR communication support.
- IT Helpdesk App: laptop, VPN, password, software, access, and troubleshooting support.
- ServiceNow Ticketing App: incident drafts, classifications, assignment notes, and resolution notes.

Each application can use its own Azure AI Foundry agent ID. The chat input is routed to HR, IT, or ServiceNow based on the user's query before the agent is called. Each app has its own chat history, uploaded context, quick prompts, and fallback guidance.

The interface uses an EY-inspired professional theme with dark surfaces, EY yellow accents, and colorful application ribbons.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The app uses the configured Azure AI Foundry project endpoint and domain agent IDs. If a cloud agent is unavailable from the local machine, the app keeps running with local uploaded-document guidance for the routed application.

## Run

```powershell
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## Configuration

Copy `.env.example` to `.env` and edit the domain agent IDs:

- `AZURE_AI_HR_AGENT_ID`
- `AZURE_AI_IT_AGENT_ID`
- `AZURE_AI_SERVICENOW_AGENT_ID`

No API key is stored for the Foundry agent.
