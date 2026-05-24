"""
schemas.py — Pydantic v2 request/response schemas for all API endpoints.

Schemas are grouped by domain and use strict typing with field validators.
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Annotated

from pydantic import BaseModel, Field, field_validator, AfterValidator

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def validate_email_format(v: str) -> str:
    if not EMAIL_REGEX.match(v):
        raise ValueError("value is not a valid email address")
    return v.lower()

# Custom EmailStr that allows private/reserved .local domains cleanly
EmailStr = Annotated[str, AfterValidator(validate_email_format)]

from backend.models import (
    LoyaltyTier,
    NotificationType,
    OrderStatus,
    PaymentMethod,
    POStatus,
    UserRole,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class OrmBase(BaseModel):
    """All response schemas inherit from this to enable ORM mode."""
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: UserRole


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.customer


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.customer
    profile_data: Optional[Dict[str, Any]] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    profile_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class UserResponse(OrmBase):
    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    loyalty_points: int
    loyalty_tier: LoyaltyTier
    profile_data: Optional[Dict[str, Any]] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------

class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=180)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    reliability_rating: float = Field(default=5.0, ge=0.0, le=10.0)
    notes: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    reliability_rating: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    notes: Optional[str] = None


class SupplierResponse(OrmBase):
    id: int
    name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    reliability_rating: float
    notes: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    cost_price: float = Field(default=0.0, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)
    category: Optional[str] = None
    unit_of_measure: str = "unit"
    image_url: Optional[str] = None
    barcode: Optional[str] = None
    bin_location: Optional[str] = None
    expiry_date: Optional[datetime] = None
    supplier_id: Optional[int] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    cost_price: Optional[float] = Field(default=None, ge=0)
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    low_stock_threshold: Optional[int] = Field(default=None, ge=0)
    category: Optional[str] = None
    unit_of_measure: Optional[str] = None
    image_url: Optional[str] = None
    barcode: Optional[str] = None
    bin_location: Optional[str] = None
    expiry_date: Optional[datetime] = None
    supplier_id: Optional[int] = None
    is_active: Optional[bool] = None


class StockAdjustment(BaseModel):
    product_id: int
    adjustment: int  # positive = add, negative = remove
    reason: Optional[str] = None


class ProductResponse(OrmBase):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    cost_price: float
    stock_quantity: int
    low_stock_threshold: int
    category: Optional[str] = None
    unit_of_measure: str
    image_url: Optional[str] = None
    barcode: Optional[str] = None
    bin_location: Optional[str] = None
    expiry_date: Optional[datetime] = None
    is_active: bool
    supplier_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @property
    def is_low_stock(self) -> bool:
        return self.stock_quantity <= self.low_stock_threshold


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class CartItem(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)


class CheckoutRequest(BaseModel):
    items: List[CartItem] = Field(..., min_length=1)
    payment_method: PaymentMethod = PaymentMethod.cash
    discount_amount: float = Field(default=0.0, ge=0)
    tax_rate: float = Field(default=0.08, ge=0, le=1)
    notes: Optional[str] = None


class OrderItemResponse(OrmBase):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    product: Optional[ProductResponse] = None


class OrderResponse(OrmBase):
    id: int
    user_id: Optional[int] = None
    subtotal: float
    tax_rate: float
    tax_amount: float
    discount_amount: float
    total_price: float
    payment_method: PaymentMethod
    status: OrderStatus
    notes: Optional[str] = None
    items: List[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# ---------------------------------------------------------------------------
# Purchase Order
# ---------------------------------------------------------------------------

class POItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_cost: float = Field(..., gt=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    items: List[POItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = None
    expected_delivery: Optional[datetime] = None


class POItemResponse(OrmBase):
    id: int
    product_id: int
    quantity: int
    unit_cost: float
    product: Optional[ProductResponse] = None


class PurchaseOrderResponse(OrmBase):
    id: int
    supplier_id: int
    status: POStatus
    total_cost: float
    notes: Optional[str] = None
    expected_delivery: Optional[datetime] = None
    items: List[POItemResponse] = []
    created_at: datetime
    updated_at: datetime


class POStatusUpdate(BaseModel):
    status: POStatus


# ---------------------------------------------------------------------------
# Employee Shift
# ---------------------------------------------------------------------------

class ShiftCreate(BaseModel):
    user_id: int
    clock_in: datetime
    clock_out: Optional[datetime] = None
    hourly_rate: float = Field(default=15.0, gt=0)
    performance_rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    notes: Optional[str] = None


class ShiftUpdate(BaseModel):
    clock_out: Optional[datetime] = None
    hourly_rate: Optional[float] = Field(default=None, gt=0)
    performance_rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    notes: Optional[str] = None


class ShiftResponse(OrmBase):
    id: int
    user_id: int
    clock_in: datetime
    clock_out: Optional[datetime] = None
    hourly_rate: float
    performance_rating: Optional[float] = None
    notes: Optional[str] = None
    hours_worked: Optional[float] = None
    gross_pay: Optional[float] = None


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------

class ReviewCreate(BaseModel):
    product_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ReviewResponse(OrmBase):
    id: int
    user_id: int
    product_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Stock Transfer
# ---------------------------------------------------------------------------

class StockTransferCreate(BaseModel):
    product_id: int
    from_bin: str
    to_bin: str
    quantity: int = Field(..., gt=0)


class StockTransferResponse(OrmBase):
    id: int
    product_id: int
    from_bin: str
    to_bin: str
    quantity: int
    transferred_by: Optional[int] = None
    transferred_at: datetime


# ---------------------------------------------------------------------------
# Reports / Dashboard
# ---------------------------------------------------------------------------

class DashboardMetrics(BaseModel):
    total_products: int
    low_stock_count: int
    total_orders_today: int
    revenue_today: float
    revenue_this_week: float
    revenue_this_month: float
    active_employees: int
    pending_purchase_orders: int
    total_customers: int
    expiring_soon_count: int


class SalesDataPoint(BaseModel):
    period: str
    revenue: float
    order_count: int
    profit: float


class TopProduct(BaseModel):
    product_id: int
    name: str
    total_sold: int
    total_revenue: float


# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------

class ReorderSuggestion(BaseModel):
    product_id: int
    product_name: str
    current_stock: int
    suggested_order_qty: int
    avg_daily_sales: float
    days_remaining: float
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Chatbot
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    suggestions: List[str] = []
    product_recommendations: List[Dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class NotificationResponse(OrmBase):
    id: int
    type: NotificationType
    message: str
    is_read: bool
    related_id: Optional[int] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Barcode / Hardware
# ---------------------------------------------------------------------------

class BarcodeInput(BaseModel):
    barcode: str = Field(..., min_length=1)
    quantity: int = Field(default=1, gt=0)


class ScaleWeightPayload(BaseModel):
    product_id: int
    weight_kg: float = Field(..., gt=0)
    price_per_kg: Optional[float] = None


class ThermalPrintRequest(BaseModel):
    order_id: int
    format: str = "standard"  # standard | compact | a4
