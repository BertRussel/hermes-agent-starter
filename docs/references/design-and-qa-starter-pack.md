---
tags:
  - type/research
  - domain/design
  - domain/ai-agents
  - domain/qa
  - domain/office
  - status/reviewed
---
# Design and QA Starter Pack for AI Agents

**Date:** 2026-10-02  
**Audience:** builders configuring a new AI agent for user-facing design, Office artifacts, web/UI, email, and visual QA  
**Sharing boundary:** public-safe synthesis. No Par 4 confidential data, credentials, private assets, or proprietary business rules are included.

## Executive recommendation

Do not try to make an agent “good at design” with one giant aesthetic prompt. Give it a production system:

1. classify the artifact and audience;
2. distinguish **preserve**, **improve**, and **redesign**;
3. collect references and label what each reference controls;
4. define design tokens before component styling;
5. build in the artifact’s native editable format;
6. render the real output;
7. inspect it visually and structurally;
8. revise bounded defects;
9. use an independent critic for important work;
10. keep human approval for final creative direction and external release.

The strongest general lesson from the research is:

> Professional-looking agent output comes less from “taste prompts” than from reference authority, structured source, native editability, real rendering, adversarial QA, and bounded revision.

## 1. Core operating contract for the new agent

### A. Start with a design read

Before building, state:

```text
Reading this as: <artifact type> for <audience>, at <stage>, with <visual language>, in <preserve / improve / redesign> mode.
```

- **Preserve:** keep brand, information architecture, content and layout language; make the smallest requested change.
- **Improve:** retain identity while improving typography, hierarchy, spacing, contrast, imagery and states.
- **Redesign:** explore a new visual direction only when explicitly requested.

### B. Classify every reference

A supplied screenshot, website or asset must be labeled as one of:

- **canonical product/source** — structure or behavior to preserve;
- **brand authority** — controls identity, type, color or visual tone;
- **UI/design inspiration** — patterns to adapt, not product scope to invent;
- **targeted specification** — an explicit screen or artifact to reproduce faithfully;
- **negative reference** — shows what to avoid.

For multi-reference work, say which reference controls structure, which controls style, and which is inspiration only.

### C. Establish tokens before styling

For non-trivial work, define or recover:

- semantic color roles;
- display/body/mono typography;
- spacing scale;
- radius and depth rules;
- grid and safe margins;
- icon/illustration language;
- motion grammar;
- accessibility thresholds;
- explicit visual taboos.

Do not invent new brand-defining tokens when an approved design system already exists.

### D. Use a bounded build loop

```text
brief → references → structured/editable build → render → inspect → compare → retain or revert → focused revision
```

- Batch obvious first-pass defects rather than prompting one pixel at a time.
- Preserve accepted checkpoints.
- Change one coherent defect class per revision.
- A successful script or valid file does not prove good design.

### E. Require real visual QA

Inspect the artifact the user will actually see:

- browser screenshots at target breakpoints;
- PPTX/PDF slide renders and a whole-deck contact sheet;
- Excel at practical zoom plus print/PDF output;
- DOCX-exported PDF pages;
- email previews at desktop and phone widths;
- social graphics at phone size;
- animation/video contact sheets and key frames.

Source-code checks, geometry assertions and file validity support QA; they cannot replace visual judgment.

## 2. General design QA rubric

Review only relevant dimensions, but never skip the rendered artifact.

### First impression and hierarchy

- Is the purpose clear within two seconds?
- Does the eye land on the correct first element?
- Is there one dominant action or evidence object?
- Are headings conclusion-led rather than generic labels?

### Typography

- Clear scale and weight hierarchy.
- Consistent line height, measure and alignment.
- No clipping, awkward wrapping or display-font collisions.
- No gratuitous font mixing.
- Body text remains comfortably readable at the target device/print size.

### Layout and responsiveness

- Intentional grid, margins, gutters and alignment.
- Mobile is designed, not merely shrunk.
- No overflow, overlap, stranded labels or accidental whitespace.
- Repeated cards/components follow one geometry system.

### Color and accessibility

- Normal text contrast approximately 4.5:1; large text and non-text UI approximately 3:1.
- Color is not the only status cue.
- Visible keyboard focus and logical tab order for interactive work.
- Practical touch targets around 44×44 CSS px.
- Reduced-motion handling when motion exists.

### Content and truth

- Copy is specific, concise and free of generic AI filler.
- No fabricated metrics, screenshots, claims or precise-looking placeholders.
- Sources, periods, units and status are visible where needed.
- Missing facts remain labeled as unknown or pending.

### Interaction states

For apps/web/UI, explicitly inspect:

- loading;
- empty;
- error and recovery;
- disabled;
- active/selected;
- hover;
- focus-visible;
- success/confirmation.

### Anti-generic review

Reject reflexive use of:

- purple/blue “AI” gradients;
- centered hero over mesh background;
- three equal feature cards everywhere;
- glassmorphism without purpose;
- fake dashboard rectangles;
- generic filler badges/version labels;
- default Inter/slate styling when it does not fit the brand;
- motion that communicates nothing.

These are not absolute bans. They require a reason tied to audience, brand or function.

## 3. Excel: user-facing workbook design and QA

Treat a workbook as a small data system, not a decorated grid.

### Recommended architecture

1. `Start_Here` / `README`
2. `Inputs` / `Assumptions`
3. `Raw_*` source tabs
4. `Model_*` / `Calc_*`
5. `Lookup_*`
6. `Summary` / `Dashboard`
7. `QA_Checks` / `Audit`

### Native construction rules

- Preserve raw data.
- Use Excel Tables for data regions.
- Prefer structured references and named assumptions over brittle coordinates.
- Keep formulas live; do not paste static totals as if calculated.
- Use native charts, validation, filters and freeze panes.
- Avoid merged cells inside data/model ranges.
- Separate editable inputs from formulas and outputs.
- Use formatting to reveal structure, not decorate.

### User-facing summary rule

The first visible sheet should answer the principal user questions immediately. For a financial report, that normally means:

1. what came in;
2. what went out;
3. the resulting position;
4. what changed;
5. what decision or action follows.

Do not put governance prose or a wall of KPI cards before the conclusion.

### Excel QA

- Reopen the workbook with an independent reader.
- Verify sheet order, table ranges/names, formulas, validations, formats and row counts.
- Check duplicate/missing/out-of-range values.
- Reconcile raw, model and summary totals.
- Confirm no visible formula errors after recalculation.
- Set recalculation-on-open when local calculation is unavailable.
- Test editability: change an assumption, add a row, sort/filter, inspect dependent output.
- Render/inspect the workbook in Excel or a faithful PDF path when layout matters.
- Remember that `openpyxl` and `XlsxWriter` do not calculate formulas.

## 4. PowerPoint and deck QA

A deck must be visually strong **and** easy for a human to edit.

### Native construction

- Use a real `.pptx`; do not flatten slides into images.
- Use real slide/master backgrounds instead of giant blocking rectangles.
- Use templates, layouts and placeholders where practical.
- Keep text editable.
- Preserve image aspect ratios; crop rather than stretch.
- Name important objects for the Selection Pane.
- Keep object count and grouping understandable.
- Put internal source/caveat text in notes rather than tiny leaked footers.

### Deck QA loop

1. Render the actual PPTX to PDF/PNGs.
2. Inspect each affected slide at full size.
3. Inspect a whole-deck contact sheet for consistency.
4. Check title/logo rails, card geometry, captions, image scale, chart readability and footers.
5. Stress-test representative text by lengthening it.
6. Replace/re-crop one representative image to prove editability.
7. Re-render after every material correction.

Coordinates alone do not prove visual alignment; fonts, side bearings and renderers can shift the result.

## 5. Word/document QA

Treat Word as a semantic document, not a canvas.

- Use real Title, Heading, Body, List, Caption and Table styles.
- Use native numbering and lists.
- Use section breaks for orientation/margins/header changes; page breaks for ordinary new pages.
- Use tables for tabular content.
- Use native headers, footers and page-number fields.
- Keep images inline unless floating placement is necessary.
- Build recurring documents from a Word-authored template.
- Preserve `.docx` as the editable source; treat PDF as an export artifact.

QA must include structural readback, placeholder/field-error search, PDF rendering, representative-page inspection, table overflow, headers/footers, unexpected blank pages and accessibility basics.

## 6. HTML email QA

Email is not normal web design.

- Default to a single-column, mobile-first layout around 600 px maximum width.
- Use table-safe HTML and inline styles, or a validated MJML pipeline for greenfield templates.
- Preserve known-good provider templates when modifying an established campaign.
- Use hosted images and meaningful alt text.
- Include deliberate preview text.
- Use one primary CTA when possible.
- Test Gmail/Outlook/mobile constraints and dark mode deliberately.
- Read back the provider-saved version and inspect a real test send before release.

## 7. Maker/critic architecture for important visual work

For high-value work, do not let the maker approve its own output.

### Maker

- receives the locked brief, references and design tokens;
- produces bounded numbered candidates;
- preserves editable source and evidence;
- does not declare final approval.

### Independent critic

- receives the same brief and immutable candidate, but not the maker’s persuasive reasoning;
- cannot edit the candidate;
- searches for reasons to reject;
- checks reference authority, hierarchy, legibility, consistency, target-size/device behavior, editability and factual accuracy;
- returns specific defects and a verdict.

### Controller/human

- verifies the candidate did not change during review;
- decides whether to retain, revise, revert or stop;
- keeps final creative direction and publication/release approval human-owned.

Stop repeated retries when the same major defect appears twice. At that point diagnose the missing capability: better source material, stronger structured representation, a different tool, or specialist human craft.

## 8. Public source and tool list

### General UI/design-agent sources

- Anthropic frontend-design skill: https://github.com/anthropics/skills/tree/main/skills/frontend-design
- Taste Skill repository: https://github.com/Leonxlnx/taste-skill
- Taste Skill site: https://www.tasteskill.dev/
- UI UX Pro Max: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
- Awesome Design MD: https://github.com/VoltAgent/awesome-design-md
- Monokern reference-first Claude Code workflow: https://x.com/monokern/status/2071246711222055363
- Nav Toor / Awesome Design MD post: https://x.com/heynavtoor/status/2040339518822432893
- JoePro frontend-design prompt review source: https://x.com/JoePro/status/2076877282312954311

Use these as pattern sources. Review licenses and code before installing anything, and do not let a generic style pack override the project’s actual brand system.

### Excel and Office sources

- Microsoft — structured references with Excel Tables: https://support.microsoft.com/en-us/excel/using-structured-references-with-excel-tables
- Microsoft — Excel accessibility: https://support.microsoft.com/en-us/accessibility/excel/accessibility-best-practices-with-excel-spreadsheets
- Microsoft Graph — working with Excel: https://learn.microsoft.com/en-us/graph/api/resources/excel?view=graph-rest-1.0
- Microsoft Graph — workbook sessions: https://learn.microsoft.com/en-us/graph/excel-manage-sessions
- Microsoft Graph — Excel API best practices: https://learn.microsoft.com/en-us/graph/workbook-best-practice
- XlsxWriter formulas: https://xlsxwriter.readthedocs.io/working_with_formulas.html
- XlsxWriter tables: https://xlsxwriter.readthedocs.io/working_with_tables.html
- openpyxl tutorial: https://openpyxl.readthedocs.io/en/stable/tutorial.html
- openpyxl tables: https://openpyxl.readthedocs.io/en/stable/worksheet_tables.html
- openpyxl styles: https://openpyxl.readthedocs.io/en/stable/styles.html
- openpyxl defined names: https://openpyxl.readthedocs.io/en/stable/defined_names.html
- Microsoft — PowerPoint accessibility: https://support.microsoft.com/en-us/accessibility/powerpoint/make-your-powerpoint-presentations-accessible-to-people-with-disabilities
- Microsoft — Word accessibility: https://support.microsoft.com/en-us/accessibility/word/make-your-word-documents-accessible-to-people-with-disabilities
- Microsoft — Word headings: https://support.microsoft.com/en-us/word/add-a-heading-in-a-word-document

### Reporting and visual communication

- SEC, *A Plain English Handbook*: https://www.sec.gov/pdf/handbook.pdf
- IFRS, Management Commentary Practice Statement: https://www.ifrs.org/issued-standards/list-of-standards/management-commentary-practice-statement/
- W3C, contrast minimum: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html
- W3C, use of color: https://www.w3.org/WAI/WCAG21/Understanding/use-of-color.html
- Cleveland & McGill, graphical perception: https://doi.org/10.1080/01621459.1984.10478080
- Yang et al., truncated bar graphs: https://doi.org/10.1016/j.jarmac.2020.10.002

### HTML email sources

- SHUJILAI email-design skill: https://github.com/SHUJILAI/email-design-skill
- Resend — introducing email skills: https://resend.com/blog/introducing-email-skills
- Framix MJML skill: https://github.com/framix-team/skill-email-html-mjml

## 9. How we integrated this research into our own agent system

We did **not** paste all the external prompts into one system message or blindly install every repository. We converted the research into a layered operating system. The layers have different jobs and different authority.

### Layer 1 — Preserve the original sources

We retain raw source captures separately from conclusions:

- original URLs and source identity;
- captured article/post text when available;
- retrieval date and provenance;
- source limitations, such as inaccessible replies or marketing claims;
- a hash when a durable captured artifact matters.

Why: the agent must be able to distinguish “the source said this” from “we adopted this as a rule.” A viral post, repository README or vendor page is evidence to inspect—not automatically an instruction.

How another agent can reproduce it:

1. Create a `sources/` or `inbox/` area.
2. Save one note per source with URL, author, date, capture method and limitations.
3. Never execute installers or import prompts merely because they were linked.
4. Review code, license, dependencies, network behavior and credential expectations before adoption.
5. Keep raw captures immutable; write conclusions elsewhere.

### Layer 2 — Synthesize by topic, not by link

We turn source material into durable research notes organized by problem:

- general design and visual systems;
- frontend/reference-first workflow;
- Excel workbook architecture and QA;
- Word-native document construction;
- PowerPoint-native deck construction;
- HTML email constraints;
- financial/reporting communication;
- creative-agent architecture and independent visual review.

Each synthesis records:

- what is genuinely useful;
- what overlaps existing capability;
- what is unsupported marketing;
- what should be softened or rejected;
- what requires a human decision;
- whether installation or further research is actually warranted.

Why: topic synthesis prevents the agent from repeatedly rediscovering the same lesson and prevents one influencer’s aesthetic doctrine from becoming a universal rule.

How another agent can reproduce it:

1. Maintain a `research/` area and topic index.
2. Compare several sources before promoting a rule.
3. Write conclusions in plain language with explicit caveats.
4. Link each conclusion back to primary/public sources.
5. Mark the result as research-only until it is converted into an operating procedure.

### Layer 3 — Convert conclusions into scoped skills

We split the durable rules into task-specific skills rather than one giant “design” prompt. Our system now has separate procedural coverage for:

- general design review and build;
- Excel workbook design and QA;
- Word document design and QA;
- editable PowerPoint/deck design and QA;
- HTML email design;
- source-faithful visual data layout;
- social campaign systems;
- visual-artifact handoff;
- a governed Art production loop with separate Designer and Critic roles.

The general skill decides **how to read the design problem**. Medium-specific skills decide **how to construct and verify the artifact natively**. Brand/project references decide **what this particular organization should look and sound like**.

Why: Excel, PowerPoint, Word, web UI, email and social graphics do not share the same construction or QA mechanics. A universal prompt tends to produce generic advice and misses medium-specific failure modes.

How another agent can reproduce it:

1. Create one small routing skill that recognizes visual/design work.
2. Create medium skills only for work the agent actually performs.
3. Keep each skill procedural: trigger, prerequisites, build workflow, QA gates, failure conditions and delivery standard.
4. Link shared references instead of duplicating long instructions across every skill.
5. Load only the relevant skill bundle for each task; excess context weakens attention and consistency.

### Layer 4 — Separate generic design principles from owner/brand preferences

We keep three authorities distinct:

1. **General principles** — hierarchy, readability, accessibility, native editability and truthful communication.
2. **Medium rules** — Excel Tables/formulas, PowerPoint masters/placeholders, Word styles/sections, responsive HTML, email-client compatibility.
3. **Owner/project design system** — approved palette, fonts, image language, layout precedent, copy voice, positive references and rejected examples.

Why: a generic design pack should never override an established brand, and one owner’s aesthetic preference should not masquerade as a universal accessibility or engineering rule.

How another agent can reproduce it:

- Store project/brand tokens in the project, not the global agent personality.
- Record approved positive references and explicit negative references.
- State which authority wins when sources conflict.
- Keep confidential assets and business-specific rules out of public/shared skill packs.

### Layer 5 — Make native editability an acceptance criterion

We changed “looks okay in a preview” into “works as a real artifact a human can continue editing.” Examples:

- Excel uses Tables, formulas, validation, named assumptions and reconciliation—not a styled screenshot.
- PowerPoint uses native backgrounds, editable text, layouts/placeholders and sensible object structure—not flattened slide images.
- Word uses real styles, headings, lists, tables, sections and fields—not positioned text boxes.
- Web/UI uses semantic components, responsive behavior and real states—not a static hero mockup.
- Creative outputs preserve layered/vector/native source when future editing is expected.

Why: visual output that cannot be edited, audited or repaired creates hidden future work.

How another agent can reproduce it:

- Define the canonical editable source format before building.
- Require a human-edit stress test.
- Preserve originals and write changes to a new candidate/version.
- Test whether representative text, images, assumptions or data rows can be changed without rebuilding the artifact.

### Layer 6 — Add deterministic checks, but never confuse them with design approval

Our skills require structural verification appropriate to the medium:

- file/package integrity;
- expected pages/slides/sheets;
- formulas, ranges, styles and object structure;
- no missing assets or placeholders;
- dimensions, safe areas, overflow and contrast;
- source hashes and output hashes when provenance matters;
- readback after cloud/provider saves when used.

These checks catch objective failures. They do not decide whether hierarchy, composition, typography or brand fit is good.

How another agent can reproduce it:

1. List objective invariants for each artifact type.
2. Automate those checks where practical.
3. Fail closed on missing assets, invalid files, overflow, broken formulas or unsupported claims.
4. Keep semantic/visual judgment as a separate gate.

### Layer 7 — Require rendering and visual inspection

We made rendered output—not source code—the visual truth. The system creates the target viewing surface and inspects it:

- responsive browser screenshots;
- PowerPoint/Word/Excel PDF renders;
- slide/page contact sheets;
- phone-size social/email previews;
- grayscale/contrast checks where relevant;
- key-frame/contact-sheet review for motion.

Why: valid source can still render with clipped text, bad font substitution, tiny charts, broken crops, poor mobile hierarchy or blank spill pages.

How another agent can reproduce it:

- Install or identify a trustworthy renderer for each medium.
- Render after every material revision.
- Inspect the individual affected page and the entire artifact/system.
- State exactly what renderer was used and what was visually inspected.
- Do not claim “looks good” from code, XML or dimensions alone.

### Layer 8 — Separate the maker from the critic

For important visual work, our production architecture uses:

- a **Designer/Maker** that creates candidates;
- a fresh **read-only Critic** that receives the locked brief, references and frozen candidate;
- a controller that verifies evidence and decides whether to revise, revert, stop or present;
- human approval for final creative direction and external use.

The Critic is asked to find reasons to reject, not to validate the Maker’s story. The Maker’s explanatory reasoning is withheld so the Critic judges the actual artifact.

Why: self-review is vulnerable to confirmation bias, and agents often rationalize visible defects after they have invested in a candidate.

How another agent can reproduce it:

1. Freeze/hash the candidate before review.
2. Give the Critic the original brief and references, not the Maker’s defense.
3. Remove generation/editing authority from the Critic.
4. Require per-criterion findings and a closed verdict.
5. Verify the candidate remained unchanged during review.
6. Treat `reviewable` as ready for human review—not automatically approved.

### Layer 9 — Turn accepted and rejected work into controlled learning

We do not let every generated artifact become a positive reference. We distinguish:

- owner-approved positive examples;
- rejected/negative examples with specific failure labels;
- project-specific lessons;
- reusable medium-level rules;
- unresolved experiments.

When the user corrects an artifact, we compare the original and corrected versions, infer the design intent behind the changes, and update the appropriate project reference or skill only when the lesson is genuinely reusable.

Why: indiscriminate retrieval teaches the agent from its own mistakes and creates stylistic drift.

How another agent can reproduce it:

- Promote only human-confirmed outcomes into positive retrieval.
- Store negative examples so they cannot be served as inspiration.
- Record the reason for acceptance/rejection.
- Keep project-specific lessons out of global skills.
- Test new rules against a held-out task before making them universal.

### Layer 10 — Use stop conditions and escalate missing craft

We added explicit brakes:

- one failed candidate triggers a focused correction;
- repeated equivalent major defects stop ordinary retries;
- the system then identifies the missing capability: source quality, structured representation, renderer, editing tool, specialist model or human craft;
- it does not hide failure behind more prompting or more infrastructure.

Why: repeated generation without a new capability wastes time and can make the agent appear busy without improving the work.

How another agent can reproduce it:

- Define severity levels and maximum cycles in advance.
- Preserve the failed artifacts and comparison evidence.
- Require a materially different plan before another attempt.
- Escalate identity-critical illustration, anatomy, advanced retouching, complex motion/3D and final brand authorship to a qualified human until a bounded benchmark proves otherwise.

## 10. Recommended setup sequence for a new agent

A practical rollout is:

### Phase 1 — Foundation

- Create `sources/`, `research/`, `skills/`, `projects/` and `references/` boundaries.
- Add the general design-read and QA rubric.
- Add preserve/improve/redesign mode.
- Add source/reference classification.
- Add explicit production/public approval boundaries.

### Phase 2 — One medium at a time

Choose the owner’s highest-value medium first—often web/UI, Excel or decks.

For that medium:

1. define native artifact rules;
2. define structural checks;
3. establish a real render path;
4. build one representative fixture;
5. run visual QA;
6. test editability;
7. document failures and corrections.

Do not build ten medium adapters before one works end to end.

### Phase 3 — Brand and preference layer

- Add the owner’s actual fonts, palette, voice, layout precedents and asset authority.
- Build a small positive-reference set and a negative-reference set.
- State what is confidential and what may be shared externally.

### Phase 4 — Independent review

- Add the frozen-candidate Maker/Critic contract for important work.
- Benchmark the Critic against known bad artifacts to prove it catches expected issues.
- Keep final approval human-owned.

### Phase 5 — Durable learning

- Compare agent output with human-corrected output.
- Promote only stable reusable lessons.
- Keep skills short and scoped; link deeper references.
- Periodically prune duplicate, stale or overly absolute rules.

### Phase 6 — Expand only on demonstrated demand

Add email, documents, social, video or 3D only when real tasks justify them. Each new lane needs its own native-source contract, renderer, QA criteria, failure brake and benchmark.

## 11. Minimal starter instruction for another agent

```text
For every user-facing artifact:
1. State the audience, artifact type, and preserve/improve/redesign mode.
2. Inspect the real source, brand assets, examples, and existing design system before inventing anything.
3. Label each reference as canonical, brand authority, inspiration, targeted specification, or negative reference.
4. Define or recover design tokens before component styling.
5. Build in the native editable format: semantic HTML/CSS, native PPTX objects, Excel Tables/formulas/charts, Word styles/tables/sections, or layered/vector source.
6. Render the real artifact at its target size/device.
7. Review hierarchy, typography, spacing, alignment, contrast, responsiveness, states, copy truth, accessibility, and editability.
8. Fix defects, rerender, and recheck. File validity or successful code execution is not visual QA.
9. For important work, use a separate read-only critic that tries to reject the frozen candidate against explicit criteria.
10. Never publish, send, overwrite the original, purchase, or make a production change without approval.
```

## 12. What not to share as universal guidance

Keep organization-specific brand rules, customer data, internal financial definitions, credentials, private source assets, deployment topology and proprietary operating procedures out of a generic agent handoff. Share the general design/QA system and public references; add the new agent owner’s own brand and operational rules separately.
