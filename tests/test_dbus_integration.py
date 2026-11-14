from pathlib import Path
from importlib.resources import files
from jatayu_driver_assistant import dbus_service
from jatayu_driver_assistant.service_protocol import DisabledRepairService

def test_dbus_identifiers():
    assert dbus_service.BUS_NAME == 'in.jatayuos.DriverAssistant'
    assert dbus_service.OBJECT_PATH == '/in/jatayuos/DriverAssistant'

def test_service_stays_disabled():
    backend = DisabledRepairService()
    assert backend.get_capabilities()['installation_enabled'] is False
    assert backend.request_installation('firmware-iwlwifi', '0000:00:14.3', 'a'*64).state == 'blocked'

def test_session_activation_only():
    root = Path(__file__).resolve().parents[1]
    descriptor = files('jatayu_driver_assistant').joinpath('in.jatayuos.DriverAssistant.service').read_text()
    source_descriptor = root/'packaging/in.jatayuos.DriverAssistant.service'
    if source_descriptor.exists():
        assert descriptor == source_descriptor.read_text()
    assert 'Exec=/usr/bin/jatayu-driver-assistant-service' in descriptor
    assert 'SystemdService=' not in descriptor
