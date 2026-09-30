---
title: "35.1: capability-ledger's post-PIN check reads only live Specs"
type: 'fix'
created: '2026-09-28'
status: 'in-review'
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
  `/planning-artifacts/specs/` tests, read `target / path`, skip on `OSError`, skip when `_frontmatter(text).get("status")`
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
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_ledger.py` -- in `_gather`'s post-PIN Spec loop, skip a path whose file is unreadable or whose frontmatter `status` is not in `_LIVE_STATUSES` -- a non-live Spec has no extract, so its warning could never be cleared
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py` -- add a pinned-repo helper and tests: non-live statuses (absorbed, draft, shipped, none) with a CAP heading and no row report nothing; a `ready` Spec with no CAP heading reports exactly one `kind: append` WARN naming its path; a path removed from the working tree reports nothing and degrades nothing -- pins the loop's new contract
- [x] Mutation check (not committed): remove the status test and confirm the absorbed and draft tests fail -- proves the tests bind the fix

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
