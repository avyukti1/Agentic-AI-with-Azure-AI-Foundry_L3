import "dotenv/config";
import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import cors from "cors";
import mammoth from "mammoth";
import multer from "multer";
import { PDFParse } from "pdf-parse";
import {
  AzureCliCredential,
  AzureDeveloperCliCredential,
  AzurePowerShellCredential,
  ChainedTokenCredential,
  DefaultAzureCredential,
} from "@azure/identity";
import { AgentsClient } from "@azure/ai-agents";

const app = express();
const port = Number(process.env.PORT || 5000);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distPath = path.resolve(__dirname, "..", "dist");
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 15 * 1024 * 1024 },
});

app.use(cors({ origin: ["http://127.0.0.1:5173", "http://localhost:5173"] }));
app.use(express.json({ limit: "1mb" }));

const sessions = new Map();
const documents = new Map();
const MAX_DOCUMENT_CHARS = 24000;

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function getCredential() {
  const tenantId = process.env.AZURE_TENANT_ID;
  const options = tenantId ? { tenantId } : {};

  if (process.env.AZURE_AUTH_MODE === "tenant_chain") {
    return new ChainedTokenCredential(
      new AzureCliCredential(options),
      new AzurePowerShellCredential(options),
      new AzureDeveloperCliCredential(options),
      new DefaultAzureCredential(options),
    );
  }

  return new DefaultAzureCredential(options);
}

const projectEndpoint = requiredEnv("AZURE_AI_PROJECT_ENDPOINT");
const client = new AgentsClient(projectEndpoint, getCredential());

const agents = [
  {
    key: "general",
    id: requiredEnv("AZURE_AI_AGENT_ID"),
    name: process.env.AZURE_AI_AGENT_NAME || "Agent",
    scope: "General reasoning",
  },
  {
    key: "hr",
    id: process.env.AZURE_AI_HR_AGENT_ID || process.env.AZURE_AI_AGENT_ID,
    name: process.env.AZURE_AI_HR_AGENT_NAME || "HRAgent",
    scope: "HR policy and employee support",
  },
  {
    key: "it",
    id: process.env.AZURE_AI_IT_AGENT_ID || process.env.AZURE_AI_AGENT_ID,
    name: process.env.AZURE_AI_IT_AGENT_NAME || "ITAgent",
    scope: "IT helpdesk and access support",
  },
  {
    key: "servicenow",
    id: process.env.AZURE_AI_SERVICENOW_AGENT_ID || process.env.AZURE_AI_AGENT_ID,
    name: process.env.AZURE_AI_SERVICENOW_AGENT_NAME || "ServNowAgent",
    scope: "ServiceNow ticket guidance",
  },
];

function getAgent(agentKey) {
  return agents.find((agent) => agent.key === agentKey) || agents[0];
}

function getSessionKey(sessionId, agentKey) {
  return `${sessionId}:${agentKey}`;
}

function getTextFromMessage(message) {
  return (message.content || [])
    .map((part) => {
      if (part.type === "text" && part.text?.value) {
        return part.text.value;
      }
      return "";
    })
    .filter(Boolean)
    .join("\n\n");
}

async function getOrCreateThread(sessionId, agentKey) {
  const sessionKey = getSessionKey(sessionId, agentKey);
  const existing = sessions.get(sessionKey);
  if (existing) {
    return existing;
  }

  const thread = await client.threads.create();
  sessions.set(sessionKey, thread.id);
  return thread.id;
}

function getDocumentContext(sessionId, agentKey) {
  return documents.get(getSessionKey(sessionId, agentKey));
}

function truncateText(text, maxChars = MAX_DOCUMENT_CHARS) {
  if (!text || text.length <= maxChars) {
    return text || "";
  }

  return `${text.slice(0, maxChars)}\n\n[Document truncated to ${maxChars} characters for this request.]`;
}

function buildAdditionalInstructions(agent, document) {
  const documentInstruction = document
    ? `The user uploaded "${document.name}". Use the document context included in user messages to answer document-related questions. If the answer is not in the document, say that clearly.`
    : "No document is currently attached to this conversation.";

  return [
    `You are ${agent.name}, a ReAct-style reasoning agent for ${agent.scope}.`,
    "Use a private Reason, Act, Observe loop to decide what to do.",
    "Do not reveal hidden chain-of-thought. Instead, answer with concise reasoning summary, useful actions, and a clear final answer.",
    "When the user's request is ambiguous, ask one focused clarification question.",
    documentInstruction,
  ].join(" ");
}

function buildUserMessage(message, document) {
  if (!document) {
    return message;
  }

  return [
    `User question:\n${message}`,
    "",
    `Uploaded document: ${document.name}`,
    "Document context:",
    truncateText(document.text),
  ].join("\n");
}

const structuredSchemas = {
  serviceTicket: {
    label: "Service ticket",
    schema: {
      summary: "string",
      category: "HR | IT | ServiceNow | General",
      priority: "low | medium | high | critical",
      requester_intent: "string",
      recommended_actions: ["string"],
      missing_information: ["string"],
      api_status: "ready | needs_clarification",
    },
  },
  actionPlan: {
    label: "Action plan",
    schema: {
      objective: "string",
      assumptions: ["string"],
      actions: [{ owner: "string", task: "string", due: "string", dependency: "string" }],
      risks: ["string"],
      api_status: "ready | needs_clarification",
    },
  },
  documentSummary: {
    label: "Document summary",
    schema: {
      title: "string",
      executive_summary: "string",
      key_points: ["string"],
      obligations_or_actions: ["string"],
      questions_to_clarify: ["string"],
      api_status: "ready | needs_clarification",
    },
  },
};

function getStructuredSchema(schemaKey) {
  return structuredSchemas[schemaKey] || structuredSchemas.serviceTicket;
}

function buildStructuredPrompt(task, schemaKey, document) {
  const selected = getStructuredSchema(schemaKey);
  const parts = [
    "Return only valid JSON. Do not wrap it in markdown. Do not include commentary.",
    `Use this JSON shape exactly: ${JSON.stringify(selected.schema)}`,
    `User request: ${task}`,
  ];

  if (document) {
    parts.push(`Uploaded document: ${document.name}`);
    parts.push("Document context:");
    parts.push(truncateText(document.text));
  }

  return parts.join("\n\n");
}

function parseJsonResponse(text) {
  const trimmed = (text || "").trim();
  if (!trimmed) {
    throw new Error("The agent did not return a structured response.");
  }

  try {
    return JSON.parse(trimmed);
  } catch {
    const match = trimmed.match(/\{[\s\S]*\}/);
    if (!match) {
      throw new Error("The agent response did not contain valid JSON.");
    }
    return JSON.parse(match[0]);
  }
}

function normalizeText(text) {
  return text.replace(/\r/g, "").replace(/[ \t]+\n/g, "\n").replace(/\n{4,}/g, "\n\n\n").trim();
}

async function extractDocumentText(file) {
  const ext = path.extname(file.originalname || "").toLowerCase();
  const mime = file.mimetype || "";

  if (ext === ".txt" || mime.startsWith("text/")) {
    return file.buffer.toString("utf8");
  }

  if (ext === ".pdf" || mime === "application/pdf") {
    const parser = new PDFParse({ data: file.buffer });
    try {
      const result = await parser.getText();
      return result.text || "";
    } finally {
      await parser.destroy();
    }
  }

  if (ext === ".docx" || mime === "application/vnd.openxmlformats-officedocument.wordprocessingml.document") {
    const result = await mammoth.extractRawText({ buffer: file.buffer });
    return result.value || "";
  }

  throw new Error("Unsupported file type. Please upload PDF, DOCX, or TXT.");
}

app.get("/api/config", (_req, res) => {
  res.json({
    projectEndpoint,
    deployment: process.env.AZURE_AI_DEPLOYMENT,
    modelVersion: process.env.AZURE_AI_MODEL_VERSION,
    temperature: Number(process.env.AZURE_AI_AGENT_TEMPERATURE || 0.2),
    topP: Number(process.env.AZURE_AI_AGENT_TOP_P || 1),
    agents: agents.map(({ key, name, scope }) => ({ key, name, scope })),
  });
});

app.get("/api/health", (_req, res) => {
  res.json({ ok: true });
});

app.post("/api/documents", upload.single("document"), async (req, res) => {
  const { sessionId = "default", agentKey = "general" } = req.body || {};
  if (!req.file) {
    return res.status(400).json({ error: "Document file is required." });
  }

  try {
    const text = normalizeText(await extractDocumentText(req.file));
    if (!text) {
      return res.status(400).json({ error: "No readable text was found in this document." });
    }

    const document = {
      name: req.file.originalname,
      type: req.file.mimetype,
      size: req.file.size,
      text,
      uploadedAt: new Date().toISOString(),
    };

    documents.set(getSessionKey(sessionId, agentKey), document);
    res.json({
      name: document.name,
      type: document.type,
      size: document.size,
      characters: document.text.length,
      uploadedAt: document.uploadedAt,
    });
  } catch (error) {
    res.status(400).json({ error: error.message || "Unable to process document." });
  }
});

app.post("/api/chat", async (req, res) => {
  const { message, sessionId = "default", agentKey = "general" } = req.body || {};
  if (!message || typeof message !== "string") {
    return res.status(400).json({ error: "Message is required." });
  }

  const agent = getAgent(agentKey);
  const document = getDocumentContext(sessionId, agent.key);
  const trace = [];

  try {
    trace.push({ stage: "Reason", status: "complete", detail: `Selected ${agent.name} for ${agent.scope}.` });
    const threadId = await getOrCreateThread(sessionId, agent.key);
    trace.push({ stage: "Act", status: "complete", detail: `Using thread ${threadId}.` });
    if (document) {
      trace.push({ stage: "Observe", status: "complete", detail: `Attached document context: ${document.name}.` });
    }

    await client.messages.create(threadId, "user", buildUserMessage(message, document));
    trace.push({ stage: "Act", status: "complete", detail: "User message added to the Azure AI Foundry thread." });

    const run = await client.runs.createAndPoll(threadId, agent.id, {
      additionalInstructions: buildAdditionalInstructions(agent, document),
      temperature: Number(process.env.AZURE_AI_AGENT_TEMPERATURE || 0.2),
      topP: Number(process.env.AZURE_AI_AGENT_TOP_P || 1),
      pollingOptions: { intervalInMs: 1200 },
    });
    trace.push({ stage: "Observe", status: run.status, detail: `Run finished with status: ${run.status}.` });

    if (run.status !== "completed") {
      return res.status(502).json({
        error: `Azure agent run did not complete. Status: ${run.status}`,
        run,
        trace,
      });
    }

    const messages = client.messages.list(threadId, { order: "desc" });
    let answer = "";
    for await (const item of messages) {
      if (item.role === "assistant") {
        answer = getTextFromMessage(item);
        break;
      }
    }

    trace.push({ stage: "Final", status: "complete", detail: "Assistant response received." });
    res.json({ answer: answer || "The agent completed, but no text answer was returned.", threadId, trace });
  } catch (error) {
    res.status(500).json({
      error: error.message || "Unexpected server error.",
      trace,
    });
  }
});

app.post("/api/structured", async (req, res) => {
  const { task, sessionId = "default", agentKey = "general", schemaKey = "serviceTicket" } = req.body || {};
  if (!task || typeof task !== "string") {
    return res.status(400).json({ error: "Task is required." });
  }

  const agent = getAgent(agentKey);
  const document = getDocumentContext(sessionId, agent.key);
  const trace = [];

  try {
    trace.push({ stage: "Reason", status: "complete", detail: `Selected schema: ${getStructuredSchema(schemaKey).label}.` });
    const thread = await client.threads.create();
    trace.push({ stage: "Act", status: "complete", detail: `Created structured output thread ${thread.id}.` });

    await client.messages.create(thread.id, "user", buildStructuredPrompt(task, schemaKey, document));
    const run = await client.runs.createAndPoll(thread.id, agent.id, {
      additionalInstructions: [
        buildAdditionalInstructions(agent, document),
        "You are generating machine-readable API output. Return only syntactically valid JSON matching the requested schema.",
      ].join(" "),
      temperature: 0.1,
      topP: 1,
      pollingOptions: { intervalInMs: 1200 },
    });
    trace.push({ stage: "Observe", status: run.status, detail: `Structured run finished with status: ${run.status}.` });

    if (run.status !== "completed") {
      return res.status(502).json({ error: `Azure agent run did not complete. Status: ${run.status}`, run, trace });
    }

    const messages = client.messages.list(thread.id, { order: "desc" });
    let raw = "";
    for await (const item of messages) {
      if (item.role === "assistant") {
        raw = getTextFromMessage(item);
        break;
      }
    }

    const json = parseJsonResponse(raw);
    trace.push({ stage: "Final", status: "complete", detail: "API-ready JSON generated." });
    res.json({ json, raw, schema: getStructuredSchema(schemaKey), trace });
  } catch (error) {
    res.status(500).json({ error: error.message || "Unable to generate structured output.", trace });
  }
});

app.delete("/api/session/:sessionId", (req, res) => {
  const prefix = `${req.params.sessionId}:`;
  for (const key of sessions.keys()) {
    if (key.startsWith(prefix)) {
      sessions.delete(key);
    }
  }
  for (const key of documents.keys()) {
    if (key.startsWith(prefix)) {
      documents.delete(key);
    }
  }
  res.status(204).end();
});

app.use("/api", (_req, res) => {
  res.status(404).json({ error: "API route not found." });
});

app.use(express.static(distPath));

app.get("*", (_req, res) => {
  res.sendFile(path.join(distPath, "index.html"));
});

app.listen(port, () => {
  console.log(`Azure Foundry ReAct server listening on http://127.0.0.1:${port}`);
});
