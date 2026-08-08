---
title: 'Notice Data Model & Archive Storage'
type: 'feature'
created: '2026-08-08'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Epic 10 (Moment 4 -- Operations Notices) needs a durable, structured record of
deprecation/fix/EOL notices (type, component, what/why/migration, deadline, reason_link) with
fast discovery and a simple edit history. The original epics-with-stories.md AC (lines 885-891)
was written terse and epic-agnostic ("Database index: notice records for quick discovery")
against the *original*, unscaled Epic 10 design, which presumes a live backend Herald does not
have anywhere in this repo (a stateless CLI plus a static web dashboard, same reality Epics 8/9
already scoped around).

**Approach (scaled down, local-storage/CLI-triggered -- the effort-level scoping decision, full
rationale in `docs/dreams/herald-moments-2-4-live-backend.md`):** a new `notices.py` bridge-core
module with two files per notice, always written together:

- `notices/YYYY-MM/<type>/<component>.md` -- the durable, git-diffable record. `YYYY-MM` is the
  notice's *creation* month (never re-derived on edit). Frontmatter carries every structured
  field; the body carries `what`/`why`/`migration` under their own `##` headings. Mirrors
  `presentations/<slug>/` as a top-level, git-tracked convention this repo already uses.
- `.herald/notices-index.json` -- a local index for `list`/`get`/category+date-range filtering
  without re-globbing `notices/` on every command, atomic-write mirroring `state.py`'s temp-file
  + `os.replace` convention.

**Judgment call: the index is a full denormalized cache, not just filter metadata.** Every
`Notice` field -- including `what`/`why`/`migration` -- round-trips through the index too, not
just the markdown file. A single writer (this module) keeps both representations in lock-step on
every call, so `get_notice` never has to reopen and re-parse a markdown file. The trade-off is
explicit duplication; if the index is ever lost, it holds no information the markdown tree does
not already carry (a future `reindex` command could rebuild it -- not implemented, out of scope).

**Judgment call: edit history is two complementary trails, not one.** The index's own
`revisions: list[{edited_at, summary}]` is a cheap, fast in-index answer to "has this been
edited, when" without a git checkout; the markdown file's own git history is the full
before/after content diff for any revision, since every author/publish/close call rewrites it as
ordinary tracked text. Neither alone was judged sufficient (see Design Notes).

## Boundaries & Constraints

**Always:**
- `author_notice` validates `notice_type` against `NOTICE_TYPES = ("deprecation", "fix", "eol")`
  and `component` against a conservative slug pattern (`[a-zA-Z0-9][a-zA-Z0-9._-]*`) before
  touching the filesystem.
- The markdown file path is deterministic: `notices/<created_at[:7]>/<type>/<component>.md`.
- `_load_index_document`/`_write_index_document` mirror `state.py`'s exact atomic-write shape:
  duplicate-JSON-key rejection, a non-dict top level raises `HeraldError`, temp file in the same
  directory + `os.replace`.
- A markdown-write failure (`OSError`) raises `HeraldError` naming the path -- never silently
  skipped, since a notice with no markdown mirror would break this module's own "git-diffable
  record" contract.

**Block If:** N/A -- purely local file I/O, no network, no spike gate.

**Never:**
- No YAML library dependency added for frontmatter -- hand-rolled `key: value` lines are
  sufficient for this module's scalar fields (Simplicity First: no new dependency for a shape
  this simple).
- No live database, no server-side index, no HTTP endpoint of any kind -- Herald has none to
  extend.

## I/O & Edge-Case Matrix

| Scenario | Expected |
|---|---|
| `author_notice` with a fresh `component` | draft `Notice`, `revisions == ({"summary": "authored", ...},)` |
| Invalid `notice_type` | `HeraldError("invalid notice type ...")` |
| Invalid `component` (e.g. `"../etc/passwd"`) | `HeraldError("invalid component ...")` |
| Missing index file | treated as empty (`{"notices": {}, "redirects": {}}`), never an error |
| Corrupt/duplicate-key index JSON | `HeraldError` naming the index path |
| `get_notice` after `author_notice` (fresh index load) | full round-trip: every field matches |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/notices.py` -- create -- `Notice`
  dataclass, `NOTICE_TYPES`, `NOTICE_STATUSES`, `DEFAULT_NOTICES_DIR`, `DEFAULT_INDEX_PATH`,
  `author_notice`, index I/O helpers (`_load_index_document`/`_write_index_document`), markdown
  rendering (`_render_markdown`/`_notice_path`/`_write_markdown`). (This module also implements
  Stories 10.3's `archive_rename` and 10.6's `publish_notice`/`close_notice`/`list_notices` --
  one module, since the storage shape and the lifecycle/redirect operations over it are
  inseparable at this scale; see those stories' specs for their own intent.)
- `src/shared/packages/pyforge-herald/tests/test_notices.py` -- create -- storage round-trip,
  validation, markdown-mirror content assertions.
- `src/shared/packages/pyforge-herald/tests/test_bridge.py` -- edit -- adds `notices` to
  `_BRIDGE_CORE_MODULES` (the AD-3/AD-4 determinism-boundary sweep): local storage only, no
  transport or inference-SDK import, so it has no cause for exclusion.

## Design Notes

**Why not store `what`/`why`/`migration` only in markdown and parse it back for `get`?** A
markdown-parsing round trip (splitting frontmatter, splitting `##` sections) is real code with
real edge cases (a section header that collides with prose, frontmatter with a `:` inside a
value) for a benefit -- avoiding one field's duplication -- that Simplicity First does not judge
worth it at this scale. The index staying a full cache means `get`/`list` are pure JSON reads,
and the markdown file's only job is being the durable, human/git-reviewable mirror.

**Why not adopt a YAML frontmatter parser?** `pyyaml` is available in *some* pixi environments in
this repo but is not a declared dependency of the `pyforge-herald` feature env, and adding one
would touch `pixi.toml` (a repo-wide, out-of-`recipes/` change requiring the `maintenance` label
and an `environment.yaml` regen at PR time -- a supervising-session concern, not this story's).
Since every frontmatter field here is a single-line scalar, hand-rolled `key: value` parsing (used
by `_render_markdown`, no parser needed on read since the index is authoritative) is sufficient.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 595 passed, 2 skipped (whole
  package, after all six Epic 10 stories).
- `ruff format --check` / `ruff check` -- clean.

## Spec Change Log

## Review Triage Log

### 2026-08-08 -- Adversarial review pass (Blind Hunter + Edge Case Hunter, no shared context)

- `[high]` `[patch]` **The index was written before the markdown file in `author_notice`/
  `publish_notice`/`close_notice`.** A markdown-write failure (permissions, disk full, a
  component name long enough to hit a filesystem's filename-length limit -- reproduced
  live with a 300-character component name) left a phantom index entry pointing at a file
  that was never created; `get_notice`/`list_notices`/the web export all reported it as a
  real, live notice with no reachable content, directly contradicting this module's own
  "always written together and always in lock-step" claim. Fixed: markdown now writes
  FIRST in all three functions -- a failure there now leaves the index genuinely
  untouched. The reverse risk (a markdown-write success followed by an index-write
  failure) is strictly safer: an orphaned markdown file is invisible to every read path
  (get/list/the web export all consult the index only), never reported as live. New
  regression test: `test_author_publish_close_write_markdown_before_the_index`.
- `[medium]` `[patch]` **`_entry_to_notice` never checked that every field the `Notice`
  dataclass requires (no default) was present**, only unknown extras and a malformed
  `revisions` type -- a missing required field (e.g. a hand-edited or corrupted
  `.herald/notices-index.json`) raised a raw `Notice.__init__() missing ... argument`
  `TypeError`, not the structural `errors.HeraldError` every other corruption check in
  this function raises (AD-6). Since `dispatch()` only catches `HeraldError`, this
  propagated as an unhandled traceback through `herald notice list`/`get` instead of the
  tool's normal one-stderr-line/exit-code reporting. Fixed: added a required-fields
  presence check before construction. New regression test:
  `test_a_corrupted_index_entry_missing_a_required_field_raises_herald_error`.
- `addressed_findings`: 2 (1 high, 1 medium). No `intent_gap`, no `bad_spec`, no `defer`,
  no `reject`.
- **Reviewed and NOT applied** (a Blind Hunter finding that, on investigation, contradicts
  this module's own deliberate, already-tested design): `archive_rename` allowing
  `old_component` to already have its own live notice was flagged as "silent shadowing."
  Both `spec-10-3`'s own tests and `test_publish_follows_a_redirect` explicitly rely on
  BOTH components legitimately having pre-existing notices before a rename -- that is the
  documented normal workflow (author under the old name, author under the new name,
  redirect old -> new), not an accident. An initial patch attempting to refuse this case
  broke 8 previously-green tests and was reverted after re-reading `spec-10-3`'s own ACs.
  See `spec-10-3`'s own Review Triage Log entry for the full reasoning.

**Re-verification (2026-08-08, after this patch):** `pixi run --frozen -e pyforge-herald
pyforge-herald-test` -- 599 passed, 2 skipped; `ruff format --check`/`ruff check` clean.

**Follow-up review recommendation:** none outstanding for this story.
