from __future__ import annotations

import logging

import httpx

from app.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


class WhatsAppService:
    def __init__(self) -> None:
        self.base_endpoint = (
            f"{settings.whatsapp_api_base_url.rstrip('/')}/"
            f"{settings.whatsapp_api_version}/{settings.whatsapp_phone_number_id}/messages"
            if settings.whatsapp_phone_number_id
            else None
        )

    async def send_text_message(self, wa_id: str, text: str) -> dict:
        if not settings.whatsapp_access_token or not self.base_endpoint:
            logger.info("WhatsApp stub send to %s: %s", wa_id, text)
            return {"status": "stubbed", "to": wa_id, "text": text}

        payload = {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": "text",
            "text": {"body": text},
        }
        headers = {
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(self.base_endpoint, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
