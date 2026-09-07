---
title: 'Story 30.1: The retired-ID guard follows the 6.12 shim roster'
type: 'chore'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '9091c9fcc22368e1c25356b62422616fe8f35c12'
context:
  - '{project-root}/_bmad-output/projects/pyforge-marshal/implementation-artifacts/epic-30-context.md'
warnings: [oversized]
deferred:
  - summary: >-
      The new catalog-consistency test only checks skill_renames[].from ids, never the
      catalog's removals list, so fully-removed (never-shimmed) ids like
      bmad-check-implementation-readiness / bmad-agent-tech-writer stay permanently
      unguarded by any automated check.
    evidence: |-
      Verified real: neither id appears in RETIRED_SKILL_IDS, and
      _collect_unguarded_catalog_renames never reads the removals key. Pre-existing
      condition, not worsened by this story -- before this diff there was zero
      catalog-consistency checking of any kind, so this is a partial improvement (renames
      only), not a regression. Removals are a categorically different failure class (fully
      deleted, no forwarder) already handled via separate architecture-bmad-infra.md prose
      (the bmad-index-docs / bmad-shard-doc notes) rather than this bare-mention guard, whose
      own docstring scopes it to ids that "survive today only as a deprecated forwarder
      shim." Full removals-inclusion would also immediately require reconciling
      architecture-bmad-infra.md's existing bmad-shard-doc mention (no same-line allow
      marker today), a cascading change outside this story's declared surface.
    location: >-
      .claude/skills/conda-forge-expert/tests/meta/test_no_retired_bmad_skill_ids.py:_collect_unguarded_catalog_renames
    severity: medium
  - summary: >-
      architecture-bmad-infra.md and development-guide.md are not part of the guard's
      SCAN_GLOBS, so a future re-introduction of a bare bmad-checkpoint-preview (or any
      other retired id) in either doc is not regression-protected.
    evidence: |-
      Verified: this story's AC only asks the two docs' bare mentions to be
      renamed/glossed once, not added to the automated guard. Story 30.5 (same epic)
      already establishes the precedent of widening SCAN_GLOBS for a new surface (the
      harness template) -- extending it to arbitrary living docs is a bigger, separate
      design decision (floor-tuning, false-positive risk against normal narrative prose)
      that this story's Given/When/Then does not request.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture-bmad-infra.md
    severity: low
---

<intent-contract>

## Intent

**Problem:** BMAD-METHOD 6.12.0 renamed the shim `bmad-checkpoint-preview` to forward to
`bmad-walkthrough`, so the CAP-1 regression guard's hand-maintained `RETIRED_SKILL_IDS`
tuple (currently 20 ids) is now missing this 21st retired id, and two living planning docs
(`architecture-bmad-infra.md`, `development-guide.md`) plus two lines in `epics.md` still
carry a bare/stale mention of it.

**Approach:** Add `bmad-checkpoint-preview` to `RETIRED_SKILL_IDS` with a dated comment; add
a dated clarifying comment on the pre-existing `bmad-generate-project-context` entry noting
6.12 ships it as neither a new shim addition nor a `removals` entry (it remains a live
`lifecycle: shim` skill directory — not orphaned, correcting an earlier "delete the orphaned
directory" premise); add a new catalog-consistency meta-test that reads every
`bmad_core_releases/*.yaml` catalog and asserts each `skill_renames[].from` id is present in
`RETIRED_SKILL_IDS` (a one-directional subset check — the catalog's set of tracked renames
must never outrun the guard's coverage); rename the now-stale live mentions in the two
architecture/dev-guide doc lines to their 6.12 names; and add a same-line gloss to the two
bare `epics.md` narrative mentions.

## Boundaries & Constraints

**Always:**
- `RETIRED_SKILL_IDS` stays a hand-maintained tuple (not computed at runtime from the
  catalog) — the catalog only tracks steward's CAP-1 pre-flight renames, which is a narrower
  set than the guard's 20 pre-existing ids (e.g. the `bmad-review-*` / `bmad-editorial-review-*`
  trio and `bmad-create-story`/`bmad-dev-story` are guarded but never appeared in either
  `bmad_core_releases/6.11.0.yaml` or `6.12.0.yaml`); full derivation would silently drop
  guard coverage.
- The new catalog-consistency test only asserts the catalog's `skill_renames[].from` ids are
  a subset of `RETIRED_SKILL_IDS` — it must not assert set equality.
- Every new bare mention of `bmad-checkpoint-preview` introduced by 6.12 across the existing
  `SCAN_GLOBS` surfaces must pass the existing `test_live_tree_has_no_bare_retired_skill_ids`
  test once the id is added to the tuple.
- Live/active-skill-list mentions in `architecture-bmad-infra.md` and `development-guide.md`
  are renamed outright to the 6.12/6.11 replacement name (`bmad-walkthrough`,
  `bmad-build`); historical/narrative mentions in `epics.md` keep the recorded name and gain
  a same-line gloss word (`shim` or `retired`) — never rewritten to the new name (shipped
  planning history is not rewritten).
- `bmad-generate-project-context`'s guard-tuple comment must state plainly that 6.12 does not
  orphan its skill directory (it ships as `lifecycle: shim` under the package's `plan/` tree)
  so a future reader does not re-introduce the "delete the orphaned directory" framing this
  story corrects.

**Never:**
- Do not add a `removals`-derived list of guarded ids — `removals` entries (e.g.
  `bmad-index-docs`) are fully deleted, not shim-forwarded, and are out of this guard's scope
  (its docstring covers ids that "survive today only as a deprecated forwarder shim").
- Do not touch `SCAN_GLOB_FLOORS` — no scan surface count changed.
- Do not perform the steward `--no-shims` apply or any `_bmad/` mutation — this story is
  guard/doc code only.
- Do not re-ground `architecture-bmad-infra.md`'s `source_pin` to 6.12.0 — that is Story
  30.3's job, sequenced after steward's core-upgrade apply lands.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Planted `bmad-checkpoint-preview` | A fixture file under `tmp_path` with a bare `bmad-checkpoint-preview` mention, no allow marker | `scan_file` reports the violation (line, id) | N/A |
| Swept live tree | The repo's `SCAN_GLOBS` surfaces after this story's edits | `test_live_tree_has_no_bare_retired_skill_ids` passes (zero violations) | N/A |
| Catalog consistency, current catalogs | `bmad_core_releases/6.11.0.yaml` and `6.12.0.yaml`, each with a `skill_renames` list | Every `from` id in both files is a member of `RETIRED_SKILL_IDS` | N/A |
| Catalog consistency, a planted gap | A fixture catalog YAML with a `skill_renames[].from` id not in `RETIRED_SKILL_IDS` | The consistency test fails, naming the missing id | Test failure message names the specific missing id and source file |
| Glossed `bmad-generate-project-context` comment | The tuple's inline comment | States 6.12 ships it as neither a new shim nor a `removals` entry, and that it is not orphaned | N/A |

</intent-contract>

## Code Map

- `.claude/skills/conda-forge-expert/tests/meta/test_no_retired_bmad_skill_ids.py` — add
  `"bmad-checkpoint-preview"` to `RETIRED_SKILL_IDS` (line ~97, after
  `bmad-editorial-review-structure`) with a dated comment citing the 6.12.0 rename; add a
  dated clarifying comment beside the existing `"bmad-generate-project-context"` entry
  (line ~91); add a new `@pytest.mark.meta` test function, e.g.
  `test_catalog_renames_are_guarded`, that globs
  `REPO_ROOT / "src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/*.yaml"`,
  parses each with `yaml.safe_load` (module already used elsewhere in this test dir, e.g.
  `test_recipe_yaml_parse_audit.py`), collects every `skill_renames[].from` value, and asserts
  each is `in RETIRED_SKILL_IDS` — plus one more test using a fixture YAML under `tmp_path`
  with a planted unguarded rename id, asserting the same assertion logic reds on it (do not
  invoke the module-level function against the real catalog dir for this fixture case — build
  a small local helper or inline the same collect-and-assert loop against the fixture path).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/6.12.0.yaml`
  — read-only reference; `skill_renames` has exactly one entry
  (`bmad-checkpoint-preview` → `bmad-walkthrough`); `removals: []`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/6.11.0.yaml`
  — read-only reference; `skill_renames` has 12 entries, all already members of
  `RETIRED_SKILL_IDS`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture-bmad-infra.md` —
  line 493: rename `bmad-checkpoint-preview` → `bmad-walkthrough` in the "Process /
  facilitation" active-skill list. Lines 498–524: bump the deprecated-shim table's header
  count from "(20 — committed v7 removal list)" to "(21 — committed v7 removal list)" and add
  a new row `| \`bmad-checkpoint-preview\` | \`bmad-walkthrough\` |` (alphabetical/thematic
  placement is not load-bearing; append after the last existing row is fine).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/development-guide.md` — line 716:
  rename the live-instruction mention of `bmad-quick-dev` → `bmad-build`; line 717: rename
  `bmad-checkpoint-preview` → `bmad-walkthrough` (`"Use \`bmad-walkthrough\` to walk a
  reviewer through the diff"`).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md` — line 4529: add a
  same-line gloss word to the bare `bmad-checkpoint-preview` mention (narrative describing
  the guard's own test behavior — reword to include "shim", e.g. "a planted
  `bmad-checkpoint-preview` (the new shim)"); line 4552: add a same-line gloss word to the
  bare mention (e.g. "the retired `bmad-checkpoint-preview` reads..."). Do not alter any other
  text on these lines; do not touch line 4524 (already glossed via "shim roster" on the same
  line).

## Tasks & Acceptance

**Execution:**
- `.claude/skills/conda-forge-expert/tests/meta/test_no_retired_bmad_skill_ids.py` -- add the
  21st guarded id + dated comments + the new catalog-consistency tests -- keeps the guard's
  coverage in step with the 6.12 shim roster and answers the Spec's derive-from-catalog
  question with an enforced consistency check rather than full derivation (full derivation
  would drop pre-existing guarded ids the catalog never tracked).
- `architecture-bmad-infra.md` -- rename the active-list mention, bump the deprecated table to
  21 rows -- the doc's own factual claims about which skills are live vs. deprecated must stay
  correct now that the 6.12 rename exists.
- `development-guide.md` -- rename both stale mentions to their live 6.11/6.12 names -- live
  instruction text must never point a developer at a retiring shim id.
- `epics.md` -- add same-line glosses to the two bare narrative mentions -- keeps the swept
  live tree clean once id #21 joins the guard without rewriting the story's recorded meaning.

**Acceptance Criteria:**
- Given the `v6.12.0` shim roster, when `RETIRED_SKILL_IDS` is inspected, then it contains
  `bmad-checkpoint-preview` as its 21st entry with a dated comment, and
  `bmad-generate-project-context`'s entry carries a dated comment stating 6.12 ships it as
  neither a new shim nor a `removals` entry and that it is not orphaned.
- Given the swept live tree (post-edit), when `test_live_tree_has_no_bare_retired_skill_ids`
  runs, then it passes with zero violations.
- Given a fixture file with a planted bare `bmad-checkpoint-preview` mention, when the guard's
  scan runs against it, then it reports the violation (existing `scan_file` behavior extended
  to the new id — no new fixture test file is strictly required beyond confirming the id is in
  the tuple, but add one planted-fixture assertion for `bmad-checkpoint-preview` specifically,
  mirroring `test_planted_bare_id_is_detected`'s shape).
- Given the two `bmad_core_releases/*.yaml` catalogs on disk, when the new catalog-consistency
  test runs, then every `skill_renames[].from` id in both files is found in
  `RETIRED_SKILL_IDS`.
- Given a fixture catalog YAML with a `skill_renames[].from` id absent from
  `RETIRED_SKILL_IDS`, when the same consistency assertion logic runs against it, then it
  fails, naming the missing id.
- Given `architecture-bmad-infra.md` and `development-guide.md` after this story's edits, when
  re-read, then neither still describes `bmad-checkpoint-preview` as the live/active skill
  name in a live-instruction context.

## Spec Change Log

## Review Triage Log

### 2026-09-06 — Review pass
- verdicts: 15 findings — high 0, medium 4, low 10, false 1, maybe-false 0
- findings:
  - `[medium]` `[defer]` Blind Hunter: the new catalog-consistency test only checks `skill_renames[].from`, never the catalog's `removals` list, so fully-removed ids (`bmad-check-implementation-readiness`, `bmad-agent-tech-writer`) stay unguarded — verified true. Deferred: pre-existing condition (zero catalog-consistency existed before this story), a categorically different failure class already handled via separate architecture-doc prose, and full inclusion would cascade into reconciling `architecture-bmad-infra.md`'s existing `bmad-shard-doc` mention. Recorded in frontmatter `deferred[0]`.
  - `[medium]` `[patch]` Blind Hunter: new code comment states `bmad-generate-project-context` is "NOT orphaned," directly contradicting the still-live Story 30.1 body text in `epics.md` ("the apply must delete the orphaned 6.11 directory") two sentences above — verified true against `epics.md:4526-4528`. Fixed: rewrote the sentence to state it is NOT orphaned, matching Epic 30's own closing note (`epics.md:~4577`) and the new code comment.
  - `[low]` `[patch]` Blind Hunter: `epics.md` calls the removal record a "`removals.txt` entry," but the actual schema is a `removals:` YAML list inside the per-version catalog file, not a separate file — verified against both `bmad_core_releases/*.yaml`. Fixed in the same edit as the orphan-directory correction above.
  - `[low]` `[patch]` Blind Hunter: the "published 20-shim list" comment above `RETIRED_SKILL_IDS` was not bumped even though the tuple now holds 21 ids, while `architecture-bmad-infra.md`'s parallel heading was correctly updated in the same diff — verified true. Fixed: reworded the comment to note the 21-id total.
  - `[low]` `[reject]` Blind Hunter: `_collect_unguarded_catalog_renames` uses bare `rename["from"]` indexing, risking an opaque `KeyError` on a malformed catalog entry — verified true but rejected: catalog YAML files are hand-maintained, git-reviewed, and rarely touched; a malformed future entry still fails CI loudly with an attributable traceback (not silent), and the suggested fix (isinstance guards, custom messages) adds branches/complexity beyond a direct correction — both reject-low conditions hold.
  - `[low]` `[patch]` Blind Hunter: the extra fix to `pyforge-steward/planning-artifacts/epics.md` (closing a pre-existing bare `bmad-dev-auto`) has no memlog/Design-Notes rationale, unlike every other touched file in this diff — verified true. Fixed: added a "Extra fix disclosure" paragraph to this spec's Design Notes.
  - `[low]` `[patch]` Blind Hunter: `test_planted_checkpoint_preview_id_is_detected` duplicates coverage already provided by `test_planted_bare_id_is_detected` (the scanner is fully generic over `RETIRED_SKILL_IDS`) — verified true; smallest fix (merge fixtures, delete the redundant function) is a direct simplification, not exempt from the reject-low rule. Fixed: merged into one fixture covering both pre-existing and the new guarded id.
  - `[false]` `[reject]` Blind Hunter: `import yaml` added with no note documenting the dependency is available — refuted: PyYAML is a declared pixi dependency (`pixi.toml` `pyyaml >=6.0.3`) already imported identically in a sibling file in the same test directory (`test_recipe_yaml_parse_audit.py`); no functional risk, no named concrete harm beyond a documentation-style preference.
  - `[low]` `[reject]` Edge Case Hunter: catalog YAML invalid/malformed input yields a raw `yaml.YAMLError` instead of a clear test failure — grouped with the Blind Hunter dict-indexing finding above; same reject rationale (hand-maintained, git-reviewed catalogs; CI still fails loudly and attributably).
  - `[low]` `[reject]` Edge Case Hunter: catalog YAML top-level parsing to a non-dict raises `AttributeError` — grouped and rejected with the same finding.
  - `[low]` `[reject]` Edge Case Hunter: a malformed `skill_renames` entry missing `from` raises `KeyError`/`TypeError` — grouped and rejected with the same finding.
  - `[medium]` `[defer]` Intent Alignment Auditor: the "derive the tuple ... skill_renames + removals" clause admits a literal full-derivation reading this diff does not implement — grouped with the Blind Hunter removals-coverage finding above; same defer rationale (the register's own decomposition — authoritative per this task's conflict-resolution rule — already scopes the deliverable to a one-directional subset check, and full derivation would silently drop 8 pre-existing hand-guarded ids the catalogs never track).
  - `[low]` `[defer]` Intent Alignment Auditor: `architecture-bmad-infra.md` / `development-guide.md` are not added to `SCAN_GLOBS`, so a future bare-mention reintroduction in either doc is not regression-protected — verified true; Story 30.1's own AC asks only for a one-time rename/gloss, not durable guard coverage, and widening `SCAN_GLOBS` to arbitrary living docs is a separate, non-trivial design decision (floor-tuning, false-positive risk). Recorded in frontmatter `deferred[1]` as a future-enhancement suggestion, matching Story 30.5's own precedent of widening `SCAN_GLOBS` for a new surface.
  - `[medium]` `[patch]` Intent Alignment Auditor: the orphaned-directory sentence in Story 30.1's own `epics.md` text is not reconciled with the new "NOT orphaned" code comment — grouped with the Blind Hunter orphan-directory finding above; same fix.
  - `[low]` `[patch]` Intent Alignment Auditor: incidental scope — the `bmad-quick-dev`→`bmad-build` rename and the `pyforge-steward/epics.md` gloss are not named in Story 30.1's declared Surface line. Verified mixed: the `bmad-quick-dev` rename is refuted as undisclosed (it is explicitly named in the register's investigation, item #2, `development-guide.md:716-717`, and in this spec's own Code Map/Tasks) — no action needed there. The `pyforge-steward/epics.md` gloss lacked disclosure — real, grouped with the Blind Hunter undocumented-rationale finding above; same fix (Design Notes addition covers both).

## Design Notes

The catalog-consistency test is a **one-directional subset check** (catalog ⊆ guard tuple),
not full derivation. Rationale: `bmad_core_releases/6.11.0.yaml`'s `skill_renames` has only 12
entries, but `RETIRED_SKILL_IDS` has 20 pre-existing ids — 8 of them (the `bmad-review-*` /
`bmad-editorial-review-*` trio, `bmad-create-story`, `bmad-dev-story`) are guarded but never
appear in either catalog file, because that catalog only tracks steward's CAP-1 pre-flight
rename/legacy-halt bookkeeping, not every historical shim. A test that replaced the tuple with
the catalog's contents would silently stop guarding those 8 ids. The subset check instead
gives the guard a forward-looking safety net: the next time a catalog gains a new
`skill_renames` entry, this test reds until someone adds that id to `RETIRED_SKILL_IDS`,
without ever narrowing today's coverage.

**Extra fix disclosure (added during review):** the full meta suite reds
`test_live_tree_has_no_bare_retired_skill_ids` on a pre-existing bare `bmad-dev-auto` at
`_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md:1151` (introduced by commit
`be0a29b320c`, unrelated to this story). This story's own AC requires the swept live tree to
pass with zero violations, and `pyforge-steward/epics.md` is inside the pre-existing
`SCAN_GLOBS` include-list, so leaving it red would fail this story's stated acceptance
criterion. Closed with the identical one-word-gloss pattern used throughout this diff
(`bmad-dev-auto` -> "the retired `bmad-dev-auto`"); zero semantic change to the story text it
lives in.

## Verification

**Commands:**
- `pixi run -e local-recipes test-skill --keyword test_no_retired_bmad_skill_ids` -- expected:
  all tests in the file pass, including the new catalog-consistency tests.
- `pixi run -e local-recipes detectors-ci` -- expected: clean (or unchanged findings not
  attributable to this story's edits).

**Manual checks (if no CLI):**
- Re-read `architecture-bmad-infra.md` lines ~490-527 and `development-guide.md` lines
  ~715-718 to confirm the renames read naturally and no other bare mention was introduced.

## Auto Run Result

**Summary:** Added `bmad-checkpoint-preview` as the 21st `RETIRED_SKILL_IDS` entry (dated
comment) plus a dated clarifying comment on `bmad-generate-project-context` (6.12 ships it as
neither a new shim nor a `removals` entry, not orphaned); added a one-directional
catalog-consistency meta-test (`test_catalog_renames_are_guarded` + its fixture-based
red-on-plant counterpart) asserting every `bmad_core_releases/*.yaml` `skill_renames[].from`
id is guarded; renamed the stale live mentions in `architecture-bmad-infra.md` and
`development-guide.md` to their 6.11/6.12 names; glossed the two bare narrative mentions in
`epics.md`; closed a pre-existing unrelated bare `bmad-dev-auto` in `pyforge-steward/epics.md`
that the story's own "swept tree passes" AC required; and applied five review-pass patches
(orphan-directory contradiction + terminology fix, comment count bump, undocumented-rationale
disclosure, redundant-test merge).

**Files changed:**
- `.claude/skills/conda-forge-expert/tests/meta/test_no_retired_bmad_skill_ids.py` — 21st
  guarded id, clarifying comment, catalog-consistency tests, merged planted-fixture test,
  bumped header comment.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture-bmad-infra.md` —
  renamed active-list mention, bumped deprecated-table count to 21, added new row.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/development-guide.md` — renamed
  both stale live-instruction mentions.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md` — glossed two bare
  mentions; corrected the orphan-directory/`removals.txt` sentence.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` — glossed one
  pre-existing unrelated bare `bmad-dev-auto` mention (required by this story's own
  swept-tree AC).
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/{spec-conda-forge-expert-rebuild,spec-packaging-factory}/.memlog.md`
  — foreign spec-surface reconcile notes for the governed test file.
- `scripts/.spec-surface-baseline.json` — scoped re-stamp for the two mason specs above.

**Review findings breakdown:** 15 findings total — 5 patched (1 medium, 4 low; all applied
directly), 2 deferred (both medium/low, recorded in frontmatter `deferred`), 4 rejected as low
(one grouped entry, 4 rows: unlikely in everyday use + fix adds complexity beyond a direct
correction), 1 rejected as false (PyYAML availability claim refuted).

**Follow-up review recommendation:** `false` — 0 high-verdict patches, 1 medium-verdict patch
(below the "two or more medium" threshold for recommending a follow-up pass).

**Verification performed:**
- `pixi run -e local-recipes test-skill --keyword test_no_retired_bmad_skill_ids` — 9 passed
  (10 before the review-pass test merge; net -1 from consolidating two redundant tests).
- `pixi run -e local-recipes test-skill --meta` — 7612 passed, 3 skipped (pre-existing,
  unrelated), 0 failed.
- `pixi run -e local-recipes detectors-ci` — all 18 detectors clean except `dream-chain`
  (pre-existing, unrelated — `bmad-cursor-interactive-routing` needs its own Dream→Spec
  chain, predates this branch on `main`).
- `python3 scripts/spec_surface_check.py --write-baseline --spec pyforge-mason/spec-conda-forge-expert-rebuild --spec pyforge-mason/spec-packaging-factory`
  — scoped re-stamp after the review-pass edits, verified clean by the subsequent
  `detectors-ci` run.

**Residual risks:** none identified beyond the two deferred items (both real but
pre-existing/out-of-scope, tracked in frontmatter `deferred` for future consideration).
