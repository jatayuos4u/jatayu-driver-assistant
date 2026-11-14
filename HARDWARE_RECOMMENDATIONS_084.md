# v0.8.4 device-specific recommendation policy

Hardware PCI vendor/class hints are insufficient to authorize a package recommendation. This release therefore deliberately disables the device-specific APT inspection button for **all** devices. A future release needs a reviewed device/firmware evidence chain and explicit package allowlist before enabling that button. The generic APT simulation is independent and is not a recommendation. No installation functionality is present.
