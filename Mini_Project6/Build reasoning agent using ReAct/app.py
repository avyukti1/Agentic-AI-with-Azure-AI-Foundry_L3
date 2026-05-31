"""Demo 1: IT Helpdesk ReAct Agent.

The demo prints each ReAct stage:
Thought -> Action -> Observation -> Final Answer.

This file is intentionally deterministic. It does not call Azure OpenAI or
Azure AI Foundry. The goal is to teach the ReAct reasoning pattern first.
"""

from __future__ import annotations

import argparse

from tools import create_ticket, search_knowledge_base


def run_agent(user_input: str) -> str:
    """Run a deterministic ReAct-style helpdesk flow.

    Args:
        user_input: The IT issue entered by the user.

    Returns:
        The final answer shown to the user.
    """

    # User Question: capture and display the issue.
    print(f"\nUser: {user_input}")

    # Thought: explain the reasoning step before selecting a tool.
    print("\nThought: The user has reported an IT issue. I should search the knowledge base first.")

    # Action: choose and call the knowledge base search tool.
    print("\nAction: search_knowledge_base")
    kb_result = search_knowledge_base(user_input)

    # Observation: display the tool result.
    print("\nObservation:")
    print(kb_result)

    # Decision: if the KB has no answer, create a ticket.
    if "No matching" in kb_result:
        print("\nThought: No KB article was found. I should create a ticket.")

        # Action: call the ticket creation tool.
        print("\nAction: create_ticket")
        ticket_result = create_ticket(user_input)

        # Observation: display ticket creation result.
        print("\nObservation:")
        print(ticket_result)

        # Final Answer: explain that a ticket was created.
        final_answer = (
            "I could not find a matching knowledge base article.\n\n"
            f"{ticket_result}\n\n"
            "Our IT team will review this issue."
        )
    else:
        # Final Answer: return the KB troubleshooting article.
        final_answer = (
            "I found a troubleshooting guide for your issue:\n\n"
            f"{kb_result}\n\n"
            "Please try these steps. If the issue continues, I can create an IT ticket."
        )

    print("\nFinal Answer:")
    print(final_answer)

    return final_answer


def parse_args() -> argparse.Namespace:
    """Read the issue from the command line when provided."""
    parser = argparse.ArgumentParser(description="Run the IT Helpdesk ReAct Agent demo.")
    parser.add_argument("issue", nargs="*", help="IT issue to troubleshoot, for example: VPN is not working")
    return parser.parse_args()


if __name__ == "__main__":
    # If an issue is passed as a command-line argument, use it.
    # Otherwise, ask the user interactively.
    args = parse_args()
    user_question = " ".join(args.issue).strip() or input("Enter your IT issue: ").strip()
    run_agent(user_question)
