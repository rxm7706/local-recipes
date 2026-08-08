---
title: A drift gate nobody can clear, and a drift signal anyone can launder
type: dream
owner: marshal
status: dreamt
---

# A drift gate nobody can clear, and a drift signal anyone can launder

> The enforcement half of [[regenerable-factory]]. That Dream built the surface
> map and the drift checker; this one makes the checker's verdict **clearable**
> and **trustworthy**, which it is not today.

## The Dream

`scripts/spec_surface_check.py` is the instrument that makes the regenerable
factory real: it proves every tracked file is governed by a spec surface, and
that no governed file drifted out from under its contract. It has carried a
large red for weeks — **61 findings on `main`** — and the reason is not that
the repo is 61 kinds of broken. It is that the detector has two defects that
make its verdict *unactionable in one direction and untrustworthy in the other*:

**You cannot clear it honestly.** `--write-baseline` stamps **every** spec in
one write. So the sanctioned fix for a single `[no-baseline]` finding —
registering one spec that legitimately has no baseline entry — necessarily
accepts **every other spec's pending drift as correct**. Settling one spec
destroys the evidence for ~34 others. The honest move is therefore to leave the
finding standing, which is exactly why the red has persisted. *A gate nobody can
safely clear stops being a gate.*

**You cannot trust it either.** The drift pass short-circuits **per SPEC, not
per file**: `if b["memlog"] != cur["memlog"]: continue  # spec moved — code
changes are presumed reconciled`. So appending **any** memlog entry marks every
governed file in that surface reconciled — including files the author never
touched. The drift half is defeatable by unrelated activity, silently, and the
disappearance is indistinguishable from a real fix in the findings count that
the dashboard renders. The larger a surface's governed set, the more it
launders; this surface governs four detectors.

These two are the same disease from opposite ends: **the reconciliation claim is
made at the wrong granularity.** Baselines are stamped all-or-nothing when they
should be per-spec; drift is cleared per-spec when it should be per-file. Fix
the granularity and both symptoms go away — the gate becomes clearable one spec
at a time, and a memlog entry stops speaking for files it never mentions.

Behind that is a rule this repo already believes everywhere else: **never claim
green you did not measure.** A "presumed reconciled" blanket is a claim nobody
measured. Where reconciliation genuinely cannot be proven, the honest output is
a *visible, non-gating* signal — not silence.

## What it looks like when real

- **`--write-baseline --spec <name>`** stamps one spec by merging into the
  existing baseline, so a single legitimately-unregistered spec can be settled
  without blessing anything else. Unscoped `--write-baseline` still exists, and
  says plainly in its own help text that it accepts every other spec's pending
  drift.
- **A memlog reconciles the paths it NAMES.** When a spec's contract moved, each
  drifted file is checked against the memlog text; named paths clear, unnamed
  paths surface as a distinct, informational `[drift-presumed]` line rather than
  vanishing. The set is always visible; the operator decides.
- **The 61 findings are worked to zero by category, not by one blanket stamp** —
  every `[no-baseline]` scoped-stamped, every `[drift]` either genuinely
  reconciled through its spec (the surface changed → the contract moves) or
  scoped-stamped with the reasoning recorded, the two `[ungoverned]` files given
  a surface or an allowlist entry, the one `[stale-allowlist]` pattern removed.
- **The verdict is green and stays green** — the next out-of-band edit is caught,
  because the signal is finally trustworthy enough to act on. Note the detector
  already *runs* in CI (`.github/workflows/detectors.yml`, via the `scope=repo`
  registry subset) but is **deliberately advisory, not blocking** — an operator
  decision of 2026-07-31 that [[fidelity-enforcement]] records as still open.
  This Dream does not settle it: a signal worth gating on has to be true first,
  which is what this work is for.
- **Nothing is silenced to get there.** If a finding cannot be honestly cleared
  in this effort, it is recorded as deferred work with its reason, not
  suppressed.

## What is real (measured 2026-08-08, on `main` at `cf885388fe`)

- **61 findings**, partitioned: **34 `[drift]`**, **24 `[no-baseline]`**,
  **2 `[ungoverned]`**, **1 `[stale-allowlist]`**.
- Drift concentrates in five specs — `pyforge-steward/spec-pyforge-steward`
  **23**, `pyforge-scribe/spec-team-memory` **5**, and 2 each in
  `pyforge-marshal/spec-fidelity-enforcement`, `spec-factory-console`,
  `spec-durable-runs`. The steward cluster is one Epic-2/3 delivery, i.e. a real
  surface change whose contract never moved — the detector is right about it.
- The two `[ungoverned]` files are
  `docs/governance/spec-pyforge-charter/{SPEC.md,.memlog.md}` — the Charter's own
  spec sits outside every surface and every allowlist entry. The instrument that
  polices the chain does not cover the document that defines it.
- The `[stale-allowlist]` entry is `pixi.toml`, which now matches nothing.
- Both defects were **reproduced live**, not read off the source:
  `DW-SURFACE-2026-08-08-1` records appending an unrelated allowlist note to one
  memlog dropping findings **63 → 61**, clearing two pending findings
  (`scripts/bmad_drift_check.py`, `scripts/dream_chain_check.py`) that the author
  never touched — recorded verbatim in that memlog under a `(NOT RECONCILED …)`
  entry so the information survived the finding.
  `DW-SURFACE-2026-08-08-2` records the all-or-nothing stamp.
- A throwaway prototype of both fixes was written and **reverted** on 2026-08-08
  once it was clear this is chain work, not a hand-patch. It established that the
  change is small and local to `main()` — scoped merge on the write path,
  per-file check on the read path — and that no other detector reads the baseline
  format. That is design evidence for the Spec, not an implementation.

## Constraints

- **Fix the granularity; do not weaken the gate.** Widening a threshold,
  allowlisting the noisy specs, or making drift non-gating would clear the red
  without making the signal true. Charter §6 forbids exactly this move.
- **Never touch `.memlog.md` history.** Memlogs are append-only decisions of
  record; the fix reads them, it never rewrites them.
- **A memlog that names no paths is not an error.** Most existing entries predate
  any naming convention, so the per-file rule must degrade to a visible
  `[drift-presumed]`, never to a hard failure that would red the gate for every
  historical entry.
- `[drift-presumed]` is **informational**. It exists to make an unproven set
  visible; if it gated, it would just be the same unclearable red in a new shape.
- The baseline file is committed state — a scoped stamp must **merge**, never
  rewrite, or it silently drops every spec it did not name.

## Non-goals

- **Not** re-homing this detector to Doctor. That is Charter §6 work already
  scoped as Doctor's Epic 6 (S-6.1 → S-6.10); this Dream fixes the instrument
  where it lives. Marshal keeps the operational guard either way — only the
  *verdict* moves, later.
- **Not** a general dependency or provenance graph. The reconciliation claim is
  "does the memlog name this path", deliberately literal. Inferring intent from
  prose would reintroduce the same "presumed reconciled" blanket this replaces.
- **Not** a rewrite of the surface-glob or coverage half. Coverage works; the two
  `[ungoverned]` files are a missing entry, not a design flaw.
- **Not** an excuse to bulk-reconcile the steward cluster by stamping it. If that
  surface genuinely changed, its contract moves — that is the whole point of the
  factory.

## Realization log

- **2026-08-08** — Captured. The 61 findings had been carried as "pre-existing,
  verified identical before/after" across several sessions (PR #322's own notes
  say so) — accurate as a non-attribution, but it had hardened into a reason not
  to look. Operator pushed back on exactly that: pre-existing explains why a
  finding is not yours, never why it stays. The two tool gaps were already filed
  as `DW-SURFACE-2026-08-08-1/2` with live reproductions; this Dream is the
  decision to fix them through the chain rather than patch the detector by hand.
  A prototype of both fixes was written, then reverted, to keep Dream-first
  ordering honest — its findings are recorded above as design evidence.
