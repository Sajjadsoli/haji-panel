#!/usr/bin/env python3
"""
Haji Panel - SSL Manager
مدیریت گواهی SSL با Certbot
"""

import subprocess
import os
import json

class SSLManager:
    """مدیریت گواهی‌های SSL/HTTPS"""

    def __init__(self):
        self.config_dir = "/opt/haji-panel/config"
        self.domain_file = os.path.join(self.config_dir, "domain.json")

    def _run(self, cmd):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            return r.returncode == 0, r.stdout.strip() or r.stderr.strip()
        except Exception as e:
            return False, str(e)

    def _load_domain(self):
        try:
            with open(self.domain_file) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_domain(self, cfg):
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.domain_file, "w") as f:
            json.dump(cfg, f, indent=2)

    def obtain_ssl(self, domain, email):
        """دریافت گواهی SSL از Let's Encrypt"""
        cmd = (
            f"certbot --nginx -d {domain} -d www.{domain} "
            f"-m {email} --agree-tos --no-eff-email --non-interactive --redirect"
        )
        ok, msg = self._run(cmd)

        if ok:
            cfg = self._load_domain()
            cfg["ssl_enabled"] = True
            self._save_domain(cfg)

        return ok, msg

    def renew_ssl(self):
        """تمدید گواهی SSL"""
        ok, msg = self._run("certbot renew --quiet")
        return ok, msg

    def test_renewal(self):
        """تست تمدید گواهی"""
        ok, msg = self._run("certbot renew --dry-run")
        return ok, msg

    def list_certificates(self):
        """لیست گواهی‌ها"""
        ok, msg = self._run("certbot certificates")
        return ok, msg

    def revoke_ssl(self, domain):
        """ابطال گواهی"""
        ok, msg = self._run(f"certbot delete --cert-name {domain} --non-interactive")
        if ok:
            cfg = self._load_domain()
            cfg["ssl_enabled"] = False
            self._save_domain(cfg)
        return ok, msg
