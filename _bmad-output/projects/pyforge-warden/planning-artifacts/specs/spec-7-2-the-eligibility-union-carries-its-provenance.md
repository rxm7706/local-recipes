---
title: 'The eligibility union carries its provenance'
type: 'feature'
created: '2026-08-22'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      "Reproducible from provenance alone" (SPEC.md CAP-2 / epics.md AC) does
      not universally hold: the required_authority_sources policy that
      actually determines status is never recorded on EligibilityResult or
      ProvenanceEntry.
    evidence: |-
      Under the default policy (None), the whole-run union of every result's
      own provenance sources reconstructs the effective required set, so
      reproducibility holds at the whole-run level. Under an explicit,
      caller-supplied override, no trace of that override survives in the
      returned data -- a third party holding only the EligibilityResult
      tuples (without also knowing the call's required_authority_sources
      argument) cannot always re-derive status from provenance alone. The
      caller who supplied the override still holds it themselves, so no
      information is lost from their vantage point; the gap only bites a
      downstream/persisted consumer. Story 7.3 (CAP-3, CycloneDX output) is
      the natural point to decide how/whether to record the effective policy
      alongside a persisted eligibility report (e.g. as document metadata),
      since that is the first point "the answer" becomes an artifact a third
      party could hold in isolation. Raised by the Intent Alignment Auditor
      review layer on the 2026-08-22 review pass.
    location: >-
      src/shared/packages/pyforge-warden/src/pyforge/warden/eligibility.py (compute_eligibility_union)
    severity: medium
baseline_revision: '585d1799199bb7e29c9a3134bc373f13ce5632db'
---

<intent-contract>

## Intent

**Problem:** Story 7.1 gave Warden a way to ingest `SourceEvidence` from heterogeneous
evidence sources and a standalone identity API, but nothing yet answers the estate-wide
question those adapters exist for: given evidence from several sources about the SAME
package identity, is it eligible for use, with a provenance trail proving the answer.

**Approach:** Add a new, pure `eligibility.py` module: an `EligibilityStatus` enum
(`eligible-union`/`observed-in-use`/`flagged-for-review`), a `ProvenanceEntry` dataclass,
an `EligibilityResult` dataclass, and `compute_eligibility_union` — a pure function over
already-ingested `sources.SourceEvidence` that groups evidence by `PackageIdentity`,
classifies each identity against a configurable (default: unanimous) set of
required-authority source names, and attaches a deduplicated provenance trail.

## Boundaries & Constraints

**Always:**
- `compute_eligibility_union` is a pure function: no filesystem/network/subprocess I/O —
  it consumes already-`ingest()`-ed `SourceEvidence`, never calls `.fetch()`/`.ingest()`
  itself (mirrors `models.py`'s "pure data" precedent).
- `EligibilityStatus`/`ProvenanceEntry`/`EligibilityResult` are NEW, standalone types in
  `eligibility.py` — never added to `models.py`'s frozen `Status` enum or
  `ComplianceReport` shape (epic Technical Decision: the two vocabularies answer
  different questions — estate-wide "may this exist" vs. project-scoped "did the scan
  pass" — and must not be merged).
- The default `required_authority_sources` (used when the caller passes `None`) is
  computed ONCE from the distinct `source_name`s present across the FULL input evidence
  tuple — NEVER re-derived per identity (a per-identity default would trivially satisfy
  "unanimous" for any identity seen by only one source, defeating the consensus policy
  entirely).
- Provenance de-duplicates by `(source_name, locator)` pair per identity — this closes
  the frontmatter `deferred` cross-observation-duplication item recorded in
  `spec-7-1-sourcecontract-adapters-the-identity-api.md` (a package seen twice by the
  same source, e.g. direct + transitive in one CycloneDX document, collapses to one
  `ProvenanceEntry` for that source+locator).
- Reuse `sources.PackageIdentity`/`sources.SourceEvidence` verbatim — never a second,
  divergent identity/evidence type.

**Block If:** none identified — the required-authority default policy and the 3-way
classification rule are fully decided in this spec per the epic AC's own delegation
("default decided here").

**Never:**
- No CycloneDX output (Story 7.3) and no FABRIC corpus fixtures (Story 7.3).
- No CLI or TOML config wiring (`cli.py`/`config.py` untouched) — this story is the pure
  computation only; a real CLI entry point or a config surface for
  `required_authority_sources` is a later story's job.
- No conflict-marker/denylist string detection — not named in this epic's own AC or
  `epic-7-context.md`'s Requirements & Constraints (the sibling Dream's "10 string
  markers" feature is pattern-reference only, not a requirement here).
- Never merge `EligibilityStatus` with `models.Status`, never import/touch `verdict.py`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Unanimous consensus | One identity has evidence from both source names present in the full evidence set; `required_authority_sources=None` | `status=ELIGIBLE_UNION`; provenance has one entry per source | No error |
| Partial consensus | One identity has evidence from only 1 of 2 source names present in the full evidence set; `required_authority_sources=None` | `status=FLAGGED_FOR_REVIEW` | No error |
| Non-required source only | Evidence for an identity comes only from a source name explicitly excluded from `required_authority_sources` | `status=OBSERVED_IN_USE` | No error |
| Explicit empty required set | `required_authority_sources=frozenset()` | Every identity's status is `OBSERVED_IN_USE` (`ELIGIBLE_UNION`/`FLAGGED_FOR_REVIEW` unreachable) | No error |
| Duplicate observation, same source+locator | Two `SourceEvidence` for the same identity, same `source_name`, same `locator` (e.g. direct + transitive in one doc) | Provenance collapses to ONE `ProvenanceEntry` for that `(source, locator)` | No error |
| Same source, different locator | Two `SourceEvidence` for the same identity, same `source_name`, different `locator` (two separate documents read by the same adapter type) | Provenance carries TWO distinct `ProvenanceEntry` rows | No error |
| Empty evidence | `evidence=()` | Returns `()` | No error |
| Distinct versions | Two `SourceEvidence` for the "same" canonical package but different `PackageIdentity.version` | Two independent `EligibilityResult` entries, each classified on its own evidence | No error |
| Determinism | Same evidence tuple + same `now`, called twice | Both calls return equal result tuples, including provenance sub-ordering | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/src/pyforge/warden/eligibility.py` -- NEW module: `EligibilityStatus`, `ProvenanceEntry`, `EligibilityResult`, `compute_eligibility_union`.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/sources.py` -- REUSE ONLY (Story 7.1): `PackageIdentity` (line ~85), `SourceEvidence` (line ~130). Do not modify.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/models.py` -- STYLE REFERENCE ONLY: `StrEnum` precedent (`Status`, line 75; `Ecosystem`, line 119). Do not modify -- frozen contract, this epic's vocabulary stays separate per epic Technical Decision.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/feeds.py` -- PATTERN REFERENCE ONLY: `is_feed_stale`/`feed_provenance` (lines 162-191) establish the `now: datetime`-injected-for-testability convention `compute_eligibility_union`'s own `now` parameter mirrors. Do not modify.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/inventory.py` -- PATTERN REFERENCE ONLY: `_union_provenance` (lines 355-375, 496-...) shows this codebase's sorted/deduplicated provenance-union convention that this story's own per-identity provenance dedup mirrors. Do not modify.
- `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-7-1-sourcecontract-adapters-the-identity-api.md` -- frontmatter `deferred` entry (cross-source de-duplication) that this story's provenance dedup closes.
- `src/shared/packages/pyforge-warden/tests/unit/test_eligibility.py` -- NEW test file.
- `src/shared/packages/pyforge-warden/tests/unit/test_sources.py` -- STYLE REFERENCE ONLY for constructing `SourceEvidence`/`PackageIdentity` fixtures and test naming conventions. Do not modify.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-warden/src/pyforge/warden/eligibility.py` -- create the module: `EligibilityStatus(StrEnum)` (`ELIGIBLE_UNION = "eligible-union"`, `OBSERVED_IN_USE = "observed-in-use"`, `FLAGGED_FOR_REVIEW = "flagged-for-review"`); `ProvenanceEntry` (frozen dataclass: `source: str`, `locator: str`, `timestamp: str`); `EligibilityResult` (frozen dataclass: `identity: PackageIdentity`, `status: EligibilityStatus`, `provenance: tuple[ProvenanceEntry, ...]`); `compute_eligibility_union(evidence: tuple[SourceEvidence, ...], *, required_authority_sources: frozenset[str] | None = None, now: datetime) -> tuple[EligibilityResult, ...]` implementing: (1) if `required_authority_sources` is `None`, compute the default ONCE as `frozenset(ev.source_name for ev in evidence)` over the FULL input tuple; (2) group evidence by `identity` (a dict keyed on the frozen, hashable `PackageIdentity`); (3) per identity, `observed = frozenset(ev.source_name for ev in group)`, `required_present = observed & required_authority_sources`; status is `ELIGIBLE_UNION` when `required_authority_sources` is non-empty and `required_present == required_authority_sources`, else `FLAGGED_FOR_REVIEW` when `required_present` is non-empty, else `OBSERVED_IN_USE`; (4) build `provenance` as one `ProvenanceEntry(source=ev.source_name, locator=ev.locator, timestamp=now.isoformat())` per DISTINCT `(source_name, locator)` pair in the group (deduplicated), sorted by `(source, locator)`; (5) return all results sorted by `(identity.ecosystem, identity.canonical_name, identity.version or "")`.
- `src/shared/packages/pyforge-warden/tests/unit/test_eligibility.py` -- unit-test the full I/O matrix above, using hand-built `SourceEvidence`/`PackageIdentity` fixtures (no adapter I/O needed -- this module is pure).

**Acceptance Criteria:**
- Given evidence built from real `sources.SourceEvidence`/`PackageIdentity` instances, when `compute_eligibility_union` runs, then every returned `EligibilityResult.identity` is the SAME `PackageIdentity` object/value from its input evidence group (no re-derivation, no second identity computation).
- Given two separate calls with different evidence tuples (different `source_name`s present) and no explicit `required_authority_sources`, when each call computes its own default, then each default reflects ONLY that call's own evidence set (never a shared module-level cached default).
- Given the full existing test suite and every REUSE-ONLY/PATTERN-REFERENCE-ONLY file in the Code Map, when this story's tests run, then none of them are modified (`git status --short` shows only the two new files touched).

## Design Notes

The default-required-authority computation MUST happen once, globally, over the full
evidence tuple -- not inside the per-identity grouping loop. A per-identity default would
mean "the sources that saw THIS package" always equals "the sources required for THIS
package," making `ELIGIBLE_UNION` trivially true for every single-source identity and
`FLAGGED_FOR_REVIEW` unreachable -- silently defeating the whole point of a consensus
policy. Computing it once from the full evidence set gives a stable meaning: "by default,
every source consulted in this run must agree."

`ProvenanceEntry` deliberately omits the Dream's `metadata` field. `epic-7-context.md`
(the actual requirements distillation -- the sibling Dream is explicitly pattern-reference
only, not a requirements source) states only "every result must carry `ProvenanceEntry`
trails (source + timestamp)"; adding an unrequested, untested `metadata` field would be
speculative surface Simplicity First forbids. `locator` is kept (present for free on every
`SourceEvidence`) because "reproducible from provenance alone" requires knowing WHERE each
contributing observation came from, not just which source type observed it.

Example: evidence `[(id=X, src="cyclonedx", loc="a.json"), (id=X, src="manifest",
loc="/proj")]` with default policy (both required) -> one `EligibilityResult` for `X`,
`status=ELIGIBLE_UNION`, `provenance=(ProvenanceEntry("cyclonedx","a.json",now),
ProvenanceEntry("manifest","/proj",now))`.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `36bc011d30` (2026-08-22, "Merge pull request #632 from rxm7706/warden/7-2-eligibility-union-provenance"). Ledger row `7-2-the-eligibility-union-carries-its-provenance: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `src/shared/packages/pyforge-warden/src/pyforge/warden/eligibility.py`, `src/shared/packages/pyforge-warden/tests/unit/test_eligibility.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
