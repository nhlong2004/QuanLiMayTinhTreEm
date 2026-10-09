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
    child_id: int
    request_type: str
    content: str

@router.post("/api/requests")
def create_child_request(data: RequestCreate, db: Session = Depends(get_db)):
    req = ChildRequest(child_id=data.child_id, request_type=data.request_type, content=data.content, status="pending")
    db.add(req)
    db.commit()
    return {"status": "success", "message": "Đã gửi yêu cầu tới phụ huynh."}

@router.get("/api/requests")
def get_child_requests(db: Session = Depends(get_db)):
    requests = db.query(ChildRequest).all()
    return requests

@router.post("/api/requests/{request_id}/approve")
async def approve_request(request_id: int, device_id: Optional[str] = None, db: Session = Depends(get_db)):
    req = db.query(ChildRequest).filter(ChildRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu.")
    
    req.status = "approved"
    db.commit()

    # Nếu có device_id, bắn lệnh khẩn cộng giờ qua WebSocket ngay lập tức (< 5s)
    if device_id:
        await manager.send_command_to_device(device_id, {"command": "add_time", "minutes": 15})

    return {"status": "success", "message": "Đã duyệt yêu cầu thành công."}