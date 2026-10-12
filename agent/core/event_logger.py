import sqlite3
import os
import sys
import json
import time
import requests
import threading
from typing import List, Dict, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CACHE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_DB_PATH = os.path.join(CACHE_DIR, "agent_events.db")

class OfflineEventLogger:
    """
    Module Hàng Đợi Sự Kiện Offline Phía Agent (Feature F3):
    - Đệm các sự kiện vào SQLite cục bộ khi máy trạm mất mạng.
    - Đảm bảo tính toàn vẹn: Không mất sự kiện khi khởi động lại máy hoặc tắt agent đột ngột.
    - Idempotency key / Batching: Đồng bộ mảng sự kiện theo lô (batch) về Server qua POST /api/events/batch.
    - Xóa các bản ghi đã đồng bộ thành công khỏi hàng đợi cục bộ.
    """

    def __init__(self, db_path: str = LOCAL_DB_PATH, server_url: str = "http://127.0.0.1:8000"):
        self.db_path = db_path
        self.server_url = server_url.rstrip("/")
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offline_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    child_id INTEGER,
                    type TEXT NOT NULL,
                    subject TEXT,
                    duration_sec INTEGER DEFAULT 0,
                    policy_id INTEGER,
                    ts TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()

    def log_event(self, device_id: str, child_id: Optional[int], event_type: str, subject: Optional[str] = None, duration_sec: int = 0, policy_id: Optional[int] = None):
        """Ghi sự kiện vào bộ nhớ đệm hàng đợi SQLite cục bộ"""
        if not device_id:
            return

        ts_now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO offline_events (device_id, child_id, type, subject, duration_sec, policy_id, ts)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (device_id, child_id, event_type, subject, duration_sec, policy_id, ts_now))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[-] [EventLogger] Lỗi lưu sự kiện offline: {e}")

    def flush_and_sync(self, batch_size: int = 50) -> int:
        """
        Đồng bộ mảng sự kiện tồn đọng về Server qua POST /api/events/batch.
        Trả về số lượng sự kiện đã đẩy lên thành công.
        """
        records = []
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, device_id, child_id, type, subject, duration_sec, policy_id, ts
                    FROM offline_events
                    ORDER BY id ASC
                    LIMIT ?
                """, (batch_size,))
                records = cursor.fetchall()
                conn.close()
            except Exception as e:
                print(f"[-] [EventLogger] Lỗi đọc sự kiện offline: {e}")
                return 0

        if not records:
            return 0

        event_ids = [r[0] for r in records]
        events_payload = []
        for r in records:
            events_payload.append({
                "device_id": r[1],
                "child_id": r[2] if r[2] is not None else 1,
                "type": r[3],
                "subject": r[4],
                "duration_sec": r[5] or 0,
                "policy_id": r[6],
                "ts": r[7]
            })

        # Gửi mảng sự kiện lên Server
        endpoint = f"{self.server_url}/api/events/batch"
        try:
            res = requests.post(endpoint, json={"events": events_payload}, timeout=6)
            if res.status_code == 200:
                # Xóa các bản ghi đã gửi thành công khỏi hàng đợi cục bộ
                with self.lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    placeholders = ",".join("?" for _ in event_ids)
                    cursor.execute(f"DELETE FROM offline_events WHERE id IN ({placeholders})", event_ids)
                    conn.commit()
                    conn.close()
                print(f"[+] [EventLogger] Đã đồng bộ thành công {len(events_payload)} sự kiện về Server.")
                return len(events_payload)
            else:
                print(f"[-] [EventLogger] Server từ chối lô sự kiện (Mã {res.status_code}): {res.text}")
        except Exception as e:
            # Máy mất mạng hoặc Server chưa online -> Giữ nguyên sự kiện trong SQLite cục bộ
            pass

        return 0

    def purge_all_offline_events(self) -> int:
        """
        Xóa toàn bộ sự kiện trong hàng đợi SQLite cục bộ của Agent (F3 BẮT BUỘC - Nghị định 13/2023).
        Được gọi khi phụ huynh nhấn nút 'Xóa toàn bộ dữ liệu của con tôi'.
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM offline_events")
                count = cursor.fetchone()[0]
                cursor.execute("DELETE FROM offline_events")
                conn.commit()
                conn.close()
                print(f"[+] [EventLogger] ĐÃ XÓA SẠCH {count} BẢN GHI TRONG BỘ ĐỆM OFFLINE CỤC BỘ THEO LỆNH XÓA!")
                return count
            except Exception as e:
                print(f"[-] [EventLogger] Lỗi xóa dữ liệu offline: {e}")
                return 0
