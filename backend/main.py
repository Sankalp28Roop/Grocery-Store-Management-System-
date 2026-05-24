"""
main.py — FastAPI application factory.

Registers all routers, configures CORS, mounts the frontend static files,
and seeds the database with realistic demo data on first run.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.auth import hash_password
from backend.database import Base, SessionLocal, engine
from backend.models import (
    EmployeeShift,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    POStatus,
    Supplier,
    User,
    UserRole,
    StorefrontSetting,
)
from backend.routers import (
    auth as auth_router,
    chatbot as chatbot_router,
    employees as employees_router,
    forecast as forecast_router,
    loyalty as loyalty_router,
    orders as orders_router,
    products as products_router,
    reports as reports_router,
    suppliers as suppliers_router,
    users as users_router,
    warehouse as warehouse_router,
    storefront as storefront_router,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ---------------------------------------------------------------------------
# Database initialization & seeding
# ---------------------------------------------------------------------------

def _seed_database() -> None:
    """Populate the database with realistic demo data on first run."""
    db = SessionLocal()
    try:
        # Seed StorefrontSettings if not exists
        if not db.query(StorefrontSetting).first():
            hero_slides = [
                {
                    "tag": "WEEKLY SPECIAL OFFER",
                    "title": "Fresh & Organic Fruits",
                    "subtitle": "Get up to 40% off on all organic tree-ripened fruits. Farm-direct, non-GMO, hand-picked daily.",
                    "bgGradient": "linear-gradient(135deg, #159957, #155799)",
                    "buttonText": "Shop Produce",
                    "category": "Fruits",
                    "image": "https://images.unsplash.com/photo-1619546813926-a78fa6372cd2?w=600"
                },
                {
                    "tag": "FRESH FROM SUNRISE BAKERY",
                    "title": "Artisan Baking Delights",
                    "subtitle": "Fresh stone-baked sourdough loaves, rich bagels, and hand-crafted pastry treats delivered daily.",
                    "bgGradient": "linear-gradient(135deg, #f4c430, #e67e22)",
                    "buttonText": "Browse Bakery",
                    "category": "Bakery",
                    "image": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600"
                },
                {
                    "tag": "WILD & SUSTAINABLE HARVEST",
                    "title": "Premium Seafood Cut",
                    "subtitle": "Premium high-quality Atlantic salmon fillets, jumbo prawns, and fresh crab catch packed on ice.",
                    "bgGradient": "linear-gradient(135deg, #00c6ff, #0072ff)",
                    "buttonText": "Order Seafood",
                    "category": "Seafood",
                    "image": "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=600"
                }
            ]
            promos = [
                {
                    "title": "Daily Harvest Green",
                    "tag": "SAVE 15%",
                    "desc": "Crisp organic leafy vegetables",
                    "bg": "#e8f7ee",
                    "color": "#00a86b",
                    "category": "Vegetables"
                },
                {
                    "title": "Free Delivery",
                    "tag": "SPEND $35+",
                    "desc": "Fast, contact-free cold delivery",
                    "bg": "#fff8eb",
                    "color": "#e67e22",
                    "action": "open-delivery"
                }
            ]
            info = {
                "newsletter": {
                    "title": "Join our newsletter list",
                    "description": "Sign up today and get a $10 coupon in your loyalty credit account instantly! Plus, receive weekly promotions, fresh recipes, and seasonal arrivals."
                },
                "footer": {
                    "about_title": "FreshMart Store",
                    "about_text": "Your number-one local provider of organic, fresh, and premium quality grocery items. Order online for fast 1-hour doorstep delivery or pick up curbside at our retail storefront location.",
                    "hours_title": "Operational Hours",
                    "hours": [
                        "Monday – Friday: 8:00 AM – 10:00 PM",
                        "Saturday – Sunday: 9:00 AM – 9:00 PM",
                        "Curbside Pickup: Open 24/7 Daily"
                    ],
                    "support_title": "Contact Support",
                    "support": [
                        "📍 100 Broadway St, New York, NY 10001",
                        "📞 Phone: +1 (212) 555-0199",
                        "✉️ Support: orders@freshmart.com"
                    ]
                }
            }
            db.add(StorefrontSetting(key="storefront_hero", value=hero_slides))
            db.add(StorefrontSetting(key="storefront_promos", value=promos))
            db.add(StorefrontSetting(key="storefront_info", value=info))
            db.commit()
            print("✅ Storefront database settings seeded successfully.")

        # Skip seeding if data already exists
        if db.query(Product).first():
            return

        # ── Users ────────────────────────────────────────────────────────
        # Alice Chen is omitted; Sankalp Swarup is seeded via asynchronous init_db_seeding.
        if db.query(User).count() <= 1:
            manager = User(name="Bob Martinez", email="manager@freshmart.com", password_hash=hash_password("manager123"), role=UserRole.manager)
            cashier1 = User(name="Carol Williams", email="cashier@freshmart.com", password_hash=hash_password("cashier123"), role=UserRole.cashier)
            cashier2 = User(name="David Lee", email="david@freshmart.com", password_hash=hash_password("cashier123"), role=UserRole.cashier)
            customer1 = User(name="Emma Johnson", email="emma@example.com", password_hash=hash_password("customer123"), role=UserRole.customer, loyalty_points=1250)
            customer2 = User(name="Frank Brown", email="frank@example.com", password_hash=hash_password("customer123"), role=UserRole.customer, loyalty_points=320)
            db.add_all([manager, cashier1, cashier2, customer1, customer2])
            db.flush()

        # ── Suppliers ────────────────────────────────────────────────────
        s1 = Supplier(name="Green Valley Farms", contact_email="orders@greenvalley.com", contact_phone="+1-555-0100", address="456 Farm Road, Valley, CA 95000", reliability_rating=9.2)
        s2 = Supplier(name="OceanBreeze Seafood", contact_email="supply@oceanbreeze.com", contact_phone="+1-555-0200", address="789 Harbor Dr, Port City, FL 33000", reliability_rating=8.5)
        s3 = Supplier(name="SunGold Bakery Co.", contact_email="wholesale@sungold.com", contact_phone="+1-555-0300", address="321 Wheat Lane, Breadton, OR 97000", reliability_rating=9.7)
        s4 = Supplier(name="Alpine Dairy Ltd.", contact_email="orders@alpinedairy.com", contact_phone="+1-555-0400", address="100 Pasture Blvd, Milktown, WI 54000", reliability_rating=9.0)
        db.add_all([s1, s2, s3, s4])
        db.flush()

        # ── Products ─────────────────────────────────────────────────────
        now = datetime.utcnow()
        products_data = [
            # Fruits
            Product(name="Organic Gala Apples", description="Crisp and sweet Washington state apples", price=3.99, cost_price=2.10, stock_quantity=150, low_stock_threshold=20, category="Fruits", unit_of_measure="lb", image_url="https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=400", barcode="8901234567890", bin_location="A-01", supplier_id=s1.id),
            Product(name="Cavendish Bananas", description="Premium ripe bananas", price=1.49, cost_price=0.70, stock_quantity=200, low_stock_threshold=30, category="Fruits", unit_of_measure="lb", image_url="https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=400", barcode="8901234567891", bin_location="A-02", supplier_id=s1.id),
            Product(name="Navel Oranges", description="Seedless juicy California navel oranges", price=4.49, cost_price=2.50, stock_quantity=120, low_stock_threshold=15, category="Fruits", unit_of_measure="lb", image_url="https://images.unsplash.com/photo-1547514701-42782101795e?w=400", barcode="8901234567892", bin_location="A-03", supplier_id=s1.id),
            Product(name="Fresh Strawberries", description="Hand-picked sweet strawberries", price=4.99, cost_price=2.80, stock_quantity=8, low_stock_threshold=10, category="Fruits", unit_of_measure="pint", image_url="https://images.unsplash.com/photo-1464965911861-746a04b4bca6?w=400", barcode="8901234567893", bin_location="A-04", supplier_id=s1.id, expiry_date=now + timedelta(days=4)),
            Product(name="Alphonso Mangoes", description="Premium imported Alphonso mangoes", price=6.99, cost_price=4.00, stock_quantity=45, low_stock_threshold=10, category="Fruits", unit_of_measure="each", image_url="https://images.unsplash.com/photo-1553279768-865429fa0078?w=400", barcode="8901234567894", bin_location="A-05", supplier_id=s1.id),
            # Vegetables
            Product(name="Baby Spinach", description="Tender organic baby spinach leaves", price=3.49, cost_price=1.80, stock_quantity=60, low_stock_threshold=15, category="Vegetables", unit_of_measure="bag", image_url="https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=400", barcode="8901234567895", bin_location="B-01", supplier_id=s1.id, expiry_date=now + timedelta(days=5)),
            Product(name="Broccoli Crown", description="Fresh organic broccoli crowns", price=2.99, cost_price=1.50, stock_quantity=80, low_stock_threshold=15, category="Vegetables", unit_of_measure="each", image_url="https://images.unsplash.com/photo-1459411621453-7b03977f4bfc?w=400", barcode="8901234567896", bin_location="B-02", supplier_id=s1.id),
            Product(name="Rainbow Carrots", description="Colorful heirloom carrot mix", price=3.29, cost_price=1.60, stock_quantity=5, low_stock_threshold=12, category="Vegetables", unit_of_measure="bunch", image_url="https://images.unsplash.com/photo-1445282768818-728615cc910a?w=400", barcode="8901234567897", bin_location="B-03", supplier_id=s1.id),
            Product(name="Roma Tomatoes", description="Firm ripe roma tomatoes", price=2.49, cost_price=1.20, stock_quantity=100, low_stock_threshold=20, category="Vegetables", unit_of_measure="lb", image_url="https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=400", barcode="8901234567898", bin_location="B-04", supplier_id=s1.id),
            # Dairy
            Product(name="Whole Milk (1 Gallon)", description="Fresh farm whole milk", price=4.29, cost_price=2.80, stock_quantity=90, low_stock_threshold=20, category="Dairy", unit_of_measure="gallon", image_url="https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400", barcode="8901234567899", bin_location="C-01", supplier_id=s4.id, expiry_date=now + timedelta(days=10)),
            Product(name="Greek Yogurt Plain", description="Thick creamy Greek yogurt 32oz", price=5.99, cost_price=3.50, stock_quantity=55, low_stock_threshold=12, category="Dairy", unit_of_measure="tub", image_url="https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400", barcode="8901234567900", bin_location="C-02", supplier_id=s4.id, expiry_date=now + timedelta(days=14)),
            Product(name="Sharp Cheddar Block", description="Aged sharp cheddar cheese 16oz", price=6.49, cost_price=4.00, stock_quantity=40, low_stock_threshold=8, category="Dairy", unit_of_measure="block", image_url="https://images.unsplash.com/photo-1552767059-ce182ead6c1b?w=400", barcode="8901234567901", bin_location="C-03", supplier_id=s4.id),
            # Bakery
            Product(name="Sourdough Loaf", description="Artisan hand-crafted sourdough", price=7.99, cost_price=3.50, stock_quantity=25, low_stock_threshold=8, category="Bakery", unit_of_measure="loaf", image_url="https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400", barcode="8901234567902", bin_location="D-01", supplier_id=s3.id, expiry_date=now + timedelta(days=3)),
            Product(name="Whole Wheat Bagels 6-Pack", description="Stone-baked whole wheat bagels", price=4.49, cost_price=2.00, stock_quantity=30, low_stock_threshold=10, category="Bakery", unit_of_measure="pack", image_url="https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=400", barcode="8901234567903", bin_location="D-02", supplier_id=s3.id),
            # Seafood
            Product(name="Atlantic Salmon Fillet", description="Wild-caught Atlantic salmon", price=12.99, cost_price=8.00, stock_quantity=3, low_stock_threshold=5, category="Seafood", unit_of_measure="lb", image_url="https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=400", barcode="8901234567904", bin_location="E-01", supplier_id=s2.id, expiry_date=now + timedelta(days=2)),
            Product(name="Jumbo Shrimp 2lb Bag", description="Peeled and deveined jumbo shrimp", price=18.99, cost_price=12.00, stock_quantity=20, low_stock_threshold=6, category="Seafood", unit_of_measure="bag", image_url="https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?w=400", barcode="8901234567905", bin_location="E-02", supplier_id=s2.id),
            # Snacks
            Product(name="Mixed Nuts Premium Tin", description="Gourmet mixed nuts with cashews, almonds, pecans", price=13.99, cost_price=8.00, stock_quantity=70, low_stock_threshold=15, category="Snacks", unit_of_measure="tin", image_url="https://images.unsplash.com/photo-1609167830220-7164aa360951?w=400", barcode="8901234567906", bin_location="F-01"),
            Product(name="Dark Chocolate 85%", description="Single origin 85% dark chocolate", price=4.99, cost_price=2.50, stock_quantity=85, low_stock_threshold=20, category="Snacks", unit_of_measure="bar", image_url="https://images.unsplash.com/photo-1548907040-4baa42d10919?w=400", barcode="8901234567907", bin_location="F-02"),
            # Beverages
            Product(name="Sparkling Water 12-Pack", description="Unflavored sparkling mineral water", price=8.99, cost_price=4.50, stock_quantity=60, low_stock_threshold=15, category="Beverages", unit_of_measure="pack", image_url="https://images.unsplash.com/photo-1567103472667-6898f3a79cf2?w=400", barcode="8901234567908", bin_location="G-01"),
            Product(name="Fresh Orange Juice 52oz", description="Cold-pressed not-from-concentrate OJ", price=5.49, cost_price=3.00, stock_quantity=35, low_stock_threshold=10, category="Beverages", unit_of_measure="bottle", image_url="https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=400", barcode="8901234567909", bin_location="G-02", expiry_date=now + timedelta(days=7)),
        ]
        db.add_all(products_data)
        db.flush()

        # Fix typo in Sharp Cheddar (stock_price shouldn't exist — ignore it, SQLAlchemy will skip unknown attrs)

        # ── Purchase Orders ───────────────────────────────────────────────
        po1 = PurchaseOrder(supplier_id=s1.id, status=POStatus.sent, total_cost=450.00, notes="Weekly fresh produce order", expected_delivery=now + timedelta(days=2))
        po2 = PurchaseOrder(supplier_id=s4.id, status=POStatus.draft, total_cost=280.00, notes="Monthly dairy replenishment")
        db.add_all([po1, po2])
        db.flush()

        db.add(PurchaseOrderItem(purchase_order_id=po1.id, product_id=products_data[0].id, quantity=100, unit_cost=2.10))
        db.add(PurchaseOrderItem(purchase_order_id=po1.id, product_id=products_data[1].id, quantity=150, unit_cost=0.70))
        db.add(PurchaseOrderItem(purchase_order_id=po2.id, product_id=products_data[9].id, quantity=50, unit_cost=2.80))

        # ── Employee Shifts ───────────────────────────────────────────────
        shifts = [
            EmployeeShift(user_id=cashier1.id, clock_in=now - timedelta(hours=8), clock_out=now - timedelta(hours=0.5), hourly_rate=18.00, performance_rating=4.5),
            EmployeeShift(user_id=cashier2.id, clock_in=now - timedelta(hours=6), clock_out=now - timedelta(hours=1), hourly_rate=17.50, performance_rating=4.2),
            EmployeeShift(user_id=cashier1.id, clock_in=now - timedelta(days=1, hours=8), clock_out=now - timedelta(days=1), hourly_rate=18.00, performance_rating=4.7),
        ]
        db.add_all(shifts)
        db.flush()

        # ── Simulated Historical Orders ───────────────────────────────────
        for i in range(30):
            day_offset = i % 20
            order_time = now - timedelta(days=day_offset, hours=(i % 10))
            subtotal = 0.0
            order = Order(
                user_id=customer1.id if i % 2 == 0 else customer2.id,
                subtotal=0,
                tax_rate=0.08,
                tax_amount=0,
                discount_amount=0,
                total_price=0,
                payment_method=PaymentMethod.card if i % 3 != 0 else PaymentMethod.cash,
                status=OrderStatus.completed,
                created_at=order_time,
                updated_at=order_time,
            )
            db.add(order)
            db.flush()

            # Add 2-4 random items per order
            item_count = (i % 3) + 2
            used_products = set()
            for j in range(item_count):
                idx = (i * 7 + j * 3) % len(products_data)
                if idx in used_products:
                    idx = (idx + 1) % len(products_data)
                used_products.add(idx)
                product = products_data[idx]
                qty = (j % 3) + 1
                line = qty * product.price
                subtotal += line
                db.add(OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=qty,
                    unit_price=product.price,
                ))

            tax = round(subtotal * 0.08, 2)
            order.subtotal = round(subtotal, 2)
            order.tax_amount = tax
            order.total_price = round(subtotal + tax, 2)

        db.commit()
        print("✅ Database seeded with demo data successfully.")
    except Exception as exc:
        db.rollback()
        print(f"⚠️  Seeding skipped or partially failed: {exc}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables
    Base.metadata.create_all(bind=engine)
    # Seed super-admin asynchronously
    from backend.database import init_db_seeding
    await init_db_seeding()
    # Seed remaining demo data
    _seed_database()
    yield
    # Cleanup (if needed)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="FreshMart Grocery Store Management System",
        description=(
            "Enterprise-grade grocery store management platform featuring "
            "multi-role authentication, POS, inventory, analytics, supplier management, "
            "employee scheduling, demand forecasting, and an integrated chatbot assistant."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routers ───────────────────────────────────────────────────────
    app.include_router(auth_router.router)
    app.include_router(users_router.router)
    app.include_router(products_router.router)
    app.include_router(orders_router.router)
    app.include_router(suppliers_router.router)
    app.include_router(employees_router.router)
    app.include_router(reports_router.router)
    app.include_router(warehouse_router.router)
    app.include_router(loyalty_router.router)
    app.include_router(forecast_router.router)
    app.include_router(chatbot_router.router)
    app.include_router(storefront_router.router)

    # ── Static frontend ───────────────────────────────────────────────────
    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    return app


app = create_app()
