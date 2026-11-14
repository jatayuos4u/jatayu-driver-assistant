# Jatayu Driver Assistant 0.8.8 Alpha

- Double-click a row in Repair Center > Hardware compatibility to open a bilingual, read-only device details dialog.
- Or select a row and use **View selected device details (read-only)**.
- Shows PCI address, vendor/device/class IDs, kernel driver, category, unverified package hint, confidence, evidence status, and explanation.
- No hardware-to-firmware match is verified; no installation is enabled.
- If the hardware JSON report says `kernel_evidence_access: not_checked`, run the kernel inspection first, then export again.

## Build on Debian 13

```bash
sudo apt install build-essential devscripts debhelper dh-python pybuild-plugin-pyproject python3-all python3-setuptools python3-pytest
python3 -m pytest -q tests/
dpkg-buildpackage -us -uc -b
sudo apt install ../jatayu-driver-assistant_0.8.8-1_all.deb
```

Source tests: 137 passed in development environment. Debian package installation must be tested on Debian 13.
