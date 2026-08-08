---
title: 'Conflict refusal on export push'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: true
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** `bridge-protocol.md` § *Export push-back* says "any conflict is refused structurally --
no partial clobber", but Story 5.1's own happy-path implementation says nothing about what happens
when a `write_files` call for one export file is rejected server-side (a real conditional-write
mismatch: someone edited that exact file directly in the Design project between Herald's last push
and this one). Without an explicit conflict path, a naive implementation either (a) lets an
unconditional-looking write clobber the Design-side edit, or (b) aborts the whole batch on the first
failure, silently leaving every OTHER already-attempted-but-unwritten file un-pushed too, with no
record of which state the operator is actually in.

**Approach:** Extend `push_exports` (Story 5.1) so a per-file `write_files` failure
(`errors.TransportError`, the shape a real conditional-write rejection surfaces through
`McpTransport`'s `_call_json`/`require_conditional` failure path) is caught *per file*, recorded, and
does NOT stop the loop -- every remaining candidate in the batch is still attempted. After every file
has been attempted, `state.py` is updated with exactly the files that succeeded (a conflicted file's
own `export:` record is left untouched, so a retry sees it as still-needing-a-push rather than
falsely "already pushed"), and only then does `push_exports` raise `errors.ExportConflictError`
naming every conflicted file -- never before every candidate has had its own chance to succeed or
fail independently.

## Boundaries & Constraints

**Always:**
- A `write_files` call that raises `errors.TransportError` for one candidate is caught by
  `push_exports` itself, appended to an internal `conflicts` list (filename + the caught exception's
  message), and the loop continues to the next candidate in the batch -- no `break`, no early return.
- `state.py`'s `f"export:{filename}"` record is written ONLY for filenames whose `write_files` call
  actually succeeded in this run. A conflicted file's own key is left exactly as it was before this
  run (absent on a first-ever push attempt, or the last genuinely-successful hash on a later one) --
  never set to a value implying a write that did not happen.
- The state write itself happens once, after the whole batch has been attempted (not once per file),
  using one `dict(existing.etags)` copy mutated only with the successful filenames' new hashes --
  every other pre-existing key (any other export's record, or any CAP-2 pull-side artifact key) is
  preserved unconditionally, proving `push_exports` never overwrites `existing.etags` wholesale.
- `errors.ExportConflictError` (already declared in `errors.py`, `HeraldError` subclass, mapped to
  exit code `3` by `exit_code_for` -- both pre-existing from the package's Epic 1 scaffold) is raised
  exactly once at the end of a run with 1+ conflicts, naming every conflicted filename and, when at
  least one file DID succeed, how many did.
- `herald deck push` surfaces an `ExportConflictError` through `dispatch` (AD-6) identically to every
  other `HeraldError` -- one stderr line, exit code `3` -- no parallel error-reporting path.

**Block If:** N/A -- no spike, no live gate.

**Never:**
- A conflict on one file must never prevent an already-successful file's `write_files` result (or its
  `state.py` record) from landing -- FR-20/NFR-02's "no partial clobber" is read here as "no partial
  clobber of the files that DID succeed", not "abort everything if anything fails".
- `push_exports` never retries a conflicted write itself within one call -- a conflict is reported
  once, cleanly; a second `herald deck push` invocation is the operator's own retry (mirroring how
  every other conflict error in this package, `SeedConflictError`/`PullConflictError`, is a one-shot
  refusal, not a self-heal attempt).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Single-file conflict | `write_files` raises `TransportError` for the one candidate | conflict recorded, state untouched for it | `ExportConflictError` |
| Conflict + another file in the same batch succeeds | 2 candidates, 1 conflicts | both writes attempted; the successful file's state record lands; only the conflicted filename is named in the raised error | `ExportConflictError` |
| Conflict does not disturb an unrelated pre-existing etag | a CAP-2 pull-side key (e.g. the prototype's) already recorded | that key survives the push run's state write unchanged | `ExportConflictError` |
| `herald deck push` on a conflict | CLI | exits 3, one stderr line naming `ExportConflictError` + the message | `ExportConflictError` -> exit 3 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` -- edit -- `push_exports`'s
  per-file `try`/`except errors.TransportError` loop body and the post-loop conditional `state.write`
  + `ExportConflictError` raise (same function Story 5.1 introduced; this story is its conflict
  branch, not a new function).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/errors.py` -- no change -- `ExportConflictError`
  and its `exit_code_for` entry (exit `3`) were already scaffolded in the package's Epic 1 error
  hierarchy in anticipation of this story; verified present, not re-added.
- `src/shared/packages/pyforge-herald/tests/test_deck_pipeline.py` -- edit -- `FakePushTransport`'s
  `write_fails` seam, the conflict-raises/conflict-does-not-record/conflict-does-not-abort-the-batch/
  conflict-preserves-an-unrelated-etag test rows.
- `src/shared/packages/pyforge-herald/tests/test_cli_push.py` -- edit -- the `ExportConflictError`
  reaches-`dispatch`-and-exits-3 row.

## Design Notes

**Judgment call: conflict detection is a caught `write_files` exception, not a parsed response
field.** `seed`'s own module doc (Story 1.6, DW-1-2-5) already records that a conflicted
`write_files`/`copy_files` answer's wire shape is unproven -- "nothing in this repo has observed that
wire shape yet" -- and gates CAP-1's own conflict check pre-flight (state + registry) specifically to
avoid needing to parse an unpinned response shape. CAP-5 cannot use the same pre-flight trick: the
whole point of the etag guard is that Herald genuinely does not know, before attempting the write,
whether Design's copy moved since the last push. The next most evidenced signal already inside this
package is `McpTransport`'s own established failure path -- a rejected conditional write reaches
`_call_json` as a tool-call error, which `_raw_text` already turns into `errors.TransportCallError`
(a `TransportError` subclass) for every other conditional write in this package
(`create_support_js`/`copy_files`/`write_files` all route through the identical
`require_conditional` + `_call_json` machinery `seed` already exercises). Catching
`errors.TransportError` per file is therefore the narrowest signal consistent with how every other
write in this codebase already reports a server-side rejection, without inventing a new unproven wire
contract. Recorded here as the same class of judgment call `seed`'s own docstring makes explicitly,
rather than a silent assumption.

**Judgment call: catching `errors.TransportError`, not the broader `errors.HeraldError`.** A bare
`except errors.HeraldError` would also swallow `errors.ExportConflictError` itself (this function's
own raise, reached only after the loop -- never inside it, so not actually reachable here, but a
narrower catch keeps that invariant obviously true by construction) and any future `HeraldError`
subclass that means something other than "the server rejected this write" (an auth failure, for
instance, ought to halt the whole push immediately rather than being misreported as a per-file
"conflict" -- `errors.AuthError` IS a `TransportError` subclass today, so this is a known, accepted
scope note: an auth failure mid-batch is currently reported the same way a genuine conflict is, one
file at a time, rather than halting early. Flagged as a verification gap below rather than silently
assumed correct, since distinguishing "credential expired" from "someone else edited this file" would
need a signal this package's `TransportError` hierarchy does not yet carry.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- full suite green.
- `ruff format --check` / `ruff check` clean on every file this story touches.
- `herald deck push --help` unaffected (no new flags -- this story only changes `push_exports`'s
  internal error handling).

**Verification gap (not closed by this story):** an `AuthError` (a `TransportError` subclass) raised
mid-batch by one file's `write_files` call is currently treated identically to a genuine etag
conflict -- reported as a per-file conflict, with the loop continuing to attempt the remaining files
against a credential that is almost certainly still bad for all of them. A future story should narrow
the catch (or check `AuthError` specifically and re-raise it immediately, halting the batch) once
`herald deck watch`'s own "halt on auth error, never retry a 401" convention
(`bridge-protocol.md` § Watch parameters) has a push-side analogue to reuse.

**Deferred live-MCP proof (NOT run by this session):** the orchestrating session must produce one
real conditional-write conflict against the live endpoint (edit the Warden Design project's
standalone-bundle-adjacent export file directly, then run `herald deck push pyforge-warden` with a
stale `if_match`) to confirm the real wire failure for a conditional-write mismatch actually surfaces
as `TransportCallError` through `McpTransport`'s existing `_call_json` path, rather than as an
ordinary success carrying an unpinned structured-conflict body (the exact DW-1-2-5 risk this story's
Design Notes name).

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (single agent, no independent second reviewer)

Adversarial re-read focused specifically on the "no partial clobber" requirement: does a conflict on
file A ever cause file B's own successful write, or its own state record, to be lost or
inconsistently applied?

- `[none]` No defects found on the primary AC. Verified directly:
  - `test_push_exports_conflict_on_one_file_does_not_abort_the_rest_of_the_batch` (monkeypatching
    `_discover_export_files` to surface two candidates, since today's real discovery only ever
    returns one -- see Story 5.1's own PPTX-deferral scope note) proves BOTH `write_files` calls are
    attempted in order, and that only the successful file's `export:` key lands in `state.py`.
  - `test_push_exports_conflict_preserves_an_already_recorded_unrelated_etag` proves a pre-existing
    CAP-2 pull-side etag (the prototype's) survives a conflicted push run untouched -- the state write
    uses a mutated copy of `existing.etags`, never a fresh dict.
  - `test_push_exports_conflict_does_not_record_state_for_the_conflicted_file` proves the conflicted
    file's own key is absent after the run, not merely "not updated to a wrong value".
- `addressed_findings`: 0 code defects. One real scope gap surfaced during this pass and recorded
  above rather than silently left implicit: `AuthError` (a `TransportError` subclass) is caught by
  the same per-file handler as a genuine etag conflict, so a mid-batch credential expiry is currently
  misreported as N independent "conflicts" instead of halting the batch once. Not fixed in this story
  (no push-side "halt on auth" convention exists yet to extend) -- flagged as a verification gap.
  `followup_review_recommended: true` retained for both this gap and the deferred live-MCP proof.

**Verification:** `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 488 passed, 2 skipped
(combined Story 5.1 + 5.2 total; see spec-5-1's own Verification section for the pre-Epic-5
baseline). `ruff format --check` / `ruff check` clean on every file this story touches.

### 2026-08-08 -- Adversarial review pass (Blind Hunter + Edge Case Hunter, no shared context)

- `[medium]` `[patch]` **The self-disclosed `AuthError`-misreported-as-a-conflict gap above was
  confirmed real and fixed** -- see spec-5-1's Review Triage Log entry for the fix (narrowed the
  per-file catch from `errors.TransportError` to `errors.TransportCallError`) and its new
  regression test. Recorded here too since this story's conflict-refusal contract is exactly the
  boundary the fix clarifies: a genuine per-file Design-side conflict still degrades gracefully and
  keeps the batch going; a genuine transport failure now halts it immediately instead of being
  absorbed into the conflict-refusal path.
- `addressed_findings`: 1 (medium, shared with spec-5-1). No new code defects specific to this
  story's own conflict-continuation logic (batch-continues-past-one-conflict, state-preserved-for-
  successes-only) -- re-verified against the patched code and still holds.

**Re-verification (2026-08-08, after this patch):** `pixi run --frozen -e pyforge-herald
pyforge-herald-test` -- 491 passed, 2 skipped.

**Follow-up review recommendation:** none outstanding beyond the pre-existing, already-disclosed
PPTX-export and deferred-live-MCP-proof gaps.
