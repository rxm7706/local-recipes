---
title: 'Story D2 (5.2): Build the Vizro dashboard + port the 28 CLIs to pages'
type: 'feature'
status: 'regenerated'
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #87 body + main commit log; dev narrative recovered, review-triage partial)'
---

> **Contract-spec — no original ever existed (corrected 2026-07-25).** This story
> (wave B9–H4) was built by the atlas migration's **in-session agent loop**, which —
> unlike `bmad-create-story` (used only for waves 0/A/B1–B8) — never emitted a per-story
> spec file. The atlas migration session (`01FYyQvBJuXwySiaMUUYCqBZ`) confirmed this
> exhaustively: no such file exists in `implementation-artifacts/`, `.bmad-loop/runs/`
> (which never existed for atlas), any git worktree, git history, or anywhere on disk.
> **Nothing was lost — there is no original to recover.** This file carries the
> load-bearing contract (Intent + Acceptance Criteria **verbatim** from the tracked
> `planning-artifacts/epics.md`) plus a dev narrative reconstructed from the merged record
> (the "Dev narrative" section below). A fuller BMAD-story-format reconstruction (Dev
> Agent Record + File List + Review Triage Log, built from the agent-loop transcripts) is
> at `../../spec-archive/retro-story-files/5-2-d2.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story D2 (5.2): Build the Vizro dashboard + port the 28 CLIs to pages

As the operator,
I want a BSL-driven Vizro app reproducing the 28 read CLIs as pages, including a factory-status page,
So that every read-only question is answerable from a page meeting the agent-legibility bar.

**Acceptance Criteria:** (spec § 9 Story D2, binding)

**Given** the D1 BSL models and the CIS two-spine design specs
**When** the Vizro app is built
**Then** a Vizro dashboard serves the core KPIs currently locked in CLIs
**And** a "factory status" page reads the BMAD artifact state (sprint-status.yaml, epics frontmatter, `bmad-drift-check --specs` JSON) — agent-readable per § 13.2
**And** each read-only legacy CLI question is answerable from a Vizro page, where for the three FR-9 exceptions (`add-handoff`, `inventory-match`, `library-futures`) "answerable" means the latest-report artifact is surfaced read-only — the bar covers all 28
**And** the live-confirmed consumer set ports first: `behind-upstream`, `query-atlas`, `whodepends`, `feedstock-health`, `my-feedstocks`, `detail-cf-atlas`, `staleness-report`
**And** pages meet the § 2.1 agent-legibility bar (semantic HTML, ARIA, deterministic layouts; NFR-8) and public-facing breadth stays at the factory-status page (SM-C4).

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-17 (authoring-feeding pages carry build timestamps).
- **Mode:** DEV-AUTO (visual judgment, § 9 preamble).
- **Gating question:** none.
- **Verify gate:** `bsl-metric-check` (+ `kedro-test`); D2 page inventory detail resolves in the CIS specs (Spine Deferred).
- **Depends on:** D1.

### Story D3 (5.3): Integrate Vizro-AI + expose the NL interface as an MCP tool

As a CFE authoring agent (and the operator),
I want a Vizro-AI natural-language query field and a `query_vizro_ai` MCP tool over the BSL knowledge graph,
So that ad-hoc questions need no SQL and are callable from Claude Code.

**Acceptance Criteria:** (spec § 9 Story D3, binding)

**Given** the D1 BSL graph and the D2 dashboard
**When** Vizro-AI is integrated
**Then** a natural-language query (e.g. the § 4.3 example) returns a generated chart/insight
**And** the `query_vizro_ai` MCP tool is callable from Claude Code
**And** the LLM backend routes through repo model-backend configuration — never a hardcoded public endpoint (Q3 default).

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-7 (MCP body carries no metric logic).
- **Mode:** ATTENDED (backend boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q3** (Vizro-AI LLM backend) — § 11 default adopted: route through repo model-backend configuration; defining the `_http.py`-analog LLM routing chain is the real work; bounds: no litellm (py3.14 floor), copilot-api bridge ineligible, llama.cpp/ollama/mlx-lm in-env.
- **Verify gate:** `bsl-metric-check` (existing; NL path verified at the attended event).
- **Depends on:** D1, D2.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

## Dev narrative — recovered from the merged record (2026-07-25)

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #87: story(D2): BSL-driven Vizro dashboard + core CLI-port pages (FR-9)

## Summary

Ships the buildable core of the read surface: a Vizro app assembled from the D1 semantic models (**AD-8** — the single metric-translation interface), the AC's live-confirmed-first pages, and the factory-status page.

- **`dashboard/data.py`** — every page loader is a **pure BSL query** (`model.query(...).execute()`); no re-implemented metric and no raw SQL in the Vizro layer (AD-8). Pages over an existing single dataset are **live** (feedstock-health → `core_feedstock_health`; my-feedstocks → `vcs_package_maintainers`); pages whose composed store isn't materialized yet are honest **BSL-wired shells** (empty typed frame, never fabricated rows) flagged DW-D2.
- **`dashboard/factory_status.py`** — reads the live BMAD artifact state (sprint-status.yaml + epics/spec frontmatter) into one deterministic semantic table carrying an **injected build timestamp** (AD-17; never `datetime.now()` at import). Missing/malformed artifacts degrade to typed-empty (a missing `epics.md` now contributes **zero** rows — no fabricated `"None"` status).
- **`dashboard/app.py`** — assembles the Vizro Dashboard object; the gate builds it **offline** (no server / no `.run()`).
- **`dashboard-dryrun` gate** — dashboard builds offline; each page has a stable id+title (deterministic layout, NFR-8 agent-legibility); loaders proven BSL-driven vs an independent query; factory-status reads the real sprint-status.yaml + carries its AD-17 stamp.
- **AD-1/AD-6 import-ban** — only the `dashboard/` subpackage imports vizro (AST guard extended, beside the D1 BSL ban).

## Scope (honest deferral)

The **full 28-page inventory + detailed page designs** are **CIS-two-spine deferred** (`DESIGN.md` + `EXPERIENCE.md` not yet produced); the **DEV-AUTO visual verification** of the rendered UI is deferred (headless container). Recorded in `deferred-work.md` DW-D2-1/-2/-3.

## Reviews

Three independent reviews. Reviewer A + Reviewer B fixes applied: **S1** — a missing `epics.md` contributes zero rows (no fabricated `"None"` status, agent-legibility); **S2** — a present-but-untyped Parquet degrades to the declared-column empty frame instead of raising `IbisTypeError`.

## Tests

`550 passed` (+19 new).

### Commits on `main`

- `0c5ea3ef90` story(D2): BSL-driven Vizro dashboard + core CLI-port pages (FR-9)  _(dev-landing)_

_This PR also carried an automated Gemini review; not reproduced here per repo policy ([[feedback_no_gemini_reviews]])._

