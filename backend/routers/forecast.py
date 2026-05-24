"""
routers/forecast.py — Demand forecasting and auto-reorder suggestion engine.

Computes average daily sales velocity from historical order data and
recommends replenishment quantities when stock dips below safety thresholds.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import require_manager_or_above
from backend.models import Order, OrderItem, OrderStatus, Product, User
from backend.schemas import ReorderSuggestion

router = APIRouter(prefix="/api/forecast", tags=["Demand Forecasting"])


@router.get("/reorder", response_model=List[ReorderSuggestion])
def reorder_suggestions(
    analysis_days: int = Query(default=30, ge=7, le=180),
    lead_time_days: int = Query(default=3, ge=1, le=30),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    """
    Evaluate historic sales to generate auto-reorder recommendations.

    Algorithm:
    1. For each active product, sum total units sold over the past `analysis_days`.
    2. Compute average daily demand = total_sold / analysis_days.
    3. Days remaining = stock_quantity / avg_daily_demand (∞ if no demand).
    4. Flag products where days_remaining < lead_time_days * 2 (safety buffer).
    5. Suggest order qty = demand for (lead_time_days + 7) days − current stock.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(days=analysis_days)

    # Aggregate sales per product over the analysis window
    sales_rows = (
        db.query(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label("total_sold"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            Order.status == OrderStatus.completed,
            Order.created_at >= since,
        )
        .group_by(OrderItem.product_id)
        .all()
    )
    sales_map = {row.product_id: int(row.total_sold) for row in sales_rows}

    products = db.query(Product).filter(Product.is_active == True).all()
    suggestions: List[ReorderSuggestion] = []

    for product in products:
        total_sold = sales_map.get(product.id, 0)
        avg_daily = total_sold / analysis_days
        if avg_daily == 0:
            days_remaining = float("inf")
        else:
            days_remaining = product.stock_quantity / avg_daily

        safety_buffer_days = lead_time_days * 2
        if days_remaining < safety_buffer_days or product.stock_quantity <= product.low_stock_threshold:
            target_stock = int(avg_daily * (lead_time_days + 7))
            suggested_qty = max(target_stock - product.stock_quantity, product.low_stock_threshold)
            suggestions.append(
                ReorderSuggestion(
                    product_id=product.id,
                    product_name=product.name,
                    current_stock=product.stock_quantity,
                    suggested_order_qty=suggested_qty,
                    avg_daily_sales=round(avg_daily, 2),
                    days_remaining=round(min(days_remaining, 9999), 1),
                    supplier_id=product.supplier_id,
                    supplier_name=product.supplier.name if product.supplier else None,
                )
            )

    return sorted(suggestions, key=lambda s: s.days_remaining)


@router.get("/velocity", response_model=List[dict])
def product_velocity(
    analysis_days: int = Query(default=30, ge=7, le=180),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    """Return product sales velocity (units/day) for movement analysis."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(days=analysis_days)

    rows = (
        db.query(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label("total_sold"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.status == OrderStatus.completed, Order.created_at >= since)
        .group_by(OrderItem.product_id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
        .all()
    )

    results = []
    for row in rows:
        product = db.get(Product, row.product_id)
        results.append({
            "product_id": row.product_id,
            "product_name": product.name if product else f"Product #{row.product_id}",
            "total_sold": int(row.total_sold),
            "avg_daily_velocity": round(int(row.total_sold) / analysis_days, 2),
            "category": product.category if product else None,
        })
    return results
