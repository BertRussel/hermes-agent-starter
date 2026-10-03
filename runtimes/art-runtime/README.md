# Art Runtime

This runtime is a validation-only, in-memory implementation of a clean-room Art contract boundary.

## Scope

- Pure standard-library behavior only.
- No filesystem mutation, no environment introspection, and no wall-clock or randomness usage.
- No network access, subprocess usage, dynamic import, `eval`/`exec`/`compile`, plugin handling, profile integration, media processing, vector processing, or video behavior.
- No credentials, customer data, private fixture content, or secrets are handled.

## Contract behavior

- Validates job contracts and candidate manifests.
- Enforces strict closed dictionaries, strict types, and bounded fields.
- Enforces POSIX-relative path safety, lowercase SHA-256 syntax, and finite state transitions.
- Produces canonical JSON bytes with sorted keys, compact separators, UTF-8 encoding, and one trailing newline.

## Authorisation model

- No creative approval authority, no production/publication authority, and no external access authority.
- `reviewable_awaiting_owner` is a normal lifecycle state and is not equivalent to approval.
- Lifecycle installation and publication remain future-canal canaries and are intentionally out of scope for this slice.
