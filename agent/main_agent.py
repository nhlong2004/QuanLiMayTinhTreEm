import time
import requests
import os
import json
import psutil

SERVER_URL = "http://127.0.0.1:8000"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

def enroll_device():
    """Thực hiện ghép đôi thiết bị với Server"""
    payload = {
        "enroll_code": "OGK2026X",
        "device_name": "PC-Phong-Khach",
        "child_name": "Bé Hoa",
        "device_fingerprint": "win10_x64_agent_v1"
    }
    try:
        print("[*] Đang gửi yêu cầu ghép đôi tới Server...")
        response = requests.post(f"{SERVER_URL}/auth/enroll", json=payload)
        if response.status_code == 200:
            data = response.json()
            save_config(data)
            print(f"[+] Ghép đôi thành công! Device ID nhận được: {data.get('device_id')}")
            return data
        else:
            print(f"[-] Lỗi ghép đôi từ Server: {response.text}")
    except Exception as e:
        print(f"[-] Không thể kết nối tới Server tại {SERVER_URL}: {e}")
    return None

def run_agent_loop():
    # Vòng lặp Agent chính: Gửi heartbeat mỗi 60s và đồng bộ policy version
    config = load_config()
    if not config or "device_id" not in config:
        config = enroll_device()
        if not config:
            print("[!] Không thể khởi động Agent do chưa ghép đôi được với Server.")
            return

    device_id = config.get("device_id")
    policy_version = config.get("policy_version", 1)

    print(f"[*] Agent đã sẵn sàng. Bắt đầu vòng lặp gửi Heartbeat cho Device ID: {device_id} (60s/lần)...")

    while True:
        payload = {
            "device_id": device_id,
            "policy_version": policy_version,
            "status": "online"
        }
        try:
            response = requests.post(f"{SERVER_URL}/api/heartbeat", json=payload)
            if response.status_code == 200:
                res_data = response.json()
                print(f"[x] [{time.strftime('%X')}] Heartbeat thành công. Phản hồi từ Server:", res_data)
                
                # Xử lý logic so sánh policy_version 
                if res_data.get("update_policy_required", False):
                    latest_ver = res_data.get("latest_policy_version")
                    print(f"[!] Phát hiện phiên bản Policy mới trên Server ({latest_ver}). Tiến hành cập nhật...")
                    policy_version = latest_ver
                    config["policy_version"] = policy_version
                    save_config(config)
            elif response.status_code == 404:
                print("[-] Thiết bị không tồn tại trên Server. Tiến hành ghép đôi lại...")
                config = enroll_device()
                if config:
                    device_id = config.get("device_id")
            else:
                print(f"[-] Lỗi phản hồi từ Server: {response.status_code}")
        except Exception as e:
            print(f"[-] Mất kết nối mạng hoặc Server ngừng hoạt động: {e}")

        #60s
        time.sleep(60)

if __name__ == "__main__":
    current_pid = os.getpid()
    p = psutil.Process(current_pid)
    print(f"[i] Khởi chạy tiến trình Agent (PID: {current_pid}, RAM sử dụng: {p.memory_info().rss / 1024 / 1024:.2f} MB)")
    
    run_agent_loop()