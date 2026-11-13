---
title: '121.6: The ledger check refuses a row that contradicts its Spec or the rules'
type: 'feature'
created: '2026-11-10'
status: 'done'
flag-exempt: detector-or-gate
difficulty: heavy
story: 121.6
spec: foundry-capability-ledger
surface:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cutover_ledger_check.py
  - src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/extract.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** fcl:CAP-1's written rules and fcl:CAP-2's `flip` form need a judge, and review found that a marker the generator does not recognise would silently keep a row at rebuild. A separate module, so the generator and the rules are each one reviewable change.

**Approach:** `rebuild-never-built`: a `rebuild` row whose Spec heading reads `(ready` and none of whose citing stories (the stories in that station's `epics.md` whose FR/AD or Parent line names the capability) reads `done` in that station's sprint-status-ledger.yaml (ruling 3; the second addendum settles the row: B-only when a live blocked or backlog Story carries it, else retire). Expiry form only (dates and Story keys are doctor's clock); `flip-expiry-lapsed` reads `pyforge.core.cutover_root.root_of_record()` and tests pass an explicit flags path. `retire-without-marker`: a `retire` row whose Spec heading has no retired marker (fnd:CAP-7's legacy form counts). `marker-contradicts-mode`: a retired marker on a row that is not `retire`. `unknown-marker`: a parenthesised status word (`minted`, `unbuilt`, `deleted`, `never built`, `retired` with no date) outside the pinned forms. Case ids are read from `case-list.md` with the first-column rule doctor uses.

Ledger key: `121-6-the-ledger-check-refuses-a-row-that-contradicts-its-spec-or-the-rules`. Type / Effort / Deps: feature / L / S-121.1.

### Living CAP citations

- **`spec-foundry-capability-ledger`** — fcl:CAP-1 (schema v1 and the written rules) and fcl:CAP-2 (the refusals and the expiry clock), amended 2026-11-10 and re-derived at mint.

## Boundaries & Constraints

**Always:**
- Dates and Story-key expiries are doctor's (spec-pyforge-doctor:CAP-95, doctor Story 56.2); this module judges the form.

**Never:**
- Never write the ledger.
- Never import another station.
- Never append a `Surface reconcile` line or stamp.

## Acceptance Criteria

- **AC1 — the rules' unit tests.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py -q -p no:cacheprovider
  ```
- **AC2 — every finding and warning code is named by a test.** Expected: prints 27 or more and [], exit 0.
  ```bash
  python3 -c "import re;s=open('src/shared/packages/pyforge-steward/src/pyforge/steward/cutover_ledger_check.py').read();t=open('src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py').read();codes=set();[codes.update(re.findall(r'\"([a-z]+(?:-[a-z]+)*)\"',s.split(k)[1].split(')')[0])) for k in ('FINDING_CODES','WARNING_CODES')];miss=sorted(c for c in codes if c not in t);print(len(codes),miss);raise SystemExit(0 if len(codes)>=27 and not miss else 1)"
  ```
- **AC3 — a flip expiry lapses only when the root of record is foundry.** Expected: exit 0, at least 2 tests selected.
  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py -q -p no:cacheprovider -k flip_expiry
  ```
- **AC4 — an unrecognised marker is a finding, a missing one a warning.** Expected: exit 0, at least 2 tests selected.
  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py -q -p no:cacheprovider -k 'unknown_marker or no_marker'
  ```
- **AC5 — package half, coverage, lint.** Expected: exit 0 (until Story 124.2 lands, steward's package half runs without test_station_tests_trigger_map.py, which reds on other units' new reads by design; 124.2 restores the full `pyforge-steward-test`).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta -q -m "not slow and not live_tree" -n auto --dist loadgroup -p no:cacheprovider --ignore=src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scope.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py --cov=pyforge.steward --cov-branch --cov-report=json:.steward/coverage/steward-unit.json && pixi run --frozen -e pyforge-steward pyforge-steward-coverage-gate && pixi run --frozen -e pyforge-guild lint-types
  ```
- **AC6 — a rebuild row nothing built is a finding.** Expected: exit 0, at least 2 tests selected (a `(ready` row whose only citing story is blocked fires; the same row with one done story is silent).
  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py -q -p no:cacheprovider -k rebuild_never_built
  ```

</intent-contract>

## Binding

Parent: `spec-foundry-capability-ledger` fcl:CAP-1, fcl:CAP-2

- Dream: `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the mint entry) and `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth*.
- Epic: Epic 121.
- Ledger key: `121-6-the-ledger-check-refuses-a-row-that-contradicts-its-spec-or-the-rules` (`backlog` at mint).
- Deps: S-121.1.
- Surface: `src/shared/packages/pyforge-steward/src/pyforge/steward/cutover_ledger_check.py`, `src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py`.
- Minted 2026-11-10 by the cutover-readiness mint (control-plane unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py -q -p no:cacheprovider` — expected: exit 0.

## Notes

- Cross-station: marshal:S-117.2 (`root_of_record()`) must land first; doctor:S-56.2 judges the expiry clock.

## Review findings (build, round 1, 2026-11-11)

An independent review failed the first build attempt. Each finding, with what this round did:

1. **major — AC2's oracle (this spec's AC2 and `plan.json` `stories[121.6].acceptance[1]`).** The regex `"([a-z]+(?:-[a-z]+)+)"` counts only hyphenated codes, so `unclassified` (one of the 24 finding codes fcl:CAP-1 and `modes.md` name) is never counted: the command prints `26 []` and exits 1. The code matches the written list exactly (24 finding codes, 3 warning codes) and the test module names all 27. The fault is in the oracle, not the build. *Action:* none in the code, and none here: the AC block and `plan.json` are the integrator's (spec owner's), outside this story's writable sections. The integrator changes `(?:-[a-z]+)+` to `(?:-[a-z]+)*` in both; the corrected command prints `27 []` and exits 0 (re-run this round). `unclassified` is not renamed (doctor's capability-ledger source uses the same word) and no 28th code is added to pad the count.
2. **minor — AC5 is red outside this story.** The coverage gate's depends-on reaches `test_station_tests_trigger_map.py` (the planned red window until steward Story 124.2), and `lint-types` reds on ruff-format of another in-flight story's file; the gate's other reds (`pyforge.steward.estate`, `pyforge.steward.session`) are files other stories touch. This story's legs are green: package-half pytest, branch coverage of `cutover_ledger_check.py`, steward ruff, format and mypy. *Action:* none here. Re-run this round, each leg under `--frozen`: the package-half pytest exits 0 (1868 passed) with `cutover_ledger_check.py` at 100% line and branch coverage; `pyforge-steward-coverage-gate` exits 1, through its depends-on's `test_station_tests_trigger_map.py` (5 failures, none naming this story's files) and, run directly, on `pyforge.steward.estate` (45.6%) and `pyforge.steward.session` (17.4%), which other stories touch; `lint-types` now exits 0. AC5 stays red until Story 124.2 and the owners of those two modules land.
3. **minor — `_judge_markers` reads a provenance parenthetical beside a pinned marker as no marker.** `modes.md` § *Marker tokens* says any other parenthesised status word on a heading line is `unknown-marker`; the check reads the generator's `marker()` (Story 121.1), where a pinned form anywhere on the line wins, so `(ready 2026-11-10) *(minted 2026-11-10)*` passes. *Not tightened here, and why:* the check and the generator read one extract by design (fcl:CAP-1); a check that called `unknown` what the generator reads as `ready` would refuse rows the generator wrote and still settle by the pinned marker. The plan reads it the lenient way too: mason Story 37.1 and warden Story 25.1 keep a mint parenthetical beside the pinned marker as provenance, and the story's Problem (an unrecognised marker silently keeping a row at `rebuild`) does not arise when a pinned marker decides the row. The written companion and the code still disagree, so the ruling is the `modes.md` owner's (spec-foundry-capability-ledger, through its memlog and a render): "a provenance parenthetical beside a pinned marker is not a marker". Recorded under *Planned deferral* below, to be ruled before Story 121.7 sweeps.
4. **minor — a governance capability reading `(ready` with a `rebuild` row always fires `rebuild-never-built`.** A governance Spec's station is `governance` (extract.md § Station rule), and no `_bmad-output/projects/governance/planning-artifacts/epics.md` exists, so its citing stories are always none and the row settles `retire`. This follows the written rule ("that station's `epics.md`", `modes.md` rule 7) and no live row triggers it today, but Story 121.7 gives the 30 governance CAPs rule 10 `rebuild`. *Not changed here:* which epics a governance row reads is a `modes.md` amendment (every station's `epics.md`, or governance capabilities never take `ready` with `rebuild`), not this story's to decide. Recorded under *Planned deferral* below, to be ruled before Story 121.7.
5. **minor — tests (`tests/unit/test_cutover_ledger_check.py`).** A mutant that removes "a `done` status wins among several ledger keys sharing one E-S prefix" survived, and the branch for a citing story whose station has no `sprint-status-ledger.yaml` was not covered. *Action:* two tests added — `test_rebuild_never_built_reads_done_among_several_keys_of_one_story` (two keys for 2.1, the first sorted one `blocked`, the other `done`: silent) and `test_rebuild_never_built_names_a_citing_story_when_the_station_has_no_sprint_ledger` (epics present, ledger absent: the message reads `2.1 (no ledger key)`). The first also carries an `epic-2` key (skipped as no story), and a third, `test_rebuild_never_built_judges_each_ready_row_of_one_station`, covers the per-station cache; the module is now at 100% line and branch coverage, and the done-wins mutant, re-run on a scratch copy, is killed by the first test.
6. **Observed this round (not the reviewer's) — AC1, AC3, AC4, AC6 and AC5's second and third legs run `pixi run` without `--frozen`.** While other stories' path-dependency metadata (atlas, mason, scribe) is ahead of `pixi.lock`, a non-frozen run re-locks it; running them as written did so once this round, and `pixi.lock` was put back to its `HEAD` content (no git write). Every result reported here is from the same command with `--frozen` added. The integrator adds `--frozen` to those commands with the AC2 fix.

## Planned deferral (written at build)

The station closer writes a ledger row for each; both need a ruling before steward Story 121.7 sweeps and regenerates the ledger to zero findings.

- **`modes.md` § Marker tokens vs the generator's pinned-form-wins reading.** The spec owner (spec-foundry-capability-ledger) rules whether a provenance parenthetical (`*(minted <date>)*`) beside a pinned marker is a marker. If it is, `_judge_markers` also scans the heading tail for an unknown status word when a pinned form wins, and the about 26 live headings of that shape are swept; if it is not, `modes.md` § Marker tokens says so. Finding 3 above.
- **Which `epics.md` a governance row's citing stories come from.** The spec owner rules either that a `station: governance` row reads every station's `epics.md` (a `modes.md` rule 7 amendment, then a change to `_Stations.citing`), or that a governance capability never takes `(ready` with a `rebuild` row. Finding 4 above.

## Review findings (build, round 2, 2026-11-11)

An independent review failed the round-1 build again. Each finding, with what this round did:

1. **major — AC2's oracle (this spec's § Acceptance Criteria AC2 block and `plan.json` `stories[121.6].acceptance[1]`, both the integrator's).** Round-1 finding 1, still open: the regex `"([a-z]+(?:-[a-z]+)+)"` never counts the unhyphenated `unclassified`, so the command prints `26 []` and exits 1 against a build that names all 27 written codes. *Action:* none in the code (renaming `unclassified` or padding a 28th code would contradict fcl:CAP-1 and `modes.md`) and none in the AC block, which is outside this story's writable sections. The integrator replaces `(?:-[a-z]+)+` with `(?:-[a-z]+)*` in both places; the corrected command prints `27 []` and exits 0 (re-run this round). AC2 as written stays red until then.
2. **minor — AC5 legs 2 and 3 (`pyforge-steward-coverage-gate` and its depends-on).** The reviewer saw leg 1 and `lint-types` exit 0 with `cutover_ledger_check.py` at 100% line and branch coverage; the gate reds on `pyforge.steward.estate` and `pyforge.steward.session` (other stories' modules) and its depends-on `pyforge-steward-test` reaches `test_station_tests_trigger_map.py` (the planned window until Story 124.2), none of which names this story's files. *Action:* none here; the owners of those modules and Story 124.2 close it. Re-run this round under `--frozen`: `lint-types` exits 0; the gate's depends-on fails only the 5 trigger-map tests and the gate itself (run by its command line) fails only `pyforge.steward.estate` (45.6%) and `pyforge.steward.session` (17.4%); `cutover_ledger_check.py` stays at 100% line and 188/188 branch coverage. Leg 1 now exits 1 for a reason item 7 names.
3. **minor — tests: three surviving mutants.** (a) `_LIVE_STORY = {"blocked"}` survived: no test asserted a `backlog`-only citing story settles as `B-only`. *Action:* added `test_rebuild_never_built_settles_b_only_when_a_backlog_story_carries_it` (only citing story `backlog`: the message reads `2.1 (backlog)` and `B-only (carried by 2.1)`). (b) `_text(row.get("pending_on"))` → `is not None` survived: no test used a blank question. *Action:* added `test_pending_without_question_when_the_question_is_blank` (`pending_on: ""` and `"  "`: `pending-without-question`, no `mode-pending` warning). (c) `found[0]` → `found[-1]` survived. *Not pinned, and why:* when several ledger keys of one story are all not `done`, which one the message names is the sprint ledger's file order, an accident of a stale slug rather than a rule `modes.md` writes; the finding code is unchanged either way, and the reviewer agrees it needs no action. Both new tests kill their mutants on a scratch copy (re-run this round).
4. **minor — `_judge_markers` vs `modes.md` § Marker tokens (a provenance parenthetical beside a pinned marker).** Round-1 finding 3, unchanged. *Action:* none in code; it stays under *Planned deferral* for the spec-foundry-capability-ledger owner to rule before Story 121.7.
5. **minor — a governance `rebuild` row reading `(ready` always fires `rebuild-never-built` (`citing: none`).** Round-1 finding 4, unchanged; no live governance row fires today (re-run read-only by the reviewer). *Action:* none in code; it stays under *Planned deferral*, to be ruled before Story 121.7.
6. **minor — AC1, AC3, AC4, AC6 and AC5 legs 2-3 run `pixi run` without `--frozen` (the integrator's).** Round-1 observation 6, still open. *Action:* every command this round ran with `--frozen` added and `git diff HEAD -- pixi.lock` stays empty; the integrator adds `--frozen` with the AC2 fix.
7. **Observed this round (not the reviewer's) — AC5 leg 1 exits 1 on an order-dependent test outside this story.** `tests/unit/test_deploy_nic_packs.py::test_run_nic_up_refuses_a_missing_pack_cli_before_nic_starts[off]` (steward Story 118.7, unchanged from `origin/main`) fails when it runs in a process where its `[on]` twin has not run first: run alone it fails (`deploy nic packs: refused — helm not on PATH`, because the first `read_boolean` in a process installs the flagd FILE provider over the test's in-memory one and records it in `pyforge.core.flags._PROVIDER_SOURCE`, so `preflight_pack_clis` reads the repository tree's ON), and it passes only after an earlier read in the same process has pinned that source, so the `[off]` fixture's in-memory provider stays current. This round's three new tests (1868 + 3 = 1871 collected) shift the xdist `loadgroup` split so `[off]` lands on a worker without `[on]` (worker `gw15`, reproduced serially from that worker's order). Leg 1 without this module's tests exits 0 (1764 passed); the full `pyforge-steward-test` split (leg 2's depends-on) does not trip it. *Action:* none here: the file is outside this story's `files_owned`. The fix belongs to the owner of `test_deploy_nic_packs.py` (steward Epic 118): the `[off]` case should switch the pack flag off the way `preflight_pack_clis` reads it (a flag tree through `PYFORGE_FLAGS_PATH`, or by patching `preflight_pack_clis`), not lean on test order.

## Integrator note (BUILD-3 gate, 2026-11-11)

Review rounds 1–3 found one blocker, and it was in the oracle, not the build. AC2's regex `(?:-[a-z]+)+` skipped the unhyphenated `unclassified` code. The integrator changed it to `(?:-[a-z]+)*` here and in `plan.json`. The corrected command prints `27 []` and exits 0. Every AC command now runs `pixi run --frozen`, so no AC re-locks `pixi.lock`. The build is unchanged.
