---
title: "79.1: A landing promotes the story's Tier-3 feed row and its tracked spec, not only the ledger twin"
type: 'fix'
created: '2026-10-01'
status: 'in-review'
baseline_revision: '681964f299f2ca5a3562aeff55db3919b25e7dc4'
review_loop_iteration: 0
followup_review_recommended: false
warnings:
  - oversized
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Every automatic landing on 2026-09-30 (doctor 34.5, steward 76.2, scribe 25.1, marshal 74.2 and 78.1) promoted the
tracked `sprint-status-ledger.yaml` row to `done` but left the story's Tier-3 feed row
(`_bmad-output/projects/<slug>/implementation-artifacts/sprint-status.yaml`) at `backlog`, so the next plain
`sprint-ledger-sync -- --project <station>` refused ("feed would un-finish") until the feed was aligned by hand
(DW-OPS-2026-10-01-1). Separately, a session that commits its tracked story spec itself and leaves no Tier-3 twin gets no
spec promotion: finalize's scan finds no Tier-3 spec, so scribe 25.1's spec stayed at `backlog` on `main` with an empty
Review Triage Log until a hand promotion (DW-FU-53-2-4, named by DW-FU-53-3-10 and never given a row until 2026-10-01).

**Approach:**

- **Feed row:** after the ledger twin's promotion succeeds, finalize writes the same key `done` in the story's Tier-3 feed: an
  atomic replace (temp file in the same directory, `os.replace`) of the resolved feed path. A row already `done` or
  `blocked` is left as it is; a missing feed file or a missing row is a WARN finding naming the path, never a crash and
  never a new row.
- **Tracked spec:** when the landing is corroborated (the same `corroborated_merged_story_keys` gate the Tier-3 promotion
  uses) and the tracked story spec's frontmatter `status` is still pre-done, finalize sets it `done` in the promotion
  commit it already makes. A spec already `done` is untouched.
- Promotions keep writing only the ledger ref and never the operator checkout's tracked files (CAP-233); the feed lives
  under `implementation-artifacts/`, which is untracked.

Ledger key: `79-1-a-landing-promotes-the-story-s-tier-3-feed-row-and-its-tracked-spec-not-only-the-ledger-twin`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- CAP-229 (promotion runs on landing, not on memory), CAP-277 (a landing's ledger promotion reaches `origin/main`), CAP-233
  (promotion never writes the operator checkout), CAP-261 (b) (Story 53.2, the landing reconciles from git facts).
- Defects of shipped capabilities, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a landing whose story's feed row reads `backlog` When finalize promotes the twin Then the feed row reads `done` and a plain `sprint-ledger-sync -- --project <station>` reports `unchanged`
- Given the feed row is already `done`, or is `blocked` When finalize runs Then the row is unchanged
- Given no feed file, or no row for the key When finalize runs Then it reports a WARN finding naming the path, creates nothing and the landing still completes
- Given a corroborated landing whose tracked story spec reads `status: backlog` and no Tier-3 twin exists When finalize runs Then the tracked spec reads `done` in the promotion commit
- Given an uncorroborated landing When finalize runs Then neither the feed row nor the tracked spec moves
- Given the feed write is removed When the new tests run Then they fail (mutation)

## Tasks

1. Read `dispatch_land_finalize/__main__.py` (`finalize_dispatch_land`, `_promote_sprint_ledger`'s call), `core/promotion.py` and the Tier-3 scan in `cli/deploy.py`.
2. Add the atomic feed-row write after a successful twin promotion, with the done/blocked guard and the WARN paths.
3. Add the tracked-spec promotion behind the existing corroboration gate.
4. Tests with a real feed file in `tmp_path`: backlog→done, already done, blocked, missing feed, missing row, tracked-spec-only session, uncorroborated; run the mutation by hand.

## Boundaries & Constraints

**Always:**
- A promotion never moves a `done` or `blocked` row backwards.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not write the operator checkout's tracked files (CAP-233).
- Do not create a feed file or a feed row that was not there.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| feed row behind | feed `backlog`, twin promoted | feed `done` | — |
| feed row done or blocked | feed `done`/`blocked` | unchanged | — |
| no feed / no row | file or key absent | WARN naming the path | landing completes |
| tracked spec only | corroborated, spec `backlog`, no Tier-3 twin | spec `done` | — |
| uncorroborated | no merge evidence | nothing moves | — |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` -- `finalize_dispatch_land`: the only caller; after `_landed_key_not_done_finding` it gains the feed and tracked-spec steps. Reuses `_parse_sprint_ledger_statuses` (cli/land.py) and `render_ledger_advancements` (core/status.py, a byte-preserving line rewrite over the same `development_status:` shape).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py` -- `_promote_sprint_ledger` reads the feed at `root/_bmad-output/projects/<slug>/implementation-artifacts/sprint-status.yaml`, syncs it INTO the twin, advances the twin, and never writes the feed back; that is the defect. Read-only here.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` -- `corroborated_merged_story_keys` (the gate: a `dispatch/<slug>/<key>` merge is trusted; a station-branch merge needs the spec at `done` on `origin/main`), `read_spec_status`, `SPEC_STATUS_DONE`. Gains the pre-done set and a pure `set_spec_status`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` -- `spec_text_at_ref` resolves the tracked spec path then reads it at a ref; the path half is extracted as `story_spec_rel_path` for the publish.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py` -- `_scan_promotions` / `_execute_promotion_plan`: the Tier-3 scan; it finds no spec when the session committed the tracked one itself. Read-only here.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py` -- `commit_paths_onto_remote_tip`: publishes onto `origin/main` without touching the operator checkout (CAP-233); accepts only `planning-artifacts/` paths under a `preflight_skip_reason`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_finalize.py` -- `_StubVcs`, `_stub_finalize`, `_read_finalize_resync_entry`: the harness the new tests extend.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` -- add `PRE_DONE_SPEC_STATUSES` and a pure `set_spec_status(text, status)` that mirrors `read_spec_status` -- one reader and one writer of the same frontmatter value
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` -- extract `story_spec_rel_path`; `spec_text_at_ref` calls it -- the publish needs the path, not the text
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` -- compute corroboration whenever the scan has a plan; add `_promote_tier3_feed_row` and `_promote_tracked_spec`, called only when the landing is corroborated and `origin/main`'s ledger reads the key `done` -- AC 1-5
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_finalize.py` -- real feed file in `tmp_path`: backlog to done, already done, blocked, missing feed, missing row, tracked-spec-only session, uncorroborated; plus unit tests for `set_spec_status` -- the I/O matrix
- Run the mutation by hand (remove the feed write, expect the new tests red, restore) -- AC 6

**Acceptance Criteria:**
- Given the intent contract's six criteria, when `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` runs, then it passes and the mutation turns the new feed tests red

## Spec Change Log

## Design Notes

- **One gate for both writes.** `corroborated` is computed whenever the scan has a plan (it was computed only when `to_promote` was non-empty), and `key in corroborated` plus `_landed_key_not_done_finding(...) is None` gates the feed row and the tracked spec. A scan with no plan (`MRS-DEPLOY-003`) fails closed: nothing moves, no WARN. The ledger twin promotion is unchanged and still unconditional.
- **A converged twin still repairs the feed.** The gate reads `origin/main`'s ledger, not `_promote_sprint_ledger`'s return value (it is empty both for a failed publish and for an already-converged twin), so a re-run of finalize fixes a feed an earlier run left behind.
- **Feed write.** Same path `_promote_sprint_ledger` reads. Rows are matched by `normalize(raw_key) == key`; only a row that is neither `done` nor `blocked` is rewritten, through `render_ledger_advancements`, written with `fs.write_text_atomic` (mkstemp in the same directory, then `os.replace`). It is gitignored Tier-3, so it is written in place and never published. No lock: a concurrent feed writer inside the read-to-replace window can lose one update; the feed is re-derivable and the window is one small file.
- **WARN, never a crash.** A missing feed, a missing row, an unreadable or unwritable feed are `MRS-DISP-047` WARN findings naming the path (the tier this module's intake step already uses for post-merge bookkeeping); nothing is created.
- **Tracked spec.** The path is resolved against `root`, then the dispatch `worktree` (the primary's local tree may not hold a spec the merged PR added until the resync below), and read at `ORIGIN_MAIN`. A status outside `PRE_DONE_SPEC_STATUSES` (`done`, `blocked`, unreadable) is left alone, silently. The write is a separate `commit_paths_onto_remote_tip` commit, since the ledger commit returns early whenever the twin is already converged; both land on `origin/main`, never the operator checkout.

## Binding

Parent capabilities: CAP-229, CAP-277, CAP-233, CAP-261 (b) (defects; no new CAP). DW-OPS-2026-10-01-1, DW-FU-53-2-4.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-01 entry.
Ledger key: `79-1-a-landing-promotes-the-story-s-tier-3-feed-row-and-its-tracked-spec-not-only-the-ledger-twin`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: the deferral burn-down's "stop the inflow" changes run before its Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
