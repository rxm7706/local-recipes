---
title: 'The failed-story safety net is reported'
type: 'feature'
created: '2026-08-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
baseline_revision: '8410edba56'
final_revision: 'b5a90a0399'
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** A session-timeout kill preserves a killed story's unlanded work at
`<run>/failed/<story>/changes.patch`, and nothing in the repo reads that path. Measured
2026-08-09: 7 patches, 26 KB-205 KB, across five stations -- all belonging to stories that
later reached `done`, discoverable only by luck.

**Approach:** Extend `marshal status`'s existing durability dimension (Story 5.5/AD-48's
`unpushed_work` family) with a second signal: for every loop home in the sweep, glob its
`.bmad-loop/runs/*/failed/*/changes.patch` files, classify each by whether its story has since
landed (`core.promotion.merged_story_keys` against `main`'s durable merge history -- AD-33, git
is sole authority), and fold the result onto that home's row. A landed patch is informational
("spent"); an unlanded one raises a WARN.

## Boundaries & Constraints

**Always:** Every `.bmad-loop/runs/*/failed/*/changes.patch` under any currently-attached
`loop/<slug>` worktree (the same enumeration `marshal status` already performs) is reported on
that home's own row, keyed by a best-effort dot-form story key (`core.identity.normalize` +
`render_feed_key` on the patch's own directory name, falling back to the raw slug on
`MalformedStoryKeyError`), size in bytes, and a `done` tri-state (`true`/`false`/`null` for
"landed evidence unavailable this run"). "Landed" means the story key is present in
`core.promotion.merged_story_keys`'s result for `main` -- never the harness's own
`state.json`/journal (a killed run's journal never shows `done`, even after the story lands via
a LATER successful run). A patch whose story is not landed, or whose landed-status could not be
determined, raises exactly one WARN naming it. No failed patches anywhere yields
`failed_patches: []` on every row and zero new findings.

**Never:** Never treats harness journal/state as "done" evidence -- git's durable merge history
only (AD-33). Never re-derives a second merge-subject-classification mechanism -- reuses
`core.promotion.merged_story_keys` exactly as `_reconcile_ledger`/`cli/deploy.py`/`cli/land.py`
already do. Never adds a new `FsPort` directory-listing primitive for this one read-only caller
-- bare `Path.glob`, mirroring `cli/spin.py::_latest_run_dir`'s own documented precedent. Never
blocks or changes `marshal status`'s exit code over a failed-patch finding -- WARN tier only,
same as `unpushed_work`'s sibling findings. Never scans a home that isn't a `loop/<slug>`
worktree in this sweep.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No failed patches anywhere | fleet of N homes, none carry a `failed/*/changes.patch` | every row's `failed_patches == []`; no new finding | none |
| Patch whose story has landed | `failed/4-13-.../changes.patch` exists; `main`'s commit subjects include a conforming merge for `4.13` | entry reports `done: true`; no finding for that entry | none |
| Patch whose story has not landed | patch exists; no conforming merge subject on `main` for that key | entry reports `done: false`; one `MRS-STATUS-010` WARN naming the story, path, and size | none |
| `main`'s commit history unreadable | `vcs.commit_subjects(root, "main")` raises, and >=1 patch exists anywhere in the fleet | every found patch reports `done: null`; ONE `MRS-STATUS-011` WARN for the whole sweep, read attempted at most once | none |
| Patch's story-dir name doesn't parse as a story key | `failed/not-a-story-name/changes.patch` | `story_key` reports the raw dir name; `done: false` (cannot be proven landed) with the same WARN as an unlanded patch | none |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py` -- add
  `failed_patches: tuple[dict[str, object], ...] = ()` to `FleetHomeFacts` (mirrors
  `unpushed_work`'s dataclass shape); include `"failed_patches": facts.failed_patches` in all
  three `build_fleet_row` row shapes (`journal_unreadable`, `has_run=False`, and the full row) --
  an independent filesystem signal that must never be hardcoded `None`/omitted in a degraded row,
  the same rationale the file's own docstring already gives for `unpushed_work`.
  **Each entry carries `confidence`, reusing this SAME module's existing
  `CONFIDENCE_CONFIRMED`/`CONFIDENCE_UNCONFIRMED` constants** -- never new ones. `done: true` is
  `confirmed` (a positive `merged_story_keys` match is proof); `done: false` is ALWAYS
  `unconfirmed`; `done: null` carries no confidence key value other than `unconfirmed`. This is
  not a new convention: Story 5.4's own `reconcile_ledger_vs_git` already tags the identical
  evidence source this way, mandated by the 2026-08-07 code review recorded in that constant's
  own comment block and enforced as a `required` field in `schemas/status.json`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` -- new
  `_gather_failed_patches(home: Path) -> tuple[Path, ...]` (bare `home.glob(".bmad-loop/runs/*/failed/*/changes.patch")`,
  no `FsPort` involved, mirrors `_latest_run_dir`'s precedent). **Filter to `p.is_file()` INSIDE
  this helper**, before any caller sees the tuple, so a directory literally named `changes.patch`
  (`Path.glob` does not distinguish file kind, and `.stat()` on a directory succeeds rather than
  raising) never opens the `if patch_paths:` gate -- otherwise it pays for the git read and can
  emit an orphaned `MRS-STATUS-011` while every row still reports `failed_patches: []`.
  New `_MRS_STATUS_010`/`_MRS_STATUS_011` constants; wire into `run_status`'s existing per-home
  loop (~line 784): for each home, glob its patches; if any exist, lazily resolve `main`'s commit
  subjects ONCE for the whole sweep (cached; on failure, emit `_MRS_STATUS_011` at most once and
  every subsequent patch reports `done: null`) and that home's own `merged_keys` via
  `_merged_keys_for_slug` -- the ONE shared policy-read-then-`promotion.merged_story_keys`
  sequence, pure (`-> tuple[frozenset[str], tuple[Finding, ...]]`, no `findings` out-param),
  called by BOTH this fold and `_reconcile_ledger`, never two copies. An ERROR-severity finding
  returned for a slug degrades THAT slug's patches to `done: null` + one `_MRS_STATUS_011` WARN
  rather than reaching `findings` (a raw `MRS-POLICY-004` would flip this command's exit code to
  4, violating the intent contract's WARN-only Boundary). Build each patch's row dict
  (`story_key`, `run_id`, `path`, `size_bytes`, `done`, `confidence`); skip a `size_bytes == 0`
  patch entirely (a kill before any diff was written preserved nothing to recover, so warning
  about it directs an operator at an empty file); `replace(facts, failed_patches=...)` before
  calling `build_fleet_row`; after building the row, emit one `_MRS_STATUS_010` WARN per
  `done is False` entry (mirrors the `unpushed_work` block immediately below it).
  **`_MRS_STATUS_010`'s message must NOT assert "has not landed" as established fact.** It states
  the unconfirmed direction and names `run_id` alongside `story_key`/`path`/`size_bytes` (repeat
  failed attempts at one story across runs are otherwise distinguishable only by a long absolute
  path -- live: `pyforge-steward` carries three run dirs). Do NOT reorder `_reconcile_ledger`'s
  policy read to after its `git log` read: a `git log` failure would then return before
  `_merged_keys_for_slug` is ever called, silently dropping the `MRS-POLICY-004` diagnostic that
  pre-existing shipped view reports today. Also correct the now-false claim in
  `--reconcile-ledger`'s own docs that its `git log`-scale walk over `main` is "never folded into
  the default view" -- this story folds it in, and the "most homes carry no failed patches"
  laziness rationale is measurably wrong (7 of 8 live homes carry patches); keep the caching
  (it is still correct to read once) but state the real reason.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` /
  `core/verdict.py` -- register `MRS-STATUS-010` (a failed-story patch has no confirming durable
  merge) and `MRS-STATUS-011` (landed-status could not be determined while classifying
  failed-story patches) in `REGISTERED_CODES` / `_CLASSIFY_TABLE`, both `Verdict.WARN` -- same
  tier as `MRS-STATUS-008`/`009`. **`MRS-STATUS-011` carries TWO causes, and all three doc sites
  (`cli/status.py`, `core/findings.py`, `core/verdict.py`) must describe both**: an unreadable
  `main` (once per sweep) AND a per-slug policy-resolution ERROR (once per affected home, so the
  "at most ONCE for the whole sweep" phrasing is wrong for that arm). The per-slug message says
  "this project's patches", never "every patch found this sweep".
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` (`_render_text_status`)
  -- render the tri-state, never two states: `FAILED_PATCHES n=<total> pending=<done is False>
  unknown=<done is None>`. Counting only `pending` makes an all-`null` sweep render
  `pending=0`, byte-identical to all-landed -- fabricating unknown as clean, which this module's
  own rule for the sibling signal forbids.
- `src/shared/packages/pyforge-marshal/tests/unit/test_status.py` -- new `TestFailedPatches`
  class mirroring `TestUnpushedWork`'s fixture convention (real `tmp_path` + `LocalFs()`,
  `_FakeVcs(worktrees=..., commit_subjects_value=...)`): no-patches-silent, landed-patch-is-
  spent (no finding), unlanded-patch-warns-as-unconfirmed, git-read-failure-degrades-every-patch-
  to-null-and-warns-once, unparseable-story-dir-name-treated-as-pending, malformed-project-policy-
  degrades-to-WARN-not-ERROR, directory-named-`changes.patch`-not-reported, zero-byte-patch-not-
  reported, and the text-format projection. Cover the spec's own Acceptance Criteria explicitly:
  **`--project SLUG` scoping** (an explicit AC, previously untested), **two homes where only one
  slug's policy is malformed** (the other must still classify -- per-home independence), and
  **`done: null` rendered in `--format text`**. Use at least one realistic bmad-loop story-dir
  name (long multi-hyphen, e.g. `4-11-marshal-land-refuses-while-a-run-is-in-flight`) and one
  two-digit epic (`12-1-...`), not only synthetic `4-13-title` fixtures.

## Tasks & Acceptance

**Execution:**
- [x] `core/status.py` -- add `failed_patches` to `FleetHomeFacts` (entry shape including
  `confidence`, reusing this module's OWN `CONFIDENCE_CONFIRMED`/`CONFIDENCE_UNCONFIRMED`) and
  thread it through all three `build_fleet_row` row shapes -- the data carrier for this signal
- [x] `core/findings.py` / `core/verdict.py` -- register `MRS-STATUS-010`/`MRS-STATUS-011` as
  `Verdict.WARN`, documenting BOTH of `011`'s causes at all three doc sites -- defines the
  findings `cli/status.py` reports below
- [x] `cli/status.py` -- add `_gather_failed_patches` (`is_file()`-filtered internally), the two
  new finding constants, `_merged_keys_for_slug` as the ONE shared merge-key sequence called by
  both this fold and `_reconcile_ledger`, and wire the glob + lazy landed-classification +
  WARN-emission into `run_status`'s per-home loop -- the feature itself
- [x] `cli/status.py` (`_render_text_status`) -- the tri-state `FAILED_PATCHES n= pending=
  unknown=` projection, so an all-unknown sweep never renders as clean
- [x] `tests/unit/test_status.py` -- `TestFailedPatches` covering the I/O matrix above PLUS the
  three Acceptance Criteria (`--project` scoping, per-home independence under a single bad
  policy, text-format `done: null`) and realistic story-dir-name fixtures

**Acceptance Criteria:**
- Given a fleet with multiple loop homes, when `marshal status` runs, then each home's row
  independently reports its own `failed_patches`, and a read/parse problem scoped to one home's
  patches never suppresses another home's real findings (mirrors this command's established
  "one bad row never blocks the sweep" precedent).
- Given `--project SLUG` scoping, when `marshal status --project SLUG` runs, then only that
  project's loop home is scanned for failed patches, consistent with the command's existing
  fleet-scoping behavior.
- Given the same fleet swept twice with no change in patches or merge history, when `marshal
  status` runs each time, then both runs report identical `failed_patches` data and finding
  counts -- the check is a pure read, never mutates or clears a patch.

## Spec Change Log

### 2026-08-10 — Review pass 2 amendment (implementation loopback 1)

**Triggering finding** `[high]` `[bad_spec]`: `MRS-STATUS-010` asserted "has not landed" as
established fact, derived from the negative direction of `core.promotion.merged_story_keys` --
the direction this package's own `core/status.py` already documents as unreliable
(`CONFIDENCE_UNCONFIRMED`, 2026-08-07 code review; `required` in `schemas/status.json`; "5 rows
for genuinely-merged stories, zero true positives"). Verified live: of 3 WARNs against the real
12-patch fleet, 2 were false (`pyforge-marshal` 1.6 -- named *in that very constant block* as one
of the 5 known false positives -- and `pyforge-steward` 8.1). The prior spec's own I/O matrix
mandated the unqualified WARN ("one `MRS-STATUS-010` WARN naming the story, path, and size"), so a
faithful re-derivation would have reproduced it; the root cause was in the spec's Code Map /
Tasks / Design Notes, not in the implementation's fidelity to them.

**What was amended** (all outside `<intent-contract>`, which is unchanged and remains
satisfiable as written): Code Map now mandates a `confidence` field reusing `core/status.py`'s
OWN existing constants; a message that states the unconfirmed direction rather than asserting
it; `run_id` in the finding; `is_file()` filtering inside `_gather_failed_patches` (before the
gate, not after); skipping zero-byte patches; a tri-state `pending=/unknown=` text projection;
both `MRS-STATUS-011` causes documented at all three doc sites with a per-slug-scoped message;
an explicit prohibition on reordering `_reconcile_ledger`'s policy read after its git read; and
correction of the now-false "never folded into the default view" claim. Tasks reset to unchecked
and extended with the three previously-untested Acceptance Criteria. Design Notes gained the
confidence rationale, the corrected laziness rationale, and the reason the classifier's own
blind spots are deferred rather than fixed here.

**Known-bad state avoided:** a durability net that fires more false alarms than real ones on the
live fleet (2 of 3), reported in the DEFAULT view with no confidence qualifier, while the sibling
view built on identical evidence carries one as a schema-required field. Also avoided: an
all-unknown sweep rendering `pending=0` (indistinguishable from all-landed) in `--format text`.

**KEEP instructions — these survived review and MUST be preserved in the re-derivation:**
1. `_merged_keys_for_slug` as the ONE shared policy-read-then-`merged_story_keys` sequence, pure
   (`-> tuple[frozenset[str], tuple[Finding, ...]]`, no out-param), called by BOTH the fleet fold
   and `_reconcile_ledger`. Pass 1 shipped two copies; the single owner is correct and verified.
2. The ERROR-severity degradation: a per-slug policy ERROR must NOT reach the default sweep's
   `findings` (a raw `MRS-POLICY-004` flips exit code to 4, violating the WARN-only Boundary) --
   degrade that slug's patches to `done: null` plus one `MRS-STATUS-011` WARN. `_reconcile_ledger`
   still surfaces such findings verbatim.
3. The lazy, sweep-wide-cached `main` commit-subjects read (`main_subjects_attempted` /
   `main_subjects_available`), with `MRS-STATUS-011` emitted at most once for the git-read arm.
4. `failed_patches` present in ALL THREE `build_fleet_row` row shapes -- never hardcoded `None`
   or omitted in a degraded row.
5. Bare `Path.glob` with `OSError -> ()`; no new `FsPort` primitive; sorted for determinism.
6. A directory named `changes.patch` is never reported (pass 1's `is_file()` guard was right --
   only its placement moves earlier).
7. `failed_patches` visible in `--format text`, not JSON-only.
8. Both codes in `REGISTERED_CODES` + `_CLASSIFY_TABLE` as `Verdict.WARN`, plus the exact-contents
   guard in `test_findings.py`.
9. The five pass-1 verified rejections recorded in the triage log below (`_read_project_policy`'s
   exception clause, `GitVcs.commit_subjects`'s failure mode, `normalize`'s contract, the
   no-silent-caps principle, `Path.glob`'s fixed-depth guarantee) -- re-verified, still correct;
   do not re-litigate or re-guard them.

## Review Triage Log

### 2026-08-10 — Review pass 1
- intent_gap: 0
- bad_spec: 0
- patch: 4 (high 1, medium 1, low 2)
- defer: 1 (low 1)
- reject: 5
- addressed_findings:
  - `[high]` `[patch]` A malformed project-policy TOML for a slug -- unrelated to this durability
    check -- injected `_merged_keys_for_slug`'s raw `PolicyIOError` finding (`MRS-POLICY-004`,
    `Verdict.ERROR`, exit code 4) straight into the DEFAULT `marshal status` sweep merely because
    that slug's home carried even a harmless, already-landed patch, violating this story's own
    Boundary ("never blocks or changes marshal status's exit code"). Fixed: an ERROR-severity
    finding from `_merged_keys_for_slug` now degrades that slug's patches to `done: null` and
    surfaces as one `MRS-STATUS-011` WARN instead -- the same tier an unreadable `main` already
    uses. `_reconcile_ledger` (an explicit `--project` diagnostic view) still surfaces such
    findings verbatim, unaffected.
  - `[medium]` `[patch]` `_merged_keys_for_slug`'s docstring claimed it "reused" `_reconcile_
    ledger`'s policy-read-then-`merged_story_keys` sequence while `_reconcile_ledger` still
    carried its own independent, byte-for-byte copy -- a real "one owner for the merge-subject
    form" violation. Fixed: `_merged_keys_for_slug` now returns `tuple[frozenset[str],
    tuple[Finding, ...]]` (pure, no `findings` out-param) and `_reconcile_ledger` calls it --
    one implementation, not two.
  - `[low]` `[patch]` A directory literally named `changes.patch` would match the glob
    (`Path.glob` does not distinguish file kind) and `.stat()` on a directory succeeds rather
    than raising, fabricating a reported entry. Fixed: `if not patch.is_file(): continue`.
  - `[low]` `[patch]` `failed_patches` was invisible in `--format text` output (`unpushed_work`
    renders there; `failed_patches` did not). Fixed: a `FAILED_PATCHES n=<total>
    pending=<count>` summary line, mirroring `unpushed_work`'s own `UNPUSHED` marker.
  - `[low]` `[defer]` The unparseable-story-dir-name fallback (`story_key = patch.parent.name`)
    flows unsanitized into the `MRS-STATUS-010` finding message with no newline-stripping, unlike
    `_render_text_status`'s own `unpushed.stat` sanitization. Pre-existing, systemic gap shared
    by `MRS-STATUS-008`'s own `remedy`/`stat` interpolation (not unique to this story) and
    low-probability given bmad-loop, not an attacker, controls this directory-name format; a
    partial fix touching only this one code path would be inconsistent. Logged to the
    deferred-work file.
  - `[reject]` (Edge Case Hunter) `policy_path.is_file()` raising something other than `OSError`
    then `_read_project_policy` raising something other than `PolicyIOError`: verified against
    `_read_project_policy`'s actual `except (OSError, UnicodeDecodeError, TOMLDecodeError)`
    clause -- no other exception is possible.
  - `[reject]` (Edge Case Hunter) `vcs.commit_subjects` raising something other than
    `VcsCommandError`: verified against `GitVcs.commit_subjects`'s actual implementation
    (subprocess-returncode check only) -- the identical call+catch pattern already ships
    unmodified in `_reconcile_ledger`.
  - `[reject]` (Edge Case Hunter) `normalize`/`render_feed_key` raising something other than
    `MalformedStoryKeyError`: verified against `normalize`'s actual contract -- it always
    constructs a valid `StoryKey`, so `render_feed_key`'s `TypeError` guard is unreachable here.
  - `[reject]` (Edge Case Hunter) unbounded findings from unpruned stale patches accumulating
    over time: no evidence of practical risk (7 total across 5 stations, per the motivating
    incident) and a cap would contradict this repo's own established "no silent caps" principle
    (`scripts/unpushed_work_check.py`'s own docstring).
  - `[reject]` (Edge Case Hunter) `patch.parent.parent.parent` assumed a fragile fixed depth:
    verified against `Path.glob` semantics -- a non-recursive, fixed-segment glob pattern
    guarantees a fixed-length result relative to the search root regardless of `home`'s own
    absolute depth.

### 2026-08-10 — Review pass 2
- intent_gap: 0
- bad_spec: 9 (high 1, medium 2, low 6)
- patch: 0
- defer: 4 (medium 2, low 2)
- reject: 3
- addressed_findings:
  - `[high]` `[bad_spec]` `MRS-STATUS-010` asserted "has not landed" as established fact from the
    negative direction of `merged_story_keys` -- the direction `core/status.py`'s own
    `CONFIDENCE_UNCONFIRMED` block documents as proving nothing (squash-merge blind spot;
    "5 rows for genuinely-merged stories, zero true positives", 2026-08-07 code review; `required`
    in `schemas/status.json`). Verified live against the real 12-patch fleet: 3 WARNs, **2 false**
    -- `pyforge-marshal` 1.6 (landed as squash `marshal: recover Story 1.6 … (#163)`, and named
    *in that very constant block* as one of the 5 known false positives) and `pyforge-steward` 8.1
    (landed as `…from rxm7706/land/steward-8-1`; 22 such merges on `main` parse to nothing).
    Spec amended to mandate a `confidence` field reusing the module's own constants and a message
    that states the direction honestly; implementation reverted for re-derivation.
  - `[medium]` `[bad_spec]` `--format text` collapsed the `done` tri-state into two states:
    `pending` counted only `done is False`, so an all-`null` sweep rendered `FAILED_PATCHES n=3
    pending=0` -- byte-identical to all-landed, fabricating unknown as clean, which this module's
    own stated rule for the sibling signal forbids. Spec now mandates `pending=` AND `unknown=`.
  - `[medium]` `[bad_spec]` `MRS-STATUS-011` was overloaded in pass 1 with a second cause (a
    per-slug policy ERROR) while all three doc sites still described only the unreadable-`main`
    cause and still claimed "attempted at most ONCE for the whole sweep" -- false for the
    per-home arm, which can fire once per misconfigured station. Its emitted message also said
    "every patch found this sweep reports done: null" when only that one slug degrades. Spec now
    requires both causes documented at all three sites and a per-slug-scoped message.
  - `[low]` `[bad_spec]` `_reconcile_ledger` behavior regression: pass 1 moved the policy read to
    after the `git log` read, so a git failure now returns before `_merged_keys_for_slug` is
    called and the `MRS-POLICY-004` diagnostic that pre-existing shipped view reported is
    silently dropped -- while `_merged_keys_for_slug`'s own docstring still claimed that view
    surfaces policy ERRORs "at face value". The justifying comment also called a genuinely
    malformed policy file's finding "spurious". Spec now prohibits the reorder.
  - `[low]` `[bad_spec]` A directory named `changes.patch` as the only glob match still opened the
    `if patch_paths:` gate (the `is_file()` guard ran too late), paying for the git read and able
    to emit an orphaned `MRS-STATUS-011` while every row reported `failed_patches: []`. Spec now
    puts the filter inside `_gather_failed_patches`.
  - `[low]` `[bad_spec]` Stale/self-contradicting rationale: `--reconcile-ledger`'s own docs say
    its `git log`-scale walk over `main` is "never folded into the default view" -- this story
    folds it in -- and the "most homes carry no failed patches" laziness justification is
    measurably false (7 of 8 live homes carry patches). Spec now states the real reason.
  - `[low]` `[bad_spec]` Test gaps against this spec's own Acceptance Criteria: `--project SLUG`
    scoping untested despite being an explicit AC; no two-home test where one slug's policy is
    malformed and the other still classifies (the per-home-independence AC, and the exact branch
    pass 1 added); no `done: null` text-rendering test (which is why the `pending=0` false-green
    shipped); every fixture a synthetic short `4-13-title`, never a realistic long bmad-loop dir
    name or a two-digit epic. Spec's task list now names all four.
  - `[low]` `[bad_spec]` `MRS-STATUS-010` omitted `run_id` though the row entry carries it, so
    repeat failed attempts at one story across runs were distinguishable only by a long absolute
    path (live: `pyforge-steward` carries three run dirs).
  - `[low]` `[bad_spec]` A zero-byte `changes.patch` (a kill before any diff was written) produced
    a WARN directing an operator to recover an empty file. Spec now skips it.
  - `[reject]` (Blind Hunter) "Genuinely unlanded patches reported `done: true` and silently
    dropped" for `pyforge-doctor` 1.4 and `pyforge-mason` 1.3, on the basis that each matched only
    a foreign station's branch. The premise was tested and is **false**: `main` also carries
    `doctor: recover Story 1.4 … (#162)` and `mason: recover Story 1.3 … (#164)`, so both stories
    really did land and the reported answer is correct. The underlying cross-project collision is
    real but currently masks nothing -- recorded as a defer against `core/promotion.py`, not as
    live data loss.
  - `[reject]` (Edge Case Hunter) Unsanitized `story_key`/`path` interpolation into the
    `MRS-STATUS-010` message (newline injection into text output). Real, but **already deferred in
    pass 1 and already present in the ledger**; its premise (systemic, shared with
    `MRS-STATUS-008`'s own `remedy`/`stat` interpolation) was re-verified and still holds. Not
    re-logged as a duplicate entry.
  - `[reject]` (Blind Hunter + Edge Case Hunter) `--escalations` retains `MRS-STATUS-010` findings
    for rows the filter removed, leaving findings that name homes absent from the payload.
    Verified as the exact shipped behavior of `MRS-STATUS-008` (Story 5.5) -- a pre-existing
    pattern this change copies rather than introduces; changing it would alter 5.5's shipped
    contract, out of this story's scope.

### 2026-08-10 — Review pass 3
- intent_gap: 0
- bad_spec: 0
- patch: 7 (medium 3, low 4)
- defer: 2 (medium 1, low 1)
- reject: 3
- addressed_findings:
  - `[medium]` `[patch]` (both reviewers, independently) The pass-2 zero-byte skip and the
    `patch.stat()` `OSError` skip both ran INSIDE the caller's per-entry loop -- after the
    `if patch_paths:` gate had already opened -- reintroducing the exact orphaned-`MRS-STATUS-011`
    hole the relocated `is_file()` filter was meant to close. Reproduced live: a home whose only
    match is a zero-byte `changes.patch`, with `main` unreadable, emitted `MRS-STATUS-011` while
    every row reported `failed_patches: []` and the verdict flipped `clean -> warn` naming nothing.
    Fixed: `_gather_failed_patches` now returns `(path, size_bytes)` pairs and owns ALL THREE
    reportability tests (`is_file()`, `st_size > 0`, `stat()`-raises), so a non-empty return
    genuinely means "there is something to report" and the caller never re-`stat()`s. This
    deviates from the Code Map's declared `-> tuple[Path, ...]` signature, deliberately: returning
    the size is what makes the size test possible in the one place it belongs.
  - `[medium]` `[patch]` `MRS-STATUS-011` named no patch at all, while the intent contract's
    Always bullet requires a patch whose landed-status "could not be determined" to raise "exactly
    one WARN naming it" -- an operator got a bare count for up to 12 unresolved patches. Fixed:
    both arms name their patches (`_name_patches`, newline-sanitized), which required moving the
    sweep-wide arm's emission to after the per-home loop, since homes scanned later are not yet
    known where the git read fails. Still exactly ONE WARN for that arm; the read is still
    attempted at most once. (The I/O matrix's "ONE WARN for the whole sweep" and the Always
    bullet's "naming it" have exactly one reading that satisfies both, so this is not an
    intent_gap.)
  - `[medium]` `[patch]` A fourth inline copy of the best-effort story-key renderer, in a story
    whose stated discipline is "one owner" -- `core/status.py::_render_story_key_best_effort`
    already is that function, and `cli` may import `core` (only the reverse direction is
    AD-3/AD-4-forbidden, which is why that helper cannot import `cli/spin.py`'s twin). Fixed by
    reusing it: the same correction pass 1 applied to `_merged_keys_for_slug`.
  - `[low]` `[patch]` The exit-code guard tested `Finding.severity`, but the Boundary it defends
    is decided by `core/verdict.py`'s `_CLASSIFY_TABLE`; the two are only accidentally aligned
    today (every `Verdict.UNEVALUABLE` policy code happens to be built at `Severity.ERROR`), so a
    future UNEVALUABLE-but-WARN code would have slipped through and changed the exit code. Now
    tests `classify(f.code)`.
  - `[low]` `[patch]` That same branch discarded `keys_findings` wholesale, so an unrelated
    WARN-tier policy finding accompanying an ERROR vanished entirely. Now only the
    exit-code-changing findings are withheld.
  - `[low]` `[patch]` `MRS-STATUS-010`'s message explained itself solely by the classifier's
    blind spots, which is wrong for its second arm (a story-dir name that never parsed as a story
    key -- no classifier limitation involved). Message now covers both arms honestly.
  - `[low]` `[patch]` `FleetHomeFacts.failed_patches`'s docstring asserted this field has "no
    could-not-be-consulted case of its own", contradicted by the caller's own
    `except OSError: return ()` and by `Path.glob`'s silent truncation. Corrected, with both
    limits named. Also corrected the sweep-cost comment, which claimed the per-slug policy
    compose was cached alongside the git read -- only the git read is.
  - `[medium]` `[defer]` `Path.glob` silently yields a PARTIAL result when an intermediate
    directory is unreadable (verified against CPython 3.14.6: a `chmod 000` story dir makes its
    patch vanish with no exception and no finding), so a real unlanded patch can go unreported --
    the false-green class this signal exists to prevent. Deferred: closing it honestly needs
    enumeration-integrity reporting under a new finding code, and the trigger requires broken
    permissions inside a loop home the harness itself creates. Logged to the deferred-work file.
  - `[low]` `[defer]` A patch for the story a home is re-driving RIGHT NOW warns as though the
    work were abandoned, though the row already carries `current_story`. Deferred: suppressing
    would contradict the Always bullet ("every patch is reported"), and annotating needs a
    contract decision about the entry shape. Logged to the deferred-work file.
  - `[reject]` (Edge Case Hunter) `normalize`'s trailing-text tolerance could fabricate a story
    key from a non-story directory name (e.g. a date-like `2026-08-...`). No practical risk:
    bmad-loop is the sole writer of `failed/<story>/` and its format is deterministic
    `<epic>-<seq>-<description>` -- the same premise pass 1 used to reject the directory-name
    sanitization concern, re-verified and still true.
  - `[reject]` (Edge Case Hunter) A `.bmad-loop` or `runs/<id>` symlink pointing into another
    home would double-count a patch and classify the copy against the wrong project's policy.
    Contrived: loop homes are created by `marshal factory spin`, never hand-symlinked, and no
    such layout exists anywhere in the live fleet.
  - `[reject]` (Blind Hunter) The default view is now permanently non-clean with two thirds of
    its live alarms known-false and no acknowledgement path. Both halves are already deferred --
    the known-false ratio to the `core/promotion.py` classifier story, the missing disposition
    path to its own ledger entry from pass 2. Nothing new to record.

### 2026-08-10 — Review pass 4
- intent_gap: 0
- bad_spec: 0
- patch: 6 (medium 2, low 4)
- defer: 4 (medium 2, low 2)
- reject: 5
- addressed_findings:
  - `[medium]` `[patch]` (Blind Hunter) Three doc sites still asserted that a POSITIVE
    `merged_story_keys` match "is proof", and this pass stamped that reading onto the wire as
    `confidence: "confirmed"` -- while this project's own ledger already records the positive
    direction as cross-project contaminated. Re-verified live against `main`'s 2,353 subjects:
    `pyforge-mason`, `pyforge-doctor` and `pyforge-scribe` each resolve ~30 keys, most belonging
    to OTHER stations (mason returns marshal's `4.1`-`4.10`), so a future killed mason story 4.1
    would report `done: true` and fire no WARN -- the SILENCING direction, the one with data-loss
    consequences, while all three prior passes hardened only the noisy negative one. Fixed at the
    doc level, not the value: the `confidence` value is Code-Map-mandated and
    `reconcile_ledger_vs_git` ships the same vocabulary for the same evidence, so all three sites
    now say "the stronger direction", name the contamination, and point at the deferral -- the
    same overclaim-correction pass 3 applied to `FleetHomeFacts.failed_patches`'s own `()` claim,
    applied consistently this time.
  - `[medium]` `[patch]` (Edge Case Hunter) `MRS-STATUS-010`'s message interpolated `story_key`
    AND `path` unsanitized while `_render_text_status`'s findings block prints one finding per
    line without escaping. Reproduced live: a story dir named
    `4-11-fine\n  MRS-STATUS-999 [error] INJECTED` forged a findings line no finding emitted.
    Pass 1 deferred this on the premise that a partial fix would be inconsistent -- a premise
    this story's own pass 3 invalidated by adding exactly that sanitization to `_name_patches`
    for the sibling code. Fixed with a `_one_line` helper covering both; the wider
    `MRS-STATUS-008` instance stays deferred.
  - `[low]` `[patch]` (Edge Case Hunter) The per-slug `MRS-STATUS-011` asserted "cannot resolve
    this project's own merge-subject policy", false for most codes that reach it:
    `MRS-POLICY-001` (an unrecognized key) classifies `UNEVALUABLE` and so blocks, yet `compose`
    still returns a usable `merge_subject_template` (verified by direct execution). The message
    now states what happened, NAMES the withheld codes (previously invisible in the only view
    most sweeps run), and points at `--reconcile-ledger` for the finding itself.
  - `[low]` `[patch]` (Blind Hunter) `_name_patches` rendered bare, undeduped story keys, and
    story numbers repeat across stations by construction -- live, `pyforge-doctor` and
    `pyforge-warden` both carry a `6-9-*` patch, so the one sweep-wide WARN read `(6.9, 6.9)` and
    located neither. Now `<slug>/<story_key>`.
  - `[low]` `[patch]` (Blind Hunter) This module's docstring claimed "No `sprint-status.yaml`,
    ledger, or any other hand-maintained feed is ever read for the fleet summary" -- false since
    this story, which reads each patch-carrying home's `marshal-policy.toml`. Corrected with the
    AD-5 reasoning that does still hold (it is CONFIGURATION, never a story-state claim).
  - `[low]` `[patch]` (Blind Hunter) KEEP instruction #3 -- "`main` is read at most ONCE per
    sweep", asserted at four doc sites -- had zero coverage: `_FakeVcs` recorded no call count, so
    deleting the guard left the suite green while turning one `git log` per invocation into one
    per home. Now counted, with tests for both the once-only and the never-when-empty halves.
  - `[medium]` `[defer]` Durability reads LOCAL `main` only while `cli/deploy.py` -- the same
    shared owner's other consumer -- reads `origin/main` + `main` (AD-29). Live reflog shows 22
    and 34 minute fetch-vs-fast-forward windows, so a just-landed story warns as pending here
    while `deploy promote` calls it durable. Bounded by the frozen intent contract's own "for
    `main`" and consistent with `_reconcile_ledger` in this same module. Logged to the
    deferred-work file.
  - `[medium]` `[defer]` `core.promotion.count_conforming_subjects` is unused, so a `main`
    yielding ZERO conforming subjects (shallow clone, grafted history) is indistinguishable from
    N genuinely-unlanded stories -- the exact ambiguity `cli/deploy.py` reports as
    `subjects_examined`/`subjects_matched`. Logged to the deferred-work file.
  - `[low]` `[defer]` The `blocking` guard degrades a whole home on ANY non-CLEAN/WARN policy
    finding, discarding an already-correct `merged_keys` including proof-grade positives.
    Conservative and safe-direction, but over-broad; narrowing it needs `_merged_keys_for_slug`
    to report whether its template came from the project's own file or a fallback. Logged to the
    deferred-work file.
  - `[low]` `[defer]` `--escalations` emits `MRS-STATUS-010` for rows the filter then removes.
    Pass 2's scope-based rejection (the pre-existing `MRS-STATUS-008` pattern) was re-verified and
    still holds, so not fixed here -- but reachability is new: the sibling fires zero findings on
    the live fleet while this signal fires 3, up to 12. Logged to the deferred-work file.
  - `[reject]` (Blind Hunter) `--format text` never names a "spent" patch though the epics AC
    says each is reported with story key and size. The spec's Code Map mandates that exact
    counts-only line (`FAILED_PATCHES n= pending= unknown=`), mirroring `unpushed_work`'s own
    single-line convention; the AC is satisfied by the `--format json` payload for every patch
    and by the findings block for every pending one, and a spent patch is informational by the
    AC's own wording.
  - `[reject]` (Blind Hunter) `_gather_failed_patches` stats each candidate twice (`is_file()`
    then `stat()`), a TOCTOU window. No failure scenario demonstrated -- the reviewer flagged it
    "for consistency, not as a live failure" -- and the helper's own guarantee (a non-empty
    return means something reportable) holds either way.
  - `[reject]` (Blind Hunter) `MRS-STATUS-011`'s per-slug arm sets `path=<slug>`, which is not a
    filesystem path. `Finding.path` in this module already carries non-paths: `MRS-STATUS-008`
    sets it to `facts.branch`, a git ref. The slug is the thing that finding is about.
  - `[reject]` (Blind Hunter) The pass-3 "non-blocking policy WARN alongside an ERROR" branch is
    unreachable today, since `MRS-POLICY-005` is the only WARN-classified policy code and its
    trigger (a missing slug) cannot co-occur with a slug-scoped ERROR. Correct but not a defect:
    it is a cheap defensive guard closing a real pass-3 finding, and removing it would re-open
    that finding the moment a WARN-tier policy code is added.
  - `[reject]` (Edge Case Hunter) `marshal status --run <id>` returns before the fold, so the
    per-run drill-down never shows that run's own preserved patch. Out of scope: the intent
    contract folds this signal onto the fleet sweep's per-home row, and names no other view.

### 2026-08-10 — Review pass 5
- intent_gap: 0
- bad_spec: 0
- patch: 6 (high 0, medium 2, low 4)
- defer: 1 (medium 1)
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` (both reviewers, independently) The sweep-wide `MRS-STATUS-011`
    interpolated the raw `VcsCommandError` into its message with no `_one_line` -- the exact
    injection class pass 4 introduced `_one_line` to close, applied to `MRS-STATUS-010`'s
    operands and not to the one arm whose interpolated value is git's own stderr. Unlike the
    pass-4 case this needs no adversarial directory name: real git, asked for a `main` that does
    not exist locally, answers in THREE lines, so the single WARN printed as three text lines
    (`--format text` is the default), two of them beginning with git-controlled text and no
    `MRS-` prefix -- and an unreadable `main` is precisely the condition this code exists to
    report. Fixed; regression test uses git's verbatim three-line stderr.
  - `[medium]` `[patch]` (both reviewers, independently) `_name_patches` named each patch
    `<slug>/<story_key>`, closing pass 4's CROSS-HOME collision while leaving the CROSS-RUN one
    open: a home accumulates one `failed/<story>/` per killed attempt, so repeated attempts at
    one story in one home rendered identically (`steward/8.1, steward/8.1, steward/8.1`) and
    located none of them -- live, `pyforge-steward` carries three run dirs. `MRS-STATUS-010`
    already carries `run_id` for exactly this reason (pass 2), and `MRS-STATUS-011` is the ONLY
    report a `done: null` patch ever gets, since `010` fires solely for `done is False`. Now
    `<slug>/<story_key>@<run_id>`.
  - `[low]` `[patch]` (Edge Case Hunter) `_one_line` collapsed only `\n` and `\r`, too narrow
    for its own stated threat model: if a `failed/<story>/` name may legally carry a newline it
    may equally carry `\v`, `\f`, `\x1c`-`\x1e`, `\x85`, `\u2028` or `\u2029` -- all legal in a
    POSIX/UTF-8 filename, all split by `str.splitlines`, which is the very method this story's
    own forged-line test asserts with, and several rendered as a break by a terminal. Widened to
    every C0 control, `\x7f`, and the three non-C0 `splitlines` breaks.
  - `[low]` `[patch]` (Blind Hunter) `_gather_failed_patches`'s docstring claimed an unreadable
    `.bmad-loop` tree "degrades to none found" via its `except OSError`, directly contradicting
    `core/status.py::FleetHomeFacts.failed_patches` -- corrected in this same story by pass 3 --
    which states the real behavior. Re-verified on CPython 3.14.6: `Path.glob` suppresses the
    error and yields a PARTIAL result (`chmod 000` on one story dir drops just that patch;
    on `failed/` empties the home), so the `except OSError` guards only a pre-iteration failure
    and a maintainer was told the conspicuous failure mode was the real one. Docstring corrected
    to match the sibling; the underlying behavior stays deferred (pass 3's entry).
  - `[low]` `[patch]` (Blind Hunter) `core/findings.py` and `core/verdict.py` both carry a
    per-story narrative in their MODULE docstrings enumerating every `MRS-STATUS-*` code as its
    story adds it; this story registered `010`/`011` in `REGISTERED_CODES`/`_CLASSIFY_TABLE` and
    documented them at the three per-code sites the Code Map names, but neither narrative moved
    past `009`. Both extended, each in its own file's idiom (findings: what the code reports and
    why WARN; verdict: why this table, not `Severity`, is what the Boundary turns on).
  - `[low]` `[patch]` (Blind Hunter) The per-slug `MRS-STATUS-011` told the operator to run
    `marshal status --project <slug> --reconcile-ledger` "for the finding itself", but
    `_reconcile_ledger` returns early on `MRS-STATUS-005` when that project's tracked ledger is
    unreadable or absent, never reaching `_merged_keys_for_slug` -- so for a station spun before
    its ledger lands, the remedy delivers a different finding. Message now states the
    precondition. (The withheld codes are named inline regardless, pass 4.)
  - `[medium]` `[defer]` `bmad-dev-auto`'s mandated defer format writes bare `- source_spec:`
    bullets carrying no `DW-<id>`, while `scripts/deferred_work_check.py` (Story 4.13 / FR-175)
    compares Tier-3 to the tracked ledger BY ID -- so this story's 11 deferrals are invisible to
    the detector built to guarantee deferrals reach a durable ledger, and it greens. Verified by
    execution (11 citations in Tier-3, 0 in the tracked ledger, detector exits 0 with "every
    Tier-3 deferral has a tracked twin"). Deferred: the entry format is dictated by the review
    skill rather than by this diff, and this run's invocation reserves ledger promotion to the
    orchestrator. Logged to the deferred-work file.
  - `[reject]` (Blind Hunter) The `.memlog.md`'s claim that "the 2 remaining errors in
    `test_status.py` are pre-existing" undercounts at 3 (`UP017` x2 + `RUF059`). Tested: `ruff
    check` on that file reports "Found 2 errors" -- the memlog is accurate and the finding is
    not. (`ruff check` on the three changed sources reports one `TRY004`, likewise present at
    the baseline revision.) The same finding's second half -- "documented at all three doc
    sites" is false -- is true only of the module-level narratives, which are a fourth and fifth
    site; the three the Code Map names do document both codes. Patched above on its own merits,
    not as a memlog correction.
  - `[reject]` (Blind Hunter) A worktree on `loop/feature/x` yields slug `feature/x`, which
    `_is_valid_project_slug` rejects, so `MRS-POLICY-006` reaches a message about "this
    project's own merge-subject policy". Contrived: loop homes are created by `marshal factory
    spin` from a project slug and no such layout exists in the live fleet -- the same premise
    pass 3 used to reject the symlinked-home case. The message also names `MRS-POLICY-006`
    explicitly, so the real cause is not concealed.
  - `[reject]` (Blind Hunter) `--format text` never names a "spent" patch. Pass 4 rejected this
    on the Code Map's explicit mandate of the counts-only `FAILED_PATCHES n= pending= unknown=`
    line; re-verified -- the Code Map still mandates exactly that string, so the premise is
    scope-based and survives.
  - `[reject]` (Blind Hunter) The pass-3 non-blocking-policy-finding branch is unreachable
    today. Pass 4 rejected this on the design premise that it is a cheap defensive guard whose
    removal would re-open a real pass-3 finding the moment a WARN-tier policy code is added;
    re-verified, still correct, and this pass's own `classify`-based guard depends on it.
  - `[reject]` (Blind Hunter) `_name_patches`'s `if not keys: return "no patches"` is dead code.
    True -- both call sites are gated on a non-empty collection -- but it is a total-function
    default in a rendering helper, with no failure scenario.
  - `[reject]` (Blind Hunter) `findings.extend(f for f in keys_findings if f not in blocking)`
    is an O(n^2) scan equivalent to re-testing `classify`. The reviewer states it has no
    behavioral difference; `keys_findings` holds at most a handful of policy findings.

## Design Notes

**Why this extends `cli/status.py` rather than a new `scripts/*_check.py` detector.** FR-176
itself says the signal is "reported alongside the other durability signals (unpushed-work-
check's family)" -- Story 5.5's own already-shipped fold. More decisively: "has this story
landed" requires `core.promotion.merged_story_keys`'s three-pattern, project-scoped merge-
subject classification (AD-24/AD-33), which is Marshal-internal Python with no external CLI
surface. `scripts/unpushed_work_check.py`/`deferred_work_check.py` deliberately avoid importing
Marshal internals and re-derive their own git logic instead -- duplicating the merge-subject
classifier in a standalone script would violate this codebase's own "one owner for the merge-
subject form" rule (Epic 4 context, Technical Decisions) and risk a second, silently-diverging
copy of a three-pattern parser that has already needed two correctness fixes (cross-project
collision, GitHub-squash blind spot). Reuse, not a new detector, is the surgical choice.

**Why the `main`-subjects read is cached once for the whole sweep.** A `git log`-scale walk over
`main` plus a per-project policy compose is the heavier read `--reconcile-ledger`'s own docs cite
as its reason for being opt-in; reading it once and reusing it for every home keeps that cost
paid a single time no matter how many homes carry patches. It is resolved lazily (on first need)
so a fleet with genuinely zero patches never pays it at all -- but note the laziness is a
degenerate-case optimization, NOT the common path: measured 2026-08-10, **7 of 8 live homes carry
at least one patch**, so a real sweep performs this read essentially always. Do not restate the
"most homes carry no failed patches" claim -- it is false.

**Why `done: false` must be reported as `unconfirmed`, never as the flat assertion "has not
landed" (review pass 2, the finding that reverted pass 1's implementation).** The two directions
of a `merged_story_keys` comparison are not equally reliable, and this package has already
established that formally: `core/status.py`'s `CONFIDENCE_CONFIRMED`/`CONFIDENCE_UNCONFIRMED`
block (added by the 2026-08-07 code review, enforced as a `required` field in
`schemas/status.json`) records that a positive match is proof, while an ABSENCE of a match proves
nothing -- `merged_story_keys` cannot parse a story key out of GitHub squash-merge prose, and a
live run against this repo's own history produced 5 "not merged" rows for genuinely-merged
stories with **zero true positives**. Two independent live measurements confirm the same failure
reproduces exactly here: of the 3 `MRS-STATUS-010` WARNs pass 1's implementation emitted against
the real 12-patch fleet, **2 were false** -- `pyforge-marshal` 1.6, which landed as the squash
subject `marshal: recover Story 1.6 — isolation verification and home enumeration (#163)` (and is
*by name* one of the 5 false positives that constant block already documents), and
`pyforge-steward` 8.1, which landed as `Merge pull request #383 from rxm7706/land/steward-8-1`
(22 such `land/<station>-<epic>-<seq>` merges exist on `main`; `normalize` anchors at position 0,
so the leading station token makes the segment unparseable). Only `pyforge-doctor` 6.9 was a true
positive. A durability net whose alarms are wrong twice as often as they are right trains an
operator to ignore it -- the precise outcome the Charter's "never overstate coverage" rule and
this repo's own never-false-green principle forbid. The intent contract's definition of "landed"
is unchanged and the WARN still fires for every unlanded patch (its Always bullet is satisfied);
what changes is that the finding and the row report the direction honestly instead of asserting a
definitional negative as a fact about the world.

**Why the classifier's own blind spots are NOT fixed here.** Extending
`core.promotion.merged_story_keys` to read squash subjects and `land/<station>-<epic>-<seq>`
branches -- and project-scoping `extract_story_key_from_github_merge_subject`, which unlike the
bmad-loop pattern takes no `project_slug` at all, so one station's patch can match on another
station's PR-merge subject (verified: `pyforge-doctor`'s 1.4 patch matches only `scribe/1-4-…`
and `steward/1-4-…`; `pyforge-mason`'s 1.3 only `herald/1-3-…`) -- would change the behavior of
three other already-shipped views (`_reconcile_ledger`, `cli/deploy.py`, `cli/land.py`) that
consume the same single owner. That is a separate story against `core/promotion.py`, deferred to
the ledger. Reporting `unconfirmed` is the honest handling available *within* this story's
boundary, and it is what the sibling view already does for the identical limitation.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: full suite green,
  including the new `TestFailedPatches` cases
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: no new disallowed import edges
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- expected: clean

## Auto Run Result

Status: done (review pass 5, follow-up review of a `done` spec — no revert, no spec amendment)

**Implemented change (cumulative, `8410edba56..b5a90a0399`).** `marshal status`'s fleet sweep
now folds a second durability signal onto every loop home's row beside `unpushed_work`: the
`.bmad-loop/runs/*/failed/*/changes.patch` a session-timeout kill preserves. Each patch is
reported with its story key, run id, path, size, a `done` tri-state, and a `confidence` drawn
from `core/status.py`'s own existing vocabulary; a patch not confirmed landed raises
`MRS-STATUS-010`, and one whose landed-status could not be determined raises `MRS-STATUS-011`.
Both are `Verdict.WARN` — the intent contract forbids this best-effort read from changing the
command's exit code.

**Files changed in this pass (6 patches, 1 defer, 6 rejects):**
- `src/pyforge/marshal/cli/status.py` — `_one_line` applied to the sweep-wide
  `MRS-STATUS-011`'s interpolated git error and widened to every `str.splitlines` break;
  `_name_patches` qualifies each patch by `@<run_id>`; `_gather_failed_patches`'s docstring
  corrected on `Path.glob`'s silent truncation; per-slug `MRS-STATUS-011` states the
  precondition for the `--reconcile-ledger` remedy it points at.
- `src/pyforge/marshal/core/findings.py` — module docstring's per-story `MRS-STATUS-*`
  narrative extended past `009` to cover `010`/`011`.
- `src/pyforge/marshal/core/verdict.py` — same, in that file's idiom (why this table, not
  `Severity`, is what the WARN-only Boundary turns on).
- `tests/unit/test_status.py` — `_FakeVcs.commit_subjects_error` (settable git failure text)
  plus three regression tests: multiline-git-error-cannot-forge-a-findings-line,
  sweep-wide-WARN-qualifies-a-repeated-key-by-run,
  non-newline-line-breaks-cannot-forge-a-findings-line.
- `planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` — pass-5 correction + notes,
  naming the three governed paths that moved.

**Review findings breakdown.** 6 patches applied (2 medium, 4 low); 1 deferred (medium — the
`bmad-dev-auto` defer format carries no `DW-<id>`, so `scripts/deferred_work_check.py` cannot
see this story's 11 deferrals and greens); 6 rejected. One rejection is a correction of the
reviewer: the claim that the memlog undercounts `test_status.py`'s pre-existing ruff errors at
2 was tested and is false — `ruff check` reports exactly 2. Two rejections re-verified pass-4
premises (the counts-only text line is Code-Map-mandated; the non-blocking-policy branch is a
deliberate defensive guard) and both still hold.

**Verification performed.**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — **3157 passed**, 9 slow
  deselected (+3 from this pass).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — **67 passed**.
- `pixi run --frozen -e pyforge-marshal lint-imports --config .../pyproject.toml --no-cache` —
  **3 contracts kept, 0 broken**.
- `ruff check` on the three changed sources — clean on `cli/status.py` and `core/findings.py`;
  `core/verdict.py`'s single `TRY004` was confirmed present at the baseline revision.
- `python3 scripts/spec_surface_check.py` — exit 0, no drift.
- Live-fleet re-check, unchanged from pass 4 as expected for a message/doc-only pass: 12
  patches across 8 homes (7 carrying), 3 `MRS-STATUS-010` (`1.6`/`6.9`/`8.1`), 9 `confirmed`
  + 3 `unconfirmed`, verdict `warn`, exit 0.
- `Path.glob` truncation re-verified directly on CPython 3.14.6 before rewriting the docstring
  that described it.

**Residual risks.**
- The classifier's own blind spots remain: the NEGATIVE direction of `merged_story_keys` cannot
  parse GitHub squash prose or `land/<station>-<epic>-<seq>` subjects (2 of 3 live WARNs are
  false), and the POSITIVE direction is cross-project contaminated (a killed mason 4.1 could
  report `done: true`). Both are reported honestly via `confidence` and both are deferred to a
  `core/promotion.py` story.
- `Path.glob` still truncates silently on an unreadable intermediate directory, so `()` is not
  proof the tree was read. Documented at both sites now; deferred.
- Durability reads LOCAL `main` only, while `cli/deploy.py` reads `origin/main` + `main`;
  deferred (bounded by the frozen intent contract's own "for `main`").
- This story's 11 (now 12) deferrals still have no tracked twin — see the pass-5 defer.

**Follow-up review recommended: true.** Five consecutive passes have each found real defects,
and this pass is no exception: the injection guard pass 4 introduced was itself incomplete on
the arm whose trigger is the ordinary failure path. The `_one_line` widening touches every
finding message this story emits, and `_name_patches`'s shape changed, so an independent pass
over the message layer is warranted even though the classification itself is unchanged.
