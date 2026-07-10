# ⚙️ راهنمای کانفیگ Haji Panel

## فایل کانفیگ اصلی

مسیر: `/opt/haji-panel/config/config.json`

```json
{
    "panel_port": 5000,
    "nginx_port": 80,
    "ssl_port": 443,
    "panel_url_port": 8443,
    "warp_enabled": true,
    "doh_enabled": true,
    "firewall_enabled": true,
    "auto_ssl": true,
    "cloudflare_dns": ["1.1.1.1", "1.0.0.1"],
    "google_dns": ["8.8.8.8", "8.8.4.4"],
    "doh_servers": [
        "https://cloudflare-dns.com/dns-query",
        "https://dns.google/dns-query"
    ]
}
```

## فایل دامنه

مسیر: `/opt/haji-panel/config/domain.json`

```json
{
    "domain": "example.com",
    "email": "you@example.com",
    "ssl_enabled": true,
    "cloudflare_proxy": false
}
```

## فایل محیط

مسیر: `/opt/haji-panel/config/.env`

```env
PANEL_PASSWORD=your_password
SECRET_KEY=your_secret_key
PANEL_PORT=5000
```

## کانفیگ Nginx

مسیر: `/etc/nginx/sites-available/haji-panel`

برای ویرایش:
```bash
nano /etc/nginx/sites-available/haji-panel
nginx -t
systemctl reload nginx
```

## ضد‌فیلتر دامنه با Cloudflare

### مراحل:
1. حساب Cloudflare بسازید
2. دامنه خود را اضافه کنید
3. Nameserver‌های Cloudflare را در پنل دامنه تنظیم کنید
4. رکورد A دامنه را به IP سرور تنظیم کنید
5. پروکسی (Orange Cloud ☁️) را فعال کنید
6. SSL Mode را روی "Full" تنظیم کنید

### نتیجه:
- ترافیک دامنه از طریق Cloudflare CDN عبور می‌کند
- IP سرور مخفی می‌ماند
- فیلتر دامنه دور زده می‌شود
- SSL رایگان فعال می‌شود

## تغییر رمز عبور پنل

```bash
# تولید رمز جدید
NEW_PASS=$(openssl rand -hex 12)

# آپدیت فایل
sed -i "s/PANEL_PASSWORD=.*/PANEL_PASSWORD=$NEW_PASS/" /opt/haji-panel/config/.env

# راه‌اندازی مجدد
systemctl restart haji-panel

echo "رمز جدید: $NEW_PASS"
```

## پورت‌های مورد نیاز

| پورت |用途 | 
|------|------|
| 22 | SSH |
| 80 | HTTP (Nginx) |
| 443 | HTTPS (SSL) |
| 8443 | پنل (در صورت استفاده از Nginx proxy) |
| 5000 | پنل (مستقیم) |

## تمدید SSL

Certbot به‌طور خودکار تمدید را انجام می‌دهد. برای تست:

```bash
certbot renew --dry-run
```

## بک‌آپ

```bash
# بک‌آپ کانفیگ
tar -czf haji-backup.tar.gz /opt/haji-panel/config/

# بازیابی
tar -xzf haji-backup.tar.gz -C /
systemctl restart haji-panel
```
