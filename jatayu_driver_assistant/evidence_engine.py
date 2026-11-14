"""Read-only kernel firmware evidence correlation. Correlation is NOT proof of package need."""
import re
import subprocess
from dataclasses import asdict, dataclass
from .firmware import parse_firmware_failures

BDF = re.compile(r"(?<![0-9a-fA-F])(?:[0-9a-fA-F]{4}:)?[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7](?![0-9a-fA-F])")
MAX_CHARS = 2_000_000

@dataclass(frozen=True)
class DeviceEvidence:
    address: str
    status: str
    messages: tuple[str, ...]
    package_hint: str | None
    verified: bool = False

    def to_dict(self):
        return asdict(self)


def correlate(hints, log_text):
    """Associate explicit failed firmware loads with an exact BDF and matching driver family.

    A log line alone is untrusted evidence; never enable device APT or installation.
    """
    failures = parse_firmware_failures(log_text[-MAX_CHARS:])
    results = []
    for hint in hints:
        matched = []
        for message, family, package in failures:
            addresses = {x.lower() for x in BDF.findall(message)}
            normalized = {x if len(x) == 12 else '0000:' + x for x in addresses}
            if hint.address.lower() not in normalized:
                continue
            # Do not infer a package from BDF alone; the driver family must agree.
            if not family or not hint.driver or not hint.driver.lower().startswith(family):
                continue
            matched.append(message[:400])
        results.append(DeviceEvidence(hint.address,
            'correlated_unverified' if matched else 'no_correlated_failure',
            tuple(matched[:5]), hint.package_hint if matched else None))
    return results


def inspect_evidence(hints, runner=subprocess.run):
    """Read current-boot kernel journal, fail closed if inaccessible."""
    try:
        result = runner(['journalctl', '-k', '-b', '--no-pager', '-o', 'cat', '-n', '4000'],
                        capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return [], 'unavailable'
    if result.returncode != 0:
        return [], 'unavailable'
    return correlate(hints, result.stdout), 'available'
