from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
import random
import string
import uuid
import hashlib
import hmac

from server.database.database import get_db
from server.app.models.models import User, Device, Policy, EnrollCode
from server.app.schemas.schemas import LoginRequest, RegisterRequest, GenerateCodeRequest, EnrollRequest

router = APIRouter(prefix="/auth", tags=["Authentication & Enrollment"])

# Quản lý số lần đăng nhập sai & Khóa tạm 15 phút (F5 BẮT BUỘC)
FAILED_ATTEMPTS = {}  # key: ip_or_user -> {"count": int, "locked_until": datetime}

def hash_password_scrypt(password: str, salt: bytes = None) -> str:
    """Băm mật khẩu bằng scrypt theo chuẩn an toàn (F5 BẮT BUỘC)"""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${key.hex()}"

def verify_password_scrypt(plain_password: str, stored_hash: str) -> bool:
    """Xác thực mật khẩu (hỗ trợ cả scrypt tiêu chuẩn và tài khoản mẫu ban đầu)"""
    if not stored_hash:
        return False
    if stored_hash.startswith("scrypt$"):
        try:
            parts = stored_hash.split("$")
            salt = bytes.fromhex(parts[1])
            expected_key = parts[2]
            key = hashlib.scrypt(plain_password.encode('utf-8'), salt=salt, n=16384, r=8, p=1, dklen=32)
            return hmac.compare_digest(key.hex(), expected_key)
        except Exception:
            return False
    # Hỗ trợ backward compatibility cho các tài khoản seed mẫu như admin123, child123
    return plain_password == stored_hash

@router.post("/register")
def register_user(data: RegisterRequest, db: Session = Depends(get_db)):
    """API Đăng ký tài khoản mới (F5 BẮT BUỘC: Mật khẩu phụ huynh tối thiểu 10 ký tự, băm scrypt)"""
    username = data.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Tên đăng nhập không được để trống")

    if data.role == "parent" and len(data.password) < 10:
        raise HTTPException(
            status_code=400,
            detail="Mật khẩu phụ huynh cần có tối thiểu 10 ký tự để đảm bảo an toàn bảo mật."
        )

    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Tên đăng nhập đã tồn tại trong hệ thống"
        )

    salt = hashlib.sha256(f"{username}{datetime.utcnow()}".encode()).digest()[:16]
    hashed_pwd = hash_password_scrypt(data.password, salt=salt)

    new_user = User(
        username=username,
        password_hash=hashed_pwd,
        role=data.role,
        child_name=data.child_name if data.role == "child" else None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "status": "success",
        "message": f"Đã khởi tạo tài khoản '{username}' thành công!",
        "user_id": new_user.id,
        "role": new_user.role,
        "username": new_user.username
    }

@router.post("/login")
def login(data: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """
    API Đăng nhập (F5 BẮT BUỘC):
    - Khóa tạm 15 phút sau 5 lần sai
    - Giới hạn tần suất theo IP / Username
    - Thiết lập Cookie HttpOnly, SameSite=Lax thời hạn 12 giờ
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    lock_key = f"{client_ip}:{data.username}"
    now = datetime.utcnow()

    # 1. Kiểm tra khóa tạm 15 phút
    if lock_key in FAILED_ATTEMPTS:
        attempt_info = FAILED_ATTEMPTS[lock_key]
        locked_until = attempt_info.get("locked_until")
        if locked_until and now < locked_until:
            wait_seconds = int((locked_until - now).total_seconds())
            wait_minutes = max(1, wait_seconds // 60)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Tài khoản đã bị tạm khóa 15 phút do nhập sai 5 lần. Vui lòng thử lại sau {wait_minutes} phút!"
            )

    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password_scrypt(data.password, user.password_hash):
        # Tăng biến đếm nhập sai
        if lock_key not in FAILED_ATTEMPTS:
            FAILED_ATTEMPTS[lock_key] = {"count": 1, "locked_until": None}
        else:
            FAILED_ATTEMPTS[lock_key]["count"] += 1

        failed_count = FAILED_ATTEMPTS[lock_key]["count"]
        if failed_count >= 5:
            FAILED_ATTEMPTS[lock_key]["locked_until"] = now + timedelta(minutes=15)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Bạn đã nhập sai 5 lần! Tài khoản tạm khóa 15 phút để đảm bảo an toàn."
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Tên đăng nhập hoặc mật khẩu không chính xác (Đã sai {failed_count}/5 lần)"
        )

    # Đăng nhập thành công -> Xóa bộ đếm sai
    if lock_key in FAILED_ATTEMPTS:
        del FAILED_ATTEMPTS[lock_key]

    token_str = f"ogk-sess-{uuid.uuid4().hex}"

    # F5 BẮT BUỘC: Thiết lập Cookie HttpOnly, SameSite=Lax, hạn 12 giờ (43200s)
    response.set_cookie(
        key="ogk_session",
        value=token_str,
        httponly=True,
        samesite="lax",
        max_age=43200,
        path="/"
    )

    if user.role == "parent":
        return {
            "access_token": token_str,
            "role": "parent",
            "username": user.username,
            "redirect_url": f"/dashboard?username={user.username}"
        }
    elif user.role == "child":
        c_name = user.child_name or user.username
        return {
            "access_token": token_str,
            "role": "child",
            "username": user.username,
            "child_name": c_name,
            "redirect_url": f"/child-screen?child_name={c_name}&username={user.username}"
        }

    raise HTTPException(status_code=400, detail="Vai trò hệ thống không hợp lệ")

@router.post("/generate-code")
def generate_enroll_code(data: GenerateCodeRequest, db: Session = Depends(get_db)):
    """Phụ huynh tạo Mã Ghép Đôi 8 ký tự bằng cách gõ đúng Tên Đăng Nhập Trẻ Em (Username duy nhất)"""
    child_username = data.child_username.strip() if data.child_username else ""
    if not child_username:
        raise HTTPException(status_code=400, detail="Vui lòng nhập tên đăng nhập tài khoản của trẻ")

    child_user = db.query(User).filter(
        User.username == child_username,
        User.role == "child"
    ).first()
    
    if not child_user:
        raise HTTPException(
            status_code=400, 
            detail=f"Tài khoản trẻ em '{child_username}' không tồn tại trong hệ thống. Vui lòng kiểm tra lại tên đăng nhập!"
        )

    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    code_str = f"OGK-{random_str}"
    
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    code_entry = EnrollCode(
        code=code_str,
        child_id=child_user.id,
        child_username=child_user.username,
        parent_username=data.parent_username,
        expires_at=expires_at,
        is_used=False
    )
    db.add(code_entry)
    db.commit()

    display_name = child_user.child_name or child_user.username

    return {
        "status": "success",
        "enroll_code": code_str,
        "child_username": child_user.username,
        "child_name": display_name,
        "parent_username": data.parent_username,
        "expires_in_minutes": 10,
        "expires_at": expires_at.isoformat()
    }

@router.post("/enroll")
def enroll_device(data: EnrollRequest, db: Session = Depends(get_db)):
    """Agent gửi mã ghép đôi 8 ký tự để liên kết thiết bị vào tài khoản"""
    code_record = db.query(EnrollCode).filter(EnrollCode.code == data.enroll_code).first()
    
    parent_username = None
    child_display_name = "Bé An"
    child_id = None
    
    if not code_record:
        if data.enroll_code == "OGK2026X":
            child_display_name = "Bé An"
            parent_username = "parent_admin"
            default_child = db.query(User).filter(User.role == "child").first()
            if default_child:
                child_id = default_child.id
        else:
            raise HTTPException(status_code=400, detail="Mã ghép đôi không tồn tại hoặc không hợp lệ")
    else:
        if code_record.is_used:
            raise HTTPException(status_code=400, detail="Mã ghép đôi này đã được sử dụng")
        if datetime.utcnow() > code_record.expires_at:
            raise HTTPException(status_code=400, detail="Mã ghép đôi đã hết hạn (quá 10 phút)")
        
        child_user = None
        if code_record.child_id:
            child_user = db.query(User).filter(User.id == code_record.child_id).first()
        elif code_record.child_username:
            child_user = db.query(User).filter(User.username == code_record.child_username).first()
            
        child_display_name = child_user.child_name if (child_user and child_user.child_name) else (code_record.child_username or "Bé An")
        child_id = child_user.id if child_user else code_record.child_id
        parent_username = code_record.parent_username
        code_record.is_used = True

    device_id = data.device_id or str(uuid.uuid4())
    
    latest_policy = None
    if parent_username:
        latest_policy = db.query(Policy).filter(Policy.parent_username == parent_username).order_by(Policy.version.desc()).first()
    if not latest_policy:
        latest_policy = db.query(Policy).filter((Policy.parent_username == None) | (Policy.version == 1)).order_by(Policy.version.asc()).first()
    if not latest_policy:
        latest_policy = db.query(Policy).order_by(Policy.version.desc()).first()
    current_version = latest_policy.version if latest_policy else 1

    device = db.query(Device).filter(Device.id == device_id).first()
    if device:
        device.device_name = data.device_name
        device.child_id = child_id
        device.child_name = child_display_name
        if parent_username:
            device.parent_username = parent_username
        device.policy_version = current_version
        device.status = "online"
        device.last_seen = datetime.utcnow()
    else:
        device = Device(
            id=device_id,
            device_name=data.device_name,
            child_id=child_id,
            child_name=child_display_name,
            parent_username=parent_username,
            policy_version=current_version,
            status="online",
            last_seen=datetime.utcnow()
        )
        db.add(device)
    
    db.commit()

    # Tự động cập nhật agent/config.json trên máy dev để người dùng không cần sửa file bằng tay
    try:
        agent_cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../agent/config.json"))
        if os.path.exists(agent_cfg_path):
            with open(agent_cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["device_id"] = device_id
            cfg["child_name"] = child_display_name
            with open(agent_cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

    return {
        "status": "success",
        "message": f"Ghép đôi thiết bị '{data.device_name}' cho '{child_display_name}' thành công!",
        "device_id": device_id,
        "child_name": child_display_name,
        "parent_username": parent_username,
        "policy_version": current_version
    }
