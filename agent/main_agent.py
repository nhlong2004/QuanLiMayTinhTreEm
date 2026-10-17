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

def run_agent_loop(
    config_path=None,
    server_url=None,
    enroll_code=None,
    device_name=None,
    force_new_device=False
):
    import uuid
    import socket
    import json
    import urllib.parse

    config_file = config_path or os.path.join(os.path.dirname(__file__), "config.json")

    # Đọc cấu hình sẵn có hoặc tạo mới
    existing_cfg = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                existing_cfg = json.load(f)
        except Exception:
            pass

    resolved_server_url = (server_url or existing_cfg.get("server_url") or os.environ.get("OGK_SERVER_URL") or "http://127.0.0.1:8000").rstrip("/")
    resolved_device_name = device_name or existing_cfg.get("device_name") or f"PC-{socket.gethostname()}"

    sync_manager = PolicySyncManager(server_url=resolved_server_url, config_file=config_file)

    # Ghép đôi thiết bị nếu chưa có device_id hoặc người dùng yêu cầu mã ghép đôi mới
    if force_new_device or enroll_code or not existing_cfg or "device_id" not in existing_cfg:
        config = sync_manager.enroll_device(
            device_name=resolved_device_name,
            enroll_code=enroll_code
        )
        if not config:
            print("[-] Không thể ghép đôi với Server. Vui lòng kiểm tra Server URL và Mã ghép đôi!")
            config = existing_cfg
    else:
        config = existing_cfg

    device_id = config.get("device_id") or str(uuid.uuid4())
    child_id = config.get("child_id", 1)
    disable_real_lock = config.get("disable_real_lock", True)

    # Đảm bảo OfflineEventLogger gửi sự kiện tới đúng Server URL của máy này
    events_db_path = os.path.join(os.path.dirname(__file__), f"agent_events_{device_id[:8]}.db")
    event_logger = OfflineEventLogger(db_path=events_db_path, server_url=resolved_server_url)

    # Khởi tạo TimeEnforcer với callback ghi nhận sự kiện cảnh báo/lùi đồng hồ (F1, F3)
    def on_enforcer_event(event_data):
        event_logger.log_event(
            device_id=device_id,
            child_id=child_id,
            event_type=event_data["type"],
            subject=event_data.get("subject"),
            duration_sec=event_data.get("duration_sec", 0)
        )

    enforcer = TimeEnforcer(on_event_callback=on_enforcer_event, disable_real_lock=disable_real_lock)

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
        nonlocal policy_details
        command = cmd_data.get("command")
        if command == "purge_offline_events":
            print("[!] [WebSocket] NHẬN LỆNH XÓA TOÀN BỘ DỮ LIỆU CỦA CON TỪ PHỤ HUYNH (Nghị định 13/2023)!")
            deleted_count = event_logger.purge_all_offline_events()
            print(f"[+] [WebSocket] Đã dọn sạch {deleted_count} bản ghi sự kiện trong SQLite của máy trẻ!")
        elif command == "sync_policy":
            print("[!] [WebSocket] NHẬN LỆNH ĐỒNG BỘ CHÍNH SÁCH MỚI TỪ SERVER!")
            success, updated_policy = sync_manager.check_and_sync()
            if success and updated_policy:
                policy_details = updated_policy
                if "blocked_domains" in policy_details:
                    dns_proxy.update_blocked_domains(policy_details.get("blocked_domains", []))
        else:
            enforcer.handle_emergency_command(cmd_data)

    ws_server_url = resolved_server_url.replace("http://", "ws://").replace("https://", "wss://")
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

    current_child_name = config.get("child_name") or "em"
    child_param = urllib.parse.quote(current_child_name)
    tray_app = SystemTrayApp(
        get_remaining_minutes_callback=lambda: enforcer.get_remaining_minutes(config.get("policy_details")),
        on_request_extra_time_callback=request_extra_time_from_tray,
        child_screen_url=f"{resolved_server_url}/child-screen?child_name={child_param}"
    )
    tray_app.start_background()

    # NT1 BẮT BUỘC: Thông báo chào thân thiện, ngắn gọn khi Agent khởi động
    current_child_name = config.get("child_name") or "em"
    tray_app.notify_startup(child_name=current_child_name)

    print(f"[*] Agent OpenGuardKids đã sẵn sàng bảo vệ '{current_child_name}'. Bắt đầu vòng lặp đồng bộ và thực thi...")

    policy_details = config.get("policy_details")
    sync_interval_sec = 5.0     # Gửi heartbeat và cập nhật live metrics mỗi 5 giây (F1, F3, F4)
    enforce_interval_sec = 2.0  # Quét ứng dụng & lịch cấm mỗi 2 giây (đáp ứng SLA < 5s của F1, F2)

    # Gửi ngay 1 nhịp tim tức thì khi khởi động để Server có ngay số phút thực tế
    try:
        sync_manager.check_and_sync(
            used_minutes=enforcer.used_minutes,
            remaining_minutes=enforcer.get_remaining_minutes(policy_details),
            bonus_minutes=enforcer.bonus_minutes
        )
    except Exception:
        pass

    last_sync_time = time.time()
    last_cfg_mtime = 0.0
    try:
        if os.path.exists(sync_manager.config_file):
            last_cfg_mtime = os.path.getmtime(sync_manager.config_file)
    except Exception:
        pass

    # Chờ 1 giây để Tray icon ổn định luồng
    time.sleep(1.0)

    while True:
        now_ts = time.time()

        # 0. Chống lạm dụng (F5, NT1): Kiểm tra biểu tượng khay hệ thống
        # Nếu biểu tượng bị tắt hoặc không hiển thị, Agent bắt buộc phải tự dừng (chống Stalkerware)
        if hasattr(tray_app, "is_running") and not tray_app.is_running():
            print("[!] [Anti-Stalkerware] Biểu tượng khay hệ thống đã dừng hoặc không thể hiển thị!")
            print("[!] Agent tự động kết thúc theo nguyên tắc minh bạch bắt buộc (NT1, F5).")
            sys.exit(0)

        # Kiểm tra file config.json có cập nhật (phản hồi tức thì < 2s khi cha mẹ đổi luật)
        try:
            if os.path.exists(sync_manager.config_file):
                cfg_mtime = os.path.getmtime(sync_manager.config_file)
                if cfg_mtime > last_cfg_mtime:
                    last_cfg_mtime = cfg_mtime
                    fresh_cfg = sync_manager.load_config()
                    if fresh_cfg.get("policy_details"):
                        policy_details = fresh_cfg["policy_details"]
                        if "blocked_domains" in policy_details:
                            dns_proxy.update_blocked_domains(policy_details.get("blocked_domains", []))
                        print(f"[*] [Agent] Đã cập nhật chính sách tức thì: {len(policy_details.get('blocked_apps', []))} apps, {len(policy_details.get('blocked_domains', []))} domains.")
        except Exception:
            pass

        # A. Chu kỳ 60 giây: Gửi nhịp tim heartbeat, đồng bộ chính sách và đẩy sự kiện lên Server
        if now_ts - last_sync_time >= sync_interval_sec:
            last_sync_time = now_ts
            try:
                success, updated_policy = sync_manager.check_and_sync(
                    used_minutes=enforcer.used_minutes,
                    remaining_minutes=enforcer.get_remaining_minutes(policy_details),
                    bonus_minutes=enforcer.bonus_minutes
                )
                if success and updated_policy:
                    policy_details = updated_policy

                # Cập nhật danh sách tên miền bị chặn cho DNS Proxy (F2)
                if policy_details and "blocked_domains" in policy_details:
                    blocked_domains = policy_details.get("blocked_domains", [])
                    dns_proxy.update_blocked_domains(blocked_domains)

                # Đẩy hàng đợi sự kiện offline về Server (F3)
                synced_count = event_logger.flush_and_sync()
                if synced_count > 0:
                    print(f"[+] [Sync] Đã đẩy {synced_count} sự kiện tồn đọng lên Server thành công.")
            except Exception as e:
                print(f"[-] [Sync] Lỗi chu kỳ đồng bộ: {e}")

        # B. Chu kỳ 2 giây: Thực thi kiểm tra quota và lịch cấm (F1 BẮT BUỘC: SLA phản hồi < 5 giây)
        try:
            is_locked, reason = enforcer.check_and_enforce(policy_details)
            if is_locked:
                event_logger.log_event(device_id=device_id, child_id=child_id, event_type="locked", subject=reason)
                print(f"[!] Lý do khóa máy: {reason}")

            # Lưu trạng thái thời gian thực ra file để Web Trẻ Em và Tray App đọc tức thì
            status_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "live_status.json"))
            with open(status_file, "w", encoding="utf-8") as sf:
                json.dump({
                    "device_id": device_id,
                    "used_minutes": enforcer.used_minutes,
                    "remaining_minutes": enforcer.get_remaining_minutes(policy_details),
                    "bonus_minutes": enforcer.bonus_minutes,
                    "effective_quota": enforcer.get_effective_quota(policy_details),
                    "updated_at": time.time()
                }, sf)
        except Exception as e:
            print(f"[-] [Enforcer] Lỗi kiểm tra thời gian: {e}")

        # C. Chu kỳ 2 giây: Kiểm soát và kết thúc ngay tiến trình ứng dụng bị cấm (F2, NT4)
        if policy_details and "blocked_apps" in policy_details:
            try:
                blocked_apps = policy_details.get("blocked_apps", [])
                violations = app_controller.scan_and_enforce(blocked_apps)
                if violations:
                    print(f"[*] Đã ngăn chặn {len(violations)} tiến trình ứng dụng vi phạm!")
            except Exception as e:
                print(f"[-] [AppController] Lỗi kiểm soát ứng dụng: {e}")

        # Nghỉ 2 giây cho chu kỳ quét tiếp theo
        time.sleep(enforce_interval_sec)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpenGuardKids Agent - Máy con")
    parser.add_argument("--server-url", default=None, help="Địa chỉ Server (VD: http://192.168.1.15:8000 hoặc http://127.0.0.1:8000)")
    parser.add_argument("--config", default=None, help="Đường dẫn file config riêng (mặc định agent/config.json)")
    parser.add_argument("--enroll-code", default=None, help="Mã ghép đôi từ phụ huynh (VD: OGK-ABC123)")
    parser.add_argument("--device-name", default=None, help="Tên hiển thị của máy tính (mặc định lấy tên máy)")
    parser.add_argument("--new-device", action="store_true", help="Tạo thiết bị mới hoàn toàn (sinh UUID mới)")
    args = parser.parse_args()

    current_pid = os.getpid()
    p = psutil.Process(current_pid)
    print(f"[i] Khởi chạy OpenGuardKids Agent (PID: {current_pid}, RAM: {p.memory_info().rss / 1024 / 1024:.2f} MB)")

    run_agent_loop(
        config_path=args.config,
        server_url=args.server_url,
        enroll_code=args.enroll_code,
        device_name=args.device_name,
        force_new_device=args.new_device
    )