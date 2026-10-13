---
title: '29.1: The range test server records each response before the client can read it'
type: 'fix'
created: '2026-10-13'
status: 'done'
baseline_revision: '0d5702f516'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/tests/integration/publish/test_emit_range.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the static-host Range proof can read its own request log before the server thread has written it, so a
one-request query fails its assertion with an empty log. Line numbers below are at `0d5702f516`.

- **What failed.** In a pre-push `pr-preflight` run on 2026-10-13 (worktree `local-recipes-wt-estate-refresh-cleanup-
  2026-10-13`), the `pyforge-atlas-test` lane went red on
  `tests/integration/publish/test_emit_range.py::test_count_star_reads_footer_only_over_range` (`:345`, assertion at
  `:356`): `assert (200 not in [] and 206 in [])`. The query had already returned the right count (`n == _N` passed on
  the line before). The same file passed alone and under `-n auto --dist loadgroup` (12 passed, three runs), and CI
  passed `atlas-test` on PR #2186 that hour.
- **Why.** `_RangeServer`'s handler (`:99-:129`) writes the body with `self.wfile.write(data)` and only then appends to
  `codes`, `ranges`, `range_spans` and `bytes_served`. The client can read the bytes, DuckDB can finish the query, and
  the test thread can assert while the server thread has not yet run the appends. The `count(*)` test makes exactly
  one Range request, so its log can be wholly empty; the other tests make several, so an earlier append is usually
  there.
- **Reproduced.** A scratch harness that holds the handler 0.5 s after each body write: the log reads `[]` right after
  the query and `[206]` one second later, every run.
- **Ruled out.** DuckDB 1.5.5's `enable_external_file_cache` (on by default) answering a reused port's URL from cache:
  three fresh connections, two on the same reused port, each issued their own Range request (`[206]`, 16,384 bytes).

**Approach:** record each response before writing any of it, in every branch, and prove it with a delayed write.

- 206 branch: append `codes`, `ranges`, `range_spans` and `bytes_served` before `send_response`; 200 branch: append
  `codes` and `bytes_served` first; 416 branch: append `codes` before `send_response`.
- The body write moves into one method, `_write_body`, which, when the server was built with `delay_after_write`, flushes
  and holds the handler thread after the client has its bytes — the window the old order lost the entry in.
- A new test, `test_the_server_records_a_response_before_the_client_can_read_it`, builds the server with
  `delay_after_write=0.5` and asserts the 206 is in the log as soon as the query returns. No sleep on the test side.

Ledger key: `29-1-the-range-test-server-records-each-response-before-the-client-can-read-it`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-16** (the read surface runs with no backend at all): Story 8.2 shipped this Range proof.
  A `fix`, so no CAP, no FR and no flag (`spec-feature-flag-governance` Q1).
- **AD-2** (host-agnostic static layout) and **AD-11** (gates are never weakened): no assertion is loosened and no
  skip, `xfail`, retry or sleep is added to an existing test.
- **Origin.** `docs/dreams/pyforge-atlas.md` Realization log, 2026-10-13 (range-test recorder race); the operator's ask
  in session, "Do this task here: Fix flaky atlas range-read test under xdist".

## Acceptance Criteria

- **AC1 — Record first.** In every branch of the handler (206, 200, 416) the log append precedes the first byte sent.
- **AC2 — Regression.** The new test passes; with the server's delay at 0.5 s it sees `206` in `codes` as soon as the
  query returns, and the log snapshotted at that instant equals the server's final log, so no response was recorded
  late however many GETs the client makes.
- **AC3 — Mutation.** Moving the 206 branch's appends back after `_write_body` makes the new test fail (`1 failed`).
- **AC4 — Nothing weakened.** Every existing test in the file keeps its body and assertions; `git diff` adds no
  `skip`, `xfail`, `rerun`, `flaky` or `sleep` to an existing test; only the test file changes.
- **AC5 — Suites.** `pixi run -e pyforge-atlas pyforge-atlas-test`, `kedro-test` and `kedro-catalog-check` pass.

## Boundaries & Constraints

- Test-only: `src/pyforge/atlas/publish/**` does not change.
- The delay seam defaults to 0 and is used by the new test only; no other test pays for it.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| a Range past EOF (`416`) | recorded, then sent (the existing clamp test still passes) |
| a non-Range client (`200`) | recorded, then sent; the whole-file test still sees one 200 |
| `delay_after_write=0` (every existing test) | behaviour as before, no flush or sleep |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-16 (a `fix`; no CAP minted).
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-13 (range-test recorder race) entry.
- Epic: Epic 29 (new), Story 29.1. `epic-29` and `epic-29-retrospective` are minted with it.
- Ledger key: `29-1-the-range-test-server-records-each-response-before-the-client-can-read-it`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."29"` (added with this mint).
- Minted and implemented 2026-10-13 in one session at the operator's ask, the Story 28.1 precedent; reviewed by an
  independent reviewer against this spec before landing (behavioural guideline 8).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/integration/publish/test_emit_range.py -q -p no:cacheprovider` — expected: 13 passed (AC2).
- AC3, the mutation, on a scratch copy placed beside the test and removed afterwards: move the 206 appends after `self._write_body(data)` and run `-k records_a_response_before` — expected: `1 failed`.
- AC4: `git diff origin/main...HEAD -- src/shared/packages/pyforge-atlas/tests/integration/publish/test_emit_range.py | grep -E '^\+.*(skip|xfail|rerun|flaky|sleep)'` — expected: only the delay seam's `time.sleep(recorder.delay_after_write)` inside `_write_body` (it defaults to 0; no existing test sets it); `git diff --name-only origin/main...HEAD -- src/` — expected: only the test file.
- `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` — expected: pass (AC5).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entry and the scoped stamp.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- 2026-10-13: minted with Epic 29 from the Dream entry of that date; implemented the same session (the 28.1
  precedent). The first hypothesis (DuckDB's external file cache) was tested and ruled out before the fix.

## Auto Run Result

- Implemented by hand in worktree `local-recipes-wt-atlas-range-recorder-race-2026-10-13` from `0d5702f516`.
- Reproduction before the fix: delayed-write harness, log `[]` right after the query, `[206]` a second later.
- After the fix: `test_emit_range.py` 13 passed; the mutation (206 appends after the write) → `1 failed`.
