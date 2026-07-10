#!/usr/bin/env python3
"""
Haji Panel - Reseller/Agency Management
سیستم مدیریت نمایندگی با حجم/یوزر نامحدود، انقضا، دوره تمدید
"""

import os
import json
import uuid as uuid_mod
import time
from datetime import datetime, timedelta

CONFIG_DIR = "/opt/haji-panel/config"
RESELLER_FILE = os.path.join(CONFIG_DIR, "resellers.json")
GRACE_PERIOD_DAYS = 4


class ResellerError(Exception):
    pass


class ResellerNotFoundError(ResellerError):
    pass


class ResellerExpiredError(ResellerError):
    pass


class VolumeExhaustedError(ResellerError):
    pass


class UserLimitExceededError(ResellerError):
    pass


class ResellerManager:
    """مدیریت نمایندگی‌ها"""

    def __init__(self, config_file=None):
        self.config_file = config_file or RESELLER_FILE
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.config_file):
            self._save({"resellers": {}})

    def _load(self):
        try:
            with open(self.config_file) as f:
                return json.load(f)
        except Exception:
            return {"resellers": {}}

    def _save(self, data):
        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def create_reseller(self, name, owner_telegram_id="", reseller_type="volume",
                        data_limit_gb=100, max_users=50, duration_days=30):
        """ساخت نماینده جدید"""
        rid = str(uuid_mod.uuid4())
        now = datetime.now()
        expires = now + timedelta(days=duration_days)

        reseller = {
            "id": rid,
            "name": name,
            "api_key": uuid_mod.uuid4().hex,
            "panel_key": uuid_mod.uuid4().hex,
            "owner_telegram_id": str(owner_telegram_id),
            "type": reseller_type,  # volume or unlimited
            "data_limit_bytes": int(data_limit_gb * 1073741824) if reseller_type == "volume" else 0,
            "data_used_bytes": 0,
            "max_users": max_users,
            "current_users": 0,
            "created_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "status": "active",
            "grace_period_days": GRACE_PERIOD_DAYS,
            "grace_expires_at": None,
            "users": [],
            "bot_token": "",
            "bot_enabled": False,
        }

        data = self._load()
        data["resellers"][rid] = reseller
        self._save(data)
        return reseller

    def delete_reseller(self, reseller_id):
        """حذف نماینده"""
        data = self._load()
        if reseller_id not in data["resellers"]:
            return False
        del data["resellers"][reseller_id]
        self._save(data)
        return True

    def get_reseller(self, reseller_id):
        """دریافت نماینده"""
        data = self._load()
        return data["resellers"].get(reseller_id)

    def get_reseller_by_api_key(self, api_key):
        """دریافت نماینده با API key"""
        data = self._load()
        for r in data["resellers"].values():
            if r.get("api_key") == api_key:
                return r
        return None

    def get_reseller_by_panel_key(self, panel_key):
        """دریافت نماینده با panel key"""
        data = self._load()
        for r in data["resellers"].values():
            if r.get("panel_key") == panel_key:
                return r
        return None

    def get_resellers_by_owner(self, owner_tg_id):
        """دریافت نمایندگی‌های یک مالک"""
        data = self._load()
        return [r for r in data["resellers"].values() if r.get("owner_telegram_id") == str(owner_tg_id)]

    def list_resellers(self):
        """لیست همه نمایندگی‌ها"""
        data = self._load()
        return list(data["resellers"].values())

    def add_volume(self, reseller_id, gb):
        """افزودن حجم به نماینده"""
        data = self._load()
        if reseller_id not in data["resellers"]:
            return False
        r = data["resellers"][reseller_id]
        r["data_limit_bytes"] += int(gb * 1073741824)
        self._save(data)
        return True

    def add_users(self, reseller_id, count):
        """افزودن ظرفیت یوزر"""
        data = self._load()
        if reseller_id not in data["resellers"]:
            return False
        r = data["resellers"][reseller_id]
        r["max_users"] += count
        self._save(data)
        return True

    def extend_reseller(self, reseller_id, days):
        """تمدید نماینده"""
        data = self._load()
        if reseller_id not in data["resellers"]:
            return False
        r = data["resellers"][reseller_id]
        current_expiry = datetime.fromisoformat(r["expires_at"])
        # If already expired, extend from now
        base = max(current_expiry, datetime.now())
        r["expires_at"] = (base + timedelta(days=days)).isoformat()
        r["status"] = "active"
        r["grace_expires_at"] = None
        # Re-enable users
        for u in r.get("users", []):
            u["enabled"] = True
        self._save(data)
        return True

    def check_expired(self):
        """بررسی انقضای همه نمایندگی‌ها"""
        data = self._load()
        now = datetime.now()
        changed = False

        for rid, r in data["resellers"].items():
            if r["status"] in ("deleted",):
                continue

            expires = datetime.fromisoformat(r["expires_at"])

            # Active -> check if expired
            if r["status"] == "active" and now > expires:
                r["status"] = "grace_period"
                r["grace_expires_at"] = (now + timedelta(days=r.get("grace_period_days", GRACE_PERIOD_DAYS))).isoformat()
                # Disable all users
                for u in r.get("users", []):
                    u["enabled"] = False
                changed = True

            # Grace period -> check if expired
            elif r["status"] == "grace_period":
                grace_expires = datetime.fromisoformat(r.get("grace_expires_at", now.isoformat()))
                if now > grace_expires:
                    # Auto-delete
                    del data["resellers"][rid]
                    changed = True

        if changed:
            self._save(data)
        return changed

    def get_status(self, reseller_id):
        """دریافت وضعیت کامل نماینده"""
        r = self.get_reseller(reseller_id)
        if not r:
            return None

        now = datetime.now()
        expires = datetime.fromisoformat(r["expires_at"])
        time_remaining = max(0, (expires - now).total_seconds())

        data_remaining = max(0, r["data_limit_bytes"] - r["data_used_bytes"]) if r["type"] == "volume" else 0

        return {
            "id": r["id"],
            "name": r["name"],
            "type": r["type"],
            "status": r["status"],
            "data_limit_gb": round(r["data_limit_bytes"] / 1073741824, 2) if r["data_limit_bytes"] > 0 else 0,
            "data_used_gb": round(r["data_used_bytes"] / 1073741824, 2),
            "data_remaining_gb": round(data_remaining / 1073741824, 2),
            "max_users": r["max_users"],
            "current_users": r["current_users"],
            "created_at": r["created_at"],
            "expires_at": r["expires_at"],
            "time_remaining_seconds": int(time_remaining),
            "grace_expires_at": r.get("grace_expires_at"),
            "bot_enabled": r.get("bot_enabled", False),
            "panel_key": r.get("panel_key", ""),
        }

    def create_user_under_reseller(self, reseller_id, user_data):
        """ساخت یوزر تحت نماینده"""
        data = self._load()
        if reseller_id not in data["resellers"]:
            raise ResellerNotFoundError("نماینده یافت نشد")

        r = data["resellers"][reseller_id]

        if r["status"] != "active":
            raise ResellerExpiredError("نماینده فعال نیست")

        if r["current_users"] >= r["max_users"]:
            raise UserLimitExceededError("حداکثر تعداد یوزر رسید")

        if r["type"] == "volume":
            user_volume = user_data.get("volume_gb", 1)
            needed = int(user_volume * 1073741824)
            if r["data_used_bytes"] + needed > r["data_limit_bytes"]:
                raise VolumeExhaustedError("حجم کافی نیست")

        uid = str(uuid_mod.uuid4())
        user = {
            "id": uid,
            "name": user_data.get("name", ""),
            "email": user_data.get("email", ""),
            "volume_gb": user_data.get("volume_gb", 1),
            "duration_days": user_data.get("duration_days", 30),
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=user_data.get("duration_days", 30))).isoformat(),
            "enabled": True,
            "access_key": uuid_mod.uuid4().hex,
        }

        r["users"].append(user)
        r["current_users"] = len(r["users"])
        self._save(data)
        return user

    def list_reseller_users(self, reseller_id):
        """لیست یوزرهای نماینده"""
        r = self.get_reseller(reseller_id)
        if not r:
            return []
        return r.get("users", [])

    def delete_reseller_user(self, reseller_id, user_id):
        """حذف یوزر نماینده"""
        data = self._load()
        if reseller_id not in data["resellers"]:
            return False
        r = data["resellers"][reseller_id]
        r["users"] = [u for u in r.get("users", []) if u["id"] != user_id]
        r["current_users"] = len(r["users"])
        self._save(data)
        return True

    def update_reseller_settings(self, reseller_id, settings):
        """بروزرسانی تنظیمات نماینده"""
        data = self._load()
        if reseller_id not in data["resellers"]:
            return False
        r = data["resellers"][reseller_id]
        for key in ["name", "bot_token", "bot_enabled", "max_users", "data_limit_gb", "owner_telegram_id"]:
            if key in settings:
                if key == "data_limit_gb":
                    r["data_limit_bytes"] = int(settings[key] * 1073741824)
                elif key == "max_users":
                    r["max_users"] = int(settings[key])
                else:
                    r[key] = settings[key]
        self._save(data)
        return True

    def record_user_traffic(self, reseller_id, user_id, bytes_used):
        """ثبت ترافیک یوزر نماینده"""
        data = self._load()
        if reseller_id not in data["resellers"]:
            return False
        r = data["resellers"][reseller_id]
        r["data_used_bytes"] += bytes_used

        # Check if volume exhausted
        if r["type"] == "volume" and r["data_used_bytes"] >= r["data_limit_bytes"]:
            for u in r.get("users", []):
                u["enabled"] = False

        self._save(data)
        return True
