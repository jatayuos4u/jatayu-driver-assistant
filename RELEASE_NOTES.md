# Jatayu Driver Assistant Basic 1.2.3 — Release candidate

Read-only, bilingual (English/Hindi) hardware discovery, device diagnostics and conservative driver-binding recommendations for JatayuOS (Debian 13 / KDE Plasma 6).

**Not a driver installer.** This build performs no installation, removal or repair. Firmware-health confirmation depends on permissions and evidence.

### Security / packaging changes

The Debian package no longer registers the experimental D-Bus activation services, system bus configuration or Polkit actions. No administrator permissions are required to start the GUI.

### Before a public stable GitHub release

Confirm copyright and logo rights, run package build via standard `dpkg-buildpackage` on Debian 13, test clean install/upgrade/remove on JatayuOS and both languages, verify package file listing, then publish a tagged release and attach `.deb` plus source archive.
