"""
routers/reports.py — Financial analytics, KPI dashboard metrics, and sales data aggregations.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, require_manager_or_above
from backend.models import (
    Notification,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    PurchaseOrder,
    POStatus,
    User,
    UserRole,
)
from backend.schemas import DashboardMetrics, SalesDataPoint, TopProduct

router = APIRouter(prefix="/api/reports", tags=["Reports & Analytics"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/dashboard", response_model=DashboardMetrics)
def dashboard_metrics(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Aggregate KPI metrics for the admin dashboard."""
    now = _utc_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    def revenue_between(start: datetime, end: datetime) -> float:
        result = (
            db.query(func.sum(Order.total_price))
            .filter(
                Order.status == OrderStatus.completed,
                Order.created_at >= start,
                Order.created_at < end,
            )
            .scalar()
        )
        return round(result or 0.0, 2)

    orders_today = (
        db.query(func.count(Order.id))
        .filter(Order.created_at >= today_start)
        .scalar()
        or 0
    )
    expiry_cutoff = now + timedelta(days=7)

    return DashboardMetrics(
        total_products=db.query(func.count(Product.id)).filter(Product.is_active == True).scalar() or 0,
        low_stock_count=db.query(func.count(Product.id)).filter(
            Product.stock_quantity <= Product.low_stock_threshold, Product.is_active == True
        ).scalar() or 0,
        total_orders_today=orders_today,
        revenue_today=revenue_between(today_start, now),
        revenue_this_week=revenue_between(week_start, now),
        revenue_this_month=revenue_between(month_start, now),
        active_employees=db.query(func.count(User.id)).filter(
            User.role.in_([UserRole.cashier, UserRole.manager]), User.is_active == True
        ).scalar() or 0,
        pending_purchase_orders=db.query(func.count(PurchaseOrder.id)).filter(
            PurchaseOrder.status.in_([POStatus.draft, POStatus.sent])
        ).scalar() or 0,
        total_customers=db.query(func.count(User.id)).filter(
            User.role == UserRole.customer, User.is_active == True
        ).scalar() or 0,
        expiring_soon_count=db.query(func.count(Product.id)).filter(
            Product.expiry_date != None,
            Product.expiry_date <= expiry_cutoff,
            Product.is_active == True,
        ).scalar() or 0,
    )


@router.get("/sales", response_model=List[SalesDataPoint])
def sales_report(
    period: str = Query(default="daily", regex="^(daily|weekly|monthly)$"),
    days_back: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    """
    Return revenue and order count aggregated by daily/weekly/monthly periods.
    Profit = Revenue − (sum of cost_price × quantity sold).
    """
    now = _utc_now()
    start = now - timedelta(days=days_back)

    completed_orders = (
        db.query(Order)
        .filter(Order.status == OrderStatus.completed, Order.created_at >= start)
        .all()
    )

    # Bucket orders by period
    buckets: dict[str, dict] = {}
    for order in completed_orders:
        dt = order.created_at
        if period == "daily":
            key = dt.strftime("%Y-%m-%d")
        elif period == "weekly":
            week_num = dt.isocalendar()[1]
            key = f"{dt.year}-W{week_num:02d}"
        else:
            key = dt.strftime("%Y-%m")

        if key not in buckets:
            buckets[key] = {"revenue": 0.0, "order_count": 0, "cost": 0.0}
        buckets[key]["revenue"] += order.total_price
        buckets[key]["order_count"] += 1
        for item in order.items:
            if item.product:
                buckets[key]["cost"] += item.product.cost_price * item.quantity

    return [
        SalesDataPoint(
            period=k,
            revenue=round(v["revenue"], 2),
            order_count=v["order_count"],
            profit=round(v["revenue"] - v["cost"], 2),
        )
        for k, v in sorted(buckets.items())
    ]


@router.get("/top-products", response_model=List[TopProduct])
def top_products(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    """Return the top-selling products ranked by total quantity sold."""
    rows = (
        db.query(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label("total_sold"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("total_revenue"),
        )
        .group_by(OrderItem.product_id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
        .all()
    )

    results = []
    for row in rows:
        product = db.get(Product, row.product_id)
        results.append(
            TopProduct(
                product_id=row.product_id,
                name=product.name if product else f"Product #{row.product_id}",
                total_sold=int(row.total_sold),
                total_revenue=round(float(row.total_revenue), 2),
            )
        )
    return results


@router.get("/notifications", response_model=List[dict])
def get_notifications(
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Retrieve system notifications."""
    q = db.query(Notification)
    if unread_only:
        q = q.filter(Notification.is_read == False)
    notifications = q.order_by(Notification.created_at.desc()).limit(50).all()
    return [
        {
            "id": n.id,
            "type": n.type.value,
            "message": n.message,
            "is_read": n.is_read,
            "related_id": n.related_id,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]


@router.patch("/notifications/{notification_id}/read", response_model=dict)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    n = db.get(Notification, notification_id)
    if not n:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"success": True}
