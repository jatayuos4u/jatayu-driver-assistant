from jatayu_driver_assistant.scanner import Device
from jatayu_driver_assistant.diagnostics import analyze

def test_unbound_pci_is_review_not_confirmed_failure():
    findings = analyze([Device('Graphics', 'Example', 'PCI', '0000:00:02.0')])
    assert findings[0].severity == 'review'
    assert 'does not prove' in findings[0].explanation

def test_virtual_interface_is_informational():
    findings = analyze([Device('Ethernet', 'lxcbr0', 'Network', 'lxcbr0')])
    assert findings[0].severity == 'info'
    assert 'No repair' in findings[0].next_step

def test_bound_device_not_flagged():
    findings = analyze([Device('Wi-Fi', 'Adapter', 'PCI', '0000:01:00.0', driver='iwlwifi')])
    assert len(findings) == 1
    assert findings[0].severity == 'info'

def test_report_findings_serializable():
    import json
    json.dumps([f.as_dict() for f in analyze([])])
