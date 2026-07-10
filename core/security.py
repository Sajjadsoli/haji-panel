#!/usr/bin/env python3
"""
Haji Panel - Security Module
ماژول امنیتی پنل: Brute-force protection, CSRF, Session timeout, Login logging
"""

import os
import json
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock

SECURITY_DIR = "/opt/haji-panel/config"
SECURITY_FILE = os.path.join(SECURITY_DIR, "security.json")
LOGIN_LOG_FILE = os.path.join(SECURITY_DIR, "login_attempts.json")

_lock = Lock()


class SecurityManager:
    """مدیریت امنیتی پنل"""

    def __init__(self):
        os.makedirs(SECURITY_DIR, exist_ok=True)
        self._ensure_files()

    def _ensure_files(self):
        if not os.path.exists(SECURITY_FILE):
            self._save({
                "max_login_attempts": 5,
                "lockout_duration_minutes": 15,
                "session_timeout_minutes": 30,
                "ip_whitelist": [],
                "ip_whitelist_enabled": False,
                "two_factor_enabled": False,
                "two_factor_secret": "",
                "csrf_enabled": True,
                "hide_server_info": True,
                "auto_block_suspicious": True,
            })
        if not os.path.exists(LOGIN_LOG_FILE):
            self._save_log({"attempts": []})

    def _load(self):
        try:
            with open(SECURITY_FILE) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, data):
        with open(SECURITY_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_log(self):
        try:
            with open(LOGIN_LOG_FILE) as f:
                return json.load(f)
        except Exception:
            return {"attempts": []}

    def _save_log(self, data):
        with open(LOGIN_LOG_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ─── Brute-Force Protection ─────────────────────────

    _attempts = defaultdict(list)
    _locked = {}

    def check_rate_limit(self, ip):
        """بررسی محدودیت نرخ ورود"""
        cfg = self._load()
        max_attempts = cfg.get("max_login_attempts", 5)
        lockout_min = cfg.get("lockout_duration_minutes", 15)

        now = time.time()

        # Check if IP is locked
        if ip in self._locked:
            unlock_time = self._locked[ip]
            if now < unlock_time:
                remaining = int(unlock_time - now)
                return False, f"IP مسدود است. {remaining} ثانیه صبر کنید."
            else:
                del self._locked[ip]
                self._attempts[ip] = []

        # Clean old attempts (older than lockout window)
        window = lockout_min * 60
        self._attempts[ip] = [t for t in self._attempts[ip] if now - t < window]

        if len(self._attempts[ip]) >= max_attempts:
            self._locked[ip] = now + window
            self.log_attempt(ip, "locked_out")
            return False, f"تلاش‌های زیادی انجام شد. IP برای {lockout_min} دقیقه مسدود شد."

        return True, "OK"

    def record_failed_login(self, ip):
        """ثبت تلاش ناموفق ورود"""
        with _lock:
            self._attempts[ip].append(time.time())
        self.log_attempt(ip, "failed")

    def record_successful_login(self, ip):
        """ثبت ورود موفق"""
        with _lock:
            self._attempts[ip] = []
            if ip in self._locked:
                del self._locked[ip]
        self.log_attempt(ip, "success")

    def log_attempt(self, ip, status):
        """ثبت لاگ تلاش ورود"""
        log = self._load_log()
        entry = {
            "ip": ip,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }
        log.setdefault("attempts", []).append(entry)
        # Keep last 200 entries
        log["attempts"] = log["attempts"][-200:]
        self._save_log(log)

    def get_login_log(self, limit=50):
        """دریافت لاگ تلاش‌های ورود"""
        log = self._load_log()
        return log.get("attempts", [])[-limit:]

    # ─── IP Whitelist ────────────────────────────────────

    def check_ip_whitelist(self, ip):
        """بررسی لیست سفید IP"""
        cfg = self._load()
        if not cfg.get("ip_whitelist_enabled", False):
            return True
        whitelist = cfg.get("ip_whitelist", [])
        return ip in whitelist

    def add_to_whitelist(self, ip):
        cfg = self._load()
        if ip not in cfg.get("ip_whitelist", []):
            cfg.setdefault("ip_whitelist", []).append(ip)
            self._save(cfg)
        return True

    def remove_from_whitelist(self, ip):
        cfg = self._load()
        if ip in cfg.get("ip_whitelist", []):
            cfg["ip_whitelist"].remove(ip)
            self._save(cfg)
        return True

    # ─── CSRF Protection ─────────────────────────────────

    _csrf_tokens = set()

    def generate_csrf_token(self):
        """تولید توکن CSRF"""
        token = secrets.token_hex(32)
        self._csrf_tokens.add(token)
        return token

    def validate_csrf_token(self, token):
        """اعتبارسنجی توکن CSRF"""
        if not token:
            return False
        if token in self._csrf_tokens:
            self._csrf_tokens.discard(token)
            return True
        return False

    # ─── Session Management ──────────────────────────────

    def get_session_timeout(self):
        """دریافت زمان انقضای سشن"""
        cfg = self._load()
        return cfg.get("session_timeout_minutes", 30) * 60

    def is_session_valid(self, session_data):
        """بررسی اعتبار سشن"""
        if not session_data.get("authenticated"):
            return False
        login_time = session_data.get("login_time", 0)
        timeout = self.get_session_timeout()
        if time.time() - login_time > timeout:
            return False
        return True

    # ─── 2FA ─────────────────────────────────────────────

    def generate_2fa_secret(self):
        """تولید رمز 2FA"""
        secret = secrets.token_hex(16)
        cfg = self._load()
        cfg["two_factor_secret"] = secret
        cfg["two_factor_enabled"] = True
        self._save(cfg)
        return secret

    def disable_2fa(self):
        """غیرفعال‌سازی 2FA"""
        cfg = self._load()
        cfg["two_factor_enabled"] = False
        cfg["two_factor_secret"] = ""
        self._save(cfg)

    def is_2fa_enabled(self):
        return self._load().get("two_factor_enabled", False)

    # ─── Settings ────────────────────────────────────────

    def get_settings(self):
        return self._load()

    def update_settings(self, settings):
        cfg = self._load()
        cfg.update(settings)
        self._save(cfg)
        return True

    def get_status(self):
        cfg = self._load()
        log = self._load_log()
        recent = log.get("attempts", [])[-20:]
        failed = sum(1 for a in recent if a["status"] == "failed")
        locked = sum(1 for a in recent if a["status"] == "locked_out")
        return {
            "max_login_attempts": cfg.get("max_login_attempts", 5),
            "lockout_duration_minutes": cfg.get("lockout_duration_minutes", 15),
            "session_timeout_minutes": cfg.get("session_timeout_minutes", 30),
            "ip_whitelist_enabled": cfg.get("ip_whitelist_enabled", False),
            "ip_whitelist_count": len(cfg.get("ip_whitelist", [])),
            "two_factor_enabled": cfg.get("two_factor_enabled", False),
            "csrf_enabled": cfg.get("csrf_enabled", True),
            "hide_server_info": cfg.get("hide_server_info", True),
            "recent_failed_logins": failed,
            "recent_lockouts": locked,
            "total_logged_attempts": len(log.get("attempts", [])),
        }
