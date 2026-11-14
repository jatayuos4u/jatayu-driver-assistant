# Jatayu Driver Assistant — Basic Edition

**Version:** 1.2.3 release candidate  
**Platform:** JatayuOS · Debian 13 · KDE Plasma 6  
**License:** GNU GPL v3 or later (`GPL-3.0-or-later`)

Jatayu Driver Assistant is a lightweight, bilingual **English/Hindi**, read-only desktop utility for exploring hardware, inspecting loaded Linux kernel drivers, reviewing diagnostics, and receiving conservative device-specific guidance.

## Features

- Overview of detected devices and driver bindings
- PCI, USB, network, audio, and Bluetooth inventory
- Diagnostics and firmware evidence checks, where accessible
- Physical-device recommendations with clear confidence limitations
- English and Hindi UI, Help, and About pages
- JSON hardware report export

**This is not a driver installer.** It does not install, remove, upgrade, or repair drivers or packages. A loaded driver alone does not prove a device is functioning. Overview counts all detected entries, whereas Recommendations filters to physical PCI/USB hardware, so the totals can differ.

## Build and test

On Debian 13, install the required Python, PySide6, and Debian packaging dependencies. In the project root:

```sh
python3 -m pytest -q tests/
dpkg-buildpackage -us -uc -b
```

The package is written to the parent directory. Run the GUI as a normal user (never with `sudo`).

## Release status

This repository is being prepared for its first public source release. Version 1.2.3 is a **release candidate** until standard Debian build validation, third-party asset rights review, and clean-install / upgrade / removal tests on JatayuOS are completed.

## License

Licensed under **GPL-3.0-or-later**. See [LICENSE](LICENSE). Third-party software and assets retain their own licenses. Please do not submit code or assets you lack permission to redistribute.

Project website: https://jatayuos.in
