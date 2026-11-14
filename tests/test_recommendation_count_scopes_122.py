from types import SimpleNamespace
from jatayu_driver_assistant.recommendation_view import build_advice, counts

def device(bus, driver, name="Device", category="Other"):
    return SimpleNamespace(bus=bus, driver=driver, name=name, category=category, identifier="id")

def test_filtered_counts_differ_from_overview_by_design():
    devices = [device("PCI", "i915", "GPU", "Graphics"), device("USB", "snd", "Audio", "Audio"), device("Network", "bridge", "lxcbr0", "Ethernet")]
    items = build_advice(devices)
    assert len(devices) == 3
    assert sum(bool(d.driver) for d in devices) == 3
    assert counts(items)["working"] == 2
    assert len(items) == 2

def test_unknown_usb_remains_visible():
    items = build_advice([device("USB", "", "USB gadget", "Other")])
    assert counts(items)["unknown"] == 1
