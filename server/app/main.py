import os
import sys
from typing import Optional

# Tắt Cython C-extension của SQLAlchemy để tránh bị Windows Application Control chặn DLL
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

# Thêm root directory vào sys.path để import các module dễ dàng
SYS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if SYS_ROOT not in sys.path:
    sys.path.insert(0, SYS_ROOT)

from fastapi import FastAPI, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from server.database.database import Base, engine, get_db
from server.app.models.models import Device, Policy, AuditLog
from server.app.api.auth import router as auth_router
from server.app.api.devices import router as devices_router
from server.app.api.policies import router as policies_router
from server.app.api import events, reports, requests_ws
from server.app.api import domains
from server.app.api import apps


# Tự động khởi tạo bảng CSDL khi khởi chạy
Base.metadata.create_all(bind=engine)

app = FastAPI(title="OpenGuardKids Server", version="2.0")

# Cấu hình Thư mục Tĩnh (Static Files: CSS, Images, Icons)
STATIC_DIR = os.path.join(SYS_ROOT, "server", "static")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "images"), exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Cấu hình Templates
TEMPLATES_DIR = os.path.join(SYS_ROOT, "server", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Register API Routers
app.include_router(auth_router)
app.include_router(devices_router)
app.include_router(policies_router)
app.include_router(events.router)
app.include_router(reports.router)
app.include_router(requests_ws.router)
app.include_router(domains.router)
app.include_router(apps.router)
@app.on_event("startup")
def startup_event():
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=WAL;")
    
    # Tác vụ tự động dọn dẹp các sự kiện cũ quá 90 ngày theo Nghị định 13/2023
    try:
        from datetime import datetime, timedelta
        from server.app.models.models import Event
        with engine.connect() as conn:
            cutoff = datetime.utcnow() - timedelta(days=90)
            with Session(engine) as s:
                del_count = s.query(Event).filter(Event.ts < cutoff).delete()
                s.commit()
                if del_count > 0:
                    print(f"[Privacy] Đã tự động dọn dẹp {del_count} bản ghi sự kiện cũ hơn 90 ngày.")
    except Exception as e:
        print(f"[Privacy] Lỗi kiểm tra dọn dẹp dữ liệu 90 ngày: {e}")

# Routes HTML cho Frontend
@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
def page_login(request: Request):
    """Trang Đăng Nhập Chung (Phụ huynh & Trẻ em)"""
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/dashboard", response_class=HTMLResponse)
def page_parent_dashboard(request: Request, username: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Trang Dashboard Quản Lý dành cho Phụ Huynh"""
    query = db.query(Device)
    latest_policy = None
    if username and hasattr(Device, "parent_username"):
        devices = query.filter(Device.parent_username == username).all()
        recent_audits = db.query(AuditLog).filter(AuditLog.actor_username == username).order_by(AuditLog.timestamp.desc()).limit(10).all()
        # Tìm chính sách của riêng phụ huynh này
        latest_policy = db.query(Policy).filter(Policy.parent_username == username).order_by(Policy.version.desc()).first()
    else:
        # Không có username chỉ định -> không trả dữ liệu thiết bị của người khác
        devices = []
        recent_audits = []

    # Nếu phụ huynh mới chưa sửa chính sách -> dùng chính sách mặc định v1
    if not latest_policy:
        latest_policy = db.query(Policy).filter((Policy.parent_username == None) | (Policy.version == 1)).order_by(Policy.version.asc()).first()
    if not latest_policy:
        latest_policy = db.query(Policy).order_by(Policy.version.desc()).first()

    return templates.TemplateResponse(
        request=request, 
        name="parent_dashboard.html", 
        context={
            "devices": devices, 
            "latest_policy": latest_policy,
            "recent_audits": recent_audits,
            "parent_username": username or ""
        }
    )

@app.get("/child-screen", response_class=HTMLResponse)
def page_child_screen(
    request: Request, 
    child_name: Optional[str] = Query(None), 
    username: Optional[str] = Query(None), 
    db: Session = Depends(get_db)
):
    """Màn hình Minh Bạch dành cho Trẻ em (NT1, NT5)"""
    from server.app.models.models import User
    child_user = None
    if username:
        child_user = db.query(User).filter(User.username == username).first()
    elif child_name and child_name != "None":
        child_user = db.query(User).filter((User.child_name == child_name) | (User.username == child_name)).first()

    device = None
    paired_parent_username = None
    if child_user:
        device = db.query(Device).filter(Device.child_id == child_user.id).first()
        if device:
            paired_parent_username = device.parent_username
        display_name = child_user.child_name or child_user.username
    else:
        display_name = child_name if child_name and child_name != "None" else "Bạn"

    # Chính sách hiển thị cho trẻ:
    # 1. Nếu ĐÃ ENROLL với phụ huynh -> Lấy chính sách của ĐÚNG phụ huynh đó
    # 2. Nếu CHƯA ENROLL -> Lấy chính sách an toàn mặc định (v1), không bị ảnh hưởng bởi phụ huynh khác
    latest_policy = None
    if paired_parent_username:
        latest_policy = db.query(Policy).filter(Policy.parent_username == paired_parent_username).order_by(Policy.version.desc()).first()

    if not latest_policy:
        latest_policy = db.query(Policy).filter((Policy.parent_username == None) | (Policy.version == 1)).order_by(Policy.version.asc()).first()
    if not latest_policy:
        latest_policy = db.query(Policy).order_by(Policy.version.desc()).first()

    return templates.TemplateResponse(
        request=request, 
        name="child_transparent.html", 
        context={
            "latest_policy": latest_policy,
            "child_name": display_name,
            "child_username": child_user.username if child_user else (username or ""),
            "child_id": child_user.id if child_user else None,
            "is_paired": (device is not None),
            "paired_device": device,
            "paired_parent_username": paired_parent_username or ""
        }
    )