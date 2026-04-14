from __future__ import annotations

import re

from app.config import get_settings
from app.models import Cart, Customer
from app.services.repository import Repository


settings = get_settings()


class BusinessTools:
    def __init__(self, repo: Repository):
        self.repo = repo

    def build_menu_message(self) -> str:
        grouped: dict[str, list[str]] = {}
        for item in self.repo.get_menu_items():
            grouped.setdefault(item.category, []).append(f"- {item.name}: Rs {int(item.price)}")

        lines = [f"Welcome to {settings.business_name}. Here is today's menu:"]
        for category, entries in grouped.items():
            lines.append(f"\n{category}")
            lines.extend(entries)
        lines.append("\nNote: Parcel charges are extra.")
        lines.append("Reply with your order. Example: 2 masala chai, 2 samosa, 1 plain maggi")
        return "\n".join(lines)

    def parse_order_text(self, text: str) -> tuple[list[tuple[object, int]], list[str]]:
        cleaned = text.lower().replace("&", ",").replace(" and ", ",")
        chunks = [chunk.strip() for chunk in cleaned.split(",") if chunk.strip()]
        matched: list[tuple[object, int]] = []
        unknown: list[str] = []

        for chunk in chunks:
            qty_match = re.match(r"^(?P<qty>\d+)\s+(?P<name>.+)$", chunk)
            qty = int(qty_match.group("qty")) if qty_match else 1
            query = qty_match.group("name") if qty_match else chunk
            menu_item = self.repo.find_menu_item_by_query(query)
            if menu_item:
                matched.append((menu_item, qty))
            else:
                unknown.append(chunk)

        return matched, unknown

    def validate_phone(self, phone: str) -> bool:
        digits = re.sub(r"\D", "", phone)
        return len(digits) == 10

    def normalize_phone(self, phone: str) -> str:
        return re.sub(r"\D", "", phone)

    def validate_block(self, block_code: str) -> bool:
        return block_code.strip().upper() in settings.allowed_blocks

    def normalize_block(self, block_code: str) -> str:
        return block_code.strip().upper()

    def cart_summary(self, cart: Cart) -> str:
        cart = self.repo.get_cart(cart.id) or cart
        lines = ["Your current cart:"]
        for item in cart.items:
            lines.append(f"- {item.qty} x {item.item_name} = Rs {int(item.line_total)}")
        lines.append(f"Subtotal: Rs {int(cart.subtotal)}")
        return "\n".join(lines)

    def customer_has_saved_profile(self, customer: Customer) -> bool:
        address = self.repo.get_default_address(customer)
        return bool(customer.name and customer.phone_number and address)
