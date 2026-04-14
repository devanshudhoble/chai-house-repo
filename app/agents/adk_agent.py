from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import ClassVar

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.events.event_actions import EventActions
from google.genai import types
from typing_extensions import override

from app.agents.order_agent import AgentResult, ChaihouseOrderFlow
from app.models import Conversation, Customer
from app.services.repository import Repository


class ChaihouseWorkflowAgent(BaseAgent):
    """Base ADK workflow agent with shared customer, conversation, and state helpers."""

    repo: Repository

    def load_runtime_context(
        self,
        ctx: InvocationContext,
    ) -> tuple[Customer, Conversation, str]:
        session_state = ctx.session.state
        customer_id = int(session_state["customer_id"])
        conversation_id = int(session_state["conversation_id"])

        customer = self.repo.get_customer(customer_id)
        conversation = self.repo.get_conversation(conversation_id)
        if not customer or not conversation:
            raise ValueError("ADK session is missing the customer or conversation context.")

        user_text = ""
        for event in reversed(ctx.session.events):
            if event.author != "user" or not event.content or not event.content.parts:
                continue
            part = event.content.parts[0]
            user_text = (part.text or "").strip()
            if user_text:
                break

        return customer, conversation, user_text

    def build_state_delta(self, customer: Customer, step: str, state: dict) -> dict:
        state_delta: dict[str, object] = {
            "step": step,
            "active_agent": self.name,
            "customer_id": customer.id,
        }
        state_delta.update(state)

        if customer.name:
            state_delta["user:name"] = customer.name
        if customer.phone_number:
            state_delta["user:phone_number"] = customer.phone_number

        address = self.repo.get_default_address(customer)
        if address:
            state_delta["user:default_block"] = address.block_code
            state_delta["user:default_flat_no"] = address.flat_no

        return state_delta

    def emit_result(
        self,
        ctx: InvocationContext,
        customer: Customer,
        result: AgentResult,
    ) -> Event:
        return Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=result.text)],
            ),
            actions=EventActions(
                state_delta=self.build_state_delta(customer, result.next_step, result.state)
            ),
        )


class GreetingMenuAgent(ChaihouseWorkflowAgent):
    """Handles the initial welcome and first menu response."""

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        customer, conversation, user_text = self.load_runtime_context(ctx)
        flow = ChaihouseOrderFlow(self.repo)
        result = flow.handle_message(customer, conversation, user_text)
        yield self.emit_result(ctx, customer, result)


class CartRoutingAgent(ChaihouseWorkflowAgent):
    """Handles cart building, saved profile reuse, and minimum-order checks."""

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        customer, conversation, user_text = self.load_runtime_context(ctx)
        flow = ChaihouseOrderFlow(self.repo)
        result = flow.handle_message(customer, conversation, user_text)
        yield self.emit_result(ctx, customer, result)


class CustomerDetailsAgent(ChaihouseWorkflowAgent):
    """Collects and validates customer name, phone, block, and flat details."""

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        customer, conversation, user_text = self.load_runtime_context(ctx)
        flow = ChaihouseOrderFlow(self.repo)
        result = flow.handle_message(customer, conversation, user_text)
        yield self.emit_result(ctx, customer, result)


class OrderConfirmationAgent(ChaihouseWorkflowAgent):
    """Handles final order confirmation and completed-order replies."""

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        customer, conversation, user_text = self.load_runtime_context(ctx)
        flow = ChaihouseOrderFlow(self.repo)
        result = flow.handle_message(customer, conversation, user_text)
        yield self.emit_result(ctx, customer, result)


class ChaihouseMainAgent(ChaihouseWorkflowAgent):
    """Root ADK agent that routes each turn to the workflow sub-agent for the active step."""

    STEP_TO_AGENT: ClassVar[dict[str, str]] = {
        "new_chat": "greeting_menu_agent",
        "collecting_items": "cart_routing_agent",
        "saved_profile_confirmation": "cart_routing_agent",
        "collecting_name": "customer_details_agent",
        "collecting_phone": "customer_details_agent",
        "collecting_block": "customer_details_agent",
        "collecting_flat": "customer_details_agent",
        "confirming_order": "order_confirmation_agent",
        "completed": "order_confirmation_agent",
    }

    @override
    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ) -> AsyncGenerator[Event, None]:
        _, conversation, _ = self.load_runtime_context(ctx)
        agent_name = self.STEP_TO_AGENT.get(conversation.current_step, "cart_routing_agent")
        routed_agent = self.find_sub_agent(agent_name)
        if not routed_agent:
            raise ValueError(f"Sub-agent `{agent_name}` is not registered in the Chaihouse ADK agent tree.")

        async for event in routed_agent.run_async(ctx):
            yield event


# =========================================================
# SUB-AGENTS
# =========================================================
def create_greeting_menu_agent(repo: Repository) -> GreetingMenuAgent:
    """Create the ADK sub-agent that welcomes the customer and sends the menu."""

    return GreetingMenuAgent(
        name="greeting_menu_agent",
        description="Welcomes the customer and sends the menu.",
        repo=repo,
    )


def create_cart_routing_agent(repo: Repository) -> CartRoutingAgent:
    """Create the ADK sub-agent that manages cart building and minimum-order checks."""

    return CartRoutingAgent(
        name="cart_routing_agent",
        description="Builds the cart, enforces the minimum order rule, and handles saved profile reuse.",
        repo=repo,
    )


def create_customer_details_agent(repo: Repository) -> CustomerDetailsAgent:
    """Create the ADK sub-agent that collects and validates delivery details."""

    return CustomerDetailsAgent(
        name="customer_details_agent",
        description="Collects and validates customer contact and delivery details.",
        repo=repo,
    )


def create_order_confirmation_agent(repo: Repository) -> OrderConfirmationAgent:
    """Create the ADK sub-agent that confirms the order and handles completed-state replies."""

    return OrderConfirmationAgent(
        name="order_confirmation_agent",
        description="Confirms the order and handles post-confirmation replies.",
        repo=repo,
    )


# =========================================================
# MAIN AGENT
# =========================================================
def build_chaihouse_agent(repo: Repository) -> ChaihouseMainAgent:
    """Build the main Chaihouse ADK agent with routed workflow sub-agents."""

    greeting_menu_agent = create_greeting_menu_agent(repo)
    cart_routing_agent = create_cart_routing_agent(repo)
    customer_details_agent = create_customer_details_agent(repo)
    order_confirmation_agent = create_order_confirmation_agent(repo)

    return ChaihouseMainAgent(
        name="chaihouse_main_agent",
        description="Routes Chaihouse WhatsApp order turns to the correct workflow sub-agent.",
        repo=repo,
        sub_agents=[
            greeting_menu_agent,
            cart_routing_agent,
            customer_details_agent,
            order_confirmation_agent,
        ],
    )
