# v0.6.0 system D-Bus backend (read-only alpha)

The system bus endpoint is `in.jatayuos.DriverAssistant.System`, object
`/in/jatayuos/DriverAssistant/System`, interface
`in.jatayuos.DriverAssistant.System1`. Its sole method is `GetCapabilities`.

The service is activated by the system bus under root, but has no methods to
run commands, install packages, modify devices, or accept arbitrary inputs.
There is no Polkit action in this release. Running as root is necessary only
for validating the system-bus activation architecture at this milestone; a
future release should minimize privileges or use a tightly scoped helper.

Test after installing:

```
gdbus call --system --dest in.jatayuos.DriverAssistant.System \
  --object-path /in/jatayuos/DriverAssistant/System \
  --method in.jatayuos.DriverAssistant.System1.GetCapabilities
```

Expected: `installation_enabled=false`, `polkit_enabled=false`,
`privileged_backend=false`. This is not a functional driver installer.
Do not distribute as a production repair tool.
