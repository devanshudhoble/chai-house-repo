from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.routes.api import router as api_router
from app.routes.dashboard import router as dashboard_router
from app.routes.webhooks import router as webhook_router
from app.seed import seed_menu


logging.basicConfig(level=logging.INFO)
settings = get_settings()
app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_menu(db)
    finally:
        db.close()


app.include_router(webhook_router)
app.include_router(dashboard_router)
app.include_router(api_router)


@app.get("/health")
def healthcheck() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.environment,
            "whatsapp_live_configured": bool(
                settings.whatsapp_access_token and settings.whatsapp_phone_number_id
            ),
        }
    )
