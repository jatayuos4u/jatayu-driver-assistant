from pathlib import Path
from jatayu_driver_assistant.scanner import pci_category, scan_all, scan_usb, Device
from jatayu_driver_assistant.i18n import tr

def test_categories():
    assert pci_category('VGA compatible controller: Intel') == 'Graphics'
    assert pci_category('Network controller: Realtek Wireless') == 'Wi-Fi'
    assert pci_category('Ethernet controller: Intel') == 'Ethernet'

def test_missing_sysfs(tmp_path):
    assert scan_all(tmp_path) == []

def test_usb_device(tmp_path):
    item = tmp_path / 'bus/usb/devices/1-1'
    item.mkdir(parents=True)
    (item / 'idVendor').write_text('1234\n')
    (item / 'idProduct').write_text('abcd\n')
    (item / 'product').write_text('Test Adapter\n')
    devices = scan_usb(tmp_path)
    assert len(devices) == 1
    assert devices[0].identifier == '1234:abcd'
    assert devices[0].name == 'Test Adapter'

def test_translations():
    assert tr('hi', 'scan') == 'हार्डवेयर जाँचें'
    assert tr('en', 'scan') == 'Scan hardware'

def test_device_serialization():
    assert Device('USB', 'Sample', 'USB', '1234:abcd').as_dict()['category'] == 'USB'
