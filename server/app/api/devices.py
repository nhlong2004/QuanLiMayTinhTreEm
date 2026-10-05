from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session
from server.database.database import get_db
from server.app.models.models import Device

router = APIRouter(prefix="/api/devices", tags=["Devices"])

@router.get("")
def list_devices(parent_username: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Danh sách các thiết bị thuộc sở hữu của Phụ huynh"""
    query = db.query(Device)
    if parent_username:
        query = query.filter(
            (Device.parent_username == parent_username) | (Device.parent_username.is_(None))
        )
    return query.all()
