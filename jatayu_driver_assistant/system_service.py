"""Fail-closed system D-Bus service with a one-shot Polkit authorization check.

No package, driver, firmware, or filesystem mutation methods are exposed.
The authorization result is informational only and is never cached or reused.
"""
import logging

from .service_protocol import DisabledRepairService

BUS_NAME = "in.jatayuos.DriverAssistant.System"
OBJECT_PATH = "/in/jatayuos/DriverAssistant/System"
INTERFACE = "in.jatayuos.DriverAssistant.System1"
POLKIT_ACTION = "in.jatayuos.driverassistant.authorize-repair"

log = logging.getLogger("jatayu_driver_assistant.polkit")


def system_capabilities():
    """Advertise the implemented authorization probe, never installation."""
    caps = DisabledRepairService().get_capabilities()
    return {**caps, "service_mode": "system_authorization_probe",
            "privileged_backend": False, "polkit_enabled": True,
            "installation_enabled": False}


def check_polkit_authorization(authority, dbus_module, sender):
    """Ask Polkit about this exact system-bus caller; do not cache the result."""
    if not isinstance(sender, str) or not sender.startswith(":"):
        raise ValueError("A unique system-bus sender is required")
    subject = dbus_module.Struct((
        dbus_module.String("system-bus-name"),
        dbus_module.Dictionary({"name": dbus_module.String(sender)}, signature="sv"),
    ), signature="sa{sv}")
    details = dbus_module.Dictionary({}, signature="ss")
    # 1 = AllowUserInteraction: permits the desktop Polkit agent to prompt.
    authorized, challenge, _details = authority.CheckAuthorization(
        subject, POLKIT_ACTION, details, dbus_module.UInt32(1), dbus_module.String(""))
    result = bool(authorized)
    log.info("Polkit authorization %s for caller %s", "granted" if result else "denied", sender)
    return {"authorized": result, "challenge": bool(challenge),
            "action_id": POLKIT_ACTION, "installation_enabled": False}


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        import dbus
        import dbus.service
        import dbus.mainloop.glib
        from gi.repository import GLib
    except ImportError as exc:
        raise SystemExit("Missing system D-Bus dependencies: " + str(exc))
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    authority_obj = bus.get_object("org.freedesktop.PolicyKit1", "/org/freedesktop/PolicyKit1/Authority")
    authority = dbus.Interface(authority_obj, "org.freedesktop.PolicyKit1.Authority")

    class CapabilityService(dbus.service.Object):
        @dbus.service.method(INTERFACE, in_signature="", out_signature="a{sv}")
        def GetCapabilities(self):
            values = system_capabilities()
            return {key: dbus.Boolean(value) if isinstance(value, bool)
                    else dbus.Int32(value) if isinstance(value, int)
                    else dbus.String(value) for key, value in values.items()}

        @dbus.service.method(INTERFACE, in_signature="", out_signature="a{sv}", sender_keyword="sender")
        def RequestAuthorization(self, sender=None):
            """Perform an interactive authorization probe; no operation follows."""
            result = check_polkit_authorization(authority, dbus, sender)
            return {key: dbus.Boolean(value) if isinstance(value, bool)
                    else dbus.String(value) for key, value in result.items()}

    name = dbus.service.BusName(BUS_NAME, bus=bus, do_not_queue=True)
    service = CapabilityService(bus, OBJECT_PATH)
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        service.remove_from_connection()


if __name__ == "__main__":
    main()
