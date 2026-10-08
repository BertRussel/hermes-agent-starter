# Recipient handoff package

This directory is the reusable, privacy-clean template assembled by `scripts/build_handoff.py`. It intentionally contains no live profile homes, provider authentication, browser state, credentials, conversations, databases, timing records, or owner identifiers.

The output archive contains exactly four initial templates: `primary`, `forge`, `verifier`, and `eve`. Optional Recon and Art are not shipped; they may be created later only for recurring task-specific needs.

Read `OPERATOR-AND-RECIPIENT-HANDOFF.md` and `NATIVE-PIPELINE-RUNBOOK.md` before restoring.