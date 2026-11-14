from pathlib import Path

def test_help_center_is_bilingual_and_offline():
    app = (Path(__file__).resolve().parents[1] / 'jatayu_driver_assistant/app.py').read_text()
    for needle in ('def build_help(self):', 'def update_help(self):', 'Getting started', 'शुरू कैसे करें', 'Kernel', 'कर्नेल', 'self.build_help()', 'self.update_help()'):
        assert needle in app

def test_help_safety_and_navigation():
    app = (Path(__file__).resolve().parents[1] / 'jatayu_driver_assistant/app.py').read_text()
    assert "('?', 4)" in app
    assert 'Driver installation and repair are disabled.' in app
    assert 'Do not disable kernel log restrictions' in app
