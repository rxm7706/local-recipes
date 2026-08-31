---
title: 'A spin-time poll timeout never permanently blinds marshal status to a healthy run'
type: 'bugfix'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: 'af07659161c6c284ed8334be828e309679313bc5'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `cli/spin.py`'s launch-time poll to confirm bmad-loop's own self-minted run id can
time out (`MRS-SPIN-004`), journaling `harness_run_id: null` into the launch OUTCOME entry
permanently. `cli/status.py::_gather_home_facts`'s only fallback,
`_resolve_harness_run_id_for_resume`, re-reads that SAME poisoned journal field and can never
recover — even though the real `.bmad-loop/runs/<id>/state.json` is live, readable, and
correctly updating for the run's whole life. Reproduced live 2026-08-15 (`pyforge-doctor`
story 9.1): `marshal status`/`fleet-picture` reported `UNKNOWN` for ~40 minutes of a healthy
run and after it finished successfully.

**Approach:** Add a THIRD fallback to `_gather_home_facts`, engaged only when both the journal
field and `_resolve_harness_run_id_for_resume` return `None`: discover the harness run id by
listing `home / ".bmad-loop" / "runs"` (NOT `cli/spin.py::_latest_run_dir`, which globs a
different path — Marshal's own Tier-3 `runs/<slug>-*` store, unrelated to bmad-loop's own run
directory naming) and taking the lexicographically-latest entry's directory name, trusting the
same "one active bmad-loop run per loop home" invariant `_latest_run_dir` itself already
trusts for its own chronological-sort claim.

</frozen-after-approval>

## Boundaries & Constraints

**Always:**
- New helper is a plain `Path.glob`/`iterdir` read, no `FsPort` routing needed (mirrors
  `_latest_run_dir`'s own precedent: "no directory-listing primitive exists on that port;
  adding one for this single, read-only caller would be disproportionate").
- Only engages when BOTH `journal_facts.harness_run_id` is `None` AND
  `resolve_harness_run_id(...)` returns `None` — never overrides a value either of those two
  already-trusted sources provides.
- The discovered id is used exactly as today's flow already uses `harness_run_id`: passed to
  `harness.run_status_snapshot(home, harness_run_id)`. If that returns `None` (the id was
  wrong, or the directory is unreadable/empty), the existing `journal_unreadable=True` path
  fires exactly as it does today — CAP-2's own contract, unchanged.
- Docstring the new helper and the call site with the same dated-review-citation density this
  file already uses everywhere else (cite this Spec, 2026-08-15, and the live reproduction
  case by name).

**Ask First:** none identified — the fallback is additive and cannot change behavior for any
run whose `harness_run_id` was already recoverable by the two existing paths.

**Never:** no live subprocess or network call (NFR-14); no change to `_latest_run_dir` itself
(it is correct for its own purpose — Marshal's Tier-3 store — and out of scope here); no
change to the poll's own timeout/retry behavior in the launch path (that is a separate,
un-specced concern per the source Spec's own Non-goals).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Journal poisoned, real run dir exists | `journal_facts.harness_run_id=None`, `_resolve_harness_run_id_for_resume(...)=None`, `home/.bmad-loop/runs/<id>/` exists with a readable `state.json` | New fallback discovers `<id>`, `run_status_snapshot` succeeds, `_gather_home_facts` returns real state (not `journal_unreadable`) | none |
| Journal poisoned, no run dir at all | same as above but `home/.bmad-loop/runs/` is empty or absent | Fallback returns `None`; existing `journal_unreadable=True` path fires (CAP-2, unchanged) | none |
| Journal poisoned, run dir exists but unreadable/corrupt `state.json` | fallback discovers `<id>`, but `run_status_snapshot(home, <id>)` returns `None` (bmad-loop's own `load_state` raised or returned an unusable shape) | `journal_unreadable=True` fires exactly as it does today when `snapshot is None` (CAP-2, unchanged) | none |
| Journal already healthy (no poisoning) | `journal_facts.harness_run_id` is a real string | New fallback never engages — zero behavior change to the already-working path | none |
| Multiple `.bmad-loop/runs/*` entries present | e.g. an older `20260813-...` run alongside the current `20260815-...` one (real, observed shape in this fleet) | Fallback picks the lexicographically-latest name, matching `_latest_run_dir`'s own trusted chronological-sort convention | none |

</frozen-after-approval>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` -- `_gather_home_facts` gains the third fallback; new small helper function alongside it (or as a private module-level function, whichever matches this file's own existing organization for `_gather_run_journal_facts`-adjacent helpers).
- `src/shared/packages/pyforge-marshal/tests/unit/` -- extend the existing status/`_gather_home_facts` test file (locate it; do not create a new one if an existing one already covers this function) with the two new cases: journal-poisoned-but-recoverable (CAP-1), journal-poisoned-and-unrecoverable (CAP-2 regression guard).

## Tasks & Acceptance

**Execution:**
- [x] `cli/status.py` -- add a private helper (e.g. `_discover_harness_run_id_by_filesystem(home: Path) -> str | None`) that lists `home / ".bmad-loop" / "runs"`, filters to directories, and returns the lexicographically-latest name, or `None` if the directory is absent/empty/unreadable -- mirrors `_latest_run_dir`'s own `OSError`-degrades-to-`None` discipline.
- [x] `cli/status.py::_gather_home_facts` -- when `harness_run_id` (from the journal + `resolve_harness_run_id` fallback) is falsy, call the new helper before giving up; use its result (if any) as `harness_run_id` for the `run_status_snapshot` call that follows.
- [x] `tests/unit/` -- add the CAP-1 case (poisoned journal, real discoverable run dir, expect real state returned) and the CAP-2 regression case (poisoned journal, no run dir at all, expect `journal_unreadable=True`/`MRS-STATUS-002` unchanged).

**Acceptance Criteria:**
- Given a run whose journal has `harness_run_id: null` and whose `.bmad-loop/runs/<id>/` exists and is readable, when `_gather_home_facts` runs, then it returns the run's real state, not `journal_unreadable=True`.
- Given a run whose journal has `harness_run_id: null` and no `.bmad-loop/runs/` directory exists (or it's empty), when `_gather_home_facts` runs, then it returns `journal_unreadable=True` exactly as today.
- Given a run whose journal already carries a real `harness_run_id`, when `_gather_home_facts` runs, then behavior is byte-for-byte unchanged from today (the new fallback never engages).

## Spec Change Log

- **2026-08-15, adversarial review (Blind Hunter + Edge Case Hunter, both independently, HIGH).** First implementation picked the lexicographically-latest `.bmad-loop/runs/` entry with no correlation to the run actually being examined -- live evidence during review showed a real loop home holds a dozen-plus historical entries, never garbage-collected, so "latest" is routinely wrong, not an edge case; a wrong pick would have silently blended a DIFFERENT run's state into the row, worse than the `unknown` this fix exists to replace. Triaged as `patch`, not `bad_spec`/`intent_gap`: the frozen intent already required "never overrides an already-trusted source" and CAP-2's own contract already required preferring an honest `unknown` over a guess -- the first draft simply failed to deliver that already-stated promise under realistic multi-directory conditions. Fixed by correlating the run id's own embedded creation timestamp (converted from bmad-loop's local time to match `launched_at`'s UTC) within a tight 5-minute window, plus requiring a `state.json` inside the candidate (matches bmad-loop's own reference `runs.py` filter). KEEP: the "never override an already-trusted source, only engage when both prior lookups return None" boundary from the original Intent -- unchanged and still correct. New tests added for multi-candidate disambiguation and an isolated unit-test class for the helper itself (`TestDiscoverHarnessRunIdByFilesystem`).
## Design Notes

The critical correction from this Spec's own initial framing: `cli/spin.py::_latest_run_dir`
globs `_tier3_path(home, slug) / "runs" / f"{slug}-*"` — Marshal's OWN run-tracking store
(`_bmad-output/projects/<slug>/implementation-artifacts/runs/<marshal-run-id>/`), a completely
different filesystem location from bmad-loop's own `<home>/.bmad-loop/runs/<bmad-loop-run-id>/`
directory, which is what `harness.run_status_snapshot` actually keys on (confirmed directly:
`adapters/harness_bmadloop.py::run_status_snapshot` does `run_dir = Path(project) / ".bmad-loop"
/ "runs" / run_id`). The new helper must glob the LATTER path, not reuse `_latest_run_dir`
itself — it is new, small, and analogous in shape, not a call-site reuse of the existing
function.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
