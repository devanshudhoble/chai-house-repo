from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.models import Conversation, Customer
from app.services.repository import Repository
from app.agents.tools import BusinessTools


settings = get_settings()


@dataclass
class AgentResult:
    text: str
    next_step: str
    state: dict


class ChaihouseOrderingAgent:
    """ADK-ready ordering orchestrator.

    The POC decision flow runs locally so the system works immediately.
    Swap this logic with a real ADK runner later without changing the rest of
    the webhook, persistence, or dashboard layers.
    """

    def __init__(self, repo: Repository):
        self.repo = repo
        self.tools = BusinessTools(repo)

    def handle_message(self, customer: Customer, conversation: Conversation, text: str) -> AgentResult:
        state = self.repo.load_state(conversation)
        step = conversation.current_step

        if step == "new_chat":
            return AgentResult(
                text=(
                    f"Hi, welcome to {settings.business_name}.\n\n"
                    f"{self.tools.build_menu_message()}"
                ),
                next_step="collecting_items",
                state=state,
            )

        if step == "collecting_items":
            return self._handle_collecting_items(customer, conversation, text, state)

        if step == "saved_profile_confirmation":
            if text.strip().lower() in {"yes", "y", "use saved address"}:
                address = self.repo.get_default_address(customer)
                cart = self.repo.get_or_create_active_cart(customer.id, conversation.id)
                order = self.repo.create_order(customer, conversation, cart, address)
                return AgentResult(
                    text=(
                        f"Order confirmed.\nOrder ID: CH{order.id:04d}\n"
                        f"Delivery: {settings.property_name}, Block {address.block_code}, Flat {address.flat_no}\n"
                        f"Total: Rs {int(order.subtotal)}\n\n"
                        "Our team will prepare it shortly."
                    ),
                    next_step="completed",
                    state=state,
                )
            return AgentResult(
                text="Please share your name.",
                next_step="collecting_name",
                state=state,
            )

        if step == "collecting_name":
            self.repo.save_customer_name(customer, text.strip())
            return AgentResult(
                text="Please share your 10-digit phone number.",
                next_step="collecting_phone",
                state=state,
            )

        if step == "collecting_phone":
            if not self.tools.validate_phone(text):
                return AgentResult(
                    text="Please send a valid 10-digit phone number.",
                    next_step=step,
                    state=state,
                )
            self.repo.save_customer_phone(customer, self.tools.normalize_phone(text))
            return AgentResult(
                text=(
                    f"Please share your {settings.property_name} block code.\n"
                    f"Allowed blocks: {', '.join(settings.allowed_blocks)}"
                ),
                next_step="collecting_block",
                state=state,
            )

        if step == "collecting_block":
            if not self.tools.validate_block(text):
                return AgentResult(
                    text=(
                        f"That block is not serviceable. Please share a valid {settings.property_name} block code.\n"
                        f"Allowed blocks: {', '.join(settings.allowed_blocks)}"
                    ),
                    next_step=step,
                    state=state,
                )
            state["block_code"] = self.tools.normalize_block(text)
            return AgentResult(
                text="Please share your flat number.",
                next_step="collecting_flat",
                state=state,
            )

        if step == "collecting_flat":
            block_code = state.get("block_code")
            if not block_code:
                return AgentResult(
                    text="Please share your block code first.",
                    next_step="collecting_block",
                    state=state,
                )

            address = self.repo.save_default_address(customer, block_code, text.strip())
            cart = self.repo.get_or_create_active_cart(customer.id, conversation.id)
            summary = self.tools.cart_summary(cart)
            return AgentResult(
                text=(
                    f"{summary}\n\n"
                    f"Delivery details:\n"
                    f"- Name: {customer.name}\n"
                    f"- Phone: {customer.phone_number}\n"
                    f"- Address: {settings.property_name}, Block {address.block_code}, Flat {address.flat_no}\n\n"
                    "Reply YES to confirm or NO to change your order."
                ),
                next_step="confirming_order",
                state={},
            )

        if step == "confirming_order":
            if text.strip().lower() not in {"yes", "y"}:
                return AgentResult(
                    text="Okay. Please send the changes you want in your cart.",
                    next_step="collecting_items",
                    state={},
                )
            address = self.repo.get_default_address(customer)
            cart = self.repo.get_or_create_active_cart(customer.id, conversation.id)
            order = self.repo.create_order(customer, conversation, cart, address)
            return AgentResult(
                text=(
                    f"Order confirmed.\nOrder ID: CH{order.id:04d}\n"
                    f"Total: Rs {int(order.subtotal)}\n"
                    "Our team will prepare it shortly."
                ),
                next_step="completed",
                state={},
            )

        if step == "completed":
            return AgentResult(
                text="Your latest order is already confirmed. Send a new message to start another order.",
                next_step="completed",
                state=state,
            )

        return AgentResult(
            text="I could not understand that. Please send your order items.",
            next_step="collecting_items",
            state=state,
        )

    def _handle_collecting_items(
        self,
        customer: Customer,
        conversation: Conversation,
        text: str,
        state: dict,
    ) -> AgentResult:
        cart = self.repo.get_or_create_active_cart(customer.id, conversation.id)
        matches, unknown = self.tools.parse_order_text(text)

        if not matches:
            cart = self.repo.get_cart(cart.id)
            reply = "I could not match any menu items from that message. Please send items like: 2 masala chai, 2 samosa, 1 plain maggi"
            if unknown:
                reply += f"\nNot matched: {', '.join(unknown)}"
            if cart and cart.subtotal < settings.min_order_value and cart.subtotal > 0:
                needed = settings.min_order_value - int(cart.subtotal)
                reply += f"\nYour cart is still below the minimum order value. Please add items worth Rs {needed} or more."
            return AgentResult(text=reply, next_step="collecting_items", state=state)

        for menu_item, qty in matches:
            self.repo.add_item_to_cart(cart, menu_item, qty)

        cart = self.repo.get_cart(cart.id)
        summary = self.tools.cart_summary(cart)

        if cart.subtotal < settings.min_order_value:
            needed = settings.min_order_value - int(cart.subtotal)
            return AgentResult(
                text=(
                    f"{summary}\n\n"
                    f"Minimum online order value is Rs {settings.min_order_value}. "
                    f"Please add items worth Rs {needed} or more."
                ),
                next_step="collecting_items",
                state=state,
            )

        if self.tools.customer_has_saved_profile(customer):
            address = self.repo.get_default_address(customer)
            return AgentResult(
                text=(
                    f"{summary}\n\n"
                    f"I found your saved delivery details:\n"
                    f"- Name: {customer.name}\n"
                    f"- Phone: {customer.phone_number}\n"
                    f"- Address: {settings.property_name}, Block {address.block_code}, Flat {address.flat_no}\n\n"
                    "Reply YES to use the saved details, or UPDATE to enter new details."
                ),
                next_step="saved_profile_confirmation",
                state=state,
            )

        return AgentResult(
            text=f"{summary}\n\nPlease share your name.",
            next_step="collecting_name",
            state=state,
        )
