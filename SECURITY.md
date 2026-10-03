# Security

## Scope for Slice 1

This repository is a local development factory and **does not contain credentials, secrets, or proprietary runtime payloads**.

## Credential policy

- Secrets are intentionally excluded from the repository.
- Runtime payload checks in release validation enforce clean-room boundaries and stdlib-only policy for Art/Engineering runtime packages.
- Deny lists used by release verification come from an external file supplied at verification time.
- Private identifiers discovered during review are handled internally and are not published in public documents.

## Disclosure process

A public disclosure route and contact process is intentionally incomplete in this slice. A definitive responsible-disclosure workflow will be added before publication.
