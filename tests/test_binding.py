from jatayu_driver_assistant.scanner import Device, binding_state, summarize

def test_unbound_pci_not_silently_healthy():
    d = Device('Graphics', 'GPU', 'PCI', '0000:00:02.0')
    assert binding_state(d) == 'unbound'

def test_usb_without_driver_not_automatically_missing():
    d = Device('USB', 'Hub', 'USB', '1234:abcd')
    assert binding_state(d) == 'unknown'

def test_counts_partition_devices():
    ds = [Device('Other', 'A', 'PCI', '1', 'xhci_hcd'),
          Device('Other', 'B', 'PCI', '2'),
          Device('USB', 'C', 'USB', '3')]
    assert summarize(ds) == {'detected': 3, 'bound': 1, 'unbound': 1, 'unknown': 1}

def test_translations_for_states():
    from jatayu_driver_assistant.i18n import tr
    assert tr('hi', 'unbound') != 'unbound'
    assert tr('en', 'unknown_status') == 'Binding unknown'
