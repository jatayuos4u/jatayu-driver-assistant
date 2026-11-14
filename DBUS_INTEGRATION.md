# v0.5.1 D-Bus integration (safe staging)

This release installs an **actual D-Bus session-bus service** for the logged-in
user. It is not a system-bus service and does not run as root. This deliberate
staging step tests activation and the IPC contract without exposing a privileged
installer. The D-Bus `RequestInstallation` method always returns `false`.

After installing the .deb, developers can test activation with:

```sh
gdbus call --session --dest in.jatayuos.DriverAssistant \
  --object-path /in/jatayuos/DriverAssistant \
  --method in.jatayuos.DriverAssistant1.GetCapabilities
```

The response should include `installation_enabled: false` and
`polkit_enabled: false`. A user-facing graphical installation flow remains
unavailable. There is **no** Polkit policy or root helper in this package.

Next step: develop a separately packaged system-bus backend with strict caller
identity, Polkit action authorization, server-side hardware and firmware
validation, trusted APT metadata checks, transaction locking, and VM security
tests. Do not copy session-bus permissions into a privileged service.
