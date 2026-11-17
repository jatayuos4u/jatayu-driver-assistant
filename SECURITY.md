# Security policy — Jatayu Driver Assistant Basic

Jatayu Driver Assistant Basic is a read-only hardware information and recommendation tool. It does **not** install, remove or repair kernel drivers, packages or firmware.

Do not run the graphical application with `sudo` or as root. Some kernel logs are restricted and the app must report unknown status when access is unavailable.

The 1.2.3 Debian package does not register Polkit actions, system D-Bus policies or privileged services. Historical development modules and packaging fixtures retained in the source tree are not activated by the published Basic Edition package.

If you find a security vulnerability, contact the maintainers privately through a verified JatayuOS channel rather than posting exploit details publicly.

## Release security

The Basic Edition CI uses SHA-pinned GitHub actions and runs read-only tests. Historical release-publishing workflows must not execute automatically. Protect the `main` branch with required pull-request reviews and enable security alerts in the GitHub repository Settings. GitHub branch protection and repository environments must be configured by an administrator.

Diagnostic JSON export uses owner-only permissions and best-effort identifier redaction, but reports can still identify your system. Review before sharing.
