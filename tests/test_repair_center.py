from pathlib import Path
APP = Path(__file__).resolve().parents[1] / 'jatayu_driver_assistant' / 'app.py'
def test_basic_navigation_omits_legacy_centers():
    source = APP.read_text()
    assert 'self.build_repair_center()' not in source
    assert 'self.build_testing_center()' not in source
    assert "('?', 4)" in source
    assert 'self.build_help()' in source

def test_recommendations_are_read_only():
    source = APP.read_text()
    section = source.split('def refresh_recommendations(self):')[1].split('def show_package_preview(self, name):')[0]
    for forbidden in ('pkexec', 'sudo', 'apt-get install', 'os.system', 'subprocess.Popen'):
        assert forbidden not in section
