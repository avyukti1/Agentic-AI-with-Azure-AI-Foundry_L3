import os
import re
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

import streamlit as st
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ListSortOrder
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import AzureCliCredential, ChainedTokenCredential, DefaultAzureCredential, InteractiveBrowserCredential
from dotenv import load_dotenv


load_dotenv()

DEFAULT_PROJECT_ENDPOINT = (
    "https://ajay-agent-project111-resource.services.ai.azure.com/api/projects/"
    "ajay-agent-project111"
)
DEFAULT_AGENT_ID = "asst_lkimK637j4tr2YYe45ZqUhXd"
DEFAULT_AGENT_NAME = "Agent941"
DEFAULT_DEPLOYMENT = "ajay-gpt-4o"
DEFAULT_MODEL_VERSION = "2024-11-20"
DEFAULT_TEMPERATURE = "0.2"
DEFAULT_TOP_P = "0.4"
DEFAULT_TENANT_ID = "94a50f17-4aa1-433b-bbb8-62ae51d5c4e8"
DEFAULT_AUTH_MODE = "tenant_chain"  # tenant_chain | azure_cli | browser | default


APP_CONFIGS = {
    "HR App": {
        "title": "Employee HR Assistant",
        "short_title": "HR",
        "accent": "#ffe600",
        "accent_soft": "rgba(255, 230, 0, 0.18)",
        "caption": "Ask about leave, onboarding, benefits, HR processes, workplace policies, or HR communications.",
        "context_label": "Policy Context",
        "upload_label": "Upload HR policy file",
        "chat_placeholder": "Ask an HR question...",
        "initial_message": "Hi, I am your HR AI assistant powered by Agent941. How can I help today?",
        "reset_message": "New HR chat started. Ask me any HR policy or employee support question.",
        "agent_context": (
            "You are answering inside an HR assistant application. Help employees with leave, benefits, "
            "onboarding, workplace policies, payroll questions, and HR communications. Avoid inventing "
            "company-specific policy details when context is missing."
        ),
        "quick_prompts": {
            "Leave Policy": "Please explain our leave policy in simple terms, including leave types and approval workflow.",
            "Onboarding": "Create an onboarding checklist for a new employee joining next week.",
            "Benefits": "Summarize common employee benefits and list what details I should verify with HR.",
            "HR Email": "Draft a professional email to HR asking for clarification about remote work eligibility.",
        },
    },
    "IT Helpdesk App": {
        "title": "IT Helpdesk Assistant",
        "short_title": "IT",
        "accent": "#35d0ff",
        "accent_soft": "rgba(53, 208, 255, 0.16)",
        "caption": "Get help with laptop issues, access requests, email, VPN, software, and troubleshooting.",
        "context_label": "IT Knowledge Context",
        "upload_label": "Upload IT SOP or troubleshooting guide",
        "chat_placeholder": "Describe the IT issue...",
        "initial_message": "Hi, I am your IT helpdesk assistant powered by Agent941. What issue should we troubleshoot?",
        "reset_message": "New IT helpdesk chat started. Describe the issue or access request.",
        "agent_context": (
            "You are answering inside an IT helpdesk application. Help users troubleshoot common endpoint, "
            "network, VPN, email, software, password, and access issues. Ask for missing device, urgency, "
            "error message, and business impact details before suggesting escalation."
        ),
        "quick_prompts": {
            "Laptop Issue": "My laptop is running very slow. Please give me a troubleshooting checklist.",
            "Password Reset": "Help me with steps for a password reset or account lockout issue.",
            "VPN Problem": "VPN is not connecting. What should I check before raising a ticket?",
            "Software Access": "Draft an IT access request for installing approved project software.",
        },
    },
    "ServiceNow Ticketing App": {
        "title": "ServiceNow Ticketing Assistant",
        "short_title": "SN",
        "accent": "#79e27d",
        "accent_soft": "rgba(121, 226, 125, 0.16)",
        "caption": "Create ticket drafts, classify incidents, summarize issues, and prepare assignment notes.",
        "context_label": "Ticketing Context",
        "upload_label": "Upload ticket policy, catalog, or SOP",
        "chat_placeholder": "Describe the ticket or incident...",
        "initial_message": "Hi, I am your ServiceNow ticketing assistant powered by Agent941. What ticket should we prepare?",
        "reset_message": "New ticketing chat started. Describe the incident, request, or change.",
        "agent_context": (
            "You are answering inside a ServiceNow ticketing application. Help draft incidents, service "
            "requests, assignment notes, impact/urgency, category, priority, short descriptions, and "
            "resolution notes. Keep outputs structured for ticket entry."
        ),
        "quick_prompts": {
            "Incident Draft": "Create a ServiceNow incident draft for a user unable to access email.",
            "Classify Ticket": "Classify this ticket by category, subcategory, impact, urgency, and priority.",
            "Assignment Notes": "Write clear assignment group notes for an unresolved VPN connectivity issue.",
            "Resolution Note": "Draft a professional resolution note after restoring application access.",
        },
    },
}


def inject_brand_styles() -> None:
    st.markdown(
        """
        <style>
            :root {
                --ey-yellow: #ffe600;
                --ey-black: #111111;
                --ey-panel: rgba(20, 20, 24, 0.92);
                --ey-border: rgba(255, 255, 255, 0.12);
            }

            .stApp {
                background:
                    radial-gradient(circle at 14% 10%, rgba(255, 230, 0, 0.16), transparent 26rem),
                    radial-gradient(circle at 84% 18%, rgba(53, 208, 255, 0.11), transparent 30rem),
                    linear-gradient(135deg, #111111 0%, #19191f 48%, #24242c 100%);
                color: #f7f7f7;
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0c0c0f 0%, #17171d 100%);
                border-right: 1px solid var(--ey-border);
            }

            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] span {
                color: #f2f2f2;
            }

            .ey-shell {
                border: 1px solid var(--ey-border);
                background: linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.035));
                border-radius: 8px;
                padding: 20px 22px;
                margin: 0 0 18px 0;
                box-shadow: 0 22px 70px rgba(0, 0, 0, 0.32);
            }

            .ey-topline {
                display: flex;
                align-items: center;
                gap: 18px;
                margin-bottom: 14px;
            }

            .ey-logo-mark {
                width: 76px;
                height: 54px;
                position: relative;
                flex: 0 0 auto;
            }

            .ey-logo-beam {
                position: absolute;
                left: 2px;
                top: 0;
                width: 72px;
                height: 10px;
                background: var(--ey-yellow);
                transform: skewY(-16deg);
                transform-origin: left center;
            }

            .ey-logo-text {
                position: absolute;
                left: 5px;
                bottom: 0;
                color: #ffffff;
                font-size: 34px;
                font-weight: 800;
                line-height: 1;
                letter-spacing: 0;
                font-family: Arial, Helvetica, sans-serif;
            }

            .ey-brand-kicker {
                color: var(--ey-yellow);
                font-weight: 700;
                font-size: 13px;
                letter-spacing: 0;
                text-transform: uppercase;
            }

            .ey-brand-title {
                font-size: 30px;
                font-weight: 760;
                margin-top: 4px;
                color: #ffffff;
                letter-spacing: 0;
            }

            .ey-brand-copy {
                color: #d8d8d8;
                margin-top: 6px;
                max-width: 820px;
                line-height: 1.45;
            }

            .ey-mode-row {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 10px;
                margin-top: 14px;
            }

            .ey-mode-chip {
                border-radius: 8px;
                padding: 11px 12px;
                background: rgba(255,255,255,0.07);
                border: 1px solid rgba(255,255,255,0.13);
                color: #f8f8f8;
                font-size: 13px;
                min-height: 54px;
            }

            .ey-mode-chip strong {
                display: block;
                color: #ffffff;
                margin-bottom: 2px;
            }

            .ey-mode-chip.hr { border-top: 4px solid #ffe600; }
            .ey-mode-chip.it { border-top: 4px solid #35d0ff; }
            .ey-mode-chip.sn { border-top: 4px solid #79e27d; }

            div[role="radiogroup"] {
                gap: 8px;
            }

            div[role="radiogroup"] label {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.13);
                border-radius: 8px;
                padding: 9px 10px;
                margin-bottom: 8px;
                transition: all 0.18s ease;
            }

            div[role="radiogroup"] label:hover {
                background: rgba(255, 230, 0, 0.12);
                border-color: rgba(255, 230, 0, 0.45);
            }

            div[role="radiogroup"] label:nth-of-type(1) { border-left: 5px solid #ffe600; }
            div[role="radiogroup"] label:nth-of-type(2) { border-left: 5px solid #35d0ff; }
            div[role="radiogroup"] label:nth-of-type(3) { border-left: 5px solid #79e27d; }

            .stButton > button {
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.16);
                background: linear-gradient(135deg, rgba(255,255,255,0.13), rgba(255,255,255,0.07));
                color: #ffffff;
                font-weight: 650;
            }

            .stButton > button:hover {
                border-color: var(--ey-yellow);
                color: var(--ey-yellow);
            }

            [data-testid="stChatMessage"] {
                background: rgba(255,255,255,0.075);
                border: 1px solid rgba(255,255,255,0.11);
                border-radius: 8px;
            }

            [data-testid="stTextInput"] input {
                background: rgba(255,255,255,0.08);
                border-color: rgba(255,255,255,0.16);
                color: #ffffff;
            }

            @media (max-width: 760px) {
                .ey-topline { align-items: flex-start; }
                .ey-mode-row { grid-template-columns: 1fr; }
                .ey-brand-title { font-size: 24px; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_brand_header() -> None:
    st.markdown(
        """
        <div class="ey-shell">
            <div class="ey-topline">
                <div class="ey-logo-mark" aria-label="EY">
                    <div class="ey-logo-beam"></div>
                    <div class="ey-logo-text">EY</div>
                </div>
                <div>
                    <div class="ey-brand-kicker">Ernst &amp; Young Global Limited</div>
                    <div class="ey-brand-title">Enterprise Agent Apps Portal</div>
                    <div class="ey-brand-copy">
                        A professional multi-application assistant experience for HR, IT helpdesk,
                        and ServiceNow ticketing workflows, powered by the shared Agent941 Foundry agent.
                    </div>
                </div>
            </div>
            <div class="ey-mode-row">
                <div class="ey-mode-chip hr"><strong>HR App</strong>People policies and employee support</div>
                <div class="ey-mode-chip it"><strong>IT Helpdesk App</strong>Access, devices, VPN and software help</div>
                <div class="ey-mode-chip sn"><strong>ServiceNow Ticketing App</strong>Incident drafts and ticket notes</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_config() -> dict[str, str]:
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT", DEFAULT_PROJECT_ENDPOINT).strip()
    agent_id = os.getenv("AZURE_AI_AGENT_ID", DEFAULT_AGENT_ID).strip()
    tenant_id = os.getenv("AZURE_TENANT_ID", DEFAULT_TENANT_ID).strip()
    auth_mode = os.getenv("AZURE_AUTH_MODE", DEFAULT_AUTH_MODE).strip().lower()
    return {
        "endpoint": endpoint,
        "agent_id": agent_id,
        "agent_name": os.getenv("AZURE_AI_AGENT_NAME", DEFAULT_AGENT_NAME).strip(),
        "deployment": os.getenv("AZURE_AI_DEPLOYMENT", DEFAULT_DEPLOYMENT).strip(),
        "model_version": os.getenv("AZURE_AI_MODEL_VERSION", DEFAULT_MODEL_VERSION).strip(),
        "temperature": os.getenv("AZURE_AI_AGENT_TEMPERATURE", DEFAULT_TEMPERATURE).strip(),
        "top_p": os.getenv("AZURE_AI_AGENT_TOP_P", DEFAULT_TOP_P).strip(),
        "tenant_id": tenant_id,
        "auth_mode": auth_mode,
    }


def build_azure_credential(tenant_id: str, auth_mode: str):
    """
    Builds a tenant-aware Azure credential.

    Why this is needed:
    - Your account is visible as an external/B2B-style UPN:
      avyuktitraining1_gmail.com#EXT#@avyuktitraining1gmail.onmicrosoft.com
    - Generic DefaultAzureCredential can pick the wrong cached tenant/account.
    - This function forces authentication against the expected tenant.
    """
    tenant_id = (tenant_id or "").strip()
    auth_mode = (auth_mode or "tenant_chain").strip().lower()

    if auth_mode == "azure_cli":
        return AzureCliCredential(tenant_id=tenant_id)

    if auth_mode == "browser":
        return InteractiveBrowserCredential(tenant_id=tenant_id)

    if auth_mode == "default":
        return DefaultAzureCredential(
            interactive_browser_tenant_id=tenant_id,
            additionally_allowed_tenants=[tenant_id, "*"],
            exclude_interactive_browser_credential=False,
        )

    # Recommended for your local Streamlit demo:
    # 1. Use Azure CLI token if already logged into the correct tenant.
    # 2. If CLI is not ready, open browser login against the correct tenant.
    return ChainedTokenCredential(
        AzureCliCredential(tenant_id=tenant_id),
        InteractiveBrowserCredential(tenant_id=tenant_id),
    )


@st.cache_resource(show_spinner=False)
def get_agents_client(endpoint: str, tenant_id: str, auth_mode: str) -> AgentsClient:
    return AgentsClient(
        endpoint=endpoint,
        credential=build_azure_credential(tenant_id, auth_mode),
    )


def extract_uploaded_text(uploaded_file) -> str:
    if uploaded_file is None:
        return ""

    suffix = Path(uploaded_file.name).suffix.lower()
    raw_bytes = uploaded_file.getvalue()

    if suffix in {".txt", ".md", ".csv"}:
        return raw_bytes.decode("utf-8", errors="ignore")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(raw_bytes))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            st.warning(f"Could not read PDF text: {exc}")
            return ""

    if suffix == ".docx":
        try:
            return extract_docx_text(raw_bytes)
        except Exception as exc:
            st.warning(f"Could not read Word document text: {exc}")
            return ""

    st.warning("Supported files: PDF, DOCX, TXT, MD, CSV.")
    return ""


def extract_docx_text(raw_bytes: bytes) -> str:
    with zipfile.ZipFile(BytesIO(raw_bytes)) as docx:
        document_xml = docx.read("word/document.xml")

    root = ElementTree.fromstring(document_xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        text_parts = [
            node.text
            for node in paragraph.findall(".//w:t", namespace)
            if node.text
        ]
        if text_parts:
            paragraphs.append(" ".join(text_parts))
    return "\n".join(paragraphs)


def normalize_text(text: str) -> str:
    """Normalize whitespace and a few common PDF extraction artifacts."""
    text = text or ""
    replacements = {
        "OƯice": "Office",
        "oƯice": "office",
        "": "•",
        "\u00a0": " ",
    }
    for old, new_value in replacements.items():
        text = text.replace(old, new_value)
    return re.sub(r"\s+", " ", text).strip()


def keyword_set(text: str) -> set[str]:
    stop_words = {
        "please", "tell", "about", "what", "when", "where", "which", "with", "from", "this", "that",
        "into", "your", "have", "show", "give", "need", "does", "will", "can", "for", "the", "and",
        "are", "you", "our", "how", "why", "who", "all", "any", "using", "explain", "policy",
        "more", "brief", "summary", "summarize", "details", "detail", "it", "doc", "document", "technology", "technologies", "abc",
        # Greeting / filler words must not trigger document retrieval.
        "hi", "hey", "hello", "there", "bro", "dear", "thanks", "thank", "ok", "okay", "yes", "no", "hmm", "hmmm", "dude",
    }
    return {
        word
        for word in re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", text.lower())
        if word not in stop_words
    }


def is_small_talk(prompt: str) -> bool:
    """Return True for greetings/acknowledgements so the app does not search documents or call Azure."""
    cleaned = re.sub(r"[^a-zA-Z ]+", " ", prompt.lower()).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return True

    greeting_phrases = {
        "hi", "hey", "hello", "hi there", "hey there", "hello there",
        "good morning", "good afternoon", "good evening", "gm", "gn",
        "thanks", "thank you", "ok", "okay", "yes", "no", "hmm", "hmmm", "bro", "dude",
    }
    if cleaned in greeting_phrases:
        return True

    words = cleaned.split()
    greeting_words = {"hi", "hey", "hello", "there", "bro", "dear", "thanks", "thank", "ok", "okay", "hmm", "hmmm", "dude"}
    return len(words) <= 3 and all(word in greeting_words for word in words)


def small_talk_answer(app_name: str) -> str:
    """Friendly response for greetings. No document retrieval, no Azure call, no fallback policy text."""
    if app_name == "HR App":
        return "Hi! I am your HR assistant. Ask me about a specific HR topic, for example: Leave Policy, Work From Home Policy, Benefits, Onboarding, or HR email draft."
    if app_name == "IT Helpdesk App":
        return "Hi! I am your IT helpdesk assistant. Please describe the issue, error message, device, and business impact so I can help properly."
    if app_name == "ServiceNow Ticketing App":
        return "Hi! I am your ServiceNow ticketing assistant. Please describe the incident or request, and I can prepare a ticket-ready summary."
    return "Hi! How can I help you today?"


SECTION_HEADINGS = [
    # HR headings
    "Work From Home Policy", "Leave Policy", "Laptop Policy", "Reimbursement Policy",
    "Office Timings", "Employee Benefits", "Benefits", "Onboarding Process", "Offboarding Process",
    "Payroll Policy", "Code of Conduct", "Travel Policy", "Attendance Policy",
    # IT headings
    "VPN Issues", "Password Reset", "Outlook Issues", "Software Access", "Laptop Issues",
    "Network Issues", "MFA Issues", "Email Issues", "IT Support Knowledge Base",
    # ServiceNow headings
    "Incident Draft", "Classify Ticket", "Assignment Notes", "Resolution Note", "SLA", "Priority", "Impact", "Urgency",
]

TOPIC_ALIASES = {
    "leave": ["Leave Policy"],
    "casual": ["Leave Policy"],
    "sick": ["Leave Policy"],
    "earned": ["Leave Policy"],
    "wfh": ["Work From Home Policy"],
    "remote": ["Work From Home Policy"],
    "home": ["Work From Home Policy"],
    "laptop": ["Laptop Policy", "Laptop Issues"],
    "reimbursement": ["Reimbursement Policy"],
    "internet": ["Reimbursement Policy"],
    "office": ["Office Timings"],
    "timing": ["Office Timings"],
    "timings": ["Office Timings"],
    "benefit": ["Employee Benefits", "Benefits"],
    "benefits": ["Employee Benefits", "Benefits"],
    "onboarding": ["Onboarding Process"],
    "joining": ["Onboarding Process"],
    "offboarding": ["Offboarding Process"],
    "exit": ["Offboarding Process"],
    "vpn": ["VPN Issues"],
    "password": ["Password Reset"],
    "outlook": ["Outlook Issues"],
    "software": ["Software Access"],
    "incident": ["Incident Draft"],
    "classification": ["Classify Ticket"],
    "classify": ["Classify Ticket"],
    "resolution": ["Resolution Note"],
}


def app_domain_score(app_name: str, text: str) -> int:
    """Prefer chunks that belong to the selected app domain and reduce cross-domain leakage."""
    lower = text.lower()
    domain_terms = {
        "HR App": ["leave", "benefit", "payroll", "employee", "onboarding", "offboarding", "hr", "work from home", "wfh", "reimbursement", "office timings"],
        "IT Helpdesk App": ["vpn", "password", "outlook", "email", "laptop", "software", "network", "access", "mfa", "device", "it support"],
        "ServiceNow Ticketing App": ["incident", "service request", "ticket", "priority", "impact", "urgency", "assignment", "sla", "resolution"],
    }
    return sum(1 for term in domain_terms.get(app_name, []) if term in lower)


def requested_headings(prompt: str) -> list[str]:
    """Map user wording like 'just leave policy' to the exact document section heading."""
    lower = prompt.lower()
    found: list[str] = []

    for heading in SECTION_HEADINGS:
        if heading.lower() in lower and heading not in found:
            found.append(heading)

    for key, headings in TOPIC_ALIASES.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            for heading in headings:
                if heading not in found:
                    found.append(heading)

    return found


def is_summary_request(prompt: str) -> bool:
    lower = prompt.lower()
    summary_words = ["brief", "summary", "summarize", "overview", "tell me about", "what is this", "what is", "explain document"]
    return any(word in lower for word in summary_words) and not requested_headings(prompt)


def split_context_into_sections(context_text: str) -> list[dict[str, str | int]]:
    """Split uploaded text by known policy/SOP headings instead of arbitrary nearby chunks."""
    clean = normalize_text(context_text)
    if not clean:
        return []

    matches = []
    for heading in SECTION_HEADINGS:
        pattern = rf"(?:^|\s)(?:\d+\.\s*)?({re.escape(heading)})(?=\s|:|$)"
        for match in re.finditer(pattern, clean, flags=re.IGNORECASE):
            matches.append((match.start(1), match.end(1), heading))

    # Deduplicate headings that start at the same location.
    unique = {}
    for start, end, heading in matches:
        key = (start, heading.lower())
        unique[key] = (start, end, heading)
    matches = sorted(unique.values(), key=lambda item: item[0])

    if not matches:
        return split_context_into_chunks(clean, max_chars=700)

    sections: list[dict[str, str | int]] = []

    # Optional intro section before first known heading.
    if matches[0][0] > 0:
        intro = clean[:matches[0][0]].strip(" -:.,")
        if len(intro) > 20:
            sections.append({"chunk_no": len(sections) + 1, "heading": "Document Title", "text": intro})

    for idx, (start, end, heading) in enumerate(matches):
        next_start = matches[idx + 1][0] if idx + 1 < len(matches) else len(clean)
        body = clean[end:next_start].strip(" -:.,")
        section_text = f"{heading}: {body}".strip()
        section_text = re.sub(r"\s+(?=\d+\.\s*)", " ", section_text)
        if len(section_text) > 8:
            sections.append({"chunk_no": len(sections) + 1, "heading": heading, "text": section_text[:1200]})

    return sections


def split_context_into_chunks(context_text: str, max_chars: int = 900) -> list[dict[str, str | int]]:
    """
    Fallback chunker only. Exact section extraction is preferred for policy/SOP documents.
    """
    clean_text = context_text.replace("\r", "\n")
    blocks = [
        normalize_text(block)
        for block in re.split(r"\n\s*\n|(?<=[.!?])\s+", clean_text)
        if normalize_text(block)
    ]

    chunks: list[dict[str, str | int]] = []
    buffer = ""
    chunk_no = 1

    for block in blocks:
        if len(buffer) + len(block) + 1 <= max_chars:
            buffer = f"{buffer} {block}".strip()
        else:
            if buffer:
                chunks.append({"chunk_no": chunk_no, "heading": "Chunk", "text": buffer})
                chunk_no += 1
            buffer = block[:max_chars]

    if buffer:
        chunks.append({"chunk_no": chunk_no, "heading": "Chunk", "text": buffer})

    return chunks


def retrieve_relevant_context(app_name: str, prompt: str, context_text: str, top_k: int = 6) -> list[dict[str, str | int]]:
    """
    Retrieves exact policy/SOP sections. This prevents 'Leave Policy' from returning WFH/laptop/reimbursement.
    """
    if not context_text.strip() or is_small_talk(prompt):
        return []

    sections = split_context_into_sections(context_text)
    exact_headings = requested_headings(prompt)

    if exact_headings:
        exact_matches = [
            section for section in sections
            if str(section.get("heading", "")).lower() in {h.lower() for h in exact_headings}
        ]
        if exact_matches:
            return exact_matches[:top_k]

    if is_summary_request(prompt):
        # Return first meaningful sections for a document brief, not random chunks.
        return [section for section in sections if section.get("heading") != "Document Title"][:top_k]

    query_words = keyword_set(prompt)
    if not query_words:
        return []

    scored = []
    for section in sections:
        section_text = str(section["text"])
        section_heading = str(section.get("heading", ""))
        section_words = keyword_set(section_text + " " + section_heading)
        overlap = query_words.intersection(section_words)
        heading_bonus = 6 if any(word in section_heading.lower() for word in query_words) else 0
        domain_bonus = min(app_domain_score(app_name, section_text), 3)
        score = (len(overlap) * 4) + heading_bonus + domain_bonus

        # Require query overlap; domain words alone should not retrieve unrelated sections.
        if overlap and score >= 4:
            scored.append((score, int(section["chunk_no"]), section))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [section for _, _, section in scored[:top_k]]


def clean_section_for_display(text: str) -> str:
    """Clean section text for user-friendly answer."""
    text = normalize_text(text)
    text = re.sub(r"\s*•\s*", "\n- ", text)
    text = re.sub(r"(?<!\n)\s+(?=\d+\.\s+[A-Z])", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def uploaded_context_answer(app_name: str, prompt: str, context_text: str) -> str:
    """
    Deterministic local answer used when Foundry fails.
    Returns exact matching section only for policy-specific questions.
    """
    if not context_text.strip():
        return ""

    relevant_sections = retrieve_relevant_context(app_name, prompt, context_text, top_k=6)

    verify_note = {
        "HR App": "Please verify the final interpretation with HR if this affects eligibility, approval, or payroll.",
        "IT Helpdesk App": "Please verify environment-specific tools, access rules, and approvals with IT support.",
        "ServiceNow Ticketing App": "Please verify live routing, assignment groups, and SLA values in ServiceNow.",
    }.get(app_name, "Please verify final details with the owning team.")

    if not relevant_sections:
        return (
            "I could not find this answer in the uploaded document. "
            "Please ask about a section that exists in the uploaded file or upload the correct policy/SOP.\n\n"
            f"{verify_note}"
        )

    if requested_headings(prompt) and len(relevant_sections) == 1:
        section = relevant_sections[0]
        heading = str(section.get("heading", "Matching Section"))
        answer = clean_section_for_display(str(section["text"]))
        return (
            f"Based only on the uploaded document, here is the **{heading}**:\n\n"
            f"{answer}\n\n"
            "I have included only the exact matching section from the uploaded document.\n\n"
            f"{verify_note}"
        )

    bullet_sections = []
    for section in relevant_sections:
        heading = str(section.get("heading", "Section"))
        body = clean_section_for_display(str(section["text"]))
        bullet_sections.append(f"### {heading}\n{body}")

    return (
        "Based only on the uploaded document, the relevant sections are:\n\n"
        + "\n\n".join(bullet_sections)
        + "\n\nI have not added company-policy details that are not visible in the uploaded document.\n\n"
        + verify_note
    )


def build_agent_prompt(app_name: str, user_prompt: str, context_text: str) -> str:
    app_config = APP_CONFIGS[app_name]
    relevant_chunks = retrieve_relevant_context(app_name, user_prompt, context_text, top_k=8)

    context_block = ""
    if context_text.strip():
        if relevant_chunks:
            chunk_text = "\n\n".join(
                f"[Source chunk {item['chunk_no']}]\n{item['text']}"
                for item in relevant_chunks
            )
            context_block = (
                "\n\nRELEVANT UPLOADED DOCUMENT EXCERPTS:\n"
                "<uploaded_context>\n"
                f"{chunk_text}\n"
                "</uploaded_context>\n"
            )
        else:
            context_block = (
                "\n\nThe user uploaded a document, but no relevant section was found for this question. "
                "Do not invent policy details. Ask the user to upload the correct policy/SOP or clarify the section.\n"
            )

    return (
        "You are a precise enterprise assistant. Follow these rules strictly:\n"
        "1. If uploaded_context is provided, answer ONLY from that context for policy/SOP-specific questions.\n"
        "2. If the answer is not present in uploaded_context, say: 'I could not find this in the uploaded document.'\n"
        "3. Do not invent numbers, eligibility, approvals, SLA, leave counts, benefits, or company rules.\n"
        "4. Use short headings and bullet points.\n"
        "5. Mention the source chunk number when using uploaded context.\n"
        "6. For generic questions without uploaded context, give general guidance and clearly say it is generic.\n\n"
        f"{app_config['agent_context']}"
        f"{context_block}\n"
        f"Application: {app_name}\n"
        f"User request:\n{user_prompt}"
    )


def message_text(message) -> str:
    if not getattr(message, "text_messages", None):
        return ""
    return message.text_messages[-1].text.value


def get_or_create_thread(client: AgentsClient, app_name: str) -> str:
    thread_key = f"thread_id_{app_name}"
    if thread_key not in st.session_state:
        thread = client.threads.create()
        st.session_state[thread_key] = thread.id
    return st.session_state[thread_key]


def ask_foundry_agent(client: AgentsClient, agent_id: str, app_name: str, prompt: str, context_text: str) -> str:
    thread_id = get_or_create_thread(client, app_name)
    agent_prompt = build_agent_prompt(app_name, prompt, context_text)

    client.messages.create(
        thread_id=thread_id,
        role="user",
        content=agent_prompt,
    )

    run = client.runs.create_and_process(
        thread_id=thread_id,
        agent_id=agent_id,
    )

    if run.status == "failed":
        raise RuntimeError(f"Agent run failed: {run.last_error}")
    if run.status not in ["completed", "succeeded"]:
        raise RuntimeError(f"Agent run ended with status: {run.status}")

    messages = client.messages.list(
        thread_id=thread_id,
        order=ListSortOrder.ASCENDING,
    )
    assistant_messages = [
        message_text(message)
        for message in messages
        if message.role == "assistant" and message_text(message)
    ]

    if not assistant_messages:
        return "The agent completed the run but did not return a text response."
    return assistant_messages[-1]


def format_agent_error(exc: Exception) -> str:
    error_text = str(exc)

    if isinstance(exc, ClientAuthenticationError):
        if "AADSTS50020" in error_text or "does not exist in tenant" in error_text:
            return (
                "Azure authentication failed because the selected account is not available in the tenant used by this app. "
                "Sign in with the external user shown in Entra ID or ask the tenant admin to add/enable that user and assign access."
            )

        if "AADSTS50076" in error_text or "multi-factor authentication" in error_text.lower():
            return (
                "Azure authentication requires MFA. Run tenant-specific device-code login, complete MFA, then restart Streamlit."
            )

        if ".azure" in error_text and "Permission denied" in error_text:
            return (
                "Azure authentication cannot read the local Azure CLI profile folder. Run PowerShell as your normal user, "
                "run `az logout`, `az account clear`, then tenant-specific login again."
            )

        return (
            "The cloud agent is configured, but this machine could not authenticate to the correct Azure tenant/project. "
            "Check AZURE_TENANT_ID, Azure CLI login, and RBAC access for the Foundry project."
        )

    return (
        "Azure AI Foundry agent request failed.\n\n"
        f"Error: `{exc}`\n\n"
        "Please confirm the project endpoint, agent ID, tenant ID, and your Azure permissions for this Foundry project."
    )


def context_note(app_name: str, context_text: str) -> str:
    if context_text.strip():
        return "\n\nUploaded context is available. Use only matching uploaded sections for company-specific answers."

    if app_name == "HR App":
        return "\n\nFor company-specific limits, eligibility, balances, or approvals, please verify the final policy with HR."
    if app_name == "IT Helpdesk App":
        return "\n\nFor environment-specific tools, approvals, or access rules, please verify with your IT support team."
    return "\n\nFor live routing, assignment groups, and SLA rules, please verify the final values in ServiceNow."


def fallback_answer(app_name: str, prompt: str, context_text: str) -> str:
    if is_small_talk(prompt):
        return small_talk_answer(app_name)

    context_answer = uploaded_context_answer(app_name, prompt, context_text)
    if context_answer:
        return context_answer

    if app_name == "IT Helpdesk App":
        return fallback_it_answer(prompt, context_text)
    if app_name == "ServiceNow Ticketing App":
        return fallback_servicenow_answer(prompt, context_text)
    return fallback_hr_answer(prompt, context_text)


def fallback_hr_answer(prompt: str, context_text: str) -> str:
    prompt_lower = prompt.lower()
    note = context_note("HR App", context_text)

    if "leave" in prompt_lower:
        return (
            "Here is a simple leave-policy summary:\n\n"
            "- Employees usually request planned leave in advance through the HR or leave-management system.\n"
            "- Common leave types include annual leave, sick leave, emergency leave, maternity/paternity leave, and unpaid leave.\n"
            "- Managers typically approve leave based on balance, business coverage, and policy eligibility.\n"
            "- Sick or emergency leave may require later documentation depending on company policy.\n"
            "- Employees should check leave balance before applying and keep their manager informed."
            f"{note}"
        )

    if "onboard" in prompt_lower or "joining" in prompt_lower:
        return (
            "Here is a practical onboarding checklist:\n\n"
            "- Confirm joining date, role, manager, work location, and reporting time.\n"
            "- Collect required identity, bank, tax, and employment documents.\n"
            "- Set up email, laptop, access cards, HR portal access, and collaboration tools.\n"
            "- Share company policies, code of conduct, security guidance, and benefits details.\n"
            "- Schedule introductions with the manager, team, HR, IT, and buddy or mentor.\n"
            "- Plan first-week goals, training sessions, and a 30-day check-in."
            f"{note}"
        )

    if "benefit" in prompt_lower:
        return (
            "Common employee benefits usually include:\n\n"
            "- Health or medical insurance.\n"
            "- Paid time off and holidays.\n"
            "- Retirement or savings plans where applicable.\n"
            "- Learning, certification, or training support.\n"
            "- Wellness, employee assistance, or flexible work programs.\n\n"
            "Details such as eligibility, enrollment window, dependents, and coverage limits should be checked with HR."
            f"{note}"
        )

    if "email" in prompt_lower or "draft" in prompt_lower:
        return (
            "Subject: Clarification Request Regarding HR Policy\n\n"
            "Dear HR Team,\n\n"
            "I hope you are doing well. I would like to request clarification regarding the relevant HR policy and the process I should follow. "
            "Please let me know the eligibility criteria, required approvals, and any documents or timelines I should be aware of.\n\n"
            "Thank you for your support.\n\n"
            "Best regards,"
            f"{note}"
        )

    return (
        "I can help with HR topics such as leave, onboarding, benefits, policy clarification, workplace guidance, and HR emails. "
        "Please share the specific HR question or process you want help with."
        f"{note}"
    )


def fallback_it_answer(prompt: str, context_text: str) -> str:
    prompt_lower = prompt.lower()
    note = context_note("IT Helpdesk App", context_text)

    if "vpn" in prompt_lower:
        return (
            "VPN troubleshooting checklist:\n\n"
            "- Confirm internet is working outside VPN.\n"
            "- Restart the VPN client and try signing in again.\n"
            "- Check username, MFA prompt, and password status.\n"
            "- Confirm system date/time is correct.\n"
            "- Try a different network such as mobile hotspot.\n"
            "- Capture the exact error message and time of failure.\n"
            "- If still failing, raise a ticket with device name, OS, location, VPN client version, and business impact."
            f"{note}"
        )

    if "password" in prompt_lower or "locked" in prompt_lower:
        return (
            "Password or lockout guidance:\n\n"
            "- Use the approved self-service password reset portal if available.\n"
            "- Wait a few minutes after repeated failed attempts before retrying.\n"
            "- Confirm MFA method is active and accessible.\n"
            "- Update saved passwords on phone, email client, VPN, and browser after reset.\n"
            "- Raise a ticket if the account remains locked or MFA is unavailable."
            f"{note}"
        )

    if "software" in prompt_lower or "install" in prompt_lower or "access" in prompt_lower:
        return (
            "Software or access request draft:\n\n"
            "- Request type: Software/access request.\n"
            "- Business justification: Needed for assigned project work.\n"
            "- User details: Name, email, department, manager.\n"
            "- Asset details: Laptop hostname or asset tag.\n"
            "- Software/access needed: Name, version, environment, role.\n"
            "- Approval needed: Manager and application owner if required."
            f"{note}"
        )

    return (
        "Please share the issue category, device name, error message, when it started, urgency, and business impact. "
        "I can then provide troubleshooting steps or a ticket-ready summary."
        f"{note}"
    )


def fallback_servicenow_answer(prompt: str, context_text: str) -> str:
    prompt_lower = prompt.lower()
    note = context_note("ServiceNow Ticketing App", context_text)

    if "classify" in prompt_lower:
        return (
            "Ticket classification template:\n\n"
            "- Type: Incident or Service Request.\n"
            "- Category: Application, Access, Hardware, Network, Security, or Software.\n"
            "- Subcategory: Specific affected service or component.\n"
            "- Impact: Single user, multiple users, department, or enterprise.\n"
            "- Urgency: Low, medium, high, or critical based on business impact.\n"
            "- Priority: Derived from impact and urgency.\n"
            "- Assignment group: Team that owns the affected service."
            f"{note}"
        )

    if "resolution" in prompt_lower:
        return (
            "Resolution note draft:\n\n"
            "Issue was investigated and the affected service/access was restored. Validation was completed with the user or monitoring evidence. "
            "No further action is pending at this time. Ticket can be closed after user confirmation."
            f"{note}"
        )

    return (
        "ServiceNow ticket draft:\n\n"
        "- Short description: User is experiencing an access or service issue.\n"
        "- Description: Include affected user, service, error message, start time, troubleshooting already attempted, and business impact.\n"
        "- Category: To be selected based on affected service.\n"
        "- Impact: Confirm number of affected users.\n"
        "- Urgency: Confirm business deadline or work stoppage.\n"
        "- Assignment notes: Please investigate, validate access/service status, and update the user with next steps."
        f"{note}"
    )


def initialize_state() -> None:
    if "active_app" not in st.session_state:
        st.session_state.active_app = "HR App"
    if "app_messages" not in st.session_state:
        st.session_state.app_messages = {}
    if "app_contexts" not in st.session_state:
        st.session_state.app_contexts = {}
    if "app_context_files" not in st.session_state:
        st.session_state.app_context_files = {}

    for app_name, app_config in APP_CONFIGS.items():
        if app_name not in st.session_state.app_messages:
            st.session_state.app_messages[app_name] = [
                {
                    "role": "assistant",
                    "content": app_config["initial_message"],
                }
            ]
        if app_name not in st.session_state.app_contexts:
            st.session_state.app_contexts[app_name] = ""
        if app_name not in st.session_state.app_context_files:
            st.session_state.app_context_files[app_name] = ""


def reset_chat(app_name: str) -> None:
    st.session_state.app_messages[app_name] = [
        {
            "role": "assistant",
            "content": APP_CONFIGS[app_name]["reset_message"],
        }
    ]
    st.session_state.pop(f"thread_id_{app_name}", None)


def main() -> None:
    st.set_page_config(page_title="EY Agent Apps Portal", page_icon="EY", layout="wide")
    inject_brand_styles()
    initialize_state()

    config = get_config()
    endpoint = config["endpoint"]
    agent_id = config["agent_id"]
    app_names = list(APP_CONFIGS.keys())
    active_app = st.session_state.active_app
    app_config = APP_CONFIGS[active_app]
    context_text = st.session_state.app_contexts[active_app]
    messages = st.session_state.app_messages[active_app]

    with st.sidebar:
        st.title("Agent Apps Portal")
        st.caption("Ernst & Young Global Limited")

        selected_app = st.radio(
            "Application",
            app_names,
            index=app_names.index(active_app),
        )
        if selected_app != active_app:
            st.session_state.active_app = selected_app
            st.rerun()

        st.subheader("Foundry Agent")
        st.selectbox(
            "Assistant engine",
            ["Azure AI Foundry Agent"],
            index=0,
            disabled=True,
        )
        st.text_input("Agent name", value=config["agent_name"], disabled=True)
        st.text_input("Project endpoint", value=endpoint, disabled=True)
        st.text_input("Agent ID", value=agent_id, disabled=True)
        st.text_input("Tenant ID", value=config["tenant_id"], disabled=True)
        st.text_input("Auth mode", value=config["auth_mode"], disabled=True)
        st.text_input("Deployment", value=f"{config['deployment']} ({config['model_version']})", disabled=True)
        st.text_input("Temperature target", value=config["temperature"], disabled=True)
        st.text_input("Top P target", value=config["top_p"], disabled=True)
        st.caption("For an existing Foundry agent, temperature/top-p must also be configured in the agent/model settings if your SDK/API version supports it.")
        st.success(f"{config['agent_name']} is configured for all apps.")
        thread_key = f"thread_id_{active_app}"
        if thread_key in st.session_state:
            st.text_input("Thread ID", value=st.session_state[thread_key], disabled=True)

        st.subheader(app_config["context_label"])
        uploaded_file = st.file_uploader(
            app_config["upload_label"],
            type=["pdf", "docx", "txt", "md", "csv"],
            key=f"upload_{active_app}",
        )
        if uploaded_file:
            previous_file = st.session_state.app_context_files.get(active_app, "")
            st.session_state.app_contexts[active_app] = extract_uploaded_text(uploaded_file)
            st.session_state.app_context_files[active_app] = uploaded_file.name
            if previous_file != uploaded_file.name:
                st.session_state.pop(f"thread_id_{active_app}", None)
            context_text = st.session_state.app_contexts[active_app]
            if context_text:
                st.success(f"Loaded {len(context_text):,} characters from {uploaded_file.name}")

        if st.button("Clear chat", use_container_width=True):
            reset_chat(active_app)
            st.rerun()

    render_brand_header()
    st.markdown(
        f"""
        <div style="
            border-left: 6px solid {app_config['accent']};
            background: {app_config['accent_soft']};
            border-radius: 8px;
            padding: 14px 16px;
            margin-bottom: 16px;
        ">
            <div style="font-size: 13px; color: {app_config['accent']}; font-weight: 750;">
                Active application: {active_app}
            </div>
            <div style="font-size: 26px; color: #ffffff; font-weight: 760; margin-top: 2px;">
                {app_config['title']}
            </div>
            <div style="color: #e4e4e4; margin-top: 5px;">
                {app_config['caption']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    quick_prompts = app_config["quick_prompts"]
    cols = st.columns(len(quick_prompts))
    for col, (label, prompt_text) in zip(cols, quick_prompts.items()):
        if col.button(label, use_container_width=True):
            st.session_state.pending_prompt = prompt_text

    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input(app_config["chat_placeholder"])
    if "pending_prompt" in st.session_state:
        prompt = st.session_state.pop("pending_prompt")

    if prompt:
        st.session_state.app_messages[active_app].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if is_small_talk(prompt):
                answer = small_talk_answer(active_app)
                st.markdown(answer)
                st.session_state.app_messages[active_app].append({"role": "assistant", "content": answer})
            else:
                with st.spinner("Asking Azure AI Foundry agent..."):
                    try:
                        client = get_agents_client(endpoint, config["tenant_id"], config["auth_mode"])
                        answer = ask_foundry_agent(
                            client=client,
                            agent_id=agent_id,
                            app_name=active_app,
                            prompt=prompt,
                            context_text=context_text,
                        )
                    except Exception as exc:
                        st.caption(format_agent_error(exc))
                        answer = fallback_answer(active_app, prompt, context_text)

                    st.markdown(answer)
                    st.session_state.app_messages[active_app].append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
