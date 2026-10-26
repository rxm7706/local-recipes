---
title: "107.1: A refresh or a sync never carries a stale-slug story key"
type: 'fix'
created: '2026-10-25'
status: 'done'
followup_review_recommended: false
baseline_revision: '48445a6b8d8b1869495f6f2618516eeb0161dfbb'
review_loop_iteration: 0
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
  - scripts/promote_sprint_status.py
  - scripts/fleet_scan.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/refresh.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/refresh.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_refresh.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_land_epic_rollups.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - .claude/skills/bmad-sprint-planning/scripts/sprint_plan.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `marshal refresh` fills every station's shared Tier-3 feed with a second key for each finished story whose
title is long or unusual, at `backlog`, and a bare `sprint-ledger-sync` copies those keys into the tracked ledger. Line
numbers are at `48445a6b8d`.

- **The writer.** `cli/refresh.py::_sync_status_step` (`:149-216`) runs `uv run
  .claude/skills/bmad-sprint-planning/scripts/sprint_plan.py generate` from the station's `epics.md` into the shared
  `_bmad-output/projects/<slug>/implementation-artifacts/sprint-status.yaml`, which every worktree and loop home reads
  through its symlink. `marshal refresh` runs it for every home, after the policy re-render (`:251`, `:280`, `:311`,
  `:350`, `:394`).
- **Why the keys differ.** `sprint_plan.py::_slug` (`:133-142`) cuts a title at 60 characters and keeps `\w`, so `_`
  and non-ASCII letters stay. The tracked ledger's keys are minted by doctor's `chain.slugify_title` (Ruling 12,
  `sources/chain.py:3710`), which neither cuts nor keeps them. So `1-2-...-the-transport-spike: done` in the ledger
  gets `1-2-...-the-transport-spik: backlog` in the feed, and `generate`'s merge keeps the feed's existing keys too.
- **The incident.** All eight primary feeds were rewritten between 04:21:57 and 04:22:18 local time on 2026-10-25,
  each within a second of its loop home's `.bmad-loop/policy.toml` re-render, and each body reads `last_updated:
  10-25-2026 04:22`, the date `_sync_status_step` passes (`:177`). They held 550 such keys: marshal 213, steward 122,
  doctor 83, mason 36, herald 33, warden 30, atlas 27, scribe 6 (548 at `backlog`, 2 at `done`). Replaying `generate`
  on the cleaned herald feed re-adds 34. The 14 steward duplicates found on 2026-09-25 had the same shape.
- **What a duplicate does.** `marshal factory spin` and `bmad-loop` read the feed for actionable stories, so a
  `backlog` duplicate of a `done` story is work to them. `scripts/promote_sprint_status.py::main` (`:341`) promotes
  every feed key the twin lacks: CAP-265's repair (`repair_feed`, `:278`) adds twin keys the feed lacks but never drops
  a feed key the twin lacks. PR #2319's post-merge sync copied all of them into six tracked ledgers and rolled 179 epics
  back to `in-progress` (reverted; nothing committed).
- **A second wart in the same output.** `_print_repaired_keys` (`:323`) prints a `done` key the feed lacks twice: it
  sits in both `lost` (`regressions` reports it `<absent>`) and `missing`.

**Approach:**
- **One rule for a stale key.** `scripts/promote_sprint_status.py` gains `stale_slug_keys(feed, twin)`: the story keys
  in the feed that the twin lacks while the twin carries the same epic number, story number and suffix (`_STORY_KEY_RE`)
  under another key. A feed key whose number the twin lacks is not stale: it may be a story not yet in the ledger.
  `split_stale_keys` splits them: a stale key is kept only when it is further along (`_STORY_PROGRESS_RANK`) than the
  best value its story already has, the twin's value for its key or the feed's own value for that key, so a run
  working the story under its old title never loses its progress; it is named for a `--rekey` (review S2). Everything
  else is dropped, including a key that is behind or level. A twin key at `done` or `blocked` keeps nothing (the ledger
  holds the outcome, and `blocked` is the operator's to lift); a stale `blocked`, or any status outside the rank table,
  ranks lowest (review round 2).
- **A bare sync drops them before it promotes.** In `main()`, after any `--rekey` translation (so a re-keyed row is
  judged through its map) and before the regression guard, the stale keys leave the feed and the map being promoted.
  The feed is rewritten by `_write_feed_development_status`, so its head and tail stay byte-for-byte. Stdout prints
  `DROPPED`, the count, and each key with the twin key (and its value) that carries its number, pointing at
  `--rekey`; a kept-ahead key prints under `KEPT` and is promoted as before. It applies under `--allow-regression` as
  well: the twin already carries that story, so nothing regresses.
- **`--feed-only`: the twin-to-feed half alone.** A new flag, with exactly one `--project`: drop the stale keys, then
  run `repair_feed` with the twin's full map (its `done` and story `blocked` values win, and twin keys the feed lacks
  are added; a value the feed has advanced is kept), write only the feed, and print one JSON object on stdout:
  `{"ok", "project", "feed", "dropped", "kept", "repaired"}`. It never writes the twin. With no feed, or a feed with no
  `development_status:` line (empty or truncated; nothing in it parses), it writes one from the twin under the header
  fields `sprint_plan.py` writes (`generated`, `last_updated`, `project`, `project_key`, `tracking_system`,
  `story_location`, `development_status`), so a second run is byte-identical (review S1). With no twin it reports
  `{"ok": true, "skipped": ...}`.
  An unknown key reports `{"ok": false, "error": ...}` and exits 2.
- **The refresh step calls it.** `_sync_status_step` runs `[sys.executable, <root>/scripts/promote_sprint_status.py,
  "--project", <slug without "pyforge-">, "--feed-only"]` through the same `PosixProcess` seam, timeout and
  `MRS-REFRESH-008` findings. It skips when the tracked twin or the script is missing. Its `done` detail names the
  dropped and repaired counts, or reads `in sync`. `sprint_plan.py` is neither called nor changed: it is
  installer-owned. `core/refresh.py`'s docstring and `cli/refresh.py`'s module docstring say the step syncs the feed
  from the tracked twin.
- **The landing path too.** `cli/land.py::_promote_sprint_ledger` renders the twin from the shared feed when a story
  lands. It drops the same `split_stale_keys` before its refusal check, so a landing cannot publish a stale key either
  (review S3).
- **The double print.** `_print_repaired_keys` names each key once; the `REPAIRED` line counts distinct keys.
- **`type: fix`, no flag.** The refresh step exists to keep the feed in step with the tracked ledger (`core/refresh.py`
  docstring, the 2026-09-10 incident), and CAP-265's sync must never add a duplicate to the twin. This restores both.
  Under `spec-feature-flag-governance` Q1 a fix carries no flag.

Ledger key: `107-1-a-refresh-or-a-sync-never-carries-a-stale-slug-story-key`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-265** (the hand ledger sync repairs unrelated feed drift itself and names every key it
  repaired): the sync also drops and names a stale-slug key, so it never promotes one.
- **`spec-pyforge-marshal` CAP-132** (← `spec-loop-home-fleet-refresh` CAP-1, FR-133) and **CAP-134** (← CAP-3,
  FR-135): the fleet refresh and its checked steps; `sync_status` stays a checked step reporting `done | skipped |
  failed` (AD-21).
- This story mints no CAP and changes no `SPEC.md` text.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, the 2026-10-25 (the refresh writes keys the ledger does
  not carry) entry; the operator's direction of 2026-10-25.

## Acceptance Criteria

- **AC1 — The replay.** A test builds the 2026-10-25 herald shape: a twin with long, `_`-bearing and non-ASCII titles'
  keys at `done`, and a feed holding their `sprint_plan` slugs at `backlog`. A bare sync exits 0, the twin's key set is
  unchanged, the feed holds none of the stale keys, and stdout names each dropped key.
- **AC2 — Not every unknown key is stale.** A feed key whose epic and story number the twin lacks survives a bare sync
  and `--feed-only`, and the bare sync promotes it.
- **AC3 — `--feed-only` writes the feed only.** The twin's bytes are unchanged; the feed gains the twin's missing keys
  and `done` values, drops the stale keys, keeps an `in-progress` value the feed has advanced past the twin's `backlog`,
  and keeps its head and tail byte-for-byte. Stdout is one JSON object naming the dropped and repaired keys.
- **AC4 — `--feed-only` edges.** An absent feed is written from the twin with the header fields; an absent twin reports
  `skipped` and writes nothing; `--feed-only` without exactly one `--project` exits 2.
- **AC5 — The refresh step.** `_sync_status_step`'s argv names `scripts/promote_sprint_status.py`, `--project acme`
  (from slug `pyforge-acme`) and `--feed-only`, and never `sprint_plan.py`. It reports `done` with the counts, `in
  sync`, `skipped` (no twin or no script), and `failed` with `MRS-REFRESH-008` for a non-zero exit, a non-JSON or
  not-ok report, a launch error and a timeout.
- **AC6 — Once per key.** A `done` key the feed lacks appears once in the `REPAIRED` output.
- **AC6a — Progress is never thrown away, and nothing else is kept.** A stale key further along than its story
  (`in-progress` beside `backlog`) survives `--feed-only` (listed under `kept`) and a bare sync (printed under `KEPT`,
  promoted as before); the refresh detail names it. A stale key behind or level with the twin's value or the feed's own
  value for that key, a stale `blocked`, and any stale key beside a `done` or `blocked` twin key are dropped.
- **AC6b — A feed with no map is rebuilt.** A zero-byte feed and one truncated before `development_status:` are
  rewritten from the twin by `--feed-only`, and a second run leaves the bytes unchanged.
- **AC6c — The landing.** A landing whose feed carries a stale `backlog` copy of a `done` twin key publishes neither the
  copy nor an epic rolled back by it (`test_land_epic_rollups.py`).
- **AC7 — Mutation.** Making `stale_slug_keys` return nothing fails AC1's and AC3's tests; making `split_stale_keys`
  drop every stale key fails AC6a's; removing the landing filter fails AC6c's. Restore each.
- **AC8 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and `pixi run --frozen -e pyforge-ci
  pyforge-deps-test` are green.

## Boundaries & Constraints

**Always:**
- Keep `repair_feed`'s one-directional move: never move a key away from `done`, never rewrite a value the feed advanced.
- Reconcile every governed path on the memlogs of every Spec `spec-surface-check` names, then stamp each scoped
  (AGENTS.md pre-PR item 5).

**Ask first:**
- Any change to `sprint_plan.py`, to the twin's header, or to which keys a sync promotes beyond dropping stale ones.

**Never:**
- Never let `--feed-only` or the refresh step write a tracked `sprint-status-ledger.yaml`.
- Never drop a feed key whose story number the twin lacks.
- Never run `marshal refresh` against the fleet as part of the story.

**Residual risk:**
- The refresh reads the primary checkout's twin, which can trail `origin/main` until that checkout fast-forwards; a
  story minted on `main` reaches the feed one refresh later. `sprint_plan.py` read the same checkout's `epics.md`, so
  this is unchanged.
- A retitled story whose new key reaches only the feed is dropped by a sync until the twin carries it; a re-key goes
  through `--rekey` (doctor Story 25.3), which translates first.
- The refresh runs the primary checkout's copy of `promote_sprint_status.py`. Until that checkout fast-forwards past
  this story, a newer `marshal` run against it gets argparse exit 2 on `--feed-only`, and every home's `sync_status`
  reports `failed` (`MRS-REFRESH-008`, WARN) without writing anything (review N2).
- A project with a tracked ledger but no board key (no `epics.md`) reports `failed` (`unknown --project key`) where
  it used to report `skipped`. Every loop home today has both (review N3).

## I/O & Edge-Case Matrix

| Case | Before | After |
|---|---|---|
| refresh, feed in step with the twin | `generate` adds `sprint_plan` slugs beside twin keys | `in sync`, nothing written |
| refresh, twin gained a story | `generate` adds it, plus slug duplicates | the twin key is added (`repaired`) |
| bare sync, feed holds a stale-slug key | promoted into the twin as a duplicate, epic rolls back | dropped from the feed and named; twin unchanged |
| feed key whose number the twin lacks | promoted | promoted (unchanged) |
| feed advanced a key past the twin | kept | kept (unchanged) |
| `--rekey` sync | translated, then judged | translated, stale keys judged through the map, then judged |
| refresh, no tracked twin | ran `generate` if `epics.md` existed | `skipped` |
| stale key ahead of its twin key | promoted as a duplicate | kept, named for `--rekey`, promoted as before |
| feed empty or truncated before its map | `generate` rebuilt it | rebuilt from the twin |
| landing, feed holds a stale key | published into the twin | left out |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-marshal` CAP-265, CAP-132 (FR-133) and CAP-134 (FR-135); AD-21. No CAP is
  minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-25 (the refresh writes keys the ledger does
  not carry) entry.
- Epic: Epic 107 (new), minted with this story, because Epics 15 and 54 are done. `epic-107` and
  `epic-107-retrospective` are minted with it.
- Ledger key: `107-1-a-refresh-or-a-sync-never-carries-a-stale-slug-story-key`.
- Deps: —.
- Surface: `marshal-policy.toml` `[epic_surfaces]."107"`, added with this mint.
- Minted 2026-10-25 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC1–AC6's tests (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- The mutation of AC7 — expected: AC1's and AC3's tests fail. Restore it.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.

**After landing (not a gate):** fast-forward the primary checkout to the merge first (its copy of the script is the one
the refresh runs). Then `marshal refresh --project <slug>` against one home reports `sync_status` `in sync` on a clean
feed, and `sprint-ledger-sync -- --project <station>` reports `unchanged`.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (the refresh writes keys the ledger does not carry) at the
  operator's direction "Do this task here: Find what writes truncated slugs into Tier-3 feeds". `type: fix`, no flag,
  no CAP.
- 2026-10-25: review round 1 applied (see the triage log): the S2 keep rule (`split_stale_keys`), the rebuilt markerless
  feed, the landing path's filter, the real parser in the test stub, AC6a–AC6c, two residual risks and the
  after-landing order.
- 2026-10-25: promoted to `done` in the landing PR after the independent review (this spec, its `epics.md` Status line
  and its ledger keys); the merge subject names this story's key.

## Review Triage Log

- **Round 1 (2026-10-25, an independent reviewer over `48445a6b8d..ae997ccfd8`): PASS, 0 blockers, 4 should-fix, 6
  nits.** Checked: AC1–AC8 as written; 1488 land/deploy/ledger/sync/refresh/promote unit tests; the AC7 mutation; all
  eight live feeds (0 stale keys, no twin with one number under two keys); a `_new_feed_text` feed loads in bmad-loop's
  `sprintstatus.load`; the planning counts (675 keys, 465 stories, 105 epics).
  - S1 (fixed): `--feed-only` appended entries under no marker to an empty or truncated feed, growing it each run.
  - S2 (fixed): a stale key further along than its twin key was dropped with its progress; now kept and named.
  - S3 (fixed): `cli/land.py::_promote_sprint_ledger` still published stale keys from the feed.
  - S4 (fixed): the test stub's parser read the feed tail as entries; it now delegates to `fleet_scan`, and AC3
    asserts the exact feed.
  - N1 (fixed): `--feed-only` with an unknown-number key, two `--project`s, `--rekey` or `--allow-regression` tested.
  - N2, N3 (recorded as residual risks); N4 (the `"107"` epic-surface comment corrected); N5 (`DROPPED` points at
    `--rekey`); N6 (promotion to `done` in the landing PR, as before).
- **Round 2 (2026-10-25, the same reviewer over `ae997ccfd8..bb408ae6dc`): FAIL, 1 blocker, 2 nits.** S1, S3, S4, N1,
  N4 and N5 confirmed fixed (the landing filter's test goes red with the filter removed).
  - Blocker (fixed): the keep rule kept every stale key that was not `backlog`, level or beside a `done` twin key, so
    keys behind their story (`in-progress` beside `review`, `blocked`, anything beside a `blocked` twin key, or level
    with the feed's own advanced value) still reached the ledger as duplicates. `split_stale_keys` now keeps only a
    key ranked above the best value its story has; the unit test covers ten cases.
  - Nits (fixed): the Dream's "cannot add one to a tracked ledger" now says a key that carries no progress; the refresh
    detail leads with the kept count instead of `in sync`.
