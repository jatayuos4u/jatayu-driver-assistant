"""Read-only Linux hardware discovery using sysfs and standard utilities."""
from dataclasses import dataclass, asdict
from pathlib import Path
import subprocess
import re

SYS = Path('/sys')

@dataclass
class Device:
    category: str
    name: str
    bus: str
    identifier: str
    driver: str = ''
    status: str = 'Detected'
    detail: str = ''

    def as_dict(self):
        return asdict(self)

def run_command(args, timeout=8):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return result.stdout if result.returncode == 0 else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''

def pci_category(text):
    t = text.lower()
    if any(s in t for s in ('vga compatible', '3d controller', 'display controller')):
        return 'Graphics'
    if 'network controller' in t or 'wireless' in t:
        return 'Wi-Fi'
    if 'ethernet controller' in t:
        return 'Ethernet'
    if 'audio device' in t or 'multimedia audio' in t:
        return 'Audio'
    if 'bluetooth' in t:
        return 'Bluetooth'
    return 'Other'

def driver_for(path):
    try:
        return (path / 'driver').resolve(strict=True).name
    except (OSError, RuntimeError):
        return ''

def scan_pci(root=SYS):
    devices = []
    output = run_command(['lspci', '-D', '-nn'])
    names = {}
    for line in output.splitlines():
        match = re.match(r'^(\S+)\s+(.+)$', line)
        if match:
            names[match.group(1)] = match.group(2)
    path = root / 'bus/pci/devices'
    if not path.exists():
        return devices
    for item in sorted(path.iterdir()):
        if not item.is_dir():
            continue
        desc = names.get(item.name, 'PCI device')
        cat = pci_category(desc)
        drv = driver_for(item)
        devices.append(Device(cat, desc, 'PCI', item.name, drv,
                              'Driver loaded' if drv else 'Needs review',
                              'No bound kernel driver detected; this may be normal for some devices.' if not drv else 'Kernel driver bound. Functionality not independently verified.'))
    return devices

def scan_usb(root=SYS):
    devices = []
    path = root / 'bus/usb/devices'
    if not path.exists():
        return devices
    for item in sorted(path.iterdir()):
        if not (item / 'idVendor').exists() or not (item / 'idProduct').exists():
            continue
        def read(name):
            try:
                return (item / name).read_text(errors='replace').strip()
            except OSError:
                return ''
        vendor = read('manufacturer')
        product = read('product')
        name = ' '.join(x for x in (vendor, product) if x) or 'USB device'
        identifier = f"{read('idVendor')}:{read('idProduct')}"
        devices.append(Device('USB', name, 'USB', identifier, driver_for(item), 'Detected',
                              'USB device detected; interface drivers may be attached separately.'))
    return devices

def scan_network(root=SYS):
    devices = []
    path = root / 'class/net'
    if not path.exists():
        return devices
    for item in sorted(path.iterdir()):
        if item.name == 'lo':
            continue
        wireless = (item / 'wireless').exists() or (item / 'phy80211').exists()
        cat = 'Wi-Fi' if wireless else 'Ethernet'
        drv = driver_for(item / 'device')
        try:
            state = (item / 'operstate').read_text().strip()
        except OSError:
            state = 'unknown'
        devices.append(Device(cat, item.name, 'Network', item.name, drv,
                              'Connected' if state == 'up' else 'Detected',
                              f'Interface state: {state}. A disconnected interface does not necessarily indicate a driver problem.'))
    return devices

def scan_audio(root=SYS):
    path = root / 'class/sound'
    if not path.exists():
        return []
    return [Device('Audio', p.name, 'Sound', p.name, driver_for(p / 'device'), 'Detected',
                   'Sound device present; playback has not been tested.')
            for p in sorted(path.glob('card[0-9]*')) if p.is_dir()]

def scan_bluetooth(root=SYS):
    path = root / 'class/bluetooth'
    if not path.exists():
        return []
    return [Device('Bluetooth', p.name, 'Bluetooth', p.name, driver_for(p / 'device'), 'Detected',
                   'Bluetooth adapter detected; pairing has not been tested.')
            for p in sorted(path.glob('hci*')) if p.is_dir()]

def scan_all(root=SYS):
    result = []
    for scan in (scan_pci, scan_usb, scan_network, scan_audio, scan_bluetooth):
        try:
            result.extend(scan(root))
        except OSError:
            continue
    return result


def binding_state(device):
    """Describe observable kernel binding, not device health.

    USB device nodes commonly have interface drivers rather than device drivers.
    Virtual interfaces and sound/Bluetooth class nodes may also lack direct links.
    """
    if device.driver:
        return 'bound'
    if device.bus == 'PCI':
        return 'unbound'
    return 'unknown'


def summarize(devices):
    """Mutually exclusive, auditable totals; no unverified failure claims."""
    states = [binding_state(device) for device in devices]
    return {'detected': len(devices), 'bound': states.count('bound'),
            'unbound': states.count('unbound'), 'unknown': states.count('unknown')}
