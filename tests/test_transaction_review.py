from jatayu_driver_assistant.recommendations import assess_transaction, preview_plan

def test_simple_plan():
    assert assess_transaction(['Inst firmware-realtek (1)', 'Conf firmware-realtek (1)'], 'firmware-realtek')[0]

def test_removal_blocked():
    assert not assess_transaction(['Remv linux-image-amd64', 'Inst firmware-realtek (1)'], 'firmware-realtek')[0]

def test_empty_plan_blocked():
    assert not assess_transaction([], 'firmware-realtek')[0]

def test_other_package_blocked():
    assert not assess_transaction(['Inst firmware-realtek (1)'], 'firmware-iwlwifi')[0]

def test_unknown_operation_blocked():
    assert not assess_transaction(['Unexpected something', 'Inst firmware-realtek (1)'], 'firmware-realtek')[0]

def test_preview_never_enables_installation():
    class Result:
        returncode = 0
        stdout = 'Inst firmware-realtek (1)\\nConf firmware-realtek (1)\\n'
        stderr = ''
    plan = preview_plan('firmware-realtek', runner=lambda *a, **kw: Result())
    assert plan['review_passed']
    assert plan['installation_enabled'] is False
