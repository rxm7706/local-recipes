<!-- RECOVERED 2026-07-25 from Claude Code session transcript fb91651f-d7e7-43e5-8794-b0d042511216.jsonl (~/.claude/projects); this is the ORIGINAL spec incl. its dev/review narrative, not an epics.md regeneration. -->
---
title: 'Story 2.3: The full supported-construct matrix (ratcheted)'
type: 'feature'
created: '2026-07-16'
status: 'draft'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/implementation-artifacts/epic-2-context.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** `extract/recipe_v1.py`/`meta_v0.py` (Story 2.2) only guarantee no-crash degrade for constructs they don't recognize — `compiler()`/`stdlib()` and `pin_subpackage()` calls currently fall through to `RAW_MALFORMED` (wrongly treated as unidentifiable noise instead of excluded build-tool/intra-recipe refs), and v1's structural `if:`/`then:`/`else:` selector entries (a dict, not a string) degrade the whole branch pair to one `RAW_MALFORMED` component instead of surfacing both conditional branches. v0's `# [sel]` comment selectors already survive extraction (both branches present as separate list items) but carry no condition tag. Both extractors' own docstrings explicitly defer this: "the full construct matrix... is Story 2.3's."

**Approach:** Teach the shared `requirement_component` (in `recipe_v1.py`, imported by `meta_v0.py`) to recognize `compiler()`/`stdlib()`/`pin_subpackage()` calls (post bare-var substitution, before the generic degrade fallback) and exclude them entirely — no `Component` emitted, mirroring `run_constrained`'s existing exclude precedent. Add a v1 `if`/`then`/`else` branch-walker that recursively expands nested conditionals into leaf entries from both branches. Add a v0 raw-text pre-pass capturing `# [cond]` trailing comments keyed by pre-comment content. Both union paths tag the leaf's `Provenance.section` with a `[if:COND]`/`[else:COND]`/`[sel:COND]` string suffix and escalate `extraction_mode` to the already-frozen `UNION_MARKED` enum value (mirrors `pyproject.py`'s existing marker-conditional precedent) when the leaf itself parses cleanly. Extend the 2.2 differential-oracle with new complex-construct fixtures for both formats, verified live against real `rattler_build`/`conda_build` renders.

## Boundaries & Constraints

**Always:**
- `compiler("x")`/`stdlib("x")`/`pin_subpackage("x", ...)` — recognized via a whole-value regex match (`^\$?\{\{\s*(compiler|stdlib|pin_subpackage)\s*\(.*\)\s*\}\}$`, run on the already bare-var-substituted string) — produce ZERO components, never `RAW_MALFORMED` (verified live: `rattler_build` resolves `compiler("c")` to a real matchspec like `'gcc_linux-64 12.*'` under a populated variant config, and `pin_subpackage(...)` to a structured, non-string dict entry in its own rendered output — neither is a real external dependency).
- v1 `if`/`then`/`else` requirements-list entries: `then`/`else` may be a scalar string or a list, and may nest (an entry inside `then`/`else` may itself be another `if` dict) — walk recursively; `then` always contributes, `else` only if present; each leaf goes through the SAME `requirement_component` path as any other entry.
- Section tagging is a STRING SUFFIX on `Provenance.section` only (e.g. `requirements.run[if:linux]`, `...[else:linux]`, `...[sel:win]`) — `interfaces.py`/`models.py`/`verdict.py` and the `Provenance`/`Component` dataclass SHAPES stay untouched (frozen-file gate).
- `extraction_mode=UNION_MARKED` applies ONLY when the leaf's own extraction succeeds as `PARSED` (mirrors `pyproject.py`'s `requirement.marker is not None` precedent exactly); a leaf that ALSO degrades (an unresolved nested construct) keeps its `NAME_ONLY`/`RAW_MALFORMED` mode — the degrade ladder is a more specific signal than the union tag, but the section suffix still applies either way.
- v0 selector pre-pass (`capture_selector_comments`) scans the RAW, un-neutralized manifest text for `<indent>- <content>  # [<cond>]` lines BEFORE `strip_jinja_statements` runs, keyed by the stripped pre-comment content; a collision (two distinct source lines sharing identical pre-comment text under different conditions) resolves last-wins — documented, honest, never a crash.
- Differential-oracle: new `recipe_complex`/`meta_complex` fixtures cover compiler/stdlib, pin_subpackage (via a second output), if/then/else (v1) / `# [sel]` sibling entries (v0), and the name-resolved+expression-version shape. The oracle's rendered-comparison set EXCLUDES compiler/stdlib-resolved names and non-string (pin_subpackage dict) entries before tokenizing — same treatment `run_constraints`' "scipy" already gets in the 2.2 common-case oracle — since extraction deliberately excludes what these two constructs render to.
- `{% for %}`-generated blocks and bare-`{{ }}`-in-v1 stay on 2.2's existing single-degraded-entry behavior; add regression fixtures/tests proving it holds (ratchet, not rewrite).

**Block If:** none identified.

**Never:** real Jinja/expression evaluation of `if` conditions, `compiler()`/`stdlib()` variant resolution, or `pin_subpackage()`'s exact-pin computation — recognition is syntactic pattern-matching only, never execution (NFR-S1 holds); per-iteration `{% for %}` expansion; `# [sel]` capture for non-list-item lines (e.g. `skip: true  # [win]`); touching `verdict.py`/`interfaces.py`/`models.py`'s frozen shapes, or growing `WithholdReason`/`ExtractionMode` (`UNION_MARKED` already exists — no new enum member needed).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `compiler("c")`/`stdlib("c")` in `build:` | v1 `${{ compiler("c") }}` or v0 `{{ compiler('c') }}` | Zero components from that entry | No error |
| `pin_subpackage("foo")` in a multi-output `run:` | v1 `${{ pin_subpackage(name + "-core") }}` | Zero components from that entry | No error |
| v1 `if`/`then`/`else`, both branches | `- if: linux\n  then: [numpy >=1.20]\n  else: [numpy]` | 2 components, sections `run[if:linux]`/`run[else:linux]`, `UNION_MARKED` | No error |
| v1 nested `if` inside `then` | outer `if: linux`, inner `if: x86_64` | Leaf section carries both tags, e.g. `run[if:linux][if:x86_64]` | No error |
| v0 sibling selector entries | `- pywin32  # [win]` / `- unixlib  # [unix]` | 2 components, sections `run[sel:win]`/`run[sel:unix]`, `UNION_MARKED` | No error |
| v0 duplicate pre-comment text, different selectors | two lines with identical dep text, different `# [cond]` | Last-captured condition wins; both components still present | No error, documented limitation |
| Expression-logic on a resolved-name entry | v1 `${{ name }}==${{ version.replace(".", "") }}` | `NAME_ONLY`, name captured, version withheld | No error |
| Oracle: complex fixture, renderer available | `recipe_complex`/`meta_complex` | `extracted-names ⊇ (rendered-names − excluded build-tool/subpackage names)` | Assertion failure on a real gap |

</intent-contract>

## Code Map

- `src/pyforge/warden/extract/recipe_v1.py` -- MODIFY: `requirement_component` gains build-tool/subpackage recognition + exclude (return type becomes `Component | None`); new `walk_if_then_else` recursive branch-walker; `walk_requirements` dispatches dict-shaped entries to it and filters `None` from both walkers' output.
- `src/pyforge/warden/extract/meta_v0.py` -- MODIFY: new `capture_selector_comments` raw-text pre-pass; `_walk_test`'s list comprehension filters `None`; wires the captured selector map into its `requirement_component` calls.
- `tests/fixtures/projects/recipe_complex/recipe.yaml`, `tests/fixtures/projects/meta_complex/meta.yaml` -- NEW: complex-construct fixtures (compiler/stdlib, pin_subpackage via a second output, if/then/else or `# [sel]`, expression-logic-on-resolved-name).
- `tests/conformance/test_extraction_oracle.py` -- MODIFY: two new tests against the complex fixtures; rendered-comparison set excludes compiler/stdlib/pin_subpackage entries before tokenizing.
- `tests/unit/test_recipe_v1_extractor.py`, `tests/unit/test_meta_v0_extractor.py` -- MODIFY: unit coverage for every I/O matrix row above.

## Tasks & Acceptance

**Execution:**
- [ ] `extract/recipe_v1.py` -- add compiler/stdlib/pin_subpackage whole-value regex recognition + exclude in `requirement_component`, change its return type to `Component | None`, update `walk_requirements`'s append to skip `None` -- closes the build-tool/subpackage matrix rows.
- [ ] `extract/recipe_v1.py` -- add `walk_if_then_else` (recursive, scalar-or-list `then`/`else`, section-suffix tagging, `UNION_MARKED` on clean-parse leaves) and dispatch from `walk_requirements` when a requirements-list entry is a dict carrying an `if` key -- closes the v1 selector-union matrix row.
- [ ] `extract/meta_v0.py` -- add `capture_selector_comments` pre-pass over the raw manifest text (before any Jinja-stripping/neutralizing), thread the captured map into its `requirement_component` calls, filter `None` from `_walk_test`'s comprehension -- closes the v0 selector-union matrix row.
- [ ] `tests/fixtures/projects/{recipe_complex,meta_complex}/` + `test_extraction_oracle.py` -- new fixtures + 2 new oracle tests (rendered-comparison excludes compiler/stdlib/pin_subpackage entries) -- satisfies the epics AC's "ratcheted against the 2.2 differential-oracle" clause.
- [ ] `tests/unit/test_recipe_v1_extractor.py` + `test_meta_v0_extractor.py` -- unit tests for every I/O matrix row (compiler/stdlib exclude, pin_subpackage exclude, if/then/else union+nesting, `# [sel]` union+collision, expression-logic degrade) -- direct coverage independent of renderer availability.

**Acceptance Criteria** *(from `epics.md`, preserved verbatim):*

**Given** the construct matrix, **When** a recipe uses them, **Then** `compiler()`/`stdlib()` → build-tool-exclude, `pin_subpackage()` → internal-exclude, `# [sel]`/`if-then-else` → **union both branches + mark**, expression-logic → degrade to name-only+marked (FR5). **And** each rule is ratcheted against the 2.2 differential-oracle (a matrix regression fails CI).

## Spec Change Log

<!-- Append-only. Populated by step-04 during review loops. Empty until the first bad_spec loopback. -->

## Review Triage Log

<!-- Append-only. Populated by step-04 on EVERY review pass. Empty until the first review pass. -->

## Design Notes

**Live-verified renderer behavior (informs the oracle's exclusion set — checked against real `rattler_build` in this repo's `local-recipes` pixi env before writing this spec, not guessed):** under a variant config supplying `c_compiler`/`c_compiler_version`/`target_platform`, `rattler_build` renders `${{ compiler("c") }}` to the STRING matchspec `'gcc_linux-64 12.*'` — a real name that would wrongly satisfy the superset assertion if not excluded from the rendered-comparison set (extraction correctly emits nothing for it). `${{ pin_subpackage(name + "-core", exact=True) }}` renders to a STRUCTURED (non-string) dict entry, `{'pin_subpackage': {'name': 'mypkg-core', 'exact': True}}`, inside the `run` list — the oracle's `_names_from_matchspecs` tokenizer must filter non-string entries before calling `.split()` on them, or it crashes. Separately (also live-verified): rendering `if: linux / then: [numpy >=1.20] / else: [numpy]` under a `target_platform: linux-64` variant selects ONLY the `then` branch — confirming the superset assertion holds naturally for selector-union (extraction's both-branches output is a strict superset of any single render), no exclusion needed on that row.

**Why exclude, not a new `WithholdReason`:** `WithholdReason` models "this dependency exists but we can't determine X about it" — `compiler()`/`stdlib()`/`pin_subpackage()` references aren't dependencies to withhold judgment on at all (a build-tool ref resolves outside the Python/conda package graph; a subpackage ref is the recipe's own other output). `run_constrained`/`run_constraints` already established this exact "recognized only to be skipped, never a `Component`" precedent in 2.2 — this story follows it rather than inventing a parallel mechanism.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: all prior 1.x/2.x suites unchanged + new test files/fixtures green; sole-ownership/no-execution/socket-deny meta-guards stay green automatically for the modified `extract/` files.
- Manual: `git diff --stat` shows zero changes to `verdict.py`, `interfaces.py`, `models.py`'s frozen enums, and to `Provenance`/`Component`'s field sets in `inventory.py`.
