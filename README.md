# Hermes Agent Starter

A privacy-clean starting point for building an owner-operated Hermes agent with:

- one personalized primary agent;
- an Obsidian Brain OS;
- Forge, Verifier, Eve, Recon and Art specialist profiles;
- governed coding, creative, browser and credential workflows;
- human approval gates;
- backup, restore and verification guidance.

This repository contains **baseline source files and operating contracts**. It is not a credential bundle, a copy of another person’s agent or a one-command production installer.

## Status

> **Baseline candidate—not yet a complete accepted public installation or production-ready release.**

The files listed below are the owner-approved baseline. Other scripts, runtimes, modular chapters and canaries remain subject to their stated capability, compatibility, source-rights and clean-installation gates.

A file’s presence does not prove that its capability is installed or working.

## Start here

### Human owner

Read in this order:

1. [`docs/OVERVIEW.md`](docs/OVERVIEW.md)
2. [`templates/PRIVATE-AGENT-BIBLE.template.md`](templates/PRIVATE-AGENT-BIBLE.template.md)
3. [Human setup](#human-setup)
4. [`docs/CAPABILITY-STATUS.md`](docs/CAPABILITY-STATUS.md)
5. [`release-manifest.json`](release-manifest.json) and [`compatibility.json`](compatibility.json)

### Agent

Read [Agent instructions](#agent-instructions), then follow the customized private Bootstrap Prompt.

## Approved baseline

```text
docs/
  OVERVIEW.md

templates/
  SOUL.template.md
  USER.template.md
  MEMORY.template.md
  PRIVATE-AGENT-BIBLE.template.md
  BOOTSTRAP-PROMPT.template.md

profiles/
  owner-agent/SOUL.md
  forge/SOUL.md
  bert-verifier/SOUL.md
  eve/SOUL.md
  recon/SOUL.md
  art/SOUL.md
```

Fixed specialist mappings:

```text
Forge      → forge
Verifier   → bert-verifier
Eve        → eve
Recon      → recon
Art        → art
```

The primary agent’s name and personality are customized for each owner. Keep the specialist names fixed so the runbooks and evidence remain portable.

# Human setup

## 1. Make a private copy

Do not personalize the public files in place. Create a private folder outside the public clone and copy:

```text
SOUL.template.md                 → SOUL.md
USER.template.md                 → USER.md
MEMORY.template.md               → MEMORY.md
PRIVATE-AGENT-BIBLE.template.md  → PRIVATE-AGENT-BIBLE.md
BOOTSTRAP-PROMPT.template.md     → BOOTSTRAP-PROMPT.md
```

Keep the public baseline unchanged for clean comparison and updates.

## 2. Edit the private files

Use this order:

1. **`SOUL.md`** — agent name, owner relationship, inspiration, personality, missions, communication and authority.
2. **`USER.md`** — stable owner facts and preferences only.
3. **`MEMORY.md`** — stable approved facts only; no tasks, secrets or raw project state.
4. **`PRIVATE-AGENT-BIBLE.md`** — platforms, paths, privacy, storage, browser, credential and approval rules.
5. **`BOOTSTRAP-PROMPT.md`** — replace every required placeholder with the same approved values.

Personality and inspiration are required. Inspiration affects character only; it never grants authority.

## 3. Review before handoff

Confirm:

- every required placeholder is resolved;
- identity, personality, missions and timezone are correct;
- approval boundaries and restricted-data classes are explicit;
- Brain OS, file-store and platform paths are correct;
- the registered secret source follows the Bible’s contract;
- no password, token, TOTP value, cookie, recovery code or OAuth material is present;
- no other person’s identity, memory, session, browser profile, Brain OS or private data was copied.

Do not continue if `release-manifest.json` blocks a required component. Resolve the gate or use the repository for review only.

## 4. Activate the primary agent

1. Install Hermes through the current official route.
2. Check the current official docs and installed command help.
3. Back up any existing installation.
4. Install the approved private `SOUL.md` in the intended primary Hermes home.
5. Start a fresh session and verify the live identity and boundaries.
6. Review `USER.md` and `MEMORY.md` before installing them through the supported route.

A copied file is not proof that the live agent is using it.

## 5. Give the agent its setup instructions

Give the active primary agent read access to:

- the private customized folder;
- this repository;
- the approved Brain OS path;
- only the tools and paths needed for setup.

Then say:

> Read the installed Soul and the private setup folder. Follow `BOOTSTRAP-PROMPT.md`. Use `PRIVATE-AGENT-BIBLE.md` as the setup authority. Complete and verify every safe Day 1 step. Stop only at the human gates defined in those files.

Never paste secrets into chat. Enter them only through the approved secret manager or provider-owned OAuth flow.

## Human approval stays required

The owner must approve before:

- sending, scheduling or publishing;
- purchases, payments, refunds, donations or advertising spend;
- account, credential, MFA, OAuth, role or permission changes;
- legal commitments, partnerships or public events;
- Gateway lifecycle changes;
- push, merge, release, deployment, production or protected-branch changes;
- meaningful deletion, overwrite, rename or movement of owner files;
- recurring automation or consequential loops;
- restricted-data handling beyond the approved scope.

Authentication does not authorize post-login actions.

# Agent instructions

## Read order

Before changing state:

1. installed `SOUL.md`;
2. private `PRIVATE-AGENT-BIBLE.md`;
3. `docs/OVERVIEW.md`;
4. private `USER.md` and reviewed `MEMORY.md`;
5. `docs/CAPABILITY-STATUS.md`, `release-manifest.json`, `release-index.yaml` and `compatibility.json`;
6. private `BOOTSTRAP-PROMPT.md`;
7. the smallest relevant current skill or runbook for the next phase;
8. current official Hermes docs and installed help where version-sensitive.

Authority order:

- installed Soul → identity and authority;
- private Bible → setup and operating contract;
- Bootstrap → Day 1 sequence;
- capability and release files → what may honestly be claimed.

## Before acting

- Confirm the owner-visible outcome.
- Resolve placeholders from approved private files.
- Verify package hashes and release gates.
- Inspect the live recipient system safely.
- Do not expose secret values or credential identifiers.
- Do not install blocked or unresolved-rights components.
- Do not infer recipient acceptance from another system’s evidence.

Explain material owner decisions before using clarify controls. Use safe defaults for routine reversible technical details.

## Execute Day 1

Follow the private Bootstrap in order:

1. freeze the setup packet;
2. verify the package;
3. inspect recipient readiness;
4. verify primary identity and owner context;
5. prove private messaging;
6. establish storage ownership;
7. build or verify Brain OS;
8. create the Approved Website Access Registry;
9. create Forge, Verifier, Eve, Recon and Art from blank;
10. verify clarify behavior;
11. prove the native coding lifecycle;
12. prove the Art lifecycle;
13. prove browser and productivity access safely;
14. prove backup, restore and rollback;
15. produce the acceptance and handoff report.

Continue through safe reversible work without repeatedly asking the owner to continue. Stop only at a genuine approval, credential, account, human-verification, safety, unavailable-capability or unrecoverable gate.

## Non-negotiable agent rules

- Never claim a capability because its file exists.
- Never type secrets from the model, logs, shell history or chat.
- Never use browser storage, autofill or Hermes/browser vaults as credential sources.
- Never publish, send, overwrite the original, purchase, or make a production change without approval.
- Never launch named specialists outside the admitted native-root lifecycle.
- Never replace Forge, Verifier, Eve, Recon or Art with a generic delegate.
- Never create a competing scheduler, timing, identity or control plane.
- Never control the Gateway lifecycle from inside the active Gateway process.
- Keep code in Git, knowledge in Brain OS, originals in approved storage and secrets in the approved secret source.
- Verify external writes by reading back the exact target.
- Treat worker reports as claims requiring controller verification.
- Record exact versions, IDs, hashes, tests, limitations and rollback paths without secrets.

Use these states precisely:

```text
planned → prepared → installed → connected → runtime verified
→ profile integrated → benchmark ready → benchmark passed
→ owner approved → published → production-ready
```

Do not collapse them into “done.”

## What the Souls do not prove

The supplied Souls are role contracts. They do not alone prove profile identity, OS isolation, authentication, tool access, Art integration, coding-lifecycle safety, Bitwarden access, browser/cloud access, recovery, benchmark quality, owner acceptance or production readiness.

Use the Bible and Bootstrap acceptance gates and retain real recipient-system evidence.

# Updating or contributing

1. Keep recipient customization outside public Git history.
2. Change one source file at a time.
3. Review exact bytes before replacing an approved file.
4. Rerun affected privacy, profile, clarify, Art, coding, browser and recovery checks.
5. Update manifests, compatibility and provenance.
6. Preserve a tested rollback path.

Do not commit credentials, private identity state, sessions, memory, Brain OS contents, browser profiles, logs or business data.

Commit, push, pull request, merge, release and publication are separate actions. Main remains human-controlled. A baseline commit is not public-release acceptance.

See [`docs/START-HERE.md`](docs/START-HERE.md) for candidate-package navigation and [`docs/CAPABILITY-STATUS.md`](docs/CAPABILITY-STATUS.md) for remaining gates.
