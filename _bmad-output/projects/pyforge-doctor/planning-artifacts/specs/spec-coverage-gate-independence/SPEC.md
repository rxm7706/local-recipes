---
spec: coverage-gate-independence
status: draft   # 2026-09-14 — seeded so the Dream's chain link is durable (dream-chain INV-1).
                # Five open questions remain and every one is a design decision about where a
                # fleet-wide blocking gate may live, so nothing downstream may bind to this yet.
                # Per docs/dreams/README.md:71-78 a `draft` Spec establishes the CHAIN, not the
                # CONTRACT — the owning Dream therefore stays `dreamt`.
created: "2026-09-14"
updated: "2026-09-14"
owner-dream: docs/dreams/coverage-gate-independence.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/coverage-gate-independence.md
open_questions:
  - where-a-fleet-wide-blocking-gate-can-live
  - is-splitting-thresholds-from-evaluator-sufficient
  - does-guild-roster-precedent-apply
  - are-the-other-seven-stations-equally-exposed
  - should-the-import-linter-catch-this-class
---

> **Seed Spec — the chain, not the contract.** Derived 2026-09-14 from
> `docs/dreams/coverage-gate-independence.md`. It exists so `dream-chain` INV-1 has a durable link
> and so the finding is recorded where downstream can see it. **Every capability below is a
> candidate. Nothing is chosen** — the remedy turned out to be a design decision, not the file move
> it first appeared to be.

# SPEC — the gate that judges a station never ships inside it

## Why

`pyforge/marshal/coverage_gate.py` and `coverage_thresholds.toml` ship inside the marshal package,
and `.github/workflows/coverage-gates.yml:90` runs that gate across all eight stations — marshal
included — with zero `continue-on-error` in 158 lines. Lowering marshal's own blocking floor is a
three-line `[stations.marshal]` edit to a file marshal owns, with no Doctor verdict involved. That
is Charter §6's prohibition verbatim, and the operator ruled its scope **broad** on 2026-09-14: any
check that can red a Marshal PR judges the Marshal.

The obvious remedy fails. `pyforge-core` and `pyforge-testing-kit` are **both governed by marshal's
own planning tree**, so relocating there moves the violation one package over. Doctor cannot host it
either — Doctor is constitutionally advisory (*"findings stay advisory — not a second PR gate"*), so
a blocking gate there trades one violation for another. And `pyforge.marshal.coverage_gate` is named
in an AD-3/AD-4 import-linter contract, so the move amends a declared layering rule.

## What the investigation CLEARED (recorded so it is not re-litigated)

- **Marshal's verdict lattice is legal.** It judges the *story's* work. `core/gate.py:41-46`
  documents `Verdict.GATE_FAILED` as *"a project's own gate failed"* as against the `ERROR` tier's
  *"an internal Marshal operation failed"* — two subjects deliberately on separate rungs.
- **`marshal seed check`'s "(CI gate)" is not literal here** — zero hits in `.github/`. It is literal
  only in the adoption guide, where an adopting repo gates its own conformance.
- **Doctor does hold Marshal's row**, with the estate's strongest independence:
  `doctor/sources/marshal.py` reads only durable artifacts and never imports `pyforge.marshal`,
  pinned structurally by a meta-test. **This module is the exemplar to copy.**

## Capabilities — all candidates, none chosen

- **CAP-1 — the evaluator does not ship inside a station it judges.**
  - *intent:* `coverage_gate.py` lives where no station it gates also governs it.
  - *success:* no `pyforge.<station>` module is the evaluator of that same station's CI gate.
    *(Open: where. The gate judges all eight, so the host must be governed by none of them.)*
- **CAP-2 — a threshold change is a governance act.**
  - *intent:* `coverage_thresholds.toml` cannot be lowered by the station it binds without the
    judging station's verdict.
  - *success:* changing any station's floor requires review by someone other than that station.
    *(Open: whether moving only the data — `guild-roster.json`'s precedent, whose own `$comment`
    says changing it is a governance act — satisfies §6, which names re-thresholding specifically.)*
- **CAP-3 — the class is caught structurally, not by investigation.**
  - *intent:* an import-linter contract forbids any `pyforge.<station>` module from evaluating that
    station's own CI gate.
  - *success:* reintroducing this shape fails a test rather than waiting for a future audit. This
    defect survived because nothing could see it.

## Constraints

- Charter §6 is ruled **broad** (2026-09-14): any check that can red a Marshal PR judges the Marshal.
- Doctor cannot host a blocking gate — it is constitutionally advisory.
- No station's floor drops as a side effect. The 80/70 defaults are `spec-pyforge-testing-charter`
  CAP-4's, not this effort's to renegotiate.
- The AD-3/AD-4 import-linter contract is amended deliberately, with reasoning, or not at all.
- Marshal's verdict lattice is out of scope — the investigation cleared it.

## Non-goals

- Re-thresholding anything. This is about *who may change a floor*, never what the floor is.
- Making Doctor's detectors blocking — that reverses the 2026-07-31 operator decision and is tracked
  as `DW-VOCAB-2026-09-14-16`.
- Rewriting the eight `pyforge-<station>-coverage-gate` pixi tasks as an end in itself; they are
  callers and follow whatever home is chosen.

## Success signal

A station cannot lower the floor that reds its own pull requests, and a future attempt to ship a
gate inside the package it judges fails a test rather than passing unnoticed for weeks.

## Open Questions

All five are carried verbatim from the Dream's § *Open questions for the Spec*. They are design
decisions about where a fleet-wide blocking gate may live, and the recursion is real: the gate
judges all eight stations, so any station-owned home reproduces the defect.
