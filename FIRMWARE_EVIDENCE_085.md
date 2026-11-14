# v0.8.5 firmware evidence correlation (read-only)

Click **Inspect hardware hints**, then **Inspect kernel firmware evidence (read-only)**.
The current-boot kernel journal is read with a fixed, non-shell `journalctl` command.
An explicit firmware load failure is correlated only when its PCI BDF matches a
scanned device and its reported driver family agrees with the bound kernel driver.
The status **Correlated (unverified)** is not proof of package requirement, nor a
verified hardware-to-package match. Logs can be missing, inaccessible, stale,
misleading or contain errors unrelated to missing packages. A missing correlation
is not proof of healthy firmware. No device-specific APT operation is enabled.
The JSON report contains the access status and any correlated log excerpts.
Kernel messages may contain device details: review exports before sharing.
Real installation and removal remain disabled.
