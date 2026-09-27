from pydantic import BaseModel

class EnrollRequest(BaseModel):
    enroll_code: str
    device_name: str
    child_name: str
    device_fingerprint: str

class HeartbeatRequest(BaseModel):
    device_id: str
    policy_version: int
    status: str = "online"