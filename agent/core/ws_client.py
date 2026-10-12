import asyncio
import json
import threading
import time
import sys
from typing import Callable, Optional
import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

class WebSocketCommandClient:
    """
    Client WebSocket Phía Agent (Feature F4, NT3):
    - Kết nối thường trực tới ws://<server>/ws/commands/{device_id}
    - Độ trễ nhận lệnh khẩn < 5 giây (Khóa ngay, Mở khóa, Cộng 15 phút, Thông báo)
    - Tự động thử lại kết nối (Auto-reconnect with exponential backoff) khi mất mạng
    - Chạy ngầm trong luồng riêng biệt không ảnh hưởng tới vòng lặp chính của Agent
    """

    def __init__(self, server_ws_url: str, device_id: str, on_command_callback: Callable[[dict], None]):
        self.server_ws_url = server_ws_url.rstrip("/")
        self.device_id = device_id
        self.on_command_callback = on_command_callback
        self.running = False
        self.client_thread: Optional[threading.Thread] = None

    def start(self):
        """Khởi động client WebSocket trên background thread"""
        if self.running:
            return
        self.running = True
        self.client_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.client_thread.start()

    def _run_async_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._listen_loop())
        finally:
            loop.close()

    async def _listen_loop(self):
        ws_url = f"{self.server_ws_url}/ws/commands/{self.device_id}"
        reconnect_delay = 2

        while self.running:
            try:
                print(f"[*] [WS Client] Đang kết nối kênh lệnh khẩn cấp: {ws_url}")
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
                    print(f"[+] [WS Client] Kênh lệnh khẩn cấp ĐÃ KẾT NỐI (Độ trễ < 5s sẵn sàng).")
                    reconnect_delay = 2  # Reset delay khi kết nối thành công

                    while self.running:
                        message = await ws.recv()
                        try:
                            command_data = json.loads(message)
                            print(f"[!] [WS Client] NHẬN LỆNH KHẨN TỪ PHỤ HUYNH: {command_data}")
                            if self.on_command_callback:
                                self.on_command_callback(command_data)
                        except Exception as e:
                            print(f"[-] [WS Client] Lỗi xử lý gói lệnh: {e}")

            except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
                if self.running:
                    print(f"[-] [WS Client] Mất kết nối tới Server. Thử lại sau {reconnect_delay}s...")
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 1.5, 30)
            except Exception as e:
                if self.running:
                    await asyncio.sleep(5)

    def stop(self):
        """Dừng client WebSocket"""
        self.running = False
        if self.client_thread:
            self.client_thread.join(timeout=1.0)
