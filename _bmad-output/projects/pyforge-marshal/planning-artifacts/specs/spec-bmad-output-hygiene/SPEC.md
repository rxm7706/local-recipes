---
spec: bmad-output-hygiene
status: in-progress
owner-dream: docs/dreams/bmad-output-hygiene.md
companions: []
sources:
  - ../../../../../../docs/dreams/bmad-output-hygiene.md
assumptions:
  - Archival moves (CAP-1, CAP-2) are safe because a live grep at spec-authoring
    time confirmed neither dead-scaffolding paths nor planning-artifacts/sprint-status.yaml
    are read by any tracked script — only the same-named but distinct
    implementation-artifacts/sprint-status.yaml (Tier-3) and sprint-status-ledger.yaml
    are live-read by dashboard tooling.
open_questions: []
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for this cleanup. `docs/dreams/bmad-output-hygiene.md` is cited for narrative rationale only.

# SPEC — bmad-output-hygiene

## Why

A single bulk commit (`dad47c408a`, 2026-08-02) stamped generic, unreviewed
template content across all 9 BMAD projects' planning trees at once: dead test
scaffolding, a hollow `sprint-status.yaml` stub, and in places a fabricated
`test-architecture.md` or an unfilled README placeholder. Remediation since then
has been real but inconsistent — some stations fixed same-day, Genesis never
fixed, dead scaffolding and the hollow stub never addressed anywhere. A same-day,
same-session finding added two more stale `PROJECTS.md` Dream pointers to the
pile. Every station's planning tree should tell the truth about itself — real
content or an honest placeholder, never a templated fiction that happens to
compile.

## Capabilities

- **CAP-1 — dead test-scaffolding archival.**
  - **intent:** `git mv` `tests/`, `pytest.ini`, and `playwright.config.ts` out
    of the 7 station roots that carry them with zero real tests (atlas,
    doctor, marshal, mason, scribe, steward, warden) into the mirrored
    `archive/_bmad-output/projects/<station>/...` path (the existing
    consolidation convention) — never delete outright. The real, wired suites
    live at `src/shared/packages/pyforge-<station>/tests/` and are untouched.
  - **success:** None of the 7 station roots contain these paths; each exists
    under its mirrored `archive/` path; no test runner or CI config anywhere
    in the repo referenced the original paths (verified before moving).

- **CAP-2 — hollow `sprint-status.yaml` archival.**
  - **intent:** `git mv` the dead, identical-shape `planning-artifacts/sprint-status.yaml`
    stub (`0%`, empty arrays) out of all 9 `pyforge-*` projects into the
    mirrored `archive/` path; `sprint-status-ledger.yaml` is the live, tracked
    twin already read by dashboard tooling and is untouched.
  - **success:** File absent from its original path in all 9 projects, present
    under its mirrored `archive/` path; `dashboard_drift_check.py` and
    `bmad_drift_check.py` still exit 0 afterward.

- **CAP-3 — Genesis `test-architecture.md` fix.**
  - **intent:** Regenerate Genesis's `test-architecture.md` — the one station the
    2026-08-02 follow-up fix (`2957718d4c`) missed — so it describes Genesis's
    real, current, constitutive scope instead of the stale pre-split
    `src/pyforge_genesis` installer narrative.
  - **success:** The file makes no claim contradicted by Genesis's own current
    PRD/architecture.

- **CAP-4 — README placeholder fill.**
  - **intent:** The literal `[role]`/`[responsibilities]` placeholders actually
    live in each station's project-root `README.md` (not planning-artifacts,
    as originally assumed) — an identical template across 8 of 9 stations
    (all but atlas, which has none), also referencing the CAP-1-archived
    `tests/`/`pytest.ini`/`playwright.config.ts` as if real. Replace the
    placeholder sentence with a real per-station role description in all 8,
    and correct the Structure/Testing sections to point at the real suites
    under `src/shared/packages/pyforge-<station>/tests/`. Also replace the 6
    generic-but-not-literally-placeholder `planning-artifacts/README.md`
    boilerplate (marshal, genesis, doctor, mason, scribe, steward — byte-identical
    3-line stub) with real content, matching the Dream's spirit even though
    its exact bracket-token wording didn't match what was on disk.
  - **success:** No station README contains a literal `[role]` or
    `[responsibilities]` token; no README describes archived scaffolding as live.

- **CAP-5 — orphaned single-file archival.**
  - **intent:** `git mv` Atlas's `RESUME-EPIC-10.md` and Herald's
    `intake-video-scripts-manticore-2026-07-31.md` into the mirrored `archive/`
    path, matching the convention already used by the same-day satellite-Dream
    consolidations. Never a hard delete.
  - **success:** Both files exist under their mirrored `archive/` path, are
    absent from their original path, and have zero remaining repo references to
    the original path.

- **CAP-6 — `project-context.md` drift fix.**
  - **intent:** Regenerate Mason's and Herald's `project-context.md` in place
    (each is the sole copy at its path). Live re-check at execution time found
    the Dream's cited "real" counts (Mason 4/38, Herald 4/17) had themselves
    gone stale — the ledgers now show Mason 4/48 and Herald 4/27 (story
    inventories grew after the Dream's 2026-08-02 audit). Both files were also
    fabricated beyond the count: a generic "Choreography & Story Executor" /
    "Presentation Deck & Infographic Layer" role label, and reference paths
    pointing at a `SPEC.md`/`architecture.md` that don't exist at those
    locations. Regenerated both with accurate role descriptions, live counts
    from `sprint-status-ledger.yaml`, and correct file paths.
  - **success:** Both files' claimed counts match `sprint-status-ledger.yaml`;
    all referenced paths exist.

- **CAP-7 — `PROJECTS.md` Dream-pointer fix.**
  - **intent:** In `_bmad-output/PROJECTS.md`'s Projects table, repoint mason's
    `Dream:` from `docs/dreams/packaging-factory.md` (a `type: practice`
    satellite that scope-noted itself out of the station chain 2026-07-25) to
    `docs/dreams/pyforge-mason.md`; repoint herald's `Dream:` from
    `docs/dreams/design-code-bridge.md` (no longer exists) to
    `docs/dreams/pyforge-herald.md`.
  - **success:** Both pointers resolve to an existing `type: dream` file that is
    each station's actual charter.

- **CAP-8 — fix CLAUDE.md's stale `local-recipes` pointer (revised; was a
  proposed relocation, reverted).**
  - **intent:** 13 files (12 under `pyforge-marshal/planning-artifacts/` plus
    `SYNC-RUNBOOK.md` at the project root) carry `project_name`/`project:
    local-recipes` in their own frontmatter, which looked like misfiling.
    `scripts/bmad_drift_check.py` (lines 50–53) records that this factory-doc
    set was deliberately moved from the placeholder `local-recipes` BMAD
    project to `pyforge-marshal` on 2026-07-28 (Charter §5 dissolution; owned
    by Marshal via the `regenerable-factory` practice) — the files are exactly
    where they belong. **CLAUDE.md §"Keeping BMAD artifacts in sync"** (lines
    102, 107) was never updated after that move and still says
    `_bmad-output/projects/local-recipes/`, which is what caused the
    misdiagnosis. Fix CLAUDE.md's two mentions to `pyforge-marshal` instead.
  - **success:** CLAUDE.md's text matches where `bmad_drift_check.py`,
    `pixi.toml`, and `docs/dashboard/generate.py` actually read from.
  - **note:** A relocation was executed, then reverted in full (verified via
    `git status` and a post-revert `bmad-drift-check --integrity-only` pass)
    before this branch went anywhere. Left here for the record.

- **CAP-9 — marshal-brief layout fix.**
  - **intent:** `product-brief-pyforge-marshal.md` is marshal's genuine, sole
    brief (cited as a fully-absorbed input by both the canonical `prd.md` and
    `architecture.md`) — just unsharded. `git mv` it to
    `briefs/brief-pyforge-marshal-2026-07-25/brief.md`, matching its own
    `created: 2026-07-25` and every other station's `briefs/brief-<slug>-<date>/brief.md`
    shape.
  - **success:** File lives at the sharded path; no remaining reference to the
    old loose path.

- **CAP-10 — herald brief/architecture directory rename (found via the fleet
  dashboard, added after reopening).**
  - **intent:** `docs/dashboard/generate.py`'s fleet scan reports real gaps
    `['brief', 'arch']` for herald — pre-existing on `main`, not introduced by
    this branch. `_stage_globs()` expects
    `briefs/brief-pyforge-herald-*/brief*.md` and
    `architecture/architecture-pyforge-herald-*/*.md` (matching every other
    station and herald's own `prds/prd-pyforge-herald-2026-08-01/`), but
    herald's directories are named `briefs/brief-herald-pitch-2026-08-01/`
    and `architecture/architecture-herald-pitch-2026-08-01/` — the
    pre-consolidation Dream slug, not the station slug. Content is current
    and real; only the directory name is wrong. `git mv` both to the
    `pyforge-herald` naming, matching CAP-9's fix shape exactly. Update live
    citations (`project-context.md`, `prd.md` `inputs:`, the spec's
    `sources:`); leave dated historical/narrative references (dream files,
    the archived dashboard snapshot) untouched. Regenerate and commit
    `docs/dashboard/data.js` (generated file — never hand-edited) as the
    final step.
  - **success:** `docs/dashboard/generate.py --source sprint-status` reports
    `pyforge-herald` `gaps: []`.

- **CAP-11 — currency-check grace period (found via user report of universal
  "outdated" readings after CAP-10).**
  - **intent:** `_currency()`'s `_FEEDS` loop in `docs/dashboard/generate.py`
    flags any positive timestamp difference — zero grace period. Every
    `spec`/`prd` finding across all 8 stations is 0–1 days, because a spec's
    `.memlog.md` gets a fresh `updated:` on every append, far more often than
    its PRD — making "spec newer than prd" true by construction, not a real
    drift signal. Add a small grace period (2 days) so only a difference
    exceeding it counts. This is the same "always red, gets ignored"
    suppression the code already applies to the separate `behind-code`
    check, extended to `_FEEDS`.
  - **success:** the 0–1 day `spec`/`prd` findings disappear from all 8
    stations; the 5 genuine multi-day pairs (CAP-12) still surface.

- **CAP-12 — catch up the genuinely stale pairs (scope refined during
  execution: 3 fixed, 3 honestly left as real findings).**
  - **intent:** Warden (`prd`/`arch`, `prd`/`gates`), doctor (`prd`/`arch`),
    scribe (`prd`/`arch`), steward (`prd`/`arch`), mason (`arch`/`epics`)
    predate this cleanup. Each PRD's own `currency_review` note was read
    first to judge whether its last bump was structural (safe to re-stamp
    downstream) or real content drift (must not be papered over):
    - **scribe, steward, warden (`prd`/`arch`)** — each PRD's
      `currency_review` explicitly says the bump was structural (project
      relocation), content unchanged. Architecture content re-checked
      against the unchanged PRD, confirmed current, re-stamped with a
      matching `updated:`/`currency_review:` pair. Stamping architecture's
      date pushed staleness downstream to `arch`/`epics` (a new finding);
      fixed by verifying epics.md was likewise unaffected and stamping it
      too, rather than leaving a moved goalpost.
    - **doctor (`prd`/`arch`)** — the PRD's own `currency_review` says the
      bump added real content (FR-10..13 from a dream-consolidation pass).
      Architecture genuinely has fallen behind. Left unfixed and visible —
      real architecture authoring, out of scope for a hygiene spec.
    - **mason (`arch`/`epics`)** — architecture binds FR-1..FR-46 but the
      PRD's own `frCount: 50`; a genuine 4-FR gap. Left unfixed and visible,
      same reasoning.
    - **warden (`prd`/`gates`)** — deliberately left unstamped. An
      implementation-readiness report is a point-in-time snapshot, not a
      living document; bumping its date would misrepresent that a new gate
      check happened. Structural property of the artifact type, not a
      defect — noted for a possible future `generate.py` refinement, not
      fixed here.
  - **success:** fleet currency findings 16 → 4 (atlas/herald/marshal/scribe/steward
    fully clean); the 3 remaining findings (doctor, mason, warden `prd`/`gates`)
    are genuine and intentionally still visible, not silently suppressed.

## Constraints

- Every change lands only under `_bmad-output/`, `docs/dreams/`, and this
  branch — nothing in `recipes/` or `pixi.toml` is touched. The PR needs the
  `maintenance` label; the pixi/`environment.yaml` sync gate does not apply.
- Nothing in this spec is ever hard-deleted. Every removal (CAP-1, CAP-2,
  CAP-5) is a `git mv` into the mirrored `archive/_bmad-output/projects/<station>/...`
  path, matching the existing consolidation convention (user directive,
  mid-execution).
- CAP-1 and CAP-2 archival moves each require a live, grep-verified "nothing
  reads this path" check immediately before moving — not just trust in the
  Dream's original 2026-08-02 audit, which can go stale as tooling changes
  underfoot.
- `docs/dashboard/data.js` is generated (`docs/dashboard/generate.py`) — never
  hand-edited. CAP-10 regenerates it as a final step, not a manual patch.
- CAP-12 never silently bumps a currency date to satisfy the detector —
  each re-stamp requires an actual read of both sides of the pair first.

## Non-goals

- No relocation of the pyforge-marshal-owned factory-doc set (`PRD.md`,
  `architecture.md`, etc.) — that placement is correct and intentional
  (2026-07-28 move); only CLAUDE.md's stale pointer to it is fixed (CAP-8).
- No new PRD, architecture, or epics chain for this cleanup itself.
- No changes to `recipes/`, the `conda-forge-expert` skill, or any station's
  actual product code.

## Success signal

Re-running the same audit method (the 5-agent sweep's grep/read checks) across
all 9 `pyforge-*` planning trees finds zero remaining Cluster 1/2/3 items from
`docs/dreams/bmad-output-hygiene.md`, and `bmad_drift_check.py` / `dream_chain_check.py`
still exit 0. `docs/dashboard/generate.py --source sprint-status`'s fleet scan
reports zero `gaps` for all 9 stations and only genuine, honestly-surfaced
`staleBy` findings (doctor's FR-10..13 architecture gap, mason's FR-47..50
gap, warden's point-in-time readiness snapshot) — never noise from a
zero-grace-period detector.
