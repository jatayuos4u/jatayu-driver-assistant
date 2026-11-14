"""Read-only PCI hardware evidence; vendor IDs are hints, not firmware diagnoses."""
from dataclasses import dataclass, asdict
from pathlib import Path
import re
from .recommendations import ALLOWED

SYS_PCI = Path('/sys/bus/pci/devices')
HEX = re.compile(r'^0x[0-9a-fA-F]{4}$')
ADDRESS = re.compile(r'^[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]$')
# Conservative mapping: PCI vendor and class family only. Not proof of a missing firmware blob.
HINTS = {('0x1002', '03'): 'firmware-amd-graphics',
         ('0x8086', '0280'): 'firmware-iwlwifi',
         ('0x10ec', '0280'): 'firmware-realtek'}

@dataclass(frozen=True)
class HardwareHint:
    address: str
    vendor_id: str
    device_id: str
    class_id: str
    driver: str
    package_hint: str | None
    confidence: str
    explanation: str
    category: str = "other"

    def to_dict(self):
        return asdict(self)


def _read_hex(path):
    try:
        value = path.read_text(encoding='ascii').strip().lower()
    except (OSError, UnicodeError):
        return None
    return value if HEX.fullmatch(value) else None


def classify_pci(class_id):
    """Categorize PCI base class; Bluetooth often uses USB and is not inferred."""
    classes = {'03': 'graphics', '02': 'network', '01': 'storage',
               '04': 'multimedia', '0c': 'controller'}
    return classes.get(class_id[2:4], 'other') if re.fullmatch(r'0x[0-9a-f]{6}', class_id) else 'other'


def report_payload(hints):
    """Portable report with no privileged actions or unsupported claims."""
    return {'schema_version': 1, 'source': 'local_pci_sysfs_read_only',
            'hardware_match_verified': False, 'installation_enabled': False,
            'device_specific_apt_enabled': False, 'recommendation_policy': 'fail_closed',
            'devices': [{**h.to_dict(), 'recommendation_status': 'no_verified_recommendation',
                         'device_specific_apt_enabled': False} for h in hints]}


def inspect_pci(root=SYS_PCI, limit=128):
    """Inspect only sysfs PCI entries. Never execute shell commands or change files."""
    result = []
    try:
        entries = sorted(root.iterdir())
    except OSError:
        return result
    for entry in entries[:limit]:
        if entry.is_symlink():
            # Real sysfs PCI entries are symlinks; only the fixed sysfs root is trusted.
            if root != SYS_PCI:
                continue
        if not ADDRESS.fullmatch(entry.name) or not entry.is_dir():
            continue
        vendor = _read_hex(entry / 'vendor')
        device = _read_hex(entry / 'device')
        try:
            cls = (entry / 'class').read_text(encoding='ascii').strip().lower()
        except (OSError, UnicodeError):
            cls = ''
        if not vendor or not device or not re.fullmatch(r'0x[0-9a-f]{6}', cls):
            continue
        try:
            driver = (entry / 'driver').resolve(strict=True).name
        except (OSError, RuntimeError):
            driver = ''
        family = cls[2:4]
        subclass = cls[2:6]
        package = HINTS.get((vendor, subclass)) or HINTS.get((vendor, family))
        if package not in ALLOWED:
            package = None
        result.append(HardwareHint(entry.name, vendor, device, cls, driver,
            package, 'low' if package else 'insufficient',
            ('Vendor/class family suggests a possible firmware package; device-level match and firmware failure are not verified.'
             if package else 'No conservative package mapping for this PCI device.'),
            classify_pci(cls)))
    return result
