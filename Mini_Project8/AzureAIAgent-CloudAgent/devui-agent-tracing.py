"""Expose a conversation-scoped Foundry agent in DevUI with tracing enabled.

The sample focuses on agent creation, async Azure authentication, and observing
agent runs through the local DevUI.
"""

# Install dependencies from a terminal before running this script. Notebook
# shell syntax such as `! pip install ...` is intentionally not executed here.
import os
import asyncio
from dotenv import load_dotenv
from agent_framework import ChatAgent
from agent_framework.azure import AzureAIClient
from azure.identity.aio import AzureCliCredential
from agent_framework.devui import serve
from azure.ai.projects.aio import AIProjectClient

async def create_docs_agent(project_endpoint: str, model: str) -> ChatAgent:
    """Create a documentation assistant backed by one Foundry conversation."""
    # AzureCliCredential reuses the developer identity created by `az login`.
    credential = AzureCliCredential()
    
    # AIProjectClient is the authenticated entry point to the Foundry project.
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=credential
    )

    # A conversation gives the agent a stable place to store message history.
    openai_client = project_client.get_openai_client()
    conversation = await openai_client.conversations.create()
    conversation_id = conversation.id
    print("Conversation ID: ", conversation_id)

    # AzureAIClient binds the project, conversation, and deployed model.
    chat_client = AzureAIClient(project_client=project_client,
                                conversation_id=conversation_id,
                                model_deployment_name=model)

    try:

        # Instructions define the agent's purpose and expected behavior.
        agent = chat_client.create_agent(
            name="docs-agent",
            instructions="You are a helpful assistant that can help with documentation questions."
        )

        print("Agent created successfully!")
        return agent
    except Exception as e:
        # Returning None lets the caller decide whether the UI should start.
        print(f"Failed to create agent: {e}")
        return None

async def load_agent():
    """Load configuration and create the agent asynchronously."""
    # .env keeps project and model settings out of source control.
    load_dotenv()
    project_endpoint = os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
    model = os.getenv("AI_FOUNDRY_DEPLOYMENT_NAME")

    agent = await create_docs_agent(project_endpoint=project_endpoint, model=model)

    return agent

def main():
    """Create the agent, then host it in the local DevUI."""
    # asyncio.run allows a normal Python entry point to call async Azure APIs.
    agent = asyncio.run(load_agent())
    # tracing_enabled records agent activity for inspection in DevUI.
    serve(entities=[agent], auto_open=True, tracing_enabled=True)

if __name__ == "__main__":
    # This guard prevents DevUI from starting when the module is imported.
    main()
