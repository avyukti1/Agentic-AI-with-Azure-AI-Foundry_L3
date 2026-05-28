import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  BarChart3,
  Bot,
  BrainCircuit,
  BriefcaseBusiness,
  Clipboard,
  CheckCircle2,
  Cpu,
  FileJson,
  MessageSquareText,
  PanelRight,
  RotateCcw,
  Send,
  Server,
  ShieldCheck,
  Sparkles,
  TicketCheck,
  Upload,
  UserRound,
  Workflow,
} from "lucide-react";
import "./styles.css";

const API_BASES = ["", "http://127.0.0.1:5000"];

async function apiFetch(path, options) {
  let lastError;

  for (const base of API_BASES) {
    try {
      const response = await fetch(`${base}${path}`, options);
      const contentType = response.headers.get("content-type") || "";
      if (response.status === 204) {
        return { response, payload: null };
      }

      const payload = contentType.includes("application/json") ? await response.json() : null;

      if (!payload) {
        throw new Error(`Expected JSON from ${path}, but received ${contentType || "unknown content"}.`);
      }

      return { response, payload };
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error("Server is not reachable.");
}

function makeSessionId() {
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

const promptChips = [
  "Summarize the uploaded document",
  "Summarize this employee request and next actions",
  "Draft a ServiceNow ticket response",
  "Classify this issue for HR or IT routing",
];

const workTabs = [
  { key: "conversation", label: "Conversation", icon: MessageSquareText },
  { key: "structured", label: "Structured Output", icon: FileJson },
  { key: "trace", label: "Reasoning", icon: Workflow },
  { key: "insights", label: "Insights", icon: BarChart3 },
];

const schemaOptions = [
  { key: "serviceTicket", label: "Service ticket" },
  { key: "actionPlan", label: "Action plan" },
  { key: "documentSummary", label: "Document summary" },
];

const agentIcons = {
  general: BrainCircuit,
  hr: BriefcaseBusiness,
  it: Cpu,
  servicenow: TicketCheck,
};

const agentTone = {
  general: "tone-yellow",
  hr: "tone-blue",
  it: "tone-teal",
  servicenow: "tone-violet",
};

function App() {
  const [config, setConfig] = useState(null);
  const [agentKey, setAgentKey] = useState("general");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Ready for enterprise HR, IT, ServiceNow, and advisory workflows through Azure AI Foundry.",
    },
  ]);
  const [trace, setTrace] = useState([]);
  const [activeTab, setActiveTab] = useState("conversation");
  const [schemaKey, setSchemaKey] = useState("serviceTicket");
  const [structuredInput, setStructuredInput] = useState("");
  const [structuredResult, setStructuredResult] = useState(null);
  const [structuredBusy, setStructuredBusy] = useState(false);
  const [documentInfo, setDocumentInfo] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState(makeSessionId);
  const fileInputRef = useRef(null);
  const scrollRef = useRef(null);

  const activeAgent = useMemo(() => {
    return config?.agents?.find((agent) => agent.key === agentKey) || config?.agents?.[0];
  }, [agentKey, config]);

  useEffect(() => {
    apiFetch("/api/config")
      .then(({ payload }) => {
        setConfig(payload);
        if (payload.agents?.[0]?.key) {
          setAgentKey(payload.agents[0].key);
        }
      })
      .catch(() => setError("Server is not reachable. Start it with npm run server or npm run dev."));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function sendMessage(event) {
    event.preventDefault();
    const text = input.trim();
    if (!text || busy) return;

    setInput("");
    setError("");
    setBusy(true);
    setTrace([{ stage: "Reason", status: "running", detail: "Preparing the request." }]);
    setMessages((items) => [...items, { role: "user", content: text }]);

    try {
      const { response, payload } = await apiFetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, agentKey, sessionId }),
      });
      if (!response.ok) {
        throw new Error(payload.error || "The Azure agent request failed.");
      }
      setTrace(payload.trace || []);
      setMessages((items) => [...items, { role: "assistant", content: payload.answer }]);
    } catch (err) {
      setError(err.message);
      setTrace((items) => [...items, { stage: "Error", status: "failed", detail: err.message }]);
    } finally {
      setBusy(false);
    }
  }

  async function resetSession() {
    await apiFetch(`/api/session/${sessionId}`, { method: "DELETE" }).catch(() => {});
    setSessionId(makeSessionId());
    setDocumentInfo(null);
    setTrace([]);
    setMessages([
      {
        role: "assistant",
        content: "New secure conversation started. The next request will use a fresh Azure AI Foundry thread.",
      },
    ]);
  }

  async function uploadDocument(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setError("");
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("document", file);
      formData.append("sessionId", sessionId);
      formData.append("agentKey", agentKey);

      const { response, payload } = await apiFetch("/api/documents", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(payload.error || "Document upload failed.");
      }

      setDocumentInfo(payload);
      setTrace((items) => [
        ...items,
        {
          stage: "Observe",
          status: "complete",
          detail: `Document ready: ${payload.name} (${payload.characters.toLocaleString()} characters).`,
        },
      ]);
      setMessages((items) => [
        ...items,
        {
          role: "assistant",
          content: `Document uploaded: ${payload.name}. Ask a question about it and I will use its extracted context.`,
        },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function generateStructuredOutput(event) {
    event.preventDefault();
    const task = structuredInput.trim();
    if (!task || structuredBusy) return;

    setError("");
    setStructuredBusy(true);
    setStructuredResult(null);

    try {
      const { response, payload } = await apiFetch("/api/structured", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task, schemaKey, agentKey, sessionId }),
      });

      if (!response.ok) {
        throw new Error(payload.error || "Structured output request failed.");
      }

      setStructuredResult(payload);
      setTrace(payload.trace || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setStructuredBusy(false);
    }
  }

  async function copyStructuredJson() {
    if (!structuredResult?.json) return;
    await navigator.clipboard?.writeText(JSON.stringify(structuredResult.json, null, 2));
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="ey-mark" aria-label="EY">EY</div>
          <div>
            <p className="brand-kicker">Enterprise AI</p>
            <h1>Foundry Service Agent</h1>
          </div>
        </div>

        <section className="panel runtime-panel">
          <div className="panel-title">
            <Server size={16} />
            Runtime
          </div>
          <dl className="runtime-list">
            <div>
              <dt>Deployment</dt>
              <dd>{config?.deployment || "Loading"}</dd>
            </div>
            <div>
              <dt>Model version</dt>
              <dd>{config?.modelVersion || "Loading"}</dd>
            </div>
            <div>
              <dt>Temperature</dt>
              <dd>{config?.temperature ?? "Loading"}</dd>
            </div>
            <div>
              <dt>Top P</dt>
              <dd>{config?.topP ?? "Loading"}</dd>
            </div>
          </dl>
        </section>

        <section className="panel document-panel">
          <div className="panel-title">
            <Upload size={16} />
            Document
          </div>
          <input
            ref={fileInputRef}
            className="file-input"
            type="file"
            accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
            onChange={uploadDocument}
          />
          <button
            className="upload-button"
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <Upload size={17} />
            {uploading ? "Processing" : "Upload PDF, DOCX, TXT"}
          </button>
          <div className={documentInfo ? "document-card attached" : "document-card"}>
            <strong>{documentInfo?.name || "No document attached"}</strong>
            <span>
              {documentInfo
                ? `${documentInfo.characters.toLocaleString()} characters extracted`
                : "Attach a document before asking document-specific questions."}
            </span>
          </div>
        </section>

        <section className="panel">
          <div className="panel-title">
            <Sparkles size={16} />
            Agent portfolio
          </div>
          <div className="agent-list">
            {(config?.agents || []).map((agent) => {
              const Icon = agentIcons[agent.key] || Sparkles;
              return (
                <button
                  key={agent.key}
                  className={`agent-choice ${agentTone[agent.key] || "tone-yellow"} ${agent.key === agentKey ? "active" : ""}`}
                  onClick={() => setAgentKey(agent.key)}
                  type="button"
                >
                  <Icon size={18} />
                  <span>{agent.name}</span>
                  <small>{agent.scope}</small>
                </button>
              );
            })}
          </div>
        </section>

        <div className="trust-strip">
          <ShieldCheck size={18} />
          <span>Authenticated through Microsoft Entra ID</span>
        </div>

        <button className="reset-button" type="button" onClick={resetSession}>
          <RotateCcw size={17} />
          New thread
        </button>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">EY internal advisory console</p>
            <h2>{activeAgent?.name || "Connecting"}</h2>
            <span>{activeAgent?.scope || "Azure AI Foundry reasoning workspace"}</span>
          </div>
          <div className="topbar-actions">
            <div className="status-pill">
              <CheckCircle2 size={16} />
              {busy ? "Running" : "Ready"}
            </div>
            <button className="icon-action" type="button" onClick={resetSession} aria-label="Reset thread" title="Reset thread">
              <RotateCcw size={18} />
            </button>
          </div>
        </header>

        <nav className="tab-ribbon" aria-label="Workspace views">
          <div className="tabs">
            {workTabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.key}
                  className={activeTab === tab.key ? "tab-button active" : "tab-button"}
                  type="button"
                  onClick={() => setActiveTab(tab.key)}
                >
                  <Icon size={17} />
                  {tab.label}
                </button>
              );
            })}
          </div>
          <div className={`ribbon-status ${agentTone[agentKey] || "tone-yellow"}`}>
            <span></span>
            {documentInfo ? `${activeAgent?.name || "Agent"} with document` : `${activeAgent?.name || "Agent"} selected`}
          </div>
        </nav>

        <section className="hero-band">
          <div>
            <p className="eyebrow">Agentic AI operations</p>
            <h3>Trusted reasoning for people, technology, and service workflows.</h3>
          </div>
          <div className="metric-row">
            <div>
              <strong>{config?.agents?.length || 0}</strong>
              <span>Agents</span>
            </div>
            <div>
              <strong>{trace.length}</strong>
              <span>Trace steps</span>
            </div>
            <div>
              <strong>{documentInfo ? "Yes" : "No"}</strong>
              <span>Document</span>
            </div>
          </div>
        </section>

        <div className="content-grid">
          <section className={`chat-panel ${activeTab !== "conversation" ? "compact-mode" : ""}`}>
            <div className="chat-header">
              <div>
                <p className="eyebrow">{activeTab === "structured" ? "API-ready outputs" : "Conversation"}</p>
                <h3>{activeTab === "structured" ? "Structured response generator" : "Decision support"}</h3>
              </div>
              {activeTab === "structured" ? <FileJson size={20} /> : <Activity size={20} />}
            </div>

            {activeTab === "structured" ? (
              <section className="structured-workspace">
                <form className="structured-form" onSubmit={generateStructuredOutput}>
                  <div className="schema-row">
                    {schemaOptions.map((schema) => (
                      <button
                        key={schema.key}
                        className={schemaKey === schema.key ? "schema-chip active" : "schema-chip"}
                        type="button"
                        onClick={() => setSchemaKey(schema.key)}
                      >
                        {schema.label}
                      </button>
                    ))}
                  </div>
                  <textarea
                    value={structuredInput}
                    onChange={(event) => setStructuredInput(event.target.value)}
                    placeholder="Describe the request, pasted notes, ticket details, or ask for structured output from the uploaded document"
                    rows={5}
                  />
                  <button className="generate-button" type="submit" disabled={structuredBusy || !structuredInput.trim()}>
                    <FileJson size={18} />
                    {structuredBusy ? "Generating" : "Generate JSON"}
                  </button>
                </form>

                <div className="json-panel">
                  <div className="json-toolbar">
                    <strong>API response</strong>
                    <button type="button" onClick={copyStructuredJson} disabled={!structuredResult?.json} title="Copy JSON">
                      <Clipboard size={16} />
                      Copy
                    </button>
                  </div>
                  <pre>{structuredResult?.json ? JSON.stringify(structuredResult.json, null, 2) : "{\n  \"status\": \"waiting_for_request\"\n}"}</pre>
                </div>
              </section>
            ) : (
              <>
                <div className="messages">
                  {messages.map((message, index) => (
                    <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
                      <div className="avatar">{message.role === "user" ? <UserRound size={18} /> : <Bot size={18} />}</div>
                      <p>{message.content}</p>
                    </article>
                  ))}
                  {busy && (
                    <article className="message assistant">
                      <div className="avatar"><Bot size={18} /></div>
                      <p>Running private reasoning, action, and observation steps in Azure AI Foundry.</p>
                    </article>
                  )}
                  <div ref={scrollRef} />
                </div>

                <div className="prompt-row">
                  {promptChips.map((prompt) => (
                    <button key={prompt} type="button" onClick={() => setInput(prompt)}>
                      {prompt}
                    </button>
                  ))}
                </div>

                {error && <div className="error-banner">{error}</div>}

                <form className="composer" onSubmit={sendMessage}>
                  <textarea
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        sendMessage(event);
                      }
                    }}
                    placeholder="Enter request, case notes, policy question, or ticket context"
                    rows={3}
                  />
                  <button type="submit" disabled={busy || !input.trim()} aria-label="Send message" title="Send message">
                    <Send size={19} />
                  </button>
                </form>
              </>
            )}
            {activeTab === "structured" && error && <div className="error-banner">{error}</div>}
          </section>

          <aside className="trace-panel">
            <div className="panel-title">
              {activeTab === "insights" ? <PanelRight size={16} /> : <BrainCircuit size={16} />}
              {activeTab === "insights" ? "Operational insights" : "ReAct trace"}
            </div>
            {activeTab === "insights" ? (
              <div className="insight-list">
                <div className="insight-card tone-yellow">
                  <strong>{messages.length}</strong>
                  <span>Conversation turns</span>
                </div>
                <div className="insight-card tone-teal">
                  <strong>{trace.length || 0}</strong>
                  <span>Observed reasoning events</span>
                </div>
                <div className="insight-card tone-violet">
                  <strong>{documentInfo ? "Attached" : "None"}</strong>
                  <span>{documentInfo?.name || "Document context"}</span>
                </div>
                <div className="insight-card tone-blue">
                  <strong>{config?.deployment || "Pending"}</strong>
                  <span>Active deployment</span>
                </div>
                <div className="quality-ribbon">
                  <ShieldCheck size={16} />
                  Browser credentials remain isolated from Azure access.
                </div>
              </div>
            ) : (
              <div className="trace-list">
                {(trace.length ? trace : [{ stage: "Idle", status: "ready", detail: "Awaiting a request." }]).map((item, index) => (
                  <div className="trace-item" key={`${item.stage}-${index}`}>
                    <span className={`dot ${item.status}`}></span>
                    <div>
                      <strong>{item.stage}</strong>
                      <small>{item.status}</small>
                      <p>{item.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
