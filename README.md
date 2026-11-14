# Jatayu Driver Assistant — Basic Edition

**Version:** 1.2.3  
**Platform:** JatayuOS / Debian 13, KDE Plasma 6  
**License:** GNU GPL v3 or later (`GPL-3.0-or-later`)

Jatayu Driver Assistant is a bilingual (English/Hindi), read-only hardware inventory and driver information utility. It discovers devices and displays their currently bound kernel drivers and conservative diagnostic guidance.

## Features

- Overview of detected hardware and driver bindings
- Devices and diagnostics views
- Recommendations limited to physical PCI/USB devices, with driver-binding status and explanations
- Help and About pages; English/Hindi UI
- Read-only reports and diagnostics

**Limitations:** This program does **not** install, remove, upgrade, or repair drivers. A bound driver does not prove a device works; a package hint is not a verified installation recommendation. Some kernel logs require additional permissions. The Overview includes all detected entries, whereas Recommendations filters to physical PCI/USB devices, so counts can differ.

## Install

Install the matching Debian package using your graphical package installer, or from its download directory:

```sh
sudo apt install ./jatayu-driver-assistant-basic_1.2.3-1_all.deb
```

Start from the applications menu or run `jatayu-driver-assistant` **without sudo**.

## Build and test from source

On Debian 13, install the development dependencies:

```sh
sudo apt install build-essential devscripts debhelper dh-python pybuild-plugin-pyproject python3-all python3-setuptools python3-pytest python3-pyside6.qtwidgets python3-pyside6.qtcore
```

Then, from the project root:

```sh
python3 -m pytest -q tests/
dpkg-buildpackage -us -uc -b
```

The package is written to the parent directory. Build dependencies and GUI runtime support must be validated on the target system.

## License and contributions

The project declares **GPL-3.0-or-later**; see [LICENSE](LICENSE) and [debian/copyright](debian/copyright). Third-party dependencies retain their respective licenses. Only submit contributions that you have the right to license under GPL-3.0-or-later. See [CONTRIBUTING.md](CONTRIBUTING.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Security

See [SECURITY.md](SECURITY.md). Do not run the GUI as root. Report security concerns privately to the project maintainers using a verified contact channel.

## Project

JatayuOS Project · https://jatayuos.in  
Repository: https://github.com/jatayuos4u/jatayu-driver-assistant

## Basic Edition packaging

This read-only package installs **no** D-Bus activation service, system D-Bus policy, privileged helper, or Polkit action. Historical service experiments remain in the source tree for reference/tests but are not activated or installed by the Debian package.
