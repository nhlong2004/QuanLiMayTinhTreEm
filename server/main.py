from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid

import models
import schemas
from database import engine, get_db

# Tạo bảng trong SQLite nếu chưa tồn tại
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="OGK Server", version="1.0.0")
templates = Jinja2Templates(directory="templates")

# 1. API Ghép đôi thiết bị (/auth/enroll) - Tuân thủ Nghị định 13/2023[cite: 1, 2]
@app.post("/auth/enroll")
def enroll_device(payload: schemas.EnrollRequest, db: Session = Depends(get_db)):
    # Trong thực tế phase 1, kiểm tra mã ghép đôi 8 ký tự (giả lập mã hợp lệ là "OGK2026X")
    if payload.enroll_code != "OGK2026X":
        raise HTTPException(status_code=400, detail="Mã ghép đôi không hợp lệ hoặc đã hết hạn (10 phút).")
    
    generated_device_id = str(uuid.uuid4())
    
    new_device = models.DeviceModel(
        device_id=generated_device_id,
        device_name=payload.device_name,
        child_name=payload.child_name,
        policy_version=1,
        last_seen=datetime.utcnow(),
        status="online"
    )
    db.add(new_device)
    db.commit()
    
    return {
        "status": "success",
        "device_id": generated_device_id,
        "access_token": f"token_{generated_device_id[:8]}",
        "policy_version": 1
    }

# 2. API Nhận nhịp tim định kỳ 60 giây từ Agent[cite: 1, 2]
@app.post("/api/heartbeat")
def receive_heartbeat(payload: schemas.HeartbeatRequest, db: Session = Depends(get_db)):
    device = db.query(models.DeviceModel).filter(models.DeviceModel.device_id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị.")
    
    # Cập nhật trạng thái và thời gian nhận nhịp tim gần nhất
    device.last_seen = datetime.utcnow()
    device.status = "online"
    db.commit()

    # Kiểm tra so sánh phiên bản chính sách (policy_version)[cite: 2]
    SERVER_LATEST_POLICY_VERSION = 1  # Giả định phiên bản mới nhất trên server là 1
    update_required = payload.policy_version < SERVER_LATEST_POLICY_VERSION

    return {
        "status": "ack",
        "server_time": datetime.utcnow().isoformat(),
        "update_policy_required": update_required,
        "latest_policy_version": SERVER_LATEST_POLICY_VERSION
    }

# 3. Giao diện Dashboard Phụ huynh (Jinja2) hiển thị trạng thái kết nối[cite: 2]
@app.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request, db: Session = Depends(get_db)):
    # Tự động chuyển trạng thái sang offline nếu quá 90 giây không nhận được heartbeat
    devices = db.query(models.DeviceModel).all()
    now = datetime.utcnow()
    for d in devices:
        if (now - d.last_seen).total_seconds() > 90:
            d.status = "offline"
    db.commit()

    return templates.TemplateResponse("dashboard.html", {"request": request, "devices": devices})