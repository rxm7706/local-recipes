---
title: '28.1: A frontmatter reader that stops at the fence, not at the first dashes'
type: 'fix'
created: '2026-09-19'
status: 'in-review'
baseline_revision: '78e195a97d53c16a2b3fe2f7f12091a96ea44d43'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/hygiene.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-50-5-the-promoter-reads-a-spec-through-its-banner.md
deferred:
  - summary: >-
      status_body_consistency._parse_frontmatter is a verbatim copy of the pre-CAP-81
      first-dashes-anywhere reader, so CAP-3 and CAP-81 now render contradictory verdicts
      on the same document
    evidence: |-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/status_body_consistency.py:219-236
      still tests for the three-dash substring anywhere in the text and splits on its first occurrence; its
      `_body_after_frontmatter` (:239-246) finds the first newline-fence-newline marker
      (the three dashes are not spelled out here so no first-dashes reader truncates this
      very entry). After CAP-81 lands,
      a Dream with prose, a three-dash thematic break and no frontmatter is `({}, False)` ->
      `dream-without-spec` in chain.py but `({}, True)` -> an `unparseable` WARN in
      status_body_consistency.py, and the 34 glued-opener (three dashes fused to `title:`) archived Dreams
      are refused by chain.py but silently parsed by this copy. Review pass 1
      (2026-09-19) verified the divergence by reading both readers; PR #1494's memlog
      entry already notes this copy "for CAP-81's story". Named blocker: CAP-81's intent
      names `chain.py::_frontmatter_parse` only, and a detector's own reader is chain
      work (Dream-first) — this needs its own CAP/story under spec-pyforge-doctor, not a
      hand-patch under Story 28.1.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/status_body_consistency.py::_parse_frontmatter
    severity: medium
  - summary: >-
      factory.py's pin-scope extractor still takes the frontmatter as the text before
      the first three-dash substring, so a pin declared after an embedded three-dash run in a
      frontmatter scalar is missed
    evidence: |-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py:631
      splits the text on its first three-dash substring; `scope = parts[1]` when the text starts with
      three dashes. A frontmatter value quoting three dashes before the pin key truncates `scope` and
      `_PIN_KEY_RE.search` misses the pin -> `pin-missing` on a doc that declares one.
      No live doc has the shape today (review pass 1 scan, 2026-09-19); same named
      blocker as the status_body_consistency entry — a separate capability's reader.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py::_doc_pin
    severity: low
  - summary: >-
      34 archived docs/dreams/*.md files carry a glued opener (three dashes fused to
      `title:` on line 1) and are now refused as unparseable-frontmatter, hiding 20
      readme-table-drift and 2 kinship-wikilink-dead findings until the openers are
      repaired
    evidence: |-
      The 2026-09-17 one-chain-per-station fold wrote the opener as three dashes fused
      to `title:`; `0b74756679` ("keep satellite Dream hashes") deliberately restored
      that shape on all 34 to hold spec-pyforge-steward's surface stable. Story 28.1's
      opener rule (an attempted-but-unbounded opener is refused, never parsed leniently
      or read as absent) turns them into 34 live `unparseable-frontmatter` WARNs
      (`gather_dreams_hygiene` 173 -> 185, `gather_dream_chain` 1 OK -> 34 WARN) and
      skips them before the readme-drift and Kinship scans (`readme-table-drift`
      73 -> 53; `kinship-wikilink-dead` 33 -> 31, both from `enterprise-airgap.md`).
      Repair: insert a line break after the three dashes on line 1 of each file.
      Two of them -- `docs/dreams/mcp-era-isolation.md` and
      `docs/dreams/mcp-host-real-station-tools.md` -- are governed by
      `pyforge-steward/spec-mcp-era-isolation` / `spec-mcp-host-real-station-tools`
      (steward memlog event + scoped `--write-baseline` for each), and the same PR must
      re-measure `test_live_tree_kinship_wikilink_dead_count` 31 -> 33 and run
      `pyforge-doctor-test` locally, because a docs-only diff cannot fire the doctor
      station lane (the MRS-GATE-001 class). Named blocker: cross-station (steward-
      governed files) and outside Story 28.1's Surface; verified live 2026-09-19.
    location: >-
      docs/dreams/ (34 files whose first line begins with the three dashes fused to `title:`; the two steward-governed ones are named in the evidence)
    severity: medium
  - summary: >-
      `unparseable-frontmatter` findings name no refusal cause, and
      `_unparseable_frontmatter_item`'s remedy text ("could not be parsed as a mapping
      ... fix the fenced YAML frontmatter block") is wrong for the attempted-but-
      unbounded opener that produces all 34 live hits
    evidence: |-
      `chain.py::_frontmatter_parse` returns `(dict, bool)`; after Story 28.1 four
      distinct refusal causes (unclosed fence; attempted-but-unbounded opener; YAML
      error; non-mapping block) collapse into one bool, so `gather_dreams_hygiene`
      (the `unparseable-frontmatter` WARN, evidence `{"subject": slug}`) and
      `_unparseable_frontmatter_item` (the remedy line) cannot say WHICH line to fix --
      for the 34 glued-opener Dreams the block IS a valid mapping and the only defect
      is line 1. Story 28.1's Never clause ("do not touch callers") excludes threading
      a reason through those call sites. Named blocker: needs a CAP that widens the
      reader's return contract (a reason enum) or adds a reason field to the finding,
      under spec-pyforge-doctor; review pass 2, 2026-09-19.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py::_unparseable_frontmatter_item
    severity: medium
  - summary: >-
      Five other doctor readers close the frontmatter block on a stripped three-dash
      line, so an indented three-dash line inside a block scalar ends their block early
      with no error -- the class Story 28.1 fixed only in chain.py::_frontmatter_parse
    evidence: |-
      `line.strip()` fence tests at `hygiene.py::_dream_frontmatter_status` (:269/:272),
      `sibling_dreams.py` (:82/:85), `status_body_consistency.py` (:518/:520 and
      :699/:702), `board.py` (:433) and `chain.py::_parse_surface` (:1615, the
      marshal-bound spec-surface contract). An `evidence: |` block scalar whose content
      has an indented three-dash line closes each of these early and drops every later
      key with no error (`_frontmatter_parse` now uses `rstrip`, column 0). 0 live
      Dreams/specs carry the shape (scan 2026-09-19). Named blocker: other
      capabilities' readers and a marshal-bound contract -- their own CAP/story, not
      Story 28.1.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/hygiene.py::_dream_frontmatter_status
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `_frontmatter_parse` on marshal's `spec-50-5-the-promoter-reads-a-spec-through-its-banner.md` returns one deferral with no `location:` where the file declares two, and a prose file containing `---` returns `({}, True)`

**Approach:** the block is bounded by line-anchored fences and a leading banner is skipped

## Boundaries & Constraints

**Always:**
- the 50.5 fixture parses both deferrals — the first with `location:` (fingerprint `fdd6bce25c09`), the second (`5434eca8c9e5`, severity high) visible to `deferred-work` and to `deferred_work_intake.py`; a prose file with a `---` rule and no leading fence is `({}, False)`; an unclosed fence is `({}, True)`; a banner-topped tracked spec parses
- every existing caller's fixture set yields byte-identical verdicts, and restoring `split("---", 2)` re-truncates the fixture (mutation test)

**Never:**
- Do not widen what counts as parseable — an unbounded or non-mapping block stays `({}, True)` (Story 17-1 / FR-144); do not change the exit-code domain; do not touch callers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-81`.
Surface (amended 2026-09-19, review pass 1 — see Spec Change Log):
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py::_frontmatter_parse` (and its fields-only wrapper `_frontmatter` — the epic's `_frontmatter_fields` is this function; no symbol of that name exists).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py::_dream_body_after_frontmatter` — the same module's body-side reader of the SAME boundary; it must derive the body from the identical line-anchored scan (Design Notes § Body boundary), or the kinship scan reads accepted frontmatter as body.
- Tests: `tests/unit/test_sources_chain_frontmatter_parse.py` (new, the primitive), `tests/unit/test_sources_chain_deferred_work.py` (the 50.5 fixture through `parse_spec_frontmatter_deferrals`), `tests/unit/test_sources_chain_dream_chain.py` (the displaced-block fixture), `tests/unit/test_sources_chain_dreams_hygiene.py` (the body-boundary fixture + one live pin re-measured). The 50.5 fixture is a byte-verbatim SNAPSHOT under `tests/fixtures/` of marshal's tracked spec as landed on `main` — not a live read of marshal's planning tree (Design Notes § Fixture).
- Landing surface: `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` (one event line) + `scripts/.spec-surface-baseline.json` (scoped stamp) — every file above is governed by `pyforge-doctor/spec-pyforge-doctor`.
- No caller changes (the functions that call `_frontmatter_parse` / `_frontmatter` are untouched); no other `sources/*.py` module's own reader is touched (see frontmatter `deferred:`).
Ledger key: `28-1-a-frontmatter-reader-that-stops-at-the-fence-not-at-the-first-dashes`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` can resolve `spec-28-1-a-frontmatter-reader-that-stops-at-the-fence-not-at-the-first-dashes.md`.

## Design Notes

Decided at review pass 1 (2026-09-19) from the epic's own wording — "the opening fence on the first line (optionally after a `<!-- … -->` banner), the closing fence a line that is exactly `---`", "a block that cannot be bounded is refused rather than degraded" — and from live measurement of the tree. These are the rules the implementation binds to; the intent-contract above is unchanged.

### Fence rule (both fences column-0, exactly `---`)

- Read the file, apply `_skip_leading_banner` (Story 50.5 / `spec-pyforge-marshal:CAP-248` port — see KEEP), then `splitlines()`.
- A line is a fence iff `line.rstrip() == "---"`. **Not** `line.strip()`: an INDENTED `  ---` is content inside a YAML block scalar (`evidence: |` … `  ---`), and treating it as the closing fence silently truncates the block — the story's own defect class one shape over from the 50.5 fixture. `hygiene.py`'s local reader uses `.strip()`; do not copy that here, and do not touch `hygiene.py`.
- Opening fence: `lines[0]` must be a fence. Closing fence: the first later line that is a fence. Everything between is the YAML block; `yaml.safe_load` it; keep the existing tail unchanged (`None` → `({}, False)`; non-mapping → `({}, True)`; YAML error → `({}, True)`; read failure → `({}, True)`).
- No closing fence → `({}, True)` (unbounded, refused — Story 17-1 / FR-144).

### Opener rule (attempt detection is separate from bounding)

- If `lines[0]` is not a fence but `lines[0].strip().startswith("---")` — e.g. `---title: …` glued on line 1, `----`, ` ---`, `--- # comment` — the document ATTEMPTED a block that cannot be bounded → `({}, True)`. This is the "refused rather than degraded" clause. **Known-bad state avoided (pass 1):** returning `({}, False)` here made 34 archived `docs/dreams/*.md` files (glued `---title:` opener from the 2026-09-17 fold, deliberately left in place by `0b74756679`) read as "no owner / no status / no title" — live `gather_dreams_hygiene` went 173 → 255 findings (+34 `dream-unowned`, +34 `dream-vocab`, +34 `missing-title`, −20 real `readme-table-drift`), a silent degradation with green tests. Under this rule the same tree measures 185: +34 `unparseable-frontmatter` (honest), `kinship-wikilink-dead` 33 → 31 (two of the 34 carried dead links and are now refused before the scan), `readme-table-drift` 73 → 53. Do NOT parse a glued opener leniently either (marshal's `is_valid_spec_text` does; it is a paper-trail smoke check, not this reader's contract).
- If `lines[0]` neither is a fence nor starts with `---` after stripping (plain prose, a leading blank line, a UTF-8 BOM, a prose file with a `---` thematic break lower down, a complete `---`/YAML/`---` block displaced below prose, an unclosed `<!--` banner) → `({}, False)`: absent metadata, per the Always clause "no leading fence is `({}, False)`". The displaced-block shape is the one existing fixture whose verdict changes (`test_sources_chain_dream_chain.py::test_markdown_without_a_leading_frontmatter_fence_surfaces_unparseable` → rename to `…_is_absent_not_unparseable`, expect `dream-without-spec` with `owner == "(none)"`, no `unparseable-frontmatter`); the docstring must say Story 28.1's Always clause supersedes the Story 17-1 pin for that exact shape.

### Body boundary (`_dream_body_after_frontmatter`)

- Replace its `text.split("---", 2)` with the same scan: skip the banner, `splitlines()`, if `lines[0]` is not a fence return the text unchanged (mirrors today's `startswith` guard for the no-frontmatter case — the caller only reaches it after `_frontmatter_parse` accepted the file), find the closing fence by the same `rstrip() == "---"` test, return `"\n".join(lines[close + 1:])` (with a trailing newline if the original had one; the kinship scan only regexes `[[…]]`, so exact whitespace is not load-bearing — say so in the docstring). No closing fence → `""` (unchanged).
- Prefer one private helper (e.g. `_split_fenced_block(text) -> tuple[list[str], list[str], bool] | None`) used by both functions over two copies of the scan.
- Pin with two `gather_dreams_hygiene` fixtures in `test_sources_chain_dreams_hygiene.py`, modelled on `test_kinship_wikilink_skips_frontmatter_fence`: (a) frontmatter containing a scalar that quotes `"---"` followed by `note: [[not-a-link]]` inside the fence; (b) a banner-topped Dream with a `[[not-a-link]]` inside the fence — both must produce NO `kinship-wikilink-dead`. **Known-bad state avoided:** with the parser fixed but the body helper untouched, both shapes emitted `kinship-wikilink-dead {'link_target': 'not-a-link'}` (verified in-process at pass 1).
- Re-measure `test_live_tree_kinship_wikilink_dead_count` (currently asserts 33) → 31 under the opener rule, with a docstring naming the two refused glued-opener Dreams as the reason and that it returns to 33 once their openers are repaired. Do not add new live-count pins (a docs-only repair PR cannot fire the doctor lane — the MRS-GATE-001 trap recorded in the memlog).

### Fixture

- Copy `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-50-5-the-promoter-reads-a-spec-through-its-banner.md` byte-verbatim (24,222 bytes at `origin/main` `62c09c2e27`) to `src/shared/packages/pyforge-doctor/tests/fixtures/chain/spec-50-5-the-promoter-reads-a-spec-through-its-banner.md`. Provenance (source path, `main` SHA, date) goes in the test's docstring, never inside the fixture (a header comment would change the bytes and, above the fence, exercise the banner skip by accident).
- The fixture test reads the SNAPSHOT: `_frontmatter_parse` → `unparseable is False`, two `deferred` items; `parse_spec_frontmatter_deferrals` → `malformed == ()`, two findings; first: location `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/spec_low_risk.py::parse_declared_low_risk`, severity `medium`, fingerprint `3bc3d91bdf95`; second: location `…/promotion.py::_skip_leading_banner`, severity `high`, fingerprint `5434eca8c9e5`. **Known-bad state avoided:** reading marshal's live tracked spec re-creates the live-baseline class that blocked this story at pass 0 — a marshal-only edit to that spec's `deferred:` would red doctor's suite on the next unrelated doctor PR, and CI's `src/shared/packages/**` paths filter cannot fire the lane on the marshal edit.
- On the Always clause's `fdd6bce25c09`: that is the PRE-fix, truncated-parse fingerprint (no `location:`); `3bc3d91bdf95` is `harvest_fingerprint(summary, location)` with the location present and is what marshal's `deferred-work-ledger.md` `origin:` line records. Assert `3bc3d91bdf95`; do not edit the intent-contract.

### Primitive tests (`tests/unit/test_sources_chain_frontmatter_parse.py`)

Cover, each as its own test against `chain._frontmatter_parse` on a `tmp_path` file: prose with a `---` rule and no leading fence → `({}, False)`; plain prose → `({}, False)`; a complete block displaced below prose → `({}, False)`; unclosed fence → `({}, True)`; a folded scalar (`>-`) quoting `---` mid-line → parses, `status`/`title` intact; a single-line quoted `title: "---"` → parses; a block scalar (`|`) containing an INDENTED `  ---` line → parses with the scalar intact and the later keys present; a glued `---title: x` opener → `({}, True)`; ` ---` (leading whitespace) → `({}, True)`; banner-topped (single-line and multi-line `<!-- -->`) → parses; banner BELOW the fence (the PR #1460 shape every tracked spec on `main` carries) → parses unchanged; unclosed `<!--` → `({}, False)`; empty block `---\n---` → `({}, False)`; non-mapping block → `({}, True)`; ordinary block → exact dict; unreadable path → `({}, True)`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: no `[spec-surface] drift: fail` line naming `pyforge-doctor/spec-pyforge-doctor` (read the lines, never the exit code — this task projects through `pyforge.doctor.verdict.exit_code_for`, a different domain than the aggregator; `docs/reference/judgement-vocabulary.md` § Severity and exit codes). Reconcile, as the LAST step after all code is final: append one `- (event by claude) …` line to `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` naming CAP-81 / Story 28.1 and the files that moved, bump its `updated:`, `git add` every new file (the stamp reads `git ls-files`, and it reads the WORKING tree — no unrelated dirty files), then `python scripts/spec_surface_check.py --write-baseline --spec pyforge-doctor/spec-pyforge-doctor`, then re-run the check. `chain.py` is also listed under `pyforge-marshal/spec-pyforge-marshal` in the baseline; if a `drift: fail` names that block after the doctor stamp, reconcile it the same scoped way and say so in Auto Run Result.

**Manual checks:**
- The Then/And of Story 28.1 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred: (1) mutation — temporarily restore the `split("---", 2)` body of `_frontmatter_parse`, run the fixture test, observe it fail (one deferral, no `location:`, fingerprint `fdd6bce25c09`), restore; (2) byte-identical — every pre-existing test in `tests/unit/test_sources_chain_*.py` passes unmodified except the one displaced-block fixture named in Design Notes; (3) live — `chain.gather_dreams_hygiene(repo_root)` measures 185 findings with `unparseable-frontmatter == 34`, `kinship-wikilink-dead == 31`, `readme-table-drift == 53` (vs 173 on the baseline parser; vs 255 under the known-bad opener rule); `chain.discover_spec_frontmatter_deferrals` over marshal's planning tree lists both `3bc3d91bdf95` and `5434eca8c9e5`. Record the numbers observed in Auto Run Result.

## Spec Change Log

### 2026-09-19 — Review pass 1 (bad_spec)

- **Triggering finding:** Edge Case Hunter + Verification Gap (grouped): `chain.py::_dream_body_after_frontmatter` (:1067-1072) still splits at the first `---` substring while the fixed `_frontmatter_parse` bounds the block by line-anchored fences, so a Dream the parser now accepts (a `---` quoted inside a frontmatter scalar) has its frontmatter tail scanned as Kinship body and emits a false `kinship-wikilink-dead`. The intent ("the block is bounded by line-anchored fences") covers where the body starts; the Binding's Surface named only `_frontmatter_parse` (and a phantom `_frontmatter_fields`), drawing a line the intent did not — the spec should have named the body-side reader of the same boundary.
- **Amended:** § Binding — Surface now names `_dream_body_after_frontmatter`, the real wrapper `_frontmatter`, the snapshot fixture, the dreams-hygiene tests, and the landing surface (memlog + scoped stamp). New § Design Notes — fence rule (column-0, `rstrip`), opener rule (attempt-but-unbounded → refused), body boundary, fixture snapshot, primitive test list. § Verification — adds `spec-surface-check` with the reconcile procedure and turns the manual checks into the three named measurements. Frontmatter `context:` lists the files the implementer must load; `deferred:` records the two sibling readers in other capabilities.
- **Known-bad states avoided:** (a) glued `---title:` opener returned `({}, False)` — 34 archived Dreams silently lost owner/status/title, live hygiene 173 → 255 with green tests; (b) `.strip()` fence test — an indented `  ---` inside a block scalar closed the block early and dropped later keys with `unparseable=False`; (c) live read of marshal's tracked 50.5 spec as the fixture — the same live-baseline class that blocked this story at pass 0; (d) body helper left on `split("---", 2)` — false `kinship-wikilink-dead` on parser-accepted Dreams; (e) governed files landed with no memlog movement and no scoped stamp — `spec-surface-check` red on four files (`test-ci` lane).
- **KEEP (from the reverted pass-0 implementation, `git show bcbbb32bc7:src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` and the three test files at that commit):** the `_BANNER_PREFIX` / `_BANNER_SUFFIX` module constants and `_skip_leading_banner` as a verbatim port of `pyforge.marshal.core.promotion`'s helper (unclosed `<!--` → text unchanged; `.lstrip()` after the banner), with its docstring citing Story 50.5 / `spec-pyforge-marshal:CAP-248` and the package's duplicate-don't-share convention; the line-scan shape of `_frontmatter_parse` and its extended docstring explaining the `split` defect, with the `try/except` read guard and the `None` / non-mapping / YAML-error tail byte-identical to baseline; the primitive test module's structure and names (`_write` helper, section banners, every case listed in Design Notes § Primitive tests, including `test_banner_below_the_fence_is_unaffected_pr_1460_shape` and `test_unreadable_path_is_unparseable`); the 50.5 fixture test's assertions (both locations, severities, fingerprints `3bc3d91bdf95` / `5434eca8c9e5`) and its docstring explaining the bug, now reading the snapshot; the `test_sources_chain_dream_chain.py` rename + rewrite with its docstring; the mutation-check procedure and the `fdd6bce25c09` explanation in Auto Run Result. Pass 0's full-suite result on the merged branch was 1762 passed / 1 skipped — the target after re-derivation is the same suite green plus the new tests.

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 34 findings — high 7, medium 9, low 12, false 6, maybe-false 0
- findings:
  - `[high]` `[patch]` (BH1) spec-surface baseline not re-stamped for this story's own files — verified: `pixi run --frozen -e pyforge-guild spec-surface-check` prints four `drift: fail` lines for `pyforge-doctor/spec-pyforge-doctor` (`chain.py`, two changed tests, one added test) and the doctor memlog's last line is still "Ready for decomposition"; the `test-ci` spec-surface meta-test reds. Moot this pass (bad_spec re-derives); carried into § Verification as the last landing step. Grouped with VG-O1.
  - `[medium]` `[patch]` (BH2) indented `  ---` inside a block scalar closes the block early — verified by reading `line.strip() == "---"` at the closing scan; two layers reproduced `({'title': 'x', 'evidence': ''}, False)` in-process; live scan of every Dream/spec found 0 files with the shape. Moot this pass; Design Notes § Fence rule (`rstrip`). Grouped with ECH2, IA-3c, ECH8.
  - `[low]` `[reject]` (BH3) the Always clause's `fdd6bce25c09` is the pre-fix fingerprint — true (with `location:` present `harvest_fingerprint` yields `3bc3d91bdf95`, matching the marshal ledger's `origin:` line), but the fix is to edit this build's spec (inside `<intent-contract>`) / `epics.md`; the code and test carry the correct value and Auto Run Result already records the discrepancy. Grouped with ECH6, IA-3d.
  - `[medium]` `[patch]` (BH4) the live-fixture test re-creates the MRS-GATE-001 live-baseline trap — verified: it reads marshal's tracked spec and asserts exact values another station owns; `.github/workflows/pyforge-station-tests.yml` paths filter cannot fire doctor's lane on a marshal planning edit; the same class blocked this story at pass 0. Moot this pass; Design Notes § Fixture (snapshot). Grouped with ECH5.
  - `[medium]` `[defer]` (BH5) sibling first-`---` readers known and not recorded — verified: `status_body_consistency.py:226` and `factory.py:631` still `split("---", 2)`; `chain.py:1071` too. The `chain.py` member is the bad_spec entry (ECH4/VG2); the two other-capability readers are recorded in frontmatter `deferred:` with the named blocker (Dream-first: a detector's own reader is chain work; PR #1494's memlog note is the seed). Grouped with VG3.
  - `[low]` `[reject]` (BH6) BOM / leading blank line / `--- # comment` flip from parsed-or-WARN to absent — logic verified from the code; live scan: 0 BOM files, 0 leading-blank-then-fence, 0 whitespace-before-opener across `docs/dreams/**` and every project's `planning-artifacts/**`; unlikely in everyday use and the fix adds a decode mode, whitespace rules, matrix rows and tests beyond a direct correction. Design Notes pins the rule (absent) so the verdict is deliberate. Grouped with ECH3.
  - `[low]` `[reject]` (BH7) the I/O matrix is still the single placeholder row while the test docstring claims to cover every row — true; the fix is to edit this build's spec (the matrix is inside `<intent-contract>`). Design Notes § Primitive tests carries the concrete case list outside the contract.
  - `[low]` `[reject]` (BH8) Auto Run Result headlines `Status: blocked` and never reports the byte-identical check as run — true; the section is rewritten by Finalize on the passing pass and the fix is to edit this build's spec. The byte-identical point is ECH7's claim (triaged there); Verification manual check (2) now names it.
  - `[low]` `[reject]` (BH9) the Surface names `_frontmatter_fields`, which does not exist — verified (`grep` empty; `_frontmatter` at `chain.py:200`); the fix is to edit this build's spec. The bad_spec amendment to the same Binding line names `_frontmatter` correctly. Grouped with VG-O3, IA-3g.
  - `[false]` `[reject]` (BH10) "verbatim port" overstates parity with marshal's helper — refuted: marshal's `text[end + len(_BANNER_SUFFIX) :].lstrip()` and doctor's `text[end + len(_BANNER_SUFFIX):].lstrip()` are the same slice; the difference is Black spacing. The four-readers/three-behaviours point is BH5's entry.
  - `[low]` `[patch]` (BH11) the mid-scalar test pins only the folded `>-` shape, not a single-line `title: "---"` — no defect (the reviewer verified the shape parses); one test to add. Moot this pass; Design Notes § Primitive tests lists it.
  - `[high]` `[patch]` (ECH1) `---title: …` glued opener flips 34 live Dreams from parsed to absent — verified live: 34 `docs/dreams/*.md` start with `---title:` (the 2026-09-17 fold; `0b74756679` kept them); `chain.gather_dreams_hygiene` measures 173 (baseline parser) → 255 (this diff: +34 `dream-unowned`, +34 `dream-vocab`, +34 `missing-title`, −20 `readme-table-drift`) → 185 under the refuse rule (+34 `unparseable-frontmatter`, kinship 33→31, drift 73→53). The intent settles the verdict (Approach: line-anchored fences; Never: an unbounded block stays `({}, True)`; epic: refused rather than degraded) — one reading, so not intent_gap; the fix is two lines inside the Surface — patch. Moot this pass; Design Notes § Opener rule. Grouped with ECH7, VG1, VG-O2, IA-3b.
  - `[medium]` `[patch]` (ECH2) indented `  ---` inside `evidence: |` before the real fence — same root cause as BH2 (`.strip()`); guard `rstrip() == "---"` adopted in Design Notes. Moot this pass.
  - `[low]` `[reject]` (ECH3) UTF-8 BOM or a blank line before the opener reads as absent (was WARN) — same root cause and refutation as BH6: 0 live instances; not everyday; fix beyond a direct correction.
  - `[medium]` `[bad_spec]` (ECH4) `_dream_body_after_frontmatter` (`chain.py:1067-1072`) still splits at the first `---` and skips no banner — verified by reading the code; VG reproduced a false `kinship-wikilink-dead {'link_target': 'not-a-link'}` in-process for a parser-accepted Dream; 0 live Dreams have the shape today (5 carry `[[…]]` in frontmatter, none with a mid-scalar `---`). Exposed by the change (before it the file was refused and never reached the scan). The Binding's Surface omitted this same-boundary reader while the intent covers it → bad_spec: Binding amended, Design Notes § Body boundary added, code reverted for re-derivation. Grouped with VG2.
  - `[medium]` `[patch]` (ECH5) marshal editing either 50.5 deferred item reds the doctor lane — same root cause as BH4; snapshot fixture adopted. Moot this pass.
  - `[low]` `[reject]` (ECH6, claim) the Always clause's `fdd6bce25c09` vs the test's `3bc3d91bdf95` — same as BH3: true, and the fix is a spec edit.
  - `[high]` `[patch]` (ECH7, claim) "every existing caller's fixture set yields byte-identical verdicts" does not hold on the live tree — verified: the 34-Dream shift above; the unit fixture sets do pass. Same root cause as ECH1 (opener rule). Moot this pass.
  - `[low]` `[patch]` (ECH8, claim) ` ---` with leading whitespace now parses via `.strip()` where the old reader refused it — logic verified; 0 live instances; a genuine widening against the Never clause. Same root cause as BH2 (`.strip()` on fences); under Design Notes' rules it is refused (`({}, True)`) again. Moot this pass.
  - `[high]` `[patch]` (VG1, gap — pre-verified) the `---<key>:` opener regression is observed by no test — trusted as filed (mutation run: old parser swapped in, all of `test_sources_chain_dreams_hygiene.py` still passes). Same root cause as ECH1; Design Notes mandates the parser-level `---title: x` case and the kinship live-pin re-measure, and deliberately adds no new live-count pin (docs-only repairs cannot fire the doctor lane). Moot this pass.
  - `[medium]` `[bad_spec]` (VG2, gap — pre-verified) `_dream_body_after_frontmatter` cuts at the first `---`; the kinship scan reads accepted frontmatter as body — trusted as filed (demonstration ran); same entry as ECH4; the two pinning fixtures it names are in Design Notes § Body boundary.
  - `[medium]` `[defer]` (VG3, gap — pre-verified, filed disposition defer) `status_body_consistency._parse_frontmatter` is the same first-`---`-anywhere reader over the same documents — trusted as filed; recorded in frontmatter `deferred:` with location, evidence and the named blocker. Same entry as BH5.
  - `[high]` `[patch]` (VG-O1) `spec-surface-check` red on this branch — same root cause as BH1 (verified four `drift: fail` lines; `chain.py` also sits in marshal's baseline block). Moot this pass; Verification names both blocks.
  - `[high]` `[patch]` (VG-O2) silent degradation on a malformed opener; triage should decide the verdict — decided: `({}, True)` (Design Notes § Opener rule, with the measured consequences of each alternative). Same root cause as ECH1. Moot this pass.
  - `[low]` `[reject]` (VG-O3) the Binding names `_frontmatter_fields` — same as BH9: true; spec edit.
  - `[false]` `[reject]` (IA-3a) the intent's expectations live at `deferred-work` / `deferred_work_intake.py` while the tests exercise the primitive — refuted as a defect: the auditor itself verified the outer surface live (`discover_spec_frontmatter_deferrals` → 119 with both fingerprints; the intake script reports all 119 already in the tracked ledger); the divergence is coverage depth, not a bad outcome. Verification manual check (3) now names the live measurement.
  - `[high]` `[patch]` (IA-3b) C2 does not hold — 34 glued-opener Dreams — same root cause as ECH1 (the A1/A2/A3 fork); the intent's single consistent reading is A2, recorded in Design Notes. Moot this pass.
  - `[medium]` `[patch]` (IA-3c) G1 vs G2 — `.strip()` reopens the defect class inside block scalars — same root cause as BH2; the epic's "a line that is exactly `---`" settles G1 (column-0). Moot this pass.
  - `[low]` `[reject]` (IA-3d) literal fingerprint mismatch `fdd6bce25c09` vs `3bc3d91bdf95` — same as BH3: spec edit; the intent's own text is internally inconsistent and the code follows the verified value.
  - `[false]` `[reject]` (IA-3e) C1 is not literal — one existing fixture was rewritten (B1 over B2) — refuted: the fixture is a complete block displaced below prose; the intent-contract's specific clause "no leading fence is `({}, False)`" and the epic's "the opening fence on the first line" mandate that verdict, so the rewrite is the intent applied, not a deviation. Design Notes § Opener rule names it as the one sanctioned verdict change.
  - `[false]` `[reject]` (IA-3f) F2 not F1 — the mutation check is not encoded in the suite — refuted as a defect: the spec's own Manual checks wording ("run, not inferred") permits a recorded run; Auto Run Result records it and the auditor reproduced it in-process. Verification manual check (1) keeps it a recorded run.
  - `[low]` `[reject]` (IA-3g) Surface naming: `_frontmatter_fields` is a phantom; two sibling first-`---` readers remain — the phantom is BH9 (spec edit, corrected in the amended Binding); the sibling readers are ECH4 (bad_spec) and BH5/VG3 (defer).
  - `[false]` `[reject]` (IA-3h) the banner clause is tested only on `tmp_path`; no tracked spec on `main` is banner-topped — refuted as a defect: post PR #1460 every tracked spec carries the banner BELOW the fence (marshal's `promotion.py` docstring; the diff's own `pr_1460_shape` test), so a synthetic banner-topped fixture is the only way to exercise the clause, and it holds.
  - `[false]` `[reject]` (IA-3i) diff contents not attributable to the story (`test_sources_status_body_promissory.py`, the memlog line, the baseline hashes) — refuted as a defect: they are PR #1494's merge from `main`, correctly attributed in Auto Run Result's re-route note; not reverted.

## Auto Run Result

Status: blocked
Blocking condition: implementation verification failed

**Summary of implemented change:** `_frontmatter_parse` in `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` no longer uses `text.split("---", 2)`. It now skips a leading `<!-- ... -->` provenance banner (`_skip_leading_banner`, ported from `pyforge.marshal.core.promotion`'s Story 50.5 helper), requires the opening fence to be a whole line that is exactly `---`, and scans line-by-line for the closing fence — so a `"---"` embedded mid-body (e.g. inside a quoted YAML scalar, or a markdown thematic break) can no longer truncate or fabricate a frontmatter boundary. A file with no leading fence is now `({}, False)` (absent metadata); an unbounded/unclosed fence still returns `({}, True)` (Story 17-1 / FR-144's refusal semantics preserved). `_frontmatter` and every existing caller inherit the fix with no code changes, per the Binding's "no caller changes" constraint.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — line-anchored fence parsing + banner skip, replacing the substring-split implementation.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_frontmatter_parse.py` (new) — direct unit coverage of every I/O-matrix row.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` — added a live-fixture test against marshal's real tracked `spec-50-5-the-promoter-reads-a-spec-through-its-banner.md`, confirming both deferrals now parse (fingerprints `3bc3d91bdf95`/`5434eca8c9e5` — see note below).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dream_chain.py` — updated `test_markdown_without_a_leading_frontmatter_fence_surfaces_unparseable` (renamed `..._is_absent_not_unparseable`) to assert the corrected `({}, False)` behavior for a `---` rule with no leading fence, per Story 28.1's own Always clause superseding the Story 17-1/FR-144 expectation for that exact shape.

**Note on the Always clause's fingerprint:** the intent-contract's Always clause names `fdd6bce25c09` as the first deferral's fingerprint. Cross-checked against marshal's tracked `deferred-work-ledger.md` (`origin: spec-deferred 3bc3d91bdf95 ... also read as spec-deferred fdd6bce25c09 by doctor's pre-fix _frontmatter_parse`) and `epics.md` itself: `fdd6bce25c09` is the *old, pre-fix, buggy* fingerprint produced by the truncating parser this story replaces; `3bc3d91bdf95` is the already-reconciled correct value, and is what `gather_deferred_work` requires to recognize the item as already-ingested. The implementation produces `3bc3d91bdf95`. Not treated as a bad_spec finding — flagging here for record since it's a literal mismatch against the Always clause's stated text, resolved in favor of verified ledger evidence rather than the spec's prose.

**Review findings breakdown:** not reached — blocked before step 4 (review).

**Verification performed:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`: 1761 passed, 1 skipped, **1 failed** (`test_sources_status_body_promissory.py::test_gather_live_herald_pair_and_zero_false_positives`).
- The one failure is a live-repo-content snapshot assertion in `status_body_consistency.py` (CAP-3 / Story 21.14) — a module with zero import/call relationship to `chain.py` (confirmed by grep: no reference to `chain` in `status_body_consistency.py`). It asserts `scanned_terminal` document counts and promissory-language hits measured live against the current repo tree; the test's own docstring ("Re-measured 2026-09-18 (was herald_pair_fired == 1)") and the last commit that touched it (`25e10952e9 fix(ci): refresh doctor/steward live-baseline tests after absorbed specs`) show this is a known class of live-baseline snapshot test that periodically needs its own dedicated recalibration commit as unrelated repo content drifts — it is not a regression this story's diff introduced.
- Confirmed pre-existing and diff-independent two ways: (1) the diff touches only `chain.py` and three test files under `tests/unit/test_sources_chain_*`, never `status_body_consistency.py` or its test file; (2) ran `test_sources_status_body_promissory.py` in isolation — same failure, same assertion, unaffected by test ordering.
- Mutation check: reverting `chain.py` to `baseline_revision` and rerunning the new/updated `chain`-scoped tests reproduces the pre-fix failures (marshal-50.5 fixture loses the second deferral and the first deferral's `location:`), confirming the fix is load-bearing.

**Residual risk:** none introduced by this story's change. The blocking condition is entirely pre-existing, unrelated drift in a different capability (CAP-3) outside this story's declared Surface (`chain.py::_frontmatter_parse`, "no caller changes") — fixing it here would require touching `status_body_consistency.py`/its test, which Dream-first governance does not authorize under this story's spec. Recommend routing the live-baseline recalibration as its own small maintenance item (same pattern as the prior `25e10952e9` commit), independent of CAP-81.

**Re-dispatched 2026-09-19 (this invocation):** the invocation prompt pointed directly at this spec file, whose frontmatter `status` is `blocked`. Per `bmad-build-auto` step 1's intent-check routing, a directly-supplied `blocked` spec HALTs immediately with blocking condition `blocked spec supplied` — no resumption attempted this pass.

Noted for whoever re-routes this next: the failure recorded above (`test_gather_live_herald_pair_and_zero_false_positives`, pre-existing and unrelated to this story's `chain.py` diff) has since been fixed on `main` by commit `41ec2b4c802993000bd98e5ebeb97f400e4e24cf` ("doctor: the live promissory test filters on WARN status — the clean-state OK summary is not a hit (red-main fallout after #1493)"), which landed after this branch's `baseline_revision` (`cefe85df1d`). This branch has not merged that commit yet. Merging/rebasing onto current `main` and re-running `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` is the likely path to unblock — flagged here as a lead, not asserted as verified, since this HALT did not attempt it.

**Re-routed 2026-09-19 by the operator (hand step):** the blocking test was fixed on `main` by PR #1494 (`7380ecdb41`); `origin/main` merged into this branch, `status` set back to `in-review` so the next dispatch resumes at the review step over the diff since `baseline_revision` (this story's `chain.py` change plus #1494's three files). The `blocked` verdict above was the gate's, not this story's.

**Review pass 1 (2026-09-19, this dispatch):** four review layers ran over the diff since `cefe85df`; 34 findings triaged (see Review Triage Log). One entry routed `bad_spec` (the same-module body reader outside the declared Surface), so the pass-0 code was reverted to baseline and the spec amended (Binding, Design Notes, Verification, Spec Change Log with KEEP) for re-derivation via step-03; `review_loop_iteration` is 1. The two other-capability readers are recorded in frontmatter `deferred:`. This section is rewritten by Finalize on the pass that reaches `done`.
