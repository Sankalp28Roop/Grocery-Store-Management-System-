"""
routers/loyalty.py — Customer loyalty points, tier calculation, and product reviews.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import Review, User
from backend.schemas import ReviewCreate, ReviewResponse

router = APIRouter(prefix="/api/loyalty", tags=["Loyalty & Reviews"])

TIER_INFO = {
    "bronze": {"min_points": 0, "discount_pct": 0, "label": "Bronze"},
    "silver": {"min_points": 500, "discount_pct": 2, "label": "Silver"},
    "gold": {"min_points": 2000, "discount_pct": 5, "label": "Gold"},
    "platinum": {"min_points": 5000, "discount_pct": 10, "label": "Platinum"},
}


@router.get("/points/{user_id}", response_model=dict)
def loyalty_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return loyalty points and tier status for a user."""
    if current_user.role.value not in ("admin", "manager") and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tier_data = TIER_INFO.get(user.loyalty_tier.value, TIER_INFO["bronze"])
    next_tiers = [t for t in TIER_INFO.values() if t["min_points"] > user.loyalty_points]
    next_tier = min(next_tiers, key=lambda t: t["min_points"]) if next_tiers else None

    return {
        "user_id": user.id,
        "name": user.name,
        "points": user.loyalty_points,
        "tier": user.loyalty_tier.value,
        "tier_label": tier_data["label"],
        "discount_pct": tier_data["discount_pct"],
        "next_tier": next_tier,
        "points_to_next_tier": (next_tier["min_points"] - user.loyalty_points) if next_tier else 0,
    }


@router.post("/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a product review. Each user can review a product once."""
    existing = (
        db.query(Review)
        .filter(Review.user_id == current_user.id, Review.product_id == payload.product_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="You have already reviewed this product")

    review = Review(
        user_id=current_user.id,
        product_id=payload.product_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.get("/reviews/product/{product_id}", response_model=List[ReviewResponse])
def product_reviews(
    product_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve all reviews for a product."""
    return db.query(Review).filter(Review.product_id == product_id).order_by(Review.created_at.desc()).all()


@router.get("/purchase-history/{user_id}", response_model=List[dict])
def purchase_history(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return summarized purchase history for loyalty tracking."""
    if current_user.role.value not in ("admin", "manager") and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from backend.models import Order, OrderStatus

    orders = (
        db.query(Order)
        .filter(Order.user_id == user_id, Order.status == OrderStatus.completed)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [
        {
            "order_id": o.id,
            "total": o.total_price,
            "items_count": len(o.items),
            "payment_method": o.payment_method.value,
            "date": o.created_at.isoformat(),
        }
        for o in orders
    ]
