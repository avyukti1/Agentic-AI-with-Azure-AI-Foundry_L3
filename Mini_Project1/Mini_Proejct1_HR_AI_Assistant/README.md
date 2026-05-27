# HR AI Portal - Streamlit + Azure OpenAI

Sample HR assistant portal using Streamlit and your Azure OpenAI deployment.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set:

```text
AZURE_OPENAI_API_KEY=your-real-key
```

## Run

```powershell
streamlit run app.py
```

Open the URL shown by Streamlit, usually:

```text
http://localhost:8501
```

## Notes

- Do not commit `.env` or real API keys.
- If an API key was shared publicly or in chat, rotate it in Azure AI Foundry.
- You can upload HR policy files in PDF, TXT, MD, or CSV format for grounded answers.
