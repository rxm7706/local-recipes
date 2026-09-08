---
id: SPEC-fleet-consistency-standard
status: ready
owner-dream: docs/dreams/pyforge-marshal.md   # § The frontier — "Fleet consistency standard"
surface:
  - scripts/governance_currency_check.py    # CAP-6, net-new — the staleness detector
companions:
  - ../../../../../EXEMPLAR-STANDARD.md     # adopted-then-rewritten: the reviewable enumeration behind this Spec's normative claims
sources:
  - docs/dreams/pyforge-marshal.md
open_questions:
  - "Does mechanizing INV-2/INV-3 into pyforge.doctor.sources land as a later story here or in pyforge-doctor? EXEMPLAR-STANDARD's own verification section admits both were measured by hand and never mechanized."
  - "Should the coverage gate's --cov target be extended over the django/portal tier? package_src() resolves to pyforge-<station>/src/pyforge/<station>, so django-pyforge's mcp_auth.py / access.py / rate_limit.py / middleware.py / circuits.py sit outside every cov target by construction. Deferred to spec-pyforge-testing-charter CAP-4's decomposition."
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale this contract intentionally omits.

# Fleet consistency standard

## Why

**A pain to solve, and the instruments are the last place anyone looks.** The fleet's content is
healthy — 25/25 detectors green, five-tier 40/40, two TODO markers across all eight stations'
source. What has drifted is the connective tissue, and it drifted because the document that
defines the operating model went stale without anything watching it.

`_bmad-output/EXEMPLAR-STANDARD.md` names four skills that no longer exist
(`bmad-document-project`, `bmad-create-story`, `bmad-check-implementation-readiness`,
`bmad-dev-auto`) and three research skills BMAD 6.12 consolidated into `bmad-deep-recon`.
Because it is stale it keeps mandating `epics-with-stories.md`, which 6.12 produces nowhere and
which is frozen at 2026-08-08 in six of eight stations while `epics.md` moved to 2026-09-06.
Meanwhile the test trees grew **eight suite names for two concepts**, and the coverage gate's
suite map recognises neither spelling of `conformance` — leaving **51 real test files measured
by nothing**. `pytest-cov` is declared in 2 of 10 pixi features, so seven station environments
cannot run a coverage gate at all. `implementation-readiness-report-` exists in three date
formats across 27 files, only one of which `bmad_drift_check.py`'s classifier matches.

Every one of those is individually small. Together they mean the operating model cannot answer
its own question — *"is this project's record complete?"* — mechanically, which is the reason
the standard was written in the first place.

The operator brief is **"simplicity and consistency decides"**: converge on BMAD 6.12's defaults,
retire customizations no longer earning their place, and do not introduce new divergence. This
Spec is that convergence, plus the detector that stops it recurring.

## Capabilities

- **CAP-1 — The operating-model standard is 6.12-accurate, and derives what it can.**
  - **intent:** A reader of the standard can trust every skill name, script path and file reference in it, and the parts that restate machine-readable facts are gone rather than maintained by hand.
  - **success:** `EXEMPLAR-STANDARD.md` names no skill, script or path that does not resolve on disk; its 16-stage skill-mapping table and its dated conformance-status snapshots are removed (the first restates BMAD's own skill set, the second is a hand-derived measurement a detector produces); INV-0..INV-5, the eleven-row conformance table, the kernel/companion rule and the provenance rules survive intact; the file keeps its path, because `pixi.toml`'s `dream-chain` detector names it as its `Contract:`.

- **CAP-2 — One test-suite vocabulary across the fleet.**
  - **intent:** A test file's directory tells any reader and any tool which suite it belongs to, using the same three names at every station.
  - **success:** Every station's tests resolve to `unit/`, `integration/` or `meta/` (plus a non-collected `fixtures/`, and `conftest.py` at the tests root); `conformance/`, `contract/`, `oracle/` and the loose root-level test files are gone; `marshal/support/` is renamed `_support/` so it stops matching suite globs; `run_station_coverage_gate.py`'s suite map needs no per-station special case; and each station's own suite passes after its move.

- **CAP-3 — No artifact survives that the toolchain no longer produces.**
  - **intent:** The planning tree contains only artifacts something still generates or a human still maintains, so a reader never has to guess whether a stale file is authoritative.
  - **success:** All eight `epics-with-stories.md` are retired, their normative content rehomed first (steward's suite-shape mandate at `epics-with-stories.md:61` is known; the other seven are audited before deletion); the four code references are removed (`hygiene_definitions.py` allowlist entry, `deps.py` and `dispatch_fleet.py` exclusions, `bmad_tea_playwright.py` fallback); no station README still points at one.

- **CAP-4 — Artifact naming is machine-classifiable.**
  - **intent:** Every planning artifact matches the classifier that governs it, so pointing a detector at a new station reports real findings rather than false `uncovered` noise.
  - **success:** Every `implementation-readiness-report-*` uses the hyphenated ISO form `bmad_drift_check.py` matches; `bmad-drift` reports zero `uncovered` files when run against any station, not only pyforge-marshal.

- **CAP-5 — The declared Python floor equals the tested floor.**
  - **intent:** A package's `requires-python` states what is actually exercised, not an aspiration nothing runs.
  - **success:** All ten packages declare `>=3.14`, matching `pixi.toml`'s `python = ">=3.14.7,3.14.*"` and every env-scoped `3.14.*` pin; no package claims support for an interpreter no environment in this repo installs.

- **CAP-6 — Governance docs cannot go stale silently.**
  - **intent:** When a skill is renamed, a script retired or a path moved, the governance documents that reference it fail a check instead of quietly misleading readers for months.
  - **success:** A detector resolves every `bmad-*` skill name, script path and file reference in `EXEMPLAR-STANDARD.md`, `AGENTS.md`, `CLAUDE.md` and `docs/reference/test-charter.md`, and exits non-zero naming each reference that no longer resolves; it is discovered by `scripts/detectors.py` and has its own pixi task; run against the pre-CAP-1 standard it reports all seven of this session's staleness findings.

## Constraints

- **`EXEMPLAR-STANDARD.md` keeps its path.** `pixi.toml:947` names it as the `dream-chain` detector's `Contract:`, and 33 other files reference it. It is rewritten in place as this Spec's companion; deleting it breaks a live gate's contract pointer.
- **AGENTS.md is written only through `bmad-project-context`.** Its managed block starts at line 9 and is replaced on refresh — a hand-edit inside it is destroyed on the next run.
- **The spec-surface baseline re-stamp runs last**, after every file move and after `git add`. `--write-baseline` reads the working tree and `git ls-files`; stamping earlier bakes the pre-move state in and reports every moved file as drift.
- **`conftest.py` and `fixtures/` stay at each station's tests root** through the convergence, so shared fixtures remain visible to both `unit/` and `integration/`.
- **No station's suite may be red at any checkpoint.** A green suite gates each convergence commit; a reading of the diff does not.
- **Coverage floors are seeded from measurement, never asserted.** Add `pytest-cov` to the seven environments lacking it, measure all eight, write each station's measured value as its starting floor, and let floors only ratchet upward.

## Non-goals

- **Re-minting the coverage gate.** `spec-pyforge-testing-charter` CAP-4 already owns it, is marshal-owned and `status: ready`, and `docs/reference/test-charter.md` Phase 4 carries the matching unchecked box. This Spec's coverage work amends that capability; it does not restate it.
- **Retroactively raising any station's coverage.** Floors are seeded at measured values. Closing individual gaps remains each station's own story work — the same boundary the testing charter already draws.
- **Re-sorting atlas's topic directories by test level.** Its 23 subdirectories are a domain taxonomy, not a suite taxonomy; they move wholesale under `unit/` with their structure intact.
- **Waiting for `spec-python-foundry-cutover`.** That effort relocates every package to `src/packages/` in a new repo. Convergence happens now so foundry carries a consistent estate rather than replicating today's drift.
- **Mechanizing INV-2/INV-3, or extending coverage over the django/portal tier.** Both are real work, both are named in `open_questions`, and bundling either here would make the change unreviewable.

## Success signal

Pointing `bmad-drift` at any station — not just pyforge-marshal — returns zero `uncovered`
files. Every station's tests live under `unit/`, `integration/` or `meta/`, and
`run_station_coverage_gate.py` measures all of them with no per-station special case, including
the 51 files nothing measured before. And re-running the CAP-6 detector against the standard as
it stood on 2026-09-07 reproduces all seven staleness findings this session had to discover by
hand.

## Assumptions

- Raising `requires-python` to `>=3.14` breaks no external consumer: no `recipes/pyforge-*` exists, so the stations are built by `pixi-build-python` for this repo's own 3.14 estate and are not published to conda-forge.
- Folding steward's `conformance/` into `unit/` inherits the unit floor rather than integration's. Taken from steward's own `test-architecture.md`, which classifies those files as unit level; not independently re-judged file by file.
- The other seven `epics-with-stories.md` carry normative content of the same kind steward's does. They are audited before deletion rather than assumed empty — steward's mandate was found by accident, which is the reason the audit is a gate.
