import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'parent' hoặc 'child'
    child_name = Column(String(100), nullable=True)

    devices = relationship("Device", back_populates="owner_child")

class Device(Base):
    __tablename__ = "devices"
    id = Column(String(36), primary_key=True)  # UUID
    device_name = Column(String(100), nullable=False)
    child_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    policy_version = Column(Integer, default=1)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(20), default="offline")

    owner_child = relationship("User", back_populates="devices")

class Policy(Base):
    __tablename__ = "policies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(Integer, unique=True, nullable=False)
    quota_weekday = Column(Integer, default=90)  # Phút mặc định ngày thường
    quota_weekend = Column(Integer, default=120) # Phút mặc định cuối tuần
    # Ma trận lịch tuần 7x48 (7 ngày x 48 block 30 phút), lưu dưới dạng chuỗi JSON ma trận hoặc chuỗi bit
    schedule_matrix_json = Column(Text, nullable=False) 
    hmac_signature = Column(String(64), nullable=False) # Chữ ký toàn vẹn chính sách (F4)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    actor_username = Column(String(50), nullable=False) # Ai thực hiện (F4)
    ip_address = Column(String(45), nullable=False)      # Từ địa chỉ IP nào (F4)
    action = Column(String(100), nullable=False)         # Hành động (VD: UPDATE_POLICY, EMERGENCY_LOCK)
    old_value = Column(Text, nullable=True)              # Giá trị cũ (F4)
    new_value = Column(Text, nullable=True)              # Giá trị mới (F4)


class EnrollCode(Base):
    __tablename__ = "enroll_codes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, index=True, nullable=False)
    child_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False)
    child_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False) # app_start, app_stop, blocked_app, quota_warning, locked, unlock_request...
    subject = Column(String(255), nullable=True)
    duration_sec = Column(Integer, default=0)
    policy_id = Column(Integer, nullable=True)

class BlockedApp(Base):
    __tablename__ = "blocked_apps"
    id = Column(Integer, primary_key=True, autoincrement=True)
    process_name = Column(String(100), nullable=False)
    file_hash = Column(String(64), nullable=True) # SHA-256

class BlockedDomain(Base):
    __tablename__ = "blocked_domains"
    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), nullable=False)
    category = Column(String(50), default="Chưa phân loại") # Giáo dục, Giải trí, Mạng xã hội, Trò chơi, Không phù hợp

class ChildRequest(Base):
    __tablename__ = "child_requests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    request_type = Column(String(50), nullable=False) # "extra_time", "unblock_app"
    content = Column(String(255), nullable=False)
    status = Column(String(20), default="pending") # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.datetime.utcnow)