---
id: SPEC-fleet-consistency-standard
status: shipped
updated: "2026-09-09"
owner-dream: docs/dreams/pyforge-marshal.md   # § The frontier — "Fleet consistency standard"
surface:
  - scripts/governance_currency_check.py    # CAP-6, net-new — the staleness detector
  - scripts/ad_citation_check.py            # CAP-6, net-new — architecture-decision citation integrity
  - scripts/.ad-citation-baseline.json      # CAP-6 — the ratchet's recorded debt; shrinks only
companions:
  - ../../../../../EXEMPLAR-STANDARD.md     # adopted-then-rewritten: the reviewable enumeration behind this Spec's normative claims
  - coverage-baseline-2026-09-07.md         # the fleet's first coverage measurement — what the ratchet ratchets FROM
sources:
  - docs/dreams/pyforge-marshal.md
open_questions:
  # ANSWERED 2026-09-09 (operator, fleet-readiness batch rows mars-B-B9 / mars-B-B10). Neither is
  # undecided any longer; both are RETITLED AS DISPOSITIONS rather than deleted, because each now
  # names another station's outstanding work.
  - "DISPOSITION (answered 2026-09-09) — mechanizing INV-2/INV-3 into `pyforge.doctor.sources` lands in PYFORGE-DOCTOR, not as a later story here. Marshal builds, Doctor judges; the split has precedent in Story 6.9, which moved `spec_surface_check` out of `scripts/` into `pyforge.doctor.sources.chain` and had both marshal Specs re-point their surfaces. Rejected: keep it in marshal — it re-creates the detector-in-marshal shape 6.9 deliberately retired. CROSS-STATION: doctor owns the story."
  - "DISPOSITION (answered 2026-09-09) — YES, the coverage gate's `--cov` target should extend over the django/portal tier, but NOT HERE: it amends `spec-pyforge-testing-charter` CAP-4, which already owns coverage. `package_src()` resolves to `pyforge-<station>/src/pyforge/<station>`, so django-pyforge's `mcp_auth.py` / `access.py` / `rate_limit.py` / `middleware.py` / `circuits.py` sit outside every cov target by construction. Epic 32 is `done`, so a new story here would reopen a closed epic. Rejected: extend `package_src()` inside fleet-consistency — it re-mints an owned capability. CROSS-STATION: the testing-charter Spec's owner takes it."
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
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `4a8034f705`: `EXEMPLAR-STANDARD.md`'s only mentions of the four retired skill names (`bmad-document-project`, `bmad-create-story`, `bmad-check-implementation-readiness`, `bmad-dev-auto`) sit inside a historical note (lines 13-20) wrapped in a `governance-currency:ignore-start/end` marker, not presented as live fact; the removed 16-stage table and dated snapshots are gone (only backward references to their removal remain, lines 15/511); 21 `INV-`-prefixed lines survive; `pixi.toml:1033` still names the file as the `dream-chain` detector's `Contract:`; `governance-currency` (CAP-6) independently confirms every reference in the file resolves.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `4a8034f705`: `EXEMPLAR-STANDARD.md` still lives at its original path with a `pixi run -e local-recipes governance-currency` clean run (see CAP-6) confirming no dead reference in it.

- **CAP-2 — One test-suite vocabulary across the fleet.**
  - **intent:** A test file's directory tells any reader and any tool which suite it belongs to, using the same three names at every station.
  - **success:** Every station's tests resolve to `unit/`, `integration/` or `meta/` (plus a non-collected `fixtures/`, and `conftest.py` at the tests root); `conformance/`, `contract/`, `oracle/` and the loose root-level test files are gone; `marshal/support/` is renamed `_support/` so it stops matching suite globs; `run_station_coverage_gate.py`'s suite map needs no per-station special case; and each station's own suite passes after its move.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `4a8034f705`: `find src/shared/packages -type d \( -name conformance -o -name contract -o -name oracle \)` returns nothing repo-wide; every one of the 8 stations' `tests/` dirs contains only `unit/`, `integration/`, `meta/` (plus `fixtures/`/`conftest.py` where used); `src/shared/packages/pyforge-marshal/tests/_support` exists (renamed from `support/`); `scripts/run_station_coverage_gate.py:_suite_test_paths` (lines 31-44) is a fixed unit/integration/meta map with an explicit comment citing Story 32.5 and no per-station branch.

- **CAP-3 — No artifact survives that the toolchain no longer produces.**
  - **intent:** The planning tree contains only artifacts something still generates or a human still maintains, so a reader never has to guess whether a stale file is authoritative.
  - **success:** All eight `epics-with-stories.md` are retired, their normative content rehomed first (steward's suite-shape mandate at `epics-with-stories.md:61` is known; the other seven are audited before deletion); the four code references are removed (`hygiene_definitions.py` allowlist entry, `deps.py` and `dispatch_fleet.py` exclusions, `bmad_tea_playwright.py` fallback); no station README still points at one.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `4a8034f705`: commit `a208caa5208` ("CAP-3 -- retire epics-with-stories.md fleet-wide") deletes all 8 stations' `epics-with-stories.md` (8 separate deletion hunks in `git show --stat`) and touches exactly the 4 named files (`_bmad/scripts/bmad_tea_playwright.py`, `pyforge-doctor/.../hygiene_definitions.py`, `pyforge-doctor/.../sources/deps.py`, `pyforge-marshal/.../core/dispatch_fleet.py`); `find _bmad-output -iname epics-with-stories.md` now returns zero hits; all 8 station `README.md` files mention the name only inside a "retired 2026-09-07, marshal Story 32.4" footnote pointing readers at `epics.md`, not as a live pointer.

- **CAP-4 — Artifact naming is machine-classifiable.**
  - **intent:** Every planning artifact matches the classifier that governs it, so pointing a detector at a new station reports real findings rather than false `uncovered` noise.
  - **success:** Every `implementation-readiness-report-*` uses the hyphenated ISO form `bmad_drift_check.py` matches; `bmad-drift` reports zero `uncovered` files when run against any station, not only pyforge-marshal.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `4a8034f705`, **NOT fully passing, not fabricating a clean result:** the hyphenated-ISO-form half holds — every `implementation-readiness-report-*` file under `_bmad-output` uses `YYYY-MM-DD` (one exception, `pyforge-marshal/planning-artifacts/implementation-readiness-report.md`, predates the `-*` glob and is a distinct un-dated doc, not a violation of the dated form). But the "zero `uncovered`" half does **not** currently hold: `pixi run -e local-recipes bmad-drift-check --json` reports 5 live `HARD` `uncovered` findings, all under pyforge-marshal — `planning-artifacts/benchmarks/structure-graph-dispatch-28-31.json` and four story-spec files (`spec-33-3-...memlog.md`, `spec-33-8-...md`, `spec-33-9-...md`, `spec-34-4-...md`). These are artifacts that landed after CAP-4's classifier work, not a regression of it, but the CAP's own success criterion is unmet at the moment of this sweep — the `pyforge.doctor.sources` classifier (Story 6.9 ported the mechanism there) has not been extended to cover them. Leaving unverified rather than fabricating a pass; the classifier gap is real, reproducible via the command above, and is a fair follow-up for whichever station owns `pyforge.doctor.sources`'s classification rules next.

- **CAP-5 — The declared Python floor equals the tested floor.**
  - **intent:** A package's `requires-python` states what is actually exercised, not an aspiration nothing runs.
  - **success:** All ten packages declare `>=3.14`, matching `pixi.toml`'s `python = ">=3.14.7,3.14.*"` and every env-scoped `3.14.*` pin; no package claims support for an interpreter no environment in this repo installs.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `4a8034f705`: `grep -L 'requires-python = ">=3.14"' src/shared/packages/pyforge-*/pyproject.toml` returns nothing — all 10 `pyforge-*` packages (atlas, core, doctor, herald, marshal, mason, scribe, steward, testing-kit, warden) declare `>=3.14`; `pixi.toml:36` floors the shared interpreter at `>=3.14.7,3.14.*` and every env-scoped `python =` pin found in the file reads `3.14.*`, no divergence. (The 8 `django-*` UI packages stay at `>=3.12` by design — a separate, non-station tier this CAP's "ten packages" wording does not cover.)

- **CAP-6 — Governance docs cannot go stale silently.**
  - **intent:** When a skill is renamed, a script retired or a path moved, the governance documents that reference it fail a check instead of quietly misleading readers for months.
  - **success:** A detector resolves every `bmad-*` skill name, script path and file reference in `EXEMPLAR-STANDARD.md`, `AGENTS.md`, `CLAUDE.md` and `docs/reference/test-charter.md`, and exits non-zero naming each reference that no longer resolves; it is discovered by `scripts/detectors.py` and has its own pixi task; run against the pre-CAP-1 standard it reports all seven of this session's staleness findings.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `4a8034f705`: `pixi run -e local-recipes python scripts/detectors.py --list` auto-discovers both `governance_currency_check` (task `governance-currency`) and `ad_citation_check` (task `ad-citation-check`) via the `scripts/*_check.py` glob, no registry entry required; `pixi run -e local-recipes governance-currency` reports "ok" clean against the 4 live governed docs; a synthetic probe (`--file` against a scratch doc citing `bmad-document-project` and a fabricated script path) exits 1 and correctly names both as `skill-not-found`/`script-not-found`, confirming the exit-non-zero-and-name-it behavior the success criterion requires. Did not re-derive the historical "all seven of this session's staleness findings" replay against the pre-2026-09-07 standard (would require reverting `EXEMPLAR-STANDARD.md`); the mechanism check above stands in as direct evidence of the same capability.

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
- `status: shipped` (2026-09-09) — CAP-1..CAP-6 decompose to Epic 32 (Stories 32.1–32.8), all
  `done`; `epic-32` and `epic-32-retrospective` are both `done` in the ledger.
