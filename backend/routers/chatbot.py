"""
routers/chatbot.py — Integrated client-side assistant endpoint.

Provides rule-based responses for navigation help, product recommendations
based on metadata, and dynamic grocery suggestions.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import Product, User
from backend.schemas import ChatMessage, ChatResponse

router = APIRouter(prefix="/api/chatbot", tags=["System Chatbot"])

# ---------------------------------------------------------------------------
# Rule-based intent map
# ---------------------------------------------------------------------------

NAVIGATION_INTENTS = {
    "dashboard": "Navigate to the **Dashboard** tab for KPI metrics and quick insights.",
    "product": "Go to **Products** in the sidebar to browse the full product catalog.",
    "inventory": "Check **Warehouse** → Inventory for bin-level stock details.",
    "order": "Visit **POS / Orders** to create a new sale or view order history.",
    "report": "Go to **Analytics** to view daily, weekly, and monthly sales reports.",
    "supplier": "Find all supplier records and purchase orders under **Suppliers**.",
    "employee": "Manage shifts and payroll under **Employees** in the sidebar.",
    "loyalty": "Customer loyalty points and tier status are in **Customer Loyalty**.",
    "forecast": "View demand forecasting and reorder suggestions under **Forecasting**.",
    "help": "I can help with navigation, product lookup, or grocery recommendations. Just ask!",
}

CATEGORY_SUGGESTIONS: Dict[str, List[str]] = {
    "fruits": ["apples", "bananas", "oranges", "strawberries", "mangoes"],
    "vegetables": ["spinach", "broccoli", "carrots", "tomatoes", "bell peppers"],
    "dairy": ["whole milk", "Greek yogurt", "cheddar cheese", "butter", "cream cheese"],
    "bakery": ["sourdough bread", "whole grain muffins", "bagels", "croissants"],
    "meat": ["chicken breast", "ground beef", "salmon fillets", "turkey"],
    "snacks": ["mixed nuts", "trail mix", "granola bars", "dark chocolate"],
    "beverages": ["sparkling water", "orange juice", "green tea", "almond milk"],
}


def _detect_intent(message: str) -> str:
    msg = message.lower()
    for keyword, response in NAVIGATION_INTENTS.items():
        if keyword in msg:
            return response
    return ""


def _detect_category(message: str) -> str:
    msg = message.lower()
    for category in CATEGORY_SUGGESTIONS:
        if category in msg:
            return category
    return ""


def _recommend_products(db: Session, category: str | None, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch active products filtered by category for recommendations."""
    q = db.query(Product).filter(Product.is_active == True, Product.stock_quantity > 0)
    if category:
        q = q.filter(Product.category.ilike(f"%{category}%"))
    products = q.limit(limit * 3).all()
    sample = random.sample(products, min(limit, len(products)))
    return [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "category": p.category,
            "unit": p.unit_of_measure,
            "image_url": p.image_url,
        }
        for p in sample
    ]


@router.post("/message", response_model=ChatResponse)
def chat(
    payload: ChatMessage,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Process a chat message and return a contextual response.

    Priority:
    1. Navigation intents → direct user to the right module.
    2. Category/product intents → return product recommendations.
    3. Grocery suggestions → recommend popular items from the store.
    4. Fallback → general assistance message.
    """
    reply = ""
    suggestions: List[str] = []
    product_recs: List[Dict[str, Any]] = []

    # 1. Navigation intent
    nav_response = _detect_intent(payload.message)
    if nav_response:
        reply = nav_response
        suggestions = ["Show me today's dashboard", "What products are low in stock?", "How do I place an order?"]

    # 2. Category-based recommendations
    else:
        category = _detect_category(payload.message)
        if category:
            product_recs = _recommend_products(db, category)
            sugg_names = CATEGORY_SUGGESTIONS.get(category, [])
            reply = f"Here are some great **{category}** options we carry in our store:"
            suggestions = [f"Tell me about {name}" for name in sugg_names[:3]]

        # 3. Grocery suggestions or general query
        elif any(kw in payload.message.lower() for kw in ["suggest", "recommend", "what should", "popular", "buy"]):
            product_recs = _recommend_products(db, None, limit=5)
            reply = "Here are some popular items our customers love right now:"
            suggestions = [f"Show me {c} products" for c in list(CATEGORY_SUGGESTIONS.keys())[:4]]

        # 4. Fallback
        else:
            reply = (
                "I'm FreshMart's assistant! I can help you with:\n"
                "- **Navigation** (ask about dashboard, products, orders, reports)\n"
                "- **Product search** by category (fruits, dairy, meat, snacks…)\n"
                "- **Grocery recommendations** (just ask 'what should I buy?')"
            )
            suggestions = ["Show me popular products", "How do I check inventory?", "Where are the sales reports?"]

    return ChatResponse(reply=reply, suggestions=suggestions, product_recommendations=product_recs)
