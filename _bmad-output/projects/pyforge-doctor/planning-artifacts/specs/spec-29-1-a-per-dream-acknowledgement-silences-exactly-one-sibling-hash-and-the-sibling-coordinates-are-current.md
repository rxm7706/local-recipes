---
title: '29.1: A per-Dream acknowledgement silences exactly one sibling hash, and the sibling coordinates are current'
type: 'feature'
created: '2026-09-19'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred:
  - summary: >-
      `DW-OPS-2026-09-19-6`'s pre-existing `raised:` clause says "the fold decision is
      mason's/steward's" but the six Dreams' actual owners are mason (4), atlas (1), and warden
      (1) -- steward owns none of them.
    evidence: |-
      Review pass 2026-09-20 (Blind Hunter): verified against the six Dreams' own `owner:`
      frontmatter. The inaccurate clause predates this story (authored 2026-09-19 when the DW
      entry was first raised) and this diff never touches that line, so it is a pre-existing
      inaccuracy, not one this change introduced.
    location: >-
      _bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md (DW-OPS-2026-09-19-6, `raised:` line)
    severity: low
declared_low_risk: false
baseline_revision: 'ff2455866b3379fccf333e175e5166dab351c67e'
---

<intent-contract>

## Intent

**Problem:** the first live run of CAP-71 with an operator token (`DW-OPS-2026-09-19-6`) reports six locally `archived`
Dreams diverging from their pre-fold sibling copies on every run — expected fold fallout the check cannot be told about, so
the six re-fire forever and will drown a genuine later change. Separately, `_SIBLING_OWNER` names
`OpenTeams-WFT-CDO`, an org GitHub now only redirects to `openteams-ai`.

**Approach:** honour a `sibling-acknowledged: <sibling content_hash>` line on the local Dream's frontmatter (silent while
the sibling's hash equals it; re-fires naming both hashes otherwise; an archived Dream without one is reported with its
status), and read the sibling from `openteams-ai/mgmt-wf-python-modernization` directly.

## Boundaries & Constraints

**Always:** read-only toward the sibling; the acknowledgement lives on the LOCAL Dream only and records a hash, never
content; unreachable / unauthenticated stay `warn` + fail-open (exit 0).
**Never:** write to the sibling; copy sibling prose; downgrade a mismatched hash to silence.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| local Dream `sibling-acknowledged:` == sibling `content_hash` | no finding for that Dream |
| acknowledged hash ≠ sibling hash | `sibling-dreams-drift: warn` naming the Dream, the acknowledged hash and the current one |
| local Dream `archived`, no acknowledgement, diverging | finding message carries `archived` so the operator sees the fold |
| no token | `sibling-dreams-unreachable`, warn, exit 0 (unchanged) |
| sibling path 404 under the new owner | `sibling-dreams-unreachable` with the HTTP status (unchanged shape) |
| the six DW-OPS-2026-09-19-6 Dreams acknowledged at their landing-day hashes | zero findings on a live run |

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-82` (extends CAP-71).
Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py`, the six local Dreams named in `DW-OPS-2026-09-19-6` (`docs/dreams/{django-accelerator-framework,enterprise-data-models-and-apis,miniforge-installer,package-inventory-eligibility,pixi-container-image,reusable-cicd-workflows}.md`: one frontmatter line each), `planning-artifacts/deferred-work-ledger.md` (`DW-OPS-2026-09-19-6` closed with the live zero).
Ledger key: `29-1-a-per-dream-acknowledgement-silences-exactly-one-sibling-hash-and-the-sibling-coordinates-are-current`.
Ledger status at mint (unchanged): `backlog`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` can resolve this file. The landing-day sibling hashes are read live (`GH_TOKEN` from the operator's shell) — never guessed.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks (live, operator token):**
- `GH_TOKEN="$(gh auth token)" pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources sibling-dreams-drift` → exit 0 and no `sibling-dreams-drift` row for the six.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py` — `_SIBLING_OWNER` → `openteams-ai` (old owner kept in the module docstring as history); `_parse_dream_fingerprint` now also extracts an optional `sibling-acknowledged:` frontmatter value (`sibling_acknowledged` key, local-only, harmless to read off a sibling fingerprint too since siblings never declare it); `_diff_shared_slugs` silences a diverging Dream when its `sibling_acknowledged` equals the sibling's current `content_hash`, otherwise fires naming both hashes, and appends `(archived)` to the message when the local Dream is `archived` and carries no acknowledgement; new `_SiblingHTTPError` (carries `status_code`) raised by `_fetch_sibling_fingerprints` only for a real `urllib.error.HTTPError` (every other transport failure still returns `None`, fail-open, unchanged) so `_gather` can report the HTTP status in the `sibling-dreams-unreachable` finding.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py` — new tests: ack-match silences despite other diverging axes, ack-mismatch re-fires naming both hashes, archived-without-ack names `archived`, non-archived-without-ack omits it, the renamed owner/`_API_BASE`, `_SiblingHTTPError` raised (with status) on both the listing fetch and a per-file fetch, and the unreachable finding naming the HTTP status at the `gather` level.
- `docs/dreams/{django-accelerator-framework,enterprise-data-models-and-apis,miniforge-installer,package-inventory-eligibility,pixi-container-image,reusable-cicd-workflows}.md` — one `sibling-acknowledged: <hash>` frontmatter line each, at the sibling's live `content_hash` measured 2026-09-20 (`openteams-ai/mgmt-wf-python-modernization`, unchanged since 2026-08-24).
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md` — `DW-OPS-2026-09-19-6` closed, citing the live zero-finding re-verification.
- `docs/dreams/pyforge-doctor.md` — the 2026-09-19 (evening) Realization-log entry that proposed this capability gets a `**Shipped 2026-09-20:**` outcome append (review patch, see Review Triage Log).

## Design Notes

- **Why raise for HTTP errors but keep returning `None` for everything else.** `_fetch_sibling_fingerprints` is documented and tested as fail-open on any failure. Changing its return contract wholesale would touch every existing exception test. Raising `_SiblingHTTPError` only from the one branch that already has a real, useful status code (`urllib.error.HTTPError.code`) is additive: a plain `OSError` (timeouts, DNS, the existing stub tests) still falls through the generic `except Exception: return None` untouched.
- **Why the acknowledgement lives on the fingerprint dict rather than a separate lookup.** `_parse_dream_fingerprint` already reads the whole frontmatter mapping once per file; adding one more `.get()` avoids a second YAML parse and keeps `_diff_shared_slugs` a single, pure comparison function.
- **Why suppression is whole-Dream, not per-axis.** The spec's matrix says an ack match yields "no finding for that Dream" — the six acceptance fixtures diverge on status, content_hash AND title simultaneously (pre-fold vs. post-fold copies), so a per-axis suppression would still fire on the other two axes and never reach the live zero the spec requires.

## Spec Change Log

_None — the pre-authored intent-contract needed no amendment; investigation confirmed the described approach was directly implementable._

## Review Triage Log

### 2026-09-20 — Review pass (Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment Auditor)

- verdicts: 10 findings — high 0, medium 0, low 2, false 7, maybe-false 0 (1 additional `defer`)
- findings:
  - `[false]` `[reject]` Blind Hunter: `sprint-status-ledger.yaml` still keys this story `backlog`, so a marshal drain could re-dispatch it — refuted: the spec's own Binding section states "Ledger status at mint (unchanged): backlog" — the key transitions at landing time via `sprint-ledger-sync`, owned by marshal's dispatch/land tooling, not by this build-auto session; standard mid-flight state for any in-progress story.
  - `[defer]` Blind Hunter: the DW-ledger's pre-existing `raised:` clause says "the fold decision is mason's/steward's" but the six Dreams' actual owners are mason/atlas/warden (steward owns none) — real inaccuracy, but pre-existing prose from the entry's original 2026-09-19 authoring, not introduced by this diff. Deferred (frontmatter `deferred:` below); low severity, cosmetic.
  - `[false]` `[reject]` Blind Hunter: acknowledgement suppression is keyed only on `content_hash`, so a sibling title/status/owner-only change (hash unchanged) would stay silenced — refuted: the spec's own I/O & Edge-Case Matrix row 1 explicitly specifies whole-Dream suppression on hash match ("no finding for that Dream"), not per-axis; the Design Notes already document this as the deliberate choice needed to reach the required live zero (the six fixtures diverge on multiple axes simultaneously).
  - `[false]` `[reject]` Blind Hunter: no test exercises "ack matches hash but another axis independently changed" — same refutation as above; not a gap since the behavior it would test is spec-mandated, not a defect.
  - `[false]` `[reject]` Blind Hunter: the `(archived)` annotation is dropped from the re-fired message when a stale acknowledgement is present, and no test asserts on it — refuted: the I/O matrix's row 3 (`archived`, no acknowledgement) is the only row that requires the `archived` tag; row 2 (acknowledged-hash-mismatch) does not mention it. The code matches the matrix literally, confirmed independently by the Intent Alignment Auditor ("a defensible, literal reading... not a contract violation").
  - `[false]` `[reject]` Blind Hunter: `_SiblingHTTPError` drops `.reason`/`.headers`, so a 403 and a 404 "surface identically" — refuted: the numeric status code IS surfaced distinctly per failure (`HTTP 403` vs `HTTP 404`), which is exactly what the spec's matrix row 5 asks for ("with the HTTP status"); the pre-existing `_unreachable_finding` shape has always been a short reason string, never a rich diagnostic dump.
  - `[low]` `[patch]` Blind Hunter: `docs/dreams/pyforge-doctor.md`'s 2026-09-19 (evening) entry that proposed this capability was left in pure future/"Proposed" tense with no outcome note, even though this diff ships it — applied: appended a `**Shipped 2026-09-20:**` sentence to that bullet recording the landed mechanism and the live zero.
  - `[false]` `[reject]` Blind Hunter: the spec's `status: in-review` and the DW-ledger's "Story 29.1 landed"/`closed` read as a lifecycle mismatch within the same diff — refuted: this same review pass advances the spec to `status: done` before the work is finalized (see below), so the two artifacts agree by the time this pass concludes and before anything lands anywhere.
  - `[false]` `[reject]` Blind Hunter: the "live re-verification" claim has no captured artifact attached to the diff, unreproducible without an operator token — refuted: the check was genuinely executed in this session (not asserted from memory); this repo's own Auto Run Result convention (see precedent `spec-30-1`) records verification as prose citing the exact command and exit code, not a committed log file, which is what both the spec's Verification section and the DW-ledger closure note already do.
  - `[low]` `[patch]` Edge Case Hunter: `sibling-acknowledged` frontmatter YAML-parses as a non-string for an all-digit value (or `true`/`false`/`null`), silently discarding a real acknowledgement — verified real (reproduced it myself while writing the ack-mismatch test, which is why that test uses a hex-looking stale hash rather than the more obvious `"0"*64`). Fails toward extra warn noise, not toward silence, so no invariant is actually broken, but the fix is trivial and closes a real footgun. Applied: `_parse_dream_fingerprint` now coerces a numeric (non-bool) scalar back to its literal text before the `isinstance(ack, str)` check; two new unit tests (`test_parse_dream_fingerprint_coerces_all_digit_ack_to_string`, `test_parse_dream_fingerprint_drops_non_scalar_ack`).
  - Verification Gap Reviewer: no findings ("No verification gaps found.") — independently confirmed test coverage for every behavioral branch (owner rename, ack-match/mismatch, archived tagging, both `_SiblingHTTPError` raise sites plus the `_gather` catch site, fail-open paths for non-HTTP errors) and that no other module reads `sibling-acknowledged`/`sibling_acknowledged` (no missing-adoption site).
  - Intent Alignment Auditor: descriptive report only (no discrete findings per its format) — confirmed the diff implements the literal, explicit reading of every I/O matrix row and every Always/Never constraint; its two identified "surface divergence" observations (row 2 vs row 3 archived-tag scope; the live-zero row's inherent two-tier verification split) are the same observations already triaged above as `false` under Blind Hunter's B5 and B9.

Patches applied (2): the Dream outcome append and the YAML-coercion defensive fix, both verified live — `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` → 1864 passed, 1 skipped, exit 0 (was 1862 passed before the two new regression tests).

## Auto Run Result

- **Summary:** `sibling_dreams.py` now honours a per-Dream `sibling-acknowledged: <hash>` frontmatter
  line — silent while it equals the sibling's current `content_hash` (whole-Dream, regardless of
  which axis diverges), re-firing naming both hashes the moment it does not — and appends
  `(archived)` to an unacknowledged, diverging, locally-`archived` Dream's message so the operator
  sees the fold. `_SIBLING_OWNER` moved to `openteams-ai` (old owner kept in the docstring as
  history); a new `_SiblingHTTPError` surfaces the real HTTP status in the
  `sibling-dreams-unreachable` finding for a real `urllib.error.HTTPError` at either fetch site,
  while every other transport failure still fails open exactly as before. All six
  `DW-OPS-2026-09-19-6` Dreams carry their landing-day `sibling-acknowledged:` hash; `DW-OPS-2026-09-19-6`
  is closed in the ledger. Review pass applied two small patches (YAML int/bool coercion for the
  acknowledgement field; a Dream Realization-log outcome append).
- **Files changed:**
  - `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py` — see Code Map.
  - `src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py` — see Code Map; 10 new tests.
  - `docs/dreams/{django-accelerator-framework,enterprise-data-models-and-apis,miniforge-installer,package-inventory-eligibility,pixi-container-image,reusable-cicd-workflows}.md` — one `sibling-acknowledged:` line each.
  - `docs/dreams/pyforge-doctor.md` — outcome append on the proposing Realization-log entry (review patch).
  - `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md` — `DW-OPS-2026-09-19-6` closed.
- **Review findings breakdown:** 10 findings across 4 layers (Blind Hunter 9, Edge Case Hunter 1, Verification Gap 0, Intent Alignment Auditor 0 discrete). 2 `low` patched (Dream outcome note; YAML numeric-coercion fix), 7 `false`/rejected (each refuted against the spec's own I/O matrix, Binding section, or this repo's established Auto-Run-Result convention — see Review Triage Log for each), 1 `defer` (pre-existing DW-ledger owner-attribution inaccuracy, not caused by this diff — recorded in frontmatter `deferred:`).
- **Verification performed (exit codes read directly, 2026-09-20):**
  - `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` → 1864 passed, 1 skipped, exit 0.
  - `test_sources_sibling_dreams.py` alone → 32 passed.
  - `GH_TOKEN="$(gh auth token)" pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources sibling-dreams-drift` → exit 0, zero `sibling-dreams-drift` findings for the six acknowledged Dreams (live, against `openteams-ai/mgmt-wf-python-modernization`).
- **Residual risks:** none rated `high`/`medium`. The acknowledgement's hash-only granularity (a sibling metadata-only change with an unchanged body would stay silenced under a stale-but-still-matching ack) is a known, spec-mandated tradeoff documented in Design Notes — not a residual defect. `sprint-status-ledger.yaml` still keys this story `backlog`; per the Binding section that transition is a landing-time step (`sprint-ledger-sync`), outside this session's scope.

Follow-up review recommendation: **false** — this pass patched 0 `high` and 0 `medium` entries (2 `low` only), below the threshold for a recommended follow-up.

