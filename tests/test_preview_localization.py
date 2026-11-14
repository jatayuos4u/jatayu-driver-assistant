"""Regression tests for presentation-only Hindi transaction preview translations."""
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / 'jatayu_driver_assistant/app.py').read_text()


def test_localization_is_display_only():
    assert 'def localized_preview_operation(operation, hindi):' in SOURCE
    assert 'def localized_preview_warning(warning, hindi):' in SOURCE
    assert 'self.localized_preview_operation(op, hi)' in SOURCE
    assert 'self.localized_preview_warning(warning, hi)' in SOURCE
    assert "'plan': plan.to_dict(), 'audit': record" in SOURCE


def test_known_warning_has_hindi_translation():
    assert 'मानवीय समीक्षा और व्यवस्थापक स्तर पर दोबारा सत्यापन' in SOURCE


def test_operation_translation_keeps_package_identifier():
    assert 'match.group(2)' in SOURCE
    assert 'इंस्टॉल (डेमो)' in SOURCE
    assert 'हटाना (डेमो)' in SOURCE


def test_unknown_operation_falls_back_to_original():
    assert 'if not match:' in SOURCE
    assert 'return operation' in SOURCE
