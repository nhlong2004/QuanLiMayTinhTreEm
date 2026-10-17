from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional
from server.database.database import get_db
from server.app.models.models import Event

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.get("/summary")
def get_reports_summary(
    period: Optional[str] = Query("week", description="today | week | all"),
    child_id: Optional[int] = Query(None),
    parent_username: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    from server.app.models.models import Device, Policy
    query_base = db.query(Event)
    dev_ids = []

    # Tìm thiết bị liên quan để lấy chính sách quota chuẩn xác
    target_device = None
    if device_id:
        target_device = db.query(Device).filter(Device.id == device_id).first()
        query_base = query_base.filter(Event.device_id == device_id)
    elif child_id is not None:
        target_device = db.query(Device).filter(Device.child_id == child_id).first()
        query_base = query_base.filter(Event.child_id == child_id)
    elif parent_username:
        dev_ids = [d[0] for d in db.query(Device.id).filter(Device.parent_username == parent_username).all()]
        if not dev_ids:
            now = datetime.utcnow()
            return {
                "period": period,
                "total_usage_hours": 0.0,
                "daily_chart": [
                    {
                        "date": (now - timedelta(days=i)).strftime("%d/%m"),
                        "day_name": f"T{(now - timedelta(days=i)).weekday() + 2}" if (now - timedelta(days=i)).weekday() < 6 else "CN",
                        "hours": 0.0,
                        "minutes": 0.0
                    }
                    for i in range(6, -1, -1)
                ],
                "top_apps": [],
                "top_domains": [],
                "blocked_stats": {
                    "apps_blocked": 0,
                    "domains_blocked": 0
                }
            }
        query_base = query_base.filter(Event.device_id.in_(dev_ids))
    else:
        now = datetime.utcnow()
        return {
            "period": period,
            "total_usage_hours": 0.0,
            "daily_chart": [
                {
                    "date": (now - timedelta(days=i)).strftime("%d/%m"),
                    "day_name": f"T{(now - timedelta(days=i)).weekday() + 2}" if (now - timedelta(days=i)).weekday() < 6 else "CN",
                    "hours": 0.0,
                    "minutes": 0.0
                }
                for i in range(6, -1, -1)
            ],
            "top_apps": [],
            "top_domains": [],
            "blocked_stats": {
                "apps_blocked": 0,
                "domains_blocked": 0
            }
        }
        
    now = datetime.utcnow()
    if period == "today":
        start_date = datetime(now.year, now.month, now.day)
        query_base = query_base.filter(Event.ts >= start_date)
    elif period == "week":
        start_date = now - timedelta(days=7)
        query_base = query_base.filter(Event.ts >= start_date)

    # 1. Tổng thời lượng sử dụng máy
    total_duration = query_base.with_entities(func.sum(Event.duration_sec)).scalar() or 0
    
    # 2. Top 10 Ứng dụng truy cập nhiều nhất (type = app_start)
    top_apps = query_base.with_entities(Event.subject, func.count(Event.id).label("count")) \
        .filter(Event.type == "app_start") \
        .group_by(Event.subject) \
        .order_by(func.count(Event.id).desc()) \
        .limit(10).all()

    # 3. Top 10 Tên miền truy cập nhiều nhất (type = domain_query)
    top_domains = query_base.with_entities(Event.subject, func.count(Event.id).label("count")) \
        .filter(Event.type == "domain_query") \
        .group_by(Event.subject) \
        .order_by(func.count(Event.id).desc()) \
        .limit(10).all()

    # 4. Thống kê số lần bị chặn ứng dụng / website
    blocked_apps_count = query_base.filter(Event.type == "blocked_app").count()
    blocked_domains_count = query_base.filter(Event.type == "blocked_domain").count()

    # 5. Dữ liệu thời lượng 7 ngày gần nhất phục vụ vẽ biểu đồ (Chart.js)
    daily_usage = []
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_sec = db.query(func.sum(Event.duration_sec)) \
            .filter(Event.ts >= day_start, Event.ts < day_end)
        if child_id is not None:
            day_sec = day_sec.filter(Event.child_id == child_id)
        elif parent_username and dev_ids:
            day_sec = day_sec.filter(Event.device_id.in_(dev_ids))
        dur = day_sec.scalar() or 0
        daily_usage.append({
            "date": day_start.strftime("%d/%m"),
            "day_name": f"T{day_start.weekday() + 2}" if day_start.weekday() < 6 else "CN",
            "hours": round(dur / 3600, 2),
            "minutes": round(dur / 60, 1)
        })

    # Lấy thông tin hạn mức chính sách (F1)
    quota_weekday = 90
    quota_weekend = 120
    bonus_minutes = 0
    live_used_minutes = None
    live_remaining_minutes = None

    if target_device:
        p_user = target_device.parent_username
        pol = None
        if p_user:
            pol = db.query(Policy).filter(Policy.parent_username == p_user).order_by(Policy.version.desc()).first()
        if not pol:
            pol = db.query(Policy).order_by(Policy.version.desc()).first()
        if pol:
            quota_weekday = pol.quota_weekday
            quota_weekend = pol.quota_weekend

        # Tính bonus_minutes từ các yêu cầu được duyệt hôm nay
        from server.app.models.models import ChildRequest
        today_start = datetime(now.year, now.month, now.day)
        approved_requests = db.query(ChildRequest).filter(
            ChildRequest.status == "approved",
            ChildRequest.request_type == "extra_time",
            (ChildRequest.device_id == target_device.id) | (ChildRequest.child_id == target_device.child_id),
            ChildRequest.created_at >= today_start
        ).all()
        bonus_minutes = len(approved_requests) * 15

        # Đọc dữ liệu thời gian thực được Agent báo cáo qua Heartbeat hoặc file live_status.json
        from server.app.api.policies import LIVE_DEVICE_METRICS
        if target_device.id in LIVE_DEVICE_METRICS:
            m = LIVE_DEVICE_METRICS[target_device.id]
            live_used_minutes = m.get("used_minutes")
            live_remaining_minutes = m.get("remaining_minutes")
            if m.get("bonus_minutes"):
                bonus_minutes = max(bonus_minutes, m.get("bonus_minutes"))
        else:
            # Fallback đọc trực tiếp file live_status.json nếu chạy cùng máy dev
            try:
                import os, json
                live_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../agent/live_status.json"))
                if os.path.exists(live_file):
                    with open(live_file, "r", encoding="utf-8") as lf:
                        st = json.load(lf)
                        if st.get("device_id") == target_device.id or not st.get("device_id"):
                            live_used_minutes = st.get("used_minutes")
                            live_remaining_minutes = st.get("remaining_minutes")
                            if st.get("bonus_minutes"):
                                bonus_minutes = max(bonus_minutes, st.get("bonus_minutes"))
            except Exception:
                pass

    base_quota = (quota_weekend if now.weekday() >= 5 else quota_weekday)
    effective_quota = base_quota + bonus_minutes
    actual_used_minutes = live_used_minutes if live_used_minutes is not None else round(total_duration / 60)
    actual_remaining_minutes = live_remaining_minutes if live_remaining_minutes is not None else max(0, effective_quota - actual_used_minutes)

    return {
        "period": period,
        "total_usage_hours": round(actual_used_minutes / 60, 2),
        "total_used_minutes": actual_used_minutes,
        "remaining_minutes": actual_remaining_minutes,
        "daily_chart": daily_usage,
        "top_apps": [{"name": app[0], "count": app[1]} for app in top_apps if app[0]],
        "top_domains": [{"name": dom[0], "count": dom[1]} for dom in top_domains if dom[0]],
        "blocked_stats": {
            "apps_blocked": blocked_apps_count,
            "domains_blocked": blocked_domains_count
        },
        "quota_info": {
            "quota_weekday": quota_weekday,
            "quota_weekend": quota_weekend,
            "bonus_minutes": bonus_minutes,
            "effective_quota": effective_quota,
            "used_minutes": actual_used_minutes,
            "remaining_minutes": actual_remaining_minutes
        }
    }