from functools import lru_cache
import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Chaihouse WhatsApp Ordering POC"
    adk_app_name: str = "chaihouse_whatsapp_ordering_poc"
    environment: str = "development"
    secret_key: str = "change-me"
    base_url: str = "http://127.0.0.1:8000"

    database_url: str = "sqlite:///./chaihouse.db"
    adk_session_database_url: str = "sqlite+aiosqlite:///./chaihouse.db"

    business_name: str = "Chaihouse Cafe"
    property_name: str = "Green Heritage"
    min_order_value: int = 500
    allowed_blocks: list[str] = Field(
        default_factory=lambda: ["AA", "AB", "AC", "BA", "BB", "BC", "CA", "CB"]
    )

    whatsapp_access_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_verify_token: str = "chaihouse-verify-token"
    whatsapp_api_base_url: str = "https://graph.facebook.com"
    whatsapp_api_version: str = "v23.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("allowed_blocks", mode="before")
    @classmethod
    def parse_allowed_blocks(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [item.strip().upper() for item in stripped.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
