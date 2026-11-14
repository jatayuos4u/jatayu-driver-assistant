# Jatayu Driver Assistant v0.7.0 Alpha — transaction foundation

This is a **read-only prototype**, not an installer. The existing GUI and bilingual English/Hindi support remain intact.

`jatayu_driver_assistant.transaction_foundation.create_plan()` accepts a validated `RepairRequest`, diagnostic evidence package names, a caller-provided APT simulation result, and operation records. It returns an immutable, fingerprinted review or blocked plan. No installation, APT execution, filesystem writes, root privilege, or new D-Bus methods are implemented.

**Limitations:** The plan does not authenticate hardware evidence, APT repository metadata, or the origin/completeness of simulation output. It intentionally rejects non-allowlisted dependencies and removals, and should not be used as permission to install. Fingerprints are for consistency, not authentication. Audit records are returned in memory; no persistent logging is claimed.

## Debian 13 build

```bash
cd jatayu-driver-assistant
python3 -m pytest -q tests/
dpkg-buildpackage -us -uc -b
sudo apt install ../jatayu-driver-assistant_0.7.0-1_all.deb
```

## Preview API example (no installation)

```python
from jatayu_driver_assistant.backend_contract import RepairRequest
from jatayu_driver_assistant.transaction_foundation import create_plan
# Substitute a package in the built-in allowlist and actual diagnostic evidence.
# A preview is not a privileged transaction approval.
```

Before implementing actual installation: obtain trusted fresh hardware evidence inside the privileged service; securely bind each transaction to a fresh Polkit authorization; verify APT metadata and exact package versions; reject unsafe dependency/removal changes; handle locks and cancellation; integrate robust transaction logging and recovery; and test in a disposable Debian 13 VM.
