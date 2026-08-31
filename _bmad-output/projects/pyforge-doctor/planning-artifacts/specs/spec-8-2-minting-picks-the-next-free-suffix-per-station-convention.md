---
title: 'Story 8.2: Minting picks the next free suffix per station convention'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: '0573453855bf6b86ee4a52191320e994aa9d6645'
final_revision: '8fce539e45'
---

<intent-contract>

## Intent

**Problem:** CAP-1's id-minting algorithm (the "next free numeric suffix per
story, querying the tracked ledger's existing maximum, never restarting at
1") only exists today as prose instructions in
`.claude/skills/bmad-dev-auto/step-04-review.md` (lines ~81-98), followed
manually by an LLM agent deferring one NEW finding during a live review
pass. It has no reusable, testable code form, and it has already produced
three real near-miss duplicate-mint incidents on 2026-08-15 (`DW-10-5-1`
against an existing `DW-10-5-1..8`, `DW-10-6-1`, `DW-13-3-1`) caught and
fixed only by hand. Story 8.3's `--fix` mode needs to mint ids for many
`LEGACY_FLAT`/`LEGACY_HEADER` entries (Story 8.1's `classify_tier3_entries`
output) in one pass, against real ledgers holding hundreds of existing ids —
by-hand minting at that volume is exactly what produced the 10x-overcount
and false-orphan bugs Epic 8 exists to stop repeating.

**Approach:** Port the prose algorithm into `mint_id_for_entry(entry:
LegacyEntry, station: str, tier3_path: Path, tracked_path: Path) -> str` in
`chain.py`, beside `classify_tier3_entries`. Pure computation, no file
writes — reuses the exact station-convention/suffix-counting rules already
proven correct in step-04-review.md's prose, ported verbatim rather than
redesigned.

## Boundaries & Constraints

**Always:** Derive `{story}` from the `LegacyEntry`'s own
`fields["source_spec"]` value (the entry's recorded spec-file path/name),
using the identical derivation rule step-04-review.md already specifies:
strip a leading `spec-`, match exactly two leading numeric groups plus an
optional single trailing letter (`<digits>-<digits><letter>?`), keep the
letter, fall back to the filename stem (or parent directory name if the
stem is empty/generic: `SPEC`, `spec`, `README`, `index`) when no such key
pattern matches, sanitize to `[A-Za-z0-9-]` and collapse/trim `-`. Collect
every `DW-` token (not just headings) from BOTH `tier3_path` and
`tracked_path`, via `\bDW-[A-Za-z0-9][A-Za-z0-9-]*` + `rstrip("-")` (the
same pattern `_ids()`/`_DW_RE` already use — reuse, don't reimplement).
Compare ids as complete tokens. A collected id counts toward the suffix
only when it is exactly the base id, or the base id followed by `-` and a
remainder that is one plain integer and nothing else — judge the WHOLE
remainder, not just the last segment (mason's real `DW-1-10-1` must not
count toward base `DW-1-1`'s suffix; its remainder `0-1` is not a plain
integer). `station == "mason"` always mints a suffixed `DW-{story}-<n>`
(never bare); every other station mints bare `DW-FU-{story}` unless that
bare id or a `DW-FU-{story}-...` id was already collected, in which case
`DW-FU-{story}-<n>` one past the highest counting suffix (numeric
comparison, never lexicographic). `station` is an explicit caller-supplied
parameter, never derived from ambient active-project state (this function
must be safely callable in a loop over all 8 projects' files, unlike
step-04-review.md's own single-active-project context).

**Block If:** an entry's `fields["source_spec"]` is missing or empty (no
key to derive `{story}` from) and no other identifying field exists on the
entry.

**Never:** write to `tier3_path`/`tracked_path` — this function only
computes and returns a candidate id string; it never appends anything
(that's Story 8.3). Do not import `pyforge.marshal.core.identity` or any
other station's package for the `{story}`-derivation logic — Doctor's
detector must not import the station it judges (fleet-wide rule); reimplement
the derivation locally, matching step-04-review.md's own prose exactly.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Non-mason, no collision | station=`doctor`, no `DW-FU-7-1*` collected | `DW-FU-7-1` (bare) | none |
| Non-mason, bare already taken | station=`marshal`, `DW-FU-6-1` collected | `DW-FU-6-1-2` | none |
| Non-mason, suffixes exist | station=`marshal`, `DW-FU-10-5-1..8` collected | `DW-FU-10-5-9` | none |
| Mason, no suffix collected | station=`mason`, nothing for story `2-1` collected | `DW-2-1-1` (never bare) | none |
| Non-counting remainder ignored | `DW-1-10-1` collected, minting base `DW-1-1` | remainder `0-1`, not counted; base still free | none |
| Letter-suffixed story key | `fields["source_spec"]` derives `{story}`=`6-1a` | mints under `6-1a`, distinct from `6-1` | none |
| Missing source_spec field | entry with no `source_spec` and no fallback identity | raises/returns an explicit error, never a silent empty-token id | ValueError naming the entry |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- add `mint_id_for_entry(entry, station, tier3_path, tracked_path) -> str`, reusing `_DW_RE`/`_ids()` for token collection and porting step-04-review.md's `{story}`-derivation + suffix-counting rules as private helpers.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- new tests covering the I/O matrix, built from real ledger excerpts where practical (mirror Story 8.1's real-excerpt fixture discipline).

## Tasks & Acceptance

**Execution:**
- [x] `chain.py` -- add `_derive_story_key(source_spec: str) -> str`, porting step-04-review.md's derivation rule verbatim (leading `spec-` strip, two-numeric-group + optional-letter match, stem/parent-dir fallback, sanitize).
- [x] `chain.py` -- add `_collect_dw_tokens(tier3_path, tracked_path) -> set[str]`, reusing `_ids()`/`_DW_RE` against both files (treat a missing file as empty; propagate an `ledger-unread:`-flagged degrade for a genuinely unreadable one, matching step-04-review.md's own read-failure handling).
- [x] `chain.py` -- add `_next_free_suffix(base_id: str, collected: set[str]) -> int | None`, implementing the whole-remainder-must-be-a-plain-integer counting rule (returns `None` when only the bare base id counts, meaning "mint bare" for non-mason).
- [x] `chain.py` -- add `mint_id_for_entry(entry, station, tier3_path, tracked_path) -> str` composing the above three, with the mason-always-suffixed / other-bare-unless-taken branch.
- [x] `tests/unit/test_sources_chain_deferred_work.py` -- cover every I/O matrix row; use marshal's real tracked ledger for the `DW-10-5-1..8` / mason `DW-1-10-1` non-counting-remainder cases (read directly, real excerpts).

**Acceptance Criteria:**
- Given marshal's real tracked ledger (which carries `DW-FU-10-5-1` through `...-8`), when minting for a new orphan whose derived story is `10-5`, then the result is `DW-FU-10-5-9`, never a duplicate of any existing id.
- Given mason's real tracked ledger carrying `DW-1-10-1`, when minting for a new orphan whose derived story is `1-1`, then `DW-1-10-1` does not count toward `1-1`'s suffix (the mint is `DW-1-1-1`, not skipped past).
- Given a `LegacyEntry` with `fields["source_spec"]` unset, when `mint_id_for_entry` runs, then it raises rather than minting a phantom `DW-`-prefixed-nothing id.

## Spec Change Log

(none yet)

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 9 (high 3, medium 2, low 4)
- defer: 0
- reject: 2 (low 2)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter found `_collect_dw_tokens`'s `except Exception: continue` silently treats a genuinely-unreadable ledger as "contributes nothing" -- confirmed by `ruff` (rule S112) and architecturally contradicts this module's own established `_probe`/`_is_file` masking-prevention philosophy (3 documented prior incidents of exactly this pattern). Edge Case Hunter independently found the same clause also swallows programmer/type errors, not just I/O errors. Fix: narrow to `except OSError`, degrade visibly rather than silently on a genuine read failure (mirrors `_load_deferred_work_baseline`'s "visible on failure" precedent, the actually-analogous pattern -- not `_load_deferred_work_baseline`'s docstring citation as originally written, which Blind Hunter showed was not equivalent).
  - `[high]` `[patch]` Blind Hunter live-verified (executed against all 8 real fleet ledgers, 76 real entries) that calling `mint_id_for_entry` repeatedly for entries sharing a derived story key, without persisting between calls, produces heavy in-batch collisions (`DW-FU-6-4-2` minted 24 times in one naive pass) -- exactly Story 8.3's intended bulk-minting use case, with zero test coverage of this scenario. Root cause traces to the Approach's stated signature (inside `<intent-contract>`), but resolves via exactly one natural reading: extend the signature with an optional caller-supplied `already_minted: set[str] | None` accumulator (the caller updates it after each mint, matching the source prose's own "mint one at a time, write before minting next" discipline) -- not a redesign, so resolved as a direct patch rather than an intent_gap loopback.
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently) found `station == "mason"` is a brittle unnormalized literal comparison -- passing `"pyforge-mason"`, `"Mason"`, or a garbage/empty value all silently take the wrong (FU-prefixed) branch with no error or observable signal, corrupting mason's id shape with no symptom until a human notices. Fix: normalize (`.strip().lower()`) and validate against the known station set, raising rather than silently defaulting.
  - `[medium]` `[patch]` Edge Case Hunter found no guard against minting a fresh id for an entry that already carries one (`entry.id is not None`, i.e. an `IDENTIFIED_*` shape) -- a plausible Story 8.3 caller mistake with no current live trigger but cheap to close now. Fixed: raises if `entry.id` is already set.
  - `[medium]` `[patch]` Edge Case Hunter (unbalanced backtick, backtick-immediately-after-`.md`) + Blind Hunter (trailing parenthetical prose after a backtick-quoted filename, confirmed live in atlas's real ledger, ~19 similar lines fleet-wide) found three related boundary bugs in backtick/extension stripping in `_derive_story_key`'s source_spec handling. Not live-breaking today (no current LEGACY-shaped entry hits it), but a real latent gap in a safety-critical id-minting path. Fixed: isolate the backtick-quoted span robustly (including unbalanced/trailing-prose cases) before deriving the key.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter found `_GENERIC_STEMS` is case-sensitive exact match (`Spec.md`/`Readme.md`/`INDEX.md` not recognized as generic), inherited unmodified from the source prose rather than hardened in the port. Fixed: case-insensitive comparison.
  - `[low]` `[patch]` Blind Hunter found `_strip_spec_prefix`'s manual slice-based prefix stripping trips `ruff` FURB188 ("prefer `str.removeprefix()`"). Fixed.
  - `[low]` `[patch]` Blind Hunter found `_derive_story_key`'s post-match `if story:` guard is unreachable-by-construction after a successful regex match against an already-sanitized capture group. Fixed: simplified.
  - `[low]` `[patch]` Blind Hunter found no end-to-end test exercises mason's bare (non-suffixed) legacy id already-collected case through `mint_id_for_entry` itself (only unit-tested against `_next_free_suffix` directly). Fixed: added, bundled with the mason-normalization patch above.
  - `[low]` `[reject]` Blind Hunter found no code-level equivalent of the source prose's station/path cross-check (`readlink -f` + `projects/<slug>/` match, built to stop minting one station's id shape into another's ledger). Rejected: this Spec's own Design Notes already deliberately scope this out -- `mint_id_for_entry` is a pure library function meant to be called in a loop over all 8 projects by an explicit `station` parameter, not resolved from ambient active-project state; Blind Hunter's own conclusion independently agrees this is "defensible as an API-boundary call." Not a defect against this story's stated contract.
  - `[low]` `[reject]` Blind Hunter noted several load-bearing design claims live only in code comments citing a "Design Notes" section not visible in the diff-only review. Rejected: an artifact of the reviewer's diff-only scope, not a real gap -- the cited Design Notes exist in this spec file and do record those decisions.

## Design Notes

This is a pure, read-only computation over already-collected id sets and an
already-classified `LegacyEntry` — no file I/O of its own beyond reading
`tier3_path`/`tracked_path` for token collection (already a read-only
operation `_ids()` performs today). It stays inside `chain.py`, safely
importable by Story 8.3's future standalone `--fix` script without
inheriting a write site, matching Story 8.1's own precedent.

`station` is intentionally NOT resolved from `_bmad/scripts/resolve_config.py`
or the active-project marker inside this function — step-04-review.md's own
station-resolution ceremony (steps 1's marker-vs-symlink cross-check) exists
because that skill runs inside one ambient active project. `mint_id_for_entry`
is a library function meant to be called by 8.3 in a loop over all 8
projects' Tier-3 files in a single process; ambient state would silently
mint the wrong station's convention if called for project N while some
other worktree's marker still names project N-1. The caller supplies
`station` explicitly, derived from which project's directory it is
currently processing (a much simpler, race-free source of truth than a
mutable marker file).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary.** Added `mint_id_for_entry(entry, station, tier3_path, tracked_path,
already_minted=None) -> str` to `chain.py`, porting
`.claude/skills/bmad-dev-auto/step-04-review.md`'s id-minting prose
(`{story}` derivation, whole-DW-token collection, whole-remainder-must-be-
one-plain-integer suffix counting, mason-always-suffixed vs. everyone-else-
bare-unless-taken) into real, tested code, plus its private helpers
(`_derive_story_key`, `_collect_dw_tokens`, `_next_free_suffix`,
`_normalize_station`). Pure computation -- no file writes.

Adversarial review (executed live against real fleet data, not just static
reading) caught three HIGH-severity bugs before landing: a silent-swallow of
genuinely-unreadable ledger files as "zero tokens" (masking real read
failures the same way this module's own `_probe`/`_is_file` were built to
stop); a batch-minting collision -- the function's stated purpose is Story
8.3's bulk `--fix` mode, but calling it repeatedly for entries sharing a
derived story key without an in-batch accumulator produced 24 identical
duplicate ids against real data; and a brittle, unnormalized `station`
comparison with no validation, silently minting the wrong id shape for a
caller mistake. All three fixed and re-verified against the exact real data
that exposed them (a chmod-000 unreadable-file probe; the same 24-entry
real-data batch, now producing 24 unique sequential ids; explicit
normalization + validation tests). Two medium fixes (a missing
already-identified guard; three related backtick/`.md`-stripping boundary
bugs, one confirmed live in atlas's real ledger) and four low fixes
(case-insensitive generic-stem matching, a ruff FURB188, an unreachable
branch, an added mason end-to-end test) round out the pass.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- `mint_id_for_entry` and helpers; added to `__all__`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- new tests covering the full I/O matrix plus all nine post-review regression cases.

**Review findings breakdown** (Blind Hunter + Edge Case Hunter, deduplicated): 0 intent_gap, 0 bad_spec, 9 patch (3 high / 2 medium / 4 low, all applied and re-verified), 0 defer, 2 reject (the station/path ambient-resolution cross-check, already deliberately scoped out by this spec's own Design Notes; a reviewer note about comments citing a Design Notes section outside its diff-only view). No loopback needed -- the batch-collision finding's root cause traced to the Approach's stated signature but resolved via exactly one natural reading (an optional accumulator parameter), not a redesign.

**Follow-up review recommendation:** `true`. Three HIGH findings, one of which (the batch-minting collision) was a genuine functional defect in the code's own stated purpose, live-confirmed against real data at real volume (24x duplication) -- this is exactly the volume/consequence bar for an independent follow-up pass before Story 8.3 builds its `--fix` mode on top of this function.

**Verification performed:** `pixi run -e pyforge-doctor pyforge-doctor-test` -> 907 passed, 2 skipped (both pre-existing/expected). `ruff check --select S112,FURB188` -> clean (both review-flagged rules resolved). 5 pre-existing, unrelated ruff findings confirmed unchanged via `git stash` diff.

**Residual risks:** `mint_id_for_entry` still has zero production callers (Story 8.3 is its first) -- same accepted shape as Story 8.1's `classify_tier3_entries` and Story 6.3's `degrade_on_exception` precedent. The source prose's station/path ambient cross-check has no code equivalent by design (see Design Notes) -- Story 8.3's caller must supply a trustworthy `station` value itself.
