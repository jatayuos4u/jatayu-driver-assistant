from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_basic_deb_install_manifest_has_no_services_or_polkit():
    install = (ROOT / 'debian/jatayu-driver-assistant.install').read_text()
    assert 'System.service' not in install
    assert 'System.conf' not in install
    assert 'polkit' not in install
    assert '.policy' not in install
    assert '/dbus-1/' not in install

def test_basic_python_scripts_have_no_elevated_entry_points():
    project = (ROOT / 'pyproject.toml').read_text()
    assert 'jatayu-driver-assistant-system-service =' not in project
    assert 'jatayu-driver-assistant-service =' not in project

def test_basic_install_dependencies_do_not_require_polkit_or_dbus():
    control = (ROOT / 'debian/control').read_text()
    assert ' polkitd' not in control
    assert ' python3-dbus' not in control
