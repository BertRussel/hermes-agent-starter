# Hermes Agent Starter

Build a private, owner-operated Hermes agent without copying another person’s identity, credentials, memory, sessions, or private knowledge.

This repository provides public source files, instructions, generic profiles, tests, and a Brain OS starter. It is **not** a credential bundle, a copy of a living agent, or a one-command production installer.

> **Status:** candidate source tree. A file being present does not prove that it is installed, connected, reviewed, or production-ready. Check [`docs/CAPABILITY-STATUS.md`](docs/CAPABILITY-STATUS.md) and [`release-manifest.json`](release-manifest.json) before installation.
>
> The portable compatibility probe targets publicly obtainable official Hermes; when a version is required, it expects it to be exactly `0.20.5`. The separate setup guide always points readers to current official installation instructions; do not treat a newer install as accepted by this candidate until compatibility is retested.

## The setup path

Follow these steps in order:

1. **Complete the private Owner Intake**

   Use [`docs/OWNER-INTAKE.pdf`](docs/OWNER-INTAKE.pdf), or the accessible Markdown form in [`docs/OWNER-INTAKE.md`](docs/OWNER-INTAKE.md). Keep the completed copy outside this public repository.

2. **Prepare an always-on server**

   Follow [`docs/ORACLE-VPS-SETUP.md`](docs/ORACLE-VPS-SETUP.md) for the economical Oracle Cloud route. You may use another suitable Linux server instead.

3. **Install and verify official Hermes**

   Follow [`docs/HERMES-SETUP.md`](docs/HERMES-SETUP.md). Get one normal command-line conversation working before adding messaging, profiles, or automation.

4. **Create a private Discord home**

   Follow [`docs/DISCORD-SETUP.md`](docs/DISCORD-SETUP.md) to create a private server, connect the bot, restrict access, and prove a private round trip.

5. **Generate the private agent files**

   Use the completed Owner Intake with the files in [`docs/templates/`](docs/templates/). Review the rendered `SOUL.md`, `USER.md`, `MEMORY.md`, private Agent Bible, and Bootstrap before installing them.

6. **Run the Day 1 Bootstrap**

   Give the active primary agent the rendered private Bootstrap based on [`docs/templates/BOOTSTRAP-PROMPT.template.md`](docs/templates/BOOTSTRAP-PROMPT.template.md). The agent discovers technical facts from the real system and verifies each safe setup stage.

7. **Accept only what was proved**

   Use the capability records, release manifest, tests, and recipient-generated evidence. Prepared files are not proof of a working installation.

## What you are building

- One personalized, owner-facing primary agent
- A durable Obsidian Brain OS
- Forge, Verifier, Eve, Recon, and Art specialist profiles
- Governed coding, research, creative, browser, and credential workflows
- Human approval gates for consequential actions
- Backup, restore, rollback, and acceptance evidence

The primary agent’s name and personality are owner-specific. The generic specialist names remain fixed:

```text
Forge      → forge
Verifier   → verifier
Eve        → eve
Recon      → recon
Art        → art
```

## Document directory

### Start and setup

- [`docs/OWNER-INTAKE.md`](docs/OWNER-INTAKE.md) — the seven owner answers
- [`docs/ORACLE-VPS-SETUP.md`](docs/ORACLE-VPS-SETUP.md) — economical Oracle VPS setup
- [`docs/HERMES-SETUP.md`](docs/HERMES-SETUP.md) — install and prove official Hermes
- [`docs/DISCORD-SETUP.md`](docs/DISCORD-SETUP.md) — private Discord server and bot setup
- [`docs/OVERVIEW.md`](docs/OVERVIEW.md) — system purpose and architecture
- [`docs/START-HERE.md`](docs/START-HERE.md) — operator path and acceptance order

### Templates and operation

- [`docs/templates/`](docs/templates/) — public inputs for generating private agent files
- [`docs/AGENT-BIBLE.md`](docs/AGENT-BIBLE.md) — full operating reference
- [`docs/WORKED-WORKFLOWS.md`](docs/WORKED-WORKFLOWS.md) — worked examples
- [`brain-os-starter/`](brain-os-starter/) — privacy-clean Obsidian starter
- [`profiles/`](profiles/) — generic specialist role distributions

### Trust and release records

- [`docs/CAPABILITY-STATUS.md`](docs/CAPABILITY-STATUS.md) — what is and is not proved
- [`docs/SOURCE-INVENTORY.md`](docs/SOURCE-INVENTORY.md) — browsable source map
- [`source-inventory.json`](source-inventory.json) — exact positive source allowlist
- [`release-manifest.json`](release-manifest.json) — release contents and rights
- [`PROVENANCE.md`](PROVENANCE.md) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) — source and licensing records
- [`SECURITY.md`](SECURITY.md) — vulnerability and security guidance
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution workflow

## Keep private material private

Never commit or publish:

- completed Owner Intake forms;
- rendered private Soul, User, Memory, Bible, or Bootstrap files;
- passwords, tokens, TOTP seeds or codes, recovery codes, cookies, or OAuth data;
- private Brain OS notes, sessions, logs, databases, browser profiles, or business records;
- another person’s identity, memories, account details, or live environment.

Keep public templates unchanged for comparison and updates. Generate recipient-specific files in a separate private folder.

## Repository workflow

Contributions target protected `dev`. Protected `main` remains human-controlled and receives only reviewed, accepted changes. Passing CI is necessary but does not replace privacy, provenance, security, exact-byte review, and owner acceptance.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the complete contribution route.
