#!/usr/bin/env python3
"""
Haji Panel - Server Monitor
مانیتورینگ منابع سرور
"""

import psutil
import time
from datetime import datetime


class ServerMonitor:
    """مانیتورینگ منابع سرور"""

    def cpu_usage(self):
        """درصد استفاده CPU"""
        return psutil.cpu_percent(interval=1)

    def cpu_count(self):
        """تعداد هسته‌های CPU"""
        return psutil.cpu_count()

    def ram_usage(self):
        """اطلاعات RAM"""
        ram = psutil.virtual_memory()
        return {
            "total": ram.total,
            "used": ram.used,
            "free": ram.available,
            "percent": ram.percent,
        }

    def disk_usage(self, path="/"):
        """اطلاعات دیسک"""
        disk = psutil.disk_usage(path)
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
        }

    def network_stats(self):
        """آمار شبکه"""
        net = psutil.net_io_counters()
        return {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
        }

    def uptime(self):
        """زمان روشن بودن سرور"""
        boot = psutil.boot_time()
        up = time.time() - boot
        hours = int(up // 3600)
        minutes = int((up % 3600) // 60)
        return f"{hours} ساعت و {minutes} دقیقه"

    def load_average(self):
        """میانگین بار سیستم"""
        try:
            load1, load5, load15 = os.getloadavg()
            return {"1min": load1, "5min": load5, "15min": load15}
        except Exception:
            return {"1min": 0, "5min": 0, "15min": 0}

    def all_stats(self):
        """تمام آمار در یک دیکشنری"""
        return {
            "cpu": {
                "usage": self.cpu_usage(),
                "cores": self.cpu_count(),
            },
            "ram": self.ram_usage(),
            "disk": self.disk_usage(),
            "network": self.network_stats(),
            "uptime": self.uptime(),
            "timestamp": datetime.now().isoformat(),
        }
