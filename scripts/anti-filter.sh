#!/bin/bash
# ============================================================
#  Haji Panel - Anti-Filter Module
#  ماژول ضد‌فیلتر سرور
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[ℹ]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# Enable Cloudflare Warp
enable_warp() {
    log_info "فعال‌سازی Cloudflare Warp..."
    
    if ! command -v warp-cli &>/dev/null; then
        log_error "Warp نصب نیست. ابتدا install.sh را اجرا کنید."
        exit 1
    fi
    
    warp-cli registration new 2>/dev/null || true
    warp-cli mode proxy
    warp-cli connect
    
    sleep 2
    
    if warp-cli status | grep -q "Connected"; then
        log_ok "Warp متصل و فعال شد"
    else
        log_warn "Warp در حال اتصال است..."
    fi
}

# Disable Cloudflare Warp
disable_warp() {
    log_info "غیرفعال‌سازی Cloudflare Warp..."
    warp-cli disconnect 2>/dev/null || true
    log_ok "Warp غیرفعال شد"
}

# Enable DoH
enable_doh() {
    log_info "فعال‌سازی DNS over HTTPS..."
    
    if command -v resolvectl &>/dev/null; then
        mkdir -p /etc/systemd/resolved.conf.d/
        cat > /etc/systemd/resolved.conf.d/doh.conf << 'EOF'
[Resolve]
DNS=1.1.1.1#one.one.one.one 8.8.8.8#dns.google
FallbackDNS=1.0.0.1#one.one.one.one 8.8.4.4#dns.google
DNSOverHTTPS=https://cloudflare-dns.com/dns-query https://dns.google/dns-query
DNSSEC=yes
EOF
        systemctl restart systemd-resolved
        log_ok "DoH فعال شد"
    else
        cp /etc/resolv.conf /etc/resolv.conf.haji-backup 2>/dev/null || true
        cat > /etc/resolv.conf << 'EOF'
nameserver 1.1.1.1
nameserver 8.8.8.8
nameserver 1.0.0.1
nameserver 8.8.4.4
EOF
        log_ok "DNS ضد‌فیلتر فعال شد"
    fi
}

# Disable DoH
disable_doh() {
    log_info "غیرفعال‌سازی DoH..."
    rm -f /etc/systemd/resolved.conf.d/doh.conf
    systemctl restart systemd-resolved 2>/dev/null || true
    
    if [[ -f /etc/resolv.conf.haji-backup ]]; then
        cp /etc/resolv.conf.haji-backup /etc/resolv.conf
        log_ok "DNS به حالت قبل برگشت"
    else
        log_ok "DoH غیرفعال شد"
    fi
}

# Anti-filter domain (Cloudflare proxy)
antifilter_domain() {
    DOMAIN=$1
    
    if [[ -z "$DOMAIN" ]]; then
        log_error "دامنه مشخص نشده"
        echo "استفاده: anti-filter.sh --domain <domain>"
        exit 1
    fi
    
    log_info "ضد‌فیلتر دامنه $DOMAIN..."
    
    # Add domain to nginx
    cat > "/etc/nginx/sites-available/$DOMAIN" << EOF
server {
    listen 80;
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
    
    client_max_body_size 50M;
}
EOF
    
    ln -sf "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"
    nginx -t && systemctl reload nginx
    
    log_ok "دامنه $DOMAIN به Nginx اضافه شد"
    log_info "برای ضد‌فیلتر کامل:"
    echo "  ۱. DNS دامنه را به IP سرور تنظیم کنید"
    echo "  ۲. در Cloudflare، پروکسی (Orange Cloud) را فعال کنید"
    echo "  ۳. SSL را از پنل فعال کنید"
}

# Status check
show_status() {
    echo -e "${CYAN}━━━ وضعیت ضد‌فیلتر Haji Panel ━━━${NC}\n"
    
    # Warp status
    if command -v warp-cli &>/dev/null; then
        WARP_STATUS=$(warp-cli status 2>/dev/null | head -1)
        echo -e "  Cloudflare Warp:  ${GREEN}$WARP_STATUS${NC}"
    else
        echo -e "  Cloudflare Warp:  ${RED}نصب نیست${NC}"
    fi
    
    # DoH status
    if [[ -f /etc/systemd/resolved.conf.d/doh.conf ]]; then
        echo -e "  DoH (systemd):    ${GREEN}فعال${NC}"
    elif grep -q "1.1.1.1" /etc/resolv.conf 2>/dev/null; then
        echo -e "  DoH (resolv):     ${GREEN}فعال${NC}"
    else
        echo -e "  DoH:              ${YELLOW}غیرفعال${NC}"
    fi
    
    # DNS test
    echo ""
    log_info "تست DNS..."
    if nslookup google.com 1.1.1.1 &>/dev/null; then
        echo -e "  DNS Resolution:   ${GREEN}OK${NC}"
    else
        echo -e "  DNS Resolution:   ${RED}خطا${NC}"
    fi
    
    # IP check
    EXTERNAL_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "نامشخص")
    WARP_IP=$(curl -s --max-time 5 --proxy socks5h://127.0.0.1:40000 ifconfig.me 2>/dev/null || echo "نامشخص")
    
    echo -e "  IP مستقیم:        $EXTERNAL_IP"
    echo -e "  IP از طریق Warp:  $WARP_IP"
    echo ""
}

# Usage
usage() {
    echo "Haji Panel - Anti-Filter Module"
    echo ""
    echo "استفاده:"
    echo "  anti-filter.sh --enable-warp     فعال‌سازی Cloudflare Warp"
    echo "  anti-filter.sh --disable-warp    غیرفعال‌سازی Warp"
    echo "  anti-filter.sh --enable-doh      فعال‌سازی DoH"
    echo "  anti-filter.sh --disable-doh     غیرفعال‌سازی DoH"
    echo "  anti-filter.sh --domain <name>   ضد‌فیلتر دامنه"
    echo "  anti-filter.sh --status          نمایش وضعیت"
    echo "  anti-filter.sh --all             فعال‌سازی همه"
    echo ""
}

# Main
case "$1" in
    --enable-warp)  enable_warp ;;
    --disable-warp) disable_warp ;;
    --enable-doh)   enable_doh ;;
    --disable-doh)  disable_doh ;;
    --domain)       antifilter_domain "$2" ;;
    --status)       show_status ;;
    --all)          enable_warp; enable_doh; show_status ;;
    *)              usage ;;
esac
