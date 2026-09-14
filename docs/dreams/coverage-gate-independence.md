---
title: The gate that judges a station never ships inside it
type: dream
owner: doctor
status: dreamt
---

# The gate that judges a station never ships inside it

> **Seed Dream.** Found 2026-09-14 while investigating whether `pyforge-marshal` violates the
> Charter's *"the hand that builds is never the gate that judges."* The suspected surface — marshal's
> verdict lattice — turned out clean. The violation was one directory up, in the coverage gate, and
> it is a *structural* defect rather than a vocabulary one. Operator ruled the Charter's prohibition
> **broad** the same day (see `pyforge-charter.md` §6 and its Realization log).

## The Dream

A check that can red a station's pull request does not live in that station's package, and the
station cannot change its own threshold without the judging station's verdict. Today one does, and
one can.

## What is real

Measured 2026-09-14, not remembered:

- **`pyforge/marshal/coverage_gate.py` and `coverage_thresholds.toml` ship inside the marshal
  package**, and `.github/workflows/coverage-gates.yml:90` runs that gate across all eight stations,
  **marshal included**. The workflow has **zero** `continue-on-error` and **zero** `|| true` across
  its 158 lines. `pixi.toml` describes it, unprompted, as *"the gate that actually reds a PR."*
- **Lowering marshal's own floor is a three-line edit to a file marshal owns.**
  `coverage_thresholds.toml` even ships the override shape as a comment
  (`# [stations.scribe] / unit = 80.0`). No Doctor verdict is involved. That is the object Charter
  §6 names: *"the Marshal may not weaken, re-threshold or disable a check that judges the Marshal."*
- **The obvious remedy does not work.** `pyforge-core` and `pyforge-testing-kit` — the two natural
  new homes — are **both governed by `pyforge-marshal`'s planning tree**
  (`.../pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/`,
  `.../spec-pyforge-testing-charter/`). Relocating there moves the violation one package over
  rather than ending it.
- **`pyforge.marshal.coverage_gate` is named in an AD-3/AD-4 import-linter contract**
  (`tests/meta/test_ad3_ad4_import_linter.py:75`), so the move changes a declared layering contract,
  not just an import path.
- **The force ratio is inverted.** `detectors.yml:119` carries `continue-on-error: true` — Doctor's
  verdict on marshal is *advisory* by the 2026-07-31 operator decision — while marshal's own gate
  **blocks**. The judge annotates; the judged station's gate reds the PR.
- **What is NOT wrong, established by the same investigation and recorded so it is not re-litigated:**
  marshal's six-rung verdict lattice judges the **story's** work, not marshal's own —
  `Verdict.GATE_FAILED` is documented in marshal's own source as *"a project's own gate failed"*
  against the `ERROR` tier's *"an internal Marshal operation failed"*, two subjects deliberately on
  separate rungs. `marshal seed check`'s *"(CI gate)"* label is not literal in this repo (zero hits
  in `.github/`). And `doctor/sources/marshal.py` already achieves the independence this Dream wants,
  structurally: it reads only durable artifacts and never imports `pyforge.marshal`, pinned by a
  meta-test. **That module is the exemplar to copy, not a thing to change.**

## Constraints

- **Doctor cannot host it.** Doctor is constitutionally advisory — *"findings stay advisory — not a
  second PR gate"* — so moving a **blocking** gate into doctor trades one violation for another.
- The Charter's §6 prohibition is now ruled **broad** (2026-09-14): any check that can red a
  Marshal PR is "a check that judges the Marshal".
- A new home must be governed by a planning tree that is **not** the subject's. Note this makes the
  question recursive: whoever hosts it must not be a station the gate judges, and the gate judges
  all eight.
- No station's floor may drop as a side effect of the move. The 80% unit / 70% integration defaults
  are `spec-pyforge-testing-charter` CAP-4's, not this effort's to renegotiate.
- The AD-3/AD-4 import-linter contract is amended deliberately, with its own reasoning, or not at all.

## Non-goals

- Re-thresholding anything. This is about *who may change a floor*, never about what the floor is.
- Making Doctor's detectors blocking — that reverses a standing operator decision and is tracked
  separately.
- Touching marshal's verdict lattice, which the investigation cleared.
- Rewriting the eight `pyforge-<station>-coverage-gate` pixi tasks as an end in itself; they are
  callers and will follow whatever home is chosen.

## Open questions for the Spec

1. **Where can a fleet-wide blocking gate live** such that no station it judges also governs it?
   Candidates: a new `pyforge-gates` distribution owned by no station; `docs/governance/` as data
   with the code in `scripts/`; or the thresholds split from the evaluator so only the *data* moves.
2. **Is splitting enough?** If `coverage_thresholds.toml` moves to `docs/governance/` (beside
   `guild-roster.json`, which already declares itself a governance act to change) while
   `coverage_gate.py` stays put, does that satisfy §6? The prohibition names *re-thresholding*
   specifically.
3. **Does `guild-roster.json`'s precedent apply** — a file whose own `$comment` says changing it is
   a governance act, not a config tweak? That is the closest existing pattern.
4. **What about the other seven?** The gate judges all eight stations from marshal's package. Is
   every station's floor equally exposed, or only marshal's (since only marshal can edit the file
   without review)?
5. **Should the import-linter contract gain a rule** forbidding any `pyforge.<station>` module from
   being the evaluator of that same station's CI gate — so this class is caught structurally rather
   than by a future investigation?

## Kinships

- [[pyforge-charter]] — Tier 0; §5's doctrine and §6's Marshal-conformance ruling, whose scope this
  Dream was minted out of.
- [[pyforge-marshal]] — the subject station; owns the package the gate ships in.
- [[pyforge-doctor]] — holds the verdict on Marshal's row, and hosts the exemplar independence.
- [[vocabulary-one-name-one-job]] — the sibling effort; its CAP-4 ruled `Gate`'s three senses on the
  same day, and this Dream is the part that a vocabulary ruling explicitly could not fix.

## Realization log

- **2026-09-14** — Seeded. A read-only investigation into whether marshal self-grades **cleared** the
  suspected surface (the verdict lattice) and found this instead. Operator ruled Charter §6 broad the
  same day, making it a named violation rather than an open question; the remedy was deliberately not
  attempted inline once `pyforge-core` and `pyforge-testing-kit` both turned out to be marshal-governed,
  which means the fix is a design decision and not a file move. Recorded before any code changed.
