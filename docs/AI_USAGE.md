# KHAI BÁO SỬ DỤNG CÔNG CỤ TRÍ TUỆ NHÂN TẠO (AI USAGE REPORT)
**Dự án:** OpenGuardKids - Ứng dụng hỗ trợ quản lý việc sử dụng máy tính của trẻ em  
**Học phần:** Chuyên đề Tốt nghiệp / Đồ án Mạng Máy tính — Khoa CNTT, HCMUS  
**Tài liệu tuân thủ:** Mục 8 (Sản phẩm phải nộp), Trang 12 Đồ án môn học OpenGuardKids  

---

## I. CHÍNH SÁCH VÀ NGUYÊN TẮC SỬ DỤNG AI

Nhóm sinh viên thực hiện đồ án tuân thủ nghiêm ngặt quy định về liêm chính học thuật:
1. **Công cụ AI đóng vai trò trợ lý (Pair Programmer / Assistant):** Hỗ trợ tra cứu tài liệu kỹ thuật, gợi ý cú pháp, tối ưu hóa giao diện và cấu trúc mã nguồn ban đầu.
2. **Sinh viên chịu trách nhiệm 100%:** Toàn bộ kiến trúc hệ thống, thuật toán cốt lõi, cơ chế bảo mật và quyết định kỹ thuật đều do thành viên nhóm trực tiếp kiểm soát, chỉnh sửa, kiểm chứng và bảo vệ trước hội đồng phản biện.
3. **Mọi đoạn mã do AI gợi ý đều được kiểm thử độc lập:** Đảm bảo vượt qua bộ 20 bài kiểm thử tự động (`pytest`) và chạy thử nghiệm thực tế trên môi trường Windows sạch.

---

## II. BẢNG KHAI BÁO CHI TIẾT SỬ DỤNG CÔNG CỤ AI

| STT | Thành phần / Module chức năng | Công cụ AI sử dụng | Nội dung cụ thể do AI hỗ trợ | Phương pháp và Bằng chứng kiểm chứng của nhóm sinh viên |
|:---:|:---|:---|:---|:---|
| **1** | **Khung dịch vụ Server (FastAPI & SQLAlchemy)** | Google Antigravity / Gemini 3.1 Pro | Gợi ý cấu trúc thư mục chuẩn modular (`app/api`, `models`, `schemas`) và mã khung (boilerplate) cho các Pydantic schemas. | Nhóm tự điều chỉnh mô hình dữ liệu quan hệ (1 phụ huynh : $n$ trẻ : $m$ thiết bị), tích hợp logic bảo mật IDOR ở tầng truy vấn và cơ chế dọn dẹp dữ liệu tự động 90 ngày. |
| **2** | **Bộ dữ liệu 200 tên miền phân loại (F2)** | Claude 3.5 Sonnet / Gemini | Hỗ trợ tổng hợp danh sách mẫu 200 tên miền phân chia đều theo 6 nhóm chuyên đề (Giáo dục, Giải trí, Mạng xã hội, Game...). | Sinh viên kiểm duyệt thủ công từng tên miền; đảm bảo **100% tên miền giáo dục không bị dương tính giả**, tuyệt đối loại bỏ các tên miền nhạy cảm theo quy chế đồ án. |
| **3** | **DNS Proxy Server (`agent/dns_proxy.py`)** | Google Antigravity / Gemini | Gợi ý cú pháp giải mã gói tin DNS bằng thư viện `dnslib` và các địa chỉ IP SafeSearch VIP của Google/Bing/YouTube. | Sinh viên kiểm chứng bằng công cụ dòng lệnh `nslookup -port=53` và Wireshark bắt gói tin UDP/53; đo đạc độ trễ p50/p95 trước và sau khi kích hoạt proxy. |
| **4** | **Kiểm soát ứng dụng & SHA-256 (`app_controller.py`)** | Gemini / Copilot | Gợi ý hàm đọc tệp exe theo từng khối nhị phân 64KB (`chunked read`) để tính mã băm SHA-256 hiệu năng cao. | Sinh viên thử nghiệm thực tế kịch bản đổi tên file `notepad.exe` thành `game.exe` trên Windows 11 để xác nhận việc nhận diện đúng mã băm. |
| **5** | **Đồng hồ đếm giờ & Chống lùi giờ (`enforcer.py`)** | Gemini 3.1 Pro | Gợi ý sử dụng `time.monotonic()` và cấu trúc `LASTINPUTINFO` từ `ctypes.windll.user32` để lấy thời gian idle. | Sinh viên viết kịch bản giả lập lùi giờ hệ thống 3 tiếng; kiểm tra bộ đếm quota không bị tăng và hệ thống kích hoạt cảnh báo ghi log chính xác. |
| **6** | **Thiết kế Giao diện UI/UX (Màn hình Trẻ em & Phụ huynh)** | Google Antigravity | Gợi ý bản mẫu CSS Glassmorphism, phối màu pastel ấm áp theo phong cách "Orange Charming" và tích hợp Google Fonts (`Amatic SC`, `Itim`). | Sinh viên tích hợp động với template Jinja2, kiểm thử hiển thị responsive trên thiết bị di động (Chrome DevTools Mobile) và bổ sung nội dung cấp 1 cho trẻ em. |
| **7** | **Bộ kiểm thử tự động (`tests/`)** | Gemini 3.1 Pro | Gợi ý khung viết fixture `pytest` với cơ sở dữ liệu SQLite in-memory cho các kịch bản test API. | Sinh viên tự viết toàn bộ 15 Unit Test và 5 Kịch bản tích hợp; xác nhận 20/20 test case đều pass với thời gian thực thi `< 1` giây. |

---

## III. CAM KẾT CỦA NHÓM SINH VIÊN

Nhóm sinh viên cam kết:
1. Bản khai báo trên là trung thực và phản ánh chính xác quá trình ứng dụng AI trong quá trình thực hiện đồ án OpenGuardKids.
2. Không sử dụng mã nguồn đóng, mã nguồn vi phạm bản quyền hay các dịch vụ phân tích dữ liệu bên thứ ba trái phép.
3. Từng thành viên trong nhóm nắm vững tường tận từng dòng mã nguồn và sẵn sàng trả lời trực tiếp mọi câu hỏi kỹ thuật trong buổi vấn đáp đồ án.
