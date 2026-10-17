# 🛡️ OpenGuardKids (OGK) - Hệ Thống Quản Lý & Bảo Vệ Máy Tính Trẻ Em
> **Triết lý:** *"Công cụ đồng hành minh bạch, không phải phần mềm theo dõi lén"*  
> **Đồ án môn học:** Chuyên Đề Tốt Nghiệp Mạng Máy Tính & An Toàn Thông Tin — HCMUS (ĐHQG-HCM)

---

## 📑 Mục Lục
1. [Tổng Quan Kiến Trúc & Tính Năng](#1-tổng-quan-kiến-trúc--tính-năng)
2. [Ý Nghĩa Mạng: `127.0.0.1` vs IP Máy Chủ (LAN IP)](#2-ý-nghĩa-mạng-127001-vs-ip-máy-chủ-lan-ip)
3. [Kỳ Vọng Kết Quả Khi Nộp Bài (Output Expectations)](#3-kỳ-vọng-kết-quả-khi-nộp-bài-output-expectations)
4. [Yêu Cầu Môi Trường & Cài Đặt](#4-yêu-cầu-môi-trường--cài-đặt)
5. [Hướng Dẫn Chạy Demo & Nộp Bài](#5-hướng-dẫn-chạy-demo--nộp-bài)
   - [Kịch bản A: Chạy trên 1 máy duy nhất (Khuyến nghị khi chấm bài)](#kịch-bản-a-chạy-trên-1-máy-duy-nhất-khuyến-nghị-khi-chấm-bài)
   - [Kịch bản B: Chạy phân tán trên nhiều máy thực tế trong mạng LAN](#kịch-bản-b-chạy-phân-tán-trên-nhiều-máy-thực-tế-trong-mạng-lan)
   - [Kịch bản C: Mô phỏng nhiều máy trẻ em trên cùng 1 PC](#kịch-bản-c-mô-phỏng-nhiều-máy-trẻ-em-trên-cùng-1-pc)
6. [Kịch Bản Kiểm Thử Đánh Giá (Test Checklist)](#6-kịch-bản-kiểm-thử-đánh-giá-test-checklist)

---

## 1. Tổng Quan Kiến Trúc & Tính Năng

Hệ thống hoạt động theo mô hình Client-Server gồm 2 thành phần chính:
* **Server (`server/`)**: Xây dựng bằng **FastAPI**, cơ sở dữ liệu **SQLite (WAL mode)**, giao diện **Jinja2 + Tailwind CSS** và kênh điều khiển thời gian thực **WebSocket**.
* **Agent (`agent/`)**: Chạy ngầm trên máy tính của trẻ, sử dụng **Python 3.11+**, `dnslib` (DNS Proxy cục bộ lọc 200 domain), `psutil` (kiểm soát tiến trình app), `pystray` (khay hệ thống System Tray), SQLite cục bộ đệm sự kiện offline khi mất mạng và client WebSocket nhận lệnh khẩn cấp tức thì.

| Mã | Tính Năng | Mô Tả |
|---|---|---|
| **F1** | Quota Thời Gian & Lịch Cấm | Đếm giờ độc lập bằng Monotonic clock, ma trận lịch tuần 7x48 block 30 phút, SLA khóa máy < 5s |
| **F2** | Chặn App & Domain | DNS Proxy lọc 200 tên miền phân loại 6 nhóm, SafeSearch VIP Google/Bing, chặn tiến trình file hash SHA-256 |
| **F3** | Event Logging & Purge | Đệm sự kiện vào SQLite cục bộ khi offline, đồng bộ lô về Server, hỗ trợ xóa toàn diện theo Nghị định 13/2023 |
| **F4** | HMAC & Lệnh Khẩn Cấp | Chữ ký HMAC SHA-256 xác thực toàn vẹn chính sách, WebSocket gửi lệnh khóa/mở/thưởng giờ < 5s |
| **F5** | Xác Thực & Bảo Mật | Hash mật khẩu scrypt, khóa tạm 15 phút sau 5 lần đăng nhập sai, cookie bảo mật HttpOnly |
| **NT1-NT6** | Nguyên Tắc Nhân Văn | Icon khay hệ thống hiển thị rõ ràng, màn hình minh bạch cho trẻ, phụ huynh sửa luật để lại nhật ký, miễn chặn trang khẩn cấp |

---

## 2. Ý Nghĩa Mạng: `127.0.0.1` vs IP Máy Chủ (LAN IP)

Khi thiết kế và chấm điểm hệ thống Client-Server phân tán, hai khái niệm này có ý nghĩa kỹ thuật rất quan trọng:

### 🌐 `127.0.0.1` (Localhost / Loopback)
* **Ý nghĩa:** Là địa chỉ IP ảo nội bộ của chính chiếc máy tính đó. Mọi gói tin gửi tới `127.0.0.1` sẽ được hệ điều hành định tuyến vòng trở lại ngay trong máy, **hoàn toàn không đi qua card mạng vật lý**.
* **Khi nào sử dụng:** Dùng để phát triển (development), viết unit test, và **chạy thử nghiệm demo trên cùng 1 chiếc laptop**.
* **Hạn chế:** Các thiết bị khác trong cùng phòng/cùng mạng WiFi **không thể kết nối** tới `127.0.0.1` của máy chủ.

### 🏠 IP Máy Chủ Trong Mạng LAN (Ví dụ: `192.168.1.50`)
* **Ý nghĩa:** Là địa chỉ IP do Router Wi-Fi cấp cho card mạng của máy chủ. Server lắng nghe tại `0.0.0.0:8000` (mọi giao tiếp mạng).
* **Khi nào sử dụng:** Dùng trong triển khai gia đình thực tế: Máy phụ huynh đặt ở phòng khách, các máy trẻ em đặt ở phòng ngủ/bàn học.
* **Tác dụng:** Máy tính của trẻ (Agent) trỏ `server_url` về `http://192.168.1.50:8000` để gửi nhịp tim, đồng bộ luật và nhận lệnh khóa máy từ xa qua WebSocket.

---

## 3. Kỳ Vọng Kết Quả Khi Nộp Bài (Output Expectations)

Khi nộp code và chạy demo chấm điểm đồ án, ban giám khảo/giảng viên sẽ kiểm tra các kết quả đầu ra chuẩn sau:

### ✅ 1. Phía Máy Chủ (Server)
1. Chạy lệnh: `python server/main.py`
2. **Output màn hình terminal:** 
   - Thông báo Server khởi chạy thành công.
   - Hiển thị địa chỉ truy cập localhost: `http://127.0.0.1:8000`.
   - Hiển thị danh sách IP LAN để kết nối máy con: `👉 http://192.168.x.x:8000`.
3. **Mở trình duyệt Web:**
   - Đăng nhập phụ huynh: `http://127.0.0.1:8000/login` (Tài khoản: `parent_admin` / `admin123`).
   - Vào Dashboard: Hiển thị đúng danh sách thiết bị con, thời lượng dùng máy hôm nay, biểu đồ cột 7 ngày, danh sách 200 tên miền bị chặn và nhật ký kiểm toán.

### ✅ 2. Phía Máy Trạm Trẻ Em (Agent)
1. Chạy lệnh: `python agent/main_agent.py` (với quyền Administrator để mở port 53 DNS).
2. **Output màn hình terminal:**
   - In thông báo: `Khởi chạy OpenGuardKids Agent (PID: ..., RAM: ... MB)`.
   - Kết nối Server thành công, gán `Device ID` và thông báo nhịp tim `Heartbeat OK`.
   - Khởi động DNS Proxy lọc tên miền tại `127.0.0.1:53`.
   - Kết nối WebSocket nhận lệnh khẩn cấp thành công.
3. **Biểu hiện trên giao diện Windows:**
   - Dưới khay hệ thống (gần đồng hồ Windows Taskbar) xuất hiện **biểu tượng chiếc khiên xanh**.
   - Di chuột vào biểu tượng hiển thị tooltip số phút còn lại.
   - Nhấp đúp vào biểu tượng sẽ tự động mở màn hình minh bạch dành cho trẻ (`child-screen`).

### ✅ 3. Thao Tác Kiểm Tra Tức Thì (Real-time SLA < 5s)
* Phụ huynh bấm nút **🔒 Khóa máy** trên web dashboard → Trong vòng 1–2 giây, terminal của con thông báo nhận lệnh khóa máy tức thì.
* Trẻ gõ truy cập trang web bị cấm (ví dụ: `tiktok.com`) → DNS Proxy chặn và chuyển hướng sinkhole về `127.0.0.1`.

---

## 4. Yêu Cầu Môi Trường & Cài Đặt

* **Hệ điều hành:** Windows 10 hoặc Windows 11 (64-bit).
* **Python:** Python 3.11 đến 3.13 (khuyến nghị Python 3.11 hoặc 3.12).
* **Quyền:** Terminal chạy Agent cần quyền Administrator để lắng nghe cổng UDP 53 (DNS Proxy).

### Bước 1: Kích hoạt Virtual Environment (venv)
```powershell
# Di chuyển vào thư mục dự án
cd "d:\SCHOOL\code\cdtnmmt\project-01-openguardkids\QuanLiMayTinhTreEm"

# Kích hoạt môi trường ảo
.\venv\Scripts\Activate.ps1
```

### Bước 2: Cài đặt thư viện phụ thuộc
```powershell
pip install -r server/requirements.txt
pip install -r agent/requirements.txt
```
*(Hoặc cài trực tiếp bằng 1 lệnh duy nhất):*
```powershell
pip install fastapi uvicorn sqlalchemy pydantic jinja2 requests psutil pywin32 dnslib websockets pystray pillow
```

### Bước 3: Khởi tạo dữ liệu mẫu (Seed Data)
```powershell
python server/database/seed.py
```
*Tài khoản thử nghiệm sẵn có:*
* **Phụ huynh:** `parent_admin` / Mật khẩu: `admin123`
* **Trẻ em:** `be_an` / Mật khẩu: `child123`
* **Mã ghép đôi dự phòng:** `OGK2026X`

---

## 5. Hướng Dẫn Chạy Demo & Nộp Bài

### Kịch bản A: Chạy trên 1 máy duy nhất (Khuyến nghị khi chấm bài)
> Đây là kịch bản phổ biến nhất khi thầy cô chấm bài trực tiếp trên máy của bạn.

1. **Mở Terminal 1 (Khởi chạy Server):**
   ```powershell
   .\venv\Scripts\Activate.ps1
   python server/main.py
   ```
2. **Mở Terminal 2 (Khởi chạy Agent - Chạy với quyền Run as Administrator):**
   ```powershell
   .\venv\Scripts\Activate.ps1
   python agent/main_agent.py
   ```
3. **Mở trình duyệt Web:**
   * Tab 1 (Bố Mẹ): `http://127.0.0.1:8000/login` -> Đăng nhập tài khoản `parent_admin`.
   * Tab 2 (Con): `http://127.0.0.1:8000/child-screen` -> Xem góc minh bạch của trẻ.

---

### Kịch bản B: Chạy phân tán trên nhiều máy thực tế trong mạng LAN
> Dùng khi báo cáo đồ án có 2 laptop kết nối cùng mạng WiFi (1 máy Server Phụ huynh, 1 hoặc nhiều máy Laptop Trẻ em).

1. **Trên Máy Chủ (Laptop Phụ huynh):**
   ```powershell
   python server/main.py
   ```
   *Terminal sẽ in ra IP mạng LAN, ví dụ: `👉 http://192.168.1.50:8000`.*
   * Phụ huynh đăng nhập vào `http://127.0.0.1:8000/dashboard`, vào tab **Máy Tính Của Con** > bấm **+ Kết Nối Máy Con** để sinh mã mới (ví dụ: `OGK-ABC123`).

2. **Trên Máy Con 1 (Laptop Trẻ em A):**
   ```powershell
   python agent/main_agent.py --server-url http://192.168.1.50:8000 --enroll-code OGK-ABC123 --device-name "Laptop-Be-An"
   ```

3. **Trên Máy Con 2 (Laptop Trẻ em B - nếu có):**
   ```powershell
   python agent/main_agent.py --server-url http://192.168.1.50:8000 --enroll-code OGK-XYZ890 --device-name "PC-Be-Lan"
   ```

---

### Kịch bản C: Mô phỏng nhiều máy trẻ em trên cùng 1 PC
> Dùng để chứng minh với giảng viên rằng hệ thống hỗ trợ nhiều máy con độc lập mà không cần phải mang nhiều laptop đi cùng.

* **Mô phỏng Máy Con 1:**
  ```powershell
  python agent/main_agent.py --config agent/config_kid1.json --enroll-code OGK2026X --device-name "May-1-Be-An"
  ```
* **Mô phỏng Máy Con 2 (Mở terminal riêng):**
  ```powershell
  python agent/main_agent.py --config agent/config_kid2.json --enroll-code OGK2026X --device-name "May-2-Be-Lan"
  ```
Trên Dashboard phụ huynh sẽ nhận diện đồng thời cả 2 máy con, đếm giờ và quản lý trạng thái online/offline riêng biệt!

---

## 6. Kịch Bản Kiểm Thử Đánh Giá (Test Checklist)

### 1. Kiểm tra DNS Proxy lọc tên miền (F2)
Mở một cửa sổ PowerShell mới và gõ lệnh kiểm tra DNS:
```powershell
# Kiểm tra tên miền bị chặn -> Sẽ trả về 127.0.0.1 (Bị sinkhole)
nslookup tiktok.com 127.0.0.1
nslookup roblox.com 127.0.0.1

# Kiểm tra tên miền cho phép -> Sẽ phân giải ra IP thật bình thường
nslookup google.com 127.0.0.1
nslookup moet.gov.vn 127.0.0.1
```

### 2. Kiểm tra lệnh khẩn cấp WebSocket < 5s (F4)
1. Tại Dashboard Phụ huynh, mục **Máy Tính Của Con**, bấm nút **🔒 Khóa máy**.
2. Quan sát màn hình Terminal của Agent: Trong vòng 1–2 giây sẽ in dòng `[WebSocket] Nhận lệnh khẩn cấp từ phụ huynh: lock_now`.
3. Bấm nút **🔓 Mở máy** hoặc **⏰ +15p** để kiểm tra phản hồi tương tự.

### 3. Kiểm tra tính năng minh bạch & tôn trọng trẻ em (NT1, NT5)
* Nhấp vào icon khay hệ thống chiếc khiên xanh > chọn **Xem chi tiết giờ dùng**.
* Màn hình góc trẻ em mở ra, thông báo đầy đủ lý do tại sao máy bị giới hạn giờ, nhật ký các lần bố mẹ thay đổi quy định và nút **"Xin thêm 15 phút"**.

---
*Chúc bạn có buổi báo cáo và nộp đồ án thành công rực rỡ! 🎉*
