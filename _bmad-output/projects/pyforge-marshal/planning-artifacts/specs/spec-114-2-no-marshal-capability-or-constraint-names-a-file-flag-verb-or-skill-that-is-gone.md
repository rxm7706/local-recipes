---
title: "114.2: No marshal capability or Constraint names a file, flag, verb or skill that is gone"
type: 'fix'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: heavy
story: '114.2'
spec: pyforge-marshal
surface:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/glossary.md
  - .claude/skills/marshal-run-watch/SKILL.md
  - scripts/promote_sprint_status.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_spec_names_live_paths.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/glossary.md
  - .claude/skills/marshal-run-watch/SKILL.md
  - scripts/promote_sprint_status.py
  - src/shared/packages/pyforge-marshal/pyproject.toml
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-116.1); S-114.1 sits earlier in this epic.
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** At `82a2b18828` a path scan (every backticked repo path, file name or `<x>_check` name in a capability block not marked retired must resolve in `git ls-files`) names 41 capabilities. Fourteen hold a dead name: the Guildhall console's `data.js` and `generate.py` (deleted 2026-08-25, `e07834580d`, steward Story 30.2) and `scripts/forward_dependency_check.py` and `scripts/dashboard_drift_check.py` (deleted 2026-08-10, `c698d4b1ad`, ported to `pyforge.doctor.sources`). Twenty-seven hold a runtime, upstream or historical name that is right by design. The packaging Constraint says Python `>=3.12`, a `genesis` console entry point and a `pyforge.genesis` namespace. CAP-57, CAP-84 and CAP-159 name `bmad-dev-auto` as the invoked skill; CAP-17, CAP-18, CAP-51, CAP-166, CAP-199, CAP-264 and CAP-299 carry stale names; CAP-8 states no harness range; `integration-layers.md` names caveman 2.4.0; `marshal-run-watch` and the ledger header name `-e local-recipes`.

**Approach:** A fix under CAP-229 (the ledger header line of `scripts/promote_sprint_status.py`, on this Spec's surface) and spec-one-chain-per-station:CAP-6 (Spec truth). One memlog `change` entry per capability group names its replacement (the memlog's Stale names direction of 2026-11-10 and its addendum list them), then one anchored render after Story 114.1's, both self-validate passes logged. The guard is a `live_tree` meta-test (the Spec sits outside the package; marker from Story 116.1): it takes every capability block whose heading is not `(retired <date>...)`, collects backticked tokens that look like a repo path (first segment a tracked top-level directory), a file name with a known extension (optionally `:line` or `::test`) or a symbol `<path>.<name>`, and every bare `<x>_check`; a token resolves when it is a tracked file or directory, the basename of one, a suffix of one, or a glob matching one; templated tokens (`<`, `{`, `$`, `~`, a space) pass. `ALLOW` is a tuple of (capability, token, reason) in the test, and this spec copies it at build.

Ledger key: `114-2-no-marshal-capability-or-constraint-names-a-file-flag-verb-or-skill-that-is-gone`. Type / Effort / Deps: fix / L / S-114.1, S-116.1.

## Boundaries & Constraints

**Always:**
- CAP-44 keeps `bmad-dev-auto`: it is the permanent `DevPolicy.skill` discriminator (AGENTS.md, Known pitfalls).
- The Constraint states `>=3.14`, console scripts `marshal` and `marshal-mcp`, module `pyforge.marshal` with the seed verbs under `pyforge.marshal.seed`.
- CAP-8 states the harness range as measured, `bmad-loop >=0.11.0,<0.13`, kept equal by `tests/meta/test_engine_version_range_sync.py`.
- Each by-design name (a loop home's runtime `policy.toml`, bmad-loop's `engine.py` and `runs.py`, `.bmad-loop/runs`, a glob fragment, `.pixi/envs/local-recipes`, an untracked marker, fixture names, `report.json`, a template's rendered name, upstream `llms.txt`) sits on `ALLOW` with its reason.

**Never:**
- Never move a pin.
- Never edit the package `pixi.toml` python lines (steward:S-124.3's).
- Never hand-edit `SPEC.md`.

## Acceptance Criteria

- **AC1 — Every backticked repo path, file name or `<x>_check` name in a capability block not marked retired resolves in `git ls-files` or sits on the guard's ALLOW table with a reason; the guard's own fixture (a capability naming `scripts/no_such_check.py`) fails it.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_spec_names_live_paths.py -q -m live_tree
  ```

  Expected: exit 0 (at `82a2b18828` the scan names 41 capabilities).

- **AC2 — The Constraint states the 3.14 floor and the real entry points.**

  ```bash
  test "$(grep -c '>=3\.12' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md)" = 0 && test "$(grep -cE 'a .genesis. console entry point|pyforge\.genesis' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md)" = 0
  ```

  Expected: exit 0.

- **AC3 — Only CAP-44 names `bmad-dev-auto`.**

  ```bash
  python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md').read();c=[m.group(1) for m in re.finditer(r'^- \*\*(CAP-\d+) — .*\n(?:  - .*\n)+',t,re.M) if 'bmad-dev-auto' in m.group(0)];print(c);sys.exit(0 if c==['CAP-44'] else 1)"
  ```

  Expected: exit 0; prints `['CAP-44']`.

- **AC4 — The Spec states the harness range.**

  ```bash
  grep -q '>=0.11.0,<0.13' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  ```

  Expected: exit 0.

- **AC5 — The companion names the installed compression layer.**

  ```bash
  grep -c 'caveman.*2\.4\.0' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/integration-layers.md
  ```

  Expected: prints 0.

- **AC6 — The watch skill and the ledger header name the Guild environment.**

  ```bash
  test "$(grep -c 'pixi run -e local-recipes' .claude/skills/marshal-run-watch/SKILL.md scripts/promote_sprint_status.py | awk -F: '{s+=$2} END {print s}')" = 0 && pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py -q
  ```

  Expected: exit 0.

- **AC7 — Planning detectors stay green.**

  ```bash
  pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild story-status-check && pixi run -e pyforge-guild status-body-consistency-check && pixi run -e pyforge-guild fr-without-cap-check && pixi run -e pyforge-guild ad-citation-check
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-229 (the script line); spec-one-chain-per-station:CAP-6 (Spec truth). No new CAP.

- Epic: Epic 114 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 114.2: No marshal capability or Constraint names a file, flag, verb or skill that is gone`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Runs after Story 114.1 because both render `SPEC.md`, and after Story 116.1 because the guard carries the `live_tree` marker.
- Cross-station: the compiled `.claude/skills/pyforge-marshal/` skill is steward:S-29.5's; the package `pixi.toml` python floor is steward:S-124.3's.
- The script's header change reaches each station's ledger at that station's next `sprint-ledger-sync`; marshal's at its own sync.
- Deferred rows this story's findings feed (written by Story 116.5): DW-marshal-114-2-1 (`devin.toml` `verified = false` and the undated cost rows, not re-checked offline), DW-marshal-114-2-2 (17 to 45 large modules named by no capability).

## Guard ALLOW table (copied at build)

`ALLOW` in `src/shared/packages/pyforge-marshal/tests/meta/test_spec_names_live_paths.py`, copied 2026-11-11. Each
name is right by design: a loop home's runtime file, bmad-loop's own module or run output, an upstream file, the
untracked active-project marker, a fixture or function name, a name kept as history, or a file a later story writes.
Glob fragments such as `spec-<e>-<n>-*.md` and commands such as `python -m pyforge.doctor.sources <name>` are templated
tokens and pass without an entry. The test fails an entry whose capability no longer carries its token, so the table
cannot outlive the text it excuses.

| Capability | Token | Reason |
|---|---|---|
| spec-pyforge-marshal:CAP-19 | `policy.toml` | a loop home's rendered bmad-loop policy, a runtime file never tracked |
| spec-pyforge-marshal:CAP-20 | `policy.toml` | a loop home's rendered bmad-loop policy, a runtime file never tracked |
| spec-pyforge-marshal:CAP-39 | `project-context.md` | the eight per-station rulebooks this capability refreshed, since retired |
| spec-pyforge-marshal:CAP-40 | `removals.txt` | bmad-method's own removals list, an upstream file |
| spec-pyforge-marshal:CAP-41 | `project-context.md` | the per-station rulebooks this capability retired |
| spec-pyforge-marshal:CAP-42 | `llms-full.txt` | bmad-method's discontinued upstream documentation file |
| spec-pyforge-marshal:CAP-42 | `llms.txt` | bmad-method's discontinued upstream documentation file |
| spec-pyforge-marshal:CAP-45 | `policy.toml` | the eight loop homes' rendered bmad-loop policy, runtime files |
| spec-pyforge-marshal:CAP-50 | `failed/*/changes.patch` | a bmad-loop run output under .bmad-loop/runs/ |
| spec-pyforge-marshal:CAP-52 | `engine.py:1707` | bmad-loop's own module, cited in the upstream issue |
| spec-pyforge-marshal:CAP-52 | `runs.py:872-908` | bmad-loop's own module, cited in the upstream issue |
| spec-pyforge-marshal:CAP-59 | `.bmad-loop/policy.toml` | a loop home's rendered bmad-loop policy, gitignored |
| spec-pyforge-marshal:CAP-69 | `src/pyforge_genesis` | the pre-split installer tree, named as what was removed |
| spec-pyforge-marshal:CAP-72 | `project-context.md` | the per-station rulebooks this capability regenerated, since retired |
| spec-pyforge-marshal:CAP-74 | `product-brief-pyforge-marshal.md` | the loose name of the brief this capability moved, history |
| spec-pyforge-marshal:CAP-105 | `orphans.json` | a consolidation run's output under its run folder |
| spec-pyforge-marshal:CAP-105 | `orphans.md` | a consolidation run's output under its run folder |
| spec-pyforge-marshal:CAP-132 | `.bmad-loop/policy.toml` | a loop home's rendered bmad-loop policy, gitignored |
| spec-pyforge-marshal:CAP-134 | `.bmad-loop/policy.toml` | a loop home's rendered bmad-loop policy, gitignored |
| spec-pyforge-marshal:CAP-134 | `policy.toml` | a loop home's rendered bmad-loop policy, a runtime file never tracked |
| spec-pyforge-marshal:CAP-164 | `changes.patch` | a bmad-loop run output, named as the analog dispatch keeps |
| spec-pyforge-marshal:CAP-165 | `policy.toml` | a loop home's rendered bmad-loop policy, a runtime file never tracked |
| spec-pyforge-marshal:CAP-171 | `.bmad-loop/runs/` | bmad-loop's runtime run directory, gitignored |
| spec-pyforge-marshal:CAP-172 | `.bmad-loop/runs/` | bmad-loop's runtime run directory, gitignored |
| spec-pyforge-marshal:CAP-227 | `.bmad-loop/runs` | bmad-loop's runtime run directory, the literal the guard matches |
| spec-pyforge-marshal:CAP-263 | `.pixi/envs/local-recipes` | named as what the watch must never reach |
| spec-pyforge-marshal:CAP-273 | `_bmad/custom/.active-project` | the shared active-project marker, untracked by design |
| spec-pyforge-marshal:CAP-279 | `.bmad-loop/policy.toml` | a loop home's rendered bmad-loop policy, gitignored |
| spec-pyforge-marshal:CAP-279 | `_bmad/custom/.active-project` | the shared active-project marker, untracked by design |
| spec-pyforge-marshal:CAP-279 | `docs/dreams/demo.md` | a fixture name in the seed check's test project |
| spec-pyforge-marshal:CAP-279 | `run_check` | a function in seed/verbs/check.py, not a script |
| spec-pyforge-marshal:CAP-298 | `installed_plugins.json` | Claude Code's own plugin registry, outside the repository |
| spec-pyforge-marshal:CAP-298 | `plugin.json` | the cached EGM plugin's manifest, outside the repository |
| spec-pyforge-marshal:CAP-298 | `report.json` | a challenge run's output under implementation-artifacts/egm/<run>/ |
| spec-pyforge-marshal:CAP-305 | `tests/_support/tree_read_guard.py` | written by Story 116.4, open while CAP-305 reads ready |
| spec-pyforge-marshal:CAP-305 | `tests/meta/test_tree_read_guard.py` | written by Story 116.4, open while CAP-305 reads ready |

## Planned deferral (written at build)

The row below is not in the deferred-work ledger yet and is not in this spec's frontmatter (`deferred-work-check` reds a
frontmatter row with no tracked ledger twin). The marshal station closer of the cutover-readiness PR (Story 116.5)
writes it to `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md`: open if the two entries
below are still on `ALLOW` when the closer runs, otherwise resolved with a pointer to the change that dropped them.

- **`DW-marshal-114-2-3`** (low; owner Story 116.5, after Story 116.4; location
  `src/shared/packages/pyforge-marshal/tests/meta/test_spec_names_live_paths.py`, `ALLOW`): the two
  spec-pyforge-marshal:CAP-305 entries, `tests/_support/tree_read_guard.py` and `tests/meta/test_tree_read_guard.py`,
  excuse files Story 116.4 (BUILD-7) writes. Once `git ls-files` lists them the names resolve on their own and the two
  entries are dead weight; the stale-entry test does not catch that, because the capability still carries the tokens.
  Drop both entries (and their rows above) once Story 116.4 has landed on the branch.

## Spec Change Log

- 2026-11-10: minted at `blocked` (forward dependency: until S-114.1 and S-116.1 are done) by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
- 2026-11-11 (build): one accepted deviation. The Always line and AC4's context name `tests/meta/test_engine_version_range_sync.py` as the test that keeps the harness range equal; that test keeps copier's range (`COPIER_VERSION_RANGE` against `pixi.toml`), not bmad-loop's. `tests/meta/test_manifest_sync.py::test_harness_range_constants_match_pyproject_dependency_pin` keeps `pyproject.toml`'s `bmad-loop` pin, the package `pixi.toml` and `HARNESS_VERSION_RANGE_TEXT` (`adapters/harness_bmadloop.py`) equal, so spec-pyforge-marshal:CAP-8 names that test; writing the other would plant a stale name in the Spec this story cleans. The range itself, `bmad-loop >=0.11.0,<0.13`, is as the Always line states, and AC4 holds. The spec-pyforge-marshal:CAP-91 text names `marshal status` (its `unpushed_work` row field), not `scripts/fleet_scan.py` or the Doctor sources as the memlog addendum of 2026-11-10 grouped it: neither holds that behaviour; the memlog change entry of 2026-11-11 records the refinement.

## Gate findings (build, BUILD-3)

- 2026-11-11, `pyforge-marshal-test` (wave gate BUILD-3): red on two tests in
  `src/shared/packages/pyforge-marshal/tests/unit/test_land_epic_rollups.py`, a file of marshal:S-116.1 (BUILD-1,
  done): `test_the_replayed_inputs_reproduce_b9869e5c6d_without_the_roll_up` (line 395; the replay's blob is no longer
  the pinned `430d290a…`) and `test_the_doctor_41_5_replay_publishes_epic_41_in_progress` (line 410; the published
  header line differs from the fixture). Cause: this story's `_HEADER` change in `scripts/promote_sprint_status.py`
  (`-e local-recipes` to `-e pyforge-guild`, spec-pyforge-marshal:CAP-229, AC6). Both tests render the historical
  `b9869e5c6d` ledger through the live script, and its header no longer matches the historical bytes. Not fixable in
  this story's files: reverting the header line fails AC6, and no script change can reproduce the historical bytes
  without the old environment name. Re-run by the wave fix: the module still gives 2 failed, 9 passed (exit 1). A
  three-hunk fix to the test file passes on a scratch copy (11 passed): constants `_HEADER_THEN` and `_HEADER_NOW` hold
  the sync's header line then and now; the replay test asserts `_HEADER_NOW in unfixed` and compares the blob of
  `unfixed.replace(_HEADER_NOW, _HEADER_THEN)` to the pin; the finalize test compares the published text to
  `_DOCTOR_BEFORE.replace(_HEADER_THEN, _HEADER_NOW)` with the 41-5 row advanced. The pinned blob ids and the
  fixture stay as they are. Left to the orchestrator: give the test file an owner in this wave (for example add it to
  this story's files_owned, since marshal:S-116.1 is done), then apply that patch.
