---
title: '26.1: A touched live-proof-only surface gets an advisory Doctor finding naming it'
type: 'feature'
created: '2026-09-18'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/live-proof-surfaces.md'
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** bugs cluster where a dev/review pass structurally cannot verify them from inside the repo alone — a live round-trip against something outside it (a third-party API, a live browser, a service with its own auth and drift) is the only real proof, and no self-report is evidence of that. `live-proof-surfaces.md` (CAP-77's companion) already catalogs six such surfaces fleet-wide, each with a real, existing proof mechanism (or an honest "no mechanism yet" note) — but nothing currently reads that catalog or surfaces it to a reviewer.

**Approach:** A new Doctor Source (`live_proof_surfaces.py`) parses `live-proof-surfaces.md`'s table into a lookup of `(station, surface, path_globs, how_to_prove, cost)`. Given a set of changed paths, it reports an advisory Finding for every catalogued surface a changed path matches, quoting the catalog's own "how to prove it live" cell verbatim. A surface whose catalog row says no mechanism exists yet reports that honestly — never invents one.

## Boundaries & Constraints

**Always:**
- The finding is always `status=warn`, never `fail` — matches AD-2's operability-not-policy posture and CAP-77's own constraint.
- The proof-step text in a finding is quoted verbatim from `live-proof-surfaces.md`, never re-derived or paraphrased.
- The catalog is the single source of truth — adding a new live-proof surface means editing `live-proof-surfaces.md`, not hardcoding a second list in the source module.
- `Source` enum gains exactly one new member (`LIVE_PROOF_SURFACE`), extending AD-3's closed taxonomy.

**Never:**
- Do not fabricate a live-proof mechanism for the atlas Chromium/DuckDB/WASM row (the catalog's own named gap) — the finding for that row states plainly no mechanism is documented yet.
- Do not gate a PR on this finding — advisory only, per CAP-77's own constraint and this Spec's AD-2.
- Do not duplicate the catalog's content into the source module's own docstrings or constants — parse the one tracked file.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PR touches `mcp_transport.py` | changed path under herald's Design MCP bridge glob | warn Finding naming herald's Claude Design bridge, quoting `--prove` as the proof step | none |
| PR touches `docsite/build.py` only | no changed path matches any catalogued surface | zero `LIVE_PROOF_SURFACE` findings | none |
| PR touches atlas's Chromium/DuckDB glob | changed path matches the no-mechanism-yet row | warn Finding stating no documented live-proof mechanism exists for this surface | none |
| `live-proof-surfaces.md` malformed/unparseable | catalog file present but table structurally broken | Finding-gathering degrades to a single warn naming the parse failure, never a crash | warn, fail-open |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-77`.
Companion: `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/live-proof-surfaces.md`.
Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/live_proof_surfaces.py` (new), `models.py` (Source enum), `report-schema.json`, `__main__.py` (DISPATCH + REGISTRY), `scripts/detectors.py` (detectors-ci row), doctor unit tests.
Ledger key: `26-1-a-touched-live-proof-only-surface-gets-an-advisory-doctor-finding-naming-it`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-26-1-a-touched-live-proof-only-surface-gets-an-advisory-doctor-finding-naming-it.md`.
