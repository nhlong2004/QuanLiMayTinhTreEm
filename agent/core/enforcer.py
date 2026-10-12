import ctypes
from ctypes import Structure, c_uint, sizeof, byref
import datetime
import json
import os
import sys
import time
import threading

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

class LASTINPUTINFO(Structure):
    _fields_ = [
        ("cbSize", c_uint),
        ("dwTime", c_uint)
    ]

def get_idle_duration_sec() -> float:
    """Lấy số giây người dùng không thao tác phím/chuột qua Win32 API GetLastInputInfo"""
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
    except Exception:
        pass
    return 0.0

class TimeEnforcer:
    def __init__(self, on_event_callback=None):
        # M6: Sử dụng đồng hồ đơn điệu (monotonic clock) chống gian lận lùi đồng hồ hệ thống
        self.last_mono = time.monotonic()
        self.last_wall_time = time.time()
        self.bonus_minutes = 0
        self.is_emergency_locked = False
        self.active_usage_seconds = 0.0
        self.on_event_callback = on_event_callback

        # Quản lý cảnh báo trước 10, 5, 1 phút (F1 BẮT BUỘC)
        self.warned_10 = False
        self.warned_5 = False
        self.warned_1 = False
        self.grace_active = False

    def update_usage(self):
        """
        Cập nhật thời gian sử dụng thực (F1 BẮT BUỘC):
        - Đo khoảng thời gian delta bằng monotonic clock
        - Bỏ qua thời gian nếu không có thao tác quá 5 phút (300s)
        - Phát hiện và ghi nhận sự kiện nếu lùi đồng hồ hệ thống (clock rollback)
        """
        now_mono = time.monotonic()
        now_wall = time.time()
        delta_sec = max(0.0, now_mono - self.last_mono)
        self.last_mono = now_mono

        # Kiểm tra lùi đồng hồ hệ thống
        wall_delta = now_wall - self.last_wall_time
        if wall_delta < -60:  # Lùi đồng hồ hơn 1 phút
            print(f"[!] [Enforcer] PHÁT HIỆN LÙI ĐỒNG HỒ HỆ THỐNG: Lệch {abs(wall_delta):.1f}s!")
            if self.on_event_callback:
                self.on_event_callback({
                    "type": "quota_warning",
                    "subject": f"Phát hiện chỉnh lùi giờ hệ thống ({int(abs(wall_delta))}s)",
                    "duration_sec": 0
                })
        self.last_wall_time = now_wall

        # Kiểm tra idle > 5 phút (300 giây)
        idle_sec = get_idle_duration_sec()
        if idle_sec >= 300:
            print(f"[*] [Enforcer] Máy tính đang nhàn rỗi (idle {idle_sec:.1f}s >= 5 phút). Tạm dừng tính giờ.")
            return

        self.active_usage_seconds += delta_sec

    @property
    def used_minutes(self) -> int:
        return int(self.active_usage_seconds / 60)

    def get_effective_quota(self, policy_details=None):
        if not policy_details:
            return 90 + self.bonus_minutes

        now = datetime.datetime.now()
        is_weekend = now.weekday() >= 5  # 5 = Thứ 7, 6 = Chủ nhật
        base_quota = policy_details.get("quota_weekend", 120) if is_weekend else policy_details.get("quota_weekday", 90)
        return base_quota + self.bonus_minutes

    def get_remaining_minutes(self, policy_details=None) -> int:
        """Tính số phút còn lại trong ngày (phục vụ hiển thị đồng hồ đếm ngược trên Tray UI)"""
        quota = self.get_effective_quota(policy_details)
        return max(0, quota - self.used_minutes)

    def add_bonus_minutes(self, minutes: int):
        """Phụ huynh thưởng thêm giờ (F4: +15 phút)"""
        self.bonus_minutes += minutes
        # Đặt lại cờ cảnh báo nếu được cộng thêm giờ
        if self.get_remaining_minutes() > 10:
            self.warned_10 = False
        if self.get_remaining_minutes() > 5:
            self.warned_5 = False
        if self.get_remaining_minutes() > 1:
            self.warned_1 = False
        self.grace_active = False
        print(f"[+] [Enforcer] Đã cộng thêm {minutes} phút thưởng. Tổng phút thưởng: {self.bonus_minutes}p")

    def handle_emergency_command(self, cmd_data: dict):
        """Xử lý lệnh khẩn nhận từ kênh WebSocket (F4, NT3)"""
        command = cmd_data.get("command")
        if command == "lock_now":
            print("[!] [Enforcer] NHẬN LỆNH KHẨN: KHÓA MÁY NGAY LẬP TỨC!")
            self.is_emergency_locked = True
            self.lock_workstation()
        elif command == "unlock":
            print("[+] [Enforcer] NHẬN LỆNH KHẨN: MỞ KHÓA MÁY!")
            self.is_emergency_locked = False
        elif command == "add_time":
            minutes = cmd_data.get("minutes", 15)
            self.add_bonus_minutes(minutes)
        elif command == "notify":
            msg = cmd_data.get("message", "")
            if msg:
                threading.Thread(
                    target=lambda: ctypes.windll.user32.MessageBoxW(0, msg, "OpenGuardKids - Lời nhắn từ Cha Mẹ", 0x40 | 0x1000),
                    daemon=True
                ).start()

    def is_in_blocked_hours(self, policy_details):
        """
        Kiểm tra thời gian cấm theo lịch tuần:
        1. Hỗ trợ ma trận 7x48 (7 ngày x 48 block 30 phút, giá trị 0 = Khóa, 1 = Cho phép) (F1 BẮT BUỘC)
        2. Hỗ trợ cấu hình dải giờ linh hoạt 'blocked_hours'
        """
        if not policy_details:
            return False

        sched = policy_details.get("schedule_json")
        if isinstance(sched, str):
            try:
                sched = json.loads(sched)
            except Exception:
                sched = {}

        now = datetime.datetime.now()
        day_idx = now.weekday()  # 0 = Thứ 2, ..., 6 = Chủ nhật
        slot_idx = now.hour * 2 + (1 if now.minute >= 30 else 0)  # 0 đến 47

        # 1. Kiểm tra theo ma trận 7x48 (F1)
        matrix = None
        if isinstance(sched, list) and len(sched) == 7:
            matrix = sched
        elif isinstance(sched, dict) and "schedule_matrix" in sched and isinstance(sched["schedule_matrix"], list):
            matrix = sched["schedule_matrix"]

        if matrix and len(matrix) > day_idx and len(matrix[day_idx]) > slot_idx:
            # 0 là bị khóa/cấm, 1 là cho phép
            slot_val = matrix[day_idx][slot_idx]
            if slot_val == 0:
                print(f"[!] [Enforcer] Ma trận 7x48: Ngày T{day_idx+2}, Slot {slot_idx} (lúc {now.strftime('%H:%M')}) bị KHÓA!")
                return True

        # 2. Kiểm tra theo dải giờ linh hoạt 'blocked_hours'
        try:
            blocked_hours = sched.get("blocked_hours", []) if isinstance(sched, dict) else []
            now_str = now.strftime("%H:%M")
            for block in blocked_hours:
                start_h, end_h = block.split("-")
                if start_h > end_h:  # Ví dụ 22:00-06:00
                    if now_str >= start_h or now_str <= end_h:
                        return True
                else:
                    if start_h <= now_str <= end_h:
                        return True
        except Exception as e:
            print(f"[-] Lỗi kiểm tra dải giờ cấm: {e}")

        return False

    def notify_warning_async(self, minutes_left: int):
        """Cảnh báo trước 10, 5, 1 phút bằng thông báo thân thiện cho trẻ (F1 BẮT BUỘC)"""
        def _show():
            msg = f"Em còn {minutes_left} phút sử dụng máy tính hôm nay nhé.\nHãy chuẩn bị lưu bài học hoặc công việc của mình nha! ⏳"
            ctypes.windll.user32.MessageBoxW(0, msg, f"OpenGuardKids - Cảnh Báo ({minutes_left} Phút Còn Lại)", 0x30 | 0x1000)
        threading.Thread(target=_show, daemon=True).start()

    def start_grace_countdown_and_lock(self):
        """Khoảng ân hạn 60 giây để trẻ kịp lưu bài trước khi khóa máy (F1 BẮT BUỘC)"""
        if self.grace_active:
            return
        self.grace_active = True

        def _grace_thread():
            print("[!] Bắt đầu khoảng ân hạn 60 giây để trẻ lưu bài...")
            if self.on_event_callback:
                self.on_event_callback({
                    "type": "quota_warning",
                    "subject": "Khoảng ân hạn 60 giây lưu bài trước khi khóa máy",
                    "duration_sec": 60
                })

            # Hiển thị thông báo ân hạn không block
            threading.Thread(
                target=lambda: ctypes.windll.user32.MessageBoxW(
                    0,
                    "ĐÃ HẾT GIỜ DÙNG MÁY!\nEm có đúng 60 GIÂY ÂN HẠN để nhấn Lưu (Save) bài tập.\nMáy sẽ tự động khóa sau 60 giây! 💾",
                    "OpenGuardKids - Ân Hạn 60 Giây Lưu Bài",
                    0x30 | 0x1000
                ),
                daemon=True
            ).start()

            time.sleep(60)
            if self.grace_active:
                print("[!] Hết 60 giây ân hạn. Khóa máy tính!")
                self.lock_workstation()

        threading.Thread(target=_grace_thread, daemon=True).start()

    def check_and_enforce(self, policy_details):
        """Kiểm tra thời gian và thực thi cảnh báo/khóa máy (F1 BẮT BUỘC)"""
        if self.is_emergency_locked:
            self.lock_workstation()
            return True, "Khóa máy theo lệnh khẩn cấp từ Phụ huynh"

        # Cập nhật thời gian sử dụng thực (loại trừ idle > 5p)
        self.update_usage()

        quota = self.get_effective_quota(policy_details)
        remaining = self.get_remaining_minutes(policy_details)

        print(f"[*] [Enforcer] Đã sử dụng thực: {self.used_minutes}p | Hạn mức hôm nay: {quota}p | Còn lại: {remaining}p")

        # 1. Cảnh báo các mốc 10 phút, 5 phút, 1 phút (F1 BẮT BUỘC)
        if remaining <= 10 and not self.warned_10 and remaining > 5:
            self.warned_10 = True
            print("[!] Cảnh báo: Còn 10 phút sử dụng!")
            self.notify_warning_async(10)
            if self.on_event_callback:
                self.on_event_callback({"type": "quota_warning", "subject": "Còn 10 phút", "duration_sec": 0})

        if remaining <= 5 and not self.warned_5 and remaining > 1:
            self.warned_5 = True
            print("[!] Cảnh báo: Còn 5 phút sử dụng!")
            self.notify_warning_async(5)
            if self.on_event_callback:
                self.on_event_callback({"type": "quota_warning", "subject": "Còn 5 phút", "duration_sec": 0})

        if remaining <= 1 and not self.warned_1 and remaining > 0:
            self.warned_1 = True
            print("[!] Cảnh báo: Còn 1 phút sử dụng!")
            self.notify_warning_async(1)
            if self.on_event_callback:
                self.on_event_callback({"type": "quota_warning", "subject": "Còn 1 phút", "duration_sec": 0})

        # 2. Hết Quota -> Kích hoạt ân hạn 60 giây rồi khóa máy
        if self.used_minutes >= quota:
            print(f"[!] VI PHẠM QUOTA! Đã dùng {self.used_minutes}/{quota} phút.")
            if not self.grace_active:
                self.start_grace_countdown_and_lock()
            return True, "Hết thời gian quota cho phép (đang kích hoạt ân hạn 60 giây)"

        # 3. Kiểm tra Giờ Cấm / Ma trận tuần 7x48 (F1 BẮT BUỘC)
        if self.is_in_blocked_hours(policy_details):
            print(f"[!] VI PHẠM LỊCH TUẦN! Hiện tại đang trong khung giờ cấm. Khóa máy trong vòng 5 giây...")
            self.lock_workstation()
            return True, "Đang trong khung giờ cấm sử dụng máy tính"

        return False, "Bình thường"

    def lock_workstation(self):
        """Gọi API của Windows để khóa màn hình máy tính"""
        try:
            print("[+] Executing LockWorkStation()...")
            ctypes.windll.user32.LockWorkStation()
        except Exception as e:
            print(f"[-] Lỗi gọi LockWorkStation: {e}")

