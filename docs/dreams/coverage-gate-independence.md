---
title: The gate that judges a station never ships inside it
type: dream
owner: guild
status: specified
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
- **The force ratio was inverted** *(measured 2026-09-14; ruled the same day, see the log)*.
  `detectors.yml` carried `continue-on-error: true` — Doctor's verdict on marshal was *advisory*
  by the 2026-07-31 operator decision — while marshal's own gate **blocks**. The judge annotated;
  the judged station's gate red the PR. Now `ledger-regression`, Doctor's committed-range
  durability verdict on Marshal's ledgers, is a dedicated blocking step in that workflow.
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
  separately *(ruled 2026-09-14 for exactly one row, `ledger-regression`; the fleet-wide posture
  is unchanged and stays outside this Dream)*.
- Touching marshal's verdict lattice, which the investigation cleared.
- Rewriting the eight `pyforge-<station>-coverage-gate` pixi tasks as an end in itself; they are
  callers and will follow whatever home is chosen.

## Open questions for the Spec — all five ruled 2026-09-14

1. **Where can a fleet-wide blocking gate live** such that no station it judges also governs it?
   **Ruled: under the Guild.** Every station-side candidate was measured and failed — `pyforge-core`,
   `pyforge-testing-kit` *and* `scripts/` are all governed by marshal's planning tree, and doctor is
   constitutionally advisory — so the question was really "who owns a policy that binds all eight",
   and the Charter's answer for the one artifact that judges every Smith is `owner: guild` (§5,
   amended this date; `guild_dreams` gains this Dream). The Spec lives at
   `docs/governance/spec-coverage-gate-independence/`; the evaluator and thresholds move under its
   surface. The `pyforge-gates` distribution was not chosen: a ninth package with no Smith is the
   `owner: crew` shape the Charter retired.
2. **Is splitting enough?** **Ruled: no.** §6 names three verbs — *weaken, re-threshold, disable* —
   and moving only the data protects one of them. The evaluator moves too.
3. **Does `guild-roster.json`'s precedent apply?** **Yes**, and it is now the same file's own
   pattern: `coverage_thresholds.toml` lands beside it in `docs/governance/` carrying the same
   "changing this is a governance act" `$comment`.
4. **What about the other seven?** **All eight are treated alike.** Under a guild-owned gate no
   station can edit its own floor without review, so the exposure is uniform rather than marshal's
   alone — which is what makes the ruling a fix and not a marshal-shaped patch.
5. **Should the import-linter contract gain a rule?** **Yes** — CAP-3. The AD-3/AD-4 contract that
   names `pyforge.marshal.coverage_gate` is amended deliberately as part of the move, and a new
   contract forbids any `pyforge.<station>` module from evaluating that station's own CI gate.

## Kinships

- [[pyforge-charter]] — Tier 0; §5's doctrine and §6's Marshal-conformance ruling, whose scope this
  Dream was minted out of.
- [[pyforge-marshal]] — the subject station; owns the package the gate ships in.
- [[pyforge-doctor]] — holds the verdict on Marshal's row, and hosts the exemplar independence.
- [[vocabulary-one-name-one-job]] — the sibling effort; its CAP-4 ruled `Gate`'s three senses on the
  same day, and this Dream is the part that a vocabulary ruling explicitly could not fix.

## Realization log

- **2026-09-14 (later the same day)** — **Ruled and `specified`.** The operator answered all five
  questions with one decision: the narrow Charter §5 amendment (`owner: guild` widens to "a gate
  that judges all eight Smiths"; the test is structural — no Smith *can* be accountable, not merely
  none is). This Dream is re-owned from doctor to `guild`, `guild_dreams` in `guild-roster.json`
  enumerates it, and the Spec moves from `pyforge-doctor/planning-artifacts/specs/` to
  `docs/governance/spec-coverage-gate-independence/` at `ready`. Doctor remains the Smith for the
  **mechanism** (§5's outcome/mechanism rule): its stories move `coverage_gate.py` and
  `coverage_thresholds.toml` under the governance Spec's surface, amend the AD-3/AD-4 contract
  deliberately, and add the CAP-3 import-linter rule — recorded in doctor's `epics.md`, not
  executed here, per "Spec → Story before code". The two rejected shapes are recorded in the
  questions above so they are not re-proposed: a `pyforge-gates` package (a Smith-less ninth
  package is `owner: crew` again) and the data-only split (protects one of §6's three verbs).
  The archived `pyforge-testing-charter` Dream is untouched — test *architecture* is marshal's
  build work; only the fleet-wide *gate* changes hands. In the same pass the force-ratio
  non-goal was ruled separately (`DW-VOCAB-2026-09-14-16`): `ledger-regression` is now a scoped
  blocking step in `detectors.yml`, so the judge's verdict on Marshal has force.
- **2026-09-14** — Seeded. A read-only investigation into whether marshal self-grades **cleared** the
  suspected surface (the verdict lattice) and found this instead. Operator ruled Charter §6 broad the
  same day, making it a named violation rather than an open question; the remedy was deliberately not
  attempted inline once `pyforge-core` and `pyforge-testing-kit` both turned out to be marshal-governed,
  which means the fix is a design decision and not a file move. Recorded before any code changed.
