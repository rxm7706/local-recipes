---
title: "Story 6-9: The `scripts/` shims retire"
type: "change"
created: "2026-08-09"
status: "done"
authored: "spec-first, ahead of implementation (operator instruction 2026-08-09: seed -> Dream -> Spec -> code)"
owner-dream: docs/dreams/pyforge-doctor.md
context:
  - '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md'
  - '{project-root}/scripts/detectors.py'
  - '{project-root}/.github/workflows/detectors.yml'
  - '{project-root}/scripts/spec_surface_allowlist.txt'
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-regenerable-factory/SPEC.md'
warnings:
  - 'BLOCKING PRECONDITION, found at spec time: deleting the shims as written would leave CI discovering ZERO detectors and exiting 0 — a structural false green. See "The precondition" below. Do not start the deletions until it is closed.'
---

## Intent

With all ten verdicts resolving as Doctor sources, remove the `scripts/*_check.py` detector
files, re-point their pixi tasks at Doctor, and retire the governance claims they leave
behind. FR-15.

**Surface:** `scripts/`, `pixi.toml`, `scripts/spec_surface_allowlist.txt`, meta-tests

`Deps: S-6.4, S-6.5, S-6.7, S-6.8` — every one of the ten must have landed first.

## The precondition (found at spec time — this is the story's real risk)

**Deleting the shims as the AC describes would silently gut CI's detector coverage.**
Verified, not inferred:

- `scripts/detectors.py::discover()` finds detectors by **AST-scanning `scripts/*_check.py`
  on disk**. Delete the files and it finds nothing.
- Its companion `_doctor_sources()` reads Doctor's `REGISTRY` instead — but returns
  `(False, [])` when `pyforge.doctor` is not importable, and its own docstring says this is
  **"DELIBERATELY not the same discipline as `discover()`'s 'unknown, never green'"**,
  because Doctor is a lean package absent from most environments.
- `.github/workflows/detectors.yml` runs on plain `setup-python` with
  `pip install --quiet pyyaml playwright` — **no pixi, no `pyforge-doctor`**.
- Observed today: `detectors.py --list` prints
  `doctor sources (declared, not scanned): (unavailable -- pyforge.doctor is not importable
  in this environment)` **even under `local-recipes`**.

Compose those and the post-retirement CI run discovers zero detectors, reports nothing, and
**exits 0**. That is the precise failure class `unpushed_work_check.py`'s docstring names —
*"a gate reporting success because it is standing somewhere the failure cannot occur"* — and
it would arrive as a side effect of a cleanup story, which is how it would go unnoticed.

**Both halves are required before any file is deleted:**

1. **CI gains Doctor.** `detectors.yml` must install `pyforge-doctor` (or switch that job to
   the pixi environment that carries it). Prove it by asserting the run reports a non-zero
   detector count, not merely that it exits 0.
2. **The degrade becomes "unknown, never green."** Once the scripts are gone, an
   unimportable `pyforge.doctor` no longer means *partial* coverage — it means **no**
   coverage, so `_doctor_sources()`'s `(False, [])` must become a hard `exit 2` (unknown)
   rather than an empty pass. The current behaviour is correct **only while the scripts
   still exist**; retiring them is exactly what invalidates it. Update the docstring's
   stated rationale in the same change, or the next reader will restore the old behaviour
   from it.

A regression test must pin this: **with `pyforge.doctor` unavailable, `detectors.py`
reports unknown and exits non-zero — never 0 with an empty registry.** Mutation-test it the
way Story 6.7's conformance test was: make Doctor unimportable and confirm the runner goes
red rather than green.

## Acceptance Criteria

- **Given** all 10 verdicts resolve as Doctor sources, **Then** the `scripts/` detector
  files are removed and their pixi tasks re-point at Doctor.
- **And** each retired file's allowlist entry is deleted — the allowlist **shrinks**, per
  `spec-regenerable-factory` CAP-2.
- **And** the two meta-tests that invoke the old paths (`test_bmad_artifacts_in_sync.py`,
  `test_spec_surface_check.py`) are **updated, not deleted**.
- **And** the four detectors that are **governed rather than allowlisted** transfer their
  surface claim: `spec-regenerable-factory`'s `surface:` globs for `spec_surface_check.py`,
  `bmad_drift_check.py`, `dream_chain_check.py`, `deferred_work_check.py` are **deleted**,
  as is `spec-surface-drift-reconciliation`'s claim on `spec_surface_check.py`. The moved
  files are governed by `spec-pyforge-doctor`'s own
  `src/shared/packages/pyforge-doctor/**` glob the moment they land there, so the transfer
  needs **no new Doctor surface entry** — only retirement of the stale ones.
- **And** those retirements are **verified, not assumed**: a `surface:` glob matching nothing
  is **not** a finding today (only allowlist entries produce `stale-allowlist`), so a stale
  claim rots silently. Confirm each retired glob by **diffing the governed-file count before
  and after**.
- **And** `spec-regenerable-factory`'s surface reaching **zero** ends its governance role —
  recorded in its memlog rather than left implicit, since that Spec is `shipped` and nothing
  else would mark the hand-off.
- **And** (added by this spec) CI's detector job reports a **non-zero detector count** after
  the retirement, and `detectors.py` **exits non-zero** when Doctor is unavailable.

## Design notes

### Which files retire, and which deliberately do not

Ten verdicts re-home; **three detectors stay**, and the distinction should be stated in the
change rather than discovered later:

- `loop_stall_check.py` and `unpushed_work_check.py` — Marshal's own operational watchdogs
  over live runs, not conformance verdicts on an artifact. Their allowlist entries say so
  explicitly and must **remain**.
- `llms_full_check.py` — judges the library catalog, not a station artifact.

Also staying: `fleet_picture.py` (a report, never a gate), `detectors.py` (the registry
itself), and `spec_surface_allowlist.txt` (cannot govern itself).

### Order of operations

Retire in an order where nothing is ever unmeasured:

1. Close the precondition (CI gains Doctor; degrade becomes unknown-never-green) and prove
   it with the regression test.
2. Re-point pixi tasks at Doctor while the scripts still exist — both paths live, verdicts
   comparable.
3. Delete the scripts and their allowlist entries.
4. Retire the surface globs, each confirmed by a governed-file-count diff.
5. Record `spec-regenerable-factory`'s hand-off in its memlog.

Steps 2 and 3 are separable and should be separate commits; a single commit that both
re-points and deletes leaves no state in which the two implementations can be compared.

### The quiet asymmetry this story has to work around

`stale-allowlist` exists; there is no `stale-surface-glob`. Deleting an allowlist entry that
still matches something is caught; leaving a `surface:` glob that matches nothing is not.
That is why the AC demands a **before/after governed-file count** rather than a visual check
— the same "too-broad or stale glob is invisible by construction" asymmetry
`spec-regenerable-factory`'s own memlog already records.

Worth considering as follow-up (not this story's scope): a `stale-surface-glob` finding
would close the asymmetry permanently and is a natural Doctor source, since the artifact it
judges is Marshal-governed.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `b8131a1df6` (2026-08-07, "docs: promote marshal Story 6.9 + steward Epic 4 story specs to tracked planning-artifacts"); also `5cf23f9d33` (2026-08-07, "marshal: sync sprint-status ledger — Story 6.9 done, Epic 6 fully closed (9/9)"); also `8bd05ca2e2` (2026-08-07, "marshal: fix Story 6.9 review finding (relative-path cwd-dependent resolvability)"). Ledger row `6-9-the-scripts-shims-retire: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-6-9-tool-surface-rendering-and-preflight-probe.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-4-1-a-ceiling-can-be-declared-machine-readably.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-4-2-the-declared-ceiling-is-one-command-away.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-4-3-asking-am-i-under-budget-never-lies.md`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `6-9-the-scripts-shims-retire: done`).
- `## Auto Run Result` reconstructed from git (none survived).
