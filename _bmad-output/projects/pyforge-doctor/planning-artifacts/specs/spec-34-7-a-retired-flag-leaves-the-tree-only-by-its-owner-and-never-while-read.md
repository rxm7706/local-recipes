---
title: '34.7: A retired flag leaves the tree only by its owner, and never while read'
type: 'feature'
created: '2026-10-15'
status: 'done'
baseline_revision: 'b673b9b1ee50e232bddb26ca9124bc1c225375c8'
flag-exempt: detector-or-gate   # the flag gate itself; a gated gate reports a silent green (spec-feature-flag-governance Q2 and its Constraint "a flag-OFF check is never a silent green ... gates themselves are exempt"), the rule 34.2, 34.3 and 34.5 followed
review_loop_iteration: 2
followup_review_recommended: false
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-2-the-flag-gate-ships-in-scripts-outside-every-station-and-runs-in-detectors-ci.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-6-a-flag-key-shared-by-several-done-stories-is-judged-against-the-latest-one.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-42-3-the-second-host-needs-no-flag.md
  - scripts/flag_gate_check.py
  - scripts/flag_rule.py
  - scripts/flag_inventory.py
  - tests/scripts/test_flag_gate_check.py
  - tests/scripts/test_flag_inventory.py
  - tests/scripts/test_flag_rule.py
  - docs/reference/story-spec-flag-block.md
deferred:
  - summary: >-
      A flag key that no story spec's `flag:` block names can leave the tree with no `retires-flag:` declaration, so
      neither `flag-key-not-in-tree` nor the retired-read walk ever judges its removal.
    evidence: >-
      Seven live keys have no flag block in any story spec: the cutover string flag, steward's glass export and the
      five steward ledger-query keys (independent review of 34.7, should-fix 2; measured 2026-10-15 at the lane-C
      tree). The gate never reads git history, so `scripts/flag_gate_check.py` cannot tell that a key left the tree;
      it judges a removal only through a `done` spec's block or a declaration. A retrofit block does not close
      it: a story can edit a landed spec's block away (to a closed-list `flag-exempt:` value on a post-rule spec, or
      by deleting it on a pre-rule one, which only warns), then remove the key and leave a reader, and the gate
      exits 0 (the re-review's proofs B2 and B3). Only a base-ref comparison, which the gate does not make, closes
      every path. The block page tells a removal story to declare `retires-flag:` anyway, so the reader check runs.
    location: scripts/flag_gate_check.py:judge_retired_reads
    severity: medium
  - summary: >-
      The retired-read walk cannot see an environment stand-in for a flag, such as the `PYFORGE_PAGES_DUTY` variable a
      workflow reads in place of steward's pages-duty flag.
    evidence: >-
      `.github/workflows/pages.yml:122` gates two steps on `env.PYFORGE_PAGES_DUTY`, which
      `scripts/pages_artifact_download.py` (`FLAG_ENV`) exports from the flag. The variable's name does not contain
      the key, so with the key retired and the exporter removed, the workflow would keep reading the stand-in's
      default (`0`) with no finding. The walk does red the exporter while it still names the key. The block page now
      makes removing every stand-in and its exporter the retiring story's own duty; nothing enforces it. A fix would
      register each stand-in beside its key in the tree's metadata, or derive it by a naming rule the gate can check.
    location: .github/workflows/pages.yml:122
    severity: low
  - summary: >-
      A reader that builds a flag key from parts (an f-string or `+`) is invisible to the retired-read walk and to the
      orphan check.
    evidence: >-
      `key_pattern` in `scripts/flag_gate_check.py` matches only a literally spelled key. No live reader builds one
      (independent review of 34.7, nit 3). The block page now says to spell a flag key literally at its read site;
      no check enforces it.
    location: scripts/flag_gate_check.py:key_pattern
    severity: low
  - summary: >-
      A `pyforge.core.*` or `pyforge.platform.*` flag key names an owning station with no project folder, so no story
      spec can ever retire it.
    evidence: >-
      `owning_station` in `scripts/flag_gate_check.py` takes the key's prefix, and only a story spec under
      `_bmad-output/projects/pyforge-<station>/` can match it; there is no `pyforge-core` or `pyforge-platform`
      project. No live key has such a prefix (independent review of 34.7, nit 1). A fix maps these prefixes to their
      owning project (core's Spec lives under pyforge-marshal) or refuses them in the tree.
    location: scripts/flag_gate_check.py:owning_station
    severity: low
  - summary: >-
      The checked-in flag inventory reports are stale: a fresh `flag-inventory` run rewrites the marshal and steward
      reports.
    evidence: >-
      Run to a scratch `--out-dir` on 2026-10-15 at the lane-C tree: every report but marshal's (14 changed lines)
      and steward's (30) matches apart from its SHA line. Marshal's "Runtime CAPs with no flag" drops from 26 to 24
      and five CAP rows turn `unresolved`, because the CAP join reads prose in a Surface line changed outside this
      story (marshal Story 102.1, `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md:10010`) as code
      paths (the join's coverage gap is DW-doctor-34-4). This story regenerates nothing.
    location: docs/governance/flag-inventory/pyforge-marshal.md
    severity: low
  - summary: >-
      A runtime reader inside a class the retired-read walk never reads hides from `flag-retired-still-read`.
    evidence: >-
      The re-review of 34.7 (finding 1, attacks A1 to A7, each exit 0) hid a reader in: build code under
      `presentations/` (`*.mjs`, `*.js`); config held in `*.md` frontmatter; a runtime module inside a `test`-named
      folder; a workflow running a script under `tests/`; UTF-16 text, which the NUL probe takes for binary; and
      runtime config elsewhere in the planning tree. None is live (its `probe_excluded.py`). Two classes are now
      read: the values of each station's `planning-artifacts/marshal-policy.toml`, and `*.spec.*`/`*.test.*` files
      that are not JS/TS code (`_is_retired_reader_candidate` in `scripts/flag_gate_check.py`). The block page lists
      the rest in the retiring story's own checklist.
    location: scripts/flag_gate_check.py:_is_retired_reader_candidate
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the flag gate had no path for a removed flag, and the first removal opened one from the wrong side.

- **The gap.** Q4 removes a flag 90 days after it is ON everywhere; the owning station files the removal story. CAP-2's
  "a flag key that is not in the tree" check (`flag-key-not-in-tree`, Story 34.2) reds every `done` spec whose `flag:`
  block names the key, so the first removal could not pass.
- **What herald 42.3 did.** Removing `pyforge.herald.pages_second_host` (commit `7de68be07a`), it taught
  `scripts/flag_gate_check.py` a `retires-flag:` frontmatter field (`RETIRES_FIELD`): a key some story spec declares
  retired and the tree no longer holds leaves its `done` specs unjudged. `scripts/flag_inventory.py` names such a key by
  its retiring story. The judged party changed the gate (Charter section 6), with no entry on
  `spec-feature-flag-governance`.
- **The leak.** Any story spec of any station, at any status, could declare `retires-flag: <key>`, delete the key and
  silence the check while code still called `read_boolean` on it. `read_boolean` on a missing key returns its default
  with a warning, never an error, so a left-behind reader silently reads off. The independent review proved it: a
  `backlog` spec declaring the key took the gate from exit 1 to exit 0 with a reader still in `src/`.

**Approach:** keep the declaration, count it only from the owner, and red every reader left behind.

- **The block's key shape.** `scripts/flag_rule.py` refuses a `flag:` block whose key has no `pyforge.<station>.`
  prefix (the block page's `pyforge.<station>.<capability>`): the block classifies `neither`, with a reason naming
  the key. A `done` block naming a station-less key could never be retired, since no owner is known once the key
  leaves the tree. No live block names one (57 blocks checked).
- **The owner.** A key's owning station is its `pyforge.<station>.` prefix. A key with no station segment has the
  tree's `metadata.owner` (normalised: trimmed, lower case, `pyforge-` dropped) as its owner while the tree holds it.
  A story spec's station is its project folder (`station_of`). Only the owner's declaration retires the key: it lifts
  `flag-key-not-in-tree` and the two-state test for a `done` spec naming the key once the tree no longer holds it.
- **A foreign declaration** (another station's, any status) FAILs `flag-retirement-not-owner` when the key's owner is
  known, naming the spec and the key, and retires nothing. With no owner known (a key with no station segment, gone
  from the tree) the declaration retires nothing and is not judged.
- **Owner agreement.** A `pyforge.<station>.` tree flag whose normalised `metadata.owner` names another station FAILs
  `flag-owner-mismatch`: the 90-day clock names `metadata.owner` as the remover, and only the prefix station retires.
  The finding's `station` is the project form, `pyforge-<station>`, as on every spec finding.
- **A reader left behind.** Every declared key the tree no longer holds is looked for, whoever declared it (the check
  only adds FAILs). The walk (`reader_files`) reads every tracked file that can act on a flag: code, configuration,
  workflows, templates and site content, including `docsite/`, `docs-site/`, `.github/`, `pixi.toml` and `_bmad/`,
  and the values (not the comments) of each station's `planning-artifacts/marshal-policy.toml`, which dispatch runs.
  Every mention counts, comments and docstrings included. It skips prose (`*.md`), tests (`tests`/`test` folders,
  `test_*.py`, `*_test.py`, `conftest.py`, and JS/TS test code: `*.test.<js|ts…>`, `*.spec.<js|ts…>`), binary
  files, the planning and history record (`_bmad-output/`, `archive/`, `docs/dreams/`, `presentations/`,
  `.claude/memory/`), `recipes/`, the spec-surface baseline, and the tree and its overlays. The key
  counts by the gate's one boundary (`key_pattern`, shared with the two-state reader: `<key>.head` and `<key>_two` are
  other names), and a module path named like the key on an import line or in `import_module("...")` is blanked first.
  Each file that still names the key FAILs `flag-retired-still-read`, naming the file and the retiring spec (the
  owner's when there is one). Tree mode reports it once; `--spec` on a declaring spec reports it for its own keys.
- **The retiring story's own absence test.** It is a test, so the walk never reads it. Herald 42.3's
  `tests/meta/test_pages_site_url.py` names the retired key on purpose and stays green by that rule, not by a
  per-story exception.
- **Unchanged:** a retirement declared while the key is still in the tree changes nothing; the inventory's retired cell
  (owner retirements only); every other finding, the rule-date baseline, the exit codes.
- `docs/reference/story-spec-flag-block.md` documents `retires-flag:`, the key shape, the reader rule (comments
  count), and what the walk cannot see: environment stand-ins (`PYFORGE_*`) and their exporters, keys built from parts
  ("spell a flag key literally at its read site"), and readers inside a class the walk never reads.

Ledger key: `34-7-a-retired-flag-leaves-the-tree-only-by-its-owner-and-never-while-read`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- **Contract.** `spec-feature-flag-governance` CAP-2's retirement path (the orchestrator's decisions of 2026-10-15
  under the operator's ruling "Doctor story in this PR", as corrected and scoped after the independent review) and
  CAP-7 (the inventory names the retiring story). Doctor is the mechanism Smith (Epic
  34's relay); the Guild Spec's memlog enumerates the story, and Doctor mints no CAP or FR (the Epic 24/25/32
  precedent).
- **No flag.** A gate is exempt, `detector-or-gate` (Q2; Constraint "a flag-OFF check is never a silent green"): a
  gated gate reports a silent green when off. 34.2, 34.3 and 34.5 carry the same exemption.
- **Origin.** Herald Story 42.3 and the independent review of commit `7de68be07a` (its blocker and first should-fix).

## Acceptance Criteria

- Given a `done` spec of station T flagging key `pyforge.test.k`, the key gone from the tree, and a story spec of
  `pyforge-test` (any status) declaring `retires-flag: pyforge.test.k`, with no reader naming the key When the gate runs
  in tree mode Then it exits 0 with no finding, and `--spec` on either spec reads `pass`.
- Given the same tree with a tracked file that names the key and can act on a flag (under `src/`, `scripts/`,
  `docsite/`, `docs-site/`, `.github/`, `_bmad/`, `pixi.toml`, or a `docs`/`fixtures` folder of a package) When the
  gate runs Then each such file is one `flag-retired-still-read` FAIL naming the file, the key and the retiring spec.
  A comment counts; so do a non-code `*.spec.json` and a value in a station's `planning-artifacts/marshal-policy.toml`
  (or the whole file, when it does not parse). Not readers: a test file (JS/TS test code included), a `*.md`, a
  binary file, the planning and history record (a marshal policy's comments included), `recipes/`, the spec-surface
  baseline, a file naming only a longer or dotted name that starts with the key (`_two`, `.head`), and a module path
  named like the key on an import line or in `import_module("...")`. `--spec` on the retiring spec reads `red` with
  the same findings.
- Given the declaration in a story spec of another station, at `backlog` or `done` When the gate runs Then it FAILs
  `flag-retirement-not-owner` naming that spec and the key's owning station. The `done` spec is red
  `flag-key-not-in-tree` (and its two-state findings) as if no retirement existed. `--spec` on the declaring spec reads
  `red`.
- Given a foreign declaration alone, with a reader left When the gate runs Then the reader is still
  `flag-retired-still-read` (naming the foreign spec), and the `done` spec is still red `flag-key-not-in-tree`. Given
  the owner's declaration added Then the reader names the owner's spec and the `done` spec is history.
- Given an owner's or a foreign declaration on a key the tree still holds When the gate runs Then the key, its readers
  and its `done` spec are judged as before; only a foreign declaration adds `flag-retirement-not-owner`.
- Given a key with no station segment that the tree holds with `metadata.owner: " Pyforge-Test "` When `pyforge-test`
  and `pyforge-doctor` both declare it Then `pyforge-test`'s is the owner's and `pyforge-doctor`'s is
  `flag-retirement-not-owner`. Once the key leaves the tree no owner is known: no declaration is judged, none lifts
  anything, and a reader left behind is `flag-retired-still-read`; with no reader the tree is clean and `--spec` on the
  owner's spec reads `pass`.
- Given a `pyforge.<station>.` tree flag whose normalised `metadata.owner` is another station When the gate runs in
  tree mode Then it FAILs `flag-owner-mismatch` naming the key and both stations, with `station: pyforge-test`; `test`,
  `pyforge-test` and ` Test ` all agree with the prefix `test`.
- Given a `flag:` block whose key has no `pyforge.<station>.` prefix (`pyforge.cutover_root`, `pyforge.herald.`,
  `pyforge..x`, `other.herald.x`, `solo`) When `scripts/flag_rule.py` classifies it Then it is `neither`, with one
  reason naming the key; a `done` post-rule spec carrying one is `flag-missing`.
- Given the inventory When a foreign station declares the retirement Then the row reads `none (key <key> not in
  tree)`. When the owner declares it Then the row reads `none (retired by <story>)` (Story 42.3's case, unchanged).
- Given the live tree (herald 42.3 retires `pyforge.herald.pages_second_host`; no reader names it) When `pixi run -e
  pyforge-guild flag-gate-check` runs Then it exits 0, and `flag-inventory` writes the herald report unchanged but for
  its SHA line.

## Boundaries & Constraints

**Always:**
- The block key's shape is checked where the block is read: `_classify_block` in `scripts/flag_rule.py`.
- Fix it where the behaviour lives: `scripts/flag_gate_check.py` (`normalise_owner`, `prefix_station`,
  `owning_station`, `declared_by_owner`, `retirement_declarations`, `judge_retirements`, `key_pattern`,
  `_is_retired_reader_candidate`, `reader_files`, `judge_retired_reads`, the owner check in `judge_tree_metadata`,
  wired into `judge_one`, `judge_tree` and `run_spec`). `scripts/flag_inventory.py` changes only its `flag_cell`
  docstring: its retired map is the gate's.
- The retired-read walk has its own reach, wider than the orphan check's `READER_ROOTS` (`src/`, `scripts/`): a root
  the orphan check skips can only cause a false red there, while here it would be a silent green. It shares
  `_list_files` and the gate's one key boundary (`key_pattern`, which `_names_key` now uses too). The orphan check is
  unchanged.
- Keep the gate naming no live flag key (`test_the_gate_holds_no_copy_of_the_exemption_list_and_names_no_live_key`).
- Add `retires-flag:` to `docs/reference/story-spec-flag-block.md`, with a third YAML example (a retiring story).
  `tests/scripts/test_flag_rule.py` checks that every example on that page classifies as written, so it
  learns the third.
- Regenerate doctor's `planning-artifacts/test-architecture.md`
  (`python _bmad/scripts/bmad_tea_playwright.py --project pyforge-doctor`) so its Story Coverage Matrix names 34.7:
  `tea-playwright-check` reds an epic story id the matrix lacks.

**Never:**
- Never import a `pyforge.<station>` module into the gate (Charter section 6, the Story 34.2 meta-test).
- Never edit herald 42.3's `retires-flag:` line, `flags.json`, `flag-overlays.json` or the rule-date baseline.
- Never read git history to find an owner: a fixture tree without git judges the same way.
- Never weaken an existing test. Herald 42.3's two gate tests move their retiring spec into the owning station's folder
  and keep every assertion.

## I/O & Edge-Case Matrix

| Declaration of `retires-flag: K` | K in the tree | Reader naming K | Findings |
|---|---|---|---|
| owner, any status | no | none | none; a `done` spec naming K is history |
| owner | no | `src/pkg/host.py`, `scripts/export_host.py` | `flag-retired-still-read` per file |
| owner | no | one of `docsite/tools/k.py`, `docsite/content/site.yml`, `.github/workflows/pages.yml`, `pixi.toml`, `docs-site/src/lib/flags.ts`, `_bmad/custom/*.toml`, `src/pkg/docs/k.py`, `src/pkg/fixtures/k.py` | `flag-retired-still-read` on that file |
| owner | no | only tests, `*.md`, binaries, `_bmad-output/`, `archive/`, `docs/dreams/`, `presentations/`, `.claude/memory/`, `recipes/`, the spec-surface baseline, `K_two`, `K.head`, or `from K import` / `import K` / `import_module('K')` | none |
| another station, `backlog` or `done` | no | none | `flag-retirement-not-owner` on that spec; the `done` spec: `flag-key-not-in-tree` and its two-state findings |
| another station | no | `src/pkg/host.py` | the above, plus `flag-retired-still-read` naming the foreign spec |
| another station plus the owner | no | `src/pkg/host.py` | `flag-retired-still-read` (naming the owner's spec) and `flag-retirement-not-owner` |
| owner | yes | yes | as before |
| another station | yes | yes | as before, plus `flag-retirement-not-owner` |
| none | no | — | `flag-key-not-in-tree` (as before) |
| owner by tree `metadata.owner` (no station segment) | yes | yes | none; another station's declaration: `flag-retirement-not-owner` |
| any (no station segment) | no | `src/pkg/reader.py` | `flag-retired-still-read`; no declaration judged |
| any (no station segment) | no | none | none |
| — (tree flag `pyforge.test.k`, `metadata.owner: steward`) | yes | — | `flag-owner-mismatch`, `station: pyforge-test` |
| owner | no | `# K was retired here` in `src/pkg/host.py` | `flag-retired-still-read` (a comment counts) |
| owner | no | a value in a station's `marshal-policy.toml`; or `docs-site/src/data/board.spec.json` | `flag-retired-still-read` |
| owner | no | only a comment in a `marshal-policy.toml`; or `board.test.jsx` | none |
| — (a `done` block whose key is `pyforge.solo`) | — | — | `flag-missing` (no `pyforge.<station>.` prefix) |

A key with no station segment (the estate's cutover string flag is the one live case) has a known owner only while
the tree holds it. Its removal story's declaration is not red once the key is gone, and the reader check still runs.
No `flag:` block may name such a key: `scripts/flag_rule.py` refuses one, since the block's key is
`pyforge.<station>.<capability>` (CAP-1). So none needs a retirement to clear `flag-key-not-in-tree`.

</intent-contract>

## Binding

- Dream: `docs/dreams/feature-flag-governance.md` § *Realization log*, the 2026-10-15 entry (the retirement leg).
- Guild Spec: `docs/governance/spec-feature-flag-governance/` — memlog decision 2026-10-15 (CAP-2 amended), the
  story-mint event (CAP-2 -> doctor 34.7), the surface-comment note, and the two self-validate events; then, after the
  independent review, an attribution correction (the contract is the orchestrator's, under the operator's ruling), a
  scoping note, the review-resolution decision, and a second render with pass 1 and a corrected pass 2; then, after
  the re-review, the nits decision and a third render with both passes. `SPEC.md` is re-derived three times by
  anchor-asserting scripts (operator-approved 2026-10-15).
- Epic: Epic 34. A new story reopens its done epic (Story 41.5's rule; the 34.6 precedent), so `epic-34` reads
  `in-progress`.
- Ledger key: `34-7-a-retired-flag-leaves-the-tree-only-by-its-owner-and-never-while-read`, minted `backlog` in the
  same commit as the epics heading.
- Deps: —. Lands with herald 42.3 in the one-PR Pages redesign (operator ruling 2026-10-15).
- Surface: Epic 34's `[epic_surfaces]` (doctor `marshal-policy.toml`) already admits both scripts, both test files, the
  block page and the Guild Spec's memlog; its comment now names 34.6 and 34.7.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_flag_gate_check.py tests/scripts/test_flag_inventory.py tests/scripts/test_flag_rule.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the Detectors scripts-suite lane).
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0 on the landing tree.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Test files:** `tests/scripts/test_flag_gate_check.py` (the owner's retirement passes; a reader left fails per file,
with the `.head` case; a reader anywhere that can act on a flag is found; the record, prose, tests and import lines
are not readers; a binary file is never read; the shared key boundary; a foreign declaration fails and retires
nothing; a foreign declaration's key is still read for; a key still in the tree; a key with no station segment;
owner mismatch and normalisation), `tests/scripts/test_flag_inventory.py` (a foreign retirement reads "not in tree"; the owner's reads
"retired by") and `tests/scripts/test_flag_rule.py` (the block page's three examples classify as written).

**Mutations (each restored afterwards):** count every declaration, not only the owner's; drop `judge_retired_reads`
from `judge_tree`; match the key as a bare substring; drop `judge_retirements` from `judge_one`; walk only
`READER_ROOTS`; skip the import-line blanking; drop the owner-mismatch check; read only owner-retired keys; read a
marshal policy whole instead of its values; take every `*.spec.*`/`*.test.*` for a test; report the mismatch
station bare; drop the block key's prefix check. Each fails at least one of the tests above.

## Named, not fixed here

Each has a `deferred:` entry above, promoted to doctor's `deferred-work-ledger.md` by
`scripts/deferred_work_intake.py --fix --project doctor`.

- **A key no `done` spec's block names** can leave the tree with no declaration (seven live keys). The gate reads no
  git history, so only a declaration or a block brings the removal into view. A retrofit block does not close it: a
  story can edit a landed block away (to a closed-list `flag-exempt:` on a post-rule spec, or by deleting it on a
  pre-rule one), then remove the key and leave a reader. Only a base-ref comparison closes every path.
- **Environment stand-ins** (`PYFORGE_*`, such as the pages-duty variable `.github/workflows/pages.yml` reads) do not
  contain the key. The walk reds their exporter while it names the key, but not the stand-in read itself.
- **Keys built from parts** (f-strings, `+`) are invisible to any whole-key match. The block page asks for the key to
  be spelled literally.
- **`pyforge.core.*` / `pyforge.platform.*` keys** name a station with no project folder, so no story can retire one.
  No live key has such a prefix.
- **The flag inventory reports are stale on this branch.** A fresh `flag-inventory` run rewrites the marshal and
  steward reports, from Surface-line prose changed outside this story. Every other report differs only by its SHA
  line. This story regenerates nothing.
- **A runtime reader inside a class the walk never reads** hides: build code under `presentations/`, config in
  `*.md` frontmatter, a runtime module in a `test`-named folder, a workflow running a script under `tests/`, UTF-16
  text, and runtime config elsewhere in the planning tree. None is live. The block page lists them in the retiring
  story's own checklist.

## Spec Change Log

- 2026-10-15: minted and built in one change on the one-PR Pages redesign branch (lane C), after the independent review
  of herald 42.3 + steward 102.5 found the gate change ungoverned (blocker) and the leak (should-fix). Chain: Dream
  entry, Guild memlog decision and events, `SPEC.md` re-derived by script, epics Story 34.7, ledger row, this spec.
- 2026-10-15, iteration 1 (the independent review of `aac6036047`: FAIL, five should-fix, no blocker). Resolved after
  lane B was merged in (`9bd2422a0d`, which brought `test_pages_site_url.py`):
  - **The walk's reach (should-fix 1).** AC2, the matrix and the "Always" bullet that said "reuse the reader walk the
    orphan check uses" are amended: the retired-read walk reads every tracked file that can act on a flag, minus a
    named non-reader list. The block page names the `PYFORGE_*` stand-ins and their exporters as readers to remove.
  - **SPEC.md overclaimed (should-fix 2).** The smaller honest change: the claims are scoped (a key a `done` spec's
    block names; readers the gate can see; `metadata.owner` while the tree holds the key), through a memlog note, a
    second script render and a corrected pass 2.
  - **Keys with no station segment (should-fix 3).** The reader check runs for every declared key gone from the tree,
    whoever declared it; the lift stays the owner's; `flag-retirement-not-owner` needs a known, different owner.
    AC6, the matrix and the two named tests are updated.
  - **The key boundary (should-fix 4).** `key_pattern` is the gate's one boundary, `_names_key` included; `.head` is
    tested.
  - **Residuals (should-fix 5).** Five named, each with a `deferred:` entry.
  - **Nits.** `metadata.owner` is normalised and `flag-owner-mismatch` added (fixture owners now follow the key); a
    module path on an import line or in `import_module(...)` is blanked; the block page says to spell a key literally;
    the memlog's operator attribution is corrected by a new entry; the stray blank line in the doctor policy's `"34"`
    array is gone; the Build Record names the worktree-local Tier-3 feed.
  - **The retiring story's absence test (iteration 1).** The rule chosen: tests are never readers (any `tests`/`test` folder,
    `test_*.py`, `*_test.py`, `*.test.*`, `*.spec.*`, `conftest.py`), so herald 42.3's `test_pages_site_url.py`, which
    names the retired key on purpose, needs no per-story exception. A file a declaration's spec names is not excluded
    by name: a list in the spec would let a story exempt a real reader.
- 2026-10-15, iteration 2 (the re-review of `6b246ac938`: RESOLVED, six nits). All six swept:
  - **Never-reader classes.** Named on the block page's checklist and as a sixth `deferred:` entry
    (`DW-doctor-34-7-6`). Two were cheap to close: JS/TS test code is a test only with a code extension, so a
    `*.spec.json` is read; and each station's `planning-artifacts/marshal-policy.toml` is read for its values, not
    its comments (herald's policy has a comment naming the retired key, and a comment there is planning record).
  - **The block key's shape.** `scripts/flag_rule.py` now refuses a block key with no `pyforge.<station>.` prefix,
    instead of deferring it; 57 live blocks checked, none affected.
  - **`DW-doctor-34-7`'s evidence** names the edit-the-landed-block-away path (proofs B2, B3).
  - **Comments count.** The block page and this spec move comments from "cannot see" to "no reader may stay".
  - **SPEC.md** drops "The retiring story removes those by hand." through a memlog decision and a third script render
    with both passes logged; CAP-1 names the key's shape.
  - **`flag-owner-mismatch`'s `station`** is `pyforge-<station>`; the test asserts it.
  - **Deferral locations** cite symbols (`scripts/flag_gate_check.py:judge_retired_reads` and the like), not line
    numbers, which this change moved. Their ledger rows' `location:` and `origin:` fingerprints moved with them, and
    `DW-doctor-34-7` carries the new evidence.

## Build Record

Built 2026-10-15 in the lane-C worktree of the one-PR Pages redesign, from `b673b9b1ee`. Every verdict is an exit code.

- `pytest tests/scripts/test_flag_gate_check.py tests/scripts/test_flag_inventory.py tests/scripts/test_flag_rule.py`
  (pyforge-guild): 311 passed, exit 0.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test`: 1579 passed, 28 skipped, exit 0. Its first run went
  red on two things this story caused: the block page's third YAML example (`test_flag_rule.py`) and the TEA matrix
  missing 34.7 (`test_tea_playwright_check.py`). Both were fixed here.
- `pixi run --frozen -e pyforge-guild flag-gate-check`: exit 0, 1479 specs, 0 fail. `--spec` on this spec and on
  herald 42.3 reads `pass`.
- Live probe: a line naming `pyforge.herald.pages_second_host` appended to a tracked herald module made the gate exit 1
  with one `flag-retired-still-read` naming that file. The file was restored byte for byte.
- Mutations: count every declaration; drop `judge_retired_reads`; match a bare substring; drop `judge_retirements`.
  Each failed 1-4 of the new tests. All were restored.
- `lint-types`, `chain-completeness-check`, `dream-chain-check`, `dreams-hygiene-check`, `deferred-work-check`,
  `ledger-regression-check`, `story-status-check`, `chain-currency-sweep-check`, `tea-playwright-check` and
  `docs-site-validate` (site) all exit 0. Working-tree ledger durability (`MARSHAL_DURABILITY`) reads OK: `epic-34`'s
  reopen is excused by the new not-done 34.7 key.
- `pyforge-doctor`'s `tests/meta/test_flag_gate_stays_outside_every_station.py`: exit 0.
- Tier-3 feed: no worktree of this PR carries an `implementation-artifacts/` link to the primary checkout. The ledger
  row was synced from a worktree-local, gitignored `_bmad-output/projects/pyforge-doctor/implementation-artifacts/
  sprint-status.yaml` (`.gitignore:12`), seeded from the tracked twin plus the 34-7 key, never from the shared
  primary store. The first sync on the primary after the merge restores the key from the twin.

### Iteration 1 (the independent review), 2026-10-15

After `git merge --no-edit pages-redesign-lane-b-2026-10-15` (fast-forward to `9bd2422a0d`). Every verdict is an exit
code.

- The three flag test files (pyforge-guild): 338 passed, exit 0.
- Mutations: count every declaration; drop `judge_retired_reads`; bare substring; drop `judge_retirements`; walk only
  `READER_ROOTS`; skip the import-line blanking; drop the owner check; read only owner-retired keys. Each failed
  1-11 tests (2, 11, 7, 4, 6, 1, 1, 2). All were restored byte for byte.
- `flag-gate-check` on the live tree: exit 0, 1479 specs, 0 fail; `--spec` on this spec and on herald 42.3 reads `pass`. The wide walk finds no reader of `pyforge.herald.pages_second_host`;
  the absence test `test_pages_site_url.py` is a test. Every one of the tree's keys has a reader the wide walk sees, and
  one retired key costs the walk about 0.2 s.
- Live probe: `flag: pyforge.herald.pages_second_host` appended to `docsite/content/site.yml` and a
  `read_boolean(...)` comment line appended to `.github/workflows/pages.yml` made the gate exit 1 with one
  `flag-retired-still-read` per file. Both files were restored byte for byte.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test`: 1606 passed, 28 skipped, exit 0.
- `scripts/deferred_work_intake.py --fix --project doctor`: exit 0, five rows ingested (`DW-doctor-34-7` to
  `DW-doctor-34-7-5`).
- `lint-types`, `chain-completeness-check`, `story-status-check`, `deferred-work-check`, `ledger-regression-check`,
  `chain-currency-sweep-check`, `dream-chain-check`, `dreams-hygiene-check`, `tea-playwright-check` and
  `docs-site-validate` (site) all exit 0.

### Iteration 2 (the re-review nits), 2026-10-15

From `6b246ac938`. Every verdict is an exit code.

- The three flag test files (pyforge-guild): 350 passed, exit 0.
- Mutations: the eight of iteration 1 plus four new ones (a marshal policy read whole; every `*.spec.*`/`*.test.*`
  a test; the mismatch station bare; no block key prefix check). Each failed 1-15 tests (2, 15, 7, 4, 9, 1, 1, 2, 2, 1, 1, 6). All
  were restored byte for byte.
- `flag-gate-check` on the live tree: exit 0, 1479 specs, 0 fail; `--spec` on this spec and on herald 42.3 reads `pass`. Herald's
  `marshal-policy.toml` comment naming the retired key is not read; a probe value naming it in the same file made
  the gate exit 1 with one `flag-retired-still-read` (restored byte for byte).
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test`: 1618 passed, 28 skipped, exit 0.
- `scripts/deferred_work_intake.py --fix --project doctor`: exit 0, `DW-doctor-34-7-6` ingested. The three rows whose
  locations moved from line numbers to symbols carry their new `location:` and `origin:` fingerprints.
- A scratch `flag-inventory` run: every report as before (marshal 14, steward 30 changed lines, the rest only the SHA
  line), so the block-key rule moves no live classification.
- `lint-types`, `chain-completeness-check`, `story-status-check`, `deferred-work-check`, `ledger-regression-check`,
  `chain-currency-sweep-check`, `dream-chain-check`, `dreams-hygiene-check`, `tea-playwright-check` and
  `docs-site-validate` (site) all exit 0.
