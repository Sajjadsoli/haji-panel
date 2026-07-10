#!/usr/bin/env python3
"""
Haji Panel - Telegram Bot for VPN Sales
ربات تلگرامی فروش VPN با مدیریت کامل

Features (inspired by MirzaBot):
- Auto webhook setup
- Admin management (add/remove admins)
- User registration & tracking
- VPN config sales & delivery
- Wallet/balance system
- Trial accounts
- Service management (renew, extend, reset)
- Payment confirmation (card-to-card)
- Broadcast messaging
- Branding customization
- Multi-language support (fa/en)
- Referral system
- Gift codes
- Support section
"""

import os
import json
import requests
import threading
import time
from datetime import datetime, timedelta

BOT_CONFIG_DIR = "/opt/haji-panel/config"
BOT_CONFIG_FILE = os.path.join(BOT_CONFIG_DIR, "bot.json")
BOT_USERS_FILE = os.path.join(BOT_CONFIG_DIR, "bot_users.json")
BOT_ORDERS_FILE = os.path.join(BOT_CONFIG_DIR, "bot_orders.json")
BRANDING_FILE = os.path.join(BOT_CONFIG_DIR, "branding.json")

TELEGRAM_API = "https://api.telegram.org/bot"


class HajiTelegramBot:
    """ربات تلگرامی فروش VPN"""

    def __init__(self):
        os.makedirs(BOT_CONFIG_DIR, exist_ok=True)
        self._ensure_files()

    def _ensure_files(self):
        if not os.path.exists(BOT_CONFIG_FILE):
            self._save_config({
                "token": "",
                "owner_id": "",
                "webhook_url": "",
                "webhook_set": False,
                "enabled": False,
                "admins": [],
                "products": [
                    {"id": 1, "name": "۱ ماهه", "volume_gb": 30, "duration_days": 30, "price_toman": 50000},
                    {"id": 2, "name": "۳ ماهه", "volume_gb": 100, "duration_days": 90, "price_toman": 120000},
                    {"id": 3, "name": "۶ ماهه", "volume_gb": 200, "duration_days": 180, "price_toman": 220000},
                ],
                "card_number": "",
                "card_holder": "",
                "support_username": "",
                "channel_id": "",
                "force_join": False,
                "trial_enabled": True,
                "trial_volume_gb": 1,
                "trial_duration_hours": 3,
                "referral_enabled": True,
                "referral_percent": 10,
                "welcome_text": "به {brand} خوش آمدید! 🛡️\nبرای خرید VPN روی دکمه زیر بزنید.",
                "language": "fa",
            })

        if not os.path.exists(BOT_USERS_FILE):
            self._save_json(BOT_USERS_FILE, {"users": {}})
        if not os.path.exists(BOT_ORDERS_FILE):
            self._save_json(BOT_ORDERS_FILE, {"orders": []})

    def _load_config(self):
        try:
            with open(BOT_CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_config(self, cfg):
        with open(BOT_CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    def _load_json(self, path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_json(self, path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_users(self):
        return self._load_json(BOT_USERS_FILE)

    def _save_users(self, data):
        self._save_json(BOT_USERS_FILE, data)

    def _load_orders(self):
        return self._load_json(BOT_ORDERS_FILE)

    def _save_orders(self, data):
        self._save_json(BOT_ORDERS_FILE, data)

    def _load_branding(self):
        try:
            with open(BRANDING_FILE) as f:
                return json.load(f)
        except Exception:
            return {"sub_link_title": "Haji Panel", "config_prefix": "Haji"}

    def _tg_api(self, method, data=None):
        """فراخوانی Telegram Bot API"""
        cfg = self._load_config()
        token = cfg.get("token", "")
        if not token:
            return None
        url = f"{TELEGRAM_API}{token}/{method}"
        try:
            resp = requests.post(url, json=data, timeout=30)
            return resp.json()
        except Exception as e:
            print(f"Telegram API error: {e}")
            return None

    # ─── Setup & Webhook ─────────────────────────────────

    def setup(self, token, owner_id, domain=""):
        """تنظیم ربات و ست کردن وب‌هوک"""
        self._save_config({**self._load_config(), "token": token, "owner_id": str(owner_id), "enabled": True})

        # Verify token
        me = self._tg_api("getMe")
        if not me or not me.get("ok"):
            return False, "توکن نامعتبر است"

        bot_username = me["result"]["username"]

        # Set webhook
        if domain:
            webhook_url = f"https://{domain}/bot/webhook"
            result = self._tg_api("setWebhook", {"url": webhook_url, "allowed_updates": ["message", "callback_query"]})
            if result and result.get("ok"):
                cfg = self._load_config()
                cfg["webhook_url"] = webhook_url
                cfg["webhook_set"] = True
                cfg["bot_username"] = bot_username
                self._save_config(cfg)
                return True, f"ربات @{bot_username} فعال شد و وب‌هوک تنظیم شد ✅"
            else:
                return False, "توکن درست اما وب‌هوک تنظیم نشد. دامنه را بررسی کنید."

        return True, f"ربات @{bot_username} فعال شد (وب‌هوک بعداً تنظیم شود)"

    def set_webhook(self, domain):
        """ست کردن وب‌هوک"""
        cfg = self._load_config()
        if not cfg.get("token"):
            return False, "توکن تنظیم نشده"

        webhook_url = f"https://{domain}/bot/webhook"
        result = self._tg_api("setWebhook", {"url": webhook_url, "allowed_updates": ["message", "callback_query"]})
        if result and result.get("ok"):
            cfg["webhook_url"] = webhook_url
            cfg["webhook_set"] = True
            self._save_config(cfg)
            return True, "وب‌هوک تنظیم شد ✅"
        return False, "خطا در تنظیم وب‌هوک"

    def delete_webhook(self):
        """حذف وب‌هوک"""
        result = self._tg_api("deleteWebhook")
        cfg = self._load_config()
        cfg["webhook_set"] = False
        cfg["webhook_url"] = ""
        self._save_config(cfg)
        return result.get("ok", False) if result else False

    # ─── Admin Management ────────────────────────────────

    def add_admin(self, admin_id, name=""):
        cfg = self._load_config()
        admin_id = str(admin_id)
        if admin_id not in cfg.get("admins", []):
            cfg.setdefault("admins", []).append(admin_id)
            self._save_config(cfg)
            return True, f"ادمین {name or admin_id} اضافه شد"
        return False, "این کاربر قبلاً ادمین است"

    def remove_admin(self, admin_id):
        cfg = self._load_config()
        admin_id = str(admin_id)
        if admin_id in cfg.get("admins", []):
            cfg["admins"].remove(admin_id)
            self._save_config(cfg)
            return True, "ادمین حذف شد"
        return False, "این کاربر ادمین نیست"

    def is_admin(self, user_id):
        cfg = self._load_config()
        return str(user_id) == cfg.get("owner_id") or str(user_id) in cfg.get("admins", [])

    def get_admins(self):
        cfg = self._load_config()
        return {"owner": cfg.get("owner_id"), "admins": cfg.get("admins", [])}

    # ─── User Management ─────────────────────────────────

    def register_user(self, user_id, username="", first_name="", referrer=None):
        users = self._load_users()
        uid = str(user_id)
        if uid not in users.get("users", {}):
            users.setdefault("users", {})[uid] = {
                "id": uid,
                "username": username,
                "first_name": first_name,
                "balance": 0,
                "registered_at": datetime.now().isoformat(),
                "referrer": referrer,
                "services": [],
                "banned": False,
                "language": "fa",
            }
            self._save_users(users)

            # Referral bonus
            if referrer and self._load_config().get("referral_enabled"):
                cfg = self._load_config()
                percent = cfg.get("referral_percent", 10)
                # Notify owner
                self._tg_api("sendMessage", {
                    "chat_id": cfg.get("owner_id"),
                    "text": f"👤 کاربر جدید: {first_name} (@{username})\n🆔 {user_id}\n👥 معرف: {referrer}"
                })
        return users.get("users", {}).get(uid)

    def get_user(self, user_id):
        users = self._load_users()
        return users.get("users", {}).get(str(user_id))

    def update_user_balance(self, user_id, amount):
        users = self._load_users()
        uid = str(user_id)
        if uid in users.get("users", {}):
            users["users"][uid]["balance"] += amount
            self._save_users(users)
            return True
        return False

    def ban_user(self, user_id, banned=True):
        users = self._load_users()
        uid = str(user_id)
        if uid in users.get("users", {}):
            users["users"][uid]["banned"] = banned
            self._save_users(users)
            return True
        return False

    def get_all_users(self):
        users = self._load_users()
        return list(users.get("users", {}).values())

    # ─── Products & Orders ───────────────────────────────

    def get_products(self):
        return self._load_config().get("products", [])

    def update_products(self, products):
        cfg = self._load_config()
        cfg["products"] = products
        self._save_config(cfg)

    def create_order(self, user_id, product_id, status="pending_payment"):
        cfg = self._load_config()
        products = cfg.get("products", [])
        product = next((p for p in products if p["id"] == product_id), None)
        if not product:
            return None

        orders = self._load_orders()
        order = {
            "id": len(orders.get("orders", [])) + 1,
            "user_id": str(user_id),
            "product_id": product_id,
            "product_name": product["name"],
            "volume_gb": product["volume_gb"],
            "duration_days": product["duration_days"],
            "price_toman": product["price_toman"],
            "status": status,
            "created_at": datetime.now().isoformat(),
        }
        orders.setdefault("orders", []).append(order)
        self._save_orders(orders)
        return order

    def update_order_status(self, order_id, status):
        orders = self._load_orders()
        for o in orders.get("orders", []):
            if o["id"] == order_id:
                o["status"] = status
                o["updated_at"] = datetime.now().isoformat()
                self._save_orders(orders)
                return True
        return False

    def get_user_orders(self, user_id):
        orders = self._load_orders()
        return [o for o in orders.get("orders", []) if o["user_id"] == str(user_id)]

    def get_pending_orders(self):
        orders = self._load_orders()
        return [o for o in orders.get("orders", []) if o["status"] == "pending_payment"]

    # ─── Trial Accounts ──────────────────────────────────

    def create_trial(self, user_id):
        cfg = self._load_config()
        if not cfg.get("trial_enabled"):
            return None
        return {
            "user_id": str(user_id),
            "volume_gb": cfg.get("trial_volume_gb", 1),
            "duration_hours": cfg.get("trial_duration_hours", 3),
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=cfg.get("trial_duration_hours", 3))).isoformat(),
        }

    # ─── Broadcast ───────────────────────────────────────

    def broadcast(self, text, target="all"):
        """ارسال پیام همگانی"""
        users = self._load_users()
        count = 0
        for uid, u in users.get("users", {}).items():
            if u.get("banned"):
                continue
            if target == "customers" and not u.get("services"):
                continue
            if target == "non_customers" and u.get("services"):
                continue
            self._tg_api("sendMessage", {"chat_id": uid, "text": text})
            count += 1
            time.sleep(0.05)  # Rate limit
        return count

    # ─── Keyboard Generation ─────────────────────────────

    def main_keyboard(self):
        """کیبورد اصلی کاربر"""
        return {
            "keyboard": [
                [{"text": "🔐 خرید اشتراک"}, {"text": "♻️ تمدید سرویس"}],
                [{"text": "🔑 اکانت تستی"}, {"text": "🛍 سرویس‌های من"}],
                [{"text": "🏦 کیف پول"}, {"text": "💵 تعرفه‌ها"}],
                [{"text": "☎️ پشتیبانی"}, {"text": "📚 آموزش"}],
                [{"text": "🎁 کد هدیه"}, {"text": "👥 زیرمجموعه‌گیری"}],
            ],
            "resize_keyboard": True,
        }

    def admin_keyboard(self):
        """کیبورد ادمین"""
        return {
            "keyboard": [
                [{"text": "📊 آمار ربات"}, {"text": "👥 مدیریت کاربران"}],
                [{"text": "💳 پرداخت‌های در انتظار"}, {"text": "📦 مدیریت محصولات"}],
                [{"text": "📢 پیام همگانی"}, {"text": "⚙️ تنظیمات ربات"}],
                [{"text": "🎫 کد هدیه"}, {"text": "🔙 پنل کاربری"}],
            ],
            "resize_keyboard": True,
        }

    # ─── Message Handler ─────────────────────────────────

    def handle_update(self, update):
        """پردازش آپدیت‌های وب‌هوک"""
        cfg = self._load_config()
        if not cfg.get("enabled"):
            return {"ok": False, "error": "ربات غیرفعال است"}

        branding = self._load_branding()
        brand = branding.get("sub_link_title", "Haji Panel")

        msg = update.get("message") or update.get("callback_query", {}).get("message")
        callback = update.get("callback_query")
        chat_id = msg.get("chat", {}).get("id") if msg else None
        user = msg.get("from", {}) if msg else {}
        user_id = user.get("id")
        text = msg.get("text", "") if msg else ""
        username = user.get("username", "")
        first_name = user.get("first_name", "")

        if not chat_id or not user_id:
            return {"ok": True}

        # Register user
        self.register_user(user_id, username, first_name)

        # Check ban
        u = self.get_user(user_id)
        if u and u.get("banned"):
            self._tg_api("sendMessage", {"chat_id": chat_id, "text": "⛔ حساب شما مسدود شده است."})
            return {"ok": True}

        # Check force join
        if cfg.get("force_join") and cfg.get("channel_id"):
            if not self._check_channel_membership(user_id, cfg["channel_id"]):
                self._tg_api("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"⚠️ برای استفاده از ربات، ابتدا در کانال عضو شوید:\n{cfg['channel_id']}"
                })
                return {"ok": True}

        is_admin = self.is_admin(user_id)

        # Handle callback queries
        if callback:
            return self._handle_callback(callback, chat_id, user_id, is_admin, brand)

        # Handle text messages
        return self._handle_text(text, chat_id, user_id, username, first_name, is_admin, brand, cfg)

    def _check_channel_membership(self, user_id, channel_id):
        result = self._tg_api("getChatMember", {"chat_id": channel_id, "user_id": user_id})
        if result and result.get("ok"):
            status = result["result"]["status"]
            return status in ["member", "administrator", "creator"]
        return False

    def _handle_text(self, text, chat_id, user_id, username, first_name, is_admin, brand, cfg):
        # Start command
        if text in ["/start", "شروع", "🔙 پنل کاربری"]:
            welcome = cfg.get("welcome_text", "به {brand} خوش آمدید! 🛡️").replace("{brand}", brand)
            kb = self.admin_keyboard() if is_admin else self.main_keyboard()
            self._tg_api("sendMessage", {"chat_id": chat_id, "text": welcome, "reply_markup": kb})
            return {"ok": True}

        # Admin commands
        if is_admin:
            if text == "📊 آمار ربات":
                users = self.get_all_users()
                pending = self.get_pending_orders()
                stats = f"📊 آمار ربات {brand}\n\n👥 کل کاربران: {len(users)}\n💳 پرداخت‌های در انتظار: {len(pending)}\n📦 محصولات: {len(cfg.get('products', []))}"
                self._tg_api("sendMessage", {"chat_id": chat_id, "text": stats})
                return {"ok": True}

            if text == "💳 پرداخت‌های در انتظار":
                pending = self.get_pending_orders()
                if not pending:
                    self._tg_api("sendMessage", {"chat_id": chat_id, "text": "پرداخت در انتظاری وجود ندارد ✅"})
                else:
                    for o in pending:
                        kb = {"inline_keyboard": [
                            [{"text": "✅ تایید", "callback_data": f"confirm_pay_{o['id']}"},
                             {"text": "❌ رد", "callback_data": f"reject_pay_{o['id']}"}]
                        ]}
                        self._tg_api("sendMessage", {
                            "chat_id": chat_id,
                            "text": f"💳 سفارش #{o['id']}\n👤 کاربر: {o['user_id']}\n📦 محصول: {o['product_name']}\n💰 مبلغ: {o['price_toman']:,} تومان",
                            "reply_markup": kb
                        })
                return {"ok": True}

            if text == "📢 پیام همگانی":
                self._tg_api("sendMessage", {"chat_id": chat_id, "text": "متن پیام را ارسال کنید:"})
                return {"ok": True}

            if text == "⚙️ تنظیمات ربات":
                settings_text = f"⚙️ تنظیمات ربات {brand}\n\n"
                settings_text += f"🟢 وضعیت: {'فعال' if cfg.get('enabled') else 'غیرفعال'}\n"
                settings_text += f"🆔 مالک: {cfg.get('owner_id')}\n"
                settings_text += f"👥 ادمین‌ها: {len(cfg.get('admins', []))}\n"
                settings_text += f"🏦 شماره کارت: {cfg.get('card_number', 'تنظیم نشده')}\n"
                settings_text += f"🔑 اکانت تستی: {'فعال' if cfg.get('trial_enabled') else 'غیرفعال'}\n"
                settings_text += f"👥 زیرمجموعه‌گیری: {'فعال' if cfg.get('referral_enabled') else 'غیرفعال'}\n"
                self._tg_api("sendMessage", {"chat_id": chat_id, "text": settings_text})
                return {"ok": True}

            if text == "👥 مدیریت کاربران":
                users = self.get_all_users()
                total = len(users)
                banned = sum(1 for u in users if u.get("banned"))
                customers = sum(1 for u in users if u.get("services"))
                self._tg_api("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"👥 مدیریت کاربران\n\nکل: {total}\nمشتریان: {customers}\nمسدود شده: {banned}"
                })
                return {"ok": True}

            if text == "📦 مدیریت محصولات":
                products = cfg.get("products", [])
                ptext = "📦 محصولات:\n\n"
                for p in products:
                    ptext += f"🆔 {p['id']} | {p['name']}\n💾 {p['volume_gb']}GB | ⏰ {p['duration_days']} روز | 💰 {p['price_toman']:,} تومان\n\n"
                self._tg_api("sendMessage", {"chat_id": chat_id, "text": ptext})
                return {"ok": True}

        # User commands
        if text == "🔐 خرید اشتراک":
            products = cfg.get("products", [])
            kb = {"inline_keyboard": [[{"text": f"{p['name']} - {p['price_toman']:,} ت", "callback_data": f"buy_{p['id']}"}] for p in products]}
            self._tg_api("sendMessage", {"chat_id": chat_id, "text": "🔐 یکی از پلن‌ها را انتخاب کنید:", "reply_markup": kb})
            return {"ok": True}

        if text == "💵 تعرفه‌ها":
            products = cfg.get("products", [])
            ptext = "💵 تعرفه‌های اشتراک:\n\n"
            for p in products:
                ptext += f"📦 {p['name']}\n💾 حجم: {p['volume_gb']} GB\n⏰ مدت: {p['duration_days']} روز\n💰 قیمت: {p['price_toman']:,} تومان\n{'─'*20}\n"
            self._tg_api("sendMessage", {"chat_id": chat_id, "text": ptext})
            return {"ok": True}

        if text == "🏦 کیف پول":
            u = self.get_user(user_id)
            balance = u.get("balance", 0) if u else 0
            self._tg_api("sendMessage", {
                "chat_id": chat_id,
                "text": f"🏦 کیف پول شما\n\n💰 موجودی: {balance:,} تومان"
            })
            return {"ok": True}

        if text == "🛍 سرویس‌های من":
            u = self.get_user(user_id)
            services = u.get("services", []) if u else []
            if not services:
                self._tg_api("sendMessage", {"chat_id": chat_id, "text": "شما هیچ سرویس فعالی ندارید.\nبرای خرید روی «🔐 خرید اشتراک» بزنید."})
            else:
                stext = "🛍 سرویس‌های شما:\n\n"
                for s in services:
                    stext += f"📦 {s.get('name', 'سرویس')}\n💾 حجم: {s.get('volume_gb', 0)} GB\n⏰ انقضا: {s.get('expires', '—')}\n{'─'*20}\n"
                self._tg_api("sendMessage", {"chat_id": chat_id, "text": stext})
            return {"ok": True}

        if text == "🔑 اکانت تستی":
            if not cfg.get("trial_enabled"):
                self._tg_api("sendMessage", {"chat_id": chat_id, "text": "اکانت تستی فعلاً غیرفعال است."})
                return {"ok": True}
            trial = self.create_trial(user_id)
            if trial:
                self._tg_api("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"🔑 اکانت تستی شما ساخته شد!\n\n💾 حجم: {trial['volume_gb']} GB\n⏰ مدت: {trial['duration_hours']} ساعت\n\nکانفیگ شما به‌زودی ارسال می‌شود."
                })
            return {"ok": True}

        if text == "☎️ پشتیبانی":
            support = cfg.get("support_username", "@support")
            self._tg_api("sendMessage", {"chat_id": chat_id, "text": f"☎️ پشتیبانی:\n\nبرای ارتباط با پشتیبانی به آیدی زیر پیام دهید:\n{support}"})
            return {"ok": True}

        if text == "📚 آموزش":
            self._tg_api("sendMessage", {
                "chat_id": chat_id,
                "text": "📚 آموزش اتصال:\n\n۱. یکی از کلاینت‌های V2ray (V2rayNG، Streisand، V2Box) را نصب کنید.\n۲. کانفیگ دریافتی را کپی کنید.\n۳. در کلاینت، گزینه Import from Clipboard را بزنید.\n۴. متصل شوید! ✅"
            })
            return {"ok": True}

        if text == "👥 زیرمجموعه‌گیری":
            if not cfg.get("referral_enabled"):
                self._tg_api("sendMessage", {"chat_id": chat_id, "text": "سیستم زیرمجموعه‌گیری غیرفعال است."})
                return {"ok": True}
            bot_user = cfg.get("bot_username", "your_bot")
            ref_link = f"https://t.me/{bot_user}?start=ref_{user_id}"
            percent = cfg.get("referral_percent", 10)
            self._tg_api("sendMessage", {
                "chat_id": chat_id,
                "text": f"👥 زیرمجموعه‌گیری\n\nلینک دعوت شما:\n{ref_link}\n\n💰 پورسانت: {percent}% از هر خرید زیرمجموعه"
            })
            return {"ok": True}

        if text == "🎁 کد هدیه":
            self._tg_api("sendMessage", {"chat_id": chat_id, "text": "🎁 کد هدیه خود را ارسال کنید:"})
            return {"ok": True}

        # Default
        self._tg_api("sendMessage", {"chat_id": chat_id, "text": "دستور نامعتبر. از منوی زیر استفاده کنید."})
        return {"ok": True}

    def _handle_callback(self, callback, chat_id, user_id, is_admin, brand):
        data = callback.get("data", "")
        callback_id = callback.get("id")

        # Answer callback
        self._tg_api("answerCallbackQuery", {"callback_query_id": callback_id})

        # Buy product
        if data.startswith("buy_"):
            product_id = int(data.replace("buy_", ""))
            cfg = self._load_config()
            product = next((p for p in cfg.get("products", []) if p["id"] == product_id), None)
            if product:
                order = self.create_order(user_id, product_id)
                card = cfg.get("card_number", "تنظیم نشده")
                holder = cfg.get("card_holder", "")
                self._tg_api("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"🛒 سفارش #{order['id']}\n📦 {product['name']}\n💰 مبلغ: {product['price_toman']:,} تومان\n\n💳 شماره کارت:\n{card}\n👤 {holder}\n\n✅ پس از پرداخت، تصویر رسید را ارسال کنید."
                })
            return {"ok": True}

        # Confirm payment (admin)
        if data.startswith("confirm_pay_") and is_admin:
            order_id = int(data.replace("confirm_pay_", ""))
            self.update_order_status(order_id, "paid")
            order = next((o for o in self._load_orders().get("orders", []) if o["id"] == order_id), None)
            if order:
                self.update_user_balance(int(order["user_id"]), -order["price_toman"])
                self._tg_api("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"✅ پرداخت #{order_id} تایید شد.\nکانفیگ به کاربر ارسال خواهد شد."
                })
                # Notify user
                self._tg_api("sendMessage", {
                    "chat_id": order["user_id"],
                    "text": f"✅ پرداخت شما تایید شد!\n📦 سفارش: {order['product_name']}\n\nکانفیگ شما به‌زودی ارسال می‌شود."
                })
            return {"ok": True}

        # Reject payment (admin)
        if data.startswith("reject_pay_") and is_admin:
            order_id = int(data.replace("reject_pay_", ""))
            self.update_order_status(order_id, "rejected")
            order = next((o for o in self._load_orders().get("orders", []) if o["id"] == order_id), None)
            if order:
                self._tg_api("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"❌ پرداخت #{order_id} رد شد."
                })
                self._tg_api("sendMessage", {
                    "chat_id": order["user_id"],
                    "text": "❌ متاسفانه پرداخت شما تایید نشد. با پشتیبانی در ارتباط باشید."
                })
            return {"ok": True}

        return {"ok": True}

    # ─── Status ──────────────────────────────────────────

    def get_status(self):
        cfg = self._load_config()
        users = self._load_users()
        orders = self._load_orders()
        return {
            "enabled": cfg.get("enabled", False),
            "token_set": bool(cfg.get("token")),
            "bot_username": cfg.get("bot_username", ""),
            "webhook_set": cfg.get("webhook_set", False),
            "webhook_url": cfg.get("webhook_url", ""),
            "owner_id": cfg.get("owner_id", ""),
            "admins": cfg.get("admins", []),
            "total_users": len(users.get("users", {})),
            "total_orders": len(orders.get("orders", [])),
            "pending_payments": len([o for o in orders.get("orders", []) if o["status"] == "pending_payment"]),
            "products": cfg.get("products", []),
            "card_number": cfg.get("card_number", ""),
            "trial_enabled": cfg.get("trial_enabled", True),
            "referral_enabled": cfg.get("referral_enabled", True),
        }
