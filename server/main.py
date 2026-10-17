"""
Launcher cho FastAPI Server.
Lưu ý: Logic chính đã được cấu trúc tại server/app/main.py
"""
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

SYS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
if SYS_ROOT not in sys.path:
    sys.path.insert(0, SYS_ROOT)

from server.app.main import app

if __name__ == "__main__":
    import uvicorn
    import argparse
    import socket

    parser = argparse.ArgumentParser(description="OpenGuardKids Server Launcher")
    parser.add_argument("--host", default="0.0.0.0", help="Địa chỉ host (mặc định 0.0.0.0 cho phép các máy trong mạng LAN kết nối)")
    parser.add_argument("--port", type=int, default=8000, help="Cổng lắng nghe (mặc định 8000)")
    parser.add_argument("--no-reload", action="store_true", help="Tắt auto-reload")
    args = parser.parse_args()

    # In ra thông tin IP mạng LAN để người dùng tiện kết nối các máy Agent/Trẻ em
    print("\n" + "="*60)
    print("🛡️  OPENGUARDKIDS SERVER ĐANG KHỞI CHẠY...")
    print(f"[*] Máy chủ lắng nghe tại: http://{args.host}:{args.port}")
    print(f"[*] Truy cập trên máy này: http://127.0.0.1:{args.port}")
    try:
        hostname = socket.gethostname()
        local_ips = socket.gethostbyname_ex(hostname)[2]
        lan_ips = [ip for ip in local_ips if not ip.startswith("127.")]
        if lan_ips:
            print("[*] Địa chỉ IP trong mạng LAN (dùng cho các máy trẻ em kết nối):")
            for ip in lan_ips:
                print(f"    👉 http://{ip}:{args.port}")
    except Exception:
        pass
    print("="*60 + "\n")

    uvicorn.run("server.app.main:app", host=args.host, port=args.port, reload=not args.no_reload)
