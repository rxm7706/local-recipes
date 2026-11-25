---
title: '54.1: herald deck pull --commit commits, and three CLI defects are closed'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 54-1-herald-deck-pull-commit-commits-and-three-cli-defects-are-closed
spec: spec-pyforge-herald
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py'
  - 'src/shared/packages/pyforge-herald/src/pyforge/herald/local_ship.py'
  - 'src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py'
  - 'src/shared/packages/pyforge-herald/src/pyforge/herald/claims.py'
  - 'src/shared/packages/pyforge-herald/src/pyforge/herald/notices.py'
  - 'src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py'
  - 'src/shared/packages/pyforge-herald/tests/unit/test_deck_pipeline.py'
  - 'src/shared/packages/pyforge-herald/tests/unit/test_cli_pull.py'
  - 'src/shared/packages/pyforge-herald/tests/unit/test_local_ship.py'
  - 'src/shared/packages/pyforge-herald/tests/unit/test_webhook.py'
  - 'src/shared/packages/pyforge-herald/tests/unit/test_claims.py'
  - 'src/shared/packages/pyforge-herald/tests/unit/test_notices.py'
  - 'src/shared/packages/pyforge-herald/tests/unit/test_cli_success.py'
  - 'src/shared/packages/pyforge-herald/tests/unit/test_cli_notice_epic10.py'
  - 'src/shared/packages/pyforge-herald/tests/unit/test_cli_progress.py'
  - 'src/shared/packages/pyforge-herald/tests/unit/test_deck_exports_handlers.py'
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/contract.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-herald.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The code review of main `7da08791f3` left herald one open row, `DW-herald-review-2026-11-24-1`, with five defects. (1) Confirmed by the session lead: `pull_deck` passes `[deck_dir, resolved_state_path]` to the committer (`deck_pipeline.py:774`), the state path is `.herald/bridge-state.json`, and `.gitignore:963` excludes `/.herald/`, so `git add` refuses it and `herald deck pull --commit` fails after `_record_pull_etag` has recorded the new etag. Reviewer-reported and not re-traced: (2) `build_on_ship_body` sends only `station` and `unblock_narrative` (`local_ship.py:155-157`) and `handle_on_ship` upserts the day's record with every omitted field defaulted (`webhook.py:684-694`), so figures recorded earlier that day read zero; (3) `success create --shipped-date` (`claims.py:502`) and `notice author --deadline` (`notices.py:572`) store the string as given, and `date.fromisoformat` raises on a malformed one at a later listing (`claims.py:405`); (4) `progress --update` with no positional station falls through to the listing and exits 0 (`cli.py:1447-1454`); (5) `deck exports` on an unknown slug raises a plain `HeraldError` and exits 1 (`cli.py:1155`).

**Approach:** Reproduce each defect first with a test that fails on the tree as it stands. For each one reproduced: commit the deck directory alone and record the etag after the commit succeeds, and when staging the deck leaves nothing to commit (the pulled deck already matches HEAD) make no commit, report the pull as not committed and still record the etag; have a ship keep the day's recorded compute, token and wall-clock figures and shipped capabilities, by having `herald-ship-local` send them in its on-ship body (the handler's same-day replace is specified and stays); refuse a date that is not `YYYY-MM-DD` when it is entered; make `progress --update` with no station a usage error; and make `deck exports` on an unknown slug exit with the code `contract.md` § exit codes documents. A defect the tree does not reproduce is recorded below as not a defect, with the reading that shows it, and its code is left as it is. `webhook.py`'s module text says a same-day on-ship delivery replaces by specification, and `contract.md` gives exit 1 to any `HeraldError` the map does not name: defects (2) and (5) are judged against those texts before any code moves.

Ledger key: `54-1-herald-deck-pull-commit-commits-and-three-cli-defects-are-closed`.

### Living CAP citations

- spec-pyforge-herald CAP-1, CAP-4, CAP-11, CAP-12, CAP-13, CAP-38 and CAP-54 (each realized, no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce a defect with a failing test before changing its code; read every verdict from its exit code, never through a pipe.
- Record a defect the tree does not show as not a defect in this spec's change log, with the file and line read.
- Keep `/.herald/` ignored; the state file is never committed.
- Treat a `--commit` with nothing staged under the deck as a pull that succeeded uncommitted: exit 0, `committed=False`, the etag recorded.
- Leave `webhook.py`'s same-day replace as it is; the producer sends the day's cumulative figures.

**Never:**
- Never put a fix behind a flag.
- Never rewrite a stored progress record, claim or notice, and never change a model or a migration in this story.
- Never change a capability's text or an exit code `contract.md` documents; a mismatch is fixed in the code.
- Never edit the SKF-compiled station skill under `.claude/skills/pyforge-herald/` in this story; its stale sentence is a named follow-up (§ Follow-ups).

## Acceptance Criteria

**Given** `deck pull --commit` passes the ignored `.herald/bridge-state.json` to `git add` after the etag is recorded, a ship upserts the day's record with omitted fields defaulted, `--shipped-date` and `--deadline` are stored unchecked, `progress --update` with no station exits 0, and `deck exports` on an unknown slug exits 1
**When** each of the five is reproduced by a failing test and each one reproduced is fixed
**Then** `deck pull --commit` commits the deck, a failed commit leaves the etag unrecorded, a deck that already matches HEAD is reported as not committed with its etag recorded, a same-day ship from the checkout that holds the day's record keeps the figures already recorded, a malformed date exits non-zero and stores nothing, `progress --update` with no station exits 2 and writes nothing, and `deck exports` on an unknown slug exits with the documented code
**And** a defect the tree does not reproduce is recorded as not a defect, and its code is left as it is

- **AC1 — The state file is ignored, and the pull's commit set does not name it.** Expected: both commands exit 0. The tests hold that the committer receives the deck directory alone, that a commit that raises leaves the etag unrecorded, and that a pull whose deck already matches HEAD makes no commit, reports `committed=False`, records the etag and prints `(nothing to commit)`.

  ```bash
  git check-ignore -q .herald/bridge-state.json
  pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/unit/test_deck_pipeline.py src/shared/packages/pyforge-herald/tests/unit/test_cli_pull.py -q
  ```

- **AC2 — A ship keeps the day's figures.** Expected: exit 0. A test records compute and token figures and a shipped capability for a station today, runs `herald-ship-local`'s delivery through `handle_on_ship`, and reads them back unchanged. The handler's replace is the specified behaviour (`webhook.py` module text) and `test_webhook.py` passes unchanged; the fix is in the producer, which reads the day's record from the progress store under `--repo-root`.

  ```bash
  pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/unit/test_local_ship.py src/shared/packages/pyforge-herald/tests/unit/test_webhook.py -q
  ```

- **AC3 — A malformed date is refused at entry.** Expected: exit 0. The tests hold that `success create --shipped-date` and `notice author --deadline` exit non-zero on a value that is not `YYYY-MM-DD` and store nothing, and that a listing over the existing rows does not raise.

  ```bash
  pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/unit/test_claims.py src/shared/packages/pyforge-herald/tests/unit/test_notices.py src/shared/packages/pyforge-herald/tests/unit/test_cli_success.py src/shared/packages/pyforge-herald/tests/unit/test_cli_notice_epic10.py -q
  ```

- **AC4 — `progress --update` with no station is a usage error.** Expected: exit 0. The test holds that the command exits 2 and writes no record.

  ```bash
  pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/unit/test_cli_progress.py -q
  ```

- **AC5 — `deck exports` on an unknown slug exits with the documented code.** Expected: exit 0. The test holds exit 2: `contract.md` § exit codes gives `DeckUsageError` exit 2, and that error's own text names the unknown slug.

  ```bash
  pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/unit/test_deck_exports_handlers.py -q
  ```

- **AC6 — Herald's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-herald pyforge-herald-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-herald CAP-1, CAP-4, CAP-11, CAP-12, CAP-13, CAP-38 and CAP-54 (each realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-11-25 entry (pull --commit commits, and three CLI defects close); operator ruling of 2026-11-25.
- Epic: Epic 54, minted with this story.
- Ledger key: `54-1-herald-deck-pull-commit-commits-and-three-cli-defects-are-closed`.
- Deferred work: closes `DW-herald-review-2026-11-24-1`; opens `DW-herald-54-1-1` (the compiled skill's stale `--commit` sentence).
- Surface: `marshal-policy.toml` `[epic_surfaces]."54"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Follow-ups

- `.claude/skills/pyforge-herald/0.1.1/pyforge-herald/SKILL.md:90` (served as `active/`) and `0.1.0/pyforge-herald/SKILL.md:86` still read "`--commit`, which stages and commits `presentations/<slug>/` and the bridge-state file". The sentence is false after this story: `--commit` stages and commits `presentations/<slug>/` alone, the bridge-state file under `/.herald/` is ignored and never committed, the etag is recorded after the commit, and a deck that already matches HEAD is reported as not committed. The file is SKF-compiled and outside this story's surface; it is corrected through `skf-update-skill`, under deferred-work row `DW-herald-54-1-1`.
- A ship run from a checkout other than the one the loopback host writes under reads a different progress store, so the day's figures still reset there. The how-to and the pixi task run the ship from the primary checkout; reading `HERALD_REPO_ROOT` in the client would be a new environment-variable read and a `contract.md` row, and is not in this story.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's ruling of the same date, for `DW-herald-review-2026-11-24-1`.
- 2026-11-25: defect 1: reproduced and fixed - `test_pull_prototype_commit_true_commits_in_a_repo_that_ignores_the_state_dir` failed on the unchanged tree with `git add -- presentations/pyforge-warden .herald/bridge-state.json` exiting 1 (ignored path), and the commit-failure tests found the etag already recorded; the three pull functions now commit the deck directory alone and record the etag after the commit.
- 2026-11-25: defect 1, review residue: reproduced and fixed - `test_pull_prototype_commit_true_with_a_deck_identical_to_head_records_the_etag_uncommitted` failed with `git commit ... exited 1: nothing to commit, working tree clean` once the state file left the commit set; `SubprocessGitCommitter.commit` now runs `git diff --cached --quiet -- <paths>` after `git add`, makes no commit and answers `False` when nothing is staged, the pull reports `committed=False` and still records the etag, and `deck pull --commit` prints `(nothing to commit)`. `GitCommitter.commit` returns `bool` (was `None`).
- 2026-11-25: defect 2: reproduced and fixed - `test_a_ship_keeps_the_figures_recorded_earlier_that_day` failed on the unchanged tree (`assert [] == ["S-1.1"]`). Judged against `webhook.py`'s module text first: the same-day replace is specified and `test_handle_on_ship_second_delivery_replaces_rather_than_merges` pins it, so the handler is unchanged and `local_ship` now sends the day's recorded figures and shipped capabilities; an unreadable progress store refuses the ship with exit 1 before any POST.
- 2026-11-25: defect 3: reproduced and fixed - `test_create_refuses_a_shipped_date_that_is_not_iso_and_stores_nothing` and `test_author_refuses_a_deadline_that_is_not_iso_and_stores_nothing` failed on the unchanged tree, and `list_claims` over a stored `tomorrow` raised `ValueError` from `date.fromisoformat`. Both dates are now refused at entry with a plain `HeraldError` (exit 1); a stored malformed `shipped_date` is left out of a ranged listing, never rewritten. The deadline half had no later crash (nothing parses a deadline); its entry check was added because `--help` documents `YYYY-MM-DD`.
- 2026-11-25: defect 4: reproduced and fixed - `test_update_with_no_station_exits_2_and_writes_nothing` failed on the unchanged tree (`assert 0 == 2`); `progress --update` with no positional station now exits 2 before dispatch.
- 2026-11-25: defect 5: reproduced and fixed - `test_cli_deck_exports_unknown_slug_exits_2` failed on the unchanged tree (exit 1). Judged against `contract.md` § exit codes first: `DeckUsageError` is exit 2 and its own text names the unknown slug, so the code moved, not the table.
- 2026-11-25: the story is implemented and in review. The station skill's stale `--commit` sentence is left as a follow-up (§ Follow-ups), by the lead's ruling.
- 2026-11-25: closed. PR #2385 merged as 080f89c4df (`Merge pyforge-steward/133-1 into main`) after its 51 CI checks passed and the full local `pr-preflight` exited 0 on 48 lanes; an independent reviewer read the diff against this spec before the merge, its findings were applied and re-reviewed.
