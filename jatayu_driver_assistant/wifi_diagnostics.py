"""Bounded, unprivileged Wi-Fi diagnostics; never change networking or packages."""
from pathlib import Path
import re
import subprocess
from .safe_process import bounded_run

NET_ROOT = Path('/sys/class/net')
RFKILL_ROOT = Path('/sys/class/rfkill')
SAFE_IFACE = re.compile(r'^[A-Za-z0-9_.:-]{1,32}$')
STATES = {'up', 'down', 'unknown', 'dormant', 'lowerlayerdown', 'notpresent', 'testing'}


def _read(path, limit=128):
    try:
        return path.read_text(encoding='utf-8', errors='replace')[:limit].strip()
    except (OSError, ValueError):
        return None


def inspect_rfkill(root=RFKILL_ROOT, limit=64):
    """Return radio switch states; do not alter RF-kill controls."""
    result = []
    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name)[:limit]
    except OSError:
        return {'status': 'unavailable', 'radios': []}
    for entry in entries:
        if not re.fullmatch(r'rfkill[0-9]+', entry.name):
            continue
        kind = _read(entry / 'type', 32)
        if kind not in ('wlan', 'wifi'):
            continue
        soft, hard = _read(entry / 'soft', 8), _read(entry / 'hard', 8)
        result.append({'name': entry.name, 'soft_blocked': soft == '1' if soft in ('0', '1') else None,
                       'hard_blocked': hard == '1' if hard in ('0', '1') else None})
    return {'status': 'ok', 'radios': result}


def inspect_networkmanager(timeout=3, runner=None):
    """Query local NetworkManager via nmcli, with fixed arguments and a deadline."""
    if runner is None:
        runner = bounded_run
    try:
        completed = runner(['nmcli', '--terse', '--escape', 'yes', '--fields',
                            'DEVICE,TYPE,STATE', 'device', 'status'],
                           capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {'status': 'unavailable', 'devices': {}}
    if completed.returncode != 0:
        return {'status': 'unavailable', 'devices': {}}
    devices = {}
    for line in completed.stdout[:16384].splitlines()[:128]:
        # nmcli escapes colons and backslashes in fields.
        fields = re.split(r'(?<!\\):', line)
        if len(fields) != 3:
            continue
        name, kind, state = (f.replace('\\:', ':') for f in fields)
        if SAFE_IFACE.fullmatch(name) and kind == 'wifi':
            devices[name] = state[:80]
    return {'status': 'ok', 'devices': devices}


def inspect_wifi(root=NET_ROOT, limit=64, rfkill_root=RFKILL_ROOT, nm_runner=None, journal_runner=None):
    """Read only: no scans, connection changes, internet tests, or installations."""
    try:
        entries = sorted(root.iterdir(), key=lambda item: item.name)[:limit]
    except OSError:
        return {'status': 'unavailable', 'interfaces': [], 'installation_enabled': False}
    radios = inspect_rfkill(rfkill_root)
    nm = inspect_networkmanager(runner=nm_runner)
    interfaces = []
    for entry in entries:
        if not SAFE_IFACE.fullmatch(entry.name):
            continue
        try:
            wireless = (entry / 'wireless').is_dir() or (entry / 'phy80211').exists()
        except OSError:
            continue
        if not wireless:
            continue
        try:
            link = entry / 'device' / 'driver'
            driver = link.resolve(strict=True).name if link.is_symlink() else None
        except (OSError, RuntimeError):
            driver = None
        state = _read(entry / 'operstate')
        if state not in STATES:
            state = 'unknown'
        nm_state = nm['devices'].get(entry.name)
        blocked = any(r['hard_blocked'] is True or r['soft_blocked'] is True for r in radios['radios'])
        if blocked:
            assessment = 'radio_block_detected'
        elif nm_state and nm_state.lower().startswith('connected'):
            assessment = 'connected_reported'
        else:
            assessment = 'unable_to_verify'
        interfaces.append({'interface': entry.name, 'operstate': state,
                           'driver': driver, 'networkmanager_state': nm_state,
                           'assessment': assessment, 'firmware_verified': False,
                           'connectivity_verified': False})
    evidence = inspect_wifi_firmware_messages(runner=journal_runner)
    return {'status': 'ok', 'interfaces': interfaces, 'rfkill': radios, 'firmware_messages': evidence,
            'networkmanager_status': nm['status'], 'installation_enabled': False,
            'connectivity_verified': False, 'firmware_verified': False}


def classify_kernel_firmware_line(line):
    """Classify bounded kernel text without treating generic firmware mentions as failures."""
    low = line.lower()
    address = re.search(r"(?<![0-9a-f])(?:[0-9a-f]{4}:)?[0-9a-f]{2}:[0-9a-f]{2}\.[0-7](?![0-9a-f])", low)
    pci = address.group(0) if address else None
    if 'i915' in low and ('fifo underrun' in low or 'pipe underrun' in low):
        return {'kind': 'graphics_warning', 'pci_address': pci, 'driver': 'i915', 'message': line[:240]}
    if 'iwlwifi' in low and 'loaded firmware version' in low:
        return {'kind': 'wifi_firmware_loaded', 'pci_address': pci, 'driver': 'iwlwifi', 'message': line[:240]}
    # A generic "Firmware Bug" or "FW already configured" is not a failed load.
    failure = any(token in low for token in ('direct firmware load', 'failed to load firmware',
        'firmware load failed', 'no suitable firmware', 'firmware file not found'))
    if failure and any(token in low for token in ('iwlwifi', 'brcmfmac', 'ath10k', 'ath11k', 'rtw89', 'wifi', 'wlan')):
        return {'kind': 'wifi_firmware_failure_hint', 'pci_address': pci,
                'driver': 'iwlwifi' if 'iwlwifi' in low else None, 'message': line[:240]}
    return None


def inspect_wifi_firmware_messages(runner=None, timeout=5, max_lines=2000):
    """Inspect current-boot journal only as current user; never elevate privileges."""
    if runner is None:
        runner = bounded_run
    limit = min(max(1, max_lines), 2000)
    try:
        result = runner(['journalctl', '--boot', '0', '--kernel', '--no-pager',
                         '--quiet', '--output=cat', '--lines', str(limit)],
                        capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {'status': 'unavailable', 'events': [], 'failure_hints': [], 'messages_checked': 0,
                'device_match_verified': False}
    stderr = (getattr(result, 'stderr', '') or '')[:2048].lower()
    if result.returncode != 0 or not (result.stdout or '').strip():
        restricted = any(token in stderr for token in ('permission', 'access denied', 'not seeing messages',
                                                       'insufficient privileges'))
        try:
            restricted = restricted or Path('/proc/sys/kernel/dmesg_restrict').read_text().strip() == '1'
        except OSError:
            pass
        return {'status': 'permission_restricted' if restricted else 'unavailable',
                'events': [], 'failure_hints': [], 'messages_checked': 0,
                'device_match_verified': False}
    lines = result.stdout[-262144:].splitlines()[-limit:]
    events = []
    for line in lines:
        event = classify_kernel_firmware_line(line)
        if event and len(events) < 24:
            events.append(event)
    failures = [e['message'] for e in events if e['kind'] == 'wifi_firmware_failure_hint'][:8]
    return {'status': 'ok', 'events': events, 'failure_hints': failures,
            'messages_checked': len(lines), 'scope': 'recent_current_boot_kernel_messages',
            'device_match_verified': False, 'installation_enabled': False}
