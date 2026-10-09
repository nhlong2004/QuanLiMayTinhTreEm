from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List, Optional
from server.database.database import get_db
from server.app.models.models import Event

router = APIRouter(prefix="/api", tags=["Events & Privacy"])

class EventItem(BaseModel):
    device_id: str
    child_id: int
    type: str
    subject: Optional[str] = None
    duration_sec: Optional[int] = 0
    policy_id: Optional[int] = None
    ts: Optional[str] = None

class EventBatchRequest(BaseModel):
    events: List[EventItem]

@router.post("/events/batch")
def receive_events_batch(data: EventBatchRequest, db: Session = Depends(get_db)):
    for item in data.events:
        event_time = datetime.utcnow()
        if item.ts:
            try:
                event_time = datetime.fromisoformat(item.ts)
            except:
                pass
        db_event = Event(
            ts=event_time,
            device_id=item.device_id,
            child_id=item.child_id,
            type=item.type,
            subject=item.subject,
            duration_sec=item.duration_sec or 0,
            policy_id=item.policy_id
        )
        db.add(db_event)
    db.commit()
    return {"status": "success", "received_count": len(data.events)}

@router.delete("/privacy/purge-data")
def purge_old_data(db: Session = Depends(get_db)):
    # Tác vụ tự động / thủ công xóa dữ liệu cũ quá 90 ngày (Nghị định 13/2023)
    cutoff_date = datetime.utcnow() - timedelta(days=90)
    deleted = db.query(Event).filter(Event.ts < cutoff_date).delete()
    db.commit()
    return {"status": "success", "message": f"Đã xóa vĩnh viễn {deleted} bản ghi sự kiện cũ hơn 90 ngày."}