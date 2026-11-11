---
title: "114.2: No marshal capability or Constraint names a file, flag, verb or skill that is gone"
type: 'fix'
created: '2026-11-10'
status: 'blocked'
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

## Spec Change Log

- 2026-11-10: minted at `blocked` (forward dependency: until S-114.1 and S-116.1 are done) by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
