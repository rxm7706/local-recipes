---
title: A spin-time poll timeout never permanently blinds marshal status to a healthy run
type: dream
owner: marshal
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-marshal]]** on 2026-09-16 (one-chain-per-station CAP-8 pilot; folded from `marshal-status-harness-run-id-poisoning`).

# A spin-time poll timeout never permanently blinds marshal status to a healthy run

## The Dream

`marshal status` (and everything built on it — `fleet-picture`'s per-station row, `dashboard-gen`'s
in-flight card) reports a run's real state — `running`/`idle`/`stopped` — for the run's entire
lifetime, even when the one-time poll `marshal factory spin` performs at launch to confirm
bmad-loop's own self-minted `harness_run_id` times out. Today it does not: that poll's failure
(`MRS-SPIN-004`) journals `"harness_run_id": null` into the run's launch OUTCOME entry
**permanently**, and every later status read — including the one legitimate fallback that
exists — re-derives from that same poisoned field and can never recover, even though the real
run directory (`.bmad-loop/runs/<run_id>/state.json`) sits on disk, correctly updating, for the
run's entire life.

## What is real

Confirmed live, 2026-08-15, reproduced on a real spin (`marshal factory spin pyforge-doctor
--story 9.1`): the poll timeout fired (`MRS-SPIN-004`), the journal recorded
`harness_run_id: null`, and `marshal status`/`fleet-picture` reported `pyforge-doctor` as
`UNKNOWN`/"status unreadable" for the run's entire ~40-minute life — including while the run
was demonstrably healthy (`ps` showed the process alive; `.bmad-loop/runs/<id>/state.json`
showed `dev-running`, correct baseline, no crash) and after it finished successfully. A prior
session (2026-08-13) recorded this same symptom as "resolved / no longer observed" — it was
not; it simply did not reproduce that session, and nobody had root-caused it as a real,
reproducing bug rather than a flake.

**Root cause, traced to source** (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/`):

- `cli/spin.py`'s launch path polls to confirm bmad-loop's own self-minted run id and journals
  it into the run-launch OUTCOME entry (`{"pid": ..., "harness_run_id": ...}`). When that poll
  times out, the entry is journaled with `harness_run_id: null` — this is the ONLY place that
  field is ever written; nothing ever goes back and corrects it later, even after the run
  proves itself alive via supervisor heartbeats.
- `cli/status.py::_gather_home_facts` (the function every `marshal status`/`fleet-picture` row
  derives from) reads `journal_facts.harness_run_id`; when it's `None`, it falls back to
  `_resolve_harness_run_id_for_resume` (`cli/spin.py:1719`) — but that helper reads the
  **identical already-poisoned journal entry**, looking for the same field. It can never
  recover a value that was never successfully written, no matter how long the run has been
  alive or how many heartbeats it has journaled since.
- Meanwhile `cli/spin.py::_latest_run_dir` already knows how to find the real, live bmad-loop
  run directory for a project by listing `.bmad-loop/runs/` — the exact information the poll
  was trying to confirm in the first place, sitting right there on disk, unused by the fallback
  path.

## What it looks like when real

- The one-time poll can still time out (network/process-timing variance is real) — the Dream
  does not eliminate the poll or its timeout.
- When it does, `_gather_home_facts`'s fallback path recovers the harness run id by
  **filesystem discovery** (the same `.bmad-loop/runs/` enumeration `_latest_run_dir` already
  performs) rather than by re-reading the same journal field that was never written —
  self-healing on the very next status read, not permanently blind for the run's whole life.
- `marshal status --format json`'s `MRS-STATUS-002` finding (today's only signal anything is
  wrong) stops firing for a run whose journal-poll merely timed out but whose bmad-loop run
  directory is real and healthy; it keeps firing, correctly, for a genuinely unrecoverable case
  (no run directory exists at all, or it's unreadable).

## Constraints

- Must not weaken `MRS-STATUS-002`'s own honest-degradation contract for the case it actually
  protects — a run whose directory genuinely cannot be found or read must still report
  `unknown`, never silently guess.
- The filesystem-discovery fallback must not introduce a live subprocess or network call per
  status read (NFR-14's own "no live harness query per home" discipline) — `_latest_run_dir`
  is already a plain `Path.glob`, so this stays within that budget.

## Non-goals

- Not fixing the poll's own timeout window or retry behavior — this Dream is about the
  permanent-blindness consequence of a timeout, not about preventing timeouts from happening.
- Not a general audit of every other journal field with a similar single-write-no-repair shape
  — scoped to `harness_run_id` specifically, the field this session's live reproduction
  actually hit.

## Kinships

[[pyforge-marshal]] (the station; `cli/spin.py`/`cli/status.py` are its own core modules) ·
[[bmad-loop-liveness-footgun]] (a sibling status-reporting footgun — `engine.pid`'s two-field
liveness misread — same family of "status reporting trusts a field that can go stale," found
the same session).

## Realization log

- **2026-08-15** — Dream captured. Root-caused during a live fleet landing pass after the user
  challenged a recurring "UNKNOWN" status finding a prior session (2026-08-13) had incorrectly
  logged as resolved. Traced to source in `cli/spin.py`/`cli/status.py`, reproduced live against
  a real spin (`pyforge-doctor --story 9.1`), and NOT hotfixed in that session per this repo's
  Dream-first policy for any `pyforge-marshal` code change. Captured as its own Dream once the
  user asked directly to fix it.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`.**
  `_discover_harness_run_id_by_filesystem` (`cli/status.py:659`) is wired as the third fallback at
  `:918-921`; CAP-2's honest degradation is held at `:930-940`. Shipped by commit `e7039b9ee6`. The
  Spec, which carried **no `status:` line at all**, is set to `shipped`. Like its sibling Dream, no
  `epics.md` story owns it — the fix landed outside the story ledger.
  **Not to be confused with the surviving `pyforge-steward` `UNKNOWN`**, which
  `DW-STATUS-2026-09-08-1` traced to a different cause — a harness-native run marshal never launched
  — owned by Story 5.11 (FR-196, `backlog`). Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
