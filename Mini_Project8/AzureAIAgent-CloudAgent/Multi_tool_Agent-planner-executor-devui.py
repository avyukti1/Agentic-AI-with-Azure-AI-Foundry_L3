"""Validated planner and execution-engine workflow exposed through DevUI.

Visible routing:
    InputValidationRouter
        |-- OutOfScopeHandler
        |-- InsufficientInformationHandler
        `-- QuotaSafeRouter --> MagenticPlannerExecutionEngine

Run:
    python Multi_tool_Agent-planner-executor-devui.py
"""

import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from agent_framework import (
    Case,
    Default,
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowViz,
    handler,
)
from agent_framework.devui import serve


DEVUI_PORT = 8090
DEVUI_TRACING_ENABLED = os.getenv("DEVUI_TRACING_ENABLED", "false").lower() == "true"

PRODUCT_CATALOG = {
    "basic": {
        "monthly_price": 120.0,
        "included_hours": 5,
        "sla": "next business day",
    },
    "standard": {
        "monthly_price": 300.0,
        "included_hours": 15,
        "sla": "8 hours",
    },
    "premium": {
        "monthly_price": 650.0,
        "included_hours": 40,
        "sla": "2 hours",
    },
}

CUSTOMERS = {
    "CUST-100": {
        "name": "Contoso Retail",
        "employees": 220,
        "discount_percent": 10,
    },
    "CUST-200": {
        "name": "Fabrikam Health",
        "employees": 850,
        "discount_percent": 15,
    },
}

@dataclass
class ValidationResult:
    """Request classification passed through the visible switch wiring."""

    request: str
    route: str
    reason: str
    missing_details: list[str]


@dataclass
class ExecutionResult:
    """Structured output from computation before final UI formatting."""

    request: str
    operation: str
    customer_id: str | None
    data: dict[str, Any]


def get_product_catalog() -> dict[str, dict[str, Any]]:
    """Return all cloud support plans, prices, included hours, and SLAs."""
    logging.info("Tool call: get_product_catalog()")
    return PRODUCT_CATALOG


def get_customer_profile(customer_id: str) -> dict[str, Any]:
    """Return the customer profile and negotiated discount for a customer ID."""
    logging.info("Tool call: get_customer_profile(customer_id=%r)", customer_id)
    return CUSTOMERS.get(customer_id, {"error": f"Unknown customer ID: {customer_id}"})


def calculate_annual_quote(
    plan_name: str,
    discount_percent: float = 0,
) -> dict[str, Any]:
    """Calculate annual list price, discount amount, and final support-plan price."""
    logging.info(
        "Tool call: calculate_annual_quote(plan_name=%r, discount_percent=%r)",
        plan_name,
        discount_percent,
    )

    plan = PRODUCT_CATALOG.get(plan_name.lower())
    if not plan:
        return {"error": f"Unknown plan: {plan_name}"}

    list_price = plan["monthly_price"] * 12
    discount_amount = list_price * discount_percent / 100
    return {
        "plan": plan_name.lower(),
        "annual_list_price": round(list_price, 2),
        "discount_percent": discount_percent,
        "discount_amount": round(discount_amount, 2),
        "annual_final_price": round(list_price - discount_amount, 2),
        "sla": plan["sla"],
        "included_hours_per_month": plan["included_hours"],
    }


def compare_plan_quotes(
    first_plan: str,
    second_plan: str,
    discount_percent: float = 0,
) -> dict[str, Any]:
    """Compare annual prices and service levels for two support plans."""
    logging.info(
        "Tool call: compare_plan_quotes(first_plan=%r, second_plan=%r, discount_percent=%r)",
        first_plan,
        second_plan,
        discount_percent,
    )

    first = calculate_annual_quote(first_plan, discount_percent)
    second = calculate_annual_quote(second_plan, discount_percent)
    if "error" in first or "error" in second:
        return {"first": first, "second": second}

    return {
        "first": first,
        "second": second,
        "annual_price_difference": round(
            second["annual_final_price"] - first["annual_final_price"],
            2,
        ),
    }


def _find_customer_id(request: str) -> str | None:
    match = re.search(r"\bCUST-\d+\b", request, flags=re.IGNORECASE)
    return match.group(0).upper() if match else None


def _find_plans(request: str) -> list[str]:
    normalized = request.casefold()
    return [plan for plan in PRODUCT_CATALOG if re.search(rf"\b{plan}\b", normalized)]


def validate_request(request: str) -> ValidationResult:
    """Classify scope and detect missing details before execution."""
    normalized = request.casefold().strip()
    customer_id = _find_customer_id(request)
    plans = _find_plans(request)
    scope_terms = (
        "support plan", "support-plan", "catalog", "customer profile", "cust-",
        "quote", "pricing", "price", "discount", "sla", "included hours",
        "compare", "recommend", "proposal", "basic", "standard", "premium",
    )
    if not any(term in normalized for term in scope_terms):
        return ValidationResult(
            request, "out_of_scope",
            "This workflow only handles support-plan catalogs, customers, quotes, comparisons, and recommendations.",
            [],
        )

    missing = []
    asks_catalog = "catalog" in normalized or "all available support plans" in normalized
    asks_profile = "profile" in normalized
    asks_compare = "compare" in normalized or "difference" in normalized
    asks_recommend = any(term in normalized for term in ("recommend", "proposal", "executive", "best plan"))
    asks_quote = any(term in normalized for term in ("quote", "annual", "cost", "price"))

    if customer_id and customer_id not in CUSTOMERS:
        missing.append(f"a supported customer ID; `{customer_id}` is unknown")
    if (asks_profile or asks_compare or asks_recommend or asks_quote) and not customer_id:
        missing.append("a customer ID (`CUST-100` or `CUST-200`)")
    if asks_compare and len(plans) < 2:
        missing.append("two plans to compare (`Basic`, `Standard`, or `Premium`)")
    if asks_quote and not asks_compare and not asks_recommend and not plans:
        missing.append("a plan name (`Basic`, `Standard`, or `Premium`)")
    if not any((asks_catalog, asks_profile, asks_compare, asks_recommend, asks_quote)):
        missing.append("an action: show catalog, show profile, calculate quote, compare, or recommend")

    if missing:
        return ValidationResult(
            request, "insufficient",
            "The question is relevant, but more valid information is required.",
            missing,
        )
    return ValidationResult(request, "valid", "The request is complete and ready to execute.", [])


def _catalog_response() -> str:
    rows = [
        f"| {name.title()} | ${plan['monthly_price']:,.2f} | {plan['included_hours']} | {plan['sla']} |"
        for name, plan in PRODUCT_CATALOG.items()
    ]
    return "\n".join([
        "## Available Support Plans", "",
        "| Plan | Monthly price | Included hours/month | SLA |",
        "|---|---:|---:|---|", *rows,
    ])


def _execute_valid_request(request: str) -> ExecutionResult:
    """Plan and compute a complete request using verified deterministic tools."""
    normalized = request.casefold()
    customer_id = _find_customer_id(request)
    plans = _find_plans(request)

    if "catalog" in normalized or "all available support plans" in normalized:
        return ExecutionResult(request, "catalog", None, {"catalog": get_product_catalog()})
    if customer_id and "profile" in normalized:
        profile = get_customer_profile(customer_id)
        return ExecutionResult(request, "profile", customer_id, {"profile": profile})

    profile = get_customer_profile(customer_id)
    discount = profile["discount_percent"]
    if len(plans) >= 2:
        comparison = compare_plan_quotes(plans[0], plans[1], discount)
        if any(term in normalized for term in ("recommend", "proposal", "executive", "best plan")):
            recommended = plans[1] if profile["employees"] >= 500 else plans[0]
            return ExecutionResult(
                request,
                "recommendation",
                customer_id,
                {
                    "profile": profile,
                    "comparison": comparison,
                    "plans": plans,
                    "recommended": recommended,
                },
            )
        return ExecutionResult(
            request,
            "comparison",
            customer_id,
            {"profile": profile, "comparison": comparison, "plans": plans},
        )

    if plans:
        quote = calculate_annual_quote(plans[0], discount)
        return ExecutionResult(
            request,
            "quote",
            customer_id,
            {"profile": profile, "quote": quote},
        )

    recommended = "premium" if profile["employees"] >= 500 else "standard"
    quote = calculate_annual_quote(recommended, discount)
    return ExecutionResult(
        request,
        "recommendation",
        customer_id,
        {"profile": profile, "quote": quote, "recommended": recommended},
    )


class InputValidationRouter(Executor):
    """Route every question through visible validation before execution."""

    @handler
    async def handle(self, request: str, ctx: WorkflowContext[ValidationResult]) -> None:
        result = validate_request(request)
        logging.info("Validation route: %s", result.route)
        await ctx.send_message(result)


class OutOfScopeHandler(Executor):
    """Explain supported scope for unrelated or wrong questions."""

    @handler
    async def handle(self, result: ValidationResult, ctx: WorkflowContext[str]) -> None:
        await ctx.yield_output(
            "## Please Enter a Relevant Question\n\n"
            f"{result.reason}\n\n"
            "Examples:\n"
            "- `Show all available support plans.`\n"
            "- `Calculate the Premium quote for CUST-200.`\n"
            "- `Compare Standard and Premium for CUST-100.`"
        )


class InsufficientInformationHandler(Executor):
    """Tell the user exactly which details are missing."""

    @handler
    async def handle(self, result: ValidationResult, ctx: WorkflowContext[str]) -> None:
        missing = "\n".join(f"- {detail}" for detail in result.missing_details)
        await ctx.yield_output(
            "## More Details Required\n\n"
            f"{result.reason}\n\nPlease provide:\n{missing}\n\n"
            "Example: `Compare Standard and Premium plans for CUST-100.`"
        )


class QuotaSafeRouter(Executor):
    """Compute supported requests locally before using any model-backed planning."""

    @handler
    async def handle(
        self,
        result: ValidationResult,
        ctx: WorkflowContext[ExecutionResult],
    ) -> None:
        logging.info("Quota-safe router computing valid request")
        await ctx.send_message(_execute_valid_request(result.request))


class MagenticPlannerExecutionEngine(Executor):
    """Render the final planner/execution-engine result in a separate visible block."""

    @handler
    async def handle(
        self,
        result: ExecutionResult,
        ctx: WorkflowContext[str],
    ) -> None:
        logging.info("Magentic planner execution engine rendering operation: %s", result.operation)
        data = result.data

        if result.operation == "catalog":
            output = _catalog_response()
        elif result.operation == "profile":
            profile = data["profile"]
            output = (
                f"## Customer Profile: {result.customer_id}\n\n"
                f"- **Name:** {profile['name']}\n"
                f"- **Employees:** {profile['employees']}\n"
                f"- **Negotiated discount:** {profile['discount_percent']}%"
            )
        elif result.operation == "quote":
            profile, quote = data["profile"], data["quote"]
            output = (
                f"## {quote['plan'].title()} Quote for {profile['name']} ({result.customer_id})\n\n"
                f"- **Final annual price:** ${quote['annual_final_price']:,.2f}\n"
                f"- **Discount:** {quote['discount_percent']}% (${quote['discount_amount']:,.2f})\n"
                f"- **SLA:** {quote['sla']}\n"
                f"- **Included hours:** {quote['included_hours_per_month']} per month"
            )
        elif result.operation == "comparison":
            profile = data["profile"]
            comparison = data["comparison"]
            plans = data["plans"]
            first, second = comparison["first"], comparison["second"]
            output = (
                f"## Comparison for {profile['name']} ({result.customer_id})\n\n"
                f"- **{plans[0].title()}:** ${first['annual_final_price']:,.2f}/year, "
                f"{first['sla']} SLA, {first['included_hours_per_month']} hours/month.\n"
                f"- **{plans[1].title()}:** ${second['annual_final_price']:,.2f}/year, "
                f"{second['sla']} SLA, {second['included_hours_per_month']} hours/month.\n"
                f"- **Annual difference:** ${abs(comparison['annual_price_difference']):,.2f}."
            )
        elif "comparison" in data:
            profile = data["profile"]
            comparison = data["comparison"]
            plans = data["plans"]
            recommended = data["recommended"]
            selected = (
                comparison["first"]
                if comparison["first"]["plan"] == recommended
                else comparison["second"]
            )
            output = (
                f"## Recommendation for {profile['name']} ({result.customer_id})\n\n"
                f"- **Recommend {recommended.title()}** for this {profile['employees']}-employee customer.\n"
                f"- **Annual price:** ${selected['annual_final_price']:,.2f} after the "
                f"{profile['discount_percent']}% discount.\n"
                f"- **Service:** {selected['sla']} SLA with "
                f"{selected['included_hours_per_month']} included hours/month.\n"
                f"- **Price difference:** ${abs(comparison['annual_price_difference']):,.2f} annually."
            )
        else:
            profile, quote = data["profile"], data["quote"]
            output = (
                f"## Recommendation for {profile['name']} ({result.customer_id})\n\n"
                f"- **Recommend {data['recommended'].title()}** based on customer scale.\n"
                f"- **Final annual price:** ${quote['annual_final_price']:,.2f}\n"
                f"- **Service:** {quote['sla']} SLA and "
                f"{quote['included_hours_per_month']} hours/month."
            )

        await ctx.yield_output(output)


def build_workflow():
    """Build visible validation and execution wiring."""
    validation = InputValidationRouter(id="InputValidationRouter")
    out_of_scope = OutOfScopeHandler(id="OutOfScopeHandler")
    insufficient = InsufficientInformationHandler(id="InsufficientInformationHandler")
    quota_safe_router = QuotaSafeRouter(id="QuotaSafeRouter")
    planner_engine = MagenticPlannerExecutionEngine(id="MagenticPlannerExecutionEngine")

    workflow = (
        WorkflowBuilder(
            name="Validated Quota-Safe Support Plan Planner",
            description=(
                "Validates scope and required details, answers simple support-plan "
                "requests locally, and delegates complex requests to Magentic."
            ),
        )
        .set_start_executor(validation)
        .add_switch_case_edge_group(
            validation,
            [
                Case(lambda result: result.route == "out_of_scope", out_of_scope),
                Case(lambda result: result.route == "insufficient", insufficient),
                Default(quota_safe_router),
            ],
        )
        .add_edge(quota_safe_router, planner_engine)
        .build()
    )
    logging.info("Mermaid Diagram:\n%s", WorkflowViz(workflow).to_mermaid())
    return workflow


def main() -> None:
    """Build and host the validated planner/executor workflow in DevUI."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("agent_framework._workflows._workflow_builder").setLevel(
        logging.ERROR
    )
    logging.info("Starting Validated Planner + Execution Engine Workflow")
    logging.info("Available at: http://localhost:%s", DEVUI_PORT)
    logging.info("OTLP tracing enabled: %s", DEVUI_TRACING_ENABLED)
    logging.info("Try out-of-scope: help me book a flight")
    logging.info("Try insufficient: calculate an annual support-plan quote")
    logging.info("Try valid: Compare Standard and Premium plans for CUST-100.")

    workflow = build_workflow()
    serve(
        entities=[workflow],
        port=DEVUI_PORT,
        auto_open=True,
        tracing_enabled=DEVUI_TRACING_ENABLED,
    )


if __name__ == "__main__":
    main()

##Recommended Inputs

# Validated these paths:

#(1) help me book a flight - Routes to OutOfScopeHandler.

#(2) calculate an annual support-plan quote - Requests customer ID and plan name.

#(3)Compare Standard and Premium plans for CUST-100.

# Show all available support plans.
# Show the customer profile for CUST-100.
# Calculate the discounted annual Premium quote for CUST-200.
# Compare Standard and Premium plans for CUST-100.
# Recommend the best plan for CUST-200 and explain your reasoning.
# What is the annual price difference between Basic and Standard for CUST-100?
# Which plan has the fastest SLA, and what would it cost CUST-200 annually?
# Compare every plan for CUST-100 using its negotiated discount.
# Prepare a three-bullet executive proposal recommending a plan for CUST-200.
# Create a comparison table showing annual price, SLA, and included hours for CUST-100.
