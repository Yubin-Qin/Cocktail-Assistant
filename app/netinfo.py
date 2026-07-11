"""Local network helpers — figure out the LAN address to advertise."""
from __future__ import annotations

import re
import socket
import subprocess


def _is_usable_lan(ip: str) -> bool:
    """A real, hostable LAN IPv4: an RFC1918 private address that is neither
    loopback nor a network/broadcast endpoint, and not the ``198.18.0.0/15``
    benchmark range that macOS proxies (Clash / Surge) bind to their TUN
    interface (which otherwise masquerades as the default route)."""
    if not ip or ip.startswith("127."):
        return False
    if ip.startswith("198.18.") or ip.startswith("198.19."):
        return False
    try:
        last = int(ip.rsplit(".", 1)[1])
    except (IndexError, ValueError):
        return False
    if last in (0, 255):  # network / broadcast on a typical /24
        return False
    return (
        ip.startswith("10.")
        or ip.startswith("192.168.")
        or re.match(r"^172\.(1[6-9]|2\d|3[01])\.", ip) is not None
    )


def _from_default_route() -> str | None:
    """Source IP the OS would use for the default route, via the UDP connect
    trick (sends nothing; the OS picks the interface). May be a proxy TUN
    address, so callers must validate the result."""
    for target in ("8.8.8.8", "1.1.1.1", "114.114.114.114"):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.connect((target, 80))
                return sock.getsockname()[0]
            finally:
                sock.close()
        except OSError:
            continue
    return None


def _from_interfaces() -> str | None:
    """Enumerate interface IPv4s via the OS and return the best private one.
    Used when the default route runs through a proxy TUN."""
    for cmd in (["ip", "-4", "-o", "addr"], ["ifconfig"]):
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, timeout=1.5
            ).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        ips = [
            ip
            for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", out)
            if _is_usable_lan(ip)
        ]
        if not ips:
            continue
        # prefer 192.168.*, then 10.*, then 172.16-31.*
        ips.sort(
            key=lambda ip: 0
            if ip.startswith("192.168.")
            else 1
            if ip.startswith("10.")
            else 2
        )
        return ips[0]
    return None


def lan_ip() -> str:
    """Best-effort primary LAN IPv4 address of this machine.

    Prefers the default-route source address; if that is a proxy/benchmark
    address (common when a VPN/proxy captures the default route), enumerates
    the real interfaces instead. Falls back gracefully if the network is down.
    """
    via_route = _from_default_route()
    if via_route and _is_usable_lan(via_route):
        return via_route
    via_ifaces = _from_interfaces()
    if via_ifaces:
        return via_ifaces
    if via_route:  # at least return something non-loopback
        return via_route
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


def url(host: str, port: int) -> str:
    return f"http://{host}:{port}"
