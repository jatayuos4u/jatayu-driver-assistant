from types import SimpleNamespace
import pytest
from jatayu_driver_assistant.recommendations import (parse_policy, inspect_packages, simulate_install, parse_simulation)
from jatayu_driver_assistant.firmware import FirmwareEvidence

def fake_runner(args, **kwargs):
    if args[:2] == ['apt-cache', 'policy']:
        return SimpleNamespace(returncode=0, stdout='Installed: (none)\nCandidate: 2025.01-1\n', stderr='')
    return SimpleNamespace(returncode=0, stdout='Inst firmware-realtek (2025.01-1 Debian:13/stable [all])\nConf firmware-realtek (2025.01-1 Debian:13/stable [all])\n', stderr='')

def test_policy():
    assert parse_policy('Installed: (none)\n Candidate: 1.0\n') == ('(none)', '1.0')

def test_no_evidence_no_recommendations():
    assert inspect_packages([], runner=fake_runner) == []

def test_allowlisted_evidence():
    evidence = [FirmwareEvidence('failed to load firmware', 'rtl', 'firmware-realtek', True)]
    result = inspect_packages(evidence, runner=fake_runner)
    assert len(result) == 1 and result[0].available

def test_untrusted_package_not_suggested():
    evidence = [FirmwareEvidence('x', 'x', 'evil-package', True)]
    assert inspect_packages(evidence, runner=fake_runner) == []

def test_simulation_only():
    ok, changes, _ = simulate_install('firmware-realtek', runner=fake_runner)
    assert ok and len(changes) == 2

def test_reject_arbitrary_command():
    with pytest.raises(ValueError):
        simulate_install('firmware-realtek; rm -rf /', runner=fake_runner)

def test_parse_changes():
    assert parse_simulation('Inst a\nRemv b\nConf a\n') == ['Inst a', 'Remv b', 'Conf a']
