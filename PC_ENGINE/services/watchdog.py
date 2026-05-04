from __future__ import annotations

import socket
import time
from dataclasses import dataclass


@dataclass
class WatchdogStatus:
    ok: bool
    reason: str
    checked_ts: int


class Watchdog:
    def __init__(self, host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.last_status = WatchdogStatus(True, "not checked yet", 0)

    def check_internet(self) -> WatchdogStatus:
        try:
            socket.setdefaulttimeout(self.timeout)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
            self.last_status = WatchdogStatus(True, "internet ok", int(time.time()))
        except Exception as exc:
            self.last_status = WatchdogStatus(False, f"internet check failed: {exc}", int(time.time()))
        return self.last_status

    def check_exchange(self, exchange, symbol: str) -> WatchdogStatus:
        try:
            ticker = exchange.fetch_ticker(symbol)
            if float(ticker.get("last") or 0) <= 0:
                raise RuntimeError("invalid ticker price")
            self.last_status = WatchdogStatus(True, "exchange ok", int(time.time()))
        except Exception as exc:
            self.last_status = WatchdogStatus(False, f"exchange check failed: {exc}", int(time.time()))
        return self.last_status
