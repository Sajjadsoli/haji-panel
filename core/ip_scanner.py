#!/usr/bin/env python3
"""
Haji Panel - Clean IP Scanner & Auto-Switcher
اسکنر آی‌پی تمیز با تست استرس واقعی و تعویض خودکار

Adapted from sMb-Scanner (smblue07/sMb-Scanner) for server-side automation.
Scans Cloudflare/Gcore/Fastly IP ranges, stress-tests them via Xray,
finds Diamond IPs, checks if current IP is filtered, and auto-switches.
"""

import os
import json
import time
import subprocess
import ipaddress
import concurrent.futures
import threading
import socket
import re
import urllib.parse
import requests
from datetime import datetime

CONFIG_DIR = "/opt/haji-panel/config"
SCANNER_FILE = os.path.join(CONFIG_DIR, "scanner.json")
XRAY_BIN = "/usr/local/xray/xray"
XRAY_CONFIG_DIR = "/usr/local/xray/config"

# Cloudflare IP ranges (subset - most common)
CLOUDFLARE_RANGES = [
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "162.159.0.0/16",
    "188.114.96.0/20",
    "190.93.240.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
]

# Gcore IP ranges
GCORE_RANGES = [
    "92.223.64.0/19",
    "139.45.16.0/20",
]

# Fastly IP ranges
FASTLY_RANGES = [
    "151.101.0.0/16",
    "199.232.0.0/16",
    "167.82.0.0/20",
]

ALL_RANGES = {
    "cloudflare": CLOUDFLARE_RANGES,
    "gcore": GCORE_RANGES,
    "fastly": FASTLY_RANGES,
}

print_lock = threading.Lock()


class IPScanner:
    """اسکنر آی‌پی تمیز با تست استرس"""

    def __init__(self):
        self.config_dir = CONFIG_DIR
        os.makedirs(self.config_dir, exist_ok=True)
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(SCANNER_FILE):
            self._save({
                "enabled": False,
                "scan_interval_hours": 6,
                "cdn_targets": ["cloudflare"],
                "max_ips_per_scan": 500,
                "concurrent_workers": 10,
                "min_speed_kbps": 100,
                "max_ping_ms": 500,
                "top_ips_count": 10,
                "multi_location": True,
                "locations": [],
                "diamond_ips": [],
                "current_ips": {},
                "last_scan": None,
                "last_scan_results": [],
                "auto_switch": True,
                "check_before_switch": True,
            })

    def _load(self):
        try:
            with open(SCANNER_FILE) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, data):
        with open(SCANNER_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_settings(self):
        return self._load()

    def update_settings(self, settings):
        data = self._load()
        data.update(settings)
        self._save(data)
        return True

    def _generate_ip_list(self, cdn_targets, max_ips):
        """تولید لیست IP از بازه‌های CDN"""
        ip_list = []
        for cdn in cdn_targets:
            ranges = ALL_RANGES.get(cdn, [])
            for rng in ranges:
                try:
                    network = ipaddress.IPv4Network(rng, strict=False)
                    for ip in network.hosts():
                        ip_list.append(str(ip))
                        if len(ip_list) >= max_ips:
                            return ip_list
                except Exception:
                    continue
        return ip_list[:max_ips]

    def _check_ip_filtered(self, ip, port=443, timeout=5):
        """بررسی فیلتر بودن یک IP"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result != 0  # True = filtered/blocked
        except Exception:
            return True

    def _stress_test_ip(self, ip, base_config, timeout=10):
        """تست استرس واقعی یک IP با Xray"""
        # Generate temp Xray config for this IP
        temp_config = self._generate_xray_config(base_config, ip)
        if not temp_config:
            return None

        config_path = f"/tmp/xray_scan_{ip.replace('.', '_')}.json"
        with open(config_path, "w") as f:
            json.dump(temp_config, f)

        try:
            # Start Xray with this config
            proc = subprocess.Popen(
                [XRAY_BIN, "run", "-config", config_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(2)

            # Test download speed through the proxy
            start_time = time.time()
            try:
                # Try downloading a test file through the proxy
                proxies = {
                    "http": "socks5://127.0.0.1:10808",
                    "https": "socks5://127.0.0.1:10808",
                }
                resp = requests.get(
                    "https://speed.cloudflare.com/__down?bytes=1000000",
                    proxies=proxies,
                    timeout=timeout,
                    stream=True,
                )
                if resp.status_code == 200:
                    data = resp.content
                    elapsed = time.time() - start_time
                    speed_kbps = (len(data) / 1024) / elapsed if elapsed > 0 else 0
                    ping_ms = elapsed * 1000

                    return {
                        "ip": ip,
                        "speed_kbps": round(speed_kbps, 1),
                        "ping_ms": round(ping_ms, 1),
                        "status": "diamond",
                        "tested_at": datetime.now().isoformat(),
                    }
            except Exception:
                pass

        except Exception:
            pass
        finally:
            try:
                proc.kill()
                proc.wait(timeout=3)
            except Exception:
                pass
            os.remove(config_path)

        return None

    def _generate_xray_config(self, base_link, new_ip):
        """تولید کانفیگ Xray برای تست IP"""
        try:
            parsed = urllib.parse.urlparse(base_link)
            qs = dict(urllib.parse.parse_qsl(parsed.query))

            security = qs.get("security", "none")
            network = qs.get("type", "tcp")
            sni = qs.get("sni", parsed.hostname)
            port = int(parsed.port) if parsed.port else 443

            outbound = {
                "tag": "proxy",
                "protocol": parsed.scheme,
                "settings": {},
                "streamSettings": {
                    "network": network,
                    "security": security,
                },
            }

            if parsed.scheme == "vless":
                outbound["settings"]["vnext"] = [{
                    "address": new_ip,
                    "port": port,
                    "users": [{
                        "id": parsed.username,
                        "encryption": "none",
                        "flow": qs.get("flow", ""),
                    }],
                }]
            elif parsed.scheme == "vmess":
                outbound["settings"]["vnext"] = [{
                    "address": new_ip,
                    "port": port,
                    "users": [{
                        "id": parsed.username,
                        "alterId": 0,
                    }],
                }]
            elif parsed.scheme == "trojan":
                outbound["settings"]["servers"] = [{
                    "address": new_ip,
                    "port": port,
                    "password": parsed.username,
                }]

            if security == "tls" or security == "reality":
                outbound["streamSettings"]["tlsSettings"] = {
                    "serverName": sni,
                    "allowInsecure": True,
                }
                if security == "reality":
                    outbound["streamSettings"]["realitySettings"] = {
                        "serverName": sni,
                        "fingerprint": "chrome",
                        "publicKey": qs.get("pb", ""),
                        "shortId": qs.get("sid", ""),
                    }

            if network == "ws":
                outbound["streamSettings"]["wsSettings"] = {
                    "path": qs.get("path", "/"),
                    "headers": {"Host": sni},
                }
            elif network == "grpc":
                outbound["streamSettings"]["grpcSettings"] = {
                    "serviceName": qs.get("serviceName", ""),
                }

            config = {
                "log": {"loglevel": "error"},
                "inbounds": [{
                    "tag": "socks",
                    "port": 10808,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "settings": {"udp": True},
                }],
                "outbounds": [outbound, {"tag": "direct", "protocol": "freedom"}],
            }

            return config
        except Exception:
            return None

    def scan(self, base_config=None, cdn_targets=None, max_ips=None, workers=None):
        """اجرای اسکن کامل"""
        settings = self._load()

        if cdn_targets is None:
            cdn_targets = settings.get("cdn_targets", ["cloudflare"])
        if max_ips is None:
            max_ips = settings.get("max_ips_per_scan", 500)
        if workers is None:
            workers = settings.get("concurrent_workers", 10)

        # Generate IP list
        ip_list = self._generate_ip_list(cdn_targets, max_ips)
        if not ip_list:
            return {"ok": False, "error": "هیچ IP برای اسکن یافت نشد"}

        # Filter out already-known bad IPs
        known_bad = {r["ip"] for r in settings.get("last_scan_results", []) if r.get("status") == "zombie"}
        ip_list = [ip for ip in ip_list if ip not in known_bad]

        # Run stress tests
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self._stress_test_ip, ip, base_config or f"vless://test@{ip}:443?security=tls&sni=cloudflare.com&type=tcp"): ip
                for ip in ip_list
            }
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        # Sort by speed (best first)
        results.sort(key=lambda x: x["speed_kbps"], reverse=True)

        # Filter by minimum criteria
        min_speed = settings.get("min_speed_kbps", 100)
        max_ping = settings.get("max_ping_ms", 500)
        top_count = settings.get("top_ips_count", 10)

        diamond_ips = [
            r for r in results
            if r["speed_kbps"] >= min_speed and r["ping_ms"] <= max_ping
        ][:top_count]

        # Multi-location: group by /16 prefix
        multi_location = settings.get("multi_location", True)
        locations = []
        if multi_location and diamond_ips:
            seen_prefixes = set()
            for ip_info in diamond_ips:
                prefix = ".".join(ip_info["ip"].split(".")[:2])
                if prefix not in seen_prefixes:
                    locations.append({
                        "prefix": prefix,
                        "ip": ip_info["ip"],
                        "speed_kbps": ip_info["speed_kbps"],
                        "ping_ms": ip_info["ping_ms"],
                    })
                    seen_prefixes.add(prefix)

        # Save results
        data = self._load()
        data["diamond_ips"] = diamond_ips
        data["last_scan"] = datetime.now().isoformat()
        data["last_scan_results"] = results[:50]  # Keep last 50
        data["locations"] = locations
        self._save(data)

        return {
            "ok": True,
            "scanned": len(ip_list),
            "diamonds_found": len(diamond_ips),
            "locations": len(locations),
            "top_ips": diamond_ips[:5],
        }

    def check_current_ip(self, subdomain):
        """بررسی فیلتر بودن IP فعلی یک ساب‌دامنه"""
        data = self._load()
        current = data.get("current_ips", {}).get(subdomain)
        if not current:
            return {"filtered": True, "ip": None, "message": "IP تنظیم نشده"}

        is_filtered = self._check_ip_filtered(current["ip"])
        return {
            "filtered": is_filtered,
            "ip": current["ip"],
            "speed_kbps": current.get("speed_kbps", 0),
            "ping_ms": current.get("ping_ms", 0),
            "last_check": datetime.now().isoformat(),
        }

    def get_best_ip(self, subdomain, exclude_current=True):
        """دریافت بهترین IP تمیز برای ساب‌دامنه"""
        data = self._load()
        diamond_ips = data.get("diamond_ips", [])
        if not diamond_ips:
            return None

        current = data.get("current_ips", {}).get(subdomain, {})
        current_ip = current.get("ip")

        # If multi-location, try to get from different location
        if data.get("multi_location", True):
            locations = data.get("locations", [])
            if locations:
                # Pick best location that's not current
                for loc in locations:
                    if loc["ip"] != current_ip:
                        return loc
        else:
            for ip_info in diamond_ips:
                if ip_info["ip"] != current_ip:
                    return ip_info

        return diamond_ips[0] if diamond_ips else None

    def assign_ip(self, subdomain, ip_info=None):
        """اختصاص IP به ساب‌دامنه"""
        data = self._load()
        if ip_info is None:
            ip_info = self.get_best_ip(subdomain)
            if not ip_info:
                return False, "هیچ IP تمیزی موجود نیست"

        if "current_ips" not in data:
            data["current_ips"] = {}

        data["current_ips"][subdomain] = {
            "ip": ip_info["ip"],
            "speed_kbps": ip_info.get("speed_kbps", 0),
            "ping_ms": ip_info.get("ping_ms", 0),
            "assigned_at": datetime.now().isoformat(),
        }
        self._save(data)
        return True, f"IP {ip_info['ip']} به {subdomain} اختصاص یافت"

    def auto_switch_if_filtered(self, subdomain):
        """تعویض خودکار IP اگر فعلی فیلتر شده باشد"""
        data = self._load()
        if not data.get("auto_switch", True):
            return False, "تعویض خودکار غیرفعال است"

        # Check current IP
        check = self.check_current_ip(subdomain)
        if not check["filtered"]:
            return True, f"IP فعلی ({check['ip']}) سالم است"

        # Current is filtered, find new IP
        if data.get("check_before_switch", True) and not data.get("diamond_ips"):
            # No diamonds available, need to scan first
            return False, "IP فعلی فیلتر شده و IP تمیزی موجود نیست. اسکن لازم است."

        best = self.get_best_ip(subdomain)
        if not best:
            return False, "IP فعلی فیلتر شده و IP تمیزی موجود نیست"

        # Verify new IP is not filtered
        if data.get("check_before_switch", True):
            if self._check_ip_filtered(best["ip"]):
                return False, f"IP جدید ({best['ip']}) هم فیلتر شده"

        # Switch
        ok, msg = self.assign_ip(subdomain, best)
        return ok, msg

    def get_status(self):
        """دریافت وضعیت کامل اسکنر"""
        data = self._load()
        return {
            "enabled": data.get("enabled", False),
            "auto_switch": data.get("auto_switch", True),
            "check_before_switch": data.get("check_before_switch", True),
            "multi_location": data.get("multi_location", True),
            "last_scan": data.get("last_scan"),
            "diamonds_count": len(data.get("diamond_ips", [])),
            "locations_count": len(data.get("locations", [])),
            "current_ips": data.get("current_ips", {}),
            "top_diamonds": data.get("diamond_ips", [])[:5],
            "locations": data.get("locations", []),
            "scan_interval_hours": data.get("scan_interval_hours", 6),
            "cdn_targets": data.get("cdn_targets", ["cloudflare"]),
        }
