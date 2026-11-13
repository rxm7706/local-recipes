---
title: '122.3: Steward''s help and output cite today''s capability ids'
type: 'fix'
created: '2026-11-10'
status: 'done'
difficulty: medium
story: 122.3
spec: pyforge-steward
surface:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/suite_advance.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/fresh_clone.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/corridor.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/audit.py
  - src/shared/packages/pyforge-steward/tests/unit/test_upgrade_pin_fan_out.py
  - src/shared/packages/pyforge-steward/tests/unit/test_upgrade_prove_landed.py
  - src/shared/packages/pyforge-steward/tests/unit/test_upgrade_apply.py
  - src/shared/packages/pyforge-steward/tests/unit/test_upgrade_next_rehearsal.py
  - src/shared/packages/pyforge-steward/tests/unit/test_fresh_clone_class_path.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/install-class-playbook.md
  - src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/oracle-map.md
  - docs/reference/station-cheat-sheet.md
  - docs/map.yaml
context:
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
declared_low_risk: false
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-123.1, S-123.2, S-123.3).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** A defect in public output (MUST 5): help and runtime strings cite pre-fold capability ids that now name other capabilities.

**Approach:** String text only: re-key each constant through the Spec's provenance map, read from the SPEC headings, never typed; one `event` entry on the steward memlog lists the eight migrated modules and the map. `test_cap_citations.py` holds MODULE_FAMILIES as data and reads oracle-map.md's source-modules column (Story 123.1) as each module's allowed set; it is `live_tree`. Comments, docstrings and package data are Story 122.4's.

Ledger key: `122-3-steward-s-help-and-output-cite-today-s-capability-ids`. Type / Effort / Deps: fix / M / S-121.2, S-122.2, S-123.1, S-123.2, S-123.3.

### Living CAP citations

- **`spec-pyforge-steward` CAP-179** — help and output are public contract; the re-key reads the provenance map on each SPEC heading (`<- spec-<absorbed> CAP-old`).

## Boundaries & Constraints

**Always:**
- Keep each line count unchanged so no SKF `[SRC:]` reference moves.
- Re-key inside a family by the provenance map; the `rekey_pairs` guard catches a wrong sibling.

**Never:**
- Never touch `_HELP['cutover']` or `_add_cutover_subparsers` in cli.py (control-plane 121.2, which rewrites that function before this story runs).
- Never change behaviour or add a line.
- Never append a `Surface reconcile` line or run a stamp.

## Acceptance Criteria

- **AC1 — the citation test passes.** Expected: exit 0: every bare `CAP-n` in a non-docstring string constant of steward source is an id SPEC.md defines and is in the citing module's allowed set (the capabilities whose oracle-map.md row names that module); every qualified id names a live Spec or a prefix CHAIN-STANDARD lists; each `_HELP` string cites only capabilities contract.md gives that duty.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py -q
  ```
- **AC2 — the test can fire.** Expected: exit 0 with at least 4 tests selected (an undefined id, an id outside the module's allowed set, a help string citing a capability its duty's contract rows lack, a re-key pair the provenance map does not hold).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py -q -k fires
  ```
- **AC3 — every re-key follows the Spec's provenance map.** Expected: exit 0: for every line changed on origin/main...HEAD under the steward package where the cited ids differ, each (old, new) pair is `<- spec-<absorbed> CAP-old` on the heading of CAP-new in SPEC.md, for an absorbed Spec in the module's family list (a branch-diff guard, as the kit's others are; it skips loudly without origin/main).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py -q -k rekey_pairs
  ```
- **AC4 — no pre-fold phrase in a string constant.** Expected: exit 0; prints `0 []` (prints `39 [...]` and exits 1 on 2026-11-10: 15 cli.py help strings and the 24 constants listed in files_owned).
  ```bash
  python3 -c "import ast,re,glob,sys;R=re.compile(r'hub:CAP-|pre-flight \(CAP-1\)|pipeline-truth \(CAP-1|CAP-8/A[D]-10|install-class CAP-3|CAP-2/6/7|CAP-9: retire|CAP-4 report-only|CAP-5 post-apply|CAP-1: report upstream|CAP-2: advance|CAP-1 report-only|CAP-2 one-command|topology.*CAP-6\)|Story 9\.5, CAP-6|CAP-4 audit trail|CAP-4.s .who saw|class-path \(CAP-3\)|CAP-3 path is|dated-extracts CAP-4|CAP-1 whole-pipeline|Automated CAP-2 advance|CAP-3 (clear|incomplete)|deliberate apply \(CAP-2\)|## CAP-[378] |CAP-1 preflight consumed|CAP-5 prove-landed|CAP-5 verdict|for CAP-2 del');h=[]
  for f in sorted(glob.glob('src/shared/packages/pyforge-steward/src/pyforge/steward/**/*.py',recursive=True)):
   t=ast.parse(open(f).read());d={id(n.body[0].value) for n in ast.walk(t) if isinstance(n,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.body and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant)}
   h+=[f.rsplit('/',1)[1]+':'+str(n.lineno) for n in ast.walk(t) if isinstance(n,ast.Constant) and isinstance(n.value,str) and id(n) not in d and R.search(n.value)]
  print(len(h),h);sys.exit(bool(h))"
  ```
- **AC5 — help names today's ids.** Expected: exit 0; `upgrade` cites CAP-9..CAP-13, `suite` cites CAP-21 and CAP-22, `deploy` cites CAP-116 for static, `track` cites CAP-54, `guards` cites CAP-55.
  ```bash
  pixi run -q --frozen -e pyforge-guild pyforge steward --help
  ```
- **AC6 — the companion heading and its reader agree.** Expected: prints 1; exit 0.
  ```bash
  grep -c '## Fresh-clone class-path (CAP-29)' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/install-class-playbook.md && pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_fresh_clone_class_path.py -q
  ```
- **AC7 — no line is added or removed in an existing source or test file.** Expected: prints 0 (BASE is the `baseline_revision` in this story's spec frontmatter), so no SKF `[SRC:]` line reference moves.
  ```bash
  git diff --numstat "$BASE"..HEAD -- src/shared/packages/pyforge-steward/src/pyforge/steward src/shared/packages/pyforge-steward/tests/unit | awk '$1!=$2' | wc -l
  ```
- **AC8 — the cheat sheet is regenerated.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild python scripts/docs_station_cli.py --check && pixi run --frozen -e pyforge-guild docs-currency-check
  ```
- **AC9 — duty count unchanged.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_cli.py src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py -q
  ```
- **AC10 — package half.** Expected: exit 0 (until Story 124.2 lands, steward's package half runs without test_station_tests_trigger_map.py, which reds on other units' new reads by design; 124.2 restores the full `pyforge-steward-test`).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta -q -m "not slow and not live_tree" -n auto --dist loadgroup -p no:cacheprovider --ignore=src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scope.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py --cov=pyforge.steward --cov-branch --cov-report=json:.steward/coverage/steward-unit.json
  ```
- **AC11 — live-tree half.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```
- **AC12 — lint and types.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild lint-types
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-179 (help and output are public contract); CHAIN-STANDARD section 6

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 122.
- Ledger key: `122-3-steward-s-help-and-output-cite-today-s-capability-ids` (`backlog` at mint).
- Deps: S-121.2, S-122.2, S-123.1, S-123.2, S-123.3.
- Surface: `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` (the help strings of `_HELP['deploy']`, `_HELP['upgrade']`, `_HELP['suite']`, `_HELP['track']` and `_HELP['guards']`; in `_add_deploy_subparsers`, the `perimeter` subparser's help and `static_help`; in `_add_provision_subparsers`, `--prove-class-path`'s help; in `_add_upgrade_subparsers`, `bmad-core`'s `--apply` and `--no-shims` helps and the `pin-fan-out`, `prove-landed` and `verify` subparsers' helps; in `_add_suite_subparsers`, the `pipeline-truth` and `advance` subparsers' helps; anchored by key, parser and argument, never by line, because Story 121.2 rewrites `_add_cutover_subparsers` first and every later line moves; not `_HELP['cutover']` or `_add_cutover_subparsers`, which are control-plane 121.2's), `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py, deploy.py, suite.py, suite_advance.py, fresh_clone.py, corridor.py and dashboard/audit.py` (string constants only), `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_pin_fan_out.py, test_upgrade_prove_landed.py, test_upgrade_apply.py, test_upgrade_next_rehearsal.py and test_fresh_clone_class_path.py` (the asserted strings only), `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/install-class-playbook.md` (the heading `## Fresh-clone class-path (CAP-3) — recorded proof`), `src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py` (new), `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/oracle-map.md` (one row for the new test), `docs/reference/station-cheat-sheet.md` (regenerated), `docs/map.yaml` (the `stamp:` mapping of reference/station-cheat-sheet.md only).
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py -q` — expected: exit 0: every bare `CAP-n` in a non-docstring string constant of steward source is an id SPEC.md defines and is in the citing module's allowed set (the capabilities whose oracle-map.md row names that module); every qualified id names a live Spec or a prefix CHAIN-STANDARD lists; each `_HELP` string cites only capabilities contract.md gives that duty.
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py -q -k fires` — expected: exit 0 with at least 4 tests selected (an undefined id, an id outside the module's allowed set, a help string citing a capability its duty's contract rows lack, a re-key pair the provenance map does not hold).

## Notes

- Cross-station: the one `docs-station-cli` regeneration of docs/reference/station-cheat-sheet.md runs here after every story that changes a station's `--help` text: control-plane 121.2 (same station), herald:S-50.3, mason:S-37.3 and atlas:S-48.3; herald:S-51.2 is ordered before it by the integrator.
- The suite help line keeps 'all 13 suite packages': it is true.
- `$BASE` in the acceptance criteria is the `baseline_revision` the build writes into this spec's frontmatter when it starts (the commit it starts from); it is not set at mint.
- Until Story 124.2 lands, steward's trigger-map test may red on other units' new reads (a planned red window); this story is judged by its own test modules and by steward's package half without that module.
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (steward and host: Story 122.5) and doctor Story 58.4 runs every scoped stamp once, after the last edit.
