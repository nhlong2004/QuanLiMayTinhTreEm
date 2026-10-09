from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
import hmac
import hashlib
import json

from server.database.database import get_db
from server.app.models.models import Device, Policy, AuditLog
from server.app.schemas.schemas import HeartbeatRequest, PolicyUpdateRequest  # Giữ nguyên schema của bạn

router = APIRouter(tags=["Policies & Heartbeat"])

SECRET_KEY = "ogk_secure_secret_key_demo"

def compute_hmac(version: int, q_weekday: int, q_weekend: int, matrix_data: any) -> str:
    """Tính toán chữ ký HMAC toàn vẹn cho chính sách (F4)"""
    matrix_str = json.dumps(matrix_data) if isinstance(matrix_data, (list, dict)) else str(matrix_data)
    message = f"{version}-{q_weekday}-{q_weekend}-{matrix_str}"
    return hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()


@router.post("/api/heartbeat")
def heartbeat(data: HeartbeatRequest, db: Session = Depends(get_db)):
    """API Nhịp tim định kỳ (60s/lần) từ Agent"""
    device = db.query(Device).filter(Device.id == data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị chưa được ghép đôi")

    # Cập nhật phiên bản policy và thời gian online
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
def update_policy(data: PolicyUpdateRequest, request: Request, db: Session = Depends(get_db)):
    """API Phụ huynh cập nhật Quota, Lịch tuần (7x48) và phát hành Policy mới kèm HMAC & AuditLog (F1, F4)"""
    latest_policy = db.query(Policy).order_by(Policy.version.desc()).first()
    new_version = (latest_policy.version + 1) if latest_policy else 1

    # Đóng gói dữ liệu lịch và các khung giờ cấm linh hoạt
    policy_payload = {
        "schedule_matrix": data.schedule_json,
        "block_windows": [w.dict() for w in data.block_windows] if data.block_windows else []
    }
    payload_str = json.dumps(policy_payload)

    # Tính chữ ký HMAC bảo mật toàn vẹn (F4)
    sig = compute_hmac(new_version, data.quota_weekday, data.quota_weekend, payload_str)

    # Lưu policy mới
    new_policy = Policy(
        version=new_version,
        quota_weekday=data.quota_weekday,
        quota_weekend=data.quota_weekend,
        schedule_json=payload_str,
        hmac_signature=sig  # Lưu ý đảm bảo bảng Policy trong models.py có cột này
    )
    db.add(new_policy)
    
    # Đồng bộ ngay phiên bản mới nhất cho tất cả thiết bị
    devices = db.query(Device).all()
    for dev in devices:
        dev.policy_version = new_version

    # Ghi nhật ký kiểm toán AuditLog (F4)
    client_ip = request.client.host if request.client else "127.0.0.1"
    old_summary = f"v{latest_policy.version}" if latest_policy else "None"
    new_summary = f"v{new_version} (W:{data.quota_weekday}/WE:{data.quota_weekend})"

    audit = AuditLog(
        actor_username="parent_admin",
        ip_address=client_ip,
        action="UPDATE_POLICY_F1_F4",
        old_value=old_summary,
        new_value=new_summary
    )
    db.add(audit)
    db.commit()
    
    return {
        "status": "success",
        "message": f"Đã phát hành chính sách phiên bản v{new_version}",
        "new_version": new_version,
        "hmac_signature": sig
    }


@router.get("/api/policy/download/{version}")
def download_policy(version: int, device_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """API để Agent tải chi tiết nội dung Policy kèm chữ ký HMAC xác thực chống giả mạo (F1, F4)"""
    policy = db.query(Policy).filter(Policy.version == version).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên bản chính sách")
    
    if device_id:
        device = db.query(Device).filter(Device.id == device_id).first()
        if device:
            device.policy_version = version
            device.last_seen = datetime.utcnow()
            db.commit()

    # Parse lại schedule_json để trả về dạng mảng/ma trận cho Agent nếu cần
    schedule_output = policy.schedule_json
    try:
        schedule_output = json.loads(policy.schedule_json)
    except:
        pass

    return {
        "version": policy.version,
        "quota_weekday": policy.quota_weekday,
        "quota_weekend": policy.quota_weekend,
        "schedule_json": schedule_output,
        "hmac_signature": getattr(policy, "hmac_signature", "")  # Trả về chữ ký HMAC cho Agent kiểm tra
    }