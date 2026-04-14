from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from sqlalchemy.orm import Session

from app.agents.adk_agent import ChaihouseAdkAgent
from app.config import get_settings
from app.models import Conversation, Customer
from app.services.repository import Repository


settings = get_settings()


@lru_cache(maxsize=1)
def get_adk_session_service() -> DatabaseSessionService:
    return DatabaseSessionService(db_url=settings.adk_session_database_url)


class ChaihouseAdkRuntime:
    def __init__(self, db: Session):
        self.repo = Repository(db)
        self.session_service = get_adk_session_service()
        root_agent = ChaihouseAdkAgent(
            name="chaihouse_order_agent",
            description="Handles Chaihouse WhatsApp ordering conversations.",
            repo=self.repo,
        )
        root_agent._adk_origin_app_name = settings.adk_app_name
        root_agent._adk_origin_path = Path(__file__).resolve().parents[2]
        self.runner = Runner(
            app=App(
                name=settings.adk_app_name,
                root_agent=root_agent,
            ),
            session_service=self.session_service,
        )

    async def ensure_session(self, customer: Customer, conversation: Conversation) -> None:
        session = await self.session_service.get_session(
            app_name=settings.adk_app_name,
            user_id=customer.wa_id,
            session_id=conversation.session_id,
        )
        if session:
            return

        await self.session_service.create_session(
            app_name=settings.adk_app_name,
            user_id=customer.wa_id,
            session_id=conversation.session_id,
            state={
                "customer_id": customer.id,
                "conversation_id": conversation.id,
                "step": conversation.current_step,
                **self.repo.load_state(conversation),
            },
        )

    async def run_turn(self, customer: Customer, conversation: Conversation, text: str) -> dict:
        await self.ensure_session(customer, conversation)

        final_text = ""
        async for event in self.runner.run_async(
            user_id=customer.wa_id,
            session_id=conversation.session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part.from_text(text=text)],
            ),
        ):
            if not event.is_final_response() or event.author != "chaihouse_order_agent":
                continue
            if not event.content or not event.content.parts:
                continue
            final_text = (event.content.parts[0].text or "").strip()

        session = await self.session_service.get_session(
            app_name=settings.adk_app_name,
            user_id=customer.wa_id,
            session_id=conversation.session_id,
        )
        if not session:
            raise ValueError("ADK session was not available after the agent run.")

        return {
            "reply": final_text,
            "next_step": str(session.state.get("step", conversation.current_step)),
            "state": {
                key: value
                for key, value in session.state.items()
                if not key.startswith(("user:", "app:", "temp:"))
                and key not in {"step", "customer_id", "conversation_id"}
            },
        }
