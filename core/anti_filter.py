#!/usr/bin/env python3
"""
Haji Panel - Anti-Filter Core Module
ماژول هسته ضد‌فیلتر
"""

import subprocess
import os
import json

class AntiFilter:
    """مدیریت لایه‌های ضد‌فیلتر سرور"""

    def __init__(self):
        self.config_dir = "/opt/haji-panel/config"

    def _run(self, cmd):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return r.returncode == 0, r.stdout.strip() or r.stderr.strip()
        except Exception as e:
            return False, str(e)

    # ─── Cloudflare Warp ──────────────────────────────

    def warp_status(self):
        ok, out = self._run("warp-cli status 2>/dev/null")
        if not ok:
            return "not_installed", "Warp نصب نیست"
        if "Connected" in out:
            return "connected", out
        return "disconnected", out

    def warp_enable(self):
        ok, msg = self._run("warp-cli registration new 2>/dev/null; warp-cli mode proxy; warp-cli connect")
        return ok, msg

    def warp_disable(self):
        ok, msg = self._run("warp-cli disconnect")
        return ok, msg

    # ─── DoH (DNS over HTTPS) ─────────────────────────

    def doh_status(self):
        if os.path.exists("/etc/systemd/resolved.conf.d/doh.conf"):
            return True
        try:
            with open("/etc/resolv.conf") as f:
                return "1.1.1.1" in f.read()
        except Exception:
            return False

    def doh_enable(self):
        doh_conf = """[Resolve]
DNS=1.1.1.1#one.one.one.one 8.8.8.8#dns.google
FallbackDNS=1.0.0.1#one.one.one.one 8.8.4.4#dns.google
DNSOverHTTPS=https://cloudflare-dns.com/dns-query https://dns.google/dns-query
DNSSEC=yes
"""
        os.makedirs("/etc/systemd/resolved.conf.d/", exist_ok=True)
        with open("/etc/systemd/resolved.conf.d/doh.conf", "w") as f:
            f.write(doh_conf)
        ok, msg = self._run("systemctl restart systemd-resolved")
        return ok, msg or "DoH فعال شد"

    def doh_disable(self):
        os.remove("/etc/systemd/resolved.conf.d/doh.conf")
        ok, msg = self._run("systemctl restart systemd-resolved")
        return ok, msg or "DoH غیرفعال شد"

    # ─── Full Status ──────────────────────────────────

    def full_status(self):
        warp_st, warp_detail = self.warp_status()
        return {
            "warp": {"status": warp_st, "detail": warp_detail},
            "doh": self.doh_status(),
            "firewall": self._run("ufw status")[1] if os.path.exists("/usr/sbin/ufw") else "نصب نیست",
        }
