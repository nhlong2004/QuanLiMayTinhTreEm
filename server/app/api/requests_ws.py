from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Optional
from server.database.database import get_db
from server.app.models.models import ChildRequest

router = APIRouter(tags=["Requests & Realtime Commands"])

# Quản lý các kết nối WebSocket của Agent theo device_id
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[device_id] = websocket

    def disconnect(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]

    async def send_command_to_device(self, device_id: str, command: dict):
        if device_id in self.active_connections:
            await self.active_connections[device_id].send_json(command)
            return True
        return False

manager = ConnectionManager()

@router.websocket("/ws/commands/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    await manager.connect(device_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Giữ kết nối lắng nghe tín hiệu phản hồi từ Agent
    except WebSocketDisconnect:
        manager.disconnect(device_id)

# API Tiếp nhận và Duyệt yêu cầu của trẻ ("Xin thêm giờ", "Báo chặn nhầm")
class RequestCreate(BaseModel):
    child_id: Optional[int] = None
    device_id: Optional[str] = None
    request_type: str  # "extra_time", "unblock_app", "report_false_positive"
    content: str

@router.post("/api/requests")
def create_child_request(data: RequestCreate, db: Session = Depends(get_db)):
    child_id = data.child_id
    if not child_id and data.device_id:
        from server.app.models.models import Device
        dev = db.query(Device).filter(Device.id == data.device_id).first()
        if dev and dev.child_id:
            child_id = dev.child_id

    req = ChildRequest(
        child_id=child_id,
        device_id=data.device_id,
        request_type=data.request_type,
        content=data.content,
        status="pending"
    )
    db.add(req)
    db.commit()
    return {"status": "success", "message": "Đã gửi yêu cầu tới phụ huynh."}

@router.get("/api/requests")
def get_child_requests(
    parent_username: Optional[str] = None,
    child_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    from server.app.models.models import Device, EnrollCode
    query = db.query(ChildRequest)
    if parent_username:
        parent_devices = db.query(Device.id).filter(Device.parent_username == parent_username).subquery()
        parent_children = db.query(EnrollCode.child_id).filter(EnrollCode.parent_username == parent_username).subquery()
        query = query.filter(
            (ChildRequest.device_id.in_(parent_devices)) |
            (ChildRequest.child_id.in_(parent_children))
        )
    elif child_id is not None:
        query = query.filter(ChildRequest.child_id == child_id)

    requests = query.order_by(ChildRequest.id.desc()).all()
    return requests

@router.post("/api/requests/{request_id}/approve")
async def approve_request(request_id: int, device_id: Optional[str] = None, db: Session = Depends(get_db)):
    req = db.query(ChildRequest).filter(ChildRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu.")
    
    req.status = "approved"
    db.commit()

    target_dev = device_id or req.device_id
    if target_dev:
        await manager.send_command_to_device(target_dev, {
            "command": "add_time",
            "minutes": 15,
            "reason": "Phụ huynh đã duyệt yêu cầu"
        })

    return {"status": "success", "message": "Đã duyệt yêu cầu thành công (+15 phút)."}

@router.post("/api/requests/{request_id}/reject")
async def reject_request(request_id: int, reason: Optional[str] = "Phụ huynh chưa đồng ý lúc này", db: Session = Depends(get_db)):
    req = db.query(ChildRequest).filter(ChildRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu.")
    
    req.status = "rejected"
    db.commit()

    if req.device_id:
        await manager.send_command_to_device(req.device_id, {
            "command": "notify",
            "message": f"Yêu cầu '{req.content}' đã bị từ chối: {reason}"
        })

    return {"status": "success", "message": "Đã từ chối yêu cầu."}

# API Phát Lệnh Khẩn trực tiếp từ Dashboard Phụ huynh (F4: < 5s)
class EmergencyCommandRequest(BaseModel):
    device_id: str
    command: str  # "lock_now", "unlock", "add_time"
    minutes: Optional[int] = 15

@router.post("/api/commands/send")
async def send_emergency_command(data: EmergencyCommandRequest):
    """Gửi lệnh khẩn qua WebSocket tới Agent: Khóa ngay, Mở khóa, Cộng 15 phút (Độ trễ < 5s)"""
    payload = {
        "command": data.command,
        "minutes": data.minutes or 15
    }
    sent = await manager.send_command_to_device(data.device_id, payload)
    if not sent:
        return {
            "status": "queued",
            "message": f"Thiết bị {data.device_id} hiện chưa kết nối WebSocket. Lệnh sẽ gửi khi thiết bị online."
        }
    return {
        "status": "success",
        "message": f"Đã gửi lệnh khẩn '{data.command}' tới thiết bị {data.device_id} thành công!"
    }