from jatayu_driver_assistant.scanner import Device
from jatayu_driver_assistant.recommendation_view import build_advice, counts, short_name


def test_virtual_network_excluded():
    devices = [Device('Ethernet', 'lxcbr0', 'Network', 'lxcbr0'),
               Device('Wi-Fi', 'Intel Wireless', 'PCI', '0000:02:00.0', 'iwlwifi')]
    items = build_advice(devices)
    assert len(items) == 1
    assert items[0].status == 'working'


def test_no_driver_is_not_automatically_missing_firmware():
    devices = [Device('USB', 'USB camera', 'USB', '1234:5678'),
               Device('Graphics', 'Display controller', 'PCI', '0000:00:02.0')]
    items = build_advice(devices)
    assert counts(items) == {'attention': 1, 'working': 0, 'unknown': 1}
    assert not any('install' in x.explanation.lower() for x in items)


def test_short_audio_name_preserves_full_name():
    name = 'Audio device [0403]: Intel Corporation High Definition Audio Controller [8086:2284] (rev 35)'
    item = build_advice([Device('Audio', name, 'PCI', '0000:00:1b.0', 'snd_hda_intel')])[0]
    assert item.name == 'HD Audio Controller'
    assert item.full_name == name
