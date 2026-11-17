"""Conservative, unprivileged firmware evidence and Debian package availability.

Never treats a kernel log line as proof that a package will fix a device.
No installation, shell invocation, or third-party downloads.
"""
from dataclasses import dataclass, asdict
import re
import subprocess
from .safe_process import bounded_run

# Only standard Debian firmware packages. These are hints, not automatic matches.
FAMILY_PACKAGES = {
    'iwlwifi': 'firmware-iwlwifi',
    'ath10k': 'firmware-atheros',
    'ath11k': 'firmware-atheros',
    'ath12k': 'firmware-atheros',
    'brcm': 'firmware-brcm80211',
    'brcmfmac': 'firmware-brcm80211',
    'rtl': 'firmware-realtek',
    'rtw': 'firmware-realtek',
    'amdgpu': 'firmware-amd-graphics',
    'radeon': 'firmware-amd-graphics',
    'mt76': 'firmware-mediatek',
    'mt79': 'firmware-mediatek',
}
MAX_LINES = 4000

@dataclass(frozen=True)
class FirmwareEvidence:
    message: str
    family: str
    package_hint: str
    package_available: bool
    def as_dict(self):
        return asdict(self)


def parse_firmware_failures(log_text):
    """Only explicit firmware load failures; never report successful loads as faults."""
    result = []
    seen = set()
    for raw in log_text.splitlines()[-MAX_LINES:]:
        line = raw.strip()[:400]
        lower = line.lower()
        if not ('firmware' in lower and (
            re.search(r'failed to (?:load|request|fetch) firmware', lower) or
            re.search(r'firmware.*(?:not found|missing|failed to load|error -2)', lower)
        )):
            continue
        if line in seen:
            continue
        seen.add(line)
        family = next((name for name in FAMILY_PACKAGES if re.search(r'(?<![a-z0-9])'+re.escape(name), lower)), '')
        result.append((line, family, FAMILY_PACKAGES.get(family, '')))
    return result[:30]


def package_available(package, runner=bounded_run):
    """Check only an internally selected Debian package name, not arbitrary input."""
    if package not in set(FAMILY_PACKAGES.values()):
        return False
    try:
        proc = runner(['apt-cache', 'policy', package], capture_output=True, text=True,
                      timeout=3, check=False)
        return proc.returncode == 0 and bool(re.search(r'^\s*Candidate:\s*(?!\(none\))\S+', proc.stdout, re.M))
    except (OSError, subprocess.TimeoutExpired):
        return False


def inspect_firmware(runner=bounded_run):
    """Read kernel journal without privileges; return reason if access is denied."""
    try:
        proc = runner(['journalctl', '-k', '-b', '--no-pager', '-o', 'cat', '-n', str(MAX_LINES)],
                      capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return [], 'Kernel log unavailable or timed out; no conclusion can be drawn.'
    if proc.returncode != 0:
        return [], 'Kernel log access unavailable. This is not evidence that firmware is healthy.'
    lines = parse_firmware_failures(proc.stdout)
    cache = {}
    for _, _, package in lines:
        if package and package not in cache:
            cache[package] = package_available(package, runner)
    findings = [FirmwareEvidence(message, family, package, cache.get(package, False))
                for message, family, package in lines]
    return findings, ('Potential firmware load failures found.' if findings else
                      'No explicit firmware-load failures in accessible recent kernel messages; hardware is not fully verified.')
