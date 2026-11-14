from jatayu_driver_assistant.live_tests import run_live_checks
import pytest

@pytest.mark.parametrize('category', ['wifi', 'graphics', 'network', 'audio', 'bluetooth'])
def test_live_checks_never_install(category):
    result = run_live_checks(category)
    assert result['source'] == 'live_local_system'
    assert result['synthetic'] is False
    assert result['installation_enabled'] is False
    assert result['hardware_modified'] is False
    assert isinstance(result['details'], list)

def test_unknown_category_rejected():
    with pytest.raises(ValueError):
        run_live_checks('arbitrary-command')
