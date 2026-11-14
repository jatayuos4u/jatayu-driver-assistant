"""Static regression checks for the synthetic structured preview UI."""
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / 'jatayu_driver_assistant/app.py').read_text()

def test_structured_cards_exist():
    for field in ('preview_safety', 'preview_status', 'preview_package',
                  'preview_operations', 'preview_warnings', 'preview_fingerprint'):
        assert f'self.{field} =' in SOURCE

def test_language_switch_rerenders_existing_preview():
    assert 'def render_transaction_preview(self):' in SOURCE
    assert 'self.render_transaction_preview()' in SOURCE
    assert 'पैकेज:' in SOURCE

def test_installation_is_visibly_disabled():
    assert 'INSTALLATION DISABLED' in SOURCE
    assert 'SIMULATION ONLY' in SOURCE

def test_export_preserves_synthetic_payload():
    assert "'source': 'fixed_demo_fixture'" in SOURCE
    assert 'json.dumps(self.last_transaction_preview, indent=2)' in SOURCE
