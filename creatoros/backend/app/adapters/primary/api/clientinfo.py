"""Best-effort request client metadata for connection/traffic tracking.

- IP from X-Forwarded-For / X-Real-IP / client host
- device / browser / OS parsed naively from the User-Agent header
- location from ip-api.com (cached, short timeout, private IPs skipped)
Nothing here should ever block a request — the middleware swallows failures.
"""
from __future__ import annotations

import json
import urllib.request
from functools import lru_cache

_UA_CACHE: dict[str, tuple[str, str, str]] = {}
_LOC_CACHE: dict[str, str] = {}

PRIVATE_PREFIXES = (
    "127.", "10.", "192.168.", "::1", "fe80:", "0.0.0.0", "100.", "172.16.", "172.17.",
    "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
    "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
)


def parse_ua(user_agent: str) -> tuple[str, str, str]:
    """Return (device, browser, os) for a User-Agent header."""
    ua = user_agent or ""
    if ua in _UA_CACHE:
        return _UA_CACHE[ua]

    low = ua.lower()
    if "iphone" in low or "ipad" in low:
        device = "mobile" if "iphone" in low else "tablet"
    elif "android" in low and "mobile" in low:
        device = "mobile"
    elif "android" in low:
        device = "tablet"
    elif "mac" in low:
        device = "desktop"
    elif "windows" in low or "linux" in low or "x11" in low:
        device = "desktop"
    else:
        device = "unknown"

    if "safari" in low and "chrome" not in low and "crios" not in low:
        browser = "Safari"
    elif "edg/" in low or "edge/" in low:
        browser = "Edge"
    elif "firefox" in low:
        browser = "Firefox"
    elif "chrome" in low or "crios" in low:
        browser = "Chrome"
    elif "curl" in low:
        browser = "curl"
    else:
        browser = "unknown"

    if "iphone" in low or "ipad" in low or "ipod" in low:
        os_ = "iOS"
    elif "android" in low:
        os_ = "Android"
    elif "mac os" in low:
        os_ = "macOS"
    elif "windows" in low:
        os_ = "Windows"
    elif "linux" in low:
        os_ = "Linux"
    else:
        os_ = "unknown"

    _UA_CACHE[ua] = (device, browser, os_)
    return device, browser, os_


@lru_cache(maxsize=256)
def _geo_for_ip(ip: str) -> str:
    """Resolve 'City, Country' for a public IPv4/IPv6 via ip-api.com."""
    if not ip or ip.startswith(PRIVATE_PREFIXES):
        return ""
    url = f"http://ip-api.com/json/{ip}?fields=status,country,city&lang=en"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CreatorOS/1.0"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        if data.get("status") == "success":
            city = str(data.get("city") or "")
            country = str(data.get("country") or "")
            return ", ".join(part for part in (city, country) if part)
    except Exception:
        pass
    return ""


def client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real = request.headers.get("x-real-ip", "")
    if real:
        return real.strip()
    return (request.client.host if request.client else "") or ""


def location_for_ip(ip: str) -> str:
    if ip in _LOC_CACHE:
        return _LOC_CACHE[ip]
    value = _geo_for_ip(ip)
    _LOC_CACHE[ip] = value
    return value


def meta_from_request(request) -> dict:
    """Dict of client metadata for tracking stores."""
    ip = client_ip(request)
    ua = request.headers.get("user-agent", "")
    device, browser, os_ = parse_ua(ua)
    return {
        "ip": ip,
        "user_agent": ua,
        "device": device,
        "browser": browser,
        "os": os_,
        "location": location_for_ip(ip),
    }