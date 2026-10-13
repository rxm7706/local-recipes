---
title: '100.2: One command moves the library pins on the policy and restores what the upgrade loses'
type: 'feature'
created: '2026-10-13'
status: 'ready-for-dev'
baseline_revision: '233e07909b5f7e89e49744cdeb642cdc0985b177'
flag:
  key: pyforge.steward.estate_refresh          # new; minted by this story (one flag per CAP: 100.3, 100.4, 100.5 reuse it)
  provider: openfeature-file                   # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through Epic 76's overlay (Story 76.1 done)
  scope: global                                # v1 is global only
  fallback: every `estate` verb refuses naming the flag (documented exit code); nothing else reads it, so pixi, the pin policy and the hand sequence are unchanged
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-100-1-the-pin-policy-is-declared-once-and-an-upgrade-is-judged-against-it.md
  - docs/intake/estate-refresh/PLAN-2026-10-13.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py
  - docs/governance/guild-roster.json
  - .claude/hooks/pre-shell.py
  - src/platform/config/flags.json
  - docs/governance/spec-feature-flag-governance/SPEC.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A refresh is six commands run from memory (`docs/intake/estate-refresh/PLAN-2026-10-13.md` § 1), the
upgrade command is copied from a comment, the result is judged by reading a diff, and nothing records what a run
moved. Story 100.1 gives the policy, the check and the restore; nothing yet runs them as one path.

**Approach:** An `estate` duty in the steward package with three verbs in this story — `plan`, `refresh`, `status`
— each a subprocess conductor over `pixi`, Story 100.1's scripts and `bump-pixi-version` (AD-1), behind one flag.

- **`estate plan`.** Renders the upgrade command from the policy (`pin_policy_check.py --render-command`), runs it
  with `--dry-run --json`, and prints one row per move: package, feature, from, to, and `held-by` (the policy row,
  if any, that will keep a clause). Below it, the BMAD table — `bmad-method` and every `bmad-*` pin: pinned floor,
  installed version from `_bmad/_config/manifest.yaml`, upstream latest through doctor's `bmad_method` gather
  (fail-open offline, says `unknown`) — and `days since last journal` from `.steward/estate-refresh/`. `--due` exits
  non-zero when the last journal is older than 30 days or absent. `--json` emits the same. The plan writes nothing,
  so an agent may run it.
- **`estate refresh`.** Refuses before any call when the tree is dirty, when the branch is `main`, or when the flag
  is off. Then: render the command; run `pixi upgrade --pinning-strategy latest-up --json --exclude …`; run
  `pin_policy_check.py --diff <base-sha>` and, on findings, `pin_policy_restore.py --from <base-sha>`; run
  `pixi lock`; run `pin_policy_check.py --fan-out` (a red verdict is journaled and reds the refresh — ruling Q13);
  when the `pixi` floor moved, run `bump-pixi-version`; write the journal and end by listing the `realize_due` rows.
  `--transitive` adds `pixi update` after the upgrade; it is operator-only (below). `estate realize` is Story
  100.5's. Every child's argv and exit code is journaled.
- **The journal.** `.steward/estate-refresh/<YYYY-MM-DD>.json` (a second run the same day appends `-2`), tracked,
  validating against a shipped frozen schema `src/pyforge/steward/data/estate-journal-schema.json`
  (`$id: urn:local-recipes:pyforge-steward:estate-journal-schema`, additive changes only): `base_sha`,
  `result_sha` (filled by `reconcile`), `platform` (the pixi platform the run used), `command`, `moves[]` (package,
  feature, from, to), `losses_restored[]` (the check's finding shape), `fan_out` (the `--fan-out` verdict and its
  findings; a red one reds the refresh), `realize_due[]` (register rows whose package moved — empty until Story
  100.5's register exists), `transitive: bool`, `bmad: {pinned, installed, latest, applied: false}`, `steps[]`
  (argv, exit, seconds), and empty `realize`, `reconcile` and `verify` blocks Stories 100.5, 100.3 and 100.4 fill.
- **`estate status`.** Prints the last journal (or `--all`), one line per block, and the `--due` verdict.
- **The `--transitive` gate (ruling Q3).** `pixi update` re-solves every transitive pin and is the one step the
  session hook already denies to agents (`pixi-add-or-update`). The duty keeps that line: a new `session_denials`
  row `steward-estate-transitive` in `docs/governance/guild-roster.json` denies `steward estate refresh --transitive`
  (and `pyforge steward …`) with a reason naming the operator form, and `.claude/hooks/pre-shell.py` gains the
  matcher (the hook asserts its matchers equal the roster list, so both move together; `.cursor/hooks.json` reuses
  the script). Agents run `plan`, and `refresh` without `--transitive`, inside a worktree that lands through a PR.
- **Flag.** `pyforge.steward.estate_refresh` in `src/platform/config/flags.json` and `flag-overlays.json` (dev on,
  staging and production off), read through `pyforge.core.flags.read_boolean` as Story 75.1 does; with it off every
  verb refuses naming the flag with a documented exit code (AD-8); the flag inventory row lands with the story.

Ledger key: `100-2-one-command-moves-the-library-pins-on-the-policy-and-restores-what-the-upgrade-loses`.
Type / Effort / Deps: feature / M / S-100.1.

### Living CAP citations

- **`spec-pyforge-steward` CAP-167** (FR-40): the duty and its first three verbs; Stories 100.3–100.5 add
  `reconcile`, `verify` and the BMAD hand-off on the same duty.
- **AD-1**: every step is a subprocess (`pixi`, the Story 100.1 scripts, `bump-pixi-version`). **AD-5** as read
  since Story 72.1: steward code never writes `pixi.toml`; `pixi upgrade` and the mutator do. **AD-7**: one duty
  module, `DUTIES` grows by one and the count assertions move (`tests/unit/test_cli.py`,
  `tests/unit/test_restore_duty.py`). **AD-8**: `main()` alone projects the exit code; the duty returns
  `DutyResult`.
- **Flag:** `pyforge.steward.estate_refresh` (new), spec-feature-flag-governance Q1.
- **Origin.** The 2026-10-13 Dream entry; plan Q3 (operator-only `--transitive`) and Q8 (monthly, `--due`).

## Acceptance Criteria

- **AC1 — Plan.** With a fake `pixi` whose `--dry-run --json` returns a recorded document, `estate plan` prints one
  row per move with `held-by` filled from the policy, the BMAD table with `installed` read from a fixture manifest
  (6.12.0) and `pinned` from the fixture `pixi.toml` (6.12.2), and `days since last journal`; `--due` exits non-zero
  with no journal and with one dated 31 days ago, 0 with one dated yesterday; `--json` validates against the
  journal schema's `plan` shape; no file is written.
- **AC2 — Refresh refusals.** On a dirty tree, on `main`, and with the flag off, `estate refresh` exits with the
  documented refusal code before any subprocess call (the fake records none).
- **AC3 — Refresh path.** On a clean branch with the fake `pixi`, `estate refresh` runs, in order, the rendered
  `pixi upgrade … --json`, `pin_policy_check.py --diff <base>`, `pin_policy_restore.py --from <base>` (only when
  the check found something), `pixi lock`, `pin_policy_check.py --fan-out` (a faked red verdict reds the refresh
  with the documented code and the journal records it), and `bump-pixi-version` only when the fake reports a `pixi`
  move; the
  journal exists, validates against the schema, and records every step's argv and exit; `pixi update` is absent
  from the recorded argv.
- **AC4 — Transitive.** With `--transitive` the recorded argv contains `pixi update` once, after the upgrade and
  before the check; the roster carries the `steward-estate-transitive` row; `python3 .claude/hooks/pre-shell.py`
  denies `pixi run -e pyforge-steward pyforge steward estate refresh --transitive` and allows the same command
  without the flag and `estate plan`; the hook's matcher-equals-roster assertion passes.
- **AC5 — Status and duty count.** `estate status` prints the last journal; `DUTIES` has 28 entries (or 29 if
  Story 99.3's `ci` has landed) and both count assertions pass; `steward --help` lists `estate`.
- **AC6 — Nothing live.** No test calls a live `pixi`, `git` or network; `pixi.toml` and `pixi.lock` at `HEAD` are
  unchanged by the test suite.

## Boundaries & Constraints

- No `realize`, `reconcile` or `verify` in this story (100.5, 100.3, 100.4).
- The duty never edits `pixi.toml` itself; the only writers are `pixi upgrade`, `pixi update` (operator), `pixi
  lock` and Story 100.1's mutator, all subprocesses.
- The policy file, the exclude list and the hold classes are never copied into the duty; it calls
  `--render-command`.
- A journal is one file per run, tracked, never rewritten by a later run (append `-2` the same day).
- The flag's per-environment values come from Epic 76's overlay; the story adds the flag and its inventory row
  only.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| `plan` offline (doctor gather raises) | BMAD `latest: unknown`, exit 0 |
| `refresh` when `pixi upgrade --json` reports zero moves | journal with empty `moves`, `pixi lock` still runs, exit 0 |
| `refresh` when the restore refuses (lock cannot solve) | journal records the refusal, exit = the documented refusal code, `pixi.toml` bytes restored |
| `refresh` twice the same day | `<date>.json` then `<date>-2.json` |
| `refresh` in a worktree whose branch is `main` | refusal before any call |
| `--transitive` run by an agent through Bash | the hook denies; the duty itself does not know who called it |
| flag off | every verb refuses naming `pyforge.steward.estate_refresh` |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-167 (FR-40), minted 2026-10-13.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-13 (estate refresh) entry.
- Epic: Epic 100, Stories 100.1–100.7.
- Ledger key: `100-2-one-command-moves-the-library-pins-on-the-policy-and-restores-what-the-upgrade-loses`.
- Ledger status at mint: `backlog`.
- Deps: S-100.1 (the policy, the check and the mutator). `marshal factory dispatch` stamps `baseline_revision` with the launch commit (Story 100.1's run did), so no
  hand re-base is needed.
- Surface: `marshal-policy.toml` `[epic_surfaces]."100"` (added with the mint).
- Minted 2026-10-13 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_estate.py -q` — expected: pass (AC1–AC5).
- `python3 .claude/hooks/pre-shell.py --self-test` (or the hook's own test under `tests/scripts/`) — expected: the roster/matcher assertion passes (AC4).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps (the roster and the hook are governed by `spec-pyforge-steward` CAP-165's surface; reconcile every Spec the detector names).
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

## Spec Change Log

- 2026-10-13: minted with CAP-167 / FR-40 and Epic 100. `type: feature`, flag `pyforge.steward.estate_refresh` (new).
  `--transitive` is operator-only by ruling Q3 (recommended answer, adopted); the `session_denials` row is a
  governance act and lands with this story, the operator confirming the row text at review.
