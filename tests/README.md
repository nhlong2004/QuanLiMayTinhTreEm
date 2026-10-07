# OpenGuardKids - Automated Test Suite (`/tests`)

Hệ thống kiểm thử tự động của dự án **OpenGuardKids** theo đúng yêu cầu đặc tả đề bài (Tối thiểu 15 Unit Test và 5 Kịch bản Tích hợp).

---

## 📁 Cấu trúc Thư mục Kiểm thử

```
/tests
  ├── __init__.py
  ├── conftest.py                # Pytest Fixtures (TestClient, DB setup, environment fallbacks)
  ├── test_unit_member01.py      # 7 Unit Tests (Backend Server, Security, Audit Log, Retention, IDOR)
  ├── test_unit_member02.py      # 8 Unit Tests (Agent Logic, SHA256 Hashing, DNS Parser, Quota, Offline Queue)
  └── test_integration.py        # 5 Integration Test Scenarios (Flow Đăng ký, Sync Policy, Events, Emergency, Request)
```

---

## 🧪 Chi tiết Danh mục Kiểm thử

### 1. Unit Tests (15 Tests)

| # | Test Name | Mô tả & Thành phần kiểm thử | Phụ trách |
|---|---|---|---|
| **UT01** | `test_hash_password_argon2id` | Xác thực băm mật khẩu bảo mật Argon2id / SHA256 | TV01 |
| **UT02** | `test_policy_hmac_signature` | Kiểm tra tính toàn vẹn chữ ký HMAC-SHA256 của Policy | TV01 |
| **UT03** | `test_enrollment_code_expiration` | Kiểm tra mã ghép đôi 8 ký tự tự động hết hạn sau 10 phút | TV01 |
| **UT04** | `test_audit_log_format` | Kiểm tra định dạng Nhật ký kiểm toán Audit Log (NT5) | TV01 |
| **UT05** | `test_event_schema_validation` | Kiểm tra Lược đồ Sự kiện Nghị định 13/2023 (Tối thiểu dữ liệu, không lưu URL) | TV01 |
| **UT06** | `test_data_retention_purge` | Kiểm tra tác vụ tự động xóa dữ liệu quá hạn 90 ngày | TV01 |
| **UT07** | `test_parent_ownership_idor` | Kiểm tra phân quyền truy cập thiết bị (Chống lỗ hổng IDOR) | TV01 |
| **UT08** | `test_sha256_exe_hashing` | Băm SHA-256 tệp thực thi (Nhận diện ứng dụng đổi tên) | TV02 |
| **UT09** | `test_process_matching` | Đối chiếu danh sách ứng dụng cấm theo tên tiến trình & mã băm SHA256 | TV02 |
| **UT10** | `test_dns_packet_parser` | Parse gói tin truy vấn tên miền DNS proxy 127.0.0.1:53 | TV02 |
| **UT11** | `test_dns_blocklist_filter` | Khớp tên miền bị chặn và tên miền con (subdomain wildcard) | TV02 |
| **UT12** | `test_safesearch_dns_rewrite` | Cưỡng chế SafeSearch bằng ánh xạ DNS sang forcesafesearch | TV02 |
| **UT13** | `test_time_schedule_checker` | Kiểm tra ma trận lịch tuần cấm/cho phép (độ phân giải giờ) | TV02 |
| **UT14** | `test_quota_counter_decrement` | Đếm thời gian sử dụng thực tế và tính quota còn lại | TV02 |
| **UT15** | `test_offline_queue_batching` | Lưu sự kiện vào hàng đợi SQLite cục bộ và gom lô đồng bộ | TV02 |

---

### 2. Integration Tests (5 Kịch bản Tích hợp)

1. **`test_scenario1_enrollment_flow`**: Quy trình ghép đôi (Enrollment) từ Đăng ký Phụ huynh/Trẻ ➔ Tạo mã 8 số ➔ Agent gửi Fingerprint ➔ Nhận Token & Device ID.
2. **`test_scenario2_policy_sync_flow`**: Quy trình cập nhật chính sách từ Dashboard ➔ Tăng Policy Version ➔ Nhịp tim (Heartbeat) phát hiện lệch phiên bản ➔ Agent gọi `GET /policy` đồng bộ.
3. **`test_scenario3_event_logging_reporting_flow`**: Agent đệm sự kiện offline ➔ Đồng bộ lô `POST /api/events/batch` ➔ Dashboard hiển thị Biểu đồ & Top 10.
4. **`test_scenario4_websocket_emergency_command_flow`**: Lệnh khẩn cấp qua WebSocket (Khóa máy ngay) đạt độ trễ < 5 giây.
5. **`test_scenario5_time_request_approval_flow`**: Trẻ bấm 'Xin thêm giờ' từ Tray UI ➔ Phụ huynh duyệt +15p ➔ Agent tự động cộng quota.

---

## 🚀 Hướng dẫn Chạy Kiểm thử (Run Tests)

Mở Terminal trong thư mục gốc của dự án (`QuanLiMayTinhTreEm`) và kích hoạt `venv`:

```powershell
# 1. Kích hoạt venv (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# 2. Chạy toàn bộ bộ kiểm thử
pytest tests/ -v

# 3. Chỉ chạy Unit Tests của Thành viên 01
pytest tests/test_unit_member01.py -v

# 4. Chỉ chạy Unit Tests của Thành viên 02
pytest tests/test_unit_member02.py -v

# 5. Chỉ chạy 5 Kịch bản Tích hợp
pytest tests/test_integration.py -v
```
