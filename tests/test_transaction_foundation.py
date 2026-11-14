import pytest
from jatayu_driver_assistant.backend_contract import RepairRequest
from jatayu_driver_assistant.recommendations import ALLOWED
from jatayu_driver_assistant.transaction_foundation import create_plan, audit_record

PKG = sorted(ALLOWED)[0]
REQ = RepairRequest(PKG, '0000:00:02.0', 'a' * 64)

def plan(operations=None, **kwargs):
    return create_plan(REQ, evidence_packages=(PKG,), simulation_ok=True,
                       operations=[f'Inst {PKG} (1.0)'] if operations is None else operations, **kwargs)

def test_review_is_not_execution():
    p = plan()
    assert p.state == 'review_required'
    assert p.installation_enabled is False
    assert p.to_dict()['installation_enabled'] is False

def test_deterministic_fingerprint():
    assert plan().fingerprint == plan().fingerprint
    assert len(plan().fingerprint) == 64

def test_missing_evidence_blocks():
    p = create_plan(REQ, simulation_ok=True, operations=[f'Inst {PKG} (1.0)'])
    assert p.state == 'blocked'

def test_failed_simulation_blocks():
    assert create_plan(REQ, evidence_packages=(PKG,), operations=[f'Inst {PKG}']).state == 'blocked'

@pytest.mark.parametrize('ops', [[], ['Remv essential'], ['Inst arbitrary-untrusted (1)'],
                                 ['Inst bad;rm -rf /'], ['Unknown thing'], ['Inst x\nRemv y'],
                                 [f'Inst {PKG}'] * 100, [f'Inst {PKG}'] * 101])
def test_unsafe_operations_block(ops):
    assert plan(ops).state == 'blocked'

def test_wrong_requested_package_blocks():
    assert plan(['Conf ' + PKG]).state == 'blocked'

def test_invalid_request_blocks():
    request = RepairRequest('not-allowlisted', '0000:00:02.0', 'a'*64)
    assert create_plan(request, simulation_ok=True, operations=['Inst not-allowlisted']).state == 'blocked'

def test_audit_record_contains_no_device_or_evidence():
    p = plan()
    a = audit_record(p)
    assert a['installation_enabled'] is False
    assert 'device_id' not in a and 'evidence_id' not in a
    with pytest.raises(ValueError):
        audit_record(p, 'installed')

def test_no_side_effect_apis():
    import inspect
    import jatayu_driver_assistant.transaction_foundation as module
    src = inspect.getsource(module)
    assert 'subprocess' not in src
    assert 'os.system' not in src
