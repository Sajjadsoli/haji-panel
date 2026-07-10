#!/bin/bash
# ============================================================
#  Haji Panel - Auto Installer
#  نصب خودکار پنل مدیریت سرور ضد‌فیلتر
# ============================================================
#  Author: Sajad Soleymani
#  GitHub: https://github.com/Sajjadsoli/haji-panel
#  License: MIT
# ============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Banner
print_banner() {
    echo -e "${CYAN}"
    echo "  ╔═══════════════════════════════════════════════════╗"
    echo "  ║                                                   ║"
    echo "  ║          🛡️  Haji Panel v1.0.0  🛡️                ║"
    echo "  ║                                                   ║"
    echo "  ║       پنل مدیریت سرور ضد‌فیلتر خودکار             ║"
    echo "  ║                                                   ║"
    echo "  ╚═══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Log functions
log_info()  { echo -e "${BLUE}[ℹ]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step()  { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}\n"; }

# Check root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "این اسکریپت باید با دسترسی root اجرا شود."
        echo -e "  اجرا با: ${YELLOW}sudo bash scripts/install.sh${NC}"
        exit 1
    fi
}

# Check OS
check_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
        log_ok "سیستم‌عامل: $PRETTY_NAME"
        
        if [[ "$OS" != "ubuntu" && "$OS" != "debian" ]]; then
            log_warn "سیستم‌عامل شما ممکن است به‌طور کامل پشتیبانی نشود."
            log_warn "پشتیبانی رسمی: Ubuntu 20.04+ / Debian 11+"
            read -p "ادامه می‌دهید؟ (y/n): " choice
            [[ "$choice" != "y" && "$choice" != "Y" ]] && exit 0
        fi
    else
        log_error "سیستم‌عامل تشخیص داده نشد."
        exit 1
    fi
}

# Install dependencies
install_deps() {
    log_step "۱. نصب پیش‌نیازها"
    
    log_info "آپدیت سیستم..."
    apt-get update -qq
    
    log_info "نصب بسته‌های ضروری..."
    DEPS=(
        python3 python3-pip python3-venv
        nginx certbot python3-certbot-nginx
        ufw curl wget git
        dnsutils resolvconf
        net-tools htop
    )
    
    apt-get install -y -qq "${DEPS[@]}"
    log_ok "پیش‌نیازها نصب شدند"
}

# Install Xray-core
install_xray() {
    log_step "۲. نصب Xray-core"
    
    XRAY_VER=$(curl -sL "https://api.github.com/repos/XTLS/Xray-core/releases/latest" | grep '"tag_name"' | cut -d'"' -f4)
    if [[ -z "$XRAY_VER" ]]; then
        XRAY_VER="v25.6.18"
    fi
    
    log_info "نسخه Xray: $XRAY_VER"
    
    ARCH=$(arch)
    XRAY_FILE="xray-linux-${ARCH}.zip"
    XRAY_URL="https://github.com/XTLS/Xray-core/releases/download/${XRAY_VER}/${XRAY_FILE}"
    
    cd /tmp
    curl -sL "$XRAY_URL" -o "$XRAY_FILE"
    
    mkdir -p /usr/local/xray
    unzip -o "$XRAY_FILE" -d /usr/local/xray/
    chmod +x /usr/local/xray/xray
    
    # Create config directory
    mkdir -p /usr/local/xray/config
    mkdir -p /usr/local/xray/assets
    
    # Download geo data
    curl -sL "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat" -o /usr/local/xray/assets/geoip.dat
    curl -sL "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat" -o /usr/local/xray/assets/geosite.dat
    
    # Default Xray config
    cat > /usr/local/xray/config/config.json << 'XRAYEOF'
{
  "log": {
    "loglevel": "warning",
    "access": "/var/log/xray/access.log",
    "error": "/var/log/xray/error.log"
  },
  "inbounds": [],
  "outbounds": [
    {
      "protocol": "freedom",
      "tag": "direct"
    },
    {
      "protocol": "blackhole",
      "tag": "block"
    }
  ],
  "routing": {
    "domainStrategy": "IPIfNonMatch",
    "rules": [
      {
        "type": "field",
        "outboundTag": "block",
        "protocol": ["bittorrent"]
      }
    ]
  }
}
XRAYEOF

    # Create log directory
    mkdir -p /var/log/xray
    touch /var/log/xray/access.log /var/log/xray/error.log
    
    # Create systemd service for Xray
    cat > /etc/systemd/system/xray.service << 'XRAYSVCEOF'
[Unit]
Description=Xray Service
Documentation=https://github.com/xtls
After=network.target nss-lookup.target

[Service]
User=root
ExecStart=/usr/local/xray/xray run -config /usr/local/xray/config/config.json
Restart=on-failure
RestartPreventExitStatus=23
LimitNPROC=10000
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
XRAYSVCEOF

    systemctl daemon-reload
    systemctl enable xray
    systemctl start xray
    
    rm -f /tmp/$XRAY_FILE
    log_ok "Xray-core نصب و فعال شد"
}

# Install Cloudflare Warp
install_warp() {
    log_step "۳. نصب Cloudflare Warp (ضد‌فیلتر)"
    
    if command -v warp-cli &>/dev/null; then
        log_ok "Warp قبلاً نصب شده است"
    else
        log_info "افزودن مخزن Cloudflare..."
        curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | \
            gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
        
        echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" \
            > /etc/apt/sources.list.d/cloudflare-client.list
        
        apt-get update -qq
        apt-get install -y -qq cloudflare-warp
        log_ok "Cloudflare Warp نصب شد"
    fi
    
    # Register and connect
    log_info "ثبت‌نام در Warp..."
    warp-cli registration new 2>/dev/null || true
    
    log_info "اتصال به Warp..."
    warp-cli mode proxy 2>/dev/null || true
    warp-cli connect 2>/dev/null || true
    
    log_ok "Cloudflare Warp فعال شد"
}

# Configure DoH (DNS over HTTPS)
configure_doh() {
    log_step "۴. کانفیگ DNS over HTTPS (DoH)"
    
    # Backup original resolv.conf
    [[ -f /etc/resolv.conf ]] && cp /etc/resolv.conf /etc/resolv.conf.backup
    
    # Configure DoH via systemd-resolved
    if command -v systemd-resolve &>/dev/null || command -v resolvectl &>/dev/null; then
        log_info "کانفیگ DoH با systemd-resolved..."
        
        mkdir -p /etc/systemd/resolved.conf.d/
        cat > /etc/systemd/resolved.conf.d/doh.conf << 'DOHEOF'
[Resolve]
DNS=1.1.1.1#one.one.one.one 8.8.8.8#dns.google
FallbackDNS=1.0.0.1#one.one.one.one 8.8.4.4#dns.google
DNSOverHTTPS=https://cloudflare-dns.com/dns-query https://dns.google/dns-query
DNSSEC=yes
DOHEOF
        
        systemctl restart systemd-resolved 2>/dev/null || true
        log_ok "DoH با systemd-resolved کانفیگ شد"
    else
        # Fallback: set DNS directly
        log_info "کانفیگ DNS مستقیم..."
        cat > /etc/resolv.conf << 'DNSEOF'
# Haji Panel - Anti-Filter DNS
nameserver 1.1.1.1
nameserver 8.8.8.8
nameserver 1.0.0.1
nameserver 8.8.4.4
DNSEOF
        log_ok "DNS ضد‌فیلتر تنظیم شد"
    fi
}

# Configure Nginx
configure_nginx() {
    log_step "۵. کانفیگ Nginx"
    
    # Remove default site
    rm -f /etc/nginx/sites-enabled/default
    
    # Create Haji Panel config
    cat > /etc/nginx/sites-available/haji-panel << 'NGINXEOF'
# Haji Panel - Nginx Configuration
server {
    listen 80;
    listen [::]:80;
    server_name _;
    
    # Panel
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Gzip
    gzip on;
    gzip_types text/css application/javascript application/json;
    
    # Client max body size
    client_max_body_size 50M;
}
NGINXEOF
    
    ln -sf /etc/nginx/sites-available/haji-panel /etc/nginx/sites-enabled/haji-panel
    
    nginx -t 2>/dev/null
    systemctl enable nginx
    systemctl restart nginx
    log_ok "Nginx کانفیگ شد"
}

# Configure Firewall
configure_firewall() {
    log_step "۶. کانفیگ فایروال (UFW)"
    
    ufw --force reset
    
    ufw default deny incoming
    ufw default allow outgoing
    
    ufw allow 22/tcp    # SSH
    ufw allow 80/tcp    # HTTP
    ufw allow 443/tcp   # HTTPS
    ufw allow 8443/tcp  # Panel
    
    ufw --force enable
    log_ok "فایروال فعال شد (پورت‌های 22, 80, 443, 8443 باز)"
}

# Install Panel
install_panel() {
    log_step "۷. نصب پنل وب"
    
    INSTALL_DIR="/opt/haji-panel"
    
    # Copy files
    mkdir -p "$INSTALL_DIR"
    cp -r "$(dirname "$0")/.."/* "$INSTALL_DIR/" 2>/dev/null || true
    
    # If running from curl, download files
    if [[ ! -d "$INSTALL_DIR/panel" ]]; then
        log_info "دانلود فایل‌های پروژه از GitHub..."
        git clone --depth 1 https://github.com/Sajjadsoli/haji-panel.git /tmp/haji-panel-clone
        cp -r /tmp/haji-panel-clone/* "$INSTALL_DIR/"
        rm -rf /tmp/haji-panel-clone
    fi
    
    # Install CLI script
    cp scripts/haji-cli.sh /usr/bin/haji
    chmod +x /usr/bin/haji
    
    # Python venv
    cd "$INSTALL_DIR/panel"
    python3 -m venv venv
    source venv/bin/activate
    pip install --quiet flask psutil requests
    deactivate
    
    # Create config
    mkdir -p "$INSTALL_DIR/config"
    cat > "$INSTALL_DIR/config/config.json" << 'CONFEOF'
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
    ],
    "branding": {
        "panel_title": "Haji Panel",
        "panel_subtitle": "پنل مدیریت سرور ضد‌فیلتر",
        "sub_link_title": "Haji Panel",
        "sub_link_subtitle": "پنل مدیریت اتصال",
        "logo_text": "🛡️ Haji Panel",
        "primary_color": "#00d4ff",
        "secondary_color": "#7b2ff7",
        "footer_text": "ساخته شده با ❤️ برای اینترنت آزاد"
    }
}
CONFEOF
    
    # Create .env
    PANEL_PASSWORD=$(openssl rand -hex 12)
    SECRET_KEY=$(openssl rand -hex 24)
    cat > "$INSTALL_DIR/config/.env" << ENVEOF
PANEL_PASSWORD=$PANEL_PASSWORD
SECRET_KEY=$SECRET_KEY
PANEL_PORT=5000
ENVEOF
    
    log_ok "پنل نصب شد"
    log_info "رمز عبور پنل: ${YELLOW}$PANEL_PASSWORD${NC}"
}

# Create systemd service
create_service() {
    log_step "۸. ساخت سرویس systemd"
    
    cat > /etc/systemd/system/haji-panel.service << 'SVCEOF'
[Unit]
Description=Haji Panel - Server Management Panel
After=network.target nginx.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/haji-panel/panel
ExecStart=/opt/haji-panel/panel/venv/bin/python /opt/haji-panel/panel/app.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=/opt/haji-panel/config/.env

[Install]
WantedBy=multi-user.target
SVCEOF
    
    systemctl daemon-reload
    systemctl enable haji-panel
    systemctl start haji-panel
    log_ok "سرویس haji-panel فعال شد"
}

# Setup scanner cron job
setup_scanner_cron() {
    log_step "۹. تنظیم اسکنر خودکار آی‌پی تمیز"
    
    # Create scanner cron script
    cat > /opt/haji-panel/scripts/auto-scan.sh << 'CRONEOF'
#!/bin/bash
# Haji Panel - Auto IP Scanner Cron Job
cd /opt/haji-panel
source venv/bin/activate 2>/dev/null
python3 -c "
from core.ip_scanner import IPScanner
scanner = IPScanner()
settings = scanner.get_settings()
if settings.get('enabled', False):
    print('Starting auto scan...')
    result = scanner.scan()
    print(f'Scan complete: {result}')
    # Auto-switch filtered IPs
    for sub in settings.get('current_ips', {}):
        ok, msg = scanner.auto_switch_if_filtered(sub)
        if not ok:
            print(f'Auto-switch failed for {sub}: {msg}')
"
CRONEOF
    chmod +x /opt/haji-panel/scripts/auto-scan.sh
    
    # Add cron job (every 6 hours by default)
    CRON_CMD="0 */6 * * * /opt/haji-panel/scripts/auto-scan.sh >> /var/log/haji-scanner.log 2>&1"
    (crontab -l 2>/dev/null | grep -v "haji-panel/scripts/auto-scan.sh"; echo "$CRON_CMD") | crontab -
    
    # Add cron for reseller expiry check
    CRON_RESELLER="0 */1 * * * cd /opt/haji-panel && python3 -c 'from core.reseller import ResellerManager; ResellerManager().check_expired()' >> /var/log/haji-reseller.log 2>&1"
    (crontab -l 2>/dev/null | grep -v "haji-reseller"; echo "$CRON_RESELLER") | crontab -
    
    log_ok "اسکنر خودکار هر ۶ ساعت فعال شد"
    log_ok "بررسی انقضای نمایندگی هر ساعت فعال شد"
}

# Get user input for domain setup
setup_domain() {
    log_step "۱۰. تنظیم دامنه و SSL"
    
    echo -e "${BOLD}برای تنظیم دامنه و SSL، اطلاعات زیر را وارد کنید:${NC}"
    echo -e "  (اگر دامنه ندارید، Enter بزنید تا بعداً تنظیم کنید)\n"
    
    read -p "🌐 دامنه شما (مثال: example.com): " DOMAIN
    read -p "📧 ایمیل برای SSL (مثال: you@example.com): " EMAIL
    
    if [[ -n "$DOMAIN" && -n "$EMAIL" ]]; then
        log_info "کانفیگ Nginx برای $DOMAIN..."
        
        # Update nginx config
        cat > /etc/nginx/sites-available/haji-panel << DOMAINEOF
# Haji Panel - $DOMAIN
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    client_max_body_size 50M;
}
DOMAINEOF
        
        nginx -t 2>/dev/null
        systemctl reload nginx
        
        # Save domain config
        cat > /opt/haji-panel/config/domain.json << DOMEOF
{
    "domain": "$DOMAIN",
    "email": "$EMAIL",
    "ssl_enabled": false,
    "cloudflare_proxy": false
}
DOMEOF
        
        # Attempt SSL
        log_info "درخواست گواهی SSL از Let's Encrypt..."
        certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" -m "$EMAIL" \
            --agree-tos --no-eff-email --non-interactive --redirect 2>/dev/null
        
        if [[ $? -eq 0 ]]; then
            log_ok "SSL برای $DOMAIN فعال شد ✅"
            
            # Update domain config
            sed -i 's/"ssl_enabled": false/"ssl_enabled": true/' /opt/haji-panel/config/domain.json
        else
            log_warn "SSL دریافت نشد. بعداً از پنل تلاش کنید."
            log_warn "ممکن است نیاز باشد DNS دامنه را به IP سرور تنظیم کنید."
        fi
        
        log_ok "دامنه $DOMAIN کانفیگ شد"
    else
        log_info "دامنه بعداً از پنل قابل تنظیم است."
        
        echo '{}' > /opt/haji-panel/config/domain.json
    fi
}

# Final summary
show_summary() {
    log_step "نصب کامل شد! 🎉"
    
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
    PANEL_PASS=$(grep PANEL_PASSWORD /opt/haji-panel/config/.env | cut -d'=' -f2)
    
    echo -e "${GREEN}${BOLD}"
    echo "  ╔═══════════════════════════════════════════════════╗"
    echo "  ║                                                   ║"
    echo "  ║          ✅ نصب با موفقیت انجام شد ✅              ║"
    echo "  ║                                                   ║"
    echo "  ╚═══════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${BOLD}📋 اطلاعات دسترسی:${NC}"
    echo -e "  🌐 آدرس پنل:  ${CYAN}http://$SERVER_IP:8443${NC}"
    echo -e "  🔑 رمز عبور:  ${YELLOW}$PANEL_PASS${NC}"
    echo -e "  📁 مسیر نصب:  /opt/haji-panel"
    echo -e "  🔧 سرویس:     systemctl {start|stop|restart} haji-panel"
    echo -e "  💎 اسکنر IP:   هر ۶ ساعت خودکار اسکن می‌کند"
    echo -e "  🤖 ربات تلگرام: از پنل ادمین فعال کنید"
    echo -e "  🖥️ CLI:        haji (منوی مدیریت)"
    echo -e "  👥 نمایندگی:    از پنل ادمین مدیریت کنید"
    echo -e "  🛡️ امنیت:      Brute-force + CSRF + Session timeout + IP whitelist"
    echo ""
    echo -e "${BOLD}🛡️ وضعیت ضد‌فیلتر:${NC}"
    echo -e "  Cloudflare Warp:  $(warp-cli status 2>/dev/null | grep -q Connected && echo -e "${GREEN}فعال${NC}" || echo -e "${YELLOW}در حال بررسی${NC}")"
    echo -e "  DoH DNS:          ${GREEN}فعال${NC}"
    echo -e "  فایروال:          ${GREEN}فعال${NC}"
    echo ""
    echo -e "${BOLD}📚 مستندات:${NC}"
    echo -e "  GitHub: https://github.com/Sajjadsoli/haji-panel"
    echo ""
    echo -e "${YELLOW}⚠️  رمز عبور را در جای امن ذخیره کنید!${NC}"
}

# Main
main() {
    print_banner
    check_root
    check_os
    install_deps
    install_xray
    install_warp
    configure_doh
    configure_nginx
    configure_firewall
    install_panel
    create_service
    setup_scanner_cron
    setup_domain
    show_summary
}

main "$@"
