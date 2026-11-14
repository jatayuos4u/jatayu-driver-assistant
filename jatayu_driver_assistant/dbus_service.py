"""Actual unprivileged session D-Bus service; deliberately never changes packages."""
from .service_protocol import DisabledRepairService

BUS_NAME = 'in.jatayuos.DriverAssistant'
OBJECT_PATH = '/in/jatayuos/DriverAssistant'
INTERFACE = 'in.jatayuos.DriverAssistant1'


def main():
    try:
        import dbus
        import dbus.service
        import dbus.mainloop.glib
        from gi.repository import GLib
    except ImportError as exc:
        raise SystemExit('Missing python3-dbus or python3-gi: ' + str(exc))

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    backend = DisabledRepairService()

    class DriverService(dbus.service.Object):
        @dbus.service.method(INTERFACE, in_signature='', out_signature='a{sv}')
        def GetCapabilities(self):
            return {key: dbus.Boolean(value) if isinstance(value, bool)
                    else dbus.Int32(value) if isinstance(value, int)
                    else dbus.String(value)
                    for key, value in backend.get_capabilities().items()}

        @dbus.service.method(INTERFACE, in_signature='sss', out_signature='b')
        def RequestInstallation(self, package, device_id, evidence_id):
            backend.request_installation(package, device_id, evidence_id)
            return False

    name = dbus.service.BusName(BUS_NAME, bus=bus, do_not_queue=True)
    service = DriverService(bus, OBJECT_PATH)
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        service.remove_from_connection()

if __name__ == '__main__':
    main()
