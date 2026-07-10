# 🛡️ Haji Panel - پنل مدیریت سرور ضد‌فیلتر

![Haji Panel Banner](assets/banner.jpeg)

> سیستم مدیریت سرور خودکار با ضد‌فیلتر، Nginx، SSL و پنل وب حرفه‌ای

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/Platform-Ubuntu%2020.04%2B-green.svg)](https://ubuntu.com/)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()

## ✨ امکانات

- 🚀 **نصب خودکار** با یک خط دستور
- 🛡️ **ضد‌فیلتر** خودکار سرور (Cloudflare DNS, DoH, CDN)
- 🌐 **Nginx** نصب و کانفیگ خودکار
- 🔒 **SSL/HTTPS** رایگان با Certbot
- 📊 **پنل وب** زیبا و حرفه‌ای
- 🔑 **مدیریت دامنه** و ضد‌فیلتر دامنه
- 📈 **مانیتورینگ** منابع سرور (CPU, RAM, Network)
- 🔥 **فایروال** خودکار (UFW)
- ⚡ **Cloudflare Warp** برای ضد‌فیلتر
- 🔄 **DoH** (DNS over HTTPS) برای دور زدن فیلتر DNS
- 📱 **واکنش‌گرا** (Responsive) برای موبایل و دسکتاپ

---

## 🚀 نصب سریع (یک خط)

### روش ۱: نصب مستقیم از GitHub

```bash
bash <(curl -sL https://raw.githubusercontent.com/Sajjadsoli/haji-panel/main/scripts/install.sh)
```

### روش ۲: کلون و نصب

```bash
git clone https://github.com/Sajjadsoli/haji-panel.git
cd haji-panel
chmod +x scripts/install.sh
sudo bash scripts/install.sh
```

---

## 📋 پیش‌نیازها

| مورد | حداقل |
|------|-------|
| سیستم‌عامل | Ubuntu 20.04 / 22.04 / 24.04 |
| RAM | 512 MB |
| دسترسی | Root / Sudo |
| پورت‌ها | 80, 443, 8443 |

---

## 🔧 مراحل نصب

نصب‌کننده خودکار به ترتیب کارهای زیر را انجام می‌دهد:

1. ✅ آپدیت سیستم و نصب پیش‌نیازها
2. ✅ نصب Nginx
3. ✅ نصب و کانفیگ ضد‌فیلتر (Cloudflare Warp + DoH)
4. ✅ نصب Certbot برای SSL
5. ✅ کانفیگ فایروال (UFW)
6. ✅ راه‌اندازی پنل وب
7. ✅ ساخت سرویس systemd
8. ✅ دریافت اطلاعات اولیه (دامنه، ایمیل) و کانفیگ

---

## 🌐 استفاده از پنل

بعد از نصب، پنل روی آدرس زیر در دسترس است:

```
http://YOUR_SERVER_IP:8443
```

یا اگر دامنه تنظیم کرده‌اید:

```
https://YOUR_DOMAIN
```

### امکانات پنل:

- 📊 **داشبورد**: وضعیت سرور، CPU، RAM، شبکه
- 🌐 **مدیریت دامنه**: افزودن/حذف دامنه، ضد‌فیلتر دامنه
- 🔒 **SSL**: دریافت و تمدید گواهی SSL
- 🛡️ **ضد‌فیلتر**: فعال/غیرفعال‌سازی Cloudflare Warp و DoH
- 🔥 **فایروال**: مدیریت پورت‌ها و قوانین
- ⚙️ **تنظیمات**: کانفیگ Nginx، Nginx reload/restart
- 📜 **لاگ‌ها**: مشاهده لاگ‌های Nginx و سیستم

---

## 🛡️ سیستم ضد‌فیلتر

Haji Panel از چند لایه برای ضد‌فیلتر استفاده می‌کند:

### ۱. Cloudflare Warp
- ترافیک سرور از طریق Cloudflare Warp عبور می‌کند
- IP سرور مخفی می‌ماند
- دور زدن فیلتر IP

### ۲. DNS over HTTPS (DoH)
- استفاده از Cloudflare DNS (1.1.1.1) و Google DNS (8.8.8.8)
- دور زدن فیلتر DNS
- جلوگیری از هدایت DNS

### ۳. Cloudflare CDN
- دامنه‌ها از طریق Cloudflare CDN عبور می‌کنند
- ضد‌فیلتر دامنه
- کش محتوا و افزایش سرعت

### ۴. Nginx Reverse Proxy
- پروکسی معکوس برای دامنه‌ها
- پشتیبانی از WebSocket
- SSL Termination

---

## 📁 ساختار پروژه

```
haji-panel/
├── scripts/
│   ├── install.sh          # اسکریپت نصب خودکار
│   ├── uninstall.sh        # اسکریپت حذف
│   └── anti-filter.sh      # اسکریپت ضد‌فیلتر
├── panel/
│   ├── app.py              # بک‌اند پنل (Flask)
│   ├── templates/
│   │   ├── base.html       # قالب پایه
│   │   ├── dashboard.html  # داشبورد
│   │   ├── domains.html    # مدیریت دامنه
│   │   ├── ssl.html        # مدیریت SSL
│   │   ├── firewall.html   # فایروال
│   │   ├── anti-filter.html # ضد‌فیلتر
│   │   └── settings.html   # تنظیمات
│   └── static/
│       ├── css/
│       │   └── style.css   # استایل پنل
│       └── js/
│           └── app.js      # منطق فرانت‌اند
├── nginx/
│   └── default.conf        # کانفیگ پیش‌فرض Nginx
├── core/
│   ├── anti_filter.py      # منطق ضد‌فیلتر
│   ├── domain_manager.py   # مدیریت دامنه
│   ├── ssl_manager.py      # مدیریت SSL
│   └── server_monitor.py   # مانیتورینگ سرور
├── docs/
│   ├── INSTALL.md          # راهنمای نصب کامل
│   └── CONFIG.md           # راهنمای کانفیگ
└── README.md
```

---

## 🔐 امنیت

- پنل با رمز عبور محافظت می‌شود
- فایروال خودکار فعال می‌شود
- SSL اجباری است
- فقط پورت‌های ضروری باز می‌شوند

---

## 🆘 پشتیبانی

- [گزارش باگ](https://github.com/Sajjadsoli/haji-panel/issues)
- [درخواست فیچر](https://github.com/Sajjadsoli/haji-panel/issues)

---

## 📜 لایسنس

MIT License - استفاده آزاد

---

## 🙏 تشکر از

- [Cloudflare](https://cloudflare.com) برای Warp و DNS
- [Nginx](https://nginx.org) برای وب‌سرور
- [Certbot](https://certbot.eff.org/) برای SSL رایگان
- [Let's Encrypt](https://letsencrypt.org/) برای گواهی‌های رایگان

---

<div align="center">

**ساخته شده با ❤️ برای اینترنت آزاد**

![Haji Panel](assets/banner.jpeg)

[نصب سریع](#-نصب-سریع-یک-خط) • [راهنمای کامل](docs/INSTALL.md) • [کانفیگ](docs/CONFIG.md)

</div>
