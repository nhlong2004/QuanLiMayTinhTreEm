from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from server.database.database import get_db
from server.app.models.models import BlockedApp

router = APIRouter(prefix="/api/apps", tags=["Blocked Apps Management"])

class AppCreateRequest(BaseModel):
    process_name: str
    file_hash: Optional[str] = None

@router.get("/")
def get_blocked_apps(db: Session = Depends(get_db)):
    return db.query(BlockedApp).all()

@router.post("/")
def add_blocked_app(data: AppCreateRequest, db: Session = Depends(get_db)):
    # Kiểm tra xem tiến trình hoặc mã băm đã tồn tại chưa
    existing = db.query(BlockedApp).filter(BlockedApp.process_name == data.process_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ứng dụng này đã có trong danh sách chặn.")

    new_app = BlockedApp(process_name=data.process_name, file_hash=data.file_hash)
    db.add(new_app)
    db.commit()
    return {"status": "success", "message": f"Đã chặn ứng dụng {data.process_name}"}

@router.delete("/{app_id}")
def delete_blocked_app(app_id: int, db: Session = Depends(get_db)):
    app_item = db.query(BlockedApp).filter(BlockedApp.id == app_id).first()
    if not app_item:
        raise HTTPException(status_code=404, detail="Không tìm thấy ứng dụng.")
    db.delete(app_item)
    db.commit()
    return {"status": "success", "message": "Đã xóa ứng dụng khỏi danh sách chặn."}