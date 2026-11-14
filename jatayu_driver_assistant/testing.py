"""Synthetic fixtures for GUI demonstrations. Never inspect or modify real drivers."""
from dataclasses import dataclass, asdict
from .firmware import parse_firmware_failures

SCENARIOS = {
    'wifi': ('Wi-Fi firmware unavailable', 'iwlwifi 0000:00:14.3: failed to load firmware iwlwifi-demo.ucode'),
    'graphics': ('Graphics firmware unavailable', 'amdgpu 0000:01:00.0: firmware demo.bin not found'),
    'healthy': ('No errors in synthetic log', 'iwlwifi 0000:00:14.3: firmware loaded successfully'),
}


def run_scenario(scenario):
    if scenario not in SCENARIOS:
        raise ValueError('Unknown test scenario')
    title, log = SCENARIOS[scenario]
    findings = parse_firmware_failures(log)
    return {
        'synthetic': True,
        'scenario': scenario,
        'title': title,
        'log': log,
        'findings': [{'message': msg, 'family': family, 'package_hint': pkg} for msg, family, pkg in findings],
        'result': 'Synthetic firmware error recognized' if findings else 'No synthetic firmware error recognized',
        'installation_enabled': False,
        'hardware_modified': False,
    }
