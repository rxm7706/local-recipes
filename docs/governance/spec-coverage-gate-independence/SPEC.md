---
spec: coverage-gate-independence
status: ready   # 2026-09-14 — seeded `draft` in the morning; ruled and flipped the same day.
                # All five open questions were answered by one operator decision (the narrow
                # Charter §5 amendment: `owner: guild` widens to "a gate that judges all eight
                # Smiths"), so the contract is settled and downstream may bind. Lives under
                # docs/governance/ beside spec-pyforge-charter because its Dream is guild-owned
                # (chain.py `_expected_spec_dir`: guild -> docs/governance/spec-<slug>/).
created: "2026-09-14"
updated: "2026-09-24"
owner-dream: docs/dreams/coverage-gate-independence.md
surface:        # Declared 2026-09-20 by doctor Story 24.1 (CAP-1/CAP-2): the evaluator and
                # its thresholds moved outside every pyforge.<station> package. All four
                # paths below are outside spec_surface_check.py's own SPEC_GLOB (it only
                # discovers `_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md`,
                # not docs/governance/), so none is tracked by that detector under THIS
                # Spec -- scripts/coverage_gate.py, scripts/coverage_gates_ci.py and
                # scripts/run_station_coverage_gate.py are allowlisted instead
                # (scripts/spec_surface_allowlist.txt, the same guild-owned-Spec-cannot-
                # declare-a-surface-here shape as scripts/chain_sprawl_baseline.py) and
                # docs/governance/coverage-thresholds.toml sits under the existing
                # `docs/governance/**` allowlist entry. This list is the documentation
                # contract, not a live detector input. Story 24.3 (2026-09-24) handed the
                # two scripts/ drivers' governance here FROM spec-pyforge-testing-charter,
                # which dropped them from its own `surface:` in the same change (its
                # memlog records the hand-over) -- the two surfaces are now disjoint, so
                # neither driver is governed twice or left ungoverned.
  - scripts/coverage_gate.py
  - docs/governance/coverage-thresholds.toml
  - scripts/coverage_gates_ci.py
  - scripts/run_station_coverage_gate.py
companions: []
sources:
  - ../../../docs/dreams/coverage-gate-independence.md
open_questions: []
  # RAISED 2026-09-14 (morning) AND CLOSED 2026-09-14 (operator ruling, same day) — the five
  # originally listed here, each answered in the Dream's § Open questions:
  #   where-a-fleet-wide-blocking-gate-can-live        -> under the Guild (docs/governance/)
  #   is-splitting-thresholds-from-evaluator-sufficient -> no; §6 names weaken/re-threshold/disable
  #   does-guild-roster-precedent-apply                 -> yes; thresholds land beside guild-roster.json
  #   are-the-other-seven-stations-equally-exposed      -> all eight treated alike under a guild gate
  #   should-the-import-linter-catch-this-class         -> yes; CAP-3
---

> **Canonical contract.** Seeded 2026-09-14 from `docs/dreams/coverage-gate-independence.md` as a
> chain-only draft; **ruled the same day** and now the complete contract for what to build, test and
> validate. The Dream in frontmatter is traceability only.

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

## Capabilities — chosen 2026-09-14

- **CAP-1 — the evaluator does not ship inside a station it judges.**
  - *intent:* `coverage_gate.py` lives where no station it gates also governs it — under this
    guild-owned Spec's surface, physically outside every `pyforge.<station>` package (the
    `scripts/` drivers move with it out of `spec-pyforge-testing-charter`'s surface).
  - *success:* no `pyforge.<station>` module is the evaluator of that same station's CI gate; the
    eight `pyforge-<station>-coverage-gate` pixi tasks and `coverage-gates.yml` call the new home;
    the AD-3/AD-4 import-linter contract that names `pyforge.marshal.coverage_gate` is amended with
    its reasoning in the same change. *(Ruled: the host is the Guild. `pyforge-gates` — a ninth
    package with no Smith — was rejected as the `owner: crew` shape.)*
- **CAP-2 — a threshold change is a governance act.**
  - *intent:* `coverage_thresholds.toml` cannot be lowered by the station it binds without the
    judging station's verdict.
  - *success:* the thresholds file lives in `docs/governance/` beside `guild-roster.json`, carrying
    the same "changing this file is a governance act" `$comment`; changing any station's floor is a
    §5 decision reviewed by someone other than that station. *(Ruled: data-only was **not**
    sufficient — §6 names *weaken, re-threshold, disable*, and moving only the data protects one of
    the three — so CAP-2 lands together with CAP-1, never instead of it.)*
- **CAP-3 — the class is caught structurally, not by investigation.**
  - *intent:* an import-linter contract forbids any `pyforge.<station>` module from evaluating that
    station's own CI gate.
  - *success:* reintroducing this shape fails a test rather than waiting for a future audit. This
    defect survived because nothing could see it. *(Ruled: yes.)*

## Constraints

- Charter §6 is ruled **broad** (2026-09-14): any check that can red a Marshal PR judges the Marshal.
- Doctor cannot host a blocking gate — it is constitutionally advisory.
- No station's floor drops as a side effect. The 80/70 defaults are `spec-pyforge-testing-charter`
  CAP-4's, not this effort's to renegotiate.
- The AD-3/AD-4 import-linter contract is amended deliberately, with reasoning, or not at all.
- Marshal's verdict lattice is out of scope — the investigation cleared it.

## Non-goals

- Re-thresholding anything. This is about *who may change a floor*, never what the floor is.
- Making Doctor's detectors blocking fleet-wide — that reverses the 2026-07-31 operator decision.
  `DW-VOCAB-2026-09-14-16` was ruled separately the same day for exactly one row
  (`ledger-regression` is a scoped blocking step in `detectors.yml`); anything wider is its own
  ruling.
- Rewriting the eight `pyforge-<station>-coverage-gate` pixi tasks as an end in itself; they are
  callers and follow whatever home is chosen.

## Success signal

A station cannot lower the floor that reds its own pull requests, and a future attempt to ship a
gate inside the package it judges fails a test rather than passing unnoticed for weeks.

## Open Questions

None. The five the seed carried were ruled 2026-09-14 by one operator decision — the narrow
Charter §5 amendment — and each answer is recorded against its question in the Dream's § *Open
questions for the Spec*. The recursion that made them hard was real (the gate judges all eight
stations, so any station-owned home reproduces the defect) and is the reason the home is the
Guild's rather than any Smith's.

## Who does the work

The **outcome** is the Guild's; the **mechanism** is Doctor's (Charter §5's outcome/mechanism
rule — Doctor is the Smith §6 already names as Marshal's judge, and its `sources/marshal.py` is the
independence exemplar this Spec's CAP-1 copies). The stories live in
`_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md` and are reflected in doctor's
`sprint-status-ledger.yaml`; they bind to this Spec's CAP ids. No code moves before those stories
exist ("Spec → Story before code").
