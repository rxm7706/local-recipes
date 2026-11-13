---
title: '57.3: Doctor''s chain closes: the oracle meta-test, the live ledger proof, the new capabilities shipped'
type: 'chore'
created: '2026-11-10'
status: 'done'
story: 57-3-doctor-s-chain-closes-the-oracle-meta-test-the-live-ledger-proof-the-new-capabilities-shipped
spec: spec-pyforge-doctor
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a test module, a Spec re-derive and planning records, no runtime path (spec-55-4's form; roster list)
surface:
  - 'src/shared/packages/pyforge-doctor/tests/meta/test_package_half_is_the_oracle.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_cutover_ledger.py'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/test-architecture.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md'
  - 'docs/dreams/pyforge-doctor.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/briefs/brief-pyforge-doctor-2026-07-25/brief.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/implementation-readiness-report-2026-11-*.md'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-58.1, S-58.2).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** Closes the doctor chain of this change after every doctor story: decision D1's oracle half, the live proof that the two ledger detectors and the writer lock read the regenerated ledger and roster, the markers of CAP-94 to CAP-100, `scripts/detectors.py` onto the Spec surface, the new deferred rows and the doctor test-architecture page.

**Approach:** Oracle rule: every Source module and DISPATCH gather exercised by an unmarked module, every check code named by one, and no unmarked module skipping on A's tree. Re-derive: one memlog entry (markers, companions, surface; the `Surface reconcile 2026-11-10` line naming every changed path from `git diff --name-only origin/main...HEAD`), then the anchored script render. The allowlist line for scripts/detectors.py is removed by Story 58.4, by content.

Ledger key: `57-3-doctor-s-chain-closes-the-oracle-meta-test-the-live-ledger-proof-the-new-capabilities-shipped`.
Type / Effort / Deps: chore / M / S-56.1, S-56.2, S-56.3, S-56.4, S-56.5, S-57.1, S-57.2, S-58.1, S-58.2; cross-station: herald:S-51.2, marshal:S-117.2, steward:S-121.4, steward:S-121.7, steward:S-122.3, steward:S-124.1, steward:S-124.5.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-94..CAP-100** — `(ready 2026-11-10)` becomes `(shipped <date>)` once Stories 56.1 to 58.2 are done.
- **`spec-pyforge-doctor` CAP-97** — the package-local half is the rebuild oracle (this story's meta-test).

## Boundaries & Constraints

**Always:**
- Write the closer's `Surface reconcile` event from `git diff --name-only origin/main...HEAD` for doctor's Spec (with Story 58.4 for docs/map.yaml, docs/MAP.md and docs/how-to/** edits after this story).
- Record the final live-module list in this spec for steward-station's one re-key edit (with Stories 56.2, 58.1 and 58.2).

**Never:**
- Never stamp here (Story 58.4 runs every scoped stamp once, last); never hand-edit the ledger.
- Never hand-edit `SPEC.md` (memlog, then `bmad-spec` or the anchored script render with both self-validate passes logged); never append a `Surface reconcile` line to another Spec's memlog or run `spec_surface_check.py --write-baseline` (Story 58.4 stamps every Spec once, last on the branch); never add new behaviour or a kill switch beyond this story's capability text (operator ruling of 2026-11-10: each gap is a deferred-work row).

## Acceptance Criteria

- **AC1 — The package-local half covers every source, and reads nothing outside the package to say so.** Expected: exit 0: every sources/*.py module is imported, and every DISPATCH gather called, by a test module without the live_tree mark (AST over src and tests only); every check-code literal defined under src appears in such a module or in the test's pinned gap list, each entry with a reason; the gap list only shrinks.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/meta/test_package_half_is_the_oracle.py -q -m 'not live_tree' -p no:cacheprovider
  ```

- **AC2 — The module runs in the package half (no live_tree mark in any form).** Expected: exit 1 (no match).

  ```bash
  git grep -n live_tree -- src/shared/packages/pyforge-doctor/tests/meta/test_package_half_is_the_oracle.py
  ```

- **AC3 — The oracle check fires.** Expected: exit 0; a synthetic gather no unmarked module calls, and a synthetic check code no unmarked module names, are each reported.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/meta/test_package_half_is_the_oracle.py -q -p no:cacheprovider -k fires
  ```

- **AC4 — Integration (after control-plane Stories 121.3 and 121.4 and core-kit Story 117.2): the detectors read the regenerated ledger and the roster.** Expected: exit 0: frozen-path-changed reports `0 frozen of N rows` with N equal to len(capabilities) of docs/foundry/capability-ledger.yaml; capability-ledger reports no FAIL; writer-lock reports this checkout is the writer; extract_caps returns the heading column of every row of the heading-case table in spec-foundry-capability-ledger/extract.md.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_live_cutover_ledger.py -q -m live_tree -p no:cacheprovider
  ```

- **AC5 — No capability of this change still reads ready.** Expected: exit 1 (no match).

  ```bash
  git grep -nE '^- \*\*CAP-(9[4-9]|100) .*\(ready ' -- _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  ```

- **AC6 — The companion and the registry are on the Spec (the allowlist line goes in 58.4).** Expected: exit 0.

  ```bash
  git grep -n '  - contract.md' -- _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md && git grep -n '  - scripts/detectors.py' -- _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  ```

- **AC7 — The live half of tests/unit is exactly the live modules, the speed budget and the fleet_scan tests.** Expected: prints nothing (exit 1).

  ```bash
  git grep -l 'mark.live_tree' -- src/shared/packages/pyforge-doctor/tests/unit | grep -vE '/test_live_|/test_check_speed_budget\.py$|/test_fleet_scan_'
  ```

- **AC8 — Skip discipline across the suite: unmarked modules hold only the three environment skips.** Expected: exit 0; prints test_checks_env_hygiene.py (non-UTF-8 filesystem), test_sources_factory.py (unprivileged user) and test_sources_registry.py (`_needs_checkout`, the baseline's one), total 3.

  ```bash
  python3 -c "import re,glob,sys;fs=glob.glob('src/shared/packages/pyforge-doctor/tests/**/test_*.py',recursive=True);u=[(f,len(re.findall(r'pytest\.skip\(|pytest\.mark\.skipif|pytest\.importorskip',open(f,encoding='utf-8').read()))) for f in fs if not re.search(r'(?m)^pytestmark\s*=(?:[^\n]*live_tree|\s*\[[^\]]*live_tree)',open(f,encoding='utf-8').read())];h=sorted((f.rsplit('/',1)[1],c) for f,c in u if c);print(h,sum(c for _,c in h));sys.exit(0 if sum(c for _,c in h)==3 else 1)"
  ```

- **AC9 — Doctor's test-architecture page names every story.** Expected: exit 0.

  ```bash
  python _bmad/scripts/bmad_tea_playwright.py --project pyforge-doctor --check
  ```

- **AC10 — The deferred rows of this change are written and open.** Expected: prints 9.

  ```bash
  grep -c '^### DW-doctor-cutover-2026-11-10-' _bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md
  ```

- **AC11 — The doctor story statuses agree with the ledger.** Expected: exit 0; every `**Status:**` line of doctor's `epics.md` matches its key in `sprint-status-ledger.yaml` (the meta-test's live-tree case; `story-status-check` is a different, repo-wide question, did a `done` feed key land, and stays in the push checks below).

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/meta/test_epics_status_tracks_the_ledger.py -q -m live_tree -p no:cacheprovider
  ```

- **AC12 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-57-3-*.md)"
  ```

- **AC13 — Lint, types and the doctor suite halves stay green.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild lint-types && pixi run --frozen -e pyforge-doctor pyforge-doctor-test && pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test && pixi run --frozen -e pyforge-doctor pyforge-doctor-coverage-gate
  ```

- **AC14 — no unreconciled drift row names pyforge-doctor/spec-pyforge-doctor (the closer's memlog names every changed path; doctor 58.4 stamps).** Expected: prints 0, exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources spec-surface --json > "$TMPDIR/ss.json"; python3 -c "import json,sys;d=json.load(open(sys.argv[1]));rows=d if isinstance(d,list) else (d.get('findings') or d.get('rows') or []);n=[r for r in rows if r.get('check') in ('drift','drift-presumed') and sys.argv[2] in json.dumps(r)];print(len(n));sys.exit(1 if n else 0)" "$TMPDIR/ss.json" pyforge-doctor/spec-pyforge-doctor
  ```

- **AC15 — doctor's readiness gate is fresh.** Expected: lists one file or more.

  ```bash
  ls _bmad-output/projects/pyforge-doctor/planning-artifacts/implementation-readiness-report-2026-1*.md
  ```

- **AC16 — doctor's chain is current: no feeds finding and no shelf finding, read from the exit code.** Expected: exit 0 (1 is a finding, 2 could not run; never through a pipe).

  ```bash
  pixi run --frozen -e pyforge-guild chain-currency-sweep-check -- --project pyforge-doctor
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-94, CAP-95, CAP-96, CAP-97, CAP-98, CAP-99, CAP-100 (markers to shipped); Spec frontmatter (companions, surface); FR-28 ← CAP-97.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-10 (the cutover readiness audit) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § *Realization log*.
- Epic: Epic 57, minted with this story.
- Ledger key: `57-3-doctor-s-chain-closes-the-oracle-meta-test-the-live-ledger-proof-the-new-capabilities-shipped` (`blocked`: a forward dependency on S-58.1 and S-58.2; unblocked only with operator confirmation once both are `done`).
- Deps: S-56.1, S-56.2, S-56.3, S-56.4, S-56.5, S-57.1, S-57.2, S-58.1, S-58.2; cross-station: herald:S-51.2, marshal:S-117.2, steward:S-121.4, steward:S-121.7, steward:S-122.3, steward:S-124.1, steward:S-124.5.
- Surface: `marshal-policy.toml` `[epic_surfaces]."57"`.
- Minted 2026-11-10 in the one chain commit of the integration branch `cutover-readiness-2026-11-10`, before any doctor story builds.

## Notes

- Closing story of the doctor chain; the PR bar and every spec-surface stamp belong to Story 58.4, which runs after it.
- `test_live_cutover_ledger.py` hands the repository root to three gathers, so steward's ROOT_HANDOFF_INPUTS must declare it (globs: docs/foundry/capability-ledger.yaml, docs/governance/guild-roster.json, src/platform/config/flags.json, the planning Spec glob, spec-foundry-capability-ledger/extract.md). The two steward tests `test_root_handoffs_are_declared_exactly` and `test_the_handoff_floor` are expected red from Story 56.2 until steward-station's re-key edit.
- New DW rows DW-doctor-cutover-2026-11-10-1 to -9 (the plan's deferred list: A-tree path literals; the Pages URL constant; bare CAP ids in comments; dated success clauses; no conformance lane; duplicate bmad_drift bodies; no Epic 52; inputs a B-laid tree lacks; no cap-duplicate-id finding). DW-doctor-egm-2026-11-05-2 (no detector checks the markers) stays open; this story appends one evidence line naming steward-station's request (Story 122.1) and the marker grammar ruled 2026-11-10.
- PRD, spine and epics take one dated reconciliation line and an `updated:` bump if chain-currency-sweep asks; the Dream takes a closing realization-log line. Run `python _bmad/scripts/bmad_tea_playwright.py --project pyforge-doctor` (never `--all`).
- Doctor's package manifest is not touched in this PR, so no retro is due.
- Cross-station deps: herald:S-51.2, marshal:S-117.2, steward:S-121.4, steward:S-121.7, steward:S-122.3, steward:S-124.1, steward:S-124.5.
- Rulings of 2026-11-10 applied (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, the second addendum, 'Accept all, run mint'): a source that measured nothing reads `unmeasured`, a warning the merge bar does not fail on; `doctor flags kill-switch` stays Doctor's one actuator; doctor's closed one-time campaigns retire; the marker grammar is CHAIN-STANDARD section 4 as steward Story 120.3 amends it (`(retired <date>[: <reason>])` and semicolon qualifiers, no `(unbuilt)` token); the operator flips `pyforge.cutover_root` by hand once the Launch slice is proven, and nothing flips it automatically.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Live-half module (written at build)

The final list for steward-station's one re-key edit (steward Story 124.2, with Stories 56.2's, 58.1's and 58.2's lists): this story adds one `test_live_` module under `src/shared/packages/pyforge-doctor/tests/unit/`, with `pytestmark = pytest.mark.live_tree`; it finds the repository root inside a module-scoped fixture, never at import. The oracle meta-test `tests/meta/test_package_half_is_the_oracle.py` carries no marker and reads only this package (`src/`, `tests/`, `pyproject.toml`), so it needs no declaration.

| Live module | Tests | What it reads |
|---|---|---|
| `test_live_cutover_ledger.py` | 4 | root hand-off to `frozen_path.gather`, `capability_ledger.gather` and `writer_lock.gather`; explicit reads of `docs/foundry/capability-ledger.yaml` and `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/extract.md` |

Inputs the three hand-offs read, for `ROOT_HANDOFF_INPUTS` (`doctor_live`): `docs/foundry/capability-ledger.yaml` (all three read it or its rows: frozen-path-changed and capability-ledger directly); `docs/governance/guild-roster.json` (writer-lock's `roots.this` and the `chain-write-off-the-writer` globs); `src/platform/config/flags.json` and `src/platform/config/flag-overlays.json` (writer-lock reads both at the merge base through `git show`; capability-ledger reads the root of record through `pyforge.core.cutover_root` for `flip` expiries); the planning Spec globs `_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md` and `docs/governance/spec-*/SPEC.md` (capability-ledger's live extract); `_bmad-output/projects/*/planning-artifacts/sprint-status-ledger.yaml` (capability-ledger's Story-expiry clock); `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md` (capability-ledger's case ids); `spec-foundry-capability-ledger/extract.md` (this module's heading-forms read). Every planning path sits under `_bmad-output/projects/*/planning-artifacts/**`; both gathers that diff against `refs/remotes/origin/main` (frozen-path-changed, writer-lock) read git history too.

## Build notes (written at build)

- **Shipped date.** CAP-94..CAP-100 read `(shipped 2026-11-12)`: the day every success clause of the seven held on the branch (CAP-95's names the ledger steward Story 121.7 regenerated, built 2026-11-12; CAP-97's names this story's meta-test). Each success command was run on 2026-11-12 and exited 0; the Spec's memlog quotes each result.
- **One set of check codes.** The oracle reads the check codes through `tests/meta/test_public_contract.py`'s `_code_facts` (imported, not copied), so the oracle and contract.md § Check codes count the same 232 codes. It counts a code as named when an unmarked module holds it as a string literal or references the source constant or enum member that holds it (`atlas._CHECK_ADOPTION_STAGE`, `HygieneFindingKind.DEAD_TEST_SCAFFOLDING`). The judge itself is left out of the half it judges, because its gap list spells every gap code.
- **The gap list.** 23 codes, each with the reason measured on 2026-11-12 from a run of the package half that recorded every `Finding` it constructs: 16 are produced by package-half tests that assert the status, the evidence or `models.is_gather_failure` and never the code; 5 (`chain-audit-*`) are named only in the live half, because the chain-layers audit runs `scripts/fleet_scan.py` from the checkout (Story 58.1), and no package-local test produces them; 2 (`ledger-untracked`, `station-unevaluable`) no package-local test reaches. `_GAP_CEILING` is 23 and an entry an unmarked module comes to name fails the suite, so the list only shrinks.
- **The tree marker's name is read, not written.** AC2 forbids the marker's name anywhere in the oracle module, so the module reads it from the package's `pyproject.toml` (the one declared marker whose description says it reads the repository outside its own package).
- **AC4's heading column.** extract.md's § Heading forms table (steward Story 120.2's file) has a Form and an Example column and no heading column. The live test reads each row's Example code span, computes the expected heading from it by that section's normalisation rule (a regex of its own, independent of `extract_caps`), and requires `extract_caps` to return exactly that heading; the one example written with the placeholder `CAP-n` (`- **CAP-n** — title`) is read with a number. An explicit expected-heading column in extract.md would make the fixture literal; that is steward's file to change.
- **AC2 and git grep.** `git grep` searches tracked files only, so AC2 run verbatim exits 1 on the untracked module whatever it holds until the wave gate commits it. The build also ran `git grep --untracked -n live_tree -- <the module>`, which reads the untracked file: exit 1, no match.
- **Chain currency.** `chain-currency-sweep-check --project pyforge-doctor` asked only for the brief (research newer than brief) and a fresh gate (the 2026-08-10 report past its 90-day shelf). The PRD, the spine and epics.md are not re-stamped: the Spec and brief lead the PRD by two days, inside the sweep's grace, and the check exits 0.
- **The station closer's rows.** Besides the nine `DW-doctor-cutover-2026-11-10-*` rows (AC10), the ledger gains the rows the planned deferrals of Stories 56.4, 56.5 and 58.1 asked the station closer to write: `DW-doctor-56-4-1`, `DW-doctor-56-5-1` and `DW-doctor-58-1-1`, all open.

## Spec Change Log

- 2026-11-10: minted from the station Dream's 2026-11-10 entry (the cutover readiness audit) and the operator's rulings of 2026-11-10.
- 2026-11-10: status `blocked` (the branch's one forward-dependency policy: Deps name S-58.1 and S-58.2 of Epic 58); AC11 keeps its title and runs the check that compares doctor's `epics.md` Status lines with the ledger (`tests/meta/test_epics_status_tracks_the_ledger.py -m live_tree`; `story-status-check` judges feed `done` keys against landing evidence, repo-wide, and stays a push check), chain currency staying with AC16.
