from jatayu_driver_assistant.hardware_compat import HardwareHint, report_payload


def test_low_confidence_hint_cannot_enable_apt():
    h = HardwareHint('0000:01:00.0', '0x1002', '0x1234', '0x030000', '',
                     'firmware-amd-graphics', 'low', 'Vendor hint', 'graphics')
    data = report_payload([h])
    assert data['device_specific_apt_enabled'] is False
    assert data['devices'][0]['recommendation_status'] == 'no_verified_recommendation'
    assert data['devices'][0]['device_specific_apt_enabled'] is False


def test_empty_hardware_report_still_fails_closed():
    data = report_payload([])
    assert data['recommendation_policy'] == 'fail_closed'
    assert data['hardware_match_verified'] is False


def test_gui_requires_verified_evidence():
    from pathlib import Path
    source = (Path(__file__).parents[1] / 'jatayu_driver_assistant' / 'app.py').read_text()
    assert 'self.hardware_device_apt.setEnabled(False)' in source
    assert 'No verified firmware recommendation' in source
    assert 'Generic APT package check (not a hardware recommendation)' in source
