# v0.6.1 Polkit authorization probe

This release adds one interactive Polkit authorization check to the root-owned system D-Bus service. The only action ID is `in.jatayuos.driverassistant.authorize-repair`; callers cannot choose an action ID or supply a command/package. The service binds the check to the unique D-Bus sender name and asks Polkit with `AllowUserInteraction`. The policy requires administrator authentication for an active local session and denies inactive/any sessions.

`RequestAuthorization` is an **authorization demonstration only**. A successful response is not a reusable token, is not cached by this service, and does not authorize a later operation. No mutating D-Bus methods exist. Installation, removal, firmware changes, module loading, and arbitrary command execution remain impossible through this interface.

The D-Bus method returns `authorized`, `challenge`, `action_id`, and `installation_enabled=false`. A desktop Polkit authentication agent must be running for a graphical prompt; without one, the request may fail or return a challenge without a visible prompt.

Test suite: `python3 -m pytest -q tests/`. Debian package build: `dpkg-buildpackage -us -uc -b`. After installing, inspect the interface with `gdbus introspect --system --dest in.jatayuos.DriverAssistant.System --object-path /in/jatayuos/DriverAssistant/System`. Test the probe with `gdbus call --system --dest in.jatayuos.DriverAssistant.System --object-path /in/jatayuos/DriverAssistant/System --method in.jatayuos.DriverAssistant.System1.RequestAuthorization`. This should trigger the desktop administrator authentication flow. Do not treat this alpha as a driver installer.
