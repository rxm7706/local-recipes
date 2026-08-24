---
title: 'Headless render gate'
type: 'feature'
created: '2026-08-14'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/specs/presentation-deck.md']
warnings: ['oversized']
baseline_revision: 'c47a46d1b7a1c6b3bd4b68038e911e49071bd9f5'
final_revision: 'ef0b9482d2824018c7cb410f8ae49d160fcebf07'
---

<intent-contract>

## Intent

**Problem:** Herald's deck pipeline can prove a built deck runs but never proves it *looks*
right (the repo's own recorded gap). Story 14.1 shipped the gate report interface with
`DEFAULT_GATES` empty; nothing populates it yet.

**Approach:** Add a `render_gate` to `deck_qa.py`, registered as `DEFAULT_GATES["render"]`,
that drives headless Chromium through every `#/<n>` slide of a built deck (`presentations/
<slug>/dist/`), screenshots each to `.herald/deck-qa/<slug>/render/`, and composes a Pillow
contact sheet -- evidence a reviewer looks at instead of trusting a clean build.

## Boundaries & Constraints

**Always:**
- Report-only: never mutates deck sources, never runs `npm run build` itself. If `presentations/
  <slug>/dist/` is absent, `render_gate` raises a clear error; `run()`'s existing per-gate
  isolation (Story 14.1) turns that into `GateResult(status="error", ...)` for the `"render"`
  gate id alone -- it never aborts the whole report or other gates.
- Serves the built `dist/` over a throwaway local static server (ephemeral `127.0.0.1` port,
  mirrors `pyforge-doctor/sources/board.py::_serve_layout_dir`) -- **not** `file://`. Resolves
  the epic's open serve-mode decision: the deck is a Vite bundle with dynamically-imported JS
  chunks, and Chromium blocks cross-origin fetch/module-import under `file://` ("Cross origin
  requests are only supported for HTTP"), a well-known limitation with no existing counter-
  evidence in this repo; `board.py` already solved the identical problem this way for its own
  Playwright gate.
- Slide identity comes from `presentations/<slug>/src/slides/manifest.json` (a flat JSON array;
  array position `i` is the slide's identity, `manifest[i]["id"]` its stable id). Hash route is
  1-indexed: `#/${i+1}`.
- Every slide capture is isolated: one slide's `goto`/`screenshot` failure records a `Finding`
  (`slide_id`, message) and leaves every other slide's capture and the gate's own
  `status: "ok"` untouched (mirrors `board.py`'s per-width isolation). Only a fully unusable
  environment (no `dist/`, no launchable Chromium at all) raises out of `render_gate` itself.
- Every Chromium/browser call (`launch`, `goto`, `screenshot`) carries an explicit timeout --
  resolves `DW-FU-14-1-2` (no timeout wraps a gate call) for this specific browser-automation
  gate.
- Every artifact path recorded in `GateResult.artifacts` is a plain `str(path)`, never a `Path`
  -- keeps `DW-FU-14-1` (non-JSON-serializable artifact) inert for this gate by construction.
- `.herald/deck-qa/<slug>/render/` is recreated fresh each run (old PNGs from a since-shrunk
  manifest never linger looking current) -- matches the existing gitignored, operator-local,
  regenerable `.herald/` convention (`db.py`, `state.py`).
- Chromium launch mirrors `board.py`'s fallback: try `channel="chrome"`, else bare
  `chromium.launch()`; if neither works, raise (caught by `run()`, becomes the gate's own error).

**Never:**
- No pixel-diff / visual-regression baseline, no automated "looks right" pass/fail -- the PNGs
  and contact sheet feed a human/LLM reviewer's judgment only (epic non-goal).
- No new slide-enumeration mechanism -- `manifest.json` is the only source of slide identity.
- No cross-platform rendering-parity claim.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | built `dist/` + 3-slide `manifest.json` | 3 PNGs + 1 contact sheet in `artifacts`, `status:"ok"`, no findings | No error |
| One slide fails | slide 2's `goto` times out | slides 1 and 3 captured; one `Finding` for slide 2; `status:"ok"` | Isolated per-slide, gate stays ok |
| `dist/` missing | no `presentations/<slug>/dist/` | `render_gate` raises | `run()` records `GateResult(status="error")` for `"render"` only; other gates unaffected |
| No usable Chromium | both launch attempts fail | `render_gate` raises | Same as above |
| All slides fail | every `goto`/`screenshot` throws | `status:"ok"`, no artifacts, one `Finding` per slide, no contact sheet | Isolated per slide; gate itself never raises |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_qa.py` -- add `render_gate`,
  `_serve_dist_dir`, `_capture_slide`, `_build_contact_sheet`; register
  `DEFAULT_GATES["render"]`.
- `pixi.toml` -- `[feature.pyforge-herald.dependencies]` -- add `playwright`,
  `playwright-python`, `pillow` (none currently present; render gate needs a headless browser +
  image compositing).
- `src/shared/packages/pyforge-herald/tests/test_deck_qa.py` -- extend with render-gate tests
  against a synthetic minimal `dist/` fixture under `tmp_path` (no Node/npm needed).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py` -- reference only:
  the static-server + Chromium-fallback + per-item isolation + `_suppress_close` teardown
  pattern this story mirrors.
- `presentations/agentic-sdlc/` -- worked example, manual verification only; not modified.

## Tasks & Acceptance

**Execution:**
- [x] `pixi.toml` -- add `playwright`, `playwright-python`, `pillow` to
      `[feature.pyforge-herald.dependencies]` -- the render gate's only new runtime deps.
- [x] `deck_qa.py` -- add `_serve_dist_dir(directory: Path) -> tuple[httpd, port]` -- ephemeral
      loopback static server, ported from `board.py::_serve_layout_dir`.
- [x] `deck_qa.py` -- add `_build_contact_sheet(png_paths: list[Path], out_path: Path) -> None`
      -- Pillow grid composite labeled by slide id; skipped when zero PNGs captured.
- [x] `deck_qa.py` -- add `render_gate(context: GateContext) -> GateResult` -- resolves
      `presentations/<slug>/{src/slides/manifest.json,dist/}`, serves `dist/` via
      `_serve_dist_dir`, launches Chromium (fallback chain), captures each slide to
      `.herald/deck-qa/<slug>/render/<slide-id>.png` with per-slide isolation, calls
      `_build_contact_sheet`, tears down safely (`_suppress_close`-style).
- [x] `deck_qa.py` -- `DEFAULT_GATES["render"] = render_gate` -- zero change to `run()`,
      `cli.py`, or the report schema.
- [x] `tests/test_deck_qa.py` -- cover every I/O matrix row above against a synthetic
      `tmp_path`-scoped deck (minimal static HTML reading `location.hash`, no real Vite build).

**Acceptance Criteria:**
- Given the epic's open serve-mode decision, when the render gate serves a built deck, then it
  uses a throwaway local static server, never `file://`.
- Given the worked-example deck built via `npm run build`, when `herald deck qa agentic-sdlc`
  runs, then artifacts include exactly one PNG per `manifest.json` entry plus one contact sheet
  under `.herald/deck-qa/agentic-sdlc/render/`.
- Given one slide whose capture raises, when the render gate runs, then that slide gets a
  `Finding` and no PNG, every other slide still captures, and `GateResult.status` stays `"ok"`.
- Given `presentations/<slug>/dist/` does not exist, when the render gate runs, then `run()`'s
  existing per-gate isolation turns the raise into `GateResult(status="error", ...)` for
  `"render"` alone.
- Given any artifact path the gate records, when the report is serialized, then every value is
  a plain `str`.
- Given every Chromium/network call the gate makes, when it executes, then each carries an
  explicit bounded timeout.

## Spec Change Log

## Review Triage Log

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6 (high 1, medium 2, low 3)
- defer: 1 (low 1)
- reject: 5 (low 5)
- addressed_findings:
  - `[high]` `[patch]` The contact-sheet composite build ran outside any per-slide isolation --
    a `_build_contact_sheet` failure (corrupt PNG, disk full) escaped `render_gate` entirely,
    which `run()`'s own per-gate isolation then converted the WHOLE gate to `status:"error"`,
    discarding every already-captured slide's `Finding`/artifact. Wrapped the call in its own
    try/except, converting a failure into one `Finding(slide_id="contact-sheet", ...)` while
    keeping every already-captured slide's own artifact. Added
    `test_render_gate_isolates_a_contact_sheet_build_failure`.
  - `[medium]` `[patch]` The per-slide capture loop caught only `except Exception`, not
    `except (Exception, SystemExit)` -- `board.py`'s own near-identical per-item loop
    deliberately catches both, with an in-file comment recording that Playwright's own internals
    have raised `SystemExit` live and that a bare `except Exception` there discarded every
    already-measured result. This story claimed to mirror that isolation "verbatim" but silently
    dropped this one hardening. Changed to `except (Exception, SystemExit) as exc:`.
  - `[medium]` `[patch]` `pyproject.toml`'s `dependencies` list did not declare `playwright`/
    `pillow` even though `render_gate` imports both directly -- a `pip install` of the package's
    own built wheel (`pyforge-herald-build-dist`) would `ImportError` at runtime. `pixi.toml`
    only carried the conda-forge split (`playwright` + `playwright-python`); the PyPI
    distribution is the single package `playwright`. Added `playwright>=1.62.0` and
    `pillow>=12.3.0` to `pyproject.toml`'s `dependencies`.
  - `[low]` `[patch]` Slide ids from `manifest.json` and `context.slug` were used unsanitized in
    filesystem paths -- a `..`-containing id/slug could write/read outside the intended
    directories, and a duplicate id (or one colliding with the reserved `contact-sheet` composite
    filename) silently overwrote an earlier slide's own PNG. Added `_single_path_segment`
    validation (`render_gate` now raises on an unsafe `slug`; `_slide_id` falls back to the
    positional id on an unsafe manifest id) plus a `seen_ids` set that disambiguates any
    collision, including against the reserved name. Added
    `test_render_gate_rejects_a_traversal_slug`,
    `test_render_gate_slide_id_with_path_separator_falls_back_to_positional`,
    `test_render_gate_duplicate_ids_are_disambiguated`.
  - `[low]` `[patch]` No test exercised a malformed `manifest.json` (invalid JSON, or valid JSON
    that is not a list) -- both of `render_gate`'s own documented raise branches for this were
    untested. Added `test_render_gate_malformed_manifest_json_raises` and
    `test_render_gate_manifest_not_a_list_raises`.
  - `[low]` `[patch]` No test exercised an unusable/unimportable `playwright` install -- the
    `except Exception as exc: raise RuntimeError(f"playwright is not usable: {exc}")` branch was
    untested. Added `test_render_gate_unimportable_playwright_raises` (`sys.modules` patching).

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6 (high 1, medium 3, low 2)
- defer: 0
- reject: 12 (low 12)
- addressed_findings:
  - `[high]` `[patch]` `_single_path_segment`'s traversal guard normalized the candidate through
    `Path(...).parts` before counting segments, so a disguised traversal string like `"./.."` (or
    `"..//"`) measured as the single part `".."` even though the raw string contained a literal
    `/` -- confirmed by direct reproduction that it made `render_dir` (and `deck_dir`) resolve
    outside the intended `.herald/deck-qa/<slug>/` tree via `context.slug`, with `render_gate`
    unconditionally `rmtree`ing whatever that resolved to. Rewrote the guard to check the raw
    string for `/`/`\` directly, never via `Path()` normalization. Added
    `test_render_gate_rejects_a_dotted_slash_traversal_slug`,
    `test_single_path_segment_rejects_dotted_slash_traversal`.
  - `[medium]` `[patch]` The Chromium launch-fallback except clauses and `_suppress_close` caught
    only `Exception`, not `SystemExit`, inconsistent with the per-slide capture loop (same file,
    same story) which explicitly catches `(Exception, SystemExit)` because "playwright's own
    internals have raised `SystemExit` live" (Design Notes) -- and `_suppress_close`'s own
    docstring promises "swallowing anything it raises." Changed both launch-fallback except
    clauses and `_suppress_close` to `except (Exception, SystemExit)`. Added
    `test_render_gate_no_usable_chromium_raises_even_on_system_exit`,
    `test_suppress_close_swallows_system_exit_too`.
  - `[medium]` `[patch]` `render_dir` was `rmtree`'d and recreated *before* Chromium's own launch
    was confirmed to work -- a "no usable chromium" failure (a documented, expected failure mode
    in the I/O matrix) destroyed the previous run's PNGs/contact-sheet with nothing produced to
    replace them, working against the gate's stated purpose of leaving a reviewer evidence to look
    at instead of trusting a clean build. Moved the `rmtree`/`mkdir` to occur only after a
    successful browser launch, immediately before the per-slide capture loop.
  - `[medium]` `[patch]` `pyproject.toml`'s `playwright` floor (`>=1.62.0`) disagreed with
    `pixi.toml`'s (`>=1.62.1`) for what the former's own added comment describes as the same
    runtime dependency -- playwright's Python package and its bundled browser build are
    version-coupled, so a `pip install` of the built wheel could resolve a mismatched
    playwright/browser pair. Raised the `pyproject.toml` floor to `>=1.62.1` to match.
  - `[low]` `[patch]` `_single_path_segment` had no type guard, unlike `_slide_id`'s established
    local convention of checking `isinstance(raw_id, str)` before calling it -- called directly on
    `context.slug` with no such check, so a non-string slug would raise a raw `TypeError` out of
    `Path()` instead of the function's documented `RuntimeError("invalid slug ...")`. Added an
    `isinstance(candidate, str)` guard. Added `test_single_path_segment_rejects_non_string_input`.
  - `[low]` `[patch]` Two tests (`test_render_gate_missing_dist_raises_and_run_isolates_it`,
    `test_render_gate_missing_manifest_raises`) both asserted only the generic substring "does not
    exist", which both failure messages share, so neither test actually proved which check fired.
    Tightened both to match the distinguishing filename (`"dist does not exist"` /
    `r"manifest\.json does not exist"`).

## Design Notes

`render_gate` lives inside `deck_qa.py` rather than a new module -- Story 14.1's own shipped
docstring commits to "all gates live in this one file per the epic's Surface lines," so this
story continues that precedent rather than introducing a cross-module registry.

Slide capture mirrors `board.py::_run_check_layout`'s two-tier isolation exactly: an outer
guard (no `dist/`, no Chromium at all) that's allowed to raise and let `run()`'s own per-gate
try/except handle it, and an inner per-slide guard that never lets one bad slide unwind the
loop. Chromium launch: `p.chromium.launch(channel="chrome")` first, bare `p.chromium.launch()`
on failure, matching the existing local precedent verbatim rather than inventing a new fallback
order.

`.herald/deck-qa/<slug>/render/` (not `presentations/<slug>/`) keeps render output beside the
other operator-local `.herald/` state (`herald.db`, `bridge-state.json`) rather than inside the
deck's own tracked/gitignored tree, and is `rmtree`'d then recreated at the start of each run so
a shrunk manifest never leaves a stale PNG looking current.

## Verification

**Commands:**
- `pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/test_deck_qa.py -v` -- expected: all new render-gate tests pass
- `pixi run -e pyforge-herald pyforge-herald-test` -- expected: full existing suite stays green

**Manual checks:**
- `cd presentations/agentic-sdlc && npm install && npm run build && cd -` then
  `pixi run -e pyforge-herald herald deck qa agentic-sdlc --repo-root .` -- inspect
  `.herald/deck-qa/agentic-sdlc/render/` for one PNG per `manifest.json` entry (currently 50,
  not the epic's stated 45 -- the deck has grown since the epic was written) plus one
  `contact-sheet.png`.

## Auto Run Result

Status: done

**Summary.** Story 14.2 adds `render_gate` to `deck_qa.py`, registered as `DEFAULT_GATES["render"]`:
it serves a built deck (`presentations/<slug>/dist/`) over a throwaway local static server (not
`file://` -- resolves the epic's own open serve-mode decision), drives headless Chromium through
every `#/<n>` slide named by `presentations/<slug>/src/slides/manifest.json`, screenshots each to
`.herald/deck-qa/<slug>/render/<slide-id>.png`, and composes a Pillow contact sheet -- evidence a
reviewer looks at instead of trusting a clean build. A single slide's capture failure is isolated
as a `Finding`; only a genuinely unusable environment (no `dist/`, no `manifest.json`, no usable
Chromium) raises, which `run()`'s existing per-gate isolation (Story 14.1) turns into
`GateResult(status="error", ...)` for `"render"` alone. Verified end-to-end against the real
50-slide worked example (`presentations/agentic-sdlc/`) in the first review pass: 50 PNGs + 1
contact sheet, `status:"ok"`, zero findings. Two review passes have now run against this diff (see
Review Triage Log): the first hardened the initial implementation (contact-sheet isolation,
`SystemExit` handling in the per-slide loop, packaging metadata, path-safety validation); the
second found and fixed a real path-traversal bypass in that same path-safety guard, plus three
further correctness/consistency gaps.

**Files changed (cumulative, both review passes):**
- `pixi.toml` -- `[feature.pyforge-herald.dependencies]`: added `playwright`, `playwright-python`,
  `pillow` (the render gate's only new runtime deps; none were present before).
- `src/shared/packages/pyforge-herald/pyproject.toml` -- added `playwright`, `pillow` to
  `dependencies` (first review pass: the conda-only `pixi.toml` addition left the PyPI wheel/sdist
  metadata silently missing both); second pass raised the `playwright` floor from `>=1.62.0` to
  `>=1.62.1` to match `pixi.toml`'s own floor exactly.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_qa.py` -- new `render_gate`,
  `_serve_dist_dir`, `_suppress_close`, `_slide_id`, `_single_path_segment`, `_build_contact_sheet`,
  `DEFAULT_GATES["render"]`; per-slide and contact-sheet-build isolation; slug/slide-id path-safety
  validation with duplicate/reserved-name disambiguation (first pass). Second pass: closed a
  traversal bypass in `_single_path_segment` (rejects `/`/`\` directly rather than via `Path()`
  normalization, which silently let `"./.."`-shaped strings through), added a type guard to the
  same function, made `SystemExit` handling consistent across the Chromium launch-fallback and
  `_suppress_close` (matching the per-slide loop's own already-justified handling), and moved the
  `render_dir` wipe to occur only after a successful Chromium launch.
- `src/shared/packages/pyforge-herald/tests/test_deck_qa.py` -- 22 new tests in the first pass
  (every I/O matrix row from the spec, plus regression tests for malformed manifests, an
  unimportable `playwright`, path-traversal rejection/fallback, duplicate-id disambiguation, and
  contact-sheet build-failure isolation); 5 more in the second pass (traversal-bypass regression at
  both the `render_gate` and `_single_path_segment` level, `SystemExit` handling in both the
  Chromium launch fallback and `_suppress_close`, a non-string-slug guard), plus two existing
  assertions tightened to distinguish which of two similarly-worded failure messages actually
  fired.
- `src/shared/packages/pyforge-herald/tests/test_cli_deck_qa.py` -- updated one existing assertion
  (report now legitimately contains the `"render"` gate id instead of an empty `gates` object).

**Review findings breakdown (this pass, 2026-08-14 second review):** 6 patches applied (high 1,
medium 3, low 2), all in `deck_qa.py` / `pyproject.toml` / `test_deck_qa.py`, each with a dedicated
regression test. The high-severity finding: `_single_path_segment`'s guard measured "one path
segment" via `Path(candidate).parts`, but `Path` normalizes away a leading `./` or trailing `/.`
-- so `"./.."` (or `"..//"`) measured as the single part `".."` even though the raw string
contained a literal `/`, a disguised traversal string the guard's own stated purpose ("no `/`, no
`..`") was supposed to reject. Confirmed by direct reproduction: passed as `context.slug`, it made
both `deck_dir` and `render_dir` resolve outside the intended `.herald/deck-qa/<slug>/` tree, and
`render_gate` unconditionally `rmtree`s whatever `render_dir` resolves to -- a real,
destructive-write escape, not a theoretical one. Fixed by checking the raw string for `/`/`\`
directly rather than routing through `Path()` normalization first. Three medium fixes: Chromium
launch-fallback and `_suppress_close` caught only `Exception`, not `SystemExit`, inconsistent with
the per-slide loop's own already-justified `(Exception, SystemExit)` handling in the same file (and
contradicting `_suppress_close`'s own docstring promise); `render_dir` was wiped before Chromium's
own launch was confirmed to work, so a "no usable chromium" failure (a documented, expected failure
mode) destroyed the previous run's evidence with nothing to replace it; and the `playwright`
version floor disagreed between `pixi.toml` (`>=1.62.1`) and `pyproject.toml` (`>=1.62.0`) for what
the latter's own comment describes as the same dependency, risking a mismatched playwright/browser
pair from a wheel install. Two low fixes: `_single_path_segment` gained a type guard (mirroring
`_slide_id`'s own established convention) so a non-string candidate gets the documented
`RuntimeError` instead of a raw `TypeError`; two tests asserting only the generic substring "does
not exist" (shared by two different failure messages) were tightened to match the distinguishing
filename. 12 items rejected (all low), each checked against the actual code, the spec's own stated
non-goals, or `conftest.py` before dropping -- notably: a claim that the suite's autouse
`deny_network` fixture would conflict with `_serve_dist_dir`'s own socket binding, refuted by
reading `conftest.py` (the fixture patches only outbound `connect`/`getaddrinfo`-style calls, never
`bind`/`listen`); a call to make `render_gate` wait for more than `networkidle` before each
screenshot, which conflicts with the spec's own explicit "Never" boundary ("no automated 'looks
right' pass/fail... epic non-goal"); a repeat of the prior pass's already-rejected "no whole-gate
wall-clock budget" finding; a duplicate of the prior pass's already-deferred `DW-FU-14-2` (CI never
provisions Chromium for this suite); and several defensible, precedent-matching design choices
(playwright/pillow as hard rather than optional dependencies, the `channel="chrome"`-first launch
order, `Finding.slide_id`'s reuse of the already-reserved `"contact-sheet"` sentinel) that this
pass judged as reasonable choices rather than defects. 0 deferred this pass (the one CI/Chromium
concern raised was already covered by the existing `DW-FU-14-2`).

**Cumulative review findings (both passes):** first pass -- 6 patches (high 1, medium 2, low 3), 1
deferred (`DW-FU-14-2`), 5 rejected; second pass -- 6 patches (high 1, medium 3, low 2), 0 deferred,
12 rejected.

**Follow-up review recommendation:** true. This pass's highest-severity fix closed a confirmed,
directly-reproduced path-traversal bug with a destructive (`rmtree`) consequence in
security-adjacent code that a prior review pass had already touched once for the identical class of
concern -- exactly the kind of finding that benefits from an independent verification pass rather
than trusting the same review loop's own fix.

**Verification performed (this pass):**
- `pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/test_deck_qa.py -v`:
  46 passed (41 from the first pass + 5 new second-pass tests).
- `pixi run -e pyforge-herald pyforge-herald-test`: 1090 passed, 4 skipped (1085 baseline + 5 net
  new test functions).
- `python scripts/spec_surface_reconcile.py`: pre-existing failure, unrelated to this story --
  `pyforge-mason/spec-django-accelerator-framework` has no memlog for 120 governed files, which
  also caused this same bmad-loop run's earlier Story 14.1 to be marked deferred. Zero files this
  story touches are governed by that spec; not this story's problem to fix.
- `git status` inspected directly after this pass's patches: only the three files listed above are
  dirty, no stray artifacts from the pytest runs.
- Manual end-to-end (`presentations/agentic-sdlc`) was performed in the first review pass only;
  this pass's fixes were verified through the automated suite (including new tests that reproduce
  the exact bypass/exception scenarios that motivated each fix) rather than repeating the manual
  `npm install && npm run build` step, since none of this pass's changes affect the happy-path
  rendering behavior the manual check already covered.

**Recovery note:** this review pass ran after a stuck-orchestrator-baseline incident (documented
project-wide precedent): the bmad-loop task's own bookkeeping (`state.json`) stayed at
`phase: "dev-running"` even though the dev session had completed and committed both Story 14.1
(`c47a46d1`) and Story 14.2 (`9de381a0`), and this worktree's branch had been reset back to
pre-story `HEAD` with the actual commits preserved only on
`attempt-preserve/20260814-202329-6e05-9de381a0`. Per the fleet-wide non-destructive escalation
policy, the preserved branch was fast-forward-merged back onto this worktree's branch (verified
clean fast-forward, working tree matched the spec's own recorded `final_revision` exactly) rather
than re-implementing from scratch, before this review pass began.

**Residual risks:** `DW-FU-14-2` (deferred, pre-existing -- see first-pass breakdown above). This is
a `local-recipes` monorepo PR touching files outside `recipes/` -- per `CLAUDE.md`'s PR CI gate
rule, the PR needs the `maintenance` label at open/update time. `pixi.toml` itself was not changed
by this second pass (only `pyproject.toml`'s already-matching floor was tightened), so
`environment.yaml`/`pixi.lock` do not need regenerating again beyond what the first pass already
produced.
