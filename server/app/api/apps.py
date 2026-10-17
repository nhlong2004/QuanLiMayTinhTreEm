import os
import sys
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from server.database.database import get_db
from server.app.models.models import BlockedApp, BlockedDomain, Policy, Device
from server.app.api.policies import compute_hmac

router = APIRouter(prefix="/api/apps", tags=["Blocked Apps Management"])

class AppCreateRequest(BaseModel):
    process_name: str
    file_hash: Optional[str] = None

def sync_policy_to_agent_and_db(db: Session, parent_username: str = None):
    latest_policy = db.query(Policy).order_by(Policy.version.desc()).first()
    new_version = (latest_policy.version + 1) if latest_policy else 1
    actor = parent_username or (latest_policy.parent_username if latest_policy else "parent_admin")
    quota_weekday = latest_policy.quota_weekday if latest_policy else 90
    quota_weekend = latest_policy.quota_weekend if latest_policy else 120
    schedule_str = latest_policy.schedule_matrix_json if latest_policy else "{}"
    sig = compute_hmac(new_version, quota_weekday, quota_weekend, schedule_str)

    new_policy = Policy(
        version=new_version,
        parent_username=actor,
        quota_weekday=quota_weekday,
        quota_weekend=quota_weekend,
        schedule_matrix_json=schedule_str,
        hmac_signature=sig
    )
    db.add(new_policy)

    # Chỉ cập nhật devices thuộc phụ huynh hiện tại (không ảnh hưởng phụ huynh khác)
    if actor:
        devices = db.query(Device).filter(Device.parent_username == actor).all()
    else:
        devices = db.query(Device).all()
    for dev in devices:
        dev.policy_version = new_version
    db.commit()

    # Cập nhật agent/config.json trên máy dev để phản hồi tức thì
    try:
        agent_cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../agent/config.json"))
        if os.path.exists(agent_cfg_path):
            with open(agent_cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)

            blocked_apps = [{"process_name": a.process_name, "file_hash": a.file_hash} for a in db.query(BlockedApp).all()]
            blocked_domains = [{"domain": d.domain, "category": d.category} for d in db.query(BlockedDomain).all()]

            cfg["policy_version"] = new_version
            if "policy_details" not in cfg:
                cfg["policy_details"] = {}
            cfg["policy_details"]["version"] = new_version
            cfg["policy_details"]["blocked_apps"] = blocked_apps
            cfg["policy_details"]["blocked_domains"] = blocked_domains
            cfg["policy_details"]["hmac_signature"] = sig

            with open(agent_cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

@router.get("/")
def get_blocked_apps(db: Session = Depends(get_db)):
    return db.query(BlockedApp).all()

@router.post("/")
def add_blocked_app(data: AppCreateRequest, parent_username: Optional[str] = Query(None), db: Session = Depends(get_db)):
    # Chuẩn hóa tên tiến trình (chuyển chữ thường)
    proc_name = data.process_name.strip().lower()
    existing = db.query(BlockedApp).filter(BlockedApp.process_name == proc_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ứng dụng này đã có trong danh sách chặn.")

    new_app = BlockedApp(process_name=proc_name, file_hash=data.file_hash)
    db.add(new_app)
    db.commit()

    sync_policy_to_agent_and_db(db, parent_username=parent_username)

    return {"status": "success", "message": f"Đã chặn ứng dụng {proc_name}"}

@router.delete("/{app_id}")
def delete_blocked_app(app_id: int, parent_username: Optional[str] = Query(None), db: Session = Depends(get_db)):
    app_item = db.query(BlockedApp).filter(BlockedApp.id == app_id).first()
    if not app_item:
        raise HTTPException(status_code=404, detail="Không tìm thấy ứng dụng.")
    db.delete(app_item)
    db.commit()

    sync_policy_to_agent_and_db(db, parent_username=parent_username)

    return {"status": "success", "message": "Đã xóa ứng dụng khỏi danh sách chặn."}