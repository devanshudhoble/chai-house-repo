from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models import Address, Cart, CartItem, Conversation, Customer, MenuItem, Message, Order


settings = get_settings()


class Repository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_customer(self, wa_id: str) -> Customer:
        customer = self.db.scalar(select(Customer).where(Customer.wa_id == wa_id))
        if customer:
            return customer

        customer = Customer(wa_id=wa_id)
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def get_active_conversation(self, customer_id: int) -> Conversation | None:
        return self.db.scalar(
            select(Conversation)
            .where(Conversation.customer_id == customer_id, Conversation.status == "active")
            .options(selectinload(Conversation.customer))
            .order_by(desc(Conversation.created_at))
            .limit(1)
        )

    def create_conversation(self, customer: Customer) -> Conversation:
        conversation = Conversation(
            customer_id=customer.id,
            channel="whatsapp",
            status="active",
            current_step="new_chat",
            session_id=f"conv_{uuid.uuid4().hex}",
            state_json=json.dumps({}),
            last_message_at=datetime.utcnow(),
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_or_create_conversation(self, customer: Customer) -> Conversation:
        conversation = self.get_active_conversation(customer.id)
        if conversation:
            return conversation
        return self.create_conversation(customer)

    def save_message(
        self,
        conversation_id: int,
        direction: str,
        text: str,
        message_type: str = "text",
        whatsapp_message_id: str | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            direction=direction,
            message_text=text,
            message_type=message_type,
            whatsapp_message_id=whatsapp_message_id,
        )
        self.db.add(message)
        conversation = self.db.get(Conversation, conversation_id)
        if conversation:
            conversation.last_message_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(message)
        return message

    def update_conversation_state(self, conversation: Conversation, step: str, state: dict) -> Conversation:
        conversation.current_step = step
        conversation.state_json = json.dumps(state)
        conversation.last_message_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def load_state(self, conversation: Conversation) -> dict:
        try:
            return json.loads(conversation.state_json or "{}")
        except json.JSONDecodeError:
            return {}

    def get_or_create_active_cart(self, customer_id: int, conversation_id: int) -> Cart:
        cart = self.db.scalar(
            select(Cart)
            .where(
                Cart.customer_id == customer_id,
                Cart.conversation_id == conversation_id,
                Cart.status == "active",
            )
            .options(selectinload(Cart.items))
            .limit(1)
        )
        if cart:
            return cart

        cart = Cart(customer_id=customer_id, conversation_id=conversation_id)
        self.db.add(cart)
        self.db.commit()
        self.db.refresh(cart)
        return cart

    def get_menu_items(self) -> list[MenuItem]:
        return list(
            self.db.scalars(
                select(MenuItem).where(MenuItem.is_available.is_(True)).order_by(MenuItem.display_order)
            )
        )

    def find_menu_item_by_query(self, query: str) -> MenuItem | None:
        normalized = query.strip().lower()
        for item in self.get_menu_items():
            aliases = [a.strip().lower() for a in item.aliases.split(",") if a.strip()]
            names = [item.name.lower(), *aliases]
            if normalized in names:
                return item
            if len(normalized) >= 4 and any(normalized in name for name in names):
                return item
        return None

    def add_item_to_cart(self, cart: Cart, menu_item: MenuItem, qty: int) -> Cart:
        existing = self.db.scalar(
            select(CartItem).where(CartItem.cart_id == cart.id, CartItem.menu_item_id == menu_item.id).limit(1)
        )
        if existing:
            existing.qty += qty
            existing.line_total = existing.qty * existing.unit_price
        else:
            self.db.add(
                CartItem(
                    cart_id=cart.id,
                    menu_item_id=menu_item.id,
                    item_name=menu_item.name,
                    qty=qty,
                    unit_price=menu_item.price,
                    line_total=menu_item.price * qty,
                )
            )

        self.db.flush()
        self.recalculate_cart(cart.id)
        self.db.commit()
        return self.db.get(Cart, cart.id)

    def recalculate_cart(self, cart_id: int) -> None:
        cart = self.db.get(Cart, cart_id)
        if not cart:
            return

        items = list(self.db.scalars(select(CartItem).where(CartItem.cart_id == cart_id)))
        subtotal = sum(item.line_total for item in items)
        cart.subtotal = subtotal
        cart.min_order_valid = subtotal >= settings.min_order_value

    def get_cart(self, cart_id: int) -> Cart | None:
        return self.db.scalar(
            select(Cart)
            .where(Cart.id == cart_id)
            .options(selectinload(Cart.items))
            .limit(1)
        )

    def save_customer_name(self, customer: Customer, name: str) -> None:
        customer.name = name.strip()
        self.db.commit()

    def save_customer_phone(self, customer: Customer, phone: str) -> None:
        customer.phone_number = phone.strip()
        self.db.commit()

    def save_default_address(self, customer: Customer, block_code: str, flat_no: str) -> Address:
        for address in customer.addresses:
            address.is_default = False

        address = Address(
            customer_id=customer.id,
            property_name=settings.property_name,
            block_code=block_code,
            flat_no=flat_no,
            is_default=True,
        )
        self.db.add(address)
        self.db.flush()
        customer.default_address_id = address.id
        self.db.commit()
        self.db.refresh(address)
        return address

    def get_default_address(self, customer: Customer) -> Address | None:
        if customer.default_address_id:
            return self.db.get(Address, customer.default_address_id)
        return None

    def create_order(self, customer: Customer, conversation: Conversation, cart: Cart, address: Address) -> Order:
        cart.status = "checked_out"
        order = Order(
            customer_id=customer.id,
            conversation_id=conversation.id,
            cart_id=cart.id,
            address_id=address.id,
            subtotal=cart.subtotal,
            status="confirmed",
            source="whatsapp",
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def list_orders(self) -> list[Order]:
        return list(
            self.db.scalars(
                select(Order)
                .options(
                    selectinload(Order.customer),
                    selectinload(Order.address),
                    selectinload(Order.cart).selectinload(Cart.items),
                )
                .order_by(desc(Order.created_at))
            )
        )

    def get_order(self, order_id: int) -> Order | None:
        return self.db.scalar(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.customer),
                selectinload(Order.address),
                selectinload(Order.cart).selectinload(Cart.items),
            )
            .limit(1)
        )
