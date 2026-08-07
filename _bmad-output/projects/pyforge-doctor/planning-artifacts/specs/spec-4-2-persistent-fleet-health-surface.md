---
title: 'Persistent fleet-health surface -- `monitor --surface PATH` (FR-11, AD-8)'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md',
  '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py',
  '{project-root}/src/shared/packages/pyforge-doctor/tests/meta/test_read_only_guard.py',
]
warnings: [
  'This story adds pyforge-doctor''s first filesystem-write call site, in direct tension with NFR-1''s blanket "no module under pyforge.doctor may write outside a tempfile-scoped path" rule. Resolved by extending the existing sole-site exemption PATTERN (mirrors sources/atlas.py''s sole-mcp-import-site precedent) to fleet_surface.py specifically -- see Design Notes.',
]
baseline_revision: 'HEAD at Story 4.2 start (after Story 4.1 landed in the same pass)'
---

<intent-contract>

## Intent

**Problem:** `monitor --fleet` is a point-in-time CLI/JSON snapshot -- an operator has to re-run and manually diff two runs by hand to see what changed in the fleet's health.

**Approach:** A new `pyforge.doctor.fleet_surface` module: `build_surface(findings, axes)` is a pure, deterministic transform of `monitor --fleet`'s OWN already-gathered `Finding`/`Source` output into a schema-versioned document (AD-8: strictly derived, never a second gather). `write_surface` is the one non-pure step -- writes that document to a path. Wired as an OPT-IN `monitor --surface PATH` flag; omitting it changes nothing about `monitor`'s existing behavior.

## Boundaries & Constraints

**Always:**
- The surface's content is derived SOLELY from the SAME `findings` tuple `monitor` already gathered (post `--source` filtering, if given) -- never an independent second gather (AD-8).
- Regenerating from the same findings is byte-identical (idempotent) -- `build_surface` sorts its own findings deterministically (by source, check, status, message) and carries NO wall-clock field anywhere, unlike `DoctorReport`'s own per-invocation `generated_at`.
- `schema_version` starts at `1` (NFR-5's `DoctorReport` precedent, extended).
- The surface's `axes` field reflects whatever axes the TRIGGERING run actually covered (never a hardcoded subset) -- automatically correct for Story 4.3's `adoption` axis with zero changes to this module.
- `--surface` is opt-in only; omitting it writes nothing.

**Never:**
- Never trigger a second `atlas.gather` call to produce the surface.
- Never embed a timestamp/wall-clock field in the surface's own content (would make every regeneration a spurious diff, defeating the whole "tracked surface" purpose).
- Never let this module's write capability leak to any OTHER module -- `fleet_surface.py` is the ONE sanctioned filesystem-write site in `pyforge.doctor`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `monitor --fleet` (no `--surface`) | Any run | Nothing written; behavior unchanged from pre-Story-4.2 | No error |
| `monitor --fleet --surface PATH` | Findings gathered | `PATH` written: `{schema_version: 1, axes, summary, findings}` | Parent dirs created if missing |
| Same findings, regenerated | Two runs, same underlying data | Byte-identical file content (idempotent) | No error |
| `--source` filter + `--surface` | Findings filtered before render | Surface reflects the FILTERED findings, matching what `--json`/text show | No error |
| `--watch adoption` + `--surface` | Adoption axis included | Surface's `axes` includes `"adoption"` | No error |
| Findings order varies between gathers | Same set, different order | `build_surface` output is order-independent (its own internal sort) | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/fleet_surface.py` -- NEW. `FLEET_SURFACE_SCHEMA_VERSION`, `build_surface`, `write_surface`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` -- EDIT. `monitor` subparser gains `--surface PATH`; `_run_monitor` calls `fleet_surface.write_surface` when given, from the same (post-filter) `findings` tuple.
- `src/shared/packages/pyforge-doctor/tests/meta/test_read_only_guard.py` -- EDIT. Adds a `fleet_surface.py`-exemption (mirrors `test_atlas_sole_mcp_import.py`'s own `_EXEMPT_RELATIVE_PATHS` pattern) plus a non-vacuous "the sanctioned site actually writes" proof test.
- `src/shared/packages/pyforge-doctor/tests/unit/test_fleet_surface.py` -- NEW. Pure-function + idempotency + schema_version + axis-fidelity coverage.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_monitor.py` -- EDIT. `--surface` CLI wiring tests.

## Design Notes

**The NFR-1 tension (the one genuinely hard call in this story):** Doctor's architecture spine states, unconditionally, "v1 is read-only everywhere -- no module under pyforge.doctor may write outside a tempfile-scoped path," enforced today by `test_read_only_guard.py`'s package-wide AST scan with NO exemption mechanism. FR-11/AD-8, however, explicitly requires writing a persistent surface FILE -- these two requirements are in direct, unavoidable tension. Two interpretations were considered:

1. **Reject the write entirely** -- have `monitor` only ever print the surface document to stdout (e.g. via a `--surface-json` flag the operator redirects with shell `>`), never touching the filesystem itself. This satisfies NFR-1 literally but makes Doctor NOT the thing writing the "tracked, at-a-glance surface" FR-11 describes -- the operator would have to remember to redirect every run, and any file living outside `pyforge.doctor`'s own process still gets written by SOMETHING; punting it to the shell doesn't eliminate the write, it just moves accountability for correctness (idempotency, schema version) outside this codebase's own test suite.
2. **Extend the existing "one sanctioned exception" pattern** -- this codebase already resolves an identical class of tension twice: AD-5 carves out `cli_bridge.py` as the ONE sanctioned subprocess site against an otherwise absolute "no bare subprocess" rule, and Story 2.1 carves out `sources/atlas.py` as the ONE sanctioned `mcp`-import site against an otherwise absolute "no `mcp` import outside the sanctioned site" rule -- both via a named, reviewed exemption list on the guarding meta-test, not by weakening the guard itself. FR-11/AD-8 is architecturally the SAME shape of exception: a v1.x addition that deliberately, narrowly, and reviewedly needs ONE capability the v1 rule otherwise forbids everywhere else.

Chose (2): `test_read_only_guard.py` gained `_EXEMPT_RELATIVE_PATHS = frozenset({Path("fleet_surface.py")})`, identical in spirit and near-identical in code shape to `test_atlas_sole_mcp_import.py`'s own exemption. AD-8's own rule bounds what that one write may do (strictly derived, idempotent, versioned) even though NFR-1's blanket text predates AD-8's existence. This is flagged in this spec's `warnings` frontmatter and via a non-vacuous "the sanctioned site actually writes" test, mirroring the existing sole-site guards' own non-vacuous proofs.

**Why the surface has no `generated_at`/timestamp field:** FR-11 AC2's idempotency requirement ("regenerating from the same findings produces byte-identical output") is incompatible with any wall-clock field in the diffable content -- a timestamp would make EVERY regeneration a spurious diff against a tracked file, which is the opposite of what a "tracked, at-a-glance" surface is for. `DoctorReport`'s own `generated_at` is fine because it's a per-invocation snapshot never expected to diff cleanly against a prior run; the surface is the opposite kind of artifact.

## Verification

- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`

**Actual results (2026-08-07):** full suite green (403 total after all four Epic 4 stories). `test_fleet_surface.py` (9 tests) + the 5 new `--surface` CLI tests + the read-only-guard exemption tests all pass.

## Review Triage Log

### 2026-08-07 -- Self-review pass (adversarial re-read of the diff)

- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 1 (NFR-1/FR-11 tension -- resolved via the exemption pattern above, not deferred; recorded here because it is the one place this story's implementation makes a judgment call the AC text doesn't fully resolve on its own)

Checked specifically for: exception handling (`write_surface`'s `path.write_text` is NOT wrapped in a local try/except -- deliberately: mirrors every other CLI-layer call in `__main__.py`, none of which locally catches I/O errors either, relying instead on `main()`'s own outer `except Exception` net to format a traceback and return exit 2 rather than crash uncaught -- confirmed by re-reading `main()`'s own docstring/structure, no new exception surface introduced); resource leaks (`Path.write_text` opens and closes its own handle internally, no dangling file descriptor); silent failures (a write failure propagates, is never swallowed); idempotency (verified BOTH at the pure-function level, `test_build_surface_is_idempotent_for_the_same_findings`, AND at the file level, `test_write_surface_overwrite_is_idempotent`/`test_monitor_surface_is_idempotent_across_two_runs` -- two different layers, not just one); the NFR-1 exemption's narrowness (confirmed via `test_no_filesystem_write_call_sites_in_package` still passing for every OTHER module -- the exemption is scoped to exactly one file, not weakened package-wide).

**Follow-up review recommendation: false** -- the one non-obvious design decision (the NFR-1 exemption) is documented in both this spec's `warnings` and Design Notes, with dedicated non-vacuous proof tests; nothing left implicit.

</intent-contract>

## Adversarial review pass (2026-08-07, Blind Hunter + Edge Case Hunter)

Dispatched with the diff file path only, no shared context. Two findings landed here:

- `medium` `patch` **`--surface` recorded the REQUESTED `--watch` axes verbatim, not the axes actually still represented after `--source` filtering.** `axes` was captured from `--watch` before the `--source` filter was applied to `findings`. Running `monitor --watch staleness,cve --source cve --surface out.json` wrote `"axes": ["cve", "staleness"]` even though every Finding in `"findings"` was from `cve` only -- contradicting this module's own docstring claim that the surface "documents exactly which Watch axes the triggering run covered." Fixed: a new `atlas.AXIS_SOURCES` table (axis name -> the `Source` member(s) that axis's `gather()` dispatch can produce; `"abandonment"` is a composite of two) lets `_run_monitor` recompute `axes` from the sources still present in `findings` after the `--source` filter, only when `--source` was actually passed. New test: `test_monitor_surface_reflects_the_source_filtered_findings` extended to assert `document["axes"] == ["cve"]`.
- `low` `patch` **`build_surface`'s sort key omitted `evidence`, risking non-deterministic tie-order across "identical" runs.** Two Findings tying on `(source, check, status, message)` but differing in `evidence` (e.g. two gather-failure sentinels sharing the same templated message) fell back to Python's stable-sort input order -- not a property of their content -- which can vary between two runs whose concurrent MCP/CLI calls resolve in a different wall-clock order, breaking the story's own documented idempotency guarantee. Fixed: the sort key now also includes a stable `json.dumps(evidence, sort_keys=True, default=str)` tiebreaker. New test: `test_build_surface_ties_on_source_check_status_message_break_on_evidence`.

**Re-verification (2026-08-07, after both patches):** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- **404 passed** (full suite).

**Follow-up review recommendation (updated): false** -- both findings are narrow, each covered by a dedicated regression test.
