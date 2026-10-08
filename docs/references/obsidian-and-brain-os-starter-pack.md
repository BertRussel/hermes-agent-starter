---
tags:
  - type/research
  - domain/brainos
  - domain/knowledge-management
  - domain/ai-agents
  - status/reviewed
  - safety/no-secrets
---
# Obsidian and Brain OS Organization Starter Pack for AI Agents

**Date:** 2026-10-02  
**Audience:** people building an AI agent that needs durable knowledge, projects, tasks, research, procedures, decisions, and operational continuity  
**Sharing boundary:** public-safe architecture. It contains no credentials, private business records, customer data, proprietary account details, or private runtime state.

## Executive recommendation

Do not treat Obsidian as a folder where an agent dumps every conversation and generated file. Treat it as the **human-readable knowledge and navigation layer** of a larger operating system.

Our working model is:

```text
Home = front door
Current State = what is true now
Task List = what needs doing
Project Registry = where project work lives
Research Index = what has already been investigated
Reference Index = reusable procedures and standards
Profile/Agent Hub = who does what and where their work belongs
Domain Hubs = routing maps for complicated operating areas
Decision Journal = why durable choices were made
Inbox = temporary intake, not permanent storage
GitHub = code source of truth
Document/file systems = canonical binaries and human working files
```

The core lesson is:

> A useful agent vault is not defined by how many notes it contains. It is defined by whether the agent can quickly find the authoritative source, distinguish current truth from history, route new material correctly, and leave durable work discoverable for the next session.

## 1. What we built and why

We built Brain OS as a layered system because one memory mechanism cannot safely do every job.

### Layer 1 — The agent's compact memory

Use agent memory only for small, stable facts that apply across nearly every session:

- who the owner is;
- enduring communication preferences;
- broad standing boundaries;
- stable environmental facts that are genuinely universal.

Do **not** use global memory for:

- full project histories;
- long procedures;
- research notes;
- temporary task status;
- raw source material;
- customer or financial records;
- every lesson from every task.

Why: global memory is always loaded. If it becomes a database, it wastes context and lets stale project detail distort unrelated work.

### Layer 2 — Skills as executable procedural knowledge

A skill tells the agent **how to perform a recurring class of work**. It should contain triggers, prerequisites, steps, safety boundaries, QA gates, failure behavior, and delivery standards.

Examples include skills for:

- Obsidian filing;
- source ingestion;
- spreadsheet QA;
- browser operations;
- code review;
- email operations;
- research;
- visual production.

A skill is not the live status page for a business system and not the storage location for project-specific facts.

### Layer 3 — Obsidian as the durable knowledge map

Obsidian holds the readable context around work:

- current operating truth;
- project overviews and evidence;
- decisions and their reasoning;
- durable research syntheses;
- reusable runbooks and standards;
- pointers to canonical code, files, archives, and cloud records.

It is the map, not necessarily the warehouse.

### Layer 4 — External systems retain their natural authority

We deliberately do not force everything into Markdown:

- source code remains in Git/GitHub;
- editable business documents remain in the appropriate document system;
- shared staff files remain in the approved collaboration platform;
- indexed/OCR documents remain in the document archive;
- credentials remain in the approved secrets system;
- runtime logs, sessions, databases, and caches remain runtime state;
- large media and source assets remain in their canonical file store.

Obsidian stores the durable pointer, context, owner, status, and retrieval route.

## 2. The top-level vault architecture

A practical starter structure is:

```text
Brain-OS/
  00-MOC/
    Brain OS Home.md
    Current State.md
    Task List Hub.md
    Agent Profiles MOC.md

  01-Strategy/
    Goals/
    Roadmaps/

  02-Development/
    Projects/
      Project Registry.md
      <Project Name>/
        00-Overview.md
        INDEX.md                  # only when complexity justifies it
        Decisions/
        Evidence/
    Decision-Journal/
      Decision Journal Index.md
    Patterns/
    Anti-Patterns/
    Lessons-Learned/

  03-Research/
    Research Index.md
    Topics/
    Technology/
    Business-Domain/

  04-Archive/
    Historical or superseded notes

  05-Reference/
    Reference Index.md
    Procedures/
    Checklists/
    Templates/
    Guides/

  06-Inbox/
    README.md
    Sources/
    Temporary captures and unprocessed material
```

The numbering keeps high-value navigation areas in a stable order. The exact names matter less than keeping each layer's responsibility unambiguous.

## 3. The essential control notes

### A. Brain OS Home — the front door

The Home note should be short. It points to the few places needed to orient the owner or agent:

- Current State;
- Task List;
- Project Registry;
- Research Index;
- Reference Index;
- Agent/Profile Hub;
- important operating hubs;
- maintenance and recovery entry points.

It is a launchpad, not a duplicate of every index.

### B. Current State — what is true now

Current State is the durable system continuity note. It answers:

- What systems are active?
- What is configured and verified?
- What is paused, degraded, or blocked?
- What is the current authoritative route?
- Where are the restore and operating procedures?
- What changed recently that future sessions must know?

This note should describe **state**, not become a giant task list or event diary.

Good entry:

```text
Document archive: active; canonical intake procedure at [[Document Intake Runbook]].
```

Bad entry:

```text
On Tuesday we tried three commands, then discussed another option...
```

Keep detailed evidence in the owning project or runbook and link to it.

### C. Task List Hub — what needs doing

Use one human-facing durable task list. Organize it by real operating areas, for example:

- business operations;
- agent/Brain OS;
- personal;
- coding projects;
- work already underway;
- waiting for owner approval;
- parked/not active.

Supporting detail can live in a backlog, project note, issue tracker, or Kanban system, but those must not quietly become competing owner-facing task lists.

Rules:

- one task appears once in its canonical owner-facing location;
- status belongs with the task;
- blocked work names the gate;
- completed work is removed or moved to a compact history;
- session-local todos are scaffolding, not durable task authority.

### D. Project Registry — what projects exist

The registry is a sparse directory, not a project-management database. Each entry should include:

- project name;
- status;
- one-sentence purpose;
- link to the project overview;
- code repository when applicable;
- canonical storage pointers;
- archive/superseded status when relevant.

Use one project folder per durable project. Keep implementation notes with the project instead of scattering them across general research and references.

### E. Research Index — what has already been investigated

The Research Index prevents redundant research. Every durable synthesis should be listed with:

- a clear title;
- date when material;
- one-line finding or decision;
- link to the full note.

Raw captures remain in Inbox/Sources. Research notes should synthesize evidence, caveats, and conclusions rather than merely repeat links.

Before starting a broad research pass, the agent checks this index first.

### F. Reference Index — how recurring work is done

The Reference Index routes to reusable:

- procedures;
- runbooks;
- standards;
- checklists;
- templates;
- operating hubs.

Project-specific facts do not belong here unless generalized into a reusable pattern.

### G. Agent/Profile MOC — who does what

For a multi-profile agent system, create one Map of Content that identifies:

- the primary controller/orchestrator;
- research profile;
- implementation/maker profile;
- independent review profile;
- creative profile;
- each role's authority and restrictions;
- where each role's durable output is filed;
- which profile owns final decisions;
- which profile must remain independent;
- links to exact role procedures and recovery notes.

The profile hub is a navigation and responsibility map. It must not imply that every profile has the same tools, credentials, authority, or access.

## 4. What a hub means in our system

A **hub** is a central routing and operating map for a broad domain. It answers “where do I start, which route applies, what is currently true, and what requires approval?”

A hub is different from a skill and a runbook:

```text
Skill = how the agent executes a class of task
Hub = where the operating routes, boundaries, state, and runbooks meet
Runbook = exact repeatable workflow for one system or task
Project note = context and evidence for one project
Current State = verified live system truth
Task List = work still to do
```

### When to create a hub

Create one when at least one of these is true:

- several tools or sub-routes exist;
- the domain crosses multiple storage or software systems;
- security, production, financial, legal, or publication boundaries matter;
- several workflows depend on the same current state;
- the owner or agent repeatedly rediscovers the setup;
- a single index would otherwise contain too much explanatory logic.

Good hub candidates:

- storage and file routing;
- email operations;
- browser operations;
- GitHub and backup;
- automation and scheduled jobs;
- skill routing;
- agent profiles;
- legal-document operations;
- finance/tax operations when several recurring workflows justify it.

### When not to create a hub

Do not create a hub merely because a topic exists.

Use a project folder or single canonical note when:

- there is only one active workflow;
- the topic is narrow or temporary;
- the material is sensitive and best kept in a bounded project area;
- a hub would duplicate an existing index;
- the structure would be cosmetic rather than solve navigation friction.

Our finance and tax material, for example, is currently handled through bounded project/domain notes and canonical records. If recurring tax preparation, source collection, deadlines, accountant exchanges, multiple entities, and annual runbooks grow complex enough, then a dedicated Tax Operations Hub becomes justified. The architecture supports that evolution without pretending the hub already exists.

## 5. Recommended hub template

```markdown
# <Domain> Operations Hub

## Purpose
What this hub controls and what it does not control.

## Bottom line
The default route in two or three lines.

## Current state
What is active, paused, degraded, unverified, or historical.

## Routing matrix
| Request type | Canonical system | Procedure | Owner/approval |

## Safe default actions
Read-only or reversible actions the agent may take routinely.

## Approval-required actions
Production, publication, credentials, payments, legal filings,
destructive changes, account changes, or external communication.

## Source-of-truth map
Which system owns notes, code, original files, shared files,
archives, credentials, and runtime evidence.

## Runbooks and checklists
Links only; do not duplicate their full instructions here.

## Evidence standard
What must be verified before claiming success.

## Recovery / rollback
How to recover or where the recovery procedure lives.

## Maintenance rule
When this hub should be updated and by whom.
```

A hub should be concise enough to scan. Exact workflows belong in linked runbooks.

## 6. Project organization

For a durable project, use three anchors when applicable:

1. **Overview** — purpose, status, owners, canonical systems, navigation.
2. **System/Brand/Architecture note** — durable rules and accepted decisions.
3. **Asset or Evidence Index** — canonical source files, outputs, manifests, and missing pieces.

Example:

```text
02-Development/Projects/Example Project/
  00-Overview.md
  Architecture/
    Accepted Architecture.md
  Decisions/
    Decision Log.md
  Evidence/
    Acceptance Evidence Index.md
  Brand/
    Brand System.md
    Asset Index.md
```

### Sparse `INDEX.md` files

Add a folder-level `INDEX.md` only when the agent repeatedly:

- gets lost;
- opens stale files;
- cannot distinguish canonical from archived material;
- needs several reads to find the start point.

A useful sparse index contains:

```text
Purpose
Where to start
Canonical files
Active versus archive boundaries
Do not use unless historical
Related research and procedures
```

Do not add an index to every folder. Excess indexes create another maintenance burden and dilute authority.

## 7. The filing decision tree

When new material arrives, classify it before saving.

```text
Is it raw or unprocessed?
  → 06-Inbox/

Is it evidence-backed synthesis useful beyond one project?
  → 03-Research/ + Research Index

Is it specific to implementing or operating one project?
  → 02-Development/Projects/<Project>/

Is it a durable decision and its rationale?
  → Decision Journal + owning project link

Is it a reusable procedure, runbook, standard, checklist, or template?
  → 05-Reference/ + Reference Index or domain hub

Is it source code?
  → Git repository; put only context/pointers in Obsidian

Is it a binary/original/shared business file?
  → canonical file/document system; add a Brain OS pointer

Is it temporary generated output?
  → working directory; promote and link only if worth retaining
```

Universal rule:

> If an artifact is worth retaining after the session, it must be discoverable from a project, subject hub, registry, or index—not only through filesystem search or chat history.

## 8. Raw capture, research, decision, and procedure are different things

One of the most important parts of our setup is preserving these distinctions.

### Raw source capture

Records what an external source said:

- URL or original identifier;
- author/publisher;
- date and retrieval method;
- captured text or artifact;
- limitations.

It has no automatic authority over the system.

### Durable research

Compares sources and states:

- what is supported;
- what is uncertain;
- what conflicts;
- what is useful;
- what is rejected;
- what decision or next experiment follows.

### Decision record

Records:

- the question;
- chosen option;
- reasons and tradeoffs;
- authority/approver;
- date;
- consequences;
- reversal conditions.

### Procedure/runbook

Tells the agent how to perform the accepted workflow:

- prerequisites;
- exact sequence;
- safety boundaries;
- evidence;
- failure behavior;
- rollback.

This separation prevents an external article from silently becoming an operating rule and prevents historical discussion from being mistaken for current procedure.

## 9. Authority and conflict resolution

Every important fact should have an owning source.

A useful authority order is:

1. exact original artifact or live verified system state;
2. accepted project decision/contract;
3. current runbook or procedure;
4. durable research synthesis;
5. raw source capture;
6. chat/session recollection.

When two notes conflict, do not average them. Determine:

- which note owns the fact;
- which is newer;
- whether the newer note explicitly supersedes the older one;
- whether the claim is historical, proposed, accepted, or verified;
- whether a live readback is needed.

Mark obsolete material as superseded or move it to an archive boundary. Do not delete useful provenance merely to make the graph look clean.

## 10. Tags, folders, links, and graph view

Use each mechanism for a distinct purpose:

- **Folders:** source-of-truth structure and lifecycle.
- **Wikilinks:** relationships and navigation.
- **Controlled tags:** metadata and filters.
- **Hubs/indexes:** curated entry points.
- **Graph groups/colors:** optional visualization derived from tags or folders.

A compact tag taxonomy can use:

```text
type/research
type/procedure
type/project
type/decision

domain/brainos
domain/finance
domain/marketing

status/draft
status/active
status/reviewed
status/superseded
status/blocked

safety/approval-required
safety/credentials
safety/pii
safety/production
```

Do not let free-form tags multiply into a second folder tree. Graph colors are views, not authority.

## 11. Keeping track of agents and specialist profiles

A multi-agent system needs both role documentation and work-routing rules.

For every profile record:

- role and purpose;
- allowed work;
- prohibited work;
- tool and credential boundaries;
- expected inputs;
- required outputs/evidence;
- where output is filed;
- who reviews it;
- escalation and stop conditions;
- recovery route;
- current versus historical model/configuration status, if relevant.

Recommended responsibility pattern:

```text
Controller/owner agent
  → understands the request, sets scope, owns final decision

Research agent
  → gathers and synthesizes evidence, updates research index

Maker/implementation agent
  → produces bounded artifacts or code, never self-accepts

Independent verifier/reviewer
  → reviews exact immutable output, cannot quietly modify it

Creative specialist
  → creates editable visual candidates with rendered evidence
```

The vault tracks roles and evidence. The runtime system enforces actual tool, credential, and action authority.

## 12. Finance, tax, legal, and other sensitive domains

Sensitive domains should be organized without copying confidential records into broad general notes.

Recommended structure:

```text
02-Development/Projects/Personal Finance/
  00-Overview.md
  Tax Year 20XX/
    Reconciliation.md
    Missing Items.md
    Accountant Questions.md
    Filing Status.md
```

Or, when complexity justifies a hub:

```text
05-Reference/Procedures/Tax Operations Hub.md
02-Development/Projects/Finance and Tax/
  Tax Year 20XX/
```

The hub contains routing, deadlines, systems, approval rules, and runbook links. Original tax documents remain in the approved encrypted/document system. Obsidian contains minimum necessary context and pointers.

Never put in a public/shared starter:

- tax IDs;
- bank details;
- credentials;
- full returns;
- customer records;
- private legal documents;
- private account URLs;
- fabricated financial status.

## 13. Maintenance and QA

A knowledge system must be tested like any other operating system.

### On every durable note change

- confirm correct folder/class;
- add frontmatter only from the controlled taxonomy;
- add the note to its owning index or hub;
- link related canonical notes;
- avoid duplicate task/status authority;
- run link/index checks;
- report the exact saved path.

### Periodic checks

- unlinked durable notes;
- missing titles;
- broken wikilinks;
- stale or duplicate hubs;
- Inbox material that should be promoted or discarded;
- conflicting Current State claims;
- completed tasks left active;
- project folders without a registry entry;
- research notes absent from Research Index;
- procedures absent from Reference Index;
- obsolete files still presented as canonical;
- binaries/source trees incorrectly stored in Obsidian;
- private data in public-safe notes.

### Evidence standard

A successful write means more than “the file command returned success.” Verify:

- the exact note exists;
- the intended index links to it;
- the indexer/link checker passes;
- no duplicate authority was created;
- a new session can find it by starting from Home or the owning hub.

## 14. What another agent should implement first

Do not recreate our entire mature vault on day one. Build the smallest useful loop.

### Phase 1 — Seven-note starter

Create:

```text
00-MOC/Brain OS Home.md
00-MOC/Current State.md
00-MOC/Task List Hub.md
02-Development/Projects/Project Registry.md
02-Development/Decision-Journal/Decision Journal Index.md
03-Research/Research Index.md
05-Reference/Reference Index.md
06-Inbox/README.md
```

Technically this is eight files because task continuity is worth making explicit from the beginning.

### Phase 2 — Filing rules

Teach the agent the decision tree:

- raw;
- research;
- project;
- decision;
- reusable reference;
- code;
- external file;
- temporary output.

Require every retained artifact to gain a pointer from an index, hub, or project overview.

### Phase 3 — First real project

Create one project overview, one accepted decision, one evidence note, and links back to Project Registry. Prove a fresh session can navigate to the canonical material without searching the entire vault.

### Phase 4 — First operating hub

Create a hub only for the first domain that genuinely has several tools/routes or meaningful safety boundaries. Storage/file routing is usually a strong first choice.

### Phase 5 — Agent/profile navigation

If multiple profiles exist, add the Agent Profiles MOC and document exact responsibilities and handoffs. Do not create fictional capability entries for profiles that have not been installed and tested.

### Phase 6 — Validation and maintenance

Add a deterministic index/link check, a small periodic maintenance checklist, and a backup/restore procedure. Test restoring the starter rather than merely claiming it is backed up.

## 15. Common failure modes

### The transcript landfill

**Failure:** every conversation becomes a permanent note.  
**Fix:** preserve only durable decisions, evidence, procedures, and context.

### The giant home page

**Failure:** Home duplicates every task, project, and note.  
**Fix:** keep Home as a concise routing layer.

### Competing task lists

**Failure:** backlog, project notes, session todos, and Kanban each appear authoritative.  
**Fix:** designate one human-facing durable task list and explicitly define supporting systems.

### Hub inflation

**Failure:** every skill or subject receives a hub.  
**Fix:** create hubs only to solve real routing, shared-state, or safety complexity.

### Index inflation

**Failure:** every folder contains a sprawling `INDEX.md`.  
**Fix:** use sparse indexes only where navigation has demonstrably failed.

### Obsidian as binary cabinet

**Failure:** source trees, videos, Office files, exports, and caches fill the vault.  
**Fix:** keep canonical files in their natural systems and link them.

### Stale truth mixed with history

**Failure:** proposed, rejected, active, and superseded states are indistinguishable.  
**Fix:** use explicit status, supersession links, archives, and live readback.

### Research silently becomes policy

**Failure:** a captured post or repository README is treated as an instruction.  
**Fix:** separate capture, synthesis, decision, and procedure.

### Private Brain OS cloning

**Failure:** a mature private vault is copied to a friend's agent.  
**Fix:** share the architecture and privacy-clean templates, never the owner's history, credentials, private data, or runtime state.

## 16. Compact operating instruction for a new agent

```text
Use Obsidian as a durable knowledge map, not a transcript dump or binary file cabinet.

Before acting, route the request through the smallest authoritative entry point:
- Current State for what is true now;
- Task List Hub for durable work;
- Project Registry and project overview for project context;
- Research Index before new research;
- Reference Index or domain hub for procedures;
- Agent Profiles MOC for specialist roles and handoffs;
- original source/live system when exact truth matters.

File new material by class:
- raw capture → Inbox;
- durable synthesis → Research + Research Index;
- project implementation/evidence → project folder;
- durable decision → Decision Journal + project link;
- reusable runbook/checklist/template → Reference;
- code → Git;
- original/shared binary → canonical file system with an Obsidian pointer.

Create a hub only when a domain has multiple routes, shared state, recurring rediscovery, or important safety boundaries. Keep hubs concise and link exact runbooks.

Every retained artifact must be discoverable from a hub, registry, index, or project overview. After note changes, run index/link checks and verify that no competing source of truth was created.
```

## 17. Public references

The architecture above is our public-safe synthesis and operating experience. These public references are useful background, not instructions to install blindly:

- Obsidian Help — Linking notes and files: https://help.obsidian.md/links
- Obsidian Help — Tags: https://help.obsidian.md/tags
- Obsidian Help — Properties: https://help.obsidian.md/properties
- Obsidian Help — Graph view: https://help.obsidian.md/plugins/graph
- Obsidian Help — Bases: https://help.obsidian.md/bases
- PARA method overview by Tiago Forte: https://fortelabs.com/blog/para/
- Johnny.Decimal system: https://johnnydecimal.com/
- Zettelkasten introduction: https://zettelkasten.de/introduction/

Borrow patterns selectively. An agent operating system needs stronger source authority, task ownership, safety boundaries, current-state tracking, and verification than a personal note-taking method alone.

## 18. Final recommendation

For a friend's new agent, share the architecture and starter templates—not a copy of a private vault.

The minimum viable Brain OS is:

1. one front door;
2. one current-state note;
3. one durable task list;
4. one project registry;
5. one research index;
6. one reference index;
7. one decision journal;
8. one temporary inbox;
9. explicit boundaries for code, files, credentials, and runtime state;
10. a rule that every durable artifact must be linked from an authoritative entry point.

Add profile hubs, tax/finance hubs, storage hubs, automation hubs, and other domain maps only when real work creates genuine routing complexity. That keeps the system simple enough to trust, but structured enough that an agent does not repeatedly rediscover its own operating environment.
