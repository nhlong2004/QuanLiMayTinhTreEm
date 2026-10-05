from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str  # 'parent' or 'child'
    child_name: Optional[str] = None

class GenerateCodeRequest(BaseModel):
    child_username: str
    parent_username: Optional[str] = None

class EnrollRequest(BaseModel):
    enroll_code: str
    device_name: str
    device_id: Optional[str] = None

class HeartbeatRequest(BaseModel):
    device_id: str
    current_policy_version: int

class PolicyUpdateRequest(BaseModel):
    quota_weekday: int
    quota_weekend: int
    schedule_json: str
