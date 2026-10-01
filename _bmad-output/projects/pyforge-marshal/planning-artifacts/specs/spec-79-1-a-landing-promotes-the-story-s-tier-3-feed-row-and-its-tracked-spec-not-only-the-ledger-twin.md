---
title: "79.1: A landing promotes the story's Tier-3 feed row and its tracked spec, not only the ledger twin"
type: 'fix'
created: '2026-10-01'
status: 'done'
baseline_revision: '681964f299f2ca5a3562aeff55db3919b25e7dc4'
review_loop_iteration: 1
followup_review_recommended: true
warnings:
  - oversized
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py
deferred:
  - summary: >-
      The Tier-3 spec promotion in finalize classifies its candidates from the scan's pre-fetch commit subjects, so on the normal GitHub-merge path it probably never fires.
    evidence: |-
      Blind Hunter, review pass 2 (2026-10-01); the ordering was reproduced with real git in pass 1: `commit_subjects(origin/main)` lacks the merge subject until the fetch finalize makes later, and `to_promote` is classified from the same `merged_keys`. Journals: 6 of 38 finalize runs carry a `deploy-promote-commit` entry, none of the last 8. Not caused by Story 79.1, which fixes its own gate. Widening the Tier-3 gate would let `_execute_promotion_plan`'s `commit_paths` commit onto the primary checkout (CAP-233), so it needs its own Spec decision.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py
    severity: medium
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
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` -- add `PRE_DONE_SPEC_STATUSES` and a pure `set_spec_status(text, status)` that mirrors `read_spec_status` -- one reader and one writer of the same frontmatter value (KEEP from attempt 1)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` -- extract `story_spec_rel_path`; `spec_text_at_ref` calls it -- the publish needs the path, not the text (KEEP from attempt 1)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` -- AC 1-5:
  - Leave the Tier-3 promotion's own corroboration (`if scan.plan is not None and scan.plan.to_promote:`) exactly as at the baseline revision; do not widen it.
  - Add a landing-corroboration step for the two new writes that is fed FRESH evidence: it runs only after `_landed_key_not_done_finding` returned `None` (that call has just fetched `origin/main`), reads `vcs.commit_subjects(root, ORIGIN_MAIN)`, joins it with `scan.combined_subjects`, and judges `promotion.corroborated_merged_story_keys` over the join with `scan.template` and the same `ORIGIN_MAIN` spec-status reader the Tier-3 gate uses. A scan with no plan fails closed; a `VcsCommandError` on that read is an `MRS-DISP-047` WARN naming the ref and nothing moves.
  - `_promote_tier3_feed_row`: judge a row by its status TOKEN (text before any `#` comment), so `blocked  # note` is left exactly as it is; every other behavior as in attempt 1. Its docstring must not claim byte preservation for CRLF input (text reads normalise to LF).
  - `_promote_tracked_spec`: a local spec that resolves but reads `None` at `origin/main`, or whose status `read_spec_status` cannot parse (for example `status: 'backlog' # note`), is an `MRS-DISP-047` WARN naming the path and moves nothing; only a terminal status (`done`, `blocked`, `superseded`) and "no local spec resolves" stay silent. One separate `commit_paths_onto_remote_tip`, as in attempt 1.
  - The resync observation payload gains additive fields `landing_corroborated`, `feed_row_promoted` and `tracked_spec_promoted` (booleans) so a skipped promotion is distinguishable on the journal from a done one; no new finding code.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_finalize.py` -- keep attempt 1's tests and helpers; add: (a) the gate driven through the REAL `_scan_promotions` and `corroborated_merged_story_keys` with a fake `VcsPort` whose `commit_subjects(ORIGIN_MAIN)` returns the merge subject only after `fetch` was called (before it: `('base',)`), asserting the feed row and spec move; (b) the same fake never fetched or returning no merge subject: nothing moves; (c) the unmatched-row WARN (`  <key> : backlog` and a tab-indented row); (d) the tracked-spec read raising `VcsCommandError`, and a spec reading `None` at `origin/main`, and an unreadable commented status: each a WARN naming the path, exit 0, no publish; (e) the feed row parametrized over `in-progress`, `review`, `ready-for-dev` -> `done`, and `blocked  # note` / `done  # note` left byte for byte; (f) AC 1's second clause through the sync's own entry point (`cli/land.py::_load_promote_sprint_status_module`) over the tmp feed and a twin in the state a landed twin has, asserting its `unchanged` verdict, not only `regressions(...) == []`; (g) the three new payload fields
- `src/shared/packages/pyforge-marshal/tests/unit/test_promotion.py` -- keep attempt 1's tests; assert all seven `PRE_DONE_SPEC_STATUSES` members by name
- Run the mutations by hand on the FINAL tree and restore after each (`cmp` against a saved copy): remove the feed write; drop the corroboration gate; remove the spec publish; feed the gate from `scan.combined_subjects` alone. Each must turn new tests red; record the counts under Auto Run Result -- AC 6

**Acceptance Criteria:**
- Given the intent contract's six criteria, when `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` runs, then it passes and the mutation turns the new feed tests red

## Spec Change Log

### 2026-10-01 -- review pass 1 (bad_spec, loop 1)

- **Trigger:** Verification Gap finding VG1 (with Intent Alignment IA3, the same root cause): finalize's scan reads merge evidence before any fetch, so the corroboration gate that guards both new writes is closed on the normal success path while every stubbed test stays green.
- **Amended (outside the intent contract):** Tasks (the finalize gate is fed fresh `origin/main` subjects; the Tier-3 corroboration stays as at baseline; WARN paths for an unreadable or absent spec; the token-only status judgement for a commented feed row; additive observation payload fields; the test list now drives the real scan and the sync's own entry point; mutations run on the final tree), Design Notes (the gate, the reading of "the promotion commit", line endings, commented status lines).
- **Known-bad state avoided:** `corroborated` empty at scan time, so the feed row stays `backlog` and the next plain `sprint-ledger-sync` refuses again, with no signal.
- **KEEP:** `PRE_DONE_SPEC_STATUSES` and `set_spec_status` (the byte-for-byte one-token rewrite that mirrors `read_spec_status`, `ValueError` on a non-token); `story_spec_rel_path` and `spec_text_at_ref` calling it; the feed rewrite through `render_ledger_advancements` and `fs.write_text_atomic`; `_promote_tracked_spec`'s root-then-worktree path resolution, the read at `ORIGIN_MAIN` and its separate publish with a `preflight_skip_reason` naming the story; WARN-never-crash; the gate reading `origin/main`'s ledger so a re-run repairs a feed; the test helpers `_PublishVcs`, `_stub_planned_finalize`, `_journaled_findings_79` and attempt 1's tests. Attempt 1's full diff is saved at `_bmad-output/projects/pyforge-marshal/implementation-artifacts/79-1-attempt-1.patch` (gitignored Tier-3; read it, re-apply what KEEP names).

## Design Notes

- **One gate, fed fresh evidence.** `_scan_promotions` reads its merge subjects from `origin/main` and local `main` BEFORE finalize's first fetch, so right after a GitHub merge neither holds the landing's merge subject. Verified with real git on 2026-10-01: before the fetch `commit_subjects(ORIGIN_MAIN)` was `('base',)` and the key was not corroborated; after it the merge subject was visible and the key corroborated. A gate fed only by the scan therefore never opens on the normal success path and the new writes silently never fire. The new gate re-reads `origin/main`'s subjects after `_landed_key_not_done_finding`'s fetch. The Tier-3 promotion keeps the scan's subjects and its own gate untouched: widening it would let `_execute_promotion_plan`'s `commit_paths` start committing on the primary checkout, which is outside this story. A scan with no plan (`MRS-DEPLOY-003`) fails closed: nothing moves. The ledger twin promotion is unchanged and still unconditional.
- **A converged twin still repairs the feed.** The gate reads `origin/main`'s ledger, not `_promote_sprint_ledger`'s return value (it is empty both for a failed publish and for an already-converged twin), so a re-run of finalize fixes a feed an earlier run left behind.
- **Feed write.** Same path `_promote_sprint_ledger` reads. Rows are matched by `normalize(raw_key) == key`; only a row that is neither `done` nor `blocked` is rewritten, through `render_ledger_advancements`, written with `fs.write_text_atomic` (mkstemp in the same directory, then `os.replace`). It is gitignored Tier-3, so it is written in place and never published. No lock: a concurrent feed writer inside the read-to-replace window can lose one update; the feed is re-derivable and the window is one small file.
- **WARN, never a crash.** A missing feed, a missing row, an unreadable or unwritable feed are `MRS-DISP-047` WARN findings naming the path (the tier this module's intake step already uses for post-merge bookkeeping); nothing is created.
- **Tracked spec.** The path is resolved against `root`, then the dispatch `worktree` (the primary's local tree may not hold a spec the merged PR added until the resync below), and read at `ORIGIN_MAIN`. A terminal status (`done`, `blocked`, `superseded`) is left alone, silently; an unreadable status or a spec absent at `origin/main` is a WARN. `read_spec_status` rejects a commented status line such as `status: 'backlog' # note` (9 of 1227 tracked specs, most carrying the spec template's trailing comment), so such a spec is skipped with a WARN rather than rewritten; reader and writer stay one regex. The write is a separate `commit_paths_onto_remote_tip` commit. Read "in the promotion commit it already makes" as "a promotion publish onto `origin/main` that finalize already makes": the ledger commit returns early whenever the twin is already converged, and one atomic commit would mean changing `_promote_sprint_ledger`, which `marshal land` shares. The end state is the same either way; if one publish fails it is a WARN and a re-run of finalize repairs it, since the gate and the status check are idempotent. Both publishes land on `origin/main`, never the operator checkout.
- **Line endings.** The feed and the spec round-trip through text reads, so CRLF input comes back LF-normalised (reproduced 2026-10-01). No tracked spec is CRLF (0 of 1227) and the feed is generated on Linux, so this is a documented limit, not a guard.

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

### 2026-10-01 -- Review pass
- verdicts: 35 findings -- high 1, medium 8, low 21, false 4, maybe-false 1
- findings:
  - Blind Hunter
  - `[medium]` `[patch]` Spec promotion skips silently when no spec resolves, origin/main has no copy, or the status is unreadable -- reproduced: 9 of 1227 tracked specs are unreadable by `read_spec_status` (a commented status line, from the spec template); folded into Tasks: WARN naming the path, silent only for terminal statuses and "no local spec"
  - `[low]` `[bad_spec]` The contract says "in the promotion commit it already makes", the code publishes a second commit -- both readings reach the same end state and a re-run repairs a failed publish; amended Design Notes state the reading and why; shares the route with EC8, VG6 and IA1
  - `[low]` `[reject]` The feed guard is a denylist (`done`/`blocked`) where the spec guard is an allowlist -- the intent contract names exactly done and blocked, and the twin promotion (`_raw_keys_needing_done`, `cli/land.py`) advances every non-done row of a landed key; an allowlist would diverge from the twin
  - `[low]` `[reject]` `MRS-DISP-047` reused for feed and spec findings -- `_run_deferred_work_intake` in the same module already uses it as the non-gating post-merge bookkeeping tier (Story 53.2); a new code is registry surface beyond an S-sized fix
  - `[medium]` `[patch]` Four new branches have no test -- two reproduced (the unmatched-row WARN via `  <key> : backlog` and a tab-indented row; a commented row); folded into the test list with the spec-read failure; the `relative_to` ValueError branch is `spec_text_at_ref`'s own logic moved verbatim and unreachable (the path is built from the canonical root), so it gets no test
  - `[low]` `[reject]` `set_spec_status` could rewrite a nested `status:` line -- probed all 1227 tracked specs: the reader picks a nested line in 0; anchoring the writer alone would split reader and writer
  - `[low]` `[reject]` Unlocked read-modify-write of the shared feed -- the window is one small file between read and `os.replace`; a writer outside marshal (bmad-loop) would not honour an advisory lock; accepted in the Design Notes and re-derivable with `--repair-feed`
  - `[medium]` `[patch]` Nothing positive is journaled, so a skipped promotion looks like a done one -- that is exactly why the stale-scan defect (VG1) was invisible; folded into Tasks: additive `landing_corroborated`, `feed_row_promoted`, `tracked_spec_promoted` payload fields; groups with EC7
  - `[low]` `[patch]` "Byte-preserving" overstated for CRLF -- reproduced, a CRLF feed comes back LF-normalised; folded into Tasks and Design Notes as wording, no behaviour change (0 of 1227 tracked specs are CRLF)
  - `[low]` `[patch]` No memlog reconcile, stamp or DW flips in the diff -- the memlog entries naming the governed paths on `spec-pyforge-marshal` and `spec-pyforge-core` are owed by this run and are written at Finalize; the DW status flips and the Realization entry belong to the landing and the operator, not this diff
  - `[low]` `[patch]` AC 6's mutation run has no recorded evidence -- the mutations are re-run on the final tree and recorded under Auto Run Result (Tasks)
  - `[low]` `[reject]` `DW-OPS-2026-10-01-1` is ambiguous across two ledgers -- the id is the intent contract's own citation; cosmetic
  - `[low]` `[patch]` Typing and style slips -- `to_promote: tuple = ()` loses the element type, moot once the Tier-3 block is restored to baseline structure (annotate it if the variable is reintroduced); the other items follow the file's existing untyped `monkeypatch` style and `lint-types` is green
  - Edge Case Hunter
  - `[medium]` `[patch]` A feed row `blocked  # note` is rewritten to `done  # note` -- reproduced; breaks the Always boundary for a reachable input (no ledger carries such a comment today); folded into Tasks: judge the status token only; groups with EC9
  - `[low]` `[reject]` Rows at `in-progress`, `optional`, `superseded` are forced to `done` -- same reasoning as the denylist finding: the contract protects done and blocked only, and the twin does the same for a landed key
  - `[low]` `[reject]` A story key on an earlier line outside `development_status:` makes the rewrite mutate the wrong line -- reproduced, but needs a feed carrying the key outside the block (generated feeds do not) and the guard adds branching; the same `render_ledger_advancements` exposure already exists in `_promote_sprint_ledger`
  - `[low]` `[reject]` The primary's stale-named local spec shadows the worktree's -- needs a renamed spec present only in the primary tree; the new WARN on an origin/main miss makes it visible; iterating candidates is more than a direct correction
  - `[low]` `[reject]` Publishing the whole spec from text read earlier can overwrite a concurrent edit -- only this story's own landing edits its tracked spec, and the window is the publish's own fetch
  - `[maybe-false]` `[defer]` Corroboration now runs on every finalize with a plan, so a non-`VcsCommandError` from the spec read could crash it -- unverified; settle by running finalize against a checkout whose tracked specs directory is unreadable; recorded in `deferred:` as medium (unverified); the Tier-3 gate is restored to baseline, so only the new gate's own reads matter and those warn on `VcsCommandError`
  - `[medium]` `[patch]` An uncorroborated landing leaves no trace of why the feed stayed `backlog` -- folded with BH8 as the `landing_corroborated` payload field; AC 5's test keeps asserting no findings, so no new WARN
  - `[low]` `[bad_spec]` Claim: the Approach says the spec is promoted "in the promotion commit it already makes" but a second commit is made -- same defect as the Blind Hunter row; amended Design Notes state the reading
  - `[medium]` `[patch]` Claim: "a row already done or blocked is left as it is" fails for a commented blocked row -- reproduced; fixed with EC1
  - Verification Gap
  - `[high]` `[bad_spec]` The real scan to `key in corroborated` gate is never exercised, and the scan runs before finalize's first fetch -- reproduced with real git and `GitVcs`: before the fetch the key is not corroborated, after it it is; `dispatch_land.py` fetches only before the merge and on a failed merge, so on the normal path the new writes never fire; amended Tasks and Design Notes (the gate re-reads `origin/main`'s subjects after the fetch; the Tier-3 gate is left untouched), Spec Change Log entry written
  - `[low]` `[patch]` The unmatched-row WARN has no test -- reproduced reachable (space before the colon, tab indent); test added to Tasks
  - `[low]` `[patch]` The tracked-spec read-failure WARN has no test -- test added to Tasks
  - `[low]` `[patch]` Feed rows other than `backlog` are never exercised -- feed test parametrized in Tasks over `in-progress`, `review`, `ready-for-dev`
  - `[low]` `[patch]` The `PRE_DONE_SPEC_STATUSES` test pins five of seven members -- Tasks require all seven by name
  - `[low]` `[bad_spec]` Other: the contract text and the shipped commit shape disagree -- same defect as the Blind Hunter row; amended Design Notes
  - Intent Alignment (its divergences, one row each)
  - `[low]` `[bad_spec]` The spec is published in its own commit and with no intent/outcome pair, where the contract says "the promotion commit" -- same defect as the Blind Hunter row; the deferred-work-intake publish in the same module writes no pair either, so only the reading is amended
  - `[medium]` `[patch]` AC 1's "plain sync reports unchanged" is checked through `regressions(...)` on a hand-written twin, not the sync's own verdict -- Tasks now require the sync's own entry point over the tmp feed and a landed-state twin
  - `[medium]` `[bad_spec]` Almost every finalize test stubs the scan, the promotion, the resync and git, so the corroboration gate was never exercised -- the same root cause as VG1; Tasks add tests driving the real scan and the real gate with a fake `VcsPort`
  - `[false]` `[reject]` The feed path is not symlink-resolved -- `implementation-artifacts/` is a directory-level symlink (AGENTS.md); `os.replace` of a same-directory temp file renames inside the target directory, and the feed file itself is not a symlink
  - `[false]` `[reject]` The feed is read and written under `root`, not the worktree -- it is the exact path `_promote_sprint_ledger` reads and `sprint-ledger-sync` reads, and the worktree's directory is a link to the same store
  - `[false]` `[reject]` An uncorroborated landing still leaves the twin `done` and the feed `backlog` -- AC 5 requires that, and the twin promotion's unconditionality is pre-existing and outside the contract
  - `[false]` `[reject]` A `blocked` feed row leaves a plain sync refusing -- AC 2 and the Always boundary require `blocked` untouched; the sync's done-to-blocked refusal is its own guard working as designed

- the `patch` rows above were folded into the amended Tasks and applied in the loop-1 re-derivation; the review pass below read them back

### 2026-10-01 -- Review pass (loop 1, after the re-derivation)
- verdicts: 31 findings -- high 0, medium 5, low 23, false 3, maybe-false 0
- carried rows (marked `carried`) were resolved by the loop-1 amendments and are not re-processed; the `bad_spec` ones among them owe no further re-derivation
- findings:
  - Blind Hunter
  - `[medium]` `[defer]` The Tier-3 promotion gate is fed the scan's pre-fetch subjects, the same stale evidence this story fixed for its own gate -- the ordering was reproduced with real git in pass 1, and `to_promote` is classified from the same `merged_keys`, so that promotion probably never fires on the normal path (journals: 6 of 38 finalize runs carry a `deploy-promote-commit`, none of the last 8); not caused by this change, and widening it would let `commit_paths` commit onto the primary checkout (CAP-233), a named blocker outside an S-sized fix; recorded in `deferred:`
  - `[low]` `[patch]` The `deferred:` entry from pass 1 contradicts the Auto Run Result -- probed myself: with the specs directory `chmod 000` on Python 3.14, `story_spec_rel_path` returns `None` and does not raise, so the pass-1 deferral is refuted; the entry is withdrawn (it would mint a false open DW row on landing) and the entry from row 1 replaces it; groups with row 19 -- fix applied: the pass-1 entry is removed from `deferred:` and the Tier-3 stale-gate entry stands in its place.
  - `[false]` `[reject]` No independent re-review of the redesign -- this pass is that review: four fresh reviewers read the redesigned diff after loop 1
  - `[low]` `[reject]` The spec points at a gitignored patch and says "attempt 1" -- the fix is to edit this build's spec; the Spec Change Log is a dated record and labels the patch as gitignored Tier-3
  - `[low]` `[bad_spec]` carried: AC 4 says "the promotion commit", the code publishes a second commit -- amended in loop 1 (the Design Notes state the reading and why); not re-processed; the operator's ratification of that reading is named as a residual risk under Auto Run Result
  - `[low]` `[reject]` "A re-run repairs it" has no trigger -- a failed publish or unwritable feed is an `MRS-DISP-047` WARN on the journal; the Design Notes say a re-run repairs it, not that one happens unprompted, and an automatic retry is machinery beyond an S-sized fix
  - `[medium]` `[patch]` The new gate is correct only because `_landed_key_not_done_finding` happens to fetch, named in a comment alone -- an edit there would silently reopen the stale-gate defect; the gate must fetch `origin/main` itself -- fix applied: `_landing_corroboration` calls `vcs.fetch(root, "origin", "main")` itself and a failed fetch is the `MRS-DISP-047` WARN; tests: the gate fetches for itself, a failing fetch moves nothing; the mutation that stops the fetch turns 3 tests red.
  - `[low]` `[patch]` Two status sets live apart (`_TERMINAL_SPEC_STATUSES` in `__main__.py`, `PRE_DONE_SPEC_STATUSES` in `promotion.py`) -- a status in neither set would drift between the two; the terminal set moves beside the other; `_origin_main_spec_status` stays a deliberate copy of the inline Tier-3 reader because that block is left byte-identical (its docstring says so) -- fix applied: `TERMINAL_SPEC_STATUSES` now lives in `core/promotion.py`; the tests use both constants and assert they are disjoint.
  - `[low]` `[reject]` carried: the feed guard is a denylist, the spec guard an allowlist -- carried from loop 1 (the contract names done and blocked only and the twin does the same for a landed key); checked now: ledgers carry done 1398, optional 297, backlog 123, blocked 22, in-progress 15 and no `superseded`, so an `optional` row under a corroborated landing is a story that landed; `_landed_key_not_done_finding` is unchanged baseline code
  - `[low]` `[reject]` The journal booleans cannot say why nothing moved -- a failed write carries its finding, and a done or blocked row and a story with no local spec are intentional silent no-ops; a reason enum is new payload surface
  - `[low]` `[reject]` No INTENT/OUTCOME pair around the spec publish -- the publish is idempotent (a re-run reads `done` and does nothing), the commit is itself the durable record, and the module's other post-merge publish (`_run_deferred_work_intake`) writes no pair either
  - `[low]` `[reject]` carried: concurrent writers can lose a feed update -- carried from loop 1: one small file between read and `os.replace`, a writer outside marshal would not honour an advisory lock, and the feed is re-derivable
  - `[low]` `[patch]` Reproduced defects rejected as pre-existing -- the wrong-line feed write is this change's own defect (the new call site applies `render_ledger_advancements` to the feed; reproduced in loop 1), so that rejection is reversed: re-parse the rewritten text and require the row to read `done` before writing, else a WARN; the stale-named local spec stays rejected because, since loop 1, a miss at `origin/main` is a WARN naming the path -- fix applied: `_promote_tier3_feed_row` re-parses the rewritten text and writes nothing unless every matched row reads `done` (a WARN otherwise); a test with the key under `notes:`; the mutation that drops the check turns 1 test red.
  - `[medium]` `[patch]` Test gaps -- the central stale-scan defect is pinned only by a hand-written model of git, and the adapter's planning-artifacts-only proof never runs against the path `story_spec_rel_path` yields; one real-git test is added (a bare origin, the real `GitVcs` and `commit_paths_onto_remote_tip`); the vacuous `other.is_file()` assertion goes; the `blocked  # note` guard and the fail-closed status read join the mutation list; the other nits (a literal ref in an assertion, `tuple = ()` on a test stub, the sync test reading the script's output) follow the file's existing style -- fix applied: a real-git test in `test_dispatch_land_finalize.py` (bare origin, real `GitVcs`, real `commit_paths_onto_remote_tip`; `origin/main`'s spec blob reads `done`, the primary untouched); the vacuous `other.is_file()` assertion is removed (it sat in `test_dispatch_land_finalize.py`); the two added mutations turn 3 and 1 tests red.
  - `[low]` `[patch]` carried: dead code and bookkeeping owed -- carried from loop 1: the memlog entries naming the governed paths on `spec-pyforge-marshal` and `spec-pyforge-core` are written at Finalize and the guard re-run (it passes now because older entries already contain the path strings, so it proves nothing about this change); the `story_spec_rel_path` ValueError branch is `spec_text_at_ref`'s own logic moved verbatim and stays untested; the journal fields are not CLI grammar, so SKILL.md is untouched -- fix applied: memlog entries naming every changed path are appended to `spec-pyforge-marshal` and `spec-pyforge-core` through `memlog.py`; no baseline was stamped; `spec_surface_reconcile.py` and the doctor `spec-surface` source both exit 0.
  - Edge Case Hunter
  - `[low]` `[reject]` A station-branch merge whose PR added the spec is never corroborated from the primary's local tree -- `spec_status_for` is called only for the station-branch shape, and finalize runs only after `dispatch_land` merges the `dispatch/<slug>/<key>` branch, a shape trusted without a spec read; the Tier-3 gate has the same limit
  - `[low]` `[reject]` A quoted feed status keeps its quotes in the token -- every ledger row is a bare token (probed: done, blocked, backlog, optional, in-progress), and the twin parser and rewriter treat quotes as part of the token everywhere
  - `[low]` `[reject]` CRLF, bare CR or non-UTF-8 spec bytes would not round-trip -- CRLF carried from loop 1 (a documented limit); probed all 1227 tracked specs: 0 fail strict UTF-8 and 0 are CRLF
  - `[low]` `[patch]` Claim: the deferred item is settled yet still in `deferred:` -- the same finding as row 2; withdrawn there -- fix applied: withdrawn together with row 2.
  - `[low]` `[bad_spec]` carried: claim that the spec is promoted "in the promotion commit" but a second commit is made -- the same defect as row 5; amended in loop 1; not re-processed
  - `[low]` `[patch]` Claim: `set_spec_status` says every line ending comes back byte for byte, but production text arrives LF-normalised -- the docstring gains the sentence; no behaviour change -- fix applied: the docstring gains the sentence.
  - Verification Gap
  - `[low]` `[patch]` The Tier-3 route and the new tracked-spec step are never run together -- read from code: `_execute_promotion_plan` copies the Tier-3 spec into the primary's `specs/` and commits it locally, so `story_spec_rel_path` resolves that copy while `origin/main` may not hold it, giving a misleading "does not exist at origin/main" WARN or a second status-only publish; AC 4 says "no Tier-3 twin exists" and nothing enforces it; the step is skipped for a key the Tier-3 route promoted this run, with a test through the real executor -- fix applied: `finalize_dispatch_land` skips `_promote_tracked_spec` for a key in `to_promote`; a test over the real `_scan_promotions` and `_execute_promotion_plan`; the mutation that drops the skip turns 1 test red.
  - Intent Alignment (its divergences, one row each)
  - `[low]` `[reject]` Two corroboration verdicts in one finalize -- deliberate and documented in the Design Notes; the disagreement they can produce is row 1's deferral
  - `[low]` `[bad_spec]` carried: the tracked spec is published in its own commit -- the same defect as row 5; amended in loop 1; not re-processed
  - `[false]` `[reject]` "After the twin's promotion succeeds" is judged on `origin/main`'s ledger, not the call's success -- that is a defensible reading the contract allows, and a failed promotion exits 1 with `MRS-DISP-051` and moves nothing
  - `[medium]` `[patch]` carried: an uncorroborated landing leaves the incident state and only a boolean says so -- carried from loop 1 (the `landing_corroborated` payload field is the implemented signal; AC 5's test keeps asserting no findings) -- fix applied (loop 1): the `landing_corroborated` payload field.
  - `[low]` `[reject]` `marshal land` and `deploy` do not write the feed row -- the contract scopes the fix to finalize and its automatic landings; no defect is shown for those paths
  - `[low]` `[reject]` carried: spec status coverage (denylist against allowlist, nine specs with a commented status) -- carried from rows 9 and loop 1; those nine specs now get a WARN naming the path
  - `[medium]` `[patch]` The tests run in-process on a fake `GitVcs`, and the real-git reproduction exists only as prose -- the same root as row 14; the real-git test covers it -- fix applied: the real-git test (see Test gaps).
  - `[low]` `[patch]` The spec publish is asserted on the recorded `writes`, not on a git ref -- covered by the same real-git test: `origin/main`'s spec blob reads `done` and the primary's working tree is untouched -- fix applied: the same real-git test asserts the blob on `origin/main`.
  - `[false]` `[reject]` AC 6's mutation is by hand and recorded as prose -- the contract and Tasks say "run the mutation by hand"

## Auto Run Result

Status: done

**Summary.** After a corroborated landing, `dispatch_land_finalize` now writes the landed story's Tier-3 feed row `done` and publishes the story's tracked spec `done` onto `origin/main`, so the next plain `sprint-ledger-sync` has nothing left to refuse and no spec stays at `backlog` on `main`. Both writes sit behind one gate that fetches `origin/main` for itself and judges `corroborated_merged_story_keys` over the fresh history joined with the scan's. Review pass 1 found that the scan reads its merge evidence before finalize's first fetch (reproduced with real git), which would have kept the gate shut on the normal path while every stubbed test stayed green; that routed `bad_spec`, the code was reverted and re-derived from the amended spec, and a second review pass found only patch-class items, applied below.

**Files changed** (all under `src/shared/packages/pyforge-marshal/` unless noted):
- `src/pyforge/marshal/dispatch_land_finalize/__main__.py` -- `_landing_corroboration`, `_promote_tier3_feed_row`, `_promote_tracked_spec`, the three observation fields `landing_corroborated`, `feed_row_promoted`, `tracked_spec_promoted`; the Tier-3 promotion block is untouched.
- `src/pyforge/marshal/core/promotion.py` -- `PRE_DONE_SPEC_STATUSES`, `TERMINAL_SPEC_STATUSES`, the pure `set_spec_status`.
- `src/pyforge/marshal/core/dispatch.py` -- `story_spec_rel_path`, called by `spec_text_at_ref`.
- `tests/unit/test_dispatch_land_finalize.py`, `tests/unit/test_promotion.py`, `tests/unit/test_dispatch.py` -- the tests, including one real-git test.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` and `.../spec-pyforge-core/.memlog.md` -- surface-reconcile entries naming every changed path.
- This story spec -- Code Map, Tasks, Design Notes, Spec Change Log, Review Triage Log, this section.

**Review findings.** Two passes, 35 findings in pass 1 (high 1, medium 8, low 21, false 4, maybe-false 1) and 31 in pass 2 (medium 5, low 23, false 3).
- Pass 1: 1 `bad_spec` group (the stale scan; 6 rows) forced the loopback; 15 `patch` rows were folded into the amended Tasks and applied in the re-derivation; 1 `defer`, later withdrawn (refuted by a probe).
- Pass 2: 12 `patch` rows applied (patched entries at entry verdict: medium 2, low 5); 1 `defer` (the Tier-3 spec promotion is fed pre-fetch subjects, so it probably never fires on the normal path; recorded in `deferred:` with its location); 3 carried `bad_spec` rows owe nothing further.
- Rejected, with the reason recorded in the Review Triage Log:
  - Pass 1: the feed denylist against the spec allowlist (the contract names done and blocked only; the twin does the same); `MRS-DISP-047` reuse (precedent in the same module); a nested `status:` rewrite (0 of 1227 specs); the unlocked feed write (narrow window; a writer outside marshal ignores locks); the ambiguous DW id (cosmetic); forced non-backlog rows (same as the denylist); a key outside `development_status:` (rejected then, reversed in pass 2 and fixed); a stale-named local spec (rare; now a WARN); a concurrent spec edit (only its own landing edits it); four Intent Alignment divergences judged `false` (symlink-resolved path, feed read under `root`, an uncorroborated landing leaving the incident state as AC 5 requires, a `blocked` row leaving the sync refusing as AC 2 requires).
  - Pass 2: no independent re-review (this pass is it); the gitignored patch reference (fixing it edits the build's spec); no retry trigger for a failed publish; the denylist again (ledgers carry done 1398, optional 297, backlog 123, blocked 22, in-progress 15, no `superseded`); the journal booleans cannot say why (new payload surface); no INTENT/OUTCOME pair around the spec publish (idempotent; the module's other publish writes none); concurrent feed writers; a station-branch spec lookup (finalize only sees a trusted shape); a quoted feed status (every ledger row is a bare token); non-UTF-8 or CRLF specs (0 of 1227 each); two corroboration verdicts (deliberate, documented); `marshal land` and `deploy` (the contract scopes the fix to finalize); the ordering reading "after the twin's promotion succeeds" (a defensible reading); AC 6's mutation recorded as prose (the contract says by hand).

**Follow-up review recommendation: `true`.** Two medium entries were patched in this pass (the gate's own fetch; the test gaps). The unverified risk: the explicit `vcs.fetch` in `_landing_corroboration`, the Tier-3 skip, the post-rewrite re-parse and the real-git test were added after the last independent review, and no reviewer has read that patched code; the full suite and nine mutations cover it.

**AC 6 -- mutations run by hand on the final tree** (the three touched test files, 284 tests; the source restored and `cmp`-checked after each):
- remove the feed write: 21 red; drop the corroboration gate: 4 red; remove the spec publish: 12 red; feed the gate from `scan.combined_subjects` alone: 43 red.
- compare the raw feed status instead of the token (`blocked  # note` is rewritten): 3 red; treat a `VcsCommandError` on the status read as `done`: 1 red.
- extra: the gate stops fetching for itself: 3 red; drop the Tier-3-promoted-key skip: 1 red; drop the post-rewrite re-parse: 1 red.

**Verification performed** (exit codes read from files, never through a pipe):
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 9259 passed, 1 skipped, 12 deselected, exit 0.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` -- exit 0.
- `python3 scripts/spec_surface_reconcile.py` -- exit 0 before and after the memlog entries; the doctor `spec-surface` source -- exit 0. That guard also passed before any memlog entry, because older entries already contain the path strings, so its green says nothing about this change; the entries were written regardless.
- Probes with real git and real data: the stale-scan ordering (before the fetch the key is not corroborated, after it it is), a CRLF feed comes back LF-normalised, 9 of 1227 tracked specs have a status line `read_spec_status` cannot parse (they now get a WARN), 0 specs fail strict UTF-8, and an unreadable `specs/` directory returns `None` from `story_spec_rel_path`.

**Residual risks.**
- The operator has not ratified the reading of "the promotion commit" as "a promotion publish onto `origin/main`"; the tracked spec lands in its own commit, and a failed publish is a WARN that only a finalize re-run repairs.
- The first real landing after this merges is the real proof; until then the gate's behaviour on a live GitHub merge rests on the real-git reproduction and test.
- Every corroborated landing with no feed file now journals one `MRS-DISP-047` WARN, as the contract requires; it will show in fleet output.
- The Tier-3 spec promotion probably never fires on the normal path; deferred, and widening it would let `commit_paths` commit onto the primary checkout.
- CRLF input comes back LF-normalised on the feed and the spec (a documented limit; none exists today).
- Owed to the landing and the operator, not this diff: the `DW-OPS-2026-10-01-1` and `DW-FU-53-2-4` status flips and the Dream Realization-log entry. No baseline was stamped.
