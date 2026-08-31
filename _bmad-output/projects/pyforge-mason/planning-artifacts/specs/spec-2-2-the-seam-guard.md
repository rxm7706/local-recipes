---
title: 'The seam guard'
type: 'feature'
created: '2026-08-10'
status: 'done'
baseline_revision: '39b02c36952edcfd8c02c929b10dbefedd9e918e'
review_loop_iteration: 0
followup_review_recommended: true
final_revision: '6ce2a9b26f'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Mason has no mechanical guarantee that recipe-authoring knowledge stays out of its
own codebase, or that only `cfe.py` ever names/invokes conda-forge-expert (CFE) — nothing today
would catch a second implementation of packaging judgement creeping in one helper at a time, the
exact failure `pyforge-atlas` already suffered (~29,000 LOC rebuilt alongside the still-live
8,902-LOC original).

**Approach:** Add two default-task meta-tests: `test_no_recipe_knowledge.py`, an AST-based
deny-list scanner over four cited categories (gotcha IDs, policy nouns/check-code prefixes, v1
recipe-field names, pin/constraint shapes) with a planted-violation fixture per category and a
rationale-completeness companion check; and `test_adapter_sole_caller.py`, an AST-based scanner
asserting no module but `cfe.py` references a CFE path, CFE script filename, or spawns a process
against one, honoring AD-3's two-entry carve-out.

## Boundaries & Constraints

**Always:** both tests are AST-based (walk string-constant and call/import nodes), never raw-text
regex — matches the sibling meta-tests' documented rationale (test-architecture.md: "AST-based
scanning, not regex, for every meta-test") and avoids the exact false-positive class that already
bit an early draft of `test_namespace_is_implicit.py` (a comment merely mentioning a banned name);
deny-list entries are structured records (category, compiled pattern, CFE-artifact citation,
rationale) in one module-level table inside `test_no_recipe_knowledge.py` (FR-42: "declared in one
reviewable module"), and a companion test asserts every entry's citation and rationale are
non-empty — this makes "weakening/removing an entry needs a rationale comment" a standing
invariant on present state rather than a git-diff check; v1-field-name entries are drawn only from
**distinctive** conda-forge vocabulary with no ordinary-English collision risk (e.g. `run_exports`,
`ignore_run_exports`, `run_constrained`, `pin_subpackage`, `pin_compatible`, `zip_keys`,
`noarch_platforms`, `conda_build_config`, `recipe-maintainers`, `skip_pyc_compilation`, each citing
`reference/recipe-yaml-reference.md`) — never the generic top-level keys (`package`, `source`,
`build`, `test(s)`, `about`, `extra`, `requirements`, `schema_version`, `context`, `outputs`,
`cache`), which already occur 2–28 times each in the shipped tree (`package.py`, the `build` verb,
`tests/`) and once as `render.py`'s own JSON-envelope key (`"schema_version"`) — a deny-list
including these would fail against Mason's own current code; check-code-prefix entries require the
prefix followed by digits (e.g. `\bSTD-\d{3}\b`), not a bare prefix substring — a bare `"CFE-"`
false-positives against Mason's own prose (`doctor.py`: "CFE-independent", `package.py`:
"CFE-independent", `exit_codes.py`: "CFE-dependent"); the gotcha-identifier pattern is `\bG[0-9]
{1,3}\b`, citing `SKILL.md`'s `## Recipe Authoring Gotchas` section (`### G<N>.` entries, G1–G107);
pin/constraint-shape entries match a leading comparison operator immediately before a digit (e.g.
`[<>=!]=?\d+(\.\d+)*`), citing `reference/pinning-reference.md`; the scan excludes module/class/
function **docstrings** (the first statement's string) — Mason's own modules already narrate CFE
concepts in prose by spec identifier (`cfe.py` cites AD-3/FR-4 throughout) without that being
"recipe knowledge"; AD-1 targets semantics encoded as data (a constant, a table, a default), not
commentary explaining a delegation boundary; `test_adapter_sole_caller.py`'s CFE-path detector
matches the literal substring `.claude/scripts/conda-forge-expert` inside any string constant —
NOT the bare word "conda-forge-expert" alone, which already appears legitimately in `cli.py`'s help
text ("wraps the conda-forge-expert craft") and would false-positive without the path-prefix
requirement; its two-entry allowlist is file-level: `resolve.py` (for `_CFE_MARKER`) and
`errors.py` (for `CfeUnresolvedError._MESSAGE`) only; CFE script filenames — parsed from `cfe.py`'s
own `_CFE_SCRIPTS` table via AST, never hand-duplicated — and any `subprocess.run`/`Popen`/`call`/
`check_call`/`check_output` call whose arguments reference either pattern have **no allowlist
anywhere**, including inside `resolve.py`/`errors.py`/`cli.py`; both new files run in the default
(non-`slow`) pytest task; every deny-list/detector category ships at least one `tmp_path`-based
positive fixture proving detection fires, mirroring `test_dependency_direction.py`'s/
`test_capability_tiers.py`'s existing regression-fixture style, plus one fixture proving a clean
synthetic module produces zero matches.

**Block If:** none identified — FR-42/FR-43, the epics.md AC block, and the four existing sibling
meta-tests fully specify this work's shape and style.

**Never:** build `recipe.py` or any `mason recipe` verb (Epic 2's later stories' scope); expand the
AD-3 carve-out beyond the two named entries; include a generic top-level v1 field name (`package`/
`source`/`build`/`test`/`about`/`extra`) as a literal deny-list entry; scan `tests/` or any
directory outside `src/pyforge/mason/`; modify `cfe.py`/`resolve.py`/`errors.py`'s existing logic
or add a rationale comment to their source (the carve-out's rationale lives in the new test's own
allowlist declaration, mirroring `_allowed_paths()`'s existing comment style in
`test_dependency_direction.py` — those three files are shipped, reviewed, tested code this story
does not touch); enforce the deny-list against `tests/meta/`/`tests/unit/` themselves (a test
fixture module planting a violation would otherwise trip the real-tree assertion).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Planted gotcha ID | synthetic module containing `"G41"` | flagged: category, file, line, pattern named | none |
| Planted check-code | synthetic module containing `"STD-001"` | flagged | none |
| Planted v1 field name | synthetic module containing `"run_exports"` as a dict key | flagged | none |
| Planted pin shape | synthetic module containing `">=1.0,<2.0"` | flagged | none |
| Deny-list entry missing a citation/rationale | synthetic table entry with an empty rationale | companion test fails, naming the entry | none |
| Real tree, current state | actual `src/pyforge/mason/` | both meta-tests pass (zero real violations) | none |
| CFE mention without the path prefix | `cli.py`'s help text ("...conda-forge-expert craft") | NOT flagged | none |
| `_CFE_MARKER` / guidance echo | real `resolve.py` / `errors.py` | NOT flagged (allowlisted) | none |
| CFE script filename outside `cfe.py` | synthetic module containing `"validate_recipe.py"` | flagged, no allowlist | none |
| `subprocess` call with a CFE-path/script argument outside `cfe.py` | synthetic module | flagged, no allowlist, even if the file is otherwise subprocess-allowed | none |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `tests/meta/test_no_recipe_knowledge.py` (new) -- deny-list table (category, pattern, CFE
  citation, rationale), AST scanner, real-tree assertion, rationale-completeness companion test,
  per-category planted-violation fixtures, one clean-module fixture.
- `tests/meta/test_adapter_sole_caller.py` (new) -- CFE-path/script/subprocess AST scanner honoring
  the two-entry allowlist, real-tree assertion, per-category fixtures (allowlisted-permitted +
  unallowlisted-flagged for the path category; flagged-everywhere for script/subprocess).

## Tasks & Acceptance

**Execution:**
- [x] `tests/meta/test_no_recipe_knowledge.py` (new) -- module-level deny-list table with one entry
  per category minimum (gotcha `\bG[0-9]{1,3}\b` citing `SKILL.md` § Recipe Authoring Gotchas;
  digit-suffixed check-code prefixes `ABT-/DEP-/FMT-/LIC-/MAINT-/PIN-/SCHEMA-/SCRIPT-/SEC-/SEL-/
  STD-/TEST-` citing `SKILL.md`'s Core Tools Reference table + `reference/*.md`; distinctive v1
  field names citing `reference/recipe-yaml-reference.md`; pin/constraint operator+digit shapes
  citing `reference/pinning-reference.md`); an AST walker over every `.py` file under
  `src/pyforge/mason/` collecting string constants (excluding the first-statement docstring of
  each module/class/function) and matching each against every table entry's pattern; a test
  asserting zero matches against the real tree, naming file/line/category/pattern on failure; a
  companion test asserting every table entry's citation and rationale fields are non-empty; one
  `tmp_path` fixture per category proving the scanner fires on a planted violation, plus one
  proving a clean synthetic module produces zero matches -- FR-42, AD-1.
- [x] `tests/meta/test_adapter_sole_caller.py` (new) -- an AST walker over every `.py` file under
  `src/pyforge/mason/` except `cfe.py`, flagging: (a) a string constant containing
  `.claude/scripts/conda-forge-expert`, allowlisted only for `resolve.py` and `errors.py`; (b) a
  string constant equal to any value in `cfe.py`'s own `_CFE_SCRIPTS` table (parsed from `cfe.py`'s
  AST, not hand-duplicated), no allowlist; (c) a `subprocess.run`/`Popen`/`call`/`check_call`/
  `check_output` call whose argument list contains a string matching (a) or (b), no allowlist even
  inside an otherwise-allowlisted file; a test asserting zero unallowlisted matches against the
  real tree, naming file/line/category; fixtures: a real-marker planted outside the allowlist
  (flagged), the real marker as it exists in `resolve.py`/`errors.py` today (permitted), a script
  filename planted in a synthetic non-`cfe.py` module (flagged), a `subprocess` call carrying a CFE
  argument planted in a synthetic module (flagged) -- FR-43, AD-3.

**Acceptance Criteria:**
- Given `tests/meta/test_no_recipe_knowledge.py`, when it scans `src/pyforge/mason/`, then it fails
  on any module containing a gotcha identifier, policy noun/check-code, v1 field name, or
  pin/constraint shape from the deny-list, naming the file, line, and matched pattern.
- Given the deny-list, when it is authored, then it enumerates at minimum the four FR-42 categories,
  each entry citing the CFE artifact it derives from, in one reviewable module-level table.
- Given the deny-list's own correctness, when the test suite runs, then a synthetic positive
  fixture exists for every category and each is detected — a deny-list matching nothing is
  therefore a failing test, not a passing one.
- Given a deny-list entry lacking a rationale or citation, when the companion test runs, then it
  fails, naming the entry.
- Given `tests/meta/test_adapter_sole_caller.py`, when it scans `src/pyforge/mason/`, then it fails
  if any module other than `cfe.py` references a CFE path, CFE script filename, or spawns a process
  against one, except the two AD-3-carved-out entries (`resolve.py`'s `_CFE_MARKER`, `errors.py`'s
  guidance echo).
- Given both tests, when the default (non-`slow`) pytest task runs, then both execute and both are
  green.
- Given this story completes, when a subsequent Epic 2–5 story adds code, then these two guards run
  against it automatically, with no per-story registration step.

## Spec Change Log

## Review Triage Log

### 2026-08-10 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high: 1, medium: 4, low: 2)
- defer: 4 (high: 1, medium: 1, low: 2)
- reject: 5
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter found the deny-list scanner only inspected string-constant
    *values*, missing identifier *positions* entirely — `def build(*, run_exports=None): ...`
    sailed through undetected even though it is exactly the "second implementation of packaging
    judgement" pattern AD-1 exists to catch. Extended `test_no_recipe_knowledge.py` with
    `_collect_identifier_targets` (function/lambda parameter names, assignment/annotated-assignment
    targets), applied to the gotcha and v1-field categories only (check-code/pin-shape patterns use
    characters no Python identifier can contain), reusing the already-collision-vetted pattern set.
    3 new regression fixtures.
  - `[medium]` `[patch]` Both Blind Hunter and Edge Case Hunter independently found
    `test_adapter_sole_caller.py`'s two-entry allowlist matched by bare `Path.name`, not a qualified
    path — a future same-named file anywhere else in the tree (e.g. `engines/resolve.py`) would
    silently inherit the carve-out. Confirmed against `test_dependency_direction.py`'s own
    already-documented "full resolved paths, not bare filenames" fix for the identical footgun.
    Switched to resolved-path comparison against `root / "resolve.py"` / `root / "errors.py"`
    specifically; added a regression fixture proving a nested same-named file is still flagged.
  - `[medium]` `[patch]` Blind Hunter found the subprocess-spawn detector recognized only five
    `subprocess`-module call names, missing `os.system`/`os.spawn*`/`os.posix_spawn`/
    `asyncio.create_subprocess_*` — none of which `import subprocess`, so none were caught by
    AD-2's existing subprocess-import guard either, a genuine unguarded evasion route. Expanded
    `_SUBPROCESS_CALL_NAMES`; added a regression fixture for `os.system`.
  - `[medium]` `[patch]` Edge Case Hunter found `_parse_cfe_script_filenames` silently dropped a
    `_CFE_SCRIPTS` value that wasn't a literal string constant, and silently used only the
    first-found table if more than one existed — either would make the allowlist source quietly
    wrong with no failure signal. Now raises `AssertionError` naming the file for both cases; 2
    new regression fixtures.
  - `[medium]` `[patch]` Edge Case Hunter found the module/class/function-docstring exemption in
    `test_no_recipe_knowledge.py` didn't cover a bare string statement immediately following a
    module/class-level assignment (the PEP 257-adjacent "attribute docstring" convention this same
    file already uses for `_V1_FIELD_NAMES`) — the file's own writing style could have
    false-positived on itself. Added `_trailing_attribute_docstring_ids`; 2 new regression fixtures
    (positive exemption + a negative control proving the adjacency requirement is real).
  - `[low]` `[patch]` Edge Case Hunter found a `bytes` literal (`b"G41"`) evades both scanners'
    `str`-only constant check. Added `_constant_text_value` (decodes `bytes`,
    `errors="replace"`) to both files; 2 new regression fixtures.
  - `[low]` `[patch]` Edge Case Hunter found the pin-shape pattern requires the comparison operator
    immediately adjacent to the digit, missing the whitespace-tolerant form (`">= 1.0"`). Added
    `\s*` between operator and digit; 1 new regression fixture.
- **Deferred (4, logged to `deferred-work.md`):** `[high]` string-concatenation/f-string/indirect-
  dispatch evasion of both scanners (Blind Hunter + Edge Case Hunter, several sub-findings) —
  closing this needs dataflow/taint analysis, a redesign of the detection methodology rather than a
  patch; notably Story 2.1's own AD-4 guard explicitly punted this class to "Story 2.2's dedicated,
  more thorough seam-guard methodology," so this story narrows but does not close that gap.
  `[medium]` subprocess-spawn detection remains name-based with no import-origin/receiver
  resolution (residual false-positive/negative surface) (Blind Hunter). `[low]` check-code-prefix
  and gotcha-identifier patterns are inherently indistinguishable from unrelated ticket-ID/domain-
  term conventions Mason doesn't currently use (Blind Hunter, two findings merged — zero current
  occurrences, no better mechanical fix). `[low]` pin-shape pattern matches a lone
  operator+digit with no paired-bounds context (Blind Hunter — zero current false positives; a
  precise fix risks missing valid single-bound pins like `"==1.2.3"`).
- **Rejected (5):** duplication between the two test files' file-reading/parsing helpers (Blind
  Hunter) — a shared `utils`/`helpers` module is explicitly forbidden by this codebase's own
  Consistency Conventions (cited repeatedly in `cfe.py`'s docstring: "the Consistency Conventions
  forbid a shared utils/helpers module"); the duplication is the accepted, intentional pattern, not
  a defect. `test_parse_cfe_script_filenames_reads_the_real_cfe_py` hardcoding the current
  `_CFE_SCRIPTS` value set, needing an update when Stories 2.4-2.10 add scripts (Blind Hunter) —
  working as designed; pytest's own set-equality failure output already shows the exact diff, and
  updating this one assertion is routine, expected maintenance alongside adding the new adapter
  itself. The real-tree assertion passing vacuously if `PKG_ROOT` somehow contained zero `.py`
  files (Edge Case Hunter) — matches the identical, already-accepted rigor level of all four
  existing sibling meta-test files (none of them count files scanned either); not a regression
  introduced by this story. The `recipe-maintainers` v1-field pattern also matching inside
  `recipe-maintainers-emeritus` (Blind Hunter) — both are genuine v1 schema fields; only the
  diagnostic label of which literal matched is imprecise, not detection correctness — cosmetic.
  The rationale-completeness companion test checking only non-emptiness, not semantic substance
  (Blind Hunter) — no mechanical fix exists for judging rationale quality; this is gated by human
  code review at merge time, the same way every other "rationale comment" convention in this
  codebase already is.

### 2026-08-10 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 10 (high: 1, medium: 5, low: 4)
- defer: 2 (low: 2)
- reject: 9
- addressed_findings:
  - `[high]` `[patch]` Both hunters independently found the AD-3 guard blind to the exact
    path idiom `cfe.py` itself uses: `cfe.py:730` spells the CFE path as
    `root / ".claude" / "scripts" / "conda-forge-expert" / _CFE_SCRIPTS[key]`, so no single
    string constant holds `_CFE_PATH_SUBSTRING` and the script name is a subscript. Verified:
    that line plus its `subprocess.run(...)` copied verbatim into a synthetic `doctor.py`
    scanned completely clean — a second module could have reimplemented Mason's whole CFE
    invocation and the one guard whose job is to prevent that reported the tree green. Added
    `_joined_segment_text`/`_segment_text`/`_outermost_join_nodes`: assembles `/`-operator
    chains and `os.path.join(...)` calls (descending into wrapping calls like `Path(".claude")`)
    into a path and matches the full substring, reported under the existing `cfe-path` category
    and allowlist. 4 new fixtures (pathlib chain, `os.path.join`, allowlist-honouring +
    nested-file control, clean-path control).
  - `[medium]` `[patch]` Edge Case Hunter found the subprocess-argument detector matched script
    filenames by equality, so a shell one-liner — `os.system("python validate_recipe.py --json")`,
    one argument containing the name — was never flagged. Switched category (c) to containment
    (category (b) stays exact-equality over standalone constants, per spec); verified no non-`cfe.py`
    module names either script today, so containment adds no false positives. 1 new fixture.
  - `[medium]` `[patch]` Both hunters found the two-entry allowlist unguarded: Blind Hunter
    replaced it with four entries — including a live `doctor.py` and a nonexistent `gone.py` — and
    the suite stayed green, making "add a third entry" the cheapest way to defeat AD-3. Added
    `test_cfe_path_allowlist_is_exactly_ad3s_two_live_carve_outs`, pinning membership and proving
    each carve-out is still live (file exists and still holds a CFE path), so a dead exemption
    fails instead of silently covering whatever that file grows next.
  - `[medium]` `[patch]` Both hunters found the identifier scan still covered only parameters and
    bare `Name` assignment targets — `self.run_exports = [...]` (a model class, the most plausible
    real shape), `def run_exports()`, `class run_exports`, `build(run_exports=...)`, and
    `for`/`with`/walrus targets all invisible. Extended `_collect_identifier_targets` with a
    recursive `_bound_names_in_target` (Name/Attribute/Tuple/List/Starred) plus def/class names,
    `AugAssign`, `For`/`AsyncFor`, `NamedExpr`, `withitem`, and call-site `keyword.arg`. 3 new
    fixtures; verified zero real-tree occurrences of any denied name in these positions first.
  - `[medium]` `[patch]` Both hunters found the deny list could be gutted with the suite green —
    `test_deny_list_covers_all_four_fr42_categories` asserts category *presence*, not entry
    coverage, so 9 of 10 v1 field names could be deleted silently (reproduced by mutation).
    Added `_REQUIRED_V1_FIELD_NAMES`, spelled out independently of `_V1_FIELD_NAMES` (deriving it
    would delete itself along with the dropped entry) plus
    `test_deny_list_covers_the_required_v1_field_names`. Verified: gutting to one entry now names
    the other nine.
  - `[medium]` `[patch]` Both hunters found the pin-shape pattern false-positives on this
    codebase's own house notation: `->` is the resolution-chain arrow in every `cli.py` precedence
    help string, and `(?:…|>)\s*\d` reads `-> 300` as the pin `"> 3"`. Green today only by luck —
    every arrow in the tree happens to be followed by a letter or `{`. Added a `(?<!-)` lookbehind,
    which cannot mask a real pin (no pin spells its operator that way). 2 new fixtures (arrow
    exempt, real `>=3.9` still flagged).
  - `[low]` `[patch]` Edge Case Hunter found `\bG[0-9]{1,3}\b` never fires beside `_` (a word
    character), so `G41_WORKAROUND = True` and `def apply_G41_patch()` — precisely the
    identifier-shaped gotcha knowledge the identifier scan exists to catch — passed the very
    pattern meant to catch them. Switched to explicit alphanumeric lookaround. 1 new fixture.
  - `[low]` `[patch]` Edge Case Hunter found a UTF-8 BOM makes both guards abort with "invalid
    Python syntax" against a perfectly runnable module (`read_text(encoding="utf-8")` leaves the
    BOM for `ast.parse`). Switched both files to `utf-8-sig`, matching `test_no_config_file.py`'s
    existing in-suite choice. 2 new fixtures.
  - `[low]` `[patch]` Blind Hunter found `_CFE_PATH_SUBSTRING` is POSIX-only, so a
    backslash-spelled literal of the identical path walks through. Added `_names_a_cfe_path`,
    normalizing separators before matching. 1 new fixture.
  - `[low]` `[patch]` Blind Hunter found the module docstring's empirical justification for
    excluding a bare `=` factually stale: it claims `cfe.py`'s `_SUBMIT_PR_TIMEOUT_SECONDS`
    trailing string "is not a docstring and so is not excluded", but the trailing-attribute-
    docstring exemption added in the previous pass does exempt it (verified at `cfe.py:763-766`).
    Rewrote the paragraph to state the current fact and the reason the operator restriction still
    carries its own weight, so the next maintainer does not reason from a false premise.
- **Deferred (2, logged to `deferred-work.md` as new entries):** `[low]` every meta-guard globs
  `*.py` only, so `.pyi` stubs and symlinked package subdirectories are outside all six guards'
  coverage (both hunters; pre-existing — the four siblings share the boundary exactly — and inert:
  the tree has neither today). `[low]` the four sibling meta-guards still read with plain `utf-8`,
  so the BOM defect patched here survives in 8 other call sites (Edge Case Hunter; pre-existing,
  out of this story's two-file Code Map, one-word fix each).
- **Rejected (9):** helper duplication across the two new files, with a 3rd/4th copy in
  `test_dependency_direction.py` and `tests/conftest.py` available (Blind Hunter) — re-verified
  rather than inherited: `cfe.py:30/59` do state the Consistency Conventions forbid a shared
  `utils`/`helpers` module, and `conftest.py` holds fixtures, not parsing helpers; the duplication
  is the codebase's intentional pattern, and refactoring four files is outside this story's Code
  Map. `test_parse_cfe_script_filenames_reads_the_real_cfe_py` hardcoding the current
  `_CFE_SCRIPTS` values (Blind Hunter) — previously rejected as working-as-designed; premise
  re-checked and still true. The AD-1 real-tree assertion passing vacuously if `PKG_ROOT` held
  zero `.py` files (both hunters) — previously rejected on sibling-rigor grounds; re-checked
  (`test_render_ownership.py:117`, `test_no_config_file.py:147`, `test_exit_code_ownership.py:121`
  all guard with `is_dir()` alone and carry the identical comment), so the rejection is scope-based
  and inherited rather than re-litigated. Name-based subprocess-call matching with no receiver
  resolution, and concatenation/f-string/indirect-dispatch evasion (both hunters) — already logged
  as deferred entries by the previous pass; not duplicated. `.pyi`-vs-`*.py` framed as this story's
  defect (deferred instead, see above). `_CFE_SCRIPTS` extended post-literal via `.update()`/`|=`
  (Edge Case Hunter) — speculative; the table is a literal and a restructure already fails loudly.
  The trailing-attribute-docstring exemption being broader than PEP 257 (Blind Hunter) — real, but
  it grants no power the already-accepted docstring exemption does not, so tightening it closes
  nothing. Check codes with other than three digits, and deny-list content gaps (`python_min`,
  `script_env`, `entry_points`) (both hunters) — the shipped patterns and field set are exactly
  what the spec enumerated; `entry_points` in particular is ordinary Python-packaging vocabulary
  the deny list deliberately avoids, and widening the table is a curation judgement for human
  review, not a review-pass patch. One literal reported under two categories when a CFE path sits
  inside a subprocess call (both hunters) — both rules genuinely are violated; the doubled line is
  accurate reporting, not an inflated count.

### 2026-08-10 — Review pass (follow-up 2)
- intent_gap: 0
- bad_spec: 0
- patch: 13 (high: 1, medium: 8, low: 4)
- defer: 2 (low: 2)
- reject: 8
- addressed_findings:
  - `[high]` `[patch]` Both hunters independently found the segment-join detector blind to
    list/tuple/starred arguments and to `.joinpath(...)`: `_segment_text` descended into a
    wrapping call's positional args but never into `ast.List`/`ast.Tuple`/`ast.Starred`, and
    `_is_join_call` matched only the bare name `join`. Reproduced: a generic
    `run_any_cfe_script(root, script, args)` passthrough built on
    `"/".join([".claude", "scripts", "conda-forge-expert"])` — the whole of what AD-3 forbids,
    with the script name caller-supplied so category (b) cannot backstop it — scanned completely
    clean, as did `os.sep.join([...])`, `os.path.join(*(...))` and
    `Path(...).joinpath(...)`. Extended `_segment_text` (list/tuple elements, starred values) and
    `_is_join_call` (`joinpath`, whose RECEIVER also carries the leading segment, unlike `join`'s);
    3 new fixtures.
  - `[medium]` `[patch]` Blind Hunter found `_is_join_call`'s own docstring asserted that hole was
    impossible ("`", ".join(parts)` passes no string constants as *arguments*, so it assembles to
    nothing and cannot be reported") — true for `join(parts)`, false for the literal-list form that
    was the actual evasion. Rewrote the paragraph so the next auditor is not told the gap cannot
    exist.
  - `[medium]` `[patch]` Both hunters found the spawn-name table missing
    `subprocess.getoutput`/`getstatusoutput` and the whole `os.exec*` family (plus
    `os.startfile`) — the same single-shell-string shape that motivated the previous pass's
    containment rule, and reproduced clean: `subprocess.getoutput("python validate_recipe.py
    --json")` and `os.execl("/bin/sh", "sh", "-c", "python validate_recipe.py")` both went
    undetected. Expanded `_SUBPROCESS_CALL_NAMES` to 30 names.
  - `[medium]` `[patch]` Blind Hunter found `_SUBPROCESS_CALL_NAMES` narrowable from nineteen names
    to two with the whole suite green (only `run`, bare `run` and `system` had fixtures), making a
    one-line deletion the cheapest way to reopen AD-3's spawn seam. Added
    `_REQUIRED_SPAWN_CALL_NAMES` (spelled out independently, so it cannot delete itself alongside
    the dropped name), a floor test, and a parametrized detection fixture per name. Verified:
    gutting the live set to one name now reds 30 tests.
  - `[medium]` `[patch]` Blind Hunter found the previous pass's coverage floor closed entry
    *deletion* but not entry *neutering* — replacing seven of ten v1 patterns with a never-matching
    regex left the suite green, since `test_deny_list_covers_the_required_v1_field_names` asserts
    on `entry.name`. The same held for eleven of the twelve check-code prefixes, which live in one
    alternation. Added parametrized "is actually detected" fixtures over both required sets, plus
    `_REQUIRED_CHECK_CODE_PREFIXES` + its floor test. Verified by mutation: both edits now red.
  - `[medium]` `[patch]` Both hunters found the allowlist-liveness assertion was a **raw-text**
    scan (`_names_a_cfe_path(_read_source(path))`), contradicting this file's own fixture blessing
    `_CFE_MARKER = Path('.claude') / 'scripts' / 'conda-forge-expert'` as a legitimate `resolve.py`
    shape — the moment a carve-out adopted the segment form the guard would report its still-live
    exemption dead, and the obvious repair to that failure is deleting a live carve-out. Switched
    the check to the AST scanner with the allowlist bypassed.
  - `[medium]` `[patch]` Edge Case Hunter found category (c)'s "no allowlist anywhere" guarantee
    false for the segment form: (a)'s join scan is skipped wholesale inside an allowlisted file, so
    `resolve.py` could assemble the CFE path inside a `subprocess.run(...)` and spawn it — script
    name from a variable, so (b) never fires either — with the tree reported clean. The spawn
    detector now reads assembled path text from its own argument subtree
    (`_joined_path_texts_in`), independent of (a)'s suppression; 1 new fixture.
  - `[medium]` `[patch]` Edge Case Hunter found the v1-field patterns still used `\b`, the exact
    defect the gotcha entry was already fixed for: `_` is a word character, so the private spelling
    `self._run_exports = []` / `def build(*, _run_exports=None)` walked through. Switched to an
    asymmetric boundary — a leading `_` is part of the name, a trailing one still a boundary, so
    `run_exports_list` stays unflagged and its regression fixture still holds. Verified zero
    real-tree hits first.
  - `[medium]` `[patch]` Both hunters found the identifier scan covered binding positions only, so
    the docstring's "every place a denied name can be bound or passed" was false: attribute
    **reads** (`return spec.run_exports` — the read side of the very field whose write side was
    already covered), `import`/`from … import` names and aliases, comprehension targets,
    `except … as`, `global`/`nonlocal`, and `match` captures were all invisible. Extended
    `_collect_identifier_targets` across all of them (deduplicated on `(lineno, name)`) after
    verifying the widened scan produces zero real-tree hits; 3 new fixtures.
  - `[low]` `[patch]` Edge Case Hunter found a segment carrying its own trailing separator
    (`Path(".claude/") / "scripts" / …`) assembles to `.claude//scripts/…` and missed the raw
    substring test. `_names_a_cfe_path` now collapses repeated separators as well as normalizing
    backslashes; 1 new fixture.
  - `[low]` `[patch]` Edge Case Hunter found `_segment_text`'s docstring claim — that joining
    across a skipped segment "cannot manufacture that 41-character path" — factually false
    (`base / ".claude" / plugin / "scripts" / "conda-forge-expert"` assembles to exactly it).
    Corrected the claim rather than substituting a placeholder: over-detection is the safer
    direction for this guard, and a placeholder would have opened a fresh evasion
    (`root / ".claude" / SCRIPTS_DIRNAME / "conda-forge-expert"`).
  - `[low]` `[patch]` Blind Hunter found `_outermost_join_nodes` collected only a `/` chain's LEFT
    operand as nested, so a right-nested chain or a join call nested inside another reported the
    same path build twice, despite the docstring claiming otherwise. Replaced with
    `_segment_child_nodes`, covering both operands and every join argument.
  - `[low]` `[patch]` Both hunters found the pin-shape pattern collides with ordinary numeric prose
    (`"--timeout must be > 0"`, `"expected exit code != 0"` both reproduce), and that Mason — a CLI
    with three numeric-flag validators and an interpreter-floor probe — is green today by wording,
    not by construction. The pattern change itself stays deferred (already a ledger entry; a
    precise fix risks missing single-bound pins like `"==1.2.3"`), but the docstring now states the
    concrete collision instead of only the abstract one, and the real-tree failure message names
    the correct repair — reword the message, do not weaken the pattern — so the failure does not
    steer the next maintainer into gutting the guard.
- **Deferred (2, logged to `deferred-work.md` as new entries):** `[low]` the CFE-path substring
  match has no trailing boundary, so a sibling path sharing the prefix
  (`.claude/scripts/conda-forge-expert-notes.md`) is reported as a CFE-wrapper reference (Blind
  Hunter; zero current occurrences, and the over-detection is arguably correct — narrowing it is a
  deliberate decision about AD-3's path category, not a patch). `[low]` all six meta-guards decode
  source themselves before `ast.parse`, so a PEP 263 coding-cookie module would be reported
  undecodable against a file CPython imports fine (Edge Case Hunter; inert, and distinct from the
  already-logged BOM entry in that it changes the read path and both clean-failure contracts).
- **Rejected (8):** helper duplication across the two new files, with `tests/meta/_scan.py`
  proposed to unify all six guards (Blind Hunter) — rejected twice before; premise re-verified
  rather than inherited (`cfe.py:30/59` do state the Consistency Conventions forbid a shared
  `utils`/`helpers` module), and refactoring four untouched files is outside this story's Code Map.
  The four siblings' `utf-8`-vs-`utf-8-sig` divergence (Blind Hunter) — already a deferred ledger
  entry from the previous pass; not duplicated.
  `test_parse_cfe_script_filenames_reads_the_real_cfe_py` hardcoding the current `_CFE_SCRIPTS`
  values (Blind Hunter, third time) — premise re-checked and still true: `_parse_cfe_script_filenames`
  already fails loudly on a rename or restructure, and pytest's set-diff output names the exact
  addition, so updating one assertion alongside adding an adapter is expected maintenance.
  Gotcha-pattern collisions with `-G3`/`BUILD_G2` (Edge Case Hunter) — already a deferred ledger
  entry covering exactly this class; not duplicated. A directory literally named `*.py` under the
  scan root surfacing as "unreadable" (Edge Case Hunter) — speculative, and the outcome is already
  a clean named assertion rather than a traceback. The attribute-docstring exemption not applying
  inside function bodies (Edge Case Hunter) — speculative, and widening an exemption only ever
  weakens the guard. `.pyi` stubs / symlinked subdirectories outside the `*.py` glob, and
  name-based spawn matching with no receiver resolution plus concatenation/f-string/indirect-
  dispatch evasion (both hunters) — all already deferred ledger entries whose wording the module
  docstrings still state accurately.

### 2026-08-10 — Review pass (follow-up 3)
- intent_gap: 0
- bad_spec: 0
- patch: 13 (high: 1, medium: 6, low: 6)
- defer: 2 (medium: 1, low: 1)
- reject: 8
- addressed_findings:
  - `[high]` `[patch]` Edge Case Hunter found the CFE-path detector blind to the multi-argument
    `pathlib` constructor — `Path(root, ".claude", "scripts", "conda-forge-expert", name)` is
    exactly `Path(root) / ".claude" / ...` and is the more idiomatic spelling, yet matched neither
    the `/`-operator form nor the `join`/`joinpath` names added by the previous two passes.
    Reproduced: that build plus its `subprocess.run(["python", str(script)])` — a verbatim
    reimplementation of `cfe.py`'s invocation with the script name caller-supplied, so category (b)
    cannot backstop it — scanned completely clean. Added `_PATH_CONSTRUCTOR_NAMES` and taught
    `_is_join_call` the multi-arg constructor form (single-arg `Path("x")` stays a wrapper, not a
    join). 2 new fixtures (detection + a negative control proving `Path(".claude") /
    "settings.json"` stays clean).
  - `[medium]` `[patch]` Both hunters found `_names_a_cfe_path` case-SENSITIVE while this file's
    own docstring already claimed "neither a Windows spelling ... is a hole" — but macOS and
    Windows filesystems are case-insensitive, so `".Claude\Scripts\conda-forge-expert"` names the
    real CFE directory and scanned clean. Edge Case Hunter added the `.` -component spelling
    (`".claude/./scripts/..."`), likewise clean. Extracted `_normalized_path_text` (separators,
    doubled separators, `.` components, case) and rewrote the docstring paragraph that asserted the
    coverage it did not have. 2 new fixtures.
  - `[medium]` `[patch]` Blind Hunter found — and Edge Case Hunter independently confirmed — that
    category (c)'s spawn-name list omitted `pty.spawn`, `runpy.run_path`/`run_module` and
    `multiprocessing.Process`, and that this is only a real hole INSIDE an allowlisted file, where
    category (a) is suppressed wholesale and category (c) is the sole remaining guard. Reproduced:
    all three launched a CFE script from `resolve.py` with the tree reported clean. Added them plus
    `asyncio`'s `subprocess_exec`/`subprocess_shell` to both `_SUBPROCESS_CALL_NAMES` and its
    independent floor (so the parametrized per-name fixture covers each), and replaced the
    docstring's implied-completeness wording with an explicit statement that the list is a name
    list, not a proof. 1 new fixture asserting both launchers fire, by line.
  - `[medium]` `[patch]` Both hunters found category (b)'s exact-equality rule defeated by a
    one-line hoist: `_CMD = "python validate_recipe.py --json"` at module level, then
    `os.system(_CMD)`, scanned clean — category (c) reads only the call's own argument subtree, and
    the longer string equals no table value. Blind Hunter found the same rule let a COMPLETE script
    path sit permanently inside an allowlisted file (`resolve.py`: `VALIDATE =
    ".claude/scripts/conda-forge-expert/validate_recipe.py"`), the one artifact AD-3 says only
    `cfe.py` may hold. Switched (b) to containment, aligning it with (c)'s already-containment rule;
    verified zero non-`cfe.py` occurrences of either script name in the real tree first, and naming
    a CFE script in Mason prose is itself what FR-43 forbids, so the widening trades against no
    false-positive class. Deviation from the Tasks line's "equal to" wording, recorded here. 2 new
    fixtures.
  - `[medium]` `[patch]` Blind Hunter found the pin-shape pattern reports ordinary Python format
    specs as conda-forge pins: `f"{name:<30}{count:>8}"` yields two violations, `"{:>6} {:<20}"`
    one. Not hypothetical — Mason's `render.py` exists to emit tables, and sibling packages already
    use `:<20`/`:<8` alignment in the same kind of CLI code; worse, the real-tree failure message
    tells the next maintainer to "reword the message -- do not weaken the pattern", advice that is
    impossible to follow for a format spec, so the predictable outcome was the pattern-gutting the
    message exists to prevent. Added `_format_spec_string_ids` (exempting f-string format specs from
    the PIN_SHAPE category only, deliberately not wholesale) plus a `:` lookbehind for the
    `.format()`-template spelling. 2 new fixtures (both spellings clean; a pin in an f-string's
    ordinary literal part still flagged).
  - `[medium]` `[patch]` Edge Case Hunter found PEP 695 syntax invisible to the identifier scan
    while the docstring claimed "every place a denied name can be bound": `type run_exports =
    list[str]` and `def build[pin_subpackage](x)` both scanned clean, and both are live syntax at
    this package's Python >=3.12 floor. Added `ast.TypeAlias`/`TypeVar`/`ParamSpec`/`TypeVarTuple`
    to `_collect_identifier_targets`. 1 new fixture covering both forms, by line.
  - `[medium]` `[patch]` Blind Hunter found the same "or read" claim false for bare names: only
    attribute reads were collected, so `from .helpers import *` followed by `return run_exports`
    was invisible. Added every `ast.Name` in any context (deduplication already handles the overlap
    with binding positions); verified zero real-tree hits across all 13 modules first. 1 new
    fixture.
  - `[low]` `[patch]` Blind Hunter found `\s*` between operator and digit also spans newlines, so
    an argparse epilog whose usage line ends `<recipe>` and whose next-but-one line starts `3 exit
    codes` reported the pin `">\n\n3"`. Narrowed to `[^\S\n]*`, which carries the docstring's
    stated intent (tolerate one space). 1 new fixture.
  - `[low]` `[patch]` Edge Case Hunter found the previous pass's `-` lookbehind cleared `->` but
    not `=>`, the same arrow one character different. Folded `=` into the lookbehind. 1 new fixture.
  - `[low]` `[patch]` Blind Hunter found the deny list case-sensitive, so `"RUN_EXPORTS"` — the
    module-constant spelling, i.e. precisely the "recipe semantics encoded as data" shape AD-1
    targets — and `"std-001"` both scanned clean. Made the v1-field and check-code patterns
    `IGNORECASE` after verifying zero real-tree hits under any casing; the gotcha pattern
    deliberately stays case-sensitive (a folded `G[0-9]{1,3}` collides with ordinary short
    identifiers like `g1`). 2 new fixtures.
  - `[low]` `[patch]` Blind Hunter found the AD-1 real-tree assertion passes vacuously on a package
    root that exists but holds no modules — previously rejected twice on sibling-parity grounds, but
    re-examined because he raised a new fact: this story's OWN sibling guard already fails loudly
    when its source parses to nothing, so the two files this story ships were internally
    inconsistent. Added the modules-scanned assertion (1 line).
  - `[low]` `[patch]` Blind Hunter found the AD-3 docstring's residual-limitations list factually
    wrong about f-strings: it claims an f-string-assembled path evades "every detector in this
    file", but the literal parts are ordinary `ast.Constant` children and ARE reported (verified).
    A maintainer trusting the note would read that red as a false positive and exempt it. Corrected
    the paragraph.
  - `[low]` `[patch]` Blind Hunter found `_joined_segment_text` returning `""` rather than `None`
    for an expression carrying no literal segment, contradicting its own documented contract and
    collecting every ordinary arithmetic `total / count` in the tree as a "path build". Fixed both
    return paths; 1 new fixture.
- **Deferred (2, logged to `deferred-work.md` as new entries):** `[medium]` AD-3's category-(a)
  carve-out is file-LEVEL by spec, so an allowlisted file may build any CFE path — not only the
  constant it was exempted for — and hand it to a caller; reproduced after this pass's fixes
  (`resolve.py` → `launch(root / '.claude' / ... / name)`, and the two-module split where
  `resolve.py` returns the path and `engines.py` spawns it), with the identical shape still flagged
  in a non-allowlisted file, so the exemption rather than the detector is what admits it. Narrowing
  it deviates from the spec's explicit "file-level" wording and risks a false red on `errors.py`'s
  user-facing prose. `[low]` the three anti-mutation floor tables are hand-mirrored copies asserted
  only in the `required ⊆ live` direction, so every entry added to a live table arrives with no
  detection fixture — demonstrated by this very pass, where four added spawn names needed the floor
  edited by hand in the same diff and nothing mechanical would have caught the omission.
- **Rejected (8):** helper duplication across the two new files, now with `tests/meta/_astscan.py`
  proposed to unify all six guards (Blind Hunter, fourth time) — premise re-verified rather than
  inherited (`cfe.py:30/59` do state the Consistency Conventions forbid a shared `utils`/`helpers`
  module), and refactoring four untouched files is outside this story's Code Map. The three floor
  tables' hand-mirrored duplication framed as a defect in itself (Blind Hunter) — deferred instead,
  see above; the duplication is load-bearing (a derived floor deletes itself alongside a dropped
  entry). One occurrence reported under two categories, and `ignore_run_exports` matching both its
  own entry and `run_exports` (Blind Hunter, third time) — both rules genuinely are violated and
  both are genuine v1 fields; the doubled line is accurate reporting. The module docstrings having
  grown into review-history changelogs (Blind Hunter) — the specific stale claims he identified
  were patched above, but a wholesale rewrite would discard the empirical justifications that are
  the only thing stopping the next maintainer from weakening a guard when it reds, which is the
  failure mode this file has now hit twice. The trailing-attribute-docstring exemption not applying
  inside function bodies (Edge Case Hunter, second time) — premise re-checked and still true, but
  widening an exemption only ever weakens the guard, and the construct is rare enough that a loud,
  named red is the better outcome. `cfe.py` as a symlink causing its target to escape the scan
  (Edge Case Hunter) — a target inside the scan root is still globbed and scanned; only a target
  outside the root escapes, which is the already-logged symlinked-subdirectory ledger entry.
  `_SUBPROCESS_CALL_NAMES` being name-based with no receiver/import-origin resolution, and
  concatenation/intermediate-variable/indirect-dispatch evasion (both hunters) — already deferred
  ledger entries; not duplicated, though the docstring wording was corrected above where it
  overstated coverage.

## Design Notes

Field-name and check-code false-positive avoidance is the load-bearing design decision here: a
literal scan of the shipped `src/pyforge/mason/` tree shows `package`/`source`/`build`/`test(s)`/
`about` already occur 2–28 times each (`package.py`, the `build` verb, `tests/`), and `render.py`
already legitimately uses the JSON-envelope key `"schema_version"`. A naive full-v1-schema
deny-list would therefore fail against the CURRENT codebase on day one, making the guard
self-defeating. The safe subset is conda-forge's distinctive nested/compound field names, verified
to have zero present occurrences (`run_exports`, `ignore_run_exports`, `pin_subpackage`,
`noarch_platforms`, etc.).

Docstrings are excluded from the scan for the identical reason: `cfe.py`'s own docstrings already
narrate CFE/architecture concepts extensively by spec identifier (AD-3, FR-4) without that
constituting recipe knowledge. A future story's docstring explaining "this mirrors CFE's `G<N>`
gotcha" would otherwise be indistinguishable from a real violation. AD-1's actual target is recipe
semantics encoded as data a use-case could act on — a constant, a table, a default — not prose that
documents a delegation boundary.

`test_adapter_sole_caller.py` derives CFE script filenames from `cfe.py`'s own `_CFE_SCRIPTS` table
via AST rather than a second hand-maintained literal list, so the two tables cannot silently drift
apart as Stories 2.4–2.10 add entries to `_CFE_SCRIPTS`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done (third review pass; no code re-derivation -- 0 intent_gap, 0 bad_spec).

**Implemented change.** Follow-up adversarial review of the two seam-guard meta-tests. Both
reviewers ran blind and in parallel; every finding below was reproduced by loading the scanners
against synthetic trees before being patched, and every widening was verified against the real
13-module tree first (zero hits) so no fix buys detection with a false red.

**Files changed**
- `src/shared/packages/pyforge-mason/tests/meta/test_adapter_sole_caller.py` -- multi-argument
  `pathlib` constructor recognized as a path join; `_normalized_path_text` extracted (case + `.`
  components added to the existing separator folding); `pty`/`runpy`/`multiprocessing`/`asyncio`
  launchers added to both spawn tables; category (b) switched from equality to containment;
  `_joined_segment_text` honours its documented `None` contract; three overstated docstring claims
  corrected. 8 new fixtures.
- `src/shared/packages/pyforge-mason/tests/meta/test_no_recipe_knowledge.py` -- f-string format
  specs exempted from the pin-shape category plus a `:` lookbehind; operator/digit gap no longer
  spans newlines; `=>` cleared alongside `->`; PEP 695 aliases/type parameters and bare `Name`
  reads added to the identifier scan; v1-field and check-code patterns case-folded; empty-package
  vacuity closed. 8 new fixtures.

**Findings breakdown.** 13 patched (1 high, 6 medium, 6 low), 2 deferred (1 medium, 1 low), 8
rejected, 0 intent_gap, 0 bad_spec. Full detail in the third Review Triage Log entry above.

**Verification.** `pixi run -e pyforge-mason pyforge-mason-test` -> 559 passed (537 before this
pass). Mutation re-probe: all 11 reproduced evasions now fire, all 4 reproduced false positives are
clean, both real-pin controls still flagged. `ruff check` unchanged (same 3 pre-existing findings).

**Residual risks.** Both deferred entries are live: an allowlisted file may still build any CFE
path and hand it to a caller (the carve-out is file-level by spec), and the three anti-mutation
floor tables stay hand-mirrored, so a future widening can arrive without a detection fixture. The
long-standing concatenation / intermediate-variable / indirect-dispatch class remains open by
design -- closing it needs dataflow analysis, not pattern matching, as Story 2.1's AD-4 guard
already recorded. This pass narrowed the guards materially but each of the three review passes has
found a fresh path-build or identifier-position shape, so an independent follow-up remains
worthwhile.

