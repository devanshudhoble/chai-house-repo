from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wa_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    default_address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.id"), nullable=True)

    addresses: Mapped[list["Address"]] = relationship(
        "Address", back_populates="customer", foreign_keys="Address.customer_id"
    )
    default_address: Mapped["Address | None"] = relationship(
        "Address", foreign_keys=[default_address_id], post_update=True
    )
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="customer")
    carts: Mapped[list["Cart"]] = relationship("Cart", back_populates="customer")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")


class Address(TimestampMixin, Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    property_name: Mapped[str] = mapped_column(String(120))
    block_code: Mapped[str] = mapped_column(String(10))
    flat_no: Mapped[str] = mapped_column(String(30))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    customer: Mapped[Customer] = relationship(
        "Customer", back_populates="addresses", foreign_keys=[customer_id]
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="address")


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp")
    status: Mapped[str] = mapped_column(String(40), default="active")
    current_step: Mapped[str] = mapped_column(String(40), default="new_chat")
    session_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    state_json: Mapped[str] = mapped_column(Text, default="{}")
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    customer: Mapped[Customer] = relationship("Customer", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation")
    carts: Mapped[list["Cart"]] = relationship("Cart", back_populates="conversation")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    direction: Mapped[str] = mapped_column(String(10))
    message_text: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(30), default="text")
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")


class MenuItem(TimestampMixin, Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[str] = mapped_column(String(60))
    price: Mapped[float] = mapped_column(Float)
    aliases: Mapped[str] = mapped_column(Text, default="")
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class Cart(TimestampMixin, Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    status: Mapped[str] = mapped_column(String(20), default="active")
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    min_order_valid: Mapped[bool] = mapped_column(Boolean, default=False)

    customer: Mapped[Customer] = relationship("Customer", back_populates="carts")
    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="carts")
    items: Mapped[list["CartItem"]] = relationship("CartItem", back_populates="cart")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="cart")


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"))
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    item_name: Mapped[str] = mapped_column(String(120))
    qty: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    line_total: Mapped[float] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    cart: Mapped[Cart] = relationship("Cart", back_populates="items")
    menu_item: Mapped[MenuItem] = relationship("MenuItem")


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"))
    address_id: Mapped[int] = mapped_column(ForeignKey("addresses.id"))
    subtotal: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="confirmed")
    source: Mapped[str] = mapped_column(String(20), default="whatsapp")

    customer: Mapped[Customer] = relationship("Customer", back_populates="orders")
    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="orders")
    cart: Mapped[Cart] = relationship("Cart", back_populates="orders")
    address: Mapped[Address] = relationship("Address", back_populates="orders")
