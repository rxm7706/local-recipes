---
title: "4.5: A repeated --platform keeps every value"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-4-3-mason-environment-lock.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-4-4-mason-environment-check.md
  - src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py
  - src/shared/packages/pyforge-mason/src/pyforge/mason/environment.py
  - .claude/skills/mason-environment/SKILL.md
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-4's success (`SPEC.md`, "platform targeting is repeatable"), FR-27 in the PRD and Story 19.3's AC
all call `--platform` repeatable. `src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py` registers it on
`environment lock` (`:890-896`) and `environment check` (`:935-943`) as a plain store. A second `--platform`
overwrites the first with no warning, and `environment.lock` / `environment.check`
(`src/shared/packages/pyforge-mason/src/pyforge/mason/environment.py:129-130`, `:179-180`) split the one value that
survives. So `--platform linux-64 --platform osx-arm64` locks `osx-arm64` alone. Story 4.3's spec chose a single
comma-separated value on purpose (`spec-4-3-mason-environment-lock.md:39-41`, Design Notes `:241-244`), to match
`ship --to`; the contract text was never brought in line, and nothing refuses the repeated form.

The same file has the twin defect on an outward verb: `package ship --to` (`cli.py:507-513`) is also a plain store, so
a repeated `--to` silently drops every target but the last.

Found by the EGM fleet audit of 2026-11-01 (marshal Story 113.7): **MAS-D-R4** (the contract says repeatable, the CLI
takes one comma-separated value) and **MAS-D-C3** (a repeated flag silently keeps only the last value), cluster
`mason-c07-platform-repeat`. Residue:
`_bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:** honour the contract as written. `--platform` accepts both forms, a repeated flag and comma-split values,
so CAP-4, FR-27 and Story 19.3 hold without a re-derive and the PRD is not edited (the cluster's decision; its memlog
event is the landing PR's, never this story's).

- `environment lock` and `environment check` register `--platform` with `action="append"`. `cli.py` flattens every
  value's comma-split tokens, in the order given, before it calls `environment.lock` / `environment.check`. The
  flattening may live in `environment.py` instead, if the implementer keeps one parser for both verbs.
- `package ship --to`, and the `package --ship` alias that shares `_add_ship_flags` (`cli.py:437`, `:837`, `:848`),
  refuse a second occurrence with a usage error (exit 2, `EXIT_USAGE`). A repeated flag never widens or narrows an
  outward ship.

Ledger key: `4-5-a-repeated-platform-keeps-every-value`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: fix / S / —.
Mode: in the EGM landing PR (marshal Story 113.7).

### Living CAP citations

- `spec-pyforge-mason` CAP-4 (`mason environment`, dependency binding): "platform targeting is repeatable and the
  engine's default is reported when none is given". This story makes the CLI meet it.
- FR-27 (the epic's FR range FR-25 to FR-29). No FR moves.
- No new CAP. `spec-feature-flag-governance` CAP-1, Q1: a `fix` carries no flag.
- AD-6: the solve stays conda-lock's; Mason only passes the platform list through.

## Acceptance Criteria

1. **The repeated form keeps every value.** Given `pyforge mason environment lock <manifest> --output <path>
   --platform linux-64 --platform osx-arm64`, When it runs, Then the engine receives `linux-64` and `osx-arm64`, in that
   order, and the rendered output and JSON envelope name both.
2. **The comma form is unchanged.** Given `--platform linux-64,osx-arm64`, When it runs, Then the engine receives the same
   two platforms as AC 1. A mix (`--platform linux-64,osx-arm64 --platform win-64`) gives all three, in order.
3. **`check` matches `lock`.** ACs 1 and 2 hold for `pyforge mason environment check <manifest> --lockfile <path>`, through
   one flattening rule.
4. **Defaults hold.** Given no `--platform`, When either verb runs, Then Mason passes no platform list and conda-lock's
   own default applies and is reported, as today. Empty tokens (`--platform linux-64,,`) are still dropped.
5. **A repeated `--to` is refused.** Given `pyforge mason package ship --to pypi-test --to pypi` (or a repeated targets
   flag on the `package --ship` alias), When it runs, Then it exits 2 with a usage error naming the flag, and nothing is
   built, checked or shipped. A single `--to pypi-test,pypi` still targets both.
6. **Red first.** The tests for ACs 1, 2, 3 and 5 in
   `src/shared/packages/pyforge-mason/tests/unit/test_cli.py` fail against `main`'s `cli.py` and pass with the fix.
   Existing tests that pinned the single-store shape
   (`test_environment_lock_passes_platform_flag_through_unparsed`,
   `test_environment_check_passes_platform_flag_through_unparsed`) are updated to the flattened contract, never
   skipped.
7. **Docs follow behaviour.** Both `--platform` help strings name the two forms.
   `.claude/skills/mason-environment/SKILL.md` (`:41-52`) changes only if its wording no longer matches; the station
   skill under `.claude/skills/pyforge-mason/` changes only through `skf-update-skill`, never by hand. Story 4.3's
   spec gets one dated Change Log line; its body is not rewritten.
8. **Green.** `pixi run --frozen -e pyforge-mason pyforge-mason-test` passes, and
   `pixi run --frozen -e pyforge-mason pyforge-mason-coverage-gate` holds the touched-module floor.

## Boundaries & Constraints

**Always:**

- Read every verdict from the exit code, never through a pipe.
- Keep the solve in conda-lock (AD-6): Mason adds no platform vocabulary and validates no platform name.
- After `git add`, stamp `spec-pyforge-mason` and `spec-pyforge-core` (co-governor of every station's `src/`), one
  `--spec` each, after a memlog entry on each names the paths.

**Never:**

- Edit the PRD, re-derive CAP-4, or hand-edit any `SPEC.md` or `sprint-status-ledger.yaml`.
- Append a repeated `--to`: an outward ship takes its targets from one flag only.
- Change `--output`'s required shape or any other verb's flags.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| repeated flag | `--platform linux-64 --platform osx-arm64` | both platforms, in order | — |
| comma form | `--platform linux-64,osx-arm64` | both platforms, in order | — |
| mixed | `--platform linux-64,osx-arm64 --platform win-64` | three platforms, in order | — |
| empty tokens | `--platform linux-64,,` | `linux-64` only | dropped, as today |
| no flag | (none) | conda-lock's default, reported | as today |
| repeated `--to` | `--to pypi-test --to pypi` | exit 2, usage error naming `--to` | nothing built or shipped |
| single `--to`, two targets | `--to pypi-test,pypi` | both targets | as today |

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-mason` CAP-4 (`mason environment`: dependency binding), FR-27. A fix, no new CAP.

Parent: CAP-4

- Dream: `docs/dreams/pyforge-mason.md` § Realization log, the 2026-11-01 entry (the EGM fleet audit).
- Audit findings carried: MAS-D-R4, MAS-D-C3 (cluster `mason-c07-platform-repeat`); residue
  `_bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 4 (Bind environments into lockfiles), done; a new not-done story reopens it (doctor Story 41.5).
- Ledger key: `4-5-a-repeated-platform-keeps-every-value`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py`,
  `src/shared/packages/pyforge-mason/src/pyforge/mason/environment.py` (only if the flattening lives there),
  `src/shared/packages/pyforge-mason/tests/unit/test_cli.py`,
  `src/shared/packages/pyforge-mason/tests/unit/test_environment.py` (only with `environment.py`),
  `.claude/skills/mason-environment/SKILL.md` (only if its wording changes), `.claude/skills/pyforge-mason/**` (only
  through `skf-update-skill`), `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-4-3-mason-environment-lock.md`
  (one Change Log line).
- Flag: none (a fix; `spec-feature-flag-governance` CAP-1, Q1).
- Minted 2026-11-01 by marshal Story 113.7's landing PR, on the operator's acceptance of the audit's recommendations.

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_cli.py -q` — expected:
  pass, with the new repeated-`--platform` and repeated-`--to` tests among them.
- `pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_environment.py -q` —
  expected: pass.
- `pixi run --frozen -e pyforge-mason pyforge-mason-coverage-gate` — expected: exit 0.

**Manual checks:**

- The red-first run (AC 6): the new tests against `git show origin/main:src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py`
  fail, and pass on the branch.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Auto Run Result

Status: backlog

Summary: not yet dispatched.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (marshal Story 113.7), findings MAS-D-R4 and MAS-D-C3, cluster
  `mason-c07-platform-repeat`; fix under `spec-pyforge-mason` CAP-4, no new CAP, no flag.

## Review Triage Log

- (none yet)
