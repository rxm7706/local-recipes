---
title: One spec's clean reconciliation should clear another's, when they share a file
type: dream
owner: marshal
status: realized
---

# One spec's clean reconciliation should clear another's, when they share a file

## The Dream

`spec-surface-check`'s own drift half (`spec-regenerable-factory` CAP-3) checks every
governing spec of a changed file **independently**: each must show its own memlog moved
and names the file, or it gets flagged, with zero awareness that another spec governing
the *same* file may have already reconciled it cleanly. A file is routinely governed by
more than one spec at once — a station's own broad kernel spec (`spec-pyforge-<station>`)
and a narrower, actively-worked spec both match it — and the checker's own code confirms
this is not an edge case: `_governed_and_ungoverned` explicitly assigns a file to *every*
matching spec, not one winner. When the kernel spec's memlog stops moving for routine
story work (which is normal — routine work reconciles against the narrower spec that
actually owns the story), it accumulates permanent, un-clearable `drift-presumed` noise
for every file the narrower spec already handles correctly.

> A file's change is accounted for the moment *some* spec that governs it says so — not
> only when *every* spec that happens to also govern it says so.

## Why now — measured, not feared

Found and fixed at data-scale on 2026-09-12 (`maintenance/kernel-spec-surface-overlap-2026-09-12`,
PR #1288): 178 `drift-presumed` findings across 17 specs, all the identical shape — a
kernel spec double-claiming files a narrower, currently-clean spec already reconciles.
The fix landed was `surface-drift-exclude:` entries naming each specific overlapping
file per kernel spec — safe, mechanical, and immediately effective (0 findings fleet-wide
afterward), but it treats the *symptom* file-by-file. It does not stop the same pattern
from recurring the next time a new narrow spec is minted under a kernel spec's remaining
surface, which is the normal, expected shape of how this factory's planning tree grows —
every station starts as one kernel spec and decomposes into dozens of story-scoped specs
over its life. The `spec-regenerable-factory` CAP-3 contract that governs this checker
was itself never written with multi-owner overlap in mind: its own intent language reads
"a governed file changed... without *the spec's* memlog moving" — singular, one spec, by
design, at the time it was written.

## What it looks like when real

- A file governed by two or more specs is `drift-presumed`/`drift` **only when none of
  its co-governing specs' memlogs name the change** — not "only when every one of them
  does."
- A newly-minted, narrow story spec that correctly reconciles a file it shares with its
  station's kernel spec produces **zero** finding against the kernel spec for that file,
  automatically, with no manual `surface-drift-exclude:` entry ever required.
- The `surface-drift-exclude:` entries this Dream's own motivating fix landed (PR #1288)
  become historical artifacts of a workaround, not a pattern anyone needs to keep hand-
  maintaining going forward — new overlaps self-resolve.
- A genuinely unreconciled change — one where *no* co-governing spec's memlog explains
  it — is still caught exactly as today. The fix narrows a false-positive, it does not
  widen what counts as accounted-for.

## Constraints / Non-goals

- **Never weakens real drift detection.** A file with zero co-governing specs, or where
  every co-governing spec's memlog is silent on it, must still flag exactly as it does
  today. This is strictly a false-positive fix for the multi-owner case, not a general
  loosening.
- **Not a redesign of spec-surface-check's coverage half.** Coverage (`ungoverned`) stays
  exactly as it is — every tracked file needs ≥1 governing spec or an allowlist entry.
  Only the DRIFT half's per-spec independence changes.
- **Not retroactive rewriting of `surface-drift-exclude:` entries already landed.** PR
  #1288's entries stay as a correctness fallback and a record of what was found; this
  Dream's Spec does not require removing them once the detector itself improves.
- **`pyforge-doctor` owns the code, `pyforge-marshal` owns the contract** — `spec-
  regenerable-factory` CAP-3 (shipped, `pyforge-marshal`) is the capability this Dream
  extends; the implementation lives in `pyforge.doctor.sources.chain` per the existing
  cross-station convention (each station records its own incoming surface claim in its
  own memlog before code lands).

## Kinships

[[regenerable-factory]] (CAP-3 — the shipped capability this Dream extends, not
replaces) · [[mcp-host-real-station-tools]] (the sibling precedent: a gap found in an
already-shipped spec's own mechanism, closed same-day with a new, narrowly-scoped Dream
rather than reopening the shipped one) · [[pyforge-marshal]] (owns `spec-regenerable-
factory`) · [[pyforge-doctor]] (owns `pyforge.doctor.sources.chain`, the actual checker
code).

## Realization log

- **2026-09-12** — Seeded (operator ruling: gap-closure enters through the Dream-to-Code
  chain like any other effort). Found reconciling 178 `drift-presumed` findings across 17
  station-kernel specs (PR #1288): every one traced to the same root cause, confirmed by
  reading `pyforge.doctor.sources.chain`'s own `_governed_and_ungoverned` (a file is
  assigned to *every* matching spec, not one) and `_drift_findings` (drift is computed
  per-spec, independently, with no cross-spec awareness at all). The immediate 178 were
  closed with `surface-drift-exclude:` entries (a data-level, per-file fix, safe and
  already proven for two prior specs this same session); this Dream captures the
  root-cause fix so the same class of noise does not keep recurring as new narrow specs
  get minted under existing kernel specs. Next act: `bmad-spec` derives the Spec under
  `pyforge-marshal`.
- **2026-09-16** — `dreamt` → `realized` (fleet-inbox-disposition). Marshal Epic 42
  (Stories 42.1–42.2) shipped in PR #1378: overlap OR on a clean co-governor. Record:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-inbox-disposition-2026-09-16.md`.
