"""Demo 3: Call a real Azure OpenAI model.

This demo is intentionally separate from app.py so the original deterministic
ReAct teaching flow stays unchanged.

Application logic:
1. Read the user question from command-line arguments.
2. If no question is provided, ask interactively in the terminal.
3. Pass the question to ask_llm() from llm_client.py.
4. Print the real Azure OpenAI response.
"""

from __future__ import annotations

import argparse

from llm_client import ask_llm


def parse_args() -> argparse.Namespace:
    """Read the question from the command line when provided.

    nargs="*" means the user can pass a sentence without wrapping every word
    separately in code. Example:

        python azure_openai_demo.py "VPN is not working"
    """

    parser = argparse.ArgumentParser(description="Ask the configured Azure OpenAI deployment.")
    parser.add_argument("question", nargs="*", help="Question to ask the real LLM")
    return parser.parse_args()


if __name__ == "__main__":
    # Step 1: Read command-line arguments.
    args = parse_args()

    # Step 2: Convert all words into one question string. If the user did not
    # pass a question, fall back to interactive terminal input.
    user_input = " ".join(args.question).strip() or input("Ask the LLM: ").strip()

    # Step 3: Call the shared LLM client. This is where the real Azure OpenAI
    # request happens through llm_client.py.
    answer = ask_llm(user_input)

    # Step 4: Print only the final answer, keeping this demo simple for learners.
    print(answer)
