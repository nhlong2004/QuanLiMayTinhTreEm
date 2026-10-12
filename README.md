# OpenGuardKids (OGK) - Hệ Thống Hỗ Trợ Quản Lý Máy Tính Trẻ Em
> **"Công cụ đồng hành, không phải phần mềm theo dõi lén"**

Dự án đồ án môn học thuộc Khoa CNTT - HCMUS. Hệ thống bao gồm 2 thành phần chính:
1. **Server (FastAPI + SQLite WAL + Jinja2/Tailwind + WebSocket)**: Quản lý chính sách, phân quyền, tiếp nhận nhịp tim, nhật ký sự kiện và bảng điều khiển cho Phụ huynh & Trẻ em.
2. **Agent (Windows Service/Process - Python 3.11+, pywin32, psutil, dnslib, pystray)**: Quản lý Quota thời gian bằng monotonic clock, DNS Proxy lọc website cục bộ tại 127.0.0.1:53, kiểm soát tiến trình ứng dụng bằng SHA-256, hàng đợi sự kiện offline và khay hệ thống (System Tray).

---

## 🛠️ Yêu Cầu Môi Trường
* **Hệ điều hành:** Windows 10/11 (x64)
* **Phiên bản Python:** Python 3.11+ (khuyến nghị 3.11 đến 3.13)
* **Quyền:** Khuyến nghị mở terminal với quyền Administrator khi chạy DNS Proxy (port 53).

---

## 🚀 Hướng Dẫn Cài Đặt (Trong vòng 5 phút)

### Bước 1: Tạo Môi Trường Ảo (Virtual Environment)
Mở PowerShell hoặc Command Prompt tại thư mục gốc của dự án:
```powershell
# Di chuyển vào thư mục dự án
cd "d:\SCHOOL\code\cdtnmmt\project-01-openguardkids\QuanLiMayTinhTreEm"

# Tạo môi trường ảo tên 'venv'
python -m venv venv

# Kích hoạt môi trường ảo trên Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# (Nếu dùng Command Prompt / CMD thông thường: venv\Scripts\activate.bat)
```
> *Lưu ý:* Nếu PowerShell báo lỗi `Execution_Policies`, hãy chạy lệnh: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` rồi kích hoạt lại.

---

### Bước 2: Cài Đặt Thư Viện Cần Thiết

Cài đặt tất cả thư viện cho cả Server và Agent:
```powershell
# Nâng cấp pip
python -m pip install --upgrade pip

# Cài đặt thư viện Server
pip install -r server/requirements.txt

# Cài đặt thư viện Agent
pip install -r agent/requirements.txt
```

*(Hoặc cài trực tiếp bằng 1 lệnh duy nhất):*
```powershell
pip install fastapi uvicorn sqlalchemy pydantic jinja2 requests psutil pywin32 dnslib websockets pystray pillow
```

---

### Bước 3: Khởi Tạo Cơ Sở Dữ Liệu & Dữ Liệu Mẫu (Seed DB)
Khởi tạo bảng SQLite và nạp sẵn tài khoản mẫu, chính sách mặc định, danh sách chặn mẫu:
```powershell
python server/database/seed.py
```
*Tài khoản thử nghiệm:*
* **Phụ huynh:** `parent_admin` / Mật khẩu: `admin123`
* **Trẻ em:** `be_an` / Mật khẩu: `child123`
* **Mã ghép đôi nhanh dự phòng:** `OGK2026X`

---

## 🖥️ Hướng Dẫn Chạy Chương Trình

### 1. Khởi chạy Server (FastAPI)
Mở Terminal 1 (đã kích hoạt `venv`):
```powershell
python server/main.py
```
* Server chạy tại: `http://127.0.0.1:8000`
* **Trang Đăng Nhập:** [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
* **Dashboard Phụ Huynh:** [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)
* **Màn Hình Minh Bạch Trẻ Em:** [http://127.0.0.1:8000/child-screen](http://127.0.0.1:8000/child-screen)
* **Tài liệu API (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 2. Khởi chạy Agent (Phía Trẻ Em)
Mở Terminal 2 (quyền **Administrator** để DNS Proxy có thể bind vào cổng 53):
```powershell
.\venv\Scripts\Activate.ps1
python agent/main_agent.py
```
Khi chạy, Agent sẽ:
1. Tự động liên kết thiết bị với Server qua `device_id`.
2. Khởi động **DNS Proxy Server** lọc tên miền tại `127.0.0.1:53`.
3. Bật **Client WebSocket** kết nối nhận lệnh khẩn từ phụ huynh (`< 5s`).
4. Hiện biểu tượng **Chiếc Khiên Xanh (System Tray)** dưới khay hệ thống Windows Taskbar.
5. Quét tiến trình ứng dụng theo SHA-256 (`psutil`) và đếm giờ bằng Monotonic clock.
