from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
import hmac
import hashlib
import json

from server.database.database import get_db
from server.app.models.models import Device, Policy, AuditLog, BlockedApp, BlockedDomain
from server.app.schemas.schemas import HeartbeatRequest, PolicyUpdateRequest  # Giữ nguyên schema của bạn

router = APIRouter(tags=["Policies & Heartbeat"])

SECRET_KEY = "ogk_secure_secret_key_demo"

def compute_hmac(version: int, q_weekday: int, q_weekend: int, matrix_data: any) -> str:
    """Tính toán chữ ký HMAC toàn vẹn cho chính sách (F4)"""
    matrix_str = json.dumps(matrix_data, sort_keys=True) if isinstance(matrix_data, (list, dict)) else str(matrix_data)
    message = f"{version}-{q_weekday}-{q_weekend}-{matrix_str}"
    return hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()


# Lưu trữ thời gian sử dụng thực từ Agent gửi lên theo thời gian thực (F1, F3)
LIVE_DEVICE_METRICS = {}

@router.post("/api/heartbeat")
def heartbeat(data: HeartbeatRequest, db: Session = Depends(get_db)):
    """API Nhịp tim định kỳ (60s/lần) từ Agent - Áp dụng đúng chính sách của Phụ huynh đã ghép đôi"""
    device = db.query(Device).filter(Device.id == data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị chưa được ghép đôi")

    # Cập nhật thời gian online
    device.policy_version = data.current_policy_version
    device.last_seen = datetime.utcnow()
    device.status = "online"

    # Cập nhật live metrics vào RAM để API summary đọc tức thì
    LIVE_DEVICE_METRICS[data.device_id] = {
        "used_minutes": data.used_minutes or 0,
        "remaining_minutes": data.remaining_minutes,
        "bonus_minutes": data.bonus_minutes or 0,
        "updated_at": datetime.utcnow()
    }

    # Tìm chính sách mới nhất của ĐÚNG phụ huynh sở hữu thiết bị này
    latest_policy = None
    if device.parent_username:
        latest_policy = db.query(Policy).filter(Policy.parent_username == device.parent_username).order_by(Policy.version.desc()).first()
    
    # Nếu phụ huynh chưa tạo chính sách riêng hoặc thiết bị chưa gắn parent -> fallback về policy mặc định (version 1)
    if not latest_policy:
        latest_policy = db.query(Policy).filter((Policy.parent_username == None) | (Policy.version == 1)).order_by(Policy.version.asc()).first()
    if not latest_policy:
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
    """API Phụ huynh cập nhật Quota, Lịch tuần (7x48) - Chỉ áp dụng cho các con/thiết bị ĐÃ GHÉP ĐÔI với phụ huynh này (F4)"""
    latest_policy = db.query(Policy).order_by(Policy.version.desc()).first()
    new_version = (latest_policy.version + 1) if latest_policy else 1
    actor = data.actor_username or "parent_admin"

    # Đóng gói dữ liệu lịch và các khung giờ cấm linh hoạt
    policy_payload = {
        "schedule_matrix": data.schedule_json,
        "block_windows": [w.dict() for w in data.block_windows] if data.block_windows else [],
        "app_category_quotas": data.app_category_quotas or {}
    }
    payload_str = json.dumps(policy_payload)

    # Tính chữ ký HMAC bảo mật toàn vẹn (F4)
    sig = compute_hmac(new_version, data.quota_weekday, data.quota_weekend, payload_str)

    # Lưu policy mới gắn với đúng parent_username
    new_policy = Policy(
        version=new_version,
        parent_username=actor,
        quota_weekday=data.quota_weekday,
        quota_weekend=data.quota_weekend,
        schedule_matrix_json=payload_str,
        hmac_signature=sig
    )
    db.add(new_policy)

    # CHỈ CẬP NHẬT phiên bản cho các thiết bị THUỘC VỀ PHỤ HUYNH NÀY (Đã enroll)
    devices = db.query(Device).filter(Device.parent_username == actor).all()
    for dev in devices:
        dev.policy_version = new_version

    # Ghi nhật ký kiểm toán AuditLog (F4)
    client_ip = request.client.host if request.client else "127.0.0.1"
    old_summary = f"v{latest_policy.version}" if latest_policy else "None"
    new_summary = f"v{new_version} (W:{data.quota_weekday}/WE:{data.quota_weekend})"

    audit = AuditLog(
        actor_username=actor,
        ip_address=client_ip,
        action="UPDATE_POLICY_F1_F4",
        old_value=old_summary,
        new_value=new_summary
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "message": f"Đã phát hành chính sách phiên bản v{new_version} cho {len(devices)} thiết bị đã kết nối của bạn!",
        "new_version": new_version,
        "affected_devices": len(devices),
        "hmac_signature": sig
    }


@router.get("/api/policy/download/{version}")
def download_policy(version: int, device_id: Optional[str] = None, db: Session = Depends(get_db)):
    """API để Agent tải chi tiết nội dung Policy kèm chữ ký HMAC xác thực chống giả mạo (F1, F4, F2)"""
    policy = db.query(Policy).filter(Policy.version == version).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên bản chính sách")
    
    if device_id and isinstance(device_id, str):
        device = db.query(Device).filter(Device.id == device_id).first()
        if device:
            device.policy_version = version
            device.last_seen = datetime.utcnow()
            db.commit()

    # Parse lại schedule_json để trả về dạng mảng/ma trận cho Agent nếu cần
    schedule_output = policy.schedule_matrix_json
    try:
        schedule_output = json.loads(policy.schedule_matrix_json)
    except:
        pass

    # Lấy danh sách blocked_apps và blocked_domains hiện hành để Agent tải về (F2)
    blocked_apps_records = db.query(BlockedApp).all()
    blocked_domains_records = db.query(BlockedDomain).all()

    blocked_apps = [{"process_name": a.process_name, "file_hash": a.file_hash} for a in blocked_apps_records]
    blocked_domains = [{"domain": d.domain, "category": d.category} for d in blocked_domains_records]

    return {
        "version": policy.version,
        "quota_weekday": policy.quota_weekday,
        "quota_weekend": policy.quota_weekend,
        "schedule_json": schedule_output,
        "schedule_matrix_json": policy.schedule_matrix_json,
        "blocked_apps": blocked_apps,
        "blocked_domains": blocked_domains,
        "hmac_signature": getattr(policy, "hmac_signature", "")
    }


@router.get("/api/audit-logs")
def get_audit_logs(
    parent_username: Optional[str] = None, 
    limit: int = 50, 
    db: Session = Depends(get_db)
):
    """
    API Lấy nhật ký kiểm toán thay đổi luật (F4 BẮT BUỘC, Nguyên tắc NT5 Minh bạch hai chiều):
    Ai, lúc nào, từ địa chỉ IP nào, giá trị cũ và mới. Trẻ được quyền xem nhật ký này.
    """
    query = db.query(AuditLog)
    if parent_username:
        query = query.filter(AuditLog.actor_username == parent_username)
    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    return [
        {
            "id": l.id,
            "timestamp": l.timestamp.strftime("%d/%m/%Y %H:%M:%S") if l.timestamp else "",
            "actor": l.actor_username,
            "ip_address": l.ip_address,
            "action": l.action,
            "old_value": l.old_value or "",
            "new_value": l.new_value or ""
        }
        for l in logs
    ]