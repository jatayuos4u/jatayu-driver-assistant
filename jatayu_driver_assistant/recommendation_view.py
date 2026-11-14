"""Conservative, presentation-only recommendations from observed hardware.

A bound driver does not prove health; an unbound device does not prove a fault.
No installation advice is inferred from device names or vendor IDs.
"""
from dataclasses import dataclass
import re

CATEGORIES = frozenset({'Wi-Fi', 'Ethernet', 'Graphics', 'Audio', 'Bluetooth', 'USB', 'Other'})
VIRTUAL_PREFIXES = ('veth', 'virbr', 'docker', 'br-', 'lxc', 'tun', 'tap', 'wg', 'zt', 'tailscale', 'vmnet', 'vboxnet', 'podman')

@dataclass(frozen=True)
class Advice:
    name: str
    full_name: str
    category: str
    driver: str
    identifier: str
    status: str
    explanation: str


def physical_device(device):
    if device.bus == 'Network':
        # Network interfaces are represented by their parent PCI/USB devices.
        # Excluding these also prevents virtual interfaces from being presented
        # as missing physical drivers.
        return False
    if device.bus not in ('PCI', 'USB'):
        return False
    return True


def short_name(device):
    name = device.name.strip()
    if device.category == 'Audio' and ('High Definition Audio Controller' in name or 'HD Audio' in name):
        return 'HD Audio Controller'
    if device.category == 'Graphics' and 'Intel' in name:
        return 'Intel Graphics Controller'
    if device.category == 'Wi-Fi' and 'Intel' in name:
        return 'Intel Wireless Adapter'
    name = re.sub(r'^\w+ controller\s*\[[^]]+\]:\s*', '', name, flags=re.I)
    name = re.sub(r'\s*\[[0-9a-fA-F]{4}:[0-9a-fA-F]{4}\]', '', name)
    name = re.sub(r'\s*\(rev [^)]+\)', '', name)
    return (name[:78].rstrip() + '…') if len(name) > 79 else (name or 'Unidentified device')


def build_advice(devices):
    result = []
    for device in devices:
        if not physical_device(device):
            continue
        driver = (device.driver or '').strip()
        if driver:
            status = 'working'
            explanation = 'Kernel driver bound. Functionality is not independently verified; no change indicated.'
        elif device.bus == 'USB' or device.category == 'Other':
            status = 'unknown'
            explanation = 'No driver shown. This may be normal; more evidence is needed.'
        else:
            status = 'attention'
            explanation = 'No kernel driver detected for this device. Investigate before changing packages.'
        result.append(Advice(short_name(device), device.name, device.category, driver,
                             device.identifier, status, explanation))
    priority = {'attention': 0, 'unknown': 1, 'working': 2}
    return sorted(result, key=lambda d: (priority[d.status], d.category, d.name))


def counts(items):
    return {status: sum(item.status == status for item in items)
            for status in ('attention', 'working', 'unknown')}
