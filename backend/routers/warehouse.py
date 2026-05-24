"""
routers/warehouse.py — Bin-level inventory tracking and intra-store stock transfers.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, pagination, require_manager_or_above
from backend.models import Product, StockTransfer, User
from backend.schemas import StockTransferCreate, StockTransferResponse

router = APIRouter(prefix="/api/warehouse", tags=["Warehouse & Inventory"])


@router.get("/inventory", response_model=List[dict])
def bin_inventory(
    bin_location: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return product inventory grouped by bin location."""
    q = db.query(Product).filter(Product.is_active == True)
    if bin_location:
        q = q.filter(Product.bin_location == bin_location)
    products = q.all()
    return [
        {
            "product_id": p.id,
            "name": p.name,
            "category": p.category,
            "bin_location": p.bin_location or "Unassigned",
            "stock_quantity": p.stock_quantity,
            "low_stock_threshold": p.low_stock_threshold,
            "is_low_stock": p.stock_quantity <= p.low_stock_threshold,
            "expiry_date": p.expiry_date.isoformat() if p.expiry_date else None,
            "unit_of_measure": p.unit_of_measure,
        }
        for p in products
    ]


@router.get("/bins", response_model=List[str])
def list_bins(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Return all unique bin location identifiers."""
    rows = db.query(Product.bin_location).filter(Product.bin_location != None).distinct().all()
    return sorted([r[0] for r in rows])


@router.post("/transfer", response_model=StockTransferResponse, status_code=status.HTTP_201_CREATED)
def transfer_stock(
    payload: StockTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_above),
):
    """
    Perform an intra-store stock bin transfer.
    Updates the product's bin_location to the destination bin.
    """
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock_quantity < payload.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock for transfer")

    transfer = StockTransfer(
        product_id=payload.product_id,
        from_bin=payload.from_bin,
        to_bin=payload.to_bin,
        quantity=payload.quantity,
        transferred_by=current_user.id,
    )
    db.add(transfer)
    product.bin_location = payload.to_bin
    db.commit()
    db.refresh(transfer)
    return transfer


@router.get("/transfers", response_model=List[StockTransferResponse])
def list_transfers(
    product_id: Optional[int] = Query(default=None),
    pag: dict = Depends(pagination),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List stock transfer history."""
    q = db.query(StockTransfer)
    if product_id:
        q = q.filter(StockTransfer.product_id == product_id)
    return q.order_by(StockTransfer.transferred_at.desc()).offset(pag["skip"]).limit(pag["limit"]).all()
