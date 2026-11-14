from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / 'jatayu_driver_assistant/app.py').read_text()

def test_preview_has_explicit_synthetic_boundary():
    assert "'synthetic_demo': True" in APP
    assert "'not_real_apt_simulation': True" in APP
    assert 'INSTALLATION DISABLED' in APP

def test_preview_supports_four_scenarios():
    for scenario in ("'review'", "'unknown'", "'removal'", "'failure'"):
        assert scenario in APP

def test_preview_has_json_export_and_translation():
    assert 'def export_transaction_preview' in APP
    assert 'def update_transaction_preview' in APP
    assert 'लेन-देन पूर्वावलोकन' in APP
