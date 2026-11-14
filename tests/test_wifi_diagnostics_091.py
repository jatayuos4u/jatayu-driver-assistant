from types import SimpleNamespace
from jatayu_driver_assistant.wifi_diagnostics import inspect_wifi, inspect_rfkill, inspect_networkmanager


def fake_nm(*args, **kwargs):
    assert args[0][-2:] == ['device', 'status']
    return SimpleNamespace(returncode=0, stdout='wlan0:wifi:connected\neth0:ethernet:connected\n')


def test_connected_is_not_internet_verified(tmp_path):
    net = tmp_path / 'net'
    (net / 'wlan0' / 'wireless').mkdir(parents=True)
    (net / 'wlan0' / 'operstate').write_text('up')
    result = inspect_wifi(net, rfkill_root=tmp_path / 'absent', nm_runner=fake_nm)
    assert result['interfaces'][0]['assessment'] == 'connected_reported'
    assert result['interfaces'][0]['connectivity_verified'] is False
    assert result['installation_enabled'] is False


def test_wifi_radio_block(tmp_path):
    rf = tmp_path / 'rfkill0'
    rf.mkdir()
    (rf / 'type').write_text('wlan')
    (rf / 'soft').write_text('1')
    (rf / 'hard').write_text('0')
    assert inspect_rfkill(tmp_path)['radios'][0]['soft_blocked'] is True


def test_networkmanager_unavailable():
    def fail(*args, **kwargs):
        raise FileNotFoundError()
    assert inspect_networkmanager(runner=fail)['status'] == 'unavailable'
