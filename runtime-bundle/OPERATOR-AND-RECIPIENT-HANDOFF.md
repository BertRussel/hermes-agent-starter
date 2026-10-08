# Operator and recipient handoff

## Before infrastructure

Recipient: create the Oracle Cloud account in the recipient's own identity, complete billing verification and MFA privately, choose the home region deliberately (it is permanent), and understand Free Tier/Always Free limits. Upgrade to Pay As You Go only when the recipient independently approves it; do not create resources merely to upgrade.

Recipient sends Operator only: chosen region, non-secret account confirmation, preferred contact channel, and the public SSH key or a safe method for exchanging one. Never email or share passwords, MFA codes, payment details, recovery codes, browser exports, provider tokens, or BWS secrets.

Ready-to-send email:

> Please create your Oracle Cloud account in your own name, complete billing and MFA privately, and choose your home region carefully because it cannot be changed. Reply only with your chosen region, account-confirmation status, and a public SSH key. Do not send passwords, MFA or recovery codes, payment details, or any secret.

## VPS and restore

Operator: provision the recipient-approved VPS, apply base OS hardening, create a private administrative path, and transfer SSH access without retaining recipient credentials. Recipient owns account, billing, MFA, model-provider consent, Discord ownership, and final acceptance.

Operator: copy the verified archive to the new VPS; compare its SHA-256 file; run the documented isolated restore verification; then rebuild/install Hermes from the included, verified source bundle. Use supported interactive authentication for providers. Do not use browser-stored passwords/autofill or a Hermes/browser vault as a credential source; BWS is the secret source where the recipient chooses it.

Recipient: create a private Discord server with owner-only access, complete supported interactive provider login, and approve only the four initial profiles. Keep profile homes isolated. Create the Brain OS vault from the starter structure.

## Ongoing ownership

Recipient owns backups, restore tests, rollbacks, updates, provider costs, support decisions, GitHub/main and production authority. Operator documents the current archive checksum, runs the acceptance checklist, and hands over only after the recipient confirms SSH, profile isolation, private Discord access, provider login, Brain OS filing, backup restore, and rollback procedure. Post-handoff self-build work is optional and must be separately admitted.
