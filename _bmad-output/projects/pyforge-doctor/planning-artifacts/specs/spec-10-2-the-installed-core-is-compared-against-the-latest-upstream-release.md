---
title: 'Story 10.2: The installed core is compared against the latest upstream release'
type: 'feature'
created: '2026-08-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false # judged: 6 patches (1 high, 5 low), all localized to the 3 already-touched files, mechanical/well-tested, no API/security/data-integrity surface beyond what this pass already reviewed -- not significant enough to warrant an independent follow-up
context: []
warnings: ['oversized']
baseline_revision: '4397583a7687c989086673c1ac82cea94a531238'
final_revision: '0557c6105d'
---

<intent-contract>

## Intent

**Problem:** Story 10.1 shipped CAP-1 (installed `bmad-method` vs. `pixi.toml`'s own declared
floor); Doctor still has no signal for CAP-2 -- whether the installed core is behind the latest
release actually published upstream, which can lag even when CAP-1 reports `ok` (a stale
declared floor hides a further-behind reality).

**Approach:** Extend the existing `bmad_method.py` source's `_gather` to also query npm's public
registry live (`GET https://registry.npmjs.org/bmad-method/latest`, stdlib `urllib.request`,
mirroring `pyforge-mason`'s `pypi_index.version_exists` precedent) and, on success, emit a second
`Finding` (same `Source.BMAD_METHOD_VERSION_DRIFT`, `check="bmad-method-upstream-drift"`) naming
installed vs. latest-upstream; on any fetch failure it adds nothing at all -- CAP-1's own Finding
is unaffected either way.

## Boundaries & Constraints

**Always:**
- Read-only, no state written; same never-crashes discipline as CAP-1 -- reuse `_gather`'s
  existing outer `degrade_on_exception` net for genuinely unexpected bugs, but the network fetch
  itself must be self-contained (never raises).
- New fetch helper `_fetch_latest_upstream_version(*, timeout: float | None = None) -> tuple[int,
  int, int] | None` -- stdlib `urllib.request`/`urllib.error` only (mirrors `pyforge-mason`'s
  `pypi_index.version_exists`, the fleet's own precedent for a bare unauthenticated JSON-index
  GET); every failure mode (`HTTPError`, `URLError`, `OSError`, `TimeoutError`, malformed JSON,
  missing/unparseable `"version"` field) folds to `None` -- never raises, never logs an error.
- Fail-open is silent: when the fetch returns `None`, `_gather` returns exactly the same one
  Finding CAP-1 already produces -- no second Finding, no WARN, no exception. CAP-2 degrading
  never changes CAP-1's own outcome.
- When the fetch succeeds, `_gather` returns two Findings: CAP-1's existing one, plus a second
  with `check="bmad-method-upstream-drift"`, `status=WARN` when installed is older than the
  fetched latest, `status=OK` when installed is equal-or-newer, `evidence={"installed": ...,
  "latest_upstream": ...}`, message naming both versions -- mirrors CAP-1's own Finding shape and
  wording style exactly.
- Existing CAP-1 tests in `test_sources_bmad_method.py` must keep asserting `len(findings) == 1`
  unmodified in their bodies -- add a module-level `autouse=True` fixture that monkeypatches
  `_fetch_latest_upstream_version` to return `None` by default (mirrors this file's own
  `test_gather_degrades_on_unexpected_exception` monkeypatch idiom, and
  `test_sources_chain_due_for_verification.py`'s own autouse-fixture-per-module convention), so
  no existing test call makes a live network request; new CAP-2 tests override the patch
  per-test.
- No new dependency: `urllib.request` is stdlib -- no `pyproject.toml`/`pixi.toml`/
  `environment.yaml` change.
- Reuses `Source.BMAD_METHOD_VERSION_DRIFT` -- no new `Source` member, no `report-schema.json`
  change, no `tests/meta/test_source_independence.py`/`SOURCE_MODULE` change, no `REGISTRY`
  structural change (comment-only touch-up permitted).

**Block If:** (none -- CAP-2's data-source decision was resolved by the operator on 2026-08-15;
see `spec-bmad-method-version-drift/SPEC.md`'s `## Capabilities` § CAP-2, commit `f1a3c28ba8`.
Nothing else in this story requires an unattended-unsafe decision.)

**Never:**
- Never wires this source into `doctor check`/`monitor`'s CLI dispatch or `fleet-picture`'s
  ATTENTION block -- Story 10.3's job, out of scope here (mirrors Story 10.1's own DISPATCH-only
  scoping).
- Never persists the fetched version anywhere (no cache, no local file) -- every `gather()` call
  pays its own round-trip, consistent with `pypi_index.py`'s own no-local-persistence precedent
  for this same class of interrogation.
- Never sends any credential, header, or auth token -- the npm registry endpoint is fully public
  and unauthenticated.
- Never imports `pyforge.marshal` or any other station package, or `bmad_loop` (unchanged from
  CAP-1's own independence discipline).
- Never changes CAP-1's own comparison logic, evidence shape, or message wording.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Installed behind latest upstream | fetch succeeds, e.g. latest `6.12.0`, installed `6.10.0` | 2 Findings: CAP-1's + a WARN upstream Finding naming both | No error |
| Installed equal to latest upstream | fetch succeeds, latest == installed | 2 Findings: CAP-1's + an OK upstream Finding | No error |
| Installed ahead of latest upstream | fetch succeeds, installed > latest (pre-release/dev install) | 2 Findings: CAP-1's + an OK upstream Finding | No error |
| Registry unreachable / times out / non-2xx / malformed JSON | fetch raises internally | Exactly 1 Finding (CAP-1's only) -- CAP-2 adds nothing | Folds to `None` inside `_fetch_latest_upstream_version`, never raises |
| CAP-1's own inputs are broken (as today) and fetch would otherwise succeed | e.g. missing `pixi.toml` | Exactly 1 WARN Finding (the existing `degrade_on_exception` generic one) -- fetch is never reached | `degrade_on_exception` still wraps the whole `_gather` call |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` -- add
  `_NPM_LATEST_URL`, `_fetch_latest_upstream_version()`, and extend `_gather` to append the
  second Finding when the fetch succeeds.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- comment-only
  touch-up on the `BMAD_METHOD_VERSION_DRIFT` `SourceRegistration` entry noting it now also
  covers CAP-2 (no field changes).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` -- add the autouse
  network-stub fixture; add a new "upstream npm comparison" banner section covering every I/O
  matrix row; add direct unit tests for `_fetch_latest_upstream_version`'s own success/failure
  branches (patch `bmad_method.urllib.request.urlopen`).

## Tasks & Acceptance

**Execution:**
- [x] `sources/bmad_method.py` -- add `_fetch_latest_upstream_version` (stdlib
  `urllib.request`, mirrors `pyforge-mason/pypi_index.py`'s `version_exists`) -- the CAP-2 data
  source, resolved 2026-08-15.
- [x] `sources/bmad_method.py` -- extend `_gather` to call the fetch helper and conditionally
  append the second Finding -- the actual CAP-2 comparison.
- [x] `sources/bmad_method.py` -- touch up the module docstring (currently titled "Story 10.1,
  Epic 10/CAP-1") to also name Story 10.2/CAP-2 -- keeps the module's own "why this file exists"
  narrative accurate now that it covers both capabilities.
- [x] `sources/__init__.py` -- update the `BMAD_METHOD_VERSION_DRIFT` registry comment -- keeps
  the docstring accurate now that the module covers two capabilities.
- [x] `tests/unit/test_sources_bmad_method.py` -- add the autouse
  `_fetch_latest_upstream_version`-stubbing fixture -- keeps every existing CAP-1 test
  network-free without editing their bodies.
- [x] `tests/unit/test_sources_bmad_method.py` -- add CAP-2 I/O-matrix tests plus direct
  `_fetch_latest_upstream_version` unit tests (success, `HTTPError`, `URLError`, `OSError`,
  `TimeoutError`, malformed JSON, missing/unparseable `version` field) -- proves the fetch
  helper itself never raises.

**Acceptance Criteria:**
- Given the installed core is older than the latest upstream release the fetch returns, when
  `gather(target)` runs, then it returns 2 Findings and the second names both versions with
  `status=WARN`.
- Given the installed core is equal to or newer than the fetched latest, when `gather(target)`
  runs, then the second Finding has `status=OK`.
- Given the upstream fetch fails for any reason (unreachable, timeout, malformed response), when
  `gather(target)` runs, then it returns exactly the 1 Finding CAP-1 already produces -- no
  second Finding, no exception, no WARN attributable to the fetch failure itself.
- Given the new fetch helper, when the full test suite runs, then `test_sources_registry.py`,
  `test_source_independence.py`, `test_models.py::test_source_taxonomy_is_exactly_this_closed_set`,
  and `test_schema_source_enum_matches_the_source_taxonomy_exactly` all pass unmodified (no new
  `Source` member, no schema change).
- Given the existing CAP-1 tests, when the test suite runs, then none of them perform a real
  network call (verified by the autouse stub) and all still assert exactly 1 Finding as before.

## Spec Change Log

(none -- initial draft)

## Review Triage Log

### 2026-08-20 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 1, medium 0, low 5)
- defer: 1: (high 0, medium 1, low 0)
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[high]` `[patch]` `_fetch_latest_upstream_version`'s except clause missed `http.client.HTTPException` (a malformed/truncated HTTP response, e.g. `BadStatusLine`/`IncompleteRead` -- verified NOT an `OSError` subclass, unlike `RemoteDisconnected`), so it would escape the helper, propagate through `_gather`, and let the outer `degrade_on_exception` discard the already-computed CAP-1 `drift_finding` too -- violating the explicit "CAP-2 degrading never changes CAP-1's own outcome" guarantee. Found independently by both Blind Hunter and Edge Case Hunter. Added `http.client.HTTPException` to the except tuple + `import http.client`, plus a direct regression test (`test_fetch_latest_upstream_version_folds_http_exception_to_none`).
  - `[low]` `[patch]` `BMAD_METHOD_VERSION_DRIFT`'s `SourceRegistration` comment didn't flag `scope="repo"`'s tension with CAP-2's live network call, unlike the verified `CHECK_LAYOUT` precedent (which names the same tension for its own loopback-socket/chromium case and defers the NFR-4-budget question to whichever story wires it). Extended the registry comment to mirror that pattern.
  - `[low]` `[patch]` `models.py`'s `Source.BMAD_METHOD_VERSION_DRIFT` per-member docstring still described only Story 10.1/CAP-1, inconsistent with this diff's own pattern of updating every other "why this exists" narrative. Extended the docstring to name CAP-2.
  - `[low]` `[patch]` `pixi.toml`'s `bmad-method-version-drift-check` task description still described only the CAP-1 comparison and cited only spec-10-1. Extended the description to name CAP-2 + spec-10-2; regenerated `environment.yaml` (byte-identical, description-only change).
  - `[low]` `[patch]` No test exercised the real `gather()` -> real `_fetch_latest_upstream_version` -> stubbed-`urlopen` path (every CAP-2 gather test stubbed the seam wholesale; every fetch-helper test bypassed `_gather`). Added `test_gather_exercises_the_real_fetch_helper_end_to_end`.
  - `[low]` `[patch]` `test_fetch_latest_upstream_version_folds_http_error_to_none` constructed `HTTPError(..., hdrs=None)`, which a real `urlopen`-raised `HTTPError` never has. Fixed to pass a minimal `email.message.Message()`.
  - `[medium]` `[defer]` `DW-FU-10-2` -- CAP-1's `ok` + CAP-2's `warn` share one `score.grade()` axis (grouped by bare `Finding.source`), so the story's own headline scenario computes `warn/total = 0.5`, short of the `> 0.5` threshold for `Grade.C` -- diluted to `Grade.B`. Not live today (this Source isn't wired into `score.grade()` yet, Story 10.3's territory and possibly beyond it); a real architecture question for whoever does that wiring, out of this story's own scope.
  - Rejected (noise / deliberate, spec-documented design choices): uniform fail-open with no signal distinguishing "unreachable" from "response shape changed" (Boundaries explicitly specify every failure mode folds to `None` alike, mirrors Story 10.1's own precedent for rejecting an analogous "differentiate failure modes" ask); CAP-2 gather-level tests not asserting the exact call args passed to the stubbed seam function (redundant with the already-thorough direct fetch-helper tests -- the two layers are deliberately tested independently, matching this file's own established `test_gather_degrades_on_unexpected_exception` pattern); module-docstring wording "runs ambiently and repeatedly... once Story 10.3 wires it in" claimed to overstate present tense (the caveat is already present inline; a phrasing nitpick, not a factual inaccuracy).

## Design Notes

`_fetch_latest_upstream_version`'s timeout defaults to 5.0s, not `pypi_index.py`'s 30s -- that
precedent is for `ship_pypi`'s own deliberate, one-shot, human-triggered publish flow; this
source runs ambiently and repeatedly (every `doctor check`/`monitor` invocation, once Story 10.3
wires it in), so a short timeout keeps a slow/unreachable registry from stalling an otherwise-fast
local check for long. Both numbers are metadata-GET-tier per the fleet's own convention
(`engines.gh._GH_PR_LIST_TIMEOUT_SECONDS`); 5.0s is this story's own judgment call for the
ambient-check tier, not drawn from an existing constant.

npm's registry JSON body for the `/latest` endpoint (`{"name": "bmad-method", "version": "X.Y.Z",
...}`) is parsed with stdlib `json.loads` on the response body -- reuse `_parse_version` for the
`"version"` string exactly as CAP-1 does for `manifest.yaml`'s version, so both capabilities
share one parsing/validation path and a malformed npm version string degrades the same way a
malformed local one does (folds into `_fetch_latest_upstream_version`'s own `None` return, not
`_parse_version`'s `ValueError` escaping raw).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary:** Story 10.2's code/tests/review landed cleanly at `3749c93afa` in the prior session,
but bmad-loop's own deterministic verify gate (`python scripts/spec_surface_reconcile.py`, one of
this run's two `[verify].commands`) still failed afterward: the commit changed 4 pyforge-doctor-
governed files and `pixi.toml` without naming them in the owning specs' `.memlog.md` files (S-13.7
-- the standing "loop doesn't reconcile the spec surface" gap already documented multiple times in
`spec-pyforge-doctor`'s own memlog for Stories 6.6-6.8/11.1-11.3), and the working tree separately
carried 6 pre-existing ungoverned files pushed directly to `origin/main` outside any BMAD spec
(commits `0f0b75232e`, `9de01865ce`, `4397583a76`) that also red the same repo-level gate
regardless of which story runs. This session repaired both, without touching any code inside
`<intent-contract>` or any file `3749c93afa` itself changed.

**Files changed (commit `0557c6105d`):**
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` --
  new "Story 10.2" section naming the 4 changed doctor-governed paths (`sources/bmad_method.py`,
  `sources/__init__.py`, `models.py`, `tests/unit/test_sources_bmad_method.py`) and this story's
  review-triage outcome.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/.memlog.md`
  -- cross-package reconciliation entry naming `pixi.toml`'s description-only change, same pattern
  as the pre-existing Story 11.1/11.2/11.3 entries in the same file.
- `scripts/spec_surface_allowlist.txt` -- 6 new dated, reasoned entries for the pre-existing
  ungoverned files (`conda-forge-packaging-inventory-operations*`,
  `openteams_identity_dashboards.py`), none of which this story touched; disposition is an
  interim exemption pending their own spec-ownership decision, not a governance claim.
- `scripts/.spec-surface-baseline.json` -- re-stamped scoped to exactly the two reconciled specs
  (`python scripts/spec_surface_check.py --write-baseline --spec pyforge-doctor/spec-pyforge-doctor
  --spec pyforge-steward/spec-python-agent-platform`); diff confirmed to touch only those 2 specs'
  entries (7 insertions / 7 deletions: 4 doctor file hashes + 1 memlog hash, 1 pixi.toml hash + 1
  memlog hash).

**Review findings breakdown:** none this pass -- a bookkeeping repair, not a review-triggering code
change.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- rc=0, `OK: every tracked file governed or
  allowlisted; no drift.` (previously rc=1, 11 findings).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` (this run's other `[verify].commands`
  entry) -- 1048 passed, 2 skipped, unchanged from the prior session's own count -- confirms this
  repair touched no production code.
- `pixi run -e local-recipes pytest` over the spec's own listed narrow command (bmad_method +
  models + registry + dispatch + source-independence) -- 179 passed.
- `pixi run -e local-recipes spec-surface-check` (the full-repo dispatcher, wider than the loop's
  own gate) -- still reports pre-existing non-gating `drift-presumed` WARNs for an unrelated spec
  (`pyforge-warden/spec-pyforge-warden`), and a top-line `spec-surface: ok`. Left untouched:
  out of this story's scope and not part of this run's `[verify].commands`.

**Residual risks:** `.claude/skills/conda-forge-expert/tests/meta/test_bmad_artifacts_in_sync.py::
test_bmad_artifacts_integrity` (a different detector, `bmad-drift-check`/`sources/factory.py`, not
`spec_surface_reconcile.py`) fails on an unrelated pre-existing finding -- `_bmad-output/projects/
pyforge-marshal/planning-artifacts/parallel-fan-out-readiness-assessment.md` not covered by any
classification rule, added by commit `6469d9db91` on 2026-08-12, well before this story's own
`baseline_revision`. Confirmed NOT part of this run's `[verify].commands` (`.bmad-loop/policy.toml`
`[verify]` names only `pyforge-doctor-test` and `spec_surface_reconcile.py`) and out of this
story's scope -- left as-is, not silently fixed and not silently ignored.

