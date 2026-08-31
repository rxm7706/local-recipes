---
title: 'Image slot scan'
type: 'feature'
created: '2026-08-14'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/docs/specs/presentation-deck.md']
warnings: ['oversized']
baseline_revision: 'ef0b9482d2824018c7cb410f8ae49d160fcebf07'
final_revision: '3ab650982398e8944d250b8c234a0cbc9ed42165'
---

<intent-contract>

## Intent

**Problem:** Herald's deck pipeline can report that a build renders (Story 14.2's render gate)
but never flags a slide shipped with an unfilled image-slot placeholder -- the CAP-2 half of
the "renders but doesn't prove it looks right" gap Story 14.1's report interface exists to
close, still unaddressed since `DEFAULT_GATES` carries only `"render"`.

**Approach:** Add `image_slot_gate` to `deck_qa.py`, registered as `DEFAULT_GATES["image-slot"]`,
that reads each manifest-listed slide's generated fragment
(`presentations/<slug>/src/slides/fragments/<id>.html`) and flags any that still contain an
unfilled image-slot placeholder, in either its raw prototype spelling (`<image-slot ...>`) or
its extractor-converted spelling (`class="image-slot"` div) -- a second real gate proving the
report shape holds for more than one gate (CAP-3).

## Boundaries & Constraints

**Always:**
- Report-only: never mutates deck sources, never triggers extraction or a build.
- Slide identity comes from `presentations/<slug>/src/slides/manifest.json`, exactly like
  `render_gate` (Story 14.2) -- no new slide-enumeration mechanism (epic constraint). Per
  manifest entry, the fragment to scan is `src/slides/fragments/<id>.html`, matching the
  extractor's own naming convention (`extract-slides.mjs`: fragment filename == manifest id).
- Recognizes BOTH spellings in the same scanned fragment file: the raw/unconverted
  `<image-slot` opening tag, and the extractor's converted `class="image-slot"` placeholder
  `<div>` (the normal case) -- either one flags that slide.
- One slide's own scan failure (missing/unreadable fragment file) is isolated to a `Finding`
  for that slide id; every other slide is still scanned and the gate's own `status` stays
  `"ok"` -- mirrors `render_gate`'s per-slide isolation.
- `context.slug` is validated with the existing `_single_path_segment` guard before any path is
  built from it, same as `render_gate`.
- A genuinely unusable environment -- `manifest.json` absent/malformed, or `fragments/` itself
  absent -- raises; `run()`'s existing per-gate isolation (Story 14.1) turns that into
  `GateResult(status="error", ...)` for `"image-slot"` alone.

**Never:**
- Not a general lorem-ipsum/"Click to add" placeholder scanner (epic's explicit non-goal) --
  only the two named `image-slot` spellings.
- Not a WCAG/accessibility check, not a pixel-diff, no fix-and-rebuild.
- Never touches `dist/` or `.herald/` -- this gate produces `findings` only, no `artifacts`
  (unlike `render_gate`, it needs no build and no browser).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path, one unfilled slide | one fragment has `class="image-slot"` divs, every other fragment clean | `status:"ok"`, exactly one `Finding` for that slide id | No error |
| Every slot filled | no fragment matches either spelling | `status:"ok"`, `findings == []` | No error |
| Raw unconverted tag | a fragment contains `<image-slot placeholder="…">` (not extractor-converted) | flagged exactly like the converted-div case | No error |
| Missing fragment file | manifest lists an id with no matching file under `fragments/` | that slide gets one `Finding`; every other slide still scanned | Isolated, gate stays `"ok"` |
| `manifest.json` missing | `presentations/<slug>/src/slides/manifest.json` absent | `image_slot_gate` raises | `run()` records `status:"error"` for `"image-slot"` alone |
| `fragments/` directory missing | directory absent | `image_slot_gate` raises | Same as above |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_qa.py` -- add `import re`,
  `_IMAGE_SLOT_TAG_RE`, `_IMAGE_SLOT_DIV_RE`, `image_slot_gate`; register
  `DEFAULT_GATES["image-slot"]`.
- `src/shared/packages/pyforge-herald/tests/test_deck_qa.py` -- extend with image-slot-gate
  tests against a synthetic `tmp_path`-scoped `presentations/<slug>/src/slides/{manifest.json,
  fragments/}` tree (no `dist/`/Playwright needed -- this gate is pure file scanning).
- `src/shared/packages/pyforge-herald/tests/test_cli_deck_qa.py` -- update
  `test_deck_qa_returns_0_and_prints_a_parseable_report`'s gate-id assertion to
  `{"render", "image-slot"}` (both `"error"` with no `presentations/pyforge-warden/` under
  `tmp_path`).
- `presentations/agentic-sdlc/` -- worked example, manual verification only; not modified. Its
  "In action" slide is now manifest id `47-in-action` (50 slides total) -- the epic's stated
  "slide 40" predates the deck's growth past 45 slides; Story 14.2 already recorded this same
  drift. Verified directly: `grep -l image-slot src/slides/fragments/*.html` returns exactly
  `47-in-action.html`, and the prototype source (`project/Agentic SDLC.dc.html`) has exactly
  three `<image-slot ...>` tags, all inside that same slide's `<section>`.

## Tasks & Acceptance

**Execution:**
- [x] `deck_qa.py` -- add `import re` and two module-level compiled patterns:
      `_IMAGE_SLOT_TAG_RE = re.compile(r"<image-slot\b")`,
      `_IMAGE_SLOT_DIV_RE = re.compile(r'class="image-slot"')`.
- [x] `deck_qa.py` -- add `image_slot_gate(context: GateContext) -> GateResult`: validate
      `context.slug` via `_single_path_segment` (raise if unsafe); load+validate
      `presentations/<slug>/src/slides/manifest.json` (absent/malformed -> raise, mirroring
      `render_gate`'s own manifest checks); raise if `fragments/` is not a directory; for each
      manifest entry resolve its slide id via `_slide_id` and read
      `fragments/<id>.html`, appending a `Finding(slide_id=id, message=...)` when either
      pattern matches or the file can't be read.
- [x] `deck_qa.py` -- `DEFAULT_GATES["image-slot"] = image_slot_gate` -- zero change to
      `run()`, `cli.py`, or the report schema.
- [x] `tests/test_deck_qa.py` -- cover every I/O matrix row above against synthetic fragments.
- [x] `tests/test_cli_deck_qa.py` -- update the gate-id-set assertion for the new gate.

**Acceptance Criteria:**
- Given the worked-example deck's real sources (`presentations/agentic-sdlc/`), when
  `herald deck qa agentic-sdlc` runs, then the report's `"image-slot"` gate has exactly one
  finding, for slide id `47-in-action`, and every other slide is clean.
- Given a deck where every fragment is free of both spellings, when the gate runs, then
  `status` is `"ok"` and `findings` is empty.
- Given a fragment containing the raw `<image-slot placeholder="…">` tag, when the gate runs,
  then that slide is flagged exactly like the converted-div case.
- Given one slide's fragment file is missing, when the gate runs, then that slide gets a
  `Finding`, every other slide is still scanned, and `GateResult.status` stays `"ok"`.
- Given `manifest.json` is absent, when the gate runs, then `run()`'s per-gate isolation turns
  the raise into `GateResult(status="error", ...)` for `"image-slot"` alone.
- Given any artifact/finding the gate produces, when the report is serialized, then every value
  round-trips through JSON exactly (matches the schema `render_gate` already proved).

## Spec Change Log

## Review Triage Log

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (high 0, medium 2, low 1)
- defer: 1 (low 1)
- reject: 9 (low 9)
- addressed_findings:
  - `[medium]` `[patch]` The per-slide fragment-read guard caught only `OSError`, not
    `UnicodeDecodeError` (a `ValueError` subclass) -- a fragment that exists but contains
    invalid UTF-8 bytes escaped the per-slide isolation the docstring explicitly promises and
    instead errored the whole gate. Confirmed independently by both reviewers. Changed to
    `except (OSError, UnicodeDecodeError)`. Added
    `test_image_slot_gate_isolates_a_non_utf8_fragment`.
  - `[medium]` `[patch]` `_IMAGE_SLOT_TAG_RE`'s `\b` boundary right after "image-slot" is
    satisfied by the word/non-word transition into a following `-` regardless of what comes
    next, so the pattern also matched an unrelated hyphenated custom element like
    `<image-slot-carousel>` -- a false-positive risk. Rewrote as a lookahead
    (`(?=[\s/>])`) that only accepts whitespace, `/`, or `>` after "image-slot". Added
    `test_image_slot_gate_does_not_over_match_a_hyphenated_custom_element`.
  - `[low]` `[patch]` Both patterns were case-sensitive; the extractor's own `<image-slot>` tag
    match is also case-sensitive, so a mixed-case `<Image-Slot>` in a prototype would slip past
    both extraction and this gate's defensive "raw unconverted tag" catch. Added
    `re.IGNORECASE` to both `_IMAGE_SLOT_TAG_RE` and `_IMAGE_SLOT_DIV_RE`. Added
    `test_image_slot_gate_matches_case_insensitively`.
- Deferred: `DW-FU-14-3` -- no `seen_ids`-style duplicate-manifest-id disambiguation (unlike
  `render_gate`'s own guard in the same file); low consequence (read-only, cosmetic duplicate
  `Finding` at worst) and structurally near-impossible against the real extractor's
  index-prefixed unique ids. Raised independently by both reviewers.
- Rejected (9, all low): class-attribute regex not tolerant of single quotes/extra classes
  (extractor deterministically emits one exact double-quoted-single-class form; broadening
  would tolerate a format the pipeline never produces -- Simplicity First); "tests are
  circular" (synthetic fixtures match `render_gate`'s own established precedent, and the AC's
  real-deck manual check already exercises actual extractor output); no awareness of HTML
  comments/script blocks (fragments are extractor-generated semantic bodies per the pipeline's
  own contract, never hand-edited or containing script/template blocks -- out of this gate's
  documented scope, which the epic itself keeps to a simple regex match, not a full parser);
  empty-manifest-without-
  `fragments/`-dir raising (correct: means extraction never ran, matches the spec's own
  "genuinely unusable environment raises" boundary); `slide_id` "unsanitized" path use (false --
  `_slide_id` already guards via `_single_path_segment`, confirmed by reading the existing
  code; Edge Case Hunter independently reached the same conclusion); malformed non-dict manifest
  entry uncovered (already safely handled by `_slide_id`'s existing fallback, same as above);
  blanket `except Exception` around `json.loads` (verbatim match of `render_gate`'s own
  already-twice-reviewed pattern in this file); unconditional `status="ok"` regardless of
  finding volume (matches the report interface's own documented status semantics --
  `status` reports gate execution health, not finding severity); docstring's "three parked
  `.pptx`-contingent gates" count (refers to a disjoint, still-accurate set of future gates,
  not render/image-slot).

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 12: (high 1, medium 2, low 9)
- addressed_findings:
  - none

Independent re-review (Blind Hunter + Edge Case Hunter, no prior context) over the identical
diff. Every finding converged with the pass above and was rejected on the same evidence:
`[high]` "unsanitized `slide_id`" path-traversal claim -- false, `_slide_id` already guards via
`_single_path_segment` (confirmed by reading the code; both reviewers independently converged on
this exact conclusion, mirroring the prior pass); `[medium]` malformed non-dict manifest entry
uncovered -- already safely handled by `_slide_id`'s existing fallback, same as above;
`[medium]` class-attribute regex intolerant of multiple classes/single quotes -- re-confirmed
against `extract-slides.mjs` (`class="image-slot"` is a deterministic, exact, double-quoted,
single-class literal; no other shape is ever produced); `[low]` x8: HTML-comment-blind text scan
(fragments are extractor-generated, never hand-edited or containing comments/script -- out of
this gate's documented scope), blanket `except Exception` around `json.loads` conflating
read/parse failures (verbatim match of `render_gate`'s own precedent), weak message-only
assertion on the malformed-JSON test (matches this suite's established `match=`-substring
convention throughout), no test for an empty manifest array (behavior is already correct --
zero-iteration loop, no bug to cover), no test for duplicate manifest ids (already tracked under
`DW-FU-14-3`; not re-minted), `round_trips_through_json` test's mismatched `slug="x"` fixture
(cosmetic, reviewer's own words: harmless), `artifacts == []` asserted in only one test (test-
coverage preference, not a behavior gap), and the module comment's claim that the extractor's own
tag match is case-sensitive too -- verified true directly against `extract-slides.mjs`'s regex
(no `i` flag).

## Design Notes

**Fragments-only, not also the raw `.dc.html` prototype.** The epic phrase "in prototype/
fragment sources" reads as the umbrella term for the deck's hand-authored/generated slide
content, not a directive to scan two separate directories with two separate slide-identity
spaces. Scanning the prototype directly would mean re-deriving slide identity from `<section>`
position (a second, parallel enumeration to `manifest.json`), which the epic's own constraints
forbid ("no new slide-enumeration mechanism"). Scanning `fragments/` -- the actual generated,
shipped per-slide source `index.js` globs into `slides[]` -- and recognizing BOTH spellings
there satisfies "must catch both spellings": the raw tag is caught defensively (a fragment that
somehow wasn't run through extraction), the converted div is caught in the normal case.

**Small manifest-loading duplication is intentional.** `render_gate` already inlines
manifest-loading/validation (open, `json.loads`, list-type check). Rather than extracting a
shared helper -- which would touch already-reviewed, twice-hardened code outside this story's
own surface for roughly eight lines of savings -- `image_slot_gate` duplicates the same small
block locally. Surgical over DRY here: `render_gate`'s manifest handling has already been
through two adversarial review passes (see Story 14.2's Review Triage Log); reworking it to
share code is a refactor this story doesn't need to make.

**Gate id `"image-slot"`, not `"placeholder"`.** Keeps the id unambiguous against the epic's
explicit non-goal (no generic lorem-ipsum/"Click to add" placeholder scanner) -- the id names
exactly what this gate detects.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks:**
- `pixi run -e pyforge-herald herald deck qa agentic-sdlc --repo-root .` -- inspect the
  `"image-slot"` gate in the printed report: exactly one finding, slide id `47-in-action`,
  every other slide id absent from `findings`.

## Auto Run Result

Status: done

**Summary.** Story 14.3 adds `image_slot_gate` to `deck_qa.py`, registered as
`DEFAULT_GATES["image-slot"]`: for each `manifest.json`-listed slide, it reads the generated
fragment (`presentations/<slug>/src/slides/fragments/<id>.html`) and flags any that still
contain an unfilled image-slot placeholder, in either the raw prototype spelling
(`<image-slot ...>`) or the extractor-converted spelling (`class="image-slot"` div) -- the CAP-2
half of the "renders but doesn't prove it looks right" gap, and the second real gate proving
Story 14.1's report shape holds for more than one gate (CAP-3). Report-only: pure file scanning,
no build, no browser, no artifacts. Verified end-to-end against the real worked example
(`presentations/agentic-sdlc/`, 50 slides): exactly one finding, slide id `47-in-action` (the
deck grew since the epic doc was written -- "slide 40" is stale, already noted by Story 14.2;
confirmed directly against the real fragment and prototype source before writing the spec).

**Files changed:**
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_qa.py` -- new `_IMAGE_SLOT_TAG_RE`,
  `_IMAGE_SLOT_DIV_RE`, `image_slot_gate`, `DEFAULT_GATES["image-slot"]`; per-slide isolation on
  a missing/unreadable/non-UTF8 fragment; whole-gate raise on missing/malformed `manifest.json`
  or missing `fragments/` (mirrors `render_gate`'s own raise-on-unusable-environment pattern).
  Review pass: case-insensitive matching on both patterns, a lookahead-based tag pattern instead
  of a `\b`-bounded one (avoids matching an unrelated hyphenated tag), and `UnicodeDecodeError`
  added to the per-slide isolation guard alongside `OSError`.
- `src/shared/packages/pyforge-herald/tests/test_deck_qa.py` -- 12 new tests covering every I/O
  matrix row (happy path, all-clean, raw tag, both-spellings-one-finding, missing fragment,
  missing manifest + `run()` isolation, missing `fragments/`, malformed/non-list manifest JSON,
  traversal-slug rejection, JSON round-trip); 3 more from the review pass (non-UTF8 fragment
  isolation, case-insensitive match, hyphenated-tag non-match regression).
- `src/shared/packages/pyforge-herald/tests/test_cli_deck_qa.py` -- updated
  `test_deck_qa_returns_0_and_prints_a_parseable_report`'s gate-id-set assertion to
  `{"render", "image-slot"}`.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- new `DW-FU-14-3` (duplicate-
  manifest-id disambiguation, deferred; see Review Triage Log).

**Review findings breakdown:** 3 patches applied (medium 2, low 1), 1 deferred (low), 9 rejected
(all low) -- see Review Triage Log for the full breakdown and per-finding rationale. Both
independent reviewers (Blind Hunter, Edge Case Hunter) converged on the same highest-value
finding (`UnicodeDecodeError` isolation) without shared context, which is why it was patched
with confidence; the hyphenated-tag over-match and case-sensitivity gaps were each raised by
one reviewer and patched as cheap, zero-risk hardening consistent with the gate's own stated
defensive purpose (catching things that slipped past extraction). Findings rejected were either
already safely handled by pre-existing, reused code (`_slide_id`'s own guards), matched an
already-twice-reviewed precedent verbatim (`render_gate`'s manifest-loading style), or asked
for tolerance/robustness beyond what the extractor's own deterministic output or the epic's
explicit scope calls for.

**Follow-up review recommendation:** false. All three patches are localized to
`image_slot_gate` (a read-only, non-destructive, newly-added function with no security or data-
loss consequence, unlike Story 14.2's rmtree-adjacent path-traversal fix), each carries a
dedicated regression test, and the full existing suite plus the real-deck manual check both stay
green after the patches. This is a few localized, low-consequence fixes, not a volume or
severity profile that benefits from an independent second pass.

**Verification performed (final):**
- `pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/test_deck_qa.py src/shared/packages/pyforge-herald/tests/test_cli_deck_qa.py -v`: 64 passed.
- `pixi run -e pyforge-herald pyforge-herald-test`: 1104 passed, 4 skipped (pre-existing skips,
  unrelated).
- `pixi run -e pyforge-herald herald deck qa agentic-sdlc --repo-root .`: `"image-slot"` gate --
  `status: "ok"`, exactly one finding, `slide_id: "47-in-action"`, no other slide flagged.
  Re-confirmed identical after the review patches.
- `git status` inspected directly: only the three source/test files listed above are dirty; no
  stray artifacts from the pytest/manual runs.

**Residual risks:** `DW-FU-14-3` (deferred, this pass -- see breakdown above). This is a
`local-recipes` monorepo diff touching files outside `recipes/`; per `CLAUDE.md`'s PR CI gate
rule, any PR opened for this change needs the `maintenance` label at open/update time.
`pixi.toml` was not changed by this story (pure-stdlib gate, no new dependency), so
`environment.yaml`/`pixi.lock` need no regeneration.

**Second review pass (2026-08-14, re-invocation).** A follow-on `bmad-dev-auto` invocation hit
the known stuck-orchestrator-baseline bug (`.claude/memory/project/the-stuck-orchestrator-
baseline-bug-*.md`): the orchestrator's recorded baseline had drifted to the PR #506 merge commit
while the first dev session was still running, so a second attempt started against a worktree
whose branch no longer contained this story's own commits. Recovered losslessly: the full chain
(14.1, 14.2, 14.2 review-fix, 14.3) was intact on `attempt-preserve/20260814-202329-6e05-3ab65098`,
and the worktree's HEAD was a clean ancestor of that branch's tip, so `git merge --ff-only`
restored everything with zero conflict risk. Per this workflow's `status: done` routing, the
recovery was followed by a genuine fresh, independent review pass (Blind Hunter + Edge Case
Hunter, no shared context, no memory of the prior pass) over the identical diff --
`ef0b9482d2..HEAD` was unchanged by the recovery. All 12 deduplicated findings converged with the
first pass's own conclusions and were rejected on re-verified evidence (see Review Triage Log);
zero new patches, zero new defers -- the duplicate-slide-id finding this pass mapped onto the
already-tracked `DW-FU-14-3` rather than minting a second ledger entry for the same substance.
Re-ran `pixi run -e pyforge-herald pytest .../test_deck_qa.py .../test_cli_deck_qa.py`: 64 passed,
confirming the recovered code is intact. No commit needed (working tree was already clean --
`git status` confirmed no changes this pass); `final_revision` is unchanged.

**Note on this run's starting state:** this worktree's branch (`bmad-loop/20260814-202329-6e05/
14-3-image-slot-scan`) was created from `main` before Stories 14.1/14.2 had landed there --
those two stories' commits (`c47a46d1b7`, `9de381a01e`, `ef0b9482d2`) existed only on their own
sibling loop worktrees' branches, not yet merged. Per the fleet-wide non-destructive escalation
policy (preserve, never re-implement from scratch), this worktree's branch was fast-forwarded
onto `bmad-loop/20260814-202329-6e05/14-2-headless-render-gate` (a clean, verified fast-forward
-- confirmed via `git merge-base --is-ancestor`) before any planning began, so this story could
build on the real, already-shipped `deck_qa.py` report interface and render gate rather than an
outdated base missing them entirely.
