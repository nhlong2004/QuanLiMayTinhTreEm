from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

DATABASE_URL = "sqlite:///./ogk_server.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    child_name = Column(String(100), nullable=True)

class Device(Base):
    __tablename__ = "devices"
    id = Column(String(50), primary_key=True, index=True) 
    device_name = Column(String(100), nullable=False)
    child_name = Column(String(100), nullable=False)
    policy_version = Column(Integer, default=1)
    last_seen = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="offline")

class Policy(Base):
    __tablename__ = "policies"
    id = Column(Integer, primary_key=True, index=True)
    version = Column(Integer, unique=True, nullable=False)
    quota_weekday = Column(Integer, default=90)  
    quota_weekend = Column(Integer, default=120) 
    schedule_json = Column(Text, nullable=True)   
    created_at = Column(DateTime, default=datetime.utcnow)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(50), ForeignKey("devices.id"))
    event_type = Column(String(50), nullable=False)
    payload = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OGK Server", version="2.0")
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=WAL;")

class EnrollRequest(BaseModel):
    device_id: str
    device_name: str
    child_name: str

class HeartbeatRequest(BaseModel):
    device_id: str
    current_policy_version: int

class LoginRequest(BaseModel):
    username: str
    password: str

class PolicyUpdateRequest(BaseModel):
    quota_weekday: int
    quota_weekend: int
    schedule_json: str



@app.get("/", response_class=HTMLResponse)
def read_dashboard(request: Request, db: Session = Depends(get_db)):
    """Giao diện Dashboard Quản lý Phụ huynh (Phase 01 & 02)"""
    devices = db.query(Device).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "devices": devices})

@app.post("/auth/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """API Đăng nhập phân quyền cho Phụ huynh và Trẻ em"""
    user = db.query(User).filter(User.username == data.username).first()
    if not user or user.password_hash != data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác"
        )
    
    if user.role == "parent":
        return {
            "access_token": f"token-parent-{user.username}",
            "role": "parent",
            "redirect_url": "/dashboard"
        }
    elif user.role == "child":
        return {
            "access_token": f"token-child-{user.username}",
            "role": "child",
            "child_name": user.child_name,
            "redirect_url": "/child-screen"
        }
    
    raise HTTPException(status_code=400, detail="Vai trò hệ thống không hợp lệ")

@app.post("/auth/enroll")
def enroll_device(data: EnrollRequest, db: Session = Depends(get_db)):
    """API Ghép đôi thiết bị từ Agent"""
    device = db.query(Device).filter(Device.id == data.device_id).first()
    latest_policy = db.query(Policy).order_by(Policy.version.desc()).first()
    current_version = latest_policy.version if latest_policy else 1

    if device:
        device.device_name = data.device_name
        device.child_name = data.child_name
        device.status = "online"
        device.last_seen = datetime.utcnow()
    else:
        device = Device(
            id=data.device_id,
            device_name=data.device_name,
            child_name=data.child_name,
            policy_version=current_version,
            status="online",
            last_seen=datetime.utcnow()
        )
        db.add(device)
    
    db.commit()
    return {
        "status": "success",
        "message": "Ghép đôi thiết bị thành công",
        "policy_version": current_version
    }

@app.post("/api/heartbeat")
def heartbeat(data: HeartbeatRequest, db: Session = Depends(get_db)):
    """API Nhịp tim định kỳ (60s/lần) từ Agent"""
    device = db.query(Device).filter(Device.id == data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị chưa được ghép đôi")

    device.last_seen = datetime.utcnow()
    device.status = "online"
    
    latest_policy = db.query(Policy).order_by(Policy.version.desc()).first()
    latest_version = latest_policy.version if latest_policy else 1

    db.commit()

    update_required = data.current_policy_version < latest_version
    return {
        "status": "active",
        "server_time": datetime.utcnow().isoformat(),
        "update_required": update_required,
        "latest_policy_version": latest_version
    }

@app.post("/api/policy/update")
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
    db.commit()
    
    return {
        "status": "success",
        "message": f"Đã phát hành chính sách phiên bản v{new_version}",
        "new_version": new_version
    }

@app.get("/api/policy/download/{version}")
def download_policy(version: int, db: Session = Depends(get_db)):
    """API để Agent tải chi tiết nội dung Policy (F1)"""
    policy = db.query(Policy).filter(Policy.version == version).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên bản chính sách")
    
    return {
        "version": policy.version,
        "quota_weekday": policy.quota_weekday,
        "quota_weekend": policy.quota_weekend,
        "schedule_json": policy.schedule_json
    }
