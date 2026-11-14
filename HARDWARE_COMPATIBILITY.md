# Hardware compatibility hints (v0.8.2 Alpha)

This release inspects local PCI sysfs vendor/device/class IDs and the bound kernel driver.
A conservative vendor/class family map may show a **low-confidence** firmware package hint.
This is **not** a device-specific match, proof of missing firmware, a diagnosis, or approval to install.
USB devices are not included in this initial matching view.
APT simulations remain read-only; package installation and removal are not implemented.
The app never runs APT as root and never uses shell=True.
