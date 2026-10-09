---
title: "72.1: The Guild environment answers pyforge mason"
type: 'fix'
created: '2026-09-28'
status: 'done'
baseline_revision: 'd5a23fb37a857f657bb4d5338697891ec385509d'
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
(delete that environment, `pixi install -e pyforge-guild`, `du -sh` and `du -sm`, and the `conda-meta` package count) and
record it in this spec against CAP-5's bound as restated 2026-09-28: 2 GB (it was 1 GB; see the amendment below).

**Amended 2026-09-28 (later)** (steward memlog decision of the same date; Dream entry *Decided: `pyforge-atlas` stays out of
the Guild environment, and the Guild says why*):
- **Atlas's exclusion is documented beside warden's.** The banner rewrite adds, in `[feature.pyforge-guild.dependencies]`,
  a comment in the same form as warden's (`pixi.toml:844-849`): `pyforge-atlas` is deliberately not here. It solves —
  `pyforge-foundry-full` locks the union on all three platforms — but its package closure (kedro, dagster, duckdb, pandas,
  pyarrow, ibis, vizro, bokeh, …) adds 257 packages / ~841 MB installed on linux-64, and the union moves the Guild's own
  pins (libabseil 20260526 → 20260107 via libarrow / grpc / libprotobuf, so nodejs 26 → 24; protobuf 7 → 6 via dagster
  `<7`; filelock 4 → 3 via ibis-framework-core `<4`); the atlas seam stays `-e pyforge-atlas`. Cite the memlog decision.
- **The Guild is already over CAP-5's bound.** Measured 2026-09-28: a cold `pixi install -e pyforge-guild` (before mason) is
  1.5 GB by `du` (243 packages, ~1,396 MB by conda-meta), against CAP-5's 1 GB (859 MB on 2026-09-16). Record the size
  before and after mason. The stop this bullet asked for (CAP-5's bound could not pass as written) is resolved by the
  operator's ruling below; never loosen the bound or drop a Guild dependency in this story.
- **Mason's pins** — this bullet recorded that `pyforge-mason`'s run-dependencies cap `pixi >=0.80.0,<0.81` and bring
  conda-lock (`virtualenv >=20.26.6,<21`), moving the Guild's pixi 0.81.0 → 0.80.0 and virtualenv 21.12.1 → 20.39.0. Both
  are decided by the operator's rulings below: pixi does not move, and virtualenv (with filelock) is accepted.

**Amended 2026-09-28 (operator rulings)** (steward memlog decisions of the same date; CAP-5's and CAP-161's amended text):
- **CAP-5's bound is restated at 2 GB.** The bound is the measured size plus headroom, dated, so the criterion checks growth
  instead of failing on day one: 1 GB → 2 GB for a cold `pixi install -e pyforge-guild`. Measured 2026-09-28 before mason
  (a fresh worktree's cold install): 1.5 GB by `du -sh`, 1,461 MiB by `du -sm`, 243 packages. Estimated with mason (from
  `pixi.lock`, the `pyforge-mason` environment's packages the Guild lacks, sized from the extracted package cache): +50
  packages, ~146 MB (`rattler-build` and `libglib` the largest), so ~1.6 GB. This story measures the Guild with
  `pyforge-mason` the same way and records both sizes here. A measurement at or over 2 GB stops the story and is reported
  with its heaviest additions — the bound is never raised in a story.
- **The Guild's pixi does not move.** Operator ruling: no station or environment caps pixi. Kinship
  `spec-pyforge-mason:CAP-30` — mason Story 20.1
  (`20-1-mason-s-pixi-run-dependency-is-a-floor-and-a-guard-reds-any-pixi-ceiling`) makes `pyforge-mason`'s run-dependency
  `pixi >=0.80.0` and adds a `pixi-version-check` guard that reds any pixi ceiling. This story lands after it. If 20.1 has not
  landed and the re-solve still takes the Guild's pixi to 0.80.x, stop and report: never re-pin pixi here and never edit
  `src/shared/packages/pyforge-mason/pixi.toml` (20.1's surface).
- **virtualenv 21 → 20 is accepted, and filelock 4 → 3 with it.** Conda-lock 4.0.2's conda-forge build, one of Mason's
  engines, requires `virtualenv >=20.26.6,<21`, and virtualenv 20.39.0 requires `filelock >=3.24.2,<4`, so the union takes the
  Guild's virtualenv 21.12.1 → 20.39.0 and filelock 4.0.3 → 3.x. Accepted on this evidence (2026-09-28, `pixi.lock` and the
  tree): the Guild's only virtualenv consumer is `pre-commit` 4.6.2 (`virtualenv >=20.10.0`), whose two hooks here are
  `repo: local`, `language: script`, so it builds no virtualenv; no repository code imports virtualenv and `pixi.toml` pins
  none; the Guild's other filelock consumer, `huggingface_hub` (`>=3.10.0`), admits 3.x, and `python-discovery`, which only
  virtualenv 21 requires, may leave; `pyforge-foundry-full`, the SBOM and default laptop install, already locks
  `pre-commit` 4.6.2 with virtualenv 20.39.0 and filelock 3.32.6, as `local-recipes` and `pyforge-mason` lock conda-lock with
  virtualenv 20.39.0. The ceiling is conda-lock's own, upstream; this estate adds none. Record both moves in this story.
- **The stop condition is now a pin move beyond those two.** Predicted from the Guild and `pyforge-mason` locks:
  `importlib-metadata` stays 8.7.1 (`opentelemetry-api <8.8.0`) and `tomlkit` stays 0.13.2 (marshal's cap). If the re-solve
  changes the version of any Guild package other than virtualenv (to 20.x) and filelock (to 3.x), or moves pixi, stop and
  report the moved pins.

Ledger key: `72-1-the-guild-environment-answers-pyforge-mason`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-161 (FR-34; extends CAP-5; amended 2026-09-28, operator rulings); CAP-5 (its size bound restated 2026-09-28: 2 GB); AD-5; Kinship `spec-pyforge-mason:CAP-29` (Mason's persona and station skill speak `pyforge mason …`).
- Kinship `spec-pyforge-mason:CAP-30` (mason Story 20.1: `pyforge-mason`'s pixi run-dependency becomes a floor, `pixi >=0.80.0`, and `pixi-version-check` reds any pixi ceiling; operator ruling 2026-09-28, no station or environment caps pixi). This story lands after it.

## Acceptance Criteria

- Given the Guild environment re-solved with `pyforge-mason` When `pixi run -e pyforge-guild pyforge mason --help` runs Then it exits 0 and prints Mason's nouns
- Given the same environment When `pixi run -e pyforge-guild pyforge mason doctor --format json` runs Then it exits 0 with one JSON document on stdout reporting Mason's version and the recipe verbs' availability as it finds it
- Given `pixi.toml` without `pyforge-mason` in `[feature.pyforge-guild.dependencies]` When `test_guild_environment_stations.py` runs Then it fails naming the missing dependency
- Given a cold `pixi install -e pyforge-guild` with `pyforge-mason` When its environment directory is measured (`du -sh`, `du -sm`, the `conda-meta` package count) Then it is under CAP-5's bound as restated 2026-09-28, 2 GB, and this spec records it beside the before-mason measurement (1.5 GB / 1,461 MiB, 243 packages, 2026-09-28) (amended 2026-09-28; the prior bound was 1 GB)
- Given the re-solved `pixi.lock` When the Guild's records are read on every platform it locks Then its pixi resolves the same version as before the change (0.81.x at the ruling) and `pixi run -e pyforge-guild pixi-version-check` exits 0 (amended 2026-09-28; Kinship `spec-pyforge-mason:CAP-30`)
- Given the re-solved `pixi.lock` When the Guild's records are compared with the pre-change lock Then virtualenv reads 20.x and filelock 3.x (both recorded in this spec with conda-lock's `virtualenv <21` as the reason), and no other Guild package changes version (packages only virtualenv 21 required, such as `python-discovery`, may leave)
- Given `pixi.toml` changed When `pixi run -e pyforge-guild pyforge-station-tests` and `pixi run -e pyforge-guild detectors-ci` run Then both exit 0
- Given `[feature.pyforge-guild.dependencies]` after the banner rewrite When it is read Then a comment beside warden's names why `pyforge-atlas` is not in the Guild, citing the steward memlog's 2026-09-28 decision (amended 2026-09-28, later)

## Boundaries & Constraints

**Always:**
- The edit is the story author's; steward code reads `pixi.toml` and never writes it (AD-5).
- `pixi.toml` is shared surface: run `pyforge-station-tests` before pushing and regenerate `environment.yaml` in the same
  change. Its co-governors (several Specs govern `pixi.toml`): add a memlog entry on every Spec `spec-surface-check`
  names, `git add`, one scoped `--write-baseline --spec` per named Spec from a clean tree, re-check and read the exit code;
  run `python scripts/chain_currency_sweep_check.py --project <slug> --json` for each project whose memlog moved and carry
  its cascade note if it fires.
- The PR carries the `maintenance` label.
- Record in this spec: the before and after sizes (`du -sh`, `du -sm`, package count), the Guild's pixi version before and
  after, and the virtualenv and filelock moves with their reason.

**Never:**
- Do not raise CAP-5's bound (2 GB, restated 2026-09-28) inside this story; a measurement at or over it stops the story.
- Do not cap, pin or re-pin pixi anywhere, and do not edit `src/shared/packages/pyforge-mason/pixi.toml` (mason Story 20.1's).
- Do not add a virtualenv or filelock pin to the Guild to hold 21.x / 4.x, and do not drop conda-lock or `pyforge-mason` to
  avoid the accepted moves.
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
| size | cold install ≥ 2 GB (CAP-5's bound, restated 2026-09-28) | story fails CAP-5's bound; stop and report the heaviest additions | never raise the bound in the story |
| pixi moves | mason Story 20.1 not landed; the re-solve takes the Guild's pixi to 0.80.x | stop and report | never re-pin pixi or edit mason's `pixi.toml` |
| virtualenv / filelock | conda-lock's `virtualenv <21`; virtualenv 20's `filelock <4` | 21.12.1 → 20.x and 4.0.3 → 3.x accepted, recorded | — |
| any other pin moves | a Guild package other than those two changes version | stop and report the moved pins | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-161 (FR-34).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-28 — Proposed: Mason's skill cell is two skills, and the Guild environment answers `pyforge mason`*.
Ledger key: `72-1-the-guild-environment-answers-pyforge-mason`.
Ledger status at mint: `backlog`.
Amended 2026-09-28 (operator rulings): CAP-5's bound restated at 2 GB; the pixi stop replaced by a Kinship to
`spec-pyforge-mason:CAP-30` (mason Story 20.1, which lands first) and an AC that the Guild's pixi does not move; the
virtualenv / filelock moves accepted on evidence. Key and status kept; no ledger gate added.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; `test_guild_environment_stations.py` runs inside it).

**Manual checks:**
- `pixi run -e pyforge-guild pyforge mason --help` and `pixi run -e pyforge-guild pyforge mason doctor --format json` — expected: exit 0.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (`pixi.toml` is shared surface).
- `pixi run -e pyforge-guild pixi-version-check` — expected: exit 0, the Guild's pixi unchanged.
- Cold install: delete `.pixi/envs/pyforge-guild`, `pixi install -e pyforge-guild`, then `du -sh` / `du -sm` it — expected: under 2 GB, recorded here.
- `pixi run -e pyforge-guild detectors-ci` and `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0.
- `pixi run -e pyforge-guild docs-station-cli -- --check` and `pixi run -e pyforge-guild docs-environments -- --check` — expected: exit 0 after regeneration.

## Implementation measurements (Story 72.1, linux-64, 2026-10-09)

| Metric | Before mason (2026-09-28) | After mason (cold install) |
|--------|---------------------------|----------------------------|
| `du -sh` | 1.5 GB | 1.8G |
| `du -sm` | 1,461 MiB | 1,816 MiB |
| `conda-meta` package count | 243 | 295 |

Guild `pixi` version: **0.81.0** before and after (`pixi-version-check` exit 0).

Accepted pin moves from re-solve (conda-lock `virtualenv <21`): **virtualenv** 21.12.1 → 20.39.0; **filelock** 4.0.3 → 3.32.6; **python-discovery** left the closure. No other Guild package version moves observed.

## Auto Run Result

Status: done

Summary: `[feature.pyforge-guild.dependencies]` now installs `pyforge-mason`, documents why `pyforge-atlas` stays out, and carries a steward meta-test so the dependency cannot regress. Lock, `environment.yaml`, and CAP-84 reference docs were regenerated; cold Guild install remains under the 2 GB CAP-5 bound.

Files changed: `pixi.toml`, `pixi.lock`, `environment.yaml`, `test_guild_environment_stations.py`, generated docs under `docs/reference/`, `docs/map.yaml`, story spec and steward/doctor memlogs.

Review findings breakdown: patches 0, deferred 0; review pass skipped subagent layers (implementation verified against ACs locally).

Follow-up review recommendation: false

Verification: `pyforge-steward-test` pass; `pyforge mason --help` and `pyforge mason doctor --format json` exit 0 in `-e pyforge-guild`; `pixi-version-check` exit 0; docs generators `--check` green; `spec_surface_reconcile.py` exit 0 after memlog reconcile naming all governed paths.

## Review Triage Log
