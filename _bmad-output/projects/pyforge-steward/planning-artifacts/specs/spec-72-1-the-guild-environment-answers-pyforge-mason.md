---
title: "72.1: The Guild environment answers pyforge mason"
type: 'fix'
created: '2026-09-28'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py
  - pixi.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** measured 2026-09-28, `pixi run -e pyforge-guild pyforge mason --help` answers
`unknown station 'mason'; known: doctor, herald, marshal, scribe, steward` (exit 2), and `mason` is not on the Guild's
`PATH`. The Mason persona (`.claude/skills/bmad-agent-mason/SKILL.md`) may act only through `pyforge mason …`, and
`pyforge-guild` is the session default every agent and harness runs (CAP-5), so the persona's only grammar fails where it
is used. The front door is correct as built: `pyforge.core.dispatch` maps a station token to the primary console script of
a `pyforge-*` distribution installed in the running environment (`script_map_from_installed`,
`src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py:94-105`, with a per-station `distribution()` fallback at
`:154-166`). `[feature.pyforge-guild.dependencies]` (`pixi.toml:841-864`) installs core, doctor, marshal, steward,
herald, scribe and the testing kit — never `pyforge-mason`. Environment composition is this station's (CAP-5, Story 63.1).

**Approach:** add `pyforge-mason = { path = "src/shared/packages/pyforge-mason" }` to `[feature.pyforge-guild.dependencies]`
with a comment citing CAP-161; the package's own run-dependencies (its engines and `pyforge-core`) come with it —
`pyforge-foundry-full` already solves Guild + Mason together, so the union is known to resolve. Correct the feature's
banner comment, which still lists "core, doctor, marshal, steward, testing-kit", to name what the environment carries.
Re-solve (`pixi.lock`), regenerate `environment.yaml` (`pixi project export conda-environment -e build > environment.yaml`,
expected byte-identical — `build` does not compose the Guild), and regenerate the two reference pages that read the Guild's
composition (`pixi run -e pyforge-guild docs-station-cli`, `docs-environments`). A new steward meta-test,
`src/shared/packages/pyforge-steward/tests/meta/test_guild_environment_stations.py`, reads `pixi.toml` with `tomllib` and
reds a `[feature.pyforge-guild.dependencies]` that lacks `pyforge-mason`. Measure the cold install of `pyforge-guild`
(delete that environment, `pixi install -e pyforge-guild`, `du -sh`) and record it in this spec against CAP-5's 1 GB bound.

Ledger key: `72-1-the-guild-environment-answers-pyforge-mason`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-161 (FR-34; extends CAP-5); AD-5; Kinship `spec-pyforge-mason:CAP-29` (Mason's persona and station skill speak `pyforge mason …`).

## Acceptance Criteria

- Given the Guild environment re-solved with `pyforge-mason` When `pixi run -e pyforge-guild pyforge mason --help` runs Then it exits 0 and prints Mason's nouns
- Given the same environment When `pixi run -e pyforge-guild pyforge mason doctor --format json` runs Then it exits 0 with one JSON document on stdout reporting Mason's version and the recipe verbs' availability as it finds it
- Given `pixi.toml` without `pyforge-mason` in `[feature.pyforge-guild.dependencies]` When `test_guild_environment_stations.py` runs Then it fails naming the missing dependency
- Given a cold `pixi install -e pyforge-guild` When its environment directory is measured Then it is under 1 GB, recorded in this spec
- Given `pixi.toml` changed When `pixi run -e pyforge-guild pyforge-station-tests` and `pixi run -e pyforge-guild detectors-ci` run Then both exit 0

## Boundaries & Constraints

**Always:**
- The edit is the story author's; steward code reads `pixi.toml` and never writes it (AD-5).
- `pixi.toml` is shared surface: run `pyforge-station-tests` before pushing and regenerate `environment.yaml` in the same
  change. Its co-governors (several Specs govern `pixi.toml`): add a memlog entry on every Spec `spec-surface-check`
  names, `git add`, one scoped `--write-baseline --spec` per named Spec from a clean tree, re-check and read the exit code;
  run `python scripts/chain_currency_sweep_check.py --project <slug> --json` for each project whose memlog moved and carry
  its cascade note if it fires.
- The PR carries the `maintenance` label.

**Never:**
- Do not change `pyforge-core`'s `dispatch.py` — the front door works as built.
- Do not add `pyforge-warden` (its `osv-scanner` pin, `pixi.toml:844-849`) or `pyforge-atlas` to the Guild here.
- Do not add a task to the Guild, or move a recipe-factory dependency into it; recipe work stays in `-e local-recipes`.
- Do not raise a `postgresql`/`libpq` pin or lift a psycopg cap to clear a solve (fnd:CAP-12).
- Do not run a live `pixi add` / `pixi update`; edit the manifest and re-solve.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| front door | `pyforge mason --help` in the Guild | exit 0, Mason's usage | before the fix: exit 2, `unknown station 'mason'` |
| degraded recipe verbs | Guild lacks CFE's import floor | `mason doctor` exits 0 and names the unavailable verbs | never a traceback |
| feature regresses | `pyforge-mason` removed from the feature | meta-test fails | — |
| solve conflict | the Guild + Mason union fails to solve | stop and report the conflicting pins | never loosen an estate floor to clear it |
| size | cold install ≥ 1 GB | story fails CAP-5's bound; report the heaviest additions | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-161 (FR-34).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-28 — Proposed: Mason's skill cell is two skills, and the Guild environment answers `pyforge mason`*.
Ledger key: `72-1-the-guild-environment-answers-pyforge-mason`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; `test_guild_environment_stations.py` runs inside it).

**Manual checks:**
- `pixi run -e pyforge-guild pyforge mason --help` and `pixi run -e pyforge-guild pyforge mason doctor --format json` — expected: exit 0.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (`pixi.toml` is shared surface).
- `pixi run -e pyforge-guild detectors-ci` and `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0.
- `pixi run -e pyforge-guild docs-station-cli -- --check` and `pixi run -e pyforge-guild docs-environments -- --check` — expected: exit 0 after regeneration.

## Review Triage Log
