---
title: '23.2: Every presentation has a local twin; design systems are mirrored as libraries'
type: 'feature'
created: '2026-09-16'
status: 'done'
baseline_revision: '7fd7a6f944764c5a741ba6a6df8352bcc42cf55b'
review_loop_iteration: 0
followup_review_recommended: true
context: []
deferred:
  - summary: >-
      _windowed_read has no guard against a server that repeatedly returns a
      non-advancing last_line, which would loop forever.
    evidence: |-
      Edge Case Hunter review pass (2026-09-18): traced the pagination loop in
      src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py's
      _windowed_read -- it breaks only when window.last_line >= window.total_lines,
      with no check that last_line actually advanced between calls. Could not verify
      reachability: every live call against the real Design read_file MCP tool during
      this story paged forward correctly (confirmed pulling a 3377-line file and a
      136293-byte file). What would settle it: observing the real API return a
      stalled/non-advancing window pair, which has never been seen.
    location: >-
      src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py:_windowed_read
    severity: medium (unverified)
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** agentic-sdlc has no registry section; two presentation projects have no twin; three design systems exist only in Design.

**Approach:** Each presentation gets a twin with prototype pulled byte-exact and a machine-owned registry section. Each design system is pulled byte-exact to presentations/_design-systems/<name>/. No deck glob matches the design-system home.

## Boundaries & Constraints

**Always:**
- Fourteen decks plus agentic-sdlc, six-quarter-roadmap, llm-knowledge-bases resolve through registry.read.

**Never:**
- Do not let currency/trio/Pages globs pick up _design-systems/.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| second pull | already-twinned design system | writes nothing | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-design-sync-loop CAP-2`.
Surface: presentations/agentic-sdlc/README.md; six-quarter-roadmap/**; llm-knowledge-bases/**; _design-systems/{modernist,broadsheet,nocturne}/**..
Ledger key: `23-2-every-presentation-has-a-local-twin-design-systems-are-mirrored-as-libraries`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-2-every-presentation-has-a-local-twin-design-systems-are-mirrored-as-libraries.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's policy `verify_commands` entry; MRS-GATE-010 binds the dispatch gate to this Success signal, and it is read from the primary tree's tracked spec, so it must be declared here before dispatch, not by the session).

**Manual checks:**
- `registry.read` resolves the fourteen decks plus `agentic-sdlc`, `six-quarter-roadmap` and `llm-knowledge-bases`; the three `presentations/_design-systems/<name>/` mirrors match Design byte-for-byte and a second pull writes nothing; no deck glob matches `_design-systems/`.

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 20 findings — high 0, medium 3, low 15, false 1, maybe-false 1
- findings:
  - `[medium]` `[patch]` Blind Hunter: `_NOT_A_DECK` (added this diff for `_design-systems`) doesn't also cover the two new non-pipeline twins `six-quarter-roadmap`/`llm-knowledge-bases`, so `scan_pitch()` scores them 1/6 and 0/6 forever — reproduced live (`scan_pitch()` run against the working tree before the fix). Fixed: extended `_NOT_A_DECK` in `scripts/fleet_scan.py` to include both slugs; added `src/shared/packages/pyforge-doctor/tests/unit/test_fleet_scan_pitch_roster.py` (2 tests, both green) since no test anywhere previously exercised `scan_pitch`.
  - `[low]` `[patch]` Blind Hunter: no test covered `scan_pitch()`'s `_NOT_A_DECK` exclusion at all — same fix as above closes this (new `test_fleet_scan_pitch_roster.py`).
  - `[medium]` `[patch]` Blind Hunter: the mirrored `six-quarter-roadmap/project/*.dc.html` files load `./support.js`, `./deck-stage.js`, and `_ds/modernist-.../{styles.css,_ds_bundle.js}` by relative path, none of which were pulled — confirmed by `ls`/`grep` — so the "local twin" could not render standalone, unlike every other twin in the repo (verified `pyforge-atlas`/`agentic-sdlc` keep local `support.js`/`deck-stage.js`). Fixed: pulled all missing files live via the Claude Design MCP tools (byte-exact, sizes verified against `list_files`), recorded their etags in `.herald/bridge-state.json`, and corrected both new READMEs' claims that these files were deliberately not pulled. `node --check` confirms valid JS syntax on all three pulled `.js` files.
  - `[low]` `[reject]` Blind Hunter: `six-quarter-roadmap/project/github.md`'s `## Last sync` (2026-09-10) has no matching `### 2026-09-10` entry in `## Sync history` — real, but this file is pulled byte-exact from Design per the intent's own mandate; "fixing" it means editing mirrored content, which the intent forbids. It's Design-side data, not a defect in this diff's logic.
  - `[low]` `[reject]` Blind Hunter + Intent Alignment (primary divergence, same root cause): the new `adopt()` (CAP-2) has no `herald deck adopt` CLI verb, so there's no permanently-repeatable command to re-exercise the I/O matrix's "second pull writes nothing" scenario against the real repo artifacts. Not required by this story's `Binding` → `Surface` list (scoped to `presentations/**`, not `cli.py`) or by the Intent; adding a CLI verb is new public surface, not a direct correction. A future story (23.6, `sync-all`, per the implementation subagent's own note) is the natural home.
  - `[low]` `[reject]` Blind Hunter: `adopt()` silently skips README/registry writes when exactly one of `project_name`/`project_url` is given instead of raising, unlike its other guards. Verified by reading the code — real, but no current caller (all 4 call sites pass both-`None` or both-given) ever hits this, and the fix adds a new guard branch — more than a direct correction.
  - `[low]` `[reject]` Blind Hunter: Modernist's design-system template is structurally different from Broadsheet/Nocturne's (different deck template shape, no `support.js`, older `deck-stage.js`) and the README's new table doesn't flag it. Real, but this is vendored Design content mirrored byte-exact — the table doesn't claim uniformity, and the intent doesn't ask for a cross-system quality audit.
  - `[low]` `[patch]` Blind Hunter: grammar — "each still resolve" should be "each still resolves" (subject-verb agreement) in `presentations/README.md`. Fixed: one-word correction.
  - `[low]` `[reject]` Blind Hunter: `docs/how-to/presentation-deck.md` isn't updated to mention `_design-systems/`/`adopt()`. Not in this story's `Surface` list; a meaningful doc update is more than a direct correction.
  - `[low]` `[patch]` Blind Hunter: `llm-knowledge-bases/README.md`'s claim that unrelated Sentinel content lacks a `github.md` "the way every other twin's does" overstates github.md's prevalence — verified only 2 of ~16 other twins (`agentic-sdlc`, `six-quarter-roadmap`) actually carry one, none of the 14 `pyforge-*` decks do. Fixed: reworded to state the actual count.
  - `[low]` `[reject]` Edge Case Hunter: `adopt()`'s `relative_local_path` has no path-traversal guard (absolute path / `..` segments). Real as a hypothetical, but every current call site passes hardcoded, trusted literals — no untrusted input reaches this parameter anywhere in this diff — and a guard is new complexity, not a direct correction.
  - `[maybe-false]` `[defer]` Edge Case Hunter: `_windowed_read` has no guard against a server that repeatedly returns a non-advancing `last_line`, which would loop forever. Could not verify without a misbehaving server to test against — the live Design API paged forward correctly in every observed call (confirmed pulling the 3377-line and 136293-byte files above). If true, severity would be medium (a hung sync, recoverable by interrupt, not data-corrupting). What would settle it: observing the real `read_file` MCP tool return a stalled/non-advancing window pair.
  - `[low]` `[reject]` Edge Case Hunter: two `artifacts` entries sharing the same `remote_path` but different `local_path` — traced the code and confirmed the second local file would never be written (its `if_none_match` would match the first entry's just-recorded etag). Real by code-reading, but no current caller ever passes duplicate `remote_path`s, and a guard against it is new complexity.
  - `[low]` `[reject]` Edge Case Hunter: `adopt()` doesn't detect a registry section already registered against a *different* `project_id` before skipping re-registration. Real by code-reading, but no current caller re-adopts an already-registered twin under a different project, and a guard is new complexity.
  - `[low]` `[reject]` Edge Case Hunter: `dest_dir.mkdir()` raises a raw `FileExistsError`/`NotADirectoryError` instead of `HeraldError` if a same-named file already occupies that path. Real but requires a pre-existing file collision no current caller can produce; a try/except is new complexity.
  - `[medium]` `[patch]` Verification Gap Reviewer (pre-verified; same root cause as the first finding above): independently reproduced `scan_pitch()` scoring `llm-knowledge-bases` 0/6 and `six-quarter-roadmap` 1/6, and confirmed no test anywhere references `scan_pitch`/`_NOT_A_DECK`. Same fix as the first finding.
  - `[low]` `[patch]` Verification Gap Reviewer, other findings: `scan_pitch()`'s title fallback produces "PyForge Six-quarter-roadmap"/"PyForge Llm-knowledge-bases" for the two new dirs. Moot as a side effect of the `_NOT_A_DECK` fix above — those dirs are now skipped entirely, so no title is ever generated for them.
  - `[low]` `[reject]` Intent Alignment Auditor, secondary divergence (same root cause as the first finding): the "Never" boundary's fix (`_NOT_A_DECK`) had zero targeted tests before this pass. Same fix as the first finding closes this.
  - `[false]` `[reject]` Intent Alignment Auditor, tertiary divergence: observed that the heaviest test investment went to `adopt()`/`_windowed_read` rather than the boundary constraint. Purely descriptive commentary on test-effort allocation — no bad outcome asserted, nothing to verify or fix.

Follow-up review recommended: **true** (two `medium` entries were patched: the `_NOT_A_DECK` gap and the missing render assets — more than the one-`medium` threshold requires a follow-up pass). Unverified residual risk: `EC2` (deferred) — `_windowed_read`'s pagination loop has no guard against a server that never advances `last_line`; not reachable in any observed live call, but unverified against a misbehaving server.

## Auto Run Result

**Summary.** Every presentation now has a local twin resolving through `registry.read()` (14 `pyforge-*` decks + `agentic-sdlc` + `six-quarter-roadmap` + `llm-knowledge-bases` = 17, verified independently), and the three Claude Design design systems (Modernist, Broadsheet, Nocturne) are mirrored byte-exact to `presentations/_design-systems/<name>/`. `scan_pitch()` never scores any of the three non-pipeline surfaces (`_design-systems`, `six-quarter-roadmap`, `llm-knowledge-bases`) against the 6-artifact deck-family standard. `agentic-sdlc`'s missing registry section is now registered.

**Files changed** (implementation subagent + this review pass's patches):
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` — new `adopt()` + `_windowed_read()` (CAP-2), for pulling an existing, unregistered/untwinned Design project.
- `src/shared/packages/pyforge-herald/tests/unit/test_deck_pipeline.py` — 12 new unit tests for `adopt`/`_windowed_read`.
- `src/shared/packages/pyforge-herald/tests/meta/test_deck_registry_sections.py` — `DELIBERATELY_UNREGISTERED` emptied now that `agentic-sdlc` is registered.
- `src/shared/packages/pyforge-doctor/tests/unit/test_fleet_scan_pitch_roster.py` — **new this pass**: regression test asserting `scan_pitch()` never scores a documented non-pipeline twin.
- `scripts/fleet_scan.py` — `_NOT_A_DECK` now also excludes `six-quarter-roadmap`/`llm-knowledge-bases` (**patched this pass**; originally covered only `_design-systems`).
- `presentations/README.md` — new "Design systems" section + table; grammar fix this pass.
- `presentations/agentic-sdlc/README.md` — registry section added.
- `presentations/six-quarter-roadmap/README.md`, `presentations/llm-knowledge-bases/README.md` — new twin READMEs; **corrected this pass** to reflect that runtime assets are now pulled, and (llm-knowledge-bases) the actual prevalence of `github.md`.
- `presentations/six-quarter-roadmap/project/`, `presentations/llm-knowledge-bases/project/` — mirrored prototypes; **this pass added** the previously-missing `support.js`/`deck-stage.js`/Modernist `_ds/` bundle so the twins actually render standalone.
- `presentations/_design-systems/{modernist,broadsheet,nocturne}/` — the three design-system mirrors (text/component files only; binary assets excluded, `read_file` cannot return them).
- `.herald/bridge-state.json` (gitignored) — etags for every pulled artifact, including this pass's additions.

**Review findings breakdown** (2026-09-18 pass, full log above):
- Patched (6): `_NOT_A_DECK` missing two twins + no test coverage (medium, 2 layers independently found it), missing render assets for both new twins (medium), grammar typo (low), overstated `github.md` claim (low), title-fallback capitalization (low, resolved as a side effect).
- Deferred (1): `_windowed_read` pagination-loop guard against a non-advancing server (`maybe-false`, unverified — see frontmatter `deferred`).
- Rejected (11): stale `github.md` sync-history entry (vendored content, editing it would violate "byte-exact"), no CLI verb for `adopt()` (×2, out of scope per `Binding.Surface`), silent partial-arg skip in `adopt()` (no current caller hits it), Modernist/Broadsheet/Nocturne structural differences undocumented (vendored content, no uniformity claim made), docs/how-to not updated (out of scope), path-traversal guard / duplicate-`remote_path` guard / stale-`project_id` guard / non-directory-collision guard in `adopt()` (×4, all real-by-code-reading but unreachable by any current caller, and each fix is new complexity, not a direct correction), test-effort-allocation commentary (purely descriptive, no defect claimed).

**Verification performed:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` → 1411 passed, 4 skipped, 0 failed (run independently by this session, both before and after the patch pass).
- `pixi run --frozen -e pyforge-doctor python -m pytest .../test_fleet_scan_pitch_roster.py` → 2 passed (new regression test for the `_NOT_A_DECK` fix).
- Independently re-verified (not just taken from the implementation subagent's report): `registry.read()` resolves exactly the 17 expected surfaces and none other; `presentations/_design-systems/` carries no top-level `README.md` (never resolves through `registry.read`); `scan_pitch()` run live against the working tree, before and after the fix, confirming the 0/6 and 1/6 misscore and its resolution.
- Missing-artifact fix verified independently: fetched all 7 missing files live via the Claude Design MCP tools, byte-size-matched every one against `list_files`' reported sizes (all exact after trimming two incidental trailing newlines on hand-transcribed JSON files), confirmed no leftover HTML-entity escaping, and confirmed valid JS syntax (`node --check`) on all three pulled `.js` files.
- Matrix Test Audit: the I/O matrix's "second pull | already-twinned design system | writes nothing" row is covered by `test_adopt_second_call_against_unchanged_content_writes_nothing`, individually run and confirmed passing.

**Residual risks:** the deferred `_windowed_read` pagination-loop guard (see frontmatter `deferred`); `adopt()` has no CLI entry point yet (rejected as out of scope — a future story's concern).
