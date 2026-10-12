import socket
import threading
import sys
import os
import time
from typing import List, Dict, Set, Optional, Callable
from dnslib import DNSRecord, DNSQuestion, QTYPE, RR, A, RCODE

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Danh sách miễn chặn vĩnh viễn (Nguyên tắc NT6: An toàn có ưu tiên tuyệt đối)
PERMANENT_ALLOWLIST = {
    "moet.gov.vn",        # Cổng thông tin Bộ GD&ĐT
    "edu.vn",             # Miền giáo dục Việt Nam
    "hcmus.edu.vn",       # Cổng thông tin trường ĐH KHTN
    "tongdai111.vn",      # Tổng đài quốc gia bảo vệ trẻ em 111
    "chinhphu.vn",        # Cổng thông tin Chính phủ
    "localhost",
    "127.0.0.1"
}

# Cưỡng chế SafeSearch cho các công cụ tìm kiếm phổ biến (Google, Bing, YouTube)
# Google SafeSearch VIP: forcesafesearch.google.com -> 216.239.38.120
# Bing SafeSearch VIP: strict.bing.com -> 204.79.197.220
# YouTube VIP: restrict.youtube.com -> 216.239.38.119
SAFESEARCH_MAPPINGS = {
    "google.com": "216.239.38.120",
    "www.google.com": "216.239.38.120",
    "google.com.vn": "216.239.38.120",
    "www.google.com.vn": "216.239.38.120",
    "bing.com": "204.79.197.220",
    "www.bing.com": "204.79.197.220",
    "youtube.com": "216.239.38.119",
    "www.youtube.com": "216.239.38.119"
}

UPSTREAM_DNS = ("8.8.8.8", 53)  # DNS chuyển tiếp mặc định khi truy vấn hợp lệ

class DNSProxyServer:
    """
    Module DNS Proxy Lọc Website Cục Bộ Phía Agent (Feature F2, NT4, NT6):
    - Lắng nghe tại UDP 127.0.0.1:53 (hoặc port cấu hình nếu kiểm thử)
    - Lọc tên miền và toàn bộ wildcard subdomains (*.example.com)
    - Cưỡng chế tìm kiếm an toàn (SafeSearch) cho Google/Bing
    - Danh sách miễn chặn vĩnh viễn bảo vệ trẻ em (NT6)
    - Callback ghi nhận sự kiện domain_query và blocked_domain (F3)
    """

    def __init__(
        self, 
        host: str = "127.0.0.1", 
        port: int = 53, 
        upstream_dns: tuple = UPSTREAM_DNS,
        on_event_callback: Optional[Callable[[dict], None]] = None
    ):
        self.host = host
        self.port = port
        self.upstream_dns = upstream_dns
        self.on_event_callback = on_event_callback

        self.blocked_domains: Dict[str, str] = {}  # domain -> category
        self.running = False
        self.sock: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None

    def update_blocked_domains(self, blocked_list: List[Dict]):
        """Cập nhật danh sách tên miền bị chặn từ Policy mới nhất của Server"""
        new_dict = {}
        for item in blocked_list:
            d = item.get("domain", "").strip().lower().rstrip(".")
            cat = item.get("category", "Chưa phân loại")
            if d:
                new_dict[d] = cat
        self.blocked_domains = new_dict
        print(f"[*] [DNS Proxy] Đã cập nhật {len(self.blocked_domains)} tên miền bị hạn chế.")

    def is_exempt(self, qname: str) -> bool:
        """Kiểm tra tên miền có nằm trong danh sách miễn chặn vĩnh viễn (NT6) hay không"""
        qname = qname.lower().rstrip(".")
        for allow in PERMANENT_ALLOWLIST:
            if qname == allow or qname.endswith("." + allow):
                return True
        return False

    def check_blocked(self, qname: str) -> Optional[str]:
        """
        Kiểm tra qname có bị chặn không.
        Hỗ trợ đối chiếu chính xác và toàn bộ tên miền con (wildcard subdomains).
        Ví dụ: chặn 'tiktok.com' sẽ tự động chặn cả 'v.tiktok.com', 'api.tiktok.com'.
        """
        if self.is_exempt(qname):
            return None

        qname = qname.lower().rstrip(".")
        if qname in self.blocked_domains:
            return self.blocked_domains[qname]

        # Kiểm tra subdomain
        for blocked_domain, cat in self.blocked_domains.items():
            if qname.endswith("." + blocked_domain):
                return cat

        return None

    def get_safesearch_ip(self, qname: str) -> Optional[str]:
        """Kiểm tra tên miền có thuộc diện cưỡng chế SafeSearch không"""
        qname = qname.lower().rstrip(".")
        for engine_domain, ip in SAFESEARCH_MAPPINGS.items():
            if qname == engine_domain or qname.endswith("." + engine_domain):
                return ip
        return None

    def forward_query(self, data: bytes) -> Optional[bytes]:
        """Chuyển tiếp truy vấn hợp lệ lên Upstream DNS server và nhận phản hồi"""
        try:
            forwarder = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            forwarder.settimeout(2.5)
            forwarder.sendto(data, self.upstream_dns)
            response, _ = forwarder.recvfrom(4096)
            forwarder.close()
            return response
        except Exception:
            return None

    def handle_dns_request(self, data: bytes, client_addr: tuple):
        """Xử lý gói tin DNS truy vấn từ trình duyệt / hệ điều hành"""
        try:
            request = DNSRecord.parse(data)
            qname = str(request.q.qname).rstrip(".").lower()
            qtype = QTYPE[request.q.qtype]

            # 1. Kiểm tra chặn tên miền (F2)
            blocked_category = self.check_blocked(qname)
            if blocked_category:
                print(f"[!] [DNS Proxy] CHẶN TÊN MIỀN: '{qname}' (Nhóm: {blocked_category}) từ {client_addr[0]}")
                
                # Phản hồi trỏ về 127.0.0.1 (sinkhole) hoặc NXDOMAIN để ngắt kết nối
                reply = request.reply()
                reply.add_answer(RR(request.q.qname, QTYPE.A, rdata=A("127.0.0.1"), ttl=60))
                self.sock.sendto(reply.pack(), client_addr)

                if self.on_event_callback:
                    self.on_event_callback({
                        "type": "blocked_domain",
                        "subject": qname,
                        "duration_sec": 0,
                        "category": blocked_category
                    })
                return

            # 2. Cưỡng chế SafeSearch (Google/Bing/YouTube)
            safesearch_ip = self.get_safesearch_ip(qname)
            if safesearch_ip and qtype == "A":
                print(f"[+] [DNS Proxy] CƯỠNG CHẾ SAFESEARCH: '{qname}' -> {safesearch_ip}")
                reply = request.reply()
                reply.add_answer(RR(request.q.qname, QTYPE.A, rdata=A(safesearch_ip), ttl=300))
                self.sock.sendto(reply.pack(), client_addr)

                if self.on_event_callback:
                    self.on_event_callback({
                        "type": "domain_query",
                        "subject": qname,
                        "duration_sec": 0,
                        "safesearch": True
                    })
                return

            # 3. Ghi nhận sự kiện truy vấn tên miền hợp lệ (F3)
            if self.on_event_callback:
                self.on_event_callback({
                    "type": "domain_query",
                    "subject": qname,
                    "duration_sec": 0
                })

            # 4. Chuyển tiếp truy vấn ra Upstream DNS
            response_data = self.forward_query(data)
            if response_data:
                self.sock.sendto(response_data, client_addr)
            else:
                # Nếu upstream timeout, trả lời Server Failure (SERVFAIL)
                reply = request.reply()
                reply.header.rcode = RCODE.SERVFAIL
                self.sock.sendto(reply.pack(), client_addr)

        except Exception as e:
            pass

    def run_server(self):
        """Vòng lặp lắng nghe gói tin UDP DNS"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.settimeout(1.0)
            self.running = True
            print(f"[+] [DNS Proxy] Đang chạy tại {self.host}:{self.port} (Upstream: {self.upstream_dns[0]})")

            while self.running:
                try:
                    data, addr = self.sock.recvfrom(4096)
                    # Xử lý trên thread riêng để đảm bảo hiệu năng cao (p50/p95 latency)
                    threading.Thread(target=self.handle_dns_request, args=(data, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception:
                    break
        except Exception as e:
            print(f"[-] [DNS Proxy] Không thể khởi tạo socket tại {self.host}:{self.port}: {e}")
        finally:
            if self.sock:
                self.sock.close()
            self.running = False
            print("[*] [DNS Proxy] Đã dừng máy chủ DNS Proxy.")

    def start_background(self):
        """Khởi chạy máy chủ DNS Proxy trên luồng nền (non-blocking)"""
        if self.running:
            return
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()

    def stop(self):
        """Dừng máy chủ DNS Proxy an toàn"""
        self.running = False
        if self.server_thread:
            self.server_thread.join(timeout=2.0)
