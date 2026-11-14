# Public release checklist (v1.2.3 Basic)

- [x] Project LICENSE contains GNU GPL v3 text
- [x] Python project metadata declares GPL-3.0-or-later
- [x] Debian copyright metadata declares GPL-3+
- [x] Official GPL-3.0-or-later licensing choice confirmed; see LICENSING.md
- [x] README reflects Basic Edition, read-only functionality, and version 1.2.3
- [ ] Confirm project ownership, contributor permissions, and rights to all source/assets
- [ ] Audit third-party licenses and attribution obligations
- [ ] Confirm maintainer email and repository ownership
- [ ] Run tests on Debian 13
- [ ] Build .deb with standard Debian build tooling
- [ ] Install, upgrade, remove, and reinstall .deb on clean JatayuOS VM
- [ ] Test English and Hindi UI, exports, and recommendation counts
- [ ] Inspect package contents for unnecessary privileged services and permissions
- [ ] Verify package and source archive checksums
- [ ] Publish GitHub source and tag after all above checks

- [x] Remove experimental D-Bus and Polkit registrations from installed Basic Edition package
- [ ] Verify the Debian 13 binary package built with standard debhelper, rather than an assembled package
- [ ] Confirm all icons/logos have appropriate rights for GitHub publication
