from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session

from server.app.models.models import Device, User
from server.database.database import get_db
router = APIRouter(prefix="/api/devices", tags=["Devices"])

@router.get("")
def list_devices(parent_username: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Danh sách các thiết bị thuộc quản lý của Phụ huynh"""
    query = db.query(Device)
    
    # Nếu có lọc theo parent_username, ta join sang bảng User (child) hoặc kiểm tra qua quan hệ
    if parent_username:
        # Lọc các thiết bị mà đứa trẻ thuộc quản lý của phụ huynh này (hoặc chưa gán)
        # Tùy thuộc vào cách bạn thiết kế quan hệ, ở đây ta join với User
        query = query.join(Device.owner_child).filter(
            (User.username == parent_username) | (Device.child_id.is_(None))
        )
        
    return query.all()