"""Shared Azure OpenAI client helper used by the real LLM demo.

The main ReAct demo in app.py remains deterministic for basic understanding.
This module is the separate bridge to a real model when you want live LLM
answers.

Application logic:
1. Load Azure OpenAI settings from the .env file.
2. Validate required configuration values.
3. Build the correct OpenAI SDK client for the endpoint style.
4. Send the user input to the configured model deployment.
5. Let the model decide whether to call local tools.
6. Execute requested tools such as search_knowledge_base or create_ticket.
7. Send tool results back to the model and return the final answer.
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI

from tools import create_ticket, search_knowledge_base


# Tool definitions tell the LLM which local Python functions it is allowed to
# call. The model does not run Python directly; it returns a structured tool
# request, and this file executes the matching local function.
HELPDESK_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the internal helpdesk knowledge base for troubleshooting steps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue": {
                        "type": "string",
                        "description": "The user's IT issue, for example VPN is not working.",
                    }
                },
                "required": ["issue"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Create an IT support ticket or case when the user asks for one or the issue cannot be resolved.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue": {
                        "type": "string",
                        "description": "The user's IT issue that should be included in the ticket.",
                    }
                },
                "required": ["issue"],
                "additionalProperties": False,
            },
        },
    },
]


def _get_required_env(name: str) -> str:
    """Read a required environment variable and raise a helpful error.

    This keeps configuration problems easy to understand. For example, if
    AZURE_OPENAI_API_KEY is missing, the app fails with a clear message instead
    of a lower-level SDK authentication error.
    """

    # os.getenv returns None when a variable is missing, so the default empty
    # string keeps the next line simple and safe.
    value = os.getenv(name, "").strip()

    # Required values must be present before we try to create the SDK client.
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


def _build_client() -> tuple[AzureOpenAI | OpenAI, str]:
    """Create a client for either Azure OpenAI endpoint style.

    Azure OpenAI can be called in two common ways:
    - New OpenAI-compatible endpoint style ending with /openai/v1
    - Classic Azure OpenAI endpoint style using AzureOpenAI + api_version
    """

    # Load variables from .env into process environment variables.
    load_dotenv()

    # Required values for all Azure OpenAI calls.
    endpoint = _get_required_env("AZURE_OPENAI_ENDPOINT").rstrip("/")
    api_key = _get_required_env("AZURE_OPENAI_API_KEY")
    deployment_name = _get_required_env("AZURE_OPENAI_DEPLOYMENT_NAME")

    # API version is mainly used by the classic AzureOpenAI client style.
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-11-20").strip()

    # The provided endpoint uses the OpenAI-compatible v1 shape:
    # https://<resource>.openai.azure.com/openai/v1
    if endpoint.endswith("/openai/v1"):
        client = OpenAI(api_key=api_key, base_url=endpoint)
    else:
        # This branch supports the older Azure endpoint shape:
        # https://<resource>.openai.azure.com
        client = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)

    # The deployment name is passed as model=... in the chat completion call.
    return client, deployment_name


def _execute_tool_call(tool_name: str, arguments_json: str) -> str:
    """Run the local Python function requested by the model.

    Args:
        tool_name: Function name selected by the LLM.
        arguments_json: JSON string containing function arguments.

    Returns:
        The local tool result as plain text.
    """

    # The SDK gives function arguments as JSON text. Convert it back to a
    # Python dictionary before calling the local tool.
    arguments = json.loads(arguments_json or "{}")
    issue = arguments.get("issue", "")

    if tool_name == "search_knowledge_base":
        return search_knowledge_base(issue)

    if tool_name == "create_ticket":
        return create_ticket(issue)

    return f"Unknown tool requested: {tool_name}"


def ask_llm(user_input: str) -> str:
    """Ask the configured Azure OpenAI deployment for a helpdesk response.

    Args:
        user_input: The user's IT issue or question.

    Returns:
        The final text answer generated by the model after any tool calls.
    """

    # Build the SDK client only when needed so .env changes are picked up on
    # each run of the script.
    client, deployment_name = _build_client()

    # Chat completions use a list of messages. The system message sets the
    # assistant behavior, and the user message contains the actual question.
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful IT helpdesk assistant. "
                "Use search_knowledge_base when the user wants troubleshooting steps. "
                "Use create_ticket when the user asks to create a ticket, case, or incident. "
                "After a tool runs, include the exact ticket or KB result in your final answer."
            ),
        },
        {"role": "user", "content": user_input},
    ]

    # First model call: the LLM either answers directly or returns a structured
    # tool request such as create_ticket({"issue": "..."}).
    response = client.chat.completions.create(
        model=deployment_name,
        messages=messages,
        tools=HELPDESK_TOOLS,
        tool_choice="auto",
        # Lower temperature keeps helpdesk answers more stable and practical.
        temperature=0.2,
    )

    assistant_message = response.choices[0].message

    # If the model did not request any tool, return its direct answer.
    if not assistant_message.tool_calls:
        return assistant_message.content or ""

    # Add the assistant tool request to the conversation before sending tool
    # outputs back. This preserves the required chat history shape.
    messages.append(assistant_message.model_dump(exclude_none=True))

    # Execute each tool call requested by the LLM and append the result.
    for tool_call in assistant_message.tool_calls:
        tool_name = tool_call.function.name
        tool_result = _execute_tool_call(tool_name, tool_call.function.arguments)

        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            }
        )

    # Second model call: now that tool results are available, ask the model to
    # produce the final user-facing answer.
    final_response = client.chat.completions.create(
        model=deployment_name,
        messages=messages,
        temperature=0.2,
    )

    return final_response.choices[0].message.content or ""
