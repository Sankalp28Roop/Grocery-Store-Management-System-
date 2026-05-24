"""
routers/storefront.py — Dynamic storefront configuration loaded from database records.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import StorefrontSetting

router = APIRouter(prefix="/api/storefront", tags=["Storefront"])


@router.get("/config")
def get_storefront_config(db: Session = Depends(get_db)):
    """Fetch dynamic B2C storefront configurations directly from database records."""
    hero_setting = db.query(StorefrontSetting).filter(StorefrontSetting.key == "storefront_hero").first()
    promos_setting = db.query(StorefrontSetting).filter(StorefrontSetting.key == "storefront_promos").first()
    info_setting = db.query(StorefrontSetting).filter(StorefrontSetting.key == "storefront_info").first()

    return {
        "hero": hero_setting.value if hero_setting else [],
        "promos": promos_setting.value if promos_setting else [],
        "info": info_setting.value if info_setting else {}
    }
