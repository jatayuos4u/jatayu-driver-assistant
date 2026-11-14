"""Unprivileged, bounded APT simulation. Informational only; never installs."""
from dataclasses import dataclass, asdict
import re
import subprocess
from .recommendations import ALLOWED, PACKAGE_RE

MAX_OUTPUT = 65536
MAX_LINES = 500
OP = re.compile(r"^(Inst|Conf|Remv) ([a-z0-9][a-z0-9+.-]*)(?:\s|$)")

@dataclass(frozen=True)
class AptPreview:
    package: str
    status: str
    operations: tuple[str, ...]
    warnings: tuple[str, ...]
    returncode: int | None
    installation_enabled: bool = False

    def to_dict(self):
        result = asdict(self)
        result['operations'] = list(self.operations)
        result['warnings'] = list(self.warnings)
        return result


def analyze_output(package, output, returncode):
    """Fail closed on malformed, truncated, or surprising APT output."""
    warnings, operations = [], []
    if not isinstance(output, str) or len(output.encode('utf-8')) > MAX_OUTPUT:
        return AptPreview(package, 'blocked', (), ('APT output missing or too large',), returncode)
    lines = output.splitlines()
    if len(lines) > MAX_LINES:
        warnings.append('APT output exceeds line limit')
    if returncode != 0:
        warnings.append('APT simulation failed')
    if re.search(r'(?im)^(?:E:|Err:|WARNING:|The following packages will be REMOVED:)', output):
        warnings.append('APT reported an error, warning, or removal')
    for line in lines[:MAX_LINES]:
        if line.startswith(('Inst ', 'Conf ', 'Remv ')):
            m = OP.match(line)
            if not m:
                warnings.append('Unrecognized operation format')
                continue
            kind, name = m.groups()
            if not PACKAGE_RE.fullmatch(name):
                warnings.append('Invalid package identifier')
            if kind == 'Remv':
                warnings.append('Package removal proposed')
            if kind == 'Inst' and name not in ALLOWED:
                warnings.append('Non-allowlisted package in proposed changes')
            operations.append(line[:300])
    if not operations:
        warnings.append('No package operations found (possibly already installed)')
    if not any(OP.match(line) and OP.match(line).groups() == ('Inst', package) for line in operations):
        warnings.append('Requested package not scheduled for installation')
    warnings.append('Live APT simulation is not verified hardware evidence or installation approval')
    return AptPreview(package, 'blocked' if len(warnings) > 1 else 'review_required',
                      tuple(operations), tuple(dict.fromkeys(warnings)), returncode)


def installed_version(package, *, runner=subprocess.run):
    """Query local dpkg database only; unknown results never imply absence."""
    if not isinstance(package, str) or package not in ALLOWED or not PACKAGE_RE.fullmatch(package):
        raise ValueError('Package is not allowlisted')
    try:
        proc = runner(['/usr/bin/dpkg-query', '-W', '-f=${Status}\t${Version}\n', '--', package],
                      shell=False, capture_output=True, text=True, timeout=5, check=False,
                      env={'PATH':'/usr/bin:/bin', 'LC_ALL':'C'})
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return 'unknown', None
    if proc.returncode == 1:
        return 'not_installed', None
    if proc.returncode != 0 or len(proc.stdout) > 512:
        return 'unknown', None
    line = proc.stdout.strip().split('\t')
    if len(line) == 2 and line[0] == 'install ok installed' and line[1]:
        return 'installed', line[1]
    return 'unknown', None


def inspect_package(package, *, runner=subprocess.run, dpkg_runner=subprocess.run):
    """Combine local dpkg status with simulation; never infer a hardware requirement."""
    state, version = installed_version(package, runner=dpkg_runner)
    preview = simulate_package(package, runner=runner)
    data = preview.to_dict()
    data['installed_state'] = state
    data['installed_version'] = version
    if state == 'installed' and preview.returncode == 0 and not preview.operations:
        data['status'] = 'already_installed'
        data['warnings'] = ['Package is already installed; no APT changes proposed',
                            'Installed package does not prove hardware needs or uses it']
    elif state == 'unknown':
        data['warnings'].append('Installed package state could not be verified')
    return data


def simulate_package(package, *, timeout=15, runner=subprocess.run):
    """Run apt-get simulation without privilege, shell, or arbitrary arguments."""
    if not isinstance(package, str) or package not in ALLOWED or not PACKAGE_RE.fullmatch(package):
        raise ValueError('Package is not allowlisted')
    if not isinstance(timeout, (int, float)) or not 1 <= timeout <= 30:
        raise ValueError('Invalid timeout')
    cmd = ['/usr/bin/apt-get', '-s', '-o', 'Debug::NoLocking=1', 'install', '--', package]
    try:
        result = runner(cmd, shell=False, capture_output=True, text=True,
                        timeout=timeout, check=False, env={'PATH':'/usr/bin:/bin', 'LC_ALL':'C'})
    except (subprocess.TimeoutExpired, OSError, UnicodeError):
        return AptPreview(package, 'blocked', (), ('APT simulation timed out or could not start',), None)
    return analyze_output(package, result.stdout + '\n' + result.stderr, result.returncode)
