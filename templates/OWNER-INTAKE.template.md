# Personal Agent — Owner Intake Template

Complete this private form before customizing the agent files.

The owner supplies personal truth, preferences and authority. A trusted setup agent uses the answers to generate:

- `SOUL.md`
- `USER.md`
- `MEMORY.md`
- `PRIVATE-AGENT-BIBLE.md`
- `BOOTSTRAP-PROMPT.md`

## Answer rules

Use one of these when appropriate:

- `UNKNOWN` — not known or not needed yet.
- `NOT APPLICABLE` — does not apply.
- `USE RECOMMENDED DEFAULT` — accept the default shown.
- `AGENT TO DISCOVER` — the setup agent may verify this technical fact from the recipient system.

Never enter passwords, tokens, API keys, TOTP seeds, recovery codes, cookies, payment-card data, private keys or OAuth credentials.

Keep the completed form outside the public repository.

---

# A. Owner identity

## 1. Owner’s full name

**Fields:** `OWNER_NAME`, `OWNER_FULL_NAME`  
**Description:** The person who owns the agent and retains consequential authority.  
**Answer:**


## 2. Owner’s first name

**Field:** `OWNER_FIRST_NAME`  
**Description:** Used where a shorter reference is needed.  
**Answer:**


## 3. Preferred form of address

**Field:** `OWNER_FORM_OF_ADDRESS`  
**Description:** What the agent should normally call the owner.  
**Answer:**


## 4. Timezone

**Fields:** `OWNER_TIMEZONE`, `TIMEZONE`  
**Description:** Use an IANA timezone such as `America/Los_Angeles`.  
**Answer:**


## 5. Optional identity details

**Used in:** `USER.md`  
**Description:** Record only details the owner wants used across sessions. Do not enter a home address.

**Pronouns:**  
**Primary language:**  
**Other working languages:**  
**General city/region, only if useful:**

---

# B. Agent identity and personality

## 6. Agent name

**Field:** `AGENT_NAME`  
**Description:** The personal name of the primary human-facing agent.  
**Answer:**


## 7. Inspirational person or figure

**Fields:** `AGENT_INSPIRATION`, `INSPIRATIONAL_PERSON`, `INSPIRATIONAL_PERSON_OR_FIGURE`  
**Description:** The person, figure, character or tradition that inspires the agent’s personality. Inspiration shapes character only; it never grants authority or permission to impersonate the inspiration.  
**Answer:**


## 8. Inspiration description

**Field:** `AGENT_INSPIRATION_DESCRIPTION`  
**Description:** One sentence explaining who or what the inspiration represents.  
**Answer:**


## 9. Personality traits

**Fields:** `AGENT_INSPIRATION_TRAITS`, `INSPIRATION_TRAITS`, `PERSONALITY_TRAITS`  
**Description:** Traits the agent should express naturally and styles it should avoid.  
**Traits to express:**  
**Traits or styles to avoid:**


## 10. Character metaphor

**Field:** `AGENT_CHARACTER_METAPHOR`  
**Description:** A short metaphor for how the agent should feel to work with. Example: “A calm operations room: clear, prepared and steady.”  
**Answer:**


## 11. Relationship to the owner

**Field:** `OWNER_RELATIONSHIP`  
**Description:** Examples include operating partner, chief of staff, project organizer, technical coordinator or confidant.  
**Answer:**


## 12. Deployment description

**Field:** `DEPLOYMENT_DESCRIPTION`  
**Recommended default:** `a private owner-operated Hermes Agent system`  
**Answer:**

---

# C. Purpose and work

## 13. Primary mission

**Field:** `PRIMARY_MISSION`  
**Description:** The most important long-term outcome the agent should support.  
**Answer:**


## 14. Secondary mission

**Field:** `SECONDARY_MISSION`  
**Answer:**


## 15. Tertiary mission

**Field:** `TERTIARY_MISSION`  
**Answer:**


## 16. Mission summary

**Field:** `OWNER_MISSIONS`  
**Description:** A short combined summary of the owner’s goals for the agent.  
**Answer:**


## 17. Owner’s stable role or context

**Field:** `OWNER_ROLE_OR_CONTEXT`  
**Description:** Durable professional or personal context useful across sessions—not a biography.  
**Answer:**


## 18. Stable support priorities

**Field:** `OWNER_SUPPORT_PRIORITIES`  
**Description:** Long-lived categories, not today’s task list.  
**Answers:**

- 
- 
- 

## 19. Organizations and operating domains

**Fields:** `RECIPIENT_SPECIFIC_DOMAINS`, `ORGANIZATIONS_AND_DOMAINS`  
**Description:** Businesses, charities, professions, programs or recurring domains the agent should understand.

- **Organization/domain:**  
  **Owner’s role:**  
  **Agent’s intended support:**

- **Organization/domain:**  
  **Owner’s role:**  
  **Agent’s intended support:**

## 20. Stable collaborators and projects

**Used in:** `USER.md`  
**Primary organization or business:**  
**Other durable organizations:**  
**Long-lived project families:**  
**Key collaborators and relationship, only when needed and approved:**

Do not include sensitive histories or full contact records.

---

# D. Communication and working style

## 21. Default response detail

**Used in:** `USER.md`  
**Choices:** concise, balanced or detailed.  
**Answer:**


## 22. Decision format

**Used in:** `USER.md`  
**Recommended default:** Explain first, compare tradeoffs, recommend a path, then use a real picker when the owner must choose.  
**Answer:**


## 23. Technical explanation style

**Used in:** `USER.md`  
**Choices:** plain language first, technical first or mixed.  
**Answer:**


## 24. Status updates

**Used in:** `USER.md`  
**Description:** Preferred length and frequency for ordinary progress updates.  
**Answer:**


## 25. Writing voice

**Field:** `OWNER_WRITING_VOICE`  
**Description:** Stable drafting characteristics. Use `UNKNOWN` until examples are approved.  
**Answer:**


## 26. Terms and forms of address

**Used in:** `USER.md`  
**Terms, names or nicknames to use:**  
**Terms or styles to avoid:**


## 27. Level of initiative

**Used in:** `USER.md`  
**Choices:** low, balanced or high for safe and reversible work.  
**Answer:**


## 28. Good support and recurring friction

**Used in:** `USER.md`  
**Good support feels like:**  
**The owner prefers to handle personally:**  
**Things that consistently create friction:**

---

# E. Authority, privacy and accessibility

## 29. Approval boundaries

**Field:** `APPROVAL_BOUNDARIES`  
**Description:** Actions that always require owner approval. At minimum consider sending, publishing, scheduling, purchases, payments, accounts, credentials, permissions, production, deployment, deletion and recurring automation.

**Always requires approval:**

- 
- 
- 

**Standing authority already granted, if any:**

- 

## 30. Explicitly prohibited actions

**Used in:** `USER.md`

- 
- 

## 31. Gateway lifecycle policy

**Field:** `GATEWAY_LIFECYCLE_POLICY`  
**Description:** Who may start, stop, restart, reload or signal the Hermes Gateway.  
**Answer:**


## 32. Final approvers

**Used in:** `USER.md`  
**Description:** Name the person or role with final authority. Do not infer it.

- **Domain:**  
  **Final approver:**

- **Domain:**  
  **Final approver:**

## 33. Restricted data classes

**Field:** `RESTRICTED_DATA_CLASSES`  
**Description:** Categories requiring special handling, limited access or human review.

- 
- 
- 

## 34. Sensitive-domain values

**Field:** `OWNER_SENSITIVE_DOMAIN_VALUES`  
**Description:** Values such as dignity, consent, privacy, accessibility, safeguarding or confidentiality.  
**Answer:**


## 35. Sensitive-domain guidance

**Field:** `RECIPIENT_SENSITIVE_DOMAIN_GUIDANCE`  
**Description:** Rules for regulated, vulnerable-person, legal, medical, disability, safeguarding, financial or other sensitive work. Do not include individual case details.  
**Answer:**


## 36. Accessibility and inclusion

**Used in:** `USER.md`  
**Reading or visual-access needs:**  
**Caption, transcript or alt-text preference:**  
**Person-first or identity-first language preference:**  
**Cultural, religious or identity considerations to respect:**  
**Areas requiring qualified human review:**

Do not infer disability, diagnosis, identity, legal status or support needs.

---

# F. Platforms and sources of truth

The owner may answer directly or use `AGENT TO DISCOVER` when the setup agent can verify the fact safely.

## 37. Primary messaging platform

**Field:** `PRIMARY_MESSAGING_PLATFORM`  
**Answer:**


## 38. Primary cloud platform

**Fields:** `PRIMARY_CLOUD_PLATFORM`, `CLOUD_PLATFORM`  
**Answer:**


## 39. Primary email and workspace

**Field:** `PRIMARY_EMAIL_AND_WORKSPACE`  
**Description:** Provider and approved account label only—never credentials.  
**Provider:**  
**Approved account label, if needed:**


## 40. Scheduling preferences

**Field:** `OWNER_SCHEDULING_PREFERENCES`  
**Answer:**


## 41. Knowledge-system name

**Field:** `KNOWLEDGE_SYSTEM_NAME`  
**Recommended default:** `Obsidian Brain OS`  
**Answer:**


## 42. Brain OS path

**Field:** `BRAIN_OS_PATH`  
**Answer:**


## 43. Original-file source of truth

**Field:** `EXACT_FILE_STORE`  
**Description:** Approved home for original files and human-facing assets.  
**Answer:**


## 44. Code source

**Field:** `CODE_SOURCE_NAME`  
**Recommended default:** `GitHub`  
**Answer:**


## 45. Git account or organization

**Field:** `GIT_ACCOUNT_OR_ORGANIZATION`  
**Description:** Approved identity or organization name—never a token.  
**Answer:**


## 46. Owner-visible task source

**Used in:** `USER.md`  
**Recommended default:** `Task List Hub`  
**Answer:**


## 47. Naming and filing

**Used in:** `USER.md`  
**Naming conventions:**  
**Filing conventions or owning procedure:**


## 48. Credential source

**Fields:** `CREDENTIAL_SOURCE_NAME`, `REGISTERED_CREDENTIAL_SOURCE`  
**Recommended contract:** `Bitwarden Secrets Manager (BWS)` through an approved controlled in-memory route.  
**Answer:**

Never put credentials in this intake.

## 49. Website access registry

**Field:** `APPROVED_WEBSITE_REGISTRY`  
**Recommended default:** `Approved Website Access Registry`  
**Answer:**


## 50. Known website identities

**Used to build:** Approved Website Access Registry  
**Description:** Record labels and authority only—never passwords or MFA values.

- **Service:**  
  **Identity label:**  
  **Purpose:**  
  **Read actions allowed:**  
  **Writes requiring approval:**  
  **Prohibited actions:**  
  **Human MFA/passkey gate, if known:**

## 51. Model and budget preferences

**Field:** `MODEL_PROVIDER_BUDGET_PREFERENCES`  
**Preferred provider, if any:**  
**Preferred model, if any:**  
**Budget or cost boundary:**

---

# G. Recommended Brain OS defaults

Use `USE RECOMMENDED DEFAULT` or write a different approved value.

## 52. Folder paths

- **`INBOX_PATH`** — recommended `06-Inbox/`  
  **Answer:**

- **`PROJECTS_PATH`** — recommended `02-Development/Projects/`  
  **Answer:**

- **`RESEARCH_PATH`** — recommended `03-Research/`  
  **Answer:**

- **`RESEARCH_INDEX_PATH`** — recommended `03-Research/Research Index.md`  
  **Answer:**

- **`REFERENCE_PATH`** — recommended `05-Reference/`  
  **Answer:**

## 53. Hub and registry names

- **`CURRENT_STATE_NAME`** — recommended `Brain OS Current State`  
  **Answer:**

- **`TASK_LIST_NAME`** — recommended `Task List Hub`  
  **Answer:**

- **`MASTER_BACKLOG_NAME`** — recommended `Master Backlog`  
  **Answer:**

- **`PROJECT_REGISTRY_NAME`** — recommended `Project Registry`  
  **Answer:**

- **`REFERENCE_INDEX_NAME`** — recommended `Reference Index`  
  **Answer:**

- **`DECISION_JOURNAL_NAME`** — recommended `Decision Journal`  
  **Answer:**

---

# H. Setup-agent discovery fields

The human normally writes `AGENT TO DISCOVER`. The setup agent must verify each value from the live recipient system and show it before installation acceptance.

- **`PACKAGE_VERSION`** — exact starter version or baseline commit.  
  **Answer:** `AGENT TO DISCOVER`

- **`HERMES_HOME`** — absolute primary Hermes home.  
  **Answer:** `AGENT TO DISCOVER`

- **`WORKBENCH_ROOT`** — absolute root for specialist workbenches.  
  **Answer:** `AGENT TO DISCOVER`

- **`REBUILD_BACKUP_PATH`** — approved privacy-clean rebuild-backup location.  
  **Answer:** `AGENT TO DISCOVER`

- **`STORAGE_OPERATIONS_HUB`** — approved storage-procedure path.  
  **Answer:** `AGENT TO DISCOVER`

- **`CANONICAL_MULTI_AGENT_RUNBOOK`** — installed native launch/timing/review runbook path.  
  **Answer:** `AGENT TO DISCOVER`

- **`TIMING_ADAPTER`** — installed approved timing-adapter path.  
  **Answer:** `AGENT TO DISCOVER`

- **`ABSOLUTE_CONTROLLER_WORKSPACE`** — native controller workspace.  
  **Answer:** `AGENT TO DISCOVER`

## Specialist fields

Resolve separately for Forge, Verifier, Eve, Recon and Art.

- **`PROFILE_NAME`** — `forge`, `bert-verifier`, `eve`, `recon` or `art`.
- **`PROFILE_HOME`** — absolute Hermes profile home.
- **`PROFILE_LAUNCHER`** — exact scrubbed launcher path.
- **`MINIMAL_APPROVED_PATH`** — smallest verified executable path.

The setup agent must not copy these values from another installation.

---

# I. Runtime-only placeholders — owner does not fill

These appear in Bible command examples or per-task contracts. Do not globally replace them while rendering the private files.

```text
BOARD
BOUNDED_DURATION
BOUNDED_TURN_COUNT
CHAT_ID
DM_GROUP_CHANNEL_OR_THREAD
LIVE_VERSION_SPECIFIC_ARGUMENTS
OWNER_VISIBLE_OBJECTIVE
PLATFORM
ROOT_ID
SCOPE_AUTHORITY_GATES_VERIFICATION_AND_CLOSEOUT
STABLE_OBJECTIVE_KEY
TIMING_RUN_ID
```

Related example-only slots may include:

```text
Project
Project Name
absolute-worktree
ambiguity or safety brakes
authoritative artifact
behavior before fix
behavior after fix
exact-remote
full-sha
literal commands
literal paths or prefixes
one-coherent-slice
path and hash
paths or schemas
project
read-only literal commands
stable-id
```

The operating agent fills these only for the specific live workflow.

---

# J. Confirmed unknowns

Unknown is safer than a guess.

**Preferred working hours:**  
**Publication authority beyond default approval rules:**  
**Financial authority beyond default approval rules:**  
**Retention requirements:**  
**Active authorized website identities:**  
**Personal or family facts relevant across every session:**  
**Other facts intentionally left unknown:**

Sensitive details needed only for one project belong in that project’s restricted source—not in this intake, `USER.md` or general memory.

---

# K. Owner review

Before handoff, confirm:

- [ ] I supplied or approved the identity and personality answers.
- [ ] Inspiration and personality are not blank.
- [ ] Missions and support domains are accurate.
- [ ] Approval boundaries are explicit.
- [ ] Restricted-data rules are explicit or marked not applicable.
- [ ] Unknown facts remain unknown rather than guessed.
- [ ] No credentials, tokens, MFA material, cookies or recovery codes are present.
- [ ] No sensitive case records or unnecessary private details are present.
- [ ] This completed file will remain outside public Git history.

**Owner name:**  
**Review date:**  
**Approval statement:** `I approve this intake as the source for generating my private agent setup files.`

---

# L. Instructions for the setup agent

1. Read this intake before editing recipient-specific files.
2. Preserve the public baseline templates unchanged.
3. Create a private recipient overlay outside the public repository.
4. Treat this file as authority for identity, personality, missions, preferences, approval and sensitive-data fields.
5. Verify `AGENT TO DISCOVER` fields read-only from the recipient system.
6. Never infer human-owned answers from email, social media, browsing history or another person’s agent.
7. Apply aliases consistently:
   - `OWNER_NAME` and `OWNER_FULL_NAME` use the approved full name.
   - `OWNER_TIMEZONE` and `TIMEZONE` use the approved timezone.
   - `AGENT_INSPIRATION`, `INSPIRATIONAL_PERSON` and `INSPIRATIONAL_PERSON_OR_FIGURE` use the approved inspiration.
   - `AGENT_INSPIRATION_TRAITS`, `INSPIRATION_TRAITS` and `PERSONALITY_TRAITS` use the approved traits.
   - `PRIMARY_CLOUD_PLATFORM` and `CLOUD_PLATFORM` use the approved platform.
   - `CREDENTIAL_SOURCE_NAME` and `REGISTERED_CREDENTIAL_SOURCE` use the approved credential-source name.
8. Preserve runtime-only placeholders.
9. Keep `UNKNOWN` unconfirmed; never turn it into a factual preference.
10. Never copy credentials into rendered files.
11. Generate the five private files named at the top of this intake.
12. Produce a private crosswalk showing where each answer was used.
13. Run unresolved-placeholder, contradiction, privacy and secret scans.
14. Distinguish runtime example tokens from missing installation fields.
15. Show the owner a concise identity-and-authority summary and the exact rendered files.
16. Do not install until the owner approves the rendered private package.

## Required validation report

```text
Owner-required fields complete:
Owner-required fields still unknown:
Agent-discovered fields verified:
Agent-discovered fields unresolved:
Runtime-only placeholders preserved:
Conflicting aliases:
Secret scan:
Privacy scan:
Rendered file paths:
Rendered file hashes:
Owner approval status:
Installation status:
```

Prepared files are not installed files. Approval of the rendered package does not authorize credential changes, Gateway lifecycle actions, publication, production changes or other consequential actions unless separately stated.
