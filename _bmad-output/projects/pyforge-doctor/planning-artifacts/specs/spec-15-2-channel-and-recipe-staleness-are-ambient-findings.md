---
title: 'Channel and recipe staleness are ambient findings'
type: 'feature'
created: '2026-08-22'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: true
context: []
warnings: [oversized]
deferred:
  - summary: >-
      Story 15.2's two new checks fire only for suite packages already
      present in `.pixi/envs` (inherited from `_gather_suite_findings`'s
      pre-existing install-state gate), so on a fresh clone/CI with no local
      suite installs, neither new check fires for any suite package -- only
      the CORE (`bmad-method`) axis is unaffected, since it reads the
      tracked `manifest.yaml` instead.
    evidence: |-
      Edge Case Hunter (Story 15.2 review): `_gather_suite_findings` returns
      `()` immediately when `_installed_suite_versions` is empty, and skips
      any package absent from `installed` inside the loop -- both
      pre-existing Story 14.1 gates that Story 15.2's new checks inherit by
      extension rather than by new design. The story's own named fixture
      (the 6.3.0 relic) is specifically about the CORE package, which is
      unaffected; the gap is narrower, scoped to suite packages only.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py:_gather_suite_findings
    severity: medium
  - summary: >-
      No dedicated fleet-picture-layer meta-test names `bmad-channel-drift`
      or `bmad-recipe-upstream-drift` specifically -- coverage of that named
      Surface is structural/generic only.
    evidence: |-
      Blind Hunter and Intent Alignment Auditor (review pass 2, independently
      convergent): `.claude/skills/conda-forge-expert/tests/meta/
      test_fleet_picture_bmad_core_drift.py`'s existing
      `test_both_cap1_and_cap2_warn_simultaneously` already proves the
      generic pass-through mechanism (any WARN Finding under
      `Source.BMAD_METHOD_VERSION_DRIFT` reaches ATTENTION regardless of
      `check` name), matching the precedent set by Stories 10.3/14.1/15.1,
      none of which added a per-check fleet-picture test either.
    location: >-
      .claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_bmad_core_drift.py
    severity: low
baseline_revision: '585d1799199bb7e29c9a3134bc373f13ce5632db'
---

<intent-contract>

## Intent

**Problem:** Doctor's suite pass (`sources/bmad_method.py`, CAP-4/Story 15.1) only compares
INSTALLED bmad packages against upstream. It never checks whether the SelfExplainML anaconda.org
channel actually serves what `recipes/<name>/recipe.yaml` declares, or whether that recipe itself
has caught up to upstream -- the channel served a stale `bmad-method 6.3.0` for four months with
no ambient signal (`spec-bmad-suite-channel-product` CAP-5, steward-owned publishing, relayed here
for detection).

**Approach:** Add two new fail-open, warn-only checks to the SAME `bmad-method-version-drift`
Source, for every package this module already watches (the CORE `bmad-method` plus every
`_suite_packages`-derived pin) whose upstream-latest is already known from the EXISTING fetch in
that package's call site (never re-fetched): `bmad-channel-drift` (channel version behind the
recipe's declared version -- reproduces the 6.3.0 relic) and `bmad-recipe-upstream-drift` (recipe
version behind upstream). Channel version comes from `GET https://api.anaconda.org/package/
SelfExplainML/{package}`'s `latest_version` field (unauthenticated, mirrors `_NPM_LATEST_URL`'s
precedent); recipe version comes from `recipes/{package}/recipe.yaml`'s `context.version` (local
read, mirrors `_github_owner_repo`'s existing recipe-read pattern).

## Boundaries & Constraints

**Always:**
- Both checks fire ONLY for a package whose upstream-latest was already resolved at that call site
  (CAP-2's `latest_upstream` for CORE; the suite loop's post-GitHub-fallback `latest` for suite
  packages) -- never a third independent upstream fetch.
- Recipe version and channel version are each parsed with the existing LENIENT
  `_parse_release_triple` (not the strict `_parse_version`) -- symmetric with `latest_upstream`'s
  own suite-side parsing and with the six `.dev0`-pinned suite recipes.
- Entirely fail-open per package per axis: a missing/unparseable `recipe.yaml` or `context.version`
  skips BOTH new findings for that package; the channel fetch failing (network error, 404, malformed
  body) skips only `bmad-channel-drift` -- neither ever affects CAP-1/CAP-2/CAP-4's own Findings.
- Suite-side channel fetches stay inside `_gather_suite_findings`'s existing shared
  `_SUITE_FETCH_TOTAL_BUDGET_SECONDS` deadline (`min(remaining, _UPSTREAM_FETCH_TIMEOUT_SECONDS)`);
  the CORE-side fetch gets its own bounded `_UPSTREAM_FETCH_TIMEOUT_SECONDS` call, adding up to 5s
  to CAP-1/CAP-2's own worst case -- bump `scripts/fleet_picture.py::bmad_core_drift_findings`'s
  `timeout=15` (and its budget-arithmetic comment) proportionally, mirroring Story 14.1's own
  precedent of updating that exact function when the inner budget grew.
- Bare unauthenticated `urllib.request` GET only (no token, no subprocess) -- this module's
  independence rule.
- Update the three in-sync comment blocks (module docstring, `models.py`'s
  `BMAD_METHOD_VERSION_DRIFT` comment, `sources/__init__.py`'s matching registration comment) --
  existing contract this file already enforces by review, not a test.

**Block If:** None -- narrow extension of an existing fail-open pass with no undecided product
question.

**Never:**
- Never hardcode a package list -- reuse the EXISTING derived watched set
  (`(DEPENDENCY_NAME,) + _suite_packages(pixi_data)`), never a new one.
- Never persist fetched channel data (mirrors the module's no-local-persistence precedent).
- Never touch `recipes/**` (read-only) or CAP-1/CAP-2/CAP-4's own comparison logic.
- No new CLI flag, no new `Source` registry member, no new `sources/__main__.py` dispatch entry --
  rides `doctor check --bmad-core` / `fleet_picture.py`'s existing ATTENTION probe unchanged (both
  already consume `bmad_method.gather`'s full return tuple generically).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| The 6.3.0 relic (CORE) | channel `latest_version=6.3.0`, recipe `context.version=6.11.0` | `bmad-channel-drift` WARN naming `bmad-method` | n/a |
| Recipe behind upstream | recipe `context.version=0.10.0`, resolved upstream `0.11.0` | `bmad-recipe-upstream-drift` WARN | n/a |
| Channel, recipe, upstream all agree | equal triples | Neither new Finding fires | n/a |
| `recipe.yaml` missing or `context.version` absent/malformed | no file, or bad YAML | Both new findings skipped for that package | Fails open |
| Channel package not found | `api.anaconda.org` 404s | `bmad-channel-drift` skipped; `bmad-recipe-upstream-drift` still evaluated | Fails open |
| Upstream unresolved for a package (npm+GitHub both miss) | `latest`/`latest_upstream` is `None` | Neither new finding attempted for that package (no upstream to compare against) | Fails open |
| Offline / anaconda.org unreachable | `URLError`/timeout | No `bmad-channel-drift` findings anywhere; rest of `gather()` unaffected | Fails open, silent |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` -- add
  `_ANACONDA_CHANNEL = "SelfExplainML"` + `_ANACONDA_PACKAGE_URL` constants; `_recipe_version(target,
  package)` (reads `recipes/<package>/recipe.yaml`'s `context.version`, lenient-parsed, fails open
  exactly like `_github_owner_repo`'s try/except shape); `_fetch_channel_version(*, package,
  timeout=None)` (mirrors `_fetch_latest_upstream_version`'s fail-open GET, `latest_version` field,
  always lenient parse). Wire the two new comparisons at TWO call sites: (a) in `_gather()`, right
  after `latest_upstream` is confirmed non-`None` (~line 719); (b) in `_gather_suite_findings`'s
  per-package loop, right after `checked += 1` (~line 593), reusing that iteration's own `latest`.
  Factor the shared "build the two Findings given a resolved recipe/channel/upstream triple" logic
  into one small helper to avoid duplicating message/evidence shape across the two call sites. Update
  the module docstring's CAP-4/Story-15.1 paragraph with a Story 15.2 paragraph.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- extend
  `BMAD_METHOD_VERSION_DRIFT`'s comment (currently ends "...riding the same surfaces.") with one
  sentence for Story 15.2.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- extend the matching
  `SourceRegistration(source=Source.BMAD_METHOD_VERSION_DRIFT, ...)` trailing comment identically.
- `scripts/fleet_picture.py` -- `bmad_core_drift_findings`'s `timeout=15` default + its budget-margin
  comment (~line 114-122): bump to `timeout=25` (see budget-repair note below), and update
  `verification_staleness_findings`'s cross-reference comment (currently cites
  `bmad_core_drift_findings`'s value) to match.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` -- new tests (see
  Tasks). `_write_recipe_yaml` already supports a `context:\n  version: "X.Y.Z"\n` block trivially;
  reuse `_stub_fetch_by_package`/`_write_conda_meta`/`_FakeClock` fixtures already present.

**Budget repair (review pass 1, bad_spec):** `_SUITE_FETCH_TOTAL_BUDGET_SECONDS` (currently `5.0`,
unchanged since Story 14.1) must grow to `10.0` -- reviewers (Blind Hunter + Edge Case Hunter,
convergent) found that the suite loop's per-package channel fetch draws from this SAME shared pool
via the EXISTING `min(remaining, _UPSTREAM_FETCH_TIMEOUT_SECONDS)` formula the Boundaries above
already specify (unchanged), and an early package's slow channel fetch could exhaust the
still-5.0s-sized pool before later packages get even their PRE-EXISTING (Story 14.1) npm/GitHub
upstream check -- a coverage regression to an EXISTING check, not just a gap in the new one.
Doubling the pool to `10.0` (still governed by the SAME unchanged per-call formula) gives
meaningfully more headroom for the added fetch without touching how any individual fetch is
bounded. The CORE-side fetch is unaffected by this change (it never shared the suite loop's pool).
Cascades to `scripts/fleet_picture.py::bmad_core_drift_findings`: inner worst case becomes
`5 (CAP-2 npm) + 10 (suite loop, bumped) + 5 (CORE channel) = 20s`, so `timeout` becomes `25`
(preserving the same ~5s margin Story 14.1 established over the inner bound), with the comment's
arithmetic updated to match. Any test hardcoding the old `5.0` budget value in its own math (e.g. a
`5.0 - 2.0` deadline computation) must be updated to `10.0 - 2.0`.

## Tasks & Acceptance

**Execution:**
- `sources/bmad_method.py` -- add `_recipe_version` + `_fetch_channel_version` + URL/channel
  constants -- the two new fail-open primitives this story needs.
- `sources/bmad_method.py` -- wire both new comparisons at the CORE and suite call sites, reusing
  each site's already-resolved upstream-latest -- the only path that changes observable behavior.
- `sources/bmad_method.py`, `models.py`, `sources/__init__.py` -- update the three in-sync comment
  blocks named in Code Map.
- `sources/bmad_method.py` -- bump `_SUITE_FETCH_TOTAL_BUDGET_SECONDS` from `5.0` to `10.0` (see
  Code Map's budget-repair note) -- the per-call `min(remaining, _UPSTREAM_FETCH_TIMEOUT_SECONDS)`
  formula stays exactly as-is.
- `scripts/fleet_picture.py` -- bump `bmad_core_drift_findings`'s timeout to `25` + its
  budget-arithmetic comment, and `verification_staleness_findings`'s cross-reference comment.
- `tests/unit/test_sources_bmad_method.py` -- unit-test `_recipe_version` (hit, missing file, missing
  `context`/`version`, malformed YAML, non-string version) and `_fetch_channel_version` (hit, 404,
  malformed JSON, missing `latest_version`, every network failure mode folding to `None`).
- `tests/unit/test_sources_bmad_method.py` -- THE 6.3.0-relic fixture: CORE recipe at `6.11.0`,
  channel stubbed at `6.3.0` -- must produce a `bmad-channel-drift` WARN naming `bmad-method`.
- `tests/unit/test_sources_bmad_method.py` -- integration-level tests per I/O matrix row: recipe
  behind upstream fires `bmad-recipe-upstream-drift`; all-agree fires neither; missing/malformed
  recipe skips both; channel 404 skips only channel-drift; upstream-unresolved skips both; offline
  (channel fetch raises) degrades silently with the rest of `gather()` unaffected; every existing
  CAP-1/2/4/15.1 test (none of which stub the channel fetch) still passes unmodified.

**Acceptance Criteria:**
- Given the 6.3.0-relic fixture (CORE recipe `6.11.0`, channel `latest_version` `6.3.0`), when
  `gather()` runs, then exactly one `bmad-channel-drift` WARN names `bmad-method`, `6.3.0`, and
  `6.11.0`.
- Given a suite package whose recipe version is behind its already-resolved upstream latest, when
  `gather()` runs, then a `bmad-recipe-upstream-drift` WARN names that package.
- Given `api.anaconda.org` unreachable, when `gather()` runs, then no `bmad-channel-drift` Finding
  appears anywhere and every other Finding is unaffected (no crash, no degrade).
- Given a package with no `recipes/<name>/recipe.yaml` or an unparseable `context.version`, when
  `gather()` runs, then neither new Finding fires for that package.
- Given every pre-15.2 test in `test_sources_bmad_method.py`, when run unmodified, then all still
  pass -- the new channel fetch is never attempted unless a test explicitly stubs/reaches it.

## Spec Change Log

### 2026-08-22 -- bad_spec repair (review pass 1)
Trigger: Blind Hunter + Edge Case Hunter convergent HIGH finding -- the suite loop's shared
`_SUITE_FETCH_TOTAL_BUDGET_SECONDS` (5.0s, unchanged since Story 14.1) now has to cover a THIRD
per-package fetch type (the new channel fetch) without any pool enlargement, so an early package's
slow channel fetch could exhaust the deadline and skip EVEN THE PRE-EXISTING npm/GitHub
upstream-drift check for later packages -- a real coverage regression to an existing check, not
just a gap in the new one.

Amended: Code Map/Tasks now specify bumping `_SUITE_FETCH_TOTAL_BUDGET_SECONDS` from `5.0` to
`10.0` (`bmad_method.py`), and `scripts/fleet_picture.py::bmad_core_drift_findings`'s subprocess
timeout + budget-arithmetic comment from `20`/"5+5+5=15s" to `25`/"5+10+5=20s", preserving the same
~5s margin Story 14.1 established between the inner worst-case and the outer subprocess bound. The
Boundaries' own `min(remaining, _UPSTREAM_FETCH_TIMEOUT_SECONDS)` per-call formula is untouched.

Known-bad state avoided: silently degrading the PRE-EXISTING (Story 14.1) suite-upstream-drift
check's own coverage as an unacknowledged side effect of adding a new, lower-priority signal to the
same fixed-size shared budget.

KEEP: the `_recipe_version`/`_fetch_channel_version`/`_channel_and_recipe_drift_findings` helper
design and both call-site wiring points (CORE in `_gather()`, suite loop in
`_gather_suite_findings`) are correct and must survive re-derivation unchanged -- only the
`_SUITE_FETCH_TOTAL_BUDGET_SECONDS` numeric constant, `fleet_picture.py`'s timeout/comment, and any
test that hardcodes the old `5.0` budget value in its own arithmetic (e.g. a `5.0 - 2.0` deadline
computation) need updating to the new `10.0` figure. All docstring/comment prose already written is
otherwise correct and should be preserved, with only the specific numbers touched.

## Review Triage Log

### 2026-08-22 -- Review pass 2 (post bad_spec re-derivation)
- intent_gap: 0
- bad_spec: 0
- patch: 8 (high 1, low 7)
- defer: 1 (low 1)
- reject: 9 (low 9)
- addressed_findings:
  - `[high]` `[patch]` The suite loop's new per-package findings
    (`bmad-channel-drift`/`bmad-recipe-upstream-drift`) were appended directly
    into the SAME `warn_findings` list that gates whether the pre-existing
    `bmad-suite-upstream-drift` OK/summary branch fires -- when only the new
    axes drift for a package whose installed-vs-upstream comparison is
    genuinely clean, `warn_findings` being non-empty (from the new findings
    alone) skips the `if checked: return (OK finding, ...)` branch entirely,
    silently dropping the suite-upstream-drift axis's own positive-
    confirmation signal. Confirmed by direct repro (not merely reasoned
    about): a fixture with `bmad-loop` installed exactly at its resolved
    upstream latest, but its recipe.yaml one version behind, produced ONLY
    the new `bmad-recipe-upstream-drift` WARN -- `bmad-suite-upstream-drift`
    was entirely absent from the findings tuple, neither WARN nor OK. Found
    directly by this review pass (not by a subagent reviewer). Fix: track
    the new per-package findings in a SEPARATE list from `warn_findings`,
    concatenated onto whichever of the WARN/OK/empty return branches fires
    -- mirrors how the FIRST (pre-loopback) implementation attempt already
    handled this correctly with its own `extra_findings` list, before the
    bad_spec re-derivation inadvertently merged the two.
  - `[low]` `[patch]` `gather()`'s own docstring was never updated for Story
    15.2 -- it still describes only CAP-1/CAP-2/CAP-4's contributions,
    breaking this module's own established in-sync-docstring convention
    (Blind Hunter, confirmed by direct inspection). Fix: add a sentence
    naming the new CORE-side `channel_recipe_findings` addition, mirroring
    how the module docstring/`models.py`/`sources/__init__.py` already
    describe it.
  - `[low]` `[patch]` No autouse fixture stubs `_fetch_channel_version` the
    way `_stub_upstream_fetch` already stubs `_fetch_latest_upstream_version`
    for every test in this file -- confirmed absent by direct grep (the
    FIRST implementation attempt had this fixture; the re-derivation dropped
    it). Real risk: a future test pairing a `context:`-bearing recipe.yaml
    fixture with a resolved upstream and forgetting to stub the channel
    fetch would make a live call to `api.anaconda.org` during CI (Blind
    Hunter). Fix: add `_stub_channel_fetch` (autouse=True) back, mirroring
    `_stub_upstream_fetch` exactly.
  - `[low]` `[patch]` The `bmad-channel-drift` message overflows
    `scripts/fleet_picture.py`'s existing 110-char truncation for a
    long package name -- confirmed by direct computation: 125 characters
    for `bmad-method-test-architecture-enterprise` (Blind Hunter, verified
    concretely by the reviewer with the actual string). Fix: shorten the
    message wording so it comfortably fits under 110 chars for this repo's
    longest watched package name.
  - `[low]` `[patch]` Add one test firing both new findings simultaneously
    at the CORE call site (only tested for a suite package today), and one
    suite-loop test proving a package whose `latest` resolves to `None`
    skips both new findings (only tested at the CORE call site today) --
    both Blind Hunter findings, cheap additive coverage matching this
    module's own thoroughness convention.
  - `[low]` `[patch]` `_channel_and_recipe_drift_findings` never states an
    explicit "Never raises: ..." docstring paragraph the way every sibling
    network-touching helper in this file does (Blind Hunter) -- add one,
    documenting the fail-open contract already true of its implementation.
  - Blind Hunter's "no fleet-picture-layer test names the two new checks
    specifically" (independently echoed by Intent Alignment Auditor pass 2)
    deduplicated into ONE `defer` (low): the existing generic
    `test_both_cap1_and_cap2_warn_simultaneously` meta-test already proves
    the pass-through mechanism for arbitrary WARN findings under this
    Source, matching the precedent set by Stories 10.3/14.1/15.1 (none of
    which added a per-check fleet-picture test either) -- worth a marker,
    not a requirement for this story.
  - Rejected (9, matching this module's own already-established precedent
    elsewhere): CORE call site has no local try/except around the new
    helper (Blind Hunter + Edge Case Hunter, convergent) -- matches CAP-1/
    CAP-2's own existing raise-then-`degrade_on_exception` pattern, unchanged
    by this story; no OK/summary counterpart for the two new warn-only
    checks -- already ruled out-of-scope in review pass 1 per the AC's
    literal wording; CORE call omits an explicit `timeout=` argument --
    matches CAP-2's own pre-existing upstream-fetch call, which also relies
    on the same internal default; no single test stitches the full
    "5+10+5=20s" worst-case arithmetic end-to-end -- individual stages are
    already tested in isolation, matching how the pre-15.2 "5+5=10s"
    arithmetic was never end-to-end tested either; evidence omits the
    channel name as a structured field -- matches this module's existing
    minimal-evidence-per-axis scoping (same reasoning as pass 1's rejected
    "evidence carries only 2 of 3 known values" finding); unbounded local
    `recipe.yaml` read with no explicit timeout (Edge Case Hunter) --
    matches every other local file read in this module, none of which have
    ever had one.
  - `[high]` `[bad_spec]` The suite loop's per-package channel fetch and the CORE-side channel fetch
    both draw from the existing `min(remaining, _UPSTREAM_FETCH_TIMEOUT_SECONDS)`-bounded pools
    without those pools being enlarged for a third fetch type, so a slow/near-timeout channel fetch
    for an early suite package could exhaust the shared `_SUITE_FETCH_TOTAL_BUDGET_SECONDS` deadline
    and skip EVEN THE PRE-EXISTING (Story 14.1) npm/GitHub upstream-drift check for later packages
    -- independently found by Blind Hunter and Edge Case Hunter (convergent). Root cause: Code
    Map/Tasks never sized the shared budget for a third per-package fetch type. Amended Code
    Map/Tasks/Design Notes to bump `_SUITE_FETCH_TOTAL_BUDGET_SECONDS` `5.0`->`10.0` and the
    corresponding `scripts/fleet_picture.py::bmad_core_drift_findings` timeout/comment arithmetic
    (`20`->`25`) -- re-deriving code now. Boundaries/Approach/I-O-matrix are unchanged; the
    `min(remaining, _UPSTREAM_FETCH_TIMEOUT_SECONDS)` per-call formula they already specify is
    untouched.
  - Edge Case Hunter's two related findings (suite-side new checks require the package to be
    locally installed; the whole suite pass returns nothing on a fresh clone/CI with no
    `.pixi/envs`) deduplicated into ONE `defer` (medium): both trace to `_gather_suite_findings`'s
    pre-existing Story 14.1 install-state gate, which Story 15.2's new checks inherit by extension
    rather than by new design; the story's own named fixture (the CORE 6.3.0 relic) is unaffected.
    Recorded in frontmatter `deferred`.
  - The remaining 14 Blind Hunter findings and Intent Alignment Auditor's one informational note
    were rejected: several match this module's own established, already-reviewed precedent
    (duplicated in-sync-comment blocks across module/models/registry docstrings; per-package
    Findings distinguished only by `evidence["package"]`; two-value evidence dicts scoped to one
    comparison axis; lenient `_parse_release_triple` reuse for pre-release strings; no 429/403
    special-casing) -- all identical in shape to how CAP-2/CAP-4/Story 15.1 already work and were
    already accepted in prior reviews. Others are out of the story's named scope per its own AC
    text (one-directional channel-drift matches the literal "6.3.0 relic" framing; no OK/summary
    Finding matches the AC's literal "warn-only findings" wording). The rest are minor style/doc
    nits (multi-line call formatting, URL-quoting a hardcoded constant, one misread of the
    `fleet_picture.py` docstring) or not real findings against the diff (one Blind Hunter bullet
    critiqued this review's own prompt-construction note, not the code; Intent Alignment's note
    about no promoted `spec-15-2-*.md` existing yet is expected process ordering -- promotion is
    the coordinating session's job after PR review, per this repo's own convention).

## Design Notes

**Watched set:** `(DEPENDENCY_NAME,) + _suite_packages(pixi_data)` -- the union of CORE and the
existing suite set -- not a fresh `recipes/*` directory glob. This deliberately excludes the three
parked/non-pixi-pinned recipes (`bmad-autopilot`, `bmad-dashboard-extension`, `mybmad-dashboard`),
consistent with `spec-bmad-suite-channel-product`'s own Non-goals and CAP-4's existing "watched ==
pixi-pinned" precedent -- steward's own CAP-1 pipeline-truth report is the tool for the full
13-package population; doctor's ambient relay stays scoped to what this repo actually installs.

**Gating both new checks on an already-resolved upstream latest** (rather than probing channel/
recipe independently of upstream reachability) is a deliberate scope-narrowing: it reuses each call
site's existing fetch outcome with zero new network cost on that axis, and keeps the control-flow
change additive rather than restructuring either existing loop's early-exit shape. A future story
could decorrelate channel-vs-recipe from upstream reachability if that proves too narrow in
practice.

**Channel constant:** `_ANACONDA_CHANNEL = "SelfExplainML"` as a plain constant (mirrors
`DEPENDENCY_NAME`'s own precedent for a repo-specific, rarely-changing identifier) rather than
deriving it from `pixi.toml`'s `channels` array -- that list mixes `conda-forge` in with it and
picking "the non-standard one" programmatically would be speculative complexity for a single fixed
value.

**Shared-budget sizing (review pass 1):** doubling `_SUITE_FETCH_TOTAL_BUDGET_SECONDS` to `10.0`
rather than giving the channel fetch its own separate, tighter timeout constant keeps the fix
inside a single well-understood pool and its existing per-call formula, at the cost of not fully
eliminating the theoretical worst case (a sufficiently slow/adversarial network could still exhaust
even a 10s pool on package 1). This matches the module's own already-documented tolerance
elsewhere ("not a hard wall-clock guarantee") -- the fix meaningfully improves the realistic/typical
case (healthy network, ~10 watched packages) without introducing a second budget concept.

## Verification

**Commands:**
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py -v`
  -- expected: all existing + new tests pass.
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor -q` -- expected: no
  regressions elsewhere (`tests/meta/test_source_independence.py` still passes -- no new imports
  outside stdlib/`yaml`).

## Auto Run Result

**Summary:** Implemented Story 15.2 -- `sources/bmad_method.py`'s `bmad-method-version-drift` Source
gains two new fail-open, warn-only checks (`bmad-channel-drift`, `bmad-recipe-upstream-drift`) for
every package it already watches (CORE `bmad-method` plus every `_suite_packages`-derived pin),
comparing that package's tracked `recipes/<name>/recipe.yaml`-declared version against what the
SelfExplainML anaconda.org channel currently serves and against the already-resolved upstream
latest -- reproduces the historical "bmad-method 6.3.0 relic served for four months with no ambient
signal" scenario as a WARN. Two review passes ran; pass 1 found and repaired a HIGH-severity
`bad_spec` (shared-budget starvation of the pre-existing suite-upstream-drift check); pass 2 found
no `bad_spec`/`intent_gap` but this review session independently confirmed (via direct repro, not
merely reasoning) a second real HIGH-severity bug -- the new findings were merged into the same list
gating the pre-existing check's own OK/summary branch, silently suppressing it -- and dispatched 8
patch findings (1 high, 7 low), all applied and independently re-verified.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` -- new
  `_ANACONDA_CHANNEL`/`_ANACONDA_PACKAGE_URL` constants; `_recipe_version` (reads
  `recipes/<pkg>/recipe.yaml`'s `context.version`, fail-open); `_fetch_channel_version` (bare
  unauthenticated GET to `api.anaconda.org/package/SelfExplainML/{package}`, fail-open);
  `_channel_and_recipe_drift_findings` (the shared, I/O-owning helper building both new Findings from
  a package's already-resolved upstream latest). Wired at both call sites (CORE in `_gather()`, suite
  loop in `_gather_suite_findings`, the latter's new findings tracked in a SEPARATE `extra_findings`
  list per the pass-2 patch, riding every return branch). `_SUITE_FETCH_TOTAL_BUDGET_SECONDS` bumped
  `5.0` -> `10.0` per the pass-1 `bad_spec` repair. Module/`gather()`/`_gather_suite_findings`
  docstrings updated.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- `BMAD_METHOD_VERSION_DRIFT`
  comment extended.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- matching registry
  comment extended.
- `scripts/fleet_picture.py` -- `bmad_core_drift_findings`'s `timeout` `15` -> `25` (budget-arithmetic
  comment updated to match); `verification_staleness_findings`'s cross-reference comment updated.
  Purely a default-parameter-value + comment change -- no logic/behavior change to the ATTENTION-block
  dispatch other stations' findings also flow through (independently re-verified: the dedicated
  `test_fleet_picture_bmad_core_drift.py` meta-suite, 6/6, and the broader `fleet_picture`-tagged
  meta-test selection, 44/44, both pass unmodified).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` -- 45 new tests (119
  total, was 90 before Story 15.1/15.2 combined -- 116 after the initial 15.2 implementation, +3 from
  the pass-2 patch round): unit coverage for `_recipe_version`/`_fetch_channel_version`/
  `_channel_and_recipe_drift_findings`, the 6.3.0-relic fixture, the full I/O matrix at both call
  sites, the pass-1 budget-starvation regression test, the pass-2 OK-suppression regression test, and
  a new `_stub_channel_fetch` autouse fixture (mirroring `_stub_upstream_fetch`) so no test can
  accidentally reach the live network.

**Review findings breakdown (both passes combined):** pass 1 -- 1 `bad_spec` (high), 1 `defer`
(medium), 15 `reject`. Pass 2 -- 8 `patch` (1 high, 7 low), 1 `defer` (low), 9 `reject`. Zero
`intent_gap` across both passes.

**Follow-up review recommendation:** `true` -- pass 2's patched findings included one `high`
severity item (the OK-suppression bug), which alone triggers the recommendation regardless of the
`3*medium + 1*low` score (score here: `3*0 + 1*7 = 7`, also `>= 5` on its own).

**Verification performed (this session, independently -- not merely trusting subagent self-reports):**
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py -q`
  -- 119/119 passed.
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor -q` (excluding 4 files broken
  by a pre-existing, unrelated `pyforge.warden` import gap in this worktree's pixi env, confirmed via
  `git stash` diff) -- 1153 passed, 1 skipped, 1 pre-existing unrelated failure
  (`test_check_speed_budget.py`, confirmed identical on a clean stash).
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py`
  -- 60/60 passed (no new imports outside stdlib/`yaml`).
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_bmad_core_drift.py`
  -- 6/6 passed; broader `-k fleet_picture` meta-test selection -- 44/44 passed.
- `pixi run -e local-recipes ruff check` on all 5 changed files -- 17 findings, rule-category-and-count
  identical to a clean `git stash` baseline (confirmed via diff) -- zero new lint findings.
- Direct repro script re-run against the final code (the exact script that discovered the pass-2 bug):
  confirms `bmad-suite-upstream-drift` OK now correctly coexists with `bmad-recipe-upstream-drift`
  WARN for the same `gather()` call.

**Residual risks:** none beyond the two items already recorded in frontmatter `deferred` (suite-side
new checks require local `.pixi/envs` install state, inherited from Story 14.1's pre-existing gate;
no fleet-picture-layer meta-test names the two new checks specifically, though the generic
pass-through mechanism already covers them structurally).
