"""Expose the Multi_tool_Agent-APIs-Tools.ipynb logic through DevUI.

The agent routes requests to:
- Open-Meteo for current weather
- REST Countries for country facts
- Microsoft Learn MCP for official Microsoft documentation

Run:
    python Multi_tool_Agent-APIs-Tools.-devui.py
"""

import logging
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx
from agent_framework import (
    ChatAgent,
    Executor,
    HostedMCPTool,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowViz,
    handler,
)
from agent_framework.azure import AzureAIClient
from agent_framework.devui import serve
from agent_framework_devui import register_cleanup
from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv


HTTP_TIMEOUT = 15.0
DEVUI_PORT = 8090
DEVUI_TRACING_ENABLED = os.getenv("DEVUI_TRACING_ENABLED", "false").lower() == "true"

# Keep Azure resources alive for DevUI and close them on DevUI's event loop.
DEVUI_RESOURCES: list[tuple[AzureAIClient, AzureCliCredential]] = []

CITY_COUNTRY = {
    "bengaluru": "India",
    "bangalore": "India",
    "london": "United Kingdom",
    "paris": "France",
    "seattle": "United States",
    "tokyo": "Japan",
}

COUNTRY_ALIASES = {
    "france": "France",
    "india": "India",
    "japan": "Japan",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "united states": "United States",
    "usa": "United States",
}


@dataclass
class RoutedRequest:
    """Request enriched with deterministic routing decisions."""

    original: str
    city: str | None
    country: str | None
    needs_weather: bool
    needs_country: bool
    needs_microsoft_learn: bool


@dataclass
class BranchResult:
    """One visible workflow branch result."""

    branch: str
    status: str
    content: Any


async def get_current_weather(city: str) -> dict[str, Any]:
    """Get the current weather for a city, including temperature, wind speed, and weather code."""
    logging.info("Tool call: get_current_weather(city=%r)", city)

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            geo_response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "en", "format": "json"},
            )
            geo_response.raise_for_status()
            locations = geo_response.json().get("results", [])
            if not locations:
                return {"error": f"No location found for {city}"}

            location = locations[0]
            weather_response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "current": (
                        "temperature_2m,apparent_temperature,"
                        "weather_code,wind_speed_10m"
                    ),
                    "timezone": "auto",
                },
            )
            weather_response.raise_for_status()
            payload = weather_response.json()
            return {
                "location": f"{location['name']}, {location.get('country', '')}",
                "timezone": payload.get("timezone"),
                "current": payload.get("current", {}),
                "units": payload.get("current_units", {}),
            }
    except httpx.HTTPError as exc:
        logging.exception("Weather API request failed")
        return {"error": f"Weather API request failed: {exc}"}


async def get_country_facts(country_name: str) -> dict[str, Any]:
    """Get official country facts such as capital, region, population, currencies, and languages."""
    logging.info("Tool call: get_country_facts(country_name=%r)", country_name)

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(
                f"https://restcountries.com/v3.1/name/{country_name}",
                params={"fullText": "true"},
            )
            if response.status_code == 404:
                return {"error": f"No country found for {country_name}"}

            response.raise_for_status()
            country = response.json()[0]
            return {
                "official_name": country.get("name", {}).get("official"),
                "capital": country.get("capital", []),
                "region": country.get("region"),
                "population": country.get("population"),
                "currencies": country.get("currencies", {}),
                "languages": country.get("languages", {}),
            }
    except httpx.HTTPError as exc:
        logging.exception("Country API request failed")
        return {"error": f"Country API request failed: {exc}"}


def _extract_city(request: str) -> str | None:
    normalized = request.casefold()
    for city in CITY_COUNTRY:
        if re.search(rf"\b{re.escape(city)}\b", normalized):
            return city.title()
    return None


def _extract_country(request: str, city: str | None) -> str | None:
    normalized = request.casefold()
    for alias, country in COUNTRY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", normalized):
            return country
    return CITY_COUNTRY.get(city.casefold()) if city else None


class RequestRouter(Executor):
    """Inspect the request and decide which detailed workflow branches are relevant."""

    @handler
    async def handle(self, request: str, ctx: WorkflowContext[RoutedRequest]) -> None:
        normalized = request.casefold()
        city = _extract_city(request)
        country = _extract_country(request, city)
        routed = RoutedRequest(
            original=request,
            city=city,
            country=country,
            needs_weather=any(term in normalized for term in ("weather", "temperature", "wind")),
            needs_country=any(
                term in normalized
                for term in (
                    "country",
                    "facts",
                    "capital",
                    "currency",
                    "population",
                    "languages",
                    "region",
                )
            ),
            needs_microsoft_learn=any(
                term in normalized
                for term in (
                    "microsoft learn",
                    "microsoft documentation",
                    "official microsoft",
                    "azure",
                    "defaultazurecredential",
                )
            ),
        )
        logging.info("Request router decision: %s", routed)
        await ctx.send_message(routed)


class WeatherExecutor(Executor):
    """Call Open-Meteo when the router identifies a weather request."""

    @handler
    async def handle(
        self,
        request: RoutedRequest,
        ctx: WorkflowContext[BranchResult],
    ) -> None:
        if not request.needs_weather:
            await ctx.send_message(BranchResult("Weather Executor", "skipped", "Weather not requested."))
            return
        if not request.city:
            await ctx.send_message(
                BranchResult("Weather Executor", "error", "Specify a supported city for weather.")
            )
            return
        result = await get_current_weather(request.city)
        await ctx.send_message(BranchResult("Weather Executor", "completed", result))


class CountryFactsExecutor(Executor):
    """Call REST Countries when the router identifies a country-facts request."""

    @handler
    async def handle(
        self,
        request: RoutedRequest,
        ctx: WorkflowContext[BranchResult],
    ) -> None:
        if not request.needs_country:
            await ctx.send_message(
                BranchResult("Country Facts Executor", "skipped", "Country facts not requested.")
            )
            return
        if not request.country:
            await ctx.send_message(
                BranchResult("Country Facts Executor", "error", "Specify a supported country.")
            )
            return
        result = await get_country_facts(request.country)
        await ctx.send_message(BranchResult("Country Facts Executor", "completed", result))


class MicrosoftLearnExecutor(Executor):
    """Invoke the Microsoft Learn MCP-backed agent for documentation requests."""

    def __init__(self, agent: ChatAgent, **kwargs: Any):
        super().__init__(**kwargs)
        self.agent = agent

    @handler
    async def handle(
        self,
        request: RoutedRequest,
        ctx: WorkflowContext[BranchResult],
    ) -> None:
        if not request.needs_microsoft_learn:
            await ctx.send_message(
                BranchResult("Microsoft Learn Agent", "skipped", "Microsoft documentation not requested.")
            )
            return
        response = await self.agent.run(request.original)
        await ctx.send_message(BranchResult("Microsoft Learn Agent", "completed", response.text))


class ResponseAggregator(Executor):
    """Combine the visible branch results into the final DevUI response."""

    @handler
    async def handle(
        self,
        results: list[BranchResult],
        ctx: WorkflowContext[str],
    ) -> None:
        lines = ["# Detailed Tool Workflow Result", ""]
        for result in results:
            lines.extend(
                [
                    f"## {result.branch}",
                    f"**Status:** {result.status}",
                    "",
                    str(result.content),
                    "",
                ]
            )
        await ctx.yield_output("\n".join(lines))


def create_microsoft_learn_agent(project_endpoint: str, model: str) -> ChatAgent:
    """Create the Microsoft Learn specialist used by its visible workflow branch."""
    credential = AzureCliCredential()

    # Lazy client construction ensures its HTTP session opens on DevUI's event loop.
    agent_client = AzureAIClient(
        project_endpoint=project_endpoint,
        model_deployment_name=model,
        credential=credential,
    )

    microsoft_learn = HostedMCPTool(
        name="Microsoft Learn",
        description="Search official Microsoft Learn documentation.",
        url="https://learn.microsoft.com/api/mcp",
        approval_mode="never_require",
    )

    agent = agent_client.create_agent(
        name="Microsoft-Learn-Agent",
        description="Answers questions using official Microsoft Learn documentation.",
        instructions=(
            "Use the Microsoft Learn tool for every answer. Return a concise answer "
            "grounded in official Microsoft documentation."
        ),
        tools=[microsoft_learn],
    )

    DEVUI_RESOURCES.append((agent_client, credential))
    logging.info("Created Microsoft-Learn-Agent")
    return agent


async def close_devui_resources() -> None:
    """Close Azure clients and credentials during DevUI shutdown."""
    for agent_client, credential in DEVUI_RESOURCES:
        await agent_client.close()
        await credential.close()
    DEVUI_RESOURCES.clear()


def build_workflow():
    """Build the visible router, tool branches, and response aggregator workflow."""
    load_dotenv()
    project_endpoint = os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
    model = os.getenv("AI_FOUNDRY_DEPLOYMENT_NAME")

    missing = [
        name
        for name, value in {
            "AI_FOUNDRY_PROJECT_ENDPOINT": project_endpoint,
            "AI_FOUNDRY_DEPLOYMENT_NAME": model,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required .env values: {', '.join(missing)}")

    logging.info("Project endpoint: %s", project_endpoint)
    logging.info("Model deployment: %s", model)
    microsoft_learn_agent = create_microsoft_learn_agent(project_endpoint, model)

    router = RequestRouter(id="RequestRouter")
    weather = WeatherExecutor(id="WeatherExecutor")
    country = CountryFactsExecutor(id="CountryFactsExecutor")
    microsoft = MicrosoftLearnExecutor(
        microsoft_learn_agent,
        id="MicrosoftLearnAgent",
    )
    aggregator = ResponseAggregator(id="ResponseAggregator")

    workflow = (
        WorkflowBuilder(
            name="External APIs and Tools Detailed Workflow",
            description=(
                "Routes requests through visible weather, country-facts, and "
                "Microsoft Learn execution branches."
            ),
        )
        .set_start_executor(router)
        .add_fan_out_edges(router, [weather, country, microsoft])
        .add_fan_in_edges([weather, country, microsoft], aggregator)
        .build()
    )
    logging.info("Mermaid Diagram:\n%s", WorkflowViz(workflow).to_mermaid())
    return workflow


def main() -> None:
    """Create the detailed external-tools workflow and host it in DevUI."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("agent_framework._workflows._workflow_builder").setLevel(logging.ERROR)
    logging.info("Starting External APIs + Tools Detailed Workflow")
    logging.info("Available at: http://localhost:%s", DEVUI_PORT)
    logging.info("OTLP tracing enabled: %s", DEVUI_TRACING_ENABLED)
    logging.info("Try: What is the current weather in Seattle?")
    logging.info(
        "Try: Give me Tokyo weather plus Japan's capital, currency, population, and languages."
    )
    logging.info(
        "Try: Using Microsoft Learn, explain Azure CLI authentication for Python apps."
    )
    logging.info(
        "Try: Compare the current weather in London with key facts about the United Kingdom."
    )

    workflow = build_workflow()
    register_cleanup(workflow, close_devui_resources)
    serve(
        entities=[workflow],
        port=DEVUI_PORT,
        auto_open=True,
        tracing_enabled=DEVUI_TRACING_ENABLED,
    )


if __name__ == "__main__":
    main()



# Sample Inputs 
# What is the current weather in Bengaluru?
# Show the temperature, wind speed, and apparent temperature in Seattle.
# What is the weather in London right now?
# Country Facts Inputs

# Give me key facts about India.
# What are Japan's capital, currency, population, and languages?
# Show the official name and region of the United Kingdom.
# Mixed API Inputs

# Give me Tokyo's current weather and key facts about Japan.
# Compare the current weather in London with facts about the United Kingdom.
# I am visiting Paris. Show its weather and provide important facts about France.
# Microsoft Learn Inputs

# Using Microsoft Learn, explain Azure CLI authentication for Python.
# How do I create an Azure Storage account using Azure CLI?
# Using official Microsoft documentation, explain DefaultAzureCredential.
# Find Microsoft Learn guidance for deploying an Azure AI Foundry agent
