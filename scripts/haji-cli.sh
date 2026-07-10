#!/bin/bash
# ============================================================
#  Haji Panel - CLI Management Script
#  اسکریپت مدیریت خط فرمان (مشابه x-ui)
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

INSTALL_DIR="/opt/haji-panel"

show_usage() {
    echo -e "${CYAN}"
    echo "  ┌──────────────────────────────────────────────────────────────────┐"
    echo "  │  Haji Panel - Control Menu Usages                                │"
    echo "  │                                                                  │"
    echo "  │  haji              - Admin Management Menu                       │"
    echo "  │  haji start        - Start Panel                                 │"
    echo "  │  haji stop         - Stop Panel                                  │"
    echo "  │  haji restart      - Restart Panel                               │"
    echo "  │  haji restart-xray - Restart Xray Core                           │"
    echo "  │  haji status       - Current Status                              │"
    echo "  │  haji settings     - Current Settings                            │"
    echo "  │  haji enable       - Enable Autostart on OS Startup              │"
    echo "  │  haji disable      - Disable Autostart on OS Startup             │"
    echo "  │  haji log          - Check Logs                                  │"
    echo "  │  haji banlog       - Check Fail2ban Ban Logs                     │"
    echo "  │  haji update       - Update Haji Panel                           │"
    echo "  │  haji update-geo   - Update Geo Files                            │"
    echo "  │  haji install      - Install Haji Panel                          │"
    echo "  │  haji uninstall    - Uninstall Haji Panel                        │"
    echo "  │  haji bot          - Telegram Bot Management                     │"
    echo "  │  haji scanner      - IP Scanner Management                       │"
    echo "  │  haji ssl          - SSL Certificate Management                  │"
    echo "  │  haji firewall     - Firewall Management                         │"
    echo "  │  haji bbr          - Enable BBR                                  │"
    echo "  │  haji speedtest    - Speedtest by Ookla                          │"
    echo "  │  haji password     - Change Panel Password                       │"
    echo "  │  haji domain       - Domain Management                           │"
    echo "  │  haji sub-domain   - Sub-link Domain Management                  │"
    echo "  │  haji security     - Security Settings                           │"
    echo "  └──────────────────────────────────────────────────────────────────┘"
    echo -e "${NC}"
}

show_menu() {
    echo -e "${CYAN}"
    echo "  ╔══════════════════════════════════════════════════════════════╗"
    echo "  ║  🛡️  Haji Panel Management Script                            ║"
    echo "  ║  0.  Exit Script                                             ║"
    echo "  ║──────────────────────────────────────────────────────────────║"
    echo "  ║  1.  Install                                                 ║"
    echo "  ║  2.  Update                                                  ║"
    echo "  ║  3.  Uninstall                                               ║"
    echo "  ║──────────────────────────────────────────────────────────────║"
    echo "  ║  4.  Reset Password                                          ║"
    echo "  ║  5.  Change Port                                             ║"
    echo "  ║  6.  View Current Settings                                   ║"
    echo "  ║──────────────────────────────────────────────────────────────║"
    echo "  ║  7.  Start                                                   ║"
    echo "  ║  8.  Stop                                                    ║"
    echo "  ║  9.  Restart                                                 ║"
    echo "  ║  10. Restart Xray                                            ║"
    echo "  ║  11. Check Status                                            ║"
    echo "  ║  12. View Logs                                               ║"
    echo "  ║──────────────────────────────────────────────────────────────║"
    echo "  ║  13. Enable Autostart                                        ║"
    echo "  ║  14. Disable Autostart                                       ║"
    echo "  ║──────────────────────────────────────────────────────────────║"
    echo "  ║  15. SSL Certificate Management                              ║"
    echo "  ║  16. Firewall Management                                     ║"
    echo "  ║  17. IP Scanner Management                                   ║"
    echo "  ║  18. Telegram Bot Management                                 ║"
    echo "  ║  19. BBR Management                                          ║"
    echo "  ║  20. Update Geo Files                                        ║"
    echo "  ║  21. Speedtest                                               ║"
    echo "  ╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    read -p "  Select option [0-21]: " choice
    
    case $choice in
        0) exit 0 ;;
        1) bash <(curl -sL https://raw.githubusercontent.com/Sajjadsoli/haji-panel/main/scripts/install.sh) ;;
        2) haji update ;;
        3) haji uninstall ;;
        4) reset_password ;;
        5) change_port ;;
        6) show_settings ;;
        7) systemctl start haji-panel; echo "Started ✅" ;;
        8) systemctl stop haji-panel; echo "Stopped ✅" ;;
        9) systemctl restart haji-panel; echo "Restarted ✅" ;;
        10) systemctl restart xray; echo "Xray restarted ✅" ;;
        11) systemctl status haji-panel --no-pager; systemctl status xray --no-pager ;;
        12) journalctl -u haji-panel -e --no-pager -f ;;
        13) systemctl enable haji-panel; echo "Autostart enabled ✅" ;;
        14) systemctl disable haji-panel; echo "Autostart disabled ✅" ;;
        15) ssl_menu ;;
        16) firewall_menu ;;
        17) scanner_menu ;;
        18) bot_menu ;;
        19) bbr_menu ;;
        20) update_geo ;;
        21) speedtest ;;
        *) echo "Invalid option" ;;
    esac
}

reset_password() {
    NEW_PASS=$(openssl rand -hex 12)
    sed -i "s/PANEL_PASSWORD=.*/PANEL_PASSWORD=$NEW_PASS/" $INSTALL_DIR/config/.env
    systemctl restart haji-panel
    echo -e "${GREEN}New password: $NEW_PASS${NC}"
}

change_port() {
    read -p "Enter new port: " port
    sed -i "s/PANEL_PORT=.*/PANEL_PORT=$port/" $INSTALL_DIR/config/.env
    ufw allow $port/tcp
    systemctl restart haji-panel
    echo -e "${GREEN}Port changed to $port ✅${NC}"
}

show_settings() {
    echo -e "${CYAN}Current Settings:${NC}"
    cat $INSTALL_DIR/config/.env 2>/dev/null
    echo ""
    cat $INSTALL_DIR/config/config.json 2>/dev/null | python3 -m json.tool 2>/dev/null
}

ssl_menu() {
    echo "1. Get SSL (Domain)"
    echo "2. Force Renew"
    echo "3. Show Existing Domains"
    read -p "Select: " choice
    case $choice in
        1) read -p "Domain: " domain; read -p "Email: " email; certbot --nginx -d $domain -d www.$domain -m $email --agree-tos --no-eff-email --redirect ;;
        2) certbot renew --force ;;
        3) certbot certificates ;;
    esac
}

firewall_menu() {
    echo "1. Enable Firewall"
    echo "2. Disable Firewall"
    echo "3. Status"
    echo "4. Open Port"
    echo "5. Close Port"
    read -p "Select: " choice
    case $choice in
        1) ufw --force enable ;;
        2) ufw disable ;;
        3) ufw status numbered ;;
        4) read -p "Port: " port; ufw allow $port/tcp ;;
        5) read -p "Port: " port; ufw deny $port/tcp ;;
    esac
}

scanner_menu() {
    echo "1. Run Scan Now"
    echo "2. Scanner Status"
    echo "3. Enable Auto-Switch"
    echo "4. Disable Auto-Switch"
    read -p "Select: " choice
    case $choice in
        1) cd $INSTALL_DIR && python3 -c "from core.ip_scanner import IPScanner; s=IPScanner(); print(s.scan())" ;;
        2) cd $INSTALL_DIR && python3 -c "from core.ip_scanner import IPScanner; s=IPScanner(); print(s.get_status())" ;;
        3) cd $INSTALL_DIR && python3 -c "from core.ip_scanner import IPScanner; s=IPScanner(); s.update_settings({'auto_switch':True}); print('Enabled')" ;;
        4) cd $INSTALL_DIR && python3 -c "from core.ip_scanner import IPScanner; s=IPScanner(); s.update_settings({'auto_switch':False}); print('Disabled')" ;;
    esac
}

bot_menu() {
    echo "1. Setup Bot (Token + Owner ID)"
    echo "2. Bot Status"
    echo "3. Set Webhook"
    echo "4. Delete Webhook"
    echo "5. Add Admin"
    echo "6. Remove Admin"
    echo "7. Broadcast Message"
    read -p "Select: " choice
    case $choice in
        1) read -p "Bot Token: " token; read -p "Owner ID: " owner; read -p "Domain: " domain; cd $INSTALL_DIR && python3 -c "from core.telegram_bot import HajiTelegramBot; b=HajiTelegramBot(); print(b.setup('$token','$owner','$domain'))" ;;
        2) cd $INSTALL_DIR && python3 -c "from core.telegram_bot import HajiTelegramBot; b=HajiTelegramBot(); import json; print(json.dumps(b.get_status(),indent=2))" ;;
        3) read -p "Domain: " domain; cd $INSTALL_DIR && python3 -c "from core.telegram_bot import HajiTelegramBot; b=HajiTelegramBot(); print(b.set_webhook('$domain'))" ;;
        4) cd $INSTALL_DIR && python3 -c "from core.telegram_bot import HajiTelegramBot; b=HajiTelegramBot(); print(b.delete_webhook())" ;;
        5) read -p "Admin ID: " aid; read -p "Name: " name; cd $INSTALL_DIR && python3 -c "from core.telegram_bot import HajiTelegramBot; b=HajiTelegramBot(); print(b.add_admin('$aid','$name'))" ;;
        6) read -p "Admin ID: " aid; cd $INSTALL_DIR && python3 -c "from core.telegram_bot import HajiTelegramBot; b=HajiTelegramBot(); print(b.remove_admin('$aid'))" ;;
        7) read -p "Message: " msg; cd $INSTALL_DIR && python3 -c "from core.telegram_bot import HajiTelegramBot; b=HajiTelegramBot(); print(f'Sent to {b.broadcast(\"$msg\")} users')" ;;
    esac
}

bbr_menu() {
    echo "1. Enable BBR"
    echo "2. Disable BBR"
    read -p "Select: " choice
    case $choice in
        1) echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf; echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf; sysctl -p; echo "BBR enabled ✅" ;;
        2) sed -i '/bbr/d' /etc/sysctl.conf; sed -i '/fq/d' /etc/sysctl.conf; sysctl -p; echo "BBR disabled ✅" ;;
    esac
}

update_geo() {
    echo "Updating geo files..."
    curl -sL "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat" -o /usr/local/xray/assets/geoip.dat
    curl -sL "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat" -o /usr/local/xray/assets/geosite.dat
    systemctl restart xray
    echo "Geo files updated ✅"
}

speedtest() {
    if ! command -v speedtest &>/dev/null; then
        curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | bash
        apt-get install -y speedtest
    fi
    speedtest
}

# ─── Password Management ───────────────────────────────────

change_password() {
    echo -e "${CYAN}Change Panel Password${NC}"
    read -s -p "  New password: " pass1; echo ""
    read -s -p "  Confirm password: " pass2; echo ""
    
    if [[ "$pass1" != "$pass2" ]]; then
        echo -e "${RED}Passwords do not match!${NC}"
        return
    fi
    
    if [[ ${#pass1} -lt 8 ]]; then
        echo -e "${RED}Password must be at least 8 characters!${NC}"
        return
    fi
    
    sed -i "s/PANEL_PASSWORD=.*/PANEL_PASSWORD=$pass1/" $INSTALL_DIR/config/.env
    systemctl restart haji-panel
    echo -e "${GREEN}Password changed successfully ✅${NC}"
}

# ─── Domain Management ─────────────────────────────────────

domain_menu() {
    echo "  1. Add Panel Domain"
    echo "  2. Add Config Domain"
    echo "  3. Add Sub-link Domain"
    echo "  4. Remove Domain"
    echo "  5. List Domains"
    read -p "  Select: " choice
    case $choice in
        1) read -p "Domain (e.g. admin.example.com): " dom; add_domain_nginx "$dom" "panel" 5000 ;;
        2) read -p "Domain (e.g. cfg.example.com): " dom; add_domain_nginx "$dom" "config" 5000 ;;
        3) read -p "Domain (e.g. sub.example.com): " dom; add_domain_nginx "$dom" "sub_link" 5000 ;;
        4) read -p "Domain to remove: " dom; remove_domain_nginx "$dom" ;;
        5) list_domains ;;
    esac
}

add_domain_nginx() {
    local domain=$1
    local dtype=$2
    local port=${3:-5000}
    
    if [[ -z "$domain" ]]; then
        echo -e "${RED}Domain is required${NC}"
        return
    fi
    
    # Create Nginx config
    cat > "/etc/nginx/sites-available/$domain" << NGINXEOF
server {
    listen 80;
    server_name $domain;
    server_tokens off;
    
    location / {
        proxy_pass http://127.0.0.1:$port;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /panel/ {
        proxy_pass http://127.0.0.1:$port;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location /sub/ {
        proxy_pass http://127.0.0.1:$port;
        proxy_set_header Host \$host;
    }
    
    location /bot/webhook {
        proxy_pass http://127.0.0.1:$port;
        proxy_set_header Host \$host;
    }
    
    proxy_hide_header X-Powered-By;
    proxy_hide_header Server;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    client_max_body_size 50M;
}
NGINXEOF
    
    ln -sf "/etc/nginx/sites-available/$domain" "/etc/nginx/sites-enabled/$domain"
    nginx -t && systemctl reload nginx
    
    # Save to config
    cd $INSTALL_DIR && python3 -c "
import json
cfg = json.load(open('config/domain.json')) if __import__('os').path.exists('config/domain.json') else {}
if 'domains' not in cfg: cfg['domains'] = []
cfg['domains'] = [d for d in cfg['domains'] if d.get('name') != '$domain']
cfg['domains'].append({'name': '$domain', 'type': '$dtype', 'port': $port})
cfg['${dtype}_domain'] = '$domain'
json.dump(cfg, open('config/domain.json','w'), indent=2, ensure_ascii=False)
"
    
    echo -e "${GREEN}Domain $domain added + Nginx configured ✅${NC}"
}

remove_domain_nginx() {
    local domain=$1
    rm -f "/etc/nginx/sites-enabled/$domain"
    rm -f "/etc/nginx/sites-available/$domain"
    nginx -t && systemctl reload nginx
    
    cd $INSTALL_DIR && python3 -c "
import json, os
p = 'config/domain.json'
if os.path.exists(p):
    cfg = json.load(open(p))
    cfg['domains'] = [d for d in cfg.get('domains',[]) if d.get('name') != '$domain']
    for k in ['sub_link_domain','config_domain','panel_domain']:
        if cfg.get(k) == '$domain': cfg.pop(k, None)
    json.dump(cfg, open(p,'w'), indent=2, ensure_ascii=False)
"
    echo -e "${GREEN}Domain $domain removed ✅${NC}"
}

list_domains() {
    cd $INSTALL_DIR && python3 -c "
import json, os
p = 'config/domain.json'
if os.path.exists(p):
    cfg = json.load(open(p))
    print('Configured domains:')
    for d in cfg.get('domains', []):
        print(f'  {d[\"name\"]} ({d[\"type\"]}) -> port {d[\"port\"]}')
    print(f'Sub-link domain: {cfg.get(\"sub_link_domain\", \"not set\")}')
    print(f'Config domain: {cfg.get(\"config_domain\", \"not set\")}')
    print(f'Panel domain: {cfg.get(\"panel_domain\", \"not set\")}')
else:
    print('No domains configured')
"
}

# ─── Sub-link Domain ───────────────────────────────────────

sub_domain_menu() {
    echo "  1. Set Sub-link Domain"
    echo "  2. Remove Sub-link Domain"
    echo "  3. Show Current"
    read -p "  Select: " choice
    case $choice in
        1) read -p "Sub-link domain (e.g. sub.example.com): " dom; add_domain_nginx "$dom" "sub_link" 5000 ;;
        2) read -p "Domain to remove: " dom; remove_domain_nginx "$dom" ;;
        3) list_domains ;;
    esac
}

# ─── Security Settings ─────────────────────────────────────

security_menu() {
    echo "  1. Show Security Status"
    echo "  2. Set Max Login Attempts"
    echo "  3. Set Lockout Duration (minutes)"
    echo "  4. Set Session Timeout (minutes)"
    echo "  5. Enable IP Whitelist"
    echo "  6. Disable IP Whitelist"
    echo "  7. Add IP to Whitelist"
    echo "  8. Remove IP from Whitelist"
    echo "  9. View Login Logs"
    echo "  10. Enable 2FA"
    echo "  11. Disable 2FA"
    read -p "  Select: " choice
    case $choice in
        1) cd $INSTALL_DIR && python3 -c "from core.security import SecurityManager; import json; print(json.dumps(SecurityManager().get_status(), indent=2))" ;;
        2) read -p "Max attempts: " val; cd $INSTALL_DIR && python3 -c "from core.security import SecurityManager; SecurityManager().update_settings({'max_login_attempts': $val}); print('Done')" ;;
        3) read -p "Minutes: " val; cd $INSTALL_DIR && python3 -c "from core.security import SecurityManager; SecurityManager().update_settings({'lockout_duration_minutes': $val}); print('Done')" ;;
        4) read -p "Minutes: " val; cd $INSTALL_DIR && python3 -c "from core.security import SecurityManager; SecurityManager().update_settings({'session_timeout_minutes': $val}); print('Done')" ;;
        5) cd $INSTALL_DIR && python3 -c "from core.security import SecurityManager; SecurityManager().update_settings({'ip_whitelist_enabled': True}); print('Enabled')" ;;
        6) cd $INSTALL_DIR && python3 -c "from core.security import SecurityManager; SecurityManager().update_settings({'ip_whitelist_enabled': False}); print('Disabled')" ;;
        7) read -p "IP: " ip; cd $INSTALL_DIR && python3 -c "from core.security import SecurityManager; SecurityManager().add_to_whitelist('$ip'); print('Added')" ;;
        8) read -p "IP: " ip; cd $INSTALL_DIR && python3 -c "from core.security import SecurityManager; SecurityManager().remove_from_whitelist('$ip'); print('Removed')" ;;
        9) cd $INSTALL_DIR && python3 -c "from core.security import SecurityManager; [print(f'{a[\"ip\"]} - {a[\"status\"]} - {a[\"timestamp\"]}') for a in SecurityManager().get_login_log(20)]" ;;
        10) cd $INSTALL_DIR && python3 -c "from core.security import SecurityManager; s=SecurityManager().generate_2fa_secret(); print(f'2FA enabled. Secret: {s}')" ;;
        11) cd $INSTALL_DIR && python3 -c "from core.security import SecurityManager; SecurityManager().disable_2fa(); print('Disabled')" ;;
    esac
}

# ─── Main ──────────────────────────────────────────────────

case "$1" in
    start)        systemctl start haji-panel; echo "Started ✅" ;;
    stop)         systemctl stop haji-panel; echo "Stopped ✅" ;;
    restart)      systemctl restart haji-panel; echo "Restarted ✅" ;;
    restart-xray) systemctl restart xray; echo "Xray restarted ✅" ;;
    status)       systemctl status haji-panel --no-pager; systemctl status xray --no-pager ;;
    settings)     show_settings ;;
    enable)       systemctl enable haji-panel; echo "Autostart enabled ✅" ;;
    disable)      systemctl disable haji-panel; echo "Autostart disabled ✅" ;;
    log)          journalctl -u haji-panel -e --no-pager -f ;;
    banlog)       cat /var/log/fail2ban.log 2>/dev/null | tail -20 ;;
    update)       cd $INSTALL_DIR && git pull origin main 2>/dev/null || echo "Manual update required"; systemctl restart haji-panel ;;
    update-geo)   update_geo ;;
    install)      bash <(curl -sL https://raw.githubusercontent.com/Sajjadsoli/haji-panel/main/scripts/install.sh) ;;
    uninstall)    bash $INSTALL_DIR/scripts/uninstall.sh ;;
    bot)          bot_menu ;;
    scanner)      scanner_menu ;;
    ssl)          ssl_menu ;;
    firewall)     firewall_menu ;;
    bbr)          bbr_menu ;;
    speedtest)    speedtest ;;
    password)     change_password ;;
    domain)       domain_menu ;;
    sub-domain)   sub_domain_menu ;;
    security)     security_menu ;;
    ""|"menu")    show_menu ;;
    *)            show_usage ;;
esac
