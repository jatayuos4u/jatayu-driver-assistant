# Security hardening — v1.2.4 candidate

- GitHub Actions action references are pinned to immutable commit hashes.
- Historical release-publishing workflows have been removed to avoid accidental publication.
- Normal GitHub CI has `contents: read` permissions.
- Diagnostic process output is bounded while reading; timeouts terminate child processes.
- Hardware text is always rendered in plain text in application labels.
- Exported JSON reports have owner-only permissions (`0600`), reject symlinks, and redact recognized MACs, UUIDs and home-directory names.
- Extra regression tests cover child timeouts, output overflow, private export, and symlink refusal.

**Human action required:** configure GitHub branch protection/repository Rulesets and a reviewed release approval environment. The application cannot set repository organization policy. Do not automatically republish old stable artifacts.

**Historical modules:** `system_service.py`, `dbus_service.py` and the `packaging/` D-Bus/Polkit fixtures were retained for historical testing and are not registered or installed by the Basic Edition. A future privileged-driver-manager project must undergo an independent security review before use.

**Limits:** The source test suite is not a substitute for a desktop runtime test, fuzzing, dependency CVE audit, or Debian package reproducibility assessment.
