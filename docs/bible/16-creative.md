# 16. Creative workflow

## Actor and authority
The designer produces candidates; a separate creative critic can review a frozen artifact. The owner controls final creative approval and public use. A render is not editorial approval.

## Prerequisites and version
Dependencies depend on the actual medium. Factory acceptance exercised an Inkscape SVG→PNG route and supporting document/raster/media routes on ARM64. Private proprietary Studio/Vector source permission does not authorize public redistribution.

## Inputs

Consult the unchanged [Design and QA Starter Pack](../references/design-and-qa-starter-pack.md) for general design routing and medium-specific QA. Excel requires live Tables/formulas and reconciliation; Word requires semantic styles and sections; PowerPoint requires editable native objects; HTML email requires client-safe layout and actual previews. Web/UI/social require target-device rendering, accessibility and interaction/size checks. Do not substitute one medium's renderer or a geometric canary for another medium's acceptance. Keep Maker/Critic separation, native editability, controlled promotion of human-approved learning and repeated-defect stop conditions. External repositories are pattern sources only, not installed or bundled dependencies; retain their license/provenance caveats.

Outcome, dimensions/formats, original/reference rights, brand/factual sources, approved tools, bounded revisions, private output destination and QA criteria.

## Procedure
Confirm source rights and retain editable originals. Freeze a brief with explicit constraints. Render harmless local test data before using a backend for real assets. Validate document structure, expected dimensions, alpha/content bounds and a changed-pixel negative; do not prove visual correctness by comparing an image only to itself. Inspect the actual output visually through the authorized QA route and reopen delivered formats. Keep candidate, rejected and owner-approved states distinct. Designer/Critic are native dependency-linked tasks, never another sidecar scheduler. Optional external model/media lanes need separate access and cannot be silently claimed from a simple raster fixture.

The original supporting runtime provides a credential-independent limited route: install its declared dependencies into a disposable virtual environment, then import `render_geometric_art` from `supporting_runtime.runtime`. Pass a dictionary with integer `width`/`height` (1–2048) and 1–100 `rectangles`, each containing only integer `x`, `y`, `width`, `height` and a six-digit hex `fill`. Rectangles must lie inside the canvas. Pass a new absent output directory; existing or symlink destinations are refused. The function writes mode-0600 `editable.svg` and `render.png` inside the mode-0700 directory, and returns hashes with status `rendered-not-owner-approved`. It never fetches references or executes SVG/script input. This route does not replace Studio/Vector's complete designer feature set.

From the source clone, run `python3 -B -m pytest -q -p no:cacheprovider`. `tests/release/test_supporting_runtime.py` reopens original and revised images and verifies exactly 224 changed pixels at bounds `(22, 2, 30, 30)` for its fictional 32×32 rectangle. Canonical acceptance additionally rebuilds and executes the extracted supporting runtime. Independent visual inspection and owner approval remain separate gates. On invalid dimensions, colors or assets, correct the brief/data before retrying with a new destination; never overwrite an accepted artifact.

## Expected results
An actual artifact and editable source exist, reopen successfully and match technical QA. Source ownership/rights and visual review remain recorded independently. The public capability needs a verified legal working route, not an omitted implementation disguised as documentation.

## Independent verification
Re-render exact extracted source, inspect hashes/dimensions/geometry and review the real image/document. The current factory creative proof does not clear public source rights or prove live design-model inference.

## Failure and recovery
On unavailable backend, test documented legal alternatives and record capability impact. Preserve the source and last valid render; do not fabricate a screenshot or approval receipt.

## Privacy and outputs
Private assets, workbench logs and approval records never enter public distributions.

## Sources
[Designer profile](../../profiles/art/README.md), [notices](../../THIRD_PARTY_NOTICES.md), [package canary](../../scripts/full_system_package.py), [workflows](../WORKED-WORKFLOWS.md).
