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
| **Định danh thiết bị & Trẻ em** | `device_id` (UUIDv4) | Định danh duy nhất máy tính trong hệ thống | Trọn đời ứng dụng (cho đến khi Hủy ghép đôi) | Phụ huynh, Hệ thống Agent | `server/app/models/models.py` (`Device.id`)<br>`agent/config.json` (`device_id`) |
| | `device_name` | Nhận biết máy tính (vd: Laptop Bé An) | Trọn đời ứng dụng | Phụ huynh | `server/app/models/models.py` (`Device.device_name`) |
| | `child_name` / `child_id` | Cá nhân hóa chính sách bảo vệ cho trẻ | Trọn đời ứng dụng | Phụ huynh, Trẻ em (màn hình minh bạch) | `server/app/models/models.py` (`Device.child_id`) |
| | `device_fingerprint` | Xác thực môi trường OS ban đầu (NĐ 13/2023) | Lưu tạm khi Ghép đôi | Phụ huynh, Hệ thống Server | `agent/core/sync.py` (`get_device_fingerprint`) |
| **Trạng thái & Giám sát** | `last_seen` (Timestamp) | Xác định máy tính đang Online hay Offline | Cập nhật đè (Chỉ giữ mốc mới nhất) | Phụ huynh | `server/app/models/models.py` (`Device.last_seen`) |
| | `status` | Hiển thị cảnh báo kết nối trên Dashboard | Cập nhật đè (online/offline) | Phụ huynh | `server/app/models/models.py` (`Device.status`) |
| | `policy_version` | Đồng bộ quy tắc bảo vệ mới nhất giữa Server và Agent | Trọn đời ứng dụng | Phụ huynh, Agent | `server/app/models/models.py` (`Device.policy_version`) |
| **Nhật ký Sự kiện (Events - Lược đồ F3)** | `ts` (Timestamp UTC) | Ghi nhận thời điểm xảy ra sự kiện | Tối đa 90 ngày (Nghị định 13/2023) | Phụ huynh, Trẻ em | `server/app/models/models.py` (`Event.ts`) |
| | `type` (app_start, blocked_domain...) | Phân loại hành vi giám sát và bảo vệ | Tối đa 90 ngày | Phụ huynh, Trẻ em | `server/app/models/models.py` (`Event.type`) |
| | `subject` (Tên miền cấp hai / Tên file exe) | Nhận diện ứng dụng hoặc website liên quan | Tối đa 90 ngày | Phụ huynh, Trẻ em | `server/app/models/models.py` (`Event.subject`) |
| | `duration_sec` | Thống kê tổng thời lượng sử dụng máy tính | Tối đa 90 ngày | Phụ huynh, Trẻ em | `server/app/models/models.py` (`Event.duration_sec`) |
| | `policy_id` | Ánh xạ phiên bản chính sách đang áp dụng | Tối đa 90 ngày | Phụ huynh, Hệ thống | `server/app/models/models.py` (`Event.policy_id`) |
| **Xác thực & Cấu hình** | `enroll_code` | Mã xác thực 8 ký tự để ghép đôi an toàn | Tối đa 10 phút (Hết hạn hoặc xóa sau khi dùng) | Phụ huynh | `server/app/models/models.py` (`EnrollCode`) |
| | `access_token` / `refresh_token` | Xác thực API giữa Agent và Server (15p + dài hạn) | Thu hồi khi hủy thiết bị | Agent (Lưu cục bộ) | `agent/config.json` (`access_token`) |

---

## IV. BIỆN PHÁP BẢO MẬT VÀ QUY TRÌNH QUẢN LÝ DỮ LIỆU

1. **Bảo mật khi truyền tải (Data in Transit):**
   - Mọi giao tiếp giữa Agent và Server được thực hiện qua giao thức HTTPS (TLS 1.2+).
   - Mã ghép đôi `enroll_code` có thời hạn 10 phút nhằm ngăn chặn tấn công giả mạo thiết bị theo tiêu chuẩn NIST SP 800-63B.

2. **Bảo mật khi lưu trữ (Data at Rest):**
   - Cơ sở dữ liệu SQLite (`ogk_server.db`) được đặt tại máy chủ riêng của phụ huynh (Self-hosted), hỗ trợ WAL mode.
   - Trường nhạy cảm mã hóa AES-GCM; khóa bảo mật lấy từ biến môi trường.
   - Thư mục cấu hình và bộ đệm của Agent đặt quyền ACL chỉ `SYSTEM` và `Administrators` được ghi.

3. **Tối thiểu hóa dữ liệu (Data Minimization - Nghị định 13/2023/NĐ-CP & NT2):**
   - Hệ thống **KHÔNG** ghi lại thao tác bàn phím (Keylogger), **KHÔNG** chụp màn hình, **KHÔNG** đọc tin nhắn / tài liệu cá nhân, **KHÔNG** lưu URL đầy đủ hay tiêu đề cửa sổ.
   - Trường `subject` chỉ lưu tên miền cấp hai hoặc tên tiến trình thực thi (.exe).

4. **Hủy và xóa dữ liệu (Data Retention & Deletion - F3 & NĐ 13/2023):**
   - Thời hạn lưu trữ sự kiện tối đa là **90 ngày**, hệ thống có tác vụ tự động dọn dẹp các bản ghi quá hạn.
   - Cung cấp nút **"Xóa toàn bộ dữ liệu của con tôi"**: Khi phụ huynh kích hoạt, server sẽ xóa toàn bộ dữ liệu sự kiện trên cơ sở dữ liệu đồng thời phát lệnh WebSocket yêu cầu Agent dọn sạch toàn bộ bộ đệm sự kiện ngoại tuyến cục bộ (`agent_events.db`).

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
