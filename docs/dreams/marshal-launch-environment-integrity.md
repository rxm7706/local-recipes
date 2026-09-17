---
title: Marshal trusts the environment it launches into — until it silently doesn't
type: dream
owner: marshal
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-marshal]]** on 2026-09-16 (one-chain-per-station CAP-8 pilot; folded from `marshal-launch-environment-integrity`).

# Marshal trusts the environment it launches into — until it silently doesn't

## The Dream

`factory dispatch` and `factory spin` both promise the same shape: launch a
detached, unattended dev session and return promptly. Neither checks, before
launching, that the environment it is about to hand a story to is actually
correct. Four times in one recovery session (2026-09-10), that assumption was
silently false, and every one of the four failed the same way — minutes into
a run, with **zero diagnostic pointing back at the cause**. The operator had
to trace each one by hand through `bmad-loop diagnose`, raw session logs, or
an eyeballed YAML diff, because the tool itself reported `verdict: ok` or
`verdict: clean` right up until the story quietly produced nothing.

**What "environment" means here, concretely, and what went wrong with each:**

1. **Harness/model pairing.** `factory dispatch` resolves a `harness_preference`
   and a `model_tier_map` independently, from two different policy layers. On
   four of eight stations (doctor, herald, mason, scribe) the model map named a
   Cursor-only model (`composer-2.5-fast`) while the harness order still
   resolved to `claude` — a pairing Claude Code's own CLI refuses outright
   (`"composer-2.5-fast" isn't described by this version's model catalog`).
   Every dispatch to these four stations died in seconds. The other four
   stations already carried a `harness_preference = ["cursor"]` override
   with a comment explaining exactly this failure mode, discovered
   independently on 2026-09-01 — the fix was never propagated fleet-wide.
   **Fixed 2026-09-10:** mirrored the override onto the remaining four
   stations' `marshal-policy.toml` (`fix/marshal-harness-preference-4-stations`).

2. **The multiplexer binary itself.** `factory spin` needs `tmux` on `PATH` to
   launch `bmad-loop run`'s session. After a host reset, `tmux` was gone
   entirely — `bmad-loop mux` reported no available backend on this platform.
   `factory spin` did not surface this: it launched, the supervisor attached,
   and `bmad-loop`'s own engine decided there was nothing to do and completed
   in under 20ms with "0 done, 0 deferred, 0 escalated" — a clean exit, not an
   error. Every mason/scribe spin attempt looked identical to "no eligible
   stories" from the caller's side. **Fixed 2026-09-10:** `tmux` added as a
   `pyforge-marshal` pixi dependency (linux-64/osx-arm64-scoped, conda-forge
   doesn't ship it for win-64) instead of relying on a system package outside
   pixi's control (`fix/marshal-tmux-dependency`).

3. **Two unsynced views of the same fact.** `factory dispatch`/`bmad-build-auto`
   read the tracked `sprint-status-ledger.yaml` directly. `factory
   spin`/`bmad-loop` read a separate, gitignored Tier-3
   `implementation-artifacts/sprint-status.yaml`. Nothing kept them in sync
   except `bmad-sprint-planning`'s own one-shot `generate` (epics.md →
   Tier-3, run once, never re-run automatically) and `sprint-ledger-sync`
   (Tier-3 → tracked ledger, "run it when a story lands," also never
   automatic). A station's Tier-3 copy sat stale for **four days**, missing
   two whole epics, while spin reported "0 done" every run with nothing to
   contradict it. **Fixed 2026-09-10:** `marshal refresh` now regenerates
   every station's Tier-3 feed from its `epics.md` as a fourth checked step,
   independent of git state, and `factory <slug> preflight` compares the
   ledger's actionable set against Tier-3 and WARNs on drift
   (`MRS-PREFLIGHT-016`) instead of letting spin silently see fewer stories
   than dispatch does (`feat/marshal-sprint-status-sync-and-drift-detection`).

4. **The promotion tool's own regression guard has a blind spot.** Running
   the newly-fixed Tier-3 regeneration surfaced a second, independent bug:
   `scripts/promote_sprint_status.py`'s regression guard (and its
   `--repair-feed` counterpart) only detects the specific transition
   `done → backlog`. A tracked-`done` story whose Tier-3 twin held a stale
   `blocked` — genuinely completed, confirmed by its own spec's `status:
   done` frontmatter and a landed commit — passed through undetected and
   silently overwrote the ledger's correct `done` with the stale `blocked`.
   Caught only because the operator eyeballed the diff before committing.
   **Specced 2026-09-10** (`spec-sprint-status-promotion-regression-guard`);
   fix in progress the same session — widen both the refusal and repair
   paths from "feed says `backlog`" to "feed says anything other than
   `done`," with `20-4`'s live regression as the reproduction case.

5. **The operator's own fleet report trusted a stale verdict over a live
   one.** `scripts/fleet_picture.py` reads `marshal status`'s per-station row,
   which carries `dispatch_verification_verdict`/`dispatch_verification_
   failed_gate` fields that persist until the NEXT `factory dispatch` run
   overwrites them — they are not cleared when a different engine (`factory
   spin`) starts running on the same station. Scribe's row still carried a
   `refused` `MRS-GATE-007` verdict from a dispatch attempt on 2026-08-31
   (10 days stale) when a brand-new, healthy `factory spin` session
   (confirmed alive via `bmad-loop diagnose`, genuinely `dev-running`) was
   labeled **STUCK** in both the station-state cell and the ATTENTION block
   — the exact same pattern as findings 1-4: two pieces of state (a live
   process fact and a recorded verdict) sitting in the same JSON row,
   un-cross-checked. **Fixed 2026-09-10:** both call sites now require
   `dispatch_phase is not None` (only ever set while dispatch is genuinely
   the live engine) alongside the refused verdict before trusting it
   (`fix/fleet-picture-stale-dispatch-verdict`). **Known gap, not yet
   built:** the `station_state()` fix has direct unit coverage; the
   ATTENTION-block site's own ~10-line `needs.append` branch inside
   `main()` does not — it would need `subprocess.run` mocked the way
   `test_fleet_picture_verification_staleness.py` already mocks
   `marshal status`'s JSON output for a different ATTENTION probe in the
   same file, rather than driving the real fleet's own ledger state.

**The pattern underneath all five.** Every one of them is a silent-success
failure mode: the tool's own reported verdict (`ok`, `clean`, `0 done`,
`STUCK`) gave no signal that anything was wrong, and each required manual
archaeology (`bmad-loop diagnose`, raw stderr, an eyeballed diff, a raw
`marshal status --format json` dump) to even locate, let alone fix. Four of
the five are now closed with a **loud** failure, an automated repair, or a
cross-check against live process state in their place; the fourth
(`promote_sprint_status.py`) landed the same session too. What remains open,
found in the same session and not yet decomposed into a story:

- **The ATTENTION-block test-coverage gap** named in finding 5 above — the
  fix is live and correct (confirmed against the real fleet), but the
  `needs.append` branch inside `main()` has no dedicated unit test the way
  `station_state()`'s does.

- **No mid-session checkpointing.** A dispatch or spin session that crashes
  (terminal/IDE crash, not a code failure) loses every uncommitted change in
  its worktree unless the *operator* notices and manually
  `git add -A && git commit`s a recovery checkpoint before relaunching. This
  session hit that path **four separate times** (doctor 21.1 twice, herald
  19.1, steward 48.6 twice) across two terminal crashes, and every recovery
  was done by hand, live, under time pressure — real work (a completed
  story, hundreds of lines of a WebSocket-streaming feature) sat one
  `git worktree` cleanup away from silent loss each time. Marshal's own
  supervisor already watches these sessions for completion; it does not
  periodically checkpoint their in-flight worktree state.
- **A crashed session and a genuinely failed one look identical to the
  ledger.** When a dispatch session dies (crash, kill, or a real failure),
  the run is recorded with a terminal verdict (`failed`, `stopped_externally`)
  that `factory drain` treats as permanently blocked — "never auto-retried,
  never forced past" by design, which is correct when the story genuinely
  failed. But an environment crash is not a story failure, and drain has no
  way to tell the two apart; every crash this session required the operator
  to notice the block, bypass it with a manual single-story `factory
  dispatch` (which does retry cleanly), and know that trick exists. There is
  no sanctioned "this was infrastructure, not the story — retry" path
  through `factory drain` itself.

## Non-goals

- Not a rewrite of the dispatch/spin split, the Tier-3/ledger two-file
  design, or `promote_sprint_status.py`'s architecture — every fix above
  works within the existing shape.
- Not a general crash-recovery framework for every marshal subprocess; scope
  is the dev/review session a story's worktree lives in.

## Realization log

- **2026-09-10** — Dream captured retroactively from a single long recovery
  session that hit all four closed findings plus the two open ones above, in
  order, while draining doctor/herald/mason/scribe/steward backlogs after two
  terminal crashes. Three of four environment-integrity findings shipped the
  same session (`fix/marshal-harness-preference-4-stations`,
  `fix/marshal-tmux-dependency`,
  `feat/marshal-sprint-status-sync-and-drift-detection`); the fourth
  (`promote_sprint_status.py`'s regression guard) is specced and mid-fix. The
  two resilience findings (no mid-session checkpoint, crashed-vs-failed
  indistinguishable to drain) are captured here, not yet decomposed into
  marshal epics.md stories — next step.
- **2026-09-10 (later, same session)** — `promote_sprint_status.py`'s
  regression guard fix landed
  (`fix/promote-sprint-status-done-strictly-senior`); the three resilience
  findings decomposed into marshal **Epic 34** (Stories 34.1-34.3, fully
  specced and dispatch-ready). A fifth environment-integrity finding
  surfaced immediately after, from the operator's own next fleet-picture
  check: `fleet_picture.py` mislabeled a healthy live spin as STUCK off a
  10-day-stale dispatch verdict — same silent-success pattern as the first
  four. Fixed the same session
  (`fix/fleet-picture-stale-dispatch-verdict`); the fix itself has direct
  unit coverage, but its ATTENTION-block sibling site does not — decomposed
  as **Story 34.4** below.
- **2026-09-11** — Retroactive `spec-marshal-launch-environment-integrity`
  authored. This Realization log had claimed `status: specified` and full
  decomposition since 2026-09-10, but no dedicated Spec file was ever
  produced — `dream-chain-check`'s INV-1 correctly flagged the gap when the
  operator asked whether any Dreams still needed specing. Epic 34
  (Stories 34.1–34.4) was already fully `done` in the tracked ledger at
  that point (confirmed via real merge commits: `local-recipes#1153`,
  `#1158`, `55153c8`/`dcda31b8cb`, `local-recipes#1145`/`02237d61b9`) — the
  new Spec documents what shipped rather than specifying new work. Status:
  specified → realized. `epic-34`'s own stale `in-progress` ledger stamp
  (all 4 stories `done` underneath it) corrected to `done` in the same
  pass.
