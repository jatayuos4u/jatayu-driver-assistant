"""Unprivileged, conservative APT package inspection and simulated previews.

No installs, no root, no shell, no network operations. Package names are fixed.
"""
from dataclasses import dataclass
import re
import subprocess
from .safe_process import bounded_run
from .firmware import FAMILY_PACKAGES

ALLOWED = frozenset(FAMILY_PACKAGES.values())
PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")

@dataclass(frozen=True)
class PackageInfo:
    name: str
    installed: str
    candidate: str
    available: bool
    evidence_count: int


def parse_policy(text):
    installed = re.search(r"^\s*Installed:\s*(\S+)", text, re.M)
    candidate = re.search(r"^\s*Candidate:\s*(\S+)", text, re.M)
    return (installed.group(1) if installed else '(unknown)',
            candidate.group(1) if candidate else '(none)')


def inspect_packages(findings, runner=bounded_run):
    """Show only allowlisted packages supported by observed firmware log evidence."""
    counts = {}
    for item in findings:
        package = item.package_hint
        if package in ALLOWED:
            counts[package] = counts.get(package, 0) + 1
    result = []
    for name in sorted(counts):
        try:
            proc = runner(['apt-cache', 'policy', name], capture_output=True,
                          text=True, timeout=5, check=False)
            installed, candidate = parse_policy(proc.stdout) if proc.returncode == 0 else ('(unknown)', '(none)')
        except (OSError, subprocess.TimeoutExpired):
            installed, candidate = '(unknown)', '(none)'
        result.append(PackageInfo(name, installed, candidate, candidate != '(none)', counts[name]))
    return result


def parse_simulation(text):
    """Summarize apt simulation output, including removals and warnings."""
    changes = []
    for line in text.splitlines():
        if line.startswith(('Inst ', 'Remv ', 'Conf ')):
            changes.append(line[:300])
    return changes[:100]


def simulate_install(name, runner=bounded_run):
    """Simulation only; never execute an actual install."""
    if name not in ALLOWED or not PACKAGE_RE.fullmatch(name):
        raise ValueError('Package is not on the trusted firmware allowlist')
    try:
        proc = runner(['apt-get', '-s', '--no-install-recommends', 'install', '--', name],
                      capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, [], f'Preview unavailable: {type(exc).__name__}'
    if proc.returncode != 0:
        return False, [], (proc.stderr or proc.stdout)[-1500:]
    return True, parse_simulation(proc.stdout), 'Simulation completed. No packages were changed.'


def assess_transaction(changes, requested_package):
    """Conservative policy for simulated APT output; never authorizes execution.

    Unknown or truncated transactions must be reviewed by a human.
    """
    if requested_package not in ALLOWED:
        return False, ['Requested package is not allowlisted']
    if not changes:
        return False, ['Simulation produced no recognized package operations']
    problems = []
    installed = set()
    for line in changes:
        if line.startswith('Remv '):
            problems.append('Package removal detected: ' + line[:120])
        elif line.startswith('Inst '):
            parts = line.split()
            if len(parts) < 2 or not PACKAGE_RE.fullmatch(parts[1]):
                problems.append('Unrecognized installation record')
            else:
                installed.add(parts[1])
        elif not line.startswith('Conf '):
            problems.append('Unrecognized transaction operation')
    if requested_package not in installed:
        problems.append('Requested package not listed for installation (may already be installed)')
    if len(changes) >= 100:
        problems.append('Transaction preview may be truncated')
    return not problems, problems


def preview_plan(name, runner=bounded_run):
    """Produce an explainable, unprivileged plan. Does not execute APT changes."""
    ok, changes, message = simulate_install(name, runner=runner)
    safe, issues = assess_transaction(changes, name) if ok else (False, [message])
    return {
        'package': name,
        'simulation_ok': ok,
        'changes': changes,
        'review_passed': safe,
        'warnings': issues,
        'installation_enabled': False,
    }


def validate_package_request(package, evidence_packages):
    """Unprivileged policy gate for a future backend protocol (NOT authorization).

    This check is advisory only; any privileged service must independently
    validate fresh evidence, repository trust and complete transaction details.
    """
    if not isinstance(package, str) or package not in ALLOWED or not PACKAGE_RE.fullmatch(package):
        return False, 'Package is not on the fixed firmware allowlist'
    if not isinstance(evidence_packages, (list, tuple, frozenset)):
        return False, 'Invalid evidence container'
    if package not in evidence_packages:
        return False, 'No recognized firmware evidence for this package'
    return True, 'Advisory evidence match only; no installation authorization'
