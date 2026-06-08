"""DevUI demo showing how the A2A client and A2A server are wired together.

Run the notebook server first:
    a2a_server.ipynb

Then run this file:
    python a2a_server_client_devui.py

Open DevUI at:
    http://localhost:8093
"""

import asyncio
import logging
from dataclasses import dataclass

import httpx
from a2a.client import ClientFactory, create_text_message_object
from a2a.client.card_resolver import A2ACardResolver
from a2a.client.client import ClientConfig
from a2a.types import AgentCard, TransportProtocol
from a2a.utils.message import get_message_text
from agent_framework import Executor, WorkflowBuilder, WorkflowContext, WorkflowViz, handler
from agent_framework.devui import serve


A2A_SERVER_URL = "http://localhost:8080"
A2A_AGENT_CARD_URL = f"{A2A_SERVER_URL}/.well-known/agent-card.json"


@dataclass
class ClientRequest:
    user_prompt: str
    base_url: str


@dataclass
class DiscoveredAgent:
    user_prompt: str
    base_url: str
    agent_card: AgentCard
    summary: str


@dataclass
class A2AProtocolRequest:
    user_prompt: str
    base_url: str
    agent_card: AgentCard
    wire_summary: str


@dataclass
class A2AProtocolResponse:
    user_prompt: str
    base_url: str
    agent_card: AgentCard
    response_text: str
    wire_summary: str


class CLIENT_UserPrompt(Executor):
    @handler
    async def handle(self, user_prompt: str, ctx: WorkflowContext[ClientRequest]) -> None:
        prompt = user_prompt.strip() or "Tell me how to create an Azure Storage Account using Azure CLI."
        await ctx.send_message(ClientRequest(user_prompt=prompt, base_url=A2A_SERVER_URL))


class A2A_DISCOVERY_GetAgentCard(Executor):
    @handler
    async def handle(self, request: ClientRequest, ctx: WorkflowContext[DiscoveredAgent]) -> None:
        async with httpx.AsyncClient(timeout=10.0) as httpx_client:
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=request.base_url)
            agent_card = await resolver.get_agent_card()

        skills = ", ".join(skill.id for skill in agent_card.skills)
        summary = f"""A2A DISCOVERY COMPLETE

Client called:
{request.base_url}/.well-known/agent-card.json

Discovered remote A2A server:
- Agent Card name: {agent_card.name}
- URL: {agent_card.url}
- Preferred transport: {agent_card.preferred_transport}
- Streaming: {agent_card.capabilities.streaming}
- Skills: {skills}
"""
        await ctx.send_message(
            DiscoveredAgent(
                user_prompt=request.user_prompt,
                base_url=request.base_url,
                agent_card=agent_card,
                summary=summary,
            )
        )


class CLIENT_BuildA2AJsonRpcMessage(Executor):
    @handler
    async def handle(self, discovered: DiscoveredAgent, ctx: WorkflowContext[A2AProtocolRequest]) -> None:
        wire_summary = f"""{discovered.summary}

A2A CLIENT MESSAGE BUILD

The client now creates:
- ClientConfig(supported_transports=[TransportProtocol.jsonrpc], streaming=True)
- ClientFactory(config).create(agent_card)
- create_text_message_object(content=user_prompt)

This prepares the JSON-RPC streaming request that will be posted to the remote A2A server.
"""
        await ctx.send_message(
            A2AProtocolRequest(
                user_prompt=discovered.user_prompt,
                base_url=discovered.base_url,
                agent_card=discovered.agent_card,
                wire_summary=wire_summary,
            )
        )


class A2A_PROTOCOL_JsonRpcStreaming(Executor):
    @handler
    async def handle(self, protocol_request: A2AProtocolRequest, ctx: WorkflowContext[A2AProtocolRequest]) -> None:
        print("A2A protocol boundary: client will use JSON-RPC streaming over HTTP.")
        await ctx.send_message(protocol_request)


class SERVER_RemoteA2AFoundryAgent(Executor):
    @handler
    async def handle(self, protocol_request: A2AProtocolRequest, ctx: WorkflowContext[A2AProtocolResponse]) -> None:
        chunks: list[str] = []

        timeout = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as httpx_client:
            config = ClientConfig(
                httpx_client=httpx_client,
                supported_transports=[TransportProtocol.jsonrpc],
                streaming=True,
            )
            client = ClientFactory(config).create(protocol_request.agent_card)
            request = create_text_message_object(content=protocol_request.user_prompt)

            async for response in client.send_message(request):
                task, _ = response
                if task.artifacts:
                    chunks.append(get_message_text(task.artifacts[-1]))

        response_text = "".join(chunks)
        wire_summary = f"""{protocol_request.wire_summary}

REMOTE SERVER EXECUTION

The remote A2A server at {protocol_request.base_url} received the JSON-RPC streaming request.

Inside the server notebook:
1. A2AStarletteApplication receives the request.
2. DefaultRequestHandler routes it to FoundryAgentExecutor.
3. FoundryAgentExecutor extracts RequestContext user input.
4. FoundryAgent.invoke_agent_stream calls Azure AI Foundry.
5. The Foundry Agent can use the Microsoft Learn MCP tool.
6. Foundry response deltas are emitted as A2A TaskArtifactUpdateEvent objects.
"""
        await ctx.send_message(
            A2AProtocolResponse(
                user_prompt=protocol_request.user_prompt,
                base_url=protocol_request.base_url,
                agent_card=protocol_request.agent_card,
                response_text=response_text,
                wire_summary=wire_summary,
            )
        )


class CLIENT_RenderStreamedResult(Executor):
    @handler
    async def handle(self, protocol_response: A2AProtocolResponse, ctx: WorkflowContext[str]) -> None:
        output = f"""A2A CLIENT/SERVER CONNECTION RESULT

WIRING SUMMARY

CLIENT_UserPrompt
  -> A2A_DISCOVERY_GetAgentCard
  -> CLIENT_BuildA2AJsonRpcMessage
  -> A2A_PROTOCOL_JsonRpcStreaming
  -> SERVER_RemoteA2AFoundryAgent
  -> CLIENT_RenderStreamedResult

WHAT IS REALLY CONNECTED

- Client side: this DevUI workflow uses the A2A SDK client.
- A2A protocol: Agent Card discovery plus JSON-RPC streaming over HTTP.
- Server side: the notebook server running at {protocol_response.base_url}.
- Foundry side: the server invokes the Azure AI Foundry agent named A2A-MCP-Agent.
- MCP side: the Foundry agent can call the Microsoft Learn MCP server.

{protocol_response.wire_summary}

USER PROMPT
{protocol_response.user_prompt}

STREAMED RESPONSE FROM A2A SERVER
{protocol_response.response_text}
"""
        await ctx.yield_output(output)


async def build_workflow():
    user_prompt = CLIENT_UserPrompt(id="CLIENT_UserPrompt")
    discovery = A2A_DISCOVERY_GetAgentCard(id="A2A_DISCOVERY_GetAgentCard")
    build_message = CLIENT_BuildA2AJsonRpcMessage(id="CLIENT_BuildA2AJsonRpcMessage")
    protocol = A2A_PROTOCOL_JsonRpcStreaming(id="A2A_PROTOCOL_JsonRpcStreaming")
    remote_server = SERVER_RemoteA2AFoundryAgent(id="SERVER_RemoteA2AFoundryAgent_localhost_8080")
    render = CLIENT_RenderStreamedResult(id="CLIENT_RenderStreamedResult")

    workflow = (
        WorkflowBuilder(
            name="A2A Client Server Wiring Demo",
            description=(
                "Shows both sides of the A2A demo in DevUI. "
                "The workflow acts as the A2A client, discovers the notebook A2A server, "
                "sends a JSON-RPC streaming request, and renders the streamed response. "
                f"Make sure a2a_server.ipynb is running at {A2A_SERVER_URL}."
            ),
        )
        .set_start_executor(user_prompt)
        .add_edge(user_prompt, discovery)
        .add_edge(discovery, build_message)
        .add_edge(build_message, protocol)
        .add_edge(protocol, remote_server)
        .add_edge(remote_server, render)
        .build()
    )

    print("A2A client/server wiring graph:\n", WorkflowViz(workflow).to_mermaid())
    return workflow


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print("Starting A2A Client/Server DevUI at http://localhost:8093")
    print(f"Expected running A2A server: {A2A_SERVER_URL}")
    print(f"Agent Card URL: {A2A_AGENT_CARD_URL}")
    workflow = asyncio.run(build_workflow())
    serve(entities=[workflow], port=8093, auto_open=True, tracing_enabled=True)


if __name__ == "__main__":
    main()
