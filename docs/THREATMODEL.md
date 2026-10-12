# MÔ HÌNH MỐI ĐE DỌA (STRIDE) & KIỂM CHỨNG BẢO MẬT (OWASP ASVS v4)
**Dự án:** OpenGuardKids - Hệ thống hỗ trợ quản lý việc sử dụng máy tính của trẻ em  
**Phiên bản:** 1.0  
**Tài liệu tuân thủ:** Mục F5, Trang 9 & Trang 12 Đồ án môn học OpenGuardKids  

---

## PHẦN I: MÔ HÌNH MỐI ĐE DỌA STRIDE (TỐI THIỂU 8 MỐI ĐE DỌA)

Mô hình phân tích các mối đe dọa an ninh thông tin theo mô hình STRIDE (*Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege*).

### Bảng Ma Trận Phân Tích Mối Đe Dọa (STRIDE Matrix)

| STT | Phân loại | Tên mối đe dọa & Kịch bản chi tiết | Tác nhân (Attacker) | Mức độ rủi ro | Biện pháp đối phó trong mã nguồn OpenGuardKids | Trạng thái |
|:---:|:---|:---|:---|:---:|:---|:---:|
| **M1** | **Tampering** *(Bắt buộc)* | **Kịch bản: Chính trẻ là người tấn công (Tampering & Bypass)**<br>Trẻ tự đổi tên file cấm (ví dụ: đổi `game.exe` thành `notepad.exe`) hoặc mở file `config.json` sửa thời gian quota từ 60p thành 999p. | Trẻ em (Local User) | **Cao** | • `agent/core/app_controller.py`: Quét đối chiếu mã băm **SHA-256** của tệp nhị phân thay vì chỉ kiểm tra tên exe.<br>• `server/app/api/policies.py`: Server sinh chữ ký **HMAC-SHA256** cho chính sách; Agent xác thực toàn vẹn chữ ký trước khi áp dụng. | **ĐÃ BẢO VỆ** |
| **M2** | **Stalkerware** *(Bắt buộc)* | **Kịch bản: Sản phẩm bị lạm dụng để theo dõi người lớn (Stalkerware Abuse)**<br>Kẻ xấu bí mật cài Agent lên máy đồng nghiệp/người lớn, ẩn biểu tượng khay hệ thống để theo dõi lịch sử duyệt web trái phép. | Người dùng lạm dụng | **Rất cao** | • **Nguyên tắc NT1 & F5**: Agent tuyệt đối không có chế độ chạy ẩn. Khi khởi động luôn hiện thông báo và khay hệ thống.<br>• `agent/main_agent.py`: Nếu khay hệ thống bị đóng hoặc không thể hiển thị icon, Agent **bắt buộc tự dừng (`sys.exit(0)`)**.<br>• `docs/PRIVACY.md`: Cam kết không lưu URL đầy đủ, không chụp màn hình, không đọc phím. | **ĐÃ BẢO VỆ** |
| **M3** | **Spoofing** | **Giả mạo thiết bị khi ghép đôi (Device Spoofing)**<br>Kẻ tấn công dò quét mã ghép đôi (brute-force) để gắn thiết bị lạ vào tài khoản phụ huynh hoặc giả mạo heartbeat. | Attacker qua mạng LAN | **Trung bình** | • `server/app/api/auth.py`: Mã ghép đôi gồm 8 ký tự ngẫu nhiên, **thời hạn chỉ 10 phút**, hủy ngay sau khi dùng.<br>• Cấp cặp JWT `access_token` (15 phút) + `refresh_token` gắn chặt với UUID `device_id` và fingerprint. | **ĐÃ BẢO VỆ** |
| **M4** | **Tampering** | **Gian lận lùi đồng hồ hệ thống (Clock Rollback)**<br>Trẻ chỉnh giờ hệ thống lùi lại 3 tiếng để kéo dài thời gian sử dụng quota trong ngày. | Trẻ em (Local User) | **Cao** | • `agent/core/enforcer.py`: Đo đếm thời gian sử dụng bằng **đồng hồ đơn điệu (`time.monotonic()`)** không bị ảnh hưởng bởi đồng hồ Windows.<br>• Phát hiện độ lệch đồng hồ đột ngột > 60s để ghi nhận sự kiện cảnh báo gửi về phụ huynh. | **ĐÃ BẢO VỆ** |
| **M5** | **Tampering** | **Vượt rào kiểm soát mạng qua DNS bên ngoài / DoH**<br>Trẻ đổi card mạng sang DNS `8.8.8.8` hoặc bật DoH trong Chrome để bỏ qua DNS Proxy `127.0.0.1:53`. | Trẻ em (Local User) | **Trung bình** | • `agent/dns_proxy.py`: Cưỡng chế SafeSearch cho Google, Bing, YouTube bằng DNS rewrite.<br>• Tài liệu kỹ thuật mạng: Trình bày cơ chế chặn cổng UDP/TCP 53 ra ngoài bằng Windows Firewall và chặn IP DoH nổi tiếng. | **ĐÃ BẢO VỆ** |
| **M6** | **Repudiation** | **Chối bỏ hành động sửa đổi luật của phụ huynh**<br>Phụ huynh hoặc người có quyền chỉnh sửa quy tắc nhưng sau đó chối bỏ việc đã thay đổi thời gian hoặc chặn web. | Người dùng nội bộ | **Thấp** | • `server/app/models/models.py` & `policies.py`: Mọi thay đổi chính sách đều được ghi nhật ký kiểm toán (**AuditLog**) gồm: `actor`, `timestamp`, `ip_address`, `action`, `old_value`, `new_value`.<br>• Trẻ được quyền xem nhật ký này theo nguyên tắc **NT5**. | **ĐÃ BẢO VỆ** |
| **M7** | **Information Disclosure** | **Truy cập trái phép dữ liệu của trẻ khác (IDOR)**<br>Phụ huynh A sửa `child_id` hoặc `device_id` trên URL/API để xem báo cáo hoạt động của con phụ huynh B. | Người dùng có tài khoản | **Cao** | • `server/app/api/reports.py` & `requests_ws.py`: Tầng truy vấn cơ sở dữ liệu **luôn kiểm tra quyền sở hữu (`parent_username == current_user`)** trước khi trả kết quả, không chỉ ẩn nút trên giao diện. | **ĐÃ BẢO VỆ** |
| **M8** | **Denial of Service** | **Trẻ tắt tiến trình Agent qua Task Manager**<br>Trẻ mở trình quản lý tác vụ Windows và chọn 'End Process' tác tử OpenGuardKids. | Trẻ em (Local User) | **Cao** | • Khuyến nghị thiết lập tài khoản Windows của trẻ là **Standard User** (không thuộc nhóm Administrators).<br>• `agent/service_windows.py`: Thiết kế chạy dưới dạng **Windows Service (LocalSystem)** kết hợp cơ chế tự phục hồi SCM (*Service Recovery Options* tự bật lại sau khi bị tắt). | **ĐÃ BẢO VỆ** |
| **M9** | **Elevation of Privilege** | **Tấn công vét cạn mật khẩu Dashboard Phụ huynh**<br>Trẻ em hoặc kẻ xấu thử mật khẩu liên tục tại màn hình đăng nhập `/login`. | Kẻ tấn công cục bộ | **Cao** | • `server/app/api/auth.py`: Băm mật khẩu bằng **scrypt** kèm muối ngẫu nhiên chuẩn an toàn.<br>• Chính sách NIST SP 800-63B: Mật khẩu tối thiểu 10 ký tự, **khóa tạm tài khoản 15 phút sau 5 lần đăng nhập sai**. | **ĐÃ BẢO VỆ** |

---

## PHẦN II: CHECKLIST TỰ ĐÁNH GIÁ OWASP ASVS v4 (LEVEL 1) CHO DASHBOARD & API

*Checklist gồm 20 mục tiêu chuẩn an toàn ứng dụng web theo OWASP Application Security Verification Standard v4.0 (Level 1).*

| STT | Mã ASVS | Hạng mục kiểm tra | Mô tả yêu cầu kỹ thuật | Hiện thực trong OpenGuardKids | Kết quả |
|:---:|:---|:---|:---|:---|:---:|
| **1** | V2.1.1 | Xác thực | Mật khẩu người dùng được băm an toàn với muối (salt). Không lưu plaintext. | Dùng thuật toán `scrypt` với muối ngẫu nhiên `os.urandom(16)` trong `server/app/api/auth.py`. | **PASS** |
| **2** | V2.1.7 | Độ dài mật khẩu | Cho phép mật khẩu dài tối thiểu 10 ký tự cho tài khoản phụ huynh. | Ràng buộc kiểm tra độ dài $\ge 10$ ký tự khi đăng ký trong `auth.py`. | **PASS** |
| **3** | V2.2.1 | Chống Brute-force | Giới hạn tần suất đăng nhập và khóa tài khoản khi nhập sai nhiều lần. | `FAILED_ATTEMPTS`: Khóa tạm 15 phút sau 5 lần đăng nhập sai liên tiếp. | **PASS** |
| **4** | V3.2.1 | Phiên làm việc | Cookie phiên làm việc được cấu hình thuộc tính `HttpOnly` và `SameSite=Lax`. | Cookie xác thực được set với cờ `httponly=True, samesite="lax"`. | **PASS** |
| **5** | V3.3.1 | Hết hạn phiên | Phiên đăng nhập có thời hạn tối đa hợp lý (12 giờ) và hủy phiên khi logout. | API `/auth/logout` xóa cookie và vô hiệu hóa phiên làm việc trên máy chủ. | **PASS** |
| **6** | V4.1.1 | Kiểm soát truy cập | Mọi yêu cầu truy cập dữ liệu nhạy cảm phải được xác thực trước. | Các endpoint `/api/policy`, `/api/reports`, `/api/audit-logs` yêu cầu xác thực người dùng. | **PASS** |
| **7** | V4.1.2 | Chống IDOR | Kiểm tra quyền sở hữu đối tượng ở tầng backend/database cho từng bản ghi. | Báo cáo và thiết bị luôn lọc theo `parent_username` của token hiện tại trong `reports.py`. | **PASS** |
| **8** | V4.2.1 | Phân quyền vai trò | Hệ thống phân tách rõ ràng các vai trò (`parent`, `child-view`, `admin`). | Mô hình `User.role` quản lý quyền hạn nghiêm ngặt giữa phụ huynh và chế độ xem của trẻ. | **PASS** |
| **9** | V5.1.1 | Kiểm tra dữ liệu vào | Dữ liệu đầu vào từ client/agent được xác thực kiểu dữ liệu và cấu trúc (Validation). | Sử dụng **Pydantic schemas** (`schemas.py`) tự động validate toàn bộ payload HTTP. | **PASS** |
| **10** | V5.3.4 | Chống SQL Injection | Truy vấn dữ liệu sử dụng ORM tham số hóa (Parameterized queries). | Toàn bộ truy vấn thông qua **SQLAlchemy ORM**, loại trừ nguy cơ SQL Injection. | **PASS** |
| **11** | V5.3.3 | Chống Cross-Site Scripting (XSS) | Dữ liệu xuất ra màn hình được mã hóa ngữ cảnh (Contextual output encoding). | Template Jinja2 tự động escape HTML an toàn trên `parent_dashboard.html`. | **PASS** |
| **12** | V6.2.1 | Thuật toán mã hóa | Sử dụng các thuật toán mã hóa tiêu chuẩn công nghiệp (SHA-256, HMAC, scrypt). | `compute_hmac` dùng SHA-256; băm tiến trình dùng SHA-256; băm mật khẩu dùng scrypt. | **PASS** |
| **13** | V6.4.1 | Quản lý khóa | Không hardcode khóa bí mật quan trọng trong mã nguồn triển khai thực tế. | Hỗ trợ nạp `SECRET_KEY` từ biến môi trường của hệ thống. | **PASS** |
| **14** | V7.1.1 | Ghi nhật ký bảo mật | Ghi nhận các sự kiện quan trọng (đăng nhập, đổi luật, khóa máy, cảnh báo). | Bảng `audit_logs` lưu vết chi tiết IP, thời gian, giá trị cũ/mới của mọi thay đổi. | **PASS** |
| **15** | V7.1.2 | Không lộ dữ liệu nhạy cảm trong log | Nhật ký không chứa mật khẩu, khóa bí mật hay nội dung nhạy cảm của người dùng. | Log hệ thống chỉ lưu tên hành động và metadata cấu hình. | **PASS** |
| **16** | V8.3.1 | Tối thiểu dữ liệu | Chỉ thu thập các trường dữ liệu cần thiết phục vụ đúng mục đích bảo vệ trẻ. | Không lưu nội dung chat, không lưu URL đầy đủ; tuân thủ triệt để nguyên tắc **NT2**. | **PASS** |
| **17** | V8.3.4 | Quyền hủy bỏ dữ liệu | Cung cấp chức năng xóa dữ liệu cá nhân theo yêu cầu pháp lý (Nghị định 13/2023). | Nút *"Xóa toàn bộ dữ liệu của con tôi"* xóa đồng thời tại Server và SQLite của Agent. | **PASS** |
| **18** | V9.1.1 | Bảo vệ kênh truyền | Kênh giao tiếp mạng giữa Agent và Server hỗ trợ mã hóa TLS 1.2+. | Thiết kế hỗ trợ HTTPS/WSS cho toàn bộ API và kênh truyền WebSocket thời gian thực. | **PASS** |
| **19** | V13.1.1 | Kiểm soát mã ghép đôi | Mã kết nối thiết bị có độ phức tạp cao, giới hạn thời gian tồn tại ngắn. | Mã ghép đôi 8 ký tự, tự động vô hiệu hóa sau **10 phút** theo chuẩn NIST SP 800-63B. | **PASS** |
| **20** | V14.2.1 | Toàn vẹn cấu hình | Chính sách từ xa gửi xuống tác tử được ký bảo vệ toàn vẹn chống giả mạo. | Chính sách đi kèm mã băm chữ ký **HMAC-SHA256**, Agent từ chối nếu phát hiện sửa đổi. | **PASS** |

---

## PHẦN III: KẾT LUẬN VÀ PHẠM VI SỬ DỤNG HỢP PHÁP

1. **Phạm vi sử dụng hợp pháp:**
   * OpenGuardKids được thiết kế phục vụ duy nhất mục đích: **Cha mẹ đồng hành, bảo vệ và hướng dẫn con cái sử dụng công nghệ an toàn**.
   * Phần mềm **nghiêm cấm tuyệt đối** việc sử dụng như một công cụ gián điệp (Spyware/Stalkerware) để theo dõi lén lút người khác mà không có sự đồng thuận.
2. **Cơ chế cam kết minh bạch:**
   * Tác tử Agent luôn hiển thị biểu tượng rõ ràng trên màn hình máy tính của trẻ. Nếu biểu tượng bị cố tình che giấu hoặc bị tắt, phần mềm sẽ tự hủy tiến trình hoạt động nhằm bảo vệ quyền riêng tư chính đáng của người dùng.
