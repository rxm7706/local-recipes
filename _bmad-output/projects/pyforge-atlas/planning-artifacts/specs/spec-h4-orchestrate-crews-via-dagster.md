---
title: 'Story H4 (9.4): Orchestrate Crews via Dagster'
type: 'feature'
status: 'regenerated'
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'
enriched: '2026-07-25 (merged PR #102 body + main commit log; dev narrative recovered, review-triage partial)'
---

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story H4 (9.4): Orchestrate Crews via Dagster

As the operator,
I want Dagster assets, sensors (new raw files), and schedules (weekly linting) triggering the Agno crews autonomously,
So that the factory layer runs itself.

**Acceptance Criteria:** (spec § 9 Story H4, binding)

**Given** the H2 crews and the C1 Dagster repository
**When** the assets/sensors/schedules land
**Then** an asset dry-run enumerates the crew assets
**And** a simulated new-raw-file event triggers the compile crew via a Sensor.

- **FRs:** FR-22(d), FR-6.
- **Invariants:** AD-22, AD-6, AD-23.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** `dagster-dryrun` (crew assets enumerate) + simulated-trigger fixture.
- **Depends on:** H1, H2, H3; C1.
- **DELIVERED (2026-07-18 — closes Wave H + the migration):** the Wave-H crews run on C1's single Dagster plane (AD-6/AD-23). `orchestration/definitions.py` gains crew ASSETS (`compiled_wiki` → CompileCrew, `wiki_lint_report` → LintCrew, `deps=[compiled_wiki]`), their asset-jobs (`wiki_compile_job`/`wiki_lint_job`), a weekly LINT schedule (`wiki_lint_schedule`, `0 6 * * 1`, § 7.2), and the new-raw-file compile SENSOR (`wiki_raw_file_sensor` → `wiki_compile_job`, ships STOPPED). The raw-scan + cursor-dedupe DECISION logic lives in `orchestration/wiki_events.py` (dagster-free — AD-1 holds; only definitions.py imports dagster). `dagster definitions validate` green; a simulated new-raw-file event (injected lister + `build_sensor_context`) → one `RunRequest` for the compile job. Live daemon + wiki-store bring-up DEFERRED (DW-H4). Gate `test_definitions_dryrun.py` H4 section (+12; C1/G3 invariants scoped to kedro op-jobs via `_kedro_jobs`). Independent review found 1 SHOULD-FIX (`_decode_cursor` crashed on a valid-JSON-but-nested cursor, breaking its "never a crash" contract) — fixed (filter to str inside the guard) + regression-tested; the `_kedro_jobs` scoping was verified NOT to weaken any C1/G3 guard.

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

### Dev summary — merged PR #102: H4: orchestrate the Wave-H wiki crews via Dagster (FR-22(d)/FR-6)

## Story H4 — Orchestrate Crews via Dagster (FR-22(d)/FR-6, § 7.2) · the FINAL story

Wires the Wave-H agno wiki crews onto C1's **single** Dagster plane (AD-6/AD-23). Completing this closes Wave H and the entire 32-story Kedro migration.

### Changes
- **`orchestration/wiki_events.py` (NEW, dagster-free — AD-1 holds)** — the new-raw-file decision logic: `scan_raw_docs` (filesystem read) + `evaluate_raw_scan` (cursor-dedupe: the cursor stores the seen raw-doc name-set; new names → run with a deterministic `run_key` + advanced cursor; nothing new → skip, cursor untouched). Mirrors `event_source.py`.
- **`orchestration/definitions.py`** (the AD-1 glue module):
  - Crew **assets** — `compiled_wiki` (CompileCrew) + `wiki_lint_report` (LintCrew, `deps=[compiled_wiki]`); write only the wiki tree (AD-22); wiki root env-driven (`ATLAS_WIKI_ROOT`, AD-2).
  - Crew asset-**jobs** `wiki_compile_job` / `wiki_lint_job`; a weekly LINT **schedule** (`wiki_lint_schedule`, `0 6 * * 1`); the new-raw-file compile **sensor** (`wiki_raw_file_sensor` → `wiki_compile_job`, AD-23 same plane, ships **STOPPED**). Injectable `raw_lister`; a failing lister degrades to `SkipReason`.
- **Tests** — the C1/G3 op-level invariants are scoped to the kedro op-jobs via a new `_kedro_jobs` helper (the factory asset jobs legitimately carry no kedro ops/tags).

### Independent review
An adversarial fresh-eyes review found **1 SHOULD-FIX** — `_decode_cursor` crashed on a valid-JSON-but-nested cursor (`[{...}]`), breaking its "never a crash" contract and able to kill a sensor tick. **Fixed** (filter to str inside the guard) + 8 regression cases. The review separately **verified** the `_kedro_jobs` scoping did NOT weaken any C1/G3 guard, and AD-1 holds (`wiki_events.py` imports no dagster).

### Deferred
- Live daemon + wiki-store bring-up (sensor RUNNING, weekly lint firing, real store) → **DW-H4**.

### Verification
- `dagster definitions validate` — **passes** offline.
- `test_definitions_dryrun.py` H4 section: assets enumerate, crew jobs resolve, weekly lint schedule, sensor targets the compile job, a **simulated new-raw-file event → RunRequest for the compile crew**, no-new-file/already-seen → SkipReason, lister-error degrades, ships STOPPED, + malformed-cursor regressions.
- Full atlas suite: **795 passed**. AD-1 import-ban green.

### Commits on `main`

- `4710a8aec8` H4: orchestrate the Wave-H wiki crews via Dagster (FR-22(d)/FR-6) (#102)  _(dev-landing)_

_This PR also carried an automated Gemini review; not reproduced here per repo policy ([[feedback_no_gemini_reviews]])._

