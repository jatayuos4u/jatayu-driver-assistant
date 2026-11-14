# v0.9.1 Alpha — Wi-Fi diagnostics

Read-only Wi-Fi interface state, local NetworkManager status via a bounded `nmcli device status` invocation, and RF-kill radio blocking status via sysfs. Results are informational only. A NetworkManager `connected` state is not proof of internet access. RF-kill devices are not guaranteed to map one-to-one to interfaces. Firmware requirements remain unverified. No driver installation, network scanning, or network modifications are possible.

Run `python3 -m pytest -q tests/` and build with `dpkg-buildpackage -us -uc -b` on Debian 13.
