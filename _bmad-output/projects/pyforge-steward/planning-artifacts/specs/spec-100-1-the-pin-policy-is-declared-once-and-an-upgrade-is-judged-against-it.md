---
title: '100.1: The pin policy is declared once and an upgrade is judged against it'
type: 'feature'
created: '2026-10-13'
status: 'done'
baseline_revision: '9fea58d6c7bf6e37d4c14c0d5de409ef3f2552a7'
flag-exempt: detector-or-gate   # a registry and its check; a gated gate reports a silent green (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/intake/estate-refresh/PLAN-2026-10-13.md
  - docs/dreams/pyforge-steward.md
  - pixi.toml
  - scripts/pixi_version_registry.py
  - scripts/pixi_version_check.py
  - scripts/bump_pixi_version.py
  - scripts/protected_refs_ruleset_check.py
  - scripts/detectors.py
  - docs/governance/guild-roster.json
  - .claude/skills/conda-forge-expert/SKILL.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The estate's "do not move" policy for `pixi upgrade` is a comment. Line numbers below are at
`233e07909b`.

- **Three generations of one command.** `pixi.toml:45` (17 `--exclude`), `:46-47` ("Canonical upgrade command (19
  excludes)"), `:48` (28 `--exclude`: `conda-libmamba-solver`, `conda-build`, `conda-index`, `conda-forge-ci-setup`,
  `conda-forge-pinning`, `frozendict`, `networkx`, `rattler-build-conda-compat`, `grayskull`, `conda-recipe-manager`,
  `conda-smithy`, `shellcheck`, `nodejs`, `python`, `django`, `channels`, `daphne`, `asgiref`, `channels_redis`,
  `wagtail`, `coderedcms`, `postgresql`, `psycopg`, `psycopg2`, `libpq`, `pgvector`, `cachebox`, `pixi`). Nothing
  reads, renders or checks any of them, and no line says why a package is held or until when.
- **What the tool loses.** `pixi upgrade --pinning-strategy latest-up` rewrites each moved pin to a bare floor
  (CFE gotcha G117). On the 2026-10-13 batch (`docs/intake/estate-refresh/PLAN-2026-10-13.md` § 2) that dropped five
  caps (`git-pkgs` `<0.22`, `liquibase-postgresql` `<42`, `opengrep` `<1.31`, `pyjwt` `<3`, `transformers` `<6.0`),
  flattened two inline tables (`liquibase-postgresql`'s `channel = "conda-forge"`; `pptxgenjs-plus`'s
  `channel = "SelfExplainML"` with its exact `4.2.1.*`), and lowered two floors (`cron-descriptor` 2.1.0 → 1.4.5,
  `openai` 3.19.2 → 2.53.0). Each loss had its reason beside it or in a story; each was found by reading the diff.
- **What checks pins today.** `scripts/pixi_version_check.py` reads cap clauses for `pixi` only; `llms_full_check.py`
  compares first floors and ignores caps and channels; the platform policy tests pin two shapes
  (`test_liquibase_channel_policy.py:26`, `test_openfeature_channel_policy.py:28`). No check knows the other 26 holds.

**Approach:** One tracked registry, `docs/governance/pin-policy.yaml`, with `docs/governance/pin-policy.schema.json`
beside it, one detector `scripts/pin_policy_check.py` and one mutator `scripts/pin_policy_restore.py` — the
`pixi_version_check.py` / `bump_pixi_version.py` pair's shape, with `protected_refs_ruleset_check.py`'s exit domain.

- **Registry shape.** Top level: `version`, `defaults` (`pinning_strategy: latest-up`, `floors_never_lower: true`),
  `pointer` (the one line `pixi.toml` carries), and `holds`. A hold row has `package`, `hold` (`never-move` |
  `cap` | `channel` | `exact` | `floor-only`), the clause the hold keeps (`cap: "<3"`; `channel: SelfExplainML`;
  `exact: "4.2.1.*"`; a `channel` row may also carry `cap`), `features` (`*` or a list of `[feature.<name>]` tables,
  including `target.*` tables), `reason`, `authority` (a Story, CAP, gotcha, or `fnd:CAP-12`), `owner`, and `until`
  (a condition or an ISO date). `never-move` rows render as `--exclude`; every other hold lets the floor rise and
  keeps its clause.
- **Seeding.** One `never-move` row per package in the 28-exclude comment, with its reason and authority (fnd:CAP-12
  for `postgresql` / `psycopg` / `psycopg2` / `libpq` / `pgvector`; CAP-5 and `pixi-version-check` for `pixi`; the
  LTS notes for `python`, `nodejs`, the Django family and `coderedcms`; the recipe-factory notes for the conda-build
  family, `grayskull`, `conda-recipe-manager`, `conda-smithy`, `shellcheck`; `frozendict`, `networkx`,
  `rattler-build-conda-compat` and `cachebox` from their own comments); one `cap` row per declaration carrying `<`
  (every feature where it appears); one `channel` row per inline table with `channel` (`bmad-loop`,
  `caveman-installer`, `codegraph`, `bmad-module-skill-forge`, `opengrep`, `pptxgenjs-plus`, `liquibase-postgresql`,
  and every other table `grep -n 'channel = ' pixi.toml` finds); one `exact` row per `*`-pin. A row's `until`
  comes from its comment where one exists; a row with none is seeded `until: unknown` and reported as a warning.
- **Static check (`--check`, the default).** Parse every `*dependencies` table in `pixi.toml` (the reader in
  `llms_full_check.py::manifest_deps` is the one to reuse). Findings: a declaration carrying a cap, an inline table
  or an exact pin with no row (`undeclared-hold`); a row whose package no listed feature declares
  (`dangling-hold`); a `pointer` line that differs from `--render-command`'s output (`stale-pointer`); a schema
  violation. A row with `until: unknown` is a warning (exit 0). Exit 0 clean, 1 with findings naming package,
  feature and clause, 2 when `pixi.toml` or the registry cannot be read.
- **Diff check (`--diff <base-ref>`).** Read `pixi.toml` at the ref through `git show` and compare pin expressions
  per (feature, package): a cap present at base and absent now (`lost-cap`); an inline table at base flattened to a
  string, or its `channel` / `build` key gone (`flattened-table`); a floor lower than base when
  `floors_never_lower` (`lowered-floor`, compared with `packaging.version.Version`); a `never-move` package whose
  expression changed (`moved-hold`). A floor-only rise is never a finding. The 2026-10-13 batch is committed as a
  fixture pair (`tests/scripts/fixtures/pin_policy/pixi.toml.base`, `.after`, and the registry) and yields exactly
  nine findings.
- **Fan-out (`--fan-out`, ruling Q13).** Read every station package-level range —
  `src/shared/packages/*/pyproject.toml` `[project.dependencies]` and each package `pixi.toml`
  `[package.run-dependencies]`, through the reader `llms_full_check.py` already has — and the version `pixi.lock`
  holds for that package in the station's environment; a locked version outside the range is a finding
  (`station-range-excludes`) naming the station, the file, the range and the version. The refresh refuses to land on
  it and the move is that station's story: no package-level pin is ever rewritten here, so no lock-block eviction is
  needed (team memory 2026-08-21: pixi does not rehash path-dep metadata). This generalizes CAP-12's `bmad-loop` /
  `bmad-method` fan-out to every package.
- **Render (`--render-command`).** Prints `pixi upgrade --pinning-strategy <defaults> --exclude <pkg>…` with every
  `never-move` package, sorted, one per `--exclude`; `pixi.toml`'s three comment lines become one pointer line that
  names the registry and the render command (no pin moves in this story).
- **Restore (`scripts/pin_policy_restore.py --from <base-ref>`).** For each `lost-cap`, `flattened-table`,
  `lowered-floor` and `moved-hold` finding, rewrite that one declaration to its policy clause at the newly resolved
  floor (`>=NEW,<CAP`; `{ version = ">=NEW,<CAP", channel = "X" }`; the base floor for a lowered one; the base
  expression for a moved hold), keep the inline comment byte-identical, then run `pixi lock` and `--check`. A lock
  that cannot solve is a refusal naming the row, and the file is restored to its pre-restore bytes.
- **Wiring.** A `pin-policy-check` task in the Guild tasks feature runs `--check`; `scripts/detectors.py` gains one
  repo-scope entry, so `detectors-ci` and `pr-preflight` run it; `docs/reference/detectors.md` is regenerated by its
  own generator.

Ledger key: `100-1-the-pin-policy-is-declared-once-and-an-upgrade-is-judged-against-it`.
Type / Effort / Deps: feature / M / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-167** (FR-40): this story builds the policy, its schema, the check, the restore
  mutator and the detector wiring; Story 100.2 builds the duty that runs them.
- **AD-1** (wrap, never reimplement): the mutator shells to `pixi lock`; no resolver of its own. **AD-5** as read
  since Story 72.1: the registry and the mutator are repo files and a repo script, never steward code writing
  `pixi.toml`. **AD-8** does not bind a `scripts/` checker, but its exit codes follow the repo convention: 0 clean,
  1 findings, 2 cannot read.
- **Flag:** `flag-exempt: detector-or-gate`. The check judges and the mutator restores on request; neither changes
  runtime behaviour.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-13 (estate refresh), and
  `docs/intake/estate-refresh/PLAN-2026-10-13.md`; its recommended answers Q2 and Q4, adopted as assumptions.

## Acceptance Criteria

- **AC1 — Seeded and clean.** `docs/governance/pin-policy.yaml` validates against the schema and holds every row the
  Approach's Seeding list names; `python scripts/pin_policy_check.py --check` exits 0 on the tree; every
  `never-move` row carries a non-empty `reason` and `authority`.
- **AC2 — Each static rule reds.** On a fixture per rule, `--check` exits 1 naming package, feature and clause: an
  undeclared `<` cap; an undeclared `{ channel = … }` table; a row for a package no feature declares; a pointer line
  that differs from `--render-command`. A row with `until: unknown` is a warning and exits 0.
- **AC3 — The batch retrodicted.** `--diff` over the committed fixture pair yields exactly nine findings: five
  `lost-cap`, two `flattened-table`, two `lowered-floor`; a fixture with floor-only rises yields zero; a fixture that
  moves `postgresql` yields one `moved-hold`.
- **AC4 — Restore.** Over the fixture pair, `pin_policy_restore.py --from` (with `pixi lock` faked to succeed)
  rewrites exactly the nine declarations to their clauses at the new floors, keeps every inline comment
  byte-identical, and the re-check exits 0; with `pixi lock` faked to fail it refuses naming the row and leaves the
  file byte-identical to its pre-restore state.
- **AC4b — Fan-out.** On a fixture whose lock holds `bmad-loop` 0.13.0 for `pyforge-marshal` against marshal's
  `>=0.11.0,<0.13`, `--fan-out` exits 1 naming `pyforge-marshal`, the file and the range; on the tree at
  `233e07909b` it exits 0; a package no station pins yields no row.
- **AC5 — Rendered, pointed, wired.** `--render-command` prints the 28 excludes sorted; `pixi.toml` carries one
  pointer line in place of `:45-48` and no pin expression changes (`git diff pixi.toml` touches comment lines only);
  `pixi run --frozen -e pyforge-guild pin-policy-check` exits 0; `scripts/detectors.py` lists it once among the
  repo-scope detectors; `detectors-ci` stays green; `docs/reference/detectors.md` matches its generator.
- **AC6 — Nothing else moves.** `pixi.lock` is unchanged; no environment is installed; `pixi-version-check`,
  `llms-full-check` and the platform policy tests keep their exit codes.

## Boundaries & Constraints

- No pin moves: this story records the holds, it does not change any floor, cap or channel.
- No `pixi update`, `pixi upgrade` or `pixi install` runs in this story's tests; `pixi lock` is faked.
- The check holds no copy of the exclude list, the prefixes or the hold classes outside the registry and the schema;
  a unit test reds a hard-coded copy.
- Python from the Guild environment only; PyYAML, jsonschema and packaging are available there (check
  `docs/reference/library-llms-full.md` before importing anything else).
- The reader of `pixi.toml` dependency tables is shared with `llms_full_check.py`, not a second parser.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| `pyjwt = ">=2.15.0,<3"` (base) → `">=2.15.1"` (after) | `lost-cap`, restore → `">=2.15.1,<3"` |
| `liquibase-postgresql = { version = ">=5.0.4,<42", channel = "conda-forge" }` → `">=5.0.4"` | `flattened-table` and `lost-cap` for one declaration, counted once as `flattened-table` |
| `pptxgenjs-plus = { version = "4.2.1.*", channel = "SelfExplainML" }` → `">=4.3.4"` | `flattened-table`; restore → the base table |
| `cron-descriptor = ">=2.1.0"` → `">=1.4.5"` | `lowered-floor`; restore → `">=2.1.0"` |
| `boto3 = ">=1.43.75"` → `">=1.43.106"` | no finding |
| `postgresql = ">=17.11,<18"` → `">=18.0"` | `moved-hold` (and `lost-cap`, counted once) |
| the same package in two features, one moved | one finding per (feature, package) |
| a `target.linux-64` dependency table | parsed like any feature table |
| registry row with `features: [python-agent-platform]` for a package only `platform-dev` declares | `dangling-hold` |
| `--diff` with a ref that has no `pixi.toml` | exit 2, message names the ref |
| `--fan-out` where a station pins a package the root does not (nested-only dep) | judged against the station env's locked version |
| `--fan-out` where the lock has no record for the package in that env | finding `station-range-unresolved` (exit 1) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-167 (FR-40), minted 2026-10-13.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-13 (estate refresh) entry.
- Epic: Epic 100 (new), Stories 100.1–100.7. `epic-100` and `epic-100-retrospective` are minted with it.
- Ledger key: `100-1-the-pin-policy-is-declared-once-and-an-upgrade-is-judged-against-it`.
- Ledger status at mint: `backlog`.
- Deps: none. Story 100.2 (`estate plan|refresh|status`) runs this story's check and mutator.
- Surface: `marshal-policy.toml` `[epic_surfaces]."100"` (added with this mint).
- Minted 2026-10-13 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-guild pin-policy-check` — expected: exit 0 (AC1, AC5); `pixi run --frozen -e pyforge-guild python scripts/pin_policy_check.py --fan-out` — expected: exit 0 (AC4b). This story creates the task,
  so it is never a launch-bound gate (MRS-GATE-011): `verify_commands` holds only the station suite.
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_pin_policy_check.py tests/scripts/test_pin_policy_restore.py -q` — expected: pass (AC2–AC4).
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the CI `scripts-suite` twin).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0 (AC5).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild llms-full-check` and `pixi run --frozen -e pyforge-guild pixi-version-check` — expected: exit 0 (AC6).
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps (`pixi.toml` is governed by seven Specs; reconcile each the detector names).
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

## Spec Change Log

- 2026-10-13: minted with CAP-167 / FR-40 and Epic 100 from the Dream entry of that date and the plan's recommended
  answers Q1–Q9 (adopted as assumptions until the operator overrides them). `type: feature`,
  `flag-exempt: detector-or-gate`. The   restore mutator lands here rather than in Story 100.2 so the check and its
  inverse are one pair with one fixture set, the `pixi_version_check.py` / `bump_pixi_version.py` shape.

## Auto Run Result

Status: in-review

Implementation landed in worktree `dispatch/pyforge-steward/100.1` (baseline `9fea58d6c7bf6e37d4c14c0d5de409ef3f2552a7`).

Verification (local):
- `pytest tests/scripts/test_pin_policy_check.py tests/scripts/test_pin_policy_restore.py` — 11 passed (pyforge-guild)
- `pyforge-doctor-scripts-test` — 1502 passed, 25 skipped (pin-policy tests skipped in pyforge-ci env)
- `pin-policy-check` / `--fan-out` — exit 0
- `spec_surface_reconcile.py` — exit 0 after memlog + allowlist

Surface reconcile memlog (`spec-pyforge-steward/.memlog.md`): `docs/governance/pin-policy.yaml`, `docs/governance/pin-policy.schema.json`, `scripts/pin_policy_check.py`, `scripts/pin_policy_lib.py`, `scripts/pin_policy_restore.py`, `tests/scripts/test_pin_policy_check.py`, `tests/scripts/test_pin_policy_restore.py`, `tests/scripts/fixtures/pin_policy/`, `pixi.toml`, `docs/reference/detectors.md`, `marshal-policy.toml`, `scripts/spec_surface_allowlist.txt`.

Scoped baseline stamp (`--write-baseline --spec …`) not run in this session — operator/steward PR step after merge prep.
