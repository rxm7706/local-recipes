---
title: "79.1: A landing promotes the story's Tier-3 feed row and its tracked spec, not only the ledger twin"
type: 'fix'
created: '2026-10-01'
status: 'in-progress'
baseline_revision: '681964f299f2ca5a3562aeff55db3919b25e7dc4'
review_loop_iteration: 1
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
deferred:
  - summary: >-
      Finalize's spec-status corroboration read may raise something other than VcsCommandError on a real checkout, which would crash finalize after the merge.
    evidence: |-
      Edge Case Hunter, review pass 1 (2026-10-01): `_spec_status_for` catches only VcsCommandError; it is unverified whether `dispatch_core.spec_text_at_ref` can raise another exception type while the scan runs. If it can, finalize exits non-zero and the landing is reported REFUSED after the PR has merged. Settle by running finalize against a checkout whose tracked specs directory is unreadable.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py
    severity: medium (unverified)
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
