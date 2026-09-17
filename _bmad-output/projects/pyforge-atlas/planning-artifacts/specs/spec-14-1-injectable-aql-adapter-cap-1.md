---
title: 'Injectable AQL adapter (Story 15.1, CAP-1)'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
difficulty: ''
baseline_revision: 'eee8e8b78d56b508276ce43f23d4ab19ec72e2b9'
final_revision: 'd5ae2e722ac640302f0aa2102f219f63f2d93981'
---

<intent-contract>

## Intent

**Problem:** Atlas can answer "what does the public PyPI/conda-forge universe look like" but has
no code path that queries an Artifactory instance's own AQL (Artifactory Query Language) API for
its own download telemetry — the org-specific signal a public crawl structurally cannot see.

**Approach:** Add a standalone, network-injectable `ArtifactoryAqlAdapter` class — following the
exact shape already proven by `pyforge.atlas.factory.lasuite.LaSuiteClient` (injected transport
callable; a default transport that refuses rather than reaching for the network) — that resolves
a virtual repository's backing repositories, then aggregates download counts by package name +
version. Mock-only: no live Artifactory instance is named, selected, or contacted; live wiring is
a separate, later, attended step outside this story.

## Boundaries & Constraints

**Always:**
- The adapter's network access happens through EXACTLY ONE injectable transport seam
  (`Callable[[AqlRequest], AqlResponse]`), mirroring `lasuite.py`'s `Opener`/`Request`/`Response`
  triad. The class itself imports no HTTP client (`requests`/`httpx`/`urllib3`/etc.) — this is
  already structurally enforced repo-wide by `tests/catalog/test_no_inline_io.py`'s whole-package
  `IO_DENYLIST` scan (`rglob("*.py")`, no exemption needed for new files).
- The default transport (used when none is injected) raises a clear, named error identifying the
  failed call and pointing at the deferred live bring-up — it never falls back to a real network
  client. Mirrors `_unconfigured_opener` in `lasuite.py`.
- Every unit test injects an in-memory mock transport (routes on method + URL, like
  `MockWagtail` in `tests/factory/test_lasuite.py`). No test constructs or reaches for a real
  HTTP client.
- The adapter carries NO credential-resolution code of its own (no token, no API-key env var, no
  CLI/env/NETRC precedence chain). Whatever `ArtifactoryConfig` needs is limited to non-credential
  fields (e.g. `base_url`). Any auth header a live call eventually needs is attached by the real
  transport, which is constructed OUTSIDE package code at the later attended live bring-up — this
  is what "credentials route only through the existing chain, never a second bespoke path" means
  operationally: this story adds zero credential-handling code, so there is no second path to
  compare against.
- New code lives in a new top-level package `pyforge.atlas.artifactory` (sibling to `factory/`,
  `nl/`, `rag/`, `trending_candidates/` — the established "new capability gets its own top-level
  package beside `pipelines/`" pattern; see `trending_candidates/__init__.py`'s own docstring for
  the precedent). It is NOT placed under `pipelines/<name>/` as a subpackage: any directory under
  `pipelines/` is auto-imported by Kedro's `find_pipelines(raise_errors=True)` and MUST expose a
  working `create_pipeline()` or the whole project's pipeline registration breaks — Story 15.3
  (CAP-4) owns creating that pipeline subpackage and will import this adapter from
  `pyforge.atlas.artifactory`.
- `resolve_backing_repos` and the download-aggregation call are two separate transport round
  trips (topology resolution, then AQL query) — do not conflate them into one request.
- Aggregation groups by the `(name, version)` pair; multiple raw rows for the same pair (e.g. one
  per backing repo, or one per file path) sum into one output row.

**Block If:**
- None identified — this story's scope (mock-only adapter, no pipeline wiring, no identity join)
  has no decision that requires human input to proceed.

**Never:**
- Never wire this into a Kedro pipeline, catalog entry, or dataset (that is Story 15.3 / CAP-4).
- Never perform the identity join or the internal/private flag (that is Story 15.2 / CAP-2, CAP-3).
- Never name, select, or contact a real Artifactory instance anywhere in code, config, or tests.
- Never add a `credentials:`/token-resolution helper, a CLI→env→NETRC precedence chain, or any
  other bespoke credential path to this module.
- Never import `requests`, `httpx`, `urllib3`, `aiohttp`, or any other HTTP client library in this
  module (enforced structurally by the existing no-inline-IO gate).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Mock transport serves a topology response for virtual repo `libs-virtual` resolving to backing repos `["libs-local", "libs-remote-cache"]`, then a download-aggregation response with rows for a known package across both backing repos and two versions | `fetch_download_rows("libs-virtual")` returns one row per `(name, version)` pair with counts summed across backing repos | No error expected |
| No transport injected | `ArtifactoryAqlAdapter(config)` constructed with no `transport` kwarg | Any method that would issue a call raises the adapter's error type immediately, naming the attempted method+URL, before any network attempt | Raises `ArtifactoryAqlError`, never hangs or falls back to a default network client |
| Non-2xx transport response | Injected transport returns e.g. `AqlResponse(500, {"detail": "boom"})` | Adapter raises `ArtifactoryAqlError` whose message contains the HTTP status and the response body, mirroring `LaSuiteClient`'s error clarity | Raises `ArtifactoryAqlError`, message is diagnosable without a traceback |
| Virtual repo with a single backing repo | Topology response resolves to exactly one backing repo | `resolve_backing_repos` returns a one-element list; aggregation proceeds unchanged | No error expected |
| Mock-only package (no public counterpart) | Download-aggregation response includes a package name never referenced elsewhere in the mock fixtures | Adapter returns its row like any other — CAP-1 does not classify or flag it; the internal/private flag is Story 15.2's job, not this adapter's | No error expected |
| Duplicate name+version rows across repos | Raw download response has two rows for the same `(name, version)` — one per backing repo, with different counts | Output has exactly one row for that `(name, version)` whose count is the sum of both | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/__init__.py` -- new package
  marker; re-exports the public adapter surface (mirrors `factory/__init__.py`'s re-export shape).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/aql_adapter.py` -- new module;
  the `ArtifactoryAqlAdapter` class + `ArtifactoryConfig`/`AqlRequest`/`AqlResponse`/`AqlTransport`
  + `ArtifactoryAqlError` + `DownloadRow`. Reference shape:
  `src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/lasuite.py` (read this file first —
  it is the pattern this module must follow: injectable transport, default-refuses, dataclass
  request/response, a clear-message error class extending `PyforgeError`).
- `src/shared/packages/pyforge-atlas/tests/artifactory/__init__.py` -- new test package marker.
- `src/shared/packages/pyforge-atlas/tests/artifactory/test_aql_adapter.py` -- new tests. Reference
  shape: `src/shared/packages/pyforge-atlas/tests/factory/test_lasuite.py` (an in-memory mock
  transport class routing on method+URL, one test per I/O Matrix row above).
- `src/shared/packages/pyforge-core/src/pyforge/core/errors.py` -- `PyforgeError` base class the
  new error type must extend (read-only reference, not modified by this story).

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/aql_adapter.py` -- create
  the module: `ArtifactoryConfig` (frozen dataclass, `base_url: str` only — no credential field);
  `AqlRequest`/`AqlResponse` frozen dataclasses (method, url, body/status_code/body, mirroring
  `Request`/`Response` in `lasuite.py`); `AqlTransport = Callable[[AqlRequest], AqlResponse]`;
  a default transport function that raises `ArtifactoryAqlError` naming the attempted method+URL;
  `ArtifactoryAqlError(PyforgeError, RuntimeError)`; `DownloadRow` (frozen dataclass: `name`,
  `version`, `download_count`); `ArtifactoryAqlAdapter` with `__init__(self, config, *,
  transport=<default>)`, `resolve_backing_repos(virtual_repo: str) -> list[str]`,
  `fetch_download_rows(virtual_repo: str) -> list[DownloadRow]` (calls `resolve_backing_repos`
  then issues the download-aggregation call then groups+sums by `(name, version)`) -- the sole new
  capability this story adds.
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/__init__.py` -- re-export
  `ArtifactoryAqlAdapter`, `ArtifactoryConfig`, `ArtifactoryAqlError`, `AqlRequest`, `AqlResponse`,
  `DownloadRow` -- gives Story 15.2/15.3 one clean import surface.
- [x] `src/shared/packages/pyforge-atlas/tests/artifactory/__init__.py` -- empty test package
  marker (mirrors `tests/factory/__init__.py`).
- [x] `src/shared/packages/pyforge-atlas/tests/artifactory/test_aql_adapter.py` -- an in-memory
  mock transport (routes on method + URL path, like `MockWagtail`) plus one test per I/O Matrix
  row: default-transport-refuses, non-2xx raises with status+body in the message, happy-path
  topology-resolution + name+version aggregation, single-backing-repo case, mock-only package
  passes through unflagged, duplicate name+version rows across repos sum into one row -- proves
  the whole CAP-1 success signal offline.

**Acceptance Criteria:**
- Given a mock AQL transport serving canned topology + download responses, when
  `fetch_download_rows(virtual_repo)` runs, then it resolves the virtual repo to its backing
  repositories and returns rows aggregated by package name + version with counts summed across
  backing repos and duplicate raw rows.
- Given `ArtifactoryAqlAdapter` constructed with no transport injected, when any method that would
  issue a call is invoked, then it raises `ArtifactoryAqlError` immediately, naming the attempted
  method + URL, with no network attempt made.
- Given the full test suite for this module, when it runs, then no test path constructs or
  imports a real HTTP client (`requests`/`httpx`/`urllib3`/etc.) — verified both by this story's
  own tests using only the in-memory mock transport, and by the pre-existing repo-wide
  `test_no_inline_io_in_package_code` gate covering the new module automatically.
- Given `pixi run -e pyforge-atlas kedro-test` and `pixi run -e pyforge-atlas kedro-catalog-check`,
  when run after this story's changes, then both pass with no modifications needed to either gate
  (the new package/module needs no new exemption or allowlist entry anywhere).

## Spec Change Log

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 2, low 4)
- defer: 1: (high 0, medium 1, low 0)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[medium]` `[patch]` Malformed download rows (missing `name`/`version`/non-numeric `count`) raised a raw `KeyError`/`TypeError`/`ValueError` instead of the module's own `ArtifactoryAqlError` contract — wrapped row extraction in `fetch_download_rows` with a clear error naming the virtual repo and the malformed row; added `test_malformed_download_row_raises_clear_error`.
  - `[medium]` `[patch]` A `None`/non-string entry in a topology response's `repositories` list silently coerced to the literal string `"None"` via `str(r)` instead of failing — `resolve_backing_repos` now validates every entry is already a `str` and raises `ArtifactoryAqlError` otherwise; added `test_non_string_backing_repo_entry_raises_clear_error`.
  - `[low]` `[patch]` `fetch_download_rows` sorted `(name, version)` pairs lexically (`sorted(totals.items())`), which silently misorders multi-digit versions (e.g. `"10.0"` before `"2.0"`) while implying a meaningful order it doesn't provide — switched to plain first-seen (insertion) order, which is deterministic without claiming semantic ordering; existing test fixtures' expected order was unaffected (insertion order already matched).
  - `[low]` `[patch]` The test file's `MockArtifactory.__call__` routed on `request.url.split("/api", 1)[-1]`, a substring split fragile to a host containing the literal text `/api` (e.g. an `api.` subdomain) — switched to `urlparse(request.url).path`.
  - `[low]` `[patch]` `test_mock_only_package_passes_through_unflagged`'s `hasattr(rows[0], "internal"/"private")` assertions were tautological (guaranteed by `DownloadRow`'s fixed dataclass fields for any input, not specific to a mock-only package) — removed them; the existing `rows == [DownloadRow(...)]` equality assertion already proves the intended "flows through like any other row" behavior.
  - `[low]` `[patch]` The module docstring claimed to follow "the exact shape proven by LaSuiteClient" while intentionally omitting `LaSuiteConfig`'s env-driven resolver (a deliberate choice per this spec's Design Notes) — softened the wording to "the same injectable-transport pattern" and added a pointer to `ArtifactoryConfig`'s docstring for why no resolver exists.
  - `[medium]` `[defer]` Epic 15's `spec-artifactory-download-intelligence` SPEC.md's `surface:` glob matches zero real tracked files (a pre-existing `scripts/spec_surface_check.py::glob_to_re` anchoring gap for wildcard-less directory patterns), leaving the whole epic invisible to the repo's spec-surface drift gate — pre-existing, not touched by this diff; deferred as `DW-FU-15-1`.
  - `[reject x8]` Real-AQL-query-syntax fidelity (explicitly out of scope per this spec's own Design Notes — mock-first, no wire format pinned); empty backing-repos list handling (a valid degenerate case, not a defect); negative download-count validation (speculative business-value validation beyond spec scope); pagination handling (explicitly deferred to the out-of-scope live bring-up); unwrapped injected-transport exceptions, unvalidated `AqlResponse.status_code` type, un-quoted `virtual_repo` path segment, and unvalidated `base_url` scheme (all four match `lasuite.py`'s own established reference behavior exactly — not a deviation this story introduced).

## Design Notes

`ArtifactoryConfig` intentionally carries only `base_url` — no `resolve_artifactory_config()` env
resolver and no token field are added in this story. `LaSuiteConfig` resolves a bearer token from
env because CMS auth is exactly that simple; Artifactory's real auth shape (API key header, or
routing through the JFrog chain some future live opener will use) is explicitly undecided and out
of scope here (Spec § Open Questions: "which live instance… outside this Spec"). Introducing a
config/env resolver now would be inventing exactly the kind of bespoke credential surface the
Boundaries section forbids. Tests construct `ArtifactoryConfig` directly with a dummy `base_url`,
exactly as `tests/factory/test_lasuite.py` constructs a dummy `LaSuiteConfig`.

The two-call shape (`resolve_backing_repos` then the download-aggregation call) is a design choice
for THIS story, not a contract pinned to any real Artifactory AQL wire format — CAP-1's success
signal only requires that virtual-repo topology is resolved to backing repos and that download
rows come out name+version-aggregated; the exact mock request/response bodies are this story's own
fixtures, invented for the mock, not a real Artifactory schema (none exists to match against —
this Spec is explicitly mock-first with no named instance).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` -- expected: full suite passes, including the new
  `tests/artifactory/test_aql_adapter.py`.
- `pixi run -e pyforge-atlas kedro-catalog-check` -- expected: passes unchanged, confirming the
  no-inline-IO / AD-1 import-direction scan covers the new module with zero HTTP-client imports
  and no orchestration-lib imports.

## Auto Run Result

Status: done

**Summary:** Implemented Story 15.1 (CAP-1) — a standalone, mock-only, network-injectable
`ArtifactoryAqlAdapter` following `lasuite.py`'s injectable-transport shape. Resolves a virtual
repo's backing repos, then aggregates download counts by name+version. Lands in a new top-level
`pyforge.atlas.artifactory` package (not under `pipelines/`, which would break Kedro's
`find_pipelines(raise_errors=True)` — a landmine identified during planning). No credential
code, no pipeline wiring, no identity join — those stay out of scope per the intent-contract.

**Files changed:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/aql_adapter.py` (new) --
  `ArtifactoryConfig`, `AqlRequest`/`AqlResponse`/`AqlTransport`, `ArtifactoryAqlError`,
  `DownloadRow`, `ArtifactoryAqlAdapter` (`resolve_backing_repos`, `fetch_download_rows`).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/__init__.py` (new) --
  re-exports the public surface for Stories 15.2/15.3.
- `src/shared/packages/pyforge-atlas/tests/artifactory/__init__.py` (new) -- test package marker.
- `src/shared/packages/pyforge-atlas/tests/artifactory/test_aql_adapter.py` (new) -- 8 tests
  (6 from the spec's I/O Matrix + 2 added during review for the new validation paths).

**Review findings breakdown (Blind Hunter + Edge Case Hunter, parallel, no shared context):**
6 patch (2 medium, 4 low) -- all auto-fixed: malformed-row error wrapping, non-string backing-repo
validation, dropped the misleading lexical version-sort in favor of plain insertion order, fixed
the test mock's fragile URL-substring routing, removed a tautological test assertion pair,
softened an overclaiming docstring line. 1 defer (medium) -- `DW-FU-15-1`: Epic 15's SPEC.md
`surface:` glob matches zero real files (a pre-existing `spec_surface_check.py` anchoring gap),
pre-existing and not caused by this diff. 8 reject -- speculative/out-of-scope hardening (real-AQL
wire-format fidelity, negative-count/status-code/URL-quoting/scheme validation, pagination,
unwrapped-transport-exception handling) that either matches `lasuite.py`'s own established
reference behavior or is explicitly out of scope per this spec's Design Notes.

**Follow-up review recommendation:** false -- the patched findings are localized, low-to-medium
severity, mechanical fixes with no API/behavior/security/data-model surface change.

**Verification performed:**
- `pixi run -e pyforge-atlas kedro-test` -- 1149 passed, 19 skipped (re-run after patches; up
  from 1147 passed before, the 2 new validation tests).
- `pixi run -e pyforge-atlas kedro-catalog-check` -- 48 passed, unchanged (no-inline-IO / AD-1
  scan covers the new module automatically, zero HTTP-client imports).
- Manually verified `pyforge.atlas.pipeline_registry.register_pipelines()` returns the identical
  9-pipeline set before and after this diff, confirming the new `artifactory/` package is
  correctly invisible to Kedro's `find_pipelines` (the landmine this story's Design Notes flagged).

**Residual risks:** None blocking. `DW-FU-15-1` (pre-existing spec-surface glob gap) is deferred
to the ledger. The adapter's request/response wire shape is intentionally invented for the mock
(no real Artifactory instance exists to match against yet, per the Spec's own mock-first
constraint) — Story 15.3's live bring-up will need to reconcile it against whatever real AQL
shape is eventually chosen, which is explicitly out of this story's scope.
