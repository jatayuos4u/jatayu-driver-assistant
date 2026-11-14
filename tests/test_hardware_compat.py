from pathlib import Path
from jatayu_driver_assistant.hardware_compat import inspect_pci


def device(root, addr, vendor, dev, cls):
    p = root / addr
    p.mkdir()
    for name, value in [('vendor', vendor), ('device', dev), ('class', cls)]:
        (p / name).write_text(value)


def test_amd_graphics_low_confidence(tmp_path):
    device(tmp_path, '0000:01:00.0', '0x1002', '0x1234', '0x030000')
    result = inspect_pci(tmp_path)
    assert len(result) == 1
    assert result[0].package_hint == 'firmware-amd-graphics'
    assert result[0].confidence == 'low'
    assert not result[0].driver


def test_unmapped_device_never_claims_match(tmp_path):
    device(tmp_path, '0000:02:00.0', '0x1234', '0x5678', '0x020000')
    result = inspect_pci(tmp_path)
    assert result[0].package_hint is None
    assert result[0].confidence == 'insufficient'


def test_malformed_sysfs_values_ignored(tmp_path):
    device(tmp_path, '0000:02:00.0', 'garbage', '0x5678', '0x020000')
    assert inspect_pci(tmp_path) == []


def test_empty_sysfs(tmp_path):
    assert inspect_pci(tmp_path) == []


def test_no_shell_or_installation_api():
    import inspect
    from jatayu_driver_assistant import hardware_compat
    source = inspect.getsource(hardware_compat)
    assert 'subprocess' not in source
    assert 'apt-get' not in source
