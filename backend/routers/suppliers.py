"""
routers/suppliers.py — Supplier records and Purchase Order management.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import pagination, require_manager_or_above
from backend.models import Product, PurchaseOrder, PurchaseOrderItem, Supplier, User
from backend.schemas import (
    POStatusUpdate,
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    SupplierCreate,
    SupplierResponse,
    SupplierUpdate,
)

router = APIRouter(prefix="/api/suppliers", tags=["Suppliers & Procurement"])


# ─── Supplier CRUD ─────────────────────────────────────────────────────────

@router.get("", response_model=List[SupplierResponse])
def list_suppliers(
    pag: dict = Depends(pagination),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    return db.query(Supplier).offset(pag["skip"]).limit(pag["limit"]).all()


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    db.delete(supplier)
    db.commit()


# ─── Purchase Orders ────────────────────────────────────────────────────────

@router.get("/purchase-orders", response_model=List[PurchaseOrderResponse])
def list_purchase_orders(
    pag: dict = Depends(pagination),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    return db.query(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).offset(pag["skip"]).limit(pag["limit"]).all()


@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    """Create a structured Purchase Order with line items and auto-calculated total."""
    supplier = db.get(Supplier, payload.supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    total_cost = sum(item.quantity * item.unit_cost for item in payload.items)
    po = PurchaseOrder(
        supplier_id=payload.supplier_id,
        total_cost=total_cost,
        notes=payload.notes,
        expected_delivery=payload.expected_delivery,
    )
    db.add(po)
    db.flush()

    for item in payload.items:
        product = db.get(Product, item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        db.add(
            PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
            )
        )

    db.commit()
    db.refresh(po)
    return po


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderResponse)
def get_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


@router.patch("/purchase-orders/{po_id}/status", response_model=PurchaseOrderResponse)
def update_po_status(
    po_id: int,
    payload: POStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    """
    Update PO status. When marked 'received', auto-increment product stock
    quantities (Goods Receipt matching).
    """
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if payload.status.value == "received" and po.status.value != "received":
        for item in po.items:
            product = db.get(Product, item.product_id)
            if product:
                product.stock_quantity += item.quantity

    po.status = payload.status
    db.commit()
    db.refresh(po)
    return po
