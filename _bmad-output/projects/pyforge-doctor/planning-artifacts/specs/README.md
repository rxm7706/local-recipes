# pyforge-doctor — story specs (tracked, durable)

Per-story specs live here, **tracked in git**, not in gitignored
`implementation-artifacts/`. In a spec-driven build the spec *is* the
contract — see `CLAUDE.md` § *Spec-driven, framework-neutral layout*, "Story
specs are durable (tracked), NOT Tier-3." After a story merges, its spec is
promoted from the run's `implementation-artifacts/` into this directory and
committed here as the source of record.

**Status (2026-08-09):** all **25** done stories have a spec here — verified
mechanically against `sprint-status-ledger.yaml`, not by eye.

### Backfill, 2026-08-09

The 2026-08-08 status line below was true when written, at 16 done stories.
Nine more landed between then and 2026-08-09 without their specs being
promoted, so the invariant silently lapsed. Backfilled in one pass, using the
recovery-source hierarchy in `CLAUDE.md` — highest fidelity first, and the
tier is recorded in each file's own frontmatter rather than inferred:

| stories | tier | source |
|---|---|---|
| `6-2` … `6-6` (5) | 1 | **Real originals**, still present in Tier-3 `implementation-artifacts/` and promoted **verbatim** (byte-identical, as `spec-1-1` was). Full `baseline_revision`/`final_revision` frontmatter intact. |
| `5-1`, `5-2`, `6-1` (3) | 3 | `epics.md`-derived contract + merged-PR Delivery Record. **No draft ever existed to promote** — all three landed via hand-driven PRs (#325, #323, and commit `6a7a099a44`), not bmad-loop runs, so there was nothing in Tier-3 and no worktree transcript. Same class as `spec-2-1`. Their `epics.md` entries carry unusually complete `Outcome` sections, so these recoveries are richer than contract-only. |
| `6-7` (1) | 0 | **Authored first-hand during implementation** (hand-driven per operator instruction, no bmad-loop run) — not a recovery at all. |

Transcript search was run and came back empty for the three Tier-3 cases: the
hits for their slugs are cross-references inside *other* stories' transcripts,
not the specs themselves, and no run-worktree directory exists for any of them.
That is consistent with their having never been driven by a loop run.

**Why this lapsed, and what would catch it next time.** Promotion is a manual
post-merge step with no detector behind it. A story can be `done` in the
ledger with no spec here and nothing reports it — which is exactly how nine
accumulated unnoticed. The check is cheap (every `done` key in
`sprint-status-ledger.yaml` should have a matching `spec-<key>.md`) and is a
natural Doctor source under Charter §6, since the artifact it would judge is
Marshal-governed. Not built here; recorded so the next lapse is a decision
rather than an accident.
