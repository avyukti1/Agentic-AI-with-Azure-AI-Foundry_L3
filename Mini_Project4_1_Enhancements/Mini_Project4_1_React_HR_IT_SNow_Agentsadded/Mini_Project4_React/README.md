# Azure AI Foundry ReAct Agent

React + Express application that talks to an existing Azure AI Foundry Agent by using the Azure AI Agents JavaScript SDK.

## Run

```powershell
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Run Built App

```powershell
npm run build
npm start
```

Open `http://127.0.0.1:5000`.

## Azure Login

This app uses Entra ID through `@azure/identity`. Before running, sign in with an account that has access to the Azure AI Foundry project:

```powershell
az login --tenant 94a50f17-4aa1-433b-bbb8-62ae51d5c4e8
az account show
```

The server reads Azure settings from `.env`. The React app calls the local Express API, so Azure credentials are never exposed to the browser.

## ReAct Behavior

The app uses a ReAct-style orchestration pattern:

1. Reason: choose the configured Foundry agent.
2. Act: create or reuse a Foundry thread, add the user message, and run the agent.
3. Observe: poll the run status.
4. Final: return the assistant response.

The UI shows an operational trace without exposing hidden chain-of-thought.

## Document Q&A

Use the **Upload PDF, DOCX, TXT** button in the sidebar to attach a document to the current agent thread.

Supported formats:

- PDF
- Word DOCX
- TXT

After upload, ask questions such as:

```text
Summarize the uploaded document.
What policy rules are mentioned in this file?
Create action items from this document.
```

The extracted document text is kept in server memory for the current session and is sent to the Azure AI Foundry agent as context for your questions. Resetting the thread clears the uploaded document context.

## Structured Response Generator

Open the **Structured Output** tab to generate API-ready JSON from natural-language requests.

Available presets:

- Service ticket
- Action plan
- Document summary

The generator uses the selected Azure AI Foundry agent and returns JSON suitable for downstream API demos. If a document is uploaded, the extracted document text is included as context for the structured output request.
