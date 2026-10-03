# Engineering Runtime

Purpose
- Own package, release and provenance metadata for the engineering runtime component.
- Validate runtime manifest, provenance, and release-index contracts from a pure-Python verifier.
- Emit deterministic runtime event timing and delegation audit reports.
- Validate execution contracts used by runtime tests and release tooling.
- Enforce local-path and dependency policy for this component in release gates.
- Support future specialist-independent integration steps without changing core contracts.

This runtime is intentionally stdlib-only.

Boundary
- No daemonization.
- No network calls.
- No gateway exposure.
- No production or publication authority.
- No install/distribution side-effects.

Synthetic API example
- `build_profile_launch(role, executable, profile_root, home_root, inherited_env=None)` returns a launch command and sanitized environment.
- `validate_git_snapshot(snapshot, expected)` verifies strict structural boundaries.
- `timing_report(events)` computes ordered phase durations and total wall time.

Installation and lifecycle notes
- Runtime installation and lifecycle management remain deferred to the canary slice only.
