"""Python bridge for optional Azure AI agent-reference calls.

Express sends JSON through stdin with the project endpoint, agent reference
name/version, and messages. This script calls Azure AI Projects and writes a
small JSON response to stdout so Node can return it to the React UI.
"""

import json
import sys

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


def main():
    payload = json.load(sys.stdin)
    endpoint = payload["endpoint"]
    agent_name = payload["agentName"]
    agent_version = payload["agentVersion"]
    messages = payload["messages"]

    project_client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )
    openai_client = project_client.get_openai_client()

    response = openai_client.responses.create(
        input=messages,
        extra_body={
            "agent_reference": {
                "name": agent_name,
                "version": agent_version,
                "type": "agent_reference",
            }
        },
    )

    print(json.dumps({"answer": response.output_text}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        sys.exit(1)
