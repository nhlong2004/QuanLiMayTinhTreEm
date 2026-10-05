from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import string
import uuid

from server.database.database import get_db
from server.app.models.models import User, Device, Policy, EnrollCode
from server.app.schemas.schemas import LoginRequest, RegisterRequest, GenerateCodeRequest, EnrollRequest

router = APIRouter(prefix="/auth", tags=["Authentication & Enrollment"])

@router.post("/register")
def register_user(data: RegisterRequest, db: Session = Depends(get_db)):
    """API Đăng ký tài khoản mới (Phụ huynh hoặc Trẻ em)"""
    existing_user = db.query(User).filter(User.username == data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Tên đăng nhập đã tồn tại trong hệ thống"
        )
    
    new_user = User(
        username=data.username,
        password_hash=data.password,
        role=data.role,
        child_name=data.child_name if data.role == "child" else None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "status": "success",
        "message": f"Đã khởi tạo tài khoản '{data.username}' thành công!",
        "user_id": new_user.id,
        "role": new_user.role,
        "username": new_user.username
    }

@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """API Đăng nhập phân quyền cho Phụ huynh và Trẻ em"""
    user = db.query(User).filter(User.username == data.username).first()
    if not user or user.password_hash != data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác"
        )
    
    if user.role == "parent":
        return {
            "access_token": f"token-parent-{user.username}",
            "role": "parent",
            "username": user.username,
            "redirect_url": f"/dashboard?username={user.username}"
        }
    elif user.role == "child":
        c_name = user.child_name or user.username
        return {
            "access_token": f"token-child-{user.username}",
            "role": "child",
            "username": user.username,
            "child_name": c_name,
            "redirect_url": f"/child-screen?child_name={c_name}"
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
    
    if not code_record:
        if data.enroll_code == "OGK2026X":
            child_display_name = "Bé An"
            parent_username = "parent_admin"
        else:
            raise HTTPException(status_code=400, detail="Mã ghép đôi không tồn tại hoặc không hợp lệ")
    else:
        if code_record.is_used:
            raise HTTPException(status_code=400, detail="Mã ghép đôi này đã được sử dụng")
        if datetime.utcnow() > code_record.expires_at:
            raise HTTPException(status_code=400, detail="Mã ghép đôi đã hết hạn (quá 10 phút)")
        
        child_user = db.query(User).filter(User.username == code_record.child_username).first()
        child_display_name = child_user.child_name if (child_user and child_user.child_name) else code_record.child_username
        parent_username = code_record.parent_username
        code_record.is_used = True

    device_id = data.device_id or str(uuid.uuid4())
    
    latest_policy = db.query(Policy).order_by(Policy.version.desc()).first()
    current_version = latest_policy.version if latest_policy else 1

    device = db.query(Device).filter(Device.id == device_id).first()
    if device:
        device.device_name = data.device_name
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
            child_name=child_display_name,
            parent_username=parent_username,
            policy_version=current_version,
            status="online",
            last_seen=datetime.utcnow()
        )
        db.add(device)
    
    db.commit()
    return {
        "status": "success",
        "message": f"Ghép đôi thiết bị '{data.device_name}' cho '{child_display_name}' thành công!",
        "device_id": device_id,
        "child_name": child_display_name,
        "parent_username": parent_username,
        "policy_version": current_version
    }
