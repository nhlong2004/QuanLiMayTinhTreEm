import ctypes
import datetime
import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

class TimeEnforcer:
    def __init__(self):
        self.start_time = time.time()
        self.used_minutes = 0

    def get_effective_quota(self, policy_details):
        if not policy_details:
            return 90  # Mac dinh 90 phut

        now = datetime.datetime.now()
        is_weekend = now.weekday() >= 5  # 5 = Thu 7, 6 = Chu nhat
        if is_weekend:
            return policy_details.get("quota_weekend", 120)
        return policy_details.get("quota_weekday", 90)

    def is_in_blocked_hours(self, policy_details):
        if not policy_details or "schedule_json" not in policy_details:
            return False
        
        try:
            sched_str = policy_details.get("schedule_json")
            if isinstance(sched_str, str):
                sched = json.loads(sched_str)
            else:
                sched = sched_str
                
            blocked_hours = sched.get("blocked_hours", [])
            now_str = datetime.datetime.now().strftime("%H:%M")
            
            for block in blocked_hours:
                start_h, end_h = block.split("-")
                if start_h > end_h: # Vi du 22:00-06:00
                    if now_str >= start_h or now_str <= end_h:
                        return True
                else:
                    if start_h <= now_str <= end_h:
                        return True
        except Exception as e:
            print(f"[-] Loi kiem tra lich cam: {e}")
            
        return False

    def check_and_enforce(self, policy_details):
        """Kiem tra thoi gian va thuc thi khoa may neu vi pham (F1)"""
        # Dem thoi gian su dung thuc te (tinh bang phut)
        self.used_minutes = int((time.time() - self.start_time) / 60)
        quota = self.get_effective_quota(policy_details)

        print(f"[*] [Enforcer] Da su dung: {self.used_minutes} phut | Han muc hom nay: {quota} phut")

        # 1. Kiem tra Quota
        if self.used_minutes >= quota:
            print(f"[!] VI PHAM QUOTA! Da dung {self.used_minutes}/{quota} phut. Tien hanh khoa may...")
            self.lock_workstation()
            return True, "Het thoi gian quota cho phap"

        # 2. Kiem tra Gio Cam (Schedule)
        if self.is_in_blocked_hours(policy_details):
            print(f"[!] VI PHAM GIO CAM! Hien tai dang trong khung gio cam. Tien hanh khoa may...")
            self.lock_workstation()
            return True, "Dang trong khung gio cam su dung may tinh"

        return False, "Binh thuong"

    def lock_workstation(self):
        """Gol API cua Windows de khoa man hinh may tinh"""
        try:
            print("[+] Executing LockWorkStation()...")
            ctypes.windll.user32.LockWorkStation()
        except Exception as e:
            print(f"[-] Loi goi LockWorkStation: {e}")
