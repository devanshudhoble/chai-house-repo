from pydantic import BaseModel


class OutboundMessage(BaseModel):
    wa_id: str
    text: str


class DashboardOrderStatusUpdate(BaseModel):
    status: str
