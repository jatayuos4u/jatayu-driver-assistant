# System service design — not deployed

Version 0.5.0 ships an **unprivileged, fail-closed protocol prototype** and
D-Bus introspection *design* XML. It does **not** install a D-Bus service,
Polkit policy, root helper, or package installer. No installation button is enabled.

Before activation, a separate review must establish:

1. Authentication/authorization per request through Polkit with caller identity
   bound to the actual system D-Bus connection; do not trust caller-supplied UID.
2. Independent evidence collection on the privileged side; client-supplied
   evidence IDs and simulated plans are never authorization.
3. Signed repository metadata verification, candidate provenance, and strict
   package allowlists appropriate for the installed Debian release.
4. APT/dpkg lock coordination, no shell invocation, cancellation, safe timeouts,
   re-simulation immediately before commit, and blocking unexpected removals.
5. Transaction logs, package-change consent, recovery planning, and post-install
   hardware checks; success installing a package is not proof of a repaired device.
6. Security review, tests in disposable Debian 13 VMs, and threat modeling
   including D-Bus sender spoofing and time-of-check/time-of-use races.

The XML under packaging/ is intentionally not installed into the system bus.
