---
title: 'Story H2 (9.2): Implement Agno Compilation, Linting, and Q&A Crews'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #100 body + main commit log; dev narrative recovered, review-triage partial)'
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
> at `../../spec-archive/retro-story-files/9-2-h2.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story H2 (9.2): Implement Agno Compilation, Linting, and Q&A Crews

As the operator,
I want `agno` crews that compile raw docs, lint the wiki, and answer questions,
So that the wiki maintains itself with agent labor.

**Acceptance Criteria:** (spec § 9 Story H2, binding)

**Given** the H1 scaffold and a fixture wiki
**When** each crew runs end-to-end
**Then** compile transforms raw → compiled, lint reports violations, and Q&A answers grounded in compiled content
**And** wiki outputs carry their source datasets' staleness markers forward (AD-13/AD-22 — republication never launders freshness).

- **FRs:** FR-22(b).
- **Invariants:** AD-22, AD-13.
- **Mode:** DEV-AUTO (spec § 9 explicit: crew design needs judgment).
- **Gating question:** none (crew design detail is a story-spec decision, Spine Deferred).
- **Verify gate:** crews-on-fixture-wiki tests in `kedro-test`.
- **Depends on:** H1.
- **DELIVERED (2026-07-18):** `factory/crews.py` — `CompileCrew` (raw→compiled, per-doc-resilient, forwards source staleness from BOTH the inline `stale:` frontmatter AND the `.staleness.json` sidecar into compiled frontmatter + a visible body banner — AD-13/AD-22, republication never launders freshness), `LintCrew` (reports `missing-frontmatter`/`missing-title`/`empty-body`/`broken-link` [path-resolved, recursive]/`laundered-staleness`/`malformed-frontmatter`; never raises), `QACrew` (grounded answers over compiled content; deterministic keyword retriever + extractive synthesizer defaults). agno-Agent/LLM synthesis + F3-vss production retriever are injectable seams, offline by default — live bring-up DEFERRED (DW-H2). Gate `tests/factory/test_crews.py` (26). AD-1 import-ban green (yaml+stdlib only). An independent adversarial review found 2 MUST-FIX (inline-staleness laundering; lint/QA crash-on-malformed) + 1 SHOULD-FIX (leaf-only broken-link) — all fixed + regression-tested before merge.

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] compile transforms raw → compiled, lint reports violations, and Q&A answers grounded in compiled content
- [x] wiki outputs carry their source datasets' staleness markers forward (AD-13/AD-22 — republication never launders freshness).

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-22(b).
- **Invariants:** AD-22, AD-13.
- **Mode:** DEV-AUTO (spec § 9 explicit: crew design needs judgment).
- **Gating question:** none (crew design detail is a story-spec decision, Spine Deferred).
- **Verify gate:** crews-on-fixture-wiki tests in `kedro-test`.
- **Depends on:** H1.
- **DELIVERED (2026-07-18):** `factory/crews.py` — `CompileCrew` (raw→compiled, per-doc-resilient, forwards source staleness from BOTH the inline `stale:` frontmatter AND the `.staleness.json` sidecar into compiled frontmatter + a visible body banner — AD-13/AD-22, republication never launders freshness), `LintCrew` (reports `missing-frontmatter`/`missing-title`/`empty-body`/`broken-link` [path-resolved, recursive]/`laundered-staleness`/`malformed-frontmatter`; never raises), `QACrew` (grounded answers over compiled content; deterministic keyword retriever + extractive synthesizer defaults). agno-Agent/LLM synthesis + F3-vss production retriever are injectable seams, offline by default — live bring-up DEFERRED (DW-H2). Gate `tests/factory/test_crews.py` (26). AD-1 import-ban green (yaml+stdlib only). An independent adversarial review found 2 MUST-FIX (inline-staleness laundering; lint/QA crash-on-malformed) + 1 SHOULD-FIX (leaf-only broken-link) — all fixed + regression-tested before merge.

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #100). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**Three crews, each mapped to its personas.** `CompileCrew` (Compiler + Linker) turns
`wiki/raw/` markdown into `wiki/compiled/`; `LintCrew` (Linter/QA) validates compiled output
and reports violations; `QACrew` (Oracle + Ingester) answers questions grounded in compiled
content.

**Staleness propagation is the load-bearing behavior.** `CompileCrew` forwards source
staleness from **both** the inline `stale:` frontmatter **and** the `.staleness.json` sidecar
(the same shape the datasets write) into the compiled frontmatter **and** a visible body
banner. A stale source can never produce a compiled page that reads as fresh — republication
never launders freshness (AD-13/AD-22). `LintCrew` then enforces this with a
`laundered-staleness` violation, so the property is checked, not merely implemented.

**Nothing raises.** `LintCrew` reports `missing-frontmatter`, `missing-title`, `empty-body`,
`broken-link` (path-resolved and recursive), `laundered-staleness`, and
`malformed-frontmatter` — and never throws. `CompileCrew` is **per-doc resilient**: one bad
document does not abort the batch. For a crew that runs unattended over a growing wiki, a
crash is a worse outcome than a reported violation.

**Offline-first with injectable synthesis (the D3/F3/G3 pattern).** Every crew's core
transform is deterministic and offline — `QACrew` defaults to a keyword retriever plus an
extractive synthesizer. The agno Agent/LLM synthesis and the F3 `vss` production retriever
are **injectable seams**, with live bring-up deferred as DW-H2. Imports stay `yaml` + stdlib,
so the AD-1 ban holds.

**The write boundary again (AD-22).** Crews read atlas datasets and the raw wiki, and write
**only** the wiki tree, through `WikiLayout` whose `stage_path` refuses any escape. No crew
writes an atlas dataset — the factory layer consumes, it never becomes a second writer.

**Adversarial review caught real defects before merge.** Two MUST-FIX — inline-staleness
laundering (the sidecar path propagated, the inline `stale:` path did not, so the exact
property the story exists to guarantee had a hole) and lint/QA crashing on malformed input
(breaking the never-raises contract) — plus one SHOULD-FIX (leaf-only broken-link resolution).
All fixed and regression-tested. Both MUST-FIXes were failures of the story's *own* headline
invariant, which is the case for adversarial review on invariant-bearing work.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-H2]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-H2]
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
| Pull request | **#100** — H2: agno compile/lint/Q&A wiki crews (FR-22(b)) |
| Merged | 2026-07-18 |
| Diff | 4 files, +789 / -0 |
| Test files touched | 1 |

**Commits**

- `f952c75` H2: agno compile/lint/Q&A wiki crews (FR-22(b))

**File list** *(exact, from the merged diff)*

```
  437 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/crews.py
  330 +     0 -  src/shared/packages/pyforge-atlas/tests/factory/test_crews.py
   20 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/__init__.py
    2 +     0 -  _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `2f4240f`** — H2: agno compile/lint/Q&A wiki crews (FR-22(b)) (#100)
  - Implement the three AI-Software-Factory crews that maintain the Karpathy
  - wiki (Wave H, spec § 7.3 / § 9 Story H2), offline-first on a fixture wiki.
  - factory/crews.py (imports yaml + stdlib only — AD-1 preserved):
  - - CompileCrew (Compiler + Linker): wiki/raw/*.md -> wiki/compiled/*.md.
  - Derives a title, carries the source ref, and PROPAGATES source staleness
  - forward (AD-13/AD-22 — republication never launders freshness) from BOTH
  - carriers: the raw doc's own `stale:` frontmatter AND the .staleness.json
  - sidecar (union; either => stale). A stale source gets a machine-readable
  - frontmatter marker AND a visible body banner. Per-doc resilient: a
  - malformed raw doc is recorded in result.failed and skipped, never
  - aborting mid-loop into a half-written compiled/ state. Byte-stable output.
  - - LintCrew (Linter/QA): reports missing-frontmatter / missing-title /
  - empty-body / broken-link / laundered-staleness / malformed-frontmatter.
  - Never raises — a malformed page is a reported violation, not a DoS of the
  - whole pass. broken-link resolves targets RELATIVE to the doc's dir against
  - the real (recursive) tree, so it neither false-negatives a wrong-subdir
  - link nor false-positives a real subdir page, and flags a link escaping
  - compiled/.
  - - QACrew (Oracle + Ingester): grounded answers over compiled content.
  - Retriever + synthesizer are injectable; defaults are offline deterministic
  - (keyword-overlap ranking + extractive answer). grounded == the answer is
  - backed by >=1 compiled snippet (the Oracle never answers ungrounded).
  - Skips a malformed page rather than crashing the answer.
  - The agno-Agent / LLM synthesis (enricher/synthesizer) and the F3 vss
  - production retriever are injectable seams that default to the offline path;
  - the live bring-up is attended -> DEFERRED (DW-H2), mirroring D3/F3.
  - Independent adversarial review found and this commit fixes: 2 MUST-FIX
  - (a raw doc's inline `stale:` frontmatter was dropped -> laundered, and
  - lint/QA raised on a malformed page instead of reporting/skipping) + 1
  - SHOULD-FIX (leaf-only broken-link matching) — all regression-tested.
  - Verify gate: tests/factory/test_crews.py (26). Full atlas suite 762 passed.
  - Also folds in the H1 DELIVERED doc catch-up (epics + sprint-status) and
  - DW-H2.
  - Claude-Session: https://claude.ai/code/session_01FYyQvBJuXwySiaMUUYCqBZ
  - Co-authored-by: Claude <noreply@anthropic.com>

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#100`.

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #100: H2: agno compile/lint/Q&A wiki crews (FR-22(b))

## Deferred Work (DW ledger)

### DW-H2 — the live `agno`-Agent / LLM synthesis + F3-vss production retriever bring-up (ATTENDED) — DEFERRED
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story H2, § 7.3, FR-22(b))
  summary: H2 shipped the three wiki crews (`factory/crews.py`: `CompileCrew`, `LintCrew`,
    `QACrew`) with their DETERMINISTIC cores running fully offline on a fixture wiki — the real
    raw→compiled→answer flow, staleness propagation, and lint rules all exercised with NO network
    and NO model. Two production seams are INJECTABLE and default to the offline path, so the
    live bring-up is the attended deferral (mirrors DW-D3-1 LLM backend + DW-F3-2 vss provisioning):
    (1) **the `agno`-Agent / LLM synthesis** — `CompileCrew`'s `enricher` and `QACrew`'s
    `synthesizer` default to offline determinism (identity enrich; extractive answer). Standing up
    a real `agno` Agent over a resolved model backend (`pyforge.atlas.nl.backend.resolve_backend`
    — repo model-backend routing, env-driven, never a hardcoded endpoint) and running the crews
    through it is the deferred generative path; (2) **the F3 vss production retriever** —
    `QACrew`'s `retriever` defaults to the offline deterministic keyword-overlap ranker; the
    production retriever is `rag.store.DuckdbVssRagStore.similarity_search` (AD-4 single engine)
    wrapped to the `Retriever` signature, which needs the vss extension provisioned (DW-F3-2). Do
    NOT weaken the H2 gate to call a live model or bind a socket (NFR-12).
  evidence: `factory/crews.py` imports only `yaml` + stdlib + `.wiki` (AD-1 import-ban green over
    the new module); `tests/factory/test_crews.py` exercises compile/lint/Q&A + staleness
    propagation offline (26 crew tests). `Enricher`/`Synthesizer`/`Retriever` are the injectable
    seams; their defaults (`_identity_enricher`, `_extractive_synthesizer`, `keyword_retriever`)
    are offline. No `agno` Agent is constructed and no model/vss is loaded in-package.
