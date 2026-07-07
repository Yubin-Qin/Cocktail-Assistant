"""Local network helpers — figure out the LAN address to advertise."""
from __future__ import annotations

import socket


def lan_ip() -> str:
    """Best-effort primary LAN IPv4 address of this machine.

    Uses the "connect a UDP socket" trick: it doesn't send anything, but the
    OS picks the interface it *would* use to reach the target, giving us the
    right address without relying on ``gethostname`` (which often returns
    ``127.0.0.1`` on macOS). Falls back gracefully if the network is down.
    """
    candidates: list[str] = []
    for target in ("8.8.8.8", "1.1.1.1", "114.114.114.114"):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.connect((target, 80))
                ip = sock.getsockname()[0]
            finally:
                sock.close()
            if ip and not ip.startswith("127."):
                candidates.append(ip)
                break
        except OSError:
            continue

    if candidates:
        return candidates[0]

    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


def url(host: str, port: int) -> str:
    return f"http://{host}:{port}"
