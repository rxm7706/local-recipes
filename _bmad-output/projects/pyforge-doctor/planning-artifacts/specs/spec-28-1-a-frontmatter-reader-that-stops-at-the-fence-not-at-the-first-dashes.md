---
title: '28.1: A frontmatter reader that stops at the fence, not at the first dashes'
type: 'fix'
created: '2026-09-19'
status: 'done'
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

- If `lines[0]` is not a fence but `lines[0].strip().startswith("---")` — e.g. `---title: …` glued on line 1, `----`, ` ---`, `--- # comment` — the document ATTEMPTED a block that cannot be bounded → `({}, True)`. This is the "refused rather than degraded" clause. **Known-bad state avoided (pass 1):** returning `({}, False)` here made 34 archived `docs/dreams/*.md` files (glued `---title:` opener from the 2026-09-17 fold, deliberately left in place by `0b74756679`) read as "no owner / no status / no title" — live `gather_dreams_hygiene` went 173 → 255 findings (+34 `dream-unowned`, +34 `dream-vocab`, +34 `missing-title`, −20 real `readme-table-drift`), a silent degradation with green tests. Under this rule the same tree measures 185: +34 `unparseable-frontmatter` (honest), `kinship-wikilink-dead` 33 → 31 (one of the 34, `enterprise-airgap.md`, carried two dead links and is now refused before the scan), `readme-table-drift` 73 → 53. Do NOT parse a glued opener leniently either (marshal's `is_valid_spec_text` does; it is a paper-trail smoke check, not this reader's contract).
- If `lines[0]` neither is a fence nor starts with `---` after stripping (plain prose, a leading blank line, a UTF-8 BOM, a prose file with a `---` thematic break lower down, a complete `---`/YAML/`---` block displaced below prose, an unclosed `<!--` banner) → `({}, False)`: absent metadata, per the Always clause "no leading fence is `({}, False)`". The displaced-block shape is the one existing fixture whose verdict changes (`test_sources_chain_dream_chain.py::test_markdown_without_a_leading_frontmatter_fence_surfaces_unparseable` → rename to `…_is_absent_not_unparseable`, expect `dream-without-spec` with `owner == "(none)"`, no `unparseable-frontmatter`); the docstring must say Story 28.1's Always clause supersedes the Story 17-1 pin for that exact shape.

### Body boundary (`_dream_body_after_frontmatter`)

- Replace its `text.split("---", 2)` with the same scan: skip the banner, `splitlines()`, if `lines[0]` is not a fence return the text unchanged (mirrors today's `startswith` guard for the no-frontmatter case — the caller only reaches it after `_frontmatter_parse` accepted the file), find the closing fence by the same `rstrip() == "---"` test, return `"\n".join(lines[close + 1:])` (with a trailing newline if the original had one; the kinship scan only regexes `[[…]]`, so exact whitespace is not load-bearing — say so in the docstring). No closing fence → `""` (unchanged).
- Prefer one private helper (e.g. `_split_fenced_block(text) -> tuple[list[str], list[str], bool] | None`) used by both functions over two copies of the scan.
- Pin with two `gather_dreams_hygiene` fixtures in `test_sources_chain_dreams_hygiene.py`, modelled on `test_kinship_wikilink_skips_frontmatter_fence`: (a) frontmatter containing a scalar that quotes `"---"` followed by `note: [[not-a-link]]` inside the fence; (b) a banner-topped Dream with a `[[not-a-link]]` inside the fence — both must produce NO `kinship-wikilink-dead`. **Known-bad state avoided:** with the parser fixed but the body helper untouched, both shapes emitted `kinship-wikilink-dead {'link_target': 'not-a-link'}` (verified in-process at pass 1).
- Re-measure `test_live_tree_kinship_wikilink_dead_count` (currently asserts 33) → 31 under the opener rule, with a docstring naming the one refused glued-opener Dream (`enterprise-airgap.md`, two dead links) as the reason and that it returns to 33 once their openers are repaired. Do not add new live-count pins (a docs-only repair PR cannot fire the doctor lane — the MRS-GATE-001 trap recorded in the memlog).

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

### 2026-09-19 — Review pass (2, after the pass-1 bad_spec re-derive)
- verdicts: 30 findings — high 0, medium 5, low 17, false 8, maybe-false 0
- findings:
  - `[low]` `[patch]` (BH1) `_skip_leading_banner` is a stale "verbatim port" — verified: `origin/main`'s marshal helper (Story 51.8 / `spec-pyforge-marshal:CAP-256`, closing DW-FU-50-6) now begins `stripped = text.lstrip("\ufeff \t\r\n")` and checks/finds the banner on `stripped`, returning `text` unchanged when no banner; 0 live BOM/blank-before-banner files. Patched: main's body ported verbatim, docstring + `_BANNER_PREFIX` comment cite spec-pyforge-marshal:CAP-256 / DW-FU-50-6, test for BOM + blank line + spaces before the banner.
  - `[low]` `[reject]` (BH2) carried — a BOM before a bare fence reads as absent; pass-1 BH6/ECH3: 0 live instances, not everyday, fix beyond a direct correction. The verdict is now pinned by VG2's test (below), so it is deliberate.
  - `[low]` `[patch]` (BH3) the column-0 fence rule is banner-dependent (`<!-- b -->\n   ---` parses; bare `   ---` is refused) — verified: the port's trailing `.lstrip()` strips indentation; 0 live bannered files; changing it would fork the port marshal parity depends on (`--> ---` / `-->  \n---` shapes). Patched by documenting the consequence in the helper's docstring and pinning it with one test. Grouped with ECH3, VG-O1.
  - `[medium]` `[defer]` (BH4) no follow-up record for the 34 glued-opener Dreams now refused live (20 `readme-table-drift` + 2 `kinship-wikilink-dead` findings hidden until repaired; two files steward-governed; the repair PR couples to the kinship live pin and cannot fire the doctor lane) — verified live; pre-existing content defect deliberately kept by `0b74756679`, outside this story's Surface and cross-station → frontmatter `deferred:` (ingested as `DW-FU-28-1-3`) naming the files, the steward stamp, and the pin coupling.
  - `[medium]` `[patch]` (BH5) `docs/detector-incident-log.md`'s Mandatory-entry rule not honoured, and the 2026-08-23 row's pinning fixture was renamed and its verdict inverted — verified (rule at lines 9-11; row at line 63 names `…_surfaces_unparseable`). Patched: a `2026-09-19` row in the existing schema (detectors, wrong claims, true values, root cause, pinning fixtures) and a superseded-note line under the 2026-08-23 row.
  - `[medium]` `[defer]` (BH6) `unparseable-frontmatter` findings carry no refusal cause and `_unparseable_frontmatter_item`'s remedy ("could not be parsed as a mapping … fix the fenced YAML block") is wrong for the glued-opener case that produces all 34 live hits — verified at `chain.py` (the `(dict, bool)` contract collapses four causes); the intent's Never clause ("do not touch callers") excludes threading a reason → frontmatter `deferred:` (ingested as `DW-FU-28-1-4`).
  - `[low]` `[patch]` (BH7) contract text unreconciled — (a) `epics.md` Story 28.1 Then / the Always clause's `fdd6bce25c09`: carried from pass-1 BH3 (`reject`, spec edit; left for the retro, noted in Auto Run Result); (b) `SPEC.md` CAP-81's success clause promises byte-identical verdicts with no caveat while the realization sanctions two verdict changes — patched with an `*(Amended 2026-09-19: …)*` parenthetical in CAP-80's existing style; nothing else in SPEC.md touched.
  - `[low]` `[reject]` (BH8) Design Notes said "two of the 34 carried dead links" / "two refused Dreams"; verified live it is one Dream (`enterprise-airgap.md`) with two dead links — the fix is to edit this build's spec; corrected in this write-back since the section is being written anyway.
  - `[low]` `[defer]` (BH9) the `.strip()` fence family in five other readers (`hygiene.py:269/272`, `sibling_dreams.py:82/85`, `status_body_consistency.py:518/520/699/702`, `board.py:433`, `chain.py:1615` `_parse_surface`) — verified by grep; 0 live docs carry an indented `  ---` inside frontmatter; other capabilities' readers and a marshal-bound contract → one class-level frontmatter `deferred:` item (ingested as `DW-FU-28-1-5`).
  - `[low]` `[patch]` (BH10) `DW-FU-28-1-2`'s `location:` was a line number (`factory.py:631`) where the convention is `path::symbol` and `harvest_fingerprint` hashes the location — verified (`_doc_pin` is the enclosing function). Patched: spec frontmatter and ledger entry read `factory.py::_doc_pin`, `origin:` fingerprint `7dd30eafde52`; intake re-run ingested the three new items; five `DW-FU-28-1*` entries, no duplicate; `deferred-work: ok`.
  - `[low]` `[reject]` (BH11) the re-derived pass recorded only one of the three Verification measurements and Auto Run Result still headlined pass 0 — true; the fix is to edit this build's spec, which Finalize does below with all three measurements.
  - `[low]` `[patch]` (BH12) docstring-stated verdicts with no pinning test (`----` opener; CRLF body normalisation; unclosed banner into the body helper) — verified missing. Patched: three tests added and the body helper's docstring now says line endings are normalised. Grouped with VG2.
  - `[low]` `[patch]` (ECH1) `"\n".join(block)` drops the trailing line break the old `parts[1]` carried, so a `|` block scalar as the LAST key loses its final newline — verified live: 12 atlas specs' `frontmatter_note` differed; appending `"\n"` makes every both-parse doc byte-identical to the old reader except the 50.5 fix target (1 of 1,800). No consumer reads `frontmatter_note`. Patched: `yaml.safe_load("\n".join(block) + "\n")` + one test.
  - `[low]` `[reject]` (ECH2) carried — BOM before a valid fence now absent (was refused); same as BH2.
  - `[low]` `[patch]` (ECH3) closed banner followed by an indented opener parses only when bannered — same root cause as BH3; documented and pinned.
  - `[low]` `[reject]` (ECH4) `splitlines()` splits on `\x0b`, `\x0c`, `\x1c`-`\x1e`, `\x85`, `\u2028`, `\u2029` and the re-join rewrites them as `\n` — logic true; no live doc carries those separators; not everyday, and swapping the split idiom changes the block/body join semantics beyond a direct correction (and diverges from every sibling reader's `splitlines()`).
  - `[low]` `[patch]` (ECH5) `gather_dream_chain` flips live from its single OK summary to 34 `unparseable-frontmatter` WARNs, unrecorded — verified (34 WARN, exit domain unchanged). Patched: the doctor memlog's CAP-81 event line now records it; no new live-count pin per Design Notes; Auto Run Result records it below.
  - `[medium]` `[defer]` (VG1, gap — pre-verified) carried — `status_body_consistency._parse_frontmatter` is the same first-`---` reader over the same Dreams; already `DW-FU-28-1`; not deferred again.
  - `[low]` `[patch]` (VG2, gap — pre-verified) the BOM-before-bare-fence verdict is pinned by no test — trusted as filed. Patched: `({}, False)` pinned in the Opener-rule section (Design Notes' chosen verdict).
  - `[low]` `[patch]` (VG-O1) the banner `.lstrip()` widens the opener behind a banner — same entry as BH3.
  - `[false]` `[reject]` (VG-O2) informational, no defect claimed: `pyforge-doctor-test` green, coverage gate OK, spec-surface clean for both stamps, `one_chain._judge` never reaches the 34 glued Dreams (all in `chain-sprawl-baseline.json`), the 34 `dream-chain` WARNs project to exit 0.
  - `[false]` `[reject]` (IA-a) carried — tests pin the primitive, not `deferred-work` / `deferred_work_intake.py`; pass-1 IA-3a: the outer surface was verified live (119 deferrals with both fingerprints; `gather_deferred_work` ok); coverage depth, not a defect. A live pin over marshal's tree would be the live-baseline class this story removed.
  - `[low]` `[reject]` (IA-b) carried — the intent's `fdd6bce25c09` is the pre-fix hash; pass-1 BH3.
  - `[false]` `[reject]` (IA-c) A5 "byte-identical verdicts" does not hold at any surface — refuted after ECH1's patch: every both-parse doc is byte-identical except the fix target; the remaining verdict changes are the intent's own clause (72 prose files → absent), the sanctioned Design Notes rule (34 refused; the displaced-block fixture), or the fix itself (the 50.5 spec's two deferrals); all recorded in the memlog, SPEC.md's CAP-81 amendment, and Auto Run Result.
  - `[false]` `[reject]` (IA-d) N1's letter holds; 72 prose files plus the leading-blank and unclosed-banner shapes move from WARN to silent-absent — refuted as a defect: the 72 are companion READMEs/satellites no source reads as metadata documents, and the two synthetic shapes are Design Notes' decided verdicts, both pinned.
  - `[false]` `[reject]` (IA-e) N3 held; `_dream_body_after_frontmatter` is a sibling reader, not a caller — descriptive; the pass-1 Binding amendment records it.
  - `[false]` `[reject]` (IA-f) carried — mutation check is a recorded run, not a suite test; pass-1 IA-3f.
  - `[false]` `[reject]` (IA-g) carried — banner-topped clause tested synthetically; no live banner-topped tracked spec exists; pass-1 IA-3h.
  - `[medium]` `[defer]` (IA-h) carried — sibling readers `DW-FU-28-1` / `DW-FU-28-1-2`; not deferred again.
  - `[false]` `[reject]` (IA-i) non-code hunks (ledger, memlogs, baseline, spec frontmatter) are landing mechanics — informational; correct.

## Auto Run Result

Status: done
Blocking condition: none

**Summary of implemented change:** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py::_frontmatter_parse` bounds the YAML block by LINE-ANCHORED fences instead of `text.split("---", 2)`: a leading `<!-- … -->` provenance banner is skipped (`_skip_leading_banner`, the verbatim port of marshal's helper as it stands on `origin/main` after Story 51.8 / spec-pyforge-marshal:CAP-256 — BOM/blank/space tolerated before the banner), the opening fence must be line 1 and the closing fence the first later line that is exactly `---` (`_is_fence`, `rstrip` so an indented `  ---` inside a block scalar stays content), and one shared scan (`_split_fenced_block`) serves both the parser and `_dream_body_after_frontmatter`, so the block the parser accepts is exactly what the Kinship scan excludes. Verdicts: an unclosed fence and an attempted-but-unbounded opener (glued `---title:`, ` ---`, `----`, `--- # c`) are refused `({}, True)` — never degraded to a silent `{}`; a prose file with a `---` thematic break, a displaced block below prose, a leading blank line / BOM, or an unclosed `<!--` is absent `({}, False)`; the `None` / non-mapping / YAML-error / read-failure tail is byte-identical to baseline, and the block is loaded with its trailing line break restored so every pre-existing both-parse document yields the identical mapping. No caller changed; the exit-code domain is untouched (the new WARNs project to 0).

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — `_BANNER_PREFIX`/`_BANNER_SUFFIX`/`_FENCE`, `_skip_leading_banner` (51.8 form), `_is_fence`, `_fenced_lines`, `_split_fenced_block`; `_frontmatter_parse` and `_dream_body_after_frontmatter` re-derived on the shared scan, with docstrings recording every verdict and the parity consequence of the banner port.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_frontmatter_parse.py` (new, 36 tests) — every Design Notes case for the primitive, the banner helper's branches, the opener rule (glued / leading-space / comment / `----` / BOM), the trailing-newline parity, CRLF, and the body boundary from the other side.
- `src/shared/packages/pyforge-doctor/tests/fixtures/chain/spec-50-5-the-promoter-reads-a-spec-through-its-banner.md` (new) — byte-verbatim snapshot (24,222 bytes, `cmp`-identical) of marshal's tracked spec as landed on `main` at `62c09c2e27`; provenance in the test docstring only.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` — `test_marshal_50_5_fixture_parses_both_deferrals` reads the snapshot: two deferrals, locations, severities, fingerprints `3bc3d91bdf95` / `5434eca8c9e5`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dream_chain.py` — displaced-block fixture renamed `…_is_absent_not_unparseable`; expects `dream-without-spec` with `owner == "(none)"` (Story 28.1's Always clause supersedes the Story 17-1 pin for that shape).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py` — two body-boundary fixtures (quoted `"---"` scalar; banner-topped) asserting no `kinship-wikilink-dead`; live pin re-measured 33 → 31 with the reason (`enterprise-airgap.md`).
- `src/shared/packages/pyforge-doctor/docs/detector-incident-log.md` — `2026-09-19` row for the wrong claims this story fixes (pinning fixtures named); the `2026-08-23` row annotated as superseded for the displaced-block shape.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md` — CAP-81 success clause gains an `*(Amended 2026-09-19: …)*` note recording the two sanctioned verdict changes.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` — CAP-81 realization event (files moved, live measurements incl. `gather_dream_chain` 1 OK → 34 WARN); scoped stamp.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` — cross-station surface-reconcile events (`chain.py` is also in marshal's block as the ported home of `spec_surface_check.py`'s verdict; `gather_spec_surface`/`_parse_surface` untouched); scoped stamp.
- `scripts/.spec-surface-baseline.json` — the doctor and marshal blocks' hashes for the files above.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md` — `DW-FU-28-1` … `DW-FU-28-1-5` ingested from this spec's `deferred:` by `scripts/deferred_work_intake.py --fix --project doctor`.
- this spec — Binding/Design Notes/Verification amended at pass 1 (bad_spec), two triage-log entries, five `deferred:` items.

**Review findings breakdown:**
- Pass 1 (34 findings over the pass-0 diff): 1 entry routed `bad_spec` (the same-module body reader `_dream_body_after_frontmatter` outside the declared Surface) — code reverted to baseline, spec amended, re-derived via step-03; 6 entries that would have been `patch` (glued-opener refusal, `rstrip` fences, fixture snapshot, spec-surface stamp, single-line quoted test) were encoded in Design Notes and delivered by the re-derive; 1 entry `defer` (sibling readers in other capabilities → `DW-FU-28-1`, `DW-FU-28-1-2`); rejected: the intent's `fdd6bce25c09` token (spec edit — the value is the pre-fix hash; the code and marshal's ledger carry `3bc3d91bdf95`), the placeholder I/O matrix row and the phantom `_frontmatter_fields` name (spec edits), the BOM / leading-blank / `--- # comment` shapes (0 live instances, fix beyond a direct correction — now pinned as deliberate verdicts), "verbatim port overstates parity" (false — Black spacing), tests-at-the-primitive / mutation-not-in-suite / banner-tested-synthetically / #1494 hunks (false — verified live, permitted by the spec's own Manual checks, no live banner-topped spec exists, correctly attributed).
- Pass 2 (30 findings over the re-derived diff): **patches applied — 8 entries (medium 1, low 7):** detector-incident-log row + superseded annotation (medium); `_skip_leading_banner` re-ported from `origin/main`'s 51.8 form with spec-pyforge-marshal:CAP-256 cited and a BOM-before-banner test; the banner-indent parity consequence documented and pinned; SPEC.md CAP-81 amendment note; `DW-FU-28-1-2` location → `factory.py::_doc_pin` + intake re-run; three docstring-verdict tests (`----`, CRLF body, unclosed banner into the body helper) + the BOM pin; `+ "\n"` trailing-newline parity (12 atlas specs restored to byte-identity); memlog line records `gather_dream_chain` 1 → 34. **Deferred — 3 new entries** (`DW-FU-28-1-3` the 34 glued-opener Dreams' repair with the steward stamp + kinship-pin coupling; `DW-FU-28-1-4` `unparseable-frontmatter` carries no refusal cause and the remedy text is wrong for the glued opener — callers are off-limits by the intent; `DW-FU-28-1-5` the `.strip()` fence family in five other readers) plus 2 carried. **Rejected:** BOM-before-bare-fence (carried low; now pinned), `splitlines()` exotic separators (no live doc; idiom change beyond a direct correction), the Design Notes "two Dreams" slip and the stale Auto Run Result (spec edits — both corrected in this write-back), the `epics.md` `fdd6bce25c09` token (carried; left for the retro), and the six descriptive/informational IA/VG rows.
- Follow-up review recommendation: **false** — pass 2 patched 0 `high` and 1 `medium` entry (first-pass rule: `true` needs a patched `high` or ≥2 patched `medium`). Patched counts by verdict: high 0, medium 1, low 7.

**Verification performed:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — **1785 passed, 1 skipped** (the pre-existing gitignored Tier-3 skip). Pass 0 was 1762 on the merged branch; pass-1 re-derive 1778; pass-2 patches 1785.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — `spec-surface: ok -- every tracked file governed or allowlisted; no drift` (read from the line; both the doctor and the marshal block were scoped-stamped after the last edit).
- `python -m pyforge.doctor.sources deferred-work` — `deferred-work: ok -- every Tier-3 deferral has a tracked twin` (five `DW-FU-28-1*` entries, no duplicate).
- Manual (1) mutation — run by the implementer and reproduced independently by the pass-2 auditor: with the `split("---", 2)` body restored, the fixture test fails (one deferral, `location == ''`, fingerprint `fdd6bce25c09`); restored, it passes. (2) byte-identical — every pre-existing `test_sources_chain_*` test passes unmodified except the displaced-block fixture and the live kinship pin (both mandated by Design Notes); measured across 1,800 tracked Dreams/specs with the old reader in-process: the ONLY both-parse document whose mapping differs is the 50.5 spec itself (the fix), 34 old-parsed documents are now refused (the glued openers), 72 prose files with a rule moved from refused to absent. (3) live — `gather_dreams_hygiene` 185 findings: `unparseable-frontmatter` 34, `kinship-wikilink-dead` 31, `readme-table-drift` 53, `dream-readme-missing` 65, `realization-log-missing` 2 (baseline parser: 173; the pass-0 absent-opener rule: 255); `gather_dream_chain`: 34 `unparseable-frontmatter` WARN (was one OK summary); `discover_spec_frontmatter_deferrals` over marshal's planning tree: 119 (was 118), `3bc3d91bdf95` and `5434eca8c9e5` present, `fdd6bce25c09` gone; `gather_deferred_work` ok either way (both were hand-promoted 2026-09-18). Coverage gate for the touched module OK (`chain.py` 94%); `test_detector_incident_log.py` green.

**Residual risks:**
- The 34 glued-opener archived Dreams are honest live WARNs until their openers are repaired (`DW-FU-28-1-3`): that docs-only PR must also re-measure `test_live_tree_kinship_wikilink_dead_count` 31 → 33 and run `pyforge-doctor-test` locally, because CI's paths filter will not fire the doctor lane on it (the MRS-GATE-001 class) — and two of the files are steward-governed (memlog + scoped stamp).
- `epics.md` Story 28.1's Then still names `fdd6bce25c09` as the with-location fingerprint (the pre-fix value); the story spec's Always clause mirrors it. Left for the Epic 28 retro (rejected twice as a spec edit); SPEC.md's own phrasing ("`fdd6bce25c09` for `3bc3d91bdf95`") is correct.
- This branch's merge-base with `main` is `7380ecdb41` (#1494); `origin/main` has moved since (marshal 51.8 among others). Landing needs a merge/rebase; the only known interaction is the banner helper, already ported from main's form.
- The sibling readers in other capabilities (`DW-FU-28-1`, `-2`, `-5`) still split at the first `---` / close on a stripped fence; the doctor renders contradictory verdicts on the same document until their own CAP lands.
- `unparseable-frontmatter` findings cannot say WHICH line to fix (`DW-FU-28-1-4`); operators reading the 34 new WARNs get the generic remedy text.
