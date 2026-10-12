import os
import sys
import threading
import time
import webbrowser
from typing import Callable, Optional
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def create_shield_icon_image(size: int = 64) -> Image.Image:
    """Tạo biểu tượng hình chiếc khiên bảo vệ màu xanh lá cho khay hệ thống (NT1)"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Vẽ nền hình tròn màu xanh ngọc/xanh lá
    padding = 4
    draw.ellipse([padding, padding, size - padding, size - padding], fill=(16, 185, 129, 255), outline=(5, 150, 105, 255), width=2)

    # Vẽ hình chiếc khiên / chữ V màu trắng ở trung tâm
    draw.polygon([
        (size * 0.3, size * 0.45),
        (size * 0.45, size * 0.65),
        (size * 0.72, size * 0.32),
        (size * 0.65, size * 0.28),
        (size * 0.45, size * 0.55),
        (size * 0.35, size * 0.40)
    ], fill=(255, 255, 255, 255))

    return img

class SystemTrayApp:
    """
    Ứng dụng Khay Hệ Thống Windows (System Tray Icon - Feature NT1, NT3, NT5):
    - Biểu tượng luôn hiển thị dưới góc phải màn hình Windows Taskbar (Không chạy ẩn).
    - Hiển thị tooltip đồng hồ đếm ngược thời gian còn lại trong ngày.
    - Click chuột mở nhanh màn hình minh bạch dành cho trẻ em (NT1, NT5).
    - Menu cho phép trẻ gửi nhanh yêu cầu: Xin thêm giờ, Báo chặn nhầm (NT3).
    """

    def __init__(
        self, 
        get_remaining_minutes_callback: Optional[Callable[[], int]] = None,
        on_request_extra_time_callback: Optional[Callable[[], None]] = None,
        child_screen_url: str = "http://127.0.0.1:8000/child-screen"
    ):
        self.get_remaining_minutes_callback = get_remaining_minutes_callback
        self.on_request_extra_time_callback = on_request_extra_time_callback
        self.child_screen_url = child_screen_url

        self.icon: Optional[pystray.Icon] = None
        self.running = False
        self.tray_thread: Optional[threading.Thread] = None

    def _open_child_screen(self):
        """Mở màn hình minh bạch cho trẻ trên trình duyệt web"""
        try:
            webbrowser.open(self.child_screen_url)
        except Exception as e:
            print(f"[-] [Tray] Không thể mở màn hình trẻ em: {e}")

    def _request_more_time(self):
        """Trẻ bấm xin thêm giờ từ menu khay hệ thống (NT3)"""
        if self.on_request_extra_time_callback:
            self.on_request_extra_time_callback()
        else:
            self._open_child_screen()

    def _build_menu(self) -> pystray.Menu:
        remaining = 90
        if self.get_remaining_minutes_callback:
            try:
                remaining = max(0, self.get_remaining_minutes_callback())
            except Exception:
                pass

        return pystray.Menu(
            item(f"⏰ Thời gian còn lại: {remaining} phút", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("🌱 Mở màn hình của em (Minh bạch)", lambda: self._open_child_screen()),
            item("⏰ Xin Bố Mẹ thêm 15 phút", lambda: self._request_more_time()),
            pystray.Menu.SEPARATOR,
            item("🛡️ OpenGuardKids đang hoạt động", lambda: None, enabled=False)
        )

    def _update_tooltip_loop(self):
        """Vòng lặp định kỳ cập nhật tooltip thời gian còn lại"""
        while self.running and self.icon:
            try:
                if self.get_remaining_minutes_callback:
                    rem = max(0, self.get_remaining_minutes_callback())
                    self.icon.title = f"OpenGuardKids: Còn {rem} phút sử dụng hôm nay"
                    # Cập nhật lại menu
                    self.icon.menu = self._build_menu()
            except Exception:
                pass
            time.sleep(15)

    def start_background(self):
        """Khởi chạy System Tray Icon trên background thread (NT1, F5)"""
        if self.running:
            return

        self.running = True
        img = create_shield_icon_image()
        self.icon = pystray.Icon(
            "OpenGuardKids",
            img,
            "OpenGuardKids - Đang đồng hành cùng em",
            menu=self._build_menu()
        )

        def _run():
            try:
                # Khởi chạy thread cập nhật tooltip
                threading.Thread(target=self._update_tooltip_loop, daemon=True).start()
                self.icon.run()
            except Exception as e:
                print(f"[-] [Tray UI] Lỗi hiển thị biểu tượng khay: {e}")
            finally:
                self.running = False

        self.tray_thread = threading.Thread(target=_run, daemon=True)
        self.tray_thread.start()
        print("[+] [Tray UI] Biểu tượng khay hệ thống Windows (NT1) ĐÃ KHỞI CHẠY thành công.")

    def is_running(self) -> bool:
        """Kiểm tra biểu tượng khay hệ thống có đang hoạt động hay không (F5: Chống lạm dụng / Stalkerware)"""
        return self.running and (self.tray_thread is not None and self.tray_thread.is_alive())

    def notify_startup(self, child_name: str = "em"):
        """Thông báo thân thiện, súc tích khi Agent khởi động (NT1 BẮT BUỘC)"""
        def _show():
            # Chờ 1.5 giây để Tray icon ổn định
            time.sleep(1.5)
            # Thử gửi Notification từ icon pystray nếu OS hỗ trợ
            notified = False
            if self.icon and hasattr(self.icon, 'notify'):
                try:
                    self.icon.notify(
                        f"Chào {child_name}! OpenGuardKids đã bật để đồng hành cùng em học tập và giải trí an toàn. ❤️",
                        "🌟 OpenGuardKids Sẵn Sàng"
                    )
                    notified = True
                except Exception:
                    pass

            # Fallback nếu pystray notify chưa kích hoạt trên phiên bản Windows hiện tại
            if not notified:
                try:
                    import ctypes
                    msg = f"Chào {child_name}!\nOpenGuardKids đã bật để đồng hành cùng em sử dụng máy tính vui vẻ & an toàn. ❤️"
                    ctypes.windll.user32.MessageBoxW(0, msg, "🌟 OpenGuardKids", 0x40 | 0x1000)
                except Exception:
                    pass

        threading.Thread(target=_show, daemon=True).start()

    def stop(self):
        """Dừng System Tray Icon"""
        self.running = False
        if self.icon:
            self.icon.stop()
        if self.tray_thread:
            self.tray_thread.join(timeout=1.0)

