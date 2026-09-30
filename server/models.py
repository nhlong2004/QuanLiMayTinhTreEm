from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

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