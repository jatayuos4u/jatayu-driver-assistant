from jatayu_driver_assistant.backend_contract import (RepairRequest, Decision, validate_request, review_simulation, capabilities)

DEVICE = '0000:00:14.3'
EVIDENCE = 'a'*64

def req(package='firmware-iwlwifi', device=DEVICE, evidence=EVIDENCE):
    return RepairRequest(package, device, evidence)

def test_valid_request_requires_review():
    r = validate_request(req(), evidence_packages=['firmware-iwlwifi'])
    assert r.decision == Decision.REVIEW and not r.installation_enabled

def test_unknown_package_blocked():
    assert validate_request(req('bash'), evidence_packages=['bash']).decision == Decision.BLOCKED

def test_bad_device_blocked():
    assert validate_request(req(device='; reboot'), evidence_packages=['firmware-iwlwifi']).decision == Decision.BLOCKED

def test_bad_evidence_blocked():
    assert validate_request(req(evidence='fake'), evidence_packages=['firmware-iwlwifi']).decision == Decision.BLOCKED

def test_missing_evidence_blocked():
    assert validate_request(req()).decision == Decision.BLOCKED

def test_removal_blocked():
    r = review_simulation(req(), ['Remv linux-image-amd64', 'Inst firmware-iwlwifi (1)'], evidence_packages=['firmware-iwlwifi'])
    assert r.decision == Decision.BLOCKED

def test_clean_preview_still_cannot_install():
    r = review_simulation(req(), ['Inst firmware-iwlwifi (1)', 'Conf firmware-iwlwifi (1)'], evidence_packages=['firmware-iwlwifi'])
    assert r.decision == Decision.REVIEW and not r.installation_enabled

def test_capabilities_never_claim_polkit():
    c = capabilities()
    assert not c['polkit_available'] and not c['installation_enabled']
