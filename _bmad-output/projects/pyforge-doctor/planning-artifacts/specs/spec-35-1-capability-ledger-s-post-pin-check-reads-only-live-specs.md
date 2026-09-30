---
title: "35.1: capability-ledger's post-PIN check reads only live Specs"
type: 'fix'
created: '2026-09-28'
status: 'done'
baseline_revision: '0df667a53da3a72a655aed96608b53c33182145d'
flag-exempt: detector-or-gate
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_ledger.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/extract.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the capability-ledger source (`sources/capability_ledger.py`, `capability-ledger-check`, part of
`detectors-ci`; Story 55.2, `fcl:CAP-2`) inventories only live Specs. `iter_live_specs` extracts CAPs from `SPEC.md` files
whose frontmatter `status` is in `_LIVE_STATUSES = {"ready", "in-progress"}` (line 36, applied at line 150), as steward's
`spec-foundry-capability-ledger/extract.md` contract says. `_gather`'s second post-PIN loop (lines ~339-353) reads no
status, though. It walks every `SPEC.md` added after the ledger's `source_sha` and warns
`post-PIN Spec without a ledger row --append` unless a row names the path or an extracted CAP lives in it. A non-live
Spec has no extracted CAP, so it always warns. It also has no extract to classify, so the warning can never be cleared.

Measured on `main` at `0c8c07e6fc`: `pixi run -e pyforge-guild capability-ledger-check` exits 0 with exactly eight WARNs,
all `kind: append`, all from that loop:

| Spec | `status` |
|---|---|
| `pyforge-doctor/…/spec-docs-shelf-alignment` | absorbed |
| `pyforge-herald/…/spec-design-sync-loop` | absorbed |
| `pyforge-marshal/…/spec-marshal-recall-in-the-loop` | draft |
| `pyforge-marshal/…/spec-marshal-run-watch` | absorbed |
| `pyforge-marshal/…/spec-token-economy-claude-session-path` | absorbed |
| `pyforge-steward/…/spec-self-hosted-bmad-marketplace` | absorbed |
| `pyforge-steward/…/spec-vocabulary-one-name-one-job` | absorbed |
| `pyforge-steward/…/spec-work-passports-dated-extracts` | absorbed |

All eight are noise. A warning nobody can clear teaches readers to skip the source, and it would bury the one that
matters: a live Spec added after the PIN with no row. The operator ruled on 2026-09-28 (night) to fix it (CAP-87).

**Approach:** in `_gather`'s post-PIN Spec loop, after the existing `endswith("/SPEC.md")` and `/planning-artifacts/specs/`
tests, read the added file's frontmatter with the module's own `_frontmatter` helper, the one `iter_live_specs` uses, and
`continue` when its `status` is not in `_LIVE_STATUSES`. Read `target / path`. If the file is gone from the working tree
(renamed or deleted after the PIN), treat it as not live and skip it, since the loop only ever reports an added path.
Change nothing else:

- the first loop's per-CAP `post-PIN unclassified --append` WARN;
- the HARD findings (an unclassified live CAP, `A-only` without an expiry, `verified-in-foundry` without a 54.1 case id);
- the finding's message, `kind: append` and status;
- `_LIVE_STATUSES` itself;
- the source's read-only posture. It writes no ledger row, and `docs/foundry/capability-ledger.yaml` is not edited to
  silence anything.

Ledger key: `35-1-capability-ledger-s-post-pin-check-reads-only-live-specs`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-doctor` CAP-87 (FR-20); CAP-36 (the detector sees what it claims to check); AD-2 (a WARN never changes the
  exit code).
- `fcl:CAP-2` (steward's `spec-foundry-capability-ledger`): its `--append` clause, which this narrows to the extract's own
  scope. The Spec itself is not edited.

## Acceptance Criteria

- Given a throwaway repository with a PIN commit and a post-PIN `SPEC.md` reading `status: absorbed`, carrying a CAP heading and no ledger row When `gather` runs Then it reports no WARN and no FAIL for that Spec
- Given the same with `status: draft` When `gather` runs Then it reports no WARN and no FAIL for that Spec
- Given a post-PIN `SPEC.md` reading `status: ready` with no CAP heading and no ledger row When `gather` runs Then it reports exactly one WARN of `kind: append` naming its path, as today
- Given a post-PIN `status: ready` Spec with an unclassified CAP When `gather` runs Then the per-CAP `post-PIN unclassified --append` WARN is reported as today (`test_post_pin_spec_without_row_is_append` still passes)
- Given a post-PIN path that is no longer in the working tree When `gather` runs Then it raises nothing and reports nothing for that path
- Given the status test removed from the loop When the absorbed and draft tests run Then they fail (mutation)
- Given `main` after this story When `pixi run -e pyforge-guild capability-ledger-check` runs Then it exits 0 with no `post-PIN Spec without a ledger row` WARN
- Given the change When `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Read `status` with the helper `iter_live_specs` uses, so "live" means the same thing in both places.
- Keep fixtures in the existing shape: `_git`, `_write_spec`, `_write_ledger` and a PIN commit, as in
  `test_post_pin_spec_without_row_is_append`.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every Spec `spec-surface-check` names (`spec-pyforge-doctor` owns `sources/**`); stamp each scoped with
  `--spec`.

**Never:**
- Do not change `_LIVE_STATUSES`, the HARD checks, the per-CAP WARN, or the finding's message or kind.
- Do not write or edit `docs/foundry/capability-ledger.yaml` to make a finding go away.
- Do not import `pyforge.steward` or `pyforge.scribe` (the module's independence note).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`, and do not edit `spec-foundry-capability-ledger`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| absorbed fold | post-PIN, `status: absorbed`, no row | nothing | — |
| draft | post-PIN, `status: draft`, no row | nothing | — |
| shipped | post-PIN, `status: shipped`, no row | nothing (not inventoried) | — |
| no status | post-PIN, frontmatter without `status` | nothing (not live) | — |
| live, no CAP | post-PIN, `status: ready`, no CAP heading, no row | one WARN `kind: append` naming the path | — |
| live, CAP unclassified | post-PIN, `status: in-progress`, CAP-1, no row | the per-CAP `post-PIN unclassified --append` WARN | as today |
| live, row names the path | post-PIN, `status: ready`, a row with its `path` | nothing | as today |
| path gone | added after the PIN, since removed | nothing | no exception |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_ledger.py` -- the fix site. `_LIVE_STATUSES`
  (line 36) and `_frontmatter` (line 122) are the reuse points; `iter_live_specs` (line 144) applies the status test at
  line 150. `_gather`'s second post-PIN loop (lines 339-354) is the only edit: after the `endswith("/SPEC.md")` and
  `/planning-artifacts/specs/` tests, read `target / path`, skip on `FileNotFoundError` / `NotADirectoryError` (gone), skip when `_frontmatter(text).get("status")`
  is not in `_LIVE_STATUSES`. The first loop (per-CAP WARN, lines 310-337), the HARD checks (270-303) and
  `_added_after_pin` (222) are read-only for this story.
- `src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py` -- add the tests here. Reuse `_git` (211),
  `_write_spec` (68), `_write_ledger` (74) and `_FIXTURE_SPEC` (18, `status: ready`, CAP-9). The reference fixture is
  `test_post_pin_spec_without_row_is_append` (218): `git init`, commit `README.md` as the PIN, write the Spec and ledger
  with `source_sha=pin`, commit again.
- `python -m pyforge.doctor.sources capability-ledger` -- the `capability-ledger-check` task's command. Measured before the
  change in this worktree: exit 0, exactly eight `post-PIN Spec without a ledger row` WARNs, the eight paths in the table.
- `_added_after_pin` diffs `PIN..HEAD` (commits), while the fix reads the working tree. A path is "gone" when it was
  committed after the PIN and then deleted in the working tree without a commit. That is the fixture for the gone-path test.
- `gather` wraps `_gather` in `degrade_on_exception`, so an unguarded `FileNotFoundError` would surface as a degraded
  finding, not a raise. The gone-path test therefore asserts no non-OK finding at all, not only "no exception".
- Read-only: `docs/foundry/capability-ledger.yaml`, `spec-foundry-capability-ledger`, `sprint-status-ledger.yaml`, every
  `SPEC.md`.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_ledger.py` -- in `_gather`'s post-PIN Spec loop, skip a path whose file is gone or whose frontmatter `status` is not in `_LIVE_STATUSES` -- a non-live Spec has no extract, so its warning could never be cleared
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py` -- add a pinned-repo helper and tests: non-live statuses (absorbed, draft, shipped, none) with a CAP heading and no row report nothing; a `ready` Spec with no CAP heading reports exactly one `kind: append` WARN naming its path; a path removed from the working tree reports nothing and degrades nothing; a live Spec behind a non-live one still warns; a path that exists but is not readable degrades instead of being skipped -- pins the loop's new contract
- [x] Mutation check (not committed): remove the status test and confirm the absorbed and draft tests fail -- proves the tests bind the fix (measured: all four non-live cases fail)

**Acceptance Criteria:**
- Given the intent-contract's eight acceptance criteria, when the unit tests and `capability-ledger-check` run, then each holds and `pyforge-doctor-test` passes

## Spec Change Log

## Source

Contract authored from `docs/dreams/pyforge-doctor.md`'s 2026-09-28 (night) Realization-log entry *Proposed:
capability-ledger's post-PIN check reads only live Specs* and `spec-pyforge-doctor` CAP-87, with the operator's ruling and
the direction entry in the Spec's `.memlog.md`.

## Binding

Parent Spec capability: `spec-pyforge-doctor` CAP-87 (FR-20).
Dream: `docs/dreams/pyforge-doctor.md` § Realization log → *2026-09-28 (night) — Proposed: capability-ledger's post-PIN
check reads only live Specs*.
Ledger key: `35-1-capability-ledger-s-post-pin-check-reads-only-live-specs`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: `flag-exempt: detector-or-gate` (a detector's own logic; a flag-OFF detector would be a silent green).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild capability-ledger-check` — expected: exit 0, and no `post-PIN Spec without a ledger row`
  WARN on `main`.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new findings.

## Review Triage Log

### 2026-09-29 — Review pass
- verdicts: 18 findings — high 0, medium 1, low 12, false 5, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind Hunter: `except OSError` skips any unreadable Spec, not only a gone one — the intent says a *gone* path is skipped. Normal `specs/*/SPEC.md` paths already degrade earlier (`iter_live_specs` reads them unguarded: measured IsADirectoryError -> one degraded WARN), so only an off-glob nested path was silently skipped (measured: `ok`). Fixed: the guard is now `except FileNotFoundError, NotADirectoryError`; test `test_post_pin_spec_present_but_unreadable_degrades_not_skips` added, and the widened-guard mutant fails it. The Code Map and Tasks wording said "unreadable" and now says "gone".
  - `[low]` `[reject]` Blind Hunter: the file is read before the `classified_paths` / extracted checks — at most a few dozen post-PIN Specs are read, and no result changes; the intent puts the read right after the two path tests.
  - `[low]` `[reject]` Blind Hunter: whole-file read for a frontmatter test, and no shared `_is_live` helper — negligible I/O, and a helper for two call sites is speculative; "live means the same" holds because both sites use `_frontmatter` + `_LIVE_STATUSES`.
  - `[low]` `[reject]` Blind Hunter: quoted status, trailing comment and BOM are untested — a quoted status is a false claim (measured: `_frontmatter` parses `'ready'` and `"in-progress"` as live); a trailing comment or BOM would equally hide a Spec from `iter_live_specs`, and none of the 171 `SPEC.md` files uses either (statuses: absorbed 153, ready 14, archived 3, draft 1). A fix would add parsing to a shared helper.
  - `[false]` `[reject]` Blind Hunter: no mutation proof for the gone-path guard and no after-state evidence — removing the guard fails `test_post_pin_spec_gone_from_working_tree_reports_nothing` (measured); the after-state is recorded under `## Auto Run Result`.
  - `[false]` `[reject]` Blind Hunter: surface reconcile deferred to the operator, so `spec-surface-check` is "likely red" — measured: `spec-surface-check` ok with 0 `drift-presumed`, `spec_surface_reconcile.py` exit 0. `spec-pyforge-doctor`'s memlog names both paths, and `spec-pyforge-core` carries a 35.1 entry. The run forbids `--write-baseline`.
  - `[low]` `[reject]` Blind Hunter: the narrowing of `fcl:CAP-2` is not recorded on `spec-foundry-capability-ledger` — the intent says that Spec is not edited and its Never list forbids it; the module docstring's `--append` line is already narrowed.
  - `[low]` `[patch]` Edge Case Hunter: same defect as the first Blind Hunter row (broad `OSError`) — fixed by the same change and test.
  - `[false]` `[reject]` Edge Case Hunter: a `target` below the git root makes `target / path` miss — unreachable: the CLI hard-codes `target = Path(".")` with no `--target` (`sources/__main__.py:246`), and the ledger path and glob already assume the repo root.
  - `[low]` `[reject]` Edge Case Hunter: an unparseable frontmatter is skipped, and it suggests a WARN when no status parses — same helper behaviour as the Blind Hunter status-shape row; a WARN contradicts the intent's I/O row "no status -> nothing".
  - `[low]` `[patch]` Edge Case Hunter: no test puts a live Spec behind a non-live one, so a `continue` -> `break` slip would pass — that is the outcome the intent exists to protect. Added `test_post_pin_non_live_spec_does_not_mask_a_live_one`; the `break` mutant fails it.
  - `[low]` `[patch]` Edge Case Hunter: no fixture for absent or unterminated frontmatter or a non-ENOENT read error — the read-error half is covered by the first patch's test (same guard, grouped with it); absent and unterminated frontmatter return `{}` in `_frontmatter`, the same path as the no-status row, so a fixture would add nothing.
  - `[low]` `[reject]` Edge Case Hunter: the intent's "the warning can never be cleared" ignores that a ledger row naming the path clears it — a claim about the intent-contract, which is read-only, and code behaviour is unaffected.
  - Verification Gap layer: no findings (it read the tests and ran them, 18 passed at that point).
  - `[false]` `[reject]` Intent Alignment: the loop's path scope (`/planning-artifacts/specs/` + `/SPEC.md`) is wider than the inventory's `_SPEC_GLOB` — not a defect: a live off-glob Spec still warns as today, and the intent says change nothing else.
  - `[low]` `[patch]` Intent Alignment: "gone" is implemented as any `OSError` — same defect as the first Blind Hunter row, fixed with it.
  - `[low]` `[reject]` Intent Alignment: no committed test runs the CLI against the live tree (AC-7 is observed by running the task) — AC-7 is a property of `main` that moves with it, and the spec lists it as a manual check; measured: `capability-ledger` exit 0, "794 live CAP extract(s) match the ledger", 0 residual WARNs (8 before).
  - `[false]` `[reject]` Intent Alignment: status is read from the working tree while `_added_after_pin` diffs `PIN..HEAD` — the intent specifies `target / path`, and the gone-path fixture depends on it.
  - `[medium]` `[patch]` Intent Alignment: `scripts/.spec-surface-baseline.json` was modified — the implementation subagent had stamped `pyforge-doctor/spec-pyforge-doctor` and `pyforge-marshal/spec-pyforge-core` (the spec's Boundaries ask for scoped stamps). This run forbids `--write-baseline`, and the stamp also baked in unrelated drift (`docs/MAP.md`, `docs/how-to/ocp-cluster-bringup.md`, `docs/how-to/pixi-tasks.md`, `docs/map.yaml`, the 34.2 flag-gate test). Fixed: the file is restored to `baseline_revision` (HEAD's copy is byte-identical), and the surface guards pass on the memlog entries alone.

## Auto Run Result

Status: done

**Change.** `_gather`'s post-PIN Spec loop in `sources/capability_ledger.py` now skips a Spec that is gone from the working tree or whose frontmatter `status` is not in `_LIVE_STATUSES` (same `_frontmatter` + `_LIVE_STATUSES` test `iter_live_specs` uses). The per-CAP WARN, the HARD checks, the finding's message and kind, `_LIVE_STATUSES` and the ledger file are untouched. The module docstring's `--append` line now says "live (ready/in-progress)".

**Files changed.**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_ledger.py` -- the loop guard and the docstring line.
- `src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py` -- `_pinned_repo` and helpers, plus 7 new test functions (10 cases, counting the four parametrized non-live statuses; the file went from 10 to 20 tests): non-live statuses report nothing, a live Spec with no CAP warns once, the per-CAP WARN is kept, a row naming the path clears it, a gone path reports nothing, a live Spec behind a non-live one still warns, and a present-but-unreadable path degrades.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` -- surface-reconcile entry naming both paths.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md` -- a 35.1 reconcile entry, written by the implementation subagent because that Spec co-governs `capability_ledger.py` in the baseline. I read it: it is accurate. `spec-surface-check` named only `spec-pyforge-doctor`.
- This story spec.

**Review.** 18 findings: patches applied 3 entries (1 medium, 2 low), deferred 0, rejected 15 with reasons in the triage log. Follow-up review recommended: `false` (no high patched, one medium patched).

**Verification (exit codes read directly).**
- `pyforge-doctor-test` exit 0, 3015 passed, 1 skipped.
- `test_capability_ledger.py` 20 passed; `ruff check` and `ruff format --check` exit 0 on both files.
- Mutations, each restored afterwards: no status test -> the 4 non-live cases fail; no gone-path guard -> the gone-path test fails; `continue` -> `break` -> the live-behind-non-live test fails; guard widened to `OSError` -> the unreadable-path test fails.
- `capability-ledger` (the `capability-ledger-check` command) exit 0: "794 live CAP extract(s) match the ledger", no `post-PIN Spec without a ledger row` WARN; 8 before the change.
- `spec_surface_reconcile.py` exit 0; `spec-surface-check` ok, no drift.
- `detectors-ci` exit 1 on three findings that are not from this diff: `pixi_version_check` (`ModuleNotFoundError: pixi_version_registry`) and `ledger-direction` (marshal 74.1 landed-but-unpromoted) fail identically on a scratch checkout of `baseline_revision`; `bmad_estate_check` passes there but fails here only because this dispatch deployed the gitignored `.claude/skills/caveman` skill (the single skill-dir difference), and the diff touches no skills path. I did not re-run it with that skill removed.

**Residual risks.**
- The spec's Boundaries say to stamp each scoped with `--spec`; this run forbids `--write-baseline`. No baseline is stamped, so the operator stamps `pyforge-doctor/spec-pyforge-doctor` (and `pyforge-marshal/spec-pyforge-core`, if wanted) at landing, from a clean tree after `git add`.
- A trailing-comment or BOM `status` line would hide a Spec from both `iter_live_specs` and this loop; none exists in the 171 current `SPEC.md` files.
- `detectors-ci` is red at this tree, so the "no new findings against main" gate rests on the baseline comparison above.
