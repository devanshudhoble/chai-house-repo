from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.order_agent import ChaihouseOrderingAgent
from app.services.repository import Repository
from app.services.whatsapp import WhatsAppService


class ConversationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = Repository(db)
        self.agent = ChaihouseOrderingAgent(self.repo)
        self.whatsapp = WhatsAppService()

    async def process_inbound_text(
        self,
        wa_id: str,
        text: str,
        whatsapp_message_id: str | None = None,
    ) -> dict:
        customer = self.repo.get_or_create_customer(wa_id)
        conversation = self.repo.get_or_create_conversation(customer)
        self.repo.save_message(conversation.id, "inbound", text, whatsapp_message_id=whatsapp_message_id)

        agent_result = self.agent.handle_message(customer, conversation, text)
        self.repo.update_conversation_state(conversation, agent_result.next_step, agent_result.state)
        self.repo.save_message(conversation.id, "outbound", agent_result.text)

        send_result = await self.whatsapp.send_text_message(wa_id, agent_result.text)
        return {
            "customer_id": customer.id,
            "conversation_id": conversation.id,
            "reply": agent_result.text,
            "delivery": send_result,
        }
