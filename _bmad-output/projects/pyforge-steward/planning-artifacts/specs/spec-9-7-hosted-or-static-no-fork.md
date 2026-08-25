---
title: 'Hosted or static, no fork (Epic 9 Story 9.7, pyforge-steward)'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: '822bc2a96f3e1d16c7c75316a78f5a278ab4b0ce'
final_revision: '022e11fa86'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-secure-live-dashboards/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-secure-live-dashboards-2026-08-09/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** CAP-8 requires that the same dashboard definition publish either hosted
(role-isolated) or as a static GitHub Pages export — never both, never a fork — but no verb in
`pyforge.steward.deploy` produces a static export today, and AD-10's refusal ("a board that has
declared an access column may not be delivered by static export... refuses rather than warns")
has no owner.

**Approach:** Add a fourth `steward deploy static --board SLUG --panel LABEL=PATH [--panel ...]
[--access-column NAME]` verb to `deploy.py`. It refuses first, unconditionally, when
`--access-column` names a non-empty column; otherwise it assembles the caller-supplied,
already-rendered panel HTML fragments (e.g. an adopter's own `plotly.graph_objects.Figure.
to_html()` output) verbatim into one self-contained responsive-grid `index.html`, written
atomically to `docs/dashboard/<board>/`. The existing `steward deploy dashboard` verb then
commits/pushes that unchanged (same reconciled-push mechanism `kedro-viz-publish.yml` already
reuses for the exact same reason) — no new git plumbing or GitHub Pages workflow is needed.

## Boundaries & Constraints

**Always:**
- `_run_static` refuses — never warns, never writes anything, never reads a `--panel` path —
  when `ns.access_column` (stripped) is non-empty, before any other validation (AD-10).
- Output always lands at `docs/dashboard/<board>/index.html`, never a caller-chosen path, so the
  existing `steward deploy dashboard` reconciled-push mechanism picks it up unchanged.
- `--board` is validated as a filesystem-safe slug (`^[A-Za-z0-9_-]+$`) before being joined into
  that path — never used unvalidated, which would let `--board ../../etc` or an absolute-path
  value write outside `docs/dashboard/`.
- Each panel's `html` is embedded byte-for-byte, never parsed or transformed — the guarantee
  that hosted and static modes share one chart-producing source, never re-derived, never a
  second codebase.
- New code lives in `deploy.py` only; it may not import `pyforge.steward.dashboard`, `django`,
  or `channels` — enforced by `tests/meta/test_invariants.py`'s existing AST-based
  `test_no_module_outside_dashboard_imports_dashboard_django_or_channels` guard.
- No new third-party dependency: panels arrive as pre-rendered HTML strings, so `pyforge-steward`
  never imports `plotly` and the `[dashboard]` extra gains no new pin.

**Block If:** none identified — CAP-8/AD-10 fully bound the scope; no undecided cross-cutting
question remains.

**Never:**
- Build or export a Plotly figure itself, or migrate any real board (Atlas's or otherwise) to
  static delivery — this story ships the mechanism; a specific adopter's CI wiring is that
  adopter's own job (architecture "Deferred": each adopter's migration is the owning station's
  call).
- Accept an `AccessDeclaration` object, or import anything under `pyforge.steward.dashboard` —
  the access-column signal crosses the `deploy.py` boundary as a plain string flag, identical in
  shape to `DeploymentTopology`'s dotted-path strings (Story 9.5 precedent).
- Reuse the `dashboard` verb name or write outside `docs/dashboard/<board>/` — collides with the
  existing GitHub-Pages program console, already flagged as a naming trap on Story 9.1's
  deferred-work ledger.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | `--board demo --panel "East=east.html" --panel "West=west.html"`, no `--access-column` | `docs/dashboard/demo/index.html` written, both panels' HTML verbatim in call order | No error expected |
| Access column declared | same as above plus `--access-column region` | refused before any panel path is read; `docs/dashboard/demo/` untouched | `DutyResult(ok=False, ...)` naming AD-10 |
| Duplicate panel labels | two `--panel` entries with the same label | refused; nothing written | Names the duplicate label |
| Malformed `--panel` | value with no `=`, or an empty label | refused; nothing written | Names the malformed entry |
| Unreadable `--panel` path | path does not exist / unreadable | refused; nothing written | `OSError` caught, path named |
| Missing `--board` or no `--panel` at all | `--panel` omitted entirely, or `--board` omitted | refused | Names the missing flag |
| Unsafe `--board` value | `--board ../../etc` or `--board /tmp/x` | refused; nothing written outside `docs/dashboard/` | Names the invalid board slug |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` -- MODIFY: add
  `StaticPanel` frozen dataclass (`label: str`, `html: str`), `render_static_index(panels, *,
  board) -> str`, `_is_board_output_dir_safe_to_write(output_dir) -> bool`, `_run_static(ns) ->
  DutyResult`, `"static"` added to `_DEPLOY_VERBS`, and an explicit dispatch branch in
  `DeployDuty.run`. `import html` (stdlib, for escaping) is required; `import re` remains
  forbidden (`test_deploy_has_no_story_status_derivation` bans it unconditionally) — the
  board-slug check stays the existing hand-rolled character-set scan.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- MODIFY:
  `_add_deploy_subparsers` gains the `static` subparser (`--board`, repeatable `--panel`,
  `--access-column`); update its docstring, the subparsers `metavar`, and `_HELP["deploy"]`.
- `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_static.py` -- NEW: covers
  every I/O-matrix row plus CLI round-trip, mirroring `test_deploy_perimeter.py`'s shape.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py`'s pre-existing
  `dashboard_diff()` (Story 2.2, `deploy.py` lines ~150-165 as of this amendment) -- MODIFY:
  **the amendment closing review pass 2's triggering finding.** Extend it to also detect
  untracked new files under `docs/dashboard/` (it currently sees only changes to already-tracked
  files via `git diff`), so `steward deploy static`'s first-ever publish of a new board is no
  longer invisible to `steward deploy dashboard`'s reconciled-push gate. Its only production call
  site is `_run_dashboard`; its only direct test file is `test_deploy_reconcile.py`, whose
  assertions are truthy/falsy on `diff_text.strip()` only (never exact diff-text shape) — confirm
  this before changing it, and preserve that property in the fix.
- `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_reconcile.py` -- MODIFY: add
  a case proving a brand-new untracked file under `docs/dashboard/` now produces a non-empty
  `dashboard_diff()` result (the exact gap review pass 2 found), alongside the existing
  tracked-file-only cases, which must keep passing unchanged.

## Tasks & Acceptance

**Execution:**
- [x] `deploy.py` -- add `StaticPanel` frozen dataclass with `__post_init__` validating both
  fields are `str`, `label` non-empty/non-padded -- mirrors `declarations.py`'s established
  validation idiom, kept in `deploy.py` since it may not import from `dashboard/`
- [x] `deploy.py` -- add `render_static_index(panels: Sequence[StaticPanel], *, board: str) ->
  str` -- raises `ValueError` naming a duplicate label; embeds each panel's `html` byte-for-byte
  verbatim (unescaped, unchanged from before this amendment — this is deliberate per Boundaries);
  but escapes `panel.label` and `board` with the stdlib `html.escape()` before interpolating them
  into `<h2>{label}</h2>` / `<title>{board}</title>` -- both feed a page this story's own Intent
  says gets committed and published, and neither carries the "verbatim by design" justification
  `html` does; add `<meta name="viewport" content="width=device-width, initial-scale=1">` to the
  rendered `<head>` so the "responsive grid" claim actually holds on a mobile viewport
- [x] `deploy.py` -- add `_is_board_output_dir_safe_to_write(output_dir: Path) -> bool` (or
  equivalent inline check), wrapped by its `_run_static` caller in `except OSError`
  (`.exists()`/`.is_dir()`/`.iterdir()`/`.stat()` can raise `PermissionError`, uncaught otherwise,
  contradicting `_run_static`'s own "never an uncaught exception" guarantee -- refuse naming the
  error instead). Before inspecting `output_dir` itself, refuse (`False`) if EITHER of the two
  fixed ancestor paths this verb's output always resolves through -- `docs` or `docs/dashboard`
  (`_DASHBOARD_RELATIVE_PATH`; derive from `output_dir`'s own parents rather than a bare
  `Path("docs")`, which would resolve against the process's actual working directory rather than
  necessarily `repo_root()`) -- `.is_symlink()`. Then refuses (`False`) if `output_dir.is_symlink()`
  (pass-2 finding: a pre-existing symlink at the target board path must never be followed).
  Otherwise `True` when `output_dir` does not exist, exists but is empty, or exists containing
  entries EXACTLY matching one of: `{index.html}` (a completed prior run -- idempotent re-publish
  is not blocked), `{index.html.tmp}` (a killed FIRST publish -- self-heals), or `{index.html,
  index.html.tmp}` (a killed REPUBLISH of an already-published board -- self-heals). **Every
  entry considered in any of those three shapes must positively satisfy `entry.is_file()` AND
  independently fail BOTH `entry.is_symlink()` AND `entry.stat().st_nlink != 1` before being
  trusted as a real file this verb itself wrote** -- **pass-5's triggering finding, and the
  structural fix closing this recurring class rather than adding one more exclusion to it**: the
  prior amendment's check was built as a list of NEGATIVE exclusions (not a symlink, not
  multiply-linked) with no POSITIVE assertion that the entry is even a plain regular file in the
  first place -- so a FIFO (`os.mkfifo`) or a bound Unix domain socket at a trusted name passes
  as "safe" (neither a symlink nor multiply-linked) exactly like a genuine file, a fifth
  recurrence of the "a filesystem-identity trick bypasses the trust check" pattern (directory
  symlink → entry symlink → entry hard link → entry special-file-type). Requiring `is_file()` as
  a POSITIVE condition (which by definition excludes every non-regular-file type -- FIFOs,
  sockets, block/char devices, directories) closes the whole class of "not a plain file" tricks
  at once, rather than requiring a new named exclusion for every filesystem primitive as it's
  discovered; `is_symlink()` remains a SEPARATE, necessary check alongside it, since `is_file()`
  follows symlinks and reports `True` for a symlink pointing at a genuine regular file. `False`
  for anything else (foreign content this verb did not create, e.g. the real
  `docs/dashboard/kedro-viz/`, or any symlinked/hard-linked/non-regular entry regardless of
  name/shape). Needs no new marker file or persistent state
- [x] `deploy.py` -- add `_run_static(ns) -> DutyResult` -- refuses first, unconditionally, if
  `ns.access_column` (stripped) is non-empty; else validates `--board` matches
  `^[A-Za-z0-9_-]+$` (refusing before any path is constructed from it) and `--panel` presence,
  then each `--panel LABEL=PATH` shape, reads each path's text catching **both** `OSError` **and**
  `UnicodeDecodeError` as a named refusal (mirrors `_tracked_ledger_refusal`'s own established
  precedent for this exact bug class -- `UnicodeDecodeError` is a `ValueError` subclass, not an
  `OSError` subclass, so it needs its own except clause or a non-UTF-8 `--panel` file crashes
  instead of refusing), calls `render_static_index`, then -- before writing -- calls
  `_is_board_output_dir_safe_to_write` inside `except OSError` (see above); if unsafe, refuses
  naming the pre-existing foreign content and writes nothing; otherwise writes atomically to
  `docs/dashboard/<board>/index.html` (mirrors `_run_perimeter`'s write-then-rename-with-cleanup
  pattern), with one refinement: `mkdir(parents=True)` is called WITHOUT `exist_ok=True` on the
  branch where `output_dir` did not already exist at safety-check time (`exist_ok=True` only on
  the branch where it legitimately already existed, e.g. a valid re-publish) -- **pass-5 finding,
  folded into the triggering amendment**: this closes the highest-value, lowest-cost slice of the
  check-then-write TOCTOU window for free -- a symlink raced into that exact path in the narrow
  gap between the safety check and the write now makes `mkdir()` raise `FileExistsError` (an
  already-caught `OSError`) instead of silently succeeding through it; full TOCTOU closure beyond
  this remains a deliberately accepted, file-wide, consistently-applied risk posture (see Design
  Notes). On a write failure, track every ANCESTOR directory `mkdir(parents=True)` freshly
  created (not only the leaf `output_dir`) and best-effort `rmdir()` each, innermost first,
  alongside the existing temp-file cleanup, so a failed write leaves no residual empty directory
  anywhere. Wrap the string-typed operations on `ns.access_column`/`ns.board`/each parsed panel
  label (`.strip()` calls, `_is_valid_board_slug`'s character scan) so a non-string field on a
  malformed `Namespace` produces a named refusal (`TypeError`/`AttributeError` caught) rather than
  an uncaught crash, mirroring `_run_perimeter`'s established precedent in this exact file for
  the identical class of gap
- [x] `deploy.py` -- add `"static"` to `_DEPLOY_VERBS`; add an explicit `if verb == "static":
  return _run_static(ns)` branch in `DeployDuty.run` -- the trailing `else` there falls through
  to `_run_status` today, so an explicit branch is required or `static` would silently misroute
- [x] `cli.py` -- `_add_deploy_subparsers` gains the `static` subparser: `--board` (required),
  `--panel` (repeatable, `action="append"`, `metavar="LABEL=PATH"`), `--access-column` (optional,
  default `None`); update the function docstring, `metavar="{dashboard,status,perimeter,static}"`,
  and `_HELP["deploy"]`
- [x] `deploy.py` -- extend the pre-existing `dashboard_diff()` (Story 2.2) to detect genuinely
  new, untracked files under `docs/dashboard/`, not only changes to already-tracked ones -- e.g.
  combine its existing `git diff -- docs/dashboard` text with a check for untracked entries (`git
  ls-files --others --exclude-standard -- docs/dashboard`, or equivalent) and fold any found into
  a non-empty returned string. Preserve its existing return contract exactly: `""` (falsy) only
  when nothing under `docs/dashboard/` differs from what's committed, non-empty (truthy) otherwise
  -- its only two callers (`_run_dashboard`'s "nothing to deploy" gate and its `--dry-run`
  printout) both key off that same truthy/falsy signal, never the text's exact shape
- [x] `tests/conformance/test_deploy_static.py` -- NEW -- covers every I/O-matrix row plus CLI
  round-trip, section-comment-divided (validation → refusal → rendering → atomicity → CLI),
  mirroring `test_deploy_perimeter.py`; include cases for: a non-UTF-8 `--panel` file (refuses,
  does not crash), a `--panel` label containing `<`/`>`/`&` (escaped in the output, not injected),
  `--board` colliding with a pre-existing directory containing more than the shapes named above
  (refuses, writes nothing) alongside re-publishing a board whose existing directory contains only
  a prior lone `index.html` (succeeds, overwrites it), a pre-existing symlink AT the target board
  path (refuses, writes nothing outside `docs/dashboard/`), a stray `index.html.tmp` left by a
  simulated killed FIRST-publish run (self-heals, succeeds), a `{index.html, index.html.tmp}` pair
  left by a simulated killed REPUBLISH (self-heals, succeeds), a directory whose lone
  `index.html.tmp` ENTRY is itself a symlink to an outside file (refuses; outside file's content
  provably unchanged after the run), a directory whose lone `index.html.tmp` ENTRY is a HARD LINK
  (`os.link`, not a symlink) to an outside file (refuses; outside file's content provably
  unchanged after the run via a real before/after content comparison, not merely an assertion the
  call refused), -- **pass-5's triggering finding, most important new case** -- a directory whose
  lone `index.html.tmp` entry is a FIFO (`os.mkfifo`) (refuses; does not hang), and a write
  failure occurring AFTER `mkdir()` succeeds that cleans up every freshly-created ancestor
  directory (this exact case existed in an earlier implementation attempt but was missing from
  the most recent re-derivation -- restore it)
- [x] `tests/conformance/test_deploy_reconcile.py` -- MODIFY -- add a case proving a brand-new
  untracked file under `docs/dashboard/` now produces a non-empty `dashboard_diff()` result,
  alongside the existing tracked-file-only cases (which must keep passing exactly as written)

**Acceptance Criteria:**
- Given a board with two `--panel` entries and no `--access-column`, when `steward deploy static
  --board demo --panel "East=east.html" --panel "West=west.html"` runs, then
  `docs/dashboard/demo/index.html` is written containing both panels' HTML verbatim, in the
  order passed, and the command exits `EXIT_OK`.
- Given the same command with `--access-column region` added, when it runs, then it refuses
  (`EXIT_FAILED`), `docs/dashboard/demo/` is not created or modified, and neither `--panel`
  path is ever opened.
- Given two `--panel` entries sharing the same label, when the command runs, then it refuses
  naming the duplicate label and writes nothing.
- Given a `--panel` value with no `=` separator, an empty label, a path that does not exist, or a
  path whose content is not valid UTF-8, when the command runs, then it refuses naming the
  specific malformed/unreadable entry (never an uncaught exception) and writes nothing.
- Given `--board ../../etc` or another value containing `/`, `\`, or `..`, when the command runs,
  then it refuses naming the invalid board slug before constructing any path from it.
- Given `--board <slug>` where `docs/dashboard/<slug>/` already exists and contains anything
  other than a lone `index.html` (e.g. the repo's real `docs/dashboard/kedro-viz/`), when the
  command runs, then it refuses naming the pre-existing foreign content and writes nothing; given
  the same directory contains only a prior `index.html` this verb wrote, when the command runs
  again for that board, then it overwrites that file successfully (idempotent re-publish is not
  blocked).
- Given a `--panel` label containing `<`, `>`, or `&`, when the command runs, then the written
  page contains the escaped form in the heading, never raw markup, while the corresponding
  panel's `html` value is still embedded byte-for-byte verbatim.
- Given a pre-existing symlink at `docs/dashboard/<board>` (regardless of what it points to or
  whether the target is empty), when the command runs, then it refuses and writes nothing through
  the symlink.
- Given `docs/dashboard/<board>/` contains only a stray `index.html.tmp` left by an earlier,
  killed FIRST-publish run, when the command runs again for that board, then it succeeds,
  self-healing rather than permanently refusing; given instead it contains both a prior
  `index.html` and a stray `index.html.tmp` (a killed REPUBLISH), when the command runs again,
  then it likewise succeeds and self-heals.
- Given `docs/dashboard/<board>/` contains a single entry named `index.html.tmp` that is itself a
  symlink to a file outside `docs/dashboard/`, when the command runs, then it refuses, and the
  symlink's target file's content is unchanged after the run.
- Given `docs/dashboard/<board>/` contains a single entry named `index.html.tmp` that is a HARD
  LINK (not a symlink) to a file outside `docs/dashboard/`, when the command runs, then it
  refuses, and the linked file's content is byte-identical before and after the run.
- Given `docs/dashboard/<board>/` contains a single entry named `index.html.tmp` that is a FIFO
  (not a symlink, not a hard link, `st_nlink == 1`), when the command runs, then it refuses
  without hanging.
- Given a board's first-ever `steward deploy static` publish (a genuinely new, untracked
  `docs/dashboard/<board>/index.html`), when `steward deploy dashboard` (bare) then runs, then
  `dashboard_diff()` reports a non-empty diff and the file is committed and pushed — the board is
  not silently invisible to the reconciled-push gate on its first publish.
- Given the whole `pyforge-steward` test suite, when `pixi run -e pyforge-steward
  pyforge-steward-test` runs, then it passes with zero regressions, and
  `tests/meta/test_invariants.py`'s dashboard-import-boundary guard reports no new offender for
  `deploy.py`.

## Spec Change Log

- **Implementation deviation (non-scope-changing):** `--board`'s `^[A-Za-z0-9_-]+$` validation is
  implemented as a manual character-set check (`_is_valid_board_slug`) rather than `re.compile`.
  A pre-existing guard, `tests/meta/test_invariants.py::test_deploy_has_no_story_status_
  derivation` (Story 5.2/AD-71/AD-1), bans `import re` anywhere in `deploy.py` unconditionally
  (it exists to keep this module from re-deriving individual story-status parsing, for which `re`
  would be the toolkit) -- discovered only by running the full suite, which the spec's own
  Verification section requires. The equivalent `^[A-Za-z0-9_-]+$` semantics are reproduced by
  hand; behavior is unchanged.

- **Bad-spec amendment (2026-08-13, review pass 1).** Triggering finding: `_run_static` wrote to
  `docs/dashboard/<board>/index.html` via unconditional `mkdir(exist_ok=True)` + atomic rename,
  with no check for pre-existing unrelated content at that path — confirmed live against this
  repo's real `docs/dashboard/kedro-viz/` (a git-tracked Kedro-Viz static export with its own
  `assets/`/`api/`/`index.html`), which `steward deploy static --board kedro-viz ...` would have
  silently overwritten. The original Boundaries named only the `dashboard`-verb-name collision
  (Story 9.1's ledger); the analogous board-slug/directory-content collision was never named. Known-
  bad state avoided: silent, unrefused destruction of another mechanism's published site content
  with no test coverage and no warning. Amended: Tasks & Acceptance gained an explicit directory-
  shape safety check (`_is_board_output_dir_safe_to_write` or equivalent) run before the write,
  refusing unless the target is absent, empty, or contains only a prior lone `index.html`; a new
  Design Note records why a directory-shape check was chosen over a persistent ownership marker.
  Folded into the same amendment (found by the same review pass, not independently triggering a
  second loopback): `UnicodeDecodeError` handling alongside `OSError` on `--panel` reads (mirrors
  `_tracked_ledger_refusal`'s already-established precedent for this exact bug class), `html.escape()`
  on `panel.label`/`board` before HTML interpolation (leaving `panel.html` verbatim, unchanged —
  that remains deliberate per the untouched Boundaries), a `<meta name="viewport">` tag, and
  best-effort cleanup of a freshly-`mkdir`'d directory on a subsequent write failure. **KEEP for
  re-derivation:** the verb's overall shape (`StaticPanel` dataclass + `render_static_index` pure
  function + `_run_static` orchestrator + explicit `DeployDuty.run` dispatch branch) worked and is
  unchanged by this amendment; the access-column-refused-first ordering worked and is unchanged;
  the atomic temp-write+rename pattern mirroring `_run_perimeter` worked and is unchanged (only
  gains the pre-write safety check and the empty-directory cleanup case); the `--board` slug regex
  implemented as a manual character-set scan (not `re`, per the Story Change Log entry above)
  worked and must be preserved unchanged; the CLI subparser wiring (`--board` required, `--panel`
  repeatable, `--access-column` optional) worked and is unchanged; the test file's section-comment-
  divided structure mirroring `test_deploy_perimeter.py` worked and should be preserved, extended
  with the new cases named in the amended Tasks above.

- **Bad-spec amendment (2026-08-13, review pass 2).** Triggering finding: the pre-existing
  `dashboard_diff()` (Story 2.2) is blind to genuinely new, untracked files under
  `docs/dashboard/` — verified live that a board's first-ever `steward deploy static` publish
  produces a file `git diff` never reports, so `steward deploy dashboard` says "nothing to
  deploy" and never commits it, contradicting this story's own Approach ("no new git plumbing
  needed"). Known-bad state avoided: every adopter's first-ever board publish silently sitting
  unpublished forever. Amended: Code Map + Tasks gained a `dashboard_diff()` extension task (detect
  untracked files, preserve the existing truthy/falsy contract exactly — confirmed low blast
  radius: one production call site, tests assert truthy/falsy only) plus a
  `test_deploy_reconcile.py` test-file addition; a new Design Note records why the shared function
  was fixed rather than duplicated. Folded into the same amendment (found by the same pass, not
  independently triggering a third loopback): `_is_board_output_dir_safe_to_write` (added last
  pass) gained a symlink check FIRST (a pre-existing symlink at the target path was bypassing the
  whole collision guard the prior amendment added) and now also treats a lone stray
  `index.html.tmp` as its own recoverable leftover rather than foreign content (self-heals after a
  killed prior run instead of permanently refusing); the write-failure cleanup now tracks and
  removes every freshly-created ANCESTOR directory, not only the leaf. **KEEP for re-derivation:**
  everything KEPT by the pass-1 entry above still applies unchanged (verb shape, access-column-
  first ordering, atomic write pattern, hand-rolled slug regex, CLI wiring, test structure); ADD:
  the directory-shape safety check's core logic (lone-`index.html`-or-empty-or-absent = safe)
  worked and is unchanged, only gaining the symlink pre-check and the stray-`.tmp` case; the
  `dashboard_diff()` fix must preserve the EXACT existing behavior for tracked-file-only diffs
  (both pre-existing `test_deploy_reconcile.py` tests must keep passing unmodified).

- **Bad-spec amendment (2026-08-13, review pass 3).** Triggering finding: independently confirmed
  by both reviewers, then reproduced live, that `_is_board_output_dir_safe_to_write`'s pass-2
  symlink defense checked `output_dir.is_symlink()` but never the ONE entry it then trusts via
  `entry.is_file()` — a symlink literally named `index.html.tmp` passed as "safe," and the
  subsequent write followed it, silently overwriting an arbitrary outside file. Known-bad state
  avoided: an arbitrary-file-overwrite primitive hiding inside the exact mechanism pass 2 added to
  prevent unsafe writes. Amended: the safety-check task now requires every entry it is about to
  trust (across all three now-recognized safe shapes) to independently fail `is_symlink()`, and
  extends self-heal to also cover a killed REPUBLISH (`{index.html, index.html.tmp}`, not only a
  killed first publish) since that shape review pass 3 also flagged as the more common real case
  the prior amendment left unsafe/permanently-blocking. Folded into the same amendment (found by
  the same pass, not independently triggering a fourth loopback): the safety-check's own
  filesystem probes now run inside `except OSError` at the call site (`PermissionError` was
  previously uncaught, contradicting `_run_static`'s own "never an uncaught exception" promise).
  Also this pass: one genuinely pre-existing, not-this-story's-problem finding
  (`dashboard_diff()`'s staged-but-uncommitted blind spot) was recorded as `DW-FU-9-7` in the
  deferred-work ledger rather than amended here — see Review Triage Log. **KEEP for
  re-derivation:** everything KEPT by the pass-1 and pass-2 entries above still applies unchanged;
  ADD: the three-shape safe-set (`{index.html}` / `{index.html.tmp}` / `{index.html,
  index.html.tmp}`) and the symlink-on-`output_dir` pre-check both worked and are unchanged, only
  gaining the additional per-entry symlink check and the third safe shape; the `dashboard_diff()`
  fix and its test coverage from pass 2 worked and are unchanged.

- **Bad-spec amendment (2026-08-13, review pass 4).** Triggering finding: independently confirmed
  by both reviewers, then reproduced live, that a HARD LINK (not a symlink) at a trusted entry
  path bypasses pass 3's `is_symlink()` check entirely — `entry.is_file()` is `True` for a hard
  link exactly as for a genuine regular file, so a hard-linked `index.html.tmp` passed as "safe,"
  and the subsequent write truncated the SHARED inode, silently corrupting an arbitrary outside
  file while `DeployDuty().run()` reported `ok=True` — worse than every prior recurrence of this
  bug class, since it succeeds rather than refuses. Fourth recurrence of the same "a filesystem-
  identity trick bypasses the trust check" pattern (directory symlink → entry symlink → entry
  hard link). Known-bad state avoided: silent data corruption reported as success. Amended: every
  trusted entry now also fails `.stat().st_nlink != 1` alongside `is_symlink()`. To reduce the
  chance of a fifth recurrence rather than fix one variant at a time, this amendment additionally
  closes two related gaps found in the same pass: the two FIXED ancestor paths (`docs`,
  `docs/dashboard`) are now checked for `is_symlink()` before any write (previously only the
  `--board`-controlled leaf was); and `_run_static`'s string-processing operations now catch
  `(TypeError, AttributeError)` around a malformed `Namespace` field, mirroring `_run_perimeter`'s
  own documented precedent in this exact file for the identical class of gap. **KEEP for
  re-derivation:** everything KEPT by the pass-1/2/3 entries above still applies unchanged; ADD:
  the per-entry `is_symlink()` check and the three-safe-shape name check both worked and are
  unchanged, only gaining the `st_nlink` check alongside `is_symlink()` and the two ancestor
  checks; the `dashboard_diff()` fix and its test coverage worked and are unchanged.

- **Bad-spec amendment (2026-08-13, review pass 5 — final loopback, `review_loop_iteration` at
  cap).** Triggering finding: independently confirmed by both reviewers via direct empirical
  testing, a FIFO or Unix domain socket at a trusted entry name (neither a symlink nor multiply-
  linked) passed `_is_board_output_dir_safe_to_write` exactly like a genuine regular file, because
  the check had only ever grown negative exclusions (not a symlink, not multiply-linked) with no
  positive assertion that the entry was a plain file to begin with — the fifth recurrence, at a
  new level, of the same "a filesystem-identity trick bypasses the trust check" pattern spanning
  all of passes 2 through 5. Known-bad state avoided: an unbounded tail of undiscovered filesystem
  primitives each requiring its own future review pass to find. Amended: every trusted entry must
  now positively satisfy `is_file()` in addition to failing `is_symlink()`/`st_nlink != 1` —
  `is_file()` excludes every non-regular-file type by construction, closing the class rather than
  one more instance of it; a new Design Note records why this is a structural fix, not one more
  patch, and both reviewers gave an explicit "sufficiently hardened for this threat model"
  assessment once it lands — the first such assessment across five passes. Folded into the same,
  final amendment: `mkdir()` drops `exist_ok=True` on the branch where `output_dir` did not
  already exist, closing the highest-value slice of the check-then-write TOCTOU window for the
  cost of one keyword argument, without taking on full lock-based concurrency-safety (a new
  Design Note explicitly records this as a deliberate, bounded, consistent-with-the-rest-of-the-
  file choice, not an oversight); a write-failure-cleans-up-ancestor-directories test — present in
  an earlier re-derivation but absent from the most recent one — is restored. **KEEP for
  re-derivation:** everything KEPT by the pass-1/2/3/4 entries above still applies unchanged; ADD:
  the per-entry `is_symlink()`/`st_nlink` checks, the three-safe-shape name check, the ancestor-
  path symlink checks, the `OSError` wrap, and the `_run_static` `(TypeError, AttributeError)`
  wrap all worked and are unchanged, only gaining the per-entry `is_file()` positive check and
  the conditional `exist_ok` on the fresh-creation `mkdir` branch; the `dashboard_diff()` fix and
  its test coverage worked and are unchanged.

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 1: (high 0, medium 1, low 0)
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

Findings from this pass (Blind Hunter + Edge Case Hunter, independent, no shared context) and
their disposition, recorded here because the bad_spec loopback makes lower-cascade categories
moot for this pass per the review protocol — restated on the next pass if they resurface:
- `[medium]` `[bad_spec]` **Triggering finding.** `_run_static` writes to
  `docs/dashboard/<board>/index.html` via `mkdir(exist_ok=True)` + atomic rename with no check
  for pre-existing, unrelated content already at that path. Confirmed live, not hypothetical:
  `docs/dashboard/kedro-viz/` already exists in this repo — a git-tracked Kedro-Viz static export
  with its own `assets/`, `api/`, `index.html` — and `steward deploy static --board kedro-viz
  ...` would silently overwrite its `index.html` today. The spec's existing Boundaries named only
  the `dashboard`-verb-name collision (Story 9.1's ledger), never the analogous board-slug/
  directory-content collision. Root cause traced to Tasks & Acceptance (the write-path task never
  specified an ownership check), not to Boundaries & Constraints itself, and is resolved with a
  single unambiguous mechanism — refuse unless the target directory is absent, empty, or contains
  exactly the lone `index.html` this verb itself would ever write (the only artifact it produces) —
  which reconciles idempotent same-board re-publish with refuse-don't-clobber for foreign content,
  with no new persistent marker/state. Amended below (see Spec Change Log).
- `[medium]` (moot, not actioned this pass — restate next pass if it resurfaces) Panel-read loop
  catches `OSError` but not `UnicodeDecodeError` (not an `OSError` subclass) on a non-UTF-8
  `--panel` file — crashes past the module's own established "refuse, never crash" convention
  (the identical bug class `_tracked_ledger_refusal` already fixed elsewhere in this same file).
  Folded into the amended Tasks below as a preventive fix rather than left to resurface.
  Independently found by both reviewers.
  - `[medium]` (moot, not actioned this pass) `render_static_index` interpolates `panel.label`
  into `<h2>{panel.label}</h2>` and `board` into `<title>{board}</title>` with no HTML-escaping —
  `panel.html` is deliberately verbatim by spec design, but `label`/`board` were never meant to
  be, and both feed a page this story's own Intent says gets committed and published on GitHub
  Pages. Folded into the amended Tasks below. Independently found by both reviewers.
  - `[low]` (moot, not actioned this pass) `output_dir.mkdir(parents=True, exist_ok=True)` can
  create a real (if empty) directory before a subsequent write failure; the failure-cleanup path
  only unlinks the temp file, never the directory, so the docstring's "nothing written until every
  check has passed" is imprecise (in practice inconsequential — git does not track empty
  directories — but cheap to close). Folded into the amended Tasks below.
  - `[low]` (moot, not actioned this pass) Generated page has no `<meta name="viewport">` tag,
  undermining the code's own "responsive grid" claim on mobile. Folded into the amended Tasks
  below.
  - `[low]` `[reject]` `--panel PATH` is unconstrained (arbitrary readable path, symlinks
  included) — this is the caller's own explicitly-supplied local file path under the same trust
  boundary as invoking the CLI at all (identical shape to the pre-existing `--tls-cert`/
  `--tls-key`/`--trusted-address` flags on `perimeter`), not a traversal vector; `--board`'s
  stricter validation exists because it constructs an *output* path, an unrelated risk class.
  - `[low]` `[reject]` "`--board` was not supplied" branch called dead code given the CLI's
  `required=True` — reachable and exercised via the tested `DeployDuty().run(ns)` direct-call
  surface (mirrors `_run_perimeter`'s identical defense-in-depth idiom), not actually dead.
  - `[low]` `[reject]` Concurrent same-`--board` invocations race on a shared, non-unique `.tmp`
  filename — an inherited limitation of the exact same fixed-name atomic-write idiom
  `_run_perimeter` already uses unchanged; not a regression this story introduced, and CI invokes
  this verb from a single job step per board, not concurrently.
  - `[low]` `[reject]` A hand-built `argparse.Namespace` with non-string `board`/`access_column`
  fields raises `AttributeError`/`TypeError` instead of a named refusal — unreachable via the real
  CLI (argparse always yields `str | None` for these untyped flags), matching the same
  assumed-shape trust level `_run_perimeter` already applies to its own `ns.*` fields.

### 2026-08-13 — Review pass 2
- intent_gap: 0
- bad_spec: 1: (high 1, medium 0, low 0)
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

- `[high]` `[bad_spec]` **Triggering finding.** `dashboard_diff()` (pre-existing, Story 2.2, a
  different story — `deploy.py`'s only untracked-file gate for `steward deploy dashboard`) runs
  plain `git diff -- docs/dashboard`, which shows changes to already-tracked files only; it is
  BLIND to genuinely new, untracked files. Verified live: after `steward deploy static --board
  newboard ...` writes `docs/dashboard/newboard/index.html` for the first time, `git status
  --porcelain` shows `?? docs/dashboard/newboard/` while `dashboard_diff()` returns `''`, so
  `steward deploy dashboard` (bare) reports "no diff — nothing to deploy" and never calls
  `commit_and_push_dashboard` — the board's first-ever publish sits unpublished forever unless an
  operator manually intervenes. `dashboard_diff`'s own docstring already documents the assumption
  this story breaks: "`dashboard-gen` only ever rewrites the existing tracked `data.js` in place,
  never adds a new file" — true for every prior caller, false for `static`, whose entire purpose is
  to create a new, previously-untracked board directory on first publish. This directly
  contradicts this story's own Intent/Approach: "the existing `steward deploy dashboard` verb then
  commits/pushes that unchanged... no new git plumbing... needed" — a promise that does not hold
  for the primary use case (a board's first publish) without this fix. Root cause traced to Code
  Map/Tasks (an existing, shared helper this story's own write path now depends on was never
  updated to see what this story newly creates), not to the Approach text itself: the fix restores
  the EXISTING promise (the existing verb still does the committing/pushing, unchanged in shape;
  only its underlying diff-detection gains untracked-file awareness) rather than contradicting it.
  Confirmed low blast radius before selecting this route: `dashboard_diff()` has exactly one
  production call site (`_run_dashboard`) and one direct test file
  (`test_deploy_reconcile.py`), whose only assertions are `diff_text.strip() == ""` / `!= ""`
  (truthy/falsy), never exact diff-text shape — a backward-compatible extension (existing
  tracked-file diff text combined with a non-empty signal when untracked files exist under
  `docs/dashboard/`) changes nothing for any existing caller's observed behavior. Amended below.
  Folded into the same amendment (found this pass, not independently triggering a second
  loopback):
  - `[medium]` `[patch, folded]` `_is_board_output_dir_safe_to_write` (added last pass) follows
    symlinks — `exists()`/`is_dir()`/`iterdir()` all transparently dereference one. Verified live:
    a symlink at `docs/dashboard/evil` pointing outside the repo, with an empty target, reports
    "safe," and the subsequent write follows it, landing `index.html` outside `docs/dashboard/`
    entirely — bypassing the collision guard this exact function exists to provide. Trivial,
    unambiguous fix: check `is_symlink()` first and refuse before any of the existing logic runs.
  - `[low]` `[patch, folded]` The write-failure cleanup path only `rmdir()`s the leaf `output_dir`
    it freshly created, never any PARENT directories `mkdir(parents=True)` also freshly created
    (e.g. `docs/` and `docs/dashboard/` themselves, if neither existed yet) — the "leaves no
    residual empty directory" claim doesn't fully hold in that case. Inconsequential in THIS repo
    (`docs/dashboard/` always already exists here) but cheap to close: track which ancestor
    directories were freshly created and best-effort `rmdir()` each, innermost first.
  - `[low]` `[patch, folded]` A prior run killed between `write_text` and `rename` leaves a lone
    `*.tmp` file, which `_is_board_output_dir_safe_to_write` then treats as "unsafe" (not a lone
    `index.html`), permanently refusing that board until a human manually deletes the stray file.
    Extend the safety check to also treat "exactly one entry, a file named `index.html.tmp`" as
    safe (this verb's own leftover, not foreign content) so a killed prior run self-heals on retry.
  - `[low]` `[reject]` Whitespace-only `--access-column` treated as "not declared" — deliberate,
    already tested (`test_static_access_column_whitespace_only_does_not_refuse`, pass-1
    amendment), and reconsidered here rather than silently overridden: the alternative
    (presence-of-flag-at-all, regardless of content, means "declared") is a genuinely defensible
    competing design, not a clear-cut single reading, and the fix would require rewording the
    Boundaries clause itself ("(stripped) is non-empty"), which is inside `<intent-contract>` — not
    something this pass silently changes. Left as-is; noted rather than dropped, in case a future
    pass wants to revisit it deliberately.
  - `[low]` `[reject]` Two independent reviewers separately flagged: check-then-write TOCTOU
    (nothing re-verifies directory shape between the safety check and the write), the shared
    non-unique `.tmp` filename under concurrent same-board runs, and `--panel LABEL=PATH` silently
    truncating a label containing its own `=` via `partition("=")`. All three are either
    inherited, already-accepted patterns elsewhere in this same file (`_run_perimeter` has the
    identical unlocked check-then-write shape and the identical fixed `.tmp` name), or a narrow,
    self-inflicted, immediately-visible-in-output misuse (a label with `=` in it) — none is a
    regression this story introduces beyond what the rest of the file already accepts.
  - `[low]` `[reject]` No size guard on `--panel` file reads (loads the whole file before any size
    check) — same disposition as pass 1's identical `--panel PATH` finding: the caller supplies
    their own local path under their own filesystem access; this is not a remote/adversarial input.
  - `[low]` `[reject]` Two independent, differently-worded validation paths for an empty/padded
    panel label (the CLI-level manual check vs. `StaticPanel.__post_init__`) are both correct,
    just under-tested for the padded-via-CLI case; a mislabeled parametrized test case (`""` for
    `--board`) actually re-exercises the "missing flag" branch, not the "invalid slug" branch it's
    filed under. Both are test-precision nitpicks with no behavioral consequence — noted for the
    re-derivation's test file to tidy up opportunistically, not a correctness finding.

### 2026-08-13 — Review pass 3
- intent_gap: 0
- bad_spec: 1: (high 1, medium 0, low 0)
- patch: 0
- defer: 1: (low 1)
- reject: 0
- addressed_findings:
  - none

- `[high]` `[bad_spec]` **Triggering finding.** Independently confirmed by both reviewers, then
  verified live by direct reproduction: `_is_board_output_dir_safe_to_write`'s pass-2 fix checked
  `output_dir.is_symlink()` but not whether the ONE lone entry it then trusts (`index.html` or
  `index.html.tmp`) is itself a symlink — `entry.is_file()` follows symlinks transparently. A
  directory containing a single entry named `index.html.tmp` that is actually a symlink to an
  arbitrary file (e.g. outside `docs/dashboard/` entirely) reports "safe to self-heal," and the
  subsequent `tmp_path.write_text(...)` follows the symlink, silently overwriting the link's
  TARGET file while leaving the symlink itself untouched — reproduced directly: a symlinked
  `index.html.tmp` pointing at a scratch file containing `SECRET-TARGET-CONTENT` was silently
  overwritten with the rendered page's content. Same bug class as the pass-2 `output_dir`-level
  symlink fix, recurring one level deeper — the directory-shape check's OWN entries were never
  symlink-checked, only the directory itself. The spec's Tasks text for this check ("or a file
  named `index.html.tmp`") stated the allowance with no symlink caveat, which is the root cause
  and lives in Tasks (outside `<intent-contract>`) — resolved the same way as pass 2's `output_dir`
  fix: check `is_symlink()` on the trusted entry/entries too, before trusting `is_file()`. Amended
  below. Folded into the same amendment (found this pass, not independently triggering a fourth
  loopback): the self-heal-after-a-killed-run logic only covered a killed FIRST publish (directory
  containing only a stray `.tmp`), not a killed REPUBLISH (which leaves TWO entries — the prior
  `index.html` plus the new `.tmp` — currently treated as foreign/unsafe, permanently blocking
  exactly the more common real-world case); extended to also treat exactly `{index.html,
  index.html.tmp}` (both individually symlink-checked) as safe. Also folded in:
  `_is_board_output_dir_safe_to_write`'s filesystem probes (`.exists()`/`.is_dir()`/`.iterdir()`)
  can raise `PermissionError` (an `OSError`) uncaught, contradicting `_run_static`'s own "never an
  uncaught exception" guarantee — wrapped at the call site.
- `[low]` `[defer]` `dashboard_diff()` cannot see a file that is staged (`git add` succeeded) but
  left uncommitted after a subsequent `git commit` failure — neither `git diff` (matches once
  staged) nor this story's added `git ls-files --others` (excludes anything already staged) sees
  that intermediate state. Genuinely pre-existing (Story 2.2's original `git diff`-only design
  already had this exact gap for tracked-file updates, predating this story entirely); this
  story's untracked-file addition merely inherits it for newly-created files reaching the same
  state. Recorded as `DW-FU-9-7` in the deferred-work ledger (station `pyforge-steward` resolved
  and cross-checked against the Tier-3 path; no existing `DW-FU-9-7` token collided).
- `[low]` `[reject]` AD-10 enforcement is entirely caller-asserted (`--access-column` is a plain
  flag, never independently verified against a board's real `AccessDeclaration`) — already an
  explicit, documented architectural tradeoff (this spec's own Design Notes, mirroring Story 9.5's
  `DeploymentTopology` precedent), forced by the import-boundary invariant this module may never
  cross; not a new finding, not fixable within this story's scope.
- `[low]` `[reject]` `dashboard_diff()`'s widened untracked-file detection now lets a stray,
  unrelated untracked file under `docs/dashboard/` alone (with no other tracked change) trigger an
  automatic commit+push that sweeps it in, where before it silently sat un-pushed forever —
  `commit_and_push_dashboard`'s own `git add -- docs/dashboard` already had this same reach
  (staging tracked and untracked content alike) before this story; only the GATING signal changed.
  Accepted as the necessary, narrower cost of fixing the far more severe invisible-first-publish
  bug this same mechanism exists to close.
- `[low]` `[reject]` TOCTOU window between the safety check and the write (nothing re-verifies
  directory shape immediately before writing) — same disposition as pass 2's identical finding:
  matches this file's established, file-wide risk-acceptance level (no locking anywhere in
  `deploy.py`, including `_run_perimeter`'s identical unlocked check-then-write shape).
- `[low]` `[reject]` `--exclude-standard` on the new `git ls-files` call means a FUTURE, unrelated
  `.gitignore` rule touching `docs/dashboard/` could someday re-open the untracked-file gap this
  amendment closes — speculative, defended by ordinary code review of whatever future change would
  introduce such a rule, not an actionable defect today.
- `[low]` `[reject]` "`--board` is required" / non-string `board`/`access_column` via a hand-built
  `Namespace` raising uncaught instead of refusing — both are exact restatements of findings
  already rejected in pass 1 with the same reasoning (unreachable via the real CLI; matches
  `_run_perimeter`'s identical established trust level for its own `ns.*` fields).

### 2026-08-13 — Review pass 4
- intent_gap: 0
- bad_spec: 1: (high 1, medium 0, low 0)
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

- `[high]` `[bad_spec]` **Triggering finding.** Independently confirmed by both reviewers, then
  reproduced live: `_is_board_output_dir_safe_to_write`'s pass-3 fix checks `entry.is_symlink()`
  before trusting `entry.is_file()`, but a HARD LINK (`os.link`) satisfies both `is_symlink() ==
  False` and `is_file() == True` while sharing an inode with an arbitrary outside file — so a
  hard-linked `index.html.tmp` passes the check, and `_run_static`'s `tmp_path.write_text(...)`
  (open-with-truncate, not unlink-then-create) silently overwrites the SHARED inode. Reproduced:
  a hard link at `docs/dashboard/demo/index.html.tmp` pointing at a file containing
  `SECRET-HARDLINK-TARGET` was silently corrupted to the rendered page's content, and — worse than
  every prior recurrence of this bug class — `DeployDuty().run()` returned `ok=True`
  ("succeeded"), not a refusal; nothing this verb reports would tell an operator anything went
  wrong. Fourth recurrence of the identical "a filesystem-identity trick bypasses the trust check"
  pattern (pass 2: symlinked directory; pass 3: symlinked entry; this pass: hard-linked entry).
  Fix: check `entry.stat().st_nlink != 1` as an additional disqualifying condition alongside
  `is_symlink()` for every trusted entry — a freshly-created regular file this verb itself wrote
  has exactly one link (itself); anything else signals it is shared with, or was substituted from,
  outside content. Amended below. Folded into the same amendment (found this pass; to reduce the
  chance of a fifth recurrence of this same class rather than fix one variant at a time, this
  amendment closes every filesystem-identity gap identified so far in one pass): `output_dir`
  itself is additionally checked for `.stat().st_nlink` implications is not applicable (directories
  cannot be hard-linked on any filesystem this project targets, so no analogous directory-level
  hardlink check exists to add); the two FIXED ancestor paths this verb's output always resolves
  through, `docs` and `docs/dashboard` (`_DASHBOARD_RELATIVE_PATH`), are now also checked for
  `is_symlink()` before any write — Blind Hunter's finding that only the per-board LEAF directory
  was ever checked, never its fixed ancestors (a lower-likelihood gap than the `--board`-controlled
  leaf, since turning a repo-fixed path into a symlink requires checkout-root filesystem access,
  but cheap enough to close in the same pass rather than defer); `_run_static`'s string-processing
  operations (`access_column.strip()`, `_is_valid_board_slug`'s character scan, `label.strip()`)
  now catch `(TypeError, AttributeError)` around a malformed `Namespace` field, mirroring
  `_run_perimeter`'s own documented precedent in this exact file for the identical class of gap
  (that function's docstring records a PRIOR review pass finding and fixing exactly this for its
  own required fields) — this pass reconsiders pass-1's and pass-3's "reject, unreachable via real
  CLI" disposition for the analogous `_run_static` gap now that `_run_perimeter`'s own precedent
  shows this file treats it as worth defending regardless of CLI-reachability. **KEEP for
  re-derivation:** everything KEPT by the pass-1/2/3 entries above still applies unchanged; ADD:
  the three-safe-shape name check and the per-entry `is_symlink()` check both worked and are
  unchanged, only gaining the per-entry `st_nlink` check alongside `is_symlink()`; the
  `dashboard_diff()` fix and its test coverage worked and are unchanged.
- `[low]` `[reject]` `dashboard_diff()`'s inability to see a staged-but-uncommitted file is a
  restatement of the finding already recorded as `DW-FU-9-7` in pass 3's deferred-work entry — not
  re-deferred, not re-actioned, same disposition.
- `[low]` `[reject]` `dashboard_diff()` concatenates its two subprocess outputs with no guaranteed
  separator, which could in principle run two lines together in `--dry-run`'s printed preview text
  if `git diff`'s output ever lacked a trailing newline — cosmetic, human-readable-preview-only,
  no functional or test impact; not bundled into an already-large amendment for a text-formatting
  nicety.
- `[low]` `[reject]` Check-then-act TOCTOU between the safety check and the write (including the
  `created_dirs` ancestor snapshot going stale under a concurrent run) — same disposition as pass
  2/3's identical findings: matches this file's established, file-wide risk-acceptance level (no
  locking anywhere in `deploy.py`).
- `[low]` `[reject]` `--panel` files are read from disk before the board's safety check runs, so a
  request ultimately refused for foreign content still pays the panel-read I/O cost first — a
  pure, no-side-effect efficiency ordering nitpick, not a correctness or security concern; reject
  rather than risk changing refusal-precedence behavior between two already-passing validation
  paths during an already-large amendment.
- `[low]` `[reject]` `--panel PATH` resolves relative to the process's current working directory,
  not `repo_root()` — this is standard, expected CLI-argument path semantics (matches how
  `perimeter`'s `--tls-cert`/`--tls-key`/`--output-dir` already behave), not a defect.

### 2026-08-13 — Review pass 5
- intent_gap: 0
- bad_spec: 1: (high 1, medium 0, low 0)
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

- `[high]` `[bad_spec]` **Triggering finding.** Independently confirmed by both reviewers via
  direct empirical testing: `_is_board_output_dir_safe_to_write`'s per-entry check verifies
  `is_symlink()` and `st_nlink == 1` but never independently verifies `entry.is_file()` itself —
  so a FIFO (`os.mkfifo`) or a bound Unix domain socket at a trusted entry name (neither a
  symlink nor multiply-linked) passes as "safe" exactly like a genuine regular file this verb
  wrote. Reproduced: `is_symlink()` is `False`, `st_nlink` is `1` for a real FIFO at
  `index.html.tmp`. Fifth recurrence of the SAME "a filesystem-identity trick bypasses the trust
  check" pattern across five passes (directory symlink → entry symlink → entry hard link → entry
  special-file-type). Root cause diagnosed structurally, not just this one instance: every prior
  amendment added another NEGATIVE exclusion (not a symlink, not multiply-linked) rather than a
  POSITIVE assertion that the entry genuinely IS a plain regular file — an open-ended list of
  exclusions can always be missing the next variant nobody has thought of yet, while a positive
  assertion (`entry.is_file()`, which by definition excludes every non-regular-file type: FIFOs,
  sockets, block/char devices, directories) closes the whole class at once. Fixed by adding
  `entry.is_file()` as a required POSITIVE condition alongside the existing negative exclusions
  (`is_symlink()` still needed separately, since `is_file()` follows symlinks and would report
  `True` for a symlink pointing at a real regular file). Both reviewers independently assessed
  the remaining threat surface (bind mounts, device nodes, ACLs, extended attributes, Unicode/
  case-normalization tricks, `..`-relative tricks) as either already excluded by existing checks
  (character-allowlisted `--board` forbids `.` entirely; exact-string `frozenset` name matching
  already fails closed on any non-identical name) or requiring a privilege level (root, mount
  access) at which an attacker would not need this check to cause harm — both gave an explicit
  "sufficiently hardened for this threat model" assessment once this fix lands, the first such
  assessment across five passes. Amended below. Folded into the same amendment (found this pass,
  chosen deliberately to close as much of the remaining surface as possible in this final
  available loopback rather than risk a sixth pass finding another variant): on the branch where
  `output_dir` does not yet exist, `mkdir()` is now called WITHOUT `exist_ok=True` (only the
  already-exists branch keeps it) — a symlink raced into that exact path in the narrow window
  between the safety check and the write now makes `mkdir()` raise `FileExistsError` (an already-
  caught `OSError`) instead of silently succeeding through it, closing the highest-value, lowest-
  cost part of the check-then-write TOCTOU window for free, without taking on full lock-based
  concurrency-safety (which remains accepted, file-wide, matching `_run_perimeter`'s identical
  posture — see below); a test proving a write failure after `mkdir()` succeeds cleans up every
  freshly-created ancestor directory was restored (present in an earlier implementation attempt,
  absent from this one — a coverage regression between re-derivations, not a behavior change).
  **KEEP for re-derivation:** everything KEPT by the pass-1/2/3/4 entries above still applies
  unchanged; ADD: the per-entry `is_symlink()`/`st_nlink` checks and the three-safe-shape name
  check all worked and are unchanged, only gaining the `is_file()` positive check per entry and
  the conditional `exist_ok` on the fresh-creation `mkdir` branch; the ancestor-path symlink
  checks, the `OSError` wrap, the `(TypeError, AttributeError)` `_run_static` wrap, and the
  `dashboard_diff()` fix from pass 4 all worked and are unchanged.
- `[low]` `[reject]` `dashboard_diff()`'s inability to see a staged-but-uncommitted file was
  re-raised this pass — exact restatement of the finding already recorded as `DW-FU-9-7` in pass
  3's deferred-work entry. Not re-deferred (would duplicate an existing entry), not re-actioned.
- `[low]` `[reject]` Full check-then-write TOCTOU closure (beyond the free `exist_ok`
  narrowing folded in above) — matches this file's established, consistently-applied, file-wide
  risk-acceptance level across passes 2/3/4/5 alike (no locking anywhere in `deploy.py`, including
  `_run_perimeter`'s identical unlocked check-then-write shape); fixing it only for this one verb
  while every sibling verb keeps the identical shape would be an inconsistency, not a correctness
  improvement.
- `[low]` `[reject]` `_is_valid_board_slug` accepting a non-string iterable of single valid
  characters (e.g. a list) without raising, deferring the eventual crash further downstream —
  requires a hand-built `Namespace` with a deliberately unusual non-string type, unreachable via
  the real CLI (argparse always yields `str`), and goes meaningfully beyond what
  `_run_perimeter`'s own precedent (which pass 4 already mirrored) actually defends against for
  its own required fields.
- `[low]` `[reject]` No CLI-level (`main([...])`) test for a missing `--board` triggering
  argparse's own `required=True` exit — would test Python's stdlib `argparse` behavior, not this
  story's logic; the duty-level refusal path is already tested directly.
- `[low]` `[reject]` `StaticPanel.html` has no non-empty requirement, asymmetric with `label`'s
  strict validation — already explicitly considered and documented as deliberate in the very
  first implementation attempt's test suite (`test_static_panel_allows_empty_html`'s own
  docstring), not a new finding.
- `[low]` `[reject]` `dashboard_diff()`'s docstring claims propagate-on-either-git-call-failing
  is untested for the new `git ls-files` call specifically, and the module's "never imports
  plotly" claim has no enforcing test unlike its neighboring "never imports re" claim — both are
  documentation/test-rigor nitpicks with zero functional or security consequence.

### 2026-08-13 — Review pass 6 (final)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 6: (low 6)
- addressed_findings:
  - none

Both reviewers independently gave an explicit, calibrated "sufficiently hardened for a
single-operator internal CLI's realistic threat model; no genuine must-fix defect" verdict — the
first such unanimous close-the-cycle verdict across six passes. Every finding this pass is either
a duplicate of an already-accepted disposition from an earlier pass, or a newly-named residual
both reviewers themselves assessed as acceptable rather than must-fix:
- `[low]` `[reject]` `dashboard_diff()`'s widened auto-commit scope (any untracked file under
  `docs/dashboard/`, not only a board this verb published) — duplicate of the finding already
  accepted in pass 3 (`commit_and_push_dashboard`'s `git add` pathspec already had this reach).
- `[low]` `[reject]` The "directory already existed" branch keeps a narrower TOCTOU window than
  the one pass 5 closed for free — duplicate of the residual risk pass 5's own Design Notes
  already name and accept as consistent with `_run_perimeter`'s identical unlocked posture.
- `[low]` `[reject]` No end-to-end (`_run_static`, not just the standalone safety-check unit
  test) coverage of the "output_dir already exists, empty" shape — a test-coverage nitpick, not a
  behavior gap (the code path is an unconditional `mkdir(exist_ok=True)` no-op plus write/rename).
- `[low]` `[reject]` A hand-built `Namespace` with `panel` set to a truthy non-list string
  iterates it character-by-character, producing a confusing message instead of a clean refusal —
  unreachable via the real CLI (`action="append"` always yields a list or `None`), same
  unreachable-via-real-CLI class as every hand-built-`Namespace` finding rejected in passes 1–5.
- `[low]` `[reject]` A caller/callee TOCTOU gap distinct from pass 5's fix: `_run_static`
  re-derives `output_dir_existed` via a second `.exists()` call rather than reusing the safety
  check's verdict, so a symlink raced in between the two calls could still route into the
  `exist_ok=True` branch. Real and more precisely located than pass 5's already-accepted residual,
  but the reviewer's own assessment is that exploiting it requires an attacker already
  co-resident on the operator's machine with race-timing access to the exact same path — at which
  point this narrow gap is not the interesting attack surface; accepted on the same basis as the
  broader TOCTOU posture this file has consistently applied since pass 2.
- `[low]` `[reject]` `--panel PATH` is read with no `is_file()` guard, so a FIFO with no writer
  hangs the read — self-inflicted by the OPERATOR's own `--panel` argument (not attacker-
  controlled input in this tool's threat model, unlike the OUTPUT-side entries this story's five
  passes hardened), recoverable by the operator themselves (Ctrl-C), and explicitly assessed by
  the reviewer as a robustness rough edge, not a correctness or data-integrity defect.

### 2026-08-13 — Review pass 7 (follow-up review of the `done` spec)
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 1, medium 1, low 1)
- defer: 1: (medium 1)
- reject: 12: (high 0, medium 4, low 8)
- addressed_findings:
  - `[high]` `[patch]` **A board slug matching any `.gitignore` rule was written, reported
    `ok=True`, and could never publish.** Independently found by both reviewers and reproduced
    end-to-end: `--board` is constrained only to `^[A-Za-z0-9_-]+$`, which admits `build`, `dist`,
    `out`, `lib`, `env`, `venv`, `logs`, `target` and `node_modules` — every one matched by a bare
    directory rule already present in this repo's `.gitignore`, which applies at ANY depth, so
    `docs/dashboard/build/index.html` is ignored today. Verified: `--board build` returned
    `ok=True` and wrote the file, while `dashboard_diff()` returned `''`, so `steward deploy
    dashboard` reports "nothing to deploy" forever — the exact silent-non-publication failure mode
    review pass 2 closed for untracked files, reopened through the `--exclude-standard` flag that
    fix introduced. Pass 3 saw this shape and rejected it as a speculative FUTURE `.gitignore`
    rule; that premise was false — the rules already exist — so the rejection was re-verified
    rather than inherited. Fixed by a new `_is_path_gitignored()` helper called in `_run_static`
    before any write: refuses naming the rule, writes nothing. A non-zero `git check-ignore` exit
    (1 = not ignored, 128 = `cwd` is not a git worktree, as in this verb's own tests) proceeds, so
    the check never makes a git worktree a precondition for writing. Classified `patch`, not
    `bad_spec`: it is a purely additive guard at one point whose correct behavior ("refuse, name
    the reason, write nothing") is already fully determined by this verb's established convention —
    re-deriving 1093 lines of six-pass-hardened code to add one guard would carry strictly more
    regression risk than it removes.
  - `[medium]` `[patch]` **A non-UTF-8 `--panel` LABEL crashed uncaught and left a stray temp
    file.** Found by Edge Case Hunter, reproduced: argv is decoded with `surrogateescape`, so a
    non-UTF-8 byte in a label survives into the rendered page as a lone surrogate and fails at
    encode time in `tmp_path.write_text(...)`. `UnicodeEncodeError` is a `ValueError`, not an
    `OSError`, so it escaped `DeployDuty.run` as `EXIT_INTERNAL` and skipped the cleanup block,
    leaving `index.html.tmp` behind — breaking this verb's own "refuse, never crash" guarantee.
    This is the exact mirror image of the `UnicodeDecodeError` case the spec already required on
    the `--panel` READ side; only the encode direction was never named. Fixed by adding
    `UnicodeEncodeError` to the existing write-path `except`, reusing the same refusal and the same
    cleanup. Reachable through the real CLI, so distinct from the hand-built-`Namespace` findings
    rejected in passes 1/3/4/5.
  - `[low]` `[patch]` **The docstring's own exemplar input produces a malformed page.** Both
    reviewers independently noted that `deploy.py` names `plotly.graph_objects.Figure.to_html()` as
    the model `--panel` input, but that call defaults to `full_html=True` and returns a COMPLETE
    document, which embedding verbatim nests `<html>`/`<head>`/`<body>` inside the assembled page
    (and `include_plotlyjs=True` inlines a full plotly.js copy per panel). Not fixable by
    validating the fragment — embedding byte-for-byte unparsed is mandated by Boundaries — so
    fixed where the defect actually is: both docstrings now say
    `to_html(full_html=False)` and spell out why, plus the multi-panel `include_plotlyjs` guidance.

Also this pass: one genuinely pre-existing, not-this-story's-problem finding (`deploy dashboard`
runs the sprint-ledger guard and a full `dashboard-gen` rebuild unconditionally before ever
computing a diff, so a static-only adopter inherits both preconditions) was recorded as
`DW-FU-9-7-2` in the deferred-work ledger rather than fixed here — it would change the pre-existing
`dashboard` verb's Story 2.2 / 5.2 contract. Ledger appended to only; no existing entry modified.

Rejected this pass (restated only if a future pass finds the disposition wrong):
- `[medium]` `[reject]` CAP-8's "same board definition, both modes" is not mechanized — `--board`
  is a bare slug and panels are operator-supplied files. Bound by this story's own
  `<intent-contract>` Never clause ("Never build or export a Plotly figure itself... this story
  ships the mechanism") and its Design Notes, which name `fig.to_html()` as the literal mechanism
  CAP-8's success criterion describes. A deliberate, documented scope boundary, not a defect.
- `[medium]` `[reject]` AD-10 is caller-asserted — `--access-column` is never verified against a
  board's real `AccessDeclaration`. Exact restatement of pass 3's rejected finding. One reviewer
  added a new rebuttal (that `declarations.py` imports only `re`/`dataclasses`/`datetime`, so the
  import-boundary rationale is weak) — re-verified rather than inherited, but the Boundaries clause
  inside `<intent-contract>` bans importing `pyforge.steward.dashboard` at all, independent of what
  that module itself imports. Changing it is an intent-contract change, out of scope here.
- `[medium]` `[reject]` Concurrent same-board runs share one fixed `.tmp` name; a loser can publish
  while a winner reports `ok=True`. Reproduced by a reviewer, but this is the identical inherited
  shape `_run_perimeter` already uses, rejected in passes 1/2/3/4/5/6 and explicitly accepted
  file-wide in this spec's own Design Notes ("Why the check-then-write race is only partially
  closed"). Unchanged disposition.
- `[medium]` `[reject]` A hand-authored lone `docs/dashboard/<board>/index.html` is trusted and
  silently overwritten, since a lone `index.html` is a trusted shape with no provenance marker.
  Real, but the AC inside `<intent-contract>` explicitly specifies that shape as safe-to-overwrite
  (idempotent re-publish), and the Design Notes record why a marker file was considered and
  rejected. Out of bounds for a non-loopback pass.
- `[low]` `[reject]` `dashboard_diff()`'s staged-but-uncommitted blind spot — already recorded as
  `DW-FU-9-7`; not re-deferred, not re-actioned.
- `[low]` `[reject]` The widened untracked-file gate lets an unrelated stray under
  `docs/dashboard/` ride into an auto-commit — duplicate of the disposition already accepted in
  passes 3 and 6 (`commit_and_push_dashboard`'s `git add` pathspec already had that reach).
- `[low]` `[reject]` A `--panel` path pointing at a FIFO blocks the read forever — rejected
  explicitly in pass 6 as operator-self-inflicted input, Ctrl-C-recoverable, and outside the
  output-side threat model these passes hardened. Unchanged.
- `[low]` `[reject]` A hand-built `Namespace` with a non-`str` `board`, or a `panel` set to a
  string rather than a list, crashes instead of refusing — unreachable through the real CLI
  (argparse yields `str | None`, and `action="append"` yields a list or `None`); rejected in
  passes 1/3/4/5/6 on the same basis.
- `[low]` `[reject]` `--access-column "  "` is stripped-then-tested where `AccessDeclaration`
  would reject padded input outright — deliberate, tested, and explicitly reconsidered-then-left
  in pass 2; the Boundaries clause states the "(stripped) is non-empty" semantics directly.
- `[low]` `[reject]` A backup tool that hard-links a published `index.html` permanently locks that
  board out of re-publishing, with a message that misdescribes the state. Reproduced, and a real
  usability cost — but refusing on `st_nlink != 1` is exactly the behavior pass 4 specified and an
  AC inside `<intent-contract>` now requires. An override flag is a new feature, not a fix.
- `[low]` `[reject]` `if output_dir_existed: output_dir.mkdir(parents=True, exist_ok=True)` is a
  no-op branch that reads as if it mirrors the `else` branch's TOCTOU hardening. Cosmetic only;
  not worth churn in a file this heavily hardened.
- `[low]` `[reject]` `dashboard_diff()` concatenates its two git outputs with no separator, so
  `--dry-run`'s preview can run a bare filename against diff context, and its docstring's claim
  that neither caller depends on the text's shape is untrue of that branch. Rejected as cosmetic
  in pass 4; unchanged, and out of the patch scope this pass kept deliberately tight.

### 2026-08-13 — Review pass 8 (follow-up review of the `done` spec)
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 0
- reject: 13: (high 0, medium 4, low 9)
- addressed_findings:
  - `[medium]` `[patch]` **The six new POSIX-only conformance tests carried no platform
    guard, on a workspace that declares and solves `win-64`.** Found by Blind Hunter, verified
    directly: `pixi.toml`'s `[workspace] platforms` is `["linux-64", "win-64", "osx-arm64-min"]`,
    `[feature.pyforge-steward]` declares no narrower `platforms` of its own, and the
    `pyforge-steward` environment is `{ features = ["pyforge-steward"], no-default-feature =
    true }` — so the suite is solved for `win-64`. `test_deploy_static.py` used `os.mkfifo`
    (absent on Windows → `AttributeError`, i.e. test ERROR rather than skip), `os.link`, and
    four `Path.symlink_to` calls (privileged on Windows), with no `sys` import and no `skipif`
    anywhere in the file. The precedent is already established one file over in the same
    conformance tier: `test_keys_plaintext_secret_scan.py:53`/`:116` guard exactly chmod and
    symlink with `@pytest.mark.skipif(sys.platform == "win32", ...)`. Fixed by importing `sys`
    and adding the matching decorator to all six, each naming the specific POSIX primitive.
    Classified `patch`, not `bad_spec`: test-only, mechanical, and the correct shape is fully
    determined by that in-repo precedent.
  - `[low]` `[patch]` **`render_static_index` silently rendered an EMPTY page for a one-shot
    iterable.** Independently found by both reviewers (Edge Case Hunter reproduced it: a
    generator argument returned the same 482-byte panel-free document as `render_static_index([],
    ...)`, with no exception). The function reads `panels` twice — the duplicate-label scan, then
    the section render — so a generator/`map`/consumed `iter()` is exhausted by the first pass.
    The annotation says `Sequence`, so this is a caller-contract violation, but the failure shape
    is wrong-output-reported-as-success on the one function whose entire job is emitting the
    published page. Fixed with a single `panels = tuple(panels)` at the top plus a docstring note
    and a new regression test. Cannot change behavior for any conforming `Sequence` input.
  - `[low]` `[patch]` **The `.gitignore` refusal added in pass 7 was undocumented in both places
    a reader would look.** Both reviewers noted it independently. `_run_static`'s docstring walks
    the reader through the full ordered pipeline (AD-10 → slug → panels → render → safety check →
    atomic write) and never mentioned `_is_path_gitignored`, which pass 7 inserted between the
    safety check and the write; `cli.py`'s `--board` help still advertised `^[A-Za-z0-9_-]+$` as
    the only constraint. In a module where every other branch is narrated, a refusal a reader
    cannot predict from the docs is a real defect of the same kind this file otherwise avoids.
    Both now name the rule and why it exists.

No `bad_spec` or `intent_gap` this pass — the second consecutive pass with neither, and the
third consecutive pass (6, 7, 8) in which no reviewer finding required re-deriving the
implementation. Every substantive finding this pass was a duplicate of a disposition already
settled in passes 1–7, and each rejection premise below was re-verified against the live code
rather than inherited:
- `[low]` `[reject]` `dashboard_diff()` cannot see a STAGED-but-uncommitted new board. Both
  reviewers found it; Blind Hunter reproduced it properly for the first time (a `.git/hooks/
  pre-commit` exiting 1, so `commit_and_push_dashboard`'s `git add` succeeds and its `git commit`
  fails, leaving `A  docs/dashboard/demo/index.html` that neither `git diff` nor `git ls-files
  --others` reports). Already recorded as `DW-FU-9-7` in pass 3 and re-raised in passes 4, 5 and
  7 — not re-deferred (that would duplicate an existing ledger entry), not re-actioned.
- `[medium]` `[reject]` A pre-existing symlink raced into the board path between
  `_is_board_output_dir_safe_to_write` and `_run_static`'s own second `output_dir.exists()` probe
  routes into the `exist_ok=True` branch, so pass 5's "no `exist_ok` on the fresh-creation branch"
  hardening never engages; Edge Case Hunter reproduced it by patching the in-window
  `_is_path_gitignored` call to plant the symlink. This is verbatim the finding pass 6 already
  located precisely and accepted. Re-verified rather than inherited, and one thing genuinely
  changed: pass 7 inserted a `git check-ignore` SUBPROCESS into that window, widening it from a
  few syscalls to a fork/exec. That is a quantitative change to an exploitability the file's
  documented, consistently-applied posture already accepts (no locking anywhere in `deploy.py`;
  `_run_perimeter` has the identical unlocked check-then-write shape; CI runs one job per board).
  Unchanged disposition.
- `[medium]` `[reject]` Concurrent same-board runs share one fixed `.tmp` name — Edge Case Hunter
  reproduced the sharpest form yet with threads (run A returned `ok=True` "wrote index.html" while
  the published file contained run B's panels). Rejected in passes 1/2/3/4/5/6/7 on the identical
  inherited-shape basis, and named explicitly in this spec's own Design Notes.
- `[medium]` `[reject]` A hand-authored lone `docs/dashboard/<board>/index.html` is trusted and
  silently overwritten (Blind Hunter reproduced it). Exact restatement of pass 7's rejection: an
  AC inside `<intent-contract>` specifies that shape as safe-to-overwrite (idempotent re-publish),
  and the Design Notes record why a provenance marker was considered and rejected.
- `[medium]` `[reject]` `--access-column ""` (present but empty) publishes rather than refusing.
  Real and reproduced, and the shell-variable-unset scenario is plausible — but the Boundaries
  clause inside `<intent-contract>` states the semantics literally ("when `ns.access_column`
  (stripped) is non-empty"). Changing it is an intent-contract change, out of bounds for a
  non-loopback pass; same disposition as the whitespace-only variant in passes 2 and 7.
- `[low]` `[reject]` `_is_valid_board_slug` does not `isinstance`-check its argument, so a
  hand-built `Namespace` with `board=["d","e","m","o"]` passes the character scan and crashes
  uncaught downstream. Reproduced, but the rejection premise from passes 1/3/4/5/6/7 — unreachable
  through the real CLI — was re-verified and still holds: argparse yields `str | None` for an
  untyped flag. Same class, same disposition.
- `[low]` `[reject]` `dashboard_diff()`'s widened untracked-file gate now lets a stray
  `index.html.tmp` from a killed publish trigger a commit that sweeps it into the repo; Edge Case
  Hunter reproduced it landing at HEAD. The pass-3/6/7 rejection premise was re-verified directly
  rather than inherited — `commit_and_push_dashboard` runs `git add -- docs/dashboard`, and `git
  add` on a pathspec stages untracked files, so any such stray already rode along on every
  dashboard deploy before this story. Only the GATING signal changed. Premise holds.
- `[low]` `[reject]` A `--panel` path pointing at a FIFO blocks the read forever (reproduced,
  exit 124 under an 8s timeout). Rejected explicitly in passes 6 and 7 as operator-self-inflicted
  input under the same trust boundary as invoking the CLI, Ctrl-C-recoverable, and outside the
  OUTPUT-side threat model these passes hardened. Unchanged.
- `[low]` `[reject]` `_is_path_gitignored` returns the same `False` for "not ignored" (rc 1) and
  "cannot answer" (rc 128), and the `fake_repo` fixture makes the check a silent no-op in most
  tests. The collapse is deliberate and already documented in that helper's own docstring — the
  guard exists to catch a board git will silently drop, never to make a git worktree a
  precondition for writing a file. The coverage observation is real but is a test-rigor note.
- `[low]` `[reject]` The `created_dirs` ancestor-cleanup branch is unreachable in production
  (`repo_root()` only returns a directory where `pyforge.doctor.sources.fleet_scan` is a file, so only
  the leaf board dir can ever be freshly created), and the test proving it monkeypatches
  `repo_root()` to a directory the real one would have raised on. Accurate, but both the behavior
  and that test are explicitly required by this spec's pass-2 and pass-5 amendments; removing
  either would contradict the frozen spec.
- `[low]` `[reject]` `dashboard_diff()`'s docstring claim that neither caller depends on the
  text's exact shape is untrue of the `--dry-run` branch, which interpolates `diff_text` into
  operator-facing output where bare untracked paths now concatenate onto a unified diff with no
  separator. Rejected as cosmetic in passes 4 and 7; unchanged.
- `[low]` `[reject]` No `--force` override or remediation hint for a gitignored board slug, and a
  board written by pre-pass-7 code leaves a stale directory the refusal message never mentions.
  An override flag is a new feature, not a fix.
- `[low]` `[reject]` `--panel PATH` resolves against the process CWD rather than `repo_root()`.
  Exact restatement of pass 4's rejection: standard CLI-argument path semantics, matching how
  `perimeter`'s own `--tls-cert`/`--tls-key`/`--output-dir` already behave.
- `[low]` `[reject]` `render_static_index` accepts an empty `panels` sequence and emits a
  content-free page. `_run_static` guards it, and no adopter path calls the function directly;
  the genuinely harmful sibling of this finding (the one-shot-iterable case) was patched above.

## Design Notes

**Why no `--dry-run` on `static`.** The existing `steward deploy dashboard --dry-run` already
previews the WHOLE `docs/dashboard/` diff — including this verb's staged output — before any
push. Duplicating dry-run here would re-implement a preview step the reconciled-push verb
already owns; the CI pattern is build-then-reconcile (stage static content, then call `steward
deploy dashboard`), exactly as `kedro-viz-publish.yml` already does for its own static export.

**Why panels arrive as pre-rendered HTML strings, not `Figure` objects.** `deploy.py` may not
import `pyforge.steward.dashboard`, `django`, or `channels` (enforced by
`test_no_module_outside_dashboard_imports_dashboard_django_or_channels`), and adding `plotly` as
a new dependency would contradict `pyproject.toml`'s own "only what's actually imported"
packaging discipline. Requiring the adopter to call `fig.to_html()` before invoking this CLI is
also the literal mechanism CAP-8's success criterion names — "without anyone hand-re-deriving
its charts for the static build."

**Why `--access-column` is a plain string flag, not an `AccessDeclaration` object.** Identical
reasoning to Story 9.5's `DeploymentTopology.cache_backend`/`channel_layer_backend`: this module
compares the STRING an adopter would pass, never an imported class, since it cannot import
`dashboard/declarations.py`.

**Why a directory-shape check, not a marker file, decides collision safety.** This verb only
ever writes exactly one file, `index.html`, directly inside `docs/dashboard/<board>/` — nothing
else. That means "does this directory contain only a lone `index.html`?" is already a complete
description of "did this verb (and only this verb) produce everything here", with no need to
invent and persist an ownership marker (an HTML comment tag, a sidecar file, etc.) that a future
reader could misinterpret or a future refactor could forget to check. A marker-based scheme was
considered and rejected: it adds state to reason about for a check that a plain `os.listdir()`
already answers exactly as well, and it would need its own migration story the day this verb's
own output shape ever changes. The directory-shape check reduces to a single boundary case worth
naming explicitly: an *empty* pre-existing directory (e.g. a leftover from a prior failed run
whose write step failed after `mkdir` but whose cleanup this amendment also now closes, see the
`_run_static` task above) is treated as safe-to-write, matching "no prior successful write, no
foreign content" rather than being treated as itself suspicious.

**Why `dashboard_diff()` gets fixed here rather than a new, story-9.7-local diff check.** The
reconciled-push contract ("no new git plumbing needed") only holds if the EXISTING `steward
deploy dashboard` verb can actually see what `static` writes. Inventing a second, parallel
diff-detection path scoped to just this verb would duplicate `dashboard_diff()`'s job and leave
two slightly different notions of "has `docs/dashboard/` changed" in the same file — exactly the
kind of fork this story's own name warns against, just one level down. Fixing the shared function
once, confirmed to have exactly one production call site and tests that only assert
truthy/falsy, is the smaller, more coherent change.

**Why a killed run's stray `.tmp` is treated as this verb's own leftover, not foreign content.**
`index.html.tmp` is a name only this verb's own atomic-write step would ever produce at that
exact path (the tmp suffix is appended to the one filename this verb writes). A directory
containing only that one file (a killed first publish), or that file alongside a prior
`index.html` (a killed republish — pass 3: the original amendment only recognized the former
shape, which a review pass correctly called out as covering the less common of the two real
"a run got killed mid-write" scenarios), unambiguously means "an earlier run of THIS verb started
and didn't finish" — clearing it and proceeding is strictly safer than a permanent,
unrecoverable-without-manual-intervention refusal for a self-inflicted, self-diagnosable state.

**Why every trusted entry gets its own `is_symlink()` check, not just `output_dir`.** Pass 2
closed "a symlink AT the board path" by checking `output_dir.is_symlink()`. Pass 3 found the same
class of gap one level in: the directory-shape check's job is "does this directory contain only
things THIS VERB put there," and `entry.is_file()` alone cannot answer that — a symlink named
exactly `index.html.tmp` also satisfies `is_file()` (it follows the link to whatever real file is
at the far end) while being something this verb never created. The fix generalizes the pass-2
lesson rather than special-casing this one instance: ANY entry this check is about to trust must
independently prove it is a real file this verb wrote, not merely a same-named path.

**Why `st_nlink != 1`, not just `is_symlink()`, decides whether a trusted entry is real.** A
symlink and a hard link are two different POSIX mechanisms for making one path resolve to
another file's content, and `Path.is_symlink()` only detects the first. A hard link IS, by every
filesystem-level test this check previously performed, an ordinary regular file — `is_symlink()`
is `False`, `is_file()` is `True` — because a hard link has no separate identity from the inode
it shares; it is not "a pointer to a file," it IS the file, under a second name. The only
observable difference is the link count (`st_nlink`): a file this verb itself creates via
`write_text` has exactly one name pointing at its inode (`st_nlink == 1`); a hard link has two or
more (the pre-planted name plus at least one elsewhere on the same filesystem). Checking
`st_nlink != 1` alongside `is_symlink()` closes the gap without assuming anything about WHERE the
other name lives — it can't, since a hard link (unlike a symlink) carries no path to inspect.

**Why `is_file()` became a required POSITIVE condition instead of one more negative exclusion.**
Three passes in a row (2, 3, 4) each found the check trusted an entry that merely LOOKED like a
plain file by name, then added one more thing to exclude (a symlinked directory, a symlinked
entry, a hard-linked entry). Pass 5 found the next gap in that same shape — a FIFO or Unix socket
at a trusted name, neither a symlink nor multiply-linked — and recognized the pattern itself was
the problem: a list of exclusions can only ever cover the variants someone has already thought
of. `entry.is_file()` is a POSITIVE claim ("this is, specifically, a regular file") that by
construction excludes every OTHER POSIX file type — FIFOs, sockets, block/character devices,
directories — in one check, because `is_file()` is defined as true only for `S_ISREG`. Requiring
it, alongside the still-necessary `is_symlink()`/`st_nlink` checks (since `is_file()` alone
follows a symlink to a genuine regular file, and doesn't distinguish a hard link from an
original), turns the trust boundary from "not one of the tricks we've found so far" into "must
affirmatively be exactly the kind of thing this verb itself would have written" — the same shape
of fix the two structural notes above already reached for symlinks and link counts, applied one
level higher, to the file's TYPE rather than its identity or naming.

**Why the check-then-write race is only partially closed, not eliminated.** `mkdir()` without
`exist_ok=True` on the fresh-creation branch closes the highest-value slice of the window (a
symlink raced in between the check and the write now raises instead of being silently followed)
for the cost of one keyword argument. Going further — re-verifying the directory's shape
immediately before the write, or taking a lock — would be new machinery this file doesn't use
anywhere else: `_run_perimeter`'s own check-then-write sequence has the identical unlocked shape,
and `_run_dashboard`'s build-diff-commit sequence isn't atomic against a concurrent invocation
either. Closing this one verb's TOCTOU window fully while every sibling verb keeps the same
shape would be inconsistent with, not more correct than, this file's existing, deliberate
posture — CI's own concurrency-group pattern (one job per board, `cancel-in-progress: false`,
per `kedro-viz-publish.yml`'s precedent) is what actually keeps two invocations from racing in
practice, not anything inside `deploy.py` itself.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test -k test_deploy_static -v` -- expected: all
  new tests pass.
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: full suite green, zero
  regressions.
- `ruff check src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py
  src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  src/shared/packages/pyforge-steward/tests/conformance/test_deploy_static.py` -- expected: clean.

## Auto Run Result

Status: `done` (follow-up review pass 8 of a `done` spec; no loopback).

**Implemented change (cumulative, unchanged in shape by this pass).** `steward deploy static`
— a fourth `deploy` verb that refuses outright on a declared `--access-column` (AD-10), then
assembles caller-supplied pre-rendered HTML panel fragments verbatim into one self-contained
`docs/dashboard/<board>/index.html` (CAP-8), written atomically behind a filesystem-identity
safety check. The pre-existing `dashboard_diff()` was extended to see untracked files so a
board's first-ever publish is visible to the existing reconciled-push verb.

**Files changed this pass (3):**
- `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_static.py` — `import sys`;
  `skipif(sys.platform == "win32")` on the six POSIX-only tests (`os.mkfifo`, `os.link`, four
  `symlink_to`); one new regression test for the one-shot-iterable fix.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` — `render_static_index`
  materializes `panels` once (`tuple(panels)`) with an explanatory docstring note;
  `_run_static`'s docstring now narrates the `_is_path_gitignored` refusal in its correct
  pipeline position.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `--board` help now states
  the `.gitignore` refusal alongside the slug pattern.

**Review findings breakdown.** 3 patches applied (1 medium, 2 low); 0 deferred; 13 rejected
(4 medium, 9 low). No `bad_spec`, no `intent_gap`. Every rejected finding was either an exact
restatement of a disposition settled in passes 1–7 or already recorded as `DW-FU-9-7`; each
rejection premise was re-verified against the live code rather than inherited, and one
(`git add`'s untracked reach) was confirmed directly. The deferred-work ledger was not touched
this pass — no new entry was warranted, and no existing entry was read, modified, or re-opened.

**Verification performed.**
- `pixi run -e pyforge-steward pyforge-steward-test` → **676 passed in 5.65s**, zero failures,
  zero regressions (675 before this pass; +1 is the new one-shot-iterable test).
- `ruff check` on the three touched files → **5 findings, byte-identical before and after this
  pass** (confirmed by stashing the patches and re-running; only line numbers shift). All 5 sit
  in pre-existing code from Stories 2.2/2.4/9.5 (`UP035` `Sequence` imports ×2, `PLW1510`
  missing `check=` ×2, one stale `RUF100` `noqa`), none in this story's code, and none introduced
  by these patches. Noted rather than fixed: there is no `[tool.ruff]` table in either
  `pyproject.toml`, no `ruff` pixi task, and no CI workflow invoking ruff, so this rule selection
  is ambient and ungated — the spec's "expected: clean" line has never held for these files.
- Reviewer claims verified independently before classifying: `win-64` is a declared workspace
  platform that the `pyforge-steward` environment solves for; the `skipif` precedent exists at
  `test_keys_plaintext_secret_scan.py:53`/`:116`.

**Residual risks.** Unchanged from pass 7 and all deliberately accepted, each with a Design Note:
the check-then-write TOCTOU window (now marginally wider, since pass 7's `git check-ignore`
subprocess sits inside it) and the shared fixed `.tmp` name under concurrent same-board runs,
both matching `_run_perimeter`'s identical file-wide unlocked posture; AD-10 enforcement being
caller-asserted, forced by the import-boundary invariant; a lone hand-authored `index.html` being
a trusted overwrite target, which an AC inside `<intent-contract>` requires; and
`dashboard_diff()`'s staged-but-uncommitted blind spot, carried as `DW-FU-9-7`.

**Follow-up review recommended: false.** The three patches are narrow and low-consequence — two
are documentation/test-guard only, and the third is a one-line defensive materialization that
cannot change behavior for any input conforming to the function's own `Sequence` annotation. No
production behavior, API, security, or data-integrity surface moved. Passes 6, 7 and 8 have now
each closed without a loopback, and this pass surfaced no new defect class.


