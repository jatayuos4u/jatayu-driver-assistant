# Jatayu Driver Assistant v0.7.1 transaction preview

The Repair Center includes **fixed synthetic demonstration fixtures**, not real APT simulations or real hardware recommendations. No packages are installed, removed, or modified. The backend planner validates an allowlisted example, unknown package, removal, and failed simulation. The preview is informational only. The JSON export includes `synthetic_demo: true` and `not_real_apt_simulation: true`.

## Test and build

```sh
python3 -m pytest -q tests/
dpkg-buildpackage -us -uc -b
```

Do not interpret a `review_required` result as permission to install. The privileged backend does not expose installation methods.
