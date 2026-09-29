# CHÍNH SÁCH BẢO MẬT và BẢO VỆ DỮ LIỆU CÁ NHÂN (PRIVACY POLICY)
**Dự án:** OpenGuardKids - Hệ thống quản lý và bảo vệ trẻ em sử dụng máy tính  
**Phiên bản:** 1.0   
**Ngày cập nhật:** 29/09/2026  

---

## I. TỔNG QUAN VÀ MỤC ĐÍCH

`PRIVACY.md` là **Tài liệu ánh xạ tuân thủ pháp lý** của đồ án **OpenGuardKids**. 

Tài liệu này xác định:
1. Toàn bộ các trường dữ liệu được thu thập, xử lý và lưu trữ trong hệ thống.
2. Cơ sở pháp lý và mục đích thu thập từng loại dữ liệu theo pháp luật Việt Nam và tiêu chuẩn quốc tế.
3. Sự ánh xạ trực tiếp giữa các quy định pháp lý với các thành phần mã nguồn (`models.py`, `schemas.py`, `main_agent.py`, `main.py`).
4. Thời hạn lưu trữ, phân quyền truy cập và chính sách tiêu hủy dữ liệu.
5. Bản điều khoản riêng biệt dành riêng cho trẻ em độc giả (Child-Friendly Version).

---

## II. BẢNG ÁNH XẠ KHUNG PHÁP LÝ & TIÊU CHUẨN AN TOÀN

Hệ thống OpenGuardKids được thiết kế dựa trên sự cân bằng giữa **quyền giám sát hợp pháp của phụ huynh** và **quyền bí mật đời sống riêng tư của trẻ em**.

| STT | Văn bản / Tiêu chuẩn | Điều khoản | Nội dung áp dụng trong OpenGuardKids | Thành phần mã nguồn tuân thủ |
|:---:|:---|:---|:---|:---|
| **1** | **Luật Trẻ em 2016** | **Điều 21** (Quyền bí mật đời sống riêng tư) | Dữ liệu thu thập chỉ phục vụ mục đích bảo vệ trẻ khỏi nội dung độc hại (lợi ích tốt nhất của trẻ). Không thu thập tin nhắn cá nhân, webcam, nội dung trao đổi riêng tư. | `server/models.py` (chỉ lưu metadata thiết bị & sự kiện chặn), `agent/dns_proxy.py` |
| **2** | **Luật An ninh mạng 2018** | **Điều 29** (Bảo vệ trẻ em trên không gian mạng) | Kiểm soát, ngăn chặn các truy cập đến trang web độc hại; tạo môi trường mạng an toàn cho trẻ giải trí, học tập. | `agent/dns_proxy.py`, `agent/monitor_app.py`, `server/models.py` (`EventModel`) |
| **3** | **Nghị định 13/2023/NĐ-CP** | **Điều 3** (8 Nguyên tắc bảo vệ DLCN) | Thu thập đúng mục đích, tối thiểu hóa dữ liệu (Data Minimization), lưu trữ có thời hạn, đảm bảo an toàn bảo mật. | `server/main.py`, `server/models.py`, `agent/main_agent.py` |
| **4** | **Nghị định 13/2023/NĐ-CP** | **Điều 8** (Hành vi bị nghiêm cấm) | Cam kết không mua bán, kinh doanh, chia sẻ dữ liệu cho bên thứ ba dưới bất kỳ hình thức nào. | Toàn bộ hệ thống OpenGuardKids (Self-hosted / Private Database) |
| **5** | **Nghị định 13/2023/NĐ-CP** | **Điều 9** (Xử lý DLCN của Trẻ em) | Bắt buộc phải có sự đồng ý của cha mẹ/người giám hộ và sự đồng thuận của trẻ (được giải thích qua phiên bản dành cho trẻ). | `server/main.py` (`/auth/enroll`), `docs/PRIVACY.md` (Phần VI) |
| **6** | **Quyết định 830/QĐ-TTg (2021)** | Chương trình bảo vệ & hỗ trợ trẻ em trên mạng | Kết hợp giữa bảo vệ thụ động (chặn lọc web) và chủ động (thống kê giúp trẻ tự quản lý thời gian). | Dashboard Phụ huynh (`server/templates/dashboard.html`), `server/main.py` |
| **7** | **OWASP ASVS v4** | **Level 1** (V4 Access Control, V14 Data Protection) | Mã hóa kết nối API, phân quyền chỉ cha mẹ xem được thiết bị đã ghép đôi, không để lộ thông tin nhạy cảm qua API public. | `server/main.py`, `schemas.py`, `agent/main_agent.py` |
| **8** | **NIST SP 800-63B** | Xác thực & Quản lý vòng đời (Digital Identity) | Sử dụng mã ghép đôi một lần (Enrollment Code - 8 ký tự, hết hạn 10 phút) và cấp Token định danh thiết bị duy nhất (UUIDv4). | `server/main.py` (`/auth/enroll`), `agent/config.json` |

---

## III. BẢNG CHI TIẾT MA TRẬN DỮ LIỆU (DATA MATRIX)

Bảng dưới đây chi tiết hóa toàn bộ thông tin dữ liệu trong hệ thống OpenGuardKids:

| Nhóm dữ liệu | Trường dữ liệu cụ thể | Mục đích thu thập | Thời hạn lưu trữ | Người có quyền xem | Ánh xạ Mã nguồn & Cơ sở dữ liệu |
|:---|:---|:---|:---|:---|:---|
| **Định danh thiết bị & Trẻ em** | `device_id` (UUIDv4) | Định danh duy nhất máy tính trong hệ thống | Trọn đời ứng dụng (cho đến khi Hủy ghép đôi) | Phụ huynh, Hệ thống Agent | `server/models.py` (`DeviceModel.device_id`)<br>`agent/config.json` (`device_id`) |
| | `device_name` | Nhận biết máy tính (vd: PC Phòng Khách) | Trọn đời ứng dụng | Phụ huynh | `server/models.py` (`DeviceModel.device_name`)<br>`server/schemas.py` (`EnrollRequest`) |
| | `child_name` | Cá nhân hóa chính sách bảo vệ cho bé | Trọn đời ứng dụng | Phụ huynh | `server/models.py` (`DeviceModel.child_name`) |
| | `device_fingerprint` | Xác thực môi trường OS ban đầu (Phase 1) | Lưu tạm khi Ghép đôi | Phụ huynh, Hệ thống Server | `agent/main_agent.py` (`enroll_device`) |
| **Trạng thái & Giám sát** | `last_seen` (Timestamp) | Xác định máy tính đang Online hay Offline | Cập nhật đè (Chỉ giữ mốc mới nhất) | Phụ huynh | `server/models.py` (`DeviceModel.last_seen`)<br>`server/main.py` (`receive_heartbeat`) |
| | `status` | Hiển thị cảnh báo kết nối trên Dashboard | Cập nhật đè (Online/Offline) | Phụ huynh | `server/models.py` (`DeviceModel.status`) |
| | `policy_version` | Đồng bộ quy tắc bảo vệ mới nhất giữa Server và Agent | Trọn đời ứng dụng | Phụ huynh, Agent | `server/models.py` (`DeviceModel.policy_version`)<br>`server/models.py` (`PolicyModel.version`) |
| **Nhật ký Sự kiện (Events)** | `event_type` (DNS_BLOCK, APP_BLOCK...) | Báo cáo các hành vi vi phạm chính sách bảo vệ | 30 ngày (Tự động xoay vòng/xóa) | Phụ huynh | `server/models.py` (`EventModel.event_type`) |
| | `subject` (Domain/Tên ứng dụng) | Giúp phụ huynh biết trang web/ứng dụng nguy hại bị chặn | 30 ngày | Phụ huynh | `server/models.py` (`EventModel.subject`) |
| | `timestamp` | Ghi nhận thời điểm xảy ra sự kiện | 30 ngày | Phụ huynh | `server/models.py` (`EventModel.timestamp`) |
| **Xác thực & Cấu hình** | `enroll_code` | Mã xác thực 8 ký tự để ghép đôi an toàn | Tối đa 10 phút (Xóa ngay sau khi dùng) | Phụ huynh | `server/main.py` (`enroll_device`) |
| | `access_token` | Xác thực API giữa Agent và Server | Thay đổi khi ghép đôi lại | Agent (Lưu cục bộ) | `agent/config.json` (`access_token`) |

---

## IV. BIỆN PHÁP BẢO MẬT VÀ QUY TRÌNH QUẢN LÝ DỮ LIỆU

1. **Bảo mật khi truyền tải (Data in Transit):**
   - Mọi giao tiếp giữa Agent và Server được thực hiện qua giao thức HTTPS (TLS 1.3 trong môi trường sản xuất).
   - Mã ghép đôi `enroll_code` có thời hạn 10 phút nhằm ngăn chặn tấn công giả mạo thiết bị theo tiêu chuẩn NIST SP 800-63B.

2. **Bảo mật khi lưu trữ (Data at Rest):**
   - Cơ sở dữ liệu SQLite (`ogk_server.db`) được đặt tại máy chủ riêng của phụ huynh (Self-hosted), không chia sẻ lên đám mây của bên thứ ba.
   - Tệp cấu hình Agent (`config.json`) lưu trữ tại thư mục bảo vệ của hệ điều hành.

3. **Tối thiểu hóa dữ liệu (Data Minimization - Nghị định 13/2023/NĐ-CP):**
   - Hệ thống **KHÔNG** ghi lại thao tác bàn phím (Keylogger), **KHÔNG** chụp màn hình khi không có cảnh báo, **KHÔNG** theo dõi nội dung trò chuyện riêng tư của trẻ.
   - Chỉ thu thập các metadata cần thiết cho chức năng bảo vệ (tên miền bị chặn, trạng thái kết nối).

4. **Hủy và xóa dữ liệu (Data Retention & Deletion):**
   - Khi phụ huynh thực hiện "Hủy ghép đôi thiết bị", toàn bộ dữ liệu liên quan (`DeviceModel`, `EventModel`) sẽ bị xóa vĩnh viễn khỏi cơ sở dữ liệu.
   - Nhật ký sự kiện (`events`) tự động xóa sau 30 ngày để đảm bảo quyền riêng tư của trẻ.

---

## V. QUYỀN HẠN CỦA PHỤ HUYNH VÀ TRẺ EM

Theo Nghị định 13/2023/NĐ-CP và Luật Trẻ em 2016, chủ thể dữ liệu có các quyền sau:
1. **Quyền được biết và truy cập:** Phụ huynh và trẻ em có thể xem toàn bộ dữ liệu đang được hệ thống thu thập trực tiếp trên Dashboard.
2. **Quyền chỉnh sửa:** Phụ huynh có thể thay đổi tên hiển thị của trẻ (`child_name`), tên thiết bị (`device_name`) bất kỳ lúc nào.
3. **Quyền xóa dữ liệu:** Phụ huynh có quyền yêu cầu xóa nhật ký sự kiện hoặc ngưng sử dụng phần mềm.
4. **Quyền phản đối và đồng thuận:** Trẻ em được giải thích rõ về hoạt động của ứng dụng và có quyền thảo luận cùng cha mẹ về các chính sách an toàn.

---

## VI. PHIÊN BẢN GIAO TIẾP DÀNH RIÊNG CHO TRẺ EM

> 🎈 **Góc dành riêng cho các bạn nhỏ!**  
> *"Chào bạn! Hãy cùng tìm hiểu xem Hiệp sĩ OpenGuardKids bảo vệ bạn như thế nào nhé!"*



### 1. 🌟 OpenGuardKids là ai và giúp gì cho bé?
OpenGuardKids là một "người bảo vệ tí hon" chạy trên máy tính của bé. Giống như việc bé đội mũ bảo hiểm khi đi xe đạp, OpenGuardKids giúp bé tránh khỏi những trang web độc hại, các vi-rút xấu xa và nhắc nhở bé nghỉ ngơi đúng giờ để bảo vệ đôi mắt sáng.

---

### 2. 🔍 Hiệp sĩ OpenGuardKids BIẾT những gì về bé?
Để bảo vệ bé tốt nhất, bạn hiệp sĩ chỉ ghi nhớ một số thông tin rất nhỏ:
- 💻 **Tên máy tính của bé:** Để biết bạn đang bảo vệ máy tính nào (ví dụ: *May-Cua-Bin*).
- 🏷️ **Tên/Biệt danh của bé:** Để gửi lời chào thân thiện (ví dụ: *Bé Bin*).
- 🟢 **Trạng thái máy tính:** Để Bố Mẹ biết máy tính đang bật hay tắt.
- 🚫 **Những trang web nguy hiểm bị ngăn lại:** Khi bé vô tình bấm vào một trang web xấu, phần mềm sẽ chặn lại và ghi nhớ để báo cho Bố Mẹ giúp đỡ bé.

---

### 3. 🙈 Hiệp sĩ OpenGuardKids KHÔNG BAO GIỜ làm gì?
Bố Mẹ và bạn hiệp sĩ rất tôn trọng quyền riêng tư của bé! Vì vậy, phần mềm:
- ❌ **KHÔNG** đọc tin nhắn, thư từ hay cuộc trò chuyện của bé với bạn bè.
- ❌ **KHÔNG** xem mật khẩu cá nhân của bé.
- ❌ **KHÔNG** tự ý bật Webcam hoặc micro để theo dõi bé.
- ❌ **KHÔNG** bán hay gửi thông tin của bé cho bất kỳ ai khác bên ngoài.

---

### 4. 👑 Ai được xem thông tin này?
Chỉ có **Bố Mẹ của bé** mới có thể xem được bảng báo cáo an toàn. Thông tin này giúp Bố Mẹ hiểu và hỗ trợ bé sử dụng máy tính một cách lành mắt và sáng tạo nhất.

---

### 5. 🤝 Quyền của bé
Bé hoàn toàn có quyền:
- Hỏi Bố Mẹ về cách phần mềm OpenGuardKids đang hoạt động.
- Thảo luận cùng Bố Mẹ để điều chỉnh thời gian sử dụng máy tính sao cho hợp lý giữa việc học và chơi!

---
*OpenGuardKids – Đồng hành cùng bé khám phá thế giới Internet an toàn và vui vẻ!* 🚀
