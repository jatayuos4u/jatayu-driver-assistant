# Privileged backend design (not yet implemented)

v0.4.2 includes only an **unprivileged validation contract**. It does not
ship a root daemon, a Polkit policy, an installer, or an authorization bypass.

Before any release enabling installation:

1. Implement a system D-Bus service with a dedicated Polkit action.
2. Re-identify hardware using kernel sysfs on the service side. Never trust GUI-supplied evidence.
3. Re-evaluate fresh firmware logs and validate the exact firmware file / package mapping.
4. Confirm candidate provenance from authenticated, configured Debian/JatayuOS repositories.
5. Obtain a complete APT transaction plan; fail closed on removals, downgrades,
   held packages, kernel changes, or other unexpected changes.
6. Ensure another package manager is not operating, and prevent TOCTOU between
   approval and execution; revalidate before execution.
7. Show the exact transaction to the user, require explicit approval and Polkit.
8. Run controlled package operations without shell interpolation or arbitrary input.
9. Maintain audit logs, progress reporting, error handling, and post-install verification.
10. Test with disposable Debian 13 VMs and fault injection, then independent review.

A successful simulation or request-validation result **never** authorizes execution.
