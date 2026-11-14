# Security policy — Jatayu Driver Assistant Basic

Jatayu Driver Assistant Basic is a read-only hardware information and recommendation tool. It does **not** install, remove or repair kernel drivers, packages or firmware.

Do not run the graphical application with `sudo` or as root. Some kernel logs are restricted and the app must report unknown status when access is unavailable.

The 1.2.3 Debian package does not register Polkit actions, system D-Bus policies or privileged services. Historical development modules and packaging fixtures retained in the source tree are not activated by the published Basic Edition package.

If you find a security vulnerability, contact the maintainers privately through a verified JatayuOS channel rather than posting exploit details publicly.
