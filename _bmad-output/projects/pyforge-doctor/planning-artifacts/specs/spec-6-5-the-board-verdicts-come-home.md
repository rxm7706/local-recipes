---
title: 'Story 6.5: The board verdicts come home'
type: 'feature'
created: '2026-08-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
baseline_revision: '88a6548bf041002f96309bed5ee1a175fa993cd6'
final_revision: 'b7296cf7674a7038100c9614603fa163a4d3873c'
---

<intent-contract>

## Intent

**Problem:** `scripts/chain_completeness_check.py`, `scripts/dashboard_drift_check.py`
and `docs/dashboard/check_layout.py` all judge Marshal's board (the fleet-status
console + its data feeds) but live outside Doctor — the station Charter §6 says
must hold the verdict. Story 6.4 proved the port pattern for the ledger; this is
the board's turn.

**Approach:** Port all three scripts' read-only judgement logic into one new
`sources/board.py`: `gather_chain_completeness` (`Source.CHAIN_COMPLETENESS`,
`scope="repo"`), `gather_dashboard_drift` (`Source.DASHBOARD_DRIFT`,
`scope="runtime"` — the epic's first runtime source), `gather_check_layout`
(`Source.CHECK_LAYOUT`, `scope="repo"`). Mechanism-only, like 6.2-6.4: no
`__main__.py` wiring (so no external dispatcher exists yet to wrap a call), no
`scripts/*_check.py`/`check_layout.py` deletion.

## Boundaries & Constraints

**Always:** No gather imports any `pyforge.<station>` package. `chain_completeness`'s
frontmatter reader is reimplemented as a tiny hand-rolled parser (no PyYAML — this
story's Surface excludes `pixi.toml`, mirroring the 6.4 precedent); its `DEFERRED_SPECS`
dict and all four invariants (INV-A spec-not-decomposed, INV-B story/ledger set
mismatch, INV-C board-vs-ledger divergence, INV-D canonical-epics-declares-no-stories)
port with identical `kind`/`detail`/`remedy` text. `dashboard_drift` reuses
`generate.py`'s `parse_sprint_status`/`dashboard_id_to_status` via the SAME
`importlib.util.spec_from_file_location` dynamic load the original script already
uses (never a `pyforge.marshal` import, never a subprocess) — resolved against
`target`, not a hardcoded path. `check_layout` dynamically imports
`docs/dashboard/check_layout.py` the same way and reuses its pure `check()`/`_rows()`
geometry functions verbatim rather than reimplementing the assertions; a missing
`playwright` import, missing `data.js`, or a browser that won't launch degrades to
one WARN Finding (mirrors the original's exit-2 UNKNOWN) — never OK, never raise.
All three `Source` members register in `sources.REGISTRY` with
`subject_station="marshal"`, `owning_station="doctor"`, and the scope each script's
own current `DETECTOR` dict already declares (preserve, don't redesign). Every
gather degrades to WARN on unreadable/missing input and never raises — including
`dashboard_drift`'s port of `_load_data_js`, whose original `raise SystemExit` on
an unparseable `data.js` becomes a WARN Finding, not a propagated exception
(`degrade_on_exception` only catches `Exception`, never `SystemExit`, so the
gather itself must not raise it). `gather_dashboard_drift` may use
`sources.degrade_on_exception` internally, wrapped around its own host-state
reads (Tier-3 feed globbing under `implementation-artifacts/`) — Story 6.3 built
it for exactly this future caller; there is no external dispatcher in this story
to wrap it from outside.
`data/report-schema.json`'s `finding.source` enum gains all three values.
Each of `chain_completeness`'s four invariants gets a dedicated test grounded in
the real incident named in the script's own docstring (Marshal's 2/24-decomposed
PRD, Doctor's orphan ledger key, Herald's 12/19-vs-47/47 board), each confirmed by
disabling that invariant's branch and observing the test fail.

**Block If:** nothing identified — all three scripts' logic is already read-only
and proven live in CI/pixi tasks.

**Never:** Add PyYAML or Playwright as a `pyforge-doctor` pixi dependency (Playwright
stays an optional, try/except-guarded import). Touch
`scripts/chain_completeness_check.py`, `scripts/dashboard_drift_check.py`,
`docs/dashboard/check_layout.py`, their pixi tasks, or `.github/workflows/detectors.yml`
(Story 6.9's job). Wire any of the three into `__main__.py`/`doctor check`. Change
`pyforge.doctor.sources.fleet_scan`'s parsers or `MARSHAL_DURABILITY`'s existing `gather()`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Open Spec undecomposed | status in `{draft,ready,in-progress}`, slug absent from PRD/epics prose | FAIL `spec-not-decomposed` (INV-A) | none |
| Spec in `DEFERRED_SPECS` | slug matches an exempt entry | no finding | none |
| Ledger key with no epics story | key in ledger, id absent from epics.md | FAIL `ledger-key-without-story` (INV-B) | none |
| Canonical epics declares 0 stories | ledger has rows, epics.md has 0 `### Story` headings | FAIL `canonical-epics-declares-no-stories` (INV-D) | none |
| `data.js` unreadable | malformed/absent | INV-C silently skipped; INV-A/B/D unaffected | none — never raises |
| Board status stale | feed says `done`, board says otherwise | FAIL `stale-done`, "will NOT self-heal" message | none |
| Twin ahead of feed | twin holds `done` a regressed feed lost | FAIL `twin-ahead`, explicit "do NOT run sprint-ledger-sync" | none |
| No drift | board, epics.md and twin all agree with the feed | one OK `Finding`, `Source.DASHBOARD_DRIFT` | none |
| Playwright not importable | `import playwright` raises `ImportError` | one WARN Finding, "could not be evaluated" | never raises |
| Chip overlap detected | two chips in one row overlap horizontally | FAIL Finding naming the chips + offset | none |
| Layout clean | all widths/pressures pass every assertion | one OK Finding, `Source.CHECK_LAYOUT` | none |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- add `Source.CHAIN_COMPLETENESS = "chain-completeness"`, `Source.DASHBOARD_DRIFT = "dashboard-drift"`, `Source.CHECK_LAYOUT = "check-layout"`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` -- add the three values to `$defs.finding.properties.source.enum`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- add three `SourceRegistration` rows (`CHAIN_COMPLETENESS`/`CHECK_LAYOUT` `scope="repo"`, `DASHBOARD_DRIFT` `scope="runtime"`; all `subject_station="marshal"`).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py` -- NEW. `gather_chain_completeness(target)`, `gather_dashboard_drift(target)`, `gather_check_layout(target)`; hand-rolled frontmatter parser; dynamic `importlib` loads of `target/pyforge.doctor.sources.fleet_scan` and `target/docs/dashboard/check_layout.py`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_completeness.py` -- NEW, one test per INV-A/B/C/D I/O-matrix row + the mutation confirmation for each.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_dashboard_drift.py` -- NEW, covers the I/O matrix incl. the twin-ahead direction guard; `gather_dashboard_drift` is called directly (no dispatcher exists yet).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_check_layout.py` -- NEW. Playwright-missing WARN path (no browser needed); `check()`/`_rows()` re-exercised directly with synthetic geometry dicts (no browser needed); `pytest.importorskip("playwright")`-gated smoke test for the live orchestration path.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_independence.py` -- NEW, mirrors `test_sources_ledger_independence.py`, `SOURCE` pointed at `sources/board.py`.

## Tasks & Acceptance

**Execution:**
- [x] `models.py` -- add the three `Source` members (closed-taxonomy-extended comment referencing Story 6.5/FR-15).
- [x] `data/report-schema.json` -- add `"chain-completeness"`, `"dashboard-drift"`, `"check-layout"` to the `source` enum.
- [x] `sources/__init__.py` -- add the three `SourceRegistration` rows to `REGISTRY`.
- [x] `sources/board.py` -- new module: hand-rolled `_frontmatter(path)` (no PyYAML); `gather_chain_completeness(target)` porting all four invariants verbatim (kind/detail/remedy text unchanged); `gather_dashboard_drift(target)` porting the stale-done/missing-story/twin-stale/twin-missing/twin-ahead checks via the same dynamic `generate.py` load; `gather_check_layout(target)` dynamically loading `check_layout.py`, reusing its `check()`/`_rows()`/`_serve()`/probe constants, degrading to WARN on `ImportError`/no browser/no `data.js`.
- [x] `tests/unit/test_sources_board_chain_completeness.py` -- cover every I/O matrix row for chain-completeness against real tmp fixtures (planning-artifacts trees, a `data.js`), plus one mutation test per invariant (disable the branch, confirm the test catches it).
- [x] `tests/unit/test_sources_board_dashboard_drift.py` -- cover the dashboard-drift I/O matrix rows against tmp fixtures mirroring `PROJECT_SOURCES`/tracked-ledger-twin layout; assert the `twin-ahead` message explicitly forbids `sprint-ledger-sync`.
- [x] `tests/unit/test_sources_board_check_layout.py` -- cover the WARN paths (no playwright / no data.js / no browser) without a real browser; exercise `check()` directly with synthetic `m` dicts for the FAIL/OK paths; one `importorskip`-gated end-to-end smoke test.
- [x] `tests/unit/test_sources_board_independence.py` -- port the three independence tests, `SOURCE` pointed at `sources/board.py`.

**Acceptance Criteria:**
- Given a monorepo checkout, when `pyforge.doctor.sources.board.gather_chain_completeness`, `gather_dashboard_drift` and `gather_check_layout` run, then each returns `Finding`s tagged with its own `Source`, routable through `verdict.exit_code_for` unchanged.
- Given `sources.REGISTRY`, when read, then it carries exactly one entry each for `CHAIN_COMPLETENESS`, `DASHBOARD_DRIFT` (`scope="runtime"`) and `CHECK_LAYOUT`, all `subject_station="marshal"`/`owning_station="doctor"`, and `test_every_source_member_has_exactly_one_registry_entry` passes.
- Given `sources/board.py`, when AST-scanned, then it imports no `pyforge.<station>` package — enforced by the new independence tests.
- Given `chain_completeness`'s INV-A..D, when each is exercised against its historical incident fixture, then the finding's `kind`/`detail`/`remedy` match the original script's output verbatim, and a mutation of that invariant's branch makes the corresponding test fail.
- Given `pyforge-doctor-test`, when run without `playwright` installed, then `test_sources_board_check_layout.py`'s WARN-path and pure-`check()` tests pass and the browser smoke test is skipped, never erroring the suite.
- Given `pyforge-doctor-test`, when run, then all prior tests plus the new ones pass, and `test_schema_source_enum_matches_the_source_taxonomy_exactly` passes.

## Spec Change Log

(none yet)

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4 (high 1, medium 1, low 2)
- defer: 2 (high 0, medium 1, low 1)
- reject: 5 (low 5)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently, both, converging on the same root cause via different trigger paths): **`gather_chain_completeness` could silently discard real FAIL findings across the whole repo when any one project's file was unreadable**, dropping the exit code to 0 — a direct violation of the spec's own I/O matrix row ("`data.js` unreadable → INV-C silently skipped; INV-A/B/D unaffected"). Root cause: the whole per-project loop was wrapped in one outer `degrade_on_exception`, and `_frontmatter`/the prose-loop only caught `OSError` (narrower than the original's broad `except Exception`), so a non-UTF-8 byte in ONE project's `SPEC.md` (or a malformed `data.js` project entry hitting `_board_lines`'s unguarded per-project loop) escaped as an exception, got caught by the outer wrap, and replaced EVERY project's already-computed findings with one vacuous WARN. Reproduced live before the fix (a well-formed project's real `spec-not-decomposed` FAIL vanished behind a WARN caused by an unrelated project's bad byte). Fixed: extracted `_check_project_chain_completeness`/`_check_project_dashboard_drift` per-project helpers, each called inside its own try/except in the outer loop so one project's failure degrades to a `*-unevaluable` WARN finding for THAT project only (mirrors `sources/ledger.py`'s own established multi-project independence discipline); broadened `_frontmatter`'s and the prose-loop's excepts to match the original script's own broad catch. Reproduced-then-fixed live for both trigger paths (non-UTF-8 byte; `null` data.js project entry); two regression tests added per source.
  - `[medium]` `[patch]` Edge Case Hunter: `dashboard_drift`'s `board_ids = {s[0] for s in stories}` and `for sid, status, *_rest in stories` were unguarded against a malformed `data.js` story entry (an empty list → `IndexError`; a 1-element tuple → `ValueError` unpacking) — same failure-swallowing consequence as the finding above, via a different site. Fixed: the `stories` list comprehension now filters to `isinstance(s, (list, tuple)) and len(s) >= 2` before either site reads it, and `_board_lines` gained an `isinstance(proj, dict)` guard for the mirror case in `chain_completeness`. Regression tests added for both (a malformed entry in one station no longer hides a different station's real finding; a non-dict entry is skipped without crashing).
  - `[low]` `[patch]` Blind Hunter: `test_open_undecomposed_spec_reports_fail`'s assertion `"no FR or epic references" in finding.message or "references" in finding.message` — the `or "references"` clause is nearly always true and defeats the point of the check (would pass even if the message text were substantially rewritten). Fixed: tightened to the single exact substring.
  - `[low]` `[patch]` Blind Hunter: `test_sources_board_dashboard_drift.py` never exercises the real `pyforge.doctor.sources.fleet_scan` (a hand-written stub stands in, for a documented and legitimate reason — the real module's own `bmad_drift_check` import ties it to the whole repo), unlike `test_sources_board_check_layout.py`, which conditionally loads the real `check_layout.py` when present. A rename/removal in the real `generate.py`'s attribute surface would not be caught by the automated suite. Fixed: added one `pytest.importorskip`-style (`skipif`-gated on file presence) test loading the REAL `generate.py` via `board._load_dashboard_generate` and pinning the exact attribute surface (`PROJECT_SOURCES`, `_KEY_SLUG_OVERRIDE`, `_DERIVE_EXCLUDE`, `parse_sprint_status`, `dashboard_id_to_status`) `gather_dashboard_drift` depends on.
  - `[medium]` `[defer]` Blind Hunter: `sources/board.py`'s independence claim ("never imports `pyforge.marshal`") stops at the Python-package boundary, not the file boundary — `gather_dashboard_drift`/`gather_check_layout` dynamically `exec_module()` two Marshal-owned files directly into Doctor's own process, so a broken/wrong `generate.py`/`check_layout.py` still executes as trusted code inside the judge. Inherited unchanged from the original scripts' own established "reuse via dynamic import" technique, which the story spec explicitly authorized (`preserve, don't redesign`) — a real structural tradeoff worth a future decision, not a defect introduced by this port. Logged to `deferred-work.md`.
  - `[low]` `[defer]` Edge Case Hunter: `gather_check_layout`'s browser orchestration loses already-collected FAIL findings if `playwright` raises partway through the width/font-pressure sweep, replacing them with one generic WARN rather than preserving partial results. Not reproduced live (no `playwright` in this env, per Boundaries); confirmed by inspection. Slightly BETTER than the original script's own `main()`, which has no top-level guard around the per-width loop at all. No production caller exists yet. Logged to `deferred-work.md`.
  - `[low]` `[reject]` Blind Hunter: `Finding.evidence["project"]` uses a different shape between `CHAIN_COMPLETENESS` (full `pyforge-<slug>` directory name) and `DASHBOARD_DRIFT` (bare board key). Declining: `Finding.evidence` is documented as "Source-specific, opaque to this envelope" (`models.py`), and each shape is preserved verbatim from its OWN original script's own `project`/`key` convention — unifying them would be an unauthorized redesign, contradicting the spec's explicit "preserve, don't redesign."
  - `[low]` `[reject]` Blind Hunter: `_frontmatter` doesn't strip YAML quoting (`status: 'draft'`) or inline `#` comments, unlike the original's `yaml.safe_load` — a quoted/commented status value would silently fail to match `OPEN_SPEC_STATUSES`. Real but theoretical for the two keys this parser actually reads (`status`, `epics_role`) — no real `SPEC.md` in this repo currently quotes or comments either field on its own line (only this story's OWN differently-shaped `implementation-artifacts/spec-*.md` frontmatter does, which `_frontmatter` never reads). Declining as low-value for now; the hand-rolled-parser tradeoff itself was an explicit, spec-mandated choice.
  - `[low]` `[reject]` Blind Hunter: `_frontmatter` never resets/bounds its scan if a frontmatter block opens with `---` but never closes with a second `---`, so an unterminated file would scan the whole remaining document for candidate `key: value` lines instead of returning `{}`. Theoretical (would require a corrupt/malformed file already flagged by other detectors) and low-consequence (spurious non-matching keys, not a crash). Declining as out of proportion to the finding's realistic likelihood.
  - `[low]` `[reject]` Edge Case Hunter: fixed `sys.modules` keys (`_doctor_board_dashboard_generate`/`_doctor_board_check_layout`) would collide if `gather_dashboard_drift`/`gather_check_layout` ran twice for two DIFFERENT targets in the same process. Verified this has NO live correctness consequence: each call's RETURN VALUE is the freshly-`exec_module`'d object, never re-fetched from `sys.modules`, so the collision is a hygiene/memory-retention nitpick only — and no production caller exists yet (spec-mandated: no `__main__.py` wiring in this story).
  - `[low]` `[reject]` Blind Hunter: the module docstring claims each chain-completeness invariant "was independently verified... to actually FIRE its own dedicated test" via manual mutation, with the verification "not re-encoded" in the suite. This is exactly what the story spec itself instructs ("you don't need to leave disabling code in the final tests") — not a defect. Independently re-verified during this review pass (INV-C's branch disabled, its test failed as expected, file restored byte-identical).

### 2026-08-09 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 11 (high 2, medium 3, low 6)
- defer: 2 (high 0, medium 2, low 0)
- reject: 4 (low 4)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently, both, same root cause): **`_board_lines`'s `isinstance(e, dict)` guard was in the wrong comprehension clause, so one malformed `data.js` entry anywhere collapsed EVERY project's real FAIL into a single vacuous WARN — exit 2 became exit 0.** A comprehension evaluates the inner iterable *before* any trailing `if`, so `[s for e in epics for s in (e.get("stories") or []) if isinstance(e, dict) and …]` never protected the `e.get(...)` call — the guard the PREVIOUS review pass added was inert. Because `board = _board_lines(...)` is computed at the top of `_check_chain_completeness` **outside** the per-project `try`, the `AttributeError` bypassed that pass's per-project isolation entirely and hit the whole-gather `degrade_on_exception`. Reproduced live on three distinct triggers (a `null` epic entry; `epics` as a string; `projects` as a list — the last escaping from after `_board_lines`' own `try` had already closed): in each case a well-formed project's genuine `spec-not-decomposed` FAIL vanished behind one WARN. This is a *regression against the original script*, which crashed loudly on the same input rather than reporting a passing verdict. Fixed: guard hoisted ahead of the second `for`, `epics` type-guarded, and a non-mapping `projects` now returns `None` ("cannot read the board" — INV-C already treats `None` and `{}` identically, so only the failure mode changes). Three regression tests added, each mutation-confirmed.
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (both): `gather_check_layout`'s `playwright` import sits **outside** the `degrade_on_exception` wrap and caught only `ImportError`, so an *installed-but-broken* playwright (missing `libnss3.so` → `OSError`; an ABI mismatch → `RuntimeError`) escaped the gather as a raised exception — breaking the function's own documented "never a raised exception" contract and the spec's I/O-matrix WARN row. Reproduced live by both hunters independently. Fixed: broadened to `except Exception`, and the preceding `data_js.is_file()` stat (also outside the wrap) guarded for `OSError`.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (both): `_run_check_layout` called `httpd.shutdown()` without `server_close()`, leaking one listening socket (and held ephemeral port) per invocation — harmless in the one-shot CLI this was ported from, unbounded in a library gather. Measured live: 50 serve/shutdown cycles → +50 open fds, monotonic; terminal state is `OSError: [Errno 24] Too many open files`, which then degrades to WARN and stops measuring layout altogether. Fixed: `server_close()` added to the `finally`.
  - `[medium]` `[patch]` Edge Case Hunter: `_run_check_layout`'s width/font-pressure sweep had no per-width isolation, so a failure at width N discarded every real FAIL already collected at widths 1..N-1 and reported a genuinely broken console bar as "could not evaluate". With `wait_until="networkidle"` and a 20s timeout, a single width's flake is the *expected* failure mode. Fixed: per-width `try/except` preserving partial results and recording the failed width, mirroring the per-project isolation discipline used by the other two gathers. **This closes the `[low]` `[defer]` entry the previous pass logged for the same issue** (that ledger entry is left untouched per the run instruction — the orchestrator owns its status).
  - `[medium]` `[patch]` Edge Case Hunter: `board_ids` was built from the `len(s) >= 2`-filtered story list, but it is a pure **membership** set that only needs `s[0]` — so a 1-element board entry `["1.1"]` was filtered out, making a story that IS on the board look absent and emitting a **false `missing-story` FAIL**. Introduced by the previous review pass's own unpacking-safety fix. Fixed: membership set built from the unfiltered list; the `>= 2` filter now constrains only the `(id, status)` unpacking set. Regression test added, mutation-confirmed.
  - `[low]` `[patch]` Edge Case Hunter: `data.get("projects", {})` does not coerce a *present-but-null* key, so `{"projects": null}` yielded `None` and raised `AttributeError` from outside the per-station `try` — the same finding-masking consequence, at two more sites. Fixed at both (`or {}` plus an `isinstance` fallback), matching `_board_lines`' own idiom.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (both): unreachable duplicated `return findings` at the tail of `_check_project_dashboard_drift`. Removed.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (both): `_frontmatter` returned raw post-`:` strings where the `yaml.safe_load` it replaced decoded them, so `status: 'draft'` read as `"'draft'"`, missed `OPEN_SPEC_STATUSES`, and **silently exempted an open, undecomposed Spec** — a false negative in the one check whose stated purpose is making "we chose not to" distinguishable from "nobody noticed". Same hazard for `epics_role: "canonical"`, where the miss skips INV-B and INV-D entirely. Both reproduced live. **This finding was `[reject]`ed by the previous pass** on the grounds that no consumed file is quoted today — re-verified and still true (all 27 live `SPEC.md` `status:` values and all 19 `epics_role:` values are unquoted), so the previous rejection was factually correct. Re-triaged to `patch` anyway on new evidence the earlier pass did not weigh: the `epics_role` consequence (silently skipping two whole invariants) was not considered, and this repo demonstrably writes quoted statuses in neighbouring spec files. Fixed with a new `_scalar()` helper matching YAML's own rules (strip surrounding quotes; strip a ` #` inline comment). Four regression tests incl. an over-stripping guard; mutation-confirmed.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (both): `_load_dashboard_generate` `exec_module`s `generate.py`, whose module body runs an unguarded `sys.path.insert(0, REPO_ROOT/"scripts")` — permanently prepending an *arbitrary* `target`'s `scripts/` to the Doctor process's import path, growing it on every call, so a later import inside Doctor could resolve against a foreign tree. Fixed: `sys.path` snapshotted and restored around the exec, and a half-initialised module no longer left in `sys.modules` when `exec_module` raises. Regression test added (mutation-confirmed) and verified live against the REAL `generate.py`.
  - `[low]` `[patch]` Blind Hunter: the per-project catch-all in `_check_chain_completeness` stamped every degraded finding `"inv": "INV-A"` although it wraps the whole INV-A/B/C/D evaluation — pointing an operator (or an `--inv` filter) at Spec decomposition when the broken input was, say, the ledger INV-B reads. Fixed to a neutral marker.
  - `[low]` `[patch]` Blind Hunter: three test-quality defects. (a) `test_unreadable_spec_in_one_project_does_not_hide_a_real_finding_in_another`'s docstring claimed to pin the per-project isolation, but `_frontmatter` already swallows the `UnicodeDecodeError`, so the fixture never reaches the isolation and the test passes with it deleted — verified; the false provenance claim is corrected in place and the test now points at the three new `_board_lines` tests that genuinely exercise it. (b) `test_multiple_projects_are_all_reported_independently` used one dirty + one clean project, so a bug dropping every project after the first would still pass — both projects are now dirty and both findings asserted. (c) `test_missing_generate_py_degrades_to_warn`'s `assert "dashboard-drift" in finding.check or finding.check == "dashboard-drift"` had a subsuming, substring-matching disjunct — tightened to equality.
  - `[medium]` `[defer]` Blind Hunter: `sources/board.py` reads the same `sprint-status-ledger.yaml` with two different parsers (`_ledger_rows` for INV-C vs the real `parse_sprint_status` for dashboard-drift), so one ledger row can be read two ways and the two gathers can contradict each other in a single run. Latent (no live ledger has an inline comment — verified 0 hits across all 8). Unifying means choosing a canonical ledger parser, the same grammar decision the existing `DONE_RE`/Route-3-alias entries turn on. Logged to `deferred-work.md`.
  - `[medium]` `[defer]` Blind Hunter: `_run_check_layout` — the only genuinely NEW code in the port — has no effective automated coverage (no test names it; the single e2e test is `playwright`-gated and its assertions are tautological). Two real defects in exactly this region survived to this review, which is direct evidence the gap hides regressions. Not closable here: the Boundaries forbid adding `playwright` as a dependency, so real coverage needs a fake-browser seam or an opt-in CI lane. Assertions deliberately NOT tightened blind, since they cannot be executed in this env to confirm a tightened form passes. Logged to `deferred-work.md`.
  - `[low]` `[reject]` Blind Hunter: `_board_lines`' story filters change INV-C's denominator versus the original (the original counted malformed entries into the total, the port drops them). Declining: the divergence manifests only on input where the original **crashed outright** — a traceback is not a behavior to preserve, and preserving the count would mean reintroducing the masking bug fixed above.
  - `[low]` `[reject]` Blind Hunter: `dashboard_drift`'s Findings carry only `evidence={"project": key}` while `chain_completeness` carries five structured keys, so a consumer wanting to partition `twin-ahead` from `twin-stale` must read prose. Declining on the same grounds the previous pass declined the identical finding: `Finding.evidence` is documented as "Source-specific, opaque to this envelope", each shape is verbatim from its own original script, and the `check` field already distinguishes the two directions.
  - `[low]` `[reject]` Blind Hunter: `rel_feed`/`rel` and `slug_`/`slug` are duplicated lookups within one function. Verified byte-identical expressions (`gen._KEY_SLUG_OVERRIDE.get(key, f"pyforge-{key}")` both times); the layout is faithful to the original's section-by-section structure. Cosmetic.
  - `[low]` `[reject]` Edge Case Hunter: `_DERIVE_EXCLUDE` is read via `getattr(..., set())` while `PROJECT_SOURCES`/`_KEY_SLUG_OVERRIDE` are bare attribute reads, so renaming either turns every station into a `dashboard-drift-unevaluable` WARN rather than one clear finding. Degradation is correct; the diagnostic is merely N-fold noisier. The attribute surface is already pinned by the previous pass's real-`generate.py` test.

### 2026-08-09 — Review pass (follow-up 2)

- intent_gap: 0
- bad_spec: 0
- patch: 13 (high 1, medium 5, low 7)
- defer: 3 (high 0, medium 1, low 2)
- reject: 3 (low 3)
- addressed_findings:
  - `[high]` `[patch]` Edge Case Hunter: **a THIRD nested `data.js` shape escaped `_board_lines` and collapsed every project's real FAIL into one vacuous WARN — exit 2 became exit 0 again.** `{"stories": 7}` is TRUTHY, so `(e.get("stories") or [])` does not catch it, and not a list, so `for s in 7` raised `TypeError` — from OUTSIDE `_check_chain_completeness`'s per-project `try`, straight into the whole-gather `degrade_on_exception`. Reproduced live: a well-formed project's genuine `spec-not-decomposed` FAIL vanished behind one WARN. This is the same finding-masking class the two previous passes each fixed once by hand (`projects` as a list; a non-dict epic entry) — and each time one more nested access was still open, which is the actual lesson. Fixed structurally rather than by adding a fourth `isinstance`: the whole per-STATION body now runs in its own `try`, so any shape this function fails to anticipate costs that one station its board line (already how INV-C spells "cannot compare this station") and nothing else. Two regression tests (`stories` a bare int; `stories` a mapping, which iterates to its keys and raises one line further down) plus a per-station isolation test; all mutation-confirmed.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (both, independently): `_run_check_layout` reported a width it **could not measure** as a layout **FAIL**. `exit_code_for` maps FAIL to exit 2 and WARN to 0, so a single `networkidle` timeout — which the code's own comment calls "the EXPECTED failure mode" at a 20s budget — turned the gate red on a board that measured clean everywhere it could be measured, contradicting `gather_check_layout`'s own docstring and this module's two siblings (both spell cannot-evaluate `warn`). Reproduced live via a stub browser. Fixed: `unmeasured` is now a separate list emitted as WARN Findings, leaving the measured widths' real verdict intact; the `.cbstatus not found` line stays FAIL because that one IS the original's own finding text for a page that loaded and did not render.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (both): the per-width isolation the previous pass added was **defeated one frame up** by the unguarded `finally: browser.close()` / `httpd.shutdown()`. Reproduced live: with the layout genuinely broken at every width and `browser.close()` raising, all real FAILs were replaced by one `warn | could not be evaluated here — RuntimeError`. The masking hole was moved, not closed. Fixed with a `_suppress_close` helper around all three teardown calls — a failed teardown must never be able to change what the gather reports.
  - `[medium]` `[patch]` Edge Case Hunter: a **present-but-non-mapping `projects`** in `data.js` (`null`, a list, a string) was coerced to `{}` and reported as a confident OK — *"the committed data.js matches the feeds"* — over a board never read. Reproduced live. The original script crashed on this input; trading a loud crash for a false green is the worst outcome available to a detector whose whole job is catching a board that lies. Fixed: a new `_board_projects` raises, so `degrade_on_exception` produces the honest WARN, exactly as it already does for an unparseable `data.js`. An ABSENT key stays an empty board (the original's own reading) — pinned by its own test.
  - `[medium]` `[patch]` Edge Case Hunter: a `SystemExit` raised by either dynamically-`exec_module`'d file escaped both gathers. `SystemExit` is a `BaseException`, which `degrade_on_exception` documents that it deliberately never catches — and `gather_check_layout`'s own `except Exception` misses it too. Reproduced live (`gather_dashboard_drift` raised `SystemExit` straight out). `_load_data_js` already makes exactly this conversion, with a docstring explaining why; the loader had simply been left out. Fixed: converted to `RuntimeError` in the loader, `KeyboardInterrupt` deliberately untouched.
  - `[medium]` `[patch]` Blind Hunter: the previous pass deferred `_run_check_layout`'s coverage gap as needing "a fake-browser seam or an opt-in CI lane" — **the seam was already in its own signature** (`_run_check_layout(target, clm, sync_playwright)` takes both the layout module and the browser factory as parameters). Verified by driving all of the above through stubs with no `playwright` installed. Closed here: 11 new tests over the orchestration, covering clean/FAIL/flake/teardown-failure/nothing-measured/no-chromium. The pre-existing deferred entry is left untouched per the run instruction (the orchestrator owns its status).
  - `[low]` `[patch]` Blind Hunter: `_board_lines` diverged from the original on `"epics": []` — the original guards `if not epics: continue` (a station it deliberately skips), the port's `isinstance` check let the empty list through, recorded `(0, 0)` and fired a **false `board-diverges-from-ledger` FAIL**. Unlike the divergence the previous pass rejected, this one manifests on input the original handled cleanly, not on input where it crashed. Fixed by restoring `not epics or` ahead of the type guard; mutation-confirmed.
  - `[low]` `[patch]` Edge Case Hunter: the same comprehension's `and s` filter dropped an **empty story slot `[]`** from INV-C's denominator, where the original counts it (`len(s) > 1` already guards the done-count) — shrinking the total until a 3-slot board read as matching a 2-row ledger, a false NEGATIVE in the check. Reproduced live. Fixed and mutation-confirmed; the sibling `and s` in `_check_project_dashboard_drift` is deliberately KEPT, since `board_ids` indexes `s[0]` there.
  - `[low]` `[patch]` Blind Hunter: `_scalar` applied its two YAML rules **in the wrong order**, stripping the inline comment before the quotes, so a quoted value containing ` #` was truncated and left with a stray quote (`'"a # b"'` → `'"a'` where yaml gives `a # b`). Same mis-decode class the helper was added last pass to prevent. Fixed: a quoted value is decoded first and its `#` left alone, matching YAML; the existing over-stripping guard test still passes unchanged.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (both): the two dynamic loaders had **drifted** — only `_load_dashboard_generate` carried the `sys.path` snapshot and the `sys.modules` cleanup the previous pass added; `_load_check_layout` `exec_module`d an arbitrary target's file with none of it (reproduced: two calls left two `sys.path` entries, monotonic; a raising file left a half-initialised module cached). Fixed by consolidating both onto one `_load_foreign_module` helper, so a hardening applied to one cannot again miss the other. Regression tests on both loaders.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (both): the `measured == 0` WARN discarded every diagnostic it had collected and asserted a cause never observed — when the page failed to LOAD, whether the bar would have rendered is exactly what is unknown. Fixed: the collected reasons are now the message. WARN itself is correct and kept (it is the original's own `exit 2` UNKNOWN).
  - `[low]` `[patch]` Blind Hunter: the `projects`-derivation block was copy-pasted into `_gather_dashboard_drift` and `_check_dashboard_drift`, the first only to compute `len(projects)` for the OK finding's evidence — so the count reported and the set actually scanned could silently disagree the moment either copy was edited. Removed by deriving once and passing down.
  - `[low]` `[patch]` Blind Hunter: `CHECK_LAYOUT`'s registry row was the one scope choice left unannotated, while its two siblings both carry an inline comment explaining theirs. Comment added naming the tension and pointing at Story 6.9 (see the matching deferred entry).
  - `[medium]` `[defer]` Blind Hunter + Edge Case Hunter (both): `_load_foreign_module` cleans only its own `sys.modules` key, so the TRANSITIVE imports the exec'd file performs stay cached — two different targets in one process silently share the first target's `bmad_drift_check`. Reproduced live (`target A -> TARGET-A`, `target B -> TARGET-A`). The previous pass's rejection of the adjacent fixed-key finding was correct for the loader's own key but does not cover transitive modules. Not patched: the honest fix is a design decision (restoring all of `sys.modules` strands objects and breaks legitimate caching), no caller passes two targets, and it belongs with the existing `exec_module`-as-trusted-code entry. Logged to `deferred-work.md`.
  - `[low]` `[defer]` Blind Hunter: `CHECK_LAYOUT` is `scope="repo"` while `gather_check_layout` binds a socket and drives Chromium — not what that field's own gloss describes, and unable to meet the 5s NFR-4 budget `doctor check` holds. Spec-mandated ("preserve, don't redesign"), no dispatcher yet, and all three resolutions belong to Story 6.9's design. Logged to `deferred-work.md`.
  - `[low]` `[defer]` Edge Case Hunter: INV-A's bare substring test silently exempts a Spec whose slug is a prefix of another named in prose. Verbatim from the original and unchanged by this port; the word-boundary fix must land in the script and the port together or the two detectors disagree, which makes it Story 6.9's business. Logged to `deferred-work.md`.
  - `[low]` `[reject]` Blind Hunter: `_load_dashboard_generate`'s comment claims the returned module "is unaffected" by the `sys.path` restore, which holds only for module-level imports — a future function-level import from `scripts/` inside `parse_sprint_status` would fail from Doctor but work from the original script. Verified safe today (every deferred import in `generate.py` is stdlib). Declining: a hazard contingent on a hypothetical future edit to another station's file, with no present consequence.
  - `[low]` `[reject]` Blind Hunter: both `chain_completeness` and `dashboard_drift` return OK over ZERO projects (a mistyped `target` yields a positive compliance assertion), where `gather_check_layout` declares the opposite rule. Real, but faithful to BOTH original scripts, and `sources/ledger.py`'s own module docstring already records this exact OK-vs-WARN split as unresolved deferred work for the whole family. Declining a third vote on a question already open — it wants one fleet-wide decision, not per-module drift.
  - `[low]` `[reject]` Edge Case Hunter: a story id written as a JSON number in a hand-authored `data.js` (`1.1` not `"1.1"`) fails the `board_ids` membership test and emits a false `missing-story` FAIL. Verified byte-identical to the original's own `board_ids = {s[0] for s in stories}` — inherited, not introduced — and `data.js` is generated with string ids. Declining per "preserve, don't redesign".

### 2026-08-09 — Review pass (follow-up 3)

- intent_gap: 0
- bad_spec: 0
- patch: 10 (high 2, medium 4, low 4)
- defer: 2 (high 0, medium 2, low 0)
- reject: 2 (high 0, medium 1, low 1)
- addressed_findings:
  - `[high]` `[patch]` Edge Case Hunter: **the per-project/per-station isolation the three previous passes built protected every project EXCEPT the one that failed** — so a real FAIL was still lost, exit 2 still became exit 0. Both `_check_project_chain_completeness` and `_check_project_dashboard_drift` accumulated into a LOCAL list and returned it at the end, so a raise part-way through discarded the findings already computed for that very project, and the caller's catch replaced them with one vacuous WARN. Two live triggers, both reproduced: a non-UTF-8 `sprint-status-ledger.yaml` in the project that owned a genuine `spec-not-decomposed` FAIL (`_ledger_rows` caught only `OSError`, but `UnicodeDecodeError` is a `ValueError`), and a non-UTF-8 `epics.md` in the station that owned a genuine `twin-missing` FAIL (`_drift_epics_md_ids` had no guard at all). Fixed structurally — `findings` is now the CALLER's list, appended to in place, so nothing already found can be unwound — plus the three narrow `except OSError` reads broadened to match the originals' own broad catch. Two defenses now cover each trigger; mutation-confirmed by reverting BOTH (either alone still yields the right verdict, which is the point).
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently, both, via different triggers): **`gather_chain_completeness` asserted *"epics, ledger and board agree"* over a board it had never read.** `_board_lines` returns `None` for any unreadable/structurally-wrong `data.js`, which correctly skips INV-C (the spec's own I/O-matrix row) — but the OK Finding's message still claimed agreement, and `evidence` recorded nothing to tell a consumer apart. Reproduced on two triggers: `projects` present-but-not-a-mapping, and a `data.js` missing the fixed literal prefix (one leading newline suffices). The asymmetry is the sharp part: the sibling `_board_projects` REFUSES the identical bytes with a docstring arguing at length that "trading a loud crash for a false green is the single worst outcome available to a detector whose whole purpose is catching a board that lies" — so one file produced a confident OK here and an honest WARN in `gather_dashboard_drift`. Fixed: `board` is derived once in `_gather_chain_completeness` and the OK now says *"the board (data.js) could not be read, so INV-C was NOT evaluated"* with `evidence["board_read"]`. Status stays OK because INV-A/B/D really did pass — the spec's row mandates INV-C be skipped, not that the run be reddened. Mutation-confirmed.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (both, opposite directions of one defect): `_board_lines` was incoherent about a malformed station line. Some shapes (`epics: [None]`, `[{"stories": "1.1"}]`) were silently FILTERED out of the story comprehension, quietly recording `(0, 0)` and firing a **false `board-diverges-from-ledger` FAIL** with a fabricated count (*"board 0/0 vs ledger 1/2"*) — reddening the gate on merely-malformed input; other shapes (`{"stories": 7}`) raised and dropped the station, where `station in board` then made INV-C **silently pass** it. Both reproduced. Fixed by extracting `_station_board_line`, which keeps the three states apart explicitly: `None` for the well-formed empty `epics: []` the original deliberately skips, a raised `ValueError` for any shape this reader cannot interpret (routed to the caller's per-station skip), and `(done, total)` for a line actually read. The two behaviors a previous pass established — a falsy `stories` is empty, an empty story slot `[]` counts toward the total — are preserved and still pinned by their own tests. Mutation-confirmed both directions.
  - `[medium]` `[patch]` Edge Case Hunter: a `SystemExit` raised by either dynamically-`exec_module`'d file **at CALL time** (from inside `parse_sprint_status` / `check()`) escaped both gathers. The previous pass added exactly this conversion to `_load_foreign_module` — but only for the IMPORT; the same file's functions were then invoked with no guard, and `SystemExit` is a `BaseException` that neither the per-unit `except Exception` nor `degrade_on_exception` catches. Reproduced live (`gather_dashboard_drift` raised `SystemExit` straight out to the caller). Fixed at both layers: a new `_no_system_exit` wrapper at each gather boundary, and the per-station/per-width catches broadened to `except (Exception, SystemExit)` so one station's exit still degrades only that station. `KeyboardInterrupt` deliberately untouched.
  - `[medium]` `[patch]` Blind Hunter: **both per-project isolation blocks were exercised by zero tests — deleting both kept the entire suite green** (confirmed by mutation: 574 passed with both removed). Neither `chain-completeness-unevaluable` nor `dashboard-drift-unevaluable` appeared in any assertion, and the one test that claimed to cover it already documented that it does not, redirecting to the `_board_lines` tests — a redirect that had itself gone stale, since those triggers are now caught per-station inside `_board_lines`. This is the class three passes have each fixed once, with nothing pinning the fix. Fixed: two tests that drive each catch-all directly and assert the OTHER unit's real FAIL survives beside the WARN; the stale docstring corrected in place.
  - `[medium]` `[patch]` Blind Hunter: nothing pinned the real `check_layout.py` attribute surface `_run_check_layout` consumes (`_serve`, `WIDE`, `NARROW`, `PRESSURES`, `APPLY`, `PROBE`, `check`) — every orchestration test drives `_StubLayoutModule`, which DEFINES those names rather than verifying them, and the one test that would notice is `playwright`-gated. A rename in the real file would make the gather raise `AttributeError`, degrade to WARN, and become a permanently green no-op with a fully green suite. The sibling gather has had exactly this test since pass 1. Fixed: the mirror test, `skipif`-gated on the real file's presence.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (both): `page.close()` sat INSIDE the per-width `try`, whose `except` appends to `unmeasured` — so a raising teardown put a **fully measured** width into the cannot-measure list while it was still counted in `measured`, producing a self-contradictory report (*"6 measurement(s): 3 width(s) x 2 font-pressure step(s); 3 width(s) could not be measured"*). Its two sibling teardowns already had `_suppress_close` for precisely this reason; this one had been missed. Fixed and mutation-confirmed.
  - `[low]` `[patch]` (found while verifying the SystemExit fix, not by either hunter): `measured += 1` ran BEFORE `clm.check(...)`, and `measured` is what gates the OK message's *"console bar edges held, no overlap"* — so a `check()` that raised at every width still produced a confident OK asserting a grid whose assertions never ran. Fixed by incrementing after `check()` returns; the new SystemExit test doubles as its pin.
  - `[low]` `[patch]` Edge Case Hunter: `_run_check_layout` served `clm.HERE` — `check_layout.py`'s own `__file__` parent — rather than `target/docs/dashboard`, so the gather validated one repo's `data.js` and then measured a different repo's board whenever the script is symlinked or shared (reproduced live). The original had no `target` parameter and could not hit this; the seam is new to the port. Fixed and mutation-confirmed.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (both): `_frontmatter` stored a value-less `key:` as `""` rather than skipping it, so a `status:` whose value sits on the next indented line (valid YAML, decoded by the `yaml.safe_load` this parser replaced) read as `""`, missed `OPEN_SPEC_STATUSES`, and **silently exempted an open, undecomposed Spec** — the same false-negative class `_scalar` was added for, through different syntax. The module docstring also claimed value-less keys were "simply skipped", which the code did not do. Fixed with `_continuation_scalar`, which reads a plain scalar continuation and still returns `None` for a real block opener (a list, a nested mapping, nothing); re-verified 0 divergences against `yaml.safe_load` across all 73 live `SPEC.md`/`epics*.md` files. Mutation-confirmed.
  - `[low]` `[patch]` Blind Hunter: both new test files repeated the bare module-scope `parents[6]` that a prior review had already guarded in `test_check_speed_budget.py` (with a comment recording the finding) — in a checkout fewer than seven levels deep an `IndexError` is a COLLECTION error for 30+ tests instead of the skip each file's own docstring promises. Guarded in both.
  - `[medium]` `[defer]` Blind Hunter: the port MOVED the dynamic-import trust boundary. Both originals resolve the file they `exec_module` from their own `__file__`, so they can only execute their OWN repo's files; `sources/board.py` resolves from the caller-supplied `target`, so once Story 6.9 wires `--target` from argv, `doctor check /untrusted/checkout` executes that checkout's two Python files with Doctor's full privileges. Distinct from the already-recorded "Marshal-owned files as trusted code" entry (that one is within one repo). Spec-mandated technique, `__main__.py` off-limits, resolutions all belong to 6.9. Logged to `deferred-work.md`.
  - `[medium]` `[defer]` Blind Hunter: all three originals still run as live fleet detectors (`scripts/detectors.py` globs both `scripts/*_check.py` and `docs/dashboard/check_*.py`) with no parity test against their ports. Sharper than the Story 6.4 instance because `DEFERRED_SPECS` is an operator-edited constant: updating it in the script the runbook names and not in `board.py` makes the two Doctor-blessed detectors contradict each other on the same tree. Parity verified BY HAND this pass (both gathers reproduce their scripts' output exactly — 1 and 5 findings, identical text), which is exactly the check nothing automates. Logged to `deferred-work.md`.
  - `[medium]` `[reject]` Blind Hunter + Edge Case Hunter (both): `_load_foreign_module` cleans only its own `sys.modules` key, so the exec'd file's TRANSITIVE imports stay cached and two targets in one process share the first target's `bmad_drift_check` (reproduced). **Already recorded in the ledger by the previous pass**, with the same reasoning for not patching (restoring all of `sys.modules` strands objects and breaks legitimate caching — a design decision, not a patch). Declining a duplicate entry; the orchestrator owns that entry's status.
  - `[low]` `[reject]` Blind Hunter: the `importorskip`-gated end-to-end smoke test asserts only tautologies (`assert findings`; `source is CHECK_LAYOUT`, set by construction; `status in (OK, FAIL, WARN)`, the whole enum). True, but the coverage it was once expected to provide now exists: the previous pass added 11 stub-driven orchestration tests through `_run_check_layout`'s own seam, and this pass added 4 more. Tightening it blind is a live risk in an env where it cannot be run — a stricter assertion could fail on a machine that has `playwright` but no chromium. Redundant rather than load-bearing.

## Design Notes

`gather_dashboard_drift` is `scope="runtime"` — the epic's first. No dispatcher
exists yet to call it (this story wires nothing into `__main__.py`), so it must
be self-guarding like its `scope="repo"` siblings: every failure mode the
original script printed-and-exited on (unparseable `data.js`, an unreadable
Tier-3 feed, a missing twin) becomes a Finding inside the gather itself, using
`sources.degrade_on_exception` where convenient rather than relying on an
external wrapper that does not exist in this story. This story's own tests call
`gather_dashboard_drift` directly and assert on its return value, mirroring how
`test_sources_ledger.py` tests `ledger.gather` directly today.

`check_layout`'s dynamic import gives `gather_check_layout` access to `check()`
(a pure function over already-measured geometry) without re-deriving the layout
math — the only NEW code is the orchestration that launches a browser, serves
`target/docs/dashboard/`, and turns `check()`'s string list into `Finding`s. This
keeps the port surgical: the assertions that matter (edges/overlap/one-row/
in-bounds/not-clipped) are byte-identical to the original, reused rather than
rewritten.

## Verification

**Commands:**
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- expected: all pass (502 + new); check-layout's browser-driven smoke test skips (no `playwright` in this env).
- `python -c "from pyforge.doctor.sources import board; from pathlib import Path; r=Path('.'); print(board.gather_chain_completeness(r)); print(board.gather_dashboard_drift(r)); print(board.gather_check_layout(r))"` (from the monorepo root) -- expected: no traceback, well-formed `Finding` tuples.

**NOTE on running the suite from a bmad-loop worktree** (same caveat Story 6.4
recorded): point `PYTHONPATH` at this worktree's own `pyforge-doctor/src` and the
env's interpreter explicitly, or the task silently tests `main`'s sources instead
of the branch's.


## Auto Run Result

Status: done (follow-up review pass 3 — review-only; no re-implementation, no
spec amendment, `<intent-contract>` untouched).

**Summary of implemented change.** A fourth adversarial review pass over the
same diff (`88a6548` → HEAD). Blind Hunter and Edge Case Hunter ran in
parallel with no shared context; both reproduced their findings live rather
than reporting them by inspection. 10 patches applied, 2 items deferred, 2
rejected. Two `high`s, and both are the same finding-masking class the three
previous passes each closed once — a real FAIL becoming a vacuous WARN, exit 2
becoming exit 0 — which continues to be the honest lesson of this module:
every pass has found the hole moved rather than closed. This pass closed it
structurally (findings accumulate in the CALLER's list, so nothing already
found can be unwound by a later raise) rather than by adding one more guard.

**Files changed.**
- `src/.../doctor/sources/board.py` — caller-owned findings lists in both
  per-unit helpers; `_station_board_line` extracted (three explicit states for
  a board line: skipped / unreadable / measured); `_continuation_scalar` added
  to `_frontmatter`; `_no_system_exit` added at both gather boundaries;
  three narrow `except OSError` reads broadened; honest OK message +
  `evidence["board_read"]` when INV-C was not evaluated; `page.close()`
  suppressed; `_serve` pointed at `target/docs/dashboard`; `measured`
  incremented after `check()` returns.
- `tests/unit/test_sources_board_chain_completeness.py` — 9 regression tests
  (own-project finding survival ×2, per-project catch-all, fabricated-`0/0`
  ×2, unreadable-board-is-not-agreement + its inverse, next-line `status:`,
  block-opener guard); one stale docstring corrected.
- `tests/unit/test_sources_board_dashboard_drift.py` — 3 regression tests
  (own-station finding survival, per-station catch-all, call-time
  `SystemExit`); `parents[6]` guarded.
- `tests/unit/test_sources_board_check_layout.py` — 4 regression tests
  (page-teardown, served directory, call-time `SystemExit` + `measured`
  accounting, real-`check_layout.py` attribute surface); `parents[6]` guarded.

**Review findings breakdown.** patch 10 (high 2, medium 4, low 4) · defer 2
(medium 2, both appended as NEW entries to `deferred-work.md`; no existing
entry read, modified or re-opened) · reject 2 (medium 1 — already on the
ledger from the previous pass; low 1) · intent_gap 0 · bad_spec 0.

**Verification performed.**
- `pytest src/shared/packages/pyforge-doctor/tests -q` → **604 passed, 1
  skipped** (588 → 604; the skip is the `playwright`-gated smoke test, as
  designed). Run with `PYTHONPATH` pinned to THIS worktree's
  `pyforge-doctor/src` and the pixi env's interpreter named explicitly, and
  the resolved `board.__file__` printed to confirm the branch's copy was under
  test — not `main`'s.
- **Every one of the 13 new regression tests mutation-confirmed**: each fix
  reverted in a scratch copy, the matching test observed to FAIL, the file
  restored. Four findings now have two independent defenses, so reverting
  either alone still produces the correct verdict — those four were confirmed
  by reverting BOTH layers. `board.py` verified restored byte-identically
  (sha256) after every mutation run.
- **Behavioral fidelity re-verified against the live repo**: `gather_chain_
  completeness` → 1 finding, `gather_dashboard_drift` → 5, matching
  `scripts/chain_completeness_check.py` and `scripts/dashboard_drift_check.py`
  finding-for-finding with identical text. (Those findings are pre-existing
  repo state — the doctor board is behind its feed — not caused by this
  change.) `gather_check_layout` → the expected single `playwright is not
  usable` WARN.
- `_frontmatter` re-checked against `yaml.safe_load` across all **73** live
  `SPEC.md`/`epics*.md` files after the parser change: **0 divergences**.

**Residual risks.**
- `_run_check_layout`'s real browser path is still never executed here (no
  `playwright` in this env, per Boundaries). The orchestration is now covered
  by 15 stub-driven tests and the real module's attribute surface is pinned,
  but no test drives a real Chromium; the pre-existing ledger entry for that
  gap stands.
- The two deferred items (caller-supplied `target` becoming an arbitrary
  `exec_module` source; three originals live alongside their ports with no
  parity test) are both Story 6.9's to resolve and have no live consequence
  while nothing dispatches these gathers.
- `CHECK_LAYOUT`'s `scope="repo"` vs its browser-driving reality remains
  spec-mandated and deferred to 6.9's design.
