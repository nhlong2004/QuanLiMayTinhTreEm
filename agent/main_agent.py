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

def run_agent_loop():
    sync_manager = PolicySyncManager()
    enforcer = TimeEnforcer()

    # Ghep doi ban dau neu chua co config
    config = sync_manager.load_config()
    if not config or "device_id" not in config:
        config = sync_manager.enroll_device()

    print("[*] Agent OpenGuardKids da san sang. Bat dau vong lap dong bo va thuc thi...")

    while True:
        # 1. Dong bo policy tu Server
        success, policy_details = sync_manager.check_and_sync()

        # 2. Thuc thi kiem tra quota va lich cam
        is_locked, reason = enforcer.check_and_enforce(policy_details)
        if is_locked:
            print(f"[!] Ly do khoa may: {reason}")

        # Chu ky lap 60 giay
        time.sleep(60)

if __name__ == "__main__":
    current_pid = os.getpid()
    p = psutil.Process(current_pid)
    print(f"[i] Khoi chay OpenGuardKids Agent (PID: {current_pid}, RAM su dung: {p.memory_info().rss / 1024 / 1024:.2f} MB)")
    
    run_agent_loop()