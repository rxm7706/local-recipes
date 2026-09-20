---
title: 'Asymmetric receipts, partial failure, and idempotence'
type: 'feature'
created: '2026-08-14'
status: 'done'
baseline_revision: '4219f1dea4d7f61ce8fa7c70c53053d4c44232d3'
final_revision: '462a3f0f291ec531aeb8cd4e6cee586b4c614778'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/src/shared/packages/pyforge-mason/src/pyforge/mason/package.py'
  - '{project-root}/src/shared/packages/pyforge-mason/src/pyforge/mason/models.py'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `ship_pypi`/`ship_channel` (Stories 3.4/3.5) each return a bare `ShipTargetResult` and
always attempt an upload -- nothing asks the target itself "is this already shipped?" first (AD-10),
so a retry of a successful ship either crashes on PyPI's duplicate-file rejection or silently
re-uploads. No `ShipReceipt` aggregate exists either (AD-9).

**Approach:** Add `ShipReceipt` (models.py): `targets` plus a pre-computed `ok` field (AD-9's
aggregate rule). Add idempotence-by-interrogation, run after build (needs the built version) and
before upload, in both `ship_pypi`/`ship_channel`: a new `pypi_index.py` module queries PyPI's JSON
index via `urllib.request` (the one file the credential-isolation guard's own docstring
pre-authorizes for this); `engines/pixi.py` gains a `search()` query; a new `engines/gh.py` adapter
searches the CFE fork for an open `add-recipe-<name>` PR, built and unit-tested standalone since
`ship_conda_forge` does not exist in this branch's lineage yet (see Never).

## Boundaries & Constraints

**Always:**
- `ShipReceipt` (models.py, frozen dataclass): `targets: tuple[ShipTargetResult, ...]`, `ok: bool`.
  `ok` is a plain FIELD (AD-1: data carries no behaviour), computed once by a new
  `package.py::build_ship_receipt(results) -> ShipReceipt` helper as `not any(r.state is
  ShipState.FAILED for r in results)` (AD-9: `not_attempted`/`pending`/`terminal` all count success).
- Interrogation runs strictly AFTER `build()` (needs the built version) and BEFORE the upload call,
  in both `ship_pypi`/`ship_channel` -- never before the existing credential check, which stays
  first (AD-14 precedent, unchanged). Uniform three-way outcome: found -> skip upload, return
  `TERMINAL` with the pre-existing reference; not-found -> upload proceeds exactly as today;
  undeterminable -> return `PENDING` naming the reason, upload never attempted (AD-10: "never an
  assumption in either direction").
- `pypi_index.py::version_exists(name, version, *, timeout=None) -> bool | None` -- the ONLY module
  under `pyforge/mason/` permitted to import `urllib.request` (credential-isolation Guard 2's own
  docstring: "Epic 3 is expected to add scoped, non-CFE HTTP capability... must loosen this guard
  explicitly when that story lands"); `requests`/`httpx`/`http.client` stay banned everywhere,
  including this file. GET `https://pypi.org/pypi/<name>/<version>/json`: 200 -> `True`, 404 ->
  `False`, anything else (timeout, other status, `URLError`) -> `None`. `name` is re-derived from
  `build_result.wheel_path`'s filename via `packaging.utils.parse_wheel_filename` (the same parse
  `engines/pep517.py` already trusts) -- `PackageBuildResult` itself is untouched.
- `engines/pixi.py::search(name, version, channel, *, timeout=None) -> bool | None` runs `pixi
  search --channel <channel> <name>==<version> --json`: exit 0 -> `True`; exit non-zero whose
  stderr contains `"No packages found"` -> `False`; anything else (absent engine, timeout, other
  failure) -> `None`. `name` is re-derived from `build_result.conda_path`'s filename via the same
  `stem.rsplit("-", 2)` technique `engines/pixi.py::build` already uses.
- `engines/gh.py` (new adapter, `name = "gh"`, `probe()`) registered in `engines/__init__.py`'s
  `_KNOWN_ENGINES`/`_ENGINE_CONDA_PACKAGES` (conda package `gh`) and `pixi.toml`
  (`gh = ">=2.97.0,<2.98"`) exactly like the four existing engines -- `mason doctor` picks it up
  automatically via the existing `probe_known_engines()` call (`doctor.py` unedited).
  `find_open_pr(repo, head_branch, *, timeout=None) -> OpenPrSearchResult` (new dataclass:
  `found: bool | None`, `url: str | None`) runs `gh pr list --repo <repo> --head <head_branch>
  --state open --json number,url`. Uses `probe_engine` (never `require_engine`) so a missing `gh`
  degrades to `found=None, url=None` rather than raising `EngineAbsentError` -- matches every other
  "cannot be interrogated" path (AD-10).
- `ship_pypi`'s interrogation-found `reference` is `f"https://pypi.org/project/{name}/{version}/"`
  (mirrors the shape `twine`'s own "View at:" URL already produces). `ship_channel`'s
  interrogation-found `reference` is the bare `channel_name` (matches its existing non-interrogation
  `TERMINAL` precedent, Story 3.5).
- New engine registration mirrors the existing four byte-for-byte: `_KNOWN_ENGINES`/
  `_ENGINE_CONDA_PACKAGES` entries, a `GH_VERSION_RANGE` `SpecifierSet` via `_minor_range`, a
  `pixi.toml` run-dependency line, and `tests/meta/test_engine_version_range_sync.py` extended with
  the same five assertion shapes (found/range/no-widen/evidence/ranges-not-pins) the other four
  engines already have.

**Block If:** none -- D-11/AD-10 name the exact three interrogation mechanisms (index query, channel
query, fork PR search) and D-9's argparse/lean-dependency stance already resolves HOW (subprocess
adapters + the one guard-pre-authorized stdlib HTTP exception); no unattended decision point remains.

**Never:**
- No `ship_conda_forge` changes and no wiring of `engines/gh.py::find_open_pr` into any ship
  function -- `ship_conda_forge` (Story 3.6) does not exist in this branch's lineage (a sibling,
  not-yet-merged worktree branched from the same point). `find_open_pr` is built and unit-tested
  standalone, ready for that wiring once the branches converge. Disclosed scope boundary, not an
  oversight.
- No `ship()` multi-target dispatcher, no CLI wiring, no `cli.py` exit-code aggregation -- `cli.py`'s
  `ship` verb (Story 3.9) is in the same situation. `build_ship_receipt`/`ShipReceipt.ok` are the
  tested, ready-to-call primitives for whichever caller reaches them after merge.
- No local persistence of any interrogation result -- AD-10 forbids a state directory, receipt
  cache, or lock file; every ship pays its own query round-trip (D-11's accepted tradeoff).
- No credential/token handling for GitHub -- `gh` handles its own auth exactly as `twine`/`pixi`
  already handle theirs; Mason never reads a `GH_TOKEN`/`GITHUB_TOKEN` value anywhere.
- No change to `ship_pypi`/`ship_channel`'s credential-check-first ordering, their existing public
  parameters, or their `FAILED`-path behavior when the build itself produces no artifact.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PyPI already shipped | build succeeds, `version_exists` -> `True` | `TERMINAL`, reference = project URL; `twine.upload` never called | No error |
| PyPI not yet shipped | `version_exists` -> `False` | unchanged: `twine.upload` runs, `TERMINAL`/`FAILED` per its returncode | No error |
| PyPI interrogation undeterminable | `version_exists` -> `None` (timeout/network) | `PENDING` naming the reason; `twine.upload` never called | Data, not raised |
| Channel already shipped | `pixi.search` -> `True` | `TERMINAL`, reference = `channel_name`; `pixi.upload` never called | No error |
| Channel interrogation undeterminable | `pixi.search` -> `None` | `PENDING` naming the reason; `pixi.upload` never called | Data, not raised |
| conda-forge open PR found | `gh pr list` returns one match | `OpenPrSearchResult(found=True, url=...)` (unwired caller) | No error |
| conda-forge, `gh` absent | `gh` not on `PATH` | `OpenPrSearchResult(found=None, url=None)` | Never raises |
| Receipt aggregate, mixed success | targets = (`TERMINAL`, `PENDING`) | `ShipReceipt.ok is True` | -- |
| Receipt aggregate, one failure | targets = (`TERMINAL`, `FAILED`) | `ShipReceipt.ok is False` | -- |

</intent-contract>

## Code Map

- `src/pyforge/mason/models.py` -- add `ShipReceipt` (`targets`, `ok`).
- `src/pyforge/mason/pypi_index.py` -- NEW. `version_exists()`.
- `src/pyforge/mason/engines/pixi.py` -- add `search()`.
- `src/pyforge/mason/engines/gh.py` -- NEW adapter: `name`, `probe()`, `OpenPrSearchResult`,
  `find_open_pr()`.
- `src/pyforge/mason/engines/__init__.py` -- register `gh` in `_KNOWN_ENGINES`/
  `_ENGINE_CONDA_PACKAGES`; add `GH_VERSION_RANGE`.
- `src/pyforge/mason/package.py` -- wire interrogation into `ship_pypi`/`ship_channel`; add
  `build_ship_receipt()`.
- `pixi.toml` (package-level) -- add `gh = ">=2.97.0,<2.98"` run-dependency.
- `tests/meta/test_credential_isolation.py` -- Guard 2 gains a narrow per-(file, module) allowlist:
  `urllib.request` permitted ONLY in `pypi_index.py`; `requests`/`httpx`/`http.client` stay banned
  there too. Update module docstring's "Epic 3... must loosen this guard explicitly" note to record
  that this story is the one doing so.
- `tests/meta/test_engine_version_range_sync.py` -- extend for `gh`/`GH_VERSION_RANGE`.
- `tests/unit/test_models.py`, `tests/unit/test_pypi_index.py` (new), `tests/unit/test_engines_pixi.py`,
  `tests/unit/test_engines_gh.py` (new), `tests/unit/test_package.py` -- coverage.

## Tasks & Acceptance

**Execution:**
- [x] `models.py` -- add `ShipReceipt(targets: tuple[ShipTargetResult, ...], ok: bool)`, frozen,
  docstring citing AD-9.
- [x] `pypi_index.py` (new) -- `version_exists(name, version, *, timeout=None) -> bool | None` via
  `urllib.request.urlopen`; catch `HTTPError` (404 -> `False`), `URLError`/`OSError`/`TimeoutError`
  -> `None`; module docstring documents the credential-isolation guard exemption.
- [x] `engines/pixi.py` -- add `search(name, version, channel, *, timeout=None) -> bool | None`;
  parse stderr for `"No packages found"` to distinguish conclusive-absent from undeterminable.
- [x] `engines/gh.py` (new) -- `name = "gh"`, `probe()` (mirrors `engines/pixi.py`'s), `@dataclass
  class OpenPrSearchResult(found: bool | None, url: str | None)`, `find_open_pr(repo, head_branch,
  *, timeout=None)`; uses `probe_engine`, never `require_engine`.
- [x] `engines/__init__.py` -- add `"gh": "gh"` to both dicts; add `GH_VERSION_RANGE =
  _minor_range("2.97.0", "2.98")`.
- [x] `pixi.toml` -- add the `gh` run-dependency line + comment update naming the fifth engine.
- [x] `package.py::ship_pypi` -- after the wheel/sdist presence check, before `twine.upload`: derive
  `(name, _, _, _) = parse_wheel_filename(...)`, call `pypi_index.version_exists(str(name),
  build_result.wheel_version)`, branch per the Always boundary's three-way outcome.
- [x] `package.py::ship_channel` -- mirror the same shape using `engines.pixi.search`.
- [x] `package.py` -- add `build_ship_receipt(results: Sequence[ShipTargetResult]) -> ShipReceipt`.
- [x] `tests/meta/test_credential_isolation.py` -- allowlist mechanism + regression test proving
  `requests`/`httpx`/`http.client` are still banned in `pypi_index.py`, and `urllib.request` is
  still banned in every OTHER file (anti-shrink floor, mirroring this file's own established
  pattern).
- [x] `tests/meta/test_engine_version_range_sync.py` -- the same five `gh` assertions the other four
  engines have.
- [x] Unit tests (new/extended files above) -- cover every I/O matrix row; `ship_pypi`/`ship_channel`
  tests mock `pypi_index.version_exists`/`engines.pixi.search` at `package.py`'s own import
  namespace (established `unittest.mock.patch` convention, e.g. `test_package.py`'s existing
  `patch("pyforge.mason.package.build", ...)` style).

**Acceptance Criteria:**
- Given a multi-target ship, when a `ShipReceipt` is built, then every target carries an explicit
  `state` and `reference`, and `ok` is `False` iff any target is `FAILED`.
- Given `pypi`/`channel:<name>` shipped once successfully, when shipped again with identical inputs,
  then no second upload is attempted and the result is `TERMINAL` with the same kind of reference a
  fresh success would carry.
- Given a target that cannot be interrogated (network/timeout/absent tool), when the ship runs, then
  the result is `PENDING` naming the reason, and the mutating upload call is never made.
- Given the codebase is inspected, then no module outside `pypi_index.py` imports `urllib.request`,
  `requests`, `httpx`, or `http.client` anywhere under `src/pyforge/mason/`.
- Given `mason doctor` runs, then its `engines` field includes `gh`'s presence/version with no
  `doctor.py` source change.

## Review Triage Log

### 2026-08-14 — Review pass 1
- intent_gap: 0
- bad_spec: 0
- patch: 2: (medium 1, low 1)
- defer: 3: (medium 2, low 1)
- reject: 9: (low 9)
- addressed_findings:
  - `[medium]` `[patch]` `engines.pixi.search()` trusted a zero `pixi search` returncode alone,
    never parsing the `--json` stdout body -- unlike its sibling `engines.gh.find_open_pr()`, which
    does validate its own JSON body. Raised by Edge Case Hunter. Fixed: `search()` now parses the
    body and requires at least one non-empty per-platform entry list before returning `True`;
    unparseable/non-dict/all-empty bodies fold into `None` (undeterminable), matching every other
    branch's existing convention. Three new tests added.
  - `[low]` `[patch]` `engines.gh.find_open_pr()` had no test for a matching PR entry that omits the
    `url` key (the code already handles it gracefully via `.get("url")`, a coverage gap only).
    Raised by Blind Hunter. Fixed: one regression test added asserting `found=True, url=None`.
  - **Rejected** (matches established precedent, spec-directed, or unreachable via the only real
    caller): (1) three of Story 3.7's own seven epic ACs (rendering both success+pending, aggregate
    exit code, partial-failure continuation) have no test coverage in this diff -- explicitly the
    spec's own disclosed Never boundary (no `ship()`/CLI wiring exists in this branch's lineage
    yet); (2) `engines.gh.find_open_pr` is fully built and tested but has zero production callers --
    same disclosed boundary (`ship_conda_forge` does not exist in this branch); (3) the Guard 2
    allowlist/ceiling anti-widen test is a hand-authored pair that can't stop a single lockstep
    edit -- matches this same file's own pre-existing, already-accepted `_REQUIRED_HTTP_IMPORTS`-
    style floor pattern used throughout it; (4) `engines.pixi.search()`'s `"No packages found"`
    stderr substring match is brittle against a future `pixi` wording change -- spec-directed
    (Design Notes, live-verified), and a drift degrades to the SAFE `None`/`PENDING` outcome, never
    a false skip; (5) `pypi_index.version_exists`'s URL is built with no `urllib.parse.quote`,
    and a control character in `name`/`version` would raise `http.client.InvalidURL`, escaping its
    documented never-raises contract -- unreachable via its only real caller (`ship_pypi`), whose
    `name`/`version` always come from `packaging.utils.parse_wheel_filename`'s own validated parse;
    matches this codebase's established "trust the caller discipline" precedent (e.g. spec-3-6's
    own identical rejection class); (6) `ShipReceipt.ok` reports `True` for an all-`PENDING`
    aggregate -- explicitly spec-directed, matching AD-9's own literal architecture text ("success
    if every target reached pending or terminal"); (7) `ship_pypi`/`ship_channel` re-derive the
    package name from the built artifact's filename instead of adding a name field to
    `PackageBuildResult` -- explicitly spec-directed, matching the identical "redundant but cheap,
    pure resolution functions called freely" precedent already established (and already rejected on
    the same grounds) in spec-3-6's own review history; (8) `ship_pypi`'s reconstructed
    already-shipped URL uses the PEP-503-canonicalized name rather than a tool-reported verbatim
    field -- AD-1's "verbatim" rule governs a WRAPPED TOOL's own reported field, and no tool ran on
    this path (twine was skipped); the constructed URL still resolves correctly regardless of
    original casing; (9) the Guard 2 allowlist keys off a bare filename, not a resolved path, so any
    file literally named `pypi_index.py` anywhere in the tree would be exempted -- matches this same
    file's own existing `cfe.py` special-case precedent, which the file's own docstring already
    documents accepting for the identical reason (a single well-known module name, not a realistic
    collision risk).
- **Deferred** (tracked station `pyforge-mason`, base id `DW-3-7`; full entries in
  `deferred-work.md`):
  - `[medium]` `[defer]` **`DW-3-7-1`** -- a concurrent ship of the same name+version between
    interrogation returning `False` and the upload call reports `FAILED`, not `TERMINAL`, for the
    race's loser (TOCTOU). Raised independently by both reviewers. Not patched: narrows, but does
    not eliminate, an ambiguity (`upload()` failing because the artifact already exists vs. failing
    for a real reason) that pre-dates this story on every retry; a proper fix needs target-specific
    duplicate-rejection detection in `engines.twine.upload`/`engines.pixi.upload` themselves.
  - `[medium]` `[defer]` **`DW-3-7-2`** -- `pypi_index.version_exists` always queries public
    `pypi.org`, even when the caller's inherited environment points the real `twine upload` at a
    different repository via `TWINE_REPOSITORY_URL`. Raised by Edge Case Hunter. Not patched: no
    repository-selection knob exists anywhere in this branch yet for `ship_pypi`/`twine.upload`
    either; `pypi_index.py`'s scope is explicitly the public index (module docstring, spec Intent).
  - `[low]` `[defer]` **`DW-3-7-3`** -- `ship_pypi`'s interrogation trusts the wheel filename's
    identity alone, never cross-validated against the sdist filename, so a mismatched dirty-`dist/`
    pair could have its skip-or-upload decision made against the wrong project. Raised by Edge Case
    Hunter. Not patched: the root cause (`engines.pep517`'s per-glob, no-cross-check artifact
    discovery) pre-dates this story and belongs in that module, not a `package.py`-only patch.

## Design Notes

**Why `gh` CLI instead of raw GitHub REST API + token:** `gh pr list --head <branch>` accepts a bare
branch name (no owner prefix required, confirmed live: `gh pr list --help`), so the fork owner never
needs to be known or looked up. `gh` also owns its own authentication exactly as `twine`/`pixi` own
theirs, preserving AD-14's credential-blindness property without Mason ever touching a token. This
matches AD-12's adapter convention (every external tool is a `PATH`-discovered subprocess adapter)
better than a bespoke authenticated HTTP client would.

**Why `pixi search` instead of an HTTP channel query:** `ship_channel`'s own Story 3.5 docstring
already notes "no equivalent live-verified URL exists to parse" for a channel destination. `pixi
search --channel <name> <spec> --json` is live-verified in this environment (exit 0 + JSON when
found, exit 1 + `"No packages found"` when not) and reuses the already-required `pixi` engine --
zero new dependency, unlike a bespoke prefix.dev API client would be.

**Why conda-forge interrogation ships unwired:** `ship_conda_forge` (Story 3.6) and the `ship()`
dispatcher (Story 3.9) both exist only in sibling worktrees not yet merged into this branch's
lineage -- confirmed via each spec's `baseline_revision`/git log. Building `find_open_pr` standalone,
fully tested, realizes FR-18's third bullet and AD-10's conda-forge mechanism now; wiring it into
`ship_conda_forge` is mechanical once the branches converge and is out of this diff's reach today.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `03d8fc8c86` (2026-08-14, "recover mason 3.7 (asymmetric receipts, partial failure and idempotence) from run 20260813-145934-3eb0's faile"); also `aa5025ba3d` (2026-08-04, "marshal: refresh dashboard after Story 3.7 lands, run paused"); also `94ba58a96d` (2026-08-03, "marshal: review pass 2 fixes for escalation, deferral, and resume (Story 3.7)"). Ledger row `3-7-asymmetric-receipts-partial-failure-and-idempotence: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `pixi.lock`, `src/shared/packages/pyforge-mason/pixi.toml`, `src/shared/packages/pyforge-mason/src/pyforge/mason/engines/__init__.py`, `src/shared/packages/pyforge-mason/src/pyforge/mason/engines/gh.py`, `src/shared/packages/pyforge-mason/src/pyforge/mason/engines/pixi.py`, `src/shared/packages/pyforge-mason/src/pyforge/mason/models.py`, `src/shared/packages/pyforge-mason/src/pyforge/mason/package.py`, `src/shared/packages/pyforge-mason/src/pyforge/mason/pypi_index.py`, `src/shared/packages/pyforge-mason/tests/meta/test_credential_isolation.py`, `src/shared/packages/pyforge-mason/tests/meta/test_engine_version_range_sync.py`, `src/shared/packages/pyforge-mason/tests/unit/test_doctor.py`, `src/shared/packages/pyforge-mason/tests/unit/test_engines.py` (+5 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `in-progress` → `done` (ledger row `3-7-asymmetric-receipts-partial-failure-and-idempotence: done`).
- `## Auto Run Result` reconstructed from git (none survived).
