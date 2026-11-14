from jatayu_driver_assistant.recommendations import validate_package_request

def test_valid_evidence_match():
    assert validate_package_request('firmware-realtek', ['firmware-realtek'])[0]

def test_evidence_absent():
    assert not validate_package_request('firmware-realtek', [])[0]

def test_unknown_package():
    assert not validate_package_request('not-a-real-driver', ['not-a-real-driver'])[0]

def test_injection_rejected():
    assert not validate_package_request('firmware-realtek; reboot', ['firmware-realtek; reboot'])[0]

def test_invalid_evidence_container():
    assert not validate_package_request('firmware-realtek', 'firmware-realtek')[0]
