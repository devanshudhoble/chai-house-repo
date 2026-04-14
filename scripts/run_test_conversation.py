import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import Base, SessionLocal, engine
from app.seed import seed_menu
from app.services.conversation import ConversationService


TEST_MESSAGES = [
    "Hi",
    "2 masala chai, 4 samosa, 2 plain maggi, 2 nimbu pani, 3 vegetable maggi",
    "Rahul",
    "9876543210",
    "AB",
    "402",
    "YES",
]


async def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_menu(db)
        service = ConversationService(db)
        wa_id = f"9198{uuid.uuid4().hex[:8]}"
        print(f"Using test wa_id: {wa_id}")
        print("-" * 60)

        for message in TEST_MESSAGES:
            result = await service.process_inbound_text(wa_id, message)
            print(f"IN : {message}")
            print(f"OUT: {result['reply']}")
            print("-" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
