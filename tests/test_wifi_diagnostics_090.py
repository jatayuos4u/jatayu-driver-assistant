from jatayu_driver_assistant.wifi_diagnostics import inspect_wifi


def test_wifi_interface(tmp_path):
    dev = tmp_path / 'wlan0'
    (dev / 'wireless').mkdir(parents=True)
    (dev / 'operstate').write_text('down\n')
    result = inspect_wifi(tmp_path)
    assert result['interfaces'][0]['interface'] == 'wlan0'
    assert result['interfaces'][0]['operstate'] == 'down'
    assert result['interfaces'][0]['firmware_verified'] is False
    assert result['installation_enabled'] is False


def test_ethernet_not_misclassified(tmp_path):
    dev = tmp_path / 'eth0'
    dev.mkdir()
    (dev / 'operstate').write_text('up\n')
    assert inspect_wifi(tmp_path)['interfaces'] == []


def test_missing_root_fails_closed(tmp_path):
    result = inspect_wifi(tmp_path / 'missing')
    assert result['status'] == 'unavailable'
    assert result['installation_enabled'] is False


def test_bad_interface_name_ignored(tmp_path):
    dev = tmp_path / 'invalid interface'
    (dev / 'wireless').mkdir(parents=True)
    assert inspect_wifi(tmp_path)['interfaces'] == []
