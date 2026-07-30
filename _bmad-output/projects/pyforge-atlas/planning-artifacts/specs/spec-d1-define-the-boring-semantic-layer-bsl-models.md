---
title: 'Story D1 (5.1): Define the Boring Semantic Layer (BSL) models'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #86 body + main commit log; dev narrative recovered, review-triage partial)'
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
> at `../../spec-archive/retro-story-files/5-1-d1.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story D1 (5.1): Define the Boring Semantic Layer (BSL) models

As a downstream consumer (page, MCP read, agent),
I want the 28 read CLIs' metric logic declared once as BSL dimensions + measures over the catalog (Ibis → DuckDB),
So that every read surface translates through one semantic interface with proven metric parity.

**Acceptance Criteria:** (spec § 9 Story D1, binding)

**Given** the metric/business logic embedded in the 28 read CLIs
**When** the BSL models are declared
**Then** BSL declares the core metrics (staleness, adoption stage, feedstock health, …)
**And** maintainer-role facts (`package_maintainers ⋈ maintainers`) are first-class BSL dimensions — the raw-SQL JOINs live consumers write today become declared queries
**And** the BSL layer is the single translation interface for downstream consumers
**And** a `bsl-metric-check` verify task exists: metric-parity fixtures proving BSL answers match the legacy CLI outputs for the core metrics (the AD-7 metric-semantics handover anchor).

- **FRs:** FR-8.
- **Invariants:** AD-8, AD-4 (Ibis → DuckDB only).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** **builds `bsl-metric-check`**.
- **Depends on:** Epic 4 (stable orchestrated datasets); B4 (canonical Parquet store).

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] BSL declares the core metrics (staleness, adoption stage, feedstock health, …)
- [x] maintainer-role facts (`package_maintainers ⋈ maintainers`) are first-class BSL dimensions — the raw-SQL JOINs live consumers write today become declared queries
- [x] the BSL layer is the single translation interface for downstream consumers
- [x] a `bsl-metric-check` verify task exists: metric-parity fixtures proving BSL answers match the legacy CLI outputs for the core metrics (the AD-7 metric-semantics handover anchor).

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-8.
- **Invariants:** AD-8, AD-4 (Ibis → DuckDB only).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** **builds `bsl-metric-check`**.
- **Depends on:** Epic 4 (stable orchestrated datasets); B4 (canonical Parquet store).

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #86). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**The single translation interface.** `semantic/metrics.py` declares the business logic
embedded in the 28 read CLIs **once**, as pure Ibis expressions over the canonical Parquet
store. Every read surface — dashboard page, NL query, agent read — translates through it
instead of writing raw SQL (AD-8).

**Ibis → DuckDB only, and it is enforced by shape.** Every function returns an Ibis
expression (`ir.Value`) evaluated by the DuckDB backend. There is deliberately **no pandas
metric path** — a metric that computes in pandas is a metric that exists twice, which is
exactly what the layer is designed to prevent (AD-4).

**The metrics that landed.** Staleness (`staleness_age_days`, from
`staleness_report.py`'s `age_days = (now - ts)//86400`), adoption stage
(`adoption_stage`, a *verbatim* port of `adoption_stage.py::_classify`), feedstock health,
downloads, the actionable scope (`is_actionable`, from the `v_actionable_packages` view),
plus the maintainer join promoted to a **first-class dimension**. D2 completes the full
28-CLI surface as it ports pages.

**Null handling is explicit, not incidental.** `staleness_age_days` maps a null-or-zero
timestamp to `ibis.null()` rather than to a large age; `adoption_stage` maps the same
condition to a `99999` sentinel *inside* the classifier because that is what the legacy
`_classify` did. The two differ on purpose — a missing timestamp is unknown staleness, but
the legacy lifecycle classifier treated it as maximally old. Porting them identically
would have been the bug.

**`METRIC_PROVENANCE` is the honesty mechanism (DW-B1-1).** Each metric records where its
formula came from, in two kinds: a citation to the legacy function or SQL predicate, and —
for the gate — an **independent re-implementation** of that formula. `bsl-metric-check`
asserts the Ibis port matches the independent re-derivation, not itself. A parity test that
compares an implementation to its own restatement proves nothing; this one was built
specifically to avoid that.

**`data_wiring` records whether the inputs are actually there.** A metric can be correctly
declared over a dataset that has not been materialized yet. Recording that distinction is
what let D2 ship honest shell pages instead of pages that silently render empty.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-D1]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-D1]
- [Architecture: _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md]

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Delivery Record

<!-- DERIVED from the merged PR via `gh` on 2026-07-27. Exact, not reconstructed. -->

| | |
|---|---|
| Pull request | **#86** — story(D1): Boring Semantic Layer models for the core atlas metrics (FR-8) |
| Merged | 2026-07-18 |
| Diff | 11 files, +1203 / -0 |
| Test files touched | 7 |

**Commits**

- `580e5ba` story(D1): Boring Semantic Layer models for the core atlas metrics (F…

**File list** *(exact, from the merged diff)*

```
  350 +     0 -  src/shared/packages/pyforge-atlas/tests/semantic/test_bsl_metric_parity.py
  268 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/metrics.py
  179 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/models.py
  158 +     0 -  src/shared/packages/pyforge-atlas/tests/semantic/test_maintainer_dimension.py
   64 +     0 -  src/shared/packages/pyforge-atlas/tests/semantic/test_metric_provenance.py
   57 +     0 -  src/shared/packages/pyforge-atlas/tests/semantic/PROVENANCE_NOTES.md
   49 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/__init__.py
   37 +     0 -  src/shared/packages/pyforge-atlas/tests/catalog/test_no_inline_io.py
   37 +     0 -  src/shared/packages/pyforge-atlas/tests/semantic/conftest.py
    4 +     0 -  pixi.toml
    0 +     0 -  src/shared/packages/pyforge-atlas/tests/semantic/__init__.py
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `580e5ba`** — story(D1): Boring Semantic Layer models for the core atlas metrics (FR-8)
  - Declares the metric/business logic embedded in the 28 read CLIs ONCE as BSL
  - dimensions + measures over the migrated canonical Parquet store, Ibis -> DuckDB
  - only (AD-4), as the single translation interface for every read surface (AD-8).
  - - semantic/metrics.py -- the core metrics as PURE Ibis expressions: staleness
  - (age_days = (now-ts)//86400, ts falsy -> null), adoption_stage (verbatim port
  - of adoption_stage.py::_classify incl. the "age or 99999" falsy-zero quirk +
  - branch order + null-age & 0-versions -> unknown), is_actionable (the 3-clause
  - v_actionable_packages COALESCE predicate), feedstock-health filters (ci-red /
  - open-prs / open-issues), downloads. METRIC_PROVENANCE separates real
  - legacy-formula anchors from migrated-node-derived metrics FLAGGED for legacy
  - recapture (DW-B1-1 honesty; no fabricated legacy values).
  - - semantic/models.py -- BSL SemanticModels binding the metrics to DuckDB tables
  - read from Parquet; the maintainer join is FIRST-CLASS (AC-2):
  - build_package_maintainers_model declares "maintainer" as a Dimension and
  - join_packages_by_maintainer declares packages-join-maintainer as a BSL
  - semantic join, so "staleness-report --maintainer X" / "feedstock-health
  - --maintainer X" become DECLARED BSL queries instead of raw-SQL JOINs.
  - - bsl-metric-check gate (tests/semantic): each metric's EXPECTED value is an
  - INDEPENDENT verbatim re-implementation of the legacy formula (never the BSL
  - expression under test), so a port-vs-legacy divergence fails the gate -- the
  - DW-B1-1 both-sides-compute-the-same trap is structurally excluded.
  - - AD-8 import-ban: only the semantic/ subtree imports boring_semantic_layer
  - (AST guard extended in tests/catalog/test_no_inline_io.py).
  - Reviewer fixes applied. Reviewer B (edge cases) confirmed the two real defects
  - it found (adoption_stage NULL total_versions parity; empty-input typing) were
  - already fixed on disk; its three test-coverage NITs are now closed: maintainer
  - NULL-group asserted (present-with-NULL, not absent) + comment corrected;
  - duplicate (conda_name, maintainer) long-form rows guarded against double-count;
  - empty-catalog SUM measures pinned as intended-NULL (not 0).
  - 531 passed (+17 new).

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#86`.

<!-- end retro story -->

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #86: story(D1): Boring Semantic Layer models for the core atlas metrics (FR-8)
