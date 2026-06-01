"""Demo 2: Structured response generator for API-ready outputs.

This demo shows how an application can force predictable output using a fixed
JSON shape. API-ready JSON is useful when another system needs to consume the
agent result, such as a web app, workflow, dashboard, or ticketing system.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from tools import search_knowledge_base


def classify_issue(issue: str) -> str:
    """Classify the issue into a simple helpdesk category.

    This is a rule-based version of what an LLM or classifier could do.
    """
    issue_lower = issue.lower()

    # Keyword-based classification keeps the demo easy to explain.
    if "vpn" in issue_lower:
        return "vpn"
    if "email" in issue_lower or "outlook" in issue_lower:
        return "email"
    if "laptop" in issue_lower or "slow" in issue_lower:
        return "laptop"

    return "unknown"


def get_priority(issue_type: str) -> str:
    """Return a demo priority for the issue category."""

    # The priority map is part of the structured business logic.
    priorities = {
        "vpn": "medium",
        "email": "medium",
        "laptop": "low",
        "unknown": "high",
    }
    return priorities[issue_type]


def parse_steps(kb_result: str) -> list[str]:
    """Extract numbered troubleshooting steps from the KB article.

    The KB articles are stored as text, but the JSON response needs an array.
    This function converts numbered lines into list items.
    """
    steps = []

    for line in kb_result.splitlines():
        cleaned_line = line.strip()
        # Example matched line: "1. Check your internet connection."
        if len(cleaned_line) > 3 and cleaned_line[0].isdigit() and cleaned_line[1] == ".":
            steps.append(cleaned_line[3:].strip())

    return steps


def generate_structured_response(issue: str) -> dict[str, Any]:
    """Generate an API-ready helpdesk response using a fixed JSON schema."""

    # Step 1: classify the issue.
    issue_type = classify_issue(issue)

    # Step 2: search the same KB tool used by the ReAct demo.
    kb_result = search_knowledge_base(issue)

    # Step 3: decide whether a ticket is required.
    ticket_required = issue_type == "unknown"

    # Step 4: build the fixed schema expected by downstream applications.
    response = {
        "issue": issue,
        "issue_type": issue_type,
        "priority": get_priority(issue_type),
        "ticket_required": ticket_required,
        "ticket_id": "INC1001" if ticket_required else None,
        "recommended_steps": [] if ticket_required else parse_steps(kb_result),
        "final_message": "",
    }

    # Step 5: add a human-friendly final message while keeping JSON structure.
    if ticket_required:
        response["final_message"] = (
            "No matching knowledge base article was found. "
            "A ticket has been created for IT review."
        )
    else:
        response["final_message"] = (
            f"Please try the recommended {issue_type} troubleshooting steps. "
            "If the issue continues, an IT ticket can be created."
        )

    return response


def parse_args() -> argparse.Namespace:
    """Read the issue from the command line when provided."""
    parser = argparse.ArgumentParser(description="Generate an API-ready structured helpdesk response.")
    parser.add_argument("issue", nargs="*", help="IT issue, for example: VPN is not working")
    return parser.parse_args()


if __name__ == "__main__":
    # If an issue is passed as a command-line argument, use it.
    # Otherwise, ask the user interactively.
    args = parse_args()
    user_issue = " ".join(args.issue).strip() or input("Enter your IT issue: ").strip()
    structured_response = generate_structured_response(user_issue)

    # Print formatted JSON so it is readable in terminal and API-ready.
    print(json.dumps(structured_response, indent=2))
