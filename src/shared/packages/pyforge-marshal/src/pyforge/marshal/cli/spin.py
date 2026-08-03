"""``marshal factory spin``/``marshal factory attach`` (Story 3.3, FR-9/
FR-17, AD-3/AD-6/AD-22/AD-25/AD-38) -- Marshal's first real launch verb.

``core/journal.py``'s mint/append mechanism (Story 3.1) and its fold (Story
3.2) shipped with zero real callers -- this module is the first: it mints a
Marshal run id, ``create_dir_exclusive``s the run's directory, and
``append_line``s an ``intent`` entry BEFORE spawning anything, and an
``outcome`` entry after (AD-6's write-before-act), around the one new
``HarnessPort.spin`` primitive -- the ONLY code in the tree permitted to
launch ``bmad-loop run`` (AD-3; enforced by the ``import-linter`` "forbidden"
contract in ``pyproject.toml``, proven by ``tests/meta/test_ad3_ad4_import_linter.py``).
``bmad-loop run``/``resume`` both block the invoking shell for the run's
entire lifetime (confirmed live against the installed 0.9.0 ``cli.py``) --
AD-22 makes detached the default so ``marshal factory spin`` returns
promptly instead of reproducing that foreground-timeout failure class.

**Order of operations (``run_spin``).** Slug shape (``MRS-SPIN-001``, before
any I/O) -> loop home provisioned (``MRS-SPIN-002``) -> [``--foreground``:
``HarnessPort.run_foreground``, relayed directly, see below] -> the
EXISTING ``HarnessPort.story_feed_error`` (``MRS-SPIN-005``, refuse early if
the feed itself is unreadable) -> ``HarnessPort.story_feed_keys`` ->
``core.identity.resolve_feed`` (AD-38: ``total`` is the WHOLE raw
population, independent of any selector -- see that function's own
docstring and this module's Design Notes below) -> refuse the launch (no
spawn, no journal entries at all) if any key is unresolved, surfacing the
EXISTING ``MRS-IDENT-001`` findings (already classified
``Verdict.UNEVALUABLE`` -- no new code needed) -> filter the RESOLVED
``StoryKey``\\s by ``--epic``/exact ``--story``/``--max-count`` into the
echoed preview list (``_filter_preview`` -- deliberately NOT
``bmad_loop.sprintstatus.select_actionable``'s full matching grammar, per
the spec's own Never clause: Marshal's own preview only needs
epic-number/exact-key/count filtering, since the harness re-derives the
REAL selection itself at spawn time from the SAME flags passed straight
through) -> mint the run id (``core.journal.mint_run_id``, AD-25) ->
``create_dir_exclusive`` the run directory -> ``append_line`` an ``intent``
entry (kind ``"run-launch"``, ``fsync=True`` per AD-30) carrying the
selector and the echoed preview -- THIS is "the resolved story list ...
recorded in the journal" -- -> ``HarnessPort.spin`` -> ``append_line`` an
``outcome`` entry (same kind, ``intent_id`` set, ``fsync=False``) carrying
``pid``/``harness_run_id`` as a plain correlation field, never a key/path/
grouping value (AD-25) -> ``ProcessPort.spawn_detached`` the supervisor
sidecar (Story 3.4, AD-9) as the LAST step, whether or not the outcome
append itself succeeded -> print the same resolved list and run id.

Story 3.4 (the supervisor's own process lifecycle, AD-9/AD-20/AD-25) adds
the sidecar spawn: a new, injectable ``process: ProcessPort | None = None``
(default ``PosixProcess()``, matching ``fs``/``harness``'s own DI
convention) whose ``spawn_detached`` launches ``python -m
pyforge.marshal.supervisor <home> <slug> <run_id> <spin_result.pid>
<supervisor_log>`` detached, redirecting its own stdout/stderr to a SEPARATE
log file from the harness's own (``_SUPERVISOR_LOG_FILENAME``, never
``_LOG_FILENAME``). Placed strictly AFTER the outcome-entry append is
attempted (succeeded or not) -- never right after ``harness.spin()``
returns -- because the supervisor's own inert-check reads that SAME
outcome entry back off disk; spawning it any earlier would race the
supervisor against an entry that is not yet journaled. A ``ProcessError``
here (the supervisor could not be launched at all) registers
``MRS-SPIN-007`` (``Verdict.WARN``): the harness launch itself already
succeeded, so losing supervision degrades the run to unsupervised, never
invalidates the launch (matches architecture.md's own "a supervisor crash
degrades to an unsupervised run ... never to a corrupted one").
``data["supervisor_log"]`` joins the envelope/text report unconditionally
(the detached sidecar's only diagnostic channel, needed whether or not the
spawn succeeded); ``data["supervisor_pid"]`` joins it on success.

**``--foreground``.** Calls the synchronous, stdio-inheriting
``HarnessPort.run_foreground`` INSTEAD of the detached ``spin`` path and
relays its result, bypassing the envelope entirely (mirrors
``run_attach``/``cli/main.py``'s ``--version`` precedent for a command that
legitimately steps outside the envelope) -- documented in its own ``--help``
text as unsafe for resumes (forward documentation only; ``marshal factory
resume`` is Story 3.7's own scope, not implemented here). Still passes
through the SAME two shared precondition gates as the detached path (a
malformed slug or an unprovisioned home are real preconditions independent
of foreground-vs-detached), but skips the story-feed/journal machinery
entirely -- there is no minted run id and nothing to journal for a launch
that never called ``spin``, and it needs no Tier-3 backlink because it
writes nothing.

**Relayed exit codes are PROJECTED, never verbatim.** Both no-envelope
paths (``--foreground`` and ``run_attach``) return their child's code
through ``core.verdict.relay_exit_code``: EXACTLY ``0``, ``1`` and
``EXIT_SIGINT`` pass through untouched, anything else -- including a child's
coincidental ``2``/``3``/``4``, which in THIS package's lattice would assert
a usage/scope/gate judgment Marshal never made -- collapses to the ERROR
rung. ``cli/main.py`` admits only ``GUARDED_EXIT_CODES`` from a handler
(AD-7's frozen domain) and clamps the rest to ``EXIT_USAGE``, so returning a
raw child code reported ``5``/``7``/``137``/``143`` as a Marshal USAGE error
-- see ``relay_exit_code``'s own docstring for both review findings.

**``run_attach``.** A SEPARATE, non-destructive command (the AC's own
wording) -- it never mutates run state, never selects among multiple runs
(``bmad-loop attach`` already defaults to the latest; disambiguating by
Marshal's own run id needs a ``core.journal.fold``-based lookup this story
does not add, per its own Never clause -- logged to ``deferred-work.md`` if
review flags it as demanded). Like ``--foreground``, it NEVER builds an
``Envelope``: its own two shared precondition gates print a plain message
and return the SAME verdict tier ``run_spin``'s identical gates would (via
``core.verdict``'s sole-owned ``classify``/``exit_code_for`` projection over
a real, registered ``Finding`` -- never a bare exit-code literal; only
``core/verdict.py`` may embed one, AD-7), and its happy path hands the
terminal to the multiplexer and relays ``bmad-loop attach``'s own exit code
(through the same projection described below) -- which the spec's own I/O
matrix documents as sometimes non-zero ("no runs found").

**Why no ``deploy``-side selection grammar.** ``core.identity`` stays
untouched by this story (not in its Code Map) -- ``_filter_preview`` lives
here, not there, and is deliberately simpler than
``bmad_loop.sprintstatus.select_actionable`` (no slug-fragment matching, no
bare-number-needs-``--epic`` resolution): it is a best-effort PREVIEW, not a
second selection authority, so an unparseable ``--story`` value previews
empty rather than raising or guessing -- the actual launch still passes the
raw flag straight through to ``bmad-loop run``, whose own engine is the
sole authority for which stories a run actually executes. Never
pre-refuses on a zero-count preview (the spec's own Never clause): that
judgment belongs to the harness's own engine at run time.

Registers ``MRS-SPIN-001`` through ``MRS-SPIN-007`` (``core/findings.py``/
``core/verdict.py``) -- see those modules' own docstrings for the full
per-code rationale. ``MRS-SPIN-006`` joined the original five in review,
splitting "launched, but its outcome could not be journaled" (``WARN`` -- a
live process now exists) off ``MRS-SPIN-003``'s "never launched, safe to
retry" (``ERROR``). ``MRS-SPIN-007`` (Story 3.4) is the supervisor-spawn
failure -- the SAME ``WARN`` tier as ``MRS-SPIN-006``, for the same reason:
a live, launched harness process is never re-classified as a failure over a
DIFFERENT paper-trail gap (losing supervision rather than losing the
outcome journal entry).
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadloop import BmadLoopHarness, HarnessError
from ..adapters.process_posix import PosixProcess, ProcessError
from ..core import policy
from ..core.identity import (
    StoryKey,
    normalize,
    render_feed_key,
    resolve_feed,
)
from ..core.journal import (
    JournalEntry,
    JournalEntryId,
    Phase,
    build_entry,
    mint_run_id,
    prepare_for_write,
)
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for, relay_exit_code
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from ..ports.process import ProcessPort
from .config import _suppress_downstream_pipe_close
from .init import _home_path

# The run journal's own filename, under the run directory (architecture.md's
# own "line-delimited JSON files under the run directory is the seed
# decision" -- Persistence backend for journals). ``_LOG_FILENAME`` is
# ``spin``'s own redirected-log target -- a SEPARATE file from the journal,
# never the same one: the journal is structured JSONL Marshal itself writes,
# the log is bmad-loop's own raw stdout/stderr text, polled once for its
# "starting" line and otherwise left for an operator to read directly.
_JOURNAL_FILENAME = "journal.jsonl"
_LOG_FILENAME = "harness.log"
# The supervisor sidecar's OWN redirected stdout/stderr -- a SEPARATE file
# from the harness's own _LOG_FILENAME, since they are two distinct detached
# processes (Story 3.4, AD-9).
_SUPERVISOR_LOG_FILENAME = "supervisor.log"

# The "kind" every entry this module writes carries -- one launch attempt,
# one intent/outcome pair, always this same kind (no other kind exists yet
# in this package's own vocabulary; a future story's supervisor/gate/etc.
# kinds are that story's own concern).
_LAUNCH_KIND = "run-launch"


def _non_negative_int(text: str) -> int:
    """The ``argparse`` ``type=`` for ``--epic``/``--max-count`` (review
    finding, Blind Hunter + Edge Case Hunter independently): neither flag
    validated its value before this fix, so a negative ``--epic`` passed
    through unchanged to ``bmad-loop run --epic <n>`` (a harmless no-match
    there, but confusing), while a negative ``--max-count`` reinterpreted
    ``_filter_preview``'s ``keys[:max_count]`` via ordinary Python slice
    semantics -- silently dropping items from the END of the preview instead
    of erroring -- and forwarded the same negative value to ``bmad-loop run
    --max-stories``. Raises ``argparse.ArgumentTypeError`` (argparse's own
    convention for a rejected value, rendered as a clean usage error) for
    anything that doesn't parse as a base-10 int or parses negative."""
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: {text!r}") from None
    if value < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {value}")
    return value


def _writer_id() -> str:
    """A fresh, process-scoped, filesystem-safe writer id (the spec's own
    Always bullet): ``f"spin-{os.getpid()}"`` -- always matches
    ``core.journal``'s ``_WRITER_ID_PATTERN`` (a pid is digits-only). One
    CLI invocation is a bounded, sequential, single-process writer, so its
    own ``counter`` (0 for the intent, 1 for the outcome -- this module
    never appends a third entry) can never collide with another writer's by
    construction, without any coordination."""
    return f"spin-{os.getpid()}"


def _now_utc() -> datetime:
    """The one CLI-boundary clock read this module performs -- mirrors
    ``cli/init.py``'s own direct ``Path.cwd()``/``os.environ`` reads (no
    ``ClockPort`` seam exists yet; AD-20's ``ClockPort`` is Story 3.4's
    supervisor scope, not this story's). ``core/journal.py`` itself reads no
    clock (AD-4) -- every timestamp it shapes is a caller-supplied fact."""
    return datetime.now(timezone.utc)


def _format_utc_compact(moment: datetime) -> str:
    """AD-25's ``mint_run_id`` id-component form: ``YYYYMMDDTHHMMSSmmmZ``."""
    return moment.strftime("%Y%m%dT%H%M%S") + f"{moment.microsecond // 1000:03d}Z"


def _format_entry_ts(moment: datetime) -> str:
    """``core.journal.JournalEntry``'s own ``ts`` form:
    ``YYYY-MM-DDTHH:MM:SS.mmmZ`` (millisecond precision, ``T``/``Z`` only --
    see that module's ``_ENTRY_TIMESTAMP_PATTERN``)."""
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _random_token() -> str:
    """AD-25's ``mint_run_id`` random component: lowercase hex, always
    matches ``core.journal``'s ``_RANDOM_TOKEN_PATTERN``
    (``secrets.token_hex`` never emits anything outside ``[0-9a-f]``)."""
    return secrets.token_hex(4)


def _tier3_path(home: Path, slug: str) -> Path:
    """The loop home's local Tier-3 path -- the SAME computation
    ``cli/init.py``'s ``tier3_backlink`` step already makes (a backlink to
    the canonical store, AD-11): writing under it reaches the canonical
    Tier-3 store through the home's own backlink, never a second path."""
    return home / "_bmad-output" / "projects" / slug / "implementation-artifacts"


def _run_dir(home: Path, slug: str, run_id: str) -> Path:
    """A run's own directory: ``<tier-3>/runs/<run_id>`` -- matches
    architecture.md's "journals and gate records live under the loop home's
    run directory, backed by the canonical Tier-3 store through the home's
    backlink" (NFR-8: survives worktree teardown)."""
    return _tier3_path(home, slug) / "runs" / run_id


def _filter_preview(
    resolved: Sequence[StoryKey],
    *,
    epic: int | None,
    story: str | None,
    max_count: int | None,
) -> tuple[StoryKey, ...]:
    """Marshal's own best-effort echoed preview (see this module's own
    docstring for why this is deliberately narrower than
    ``bmad_loop.sprintstatus.select_actionable``): filters ``resolved`` by
    ``epic`` (exact match), then by ``story`` (normalized via
    ``core.identity.normalize`` and matched for EXACT equality -- an
    unparseable ``story`` previews empty rather than raising or falling back
    to a fuzzy match, since the real selection never runs through this
    function), then truncates to ``max_count``. Any argument left ``None``
    is a no-op filter for that axis."""
    keys: Sequence[StoryKey] = resolved
    if epic is not None:
        keys = [key for key in keys if key.epic == epic]
    if story is not None:
        try:
            target = normalize(story)
        # `ValueError`, not just `MalformedStoryKeyError` (which is a
        # ValueError SUBCLASS, so this stays a strict superset of the
        # documented case). `normalize` ends in `int(match.group("epic"))`,
        # and `_KEY_RE` happily matches an arbitrarily long digit run -- so
        # `--story <4301-digit epic>.1` raises CPython >= 3.11's PLAIN
        # ValueError ("Exceeds the limit (4300 digits) for integer string
        # conversion") past this catch and out of `main()` as a raw
        # traceback (reproduced live by both reviewers, reachable from any
        # shell with one long argument). `core/journal.py` already
        # documents this exact CPython behaviour and widened its own
        # catches for it; this call site is the same class.
        except ValueError:
            keys = ()
        else:
            keys = [key for key in keys if key == target]
    if max_count is not None:
        keys = keys[:max_count]
    return tuple(keys)


def _append_entry(fs: FsPort, run_dir: Path, entry: JournalEntry, *, fsync: bool) -> None:
    """The one write path every journal append in this module uses:
    ``core.journal.prepare_for_write``'s sidecar decision, then the sidecar
    blob (if any) BEFORE the line that references it -- so a reader can
    never observe a line whose ``sidecar_ref`` does not yet resolve -- then
    the line itself via ``FsPort.append_line``. ``fsync`` is the caller's own
    choice (AD-30: ``True`` for ``phase: intent``, ``False`` for
    ``phase: outcome``)."""
    prepared = prepare_for_write(entry)
    if prepared.sidecar_relative_path is not None:
        fs.write_text_atomic(run_dir / prepared.sidecar_relative_path, prepared.sidecar_content)
    fs.append_line(run_dir / _JOURNAL_FILENAME, prepared.line, fsync=fsync)


def add_factory_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``factory`` subcommand on ``main.py``'s subparser tree,
    with nested ``spin``/``attach`` actions (mirrors ``cli/gate.py``'s own
    nested-action shape)."""
    parser = subparsers.add_parser(
        "factory",
        help="Launch and attach to bmad-loop runs (AD-3/AD-22/AD-25).",
        description=(
            "Detached-by-default bmad-loop launch with scoped story "
            "selection (marshal factory spin), and a separate, "
            "non-destructive session-attach command (marshal factory "
            "attach)."
        ),
    )
    factory_subparsers = parser.add_subparsers(dest="factory_command", required=True)

    spin_parser = factory_subparsers.add_parser(
        "spin",
        help="Detach-launch a bmad-loop run for a provisioned loop home (AD-22/AD-25/AD-38).",
        description=(
            "Resolves the provisioned loop home, verifies the raw story "
            "feed resolves completely (AD-38), mints a Marshal run id, "
            "journals intent/outcome around the detached launch, and "
            "returns promptly with the run id -- the launched harness "
            "process survives this invocation exiting (AD-22)."
        ),
    )
    spin_parser.add_argument("slug", help="The BMAD project slug whose loop home to launch.")
    spin_parser.add_argument(
        "--epic",
        type=_non_negative_int,
        default=None,
        metavar="N",
        help="Only stories from this epic (passed through to 'bmad-loop run').",
    )
    spin_parser.add_argument(
        "--story",
        default=None,
        metavar="KEY",
        help="A single story reference (passed through to 'bmad-loop run').",
    )
    spin_parser.add_argument(
        "--max-count",
        dest="max_count",
        type=_non_negative_int,
        default=None,
        metavar="N",
        help="Stop after N stories (passed through to 'bmad-loop run' as --max-stories).",
    )
    spin_parser.add_argument(
        "--foreground",
        action="store_true",
        help=(
            "Run 'bmad-loop run' inline instead of detached, blocking this "
            "invocation until it exits and relaying its exit code (projected "
            "into marshal's own exit-code domain: 0/1/130 pass through, any "
            "other non-zero reports as an error). UNSAFE for resumes "
            "(marshal factory resume is a separate, later story's scope) -- "
            "forward documentation only."
        ),
    )
    spin_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text). Not used under --foreground.",
    )
    spin_parser.set_defaults(handler=run_spin)

    attach_parser = factory_subparsers.add_parser(
        "attach",
        help="Attach to a live run's session -- separate, non-destructive (AD-22).",
        description=(
            "Execs 'bmad-loop attach', inheriting this process's own "
            "stdio -- interactive by design, and never mutates run state. "
            "Its exit code is PROJECTED, not relayed verbatim: 0, 1 and 130 "
            "pass through, anything else collapses to Marshal's ERROR code "
            "(4). See core.verdict.relay_exit_code."
        ),
    )
    attach_parser.add_argument("slug", help="The BMAD project slug whose loop home to attach to.")
    attach_parser.set_defaults(handler=run_attach)


def run_spin(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    harness: HarnessPort | None = None,
    process: ProcessPort | None = None,
) -> int:
    fs = fs if fs is not None else LocalFs()
    harness = harness if harness is not None else BmadLoopHarness()
    process = process if process is not None else PosixProcess()

    slug = args.slug
    findings: list[Finding] = []
    data: dict[str, object] = {"slug": slug}

    # --- slug shape -- blocking, before ANY filesystem/harness touch --------
    # mirrors run_init/run_preflight/run_teardown's own identical pre-I/O
    # shape gate (the SAME core.policy._is_valid_project_slug check -- no
    # second slug regex).
    if not policy._is_valid_project_slug(slug):
        findings.append(
            Finding(
                code="MRS-SPIN-001",
                severity=Severity.ERROR,
                message=(
                    f"malformed project slug {slug!r} -- must be one safe "
                    "path segment (letters, digits, '.', '_', '-'; not '.' "
                    "or '..'; at most 255 characters)"
                ),
            )
        )
        return _emit(args, data, findings)

    # --- loop home must exist -- blocking, before either launch path --------
    try:
        home = _home_path(slug)
    except (RuntimeError, OSError) as exc:
        # Path.home()/expanduser can raise RuntimeError when HOME is
        # unresolvable (mirrors run_init/run_preflight's identical catch).
        findings.append(
            Finding(
                code="MRS-SPIN-002",
                severity=Severity.ERROR,
                message=f"resolving the loop-home root: {exc}",
            )
        )
        return _emit(args, data, findings)
    data["home"] = str(home)

    if not fs.is_dir(home):
        findings.append(
            Finding(
                code="MRS-SPIN-002",
                severity=Severity.ERROR,
                message=(
                    f"loop home not provisioned: {str(home)!r} is not a directory "
                    f"-- run 'marshal init {slug}' first"
                ),
                path=str(home),
            )
        )
        return _emit(args, data, findings)

    # --- --foreground: a wholly separate, synchronous path -------------------
    # Skips the story-feed/journal machinery entirely -- there is no minted
    # run id and nothing to journal for a launch that never calls spin() (see
    # this module's own docstring).
    if args.foreground:
        try:
            code = harness.run_foreground(
                home, epic=args.epic, story=args.story, max_count=args.max_count
            )
        except HarnessError as exc:
            findings.append(
                Finding(
                    code="MRS-SPIN-003",
                    severity=Severity.ERROR,
                    message=f"cannot launch bmad-loop run: {exc}",
                )
            )
            return _emit(args, data, findings)
        # Relays bmad-loop run's own result, bypassing the envelope entirely
        # (mirrors run_attach/cli/main.py --version's existing precedent) --
        # through core.verdict's own `relay_exit_code` projection, never the
        # raw child code: main() admits only GUARDED_EXIT_CODES from a
        # handler (AD-7's frozen domain), so returning the raw value here
        # silently reported every out-of-domain child code as EXIT_USAGE.
        # See that function's own docstring for the full review finding.
        return relay_exit_code(code)

    # --- story feed must resolve -- refuse early, before any write ----------
    # `story_feed_error`'s own port docstring promises "never raises" (the
    # message text IS the return value), but its adapter's catch tuples are
    # not exhaustive over what bmad_loop's own parsing can throw -- review
    # finding, reproduced independently by both reviewers against a real
    # feed: deeply-nested YAML raises `RecursionError` (a RuntimeError, so
    # `yaml.YAMLError` never sees it), and an over-long digit run in a key
    # raises a plain `ValueError` out of bmad_loop's own `int()`. Either
    # escaped this call site as a raw traceback out of `main()`, whose only
    # catches are SystemExit/KeyboardInterrupt.
    #
    # Guarded here rather than in the adapter because the promise this
    # protects is `main()`'s, and because the SIBLING call 17 lines below
    # was already wrapped for exactly this shape by an earlier pass -- the
    # asymmetry between two adjacent calls was the defect. `core/journal.py`
    # catches this same (ValueError, TypeError, RecursionError) trio for the
    # same reason; the adapter's own tuples are a pre-existing gap
    # `cli/init.py` shares and are left for a focused pass.
    try:
        feed_error = harness.story_feed_error(home)
    except (ValueError, TypeError, RecursionError, OSError) as exc:
        feed_error = f"cannot read story feed: {exc}"
    if feed_error is not None:
        findings.append(
            Finding(code="MRS-SPIN-005", severity=Severity.ERROR, message=feed_error)
        )
        return _emit(args, data, findings)

    # --- AD-38 feed completeness -- refuse the launch if anything failed ----
    # to parse; nothing has been minted or written yet, so refusing here
    # produces NO journal entries at all (the spec's own Always bullet).
    # `story_feed_keys` documents it can still raise `HarnessError` despite
    # the `story_feed_error` gate above (a TOCTOU window, or a caller that
    # reaches it via a path that skipped that gate) -- review finding
    # (Edge Case Hunter, verified live): this call was unguarded, so that
    # documented raise crashed run_spin with a raw traceback instead of the
    # clean MRS-SPIN-005 exit every OTHER harness call in this function
    # already produces.
    try:
        raw_keys = harness.story_feed_keys(home)
    except HarnessError as exc:
        findings.append(
            Finding(code="MRS-SPIN-005", severity=Severity.ERROR, message=str(exc))
        )
        return _emit(args, data, findings)
    # `resolve_feed` catches only `MalformedStoryKeyError` around its own
    # `normalize` calls, so a raw feed key whose epic position exceeds
    # CPython's 4300-digit int-conversion limit raises a PLAIN ValueError
    # through it (review finding, reproduced live against a real
    # sprint-status.yaml using YAML explicit-key syntax). This module is
    # `resolve_feed`'s only caller in the tree, so the crash is newly
    # reachable with this story; guarded HERE rather than by widening
    # `core/identity.py`, which is deliberately outside this story's Code
    # Map. A feed key Marshal cannot even attempt to parse is exactly
    # MRS-SPIN-005's own "missing or unparseable" scenario.
    try:
        resolution = resolve_feed(raw_keys)
    except ValueError as exc:
        findings.append(
            Finding(
                code="MRS-SPIN-005",
                severity=Severity.ERROR,
                message=f"cannot parse the story feed's keys: {exc}",
            )
        )
        return _emit(args, data, findings)
    data["feed"] = {
        "resolved": len(resolution.resolved),
        "total": resolution.total,
        "unresolved": list(resolution.unresolved),
    }
    if resolution.unresolved:
        findings.extend(resolution.findings)
        return _emit(args, data, findings)

    # --- echoed preview -------------------------------------------------------
    preview = _filter_preview(
        resolution.resolved, epic=args.epic, story=args.story, max_count=args.max_count
    )
    data["selector"] = {"epic": args.epic, "story": args.story, "max_count": args.max_count}
    data["preview"] = [render_feed_key(key) for key in preview]

    # --- Tier-3 backlink must exist -- the LAST precondition before the ----
    # first write, and the only one the write path alone needs (which is why
    # --foreground, which writes nothing, returns above without it).
    #
    # Review finding (Blind Hunter + Edge Case Hunter, both verified live):
    # `fs.is_dir(home)` was the ONLY home precondition, so a home whose
    # Tier-3 backlink is absent still reached `fs.ensure_dir(run_dir.parent)`
    # below -- whose `parents=True` then FABRICATED
    # `_bmad-output/projects/<slug>/implementation-artifacts/runs/` as real
    # local directories inside the home, and wrote this run's journal and
    # harness.log into them, at exit 0 with no finding at all. Two harms:
    # NFR-8 (those journals must survive worktree teardown -- through the
    # backlink they live in the canonical store; fabricated locally they die
    # with the home), and a later repair `marshal init <slug>` is then
    # PERMANENTLY refused by its own MRS-INIT-005 ("a real, non-empty
    # directory -- refusing to replace it with a backlink").
    #
    # A missing backlink IS a provisioning gap, so this is MRS-SPIN-002's own
    # scenario ("loop home not provisioned"), not a new code -- and presence
    # is the whole check: `marshal homes`' own MRS-HOMES-002 realpath-vs-
    # canonical comparison needs a VcsPort-derived repo root this command
    # does not take. A backlink that EXISTS but points elsewhere still writes
    # through to a single, real Tier-3 store; only its ABSENCE causes the
    # fabrication above.
    #
    # `read_symlink_target` RAISES `FsError` on any `OSError` -- its own
    # implementation comment names the concrete trigger, a `PermissionError`
    # from an unsearchable ancestor on this package's 3.12 floor. This call
    # was the ONLY unguarded `FsPort` call in `run_spin` (review finding,
    # Blind Hunter + Edge Case Hunter, both verified live): every sibling
    # call site guards it (`cli/init.py`'s own two blocking probes do), every
    # OTHER fs call in this function guards it, and `main()` catches only
    # `SystemExit`/`KeyboardInterrupt` -- so an escape here surfaced as a raw
    # traceback, breaking that function's own documented "never raises"
    # contract. Exactly the class of defect this same story already fixed
    # twice (`story_feed_keys`, `_relay_attach_finding`).
    tier3_path = _tier3_path(home, slug)
    try:
        tier3_target = fs.read_symlink_target(tier3_path)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-SPIN-002",
                severity=Severity.ERROR,
                message=(
                    f"cannot read the loop home Tier-3 backlink "
                    f"{str(tier3_path)!r}: {exc}"
                ),
                path=str(tier3_path),
            )
        )
        return _emit(args, data, findings)
    if tier3_target is None:
        findings.append(
            Finding(
                code="MRS-SPIN-002",
                severity=Severity.ERROR,
                message=(
                    f"loop home Tier-3 backlink not provisioned: {str(tier3_path)!r} "
                    f"is not a symlink to the canonical store -- run "
                    f"'marshal init {slug}' first"
                ),
                path=str(tier3_path),
            )
        )
        return _emit(args, data, findings)
    # A backlink that EXISTS but DANGLES (its target removed -- a repo
    # re-clone, a moved checkout) passes the presence check above, then made
    # `ensure_dir(run_dir.parent)` raise `FileExistsError` from
    # `Path.mkdir(parents=True, exist_ok=True)`, since a dangling symlink is
    # not a directory. Review finding, reproduced: that surfaced as
    # `MRS-SPIN-003 [error] cannot create run directory <run-dir>: [Errno 17]
    # File exists: <implementation-artifacts>` -- a LAUNCH-failure code, and a
    # message naming a path that is not the one it says it is, for what is
    # unambiguously the same provisioning gap the presence check above exists
    # to catch. `is_dir` follows the link, so it is False for exactly the
    # dangling case and True for a healthy one.
    if not fs.is_dir(tier3_path):
        findings.append(
            Finding(
                code="MRS-SPIN-002",
                severity=Severity.ERROR,
                message=(
                    f"loop home Tier-3 backlink is dangling: {str(tier3_path)!r} "
                    f"points at {str(tier3_target)!r}, which is not a directory "
                    f"-- run 'marshal init {slug}' first"
                ),
                path=str(tier3_path),
            )
        )
        return _emit(args, data, findings)

    # --- mint the run id, THEN create its directory (AD-25/AD-6) ------------
    writer_id = _writer_id()
    mint_moment = _now_utc()
    run_id = mint_run_id(slug, _format_utc_compact(mint_moment), _random_token())
    data["run_id"] = run_id

    run_dir = _run_dir(home, slug, run_id)
    try:
        fs.ensure_dir(run_dir.parent)
        fs.create_dir_exclusive(run_dir)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-SPIN-003",
                severity=Severity.ERROR,
                message=f"cannot create run directory {str(run_dir)!r}: {exc}",
            )
        )
        return _emit(args, data, findings)

    # --- write-before-act: intent BEFORE the spawn (AD-6) --------------------
    intent_id = JournalEntryId(writer_id, 0)
    intent_entry = build_entry(
        id=intent_id,
        ts=_format_entry_ts(mint_moment),
        run_id=run_id,
        kind=_LAUNCH_KIND,
        phase=Phase.INTENT,
        payload={
            "epic": args.epic,
            "story": args.story,
            "max_count": args.max_count,
            "preview": list(data["preview"]),
        },
    )
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-SPIN-003",
                severity=Severity.ERROR,
                message=f"cannot journal the launch intent: {exc}",
            )
        )
        return _emit(args, data, findings)

    # --- the detached spawn itself --------------------------------------------
    # The log path is reported (review finding, Blind Hunter): it was
    # computed, handed to `spin`, and then dropped -- absent from `data`,
    # from both journal entries, and from MRS-SPIN-004's own message. For a
    # DETACHED child the operator no longer has its stdout, so this file is
    # the only diagnostic they have; a warning that the run id "could not be
    # confirmed" without saying where the output went is unactionable.
    log_path = run_dir / _LOG_FILENAME
    data["log"] = str(log_path)
    try:
        spin_result = harness.spin(
            home,
            epic=args.epic,
            story=args.story,
            max_count=args.max_count,
            log_path=log_path,
        )
    except HarnessError as exc:
        findings.append(
            Finding(
                code="MRS-SPIN-003",
                severity=Severity.ERROR,
                message=f"cannot launch bmad-loop run: {exc}",
            )
        )
        # AD-6: the attempt is journaled as a FAILED outcome, never as a
        # successful launch -- run id and directory already exist by this
        # point, so the failure must still be recorded against them.
        outcome_entry = build_entry(
            id=JournalEntryId(writer_id, 1),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind=_LAUNCH_KIND,
            phase=Phase.OUTCOME,
            intent_id=intent_id,
            payload={"pid": None, "harness_run_id": None, "error": str(exc)},
        )
        try:
            _append_entry(fs, run_dir, outcome_entry, fsync=False)
        except FsError:
            # A second I/O failure recording the first does not change the
            # outcome (the launch already failed, already the finding
            # above) -- only the audit trail; nothing further to do.
            pass
        return _emit(args, data, findings)

    data["pid"] = spin_result.pid
    data["harness_run_id"] = spin_result.harness_run_id
    if spin_result.harness_run_id is None:
        findings.append(
            Finding(
                code="MRS-SPIN-004",
                severity=Severity.WARN,
                message=(
                    f"bmad-loop run launched (pid {spin_result.pid}) but its "
                    "own self-minted run id could not be confirmed within "
                    f"the poll window -- see {log_path}"
                ),
            )
        )

    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, 1),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=_LAUNCH_KIND,
        phase=Phase.OUTCOME,
        intent_id=intent_id,
        payload={"pid": spin_result.pid, "harness_run_id": spin_result.harness_run_id},
    )
    try:
        _append_entry(fs, run_dir, outcome_entry, fsync=False)
    except FsError as exc:
        # The process is already live and detached -- there is nothing left
        # to roll back; the gap is that its outcome could not be journaled.
        # A DISTINCT code from MRS-SPIN-003 (review finding, Blind Hunter,
        # verified live): reusing 003 here conflated "never launched, safe
        # to retry" with "a live process now exists, unaccounted for in the
        # journal" -- a caller treating either alike as safe-to-retry could
        # double-spawn a second concurrent run against the same project.
        findings.append(
            Finding(
                code="MRS-SPIN-006",
                severity=Severity.WARN,
                message=(
                    f"bmad-loop run launched (pid {spin_result.pid}) but its "
                    f"outcome could not be journaled: {exc}"
                ),
            )
        )

    # --- spawn the supervisor sidecar -- the LAST step (Story 3.4, AD-9) ----
    # Deliberately AFTER the outcome-entry append above is attempted --
    # succeeded or not. The supervisor's own inert-check reads this run's
    # journal back off disk to prove Marshal ownership, and it accepts
    # EITHER the intent or the outcome run-launch entry, so ordering this
    # spawn after the outcome append is no longer a correctness requirement
    # (the intent entry is written fsync=True BEFORE harness.spin(), so
    # ownership is already provable at any point after that). It stays last
    # for a different, still-live reason: everything above can add findings
    # to this same report, and a supervisor that attached BEFORE the outcome
    # entry landed would interleave its own observation entries with
    # cli/spin.py's own outcome append -- two writers appending to one
    # journal with no ordering guarantee between them. Keeping the spawn
    # last means the launch's own intent/outcome pair is closed before a
    # second writer ever opens the file.
    supervisor_log = run_dir / _SUPERVISOR_LOG_FILENAME
    # Reported unconditionally, BEFORE the spawn attempt (review finding):
    # this file is the detached supervisor's only diagnostic channel -- its
    # stderr goes nowhere else -- so an operator whose supervisor dies 60s
    # later on an unwritable journal needs the path whether or not the spawn
    # itself succeeded. `data["log"]` above carries the harness's own log for
    # exactly this reason, recorded there as a prior review finding: "a
    # warning ... without saying where the output went is unactionable".
    data["supervisor_log"] = str(supervisor_log)
    try:
        supervisor_pid = process.spawn_detached(
            [
                sys.executable,
                "-m",
                "pyforge.marshal.supervisor",
                str(home),
                slug,
                run_id,
                str(spin_result.pid),
                str(supervisor_log),
            ],
            cwd=home,
            log_path=supervisor_log,
        )
    except ProcessError as exc:
        # The harness launch already succeeded (a live process exists) --
        # losing supervision degrades the run to unsupervised, never
        # invalidates the launch: WARN, the same tier as MRS-SPIN-006's own
        # "a different paper-trail gap over an already-successful launch".
        findings.append(
            Finding(
                code="MRS-SPIN-007",
                severity=Severity.WARN,
                message=(
                    f"bmad-loop run launched (pid {spin_result.pid}) but its "
                    f"supervisor could not be spawned: {exc} -- the run "
                    f"continues unsupervised (supervisor log: {supervisor_log})"
                ),
            )
        )
    else:
        data["supervisor_pid"] = supervisor_pid

    return _emit(args, data, findings)


def _scalar(value: object) -> str:
    """Render one ``data`` scalar for the text projection: ``None`` as the
    JSON spelling ``null`` (so the two ``--format`` paths agree instead of
    the text one leaking a Python ``repr``), every string quoted, every
    other value as-is. See ``_render_text``'s own comment for why the
    quoting is load-bearing rather than cosmetic."""
    if value is None:
        return "null"
    if isinstance(value, str):
        return repr(value)
    return str(value)


def _render_text(data: Mapping[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14), matching every sibling command's
    own ``_render_text`` convention."""
    # Every field here whose content is attacker- or typo-controlled is
    # rendered through `_scalar` (i.e. `repr`), exactly as `cli/gate.py`'s
    # own `_render_text` already does across two of its review passes --
    # this module shipped without that hardening and both reviewers
    # reproduced the consequence live. A newline inside any of them forges
    # whole lines of this report: `--story $'9.9\nfindings:\n  MRS-SPIN-001
    # [error] FORGED: launch refused'` printed a `findings:` block that no
    # Finding produced, on a run that had genuinely LAUNCHED (rc=0), and a
    # raw feed key carrying `\nrun_id: ...\npid: 1` printed a run id and pid
    # for a launch that was REFUSED. `--format json` was never affected
    # (`ensure_ascii=True`, and JSON escapes newlines) -- but text is the
    # DEFAULT, so the default invocation is the exposed one.
    #
    # Quoting also makes this path encoding-safe, which is why `_emit`'s own
    # guard below could stay narrow for so long: Python decodes argv with
    # `surrogateescape`, so a non-UTF-8 byte in `--story` reached a strict
    # UTF-8 stdout and raised `UnicodeEncodeError` -- AFTER the detached
    # child was live and both journal entries fsynced, i.e. a traceback
    # instead of the run id the operator needs to attach. `repr` output is
    # pure ASCII, so the surrogate can no longer reach the encoder.
    #
    # Finding MESSAGES are deliberately NOT quoted -- they are Marshal's own
    # prose and must stay readable, the same split `cli/gate.py` documents;
    # every message that interpolates an untrusted value quotes it at
    # construction instead (see the `MRS-SPIN-001`/`002` sites above).
    lines = [f"factory spin: {_scalar(data['slug'])}"]
    if "home" in data:
        lines.append(f"home: {_scalar(str(data['home']))}")
    if "feed" in data:
        feed = data["feed"]
        lines.append(f"feed: resolved {feed['resolved']} of {feed['total']}")
        if feed["unresolved"]:
            lines.append(f"  unresolved: {', '.join(repr(key) for key in feed['unresolved'])}")
    if "selector" in data:
        selector = data["selector"]
        lines.append(
            f"selector: epic={_scalar(selector['epic'])} "
            f"story={_scalar(selector['story'])} "
            f"max_count={_scalar(selector['max_count'])}"
        )
    if "preview" in data:
        lines.append(f"preview ({len(data['preview'])}): {', '.join(data['preview'])}")
    if "run_id" in data:
        lines.append(f"run_id: {data['run_id']}")
    if "log" in data:
        lines.append(f"log: {_scalar(str(data['log']))}")
    if "pid" in data:
        lines.append(f"pid: {data['pid']}")
    if "harness_run_id" in data:
        lines.append(f"harness_run_id: {_scalar(data['harness_run_id'])}")
    if "supervisor_log" in data:
        lines.append(f"supervisor_log: {_scalar(str(data['supervisor_log']))}")
    if "supervisor_pid" in data:
        # Through `_scalar` like every sibling scalar here (review finding):
        # a raw f-string opts this one field out of the single helper that
        # exists to keep the text and JSON projections agreeing.
        lines.append(f"supervisor_pid: {_scalar(data['supervisor_pid'])}")
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)


def _emit(args: argparse.Namespace, data: dict[str, object], findings: list[Finding]) -> int:
    verdict_value = compute_verdict(tuple(findings))
    envelope = build_envelope(
        command="factory spin", verdict=verdict_value, data=data, findings=tuple(findings)
    )
    # Same flush + broken-pipe-suppression convention as every sibling
    # command's own _emit (cli/init.py, cli/gate.py, cli/config.py).
    #
    # `UnicodeEncodeError` is caught alongside `OSError` for the same
    # reason and with the same remedy: `_render_text`'s quoting now keeps
    # surrogates out of the encoder, but this is the LAST line between a
    # print failure and a raw traceback out of `main()` -- and by the time
    # it runs on the success path the detached child is already live and
    # both journal entries are fsynced, so the work is done and a dead or
    # undecodable stdout must not turn it into a crash. A `ValueError`
    # subclass, so the pre-existing `OSError` catch never saw it.
    try:
        if args.format == "json":
            print(json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True), flush=True)
        else:
            print(_render_text(envelope.data, envelope.findings), flush=True)
    except (OSError, UnicodeEncodeError):
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def run_attach(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    harness: HarnessPort | None = None,
) -> int:
    """``marshal factory attach <slug>`` -- unlike ``run_spin``, this NEVER
    builds an ``Envelope`` (the spec's own Always bullet: "attach does NOT
    [build one] -- it hands the terminal to the multiplexer and relays
    bmad-loop's own exit code directly", mirroring ``cli/main.py``'s
    ``--version`` precedent for a command that legitimately bypasses it).
    Its own two shared precondition gates still classify through
    ``core.verdict``'s sole-owned ``classify``/``exit_code_for`` projection
    over a real, registered ``Finding`` -- never a bare exit-code literal
    (AD-7) -- printed as a plain message rather than serialized into a JSON
    envelope; there being no envelope changes only the RENDERING, not which
    lattice rung each precondition failure occupies."""
    fs = fs if fs is not None else LocalFs()
    harness = harness if harness is not None else BmadLoopHarness()

    slug = args.slug

    if not policy._is_valid_project_slug(slug):
        finding = Finding(
            code="MRS-SPIN-001",
            severity=Severity.ERROR,
            message=(
                f"malformed project slug {slug!r} -- must be one safe path "
                "segment (letters, digits, '.', '_', '-'; not '.' or '..'; "
                "at most 255 characters)"
            ),
        )
        return _relay_attach_finding(finding)

    try:
        home = _home_path(slug)
    except (RuntimeError, OSError) as exc:
        finding = Finding(
            code="MRS-SPIN-002",
            severity=Severity.ERROR,
            message=f"resolving the loop-home root: {exc}",
        )
        return _relay_attach_finding(finding)

    if not fs.is_dir(home):
        finding = Finding(
            code="MRS-SPIN-002",
            severity=Severity.ERROR,
            message=(
                f"loop home not provisioned: {str(home)!r} is not a directory -- "
                f"run 'marshal init {slug}' first"
            ),
            path=str(home),
        )
        return _relay_attach_finding(finding)

    try:
        # Same `relay_exit_code` projection --foreground uses, for the same
        # reason (AD-7's frozen domain vs main()'s handler clamp) -- see
        # core/verdict.py's own docstring for the review finding.
        return relay_exit_code(harness.attach(home))
    except HarnessError as exc:
        finding = Finding(
            code="MRS-SPIN-003",
            severity=Severity.ERROR,
            message=f"cannot launch bmad-loop attach: {exc}",
        )
        return _relay_attach_finding(finding)


def _relay_attach_finding(finding: Finding) -> int:
    """``run_attach``'s own no-envelope error path: print the finding to
    stderr and project its classification straight to an exit code -- the
    same ``compute_verdict``/``exit_code_for`` machinery every enveloped
    command uses, minus the envelope itself.

    Two review findings, both verified live. (1) The line printed only
    ``finding.message``, dropping the CODE every other command in this
    package emits (``_render_text``'s own ``{code} [{severity}] {message}``
    shape) -- so ``marshal factory attach ../escaped`` and the IDENTICAL
    ``run_spin`` refusal were uncorrelatable by an operator or a log
    scraper. It now uses that same shape. (2) The ``print`` was unguarded,
    unlike its sibling ``_emit``: an unwritable stderr (a closed pipe, a
    full disk) raised ``OSError`` straight out of ``run_attach``, breaking
    ``main()``'s own documented "never raises" contract with a raw
    traceback. Guarded here exactly as ``_emit`` guards its own -- including
    that guard's own ``UnicodeEncodeError`` arm, since the slug this path
    reports reaches it straight from ``argv`` (decoded with
    ``surrogateescape``) and every finding here quotes it."""
    try:
        print(
            f"error: {finding.code} [{finding.severity.value}] {finding.message}",
            file=sys.stderr,
            flush=True,
        )
    except (OSError, UnicodeEncodeError):
        _suppress_downstream_pipe_close()
    return exit_code_for(compute_verdict((finding,)))
