from jatayu_driver_assistant.service_protocol import DisabledRepairService

service = DisabledRepairService()

def test_capabilities_fail_closed():
    assert service.get_capabilities()['installation_enabled'] is False
    assert service.get_capabilities()['polkit_enabled'] is False

def test_unknown_package_blocked():
    assert service.request_installation('bash', '0000:00:14.3', 'a'*64).state == 'blocked'

def test_allowlisted_package_still_blocked():
    assert service.request_installation('firmware-iwlwifi', '0000:00:14.3', 'a'*64).installation_enabled is False

def test_oversized_input_blocked():
    assert 'oversized' in service.request_installation('a'*10000, '0000:00:14.3', 'a'*64).message

def test_reinstall_blocked():
    assert service.request_reinstallation('firmware-iwlwifi', '0000:00:14.3', 'a'*64).state == 'blocked'
