from types import SimpleNamespace
from jatayu_driver_assistant.firmware import parse_firmware_failures, package_available, inspect_firmware


def fake_runner(argv, **kwargs):
    if argv[0] == 'journalctl':
        return SimpleNamespace(returncode=0, stdout='iwlwifi 0000:00:14.3: failed to load firmware iwlwifi-test.ucode\n')
    return SimpleNamespace(returncode=0, stdout='firmware-iwlwifi:\n  Candidate: 20250410-2\n')


def test_detects_explicit_failure():
    assert parse_firmware_failures('iwlwifi: failed to load firmware abc.ucode')[0][1] == 'iwlwifi'


def test_ignores_successful_load():
    assert parse_firmware_failures('iwlwifi: loaded firmware version 12') == []


def test_no_arbitrary_package_queries():
    assert not package_available('evil; rm -rf /', fake_runner)


def test_known_candidate():
    assert package_available('firmware-iwlwifi', fake_runner)


def test_inaccessible_logs_are_unknown():
    def denied(argv, **kwargs):
        return SimpleNamespace(returncode=1, stdout='', stderr='Permission denied')
    evidence, note = inspect_firmware(denied)
    assert not evidence and 'unavailable' in note


def test_evidence_hint_not_claimed_as_fix():
    evidence, note = inspect_firmware(fake_runner)
    assert evidence[0].package_hint == 'firmware-iwlwifi'
    assert evidence[0].package_available
