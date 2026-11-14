import json
from dataclasses import asdict
from jatayu_driver_assistant.hardware_compat import classify_pci, inspect_pci, report_payload


def test_categories():
    assert classify_pci('0x030000') == 'graphics'
    assert classify_pci('0x028000') == 'network'
    assert classify_pci('0x010601') == 'storage'
    assert classify_pci('0x040300') == 'multimedia'
    assert classify_pci('0x0c0330') == 'controller'
    assert classify_pci('bad') == 'other'


def test_report_is_explicitly_read_only(tmp_path):
    pci = tmp_path / '0000:01:00.0'
    pci.mkdir()
    (pci / 'vendor').write_text('0x1002')
    (pci / 'device').write_text('0x1234')
    (pci / 'class').write_text('0x030000')
    hints = inspect_pci(tmp_path)
    payload = report_payload(hints)
    assert payload['installation_enabled'] is False
    assert payload['hardware_match_verified'] is False
    assert payload['source'] == 'local_pci_sysfs_read_only'
    assert payload['devices'][0]['category'] == 'graphics'
    assert payload['devices'][0]['confidence'] == 'low'
    assert json.loads(json.dumps(payload)) == payload


def test_symlink_escape_is_not_followed_for_test_roots(tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    for name, value in [('vendor','0x1002'),('device','0x1234'),('class','0x030000')]:
        (outside / name).write_text(value)
    root = tmp_path / 'pci'
    root.mkdir()
    (root / '0000:01:00.0').symlink_to(outside, target_is_directory=True)
    assert inspect_pci(root) == []


def test_missing_and_malformed_evidence_not_exported(tmp_path):
    pci = tmp_path / '0000:01:00.0'
    pci.mkdir()
    (pci / 'vendor').write_text('0x1002')
    (pci / 'device').write_text('0x1234')
    (pci / 'class').write_text('0xBAD')
    assert report_payload(inspect_pci(tmp_path))['devices'] == []


def test_gui_source_contains_filters_and_export():
    from pathlib import Path
    text = (Path(__file__).parents[1] / 'jatayu_driver_assistant' / 'app.py').read_text()
    assert 'self.hardware_filter' in text
    assert 'self.hardware_search' in text
    assert 'self.hardware_table' in text
    assert 'report_payload(self.hardware_hints)' in text
