---
title: "83.22: The landing's ledger guard judges the twin it overwrites"
type: 'fix'
created: '2026-10-04'
status: 'in-progress'
baseline_revision: '1d62151fe27a3afef7ed8bebc39a731d83e5b279'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-21-landing-finalize-writes-the-epic-roll-ups-the-sync-writes.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py
  - scripts/promote_sprint_status.py
  - scripts/fleet_scan.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 83.21 landed as #1828 on 2026-10-04. Its landing review found that the feed-sync guard in the landing's ledger promotion judges a different ledger from the one the promotion overwrites, plus four smaller gaps. Line numbers below are from main at `afaa41af48`.

- **MEDIUM:** in `cli/land.py::_promote_sprint_ledger`, the promotion publishes over `fresh_ledger`, which is `origin/<base>`'s ledger text (`vcs.file_text_at_ref(..., remote_tracking_ref(base), ledger_rel)`, around :1501-1517). But the guard's `existing` map is built from the primary checkout's local file: `existing = gen.parse_sprint_status(ledger_path) if fresh_ledger.strip() else {}` (:1543), and `_land_feed_sync_refusal(promote_mod, existing, incoming)` (:1544, defined at :1363) judges that. When the primary's local copy lags `origin/main`, a feed that drops a key or un-finishes one that only `origin/main` holds passes the guard and is published. This is how the 2026-10-03 epic drops (`1be676d263`, `fd328844d6`, `cc137c9faa`) got past the guard; #1828's description says so. No test pins which text the guard reads.
- **LOW-1:** `_roll_up_epic_rows` (:1347) reads statuses with land's own `_parse_sprint_ledger_statuses` (:1289). That parser stops at any non-indented line inside `development_status:` (`if raw and not raw.startswith((" ", "\t")): break`, :1302), so a column-0 `# comment` inside the block ends the parse early, and every row below it is left out of the roll-up. The sync's parser, `scripts/fleet_scan.py::parse_sprint_status` (:299), skips a column-0 comment and reads on.
- **LOW-2:** `core/status.py::render_ledger_status_rewrites` (:2072) rewrites the first line anywhere in the file whose pre-colon text equals a key. It does not limit itself to `development_status:`, so a header comment or another top-level block that carries `<key>:` is rewritten instead of the row. `render_ledger_advancements` calls it too.
- **LOW-3:** `cli/deploy.py::run_reconcile_completions` (`marshal deploy reconcile-completions`, :3668) advances story rows with `status.render_ledger_advancements` (:4005) and never applies the sync's epic roll-up, so it can leave an epic at `in-progress` after its last story reaches `done`.
- **LOW-4:** the MRS-LAND-011 WARN that names a missing `apply_epic_rollups` (around :1572-1586) fires only after both early returns (:1562, :1566). So a run with nothing to publish says nothing, even though its feed was not synced because the roll-up could not be loaded.

**Approach:**
- Build the guard's `existing` from `fresh_ledger`, the text the promotion publishes over, and read it with the sync's own parser. That parser takes a path, so use a temporary file, or another way that reuses `fleet_scan.parse_sprint_status` unchanged. Never use land's parser, and never fall back to the local file.
- Make `_roll_up_epic_rows` read statuses with the same parser, so its roll-up sees every row the sync sees.
- Limit `render_ledger_status_rewrites` to lines inside the `development_status:` block, under the block rules that parser uses.
- Run `run_reconcile_completions`'s advanced text through the same roll-up (`_sync_epic_rollup` / `_roll_up_epic_rows`), with the same rule when the module is missing: write no epic row it did not compute, and journal a WARN.
- Emit the missing-roll-up WARN whenever the roll-up cannot be loaded and a feed was present or a wave key needed promotion, including a run that then publishes nothing.

Ledger key: `83-22-the-landing-s-ledger-guard-judges-the-twin-it-overwrites`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 48.1 (the feed-sync drop guard), Story 79.1 (a landing promotes the story's feed row, tracked spec and ledger twin), Story 28.24 (the sync's roll-up) and Story 83.21 (the landing applies it). This is a defect of shipped behaviour, so it mints no new CAP. Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.

## Acceptance Criteria

- Given a primary checkout whose local ledger lacks a backlog key that `origin/main`'s ledger holds, and a feed that also lacks it When the landing finalize promotes the ledger Then the guard refuses the feed sync (MRS-LAND-011 WARN naming the key) and the published twin still carries the key. A real-git fixture with a stale primary clone pins it, and making the guard read the local file fails the test (mutation).
- Given a primary checkout whose local ledger holds a key below `done` that `origin/main` holds `done`, and a feed that reads it `backlog` When the finalize promotes Then the guard refuses with the `un-finish` label and `origin/main`'s `done` survives
- Given a primary checkout whose local ledger holds a `done` key that `origin/main` no longer carries, and a feed without it When the finalize promotes Then the guard does not refuse on that key, because the published text never held it
- Given a ledger with a column-0 `# comment` inside `development_status:` above an epic's stories When the finalize rolls up epic rows Then the epic reads the value the sync's `apply_epic_rollups` computes from every row, and reverting to land's parser fails the test (mutation)
- Given a ledger whose header comment carries `<key>:` text matching a story key When `render_ledger_status_rewrites` runs for that key Then only the `development_status:` row changes, and both callers keep their byte-for-byte behaviour on every other line
- Given `marshal deploy reconcile-completions` advancing the last open story of an epic When it writes the ledger Then the epic row reads `done`; with the promotion module unavailable it writes no epic row and journals a WARN
- Given the promotion module cannot be loaded and the twin already marks every wave key `done` When the finalize runs with a feed present Then the MRS-LAND-011 WARN naming the missing roll-up is still emitted and nothing is published
- Given each of the five fixes When its rule is removed Then a new test fails (mutation)

## Boundaries & Constraints

**Always:**
- Use the sync's own parser and its own `apply_epic_rollups`. Never add a second parser or a second roll-up rule.
- The guard judges exactly the text the promotion publishes over.
- Keep the targeted line rewrite: every byte outside the rewritten rows stays as it was.

**Never:**
- Never edit `scripts/promote_sprint_status.py` or `scripts/fleet_scan.py`. Both are outside Epic 83's surface, and the sync's behaviour is not in question.
- Never relax `regressions()` or `ledger-regression` to make a refusal go away.
- Never fall back to the primary checkout's local ledger when the remote read succeeds. The existing fetch-failure path, which publishes nothing, stays as it is.

</intent-contract>

## Binding

- Parent: Story 83.21 (#1828) and its landing review.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (landing guard source) entry.
- Epic: Epic 83.
- Ledger key: `83-22-the-landing-s-ledger-guard-judges-the-twin-it-overwrites`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Minted 2026-10-04 at the operator's request, folding 83.21's landing-review findings (one medium, four low) into one story.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild ledger-regression-check` over the promotion commit a fixture landing makes — expected: `ok`.

## Review Triage Log

- No review has run yet.
