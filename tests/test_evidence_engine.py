from types import SimpleNamespace
from jatayu_driver_assistant.evidence_engine import correlate, inspect_evidence


def hint(address='0000:00:14.3', driver='iwlwifi'):
    return SimpleNamespace(address=address, driver=driver, package_hint='firmware-iwlwifi')


def test_exact_device_and_driver_correlation():
    line = 'iwlwifi 0000:00:14.3: failed to load firmware iwlwifi-demo.ucode'
    result = correlate([hint()], line)[0]
    assert result.status == 'correlated_unverified'
    assert result.verified is False


def test_wrong_device_does_not_correlate():
    line = 'iwlwifi 0000:00:14.2: failed to load firmware iwlwifi-demo.ucode'
    assert correlate([hint()], line)[0].status == 'no_correlated_failure'


def test_wrong_driver_does_not_correlate():
    line = 'iwlwifi 0000:00:14.3: failed to load firmware iwlwifi-demo.ucode'
    assert correlate([hint(driver='ath10k_pci')], line)[0].status == 'no_correlated_failure'


def test_successful_load_does_not_correlate():
    line = 'iwlwifi 0000:00:14.3: loaded firmware version 90'
    assert correlate([hint()], line)[0].status == 'no_correlated_failure'


def test_no_address_does_not_correlate():
    line = 'iwlwifi: failed to load firmware iwlwifi-demo.ucode'
    assert correlate([hint()], line)[0].status == 'no_correlated_failure'


def test_journal_denied_fails_closed():
    def denied(*args, **kwargs):
        return SimpleNamespace(returncode=1, stdout='')
    assert inspect_evidence([hint()], denied) == ([], 'unavailable')


def test_journal_timeout_fails_closed():
    import subprocess
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired('journalctl', 5)
    assert inspect_evidence([hint()], timeout) == ([], 'unavailable')
