"""Orchestrator and sub-agent workflow displayed in Microsoft Agent Framework DevUI."""

import asyncio
import logging
import os
from pathlib import Path

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, WorkflowViz, handler
from agent_framework.azure import AzureAIClient
from agent_framework.devui import serve
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv


ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(ENV_PATH)

PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
MODEL_DEPLOYMENT = os.getenv("MODEL_DEPLOYMENT_NAME")

if not PROJECT_ENDPOINT or not MODEL_DEPLOYMENT:
    raise RuntimeError(f"FOUNDRY_PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME are required in {ENV_PATH}")


async def create_agent(name: str, instructions: str):
    """Create a framework agent backed by the configured Microsoft Foundry project."""
    credential = AzureCliCredential()
    project_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
    conversation = await project_client.get_openai_client().conversations.create()
    chat_client = AzureAIClient(
        project_client=project_client,
        conversation_id=conversation.id,
        model_deployment_name=MODEL_DEPLOYMENT,
    )

    try:
        agent = chat_client.create_agent(name=name, instructions=instructions)
        print(f"Created {name} with conversation {conversation.id}")
        return agent
    finally:
        await chat_client.close()
        await credential.close()


class OrchestratorIntakeExecutor(Executor):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(self, user_request: str, ctx: WorkflowContext[str]) -> None:
        prompt = f"""Prepare a delegation brief for two specialist agents.

User request:
{user_request}

Preserve the original request and clarify what the requirements analyst and
implementation specialist must each contribute."""
        response = await self.agent.run(prompt)
        await ctx.send_message(f"ORCHESTRATOR DELEGATION BRIEF\n\n{response}")


class RequirementsAnalystExecutor(Executor):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(self, delegation_brief: str, ctx: WorkflowContext[str]) -> None:
        response = await self.agent.run(delegation_brief)
        await ctx.send_message(f"REQUIREMENTS ANALYST REPORT\n\n{response}")


class ImplementationSpecialistExecutor(Executor):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(self, delegation_brief: str, ctx: WorkflowContext[str]) -> None:
        response = await self.agent.run(delegation_brief)
        await ctx.send_message(f"IMPLEMENTATION SPECIALIST REPORT\n\n{response}")


class OrchestratorSynthesisExecutor(Executor):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(self, specialist_reports: list[str], ctx: WorkflowContext[str]) -> None:
        reports = "\n\n---\n\n".join(specialist_reports)
        prompt = f"""Synthesize these specialist reports into one implementation-ready answer.
Remove duplication, reconcile conflicts, and identify unresolved assumptions.

{reports}"""
        response = await self.agent.run(prompt)
        await ctx.yield_output(f"ORCHESTRATOR FINAL ANSWER\n\n{response}")


async def build_workflow():
    orchestrator = await create_agent(
        "DevUI-Orchestrator-Agent",
        "You coordinate specialist agents and synthesize their work into one accurate final answer.",
    )
    requirements_agent = await create_agent(
        "DevUI-Requirements-Agent",
        "You are a requirements analyst. Return goals, constraints, risks, assumptions, and acceptance criteria.",
    )
    implementation_agent = await create_agent(
        "DevUI-Implementation-Agent",
        "You are a senior Azure engineer. Return practical commands, security controls, and verification steps.",
    )

    intake = OrchestratorIntakeExecutor(orchestrator, id="OrchestratorIntake")
    requirements = RequirementsAnalystExecutor(requirements_agent, id="RequirementsSubAgent")
    implementation = ImplementationSpecialistExecutor(implementation_agent, id="ImplementationSubAgent")
    synthesis = OrchestratorSynthesisExecutor(orchestrator, id="OrchestratorSynthesis")

    workflow = (
        WorkflowBuilder(
            name="Orchestrator and Sub-Agents",
            description="An orchestrator delegates work in parallel and synthesizes the specialist reports.",
        )
        .set_start_executor(intake)
        .add_fan_out_edges(intake, [requirements, implementation])
        .add_fan_in_edges([requirements, implementation], synthesis)
        .build()
    )

    print("Semantic coordination graph:\n", WorkflowViz(workflow).to_mermaid())
    return workflow


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print("Starting Orchestrator and Sub-Agents DevUI at http://localhost:8091")
    workflow = asyncio.run(build_workflow())
    serve(entities=[workflow], port=8091, auto_open=True, tracing_enabled=True)


if __name__ == "__main__":
    main()
