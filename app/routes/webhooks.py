from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.services.conversation import ConversationService


router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])
settings = get_settings()


@router.get("")
def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    change_values = []
    for entry in payload.get("entry", []):
        change_values.extend(change.get("value", {}) for change in entry.get("changes", []))

    service = ConversationService(db)
    processed = []

    for value in change_values:
        for message in value.get("messages", []):
            if message.get("type") != "text":
                continue

            wa_id = message.get("from")
            body = message.get("text", {}).get("body", "").strip()
            if not wa_id or not body:
                continue

            result = await service.process_inbound_text(
                wa_id=wa_id,
                text=body,
                whatsapp_message_id=message.get("id"),
            )
            processed.append(result)

    return {"status": "ok", "processed": processed}
