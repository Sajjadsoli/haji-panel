#!/bin/bash
# ============================================================
#  Haji Panel - Uninstaller
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "[ℹ] $1"; }
log_ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[⚠]${NC} $1"; }

if [[ $EUID -ne 0 ]]; then
    echo "اجرا با: sudo bash scripts/uninstall.sh"
    exit 1
fi

echo "🛡️ Haji Panel - حذف"
echo ""

read -p "آیا از حذف Haji Panel مطمئن هستید؟ (yes/no): " confirm
[[ "$confirm" != "yes" ]] && echo "لغو شد." && exit 0

# Stop service
log_info "توقف سرویس..."
systemctl stop haji-panel 2>/dev/null || true
systemctl disable haji-panel 2>/dev/null || true
rm -f /etc/systemd/system/haji-panel.service
systemctl daemon-reload

# Disconnect Warp
log_info "قطع Warp..."
warp-cli disconnect 2>/dev/null || true

# Remove Nginx config
log_info "حذف کانفیگ Nginx..."
rm -f /etc/nginx/sites-enabled/haji-panel
rm -f /etc/nginx/sites-available/haji-panel
systemctl reload nginx 2>/dev/null || true

# Restore DNS
log_info "بازگردانی DNS..."
rm -f /etc/systemd/resolved.conf.d/doh.conf
systemctl restart systemd-resolved 2>/dev/null || true
[[ -f /etc/resolv.conf.haji-backup ]] && cp /etc/resolv.conf.haji-backup /etc/resolv.conf

# Remove files
log_info "حذف فایل‌ها..."
rm -rf /opt/haji-panel

log_ok "Haji Panel حذف شد ✅"
