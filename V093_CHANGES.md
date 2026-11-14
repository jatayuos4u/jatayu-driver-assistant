# v0.9.3 Alpha — Kernel evidence classification

- Reads up to 2,000 current-boot kernel journal messages as the invoking user, without sudo or Polkit escalation.
- Reports restricted journal access separately from missing logs.
- Classifies Intel iwlwifi firmware-load success, possible Wi-Fi firmware load failures, and unrelated Intel i915 FIFO underrun warnings.
- Never infers that a firmware package must be installed. Device association is not verified; installation remains disabled.
- English and Hindi status summaries in Wi-Fi diagnostics.
- Logs may be unavailable under Debian 13 journal access restrictions; do not weaken OS security settings to run diagnostics.
