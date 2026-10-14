---
title: "100.1: A landing records which CI surfaces were paused when it merged"
type: 'feature'
created: '2026-10-14'
status: in-progress
baseline_revision: 63c7cbbff4a5cd1afb07b0f122c7f61a495fd95e
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.marshal.landing_ci_pauses
  provider: openfeature-file
  default: {production: off, staging: off, dev: on}
  scope: global
  fallback: "no steward read: the landing journal, the PR body and the finalize record carry no ci_pauses_at_merge, exactly as on main"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/ci-surfaces.yaml
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json
  - src/shared/packages/pyforge-steward/tests/unit/test_ci_status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/scribe_cli.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/journal.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_no_engine_or_scribe_internals_import.py
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a dispatch landing records its PR's check runs (`landing_checks`, Story 80.1) but never that a CI gate was
paused. With `PAUSE_PLATFORM_CONTAINER_BUILDS=true` since 2026-10-09, every platform-touching story landed with
`platform-ci.container` and `platform-ci.container-dbgpt` skipped (and `golden-path-promotion` with them, through
`needs:`); with `PAUSE_CONTAINER_BUILDS=true` since 2026-10-04, every station story landed without
`station-tests.guild-container`. Six workflows have been disabled by hand since 2026-08-24. The landing journal, the
PR body and the finalize record say nothing of any of it, so a reader sees a green merge and cannot tell a skipped
gate from a passed one. Steward Story 99.3 (merged 2026-10-13, `7ec2ea85f3`) now answers the question in one call.
Line numbers below are at `8d04520770`.

- **What steward answers.** `pyforge steward ci status --json` prints one envelope on stdout and exits 0:
  `{fetched_at, repo, rate_limit: {core_limit, core_remaining}, rows: [...]}`, frozen as
  `urn:local-recipes:pyforge-steward:ci-status-schema` (`data/ci-status-schema.json`, additive changes only). A row has
  `id`, `switch`, `declared_state`, `live_switch_value`, `verdict`, and optionally `paused_since`, `review_by`,
  `review_days_left`, `owner`, `last_green_run`, `detail`. Steward refuses with exit 3 and text on stderr when its flag
  `pyforge.steward.ci_pause_control` is off (the default), when `gh` is unauthenticated or at a 0/60 rate limit, or
  when the variable or workflow read fails. When only a run-list read fails, the duty returns `ok=False` and steward's
  `main` (`cli.py:1757`) prints the envelope to **stderr** and exits 1.
- **Why the verdict is not enough.** `_build_rows` (`ci.py:467`) ranks `drift`, then `stuck`, then `overdue` above
  the state verdict (`:514`-`:522`). A pause past its `review_by` (2026-11-01 for both live pauses) reads `overdue`,
  and a pause on a stuck workflow reads `stuck`. The envelope has no `switch_class`, and the four grandfathered opt-ins
  (`PLATFORM_CI_AIR_GAP_PARITY`, `PLATFORM_CI_GKE_PORTABILITY_SMOKE`, `PLATFORM_CI_OCP_PORTABILITY_SMOKE`,
  `PLATFORM_CI_PUSH_REGISTRY`) carry no `ENABLE_` prefix and run when their value is `true`. In
  `docs/governance/ci-surfaces.yaml` every enable row is declared `opt-in-off` (7 rows), every pause row `live`,
  `paused` or `paused-manually` (52 rows), and the one value row (`PLATFORM_CI_REGISTRY`) is `live` with a non-boolean
  value.
- **Where the landing is.** `dispatch_land.execute_dispatch_land` (`:1259`) opens or updates the PR with
  `_dispatch_pr_body` (`:105`) before the check wait, waits in `_wait_for_landing_checks` (`:1746`), records
  `data[LANDING_CHECKS_FIELD]` (`:1756`), merges with `forge.merge_pr` (`:1877`), heals and retries on a failed merge,
  then spawns `pyforge.marshal.dispatch_land_finalize` (`:2077`-`:2089`). The supervisor copies `landing_checks` into
  the dispatch-land outcome payload (`dispatch_supervisor/__main__.py:2124`-`:2126`), and so does `cli/dispatch.py`
  (`:3476`-`:3478`). Finalize writes one `dispatch-land-finalize-resync` journal entry (`__main__.py:1035`).

**Approach:**
- **The read.** With the flag on, once per landing, after `_wait_for_landing_checks` and before the first
  `forge.merge_pr` (a heal retry does not read again), call steward through a new `adapters/steward_cli.py`, the only
  module permitted to invoke the steward CLI. It follows `adapters/scribe_cli.py`'s discipline: probe `pyforge` on
  `PATH`, then the repo's `.pixi/envs/pyforge-steward/bin` and `.pixi/envs/pyforge-guild/bin`; run
  `pyforge steward ci status --json` through the injected `ProcessPort` with a timeout (a module constant); turn every
  failure into a reason and raise nothing.
- **The rule (pure, in `core/`).** From a parsed envelope, list each row whose `declared_state` is `paused-manually`,
  or whose `live_switch_value`, stripped and lower-cased, is `true` and whose `declared_state` is neither `opt-in-off`
  nor `retired`. Skip the synthetic `unregistered:<NAME>` and `unregistered-workflow:<file>` drift rows. Sort the ids.
  The record is `{"state": "read", "surfaces": [...], "fetched_at": <the envelope's fetched_at>}`, with an empty list
  written explicitly.
- **Unknown.** No binary, a timeout, any non-zero exit (3 or 1), or stdout that is not a JSON object carrying
  `fetched_at`, `repo`, `rate_limit` and a `rows` list gives `{"state": "unknown", "reason": "<cause, with the exit
  code and the first line of stderr, bounded>"}`. Marshal never parses stderr for rows.
- **Where it goes.** `core/journal.py` gains `CI_PAUSES_AT_MERGE_FIELD = "ci_pauses_at_merge"` beside
  `LANDING_CHECKS_FIELD`. `execute_dispatch_land` puts the record in `data`; the supervisor and `cli/dispatch.py` copy it
  into the outcome payload where they copy `landing_checks`. The key is absent when the flag is off or the landing never
  reached the merge step (ALREADY_LANDED, HELD_FOR_REVIEW, a refusal before the merge), as `landing_checks` is.
- **The PR body.** A pure renderer beside `_dispatch_pr_body` returns today's text plus one line:
  `CI paused at merge: <id>, <id>`, `CI paused at merge: none`, or `CI paused at merge: unknown (<reason>)`. It
  reaches GitHub through the existing `forge.update_pr` seam, after the read and before the merge. A `ForgeCommandError`
  there is one new registered finding code classified WARN, so `status_for` keeps the landing OK; the merge goes ahead.
- **The promotion record.** Finalize gains `--ci-pauses-at-merge <json>` (the `--landing-subject` precedent) and
  writes the same object, unchanged, into its `dispatch-land-finalize-resync` payload. An argument that is not valid
  JSON is recorded as `{"state": "unknown", "reason": "finalize could not parse the landing's record"}`, never dropped.
- **The flag.** `pyforge.marshal.landing_ci_pauses` joins `src/platform/config/flags.json` (`defaultVariant: off`,
  metadata owner `marshal`, story `100-1-a-landing-records-which-ci-surfaces-were-paused-when-it-merged`) and
  `flag-overlays.json` (dev `on`, staging `off`, production `off`). Read it as `verify_fix_loop_enabled` reads its flag
  (`dispatch_verify.py:1129`); an unreadable tree reads as off.

Ledger key: `100-1-a-landing-records-which-ci-surfaces-were-paused-when-it-merged`.
Type / Effort / Deps: feature / S / none (steward Story 99.3 is done).

### Living CAP citations

- **`spec-pyforge-marshal` CAP-292** (FR-239): this story builds all of it. It extends CAP-284 (the check wait, whose
  record it sits beside) and CAP-4 (a landing with a durable paper trail).
- **`pyforge-steward:CAP-166`** (steward Story 99.3): the read. Always cite it qualified; marshal has its own CAP-166.
- **AD-2 / AD-71:** steward is wrapped through its CLI; the CI estate stays steward's. **AD-4 / AD-20:** the rule and
  the renderer are pure; the subprocess is in the adapter. **AD-8:** "could not read" never becomes an empty list.
  **AD-9:** the supervisor still imports nothing from `cli/`; finalize stays a subprocess. **AD-15:** one registered
  code. **AD-40:** one more field in the landing's journal verdict, no new landing rule or policy key. **AD-41:**
  binds gating, and this read gates nothing. **AD-73:** `pyforge.core.landing_evidence` and the merge subject are
  untouched.
- **Flag:** `pyforge.marshal.landing_ci_pauses`, owner marshal (`spec-feature-flag-governance` Q1/Q3). Not exempt: it
  judges and gates nothing, and it changes what a landing writes.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, the 2026-10-12 (ci pauses at merge) and 2026-10-14 (ci
  pauses at merge, specced) entries; `docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md` § 4.4 and § 6; the
  operator's direction of 2026-10-13 (mint after 99.3) and rulings Q1–Q8 of 2026-10-12.

## Acceptance Criteria

- **AC1 — The list.** With the flag on and a fake process returning a recorded envelope that holds two `paused` rows
  with `live_switch_value: "true"`, one paused row past `review_by` (verdict `overdue`), one `paused-manually` row, one
  `opt-in-off` row whose value is `"true"`, one `value` row, `live` rows, and one `unregistered:PAUSE_FOO` drift row:
  the landing journal's `ci_pauses_at_merge` is `{"state": "read", "surfaces": [the four paused ids, sorted],
  "fetched_at": <the envelope's>}`. A unit test of the pure rule covers each row kind alone.
- **AC2 — Empty is written.** An envelope whose rows are all `live`, `opt-in-off` with no value, or `retired` gives
  `"surfaces": []`, present in the record, and the PR-body line `CI paused at merge: none`.
- **AC3 — Unknown is never empty.** Each of these journals `{"state": "unknown", "reason": ...}` with a reason naming
  its cause, and the landing still merges: no `pyforge` binary; a timeout; exit 3 with a refusal on stderr; exit 1
  with an envelope on stderr; exit 0 with stdout that is not JSON; exit 0 with a JSON object missing `rows`. The
  PR-body line reads `CI paused at merge: unknown (<reason>)`.
- **AC4 — The PR body.** The body passed to `forge.update_pr` before `forge.merge_pr` is today's text plus exactly one
  `CI paused at merge:` line naming the same ids as the journal, in the same order. With `update_pr` raising
  `ForgeCommandError`, the landing emits the new WARN-class code, merges, and returns `LANDED`.
- **AC5 — One read, at the merge.** The steward call happens once per landing, after the check wait: a landing whose
  check wait refuses makes no steward call; a heal retry after a failed first merge does not call again; ALREADY_LANDED
  and HELD_FOR_REVIEW write no key.
- **AC6 — Carried through.** The supervisor's dispatch-land outcome payload and `cli/dispatch.py`'s data carry the
  record unchanged; finalize, given `--ci-pauses-at-merge`, writes the identical object into its
  `dispatch-land-finalize-resync` payload; an unparseable argument is recorded as `unknown`.
- **AC7 — Both flag states.** One test file, `tests/unit/test_landing_ci_pauses.py`, runs the landing with
  `@flag_states("pyforge.marshal.landing_ci_pauses")` from `pyforge.testing_kit.flags`: on, AC1's record and PR line;
  off, no steward call, no `ci_pauses_at_merge` key in either record, and a PR body byte-identical to
  `_dispatch_pr_body`'s today.
- **AC8 — One reader.** A meta-test (the AST technique of `tests/meta/test_no_engine_or_scribe_internals_import.py`)
  fails when any module in `pyforge.marshal` imports `pyforge.steward`, and when any module other than
  `adapters/steward_cli.py` names the steward CLI in an argv.
- **AC9 — Mutation.** Each change below fails a named test: listing by `verdict == "paused"` alone (AC1's overdue row);
  dropping the explicit empty list (AC2); mapping a failed read to `[]` (AC3); a second steward call on the heal path
  (AC5); reading the flag as on when the tree is unreadable (AC7).

## Boundaries & Constraints

**Always:**
- Read steward only through `pyforge steward ci status --json`, through `adapters/steward_cli.py`, with a timeout.
- Write `unknown` with a reason whenever the envelope is not in hand; write the empty list when it is and nothing was
  paused.
- Keep the record one object under one key, the same object in the landing journal, the outcome payload and the
  finalize record.
- Reconcile every governed path on the memlogs of the Specs that govern it (`spec-pyforge-marshal`, and
  `spec-pyforge-core`, which co-governs station `src/`; the flagd tree's governors as `spec-surface-check` names
  them), then stamp scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never import `pyforge.steward`, and never read `gh variable list`, the Actions API or
  `docs/governance/ci-surfaces.yaml` from marshal: steward is the one reader of the pause state.
- Never refuse, delay or re-verdict a landing because of a pause or an unknown read; never wait on CI for it.
- Never parse stderr for rows, and never treat a partial read (exit 1) as complete.
- Never change `pyforge.core.landing_evidence`, the merge subject, `landing_rules` or any policy key; never edit
  steward.
- Never flip `pyforge.steward.ci_pause_control`; that is the operator's.

**Residual risk:**
- The master switch `PAUSE_ALL_CI` has no row in steward's envelope (the Spec's open question), so a landing under
  the master lists each surface's own switch only. The test fixture pins today's behaviour; when steward adds the
  master's value, a follow-up story lists every surface under it.
- With steward's flag off (its default), every landing records `unknown` with the flag-off refusal as its reason
  until the operator turns it on.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| Flag off | no steward call; no `ci_pauses_at_merge` key; PR body unchanged |
| Envelope, rows include `paused`, `overdue` pause, `paused-manually` | `{"state": "read", "surfaces": [sorted ids], "fetched_at": ...}` |
| `opt-in-off` row with `live_switch_value: "true"` | not listed (an opt-in that is on runs) |
| `value` row (`PLATFORM_CI_REGISTRY`, a URL) | not listed |
| `retired` row | not listed |
| `unregistered:PAUSE_FOO` drift row with value `true` | not listed (no workflow reads it) |
| `live_switch_value: "TRUE "` on a `live` row | listed (steward's own `_truthy`: strip, lower) |
| All rows live | `"surfaces": []`; line `CI paused at merge: none` |
| `PAUSE_ALL_CI=true`, no other switch | `"surfaces": []` (no master row; the residual risk above) |
| Steward exit 3 (flag off, rate limit, `gh` failure) | `unknown`, reason with exit 3 and stderr's first line |
| Steward exit 1, envelope on stderr | `unknown`, reason names a partial read |
| No `pyforge` binary, or a timeout | `unknown`, reason names it |
| Stdout not JSON, or JSON without `rows` | `unknown`, reason names it |
| `forge.update_pr` raises | WARN-class finding; merge proceeds; `LANDED` |
| Check wait refuses | no steward call; no key |
| First merge fails, heal retries | one steward call in total |
| Finalize `--ci-pauses-at-merge` not valid JSON | finalize record holds `unknown` |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-marshal` CAP-292 (FR-239), minted 2026-10-14. Reads `pyforge-steward:CAP-166`.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-12 (ci pauses at merge) and 2026-10-14 (ci
  pauses at merge, specced) entries.
- Epic: Epic 100 (new), minted with this story. `epic-100` and `epic-100-retrospective` are minted with it.
- Ledger key: `100-1-a-landing-records-which-ci-surfaces-were-paused-when-it-merged`.
- Ledger status at mint: `backlog`.
- Deps: none. Steward Story 99.3 (`pyforge steward ci status --json`) is done.
- Surface: `marshal-policy.toml` `[epic_surfaces]."100"` (added with this mint).
- Minted 2026-10-14 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC1–AC8's tests (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- Two-state flag coverage (`spec-feature-flag-governance` CAP-4): `src/shared/packages/pyforge-marshal/tests/unit/test_landing_ci_pauses.py` — `@flag_states("pyforge.marshal.landing_ci_pauses")` from `pyforge.testing_kit.flags` parametrizes on then off (AC7).
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_landing_ci_pauses.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python3 scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.
- The five mutations of AC9 — expected: each fails its named test. Restore each.
- Operator, after landing, with both flags on in the environment the landing runs in and `gh` authenticated: the next real dispatch landing's journal and PR body carry `ci_pauses_at_merge` and its line, naming `platform-ci.container`, `platform-ci.container-dbgpt`, `station-tests.guild-container` and the six `paused-manually` workflows while those pauses stand.

## Spec Change Log

- 2026-10-14: minted with CAP-292 / FR-239 and Epic 100 from the Dream entries of 2026-10-12 and 2026-10-14, after
  steward Story 99.3 landed. `type: feature`, flag `pyforge.marshal.landing_ci_pauses`. The record is one object, not
  the Dream's bare list (memlog decision of 2026-10-14), and a row is listed from its declared state and live switch,
  not its verdict.

## Review Triage Log

- No review has run yet.
