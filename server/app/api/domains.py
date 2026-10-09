from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from server.database.database import get_db
from server.app.models.models import BlockedDomain

router = APIRouter(prefix="/api/domains", tags=["Blocked Domains Management"])

class DomainCreateRequest(BaseModel):
    domain: str
    category: str  # Giáo dục, Giải trí, Mạng xã hội, Trò chơi, Không phù hợp, Chưa phân loại

@router.get("/")
def get_blocked_domains(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(BlockedDomain)
    if category and category != "Tất cả":
        query = query.filter(BlockedDomain.category == category)
    return query.all()

@router.post("/")
def add_blocked_domain(data: DomainCreateRequest, db: Session = Depends(get_db)):
    valid_categories = ["Giáo dục", "Giải trí", "Mạng xã hội", "Trò chơi", "Không phù hợp", "Chưa phân loại"]
    if data.category not in valid_categories:
        raise HTTPException(status_code=400, detail="Nhóm phân loại không hợp lệ.")
    
    # Kiểm tra xem domain đã tồn tại chưa
    existing = db.query(BlockedDomain).filter(BlockedDomain.domain == data.domain).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tên miền này đã có trong danh sách chặn.")

    new_domain = BlockedDomain(domain=data.domain, category=data.category)
    db.add(new_domain)
    db.commit()
    return {"status": "success", "message": f"Đã thêm miền {data.domain} vào nhóm {data.category}"}

@router.delete("/{domain_id}")
def delete_blocked_domain(domain_id: int, db: Session = Depends(get_db)):
    domain_item = db.query(BlockedDomain).filter(BlockedDomain.id == domain_id).first()
    if not domain_item:
        raise HTTPException(status_code=404, detail="Không tìm thấy tên miền.")
    db.delete(domain_item)
    db.commit()
    return {"status": "success", "message": "Đã xóa tên miền khỏi danh sách chặn."}