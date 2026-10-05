import os
import sys

# Tắt Cython C-extension của SQLAlchemy để tránh bị Windows Application Control chặn DLL
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

# Set UTF-8 encoding cho stdout trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SYS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if SYS_ROOT not in sys.path:
    sys.path.insert(0, SYS_ROOT)

from server.database.database import Base, engine, SessionLocal
from server.app.models.models import User, Policy, Device, EnrollCode

def init_db():
    # Tự động tạo bảng nếu chưa có
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Thêm dữ liệu mẫu ban đầu nếu chưa có
    if not db.query(User).filter(User.username == "parent_admin").first():
        parent = User(username="parent_admin", password_hash="admin123", role="parent")
        child = User(username="be_an", password_hash="child123", role="child", child_name="Bé An")
        db.add_all([parent, child])

    if not db.query(Policy).first():
        default_policy = Policy(
            version=1,
            quota_weekday=90,
            quota_weekend=120,
            schedule_json='{"blocked_hours": ["22:00-06:00"]}'
        )
        db.add(default_policy)

    if not db.query(Device).filter(Device.id == "7b67f9f8-7df6-4e96-8d66-2616c7b7dc13").first():
        sample_device = Device(
            id="7b67f9f8-7df6-4e96-8d66-2616c7b7dc13",
            device_name="PC-phong-khach",
            child_name="Bé An",
            parent_username="parent_admin",
            policy_version=1,
            status="online"
        )
        db.add(sample_device)

    db.commit()
    db.close()
    print("[+] Da khoi tao thanh cong co so du lieu mẫu (Seed Data)!")

def reset_db():
    # Xoá database cũ để cập nhật Schema mới
    DB_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(DB_DIR, "ogk_server.db")
    
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("[+] Da cap nhat CSDL theo Schema moi!")
    init_db()

if __name__ == "__main__":
    reset_db()
