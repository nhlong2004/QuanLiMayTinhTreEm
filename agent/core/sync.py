import requests
import json
import os
import sys
import time
import hmac
import hashlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SERVER_URL = "http://127.0.0.1:8000"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
SECRET_KEY = "ogk_secure_secret_key_demo"

def compute_policy_hmac(version: int, q_weekday: int, q_weekend: int, matrix_data: any) -> str:
    """Tính toán lại chữ ký HMAC tại Agent để đối chiếu tính toàn vẹn (F4 BẮT BUỘC)"""
    matrix_str = json.dumps(matrix_data, sort_keys=True) if isinstance(matrix_data, (list, dict)) else str(matrix_data)
    message = f"{version}-{q_weekday}-{q_weekend}-{matrix_str}"
    return hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()

class PolicySyncManager:
    def __init__(self, server_url=SERVER_URL, config_file=CONFIG_FILE):
        self.server_url = server_url
        self.config_file = config_file

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[-] Loi doc config: {e}")
        return {}

    def save_config(self, config_data):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)

    def enroll_device(self, device_name="PC-Phong-Khach", child_name="Be An"):
        """Ghep doi thiet bi voi Server"""
        config = self.load_config()
        enroll_code = config.get("enroll_code", "OGK2026X")
        device_id = config.get("device_id", "7b67f9f8-7df6-4e96-8d66-2616c7b7dc13")

        payload = {
            "enroll_code": enroll_code,
            "device_id": device_id,
            "device_name": device_name
        }
        try:
            print(f"[*] Dang ket noi Server ({self.server_url}/auth/enroll) de ghep doi voi ma: {enroll_code}...")
            res = requests.post(f"{self.server_url}/auth/enroll", json=payload, timeout=5)
            if res.status_code == 200:
                data = res.json()
                config["device_id"] = data.get("device_id", device_id)
                config["child_name"] = data.get("child_name", child_name)
                config["policy_version"] = data.get("policy_version", 1)
                self.save_config(config)
                print(f"[+] Ghep doi thiet bi thanh cong! Device ID: {config['device_id']}")
                return config
            else:
                print(f"[-] Ghep doi that bai: {res.text}")
        except Exception as e:
            print(f"[-] Loi ket noi Server khi ghep doi: {e}")
        return None

    def verify_policy_hmac(self, policy_data: dict) -> bool:
        """
        Xác thực toàn vẹn chữ ký HMAC của Chính sách (F4 BẮT BUỘC).
        Agent lập tức từ chối nếu chính sách bị giả mạo hoặc sai chữ ký.
        """
        if not policy_data:
            return False

        received_sig = policy_data.get("hmac_signature", "")
        if not received_sig:
            print("[-] [HMAC] CẢNH BÁO: Chính sách thiếu chữ ký HMAC!")
            return False

        version = policy_data.get("version", 1)
        q_weekday = policy_data.get("quota_weekday", 90)
        q_weekend = policy_data.get("quota_weekend", 120)
        
        # Thử tính HMAC với schedule_matrix_json nguyên bản hoặc schedule_json
        matrix_raw = policy_data.get("schedule_matrix_json")
        if matrix_raw is None:
            matrix_raw = policy_data.get("schedule_json")

        expected_sig = compute_policy_hmac(version, q_weekday, q_weekend, matrix_raw)

        if hmac.compare_digest(received_sig, expected_sig):
            print(f"[+] [HMAC] Xác thực chữ ký toàn vẹn chính sách v{version} THÀNH CÔNG! ({received_sig[:12]}...)")
            return True

        # Thử lại với dạng json object nếu matrix_raw là string hoặc ngược lại
        if isinstance(matrix_raw, str):
            try:
                matrix_obj = json.loads(matrix_raw)
                alt_sig = compute_policy_hmac(version, q_weekday, q_weekend, matrix_obj)
                if hmac.compare_digest(received_sig, alt_sig):
                    print(f"[+] [HMAC] Xác thực chữ ký chính sách v{version} THÀNH CÔNG (Alt)! ({received_sig[:12]}...)")
                    return True
            except Exception:
                pass

        print(f"[!] [HMAC] TỪ CHỐI CHÍNH SÁCH V{version}: Chữ ký HMAC không khớp! (Có dấu hiệu bị chỉnh sửa)")
        return False

    def check_and_sync(self):
        """Gui heartbeat dinh ky & dong bo Policy neu co phien ban moi"""
        config = self.load_config()
        if not config or "device_id" not in config:
            config = self.enroll_device()
            if not config:
                return False, None

        device_id = config.get("device_id")
        current_version = config.get("policy_version", 1)

        payload = {
            "device_id": device_id,
            "current_policy_version": current_version
        }

        try:
            res = requests.post(f"{self.server_url}/api/heartbeat", json=payload, timeout=5)
            if res.status_code == 200:
                data = res.json()
                print(f"[x] [{time.strftime('%X')}] Heartbeat OK. Server response:", data)
                
                if data.get("update_policy_required", False):
                    latest_ver = data.get("latest_policy_version")
                    print(f"[!] Server thong bao co Policy v{latest_ver} moi. Tien hanh tai ve...")
                    policy_data = self.download_policy(latest_ver, device_id=device_id)
                    if policy_data:
                        # F4 BẮT BUỘC: Kiểm tra toàn vẹn chữ ký HMAC
                        if self.verify_policy_hmac(policy_data):
                            config["policy_version"] = latest_ver
                            config["policy_details"] = policy_data
                            self.save_config(config)
                            print(f"[+] Da ap dung Policy v{latest_ver} hop le thanh cong!")
                            return True, policy_data
                        else:
                            print(f"[!] CANH BAO AN TOAN: Agent tu choi ap dung Policy v{latest_ver} do vi pham chu ky toan ven HMAC!")
                            return False, config.get("policy_details")
                return True, config.get("policy_details")
            elif res.status_code == 404:
                print("[-] Thiet bi chua co tren Server. Thu ghep doi lai...")
                self.enroll_device()
        except Exception as e:
            print(f"[-] Loi Heartbeat / Ket noi Server: {e}")
        
        return False, config.get("policy_details")

    def download_policy(self, version, device_id=None):
        """Tai chi tiet chinh sach theo phien ban va truyen device_id de cap nhat trang thai dong bo"""
        try:
            url = f"{self.server_url}/api/policy/download/{version}"
            if device_id:
                url += f"?device_id={device_id}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                return res.json()
            print(f"[-] Khong the tai policy v{version}: {res.text}")
        except Exception as e:
            print(f"[-] Loi tai policy: {e}")
        return None
