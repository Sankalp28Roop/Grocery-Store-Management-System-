"""
database.py — SQLAlchemy async engine, session factory, and Base class.

All ORM models inherit from Base. Sessions are provided via the
get_db() dependency injected into FastAPI route handlers.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'grocery_store.db'}")

# ---------------------------------------------------------------------------
# Engine — SQLite with WAL mode and foreign key enforcement
# ---------------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI threads
    echo=False,  # Set True for SQL debug output
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    """Enable WAL mode and foreign key support on every new connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.close()


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db():
    """
    Yield a database session and guarantee it is closed after the request,
    even if an exception is raised.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Seeding & Admin Configuration Fallbacks
# ---------------------------------------------------------------------------
ADMIN_NAME = os.getenv("ADMIN_NAME", "Sankalp Swarup")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "sankalp.swarup@grocerymania.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_ROLE = os.getenv("ADMIN_ROLE", "admin")


async def init_db_seeding() -> None:
    """
    Asynchronously initialize database schema seeding.
    Checks if an administrator account already exists. If not, it programmatically
    inserts the initial, permanent operational super-administrator record.
    """
    from backend.models import User, UserRole
    from backend.auth import hash_password

    db = SessionLocal()
    try:
        # Check if an administrator already exists
        admin_exists = db.query(User).filter(User.role == UserRole.admin).first()

        if not admin_exists:
            super_admin = User(
                name=ADMIN_NAME,
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                role=UserRole.admin,
                is_active=True,
            )
            db.add(super_admin)
            db.commit()
            print(f"Database Initialization Complete: Dynamic Admin Account Created for {ADMIN_NAME}.")
    except Exception as exc:
        db.rollback()
        print(f"⚠️  Database initialization seeding failed: {exc}")
    finally:
        db.close()

