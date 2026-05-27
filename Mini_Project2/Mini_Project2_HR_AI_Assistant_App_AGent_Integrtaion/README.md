# Agent Apps Foundry Portal

Streamlit multi-application portal integrated with the existing Azure AI Foundry agent:

- Project endpoint: `https://ajay-agent-project111-resource.services.ai.azure.com/api/projects/ajay-agent-project111`
- Agent ID: `asst_lkimK637j4tr2YYe45ZqUhXd`
- Agent name: `Agent941`
- Deployment behind the agent: `ajay-gpt-4o`
- Model version: `2024-11-20`
- Temperature: `1`
- Top P: `1`

## Applications

- HR App: leave, onboarding, benefits, policies, and HR communication support.
- IT Helpdesk App: laptop, VPN, password, software, access, and troubleshooting support.
- ServiceNow Ticketing App: incident drafts, classifications, assignment notes, and resolution notes.

All three applications use the same Azure AI Foundry agent. Each app has its own chat history, uploaded context, quick prompts, and fallback guidance.

The interface uses an EY-inspired professional theme with dark surfaces, EY yellow accents, and colorful application ribbons.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The app uses the configured Azure AI Foundry project endpoint and agent ID. If the cloud agent is unavailable from the local machine, the app keeps running with built-in guidance for the selected application.

## Run

```powershell
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## Configuration

Copy `.env.example` to `.env` and edit if your project endpoint or agent ID changes.

No API key is stored for the Foundry agent.
