from pathlib import Path
import xml.etree.ElementTree as ET
from jatayu_driver_assistant.system_service import (
    system_capabilities, BUS_NAME, OBJECT_PATH, INTERFACE, POLKIT_ACTION,
    check_polkit_authorization,
)

ROOT = Path(__file__).resolve().parents[1]

class FakeDBus:
    String = staticmethod(str)
    UInt32 = staticmethod(int)
    class Dictionary(dict):
        def __init__(self, *args, signature=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.signature = signature
    class Struct(tuple):
        def __new__(cls, value, signature=None):
            obj = super().__new__(cls, value)
            obj.signature = signature
            return obj

class FakeAuthority:
    def __init__(self, authorized, challenge=False):
        self.authorized, self.challenge = authorized, challenge
        self.args = None
    def CheckAuthorization(self, *args):
        self.args = args
        return self.authorized, self.challenge, {}

def test_capabilities_fail_closed_but_polkit_probe_is_available():
    caps = system_capabilities()
    assert caps['installation_enabled'] is False
    assert caps['polkit_enabled'] is True
    assert caps['privileged_backend'] is False
    assert caps['service_mode'] == 'system_authorization_probe'

def test_distinct_bus_names():
    from jatayu_driver_assistant.dbus_service import BUS_NAME as session_name
    assert BUS_NAME != session_name
    assert OBJECT_PATH.startswith('/')

def test_interface_exposes_only_capabilities_and_auth_probe():
    root = ET.parse(ROOT / 'packaging/in.jatayuos.DriverAssistant.System.xml').getroot()
    methods = [m.attrib['name'] for m in root.iter('method')]
    assert methods == ['GetCapabilities', 'RequestAuthorization']
    assert not any('Install' in name or 'Remove' in name for name in methods)

def test_service_activation_is_explicit_root():
    descriptor = (ROOT / 'packaging/in.jatayuos.DriverAssistant.System.service').read_text()
    assert 'User=root' in descriptor
    assert f'Name={BUS_NAME}' in descriptor

def test_dbus_policy_allows_only_two_declared_service_methods():
    root = ET.parse(ROOT / 'packaging/in.jatayuos.DriverAssistant.System.conf').getroot()
    allowed = [e.attrib.get('send_member') for e in root.iter('allow') if 'send_member' in e.attrib]
    assert allowed == ['GetCapabilities', 'RequestAuthorization']

def test_polkit_policy_requires_admin_authentication():
    root = ET.parse(ROOT / 'packaging/in.jatayuos.DriverAssistant.policy').getroot()
    action = root.find(f"action[@id='{POLKIT_ACTION}']")
    assert action is not None
    defaults = action.find('defaults')
    assert defaults.findtext('allow_any') == 'no'
    assert defaults.findtext('allow_inactive') == 'no'
    assert defaults.findtext('allow_active') == 'auth_admin'

def test_authorization_uses_unique_dbus_sender_and_fixed_action():
    authority = FakeAuthority(True)
    result = check_polkit_authorization(authority, FakeDBus, ':1.42')
    assert result['authorized'] is True
    assert result['installation_enabled'] is False
    assert authority.args[1] == POLKIT_ACTION
    assert authority.args[0][1]['name'] == ':1.42'
    assert authority.args[3] == 1

def test_denied_authorization_stays_denied():
    authority = FakeAuthority(False, True)
    result = check_polkit_authorization(authority, FakeDBus, ':1.43')
    assert result['authorized'] is False
    assert result['challenge'] is True
    assert result['installation_enabled'] is False

def test_rejects_missing_or_non_unique_sender():
    import pytest
    authority = FakeAuthority(True)
    with pytest.raises(ValueError):
        check_polkit_authorization(authority, FakeDBus, 'org.example.Client')
