from sqlalchemy import Column, String, Integer, DateTime, Text
from datetime import datetime
from database import Base

class DeviceModel(Base):
    __tablename__ = "devices"

    device_id = Column(String, primary_key=True, index=True)
    device_name = Column(String, nullable=False)
    child_name = Column(String, nullable=False)
    policy_version = Column(Integer, default=1)
    last_seen = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="offline")

class PolicyModel(Base):
    __tablename__ = "policies"

    policy_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    version = Column(Integer, unique=True, nullable=False)
    content_json = Column(Text, nullable=False) 
    created_at = Column(DateTime, default=datetime.utcnow)

class EventModel(Base):
    __tablename__ = "events"

    event_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String, index=True)
    event_type = Column(String)
    subject = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)