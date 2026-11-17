"""Unprivileged, read-only checks of actual local hardware. Never infer health from missing logs."""
from pathlib import Path
import subprocess
from .safe_process import bounded_run

CATEGORIES = ('wifi', 'graphics', 'network', 'audio', 'bluetooth')


def _command(argv):
    try:
        result = bounded_run(argv, capture_output=True, text=True, timeout=5, check=False)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    return result.returncode, (result.stdout or result.stderr).strip()[:6000]


def run_live_checks(category):
    if category not in CATEGORIES:
        raise ValueError('Unsupported hardware check')
    details = []
    status = 'unknown'
    if category in ('wifi', 'network'):
        base = Path('/sys/class/net')
        try:
            names = sorted(p.name for p in base.iterdir() if p.name != 'lo')
        except OSError as exc:
            names = []
            details.append(f'Cannot read network interfaces: {exc}')
        for name in names:
            iface = base / name
            try:
                state = (iface / 'operstate').read_text().strip()
            except OSError:
                state = 'unknown'
            try:
                driver = (iface / 'device/driver').resolve().name
            except OSError:
                driver = 'unknown'
            is_wifi = (iface / 'wireless').exists() or name.startswith(('wl', 'wlan'))
            if category == 'wifi' and not is_wifi:
                continue
            details.append(f'{name}: state={state}, driver={driver}')
        status = 'detected' if details else 'no matching interface detected'
        code, output = _command(['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE', 'device', 'status'])
        if code == 0:
            details.append('NetworkManager: ' + output)
        elif output:
            details.append('NetworkManager information unavailable: ' + output)
        if category == 'wifi':
            code, output = _command(['rfkill', 'list'])
            if code == 0:
                details.append('Radio block information: ' + output)
            else:
                details.append('Radio block information unavailable')
    elif category == 'graphics':
        base = Path('/sys/class/drm')
        try:
            cards = sorted(p for p in base.glob('card[0-9]*') if p.name[4:].isdigit())
        except OSError:
            cards = []
        for card in cards:
            try:
                driver = (card / 'device/driver').resolve().name
            except OSError:
                driver = 'unknown'
            details.append(f'{card.name}: driver={driver}')
        status = 'detected' if details else 'no DRM graphics card detected'
        details.append('Display glitches and kernel errors cannot be ruled out by this check.')
    elif category == 'audio':
        try:
            cards = Path('/proc/asound/cards').read_text().strip()
            details.append(cards or 'No ALSA sound cards listed')
            status = 'detected' if cards and 'no soundcards' not in cards.lower() else 'no sound cards detected'
        except OSError as exc:
            details.append(f'ALSA information unavailable: {exc}')
    elif category == 'bluetooth':
        try:
            adapters = sorted(p.name for p in Path('/sys/class/bluetooth').glob('hci*'))
        except OSError:
            adapters = []
        details.extend(adapters)
        status = 'detected' if adapters else 'no Bluetooth adapter detected'
        code, output = _command(['rfkill', 'list', 'bluetooth'])
        if code == 0 and output:
            details.append('Radio block information: ' + output)
    return {'source': 'live_local_system', 'synthetic': False, 'category': category,
            'status': status, 'details': details, 'installation_enabled': False,
            'hardware_modified': False,
            'limitations': 'Detection does not prove complete driver or firmware health.'}
