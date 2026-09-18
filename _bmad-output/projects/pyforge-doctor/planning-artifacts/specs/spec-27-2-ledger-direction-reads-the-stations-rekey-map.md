---
title: '27.2: `ledger-direction` reads the station''s rekey map'
type: 'fix'
created: '2026-09-18'
status: 'in-review'
baseline_revision: '9a89b3ec873957676b8c76accd159bc0be21d5d9'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `gather_direction` compares keys parsed from merge history straight against the tracked ledger, so a station that renumbered its stories (atlas, `rekey-2026-09-17.md`: 13-5 → 12-5-…, 14-4 → 13-4-…, 15-3 → 14-3-…) reads its own bmad-loop merges as `landed-but-unpromoted` — three live rows on today's `main`. `gather()` has applied the rekey maps since Story 25.3; `gather_direction` never did.

**Approach:** Pass every merge-history key through the station's `rekey-*.md` maps (via `pyforge.doctor.rekey.parse_rekey`, the reader `gather()` uses) before the ledger comparison; an unreadable or malformed map is a WARN naming the file.

## Boundaries & Constraints

**Always:**
- `ledger-direction-check` on today's `main` reports no atlas `landed-but-unpromoted` row; a fixture with a rekey map and a merge naming the old key reports nothing; the same fixture without the map reports the row (mutation test).
- An unreadable or malformed rekey map is a WARN that names the file — never a silent pass, never a crash; the exit-code domain `{0, 2, 130}` is untouched.

**Never:**
- Do not re-implement rekey parsing — reuse `pyforge.doctor.rekey.parse_rekey` and the `_rekey_paths` discovery `gather()` already has.
- Do not soften any other `ledger-direction` verdict; every other source stays advisory.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| renumbered station | merge names old key; map says old → new; new is done | no finding | n/a |
| no map | same merge, no rekey-*.md | `landed-but-unpromoted` | n/a |
| broken map | rekey-*.md unparseable | WARN `rekey-map-unreadable` naming the file | never crash |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-79`.
Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py` (`gather_direction`); `tests/unit/test_sources_ledger_direction.py`.
Ledger key: `27-2-ledger-direction-reads-the-stations-rekey-map`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-27-2-ledger-direction-reads-the-stations-rekey-map.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- `pixi run -e pyforge-guild ledger-direction-check` on `main` exits 0 with no `pyforge-atlas/13-5`, `14-4` or `15-3` row.

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 11 findings — high 0, medium 3, low 5, false 3, maybe-false 0
- findings:
  - `[medium]` `[patch]` `_rekey_sid_maps` resolves only one hop of a rekey chain: a station re-keyed twice (two separate `rekey-*.md` files, e.g. `a -> b` then `b -> c`) still misreads a merge naming the oldest spelling `a` as `landed-but-unpromoted` — the same package's sibling `rekey.reverse_map` (`rekey.py:108-123`) already fixpoint-walks exactly this chain shape and its docstring names it as the anticipated case; `_rekey_sid_maps` does a flat single `project_map[old_sid] = new_sid` per line with no chase. Concretely demonstrated by the verification-gap layer: two chained maps `13-5->12-5`, `12-5->11-5`, a merge naming `13-5`, ledger done at `11-5-...` — none of the 4 new tests construct this, all use exactly one map file. Fix: walk `project_map` to a fixed point (mirroring `reverse_map`'s hop-walk) before returning it. **Applied:** added a hop-walk (capped at 64, mirroring `reverse_map`) that resolves every `project_map` entry to its fixed point before returning; new test `test_chained_rekey_maps_resolve_to_current_key` pins it.
  - `[medium]` `[patch]` (blind-hunter, same root cause) No test exercises the multi-hop/chained-rename scenario — every `_write_rekey` call site in the new tests passes exactly one map file, so the single-hop limitation above ships uncovered. **Applied:** covered by the same new test.
  - `[medium]` `[patch]` (edge-case-hunter, same root cause) `ledger.py:733-782`: "a station ships a second rekey file renumbering an already-renumbered sid" reaches the identical single-hop gap. **Applied:** covered by the same hop-walk fix and test.
  - `[medium]` `[patch]` (verification-gap, same root cause) `ledger.py:776-781` / `899-901`: filed the concrete reproduction above with line citations to both the map-building loop and its one-shot `.get()` lookup; disposition filed pre-verified per this layer's evidence rules. **Applied:** covered by the same hop-walk fix and test.
  - `[low]` `[reject]` Grain-reducing both sides of every rekey line to `<epic>-<seq>` (`_story_id`) risks a silent overwrite in `project_map` if two full keys reduce to the same grain, with no WARN — `parse_rekey`'s own duplicate/collision detection runs on full pre-reduction strings so can't catch it. Checked against real data: this repo's station rekey maps mint one canonical `<epic>-<seq>` per real story (minting picks the next free suffix per station convention), so two distinct stories sharing a grain would itself be a pre-existing minting bug, not something this diff can trigger; a guarding fix would need new collision-tracking state (branches/params), which is more than a direct correction — rejected on both unlikely-in-practice and non-trivial-fix grounds.
  - `[low]` `[reject]` `_rekey_sid_maps` duplicates most of `_new_rekey_maps`'s body (unreadable-blob and malformed-map branches) instead of sharing a helper — a real drift risk if the two message formats diverge later, but the fix (extracting a shared reader) is a refactor, not a direct correction, and today's behavior is correct; rejected as low + fix-more-than-trivial.
  - `[low]` `[patch]` Dead fallback `project = m.group(1) if m else path.split("/")[2]` (`ledger.py:736`) is unreachable: `path` always comes from `_rekey_paths`, which already filters with `_REKEY_RE.match`, so `m` can never be `None`. Fix: drop the `else` branch (direct deletion, trivial). **Applied:** replaced with `project = _REKEY_RE.match(path).group(1)`.
  - `[false]` `[reject]` `_rekey_sid_maps` reads rekey maps only from the committed blob at `base_ref`, never the working tree, allegedly letting a same-run comparison mis-fire before a new map lands on `base_ref`. Refuted: this exactly mirrors the pre-existing convention that merge `subjects` themselves are also read only from `base_ref`'s committed history (`_git(target, "log", ..., base_ref)`), not the working tree — consistent with, not a regression from, how `gather_direction` already worked before this diff.
  - `[false]` `[reject]` (edge-case-hunter) `ledger.py:899-901`: claims a merge naming a post-fold sid could collide with an unrelated story's still-live pre-fold sid. Refuted: for any sid that is not a rekey-map key, `sid_map.get(sid, sid)` is a no-op — bit-for-bit the same lookup path `gather_direction` had before this story, so this diff cannot introduce or worsen such a collision. Also checked concretely against the real atlas map: old epic 12 only ever had stories `12-1..12-3`, so there is no un-translated old `12-5` merge that could collide with the new (translated) `12-5` the reviewer's terse JSON gestured at.
  - `[false]` `[reject]` (edge-case-hunter) `ledger.py:776-781`: claims a syntactically valid rekey line that doesn't reduce to the `<epic>-<seq>` grain (a "legacy alias id") gets silently dropped from translation. Refuted on two counts: (1) checked all 8 live `rekey-*.md` files in this repo — the only lines that fail to reduce are paired `epic-N -> epic-M` lines (both sides fail together, e.g. atlas's own map), never an asymmetric line where one side is a real story id and the other isn't; those epic-level lines are a documented separate use of the same grammar (epic-doc renaming), not story-id translation. (2) Even if it happened, the fallback is `sid_map.get(sid, sid)` leaving the id untranslated — identical to the already-accepted "no map" baseline behavior in this spec's own I/O matrix, not a new or worse outcome.
  - `[low]` `[patch]` (edge-case-hunter) `ledger.py:846-860`: when a target has zero tracked `sprint-status-ledger.yaml` files anywhere, `gather_direction` returns early (`if not ledger_paths: return (...)`, line 845) *before* `_rekey_sid_maps` is ever called (line 856) — a malformed or unreadable rekey map in that repo never surfaces its WARN, contradicting the spec's "never a silent pass" boundary in that narrow window. Fix: compute `rekey_maps, rekey_problems` before the `ledger_paths` early return and include `rekey_problems` in that return's findings (direct, trivial reordering). **Applied:** `_rekey_sid_maps` is now called before the `ledger_paths` check, and `rekey_problems` are spliced into the early-return tuple.
