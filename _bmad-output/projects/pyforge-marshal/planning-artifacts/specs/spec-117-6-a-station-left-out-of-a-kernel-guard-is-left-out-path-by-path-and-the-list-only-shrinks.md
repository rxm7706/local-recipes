---
title: "117.6: A station left out of a kernel guard is left out path by path, and the list only shrinks"
type: 'feature'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a sole-ownership guard (roster flag_exemptions): a gated guard reports a silent green
difficulty: medium
story: '117.6'
spec: pyforge-core
surface:
  - src/shared/packages/pyforge-core/tests/meta/test_station_exclusions_only_shrink.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/pyforge-unifying-strategy.md
  - src/shared/packages/pyforge-core/tests/meta/test_exception_root_sole_ownership.py
  - src/shared/packages/pyforge-core/tests/meta/test_process_sole_ownership.py
  - src/shared/packages/pyforge-core/tests/meta/conftest.py
  - src/shared/packages/pyforge-core/src/pyforge/core/errors.py
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** An audit defect of 2026-11-10 (a guard that cannot fire): the exception-root guard excludes steward and doctor, the subprocess guard excludes six stations, and neither scans `pyforge-core` itself, so a new builtin-rooted class or a new raw subprocess call in those trees is never seen.

**Approach:** Realizes the spec-pyforge-core:CAP-7 amendment (memlog 2026-11-10, rendered by Story 117.5). No product code changes. Two frozensets of relative paths, the shape of the subprocess guard's `_EXEMPT_RELATIVE_PATHS` and steward's `UNSPLIT_ON_A_STATION_SRC_EDIT`: `_UNREPARENTED_ROOTS` (`pyforge-<s>/src/pyforge/<s>/<path>::<Class>` for the exception guard's out-of-scope stations and for pyforge-core) and `_SUBPROCESS_FILES` (`pyforge-<s>/src/...` files for the subprocess guard's out-of-scope stations). The measurement imports the guards' own detectors from the sibling modules (`_root_violations`, `_subprocess_violations`, `_OUT_OF_SCOPE_STATIONS`; `from conftest import PACKAGES_ROOT, parse_module`), so the rule is not copied. Measured equals pinned: a new entry fails with `root it at pyforge.core.errors.PyforgeError` or `launch it through pyforge.core.process`; a pin with no measured entry fails with `lower the pin`. Paths, not counts: a count would hide a violation that moves files and would red a module split. `PyforgeError` itself (`class PyforgeError(Exception)` matches the detector) is excluded by name. The four synthetic proofs carry `fires`, the two scope tests `scope`. Plan-time measurement for the record (`f614d6a9b8`): roots in steward, doctor and pyforge-core (PyforgeError aside); subprocess files in steward, herald, mason, scribe, doctor and warden.

Ledger key: `117-6-a-station-left-out-of-a-kernel-guard-is-left-out-path-by-path-and-the-list-only-shrinks`. Type / Effort / Deps: feature / M / S-115.1, S-115.2, S-115.3, S-115.4, S-117.1, S-117.2, S-117.3, S-117.4, S-117.5, S-117.7 (same-station keys, as in `epics.md`; the cross-station dependencies are in Notes).

## Boundaries & Constraints

**Always:**
- Runs on the integration branch after every story of this PR that edits a station's `src/`, so the pins are measured once, on final code.
- No number is written into the capability or the deferred rows before this story measures.

**Never:**
- Never re-parent an exception class or reroute a subprocess call here (operator ruling of 2026-11-10: re-parenting stays out; the pins only shrink).
- Never append a `Surface reconcile` line to any Spec's memlog and never run `spec_surface_check.py --write-baseline`: the governed paths go in this spec's `surface:`, Story 117.8 reconciles core and the testing charter, and doctor:S-58.4 stamps once.

## Acceptance Criteria

- **AC1 — Pins equal the guards' own measurement on the integration branch.**

  ```bash
  pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/meta/test_station_exclusions_only_shrink.py -q -p no:cacheprovider
  ```

  Expected: exit 0.

- **AC2 — The ratchet fires on synthetic trees.**

  ```bash
  pixi run --frozen -e pyforge-core python -c "import re,subprocess,sys; r=subprocess.run(['pytest','src/shared/packages/pyforge-core/tests/meta/test_station_exclusions_only_shrink.py','-q','-p','no:cacheprovider','-k','fires'],capture_output=True,text=True); m=re.search(r'(\d+) passed',r.stdout); print(r.returncode, m and m.group(1)); sys.exit(r.returncode or not m or int(m.group(1))<4)"
  ```

  Expected: exit 0, at least 4 passed: a new builtin-rooted class in an excluded package, a new subprocess call site in an excluded station, a stale root pin and a stale file pin each fail the check.

- **AC3 — The pinned stations are the guards' own exclusions, and PyforgeError is excluded by name.**

  ```bash
  pixi run --frozen -e pyforge-core python -c "import re,subprocess,sys; r=subprocess.run(['pytest','src/shared/packages/pyforge-core/tests/meta/test_station_exclusions_only_shrink.py','-q','-p','no:cacheprovider','-k','scope'],capture_output=True,text=True); m=re.search(r'(\d+) passed',r.stdout); print(r.returncode, m and m.group(1)); sys.exit(r.returncode or not m or int(m.group(1))<2)"
  ```

  Expected: exit 0, at least 2 passed (pinned stations == each guard's `_OUT_OF_SCOPE_STATIONS`, plus pyforge-core for roots; `pyforge-core/src/pyforge/core/errors.py::PyforgeError` is never a pin).

- **AC4 — Live-tree marker.**

  ```bash
  grep -c '^pytestmark = pytest.mark.live_tree$' src/shared/packages/pyforge-core/tests/meta/test_station_exclusions_only_shrink.py
  ```

  Expected: prints 1.

- **AC5 — What this PR added to the pins is named.**

  The story spec gains a `## Verification` section with one line `Added pins: none`, or `Added pins: <pin> (<station>:S-<E>.<S>)[, ...]` listing every pin that is not in the plan-time measurement at `f614d6a9b8` (the guards' own detectors) with the story that added it; each added pin also gets a `deferred:` entry naming its story, which Story 116.5 ingests.

  ```bash
  grep -cE '^Added pins: (none|.+ \(([a-z]+:)?S-[0-9]+\.[0-9]+\)(, .+ \(([a-z]+:)?S-[0-9]+\.[0-9]+\))*)$' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-117-6-a-station-left-out-of-a-kernel-guard-is-left-out-path-by-path-and-the-list-only-shrinks.md
  ```

  Expected: prints 1.

- **AC6 — The whole core suite still passes as wired.**

  ```bash
  pixi run --frozen -e pyforge-core pyforge-core-test
  ```

  Expected: exit 0.

- **AC7 — Lint and types.**

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-core` (spec-pyforge-core:CAP-7, amended 2026-11-10; FR-163, body unchanged); AD-67, AD-68, AD-69.

- Epic: Epic 117 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 117.6: A station left out of a kernel guard is left out path by path, and the list only shrinks`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The shared floor says what it is: core and the testing kit before the cutover.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda (operator, "Accept all, run mint").

## Notes

- Cross-station deps (every story of this PR that edits a station's `src/`, except steward:S-122.4, comment lines only): warden:S-25.3, scribe:S-33.2, mason:S-37.3, mason:S-39.1, atlas:S-48.2, atlas:S-48.3, herald:S-50.3, herald:S-52.2, doctor:S-56.1, doctor:S-56.2, doctor:S-56.3, doctor:S-56.4, doctor:S-56.5, steward:S-121.1, steward:S-121.2, steward:S-121.6, steward:S-122.3, steward:S-123.2, steward:S-123.3; same-project: S-115.1..S-115.4, S-117.1..S-117.5, S-117.7. Their code stories were asked not to grow these lists; any growth is named. The cross-station deps are not in the `epics.md` Deps line, because marshal's Deps parser drops a station prefix and would read each as a marshal key; only the integration branch's wave order (plan.json) holds them.
- Deferred rows (written by Story 116.5): DW-marshal-117-6-1 (six stations stay outside the kernel's exception-root and subprocess guards; this story pins them, it does not migrate them), DW-marshal-117-6-2 (the leaf's own exception classes are rooted at builtins, not at PyforgeError).
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (core and the testing charter: Story 117.8; marshal: Story 116.5; steward and the host: steward:S-122.5), and doctor:S-58.4 runs every scoped stamp once, after the last edit on the branch.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). Its Deps (Stories of Epics 115 and 117) name no later epic of this station, so the one forward-dependency policy of this PR's mints (a story is minted `blocked` only when its Deps name a later epic) leaves it `backlog`; the integration branch's wave order and marshal's Deps-aware drain hold them. Its cross-station deps are in Notes, not in the Deps line, and only the integration branch's wave order holds them, since marshal's Deps parser is station-local. The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10, the shared-floor section) and the memlog entries of `spec-pyforge-core` came first; `SPEC.md` is rendered by Story 117.5.
- 2026-11-11: fix pass after the third review of the mint. The cross-station keys left the Deps line here and in `epics.md` (marshal's Deps parser read them as marshal keys, some done and unrelated, some absent); they stay in Notes, and the entry above no longer says marshal's drain holds them.
