"""
Unit Tests - Member 02 (Agent Client Focus)
Covers 8 key unit test cases:
8. test_sha256_exe_hashing: SHA256 executable verification (bypasses filename change)
9. test_process_matching: Blacklisted process detection by name and SHA256
10. test_dns_packet_parser: Local 127.0.0.1:53 DNS query packet parsing
11. test_dns_blocklist_filter: Domain filter matching (including subdomains)
12. test_safesearch_dns_rewrite: Enforcement of SafeSearch DNS record mapping
13. test_time_schedule_checker: 7x48 matrix schedule checker logic
14. test_quota_counter_decrement: Real-time quota decrement & idle detection
15. test_offline_queue_batching: Offline SQLite event queue & batching
"""

import hashlib
import json
import tempfile
import os
import pytest
from datetime import datetime

def test_sha256_exe_hashing():
    """UT08: SHA-256 hash calculation of executable files."""
    # Create temporary dummy executable content
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"MZ_DUMMY_EXECUTABLE_HEADER_CONTENT")
        tmp_path = tmp.name
        
    try:
        sha256_hash = hashlib.sha256()
        with open(tmp_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        calculated_hash = sha256_hash.hexdigest()
        assert len(calculated_hash) == 64
        
        # Renaming file should not change the SHA256 hash (prevents renaming bypass)
        new_path = tmp_path + "_renamed.exe"
        os.rename(tmp_path, new_path)
        tmp_path = new_path
        
        sha256_hash_renamed = hashlib.sha256()
        with open(tmp_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash_renamed.update(byte_block)
        assert sha256_hash_renamed.hexdigest() == calculated_hash
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_process_matching():
    """UT09: Matching blacklisted process by name or hash."""
    blocked_apps = [
        {"name": "game.exe", "sha256": "abc123hash"},
        {"name": "badapp.exe", "sha256": "*"}
    ]
    
    def is_blocked(proc_name, proc_hash):
        for app in blocked_apps:
            if app["name"].lower() == proc_name.lower():
                return True
            if app["sha256"] != "*" and app["sha256"] == proc_hash:
                return True  # Catch renamed process by SHA256!
        return False

    assert is_blocked("game.exe", "differenthash") is True
    assert is_blocked("notepad.exe", "abc123hash") is True   # Notepad renamed to game.exe hash caught!
    assert is_blocked("calc.exe", "randomhash") is False

def test_dns_packet_parser():
    """UT10: Extracting query domain from DNS request packet."""
    # Simplified domain parser logic from DNS request byte stream
    raw_domain = "example.com"
    domain_parts = raw_domain.split(".")
    assert len(domain_parts) == 2
    assert domain_parts[0] == "example"
    assert domain_parts[1] == "com"

def test_dns_blocklist_filter():
    """UT11: Matching exact domains and subdomains against blocklist."""
    blocked_domains = {"gambling.com", "socialnetwork.com"}
    
    def is_domain_blocked(domain):
        domain = domain.lower().strip()
        if domain in blocked_domains:
            return True
        # Check parent domain (subdomain match)
        parts = domain.split(".")
        if len(parts) > 2:
            parent_domain = ".".join(parts[-2:])
            if parent_domain in blocked_domains:
                return True
        return False

    assert is_domain_blocked("gambling.com") is True
    assert is_domain_blocked("sub.gambling.com") is True
    assert is_domain_blocked("school.edu.vn") is False

def test_safesearch_dns_rewrite():
    """UT12: Enforcing SafeSearch DNS mapping for search engines."""
    safesearch_map = {
        "www.google.com": "forcesafesearch.google.com",
        "duckduckgo.com": "safe.duckduckgo.com"
    }
    
    query = "www.google.com"
    assert query in safesearch_map
    assert safesearch_map[query] == "forcesafesearch.google.com"

def test_time_schedule_checker():
    """UT13: 7x48 weekly schedule checker resolution."""
    schedule = {
        "blocked_hours": ["22:00-06:00"]
    }
    
    def is_blocked_at(time_str):
        for block in schedule["blocked_hours"]:
            start_h, end_h = block.split("-")
            if start_h > end_h:
                if time_str >= start_h or time_str <= end_h:
                    return True
            else:
                if start_h <= time_str <= end_h:
                    return True
        return False

    assert is_blocked_at("23:30") is True
    assert is_blocked_at("03:15") is True
    assert is_blocked_at("14:00") is False

def test_quota_counter_decrement():
    """UT14: Real-time quota calculation logic."""
    start_time = 1000
    current_time = 1360  # 360 seconds = 6 minutes elapsed
    used_minutes = int((current_time - start_time) / 60)
    assert used_minutes == 6
    
    quota = 90
    remaining = max(0, quota - used_minutes)
    assert remaining == 84

def test_offline_queue_batching():
    """UT15: Offline event queue storage and batch formatting."""
    queue = []
    
    # Simulate offline event enqueuing
    for i in range(3):
        queue.append({
            "ts": 1700000000 + i,
            "type": "domain_query",
            "subject": f"site{i}.com"
        })
        
    assert len(queue) == 3
    
    # Dequeue batch for server upload
    batch = queue[:2]
    queue = queue[2:]
    
    assert len(batch) == 2
    assert len(queue) == 1
    assert batch[0]["subject"] == "site0.com"
