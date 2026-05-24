"""
routers/products.py — Product and inventory management endpoints.

Includes full CRUD, stock adjustments, barcode lookup, low-stock queries,
and expiry-date alerts.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, pagination, require_manager_or_above
from backend.models import Notification, NotificationType, Product, User
from backend.schemas import (
    BarcodeInput,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    ScaleWeightPayload,
    StockAdjustment,
)

router = APIRouter(prefix="/api/products", tags=["Products"])


def _trigger_low_stock_notification(product: Product, db: Session) -> None:
    """Create a low-stock notification if the product is below threshold."""
    if product.stock_quantity <= product.low_stock_threshold:
        note = Notification(
            type=NotificationType.low_stock,
            message=f"Low stock alert: '{product.name}' has only {product.stock_quantity} {product.unit_of_measure}(s) remaining.",
            related_id=product.id,
        )
        db.add(note)


@router.get("", response_model=List[ProductResponse])
def list_products(
    category: Optional[str] = Query(default=None),
    low_stock_only: bool = Query(default=False),
    search: Optional[str] = Query(default=None),
    active_only: bool = Query(default=True),
    pag: dict = Depends(pagination),
    db: Session = Depends(get_db),
):
    """List products with optional filters for category, stock level, and search."""
    q = db.query(Product)
    if active_only:
        q = q.filter(Product.is_active == True)
    if category:
        q = q.filter(Product.category == category)
    if low_stock_only:
        q = q.filter(Product.stock_quantity <= Product.low_stock_threshold)
    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))
    return q.offset(pag["skip"]).limit(pag["limit"]).all()


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    """Create a new product (manager/admin)."""
    if payload.barcode:
        existing = db.query(Product).filter(Product.barcode == payload.barcode).first()
        if existing:
            raise HTTPException(status_code=409, detail="Barcode already registered")
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    _trigger_low_stock_notification(product, db)
    db.commit()
    return product


@router.get("/categories", response_model=List[str])
def list_categories(db: Session = Depends(get_db)):
    """Return a deduplicated list of all product categories."""
    rows = db.query(Product.category).filter(Product.category != None).distinct().all()
    return sorted([r[0] for r in rows])


@router.get("/expiring-soon", response_model=List[ProductResponse])
def expiring_soon(
    days: int = Query(default=7, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return products expiring within the next N days."""
    cutoff = datetime.now(timezone.utc) + timedelta(days=days)
    return (
        db.query(Product)
        .filter(Product.expiry_date != None, Product.expiry_date <= cutoff, Product.is_active == True)
        .all()
    )


@router.get("/barcode/{barcode}", response_model=ProductResponse)
def lookup_by_barcode(
    barcode: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Simulate barcode/RFID scanner lookup — resolve barcode to product."""
    product = db.query(Product).filter(Product.barcode == barcode).first()
    if not product:
        raise HTTPException(status_code=404, detail="No product found for this barcode")
    return product


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Retrieve a single product by ID."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    """Update product attributes (manager/admin)."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    _trigger_low_stock_notification(product, db)
    db.commit()
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    """Soft-delete a product (manager/admin)."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    db.commit()


@router.post("/adjust-stock", response_model=ProductResponse)
def adjust_stock(
    payload: StockAdjustment,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    """Apply a manual stock quantity adjustment (positive or negative)."""
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    new_qty = product.stock_quantity + payload.adjustment
    if new_qty < 0:
        raise HTTPException(status_code=400, detail="Stock cannot go negative")
    product.stock_quantity = new_qty
    db.commit()
    db.refresh(product)
    _trigger_low_stock_notification(product, db)
    db.commit()
    return product


@router.post("/scale-weight", response_model=dict)
def process_scale_weight(
    payload: ScaleWeightPayload,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Simulate scale weight payload — calculate price from weight."""
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    price_per_kg = payload.price_per_kg or product.price
    total = round(payload.weight_kg * price_per_kg, 2)
    return {
        "product_id": product.id,
        "product_name": product.name,
        "weight_kg": payload.weight_kg,
        "price_per_kg": price_per_kg,
        "total_price": total,
    }
