"""Network utilities for BacPipes."""

import socket
from typing import Optional, List, Dict


def get_local_ip() -> Optional[str]:
    """Auto-detect local IP address.

    Creates a UDP socket and connects to an external address
    to determine the local IP address.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        # Fallback: try to get from hostname
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip and not local_ip.startswith("127."):
                return local_ip
        except Exception:
            pass
        return None


def get_network_interfaces() -> List[Dict[str, str]]:
    """Get list of network interfaces with their IP addresses.

    Returns a list of dictionaries with 'name' and 'ip' keys.
    """
    interfaces = []

    try:
        import netifaces
    except ImportError:
        # netifaces not available, return just the detected local IP
        local_ip = get_local_ip()
        if local_ip:
            interfaces.append({"name": "default", "ip": local_ip})
        return interfaces

    try:
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr.get("addr")
                    if ip and not ip.startswith("127."):
                        interfaces.append({"name": iface, "ip": ip})
    except Exception:
        # Fallback to simple detection
        local_ip = get_local_ip()
        if local_ip:
            interfaces.append({"name": "default", "ip": local_ip})

    return interfaces
