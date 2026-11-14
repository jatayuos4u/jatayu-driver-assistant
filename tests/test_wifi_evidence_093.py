from types import SimpleNamespace
from jatayu_driver_assistant.wifi_diagnostics import classify_kernel_firmware_line, inspect_wifi_firmware_messages


def test_loaded_firmware():
    event = classify_kernel_firmware_line('iwlwifi 0000:02:00.0: loaded firmware version 29.x 7265D-29.ucode')
    assert event['kind'] == 'wifi_firmware_loaded'
    assert event['pci_address'] == '0000:02:00.0'


def test_graphics_is_not_wifi_failure():
    event = classify_kernel_firmware_line('i915 0000:00:02.0: [drm] *ERROR* CPU pipe A FIFO underrun')
    assert event['kind'] == 'graphics_warning'


def test_generic_firmware_bug_not_failure():
    assert classify_kernel_firmware_line('wmi_bus: [Firmware Bug]: WMBF method missing') is None
    assert classify_kernel_firmware_line('iwlwifi 0000:02:00.0: FW already configured (0)') is None


def test_failed_firmware_hint():
    event = classify_kernel_firmware_line('iwlwifi 0000:02:00.0: failed to load firmware')
    assert event['kind'] == 'wifi_firmware_failure_hint'


def test_restricted_journal(monkeypatch):
    monkeypatch.setattr('jatayu_driver_assistant.wifi_diagnostics.Path.read_text', lambda *a, **kw: '1')
    runner = lambda *a, **kw: SimpleNamespace(returncode=1, stdout='', stderr='Permission denied')
    report = inspect_wifi_firmware_messages(runner=runner)
    assert report['status'] == 'permission_restricted'


def test_successful_journal():
    runner = lambda *a, **kw: SimpleNamespace(returncode=0, stdout='iwlwifi 0000:02:00.0: loaded firmware version 29.x\n', stderr='')
    report = inspect_wifi_firmware_messages(runner=runner)
    assert report['status'] == 'ok'
    assert report['events'][0]['kind'] == 'wifi_firmware_loaded'
    assert not report['installation_enabled']
