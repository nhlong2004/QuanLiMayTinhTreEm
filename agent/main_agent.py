import time
import os
import sys
import psutil

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SYS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
if SYS_ROOT not in sys.path:
    sys.path.insert(0, SYS_ROOT)

from agent.core.sync import PolicySyncManager
from agent.core.enforcer import TimeEnforcer
from agent.core.app_controller import AppController
from agent.dns_proxy import DNSProxyServer
from agent.core.event_logger import OfflineEventLogger
from agent.core.ws_client import WebSocketCommandClient
from agent.tray_app import SystemTrayApp

def run_agent_loop():
    sync_manager = PolicySyncManager()
    event_logger = OfflineEventLogger()

    # Khởi tạo TimeEnforcer với callback ghi nhận sự kiện cảnh báo/lùi đồng hồ (F1, F3)
    def on_enforcer_event(event_data):
        event_logger.log_event(
            device_id=device_id,
            child_id=child_id,
            event_type=event_data["type"],
            subject=event_data.get("subject"),
            duration_sec=event_data.get("duration_sec", 0)
        )

    enforcer = TimeEnforcer(on_event_callback=on_enforcer_event)

    # Ghep doi ban dau neu chua co config
    config = sync_manager.load_config()
    if not config or "device_id" not in config:
        config = sync_manager.enroll_device()

    device_id = config.get("device_id", "7b67f9f8-7df6-4e96-8d66-2616c7b7dc13")
    child_id = config.get("child_id", 1)

    # 1. Callback ghi nhận sự kiện vi phạm ứng dụng (F3)
    def on_app_violation(event_data):
        event_logger.log_event(
            device_id=device_id,
            child_id=child_id,
            event_type=event_data["type"],
            subject=event_data["subject"],
            duration_sec=0
        )

    app_controller = AppController(on_violation_callback=on_app_violation)

    # 2. Callback ghi nhận truy vấn tên miền DNS (F3)
    def on_dns_event(event_data):
        event_logger.log_event(
            device_id=device_id,
            child_id=child_id,
            event_type=event_data["type"],
            subject=event_data["subject"],
            duration_sec=0
        )

    # Khởi chạy DNS Proxy server tại 127.0.0.1:53 (F2)
    dns_proxy = DNSProxyServer(host="127.0.0.1", port=53, on_event_callback=on_dns_event)
    dns_proxy.start_background()

    # 3. Khởi chạy WebSocket Client nhận lệnh khẩn từ Phụ huynh (< 5s) (F4, NT3, F3)
    def handle_incoming_ws_command(cmd_data: dict):
        command = cmd_data.get("command")
        if command == "purge_offline_events":
            print("[!] [WebSocket] NHẬN LỆNH XÓA TOÀN BỘ DỮ LIỆU CỦA CON TỪ PHỤ HUYNH (Nghị định 13/2023)!")
            deleted_count = event_logger.purge_all_offline_events()
            print(f"[+] [WebSocket] Đã dọn sạch {deleted_count} bản ghi sự kiện trong SQLite của máy trẻ!")
        else:
            enforcer.handle_emergency_command(cmd_data)

    ws_server_url = "ws://127.0.0.1:8000"
    ws_client = WebSocketCommandClient(
        server_ws_url=ws_server_url,
        device_id=device_id,
        on_command_callback=handle_incoming_ws_command
    )
    ws_client.start()

    # 4. Khởi chạy System Tray Icon ở góc phải màn hình Windows Taskbar (NT1)
    def request_extra_time_from_tray():
        try:
            import requests
            requests.post(
                f"{sync_manager.server_url}/api/requests",
                json={
                    "device_id": device_id,
                    "child_id": child_id,
                    "request_type": "extra_time",
                    "content": "Con bấm xin thêm 15 phút từ biểu tượng khay hệ thống"
                },
                timeout=4
            )
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "Đã gửi yêu cầu xin thêm 15 phút tới Bố Mẹ!", "OpenGuardKids", 0x40 | 0x1000)
        except Exception as ex:
            print(f"[-] [Tray] Lỗi gửi yêu cầu: {ex}")

    tray_app = SystemTrayApp(
        get_remaining_minutes_callback=lambda: enforcer.get_remaining_minutes(config.get("policy_details")),
        on_request_extra_time_callback=request_extra_time_from_tray,
        child_screen_url=f"{sync_manager.server_url}/child-screen"
    )
    tray_app.start_background()

    # NT1 BẮT BUỘC: Thông báo chào thân thiện, ngắn gọn khi Agent khởi động
    current_child_name = config.get("child_name") or "em"
    tray_app.notify_startup(child_name=current_child_name)

    print(f"[*] Agent OpenGuardKids đã sẵn sàng bảo vệ '{current_child_name}'. Bắt đầu vòng lặp đồng bộ...")

    while True:
        # A. Đồng bộ chính sách từ Server
        success, policy_details = sync_manager.check_and_sync()

        # B. Đẩy hàng đợi sự kiện offline về Server (F3)
        synced_count = event_logger.flush_and_sync()
        if synced_count > 0:
            print(f"[+] [Sync] Đã đẩy {synced_count} sự kiện tồn đọng lên Server thành công.")

        # C. Thực thi kiểm tra quota và lịch cấm (F1)
        is_locked, reason = enforcer.check_and_enforce(policy_details)
        if is_locked:
            event_logger.log_event(device_id=device_id, child_id=child_id, event_type="locked", subject=reason)
            print(f"[!] Lý do khóa máy: {reason}")

        # D. Kiểm soát tiến trình ứng dụng bị chặn (F2, NT4)
        if policy_details and "blocked_apps" in policy_details:
            blocked_apps = policy_details.get("blocked_apps", [])
            violations = app_controller.scan_and_enforce(blocked_apps)
            if violations:
                print(f"[*] Đã ngăn chặn {len(violations)} tiến trình ứng dụng vi phạm!")

        # E. Cập nhật danh sách tên miền bị chặn cho DNS Proxy (F2)
        if policy_details and "blocked_domains" in policy_details:
            blocked_domains = policy_details.get("blocked_domains", [])
            dns_proxy.update_blocked_domains(blocked_domains)

        # Chu kỳ lặp 60 giây
        time.sleep(60)

if __name__ == "__main__":
    current_pid = os.getpid()
    p = psutil.Process(current_pid)
    print(f"[i] Khởi chạy OpenGuardKids Agent (PID: {current_pid}, RAM sử dụng: {p.memory_info().rss / 1024 / 1024:.2f} MB)")
    
    run_agent_loop()