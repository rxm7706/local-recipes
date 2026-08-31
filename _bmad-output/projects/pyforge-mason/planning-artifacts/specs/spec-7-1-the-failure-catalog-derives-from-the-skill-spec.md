---
title: 'The failure catalog derives from the skill spec'
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_revision: 'fd5c16c16aee5550fd9b18e06a64d6f127a279f1'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
deferred:
  - summary: >-
      symptom_signature tokens are not all meaningfully diagnostic: some rows
      carry a single generic word (e.g. "fails", "work") or a full sentence
      pulled verbatim as their entire signature, and common tokens (e.g.
      "noarch: python", "pip check") repeat across dozens of unrelated rows.
    evidence: |-
      Cross-validated by two independent reviewers (Blind Hunter + the
      Verification Gap Reviewer) against the real committed catalog: G98's
      row is just ["fails"] (SKILL.md:3792, an ordinary English word in
      quotes, not a literal error string); G13 includes "(parens)" and
      "isolate" (SKILL.md:1814, typographic emphasis, not symptom text); G59
      includes an entire reviewer sentence verbatim. Inherent to the
      deliberately narrow, deterministic quote/backtick extraction rule this
      story's intent-contract specifies (a pure syntactic derivation, not an
      NLP/quality filter) — faithful to SKILL.md's prose, not a defect in the
      extractor. Revisit if/when a consumer (Story 7.2 or a future
      build-failure matcher) needs stronger signal quality; a fix would need
      a curated stopword/specificity heuristic that the current spec
      deliberately doesn't define.
    location: >-
      .claude/skills/conda-forge-expert/scripts/failure_catalog_generator.py:_signature_tokens
    severity: medium
  - summary: >-
      The fenced-code-block inclusion heuristic in _symptom_paragraph only
      fires when the Symptom paragraph's prose ends in a literal colon.
    evidence: |-
      A Symptom paragraph that is a complete sentence (no trailing ':')
      immediately followed by a diagnostic fenced code block never gets that
      block's content folded into symptom_signature, even when the block is
      the most useful diagnostic material in the entry. Empirically grounded
      in G5's "fails ... with:" pattern (the one case investigated during
      planning); other, non-colon-ending shapes were not surveyed across all
      110 gotchas. Not a defect against any stated AC — all 110 real rows
      already produce a non-empty signature via the whole-body fallback —
      but a real, narrow-heuristic limitation worth widening later if
      signature richness turns out to matter.
    location: >-
      .claude/skills/conda-forge-expert/scripts/failure_catalog_generator.py:_symptom_paragraph
    severity: low
  - summary: >-
      _ENFORCED_BY_RE's exact-phrase match ("The optimizer's **CODE**
      check") has no fallback signal distinguishing "no check exists yet"
      from "the phrasing drifted."
    evidence: |-
      This is the intent-contract's own deliberate design (Always: "This is
      deliberately conservative... a false non-null pointer is strictly
      worse than an honest null"), so the brittleness itself is intended
      behavior, not a bug. The gap is narrower: a future SKILL.md rewording
      of the two existing declarative sentences (G2/G3) — e.g. pluralizing
      "check" to "checks", or a typo — would silently degrade that row to
      null with no diagnostic distinguishing it from a genuine "not yet
      enforced" gotcha. Currently zero near-miss phrasings exist in the real
      110-gotcha corpus, so there is no live impact today. Worth a mild
      warning/logging enhancement later if SKILL.md's phrasing conventions
      ever drift.
    location: >-
      .claude/skills/conda-forge-expert/scripts/failure_catalog_generator.py:extract_enforced_by
    severity: low
  - summary: >-
      failure-catalog.yaml has no schema_version/format_version field.
    evidence: |-
      Raised by the Blind Hunter review. Reasonable forward-looking idea —
      nothing today consumes the file (Story 7.2, which will build the
      consuming lint/drift gate, doesn't exist yet), so adding a version
      field now would be speculative per this repo's Simplicity First
      principle ("minimum code that solves the problem; nothing
      speculative"). Revisit when Story 7.2 defines what it actually needs
      from the catalog's shape.
    location: >-
      .claude/skills/conda-forge-expert/config/failure-catalog.yaml
    severity: low
---

<intent-contract>

## Intent

**Problem:** `SKILL.md`'s 110-entry gotcha corpus (`G1`–`G110`, "Recipe Authoring
Gotchas" section) is prose with no machine linkage to the checks that enforce
it, so knowledge and enforcement drift apart silently.

**Approach:** Write a deterministic generator script that parses SKILL.md's
gotcha corpus and emits `.claude/skills/conda-forge-expert/config/failure-catalog.yaml`
— one row per gotcha with greppable `symptom_signature` tokens and an
`enforced_by` pointer into the real `recipe_optimizer.py` check-code registry
(or explicit `null`). Wire it up per this repo's three-place new-script
convention (pixi task, `SCRIPTS` list, CLI wrapper) plus a regeneration-parity
meta-test proving hand-edits are detectably wrong.

## Boundaries & Constraints

**Always:**
- The generator is a pure function of SKILL.md's gotcha-section text: same
  input text → byte-identical output file, every run (no wall-clock
  timestamps, no non-deterministic ordering, no network).
- `enforced_by` is assigned ONLY when the gotcha's body contains the exact
  declarative phrase `` The optimizer's **<CODE>** check `` AND `<CODE>` is a
  real, live entry in `recipe_optimizer.py`'s `code="..."` registry (parsed
  from the script's source at generation time, not hand-copied into this
  script). Any other case — no phrase, phrase present but code doesn't exist,
  or the phrase appears more than once with different codes in one gotcha
  body — resolves to `null`. This is deliberately conservative: it is the
  Dream's "honest null" backlog, not an attempt to guess enforcement.
- Follow the repo's three-place new-script convention exactly: a
  `[feature.local-recipes.tasks.generate-failure-catalog]` entry in
  `pixi.toml`, a `.claude/scripts/conda-forge-expert/failure_catalog_generator.py`
  thin subprocess wrapper (filename matches the canonical script), and an
  alphabetised `SCRIPTS` list entry in
  `tests/meta/test_all_scripts_runnable.py`.
- Output file lives at
  `.claude/skills/conda-forge-expert/config/failure-catalog.yaml`
  (config-side, per the spec's pre-resolved `open_questions` entry — it is
  derived-but-tracked, not mutable runtime state).
- New script resolves the repo root via `scripts/_paths.py::get_repo_root()`
  (per SKILL.md's "New Scripts Resolve the Data Dir / Repo Root Through
  `_paths`" constraint) — never a hand-rolled `Path(__file__).parent` walk.
- Write the YAML with `ruamel.yaml` (the pattern `recipe_optimizer.py` already
  uses in this skill), never hand-built string concatenation — G92 in
  SKILL.md documents a real corruption class from unquoted `#`/`:` in
  hand-emitted YAML free text; a real YAML writer handles quoting correctly.
- Regenerating the file from an unchanged SKILL.md must be idempotent
  (running the generator twice produces the same bytes both times).

**Block If:** none identified — the schema, extraction rules, and file
location are all pinned by the spec's own `open_questions` resolution and by
SKILL.md's existing, stable gotcha-heading format (`### G<N>. <title>`, with
`**Symptom**:` / `**Why**:` / `**Fix**:` sub-paragraphs). If SKILL.md's
gotcha-heading format itself turns out inconsistent across all 110 entries in
a way that breaks a uniform regex, HALT with blocking condition
`skill-md gotcha format inconsistent` rather than special-casing silently.

**Never:**
- Never modify `SKILL.md` itself — prose stays authoritative; the catalog
  strictly derives from it.
- Never modify `.claude/skills/conda-forge-expert/scripts/failure_analyzer.py`
  or `.claude/skills/conda-forge-expert/scripts/recipe_optimizer.py` — this
  story only *reads* `recipe_optimizer.py`'s check-code registry to validate
  `enforced_by` pointers at generation time; it does not touch either file.
  `failure_analyzer.py` is a separate, unrelated system (regex-matches build
  *log text* against a 41-pattern library) — do not conflate it with this
  story's SKILL.md-gotcha catalog.
- Never implement the CI drift/lint gate that resolves `enforced_by` pointers
  against the live check surface and fails CI on catalog↔SKILL.md drift —
  that is Story 7.2 (`S-7.1` dependency), explicitly out of scope here. This
  story's own regeneration-parity meta-test (below) is narrower: it only
  proves the catalog is currently in sync with SKILL.md and that hand-edits
  are detectable, not a standing CI gate wired into the doctor detector
  family.
- Never bump `.claude/skills/conda-forge-expert/config/skill-config.yaml`'s
  version or add a `CHANGELOG.md` entry in this story — the Rule-2
  conda-forge-expert retro (CLAUDE.md) lands at the *effort's* closeout
  (after Story 7.2 also ships), not per-story.
- Never invent new `recipe_optimizer.py` check codes to raise the
  `enforced_by` coverage number — the null-rows list is a report/backlog,
  never an actuator (spec Non-goals).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | SKILL.md's current gotcha section (110 entries) | `failure-catalog.yaml` with 110 rows, `id: G1`..`G110` in order, `source_sha256` matching a hash of the extracted section text | No error expected |
| A gotcha with the enforcement phrase | G2's body contains `` The optimizer's **ABT-002** check flags this `` | Row for G2 has `enforced_by: ".claude/skills/conda-forge-expert/scripts/recipe_optimizer.py:ABT-002"` (ABT-002 confirmed present in the live registry) | No error expected |
| A gotcha with a *stale* code mention | Body mentions a code (e.g. a "proposed", "not yet shipped" code like `JIN-001` or `DEP-005`) that does NOT appear in `recipe_optimizer.py`'s live `code="..."` registry | `enforced_by: null` for that row — never a bogus pointer | No error expected (this is the expected, honest null case) |
| A gotcha with a plain cross-reference | G20's body lists G2/G3's codes (`ABT-002`, `SEL-003`) only as a narrative "class of traps" list, not the declarative phrase | `enforced_by: null` for G20 (the phrase-match regex requires the exact `` The optimizer's **CODE** check `` wording; a bare code mention elsewhere in the body does not count) | No error expected |
| Idempotent re-run | Generator run twice in a row with SKILL.md unchanged | Byte-identical output both times | No error expected |
| SKILL.md gotcha section missing or unparseable | The `## Recipe Authoring Gotchas` heading is absent, or zero `### G<N>.` entries are found under it | Exit non-zero with a clear stderr message; do not write a partial/empty catalog file | Non-zero exit, no output-file write |
| `--check` mode (used by the meta-test) | Existing `failure-catalog.yaml` present on disk | Regenerate into memory, diff against the on-disk file; exit 0 if identical, non-zero with a diff summary if not | Non-zero exit with a readable diff on mismatch |

</intent-contract>

## Code Map

- `.claude/skills/conda-forge-expert/SKILL.md:1441-4080` — the `## Recipe
  Authoring Gotchas` section (`### G1.` through `### G110.`). Format per
  entry: `### G<N>. <title>` heading, then `**Symptom**: ...`, `**Why**:
  ...`, `**Fix**: ...` paragraphs (sometimes with additional named
  sub-sections like `**Caveat**`, `**Case study**`, code fences). The next
  top-level `## ` heading after this section is `## Skill Automation` at
  line 4080 — use it as the section's end boundary.
- `.claude/skills/conda-forge-expert/SKILL.md:1445-1516` — G1/G2 full text,
  read directly during investigation; G2's body (line 1495) contains the
  exact enforcement phrase: `` The optimizer's **ABT-002** check flags this
  in v1 recipes. ``. G3's body (line 1518-1535, specifically the Fix
  paragraph) contains `` The optimizer's **SEL-003** check flags v0-style
  `py < N` in v1 recipes. `` — these are the ONLY two matches for this exact
  phrase pattern across all 110 gotchas (verified via
  `grep -n "optimizer's\|check flags" ` over the extracted section — see
  Design Notes). G20 (line 2106-2148) is the confirmed negative case: its
  body mentions `ABT-002` and `SEL-003` only inside a narrative "class of
  substitution traps" bullet list (not the declarative phrase), and
  explicitly states a *third* code, `` **`JIN-001`** ``, "Tracked as skill
  TODO; not yet shipped" — proving `JIN-001` must resolve to `null` (it is
  not in the live registry either).
- `.claude/skills/conda-forge-expert/scripts/recipe_optimizer.py` — the real,
  greppable check-code registry. Read-only for this story. The registry is
  NOT the module docstring's header count comment (which is itself stale —
  it says "17 total" but the docstring body lists 20, and the *actual* live
  `code="..."` assignments in the function bodies total 22, including
  `ABT-003` and `SEL-004` which are absent from BOTH the docstring header
  count and its body list). Derive the registry by regex-scanning the
  literal `code="([A-Z]+-[0-9]+)"` assignments in the script's source text —
  never from the docstring, and never hand-copied into the new script (spec
  contract Charter §2 / "Derive, don't declare"). Confirmed live registry
  (22 codes): `SCHEMA-001, DEP-001, DEP-002, PIN-001, ABT-001, ABT-002,
  ABT-003, LIC-001, FMT-001, SCRIPT-001, SCRIPT-002, SEL-001, SEL-002,
  SEL-003, SEL-004, STD-001, STD-002, SEC-001, TEST-001, TEST-002, TEST-003,
  MAINT-001`.
- `.claude/skills/conda-forge-expert/scripts/_paths.py` — `get_repo_root()`
  / `get_data_dir()`. Import pattern: `from _paths import get_repo_root`
  after inserting the script's own directory onto `sys.path` (see the
  guarded-insert pattern already used by `recipe_optimizer.py` and
  `cwe_seed_gap.py`, lines ~49-56 and ~30-32 respectively — copy that
  guard, not a bare unconditional `sys.path.insert`).
- `.claude/skills/conda-forge-expert/scripts/cwe_seed_gap.py` — reference
  pattern for a read-only, offline, `argparse`-driven CLI in this scripts
  directory (imports, `--json`/`--out`/`--limit` flag shapes, `main()`
  returning an int, `if __name__ == "__main__": sys.exit(main())`). This
  story's generator is a REAL writer (not an advisory suggester like
  `cwe_seed_gap.py`), so it needs a `--check` flag (dry-run: diff against
  the on-disk file, exit non-zero on mismatch, never write) in addition to
  the default write-mode — model `--check` after any existing "verify
  without mutating" flag pattern in this scripts directory if one exists,
  otherwise implement straightforwardly (read on-disk file if present,
  compare against freshly-generated content, report and exit).
- `.claude/scripts/conda-forge-expert/cwe_seed_gap.py` — the canonical thin
  wrapper shape to copy for the new
  `.claude/scripts/conda-forge-expert/failure_catalog_generator.py`
  (subprocess to the canonical script, `Path(__file__).parent.parent.parent
  / "skills" / "conda-forge-expert" / "scripts" / "<name>.py"`, no logic).
- `pixi.toml:833-839` — the `fetch-cwe-catalog` / `cwe-seed-gap` task-block
  pattern to copy for the new `[feature.local-recipes.tasks.generate-failure-catalog]`
  entry (task name free-form; `cmd = "python
  .claude/scripts/conda-forge-expert/failure_catalog_generator.py"`).
- `.claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py:11-68`
  — the `SCRIPTS` list (append `"failure_catalog_generator.py"` in
  alphabetical position, between `"failure_analyzer.py"` and
  `"feedstock_context.py"`) and the `NO_HELP` set (the new script supports
  `--help` via argparse, so no `NO_HELP` entry needed).
- `.claude/skills/conda-forge-expert/tests/meta/test_skill_md_consistency.py`
  — `test_pixi_toml_tasks_reference_existing_scripts` and
  `test_every_user_script_has_a_pixi_task` will auto-pass once the pixi task
  + wrapper exist with matching filenames; no edits needed to this test file
  itself.
- `.claude/skills/conda-forge-expert/tests/unit/test_cwe_seed_gap.py` —
  reference shape for the new unit test file
  `tests/unit/test_failure_catalog_generator.py` (module-scope
  `importlib.util` loader fixture pattern; see lines 19-31 for the exact
  loader helper to copy).
- `.claude/skills/conda-forge-expert/tests/meta/test_skill_files_tracked.py`
  — walks the filesystem and diffs against `git ls-files` (not
  `git status`, which a stray `.git/info/exclude` entry could mask per the
  ZEROTH-step warning in this repo's own new-script convention memory).
  Confirm the new script files are actually `git add`-able / tracked before
  considering the story done — this test will catch it if not, but verify
  proactively too.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-machine-checked-recipe-knowledge/SPEC.md`
  — the governing SPEC.md (CAP-1). Its `open_questions` entry
  ("Catalog file home: `.claude/skills/conda-forge-expert/config/` vs
  `data/` — decide at 7.1 (it is derived+tracked, so config-side).") is
  RESOLVED by this spec: `config/`. No SPEC.md edit needed by this story —
  the resolution is recorded here in the Design Notes below for traceability.

## Tasks & Acceptance

**Execution:**
- `.claude/skills/conda-forge-expert/scripts/failure_catalog_generator.py` --
  NEW canonical script -- parses SKILL.md's gotcha section deterministically,
  cross-references `recipe_optimizer.py`'s live `code="..."` registry, and
  writes `.claude/skills/conda-forge-expert/config/failure-catalog.yaml`.
  Supports `--check` (diff-only, exit non-zero on mismatch, never writes)
  and default write-mode. Resolves paths via `_paths.get_repo_root()`.
  Uses `ruamel.yaml` for the write.
- `.claude/skills/conda-forge-expert/config/failure-catalog.yaml` -- NEW
  generated artifact -- committed output of a `--write` run against the
  current SKILL.md.
- `.claude/scripts/conda-forge-expert/failure_catalog_generator.py` -- NEW
  thin wrapper -- subprocess delegate to the canonical script (three-place
  rule, tier 3/3).
- `pixi.toml` -- ADD `[feature.local-recipes.tasks.generate-failure-catalog]`
  block -- three-place rule, tier 2/3 (wires the wrapper into `pixi run`).
- `.claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py`
  -- ADD `"failure_catalog_generator.py"` to `SCRIPTS` (alphabetical
  position) -- three-place rule, tier 1/3 (keeps the meta-suite's
  drift-detection green for the new script).
- `.claude/skills/conda-forge-expert/tests/unit/test_failure_catalog_generator.py`
  -- NEW -- unit tests for the parser/extractor logic against a small
  synthetic SKILL.md-shaped fixture (do not depend on the real 4200-line
  SKILL.md for unit coverage; use an inline fixture string covering: a
  gotcha with the enforcement phrase + a real code, a gotcha with no code
  mention, a gotcha mentioning a stale/nonexistent code, a gotcha with the
  phrase pointing at TWO different codes in one body — must resolve to
  `null` per the ambiguity rule).
- `.claude/skills/conda-forge-expert/tests/meta/test_failure_catalog_freshness.py`
  -- NEW -- meta-test asserting `failure_catalog_generator.py --check`
  exits 0 against the real, live SKILL.md and the committed
  `failure-catalog.yaml` (this is the story's "derived-artifact discipline:
  hand edits detectably wrong" proof — a hand-edit to the catalog, or a
  SKILL.md edit without regenerating, reds this test). Model the
  invocation/subprocess pattern after
  `test_bmad_artifacts_in_sync.py` or `test_recipe_yaml_schema_header.py`
  (whichever runs an external script via `subprocess.run` and asserts its
  exit code) rather than reinventing a subprocess-invocation pattern.

**Acceptance Criteria:**
- Given the current SKILL.md, when `failure_catalog_generator.py --check`
  runs, then it exits 0 (the committed `failure-catalog.yaml` matches a
  fresh regeneration).
- Given the current SKILL.md, when `failure_catalog_generator.py` (write
  mode) runs twice in a row, then both runs produce byte-identical output
  (idempotency / determinism).
- Given `failure-catalog.yaml`, when inspected, then it has exactly 110
  rows with `id` values `G1` through `G110` in ascending numeric order, and
  every row has a non-empty `symptom_signature` list.
- Given `failure-catalog.yaml`, when inspected, then exactly the rows for
  `G2` and `G3` carry a non-null `enforced_by` pointer (matching the current
  SKILL.md content verified during investigation), and every other row's
  `enforced_by` is explicit `null` — never a bogus/unresolvable string.
- Given a hand-edit to `failure-catalog.yaml` (e.g. deleting a row or
  changing a `symptom_signature` value), when
  `failure_catalog_generator.py --check` runs, then it exits non-zero with
  a diff summary (proves "hand edits detectably wrong").
- Given `pixi run -e local-recipes test-skill -- --meta`, when run after
  this story's changes, then it passes (the three-place-rule meta-tests —
  `test_all_scripts_runnable`, `test_pixi_toml_tasks_reference_existing_scripts`,
  `test_every_user_script_has_a_pixi_task`, `test_skill_files_tracked` —
  all green).

## Spec Change Log

_(empty — no review loopback yet)_

## Review Triage Log

### 2026-08-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 5, low 2)
- defer: 4: (high 0, medium 1, low 3)
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[medium]` `[patch]` `split_gotcha_entries` raised nothing on a malformed `### G` heading (missing `. <title>`) — it silently absorbed the line into the previous entry's body, corrupting that entry's signature and dropping the malformed gotcha from the catalog with no error. Fixed: raises `CatalogError` on any line matching `^### G` that doesn't fully match the heading regex. Added `test_split_gotcha_entries_malformed_heading_raises`.
  - `[medium]` `[patch]` `split_gotcha_entries` had no duplicate-number check — two headings sharing the same `G<N>` would both parse and ship as two rows with the same `id`, violating "one row per gotcha" silently. Fixed: raises `CatalogError` on a repeated gotcha number. Added `test_split_gotcha_entries_duplicate_number_raises`.
  - `[low]` `[patch]` `extract_gotcha_section`'s section-heading match only stripped the trailing newline (`line.rstrip("\n")`), so trailing whitespace on the heading line would make the section undetectable. Fixed: `line.rstrip()`.
  - `[medium]` `[patch]` `_REGISTRY_CODE_RE` matched only double-quoted `code="..."` assignments in `recipe_optimizer.py`; a future single-quoted assignment there (out of this story's scope to prevent, not to read robustly) would silently vanish from the derived registry and mis-resolve its gotcha's `enforced_by` to null. Fixed: `code=["\']([A-Z]+-[0-9]+)["\']` accepts either quote style. Added `test_extract_optimizer_registry_accepts_single_quoted_code`.
  - `[medium]` `[patch]` `main()`'s file I/O was inconsistently guarded: the two SKILL.md/optimizer read try/excepts caught `OSError` but not `UnicodeDecodeError`; the `--check` on-disk read and the final `mkdir`+`write_text` had no guard at all, so a filesystem failure there crashed with a raw traceback instead of the function's own established clean-error-and-`return 1` pattern. Fixed: all three read sites now catch `(OSError, UnicodeDecodeError)`; the on-disk `--check` read and the write are now wrapped the same way. Added `test_main_write_failure_is_guarded` and `test_main_check_on_disk_read_failure_is_guarded`.
  - `[medium]` `[patch]` `build_catalog` had no structural guarantee behind the spec's own "every row has a non-empty `symptom_signature`" acceptance criterion — it held only empirically (all 110 real gotchas happen to produce a non-empty signature via the whole-body fallback). Fixed: raises `CatalogError` naming the offending gotcha id if a row's signature would be empty. Added `test_build_catalog_zero_signature_tokens_raises`.
  - `[low]` `[patch]` `quickref/commands-cheatsheet.md` didn't list the new `generate-failure-catalog` pixi task, unlike its sibling generator tasks (`cwe-seed-gap`, `fetch-cwe-catalog`, etc.). Fixed: added a matching entry.

Rejected (3, all explicitly excluded by this story's own `<intent-contract>`, not a gap): no CHANGELOG entry / skill-config.yaml version bump this story (intent-contract's own "Never" boundary — the Rule-2 retro lands at the effort's closeout after Story 7.2, not per-story); no inline SKILL.md note about the regen requirement (would require editing SKILL.md, forbidden by intent-contract's "Never modify SKILL.md itself"); only 2/110 gotchas resolve `enforced_by` (intent-contract's own "Always" boundary states this is the deliberate, honest starting state — "the null rows ARE the backlog").

Deferred (4, real but judgment-heavy quality observations that don't violate any stated AC — see frontmatter `deferred` for full detail): signature-token specificity/length (generic single-word or whole-sentence tokens; medium), the colon-only fenced-code-block inclusion heuristic (low), `enforced_by`'s exact-phrase match having no drift-warning signal (low), and no `schema_version` field in the catalog (low, speculative until Story 7.2 defines a real need).

## Design Notes

**`enforced_by` extraction is deliberately narrow, not a general NLP match.**
Investigation (grepping the extracted gotcha section for every known live
check code plus every `[A-Z]{2,6}-[0-9]{2,4}`-shaped token) found only 7
G-numbers mentioning any check-code-shaped string at all, and only 2 of
those (G2 → `ABT-002`, G3 → `SEL-003`) use the exact declarative phrase
`` The optimizer's **<CODE>** check ``. The others are cross-references
(G20's "class of traps" list, which explicitly cites a fourth code,
`JIN-001`, as "not yet shipped"), a self-contradicting false-positive
description (G29's title/body describes `TEST-001` *misfiring*, not
correctly enforcing, on that gotcha — the phrase-match rule correctly
excludes it since the exact wording isn't present), or bare parenthetical
asides (G44's "STD-001 does not apply" — a negation; G90's "(STD-001)" — a
weak aside). A catalog where 108/110 rows are `null` and only 2 are covered
is not a bug in the extractor — it is the accurate, honest starting state
this epic exists to surface (Dream: "the null-rows report IS the
prioritized backlog for new checks"). Resist the temptation to loosen the
regex to catch more rows; a false non-null pointer is strictly worse than
an honest null (SPEC constraint: "planting a bogus pointer... reds the
suite" is Story 7.2's proof obligation, and a generator that ships bogus
pointers defeats that proof before 7.2 even exists).

**`symptom_signature` token extraction.** Each gotcha's `**Symptom**:`
paragraph (through the next `**Why**:` or blank-terminated boundary; include
an immediately-following fenced code block if the Symptom paragraph's prose
ends without full sentences, i.e. it trails into a code block as its
evidence — see G5's "fails ... with:" pattern) is scanned for two
regex classes, in order of appearance, deduped, capped at a small count
(e.g. 8) to keep rows grep-scannable: double-quoted substrings (real error
strings, e.g. `"No license files were copied"`) and backtick code spans
(e.g. `` `export FOO=bar` ``). This mirrors how the gotchas are already
authored (they consistently use backticks for code/commands and double
quotes for literal error text), so no new annotation convention is needed
on the SKILL.md side.

**Schema:**
```yaml
# GENERATED FILE — DO NOT HAND-EDIT.
# Regenerate with: pixi run -e local-recipes generate-failure-catalog
# Derived deterministically from .claude/skills/conda-forge-expert/SKILL.md's
# "Recipe Authoring Gotchas" section. Hand edits are detectably wrong —
# regenerating overwrites them; see tests/meta/test_failure_catalog_freshness.py.
source_sha256: "<sha256 of the extracted gotcha-section text>"
rows:
  - id: G1
    title: "`script:` list entries run in separate shells — env vars do NOT carry across entries"
    symptom_signature:
      - "export FOO=bar"
      - "pip install"
      - "CFLAGS"
    enforced_by: null
  - id: G2
    title: "v0/meta.yaml field names in v1 recipe.yaml are silently ignored"
    symptom_signature:
      - "..."
    enforced_by: ".claude/skills/conda-forge-expert/scripts/recipe_optimizer.py:ABT-002"
```
No `generated_at` timestamp field — a wall-clock value would make every
regeneration a spurious diff and break the `--check` idempotency
requirement. `source_sha256` (a hash of the extracted gotcha-section text,
not the whole SKILL.md file) is the traceable "what was this derived from"
anchor instead, and doubles as the natural drift signal Story 7.2's CI gate
can build on.

**Why config/, not data/.** `SPEC.md`'s own open question resolves this:
the catalog is a derived-but-tracked artifact (git-committed, reviewed like
code), not mutable runtime state — `.claude/data/conda-forge-expert/` is
gitignored (cf_atlas.db, caches). `config/` already holds
`skill-config.yaml`, a tracked, hand-and-tool-maintained file of the same
character.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Not applicable — all checks above are scriptable.

## Auto Run Result

**Summary:** Implemented Story 7.1 exactly per the intent-contract: a new deterministic generator (`failure_catalog_generator.py`) parses SKILL.md's `## Recipe Authoring Gotchas` section (`### G1.`..`### G110.`) into `.claude/skills/conda-forge-expert/config/failure-catalog.yaml` — one row per gotcha with `symptom_signature` (greppable quoted/backtick tokens) and `enforced_by` (a pointer into `recipe_optimizer.py`'s live check-code registry, derived by regex from that script's source, or explicit `null`). Wired per the repo's three-place new-script convention (pixi task, `SCRIPTS` list, CLI wrapper) plus a regeneration-parity meta-test. A step-04 review pass (Blind Hunter + Edge Case Hunter + Verification Gap Reviewer + Intent Alignment Auditor, run in parallel) found 0 intent_gap / 0 bad_spec findings; 7 patch findings were applied directly (parser robustness + I/O guarding + a structural non-empty-signature guarantee + a cheatsheet doc entry); 4 findings were deferred as real-but-non-blocking quality observations; 3 findings were rejected as explicitly excluded by the spec's own `<intent-contract>` boundaries.

**Files changed:**
- `.claude/skills/conda-forge-expert/scripts/failure_catalog_generator.py` — new canonical generator (parse, cross-reference, render, `--check`/write CLI).
- `.claude/skills/conda-forge-expert/config/failure-catalog.yaml` — new generated artifact (110 rows, `G1`-`G110`; `enforced_by` non-null on exactly `G2`/`G3`).
- `.claude/scripts/conda-forge-expert/failure_catalog_generator.py` — new thin subprocess wrapper (three-place rule, tier 3/3).
- `pixi.toml` — new `[feature.local-recipes.tasks.generate-failure-catalog]` task (tier 2/3).
- `.claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py` — `failure_catalog_generator.py` added to `SCRIPTS` (tier 1/3).
- `.claude/skills/conda-forge-expert/tests/meta/test_failure_catalog_freshness.py` — new meta-test running `--check` against the live SKILL.md (the "hand edits detectably wrong" proof).
- `.claude/skills/conda-forge-expert/tests/unit/test_failure_catalog_generator.py` — new unit tests (28, all passing) against an inline synthetic fixture.
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` — added the `generate-failure-catalog` pixi task entry (review patch).

**Review findings breakdown:** patch: 7 (medium 5, low 2) — all applied. defer: 4 (medium 1, low 3) — recorded in frontmatter `deferred`. reject: 3 (low 3) — all explicitly excluded by intent-contract's own Never/Always boundaries (no per-story CHANGELOG/version bump; no SKILL.md self-edit; the 2/110 `enforced_by` coverage is the deliberate honest-null starting state).

**Follow-up review recommendation:** `true` — this pass's patch findings scored 3×5(medium) + 1×2(low) = 17 (≥5 threshold); no high-severity patch findings.

**Verification performed:**
- `pixi run -e local-recipes generate-failure-catalog -- --check` — exit 0, "failure-catalog.yaml is in sync with SKILL.md (110 rows)." (run independently after both the initial implementation and the 7-patch pass).
- Row-count/ordering sanity check (`yaml.safe_load` + assert 110 rows `G1`..`G110` in order) — passed.
- `pixi run -e local-recipes test-skill -- --unit -k failure_catalog -v` — 28/28 passed (independently re-run after the patch pass).
- `pixi run -e local-recipes test-skill -- --meta` — 7551 passed, 2 failed, 3 skipped. The 2 failures (`test_no_redundant_python_min.py`, `test_recipe_yaml_parse_audit.py`) are pre-existing and unrelated to this story — confirmed via `git stash` against the pre-story baseline (`fd5c16c16aee5550fd9b18e06a64d6f127a279f1`), which reproduces the identical 2 failures with 0 files from this story present.
- `pixi project export conda-environment -e build` diffed against the committed `environment.yaml` — no drift (the `pixi.toml` change is task-only, adds no dependency).
- Read the full diff against baseline and the final generator source directly to confirm every one of the 7 patch findings was substantively (not just superficially) applied, not merely claimed.
- `git status` / `git diff --cached --stat` confirm exactly the 8 expected files are staged, matching the Code Map and Tasks sections.

**Residual risks:** None blocking. The 4 deferred findings (signature-token specificity, the colon-only fence-inclusion heuristic, `enforced_by`'s no-drift-warning brittleness, no `schema_version` field) are real but judgment-heavy quality observations that don't violate any stated AC — flagged for whoever picks up Story 7.2 (the CI drift/lint gate that will actually consume this catalog) to revisit if signature/pointer quality turns out to matter in practice.
