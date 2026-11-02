---
title: "25.18: Wave A's no-refresh recipes are re-bucketed live from the atlas"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
flag-exempt: recipe-build
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-2-track-b-refreshes-the-co-maintained-recipes-and-keeps-every-other-maintainer-s-work.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-14-wave-f-s-other-18-packages-are-built-by-their-feedstock-s-own-mirror.md
deferred: []
---

<intent-contract>

## Intent

**Problem:** Wave A (Story 25.2, 2026-10-09) bucketed every co-maintained package by matching it to a
`recipes/<name>/` directory and reading the first version line it found. That is how it misread the four `lfx-*`
bundles as `v1-ahead`: it read duplicate directories and their first output's version. Story 25.14 re-checked only
its 22 names. So the rest of Wave A's no-refresh buckets were never re-verified: 162 `v1-current`, the 4 `v1-ahead`
left after the `lfx-*` bundles, and 2 `other-non-pep440` (168 in all; 25.2's spec, Wave A table). Any multi-output
recipe in them was judged by its first version line, not by each output. The station memlog's line that
"`v1-ahead` (8) and `other-non-pep440` (2) get no story" was an agent's decision, not an operator ruling.
`DW-mason-25-14` records the mapping rule (use the atlas's `packages.feedstock_name`, never the directory name) and
stays open.

Wave A cannot be replayed: its baseline (`.cursor/track_b_baseline.json`, `.cursor/track_b_baseline.md`) and its script
(`.cursor/track_b_wave_a.py`) were never committed and are gone.

Found by the EGM fleet audit of 2026-11-01 (marshal Story 113.7): **MAS-D-C4**, cluster `mason-c09-wave-a-residue`.
Residue: `_bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:** re-derive the 168 live. Invoke `conda-forge-expert` first (Rule 1) and work in `-e local-recipes`, local
only.

- Map each co-maintained package to its feedstock through the atlas's `packages.feedstock_name` (`DW-mason-25-14`;
  Wave A step A3 of the companion `feedstock-refresh.md`), never by directory name.
- Compare each output's own `context` version with its feedstock's published version, so a multi-output recipe is
  judged output by output.
- Record every one of the 168 with its bucket and the reason in this spec.
- Refresh each one found behind with `pixi run -e local-recipes refresh-wave`, to an end state in CAP-35's outcome
  set (cluster `mason-c03`'s re-derive).

**Parked (operator ruling 2026-11-01):** it stays `backlog`, and `DW-mason-25-14` stays open until it lands.

Ledger key: `25-18-wave-a-s-no-refresh-recipes-are-re-bucketed-live-from-the-atlas`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (the feedstock refresh campaign is Mason's), FR-57: each track re-counts its scope live
  from the atlas; every recipe in scope reaches its feedstock's published version; no co-maintainer is dropped.
- No new CAP. `spec-feature-flag-governance` CAP-1, Q1: a `fix` carries no flag; `flag-exempt: recipe-build` records
  the class.
- AD-1, AD-15: no Mason package change; every CFE-surface edit lands in a `retro(cfe):` commit.

## Acceptance Criteria

1. **The scope is re-derived, not replayed.** Given the atlas refreshed within its `<atlas_max_age_d>` window, When the
   story maps Wave A's no-refresh packages through `packages.feedstock_name`, Then the spec records the live count
   before any refresh starts, and names every package with its feedstock.
2. **Every output is judged.** Then each recipe is bucketed by every output's own `context` version against its
   feedstock's published version (current, behind, ahead or non-PEP 440), with the reason recorded; no bucket rests on
   the first version line of a multi-output recipe.
3. **Behind recipes are refreshed.** Each recipe found behind is refreshed through
   `pixi run -e local-recipes refresh-wave <manifest> --gates --build --report-dir <dir>` and ends in CAP-35's outcome
   set (a green linux-64 build, a recorded G95 block, or `needs-review` with its reason). Its `recipe-maintainers` stays
   a superset of the deployed feedstock's (G53); a G72 suite's bundle pins move with its version.
4. **Ahead and non-PEP 440 are explained.** Each recipe bucketed ahead or non-PEP 440 carries the reason it stays.
5. **The deferral closes.** `DW-mason-25-14` in
   `_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md` gains a `verified:` line citing this
   spec's mapping, and closes.
6. **Local only.** No push, PR, fork, issue or comment outside `rxm7706/local-recipes`; no `mason recipe submit`,
   `mason package ship`, CFE `submit_pr` or `prepare_submission_branch`.
7. **Retro.** A `retro(cfe):` commit lands a CFE `CHANGELOG.md` semver entry, shared with Story 25.17's if both land
   together.
8. **Green.** `pixi run --frozen -e pyforge-mason pyforge-mason-test` passes.

## Boundaries & Constraints

**Always:**

- Invoke `conda-forge-expert` before any recipe edit.
- Read every verdict from the exit code, never through a pipe.
- Build each recipe into an isolated output directory (G52).

**Never:**

- Bucket a package by its `recipes/<name>/` directory name alone.
- Refresh a recipe outside Wave A's no-refresh buckets; Story 25.17 owns the build records of Epic 25's built recipes.
- Hand-write a `cfe-local-build-*` field, or hand-edit any `SPEC.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| single output, current | `context.version` = published | bucket `current`, no refresh | — |
| multi-output, one output behind | first output current, another behind | bucket `behind`, refreshed | — |
| ahead | local > published | bucket `ahead`, reason recorded | — |
| non-PEP 440 version | e.g. a date or tag form | bucket `non-pep440`, reason recorded | — |
| directory name differs from feedstock | atlas maps to another feedstock | judged against the atlas's feedstock | — |
| refresh still red | build fails after diagnosis | `needs-review` with the reason | — |

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-mason` CAP-35 (the feedstock refresh campaign is Mason's), FR-57. A fix, no new
  CAP.

Parent: CAP-35

- Dream: `docs/dreams/pyforge-mason.md` § Realization log, the 2026-11-01 entry (the EGM fleet audit).
- Audit finding carried: MAS-D-C4 (cluster `mason-c09-wave-a-residue`); residue
  `_bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 25 (the feedstock refresh campaign), done; a new not-done story reopens it (doctor Story 41.5).
- Ledger key: `25-18-wave-a-s-no-refresh-recipes-are-re-bucketed-live-from-the-atlas`.
- Deps: —.
- Surface: `recipes/<name>/recipe.yaml` for each recipe the re-bucket finds behind; this spec's bucket record;
  `_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md` (`DW-mason-25-14`); the CFE retro
  surface (`.claude/skills/conda-forge-expert/CHANGELOG.md` and its version carriers), committed alone as
  `retro(cfe): …`.
- Flag: none (a fix; `spec-feature-flag-governance` CAP-1, Q1); `flag-exempt: recipe-build`.
- Mode: parked at `backlog` (operator ruling 2026-11-01).
- Minted 2026-11-01 by marshal Story 113.7's landing PR, on the operator's acceptance of the audit's recommendations.

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**

- `pixi run -e local-recipes refresh-wave <manifest> --gates --build --report-dir <dir>` over the recipes found behind
  — expected: a report row per recipe, each in the outcome set.
- `grep -n "DW-mason-25-14:" -A12 _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md` —
  expected: a `verified:` line and a closed status.
- `pixi run -e pyforge-guild deferred-work-check` and `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0.

## Auto Run Result

Status: backlog

Summary: not yet dispatched (parked by the operator's ruling of 2026-11-01).

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (marshal Story 113.7), finding MAS-D-C4, cluster
  `mason-c09-wave-a-residue`; fix under `spec-pyforge-mason` CAP-35, no new CAP; parked at `backlog`.

## Review Triage Log

- (none yet)
