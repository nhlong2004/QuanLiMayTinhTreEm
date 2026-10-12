import os
import sys
import hashlib
import psutil
import ctypes
import threading
from typing import List, Dict, Optional, Tuple, Set

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def compute_file_sha256(filepath: str) -> Optional[str]:
    """Tính mã băm SHA-256 của file thực thi .exe (đọc từng block 64KB)"""
    if not filepath or not os.path.exists(filepath):
        return None
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest().lower()
    except (PermissionError, OSError):
        return None

def show_blocked_dialog_async(app_name: str, reason: str = "Ứng dụng nằm trong danh sách cấm"):
    """
    Hiển thị thông báo giải thích lý do chặn (Nguyên tắc NT4: Không im lặng, minh bạch lý do).
    Chạy trên luồng riêng biệt để không block vòng lặp quét của Agent.
    """
    def _dialog():
        title = "OpenGuardKids - Thông Báo Bảo Vệ"
        message = (
            f"Ứng dụng '{app_name}' đã được đóng lại.\n\n"
            f"Lý do: {reason}.\n"
            f"Chính sách do Phụ huynh thiết lập nhằm bảo vệ và quản lý thời gian sử dụng."
        )
        # MB_ICONWARNING = 0x30 | MB_OK = 0x0 | MB_SYSTEMMODAL = 0x1000
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x30 | 0x1000)

    t = threading.Thread(target=_dialog, daemon=True)
    t.start()

class AppController:
    """
    Module Kiểm soát Ứng dụng phía Agent (F2, NT4):
    - Quét các tiến trình qua psutil.process_iter()
    - Đối chiếu tên tiến trình (.exe)
    - Đối chiếu mã băm SHA-256 của tệp thực thi (ngăn chặn bypass bằng cách đổi tên file)
    - Kết thúc tiến trình vi phạm và hiển thị giải thích
    """

    def __init__(self, on_violation_callback=None):
        self.on_violation_callback = on_violation_callback
        self.cached_hashes: Dict[str, str] = {}  # Cache hash của filepath để tránh đọc đĩa liên tục
        self.last_killed_pids: Set[int] = set()

    def _get_process_info(self, proc: psutil.Process) -> Optional[Tuple[int, str, Optional[str]]]:
        try:
            pid = proc.pid
            name = proc.name().lower()
            try:
                exe_path = proc.exe()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                exe_path = None
            return pid, name, exe_path
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None

    def scan_and_enforce(self, blocked_apps: List[Dict]) -> List[Dict]:
        """
        Quét danh sách tiến trình đang chạy và xử lý vi phạm.
        blocked_apps: [{'process_name': 'game.exe', 'file_hash': 'sha256...'}, ...]
        Trả về danh sách các sự kiện vi phạm đã ghi nhận.
        """
        if not blocked_apps:
            return []

        # Chuẩn hóa danh sách chặn
        blocked_names = {item.get("process_name", "").lower(): item for item in blocked_apps if item.get("process_name")}
        blocked_hashes = {item.get("file_hash", "").lower(): item for item in blocked_apps if item.get("file_hash")}

        violations = []
        current_agent_pid = os.getpid()

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.pid == current_agent_pid or proc.pid <= 4:
                    continue  # Bỏ qua chính agent và System idle/kernel

                proc_info = self._get_process_info(proc)
                if not proc_info:
                    continue
                pid, name, exe_path = proc_info

                matched_rule = None
                matched_reason = ""

                # 1. Kiểm tra theo tên tiến trình
                if name in blocked_names:
                    matched_rule = blocked_names[name]
                    matched_reason = f"Tên tiến trình '{name}' có trong danh sách hạn chế"

                # 2. Kiểm tra theo mã băm SHA-256 nếu có exe_path (chống đổi tên file để lách luật)
                file_hash = None
                if exe_path:
                    if exe_path in self.cached_hashes:
                        file_hash = self.cached_hashes[exe_path]
                    else:
                        file_hash = compute_file_sha256(exe_path)
                        if file_hash:
                            self.cached_hashes[exe_path] = file_hash

                    if file_hash and file_hash in blocked_hashes:
                        matched_rule = blocked_hashes[file_hash]
                        matched_reason = f"Mã băm SHA-256 trùng khớp với tệp bị cấm ({file_hash[:12]}...)"

                # Xử lý khi phát hiện vi phạm
                if matched_rule:
                    print(f"[!] [AppController] PHÁT HIỆN VI PHẠM: PID {pid} ({name}) - {matched_reason}")
                    try:
                        proc.kill()
                        print(f"[+] [AppController] Đã chấm dứt tiến trình PID {pid} ({name})")
                    except Exception as ex:
                        print(f"[-] [AppController] Không thể kill PID {pid}: {ex}")

                    # NT4: Hiển thị thông báo giải thích cho trẻ (không im lặng)
                    show_blocked_dialog_async(name, matched_reason)

                    violation_event = {
                        "type": "blocked_app",
                        "subject": name,
                        "duration_sec": 0,
                        "details": matched_reason
                    }
                    violations.append(violation_event)

                    if self.on_violation_callback:
                        self.on_violation_callback(violation_event)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                continue

        return violations
