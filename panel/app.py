#!/usr/bin/env python3
"""
Haji Panel - Panel Backend (Flask)
پنل مدیریت سرور ضد‌فیلتر
"""

import os
import json
import subprocess
import psutil
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "haji-panel-secret-change-me")

CONFIG_DIR = "/opt/haji-panel/config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DOMAIN_FILE = os.path.join(CONFIG_DIR, "domain.json")
BRANDING_FILE = os.path.join(CONFIG_DIR, "branding.json")
PANEL_PASSWORD = os.environ.get("PANEL_PASSWORD", "admin")

# ─── Branding ───────────────────────────────────────────────

DEFAULT_BRANDING = {
    "panel_title": "Haji Panel",
    "panel_subtitle": "پنل مدیریت سرور ضد‌فیلتر",
    "sub_link_title": "Haji Panel",
    "sub_link_subtitle": "پنل مدیریت اتصال",
    "logo_text": "🛡️ Haji Panel",
    "primary_color": "#00d4ff",
    "secondary_color": "#7b2ff7",
    "footer_text": "ساخته شده با ❤️ برای اینترنت آزاد",
    "config_prefix": "Haji",
}

def load_branding():
    try:
        with open(BRANDING_FILE) as f:
            cfg = json.load(f)
            # Merge with defaults
            result = DEFAULT_BRANDING.copy()
            result.update(cfg)
            return result
    except Exception:
        return DEFAULT_BRANDING.copy()

def save_branding(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(BRANDING_FILE, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# ─── Auth ───────────────────────────────────────────────────

def check_auth():
    return session.get("authenticated", False)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == PANEL_PASSWORD:
            session["authenticated"] = True
            return redirect("/")
        return render_template("login.html", error="رمز عبور اشتباه است")
    return render_template("login.html", error=None)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ─── Auth middleware ────────────────────────────────────────

@app.before_request
def require_auth():
    if request.endpoint in ("login", "static"):
        return None
    if not check_auth():
        return redirect("/login")
    return None

# ─── Helpers ────────────────────────────────────────────────

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def load_domain_config():
    try:
        with open(DOMAIN_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_domain_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(DOMAIN_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return False, str(e)

def get_warp_status():
    ok, output = run_cmd("warp-cli status 2>/dev/null")
    if ok and "Connected" in output:
        return "connected", output
    elif ok and "Disconnected" in output:
        return "disconnected", output
    return "not_installed", "Warp نصب نیست"

def get_doh_status():
    if os.path.exists("/etc/systemd/resolved.conf.d/doh.conf"):
        return True
    try:
        with open("/etc/resolv.conf") as f:
            return "1.1.1.1" in f.read()
    except Exception:
        return False

# ─── Routes ─────────────────────────────────────────────────

@app.route("/")
def dashboard():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    
    warp_status, warp_detail = get_warp_status()
    doh_status = get_doh_status()
    domain_cfg = load_domain_config()
    
    return render_template("dashboard.html",
        cpu=cpu,
        ram_total=ram.total,
        ram_used=ram.used,
        ram_percent=ram.percent,
        disk_total=disk.total,
        disk_used=disk.used,
        disk_percent=disk.percent,
        net_sent=net.bytes_sent,
        net_recv=net.bytes_recv,
        warp_status=warp_status,
        warp_detail=warp_detail,
        doh_status=doh_status,
        domain=domain_cfg.get("domain", ""),
        ssl_enabled=domain_cfg.get("ssl_enabled", False),
        uptime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

@app.route("/domains")
def domains_page():
    domain_cfg = load_domain_config()
    subdomains = domain_cfg.get("subdomains", [])
    return render_template("domains.html", domain_cfg=domain_cfg, subdomains=subdomains)

@app.route("/ssl")
def ssl_page():
    domain_cfg = load_domain_config()
    return render_template("ssl.html", domain_cfg=domain_cfg)

@app.route("/anti-filter")
def anti_filter_page():
    warp_status, warp_detail = get_warp_status()
    doh_status = get_doh_status()
    return render_template("anti-filter.html",
        warp_status=warp_status,
        warp_detail=warp_detail,
        doh_status=doh_status)

@app.route("/firewall")
def firewall_page():
    ok, output = run_cmd("ufw status numbered 2>/dev/null")
    rules = output if ok else "فایروال نصب نیست"
    return render_template("firewall.html", rules=rules)

@app.route("/settings")
def settings_page():
    config = load_config()
    branding = load_branding()
    return render_template("settings.html", config=config, branding=branding)

# ─── API ────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    warp_status, _ = get_warp_status()
    return jsonify({
        "cpu": cpu,
        "ram_percent": ram.percent,
        "ram_used": ram.used,
        "ram_total": ram.total,
        "warp": warp_status,
        "doh": get_doh_status(),
        "timestamp": datetime.now().isoformat(),
    })

@app.route("/api/warp/<action>")
def api_warp(action):
    if action == "enable":
        ok, msg = run_cmd("warp-cli connect 2>/dev/null")
    elif action == "disable":
        ok, msg = run_cmd("warp-cli disconnect 2>/dev/null")
    else:
        return jsonify({"ok": False, "error": "action نامعتبر"})
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/doh/<action>")
def api_doh(action):
    if action == "enable":
        ok, msg = run_cmd("bash /opt/haji-panel/scripts/anti-filter.sh --enable-doh")
    elif action == "disable":
        ok, msg = run_cmd("bash /opt/haji-panel/scripts/anti-filter.sh --disable-doh")
    else:
        return jsonify({"ok": False, "error": "action نامعتبر"})
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/domain", methods=["POST"])
def api_domain():
    data = request.json or {}
    domain = data.get("domain", "").strip()
    email = data.get("email", "").strip()
    
    if not domain:
        return jsonify({"ok": False, "error": "دامنه الزامی است"})
    
    cfg = {"domain": domain, "email": email, "ssl_enabled": False, "cloudflare_proxy": False}
    save_domain_config(cfg)
    
    # Add to nginx
    nginx_conf = f"""server {{
    listen 80;
    server_name {domain} www.{domain};
    location / {{
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
    client_max_body_size 50M;
}}"""
    
    with open(f"/etc/nginx/sites-available/{domain}", "w") as f:
        f.write(nginx_conf)
    
    os.symlink(f"/etc/nginx/sites-available/{domain}",
               f"/etc/nginx/sites-enabled/{domain}")
    
    ok, msg = run_cmd("nginx -t && systemctl reload nginx")
    return jsonify({"ok": ok, "message": f"دامنه {domain} اضافه شد"})

# ─── Branding API ───────────────────────────────────────────

@app.route("/api/branding", methods=["GET"])
def api_get_branding():
    return jsonify({"ok": True, "branding": load_branding()})

@app.route("/api/branding", methods=["POST"])
def api_save_branding():
    data = request.json or {}
    branding = load_branding()
    for key in DEFAULT_BRANDING:
        if key in data:
            branding[key] = data[key]
    save_branding(branding)
    return jsonify({"ok": True, "message": "برندینگ ذخیره شد"})

# ─── Xray API ───────────────────────────────────────────────

@app.route("/api/xray/status")
def api_xray_status():
    ok, msg = run_cmd("systemctl is-active xray 2>/dev/null")
    version_ok, version = run_cmd("/usr/local/xray/xray version 2>/dev/null | head -1")
    return jsonify({
        "ok": True,
        "running": ok and "active" in msg,
        "version": version if version_ok else "نامشخص"
    })

@app.route("/api/xray/restart")
def api_xray_restart():
    ok, msg = run_cmd("systemctl restart xray")
    return jsonify({"ok": ok, "message": "Xray راه‌اندازی مجدد شد" if ok else msg})

@app.route("/api/xray/config")
def api_xray_config():
    ok, content = run_cmd("cat /usr/local/xray/config/config.json 2>/dev/null")
    return jsonify({"ok": ok, "config": content})

@app.route("/api/xray/inbounds")
def api_xray_inbounds():
    ok, content = run_cmd("cat /usr/local/xray/config/config.json 2>/dev/null")
    if not ok:
        return jsonify({"ok": False, "inbounds": []})
    try:
        cfg = json.loads(content)
        inbounds = cfg.get("inbounds", [])
        return jsonify({"ok": True, "inbounds": inbounds})
    except Exception:
        return jsonify({"ok": False, "inbounds": []})

# ─── IP Scanner API ─────────────────────────────────────────

@app.route("/api/scanner/status")
def api_scanner_status():
    from core.ip_scanner import IPScanner
    scanner = IPScanner()
    return jsonify({"ok": True, "status": scanner.get_status()})

@app.route("/api/scanner/settings", methods=["POST"])
def api_scanner_settings():
    from core.ip_scanner import IPScanner
    scanner = IPScanner()
    data = request.json or {}
    scanner.update_settings(data)
    return jsonify({"ok": True, "message": "تنظیمات اسکنر ذخیره شد"})

@app.route("/api/scanner/scan", methods=["POST"])
def api_scanner_scan():
    from core.ip_scanner import IPScanner
    scanner = IPScanner()
    data = request.json or {}
    result = scanner.scan(
        base_config=data.get("base_config"),
        cdn_targets=data.get("cdn_targets"),
        max_ips=data.get("max_ips"),
        workers=data.get("workers"),
    )
    return jsonify(result)

@app.route("/api/scanner/check/<path:subdomain>")
def api_scanner_check(subdomain):
    from core.ip_scanner import IPScanner
    scanner = IPScanner()
    result = scanner.check_current_ip(subdomain)
    return jsonify({"ok": True, "check": result})

@app.route("/api/scanner/switch/<path:subdomain>", methods=["POST"])
def api_scanner_switch(subdomain):
    from core.ip_scanner import IPScanner
    scanner = IPScanner()
    ok, msg = scanner.auto_switch_if_filtered(subdomain)
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/scanner/assign/<path:subdomain>", methods=["POST"])
def api_scanner_assign(subdomain):
    from core.ip_scanner import IPScanner
    scanner = IPScanner()
    data = request.json or {}
    ip_info = data.get("ip_info")
    ok, msg = scanner.assign_ip(subdomain, ip_info)
    return jsonify({"ok": ok, "message": msg})

# ─── Telegram Bot API ──────────────────────────────────────

@app.route("/api/bot/status")
def api_bot_status():
    from core.telegram_bot import HajiTelegramBot
    bot = HajiTelegramBot()
    return jsonify({"ok": True, "status": bot.get_status()})

@app.route("/api/bot/setup", methods=["POST"])
def api_bot_setup():
    from core.telegram_bot import HajiTelegramBot
    bot = HajiTelegramBot()
    data = request.json or {}
    ok, msg = bot.setup(data.get("token", ""), data.get("owner_id", ""), data.get("domain", ""))
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/bot/webhook", methods=["POST"])
def api_bot_set_webhook():
    from core.telegram_bot import HajiTelegramBot
    bot = HajiTelegramBot()
    data = request.json or {}
    ok, msg = bot.set_webhook(data.get("domain", ""))
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/bot/admin", methods=["POST"])
def api_bot_admin():
    from core.telegram_bot import HajiTelegramBot
    bot = HajiTelegramBot()
    data = request.json or {}
    action = data.get("action", "")
    if action == "add":
        ok, msg = bot.add_admin(data.get("admin_id"), data.get("name", ""))
    elif action == "remove":
        ok, msg = bot.remove_admin(data.get("admin_id"))
    else:
        return jsonify({"ok": False, "error": "action نامعتبر"})
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/bot/products", methods=["POST"])
def api_bot_products():
    from core.telegram_bot import HajiTelegramBot
    bot = HajiTelegramBot()
    data = request.json or {}
    bot.update_products(data.get("products", []))
    return jsonify({"ok": True, "message": "محصولات ذخیره شد"})

@app.route("/api/bot/settings", methods=["POST"])
def api_bot_settings():
    from core.telegram_bot import HajiTelegramBot
    bot = HajiTelegramBot()
    data = request.json or {}
    cfg = bot._load_config()
    for key in ["card_number", "card_holder", "support_username", "channel_id", "force_join", "trial_enabled", "trial_volume_gb", "trial_duration_hours", "referral_enabled", "referral_percent", "welcome_text"]:
        if key in data:
            cfg[key] = data[key]
    bot._save_config(cfg)
    return jsonify({"ok": True, "message": "تنظیمات ربات ذخیره شد"})

@app.route("/api/bot/broadcast", methods=["POST"])
def api_bot_broadcast():
    from core.telegram_bot import HajiTelegramBot
    bot = HajiTelegramBot()
    data = request.json or {}
    count = bot.broadcast(data.get("text", ""), data.get("target", "all"))
    return jsonify({"ok": True, "message": f"پیام به {count} کاربر ارسال شد"})

@app.route("/bot/webhook", methods=["POST"])
def bot_webhook():
    """وب‌هوک تلگرام"""
    from core.telegram_bot import HajiTelegramBot
    bot = HajiTelegramBot()
    update = request.json or {}
    result = bot.handle_update(update)
    return jsonify(result)

# ─── Subdomain Panel (Graphical) ─────────────────────────

@app.route("/subdomain-panel")
def subdomain_panel_page():
    """پنل گرافیکی ساب‌دامنه"""
    subdomain = request.args.get("name", request.host)
    branding = load_branding()
    return render_template("subdomain_panel.html", subdomain=subdomain, branding=branding)

@app.route("/api/traffic/<path:subdomain>")
def api_traffic_status(subdomain):
    """دریافت وضعیت ترافیک و زمان ساب‌دامنه"""
    from core.traffic_monitor import TrafficMonitor
    tm = TrafficMonitor()
    status = tm.get_status(subdomain)
    if status is None:
        # Auto-init with defaults
        tm.init_subdomain(subdomain)
        status = tm.get_status(subdomain)
    return jsonify({"ok": True, "status": status})

@app.route("/api/traffic/<path:subdomain>/limits", methods=["POST"])
def api_traffic_limits(subdomain):
    """بروزرسانی محدودیت‌های ساب‌دامنه"""
    from core.traffic_monitor import TrafficMonitor
    tm = TrafficMonitor()
    data = request.json or {}
    ok = tm.update_limits(
        subdomain,
        data_limit_gb=data.get("data_limit_gb"),
        time_limit_hours=data.get("time_limit_hours")
    )
    return jsonify({"ok": ok, "message": "محدودیت‌ها بروزرسانی شد" if ok else "خطا"})

@app.route("/api/traffic/<path:subdomain>/reset", methods=["POST"])
def api_traffic_reset(subdomain):
    """ریست مصرف ساب‌دامنه"""
    from core.traffic_monitor import TrafficMonitor
    tm = TrafficMonitor()
    ok = tm.reset_usage(subdomain)
    return jsonify({"ok": ok, "message": "مصرف ریست شد" if ok else "خطا"})

@app.route("/api/traffic/<path:subdomain>/configs")
def api_traffic_configs(subdomain):
    """دریافت کانفیگ‌های قابل کپی ساب‌دامنه"""
    from core.traffic_monitor import TrafficMonitor
    tm = TrafficMonitor()
    branding = load_branding()
    configs = tm.get_configs(subdomain, config_prefix=branding.get("config_prefix", "Haji"))
    
    # Inject clean IP if available
    from core.ip_scanner import IPScanner
    scanner = IPScanner()
    current_ip = scanner.get_status().get("current_ips", {}).get(subdomain)
    if current_ip:
        # Replace host in config links with clean IP
        for c in configs:
            if c["type"] != "sub":
                c["link"] = c["link"].replace(f"@{subdomain}:", f"@{current_ip['ip']}:").replace(f"@{subdomain}/", f"@{current_ip['ip']}/")
                c["desc"] += f" • 💎 IP: {current_ip['ip']}"
    
    return jsonify({"ok": True, "configs": configs})

@app.route("/sub/<path:subdomain>")
def sub_subscription(subdomain):
    """لینک اشتراک (Subscription) برای کلاینت‌ها"""
    import base64
    from core.traffic_monitor import TrafficMonitor
    tm = TrafficMonitor()
    branding = load_branding()
    configs = tm.get_configs(subdomain, config_prefix=branding.get("config_prefix", "Haji"))
    # Only proxy configs (not subscription link itself)
    links = [c["link"] for c in configs if c["type"] != "sub"]
    sub_content = base64.b64encode("\n".join(links).encode()).decode()
    return sub_content, 200, {"Content-Type": "text/plain; charset=utf-8"}

@app.route("/api/subdomain", methods=["POST"])
def api_subdomain():
    data = request.json or {}
    subdomain = data.get("subdomain", "").strip()
    port = data.get("port", 5000)
    
    if not subdomain:
        return jsonify({"ok": False, "error": "ساب‌دامنه الزامی است"})
    
    try:
        port = int(port)
    except (ValueError, TypeError):
        port = 5000
    
    if port < 1 or port > 65535:
        return jsonify({"ok": False, "error": "پورت نامعتبر (۱-۶۵۵۳۵)"})
    
    # Create nginx config for subdomain - serves panel + proxies to app
    nginx_conf = f"""server {{
    listen 80;
    server_name {subdomain};
    
    # Subdomain management panel
    location /panel {{
        proxy_pass http://127.0.0.1:5000/subdomain-panel?name={subdomain};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    # Traffic API
    location /api/traffic {{
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    # Main app proxy
    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
    client_max_body_size 50M;
}}"""
    
    conf_path = f"/etc/nginx/sites-available/{subdomain}"
    with open(conf_path, "w") as f:
        f.write(nginx_conf)
    
    enabled_path = f"/etc/nginx/sites-enabled/{subdomain}"
    if os.path.islink(enabled_path) or os.path.exists(enabled_path):
        os.remove(enabled_path)
    os.symlink(conf_path, enabled_path)
    
    ok, msg = run_cmd("nginx -t && systemctl reload nginx")
    
    if ok:
        cfg = load_domain_config()
        if "subdomains" not in cfg:
            cfg["subdomains"] = []
        cfg["subdomains"] = [s for s in cfg["subdomains"] if s.get("name") != subdomain]
        cfg["subdomains"].append({"name": subdomain, "port": port, "ssl": False})
        save_domain_config(cfg)
        
        # Initialize traffic monitoring
        from core.traffic_monitor import TrafficMonitor
        tm = TrafficMonitor()
        tm.init_subdomain(subdomain, port=port)
    
    return jsonify({"ok": ok, "message": f"ساب‌دامنه {subdomain} اضافه شد"})

@app.route("/api/subdomain/delete", methods=["POST"])
def api_subdomain_delete():
    data = request.json or {}
    subdomain = data.get("subdomain", "").strip()
    
    if not subdomain:
        return jsonify({"ok": False, "error": "ساب‌دامنه الزامی است"})
    
    enabled_path = f"/etc/nginx/sites-enabled/{subdomain}"
    available_path = f"/etc/nginx/sites-available/{subdomain}"
    
    if os.path.islink(enabled_path) or os.path.exists(enabled_path):
        os.remove(enabled_path)
    if os.path.exists(available_path):
        os.remove(available_path)
    
    ok, msg = run_cmd("nginx -t && systemctl reload nginx")
    
    if ok:
        cfg = load_domain_config()
        if "subdomains" in cfg:
            cfg["subdomains"] = [s for s in cfg["subdomains"] if s.get("name") != subdomain]
            save_domain_config(cfg)
        
        # Remove traffic monitoring
        from core.traffic_monitor import TrafficMonitor
        tm = TrafficMonitor()
        tm.remove_subdomain(subdomain)
    
    return jsonify({"ok": ok, "message": f"ساب‌دامنه {subdomain} حذف شد"})

@app.route("/api/ssl", methods=["POST"])
def api_ssl():
    data = request.json or {}
    domain = data.get("domain", "").strip()
    email = data.get("email", "").strip()
    
    if not domain or not email:
        return jsonify({"ok": False, "error": "دامنه و ایمیل الزامی است"})
    
    cmd = f"certbot --nginx -d {domain} -d www.{domain} -m {email} --agree-tos --no-eff-email --non-interactive --redirect"
    ok, msg = run_cmd(cmd)
    
    if ok:
        cfg = load_domain_config()
        cfg["ssl_enabled"] = True
        save_domain_config(cfg)
    
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/firewall", methods=["POST"])
def api_firewall():
    data = request.json or {}
    action = data.get("action", "")
    port = data.get("port", "")
    proto = data.get("proto", "tcp")
    
    if action == "allow" and port:
        ok, msg = run_cmd(f"ufw allow {port}/{proto}")
    elif action == "deny" and port:
        ok, msg = run_cmd(f"ufw deny {port}/{proto}")
    elif action == "reload":
        ok, msg = run_cmd("ufw reload")
    elif action == "status":
        ok, msg = run_cmd("ufw status numbered")
    else:
        return jsonify({"ok": False, "error": "action نامعتبر"})
    
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/nginx/<action>")
def api_nginx(action):
    if action == "reload":
        ok, msg = run_cmd("nginx -t && systemctl reload nginx")
    elif action == "restart":
        ok, msg = run_cmd("systemctl restart nginx")
    elif action == "status":
        ok, msg = run_cmd("systemctl status nginx --no-pager")
    elif action == "test":
        ok, msg = run_cmd("nginx -t")
    else:
        return jsonify({"ok": False, "error": "action نامعتبر"})
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/logs")
def api_logs():
    log_type = request.args.get("type", "nginx")
    lines = request.args.get("lines", "50")
    
    log_files = {
        "nginx_access": "/var/log/nginx/access.log",
        "nginx_error": "/var/log/nginx/error.log",
        "haji": "/var/log/syslog",
    }
    
    log_file = log_files.get(log_type, log_files["nginx_error"])
    ok, output = run_cmd(f"tail -n {lines} {log_file} 2>/dev/null")
    return jsonify({"ok": ok, "logs": output})

# ─── Main ───────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PANEL_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
