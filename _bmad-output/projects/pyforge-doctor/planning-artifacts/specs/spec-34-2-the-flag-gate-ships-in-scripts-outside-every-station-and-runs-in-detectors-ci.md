---
title: '34.2: The flag gate ships in scripts, outside every station, and runs in detectors-ci'
type: 'feature'
created: '2026-09-28'
status: 'in-progress'
baseline_revision: '7151e3d2653a6289c4f01a4ac17f8514aee3247a'
flag-exempt: detector-or-gate   # a gated gate reports a silent green (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
warnings: [oversized]
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-1-the-flag-rule-has-a-closed-exemption-list-a-rule-date-baseline-and-one-block-shape.md
  - scripts/coverage_gate.py
  - scripts/detectors.py
  - src/platform/config/flags.json
  - src/shared/packages/pyforge-doctor/tests/meta/test_coverage_gate_stays_outside_every_station.py
deferred:
  - summary: >-
      Scribe Story 24.1 is a post-rule `type: feature` story spec that carries neither a `flag:` block nor a
      `flag-exempt:` value, so the gate reds it (`flag-missing`) and the landing is blocked on scribe.
    evidence: |-
      PR #1672 merged after the rule-date baseline (5e977accb9). `pixi run -e pyforge-guild flag-gate-check` on the
      landing tree exits 1 with exactly two FAIL findings, this spec and the one below; every other finding is a
      pre-rule WARN. A red `flag-gate-check` row would red `detectors-ci` for every PR, and this story may neither
      edit scribe's specs nor exempt them. Scribe adds a `flag:` block, or a `flag-exempt:` value from the roster's
      closed list, to both specs before this story lands.
    location: >-
      _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-24-1-the-bmad-estate-catalog-is-generated-not-written.md
    severity: high
  - summary: >-
      Scribe Story 24.2 is a post-rule `type: feature` story spec that carries neither a `flag:` block nor a
      `flag-exempt:` value, so the gate reds it (`flag-missing`) and the landing is blocked on scribe.
    evidence: |-
      Same cause and same fix as Story 24.1 above: merged in PR #1672 after the baseline, reported to its owning Smith,
      not exempted by this story.
    location: >-
      _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-24-2-the-catalog-cannot-drift-silently.md
    severity: high
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-feature-flag-governance` CAP-2 is the gate that makes the rule bite: from the rule date (2026-09-28)
`detectors-ci` reds a post-rule `type: feature` story spec that carries neither a `flag:` block nor a `flag-exempt:`
value, and it keeps the one tree (`src/platform/config/flags.json`, canopy:AD-11) honest. The gate judges all eight
Smiths, so under Charter §6 it cannot ship inside any of them — Doctor's included, because Doctor is constitutionally
advisory (the coverage-gate-independence resolution: `scripts/coverage_gate.py`, Story 24.1, pinned by Story 24.2's
meta-test). Marshal Story 74.2 will consult this gate at dispatch, so the gate also needs a one-spec interface.

**Approach:** `scripts/flag_gate_check.py` declares `DETECTOR = {"scope": "repo"}`, so `scripts/detectors.py` discovers it
and `detectors-ci` runs it; the `flag-gate-check` pixi task (guild tasks) invokes it. It reuses Story 34.1's
`scripts/flag_rule.py` for classification and the baseline, and reads the tree as JSON. Tree mode walks every tracked
`_bmad-output/projects/*/planning-artifacts/specs/spec-<E>-<S>-*.md` and the tree:
- **FAIL** (exit 1): a post-rule `type: feature` spec that is `neither`; a `flag-exempt:` value not on the roster; a spec
  whose frontmatter `status` is `done` and whose `flag.key` is not a key of the tree (a story still in backlog has not
  added its key yet, so only a landed one is judged); a tree key that no tracked file under `src/` or `scripts/` reads,
  excluding the tree itself, story specs, docs and tests.
- **WARN** (never a FAIL): a pre-rule `type: feature` spec that is `neither` (Ruling 3), grouped by station — the list
  Story 34.4's inventory counts.
- **Unknown** (exit 2): the tree, the roster or the baseline cannot be read — never green (fidelity-enforcement).

`--spec <path>` judges one story spec and prints one JSON object — `verdict` (`pass`, `warn` or `red`), `findings`,
`rule_date` — exiting 0 on `pass` or `warn`, 1 on `red`, 2 when it cannot judge. That object is the interface marshal Story
74.2's dispatch preflight consults. A meta-test in doctor's `tests/meta/` (and its companion copy under
`pyforge-core/tests/meta/`, Story 24.2's reason: the core suite runs on any single-station change) fails if any
`pyforge.<station>` module defines or imports the gate. The metadata checks (per-environment defaults, the 90-day clock)
are Story 34.3's; the two-state-test check is Story 34.5's.

Ledger key: `34-2-the-flag-gate-ships-in-scripts-outside-every-station-and-runs-in-detectors-ci`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-34.1.

### Living CAP citations

- `spec-feature-flag-governance` CAP-2 (Guild-owned; Doctor as mechanism Smith — Epic 24's relay; no doctor CAP or FR).
- Kinship: marshal Story 74.2 (`spec-feature-flag-governance` CAP-3, consults `--spec`; minted `blocked` behind this
  story); `spec-coverage-gate-independence` CAP-1/CAP-3 (the same "outside every station" shape and its meta-test).

## Acceptance Criteria

- Given a fixture tree with a post-rule `type: feature` spec that carries neither When the gate runs Then it exits 1 with one FAIL naming the spec and the missing block
- Given the same spec listed in the baseline When the gate runs Then it exits 0 with one WARN naming it under its station
- Given `flag-exempt: someday` on any spec When the gate runs Then one FAIL names the unknown value
- Given a `done` flagged spec whose key the tree lacks When the gate runs Then one FAIL names the key; given the same spec at `backlog` Then no finding
- Given a fixture tree holding a test-local key (for example `pyforge.test.orphan`) that no file under the fixture's `src/` or `scripts/` mentions When the gate runs Then one FAIL names the key; given the same fixture with a fixture `src/` file that reads the key Then no finding
- Given the live tree at the landing SHA When the gate runs Then no orphan-key finding: every key it holds is read in `src/` (`pyforge.cutover_root` through `pyforge.core.cutover_root.CUTOVER_FLAG`; any other key the tree holds by then through its own reader). *(Amended 2026-09-29: this criterion named `pyforge.three_surfaces` on the live tree, and steward Story 76.4 removes that demo flag from the tree and from `src/` together, by operator ruling of 2026-09-28 (night). The orphan-key behaviour is now proven on a test-local fixture key, so the criterion holds whether 34.2 lands before or after 76.4.)*
- Given `--spec <path>` on each fixture When it runs Then it prints one JSON object with `verdict` `red`, `warn` or `pass` and exits 1, 0 or 0
- Given an unreadable tree, roster or baseline When the gate runs Then it exits 2 and reports what it could not read
- Given a planted `pyforge.<station>.flag_gate` module in a temporary tree When the meta-test runs Then it fails; on the real tree it passes
- Given the live tree at the landing SHA When `pixi run -e pyforge-guild flag-gate-check` runs Then it exits 0 (warnings allowed), and `pixi run -e pyforge-guild detectors-ci` reports no new finding against `main`
- Given the change When `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Ship the gate in `scripts/`, its tests in `tests/scripts/`, and nothing of it in any `pyforge.<station>` package.
- Read the exemption list and the baseline through `scripts/flag_rule.py` (Story 34.1), never a second copy.
- Register the `flag-gate-check` task in `pixi.toml` and regenerate `environment.yaml` in the same change
  (`pixi project export conda-environment -e build > environment.yaml`); add the script's allowlist line to
  `scripts/spec_surface_allowlist.txt`; record the new paths in the Guild Spec's `.memlog.md` via `memlog.py`.
- Leave the tree at zero FAIL at the landing SHA: a post-rule spec that lacks both is named in the landing PR and
  reported to its owning Smith, never exempted by this story.

**Never:**
- Do not import `pyforge.doctor` or any station's internals from the gate.
- Do not read `.steward/flags.json`: steward Story 76.3 folds that second tree into the one tree.
- Do not add a second PR verdict: the gate is one row of `detectors-ci`.
- Do not edit `SPEC.md`, `sprint-status-ledger.yaml` or the roster's list; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new feature, no block | post-rule, `neither` | FAIL | exit 1 |
| backlog feature, no block | pre-rule, `neither` | WARN under its station | exit 0 |
| `fix` / `chore` / `docs` | any | nothing (Q1) | — |
| unknown exemption | `flag-exempt: later` | FAIL | exit 1 |
| landed, key missing | `done`, key not in tree | FAIL | exit 1 |
| not landed, key missing | `backlog`, key not in tree | nothing | — |
| orphan tree key | no reader in `src/` or `scripts/` | FAIL | exit 1 |
| one spec | `--spec <path>` | one JSON object | exit 0/1/2 |
| unreadable input | tree, roster or baseline | the input named | exit 2 |

</intent-contract>

## Code Map

- `scripts/flag_rule.py` -- Story 34.1's pure reader; reuse `load_exemptions`, `load_baseline`/`read_baseline` (`rule_date`), `is_story_spec`, `is_post_rule`, `in_scope`, `classify_frontmatter`, `repo_relative`, and the two named errors `RosterUnreadable`/`BaselineUnreadable` (both under `FlagRuleError` = exit 2). `_frontmatter` is private: expose it as a public `read_frontmatter`, so the gate reads each spec once.
- `scripts/precommit_config_check.py` -- the shape to copy: `DETECTOR = {"scope": "repo"}` above the imports, `main() -> int`, `sys.exit(main())`; exit 0/1/2. `scripts/detectors.py` finds it by the `*_check.py` glob and pairs it to the pixi task whose `cmd` contains the file name.
- `src/platform/config/flags.json` -- the one tree; keys today: `pyforge.three_surfaces`, `pyforge.cutover_root`, `pyforge.steward.ghe_fleet_credentials`, all read in `src/` non-test files.
- `src/shared/packages/pyforge-doctor/tests/meta/test_coverage_gate_stays_outside_every_station.py` and `pyforge-core/tests/meta/test_coverage_gate_ci_trigger_companion.py` -- the "outside every station" meta-test and its core companion (predicates duplicated on purpose; core does not depend on doctor).
- `pixi.toml` ~line 1311 -- `[feature.guild-tasks.tasks.precommit-config-check]`: the sibling task shape for `flag-gate-check`.
- `scripts/spec_surface_allowlist.txt` lines 40-44 -- the `flag_rule.py` / `coverage_gate.py` allowlist lines to mirror.
- `tests/scripts/test_flag_rule.py` -- the test header to copy (`pytest.importorskip("yaml")`, `sys.path.insert` of `scripts/`).
- Live tree measured 2026-09-29 with `flag_rule`: 839 pre-rule feature specs `neither` (WARN); 22 post-rule `exempt`; 19 post-rule `flag`; **2 post-rule `neither`**: scribe `spec-24-1-...` and `spec-24-2-...` (see Design Notes).

## Tasks & Acceptance

**Execution:**
- `scripts/flag_rule.py` -- add public `read_frontmatter(path, *, repo_root=None)` wrapping `_frontmatter`; unit-test it in `tests/scripts/test_flag_rule.py` -- one read per spec, no private import across files
- `scripts/flag_gate_check.py` -- new: `DETECTOR = {"scope": "repo"}`; `--root`, `--spec`, `--json`, `-v`; tree mode (5 finding kinds: `flag-missing`, `flag-exempt-unknown`, `flag-key-not-in-tree`, `flag-key-orphan` FAIL; `flag-pre-rule` WARN grouped by station); `--spec` mode prints one JSON object (`verdict`, `findings`, `rule_date`); exit 0/1/2 -- the gate itself
- `tests/scripts/test_flag_gate_check.py` -- new: fixture-tree tests for every I/O row and every AC (fixture `src/`, `scripts/`, roster, baseline, tree written under `tmp_path`); assert exit codes, finding text, `--spec` JSON, exit 2 on each unreadable input -- the oracle
- `src/shared/packages/pyforge-doctor/tests/meta/test_flag_gate_stays_outside_every_station.py` -- new: scan all eight stations for a module named `flag_gate`/`flag_gate_check` (file or package dir) or importing it (static or dynamic); planted-module proof per station; real tree passes -- Charter section 6
- `src/shared/packages/pyforge-core/tests/meta/test_flag_gate_ci_trigger_companion.py` -- new: narrower copy for single-station PRs, same predicates -- core suite runs on any station change
- `pixi.toml` -- add `[feature.guild-tasks.tasks.flag-gate-check]` (`cmd = "python scripts/flag_gate_check.py"`) after `precommit-config-check`; `environment.yaml` -- regenerate with `pixi project export conda-environment -e build > environment.yaml` -- registry needs a task or `detectors` reports a gap
- `scripts/spec_surface_allowlist.txt` -- add the `scripts/flag_gate_check.py` line -- same shape as `flag_rule.py`
- `docs/governance/spec-feature-flag-governance/.memlog.md` (via `_bmad/scripts/memlog.py append`) and every co-governor `python scripts/spec_surface_reconcile.py` names -- record the new paths; never `--write-baseline`

**Acceptance Criteria:**
- Given the Acceptance Criteria in the intent contract, when `pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_gate_check.py tests/scripts/test_flag_rule.py -q` runs, then it passes
- Given the meta-test and its core companion, when they run against the real tree, then both pass; against a planted `pyforge.<station>.flag_gate` module, both fail
- Given `pixi run -e pyforge-guild detectors --scope repo --list`, when it runs, then `flag_gate_check` is listed with task `flag-gate-check` and no registry gap is reported

## Spec Change Log

- 2026-09-30 -- operator decision, unblocked (no change to the intent contract): scribe fixed the two specs this gate reds on the live tree -- `spec-24-1-...` now reads `flag-exempt: docs-only` and `spec-24-2-...` `flag-exempt: detector-or-gate` (PR `unblock-wave1-2026-09-30`, merged to `origin/main`; recorded on `spec-feature-flag-governance` and `spec-pyforge-scribe`). Before anything else, bring `origin/main` into this branch (merge, never rebase), resolve any conflict in favour of `main` outside this story's surface, then re-run the Verification commands and `pixi run -e pyforge-guild flag-gate-check` against the merged tree and read each exit code. The AC "the live tree exits 0" is expected to hold now; if the gate names any other spec, record it in `deferred:` and stop blocked again rather than editing another station's spec. The implementation itself is complete and is not redone.
- 2026-09-29 -- implemented: status `in-progress` -> `in-review`; every task done; the intent contract is unchanged. `deferred:` records the two scribe specs the live tree reds (Design Notes, Live-tree conflict). Two additions beyond the Tasks list, both forced by a detector: `docs/reference/detectors.md` and `docs/how-to/pixi-tasks.md` re-rendered (`docs-detectors`, `docs-pixi-tasks`; the first also picks up `bmad_estate_check`, missing since PR #1672), and one sentence in `docs/reference/story-spec-flag-block.md` that said the gate was a separate story's. Not delivered as written: the AC "the live tree exits 0" cannot hold until scribe fixes its two specs.

## Design Notes

**Unknown exemption vs `neither`.** A `flag-exempt:` value that is non-blank and off the roster yields one `flag-exempt-unknown` FAIL (any spec, any type, pre- or post-rule) and suppresses that spec's `flag-missing` finding, so `someday` never reports twice. A blank or doubled declaration stays `neither`. A spec whose frontmatter cannot be read is treated as `neither` (never silently out of scope).

**Orphan key search.** A key is read when its text appears in a tracked file under `src/` or `scripts/`: `git ls-files` when `<root>/.git` exists, else a filesystem walk (fixtures). Skipped: the tree, any path part `tests`/`test`/`docs`/`fixtures`, `test_*.py`, `conftest.py`, and `*.md`. The gate names no live key in its own source, so it never satisfies itself.

**`--spec`** judges one story spec: `red` (post-rule `neither`, unknown exemption, `done` key absent from tree), `warn` (pre-rule `neither`), else `pass`. A path that is unreadable or not a story spec exits 2 with `verdict: "unknown"`, never green.

**Live-tree conflict (found in planning, 2026-09-29).** Scribe Stories 24.1 and 24.2 (PR #1672, merged after the baseline) are post-rule `type: feature` specs carrying neither block, so the gate correctly reds the live tree with 2 FAIL findings, and the intent contract's "no exemption by this story" and "zero FAIL at the landing SHA" cannot both hold until scribe adds a block or exemption to its own specs. Implement the gate as specified; do not edit scribe's specs and do not exempt them here. Record both specs in a `deferred:` entry located at each spec path, name them in the landing PR, and report the landing as blocked on scribe, since a red `detectors-ci` row would red every PR.

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-2 and its rulings (memlog 3 and 23),
`docs/dreams/feature-flag-governance.md`, and the coverage-gate-independence precedent (doctor Stories 24.1 and 24.2),
decomposed 2026-09-28 (night) as Epic 34's mint.

## Binding

Parent Spec capability: `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-2 (Guild-owned; Doctor as mechanism
Smith).
Dream: `docs/dreams/feature-flag-governance.md` § Realization log → *2026-09-28 (night)*.
Ledger key: `34-2-the-flag-gate-ships-in-scripts-outside-every-station-and-runs-in-detectors-ci`.
Ledger status at mint: `backlog`.
Policy: `marshal-policy.toml` `[epic_surfaces]` `"34"`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_gate_check.py tests/scripts/test_flag_rule.py -q` — expected: pass.
- `pixi run -e pyforge-guild flag-gate-check` — expected: exit 0 on the landing tree (WARNs allowed).
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`.
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass (the companion meta-test).

## Review Triage Log

## Auto Run Result

Status: blocked
Blocking condition: implementation verification failed -- `pixi run -e pyforge-guild flag-gate-check` exits 1 on the live tree, not 0. Two FAIL findings (`flag-missing`), both post-rule `type: feature` specs merged in PR #1672 after the rule-date baseline, carrying neither a `flag:` block nor a `flag-exempt:` value: `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-24-1-the-bmad-estate-catalog-is-generated-not-written.md` and `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-24-2-the-catalog-cannot-drift-silently.md`. This story may neither edit scribe's specs nor exempt them, so the failure cannot be fixed here. Scribe adds a `flag:` block or a roster `flag-exempt:` value to both, then this story lands; until then the gate's `detectors-ci` row would red every PR. Recorded in `deferred:` and promoted to `DW-doctor-34-2` / `DW-doctor-34-2-2` in the doctor deferred-work ledger. The operator flips the row once scribe has fixed its specs.

Built and verified (measured 2026-09-29, exit codes read directly):
- `scripts/flag_gate_check.py` (`DETECTOR = {"scope": "repo"}`, task `flag-gate-check`), public `read_frontmatter` in `scripts/flag_rule.py`, `tests/scripts/test_flag_gate_check.py`, the doctor meta-test and its core companion, allowlist line, regenerated `docs/reference/detectors.md`, `docs/how-to/pixi-tasks.md`, `docs/map.yaml`.
- `tests/scripts/test_flag_gate_check.py` + `test_flag_rule.py`: 149 passed. `pyforge-doctor-test`: 3005 passed, 1 skipped, exit 0. `pyforge-core-test`: 1992 passed, exit 0. Every I/O-matrix row has a passing test.
- Live tree: 1206 story specs judged, 2 FAIL (the scribe pair), 840 WARN; no orphan key, no unknown exemption, no `done` key missing from the tree.
- `python scripts/spec_surface_reconcile.py` and `spec-surface-check` exit 0. `scripts/.spec-surface-baseline.json` is unchanged: the implementation subagent's three scoped `--write-baseline` stamps were reverted (this run forbids `--write-baseline`); the surface is reconciled by memlog entries on `docs/governance/spec-feature-flag-governance`, `spec-pyforge-doctor`, `spec-pyforge-core` and `spec-pyforge-unifying-strategy`, plus a correction entry on the Guild Spec.
- `detectors-ci` also shows `bmad_estate_check` (the gitignored, dispatch-seeded `.claude/skills/caveman/`) and `ledger-direction` (`pyforge-marshal/77-1` is on `origin/main`, not on this branch). Neither is touched by this diff; expect both to clear on rebase / in CI.

Not run: adversarial review (step 4), because verification failed. Open for the reviewer once unblocked: `marshal-policy.toml` `[epic_surfaces]` `"34"` does not admit the doctor deferred-work ledger, `docs/reference/detectors.md` or `docs/how-to/pixi-tasks.md`, and admits a core file named `test_flag_gate_stays_outside_every_station.py` where this spec names `test_flag_gate_ci_trigger_companion.py`; the spec's name was followed.
