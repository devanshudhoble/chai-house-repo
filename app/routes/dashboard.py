from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.repository import Repository


router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    repo = Repository(db)
    orders = repo.list_orders()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "orders": orders,
        },
    )


@router.get("/dashboard/orders/{order_id}", response_class=HTMLResponse)
def order_detail(order_id: int, request: Request, db: Session = Depends(get_db)):
    repo = Repository(db)
    order = repo.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return templates.TemplateResponse(request, "order_detail.html", {"order": order})


@router.post("/dashboard/orders/{order_id}/status")
def update_order_status(order_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    repo = Repository(db)
    order = repo.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = status
    db.commit()
    return RedirectResponse(url=f"/dashboard/orders/{order_id}", status_code=303)
