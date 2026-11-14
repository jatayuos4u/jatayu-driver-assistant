# Live APT analysis — v0.8.0 Alpha

The Repair Center offers a read-only APT simulation for the first fixed allowlisted firmware package (alphabetical order). It is **not** selected based on detected hardware and must not be interpreted as a driver recommendation. It uses `/usr/bin/apt-get -s -o Debug::NoLocking=1 install -- PACKAGE` without shell execution or root privileges. It does not execute package installation. APT simulation may read package metadata and invoke APT configuration hooks; use trusted system configuration. Results are informational only and cannot authorize installation. Unexpected removals and non-allowlisted dependencies are blocked. The fixed synthetic preview remains separate.

No privileged installation backend is included. Do not release this alpha as a working driver installer.
