from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List, Optional, Union, Any

from server.database.database import get_db
from server.app.models.models import Event

router = APIRouter(prefix="/api", tags=["Events & Privacy"])

class EventItem(BaseModel):
    device_id: str
    child_id: Optional[Union[int, str]] = 1
    type: str
    subject: Optional[str] = None
    duration_sec: Optional[int] = 0
    policy_id: Optional[int] = None
    ts: Optional[Union[int, float, str]] = None

class EventBatchRequest(BaseModel):
    events: List[EventItem]
    device_id: Optional[str] = None

@router.post("/events/batch")
def receive_events_batch(data: EventBatchRequest, db: Session = Depends(get_db)):
    for item in data.events:
        event_time = datetime.utcnow()
        if item.ts:
            try:
                if isinstance(item.ts, (int, float)):
                    event_time = datetime.utcfromtimestamp(item.ts)
                else:
                    event_time = datetime.fromisoformat(str(item.ts))
            except Exception:
                pass

        c_id = None
        if isinstance(item.child_id, int):
            c_id = item.child_id
        elif isinstance(item.child_id, str) and item.child_id.isdigit():
            c_id = int(item.child_id)

        db_event = Event(
            ts=event_time,
            device_id=item.device_id,
            child_id=c_id,
            type=item.type,
            subject=item.subject,
            duration_sec=item.duration_sec or 0,
            policy_id=item.policy_id
        )
        db.add(db_event)
    db.commit()
    return {"status": "success", "received_count": len(data.events)}

@router.delete("/privacy/purge-data")
async def purge_data(
    child_id: Optional[int] = None, 
    purge_all: bool = False, 
    parent_username: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """API Xóa dữ liệu theo Nghị định 13/2023 & BẮT BUỘC F3:
    1. 'Xóa toàn bộ dữ liệu của con tôi': Xóa đồng thời trên server VÀ trong bộ đệm của agent.
    2. Tự động xóa sự kiện quá 90 ngày.
    """
    from server.app.models.models import Device
    from server.app.api.requests_ws import manager

    if purge_all or child_id is not None or parent_username:
        query = db.query(Event)
        dev_ids = []

        if child_id is not None:
            query = query.filter(Event.child_id == child_id)
            dev_ids = [d[0] for d in db.query(Device.id).filter(Device.child_id == child_id).all()]
        elif parent_username:
            dev_ids = [d[0] for d in db.query(Device.id).filter(Device.parent_username == parent_username).all()]
            if dev_ids:
                query = query.filter(Event.device_id.in_(dev_ids))

        deleted = query.delete(synchronize_session=False)
        db.commit()

        # F3 BẮT BUỘC: Gửi lệnh qua WebSocket xóa đồng thời trong bộ đệm của Agent
        agent_purged_count = 0
        if not dev_ids and purge_all:
            dev_ids = list(manager.active_connections.keys())

        for d_id in dev_ids:
            sent = await manager.send_command_to_device(d_id, {
                "command": "purge_offline_events",
                "reason": "Phụ huynh kích hoạt quyền được lãng quên (Nghị định 13/2023)"
            })
            if sent:
                agent_purged_count += 1

        return {
            "status": "success",
            "message": f"Đã xóa vĩnh viễn {deleted} sự kiện trên máy chủ và phát lệnh xóa sạch bộ đệm offline tới {len(dev_ids)} thiết bị của con!",
            "deleted_server_events": deleted,
            "notified_agent_devices": len(dev_ids)
        }
    else:
        # Tự động dọn dẹp các sự kiện cũ hơn 90 ngày (F3 BẮT BUỘC)
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        deleted = db.query(Event).filter(Event.ts < cutoff_date).delete(synchronize_session=False)
        db.commit()
        return {
            "status": "success",
            "message": f"Đã tự động xóa {deleted} sự kiện quá thời hạn lưu trữ 90 ngày theo quy định.",
            "deleted_server_events": deleted
        }