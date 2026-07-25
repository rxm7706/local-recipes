---
title: 'Story H4 (9.4): Orchestrate Crews via Dagster'
type: 'feature'
status: 'regenerated'
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'
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
