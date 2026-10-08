---
title: "85.6: Every command a session denial names as the sanctioned form exists"
type: 'fix'
created: '2026-10-07'
status: 'in-progress'
baseline_revision: '5c1ff88e5a60bee67e66c10b721fa8fabff0a091'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-85-1-the-session-hook-refuses-deleting-protected-branches-and-loop-homes.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-85-4-the-hook-denies-every-protected-ref-deletion-and-any-deletion-that-orphans-commits.md
  - docs/governance/guild-roster.json
  - .claude/hooks/pre-shell.py
  - tests/scripts/test_pre_shell_hook.py
  - scripts/worktree_sweep.py
  - pixi.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the session hook tells an agent to run commands that do not exist, so an agent that follows the hook's
own advice fails.

- **The reasons.** `docs/governance/guild-roster.json` `session_denials` is the one declared list the hook
  (`.claude/hooks/pre-shell.py`) denies from, and each entry's `reason` is the line the agent reads. Measured on
  `b364823896`: the `protected-ref-deletion` reason (about :390) says "retire a branch with
  `python scripts/worktree_sweep.py --retire <branch>`", and the `unreachable-ref-deletion` `unreachable` reason
  (about :397) says "use `pyforge marshal preserve tag` or `python scripts/worktree_sweep.py --retire <branch>`".
- **Neither form exists.** `python scripts/worktree_sweep.py --retire x` exits 2 with "unrecognized arguments:
  --retire x"; the parser accepts only `--execute`, `--delete-merged-local-branches`, `--prune-home-remotes`,
  `--preserve-dir` and `--format`. No marshal CLI registers a `preserve` verb. Both are planned work: marshal Story
  87.1 (the sweeper's `--remote` and explicit-name `--retire`) and Story 87.3 (`pyforge.core.preserve_refs` and its
  verb), both `backlog`. Stories 85.1 and 85.4 wrote the reasons ahead of them, and CAP-165's intent names both forms.
- **Nothing checks a reason.** The hook asserts that its `MATCHERS` match the roster's ids, and the hook tests pin
  that the two reasons contain `worktree_sweep.py --retire` (`tests/scripts/test_pre_shell_hook.py` about :608, :709,
  :754), so the tests hold the broken text in place.

**Approach:**

- **A test over the roster.** A new test reads every `session_denials` reason, each string of a reason object
  included, and takes every backticked span. It classifies each span:
  - `python scripts/<x>.py …` or `uv run _bmad/scripts/<x>.py …`: the file exists, and its parser accepts every flag
    the span names (parsed with placeholders filled, or checked against the script's `--help`);
  - `pixi run -e <env> <task> …`: `pixi.toml` declares the environment and the task (a `{task}` placeholder stands for
    any guild task);
  - `pyforge <station> <verb> …`: that station's CLI parser accepts the verb path. The test builds the parser from
    source (`sys.path` on the station's and `pyforge-core`'s `src/`, as the detector tests load doctor's registry), so
    it runs in the dependency-free `pyforge-ci` environment the CI `scripts-suite` uses; steward's `cli.py` and
    `pyforge.core.flags` import only the standard library. A station whose parser cannot be built there fails the
    span, never skips it;
  - third-party, not checked: a span whose first word is `git`, `gh` or `npx`, `uv run` with no script path, `pixi`
    with a subcommand other than `run`, or a bare flag (`--squash`).
  A placeholder (`<branch>`, `<slug>`, `<project>/<spec>`, `<station>`, `{task}`) stands for an argument. A span the
  test cannot classify fails it, so a new reason cannot slip past.
- **Two reasons name what exists.** `protected-ref-deletion` and `unreachable-ref-deletion` stop naming
  `--retire` and `marshal preserve tag`. Until marshal 87.1 and 87.3 ship those forms, the sanctioned act is the
  operator's: the reason tells the agent to hand the operator the command (for a protected branch, a loop home, or a
  deletion that would orphan commits). The `fetch_remedy` reason keeps its `git fetch origin` and drops "the
  sanctioned preserve/retire forms".
- **Only reason text changes.** The ids, triggers, `applies_to`, the hook's `MATCHERS` and their parity check are
  untouched; no denial is added or removed. Adding or changing a denial is a governance act, and the operator rulings
  of 2026-10-04 that created these two entries stand.
- **Later.** When marshal 87.1 and 87.3 land, their stories may name their forms in these reasons again; the same test
  then admits them once they resolve (a marshal verb needs marshal's parser buildable where the test runs, or the
  resolver extended by that story).

Ledger key: `85-6-every-command-a-session-denial-names-as-the-sanctioned-form-exists`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-165 (FR-38): the reasons Stories 85.1 and 85.4 wrote; and CAP-5
  (Story 63.3): each denial gives "a one-line reason naming the sanctioned form". A reason that names a form which does
  not exist breaks that promise, so this is a fix and mints no CAP.
- **CAP-165's wording.** CAP-165's intent says the reachability denial names "`marshal preserve tag` and the sweeper's
  `--retire`". Those are its marshal twin's forms (spec-pyforge-marshal:CAP-287, Stories 87.1 and 87.3); this story
  reads that clause as binding once they resolve, and records the reading in the Spec memlog's mint entry, not as a
  `SPEC.md` change.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag; the hook is a session guardrail
  (`detector-or-gate`).
- **Origin.** Found on 2026-10-06 while an abandoned scratch workspace was cleaned up: the hook's advice named a flag
  the sweeper does not have. Re-verified on `b364823896` (exit 2).

## Acceptance Criteria

- Given the roster on `b364823896` When the new test runs Then it fails, naming `python scripts/worktree_sweep.py
  --retire <branch>` (in two reasons) and `pyforge marshal preserve tag`.
- Given the fixed roster When the new test runs Then it passes: `python scripts/spec_surface_check.py --write-baseline
  --spec <project>/<spec>`, `uv run _bmad/scripts/memlog.py`, `pixi run -e pyforge-guild sprint-ledger-sync --
  --project <station>`, `pixi run -e pyforge-guild {task}` and `pyforge steward workspace start <slug>` resolve, and
  the third-party spans are skipped.
- Given a fixture roster whose reason names `python scripts/worktree_sweep.py --no-such-flag` When the test runs
  Then it fails naming the flag; a reason naming `python scripts/no_such_script.py` fails naming the path; a reason
  naming `pyforge steward no-such-verb` fails naming the verb; a reason naming an unclassifiable span fails naming it.
- Given the fixed roster When the hook denies `git branch -D` on a branch whose tip nothing else reaches, or `git
  push origin --delete loop/x` Then the reason names the operator act and no command that fails.
- Given the fixed roster and the script When `load_denial_rules()` runs Then every id still matches a callable in
  `MATCHERS`, and the id, trigger and `applies_to` of every entry are byte-identical to `b364823896`.
- Given `--retire` put back into either reason When the new test runs Then it fails (mutation).

## Boundaries & Constraints

**Always:**
- Change only reason strings in `docs/governance/guild-roster.json`.
- Keep each reason one line that names what to do instead.
- Update the hook tests that pinned `worktree_sweep.py --retire` to assert the new text.
- Run the new test in the CI scripts suite (`pyforge-doctor-scripts-test`, the `scripts-suite` twin), like the hook's
  own tests.

**Never:**
- Never add, remove or re-scope a denial, and never touch `MATCHERS` or the parity check.
- Never name a command in a reason that the test does not resolve or skip as third-party.
- Never print a tag-minting remedy (a `git tag preserve/…` or `git tag archive/…` line): marshal Story 87.2's rule,
  after a printed remedy minted 682 public tags.
- Never add `--retire` to `scripts/worktree_sweep.py` here; that is marshal Story 87.1.
- Never weaken or delete an existing test.

## I/O & Edge-Case Matrix

| Span in a reason | Classified as | Resolves when |
|---|---|---|
| `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` | repo script | file exists, parser accepts both flags |
| `python scripts/worktree_sweep.py --retire <branch>` | repo script | never on `b364823896`: `--retire` rejected |
| `uv run _bmad/scripts/memlog.py` | repo script | file exists |
| `pixi run -e pyforge-guild sprint-ledger-sync -- --project <station>` | pixi task | env and task declared |
| `pixi run -e pyforge-guild {task}` | pixi task | env declared; `{task}` is a placeholder |
| `pyforge steward workspace start <slug>` | station verb | steward's parser accepts `workspace start` |
| `pyforge marshal preserve tag` | station verb | not until marshal Story 87.3 |
| `git fetch origin`, `gh pr merge --merge`, `npx skills add`, `pixi lock`, `uv run`, `--squash` | third-party | not checked |
| anything else | unclassified | the test fails |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-07 (tooling gaps) entry.
- Epic: Epic 85 (CAP-165; `in-progress` while Story 85.5 is `blocked`).
- Ledger key: `85-6-every-command-a-session-denial-names-as-the-sanctioned-form-exists`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Spec: `spec-pyforge-steward/.memlog.md` records the mint and the reading of CAP-165's naming clause; `SPEC.md`
  untouched.
- Governance: reason text only; the `session_denials` list (ids, triggers, `applies_to`) is unchanged.
- Cross-station: marshal Stories 87.1 and 87.3 may restore their forms in these reasons when they ship; this story's
  test then admits them.
- Minted 2026-10-07 with Stories 63.7 and 13.5, in one chain commit. Epic 85's `[epic_surfaces]` entry already
  admits every path above.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_session_denial_forms.py
  tests/scripts/test_pre_shell_hook.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the CI `scripts-suite` twin).
- Mutation: put `--retire` back into the `protected-ref-deletion` reason and re-run the new test; it fails. Restore it.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
