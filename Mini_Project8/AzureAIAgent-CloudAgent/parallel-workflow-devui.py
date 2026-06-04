"""Vacation Planning Workflow Sample for DevUI.

This sample demonstrates a multi-agent workflow for vacation planning using the Microsoft Agent Framework.
Agents include: Location Picker, Destination Recommender, Weather, Cuisine Suggestion, and Itinerary Planner.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
    WorkflowViz,
)
from agent_framework import ChatAgent
from agent_framework.azure import AzureAIClient
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import AzureCliCredential
from agent_framework.devui import serve

# Configuration is kept outside the source code in .env. This avoids hard-coding
# deployment-specific values and lets the workflow run in other environments.
load_dotenv()
project_endpoint = os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
model = os.getenv("AI_FOUNDRY_DEPLOYMENT_NAME")

print("Project Endpoint: ", project_endpoint)
print("Model: ", model)

async def create_agent(agent_name: str, agent_instructions: str) -> ChatAgent:
    """Create one conversation-scoped Foundry chat agent.

    Each specialist receives its own conversation so its messages and context
    remain independent from the other parallel branches.
    """
    # AzureCliCredential uses the identity established by `az login`.
    credential = AzureCliCredential()
    # AIProjectClient is the entry point to resources in the Foundry project.
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=credential
    )
    # A conversation stores the messages exchanged by this specific agent.
    openai_client = project_client.get_openai_client()
    conversation = await openai_client.conversations.create()
    conversation_id = conversation.id
    print("Conversation ID: ", conversation_id)

    # AzureAIClient binds the project, model deployment, and conversation.
    chat_client = AzureAIClient(
        project_client=project_client,
        conversation_id=conversation_id,
        model_deployment_name=model
    )

    try:
        agent = chat_client.create_agent(
            name=agent_name,
            instructions=agent_instructions,
        )
        print(f"{agent_name} Agent created successfully!")
        return agent
    finally:
        # Close network-backed clients after the agent definition is created.
        await chat_client.close()
        await credential.close()

# Executors are workflow nodes. A handler receives the upstream node's message,
# invokes its specialist agent, and publishes the result through the context.
class LocationSelectorExecutor(Executor):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(self, user_query: str, ctx: WorkflowContext[str]) -> None:
        response = await self.agent.run(user_query)
        # send_message forwards this location result to every fan-out branch.
        await ctx.send_message(str(response))

class DestinationRecommenderExecutor(Executor):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(self, location: str, ctx: WorkflowContext[str]) -> None:
        response = await self.agent.run(location)
        await ctx.send_message(str(response))

class WeatherExecutor(Executor):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(self, location: str, ctx: WorkflowContext[str]) -> None:
        response = await self.agent.run(location)
        await ctx.send_message(str(response))

class CuisineSuggestionExecutor(Executor):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(self, location: str, ctx: WorkflowContext[str]) -> None:
        response = await self.agent.run(location)
        await ctx.send_message(str(response))

class ItineraryPlannerExecutor(Executor):
    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(self, results: list[str], ctx: WorkflowContext[str]) -> None:
        # Fan-in supplies a list containing all three parallel branch results.
        response = await self.agent.run(results)
        # yield_output marks this value as the workflow's final result.
        await ctx.yield_output(str(response))

async def build_workflow():
    """Create the specialist agents and connect them as a parallel workflow."""
    # Agent instructions establish a focused role for each workflow stage.
    location_picker_agent = await create_agent(
        agent_name="Location-Picker-Agent",
        agent_instructions="You are a helpful assistant that helps users pick a location for their vacation."
    )
    destination_recommender_agent = await create_agent(
        agent_name="Destination-Recommender-Agent",
        agent_instructions="You are a travel expert that provides personalized vacation recommendations based on user preferences and locations."
    )
    weather_agent = await create_agent(
        agent_name="Weather-Agent",
        agent_instructions="You are a weather expert that provides accurate and up-to-date weather information for various locations selected"
    )
    cuisine_suggestion_agent = await create_agent(
        agent_name="Cuisine-Suggestion-Agent",
        agent_instructions="You are a culinary expert that suggests popular local cuisines and dining options based on the selected vacation destinations."
    )
    itinerary_planner_agent = await create_agent(
        agent_name="Itinerary-Planner-Agent",
        agent_instructions="You are an itinerary planning expert that creates detailed travel itineraries based on user preferences, selected destinations, weather conditions, and local cuisine options."
    )

    # Executor IDs make nodes identifiable in traces and visualizations.
    location_selector_executor = LocationSelectorExecutor(location_picker_agent, id="LocationSelector")
    destination_recommender_executor = DestinationRecommenderExecutor(destination_recommender_agent, id="DestinationRecommender")
    weather_executor = WeatherExecutor(weather_agent, id="Weather")
    cuisine_suggestion_executor = CuisineSuggestionExecutor(cuisine_suggestion_agent, id="CuisineSuggestion")
    itinerary_planner_executor = ItineraryPlannerExecutor(itinerary_planner_agent, id="ItineraryPlanner")

    # State lets workflow infrastructure inspect or persist the objects
    # associated with an executor.
    for executor in [
        location_selector_executor,
        destination_recommender_executor,
        weather_executor,
        cuisine_suggestion_executor,
        itinerary_planner_executor,
    ]:
        executor.state = {
            "location_picker_agent": location_picker_agent,
            "destination_recommender_agent": destination_recommender_agent,
            "weather_agent": weather_agent,
            "cuisine_suggestion_agent": cuisine_suggestion_agent,
            "itinerary_planner_agent": itinerary_planner_agent,
        }

    # Data flow:
    # user -> location selector -> three concurrent specialists -> itinerary.
    workflow = (
        WorkflowBuilder(
            name="Vacation Planner Workflow",
            description="Multi-agent workflow for vacation planning with recommendations and itinerary."
        )
        .set_start_executor(location_selector_executor)
        # Fan-out starts independent branches from the same location message.
        .add_fan_out_edges(location_selector_executor, [
            destination_recommender_executor,
            weather_executor,
            cuisine_suggestion_executor
        ])
        # Fan-in waits for every branch before planning the itinerary.
        .add_fan_in_edges([
            destination_recommender_executor,
            weather_executor,
            cuisine_suggestion_executor
        ], itinerary_planner_executor)
        .build()
    )

    # Mermaid text makes the workflow graph easy to inspect or document.
    viz = WorkflowViz(workflow)
    mermaid_content = viz.to_mermaid()
    print("Mermaid Diagram:\n", mermaid_content)

    return workflow

def main():
    """Launch the vacation planning workflow in DevUI."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)
    logger.info("Starting Vacation Planning Workflow")
    logger.info("Available at: http://localhost:8090")
    logger.info("Entity ID: workflow_vacation_planner")

    # asyncio.run bridges this synchronous entry point to async setup.
    workflow = asyncio.run(build_workflow())
    # DevUI provides an interactive browser client. Tracing records each node
    # and agent call so the execution can be inspected.
    serve(entities=[workflow], port=8090, auto_open=True, tracing_enabled=True)

if __name__ == "__main__":
    # This guard runs main only when the file is executed directly.
    main()
