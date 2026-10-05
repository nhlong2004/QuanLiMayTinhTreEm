from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
from server.database.database import get_db
from server.app.models.models import Device, Policy
from server.app.schemas.schemas import HeartbeatRequest, PolicyUpdateRequest

router = APIRouter(tags=["Policies & Heartbeat"])

@router.post("/api/heartbeat")
def heartbeat(data: HeartbeatRequest, db: Session = Depends(get_db)):
    """API Nhịp tim định kỳ (60s/lần) từ Agent"""
    device = db.query(Device).filter(Device.id == data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị chưa được ghép đôi")

    # Cập nhật phiên bản policy mà máy con đang thực sự áp dụng và thời gian online
    device.policy_version = data.current_policy_version
    device.last_seen = datetime.utcnow()
    device.status = "online"
    
    latest_policy = db.query(Policy).order_by(Policy.version.desc()).first()
    latest_version = latest_policy.version if latest_policy else 1

    db.commit()

    update_required = data.current_policy_version < latest_version
    return {
        "status": "active",
        "server_time": datetime.utcnow().isoformat(),
        "update_policy_required": update_required,
        "latest_policy_version": latest_version
    }

@router.post("/api/policy/update")
def update_policy(data: PolicyUpdateRequest, db: Session = Depends(get_db)):
    """API Phụ huynh cập nhật Quota, Lịch tuần và phát hành Policy mới (F1, F4)"""
    latest_policy = db.query(Policy).order_by(Policy.version.desc()).first()
    new_version = (latest_policy.version + 1) if latest_policy else 1

    new_policy = Policy(
        version=new_version,
        quota_weekday=data.quota_weekday,
        quota_weekend=data.quota_weekend,
        schedule_json=data.schedule_json
    )
    db.add(new_policy)
    
    # Đồng bộ ngay phiên bản mới nhất cho tất cả thiết bị
    devices = db.query(Device).all()
    for dev in devices:
        dev.policy_version = new_version

    db.commit()
    
    return {
        "status": "success",
        "message": f"Đã phát hành chính sách phiên bản v{new_version}",
        "new_version": new_version
    }

@router.get("/api/policy/download/{version}")
def download_policy(version: int, device_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """API để Agent tải chi tiết nội dung Policy và cập nhật trạng thái đồng bộ (F1)"""
    policy = db.query(Policy).filter(Policy.version == version).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên bản chính sách")
    
    if device_id:
        device = db.query(Device).filter(Device.id == device_id).first()
        if device:
            device.policy_version = version
            device.last_seen = datetime.utcnow()
            db.commit()

    return {
        "version": policy.version,
        "quota_weekday": policy.quota_weekday,
        "quota_weekend": policy.quota_weekend,
        "schedule_json": policy.schedule_json
    }
