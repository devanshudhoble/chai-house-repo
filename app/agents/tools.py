from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Any

from app.db import SessionLocal
from app.config import get_settings
from app.models import Cart, Customer
from app.services.repository import Repository


settings = get_settings()


@contextmanager
def repository_context():
    db = SessionLocal()
    try:
        yield Repository(db)
    finally:
        db.close()


class BusinessTools:
    def __init__(self, repo: Repository):
        self.repo = repo

    def get_menu_payload(self, flags: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return the current menu as a structured payload.

        Args:
            flags: Optional behavior flags.
                - include_examples: bool, default True
                - include_parcel_note: bool, default True

        Returns:
            A dictionary with grouped menu lines, optional notes, and guidance text.
        """
        flags = flags or {}
        grouped: dict[str, list[str]] = {}
        for item in self.repo.get_menu_items():
            grouped.setdefault(item.category, []).append(f"- {item.name}: Rs {int(item.price)}")

        lines = [f"Welcome to {settings.business_name}. Here is today's menu:"]
        for category, entries in grouped.items():
            lines.append(f"\n{category}")
            lines.extend(entries)

        if flags.get("include_parcel_note", True):
            lines.append("\nNote: Parcel charges are extra.")
        if flags.get("include_examples", True):
            lines.append("Reply with your order. Example: 2 masala chai, 2 samosa, 1 plain maggi")

        return {
            "ok": True,
            "menu_lines": lines,
            "categories": grouped,
        }

    def build_menu_message(self, flags: dict[str, Any] | None = None) -> str:
        payload = self.get_menu_payload(flags=flags)
        return "\n".join(payload["menu_lines"])

    def parse_order_payload(self, text: str, flags: dict[str, Any] | None = None) -> dict[str, Any]:
        """Parse a free-text order into matched items and unknown fragments.

        Args:
            text: Raw customer order text such as "2 masala chai, 1 samosa".
            flags: Optional parsing flags.
                - split_and: bool, default True
                - allow_default_qty: bool, default True

        Returns:
            A dictionary containing matched menu items, quantities, and unknown text fragments.
        """
        flags = flags or {}
        cleaned = text.lower().replace("&", ",").replace(" and ", ",")
        chunks = [chunk.strip() for chunk in cleaned.split(",") if chunk.strip()]
        matched: list[tuple[object, int]] = []
        unknown: list[str] = []

        for chunk in chunks:
            qty_match = re.match(r"^(?P<qty>\d+)\s+(?P<name>.+)$", chunk)
            qty = int(qty_match.group("qty")) if qty_match else (1 if flags.get("allow_default_qty", True) else 0)
            query = qty_match.group("name") if qty_match else chunk
            menu_item = self.repo.find_menu_item_by_query(query)
            if menu_item:
                matched.append((menu_item, qty))
            else:
                unknown.append(chunk)

        return {
            "ok": True,
            "matches": matched,
            "unknown": unknown,
            "parsed_chunks": chunks,
        }

    def parse_order_text(self, text: str) -> tuple[list[tuple[object, int]], list[str]]:
        payload = self.parse_order_payload(text)
        return payload["matches"], payload["unknown"]

    def validate_phone_payload(self, phone: str, flags: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validate and normalize a customer phone number.

        Args:
            phone: Raw phone value from the customer.
            flags: Optional validation flags.
                - required_length: int, default 10

        Returns:
            A dictionary with validation status and normalized digits.
        """
        flags = flags or {}
        digits = re.sub(r"\D", "", phone)
        required_length = int(flags.get("required_length", 10))
        return {
            "ok": len(digits) == required_length,
            "normalized_phone": digits,
            "required_length": required_length,
        }

    def validate_phone(self, phone: str) -> bool:
        return self.validate_phone_payload(phone)["ok"]

    def normalize_phone(self, phone: str) -> str:
        return self.validate_phone_payload(phone)["normalized_phone"]

    def validate_block_payload(
        self,
        block_code: str,
        flags: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate and normalize a Green Heritage delivery block code.

        Args:
            block_code: Raw block value from the customer.
            flags: Optional validation flags.
                - allowed_blocks: list[str], defaults to app settings

        Returns:
            A dictionary with validation status, normalized block, and the allowed list.
        """
        flags = flags or {}
        allowed_blocks = [block.strip().upper() for block in flags.get("allowed_blocks", settings.allowed_blocks)]
        normalized = block_code.strip().upper()
        return {
            "ok": normalized in allowed_blocks,
            "normalized_block": normalized,
            "allowed_blocks": allowed_blocks,
        }

    def validate_block(self, block_code: str) -> bool:
        return self.validate_block_payload(block_code)["ok"]

    def normalize_block(self, block_code: str) -> str:
        return self.validate_block_payload(block_code)["normalized_block"]

    def get_cart_summary_payload(
        self,
        cart: Cart,
        flags: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a structured cart summary for customer-facing or internal use.

        Args:
            cart: Active cart entity.
            flags: Optional summary flags.
                - include_header: bool, default True

        Returns:
            A dictionary with summary lines, subtotal, and item rows.
        """
        flags = flags or {}
        cart = self.repo.get_cart(cart.id) or cart
        lines = ["Your current cart:"] if flags.get("include_header", True) else []
        items: list[dict[str, Any]] = []
        for item in cart.items:
            items.append(
                {
                    "item_name": item.item_name,
                    "qty": item.qty,
                    "unit_price": int(item.unit_price),
                    "line_total": int(item.line_total),
                }
            )
            lines.append(f"- {item.qty} x {item.item_name} = Rs {int(item.line_total)}")
        lines.append(f"Subtotal: Rs {int(cart.subtotal)}")
        return {
            "ok": True,
            "lines": lines,
            "items": items,
            "subtotal": int(cart.subtotal),
        }

    def cart_summary(self, cart: Cart) -> str:
        return "\n".join(self.get_cart_summary_payload(cart)["lines"])

    def get_saved_profile_payload(
        self,
        customer: Customer,
        flags: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return whether the customer has a reusable saved profile and address.

        Args:
            customer: Customer entity.
            flags: Optional flags reserved for future profile policies.

        Returns:
            A dictionary with saved-profile availability and current default address fields.
        """
        flags = flags or {}
        address = self.repo.get_default_address(customer)
        return {
            "ok": True,
            "has_saved_profile": bool(customer.name and customer.phone_number and address),
            "name": customer.name,
            "phone_number": customer.phone_number,
            "block_code": address.block_code if address else None,
            "flat_no": address.flat_no if address else None,
            "flags": flags,
        }

    def customer_has_saved_profile(self, customer: Customer) -> bool:
        return self.get_saved_profile_payload(customer)["has_saved_profile"]


# =========================================================
# TOOL FUNCTIONS
# =========================================================
def get_menu_tool(args: dict | None = None, flags: dict | None = None) -> dict[str, Any]:
    """Return the current Chaihouse menu as a structured payload.

    Args:
        args: Optional arguments reserved for future filtering.
        flags: Optional output flags.
            - include_examples: bool, default True
            - include_parcel_note: bool, default True

    Returns:
        Structured menu data with grouped categories and rendered menu lines.
    """
    _ = args or {}
    flags = flags or {}
    with repository_context() as repo:
        return BusinessTools(repo).get_menu_payload(flags=flags)


def parse_order_tool(order_text: str, args: dict | None = None, flags: dict | None = None) -> dict[str, Any]:
    """Parse customer order text into known menu items and unknown fragments.

    Args:
        order_text: Raw order text from the customer.
        args: Optional parsing arguments reserved for future expansion.
        flags: Optional behavior flags.
            - allow_default_qty: bool, default True

    Returns:
        Structured parse result including matched items and unmatched fragments.
    """
    _ = args or {}
    flags = flags or {}
    with repository_context() as repo:
        return BusinessTools(repo).parse_order_payload(order_text, flags=flags)


def validate_phone_tool(phone_number: str, args: dict | None = None, flags: dict | None = None) -> dict[str, Any]:
    """Validate and normalize a customer phone number.

    Args:
        phone_number: Raw phone number from the customer.
        args: Optional validation arguments reserved for future policy use.
        flags: Optional validation flags.
            - required_length: int, default 10

    Returns:
        Validation result including normalized digits.
    """
    _ = args or {}
    flags = flags or {}
    with repository_context() as repo:
        return BusinessTools(repo).validate_phone_payload(phone_number, flags=flags)


def validate_block_tool(block_code: str, args: dict | None = None, flags: dict | None = None) -> dict[str, Any]:
    """Validate a Green Heritage block code against the configured serviceable blocks.

    Args:
        block_code: Raw block code from the customer.
        args: Optional validation arguments reserved for future rules.
        flags: Optional validation flags.
            - allowed_blocks: list[str], defaults to configured app blocks

    Returns:
        Validation result including normalized block code.
    """
    _ = args or {}
    flags = flags or {}
    with repository_context() as repo:
        return BusinessTools(repo).validate_block_payload(block_code, flags=flags)


def get_saved_profile_tool(customer_id: int, args: dict | None = None, flags: dict | None = None) -> dict[str, Any]:
    """Load a saved customer profile for address reuse decisions.

    Args:
        customer_id: Internal customer identifier.
        args: Optional arguments reserved for future profile scopes.
        flags: Optional flags reserved for future profile policies.

    Returns:
        Structured saved-profile data with customer contact and default address details.
    """
    _ = args or {}
    flags = flags or {}
    with repository_context() as repo:
        customer = repo.get_customer(customer_id)
        if not customer:
            return {"ok": False, "message": "Customer not found", "customer_id": customer_id}
        return BusinessTools(repo).get_saved_profile_payload(customer, flags=flags)
