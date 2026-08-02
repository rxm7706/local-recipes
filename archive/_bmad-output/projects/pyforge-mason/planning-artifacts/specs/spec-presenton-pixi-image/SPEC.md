---
id: SPEC-presenton-pixi-image
spec: presenton-pixi-image
status: archived
archived-reason: blocked
owner-dream: docs/dreams/presenton-pixi-image.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/presenton-pixi-image.md
  - ../../briefs/brief-presenton-pixi-image-2026-07-25/brief.md
  - ../../briefs/brief-presenton-pixi-image-2026-07-25/addendum.md
  - ../../prds/prd-presenton-pixi-image-2026-05-01/prd.md
  - ../../architecture/architecture-presenton-pixi-image-2026-07-25/ARCHITECTURE-SPINE.md
  - ../../epics-presenton-pixi-image.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`blocked`). Charter §5 requires
> every Dream to carry a Spec, archived included: a retirement record is how the next reader
> learns from the decision instead of rediscovering the idea. It states what was contracted,
> why it ended, and what survives — not a plan for work that will not happen.

# presenton-pixi-image — retirement record

## Why it was contracted

An air-gapped, conda-forge-native repackaging of the open-source Presenton AI
deck-generation app for Red Hat OpenShift in regulated-enterprise environments
(govtech/fintech/defense-adjacent) where cloud Microsoft 365 Copilot cannot be
used. Five confirmed conda-forge recipes (`presenton-export-node`,
`pptx-assembler`, `pptx-thumbnail-inject`, `playwright-with-chromium`,
`llmai`) replacing every LibreOffice-dependent or closed-source component,
assembled into one pixi-locked, SBOM-attested, cosign-signed OCI image
deployed via Helm on OpenShift Restricted SCC, with a two-gate JTBD success
signal (a binary buyer-gate: recipes merged → mirrored → registry-published
with attestation; a behavioral user-gate: a pilot customer clearing a
three-signatory acceptance checklist within 12–18 weeks).

The full BMAD planning chain — technical + domain research, a product brief
and addendum, a revised PRD, an 8-AD architecture spine, and 7 epics / 30
stories — landed 2026-07-25, complete and internally consistent (`campaign:
presenton chain landed — Dream in-spec`).

## Why it ended

**Blocked, not superseded and not abandoned by decision.** The Dream's own
frontmatter has carried `blocked-on: Phase-0 decision gate (Epic 1)` since it
was written, and that gate is real: the PRD names six Phase-0 exit criteria
that must clear before v1 build kickoff, and none has been resolved since the
chain landed. The highest-urgency one is exit 6 — whether Microsoft's
disconnected on-prem stack (Azure Local disconnected operations + Microsoft
365 Local + Foundry Local, GA worldwide 2026-02-24) already includes or
roadmaps a Copilot-for-PowerPoint-equivalent. That question is existential to
this Dream's own risk register (R3): if answered yes, the product's reason to
exist narrows or disappears. It requires external market research nobody has
performed since 2026-07-25. The same exit also decides whether the recipe
count is 5 or 7 (the `mem0ai`/`fastembed-vectorstore` memory-subsystem
question), which changes the shape of every downstream epic. Exit 1
(GGUF model + quantization choice, with a benchmarking methodology) is the
critical-path long-pole gating exits 2–3; it too is unresolved. None of the
six exits is a local engineering task — they require a market-research pass,
a hands-on OpenShift cluster spike (the Chromium-sandbox-under-`restricted-v3`
question in AD-4/AD-8), and a legal review of `psycopg`'s LGPL-3.0 obligation
— and no evidence exists that any of that work has happened.

Two facts corroborate that this is a stall, not a decision: (1) no story has
entered implementation — there is no `implementation-artifacts/` entry for
this project anywhere in the repository, unlike `pyforge-mason` itself, which
has shipped four real stories in the same window; (2) on 2026-07-28 the BMAD
*project* registration `presenton-pixi-image` was administratively dissolved
into `pyforge-mason/planning-artifacts/` per Charter §5 — an org-structure
move (its chain now lives as `epics-presenton-pixi-image.md` alongside
Mason's own `epics.md`), not a statement that the work itself was cancelled.

Nothing in the record states this was deprioritized in favor of other work,
found to duplicate existing scope, or superseded by a different plan — those
would be different, false claims. The honest account is narrower: a real,
externally-blocking decision gate has sat open for a week with no forward
motion, while the planning artifacts otherwise remain sound.

## What carries forward

- **The planning chain itself is not invalidated** — research, brief, PRD,
  architecture spine, and epics remain internally consistent and would not
  need to be re-derived if the Phase-0 gate ever clears. `epics-presenton-pixi-image.md`
  stays alongside `pyforge-mason`'s own epics for that reason.
- **The confirmed-necessary recipe list and its dependency-closure research**
  (`brief-presenton-pixi-image-2026-07-25/addendum.md` § *Technical constraints
  surfaced by research*): the five confirmed recipes, the removed
  `template-style-extractor`, and the full conda-forge-availability table for
  Presenton's backend closure (`fastmcp`, `dirtyjson`, `sqlmodel`, `asyncpg`,
  `aiomysql`, `psycopg`, `google-genai`, `pathvalidate`, `pdfplumber`,
  `python-pptx`, `fastembed`, `nltk`, `fonttools` — all confirmed present on
  conda-forge) is reusable groundwork, not lost.
- **`recipes/presenton/` already exists and is actively maintained** in this
  repository's own factory (the base app, Apache-2.0, currently version
  0.7.3) — independent of this Dream and predating it. It is not one of the
  five recipes this Dream scoped (which target the closed-source export/PPTX
  pipeline the base app depends on, not the app itself), but its existence
  means a future resumption does not start from zero on the base package.
- **The rejected-alternative history** (the `pptx2marp-bridge-marp2pptx`
  vendoring approach, killed on lossy round-trip + missing-thumbnail grounds;
  rebuilding `template-style-extractor` from scratch, rejected because
  upstream already ships the equivalent LibreOffice-free import) does not
  need to be relitigated if this resumes.

## Non-goals

- **Reviving this Dream by writing new code against its epics today.** The
  Phase-0 gate is unresolved; starting Epic 2+ before it clears repeats the
  exact risk the PRD itself gates against.
- **Treating this record as a backlog item.** Archived Dreams are excluded
  from the Backlog board by design.
- **Reading the 2026-07-28 project dissolution as evidence the work was
  cancelled.** It was an administrative move (Charter §5, the chain follows
  its owning Smith), not a disposition on the Dream itself — the disposition
  recorded here (`blocked`) is a separate, later decision.
- **Folding this Dream's intent into `pyforge-mason`'s own narrative.** The
  two are genuinely different subject matter — an air-gapped repackage of a
  third-party AI deck tool versus the `mason` CLI — and archiving this
  separately (rather than absorbing it) reflects that difference honestly.

## Success signal

A reader arriving at this Dream learns in one page that it is paused on a
real, unresolved, externally-scoped decision gate — not cancelled, not
duplicated, not superseded — and knows exactly which six Phase-0 exit
criteria would need to clear (and where the research to clear them starts)
before Epic 1 could restart.
