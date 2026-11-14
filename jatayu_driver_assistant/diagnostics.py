"""Evidence-based, read-only diagnostics. No driver installation or shell execution."""
from dataclasses import dataclass, asdict
from .scanner import binding_state

@dataclass(frozen=True)
class Finding:
    severity: str
    title: str
    explanation: str
    next_step: str
    identifier: str = ''

    def as_dict(self):
        return asdict(self)


def analyze(devices):
    """Never equate an absent binding with a broken or missing driver."""
    findings = []
    for device in devices:
        state = binding_state(device)
        if state == 'unbound':
            findings.append(Finding(
                'review', 'PCI device without a bound kernel driver',
                f'{device.name} ({device.identifier}) has no driver binding in sysfs. '
                'This can be normal; it does not prove a driver is missing.',
                'Check whether the device works. If not, review kernel logs and supported Debian firmware packages.',
                device.identifier))
        elif state == 'unknown' and device.bus == 'Network':
            findings.append(Finding(
                'info', 'Network interface binding not determined',
                f'{device.name} has no directly associated kernel module. Virtual bridges, tunnels and '
                'other software interfaces commonly work this way.',
                'No repair is recommended based on this finding alone.', device.identifier))
    if not findings:
        findings.append(Finding(
            'info', 'No obvious driver-binding concerns detected',
            'This scan did not find unbound PCI devices. This does not verify firmware integrity, '
            'device functionality or package health.',
            'If hardware is malfunctioning, use device-specific troubleshooting.'))
    return findings
