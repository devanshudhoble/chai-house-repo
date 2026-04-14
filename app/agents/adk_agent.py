from __future__ import annotations

from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.events.event_actions import EventActions
from google.genai import types
from typing_extensions import override

from app.agents.order_agent import ChaihouseOrderFlow
from app.models import Conversation, Customer
from app.services.repository import Repository


class ChaihouseAdkAgent(BaseAgent):
    """Real ADK custom agent for the Chaihouse ordering flow."""

    repo: Repository

    @override
    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ) -> AsyncGenerator[Event, None]:
        customer, conversation, user_text = self._load_runtime_context(ctx)
        flow = ChaihouseOrderFlow(self.repo)
        result = flow.handle_message(customer, conversation, user_text)

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=result.text)],
            ),
            actions=EventActions(
                state_delta=self._build_state_delta(customer, result.next_step, result.state)
            ),
        )

    def _load_runtime_context(
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

    def _build_state_delta(self, customer: Customer, step: str, state: dict) -> dict:
        state_delta: dict[str, object] = {
            "step": step,
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
