from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from server.database.database import get_db
from server.app.models.models import Event

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.get("/summary")
def get_reports_summary(db: Session = Depends(get_db)):
    # Tổng thời lượng sử dụng máy
    total_duration = db.query(func.sum(Event.duration_sec)).scalar() or 0
    
    # Top 10 Ứng dụng truy cập nhiều nhất (type = app_start)
    top_apps = db.query(Event.subject, func.count(Event.id).label("count")) \
        .filter(Event.type == "app_start") \
        .group_by(Event.subject) \
        .order_by(func.count(Event.id).desc()) \
        .limit(10).all()

    # Top 10 Tên miền truy cập nhiều nhất (type = domain_query)
    top_domains = db.query(Event.subject, func.count(Event.id).label("count")) \
        .filter(Event.type == "domain_query") \
        .group_by(Event.subject) \
        .order_by(func.count(Event.id).desc()) \
        .limit(10).all()

    # Thống kê số lần bị chặn ứng dụng / website
    blocked_apps_count = db.query(Event).filter(Event.type == "blocked_app").count()
    blocked_domains_count = db.query(Event).filter(Event.type == "blocked_domain").count()

    return {
        "total_usage_hours": round(total_duration / 3600, 2),
        "top_apps": [{"name": app[0], "count": app[1]} for app in top_apps if app[0]],
        "top_domains": [{"name": dom[0], "count": dom[1]} for dom in top_domains if dom[0]],
        "blocked_stats": {
            "apps_blocked": blocked_apps_count,
            "domains_blocked": blocked_domains_count
        }
    }