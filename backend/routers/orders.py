"""
routers/orders.py — Point-of-Sale checkout, order management, and invoice generation.

Handles real-time cart validation, stock deduction, loyalty point accumulation,
payment simulation, and thermal-print-ready invoice formatting.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, pagination, require_cashier_or_above
from backend.models import (
    LoyaltyTier,
    Notification,
    NotificationType,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    User,
)
from backend.schemas import (
    CheckoutRequest,
    OrderResponse,
    OrderStatusUpdate,
    ThermalPrintRequest,
)

router = APIRouter(prefix="/api/orders", tags=["Orders & POS"])

# Loyalty tier thresholds
TIER_THRESHOLDS = {
    LoyaltyTier.bronze: 0,
    LoyaltyTier.silver: 500,
    LoyaltyTier.gold: 2000,
    LoyaltyTier.platinum: 5000,
}


def _recalculate_tier(user: User) -> None:
    """Promote customer loyalty tier based on accumulated points."""
    pts = user.loyalty_points
    if pts >= 5000:
        user.loyalty_tier = LoyaltyTier.platinum
    elif pts >= 2000:
        user.loyalty_tier = LoyaltyTier.gold
    elif pts >= 500:
        user.loyalty_tier = LoyaltyTier.silver
    else:
        user.loyalty_tier = LoyaltyTier.bronze


@router.post("/checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cashier_or_above),
):
    """
    Full POS checkout flow:
    1. Validate all cart items and available stock.
    2. Compute subtotal, tax, discount, and total.
    3. Deduct stock quantities.
    4. Persist Order and OrderItems.
    5. Award loyalty points to the user.
    6. Fire low-stock notifications if thresholds are breached.
    """
    # --- Step 1: Validate items & fetch products ---
    products_map: dict[int, Product] = {}
    for item in payload.items:
        product = db.get(Product, item.product_id)
        if not product or not product.is_active:
            raise HTTPException(
                status_code=404,
                detail=f"Product ID {item.product_id} not found or inactive",
            )
        if product.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for '{product.name}': requested {item.quantity}, available {product.stock_quantity}",
            )
        products_map[item.product_id] = product

    # --- Step 2: Calculate totals ---
    subtotal = sum(
        products_map[item.product_id].price * item.quantity for item in payload.items
    )
    tax_amount = round(subtotal * payload.tax_rate, 2)
    discount = min(payload.discount_amount, subtotal)
    total = round(subtotal + tax_amount - discount, 2)

    # --- Step 3: Create Order ---
    order = Order(
        user_id=current_user.id,
        subtotal=round(subtotal, 2),
        tax_rate=payload.tax_rate,
        tax_amount=tax_amount,
        discount_amount=discount,
        total_price=total,
        payment_method=payload.payment_method,
        status=OrderStatus.completed,
        notes=payload.notes,
    )
    db.add(order)
    db.flush()  # Get order.id before committing

    # --- Step 4: Create OrderItems + deduct stock ---
    for item in payload.items:
        product = products_map[item.product_id]
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=product.price,
            )
        )
        product.stock_quantity -= item.quantity

        # Low-stock notification
        if product.stock_quantity <= product.low_stock_threshold:
            db.add(
                Notification(
                    type=NotificationType.low_stock,
                    message=f"Low stock: '{product.name}' → {product.stock_quantity} remaining",
                    related_id=product.id,
                )
            )

    # --- Step 5: Award loyalty points (1 point per $1 spent) ---
    points_earned = int(total)
    current_user.loyalty_points += points_earned
    _recalculate_tier(current_user)

    # --- Step 6: New-order notification ---
    db.add(
        Notification(
            type=NotificationType.new_order,
            message=f"New order #{order.id} placed — ${total:.2f} via {payload.payment_method.value}",
            related_id=order.id,
        )
    )

    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=List[OrderResponse])
def list_orders(
    user_id: Optional[int] = Query(default=None),
    status_filter: Optional[OrderStatus] = Query(default=None, alias="status"),
    pag: dict = Depends(pagination),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List orders. Customers see only their own; staff/admin see all."""
    q = db.query(Order)
    if current_user.role.value == "customer":
        q = q.filter(Order.user_id == current_user.id)
    elif user_id:
        q = q.filter(Order.user_id == user_id)
    if status_filter:
        q = q.filter(Order.status == status_filter)
    return q.order_by(Order.created_at.desc()).offset(pag["skip"]).limit(pag["limit"]).all()


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a single order. Customers can only view their own orders."""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.role.value == "customer" and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_cashier_or_above),
):
    """Update order status (cashier+)."""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = payload.status
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/invoice", response_model=dict)
def generate_invoice(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a structured digital invoice payload suitable for thermal printing."""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.role.value == "customer" and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    line_items = [
        {
            "name": item.product.name if item.product else f"Product #{item.product_id}",
            "qty": item.quantity,
            "unit_price": item.unit_price,
            "line_total": round(item.quantity * item.unit_price, 2),
        }
        for item in order.items
    ]

    return {
        "invoice_number": f"INV-{order.id:06d}",
        "date": order.created_at.isoformat(),
        "cashier": current_user.name,
        "payment_method": order.payment_method.value,
        "line_items": line_items,
        "subtotal": order.subtotal,
        "tax_rate_pct": f"{order.tax_rate * 100:.1f}%",
        "tax_amount": order.tax_amount,
        "discount": order.discount_amount,
        "total": order.total_price,
        "status": order.status.value,
        "store_name": "FreshMart Grocery Store",
        "store_address": "123 Market Street, City, ST 00000",
        "thank_you_message": "Thank you for shopping with us!",
    }
