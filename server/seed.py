# seed.py
from models import Base, User, Policy, Device
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./ogk_server.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Kiểm tra xem đã có dữ liệu chưa
    if db.query(User).first():
        print("Database đã có dữ liệu mẫu.")
        db.close()
        return

    # 1. Tạo tài khoản Phụ huynh và Trẻ em
    parent = User(username="parent_admin", password_hash="admin123", role="parent")
    child = User(username="be_an", password_hash="child123", role="child", child_name="Bé An")
    db.add_all([parent, child])

    # 2. Tạo chính sách mặc định (F1) phiên bản 1
    default_policy = Policy(
        version=1,
        quota_weekday=90,
        quota_weekend=120,
        schedule_json='{"blocked_hours": ["22:00-06:00"]}'
    )
    db.add(default_policy)

    # 3. Tạo thiết bị mẫu liên kết với Bé An
    sample_device = Device(
        id="7b67f9f8-7df6-4e96-8d66-2616c7b7dc13",
        device_name="PC-phong-khach",
        child_name="Bé An",
        policy_version=1,
        status="online"
    )
    db.add(sample_device)

    db.commit()
    db.close()
    print("Đã khởi tạo thành công cơ sở dữ liệu mẫu (Seed Data)!")

if __name__ == "__main__":
    init_db()