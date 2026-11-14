import pytest
from jatayu_driver_assistant.testing import run_scenario

@pytest.mark.parametrize('name', ['wifi', 'graphics'])
def test_firmware_failure_detected(name):
    result = run_scenario(name)
    assert result['synthetic'] is True
    assert result['findings']
    assert result['installation_enabled'] is False
    assert result['hardware_modified'] is False

def test_healthy_case():
    assert run_scenario('healthy')['findings'] == []

def test_invalid_case():
    with pytest.raises(ValueError):
        run_scenario('unknown')

def test_fixtures_are_not_real_scan():
    result = run_scenario('wifi')
    assert 'demo' in result['log']
    assert result['synthetic']
