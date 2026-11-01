---
title: "50.2: fr-baseline.json grows only through its script"
type: 'fix'
created: '2026-11-01'
status: 'done'
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

Status: in-review (built in-PR on `egm-audit-2026-11`, 2026-11-01; nothing committed, staged or stamped by the build).

**What changed**

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py` — `_base_fr_baseline` reads
  `docs/governance/fr-baseline.json` at `merge-base(HEAD, refs/remotes/origin/main)` through `cli_bridge.run_git`
  (`rev-parse --verify --quiet refs/remotes/origin/main^{commit}`, `merge-base`, `show <sha>:<path>`; `ORIGIN_MAIN`
  from `refs.py`, never a fetch) and returns the cause when it cannot: the target is not a checkout top (no
  `<target>/.git`), no `refs/remotes/origin/main`, no merge-base, the file absent at the base, or not a JSON object
  there. `_fr_baseline_growth(base, head)` is the one definition of growth (a `projects` id or `findings` key per
  station present at head and absent at base; a removal is never growth). `_gather_fr_without_cap` appends one
  `fr-baseline-grown` FAIL (evidence `station`, `kind`, `key`, `merge_base`) for each grown key the file's `forced`
  list does not name, and drops that key from the hiding sets first, so the finding it would have hidden still
  fires; an unread base is one `fr-baseline-base-unread` WARN (evidence `baseline`, `base`, `cause`) and the arrows
  are judged as before. `record_fr_additions(previous, data, head)` (new, public, pure) writes a
  `{station, kind, key, head}` record for each key `data` adds over the file the script read and drops a record
  whose key `data` no longer holds; `prune_fr_baseline` drops such a record too (it is listed in `removed`);
  `snapshot_fr_baseline` carries `forced`. An `owners` row admits nothing. `_FR_BASELINE_COMMENT` gains three lines
  naming `forced`; the module docstring names both codes and the git read.
- `scripts/fr_baseline.py` — `--project` prints the `_print_delta` ADD/REMOVE lines and exits 1 on any addition
  without `--force` (file untouched); every write (`--project`, `--snapshot-findings`, a forced `--snapshot` over an
  existing file) calls `record_fr_additions` and prints `FORCED <station> <kind> <key> @ <head>` per record. The
  docstring states the record and the refusal.
- `docs/governance/fr-baseline.json` — `$comment` resynced to `_FR_BASELINE_COMMENT` (three `forced` lines); no
  `projects` id or `findings` key added or removed, no `forced` list.
- `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md` — § 12 *One writer* names the guard
  (`fr-baseline-grown`, the `forced` record, the merge-base read, `fr-baseline-base-unread`, `--project`'s refusal);
  *Enforced, not asserted* lists both codes beside the others (AC9).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py` — git fixtures under
  `tmp_path` (`refs/remotes/origin/main` by `update-ref`, a `topic` branch, the leaky-`GIT_*` scrub of
  `test_sources_ledger.py`). New: `test_hand_added_baseline_keys_fail_and_hide_nothing` (AC1, committed and
  uncommitted edits), `test_a_key_the_script_forced_is_admitted_and_an_owners_row_is_not` (AC2, through the script's
  `--project --force` and `--snapshot-findings --force`), `test_a_removed_key_and_an_unchanged_file_are_silent`
  (AC3), `test_an_unread_base_is_one_warn_and_the_arrows_are_judged_as_before[no-origin-main | no-merge-base |
  absent-at-base | not-a-checkout]` (AC4), `test_cli_project_prints_the_delta_and_refuses_growth_without_force`
  (AC5), `test_record_and_prune_keep_one_record_per_present_key`; the `--snapshot-findings --force` test asserts the
  record, and the re-snapshot test asserts `forced` is carried.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain.py` —
  `test_fr_pre_rule_population_is_never_a_finding` counted every finding (`(f,) = …`); it now counts the
  `fr-baseline-base-unread` WARN its non-git fixture yields beside the OK row (AC7).
- Memlogs (via `uv run _bmad/scripts/memlog.py`): `spec-pyforge-doctor` one surface-reconcile event naming every path
  above and one `(decision)` amending CAP-92's success (AC10); `docs/governance/spec-one-chain-per-station/.memlog.md`
  one event naming the § 12 change (AC9).

**Commands run (exit codes read from `$?`, never through a pipe)**

- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py -q` — 0 (54 passed).
- `… pytest …/test_sources_one_chain_fr_arrows.py …/test_sources_one_chain.py -q` — 0 (74 passed before the
  `no-merge-base` case was added; the module alone 54 passed after).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 0 (1213 passed).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test` — 0 (2727 passed; speed budget 4 passed).
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/meta/test_cli_bridge_sole_subprocess.py -q` — 0 (11 passed).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-coverage-gate` — 0, but it measures committed touched modules
  only ("no pyforge station packages touched" on an uncommitted tree); merged unit + live JSON give `one_chain.py`
  98.9% line coverage (742/750).
- `ruff check` and `ruff format --check` (pyforge-guild's ruff, run from `src/shared/packages/pyforge-doctor/`, its
  `[tool.ruff]`) on `one_chain.py` and the two test files — 0 and 0. `mypy -p pyforge.doctor` from the package dir
  (its `[tool.mypy]`, the `lint-types` mypy argv) — 0 (50 source files). The full `lint-types` was not run.
- `pixi run --frozen -e pyforge-guild fr-without-cap-check` — 0; no `fr-baseline-grown`, no
  `fr-baseline-base-unread` on this checkout (merge-base `03a7aff5d9`), OK row "547 enforced of 644" (AC8, local).
- AC6 mutations, each on a scratch copy of the package and script (never the worktree), against the test module:
  base comparison removed → `test_hand_added_baseline_keys_fail_and_hide_nothing` (and the AC2 owners leg) fail;
  forced record ignored → `test_a_key_the_script_forced_is_admitted_and_an_owners_row_is_not` fails; WARN turned
  into FAIL → the four `test_an_unread_base_is_one_warn…` cases fail; `--project` growth admitted without
  `--force` → `test_cli_project_prints_the_delta_and_refuses_growth_without_force` fails. The copy was restored and
  diffed identical after each (the two live-tree tests fail on the scratch copy in every run, the copy having no
  PRDs).
- `pixi run --frozen -e pyforge-guild spec-surface-check` — 0 (read-only; nothing stamped).

**Left for the session owner (not this build's to do)**

- AC11: `spec-pyforge-core`'s co-governor reconcile event for the three doctor package paths, then the scoped stamps
  (`spec-pyforge-doctor`, `spec-pyforge-core`) from a clean tree after `git add`. `scripts/fr_baseline.py` and
  `docs/governance/**` are allowlisted in `scripts/spec_surface_allowlist.txt`, so AC9's "stamped scoped" has no
  Spec surface to stamp for `spec-one-chain-per-station`.
- The pre-push gates: `detectors-ci` and `PYFORGE_PREFLIGHT_SCOPE=full pr-preflight` (AC8's `detectors-ci` leg).
- `pixi.toml`'s `fr-without-cap-check` description (and its generated row in `docs/how-to/pixi-tasks.md`) still
  lists the codes without `fr-baseline-grown` / `fr-baseline-base-unread`; left untouched because other agents edit
  `pixi.toml` in this worktree.

**Review follow-up 2026-11-01** (the review's advisory): `pixi.toml`'s `fr-without-cap-check` description, and
nothing else in `pixi.toml`, now names doctor Story 50.2, FAIL `fr-baseline-grown` (a `projects` id or `findings` key
added since the merge-base of HEAD and `refs/remotes/origin/main` that no `forced` record names), WARN
`fr-baseline-base-unread` (a merge-base copy that cannot be read) and `--project`'s refusal to ADD an id without
`--force`. `docs/how-to/pixi-tasks.md` was regenerated by `scripts/docs_pixi_tasks.py` (its `fr-without-cap-check`
row and header stamp only), never hand-edited: `--check` exited 1 before the regeneration and 0 after. Surface
reconcile on the `spec-pyforge-doctor` memlog; `pixi.toml`'s other governors are the session owner's.

## Spec Change Log

- 2026-11-01: minted `backlog` (in-PR) from the EGM audit's cluster DOC-CL-3 (finding DOC-M-D1) at the operator's
  acceptance of every recommendation, 2026-11-01; marshal Story 113.7's landing.
- 2026-11-01: built in-PR; status `in-review`. The script's record is a `forced` list of `{station, kind, key, head}`
  in `docs/governance/fr-baseline.json`; it is also written by the one-time first `--snapshot-findings` (that act
  adds keys without `--force`) and by a forced `--snapshot` over an existing file, and a record whose key is gone is
  dropped so it cannot admit a later hand re-add.
- 2026-11-01: `in-review` -> `done` — independent review passed (Review Triage Log); AC11's stamps and AC8's
  `detectors-ci` leg (red only on the fleet-wide chain-currency gate) stay the session owner's.

## Review Triage Log

- 2026-11-01 — reviewer: independent session (did not write this code; judged the diff against this spec, not the
  Auto Run Result). **Verdict: pass.**
  - Read: `git diff HEAD` of `one_chain.py`, `scripts/fr_baseline.py`, both test modules, `fr-baseline.json` (only
    `$comment` changed; no `projects` id or `findings` key added or removed), CHAIN-STANDARD § 12 and both memlogs;
    the callers of the gather (`sources/__main__.py`, `test_sources_dispatch.py`, `scripts/detectors.py`'s
    `fr-without-cap` row); `.github/workflows/detectors.yml` checks out with `fetch-depth: 0`, so CI has
    `refs/remotes/origin/main` and the guard fires there rather than warning.
  - AC1–AC7, AC9, AC10 hold in code and tests: growth is read against `merge-base(HEAD, refs/remotes/origin/main)`
    through `cli_bridge.run_git` by the full refname, no fetch; a grown key is dropped from the hiding sets first, so
    the finding it hid still FAILs; only a `forced` record admits, an `owners` row never; removal is silent; the four
    unread-base shapes are one WARN each with the arrows judged as before; `--project` prints its delta and exits 1 on
    an ADD without `--force`; every assertion counting the checks counts the new codes
    (`test_fr_pre_rule_population_is_never_a_finding`); the sole-subprocess meta-test passes; CHAIN-STANDARD § 12 and
    *Enforced, not asserted* name both codes; `docs/governance/**` is allowlisted, so AC9 has no stamp to take.
    Accepted deviation (Spec Change Log): the one-time first `--snapshot-findings` also writes `forced` records.
  - Commands (exit codes read from `$?`): `pytest …/test_sources_one_chain_fr_arrows.py …/test_sources_one_chain.py`
    0 (75 passed); `pyforge-doctor-test` 0 (1213); `pyforge-doctor-live-test` 0 (2728 + speed budget 4 passed);
    `pytest …/test_cli_bridge_sole_subprocess.py` 0 (11); `fr-without-cap-check` 0 (no `fr-baseline-grown`, no
    `fr-baseline-base-unread`; "547 enforced of 644"); `lint_types.py ruff` 1 for pyforge-doctor but only on
    `test_sources_pages_liveness.py` (Story 48.3's file), `ruff-format` 0, `mypy` 0; `spec-surface-check` 0.
  - AC6 mutations, each on a scratch mirror of the package and `scripts/fr_baseline.py` (`PYTHONPATH` to the
    mirror's `src`), restored each time: growth loop emptied → `test_hand_added_baseline_keys_fail_and_hide_nothing`
    and `test_a_key_the_script_forced_is_admitted_and_an_owners_row_is_not`; forced check removed → the latter;
    `fr-baseline-base-unread` as FAIL → the four `test_an_unread_base_is_one_warn…` cases (and five others);
    `--project` refusal disabled → `test_cli_project_prints_the_delta_and_refuses_growth_without_force`.
  - AC8's `detectors-ci` leg: `pixi run -e pyforge-guild detectors-ci` exits 1 today, solely on
    `chain_currency_sweep_check` (`chain-audit-checkpoint-staleness` on all eight stations, the fleet-wide currency
    gate the EGM audit's memlog appends trip); its `fr-without-cap` row passes. Not this story's defect; the session
    owner's reconcile sweep has to clear it before the push.
  - Failures: none.
  - Advisory (no AC; healed tissue): `pixi.toml`'s `fr-without-cap-check` description and its generated row at
    `docs/how-to/pixi-tasks.md:114` still list the codes without `fr-baseline-grown` / `fr-baseline-base-unread` and
    describe `--project` without its refusal; regenerate both when `pixi.toml` is free.
  - Left to the session owner (reserved by this workflow, not judged): AC11's `spec-pyforge-core` co-governor
    reconcile and the scoped stamps; the full `pr-preflight`.
- 2026-11-01 — reviewer: independent session, review follow-up for Stories 48.3 and 50.2 (did not write it; judged
  the diff against HEAD `f742908321` and against the code it describes, not the implementer's notes). **Verdict:
  pass.**
  - Read: `git diff HEAD` of `models.py`, `tests/scripts/test_fleet_picture_pages_liveness.py`, `pixi.toml`,
    `docs/how-to/pixi-tasks.md`, the `spec-pyforge-doctor` memlog and the 48.3 and 50.2 story specs. Each diff holds
    only the expected hunk: the `PAGES_LIVENESS` comment; the `_STALE` fixture comment (the message, the evidence and
    the six tests unchanged); the one `fr-without-cap-check` description line in `pixi.toml` (no dependency or other
    line); the generated page's `fr-without-cap-check` row and its header stamp; one memlog event plus its `updated:`
    key; one follow-up paragraph in each story spec.
  - (1) The new `models.py` text matches `sources/pages_liveness.py` (`pending = commit_date > last_modified`, WARN
    only when `waited > STALE_AFTER`, the OK row otherwise, `_unavailable` one WARN) and its module docstring.
    (2) The fixture label is accurate: Story 48.3's message starts "Pages input waited", and `fleet_picture.py:1323`
    only cuts the message at 110 characters. (3) The description matches `one_chain.py` (merge-base of `HEAD` and
    `refs/remotes/origin/main`, the `forced` list only `scripts/fr_baseline.py` writes, an `owners` row never
    admits, the unread base a WARN) and `fr_baseline.py`'s `--project` refusal without `--force`. The generated row
    is byte-identical to the new description. `docs_pixi_tasks.py` is the only script that reads task descriptions.
    The memlog event lists `pixi.toml`.
  - No behaviour change (comments, one task description and a regenerated page), so no new test is owed; the drift
    the page could carry is pinned by `docs_pixi_tasks.py --check`.
  - Commands (exit codes read from `$?` or a log file, never through a pipe): `pixi run --frozen -e pyforge-doctor
    pyforge-doctor-test` 0 (1213 passed); `pytest tests/scripts/test_fleet_picture_pages_liveness.py`
    (pyforge-guild) 0 (6 passed); `python scripts/docs_pixi_tasks.py --check` 0 ("current");
    `docs_environments.py --check` 0; ruff check and format on `models.py` with the doctor `[tool.ruff]` 0 / 0;
    `python -m pyforge.doctor.sources spec-surface` 0, with no finding on any of these paths.
  - Failures: none.
  - Advisory (not this change): ruff 0.17's defaults on `tests/scripts/test_fleet_picture_pages_liveness.py` exit 1
    for check (ten PIE807) and 1 for format. The HEAD copy fails both the same way, so this change added none.
    `tests/scripts/` has no `[tool.ruff]` and no CI lane lints it: ruff's defaults report 188 findings across the
    directory and would reformat 75 files there. Treat that as a separate effort, not this follow-up's.
