from pydantic import BaseModel
from typing import Optional, List,Any, Dict

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
class BlockWindow(BaseModel):
    start: str  # Ví dụ: "22:00" hoặc "11:00"
    end: str    # Ví dụ: "06:00" hoặc "13:00"

class PolicyUpdateRequest(BaseModel):
    quota_weekday: int
    quota_weekend: int
    schedule_json: Optional[Any] = None
    app_category_quotas: Optional[Dict[str, int]] = None  # Ví dụ: {"games": 45, "study": -1} (-1 là không giới hạn)