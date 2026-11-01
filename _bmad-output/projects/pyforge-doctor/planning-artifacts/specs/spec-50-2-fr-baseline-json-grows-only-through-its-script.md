---
title: "50.2: fr-baseline.json grows only through its script"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-50-1-fr-without-cap-resolves-every-arrow-against-a-defined-capability-and-names-a-counted-run.md
  - docs/dreams/pyforge-doctor.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/governance/spec-one-chain-per-station/.memlog.md
  - docs/governance/fr-baseline.json
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli_bridge.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py
  - src/shared/packages/pyforge-doctor/tests/meta/test_cli_bridge_sole_subprocess.py
  - scripts/fr_baseline.py
---

<intent-contract>

## Intent

**Problem:** CAP-92 promises that `fr-without-cap` fails a requirement-arrow finding only when it is new against
`docs/governance/fr-baseline.json`, "whose `projects` map is the arrowless population and whose `findings` map only
shrinks". At `03a7aff5d9` the shrink-only rule is enforced only inside `scripts/fr_baseline.py`:

- `gather_fr_without_cap` (`src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py`) trusts every
  `projects` id and `findings` key it reads in the file and never compares the file with a base, so a hand-added key
  turns a new FAIL into an `fr-baselined` OK row and no check catches it.
- `scripts/fr_baseline.py --snapshot-findings` refuses growth unless `--force` (`scripts/fr_baseline.py:120-129`), but
  `--project` writes whatever it re-snapshots, with no delta printed and no refusal.
- The file's `owners` map is hand-maintained (its own `$comment` says so), so "an owner story names it" cannot be the
  escape.

The same class laundered a baseline in PR #1605. CAP-92 routes `rebuild`, so the foundry rebuilds the ratchet from
its text; the ratchet has to be enforced, not left to review. This is the EGM audit's accepted finding DOC-M-D1
(cluster DOC-CL-3), recorded in
`_bmad-output/projects/pyforge-doctor/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
1. **Read the base.** `fr-without-cap` resolves the merge-base of `HEAD` and `refs/remotes/origin/main` (the full
   refname) and reads `docs/governance/fr-baseline.json` at it, through `cli_bridge.run_git` (`merge-base`, then
   `show <sha>:docs/governance/fr-baseline.json`), the way `sources/ledger.py`'s ledger-regression check resolves
   its PR-shaped base. On `main` itself the merge-base is `HEAD` and nothing has grown.
2. **Fail growth.** Each `projects` id or `findings` key (per station) present at `HEAD` and absent at the base is
   one `fr-baseline-grown` FAIL naming the station and the key, unless `scripts/fr_baseline.py` recorded it as a
   forced addition (below). A removed key is never a finding: `--prune` is the routine verb.
3. **The script's record is the only escape.** `scripts/fr_baseline.py` records, in the file, each key it adds under
   `--force`: a reviewed `--snapshot-findings --force`, or a `--project --force` re-snapshot at a station's fold PR.
   The record names the key and the run's `HEAD`. `fr-without-cap` admits a grown key only when that record names
   it; an `owners` row never admits one.
4. **No base is a warning.** When the merge-base or the base read fails (no `refs/remotes/origin/main`, a shallow
   clone, the file absent at the base), `fr-without-cap` yields one `fr-baseline-base-unread` WARN naming the cause,
   never a FAIL, and judges the arrows as today.
5. **`--project` refuses growth.** `scripts/fr_baseline.py --project <slug>` prints each id it would add and remove,
   and refuses (exit 1) when it would add one, unless `--force`, matching `--snapshot-findings`.
6. **Name the guard and record the chain.** CHAIN-STANDARD § 12 names the guard; a memlog event on
   `spec-one-chain-per-station` records it; a decision on the station Spec's memlog amends CAP-92's success.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-92** (every requirement arrow resolves to a defined capability, and a counted run is
  named): its success already says the `findings` map only shrinks; this story enforces it at the detector. A fix,
  no new CAP.
- **`spec-one-chain-per-station` CAP-5** (as amended 2026-10-26; CHAIN-STANDARD § 12): the rule the detector
  enforces; § 12 gains the guard's name.
- **`spec-pyforge-doctor` AD-1, AD-5** and the full-refname rule: a library call, `run_git` the one subprocess site,
  `refs/remotes/origin/main` never a bare `main`.
- **No flag.** `type: fix` (`spec-feature-flag-governance` Q1).
- **Origin.** `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry; the
  operator's acceptance of every audit recommendation, 2026-11-01 (memlog decision at line 875).

## Acceptance Criteria

- **AC1 — Growth fails.** In a fixture git repository under `tmp_path` with a `refs/remotes/origin/main` ref, a
  `projects` id added by hand since the merge-base yields one `fr-baseline-grown` FAIL naming its station and id, and
  a `findings` key added by hand yields one naming its station and key; the finding it would have hidden is still a
  FAIL.
- **AC2 — The forced record admits.** A key `scripts/fr_baseline.py` added under `--force` (its record naming the
  key) yields no `fr-baseline-grown`; a key whose only cover is an `owners` row still FAILs.
- **AC3 — Shrinking is silent.** A key removed since the base yields no finding; an unchanged file yields none.
- **AC4 — No base, a warning.** With no `refs/remotes/origin/main`, or the file absent at the base, the detector
  yields one `fr-baseline-base-unread` WARN naming the cause, no `fr-baseline-grown`, and the arrow findings it
  yields today.
- **AC5 — `--project` refuses growth.** `scripts/fr_baseline.py --project <slug>` prints the ids it would add and
  remove and exits 1 when it would add one, without `--force`; with `--force` it writes them and records each as a
  forced addition. `--snapshot-findings --force` records its added keys the same way.
- **AC6 — Mutation.** Each change below fails a named test in
  `src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py`; restore each:
  - the base comparison removed (a hand-added key passes);
  - the forced record ignored (a forced key FAILs);
  - the no-base WARN turned into a FAIL;
  - `--project` growth admitted without `--force`.
- **AC7 — Counts and budgets.** Every assertion that counts `fr-without-cap`'s check codes counts the two new ones;
  the sole-subprocess meta-test
  (`src/shared/packages/pyforge-doctor/tests/meta/test_cli_bridge_sole_subprocess.py`) still names `cli_bridge` alone;
  `doctor check` stays inside its five-second CPU budget.
- **AC8 — Live tree green.** On the PR head `python -m pyforge.doctor.sources fr-without-cap` yields no
  `fr-baseline-grown` (the PR adds no baseline key) and `detectors-ci` exits 0.
- **AC9 — The standard names it.** CHAIN-STANDARD § 12
  (`docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md`) names `fr-baseline-grown` and
  `fr-baseline-base-unread` beside the codes it lists; one event on
  `docs/governance/spec-one-chain-per-station/.memlog.md`, appended with `_bmad/scripts/memlog.py`, names the change;
  that Spec is stamped scoped.
- **AC10 — The chain.** One `(decision)` line on
  `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`, appended with
  `_bmad/scripts/memlog.py`, amends CAP-92's success for the DOC-CL-1 re-derive: `fr-without-cap` enforces the
  ratchet against the merge-base, and a grown key passes only through the script's forced record. The DOC-M-D1 event
  is already on that memlog (line 882). `SPEC.md` is not hand-edited.
- **AC11 — Surface reconciled.** Each governed path this story changes is named in a reconcile event on every Spec
  `spec-surface-check` names for it (`spec-pyforge-doctor`; `spec-pyforge-core`, which co-governs station `src/`;
  `spec-one-chain-per-station` for the standard), then stamped scoped, one `--spec` each, from a clean tree after
  `git add`.

## Boundaries & Constraints

**Always:**
- Keep Epic 50's HARD boundaries: every check stays on `Source.FR_WITHOUT_CAP`; findings fail only when new against
  the baseline; the advisory score never changes the exit code; `--prune` only removes; no detector edits a PRD.
- Read the base through `cli_bridge.run_git` only (AD-5), with the full refname; read every verdict from the exit
  code, never through a pipe.

**Never:**
- Never admit a grown key because an `owners` row names a story: `owners` is edited by hand.
- Never fetch: a stale remote-tracking ref can only hide growth already on `main`, and the no-base case warns.
- Never hand-edit `SPEC.md`; never stamp a Spec this story's diff does not touch.

**Residual risk:**
- A hand edit that adds a key and forges the script's record for it passes the detector. The record makes the act
  visible in review as a forced addition; the reviewed `--force` is the ruled design (CAP-92).

## I/O & Edge-Case Matrix

| `fr-baseline.json` at `HEAD` against the merge-base | Finding |
|---|---|
| unchanged | none |
| a key removed | none |
| a `projects` id added by hand | `fr-baseline-grown` FAIL |
| a `findings` key added by hand | `fr-baseline-grown` FAIL |
| a key added by `--force`, recorded | none |
| a key added by hand, named only in `owners` | `fr-baseline-grown` FAIL |
| no `refs/remotes/origin/main` | `fr-baseline-base-unread` WARN |
| file absent at the base | `fr-baseline-base-unread` WARN |

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-doctor` CAP-92 (Story 50.1, `fr-without-cap` and its baseline). No CAP is minted,
  and `SPEC.md` changes only through the DOC-CL-1 re-derive.

Parent: spec-pyforge-doctor CAP-92

- Audit finding carried: DOC-M-D1 (cluster DOC-CL-3); residue file
  `_bmad-output/projects/pyforge-doctor/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Epic: Epic 50 (`done`; this story reopens it through the roll-up, Story 41.5). The audit's cluster drafted it as
  Story 56.3 under a new Epic 56; it is keyed into its done epic instead (operator rule 2026-10-04: a fix story goes
  into its done epic).
- Ledger key: `50-2-fr-baseline-json-grows-only-through-its-script`.
- Deps: none.
- Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py`, `scripts/fr_baseline.py`,
  `src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py`,
  `docs/governance/fr-baseline.json`, `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md`.
  `marshal-policy.toml` has no `[epic_surfaces]."50"` entry: a dispatched build declares one first (MRS-GATE-007);
  the in-PR hand build needs no change.
- Build mode: in-PR (built in the EGM audit landing PR, branch `egm-audit-2026-11`).
- Minted 2026-11-01 by marshal Story 113.7's landing.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py -q` — expected: pass (AC1–AC6).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test` — expected: pass (the test file is `live_tree`-marked, so this half runs it, with the speed-budget test alone; AC7).
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/meta/test_cli_bridge_sole_subprocess.py -q` — expected: pass (AC7).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-guild fr-without-cap-check` — expected: exit 0, no `fr-baseline-grown` (AC8).
- The four mutations of AC6 — expected: each fails its named test. Restore each.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog events and the scoped stamps (AC9, AC11).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (AC8).
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.

## Auto Run Result

Status: backlog

## Spec Change Log

- 2026-11-01: minted `backlog` (in-PR) from the EGM audit's cluster DOC-CL-3 (finding DOC-M-D1) at the operator's
  acceptance of every recommendation, 2026-11-01; marshal Story 113.7's landing.

## Review Triage Log

- (none yet)
