from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from datetime import datetime
from server.database.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'parent' or 'child'
    child_name = Column(String(100), nullable=True) 

class Device(Base):
    __tablename__ = "devices"
    id = Column(String(50), primary_key=True, index=True) 
    device_name = Column(String(100), nullable=False)
    child_name = Column(String(100), nullable=False)
    parent_username = Column(String(50), nullable=True)  # Gắn với Phụ huynh sở hữu
    policy_version = Column(Integer, default=1)
    last_seen = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="offline")

class EnrollCode(Base):
    __tablename__ = "enroll_codes"
    code = Column(String(10), primary_key=True, index=True)
    child_username = Column(String(50), nullable=False)  # Tên đăng nhập duy nhất của trẻ
    parent_username = Column(String(50), nullable=True)  # Phụ huynh tạo mã này
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)

class Policy(Base):
    __tablename__ = "policies"
    id = Column(Integer, primary_key=True, index=True)
    version = Column(Integer, unique=True, nullable=False)
    quota_weekday = Column(Integer, default=90)   # Phút/ngày
    quota_weekend = Column(Integer, default=120)  # Phút/ngày
    schedule_json = Column(Text, nullable=True)   # Cấu hình giờ cấm / cho phép
    created_at = Column(DateTime, default=datetime.utcnow)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(50), ForeignKey("devices.id"))
    event_type = Column(String(50), nullable=False)
    payload = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
