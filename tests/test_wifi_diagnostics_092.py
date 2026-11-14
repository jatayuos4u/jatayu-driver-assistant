from types import SimpleNamespace
from jatayu_driver_assistant.wifi_diagnostics import inspect_wifi_firmware_messages

def test_detects_failure_without_device_claim():
    def runner(*args, **kwargs):
        assert args[0][:3] == ['journalctl', '--boot', '0']
        return SimpleNamespace(returncode=0, stdout='iwlwifi: Direct firmware load for x failed with error -2\n')
    result = inspect_wifi_firmware_messages(runner=runner)
    assert len(result['failure_hints']) == 1
    assert result['device_match_verified'] is False

def test_unavailable_is_not_healthy():
    def runner(*args, **kwargs):
        raise FileNotFoundError()
    assert inspect_wifi_firmware_messages(runner=runner)['status'] == 'unavailable'

def test_no_match_is_not_verified():
    def runner(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout='iwlwifi: loaded firmware version 1\n')
    result = inspect_wifi_firmware_messages(runner=runner)
    assert result['failure_hints'] == []
    assert result['device_match_verified'] is False
