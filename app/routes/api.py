from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.services.repository import Repository


router = APIRouter(prefix="/api", tags=["api"])
settings = get_settings()


@router.get("/menu")
def get_menu(db: Session = Depends(get_db)):
    repo = Repository(db)
    items = repo.get_menu_items()
    return {
        "business_name": settings.business_name,
        "property_name": settings.property_name,
        "min_order_value": settings.min_order_value,
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "price": item.price,
                "is_available": item.is_available,
            }
            for item in items
        ],
    }


@router.get("/settings")
def get_runtime_settings():
    return {
        "business_name": settings.business_name,
        "property_name": settings.property_name,
        "min_order_value": settings.min_order_value,
        "allowed_blocks": settings.allowed_blocks,
        "whatsapp_live_configured": bool(
            settings.whatsapp_access_token and settings.whatsapp_phone_number_id
        ),
    }
