---
title: "109.8: The marketplace closes Story 109.3's deferred review rows"
type: 'fix'
created: '2026-10-30'
status: 'done'
baseline_revision: '2c40d7c5f9'
review_loop_iteration: 3
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/marketplace_pages.py
  - src/shared/packages/pyforge-steward/tests/unit/test_marketplace_pages.py
  - src/shared/packages/pyforge-steward/tests/unit/test_marketplace_markdown.py
  - src/shared/packages/pyforge-herald/tests/meta/test_marketplace_mount.py
  - docs-site/src/lib/marketplace.ts
  - docs/foundry/marketplace/README.md
  - docs/foundry/marketplace/MANUAL-CHECKLIST.md
  - .github/PULL_REQUEST_TEMPLATE/marketplace-skill.md
  - docs/how-to/deploy-the-docs-site-to-github-enterprise-pages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-109-3-a-marketplace-tree-renders-a-pages-index-from-listings.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 109.3 landed with ten deferred-work rows, `DW-steward-109-3-1` to `-10`. Its loop-7 and loop-8 review
contract recorded each one instead of failing the story. None writes outside the tree, injects markup or turns a
deploy off silently, but each is something a contributor or a pilot teammate can still trip on:

1. `related` entries that are empty, padded, repeated or self-referencing pass the listing rules (`-1`).
2. An empty or non-slug directory between the skill folders, or `skills` as a regular file, passes the folder scan
   (`-2`).
3. `- - x` renders its inner marker as item text (`-3`).
4. Seventeen editorial placement items across the marketplace documents and cards (`-4`, part closed by 109.7).
5. A manifest destination that is a FIFO hangs the writer, a directory or the root raises raw, a hard link has its
   other name overwritten, and an unwritable or non-directory parent raises raw (`-5`, and `-10`'s root case).
6. `**` inside a link destination puts `<strong>` inside the `href` (`-6`).
7. Six mutants survive, two cases are tested indirectly, and TEA's four advisories stand, including a 1,578-line test
   file (`-7`).
8. Two refusals loop 6 asked for were never decided: a symlinked `index.yaml`, and a sparse overlay off dev (`-8`).
9. The loop-7 contract's readings were never confirmed, and README, the PR template and the 109.3 spec carry small text
   items (`-9`).
10. Loop 8's residue: test gaps on rows 113, 116 and 117 and the clone-URL lookahead; README's `~`/`%` sentence; a
    targeting-rule message that names a fallback that did not happen (`-10`).

**Operator rulings (2026-10-30):** both `-8` refusals stay and README says so; the loop-7 readings are written into
109.3's contract as confirmed; `test_marketplace_pages.py` is split by subject.

**Approach:** close each row as its `fix:` line lays out, with the rulings above. A fix needs no flag
(`spec-feature-flag-governance` Q1). Regenerate `site/`.

## Acceptance criteria

1. `_validate_related` refuses an entry that is empty, carries surrounding whitespace, or repeats another entry, by
   name; `_check_rows` refuses an `@<scope>/<slug>` entry naming the row's own id. One refusal case for each.
2. `_skill_folders` refuses, by name: `skills` existing as something other than a directory; a scope or slug directory
   whose name does not match `SLUG` whole; an empty scope directory. Each shape is refused through the scan and through
   `write_site_from_index`.
3. `render_markdown("- - x")` renders `<ul><li><ul><li>x</li></ul></li></ul>`, and the ordered and mixed forms nest
   the same way. Past the renderer's one nesting level a marker stays text, and the docstring says so.
4. The manifest writers refuse an existing destination that is not a regular file (a FIFO, a directory, the
   marketplace root) by name, without blocking. They write through a temporary file in the destination's directory and
   `os.replace`, so a hard link's other name keeps its bytes. An `OSError` creating the directory or writing the file
   is a `MarketplaceIndexError` naming the destination. Rewriting an existing manifest succeeds. A destination outside
   the tree, including an outside alias of an in-tree symlink, stays the caller's, and the docstring says so.
5. `_inline` substitutes links before `**strong**`. `[a](https://e.test/**b**)` keeps `**b**` literal in the `href`;
   `**[c](https://e.test/x**)` emits no `<strong>`; `**see [a](https://e.test/)**` still wraps the link in `<strong>`;
   `[**a**](https://e.test/)` keeps `<strong>` inside the link text. U+0000 renders as U+FFFD.
6. Each `-7` survivor has a case that kills it (the non-directory check widened to the last part, the `is_symlink()`
   half of `_load_yaml`'s guard, `expandtabs(8)` on the fence-item prefix, `_expand_leading` counting a tab as four
   spaces, a case-sensitive `DISABLED`, `_contained_dest`'s final resolve). The directory and absent index cases run
   through `write_site_from_index` and the manifest writers. `test_marketplace_pages.py` is split by subject, with no
   test lost. The manifest test at TEA's M3 is one subject per test, the flag-tree JSON (M2) is built by a helper, and
   the byte cap (L6) is named by its constant.
7. README § Regenerate the site says a symlinked `index.yaml` is refused and, off dev, an overlay that does not name
   the flag is refused, and says why each stays.
8. Story 109.3's § Review contract for loop 7 carries the six readings as operator-confirmed on 2026-10-30. Its other
   `-9` items land: the § Fixes (loop 6) intro, the `--basetemp` note, and the row-109 command prefixed with
   `HERALD_DOCS_SITE_REQUIRED=1`. README's layer paragraph credits `_check_rows` and `_check_folders_declared` with
   the cross-row rules, and the PR template's card-name row uses parentheses.
9. `-10`'s test gaps each have a case: the own-key and sibling-key unknown-key flag trees, the `DEPLOY_SERVER` anchor,
   IPv6 class, owner-side `.`/`..` lookahead and 64-digit commit bound, `[r](a<b.md)` and `[b](steps.md>)` under a
   relative base, and the clone-URL lookahead's `_`, `-` and `.`-digit members. README says `~` and `%` continue the
   clone URL. The flag-env refusal names a targeting rule when the flag carries one.
10. `-4`'s placement items land as the structure lens laid them out:
    - README: the release paragraph moves under § Regenerate the site; § Regenerate the site gets "What a card shows"
      and "What each layer refuses" H3s; the lede's location paragraph moves to § Provenance; the tier mapping has one
      home (the PR template); "Index schema" is renamed for what the section holds.
    - The PR template's § Listing rows sit with the rows they belong to.
    - MANUAL-CHECKLIST: § Runbooks is one line at the top naming the pilot; "the matrix" has an antecedent; the two
      plugin rows do not repeat a tail; the Epic-60 items are not checkboxes.
    - The three `SKILL.md` files lead with the unpublished state; warden `steps.md` step 2 says the not-a-verdict fact
      once.
    - The card carries its lane in the header meta line and its sources as one paragraph under Install, not a second
      list.
    - The how-to's intro names § 7's audience, and § 7 names no zip by hand.
    The `SKILL.md`/`steps.md` command copies and the install lines stay.
11. The committed `docs/foundry/marketplace/site/` matches a fresh render. `DW-steward-109-3-1` to `-10` each carry a
    `closed:` line and `status: closed`.

## Boundaries

- Do not edit the estate skills under `.claude/skills/`, `CatalogEngine.render` or `registry/estate.yaml`. Do not add a
  steward CLI duty.
- Change no listing field and nothing about what is published.
- `docs-site/src/lib/marketplace.ts` changes no behaviour; its comments may change.
- A done story's spec (109.3) changes only where `DW-steward-109-3-9` names it.

</intent-contract>

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit -q -k "marketplace or pilot"`
  — expected: exit 0.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0.
- `HERALD_DOCS_SITE_REQUIRED=1 pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_marketplace_mount.py -q --basetemp="$HOME/.cache/pyforge-preflight-tmp/herald"`
  — expected: exit 0.
- From the repository root, `env -u PYFORGE_ENVIRONMENT pixi run --frozen -e pyforge-steward python -c "from pathlib import Path; from pyforge.steward.marketplace_pages import write_plugin_manifests, write_site_from_index; r = Path('docs/foundry/marketplace'); write_site_from_index(r / 'index.yaml', r / 'site'); write_plugin_manifests(r / 'index.yaml')"`,
  then `git diff --exit-code docs/foundry/marketplace/site docs/foundry/marketplace/.claude-plugin docs/foundry/marketplace/.agents`
  — expected: exit 0.
- `pixi run --frozen --environment site docs-site-validate-links` — expected: exit 0.

**Manual checks:**

- One card reads with its lane in the header and one sources paragraph under Install.

Story 109.3's Verification still names `test_marketplace_pages.py`, which after the split holds the site, card and
committed-index tests; this story's first command (`-k "marketplace or pilot"`) runs the listing, build-line and manifest modules
beside it (review loop 1, row 9: the note stays here, not in 109.3's spec).

## Review (loop 1)

2026-10-30, independent: a fresh subagent over the staged diff against `origin/main` (`2c40d7c5f9`) and this spec.
Verdict **FAIL** on two rows. All 11 ACs met; the five Verification commands exit 0 (326, 1687 + 33, 77 passed; the
scratch re-render `diff -r` empty; links 0 issues); 26 mutants, 24 killed; 60,000 `_inline` and 40,000 list fuzz
inputs, no exception and nothing worse than `origin/main`; collected ids 251 → 309, none lost; Boundaries held.

| Row | Blocking | Location | Finding | Fix asked |
|---|---|---|---|---|
| 1 | yes | `main`, the targeting branch | With a targeting rule present every mismatch is blamed on the rule; a rule selecting `on` beside a sibling's unknown key reads off through the reader's fallback, and the message named only the rule (`origin/main` named the fallback, truly) | Name both causes; a case |
| 2 | yes | README, the clone-URL sentence | "a `.` and more" is left as written; only a `.` followed by a letter or digit is (`….git.-x` and `….git._x` are rewritten) | Say "a `.` followed by a letter or digit" |
| 3 | no | the own/sibling unknown-key cases | They stub the reader, so `where` cannot change the result | Optionally run the real reader in a subprocess |
| 4 | no | `_write_manifest` | `O_EXCL` → `O_TRUNC` and the cleanup dropped both survive | A case each |
| 5 | no | `_write_manifest` | The fixed temp name `.<name>.<pid>.tmp` left by a killed run with a reused pid refuses every later write | `tempfile.mkstemp` |
| 6 | no | `_write_manifest` docstring | A last-component symlink outside the tree is now replaced, not followed; device files are refused | Say both |
| 7 | no | `render_markdown` | `- - x\n    - deeper` flattens `deeper` into the nested list | Optionally note it |
| 8 | no | `_skill_folders` | An unreadable scope directory raises a raw `PermissionError` (as `origin/main` did) | Wrap it |
| 9 | no | 109.3's § Verification | The split note goes past what `DW-steward-109-3-9` names | Keep the pointer; move the note here |
| 10 | no | `render_markdown`, fences | U+0000 in a fence or its info string still renders raw | Replace it there too |

## Fixes (loop 1)

All ten rows landed the same day except row 3's subprocess, declined:

- Row 1: the targeting branch's refusal names both causes, the rule's variant or the reader's fallback after its
  provider refused the tree; `test_flag_env_names_a_targeting_rule_that_turns_the_flag_off` pins the text.
- Row 2: README says "a `.` followed by a letter or digit".
- Row 3, declined: the real reader pins the process-wide OpenFeature provider to a tree flagd cannot parse (the reason
  the loop-8 test stubs it) and waits 8 s for readiness on each run; the two cases now say they pin `main`'s side
  (neither shape is refused earlier under another message). The reviewer and this story's own probe ran both shapes
  through the real reader: exit 2.
- Rows 4 and 5: `_write_manifest` writes through `tempfile.mkstemp` in the destination's resolved directory (a new
  name, never followed or reused), keeps an existing destination's mode or `0o644`, and removes the temporary file when
  the move fails; `test_a_failed_move_leaves_no_temporary_file`, `test_a_stale_temporary_file_does_not_block_the_write`
  (a planted symlink keeps its target uncreated) and `test_the_manifest_keeps_an_existing_mode_and_is_0o644_when_new`.
- Row 6: the docstring says both.
- Row 7: the docstring says a deeper item joins the nested list.
- Row 8: `_entries` turns an unreadable directory into a listing error naming it;
  `test_an_unreadable_scope_directory_is_a_listing_error`.
- Row 9: 109.3's Verification keeps the pointer sentence; the split note is above.
- Row 10: `render_markdown` replaces U+0000 before it parses; `test_u0000_renders_as_ufffd_in_a_fence_and_its_info_string_too`.

## Review (loop 2)

2026-10-30, independent: a fresh subagent over the staged diff, a row verifier reading the code against the loop-1
table before § Fixes (loop 1). Verdict **PASS**. Rows 1, 2 and 4-10 closed; row 3's decline judged sound (8 s of
provider readiness per run). The five Verification commands exit 0 (334; 1688 + 33; 77 passed; the scratch re-render
`diff -r` empty; links 0 issues); ruff, format and mypy exit 0; 14 mutants, 12 killed; `marketplace_pages.py` at 94%
branch coverage under the marketplace tests. Four non-blocking rows:

| Row | Blocking | Location | Finding | Fix asked |
|---|---|---|---|---|
| 11 | no | the two fallback tests; `main`'s targeting branch | The loop-1 message contains the fallback needle, so `if enabled is not expected:` (every mismatch blamed on a rule) passes | Assert no rule is named where there is none |
| 12 | no | `_inline` | Its U+0000 replacement is unreachable (its one caller replaces first); the mutant is equivalent | Drop it or note it |
| 13 | no | this spec's Verification note | `test_marketplace_pages.py` also holds committed-index tests and a `validate_listing` tier test | Move the tier test, or fix the note |
| 14 | no | `_write_manifest` | A failing `os.fdopen` leaks the descriptor; a failing cleanup `unlink` masks the original error; the temporary name adds 14 bytes to the name | Close it; note the limit |

## Fixes (loop 2)

- Row 11: both fallback tests assert `"targeting rule" not in` the message; the mutant is killed.
- Row 12: `_inline` no longer replaces U+0000; its docstring says `render_markdown` has.
- Row 13: the tier test moved to `test_marketplace_listing.py`; the note says "site, card and committed-index tests".
- Row 14: closed by the delegation below (the primitive closes the `mkstemp` descriptor before writing and suppresses
  a failing cleanup `unlink`, so the original error is reported); the docstring names the 14-byte limit.

## Pre-push check (2026-10-30)

The full-scope `pr-preflight` refused the push: `pyforge-core`'s
`tests/meta/test_atomic_write_sole_ownership.py` found `_write_manifest` holding a second temp-file-then-`os.replace`
implementation outside `pyforge-core` (spec-pyforge-core CAP-2 and CAP-7). `_write_manifest` now keeps its refusals
and its mode rule and delegates the write to `pyforge.core.atomic_write.atomic_write_text`, handing it the destination's resolved
directory (`mkstemp` reads `..` lexically). `test_a_failed_move_leaves_no_temporary_file` fails `os.replace` inside
that one call only (the flag reader writes through the same primitive); the loop-2 `os.fdopen` test is gone with the
code it pinned.

## Review (loop 3)

2026-10-30, independent and narrow: a fresh subagent over the post-loop-2 delta (the delegation above) against AC4,
loop-1 rows 4-6 and loop-2 row 14. Verdict **PASS**. 49 in-process probes through both writers held (the refusals,
the hard link, every `OSError` path named with no temporary file left, the rewrite, the mode under umask 022 and 077,
the `link/..` index, the symlink rules, the 14-byte limit); the sole-ownership meta-test exits 0 (625); the
marketplace tests exit 0 (334) and three in-process mutants of the delegation are killed; ruff exits 0. Two
non-blocking rows:

| Row | Blocking | Location | Finding | Fix asked |
|---|---|---|---|---|
| 15 | no | the docstring, this spec, the ledger line | `pyforge.core.atomic_write_text` is not an importable name; the module is `pyforge.core.atomic_write` | Spell the module path |
| 16 | no | `test_a_stale_temporary_file_does_not_block_the_write` | The planted names use the loop-1 separator, not the primitive's `.<name>-` prefix | Plant one of the primitive's shape too |

## Fixes (loop 3)

- Row 15: the docstring and this spec name `pyforge.core.atomic_write.atomic_write_text`; the ledger line names the
  module too.
- Row 16: the test also plants a `.marketplace.json-<x>.tmp` symlink and checks its target stays uncreated.

