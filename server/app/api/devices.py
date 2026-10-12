from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session

from server.app.models.models import Device, User
from server.database.database import get_db
router = APIRouter(prefix="/api/devices", tags=["Devices"])

@router.get("")
def list_devices(
    parent_username: Optional[str] = Query(None),
    child_username: Optional[str] = Query(None),
    child_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Danh sách các thiết bị thuộc quản lý của Phụ huynh hoặc Trẻ em"""
    query = db.query(Device)
    
    if parent_username:
        query = query.filter(Device.parent_username == parent_username)
    if child_id:
        query = query.filter(Device.child_id == child_id)
    if child_username:
        query = query.join(User, Device.child_id == User.id).filter(User.username == child_username)
        
    return query.all()