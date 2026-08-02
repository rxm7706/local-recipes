---
spec: bmad-output-hygiene
status: ready
owner-dream: docs/dreams/bmad-output-hygiene.md
companions: []
sources:
  - ../../../../../../docs/dreams/bmad-output-hygiene.md
assumptions:
  - Deletions (CAP-1, CAP-2) are safe because a live grep at spec-authoring time
    confirmed neither dead-scaffolding paths nor planning-artifacts/sprint-status.yaml
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

- **CAP-1 — dead test-scaffolding removal.**
  - **intent:** Remove `tests/`, `pytest.ini`, and `playwright.config.ts` from
    the 7 station roots that carry them with zero real tests (atlas, doctor,
    marshal, mason, scribe, steward, warden) — the real, wired suites live at
    `src/shared/packages/pyforge-<station>/tests/`.
  - **success:** None of the 7 directories contain these paths; no test runner
    or CI config anywhere in the repo referenced them (verified before removal).

- **CAP-2 — hollow `sprint-status.yaml` removal.**
  - **intent:** Delete the dead, identical-shape `planning-artifacts/sprint-status.yaml`
    stub (`0%`, empty arrays) from all 9 `pyforge-*` projects; `sprint-status-ledger.yaml`
    is the live, tracked twin already read by dashboard tooling.
  - **success:** File absent in all 9 projects; `dashboard_drift_check.py` and
    `bmad_drift_check.py` still exit 0 afterward.

- **CAP-3 — Genesis `test-architecture.md` fix.**
  - **intent:** Regenerate Genesis's `test-architecture.md` — the one station the
    2026-08-02 follow-up fix (`2957718d4c`) missed — so it describes Genesis's
    real, current, constitutive scope instead of the stale pre-split
    `src/pyforge_genesis` installer narrative.
  - **success:** The file makes no claim contradicted by Genesis's own current
    PRD/architecture.

- **CAP-4 — README placeholder fill.**
  - **intent:** Replace the unfilled `[role]`/`[responsibilities]` template text
    in marshal, herald, genesis, and doctor's planning-artifacts READMEs with
    real per-station content; check the remaining 5 stations during execution
    and fix any also found.
  - **success:** No station README contains a literal `[role]` or
    `[responsibilities]` token.

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
    (each is the sole copy at its path) so claimed story counts match reality
    (Mason: 38/38 → 4/38; Herald: 17/17 → 4/17, per each Dream/ledger).
  - **success:** Both files' claimed counts match `sprint-status-ledger.yaml`.

- **CAP-7 — `PROJECTS.md` Dream-pointer fix.**
  - **intent:** In `_bmad-output/PROJECTS.md`'s Projects table, repoint mason's
    `Dream:` from `docs/dreams/packaging-factory.md` (a `type: practice`
    satellite that scope-noted itself out of the station chain 2026-07-25) to
    `docs/dreams/pyforge-mason.md`; repoint herald's `Dream:` from
    `docs/dreams/design-code-bridge.md` (no longer exists) to
    `docs/dreams/pyforge-herald.md`.
  - **success:** Both pointers resolve to an existing `type: dream` file that is
    each station's actual charter.

- **CAP-8 — relocate the misfiled local-recipes doc set.**
  - **intent:** 12 files under `pyforge-marshal/planning-artifacts/` plus
    `SYNC-RUNBOOK.md` at the `pyforge-marshal` project root declare
    `project_name`/`project: local-recipes` in their own frontmatter — they are
    local-recipes' entire PRD/architecture set (`PRD.md`, `architecture.md` +
    its 4 split parts, `integration-architecture.md`, `validation-report-PRD.md`,
    `implementation-readiness-report.md`, `index.md`, `project-overview.md`,
    `source-tree-analysis.md`, `deployment-guide.md`, `development-guide.md`,
    `project-parts.json`), misfiled under the wrong BMAD project (matches the
    marker/symlink-desync hazard CLAUDE.md already documents; independently
    corroborated because CLAUDE.md itself cites `SYNC-RUNBOOK.md` at the
    local-recipes path). `git mv` all 13 to
    `_bmad-output/projects/local-recipes/` (12 into `planning-artifacts/`,
    `SYNC-RUNBOOK.md` to the project root), preserving history.
  - **success:** All 13 files exist under `local-recipes/`, absent from
    `pyforge-marshal/`; marshal's own spec/PRD/architecture chain (confirmed to
    never cite these files) is unaffected.

- **CAP-9 — marshal-brief layout fix.**
  - **intent:** `product-brief-pyforge-marshal.md` is marshal's genuine, sole
    brief (cited as a fully-absorbed input by both the canonical `prd.md` and
    `architecture.md`) — just unsharded. `git mv` it to
    `briefs/brief-pyforge-marshal-2026-07-25/brief.md`, matching its own
    `created: 2026-07-25` and every other station's `briefs/brief-<slug>-<date>/brief.md`
    shape.
  - **success:** File lives at the sharded path; no remaining reference to the
    old loose path.

## Constraints

- Every change lands only under `_bmad-output/`, `docs/dreams/`, and this
  branch — nothing in `recipes/` or `pixi.toml` is touched. The PR needs the
  `maintenance` label; the pixi/`environment.yaml` sync gate does not apply.
- CAP-1 and CAP-2 deletions each require a live, grep-verified "nothing reads
  this path" check immediately before removal — not just trust in the Dream's
  original 2026-08-02 audit, which can go stale as tooling changes underfoot.
- Archival (CAP-5) always uses `git mv` into the mirrored `archive/` path.
  Nothing in this spec is hard-deleted except the two confirmed-dead,
  confirmed-unread stub file classes in CAP-1/CAP-2.

## Non-goals

- No content edits to the relocated local-recipes files (CAP-8) beyond the
  move itself — any drift within them is a separate matter.
- No new PRD, architecture, or epics chain for this cleanup itself.
- No changes to `recipes/`, the `conda-forge-expert` skill, or any station's
  actual product code.

## Success signal

Re-running the same audit method (the 5-agent sweep's grep/read checks) across
all 9 `pyforge-*` planning trees finds zero remaining Cluster 1/2/3 items from
`docs/dreams/bmad-output-hygiene.md`, and `bmad_drift_check.py` / `dream_chain_check.py`
still exit 0.
