---
title: "41.4: The check CLI, the env and engines checks, the score and the bmad-method source report every degradation they meet"
type: 'fix'
created: '2026-10-03'
status: 'in-progress'
baseline_revision: 30a18afa3a
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Doctor's check CLI, its env and engines checks, the score and the bmad-method source carry 28 open deferrals (6 medium, 22 low): a first-match filter and a discarded degradation message, false-green exits on a typo'd path or an impossible `--source`, guard and header shapes the env scanner cannot see, a load-flaky budget test, constraint shapes the floor reader cannot parse, suite checks gated on local installs, a score that grades an unevaluable axis as a letter, and packaging and meta-test gaps.

**Approach:** Fix each row where its behaviour lives (one line each below): `gather_one` returns all matches and keeps the sentinel, the CLI refuses impossible filters and names bad paths, the env scanner gains the guard and header shapes, the floor reader parses specifier sets from every table shape, one cannot-evaluate evidence marker feeds the score.

Ledger key: `41-4-the-check-cli-the-score-and-the-bmad-method-source-report-every-degradation`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- spec-pyforge-doctor CAP-1, CAP-2, CAP-5, CAP-13-CAP-16, CAP-86 (the capabilities that shipped each behaviour); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given two files matching one env check, a degraded engines category, an `--env`-only run on `/no/such/dir`, or `doctor monitor --source <a source the axis cannot emit>` When `doctor check` or `monitor` runs Then both Findings, the specific degradation message, a not-a-directory WARN and a usage error (exit 2) are reported, respectively
- Given the early-return guard, a ternary or `match` host guard, `not f(h)` negation and a bare `return {...}` credential header When `env_hygiene` scans them Then each is classified as the row says
- Given inline-table, compound-range, whitespace and multi-table `bmad-method` constraints and a diverging manifest When the bmad-method source runs Then each floor is extracted with its table named, an unparseable one is its own WARN, and the divergence WARNs
- Given the unresolvable-head ledger WARN, `chain-layers-audit-unevaluable` and `bmad-drift-unevaluable` When `score.grade` runs Then each axis grades `incomplete`
- Given a loaded host When `test_check_speed_budget.py` runs several times in a row Then it passes every time
- Given any code row above When its fix is reverted Then at least one test in the station suite fails
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-1-5`, `DW-FU-1-5-3`, `DW-FU-6-4-13`, `DW-FU-6-6-8`, `DW-FU-15-2`, `DW-doctor-40-1`, `DW-1-1-3`, `DW-1-1-4`, `DW-FU-10-1-2`, `DW-FU-10-1-3`, `DW-FU-10-1-4`, `DW-FU-10-1-6`, `DW-FU-10-1-7`, `DW-FU-10-2`, `DW-FU-10-3`, `DW-FU-10-3-2`, `DW-FU-10-3-3`, `DW-FU-1-2`, `DW-FU-1-2-2`, `DW-FU-1-4`, `DW-FU-1-4-2`, `DW-FU-14-1-2`, `DW-FU-15-1`, `DW-FU-15-1-2`, `DW-FU-15-2-2`, `DW-FU-1-5-4`, `DW-FU-18-2`, `DW-FU-20-4` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Keep `bmad_method.gather`'s "ok or warn, never fail" contract and its fail-open network budget. A `pixi.toml` change regenerates `environment.yaml` in the same change. A change under `.claude/skills/conda-forge-expert/` invokes the conda-forge-expert skill first and lands as one `retro(cfe):` commit with a CHANGELOG entry and semver bump. Re-verify each row at HEAD before fixing it: a row whose defect a later landing already removed closes citing the `path:line` of that fix and the test that pins it (adding the test when none exists), never on prose alone. Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix. A governed file moves only with its owning Spec's memlog naming it, then a scoped stamp for exactly that Spec (AGENTS.md pre-PR item 5); `spec-pyforge-core` co-governs every station's `src/`.

**Never:** Never raise the speed budget without a recorded measurement, and never let a repo-scope run reach the network. Never close a row without a landed fix, a `resolution:` naming this story and a `verified:` line citing what was read. Never edit `SPEC.md` by hand or stamp a bare `--write-baseline`. Never weaken or delete a test to make a row pass. Never turn a warn-only finding into a gate.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phases 4 and 5)

28 rows: 6 medium, 22 low.

- `DW-FU-1-5` (medium) — `checks.registry.gather_one` returns every Finding for the named check (each matching file under `env`), and a named `--env` run on an incomplete scan also returns the incomplete-scan sentinel, so it can never read as clean.
- `DW-FU-1-5-3` (medium) — An `--env`-only run on a target that is not a directory emits a not-a-directory WARN, never `0 finding(s)` with exit 0.
- `DW-FU-6-4-13` (medium) — `doctor monitor --source` accepts only a value some gather on the selected axis can emit, so `--source ledger-regression` on a watch axis is a usage error (exit 2), not a silent zero.
- `DW-FU-6-6-8` (medium) — `test_check_speed_budget.py` measures `doctor check`'s own work on a warm run against a budget re-baselined from a recorded measurement (or the median of several runs), so host load no longer flips it; consecutive green runs on the loaded host are the evidence.
- `DW-FU-15-2` (medium) — `_gather_suite_findings`'s channel-drift and recipe-upstream-drift checks key off the tracked pins and recipes, not `.pixi/envs` install state, so they fire on a fresh clone and in CI.
- `DW-doctor-40-1` (medium) — One evidence marker for "this axis could not be evaluated" is carried by every cannot-evaluate WARN (the unresolvable-head ledger WARN, `chain-layers-audit-unevaluable`, `bmad-drift-unevaluable`), and `score._is_gather_failure` reads it, so those axes grade `incomplete`.
- `DW-1-1-3` (low) — Doctor's three hatchling constraints agree at one floor (`pyproject.toml [build-system] requires`, the package `pixi.toml` host dependency, the root `pixi.toml` feature); `environment.yaml` regenerated in the same change.
- `DW-1-1-4` (low) — `tests/meta/test_verdict_sole_ownership.py`'s AST detector also catches a bare `raise SystemExit` (an `ast.Raise` of a `Name`).
- `DW-FU-10-1-2` (low) — `bmad_method._declared_floors` reads the inline-table (`{ version = ">=…" }`) and `pypi-dependencies` constraint shapes.
- `DW-FU-10-1-3` (low) — The declared-floor Finding's evidence names the `pixi.toml` table that produced the winning floor.
- `DW-FU-10-1-4` (low) — `_declared_floors` keeps every valid floor and reports an unparseable constraint as its own WARN instead of discarding the floors already found.
- `DW-FU-10-1-6` (low) — The floor is extracted from a compound range (`>=6.11.0,<7`) and tolerates whitespace after the operator (parsed as a specifier set, not `_FLOOR_RE`'s exact shape).
- `DW-FU-10-1-7` (low) — `bmad_method.gather` compares `_bmad/_config/manifest.yaml`'s `installation.version` with each module's `version` and WARNs when they diverge.
- `DW-FU-10-2` (low) — The declared-floor (CAP-1) and upstream (CAP-2) Findings grade independently, so a CAP-2 WARN fed to `score.grade` is never diluted to B by CAP-1's OK.
- `DW-FU-10-3` (low) — A test pins `bmad_method.gather`'s "ok or warn, never fail" contract, and `scripts/fleet_scan.py`'s `bmad_core_drift_findings()` degrades a non-zero exit to one watch line without relying on `check=True` (the file is governed by `spec-pyforge-marshal`: reconcile its memlog).
- `DW-FU-10-3-2` (low) — `REGISTRY`'s `BMAD_METHOD_VERSION_DRIFT` entry declares its network read, and `--scope repo` honours it, so a repo-scope run stays offline.
- `DW-FU-10-3-3` (low) — A test drives `scripts/fleet_scan.py`'s `main()` with stubbed probes and asserts each ATTENTION probe's result reaches the printed `watch`/`needs` lists.
- `DW-FU-1-2` (low) — `sources/warden.py`'s `_INSTALL_HINT` names the pixi environment that carries warden, not `pip install`.
- `DW-FU-1-2-2` (low) — `test_no_warden_import.py` and `test_sources_warden_no_subprocess.py` resolve `import pyforge.warden` followed by an attribute chain to the submodule it reaches.
- `DW-FU-1-4` (low) — `checks.env_hygiene` detects a credential header in a bare `return {...}` dict literal and recognises a ternary (`IfExp`) host guard and `match`/`case`.
- `DW-FU-1-4-2` (low) — `checks.env_hygiene` recognises the early-return guard idiom (a preceding sibling `if` whose body always returns or raises) and resolves `not f(h)` and `BoolOp` negation polarity.
- `DW-FU-14-1-2` (low) — `bmad_method` reports an installed suite package behind its own `pixi.toml` floor, offline, as the suite analog of CAP-1.
- `DW-FU-15-1` (low) — `_fetch_latest_github_release`'s `/tags` fallback follows pagination (the `Link` header) inside the existing fail-open budget.
- `DW-FU-15-1-2` (low) — A test reads the live `recipes/<name>/recipe.yaml` of each npm-invisible package and proves the GitHub fallback resolves it (the fetch seam stubbed, the mapping read live).
- `DW-FU-15-2-2` (low) — A fleet-picture meta-test names `bmad-channel-drift` and `bmad-recipe-upstream-drift` (`.claude/skills/conda-forge-expert/tests/meta/`: invoke the conda-forge-expert skill first and land it as one `retro(cfe):` commit with a CHANGELOG entry and semver bump).
- `DW-FU-1-5-4` (low) — A named `--engines NAME` run on a degraded category keeps warden's specific degradation message, and the CLI's synthetic FAIL quotes it.
- `DW-FU-18-2` (low) — The DW-FU-6-6-8 budget fix covers the cold worktree start too (the measured run is warm), so the first run in a fresh worktree no longer flakes.
- `DW-FU-20-4` (low) — `.claude/skills/bmad-agent-doctor/SKILL.md`'s `## Allowed actions (CAP-16)` names how a doctor task consults `bmad-os-root-cause-analysis`, matching the routing note at :14.

## Binding

Parent: spec-pyforge-doctor CAP-1, CAP-2, CAP-5, CAP-13-CAP-16, CAP-86 (the capabilities that shipped each behaviour); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `41-4-the-check-cli-the-score-and-the-bmad-method-source-report-every-degradation`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 4+5 rulings (fix every open medium deferral and the lows in the modules it touches, no blanket closure; sizing override the same day: fewer, larger stories split by package area, at most about 30 rows each).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Spec Change Log

- 2026-10-03: Operator ruling (2026-10-03): a row that only an independent follow-up review of an already-landed story can close (a DW-FRR "follow-up review still recommended" row) is not in the Phase 4+5 fix stories, because an implementation session can never close it; those reviews run later as separate per-station review batches. Removed from this story's scope: `DW-FRR-14-1`, `DW-FRR-15-1`, `DW-FRR-15-2`, `DW-FRR-38-4` (4 low); the follow-up-review acceptance criterion, the review step in the Approach and the review boundary went with them. The rows stay open in the deferred-work ledger. 32 rows (6 medium, 26 low) became 28 (6 medium, 22 low).

## Review Triage Log

- No review has run yet.
