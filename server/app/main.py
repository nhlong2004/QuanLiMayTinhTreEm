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
    if username and hasattr(Device, "parent_username"):
        devices = query.filter(Device.parent_username == username).all()
    else:
        devices = query.all()

    latest_policy = db.query(Policy).order_by(Policy.version.desc()).first()
    recent_audits = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10).all()

    return templates.TemplateResponse(
        request=request, 
        name="parent_dashboard.html", 
        context={
            "devices": devices, 
            "latest_policy": latest_policy,
            "recent_audits": recent_audits,
            "parent_username": username or "Phụ huynh"
        }
    )

@app.get("/child-screen", response_class=HTMLResponse)
def page_child_screen(request: Request, child_name: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Màn hình Minh Bạch dành cho Trẻ em (NT1, NT5)"""
    latest_policy = db.query(Policy).order_by(Policy.version.desc()).first()
    display_name = child_name if child_name and child_name != "None" else "Bạn"
    return templates.TemplateResponse(
        request=request, 
        name="child_transparent.html", 
        context={
            "latest_policy": latest_policy,
            "child_name": display_name
        }
    )