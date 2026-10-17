import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 1. Thêm đường dẫn gốc vào sys.path để Python nhận diện toàn bộ package 'server'
SYS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if SYS_ROOT not in sys.path:
    sys.path.insert(0, SYS_ROOT)

import hmac
import hashlib
import json

# 2. Import đúng đường dẫn từ package server
from server.database.database import SessionLocal, engine
from server.app.models.models import Base, User, Device, Policy, BlockedApp, BlockedDomain, Event, ChildRequest, EnrollCode

SECRET_KEY = "ogk_secure_secret_key_demo"

def generate_policy_hmac(policy_data: dict) -> str:
    message = f"{policy_data['version']}-{policy_data['quota_weekday']}-{policy_data['quota_weekend']}-{policy_data['schedule_matrix_json']}"
    return hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()

def init_db():
    # Khởi tạo bảng dựa trên Base của SQLAlchemy
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(User).first():
        print("Database đã có dữ liệu mẫu.")
        db.close()
        return

    # 1. Tạo tài khoản Phụ huynh và Trẻ em (Mô hình 1 : n)
    parent = User(username="parent_admin", password_hash="admin123", role="parent")
    child = User(username="be_an", password_hash="child123", role="child", child_name="Bé An")
    db.add_all([parent, child])
    db.commit()

    # 2. Khởi tạo ma trận lịch tuần 7x48 mặc định (7 ngày, mỗi ngày 48 khoảng 30 phút: tất cả là 1 - cho phép)
    default_matrix = [[1 for _ in range(48)] for _ in range(7)]
    schedule_str = json.dumps(default_matrix)

    # 3. Tạo phiên bản chính sách v1 (Mặc định 90 phút ngày trong tuần, 120 phút cuối tuần)
    policy_data = {
        "version": 1,
        "quota_weekday": 90,
        "quota_weekend": 120,
        "schedule_matrix_json": schedule_str
    }
    sig = generate_policy_hmac(policy_data)

    policy_v1 = Policy(
        version=1,
        parent_username=parent.username,
        quota_weekday=90,
        quota_weekend=120,
        schedule_matrix_json=schedule_str,
        hmac_signature=sig
    )
    db.add(policy_v1)

    # 4. Tạo thiết bị mẫu liên kết với trẻ
    device = Device(
        id="7b67f9f8-7df6-4e96-8d66-2616c7b7dc13",
        device_name="PC-phong-khach",
        child_id=child.id,
        child_name=child.child_name,
        parent_username=parent.username,
        policy_version=1,
        status="online"
    )
    db.add(device)

    # 4b. Tạo mã ghép đôi mẫu OGK2026X cho bé An
    sample_enroll = EnrollCode(
        code="OGK2026X",
        child_id=child.id,
        child_username=child.username,
        parent_username=parent.username,
        is_used=True
    )
    db.add(sample_enroll)

    # 5. Khởi tạo dữ liệu mẫu Ứng dụng bị chặn (F2)
    sample_apps = [
        BlockedApp(process_name="game.exe", file_hash=None),
        BlockedApp(process_name="cheatengine.exe", file_hash=None),
        BlockedApp(process_name="roblox.exe", file_hash=None)
    ]
    db.add_all(sample_apps)

    # 6. Khởi tạo danh mục phân loại 200 tên miền thuộc 6 nhóm (F2 BẮT BUỘC)
    try:
        from server.database.domains_dataset_200 import CLASSIFIED_DOMAINS
        for item in CLASSIFIED_DOMAINS:
            exist = db.query(BlockedDomain).filter(BlockedDomain.domain == item["domain"]).first()
            if not exist:
                db.add(BlockedDomain(domain=item["domain"], category=item["category"]))
    except Exception as ex:
        print(f"[-] Lỗi nạp 200 domain dataset: {ex}")

    db.commit()
    db.close()
    print("Đã khởi tạo dữ liệu mẫu thành công với ma trận 7x48, 200 tên miền phân loại 6 nhóm và chữ ký HMAC!")

if __name__ == "__main__":
    init_db()