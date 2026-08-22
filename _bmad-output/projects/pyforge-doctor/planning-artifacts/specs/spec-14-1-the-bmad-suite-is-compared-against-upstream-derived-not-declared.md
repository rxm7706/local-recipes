---
title: 'Story 14.1: The bmad-suite is compared against upstream, derived not declared'
type: 'feature'
created: '2026-08-21'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true # 1 medium + 10 low patches -> score 13 >= 5 (mechanical); all lows are comment/test-hardening tier
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      GitHub-releases fallback for the npm-invisible suite packages: 6 of the 10 live
      bmad-* pins (bmad-loop, bmad-labs-skills, bmad-manticore, bmad-method-wds-expansion,
      bmad-module-template, bmad-utility-skills) are GitHub-only local conda recipes that
      404 on registry.npmjs.org, so the live CAP-4 path is structurally blind to them —
      including bmad-loop, the package whose 0.9.0-vs-0.11.0 lag motivated CAP-4.
    evidence: |-
      Live probe 2026-08-21 during Story 14.1: only bmad-builder,
      bmad-creative-intelligence-suite, bmad-dashboard, and
      bmad-method-test-architecture-enterprise return 200 from
      https://registry.npmjs.org/{package}/latest. Recorded as a (note) in
      spec-bmad-method-version-drift/.memlog.md. The 404s fold to per-package
      silent skip exactly as the fail-open contract specifies, so no Finding can
      ever fire for these 6 on the live path; the fixture proof passes only via
      the stubbed fetch seam. Intent authorized "follow whatever bmad_method.py's
      existing upstream query does and generalize it" — npm-only — so this is a
      follow-on capability, not a defect in this story.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py
    severity: medium
  - summary: >-
      Suite pin-floor-vs-installed (offline CAP-1 analog for the suite) is not covered by
      any capability: an installed suite package behind its own pixi.toml floor (the
      fixture's literal shape — bmad-loop 0.9.0 installed vs >=0.11.0 pinned) is provable
      with zero network but produces no signal; pins are used only as the watched-set
      roster.
    evidence: |-
      Blind Hunter review, Story 14.1: the design notes dismiss it as "pixi install
      hygiene, not upstream drift" but no other capability catches it either. Arguably
      pixi's own territory (the state means pixi install has not run since the pin
      bump); an operator decision on whether Doctor should ambient-report it.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py
    severity: low
baseline_revision: 'f2bf10c89aa02b89aba952ff376f7c57378d695a'
final_revision: 'c8894d7ce137d07c09d34bbd11d5bb067d7119a9'
---

<intent-contract>

## Intent

**Problem:** Epic 10 taught Doctor to notice when the installed BMAD-METHOD *core* falls behind
its declared floor (CAP-1) or upstream latest (CAP-2), but the suite tools around it stay
invisible: in the live 2026-08-21 upgrade session `bmad-loop` sat at 0.9.0 vs upstream 0.11.0
(0.9.0 stalls every unattended session on BMAD >= 6.11) and TEA lagged 1.19.1 vs 1.23.2
(1.19.1's `tea-test-review` bin was published empty) with no ambient signal (CAP-4).

**Approach:** Extend `bmad_method.py`'s `_gather` with a suite pass: derive the watched set from
`pixi.toml`'s `bmad-*` pins (never a hardcoded list), read each package's installed version from
`.pixi/envs/*/conda-meta/` filenames, query npm per package through the SAME generalized
fail-open fetch helper CAP-2 already holds, and emit a warn-only Finding
(`check="bmad-suite-upstream-drift"`) per package behind upstream — flowing automatically through
Story 10.3's existing surfaces (`doctor check --bmad-core`, fleet-picture ATTENTION).

## Boundaries & Constraints

**Always:**
- Watched set = every dependency key starting `bmad-` across every table `_dependency_tables`
  already walks, EXCLUDING `DEPENDENCY_NAME` itself (the core is CAP-1/CAP-2's own territory —
  including it would duplicate `bmad-method-upstream-drift`). Sorted for deterministic output.
- Generalize the existing fetch seam in place: `_fetch_latest_upstream_version(*, package: str =
  DEPENDENCY_NAME, timeout: float | None = None)` with `_NPM_LATEST_URL` becoming a `{package}`
  template. Keyword-only `package` keeps the existing autouse test stub (`lambda **_: None`) and
  every existing caller/direct test working unmodified.
- The suite pass is ENTIRELY fail-open and never raises — unlike CAP-1/CAP-2's raise-then-
  `degrade_on_exception` style. Rationale (document in code): CAP-1/2 read TRACKED contract
  files where absence is a reportable misconfiguration; the suite pass reads gitignored runtime
  state (`.pixi/envs/*/conda-meta/`) that is legitimately absent on a fresh clone/CI, and its
  per-package fetches degrade individually. No `.pixi`, no matching pins, unparseable versions,
  or all fetches failing => no suite Finding at all, and CAP-1/CAP-2 outcomes are untouched.
- Installed version per package: newest release triple across every
  `.pixi/envs/*/conda-meta/{name}-<version>-<build>.json` filename (conda versions cannot
  contain `-`, so the filename parse is exact); parse versions with a new lenient
  `_parse_release_triple` (leading `X.Y.Z`, tolerates `.dev0`/prerelease suffixes) because
  suite pins like `1.2.2.dev0` legitimately fail `_parse_version`'s strict form. Comparison is
  release-triple only; equal triples (e.g. installed `1.2.2.dev0` vs upstream `1.2.2`) count as
  current — warn-only signal, biased against false warns.
- Per package behind upstream: one WARN Finding, `source=Source.BMAD_METHOD_VERSION_DRIFT`,
  `check="bmad-suite-upstream-drift"`, message `installed {name} {installed} is behind the
  latest upstream release {latest}`, evidence `{"package", "installed", "latest_upstream"}` —
  mirrors CAP-2's shape/wording. When at least one package was successfully checked and none is
  behind: exactly one OK Finding (same check) naming how many packages were checked. When zero
  were checked: no suite Finding.
- Total suite fetch cost is bounded by a shared monotonic deadline
  (`_SUITE_FETCH_TOTAL_BUDGET_SECONDS = 5.0`; per-fetch timeout = min(remaining, 5.0), skip the
  rest once exhausted): worst-case `_gather` network time stays CAP-2's 5s + 5s = 10s, inside
  `fleet_picture.bmad_core_drift_findings`'s 15s subprocess bound.
- Status is only OK or WARN, never FAIL (CAP-3 non-gating, unchanged); the suite findings ride
  the existing surfaces with ZERO changes to `__main__.py`, `fleet_picture.py`, or `check.py` —
  they dispatch `bmad_method.gather` and filter on `status`, not `check`.
- Keep the "keep this comment in sync whenever gather()'s own scope grows" contract: extend the
  `models.py` `BMAD_METHOD_VERSION_DRIFT` member comment, the `sources/__init__.py` REGISTRY
  comment, and `bmad_method.py`'s module docstring to name Story 14.1/CAP-4.
- Name every changed file in BOTH owning memlogs (`specs/spec-bmad-method-version-drift/
  .memlog.md` for the capability, `specs/spec-pyforge-doctor/.memlog.md` for the governed
  package surface) — the spec-surface drift verdict requires the owning spec's memlog to move
  with its files (Story 10.2's own Auto Run Result documents the red that omission causes).

**Block If:** (none — CAP-4's data-source and fail-open decisions were made by the operator in
`spec-bmad-method-version-drift/SPEC.md` on 2026-08-21; registry placement is resolved by the
epic's own "extend the existing Source" framing and the parent dispatch.)

**Never:**
- Never a hardcoded package list, and never a new `Source` member — no `report-schema.json`,
  registry-structure, or taxonomy-test change.
- Never touches `pixi.toml` (governed by four foreign specs — marshal/steward; the
  `bmad-method-version-drift-check` task-description touch-up is deliberately deferred rather
  than dragging four foreign memlogs into this story).
- Never runs `pixi`, `npm`, or any subprocess; never writes to `_bmad/**` or anywhere else;
  never persists fetched versions (per-call round-trips, `pypi_index.py` precedent).
- Never changes CAP-1/CAP-2's comparison logic, evidence shapes, message wording, or the strict
  `_parse_version` path they share; never imports station packages or `bmad_loop`.
- Never parses `pixi.lock` (multi-MB YAML — would blow the ambient-check speed budget for a
  fact conda-meta filenames already carry).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 2026-08-21 pre-update fixture | pins incl. `bmad-loop`, TEA; conda-meta 0.9.0 / 1.19.1; npm stubs 0.11.0 / 1.23.2 | CAP-1/2 findings + 2 suite WARNs naming `bmad-loop 0.9.0` < `0.11.0` and TEA `1.19.1` < `1.23.2` | No error |
| All suite packages current (live repo today) | installed == npm latest for every pin | CAP-1/2 findings + exactly 1 suite OK Finding naming the checked count | No error |
| Registry unreachable (offline) | every fetch returns None | CAP-1 finding only (CAP-2 + suite both silently absent) | Fail-open, no error |
| One package missing from npm (404), others resolve | mixed fetch results | 404'd package skipped; others compared normally | Per-package fail-open |
| No `.pixi/envs` at target (fresh clone/CI) | pins present, no runtime state | No suite Finding; CAP-1/2 unchanged | Fail-open, no fetches issued |
| No `bmad-*` pins besides the core | e.g. existing `_PIXI_SINGLE` fixture | No suite Finding; existing tests' `len(findings)` unchanged | No error |
| Unparseable installed version (weird filename) | conda-meta `name-garbage-build.json` | That package skipped silently | Fail-open |
| Suite deadline exhausted mid-loop | first fetch consumes the budget | Remaining packages skipped, findings only for those checked | Fail-open |
| CAP-1 inputs broken (missing pixi.toml) | as today | 1 generic WARN via `degrade_on_exception`; suite pass never reached | Unchanged outer net |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` — the whole
  implementation. Reuse: `_dependency_tables` (walks all 4 table shapes), `_parse_version`
  (strict, untouched), `_fetch_latest_upstream_version` (lines 173-207; add `package` kwarg,
  `_NPM_LATEST_URL` line 158 → template), `_gather` (lines 234-302; append suite findings before
  return — note BOTH return statements: the early `return (drift_finding,)` at line 274 must
  also grow the suite tuple, i.e. restructure so the suite pass runs regardless of CAP-2's fetch
  outcome). New: `_SUITE_PREFIX`, `_SUITE_FETCH_TOTAL_BUDGET_SECONDS`, `_parse_release_triple`,
  `_suite_packages`, `_installed_suite_versions`, `_gather_suite_findings`. Import `time`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` — conventions:
  real tmp fixture trees via `_write_pixi`/`_write_manifest`; autouse `_stub_upstream_fetch`
  (line 44, `lambda **_: None` — still matches the keyword-only generalized seam);
  `_real_fetch_latest_upstream_version` captured pre-patch for direct tests. Add: a
  `_write_conda_meta(target, env, name, version)` helper; banner section "suite upstream
  comparison (Story 14.1, CAP-4)" covering every new I/O row incl. THE fixture test
  `test_2026_08_21_pre_update_fixture_names_bmad_loop_and_tea`; direct tests for
  `_parse_release_triple` and the `package` kwarg URL construction.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` — lines 144-164: extend the
  `BMAD_METHOD_VERSION_DRIFT` member comment (mandated in-sync contract).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` — lines 303-337:
  extend the REGISTRY entry comment (comment-only, no field change).
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-method-version-drift/.memlog.md`
  + `.../specs/spec-pyforge-doctor/.memlog.md` — append typed entries naming the changed files.
- Read-only context (no changes): `sources/__main__.py` DISPATCH (routes
  `bmad-method-version-drift` → `bmad_method.gather`), `scripts/fleet_picture.py`
  `bmad_core_drift_findings` (15s bound, filters `status == "warn"`, renders `check: message`).

## Tasks & Acceptance

**Execution:**
- `sources/bmad_method.py` — generalize the fetch seam (`package` kwarg + URL template) —
  one shared fail-open network path for core and suite.
- `sources/bmad_method.py` — add `_suite_packages` (derive from pins), `_parse_release_triple`,
  `_installed_suite_versions` (conda-meta filename scan), `_gather_suite_findings`
  (deadline-bounded fetch loop + Finding construction); append its result in `_gather` on both
  success-path returns; update the module docstring for CAP-4.
- `models.py` + `sources/__init__.py` — extend the two mandated in-sync comments.
- `tests/unit/test_sources_bmad_method.py` — add the CAP-4 banner section: the 2026-08-21
  pre-update fixture test, every new I/O-matrix row, and direct unit tests for the new helpers.
- Both owning `.memlog.md` files — append entries naming every changed file.

**Acceptance Criteria:**
- Given a fixture of the 2026-08-21 pre-update state (pins for `bmad-loop` + TEA, conda-meta
  0.9.0 / 1.19.1, npm fetch stubbed 0.11.0 / 1.23.2), when `gather(target)` runs, then two WARN
  Findings with `check="bmad-suite-upstream-drift"` name `bmad-loop 0.9.0` vs `0.11.0` and
  `bmad-method-test-architecture-enterprise 1.19.1` vs `1.23.2`.
- Given every fetch fails (offline), when `gather(target)` runs, then output is byte-identical
  to today's CAP-1-only behavior — no suite Finding, no error.
- Given no `.pixi/envs` directory, when `gather(target)` runs, then zero suite fetches are
  issued and no suite Finding appears.
- Given the full doctor suite (`pixi run -e pyforge-doctor python -m pytest
  src/shared/packages/pyforge-doctor/tests -q`), when it runs, then every pre-existing test
  passes unmodified in body (the autouse stub keeps them network-free) and the meta tests
  (source independence, sole-subprocess, taxonomy, schema) stay green with no changes.
- Given the live repo (now current: bmad-loop 0.11.0, TEA 1.23.2), when `python -m
  pyforge.doctor.sources bmad-method-version-drift` runs online, then the suite check reports
  ok (or is silently absent offline) and the exit code is 0.

## Spec Change Log

(none — initial draft)

## Review Triage Log

### 2026-08-21 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 0, medium 1, low 10)
- defer: 2: (high 0, medium 1, low 1)
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `[medium]` `[patch]` Mutation-proven test gap (Verification Gap reviewer): no test covered the MIXED suite configuration (one behind + one current, both fetches succeeding) — a guard bug confined to that branch (`if warn_findings and checked == len(warn_findings)`) passed all 61 tests while swallowing the WARN behind an OK, and the mixed state is the common live shape. Added a gather-level mixed-configuration fixture test asserting exactly one WARN and no suite OK.
  - `[low]` `[patch]` Suite OK evidence hid the watched-vs-checked gap (live: "4 checked" of 10 watched, 6 npm-invisible). Added `packages_watched` to the OK finding's evidence (WARN evidence shape untouched — spec-fixed).
  - `[low]` `[patch]` Asymmetric parsing: upstream side used strict `_parse_version` for suite packages, so a prerelease npm `latest` (e.g. `0.12.0-rc.1`) silently dropped that package while the installed side parsed leniently. Suite packages now parse upstream with `_parse_release_triple`; core keeps CAP-2's strict path; direct test added for both.
  - `[low]` `[patch]` Package name interpolated into the registry URL raw — added `urllib.parse.quote(package, safe="")` at the seam.
  - `[low]` `[patch]` `_SUITE_FETCH_TOTAL_BUDGET_SECONDS` comment overclaimed a hard 10s wall-clock bound; `urlopen`'s timeout is per-socket-operation idle, so a slow-drip response can exceed it (CAP-2 carries the same semantics). Comment softened to "design budget bounding which fetches start", not a guarantee.
  - `[low]` `[patch]` The load-bearing conda-name==npm-name assumption (why 6 of 10 live pins are invisible) was undocumented — named in the CAP-4 module-docstring paragraph/`_SUITE_PREFIX` comment with the silent-skip consequence.
  - `[low]` `[patch]` `test_every_fetch_failing_is_byte_identical_to_cap1_only` asserted only len/check/status — strengthened to full Finding equality (message + evidence).
  - `[low]` `[patch]` No test covered realistic conda-meta noise (suffix-less `history` file; non-directory entry under `.pixi/envs/`) — both now written by a test and asserted skipped.
  - `[low]` `[patch]` `_PIXI_SUITE_PRE_UPDATE` pairs post-update pins with pre-update installed versions (a state pixi's solver never produces) — comment added: the fixture is a reconstruction; pins only derive the watched set, floors are never compared.
  - `[low]` `[patch]` `_parse_release_triple` rejected conda epoch versions (`1!0.9.0`), permanently exempting an epoch-versioned package — regex accepts an optional `\d+!` prefix; test line added.
  - `[low]` `[patch]` `scripts/fleet_picture.py`'s 15s-timeout justification comment still reasoned from a 5s inner HTTP bound; updated (comment-only) for the ~10s worst-case budget Story 14.1 introduced. File is allowlisted, not spec-governed.
  - Deferred (2, recorded in frontmatter `deferred`): GitHub-releases fallback for the 6 npm-invisible suite packages incl. bmad-loop (medium); suite pin-floor-vs-installed offline signal, no owning capability (low).
  - Rejected (7, noise / deliberate spec-documented choices / workflow-stage artifacts): fixture "counterfactual data" complaint (the stubbed fixture is the intent's own mandated proof; the underlying data-source reach gap is the medium defer above); WARN evidence lacking checked-count context (WARN evidence shape is spec-fixed to mirror CAP-2); catch-all `except Exception` observability (intent demands silence on failure; rationale documented in the docstring); lexical tie-break among equal installed triples (cosmetic — message text only, comparison unaffected); missing story/sprint bookkeeping in the diff (the finalize flow's job, runs after review by design); mid-loop exception discarding collected WARNs (deliberate documented last-resort net; the cited TypeError example is in fact caught inside the helper); ambient-surface proof location (Intent Alignment Reading C — the intent's stated proof obligation is the gather-level fixture; both consumers verified by two reviewers reading the unchanged wiring plus a live end-to-end run of the exact dispatcher command fleet-picture shells).

## Design Notes

The suite pass runs regardless of CAP-2's own fetch outcome (independent fail-open, simplest
coupling), but shares its 5.0s-per-request ceiling and adds its own 5.0s TOTAL deadline so the
worst-case blackholed-network cost of the whole gather is 10s — measured against the tightest
downstream bound, fleet_picture's 15s subprocess timeout. Happy-path cost is ~11 sequential
metadata GETs (~1-3s), acceptable for an opt-in check.

Installed-version source is `.pixi/envs/*/conda-meta/` FILENAMES, not JSON bodies and not
`pixi.lock`: the filename grammar `<name>-<version>-<build>.json` is unambiguous for a known
name (conda versions cannot contain `-`), needs zero file reads, and reflects what is ACTUALLY
installed (the epic's own wording) rather than what the lock resolves. Max across envs: the
signal asks "has this repo caught up anywhere"; a partially-synced env set is `pixi install`
hygiene, not upstream drift, and per-env findings would multiply noise in a warn-only channel.

## Verification

**Commands:**
- `pixi run -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests -q` —
  expected: all pass, zero live network calls.
- `pixi run -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/meta/test_bmad_artifacts_in_sync.py -q` — expected: green (no pixi.toml change, no new task).
- `pixi run -e local-recipes python -m pyforge.doctor.sources bmad-method-version-drift --json`
  — expected live today: CAP-1/2 ok + one suite ok Finding (registry reachable) naming the
  checked count; exit 0.

## Auto Run Result

Status: done

**Summary:** CAP-4 shipped inside the existing `bmad-method-version-drift` Source: `_gather` now
runs a fully fail-open suite pass — watched set derived at gather time from `pixi.toml`'s
`bmad-*` dependency keys (core excluded), installed versions read from
`.pixi/envs/*/conda-meta/` filenames (newest triple across envs), each compared against its
latest npm release through the generalized `package`-kwarg fetch seam under a 5.0s shared
monotonic deadline — emitting one WARN per package behind upstream
(`check="bmad-suite-upstream-drift"`, CAP-2's shape/wording) and exactly one OK naming
checked/watched counts when all checked are current. Zero wiring changes: the findings ride
Story 10.3's surfaces (`doctor check --bmad-core`, fleet-picture ATTENTION) by status.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` — CAP-4 suite
  pass + generalized fetch seam (strict core / lenient suite parse split, URL quoting, epoch
  tolerance, honest budget comments, name-identity assumption documented).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` — CAP-4 banner
  section: THE 2026-08-21 pre-update fixture test, mixed one-behind-one-current test
  (mutation-gap closure), every I/O-matrix row, conda-meta noise, direct helper/URL tests.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` — mandated keep-in-sync
  member comment extended (comment-only).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` — REGISTRY entry
  comment extended (comment-only).
- `scripts/fleet_picture.py` — `bmad_core_drift_findings` 15s-timeout margin comment updated
  for the ~10s worst-case budget (comment-only; allowlisted file).
- `specs/spec-bmad-method-version-drift/.memlog.md` + `specs/spec-pyforge-doctor/.memlog.md` —
  typed entries naming every changed file (implementation + review-pass patches), plus the
  npm-visibility live finding.

**Review findings breakdown:** 4 parallel layers (Blind Hunter, Edge Case Hunter, Verification
Gap, Intent Alignment). Triage: 0 intent_gap, 0 bad_spec, **11 patched** (1 medium — the
mutation-proven mixed-configuration test gap; 10 low), **2 deferred** (frontmatter `deferred`:
GitHub-releases fallback for the 6 npm-invisible suite packages incl. bmad-loop, medium; suite
pin-floor-vs-installed offline signal, low), **7 rejected** (noise / deliberate spec-documented
choices — itemized in the Review Triage Log).

**Follow-up review recommendation:** patched counts high=0, medium=1, low=10 → score
3×1 + 10 = 13 ≥ 5 → `followup_review_recommended: true`. (Mechanical formula outcome; all 10
low patches are comment/test-hardening tier.)

**Verification performed:**
- Full doctor suite: `pixi run -e pyforge-doctor python -m pytest
  src/shared/packages/pyforge-doctor/tests -q` → **1166 passed, 1 skipped** (pre-story: 1163
  passed, 1 skipped; the target file alone: 64 tests). Meta tests (source independence,
  sole-subprocess, taxonomy, schema) green unmodified.
- CFE meta: `pixi run -e local-recipes python -m pytest
  .claude/skills/conda-forge-expert/tests/meta/test_bmad_artifacts_in_sync.py -q` → 1 passed.
- Live smoke: `python -m pyforge.doctor.sources bmad-method-version-drift --json` → 3 findings,
  all ok (installed 6.11.0 meets floor and npm latest; suite
  `{"packages_checked": 4, "packages_watched": 10}`), exit 0 — the live env is current, so the
  drift case is carried by the fixture test exactly as intended.
- Matrix test audit: every I/O row mapped to a passing named test.

**Residual risks:**
- The live npm data source cannot see 6 of the 10 watched packages (GitHub-only conda recipes,
  404 → per-package silent skip) — including bmad-loop, CAP-4's motivating case. Tracked as the
  medium deferred item (GitHub-releases fallback follow-on); the OK finding's
  `packages_watched` vs `packages_checked` evidence keys make the gap visible to operators.
- The 10s worst-case network budget is a design budget, not a hard wall-clock guarantee
  (`urlopen` timeouts are per-socket-operation idle timeouts) — documented in-code; the
  fleet-picture 15s subprocess bound retains positive margin.
