"""Planner, executor, and validator collaboration workflow displayed in DevUI."""

import asyncio
import logging
import os
from dataclasses import dataclass
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


@dataclass
class PlanPackage:
    request: str
    plan: str


@dataclass
class SolutionPackage:
    request: str
    plan: str
    solution: str
    attempt: int
    feedback: str = ""


@dataclass
class ValidationPackage:
    request: str
    plan: str
    solution: str
    review: str
    approved: bool
    attempt: int


async def create_agent(name: str, instructions: str):
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


class PlannerExecutor(Executor):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(self, request: str, ctx: WorkflowContext[PlanPackage]) -> None:
        response = await self.agent.run(
            f"Create a numbered, dependency-aware plan with risks and acceptance criteria.\n\n{request}"
        )
        await ctx.send_message(PlanPackage(request=request, plan=str(response)))


class SolutionExecutor(Executor):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(self, package: PlanPackage, ctx: WorkflowContext[SolutionPackage]) -> None:
        prompt = f"""Implement this request according to the plan.

Request:
{package.request}

Plan:
{package.plan}

Return a complete standalone solution with commands and verification steps."""
        response = await self.agent.run(prompt)
        await ctx.send_message(
            SolutionPackage(
                request=package.request,
                plan=package.plan,
                solution=str(response),
                attempt=1,
            )
        )


class ValidatorExecutor(Executor):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(self, package: SolutionPackage, ctx: WorkflowContext[ValidationPackage]) -> None:
        prompt = f"""Validate the proposed solution for correctness, completeness, security,
command consistency, and acceptance criteria. End with exactly DECISION: APPROVED
or DECISION: REVISE, followed by actionable feedback.

Request:
{package.request}

Plan:
{package.plan}

Proposed solution:
{package.solution}"""
        response = str(await self.agent.run(prompt))
        await ctx.send_message(
            ValidationPackage(
                request=package.request,
                plan=package.plan,
                solution=package.solution,
                review=response,
                approved="DECISION: APPROVED" in response.upper(),
                attempt=package.attempt,
            )
        )


class RevisionExecutor(Executor):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(self, package: ValidationPackage, ctx: WorkflowContext[SolutionPackage]) -> None:
        prompt = f"""Revise the solution using the validator feedback. Return a complete
standalone replacement solution.

Request:
{package.request}

Plan:
{package.plan}

Previous solution:
{package.solution}

Validator feedback:
{package.review}"""
        response = await self.agent.run(prompt)
        await ctx.send_message(
            SolutionPackage(
                request=package.request,
                plan=package.plan,
                solution=str(response),
                attempt=2,
                feedback=package.review,
            )
        )


class PublisherExecutor(Executor):
    @handler
    async def handle(self, package: ValidationPackage, ctx: WorkflowContext[str]) -> None:
        status = "APPROVED" if package.approved else "REVIEW REQUIRED AFTER FINAL ATTEMPT"
        output = f"""COLLABORATION RESULT: {status}

EXECUTION ATTEMPT: {package.attempt}

FINAL SOLUTION
{package.solution}

VALIDATOR REVIEW
{package.review}"""
        await ctx.yield_output(output)


def is_approved(package: ValidationPackage) -> bool:
    return package.approved


def needs_revision(package: ValidationPackage) -> bool:
    return not package.approved


async def build_workflow():
    planner_agent = await create_agent(
        "DevUI-Planner-Agent",
        "You are a solution planner. Plan work without implementing it.",
    )
    executor_agent = await create_agent(
        "DevUI-Executor-Agent",
        "You are a senior Azure engineer. Implement supplied plans with secure, practical commands.",
    )
    validator_agent = await create_agent(
        "DevUI-Validator-Agent",
        "You are a strict technical validator. Approve only correct, complete, secure solutions.",
    )

    planner = PlannerExecutor(planner_agent, id="PlannerAgent")
    executor = SolutionExecutor(executor_agent, id="ExecutorAgent")
    validator = ValidatorExecutor(validator_agent, id="ValidatorAgent")
    revision = RevisionExecutor(executor_agent, id="ExecutorRevision")
    final_validator = ValidatorExecutor(validator_agent, id="FinalValidator")
    publisher = PublisherExecutor(id="PublishResult")

    workflow = (
        WorkflowBuilder(
            name="Planner Executor Validator Collaboration",
            description="A visible review workflow with one conditional revision opportunity.",
        )
        .set_start_executor(planner)
        .add_edge(planner, executor)
        .add_edge(executor, validator)
        .add_edge(validator, publisher, condition=is_approved)
        .add_edge(validator, revision, condition=needs_revision)
        .add_edge(revision, final_validator)
        .add_edge(final_validator, publisher)
        .build()
    )

    print("Semantic coordination graph:\n", WorkflowViz(workflow).to_mermaid())
    return workflow


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print("Starting Planner-Executor-Validator DevUI at http://localhost:8092")
    workflow = asyncio.run(build_workflow())
    serve(entities=[workflow], port=8092, auto_open=True, tracing_enabled=True)


if __name__ == "__main__":
    main()
