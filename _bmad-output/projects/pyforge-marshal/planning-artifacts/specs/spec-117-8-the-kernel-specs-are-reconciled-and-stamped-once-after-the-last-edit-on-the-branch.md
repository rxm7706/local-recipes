---
title: "117.8: The kernel Specs are reconciled and stamped once, after the last edit on the branch"
type: 'chore'
created: '2026-11-10'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: easy
story: '117.8'
spec: pyforge-core
surface:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/.memlog.md
  - scripts/spec_surface_check.py
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
  - .claude/memory/feedback/a-union-merge-of-a-memlog-keeps-both-sides-frontmatter-updat.md
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-118.1, S-118.2); it also waits on the Epic 115 and 117 stories its Deps name, and on the cross-station stories its Notes name, which only the integration branch's wave order sequences.
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** Review issue 4 of the 2026-11-10 design pass: `spec-pyforge-core`'s surface covers every station's `src/**` and `pixi.toml`, so a per-story reconcile is stale at the next edit and parallel writes collide. One integration step at the end of the branch writes the reconcile lines the core Spec and the testing charter owe, and flips the markers of the capabilities this PR builds (operator ruling of 2026-11-10: the markers flip to shipped inside the PR, at each station's closing story).

**Approach:** Runs last in the PR, after every story of every unit that edits a path on these two Specs' surfaces. Sequence, from a clean tree: (a) run `spec-surface-check` and read the drifted paths it names for spec-pyforge-core and spec-pyforge-testing-charter; (b) append one `(event) Surface reconcile 2026-11-10 (marshal Story 117.8, cutover-readiness integration): <path> (<story key>), ...` line per Spec with `uv run _bmad/scripts/memlog.py append`, naming every changed path no earlier line of this PR names and the story that moved it (from `git log --format=%s -- <path>` on the branch), with literal full paths; (c) append one `(change)` entry per Spec flipping spec-pyforge-core:CAP-7, spec-pyforge-core:CAP-8, spec-pyforge-core:CAP-12, spec-pyforge-core:CAP-13, spec-pyforge-core:CAP-14 and spec-pyforge-testing-charter:CAP-3, spec-pyforge-testing-charter:CAP-6, spec-pyforge-testing-charter:CAP-7 from `(ready 2026-11-10)` to `(shipped <integration date>)` once every story realizing them reads `done` on the branch, render each `SPEC.md` once through the anchored script and log both self-validate passes naming Story 117.8; (d) `git add`; (e) re-run `spec-surface-check` and read its exit code. Union merges keep main's lines first and one `updated:` frontmatter key.

Ledger key: `117-8-the-kernel-specs-are-reconciled-and-stamped-once-after-the-last-edit-on-the-branch`. Type / Effort / Deps: chore / S / S-115.1, S-115.2, S-115.3, S-115.4, S-117.1, S-117.2, S-117.3, S-117.4, S-117.5, S-117.6, S-117.7, S-118.1, S-118.2 (same-station keys, as in `epics.md`; the cross-station dependencies are in Notes).

## Boundaries & Constraints

**Always:**
- Each memlog keeps exactly one `updated:` frontmatter key after the union merges.
- The reconcile names paths from `git diff --name-only origin/main...HEAD` against each surface; the incoming co-governor lines of other units count as named.

**Never:**
- Never write `scripts/.spec-surface-baseline.json`: doctor:S-58.4 runs every scoped stamp once, after the last edit on the branch.
- Never append to spec-pyforge-marshal's or spec-pyforge-unifying-strategy's memlog: their closers are Story 116.5 and steward:S-122.5.
- Never hand-edit a `SPEC.md`.

## Acceptance Criteria

- **AC1 — One reconcile line per governor this story closes (core and the testing charter).**

  ```bash
  for m in _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/.memlog.md; do grep -c 'Surface reconcile 2026-11-10 (marshal Story 117.8' "$m"; done
  ```

  Expected: prints 1 twice (marshal's and the host's reconcile lines are 116.5's and 122.5's).

- **AC2 — Each memlog keeps one `updated:` key after the union merges.**

  ```bash
  python3 -c "import sys,pathlib; c=[pathlib.Path(p).read_text(encoding='utf-8').split('---')[1].count('\nupdated:') for p in sys.argv[1:]]; print(c); sys.exit(c!=[1]*len(c))" _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/.memlog.md _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md
  ```

  Expected: exit 0, prints `[1, 1, 1, 1]`.

- **AC3 — Core's and the kit's package halves read nothing outside, now that the split jobs exist.**

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q -p no:cacheprovider -k 'package_half_reads_nothing or root_handoffs_are_declared or derivation'
  ```

  Expected: exit 0, with `core` and `testing_kit` among the parametrized package halves (needs steward-station 124.1 and 124.2).

- **AC4 — Chain and ledger detectors.**

  ```bash
  pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild fr-without-cap-check && pixi run -e pyforge-guild capability-ledger-check && pixi run -e pyforge-guild story-status-check && pixi run -e pyforge-guild deferred-work-check
  ```

  Expected: exit 0 each.

- **AC5 — The markers flipped through the render (operator ruling of 2026-11-10: inside the PR).**

  ```bash
  grep -ci 'self-validate.*Story 117\.8' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/.memlog.md
  ```

  Expected: prints 2 for each file (Pass 1 and Pass 2 naming Story 117.8).

- **AC6 — no unreconciled drift row names pyforge-marshal/spec-pyforge-core (the closer's memlog names every changed path; doctor 58.4 stamps).**

  ```bash
  pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources spec-surface --json > "$TMPDIR/ss.json"; python3 -c "import json,sys;d=json.load(open(sys.argv[1]));rows=d if isinstance(d,list) else (d.get('findings') or d.get('rows') or []);n=[r for r in rows if r.get('check') in ('drift','drift-presumed') and sys.argv[2] in json.dumps(r)];print(len(n));sys.exit(1 if n else 0)" "$TMPDIR/ss.json" pyforge-marshal/spec-pyforge-core
  ```

  Expected: prints 0, exit 0.

- **AC7 — no unreconciled drift row names pyforge-marshal/spec-pyforge-testing-charter (the closer's memlog names every changed path; doctor 58.4 stamps).**

  ```bash
  pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources spec-surface --json > "$TMPDIR/ss.json"; python3 -c "import json,sys;d=json.load(open(sys.argv[1]));rows=d if isinstance(d,list) else (d.get('findings') or d.get('rows') or []);n=[r for r in rows if r.get('check') in ('drift','drift-presumed') and sys.argv[2] in json.dumps(r)];print(len(n));sys.exit(1 if n else 0)" "$TMPDIR/ss.json" pyforge-marshal/spec-pyforge-testing-charter
  ```

  Expected: prints 0, exit 0.

- **AC8 — Every capability of both Specs reads shipped once the flip renders (operator ruling of 2026-11-10).**

  ```bash
  python3 -c "import re,sys,pathlib; b='_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/'; m=lambda s: dict(re.findall(r'^- \*\*(CAP-\d+) — .*?\((shipped|ready|retired) \d{4}-\d{2}-\d{2}', pathlib.Path(b+s+'/SPEC.md').read_text(encoding='utf-8'), re.M)); c,k=m('spec-pyforge-core'),m('spec-pyforge-testing-charter'); bad=sorted(x for x,v in c.items() if v!='shipped')+sorted('kit:'+x for x,v in k.items() if v!='shipped'); print(len(c), len(k), bad); sys.exit(len(c)!=14 or len(k)!=7 or bool(bad))"
  ```

  Expected: exit 0, prints `14 7 []`.

</intent-contract>

## Binding

Parent: `spec-pyforge-core` (spec-pyforge-core:CAP-1..spec-pyforge-core:CAP-14) and `spec-pyforge-testing-charter` (spec-pyforge-testing-charter:CAP-1..spec-pyforge-testing-charter:CAP-7) (reconcile; the marker flip of spec-pyforge-core:CAP-7, spec-pyforge-core:CAP-8, spec-pyforge-core:CAP-12..spec-pyforge-core:CAP-14 and spec-pyforge-testing-charter:CAP-3, spec-pyforge-testing-charter:CAP-6, spec-pyforge-testing-charter:CAP-7); no AD.

- Epic: Epic 117 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 117.8: The kernel Specs are reconciled and stamped once, after the last edit on the branch`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The shared floor says what it is: core and the testing kit before the cutover.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda (operator, "Accept all, run mint").

## Notes

- Cross-station deps: warden:S-25.3, scribe:S-33.2, mason:S-37.3, mason:S-39.1, atlas:S-48.2, atlas:S-48.3, herald:S-50.3, herald:S-50.4, herald:S-52.2, doctor:S-56.1, doctor:S-56.2, doctor:S-56.3, doctor:S-56.4, doctor:S-56.5, steward:S-121.1, steward:S-121.2, steward:S-121.6, steward:S-121.7, steward:S-122.3, steward:S-122.4, steward:S-123.2, steward:S-123.3, steward:S-124.1, steward:S-124.3, steward:S-124.4; same-project: S-115.1..S-115.4, S-117.1..S-117.7, S-118.1, S-118.2. The cross-station deps are not in the `epics.md` Deps line, because marshal's Deps parser drops a station prefix and would read each as a marshal key; only the integration branch's wave order (plan.json) holds them.
- AC3 needs steward:S-124.1 and steward:S-124.2 (the split jobs); AC4's `capability-ledger-check` needs steward:S-121.7 (the regenerated ledger).
- No post-merge flip row: the operator ruled the flip inside the PR, so DW-marshal-117-8-1 is never written.
- Story 116.5 (marshal's closer) depends on this story.

## Spec Change Log

- 2026-11-10: minted at `blocked` (forward dependency: until every story its Deps name is done) by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10, the shared-floor section) and the memlog entries of `spec-pyforge-core` and `spec-pyforge-testing-charter` came first; both `SPEC.md` files are rendered first by Stories 117.5 and 118.2; this story renders each once more for the marker flip.
- 2026-11-11: fix pass after the third review of the mint. The cross-station keys left the Deps line here and in `epics.md` (marshal's Deps parser read them as marshal keys); they stay in Notes, held only by the integration branch's wave order.
