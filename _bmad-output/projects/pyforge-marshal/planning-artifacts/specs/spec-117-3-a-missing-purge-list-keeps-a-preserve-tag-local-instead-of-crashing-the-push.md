---
title: "117.3: A missing purge list keeps a preserve tag local instead of crashing the push"
type: 'fix'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: easy
story: '117.3'
spec: pyforge-marshal
surface:
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
  - src/shared/packages/pyforge-core/tests/unit/test_preserve_refs.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/engine_preserve.py
  - docs/governance/preserve-purge-list.json
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** An audit defect of 2026-11-10 (a hard-coded root with no guard): `push_preserve_ref` calls `load_purge_list` on `docs/governance/preserve-purge-list.json` unguarded (`preserve_refs.py:872`), and marshal's callers catch only `PreserveGitError` (`supervisor/engine_preserve.py:197-200`), so on a root without that file the path that preserves work dies with `FileNotFoundError`.

**Approach:** A fix under spec-pyforge-marshal:CAP-287 (FR-234); its clause is in the memlog of 2026-11-10 and Story 114.1 renders it. `push_preserve_ref` wraps only its `load_purge_list(plist_path)` call, catching `OSError` and `json.JSONDecodeError`, and returns `PushPreserveResult(refname, False, (finding,))` with a new `ContentGateReason` member (for example `PURGE_LIST_UNREADABLE`) before any network call. `load_purge_list` keeps raising for its direct callers. Test names carry `purge_list`. The red-first run on the module as it was is recorded in this spec's Verification.

Ledger key: `117-3-a-missing-purge-list-keeps-a-preserve-tag-local-instead-of-crashing-the-push`. Type / Effort / Deps: fix / S / —.

## Boundaries & Constraints

**Always:**
- A refused push leaves the tag local with a finding and sends nothing to `origin`.
- No `except` clause widens (AD-68).

**Never:**
- No new exception class (so Story 117.6 pins nothing new), no default path change, no environment variable.
- Never touch the other literals the audit names: `landing_evidence`'s recovery SHAs are inert history and `league_measure` belongs to spec-pyforge-steward:CAP-46.
- Never append a `Surface reconcile` line to any Spec's memlog and never run `spec_surface_check.py --write-baseline`: the governed paths go in this spec's `surface:`, Story 117.8 reconciles core and the testing charter, and doctor:S-58.4 stamps once.

## Acceptance Criteria

- **AC1 — New tests for a missing and an unparsable purge list.**

  ```bash
  pixi run --frozen -e pyforge-core python -c "import re,subprocess,sys; r=subprocess.run(['pytest','src/shared/packages/pyforge-core/tests/unit/test_preserve_refs.py','-q','-p','no:cacheprovider','-k','purge_list'],capture_output=True,text=True); m=re.search(r'(\d+) passed',r.stdout); print(r.returncode, m and m.group(1)); sys.exit(r.returncode or not m or int(m.group(1))<2)"
  ```

  Expected: exit 0, at least 2 passed: the push returns `pushed=False` with a finding whose reason names the purge list, the tag exists locally, nothing reaches the bare origin.

- **AC2 — Red first, on the module as it was.**

  ```bash
  ( D=$(mktemp -d) && cp -r src/shared/packages/pyforge-core/src "$D/src" && git show $(git merge-base origin/main HEAD):src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py > "$D/src/pyforge/core/preserve_refs.py" && pixi run --frozen -e pyforge-core env PYTHONPATH="$D/src" python -m pytest src/shared/packages/pyforge-core/tests/unit/test_preserve_refs.py -q -k purge_list -p no:cacheprovider; echo rc=$? )
  ```

  Expected: prints `rc=1`: the new tests fail on the old module with FileNotFoundError; the run is recorded in the story spec's Verification.

- **AC3 — The whole core suite still passes as wired.**

  ```bash
  pixi run --frozen -e pyforge-core pyforge-core-test
  ```

  Expected: exit 0.

- **AC4 — Callers still pass.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests -q -k preserve -p no:cacheprovider && pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit -q -k preserve -p no:cacheprovider
  ```

  Expected: exit 0.

- **AC5 — Sole grammar.**

  ```bash
  pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/meta/test_preserve_refs_sole_grammar.py -q -p no:cacheprovider
  ```

  Expected: exit 0.

- **AC6 — Lint and types.**

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-287 (amended 2026-11-10; FR-234); AD-81, AD-68. Governors of `preserve_refs.py`: spec-pyforge-core, spec-pyforge-marshal, spec-pyforge-unifying-strategy and, for preserve refs, spec-pyforge-steward:CAP-165; Story 117.8 reconciles the core and charter Specs, Story 116.5 marshal's.

- Epic: Epic 117 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 117.3: A missing purge list keeps a preserve tag local instead of crashing the push`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The shared floor says what it is: core and the testing kit before the cutover.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda (operator, "Accept all, run mint").

## Notes

- Deps: none; it cites marshal's existing CAP-287.
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (core and the testing charter: Story 117.8; marshal: Story 116.5; steward and the host: steward:S-122.5), and doctor:S-58.4 runs every scoped stamp once, after the last edit on the branch.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10, the shared-floor section) and the memlog entries of `spec-pyforge-marshal` (the CAP-287 clause) came first; `SPEC.md` is rendered by Story 114.1.
