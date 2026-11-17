from pathlib import Path

def test_about_links_and_language():
    text = (Path(__file__).resolve().parents[1] / 'jatayu_driver_assistant/app.py').read_text()
    assert 'https://jatayuos.in' in text
    assert 'https://github.com/jatayuos4u' in text
    assert 'def update_about(self):' in text
    assert "self.language == 'hi'" in text
    assert '1.2.4' in text

def test_no_privileged_install_in_about_update():
    text = (Path(__file__).resolve().parents[1] / 'jatayu_driver_assistant/app.py').read_text()
    assert 'pkexec' not in text
    assert 'sudo apt install' not in text
