from pathlib import Path


def test_preview_has_scroll_area_and_elided_labels():
    source = (Path(__file__).resolve().parents[1] / 'jatayu_driver_assistant' / 'app.py').read_text()
    assert 'class ElidedLabel(QLabel)' in source
    assert 'QFontMetrics(self.font()).elidedText' in source
    assert 'self.preview_scroll = QScrollArea()' in source
    assert 'row.setMinimumHeight(68)' in source


def test_preview_does_not_hide_rows_during_refresh():
    source = (Path(__file__).resolve().parents[1] / 'jatayu_driver_assistant' / 'app.py').read_text()
    assert 'row.setVisible(' not in source
