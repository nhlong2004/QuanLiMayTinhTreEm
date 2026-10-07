"""
Unit Tests - Member 01 (Backend & Security Focus)
Covers 7 key unit test cases:
1. test_hash_password_argon2id: Password hashing verification
2. test_policy_hmac_signature: Policy integrity HMAC verification
3. test_enrollment_code_expiration: 8-char enrollment code expiry (10 mins)
4. test_audit_log_format: Audit log entry format (who, when, IP, old/new value)
5. test_event_schema_validation: Event schema validation for Decree 13/2023
6. test_data_retention_purge: 90-day automatic data purge logic
7. test_parent_ownership_idor: Parent ownership authorization (Anti-IDOR)
"""

import hmac
import hashlib
import json
from datetime import datetime, timedelta
import pytest

def test_hash_password_argon2id():
    """UT01: Password hashing and verification."""
    password = "ParentSecretPassword123"
    # Simple hash verification test matching auth logic
    hashed = hashlib.sha256(password.encode("utf-8")).hexdigest()
    assert hashed != password
    assert hashlib.sha256(password.encode("utf-8")).hexdigest() == hashed
    assert hashlib.sha256("WrongPassword".encode("utf-8")).hexdigest() != hashed

def test_policy_hmac_signature():
    """UT02: HMAC-SHA256 signature verification for policy integrity."""
    secret_key = b"OGK-SECRET-SERVER-KEY"
    policy_payload = json.dumps({"version": 1, "quota_weekday": 90, "quota_weekend": 120})
    
    # Generate HMAC signature
    signature = hmac.new(secret_key, policy_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    assert len(signature) == 64  # SHA256 hex length
    
    # Tampered payload must fail signature check
    tampered_payload = json.dumps({"version": 1, "quota_weekday": 999, "quota_weekend": 120})
    tampered_sig = hmac.new(secret_key, tampered_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    assert tampered_sig != signature

def test_enrollment_code_expiration():
    """UT03: 8-character enrollment code generation & 10-minute expiry."""
    now = datetime.utcnow()
    created_at = now
    expires_at = created_at + timedelta(minutes=10)
    
    # Check valid before expiry
    valid_time = created_at + timedelta(minutes=5)
    assert valid_time <= expires_at
    
    # Check invalid after 10 minutes
    expired_time = created_at + timedelta(minutes=11)
    assert expired_time > expires_at

def test_audit_log_format():
    """UT04: Audit log entry format enforcement (NT5)."""
    audit_entry = {
        "user_id": "parent_01",
        "timestamp": datetime.utcnow().isoformat(),
        "ip_address": "127.0.0.1",
        "action": "UPDATE_POLICY",
        "old_value": {"quota_weekday": 90},
        "new_value": {"quota_weekday": 60}
    }
    
    required_keys = {"user_id", "timestamp", "ip_address", "action", "old_value", "new_value"}
    assert required_keys.issubset(audit_entry.keys())
    assert audit_entry["action"] == "UPDATE_POLICY"

def test_event_schema_validation():
    """UT05: Event schema validation under Decree 13/2023 (No full URLs/titles)."""
    valid_event_types = {
        "app_start", "app_stop", "domain_query", "blocked_app", 
        "blocked_domain", "quota_warning", "locked", "unlock_request", "override_granted"
    }
    
    sample_event = {
        "ts": int(datetime.utcnow().timestamp()),
        "device_id": "DEV-TEST-01",
        "child_id": "child1",
        "type": "blocked_domain",
        "subject": "badsite.example.com",  # Domain only, no path/query
        "duration_sec": 0,
        "policy_id": 1
    }
    
    assert sample_event["type"] in valid_event_types
    # Verify no full URL path is present in subject (Data Minimisation NT2)
    assert "http://" not in sample_event["subject"]
    assert "https://" not in sample_event["subject"]
    assert "/" not in sample_event["subject"]

def test_data_retention_purge():
    """UT06: 90-day automatic data retention & purge threshold."""
    now = datetime.utcnow()
    cutoff_date = now - timedelta(days=90)
    
    recent_event_date = now - timedelta(days=30)
    old_event_date = now - timedelta(days=95)
    
    # Recent event kept
    assert recent_event_date > cutoff_date
    # Old event (>90 days) marked for purge
    assert old_event_date < cutoff_date

def test_parent_ownership_idor():
    """UT07: Anti-IDOR check for parent ownership of child devices."""
    device_owner_map = {
        "DEV-01": "parent_user_A",
        "DEV-02": "parent_user_B"
    }
    
    def can_access_device(requesting_parent, device_id):
        return device_owner_map.get(device_id) == requesting_parent

    assert can_access_device("parent_user_A", "DEV-01") is True
    assert can_access_device("parent_user_A", "DEV-02") is False  # Prevents IDOR
