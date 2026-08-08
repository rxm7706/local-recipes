---
title: 'CLI Runbooks & Troubleshooting'
type: 'feature'
created: '2026-08-08'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** The Epic 12 ACs in
`_bmad-output/projects/pyforge-herald/planning-artifacts/epics-with-stories.md`
(lines 972-1006) call for "how to author a notice" / "how to publish a
claim" walkthroughs and a troubleshooting section covering "webhook
failures, automation misses, stale links." That framing assumes the
live-database/webhook/cron version of Epics 8-10 the epics doc originally
specced. Epics 8-10 actually shipped **scaled down** to local JSON
storage with every record created by an operator running an explicit CLI
command by hand (2026-08-08 scope decision,
`docs/dreams/herald-moments-2-4-live-backend.md`) -- there is no webhook,
database, or cron anywhere in this codebase. Documenting "webhook not
firing" diagnosis for infrastructure that was never built would send an
operator debugging a phantom.

**Approach:** write `docs/cli-runbooks.md` covering the two real
walkthroughs (author a notice, publish a claim) plus the operator-role
gate mechanics, then a troubleshooting section built entirely from
failure modes reproduced by actually running the built `herald` binary in
a scratch directory (not from the epics doc's illustrative examples):
operator-role refusal, evidence-link validation failure at publish time,
a malformed `.herald/*.json` file, `--date-range`/`--json` usage errors,
unknown station/claim/notice, and argparse-level usage errors. Every
command and its exact stdout/stderr in the doc was captured live via
`pixi run --frozen -e pyforge-herald herald ...` on 2026-08-08 -- none of
it is guessed or copied from the spec's fictional webhook examples. An
explicit "what is not a failure mode here" callout and an escalation path
close the file.

**Judgment call: one consolidated `docs/` directory for all four Epic 12
stories, not scattered locations.** The package had no existing `docs/`
convention (only a stale `README.md` describing the pixi build-skeleton
stage) and `web/README.md` covers only the web app's own dev workflow --
neither was a natural home for operator runbooks. `docs/README.md` indexes
all four Epic 12 files; the package `README.md` gained a two-line pointer
to it (the only change to a non-`docs/` file in this whole epic).

## Boundaries & Constraints

**Always:**
- Every command example in the doc reproduces a command actually run
  against the built `herald` binary during authoring; every literal error
  message quoted is the real string the CLI printed, not a paraphrase.
- The scope caveat (no webhook/database/cron; see the Dream) is stated
  once, prominently, near the top -- not repeated per subsection.
- Cross-references `automation-troubleshooting.md` (Story 12.4) for
  `herald success validate` (re-checking evidence on an already-published
  claim) rather than duplicating that content here, since this file's
  evidence-link section only covers the publish-time hard-abort case.

**Block If:** N/A -- no spike gate; pure documentation.

**Never:**
- No fictional troubleshooting content (webhook retries, cron-miss
  diagnosis, operator-alert delivery) presented as if it exists.
- No production-code behavior change implied by the docs that isn't true
  of the actual `cli.py`/`auth.py`/`errors.py` source read as part of this
  story's research.

## I/O & Edge-Case Matrix

N/A -- documentation-only story; no new code paths. The matrix below is
the set of failure modes the troubleshooting section actually verifies by
reproduction (all captured live, 2026-08-08, via the built `herald`
binary in a scratch directory):

| Scenario | Command | Real captured result |
|---|---|---|
| No auth context | `herald progress warden --update ...` | `OperatorAuthorizationError: auth context missing. Configure with \`herald auth login\` or set HERALD_TOKEN env var` (exit 1) |
| Wrong role | `HERALD_TOKEN=viewer:x herald progress warden --update ...` | `OperatorAuthorizationError: unauthorized: operator role required (found role 'viewer')` (exit 1) |
| Broken evidence link at publish | `herald success publish <id> --thesis ...` | `EvidenceLinkError: claim '<id>' has 1 broken evidence link(s): ...` (exit 1, nothing persisted) |
| Malformed `claims.json` | `herald success list` (after hand-corrupting the file) | `HeraldError: claims file ... could not be read: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)` (exit 1) |
| Bad `--date-range` | `herald progress --date-range "2026-08-01"` | `InvalidDateRangeError: Invalid date format: ...` (exit 1; JSON-shaped on stderr with `--json`) |
| Unknown station | `herald progress bogus-station` | `HeraldError: Station 'bogus-station' not found. Available: ...` (exit 1) |
| Unknown subcommand | `herald bogus` | argparse usage error, exit 2 |
| No command | `herald` | `no command given; valid subcommands: ...` (exit 1, not 2) |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/docs/cli-runbooks.md` -- create --
  the runbook + troubleshooting doc.
- `src/shared/packages/pyforge-herald/docs/README.md` -- create -- index
  for all four Epic 12 docs (shared across Stories 12.1-12.4; created once
  by this story).
- `src/shared/packages/pyforge-herald/README.md` -- edit -- two-line
  pointer to `docs/README.md` and `web/README.md`, added under the
  existing "Develop" section.

No `src/pyforge/herald/` (production code) changes. One candidate fix was
identified and deliberately **not** made: `auth.py`'s
`OperatorAuthorizationError` message references a nonexistent `herald auth
login` subcommand. `tests/test_auth.py::test_...` asserts that exact
wording as Story 6.3's own AC text, so correcting it would mean revising a
locked acceptance-criterion string and its test, which is out of scope for
a documentation story. Documented instead as a known wording gap in both
`cli-runbooks.md` and `operator-guide.md` (Story 12.3), with the real
remediation (`HERALD_TOKEN` / `~/.herald/config`) given explicitly.

## Design Notes

Reframing rationale beyond what's stated in Intent: the original AC's
"escalation path (contact Herald team, file issue)" assumed a team/backend
this repo doesn't have either -- there is no separate Herald team inbox.
The doc's escalation path instead points at (1) this repo's own
troubleshooting docs, (2) the Dream file for anything that looks like a
missing automation, (3) a GitHub issue against `rxm7706/local-recipes`,
matching how every other piece of this repo actually gets support.

## Verification

**Commands:**
- Every `herald` invocation quoted in `cli-runbooks.md` was run against
  `pixi run --frozen -e pyforge-herald herald ...` (built via `which
  herald` inside that env) in a scratch directory outside the repo, and
  its real stdout/stderr/exit code captured before being pasted into the
  doc.
- No automated test suite applies to markdown-only changes; `ruff
  format`/`ruff check` untouched (no `.py` files under this story).

## Spec Change Log

## Review Triage Log

### 2026-08-08 -- Adversarial review pass (Blind Hunter + Edge Case Hunter, no shared context)

- `[medium]` `[patch]` **No file told a reader how to get `herald` on their command line** -- every worked example silently assumed an activated `pyforge-herald` pixi environment, with the only hint a footnote saying the *doc's own author* ran it that way. A first-time operator following any doc's first example verbatim in a bare shell hits `command not found`, not any documented `HeraldError`. Fixed: added a Prerequisites section to `operator-guide.md` (the natural "getting started" home for it) plus a one-line cross-reference at the top of `cli-runbooks.md`.
- `[low]` `[patch]` **The claim id `9c3590d4-...` was reused in this file's own troubleshooting section with contradictory evidence** (the walkthrough shows it published cleanly; the "Evidence link validation failure" section shows the *same id* failing to publish on a broken link) -- both self-contradictory within this one file and, separately, contradictory against `automation-troubleshooting.md`'s reuse of the same id with yet another evidence shape. Fixed: the troubleshooting section now uses a distinct id (`a17e2b60-...`) with an explicit note that it's a separate scratch claim, not the walkthrough's.
- `addressed_findings`: 2 (1 medium, 1 low). No `intent_gap`, no `bad_spec`, no `defer`, no `reject`.

**Follow-up review recommendation:** none outstanding for this story.
