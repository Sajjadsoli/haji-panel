#!/usr/bin/env python3
"""
Haji Panel - Traffic & Time Monitor
مانیتورینگ حجم مصرفی و زمان باقی‌مانده هر ساب‌دامنه
"""

import os
import json
import time
from datetime import datetime, timedelta


class TrafficMonitor:
    """مدیریت حجم و زمان ساب‌دامنه‌ها"""

    def __init__(self):
        self.config_dir = "/opt/haji-panel/config"
        self.traffic_file = os.path.join(self.config_dir, "traffic.json")
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.traffic_file):
            os.makedirs(self.config_dir, exist_ok=True)
            self._save_raw({"subdomains": {}})

    def _load(self):
        try:
            with open(self.traffic_file) as f:
                return json.load(f)
        except Exception:
            return {"subdomains": {}}

    def _save(self, data):
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.traffic_file, "w") as f:
            json.dump(data, f, indent=2)

    def _save_raw(self, data):
        self._save(data)

    def init_subdomain(self, name, data_limit_gb=10, time_limit_hours=720, port=5000):
        """راه‌اندازی مانیتورینگ برای ساب‌دامنه جدید"""
        data = self._load()
        data["subdomains"][name] = {
            "name": name,
            "port": port,
            "data_limit_bytes": int(data_limit_gb * 1073741824),
            "data_used_bytes": 0,
            "time_limit_seconds": int(time_limit_hours * 3600),
            "time_used_seconds": 0,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=time_limit_hours)).isoformat(),
            "last_active": datetime.now().isoformat(),
            "status": "active",
            "history": [],
        }
        self._save(data)
        return True

    def remove_subdomain(self, name):
        """حذف مانیتورینگ ساب‌دامنه"""
        data = self._load()
        if name in data["subdomains"]:
            del data["subdomains"][name]
            self._save(data)
        return True

    def record_traffic(self, name, bytes_in, bytes_out):
        """ثبت ترافیک مصرفی"""
        data = self._load()
        if name not in data["subdomains"]:
            return False

        sub = data["subdomains"][name]
        total = bytes_in + bytes_out
        sub["data_used_bytes"] += total
        sub["last_active"] = datetime.now().isoformat()

        # Add to history (keep last 100 entries)
        today = datetime.now().strftime("%Y-%m-%d %H:00")
        history = sub.get("history", [])
        if history and history[-1]["time"] == today:
            history[-1]["bytes"] += total
        else:
            history.append({"time": today, "bytes": total})
        sub["history"] = history[-100:]

        # Check limits
        if sub["data_used_bytes"] >= sub["data_limit_bytes"]:
            sub["status"] = "data_exceeded"
        elif self._is_expired(name):
            sub["status"] = "expired"
        else:
            sub["status"] = "active"

        self._save(data)
        return True

    def record_time(self, name, seconds):
        """ثبت زمان مصرفی"""
        data = self._load()
        if name not in data["subdomains"]:
            return False

        sub = data["subdomains"][name]
        sub["time_used_seconds"] += seconds
        sub["last_active"] = datetime.now().isoformat()

        if self._is_expired(name):
            sub["status"] = "expired"
        elif sub["data_used_bytes"] >= sub["data_limit_bytes"]:
            sub["status"] = "data_exceeded"
        else:
            sub["status"] = "active"

        self._save(data)
        return True

    def _is_expired(self, name):
        data = self._load()
        if name not in data["subdomains"]:
            return True
        sub = data["subdomains"][name]
        expires = datetime.fromisoformat(sub["expires_at"])
        return datetime.now() > expires

    def get_status(self, name):
        """دریافت وضعیت کامل ساب‌دامنه"""
        data = self._load()
        if name not in data["subdomains"]:
            return None

        sub = data["subdomains"][name]
        now = datetime.now()
        expires = datetime.fromisoformat(sub["expires_at"])
        created = datetime.fromisoformat(sub["created_at"])

        data_remaining = max(0, sub["data_limit_bytes"] - sub["data_used_bytes"])
        time_remaining = max(0, (expires - now).total_seconds())

        data_percent = round((sub["data_used_bytes"] / sub["data_limit_bytes"]) * 100, 1) if sub["data_limit_bytes"] > 0 else 0
        time_percent = round((1 - time_remaining / sub["time_limit_seconds"]) * 100, 1) if sub["time_limit_seconds"] > 0 else 0

        # Update status
        if self._is_expired(name):
            sub["status"] = "expired"
        elif sub["data_used_bytes"] >= sub["data_limit_bytes"]:
            sub["status"] = "data_exceeded"
        else:
            sub["status"] = "active"
        self._save(data)

        return {
            "name": sub["name"],
            "port": sub["port"],
            "status": sub["status"],
            "data_limit_bytes": sub["data_limit_bytes"],
            "data_used_bytes": sub["data_used_bytes"],
            "data_remaining_bytes": data_remaining,
            "data_percent": data_percent,
            "time_limit_seconds": sub["time_limit_seconds"],
            "time_used_seconds": sub["time_used_seconds"],
            "time_remaining_seconds": int(time_remaining),
            "time_percent": time_percent,
            "created_at": sub["created_at"],
            "expires_at": sub["expires_at"],
            "last_active": sub.get("last_active", ""),
            "history": sub.get("history", []),
        }

    def get_all_status(self):
        """دریافت وضعیت همه ساب‌دامنه‌ها"""
        data = self._load()
        result = []
        for name in data["subdomains"]:
            s = self.get_status(name)
            if s:
                result.append(s)
        return result

    def get_configs(self, name, server_ip=""):
        """تولید کانفیگ‌های قابل کپی برای ساب‌دامنه"""
        import base64
        import uuid as uuid_mod

        data = self._load()
        if name not in data["subdomains"]:
            return []

        sub = data["subdomains"][name]
        uid = str(uuid_mod.uuid4())
        port = sub.get("port", 443)
        host = name

        configs = []

        # VLESS (Reality)
        configs.append({
            "type": "vless",
            "name": "VLESS Reality",
            "icon": "🟢",
            "link": f"vless://{uid}@{host}:443?encryption=none&security=reality&sni={host}&fp=chrome&type=tcp&flow=xtls-rprx-vision#Haji-{name}",
            "desc": "VLESS با Reality - ضد‌فیلتر قوی"
        })

        # VMess
        vmess_json = json.dumps({
            "v": "2", "ps": f"Haji-{name}",
            "add": host, "port": "443",
            "id": uid, "aid": "0",
            "net": "ws", "type": "none",
            "host": host, "path": "/",
            "tls": "tls"
        })
        vmess_b64 = base64.b64encode(vmess_json.encode()).decode()
        configs.append({
            "type": "vmess",
            "name": "VMess WS TLS",
            "icon": "🔵",
            "link": f"vmess://{vmess_b64}",
            "desc": "VMess با WebSocket و TLS"
        })

        # Trojan
        configs.append({
            "type": "trojan",
            "name": "Trojan",
            "icon": "🟣",
            "link": f"trojan://{uid}@{host}:443?security=tls&sni={host}#Haji-{name}",
            "desc": "Trojan با TLS"
        })

        # VLESS gRPC
        configs.append({
            "type": "vless-grpc",
            "name": "VLESS gRPC",
            "icon": "🟡",
            "link": f"vless://{uid}@{host}:443?encryption=none&security=tls&sni={host}&type=grpc&serviceName=haji&mode=gun#Haji-gRPC-{name}",
            "desc": "VLESS با gRPC - مناسب CDN"
        })

        # Shadowsocks
        configs.append({
            "type": "ss",
            "name": "Shadowsocks",
            "icon": "🔴",
            "link": f"ss://YWVzLTI1Ni1nY206{uid[:16]}@{host}:8388#Haji-SS-{name}",
            "desc": "Shadowsocks - سبک و سریع"
        })

        # Subscription link
        configs.append({
            "type": "sub",
            "name": "لینک اشتراک (Subscription)",
            "icon": "📋",
            "link": f"https://{host}/sub/{name}",
            "desc": "لینک اشتراک برای ایمپورت خودکار در کلاینت‌ها"
        })

        return configs

    def update_limits(self, name, data_limit_gb=None, time_limit_hours=None):
        """بروزرسانی محدودیت‌ها"""
        data = self._load()
        if name not in data["subdomains"]:
            return False

        sub = data["subdomains"][name]
        if data_limit_gb is not None:
            sub["data_limit_bytes"] = int(data_limit_gb * 1073741824)
        if time_limit_hours is not None:
            sub["time_limit_seconds"] = int(time_limit_hours * 3600)
            sub["expires_at"] = (datetime.now() + timedelta(hours=time_limit_hours)).isoformat()

        self._save(data)
        return True

    def reset_usage(self, name):
        """ریست مصرف"""
        data = self._load()
        if name not in data["subdomains"]:
            return False

        sub = data["subdomains"][name]
        sub["data_used_bytes"] = 0
        sub["time_used_seconds"] = 0
        sub["history"] = []
        sub["status"] = "active"
        sub["created_at"] = datetime.now().isoformat()
        sub["expires_at"] = (datetime.now() + timedelta(seconds=sub["time_limit_seconds"])).isoformat()

        self._save(data)
        return True
