import re
from typing import Tuple


# Patterns that usually indicate prompt injection, jailbreak, or attempts to
# inspect hidden instructions.
BLOCKED_PATTERNS = [
    r"ignore previous instructions",
    r"reveal system prompt",
    r"show hidden prompt",
    r"bypass policy",
    r"disable guardrails",
    r"jailbreak",
    r"developer message",
    r"system message",
]

# Patterns that should not appear in generated answers because they look like
# credentials or other sensitive configuration values.
SENSITIVE_PATTERNS = [
    r"api[_ -]?key",
    r"password",
    r"secret",
    r"connection string",
    r"private key",
    r"token",
]


def input_guardrail(user_prompt: str) -> Tuple[bool, str]:
    """Block obvious unsafe user prompts before any cloud API call."""
    prompt_lower = user_prompt.lower()

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, prompt_lower):
            return False, "Blocked: possible prompt injection or jailbreak attempt."

    return True, "Allowed"


def output_guardrail(ai_response: str) -> Tuple[bool, str]:
    """Block model responses that appear to contain sensitive information."""
    response_lower = ai_response.lower()

    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, response_lower):
            return False, "Blocked: response may contain sensitive data."

    return True, "Allowed"
