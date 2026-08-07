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

Story 3.5 (idle-strand detection, AD-9/AD-20, FR-12) grows the supervisor
spawn's argv from 5 to 6 positionals: the effective ``idle_threshold_minutes``
(``core.policy.EffectivePolicy.seed_view()``'s own 10th SEED key, resolved by
composing against the SAME conventional project-policy layer ``marshal
config`` reads -- a missing or unreadable file degrades to Marshal's own
``DEFAULT_POLICY`` value rather than aborting an otherwise-successful
launch, since this is a supplementary numeric value for the supervisor's
own soft ladder, never a launch precondition) is appended as the LAST argv
element, the same mechanism ``watched_pid``/``log_path`` already use.

Story 3.6 (budget ceilings, AD-20/AD-32, FR-13) grows the argv further, 6 ->
10: the 4 budget-ceiling SEED keys (``max_tokens_per_story``,
``max_tokens_per_run``, ``max_wall_clock_minutes_per_story``,
``max_wall_clock_minutes_per_run``) are resolved from the SAME
``effective_policy`` composition ``idle_threshold_minutes`` already reads
(never a second ``compose()`` call) and appended in that order, mirroring
``idle_threshold_minutes``'s own wiring exactly. The same story adds a
non-blocking FR-14 preflight advisory (``MRS-SPIN-009``) after the echoed
preview is computed and before the harness launches: for each SELECTED
story key (the ``_filter_preview`` output, never the whole resolved feed --
a review finding: advising over the unfiltered set warned about stories
``--epic``/``--story``/``--max-count`` had already excluded from this
launch), a fixed-threshold check of its spec file's byte size plus a
best-effort scan of this loop home's OWN prior ``.bmad-loop/runs/*/
state.json`` files for a matching task with ``attempt >= 2`` or a terminal
``deferred``/``escalated`` phase -- either signal emits one WARN naming the
story and the reason(s); never blocks the launch, and "declared difficulty"
is deliberately NOT an input (see ``deferred-work.md``: no
difficulty-classification mechanism exists anywhere in this codebase yet).
Both signals match by NORMALIZED story key / titled spec filename, never by
a rendered string form (review finding -- matching on the rendered forms
made both halves unreachable on real data; see ``_prior_attempt_keys`` and
``_large_spec_bytes``).

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

Story 3.7 (escalation, deferral, and resume, AD-3/AD-25/AD-45,
FR-15/16/17) adds ``marshal factory resume``, this module's second launch
verb: ``run_resume`` finds the most recent Marshal run directory for
``slug`` under the Tier-3 store (``<tier3>/runs/<slug>-*``, sorted --
``MRS-SPIN-011`` if none exists), folds its journal to recover the
harness's own self-minted ``harness_run_id`` (the SAME
``run-launch``-outcome-entry lookup ``supervisor/__main__.py::
_resolve_harness_run_id`` performs, reproduced here rather than imported --
this module already duplicates several of ITS own helpers across that same
AD-9 boundary, and the new one is small, pure, and private; ``MRS-SPIN-011``
again if it cannot be recovered), then calls ``HarnessPort.
run_status_snapshot`` **live** and classifies it via ``core.supervise.
evaluate_escalation`` -- never trusting the historical journal for the
resolved/unresolved question, only for discovering which ``harness_run_id``
to check (the spec's own Always bullet: an arbitrarily long gap can
separate detection from a resume attempt, and only a fresh read answers "is
it STILL unresolved right now"). ``EscalationStatus.UNRESOLVED`` refuses
with ``MRS-SPIN-010`` before any spawn, mint, or journal write. Otherwise it
mints a FRESH Marshal run id (never reusing the prior one -- AD-25), journals
a ``"run-resume"`` intent carrying AD-45's four back-reference fields
(``story_key``, ``reason``, ``resolution_reference`` -- via the new
``HarnessPort.resolution_reference`` seam, since AD-3 confines the
``bmad_loop.resolve`` import this needs to ``adapters/harness_bmadloop.py``
alone, never this module directly -- and ``resolver``, via
``getpass.getuser()``, AD-27's own "attributable, not authenticated" trust
model) before spawning, detach-launches ``HarnessPort.resume`` (the
identical detached-launch recipe ``spin`` uses), journals the outcome, and
spawns a fresh supervisor sidecar via ``_spawn_supervisor_sidecar`` -- the
SAME argv-construction/policy-composition logic ``run_spin``'s own tail
already performs, extracted into a shared helper (Story 3.7) so the two
launch verbs cannot drift out of agreement over what a supervisor sidecar's
10-positional argv looks like. ``resume`` accepts no ``--epic``/``--story``/
``--max-count`` (the spec's own Never clause: ``bmad-loop resume`` itself
ignores them, rebuilding the engine from state-pinned scope only) and no
``--foreground`` (no synchronous ``HarnessPort`` counterpart to
``resume`` exists, unlike ``spin``'s own ``run_foreground`` -- inventing one
with no real caller would be speculative surface this story's own Code Map
does not ask for; a factual inaccuracy in the intent-contract's own literal
wording, recorded in the spec's Spec Change Log).

Registers ``MRS-SPIN-001`` through ``MRS-SPIN-012`` (``core/findings.py``/
``core/verdict.py``) -- see those modules' own docstrings for the full
per-code rationale. ``MRS-SPIN-006`` joined the original five in review,
splitting "launched, but its outcome could not be journaled" (``WARN`` -- a
live process now exists) off ``MRS-SPIN-003``'s "never launched, safe to
retry" (``ERROR``). ``MRS-SPIN-007`` (Story 3.4) is the supervisor-spawn
failure -- the SAME ``WARN`` tier as ``MRS-SPIN-006``, for the same reason:
a live, launched harness process is never re-classified as a failure over a
DIFFERENT paper-trail gap (losing supervision rather than losing the
outcome journal entry). ``MRS-SPIN-008`` (Story 3.5) is the project-policy
composition finding wrapper. ``MRS-SPIN-009`` (Story 3.6) is the FR-14
preflight advisory above -- also ``WARN``: it is a non-blocking heads-up
about the story about to run, never a launch precondition. ``MRS-SPIN-010``/
``MRS-SPIN-011`` (Story 3.7) are ``resume``'s own two refusal codes -- both
``ERROR``, since both block a real spawn from ever happening, unlike every
other ``MRS-SPIN-*`` WARN above, which all describe an ALREADY-launched
process. ``MRS-SPIN-012`` (Story 3.7, added in review) is the third code
``resume`` alone raises, and the only ``WARN`` of the three: the live
escalation gate could not read the run's status at all, so it proceeds
without having confirmed anything -- ambiguity, never a refusal.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import secrets
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadloop import BmadLoopHarness, HarnessError
from ..adapters.process_posix import PosixProcess, ProcessError
from ..core import policy
from ..core.identity import (
    StoryKey,
    normalize,
    render_feed_key,
    render_filename_slug,
    resolve_feed,
)
from ..core.journal import (
    JournalEntry,
    JournalEntryId,
    Phase,
    build_entry,
    fold,
    mint_run_id,
    prepare_for_write,
)
from ..core.model import Finding, Severity, build_envelope
from ..core.supervise import EscalationStatus, evaluate_escalation
from ..core.verdict import compute_verdict, exit_code_for, relay_exit_code
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from ..ports.process import ProcessPort
from .config import (
    PolicyIOError,
    _read_project_policy,
    _suppress_downstream_pipe_close,
    conventional_project_policy_path,
)
from .init import _home_path

if TYPE_CHECKING:
    # Story 5.6 (FR-65/AD-50): `run_spin`'s `context` parameter below is
    # type-only -- this module's own internal logic is NOT retrofitted to
    # CONSUME it in this pass (see cli/main.py's own module docstring and
    # the spec's Design Notes); a real (non-TYPE_CHECKING) import would add
    # a runtime dependency this module doesn't otherwise need.
    from ..core.context import MarshalContext

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
# Story 3.7's own resume kind -- a SEPARATE intent/outcome pair from
# `_LAUNCH_KIND` above (a resume is a distinct action from a launch, even
# though both mint a fresh Marshal run id and spawn a supervisor sidecar the
# same way).
_RESUME_KIND = "run-resume"

# Story 3.6's FR-14 preflight advisory (MRS-SPIN-009) -- a fixed "this spec
# is large" threshold, calibrated against this repo's own existing story
# specs under `_bmad-output/implementation-artifacts/spec-*.md` (a live
# sample spans roughly 20-62KB; 40_000 bytes sits at the upper-middle of
# that range -- large enough that a spec below it is unremarkable, without
# waiting for the single largest outlier). Not a policy knob (the spec's own
# Never clause names "declared difficulty" as deliberately out of scope for
# this advisory; a size threshold is simpler still, and no caller has asked
# for it to be tunable).
_LARGE_SPEC_BYTES = 40_000

# bmad-loop's own per-run phase strings a task can be LEFT in (never
# progressed past) -- the raw JSON values `runs.py`'s own state.json writes,
# read here WITHOUT importing bmad_loop (this module is not
# `adapters/harness_bmadloop.py`, the one seam AD-3 reserves for that
# import) -- a best-effort scan reads the raw dict, matching
# `supervisor/__main__.py`'s own precedent of parsing bmad-loop-owned output
# by its known-live shape rather than through the package.
_PRIOR_ATTEMPT_PHASES = frozenset({"deferred", "escalated"})


def _prior_attempt_keys(home: Path) -> set[StoryKey]:
    """FR-14's own prior-attempt signal (Story 3.6, best-effort, never
    raises): every story key for which any of this loop home's OWN past
    bmad-loop runs (``.bmad-loop/runs/*/state.json``) recorded a task with
    ``attempt >= 2`` or a phase in ``_PRIOR_ATTEMPT_PHASES``. Reads the raw
    JSON document directly (never ``bmad_loop.journal.load_state`` -- that
    seam belongs solely to ``adapters/harness_bmadloop.py``, AD-3) and skips
    any file this cannot parse as a JSON object with the expected shape --
    one unreadable or malformed prior run must never abort the scan, still
    less the whole command.

    Task keys are matched by NORMALIZING them through ``core.identity``
    (AD-23's sole parser), never by string equality against a rendered form
    (review finding -- the defect that made this whole signal dead code).
    bmad-loop keys ``state.json``'s ``tasks`` map by its OWN key spelling,
    the full sprint-status slug (verified live: ``"3-6-budget-ceilings-and-
    the-heaviest-story-advisory"``), while the first implementation looked
    up ``render_feed_key(key)`` -- the dot form, ``"3.6"`` -- so the lookup
    could never hit on real data and the advisory never fired in production.
    ``normalize`` accepts BOTH spellings and either one collapses to the
    same ``StoryKey``, so this now works against today's slug keys and
    survives an upstream switch to the dot form.

    Scans each ``state.json`` exactly ONCE and returns a set, rather than
    re-globbing and re-parsing every prior run per resolved story -- the
    caller has N stories to check and this home may retain many runs."""
    flagged: set[StoryKey] = set()
    for state_path in home.glob(".bmad-loop/runs/*/state.json"):
        try:
            document = json.loads(state_path.read_text(encoding="utf-8"))
        # `RecursionError` alongside the rest (review finding): `json.loads`
        # raises it -- NOT a `ValueError` -- on a deeply nested document, and
        # this helper's own contract is "never raises". `MemoryError` for an
        # oversized file is deliberately NOT caught: that is a process-wide
        # condition, not a malformed-input one.
        except (OSError, ValueError, UnicodeDecodeError, RecursionError):
            continue
        if not isinstance(document, Mapping):
            continue
        tasks = document.get("tasks")
        if not isinstance(tasks, Mapping):
            continue
        for raw_key, task in tasks.items():
            if not isinstance(task, Mapping):
                continue
            attempt = task.get("attempt", 0)
            phase = task.get("phase")
            # `(int, float)`, not `int` alone (review finding, defensive):
            # this reads RAW JSON, never through `bmad_loop`'s own
            # `int(d["attempt"])` coercion (that seam belongs solely to
            # `adapters/harness_bmadloop.py`, AD-3) -- a `state.json` written
            # by a future or non-conforming writer could serialize
            # `"attempt": 2.0`, which JSON parses as a Python `float`,
            # silently failing an `isinstance(attempt, int)` check and
            # suppressing a genuine prior-attempt signal.
            retried = (
                isinstance(attempt, (int, float))
                and not isinstance(attempt, bool)
                and attempt >= 2
            )
            left_terminal = isinstance(phase, str) and phase in _PRIOR_ATTEMPT_PHASES
            if not (retried or left_terminal):
                continue
            # The task's own `story_key` field first (bmad-loop writes it
            # alongside the map key), falling back to the map key itself.
            candidate = task.get("story_key")
            if not isinstance(candidate, str):
                candidate = raw_key
            try:
                flagged.add(normalize(candidate))
            except ValueError:
                # `MalformedStoryKeyError` is a `ValueError`. A task key this
                # package cannot parse is simply not a story it can advise
                # about -- never a reason to abort the scan.
                continue
    return flagged


def _large_spec_bytes(home: Path, slug: str, key: StoryKey) -> int:
    """FR-14's own spec-size signal (Story 3.6, best-effort, never raises):
    the size in bytes of ``key``'s story spec in this loop home's Tier-3
    store, or ``0`` when no spec file exists yet.

    Matches ``spec-<key>-<title>.md`` as well as a bare ``spec-<key>.md``
    (review finding -- the defect that made this signal dead code). The
    first implementation probed the single exact path
    ``spec-{render_filename_slug(key)}.md`` (``spec-3-6.md``), the literal
    formula this story's own intent contract names; but every spec
    ``bmad-dev-auto`` actually writes carries a descriptive title after the
    key (``spec-3-6-budget-ceilings-and-the-heaviest-story-advisory.md`` --
    its step-01 derives ``spec-{slug}.md`` from a slug that LEADS with the
    story number and continues with the intent text), so the ``stat()``
    always raised and ``spec_size`` was pinned at ``0`` for every story.
    Verified against this project's own Tier-3 store: 21 of 21 specs carry
    the title, and 7 of them would have crossed the threshold.

    The ``-*`` glob is deliberately anchored on a trailing hyphen so story
    ``3.6`` cannot match story ``3.60``'s own spec. The largest match wins
    (there is normally exactly one; a ``-2`` re-run suffix from step-01's
    own collision handling can produce a second)."""
    tier3 = _tier3_path(home, slug)
    stem = f"spec-{render_filename_slug(key)}"
    try:
        titled = sorted(tier3.glob(f"{stem}-*.md"))
    except OSError:
        titled = []
    largest = 0
    for candidate in (tier3 / f"{stem}.md", *titled):
        try:
            largest = max(largest, candidate.stat().st_size)
        except OSError:
            continue
    return largest


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

    resume_parser = factory_subparsers.add_parser(
        "resume",
        help="Resume a paused bmad-loop run, refusing an unresolved escalation (AD-45).",
        description=(
            "Finds the most recent Marshal run for the loop home, checks "
            "LIVE whether its blocking escalation (if any) is still "
            "unresolved -- refusing before any spawn if so -- then "
            "detach-launches 'bmad-loop resume' and re-attaches a fresh "
            "supervisor, journaling an AD-45 back-reference to the "
            "resolving decision. No --epic/--story/--max-count (bmad-loop "
            "resume itself rebuilds from state-pinned scope only)."
        ),
    )
    resume_parser.add_argument("slug", help="The BMAD project slug whose loop home to resume.")
    resume_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    resume_parser.set_defaults(handler=run_resume)


def _spawn_supervisor_sidecar(
    process: ProcessPort,
    findings: list[Finding],
    data: dict[str, object],
    *,
    home: Path,
    slug: str,
    run_id: str,
    watched_pid: int,
    run_dir: Path,
    launched_via: str = "bmad-loop run",
) -> None:
    """Resolve the supervisor's 5 supplementary values (idle threshold plus
    Story 3.6's 4 budget ceilings) from the project-policy composition and
    spawn the detached sidecar with the standard 10-positional argv --
    extracted (Story 3.7) from ``run_spin``'s own original inline tail so
    ``run_resume`` shares this EXACT logic rather than a second, drifting
    copy; a pure extraction, ``run_spin``'s own behavior is unchanged.
    Mutates ``findings``/``data`` in place, mirroring every other step in
    this module's two launch verbs.

    ``launched_via`` (review finding) names the command that actually
    started ``watched_pid`` in ``MRS-SPIN-007``'s own message -- defaults to
    ``run_spin``'s own ``"bmad-loop run"``; ``run_resume`` passes
    ``"bmad-loop resume"`` so a supervisor-spawn failure after a RESUME
    never misreports itself as a fresh launch.

    Deliberately AFTER the caller's own launch outcome entry has been
    journaled (succeeded or not) -- see ``run_spin``'s own docstring for why
    the spawn stays last: everything before it can add findings to the same
    report, and a supervisor that attached before the outcome landed would
    interleave its own observation entries with this module's own append,
    two writers racing one journal file with no ordering guarantee between
    them."""
    supervisor_log = run_dir / _SUPERVISOR_LOG_FILENAME
    # Reported unconditionally, BEFORE the spawn attempt (review finding,
    # preserved from run_spin's own original tail): this file is the
    # detached supervisor's only diagnostic channel -- its stderr goes
    # nowhere else -- so an operator whose supervisor dies 60s later on an
    # unwritable journal needs the path whether or not the spawn itself
    # succeeded.
    data["supervisor_log"] = str(supervisor_log)

    # --- resolve idle_threshold_minutes for the supervisor's 6th argv -------
    # (Story 3.5, FR-12). Reads the SAME conventional project-policy layer
    # `marshal config` composes against -- a nonexistent file (the common
    # case in this repo's own test fixtures, and for any project with no
    # tuned overrides) composes against an empty project layer, landing on
    # `core.policy.DEFAULT_POLICY`'s own default (25). A read failure (a
    # corrupt or unreadable file) degrades the SAME way: this is a
    # supplementary numeric value for the supervisor's own soft ladder, not
    # a launch precondition, so it must never abort an otherwise-successful
    # harness launch the way a `--project-policy` read failure aborts
    # `marshal config` itself.
    project_policy_path = conventional_project_policy_path(slug)
    project_policy_data: Mapping[str, object] = {}
    if project_policy_path.is_file():
        try:
            project_policy_data = _read_project_policy(project_policy_path)
        except Exception:  # noqa: BLE001 -- deliberate, see below
            # BROAD on purpose (review finding), and the only broad except in
            # this module. This read is the LAST step on the post-launch
            # path: by the time it runs a real bmad-loop process is already
            # live and journalled, and the detached supervisor has not been
            # spawned yet. Anything that escapes here therefore leaves the
            # worst state this command can produce -- a running, UNSUPERVISED
            # harness -- and exits non-zero, which invites the caller to
            # retry and double-dispatch the very story the live run is
            # already working (the exact hazard this story's Design Notes
            # give as the reason `stop`+`resume` is the retry primitive).
            #
            # `PolicyIOError` alone was under-inclusive against this
            # module's own stated rule one comment up ("must never abort an
            # otherwise-successful harness launch"): `_read_project_policy`
            # translates the I/O and parse failures it anticipates, but
            # `tomllib.load` raises a bare `RecursionError` on a deeply
            # nested document, which is neither an `OSError` nor a
            # `ValueError` and so passed straight through. The value being
            # read is a supplementary tuning number for a soft ladder; no
            # failure to obtain it justifies abandoning a live run.
            project_policy_data = {}
    effective_policy, policy_findings = policy.compose(
        project_slug=slug, project=project_policy_data, flags={}
    )
    # Surfaced into this report -- but RE-TIERED, never extended verbatim
    # (review finding, two passes). The findings themselves must reach the
    # operator: this variable was once captured and never looked at again,
    # so a malformed `idle_threshold_minutes` override in the project's own
    # marshal-policy.toml silently fell back to the code default with zero
    # diagnostic. But splicing them in as-is was the opposite error:
    # MRS-POLICY-001/002/003/004/006 all classify `Verdict.UNEVALUABLE`
    # (exit 1), which is right for `marshal config` -- whose whole job IS
    # the policy -- and wrong here, where the policy is a supplementary
    # input read AFTER a real harness process is already live. Any unknown
    # key or malformed value ANYWHERE in the project's policy file would
    # have made `marshal factory spin` exit 1 over a successfully launched,
    # supervised run, and a caller that retries on non-zero would then
    # double-dispatch the same story -- the exact hazard this story's own
    # Design Notes give as the reason `stop`+`resume` is the retry
    # primitive. One WARN-tier MRS-SPIN-008 carries every underlying
    # message instead, preserving the diagnostic without inverting the
    # launch's own verdict.
    #
    # The wording says "every key a finding names", never "the threshold"
    # (follow-up review finding): `compose()` is called over the WHOLE 19-key
    # vocabulary, so an unknown key or a malformed `max_dev_attempts`
    # anywhere in the project's policy file lands here too -- and the earlier
    # text asserted, on every such launch, that the idle threshold had fallen
    # back to its default when it had not. A diagnostic that names the wrong
    # key sends the operator hunting a defect that is not there.
    if policy_findings:
        findings.append(
            Finding(
                code="MRS-SPIN-008",
                severity=Severity.WARN,
                message=(
                    "the project policy layer produced "
                    f"{len(policy_findings)} finding(s) while composing the "
                    "supervisor's idle threshold (the launch itself is "
                    "unaffected; every key a finding below names kept its "
                    "composed default instead of the project's own value): "
                    + "; ".join(
                        f"{finding.code}: {finding.message}"
                        for finding in policy_findings
                    )
                ),
            )
        )
    idle_threshold_minutes = effective_policy.seed_view()["idle_threshold_minutes"].value
    # Story 3.6's 4 budget-ceiling values -- resolved from the SAME
    # `effective_policy` composition idle_threshold_minutes above already
    # reads (never a second `compose()` call), and appended as argv
    # positionals 7-10, mirroring idle_threshold_minutes's own 6th-argv
    # wiring exactly.
    max_tokens_per_story = effective_policy.seed_view()["max_tokens_per_story"].value
    max_tokens_per_run = effective_policy.seed_view()["max_tokens_per_run"].value
    max_wall_clock_minutes_per_story = effective_policy.seed_view()[
        "max_wall_clock_minutes_per_story"
    ].value
    max_wall_clock_minutes_per_run = effective_policy.seed_view()[
        "max_wall_clock_minutes_per_run"
    ].value

    try:
        supervisor_pid = process.spawn_detached(
            [
                sys.executable,
                "-m",
                "pyforge.marshal.supervisor",
                str(home),
                slug,
                run_id,
                str(watched_pid),
                str(supervisor_log),
                str(idle_threshold_minutes),
                str(max_tokens_per_story),
                str(max_tokens_per_run),
                str(max_wall_clock_minutes_per_story),
                str(max_wall_clock_minutes_per_run),
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
                    # `supervisor_log` quoted at construction (review
                    # finding): `_render_text` deliberately does NOT quote
                    # finding MESSAGES -- its own comment states the split
                    # and requires "every message that interpolates an
                    # untrusted value quotes it at construction instead",
                    # which the `MRS-SPIN-001`/`002` sites above already do
                    # (`{slug!r}`, `{str(home)!r}`). This message shipped
                    # with a RAW path derived from `BMAD_LOOP_HOME_ROOT`,
                    # which `cli/init.py::_loop_home_root` reads unvalidated
                    # and only anchors to absolute -- so a newline in it
                    # forged whole lines of this report (a second
                    # `findings:` block, on a run that genuinely launched at
                    # rc=0), reintroducing on this story's own new finding
                    # exactly the defect a prior pass fixed for `--story`
                    # and raw feed keys.
                    f"{launched_via} launched (pid {watched_pid}) but its "
                    f"supervisor could not be spawned: {exc} -- the run "
                    f"continues unsupervised (supervisor log: "
                    f"{str(supervisor_log)!r})"
                ),
            )
        )
    else:
        data["supervisor_pid"] = supervisor_pid


def run_spin(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    harness: HarnessPort | None = None,
    process: ProcessPort | None = None,
    context: MarshalContext | None = None,
) -> int:
    # Story 5.6 (FR-65/AD-50): `context`, if `cli/main.py`'s dispatch
    # resolved one, is accepted but deliberately UNUSED here -- proving the
    # "resolved once at the front door" plumbing reaches this handler
    # without retrofitting its own internal policy/home-path derivation
    # (see this story's own Design Notes; `cli/main.py`'s module docstring
    # names the exact three already-shipped commands this applies to).
    del context
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

    # --- Story 3.6 FR-14: preflight advisory (MRS-SPIN-009) -----------------
    # Non-blocking: for each SELECTED story key, warn when its spec size or
    # prior-attempt history in THIS SAME loop home suggests it is likely to
    # exceed budget. Never changes `_emit`'s own exit-code handling beyond
    # the ordinary WARN-tier this command's other WARN findings already get
    # (MRS-SPIN-004/006/007/008); "declared difficulty" is deliberately not
    # an input (see the module docstring's own Never clause / the
    # deferred-work.md entry this story adds).
    #
    # Iterates `preview`, NOT `resolution.resolved` (review finding): the
    # advisory ran BEFORE `_filter_preview` and so warned about every story
    # in the feed, including the ones `--epic`/`--story`/`--max-count` had
    # already excluded from this launch -- up to N-1 WARN findings, and a
    # WARN verdict on the exit envelope, about work that will not run. The
    # acceptance criterion is "preflight warns when a SELECTED story is
    # likely to exceed the session budget"; only the filtered set is
    # selected.
    prior_attempts = _prior_attempt_keys(home) if preview else set()
    for key in preview:
        reasons: list[str] = []
        spec_size = _large_spec_bytes(home, slug, key)
        if spec_size >= _LARGE_SPEC_BYTES:
            reasons.append(f"spec size {spec_size} bytes >= {_LARGE_SPEC_BYTES}")
        if key in prior_attempts:
            reasons.append(
                "a prior run in this loop home recorded attempt >= 2 or a "
                "deferred/escalated outcome for this story"
            )
        if reasons:
            findings.append(
                Finding(
                    code="MRS-SPIN-009",
                    severity=Severity.WARN,
                    message=(
                        f"story {render_feed_key(key)!r} may exceed budget: "
                        + "; ".join(reasons)
                    ),
                )
            )

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
    _spawn_supervisor_sidecar(
        process,
        findings,
        data,
        home=home,
        slug=slug,
        run_id=run_id,
        watched_pid=spin_result.pid,
        run_dir=run_dir,
    )

    return _emit(args, data, findings)


def _latest_run_dir(home: Path, slug: str) -> Path | None:
    """The most recent Marshal run directory for ``slug`` under this loop
    home's Tier-3 store (``<tier3>/runs/<slug>-*``, sorted -- AD-25's own
    "sortable chronologically within a slug"), or ``None`` if none exists.
    A plain ``Path.glob``, not routed through ``FsPort`` (no directory-
    listing primitive exists on that port; adding one for this single,
    read-only caller would be disproportionate -- mirrors this module's own
    ``_prior_attempt_keys``/``_large_spec_bytes`` precedent, Story 3.6)."""
    runs_dir = _tier3_path(home, slug) / "runs"
    try:
        candidates = sorted(path for path in runs_dir.glob(f"{slug}-*") if path.is_dir())
    except OSError:
        return None
    return candidates[-1] if candidates else None


def _resolve_harness_run_id_for_resume(fs: FsPort, run_dir: Path, run_id: str) -> str | None:
    """``run_dir``'s own launch OUTCOME entry's ``harness_run_id`` field --
    the SAME lookup ``supervisor/__main__.py::_resolve_harness_run_id``
    performs, reproduced here rather than imported (this module already
    duplicates several of that module's own small, pure, private helpers
    across the identical AD-9 boundary -- e.g. ``_tier3_path``/``_run_dir``
    below). Checks BOTH ``_LAUNCH_KIND`` and ``_RESUME_KIND`` (a run this
    resume is chaining off of may itself have been minted by an earlier
    ``marshal factory resume``, whose own outcome entry carries the SAME
    field under the other kind) -- ``None`` if the journal cannot be read,
    or neither kind has a matching outcome entry with a real
    ``harness_run_id``."""
    try:
        text = fs.read_text(run_dir / _JOURNAL_FILENAME)
    except FsError:
        return None
    lines = text.split("\n") if text is not None else []
    fold_result = fold(lines)
    for kind in (_LAUNCH_KIND, _RESUME_KIND):
        for entry in fold_result.by_kind(kind):
            if entry.run_id != run_id or entry.phase is not Phase.OUTCOME:
                continue
            candidate = entry.payload.get("harness_run_id")
            if isinstance(candidate, str) and candidate:
                return candidate
    return None


def _render_story_key_best_effort(raw: str | None) -> str | None:
    """Marshal's own canonical dot form for a harness-native story key
    (``core.identity``'s own ``normalize``/``render_feed_key``), falling
    back to ``raw`` unchanged when it does not parse -- mirrors
    ``supervisor/__main__.py::_feed_key_form``'s identical convention and
    identical rationale (a key this package cannot normalize is still
    better attribution than none). ``None`` in, ``None`` out."""
    if raw is None:
        return None
    try:
        return render_feed_key(normalize(raw))
    except ValueError:
        return raw


def run_resume(
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

    # --- loop home + Tier-3 backlink must be provisioned ---------------------
    # A simplified restatement of run_spin's own identical checks (its own
    # extensively-commented block explains each individual failure mode this
    # mirrors -- MRS-SPIN-002 covers all of them, matching that function's
    # own single-code convention for "loop home not provisioned").
    try:
        home = _home_path(slug)
    except (RuntimeError, OSError) as exc:
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
    if tier3_target is None or not fs.is_dir(tier3_path):
        findings.append(
            Finding(
                code="MRS-SPIN-002",
                severity=Severity.ERROR,
                message=(
                    f"loop home Tier-3 backlink not provisioned or dangling: "
                    f"{str(tier3_path)!r} -- run 'marshal init {slug}' first"
                ),
                path=str(tier3_path),
            )
        )
        return _emit(args, data, findings)

    # --- find the most recent Marshal run for this slug ----------------------
    prior_run_dir = _latest_run_dir(home, slug)
    if prior_run_dir is None:
        findings.append(
            Finding(
                code="MRS-SPIN-011",
                severity=Severity.ERROR,
                message=(
                    f"no resumable run found for {slug!r} under "
                    f"{str(tier3_path / 'runs')!r}"
                ),
            )
        )
        return _emit(args, data, findings)
    prior_run_id = prior_run_dir.name
    data["resumed_from_run"] = prior_run_id

    harness_run_id = _resolve_harness_run_id_for_resume(fs, prior_run_dir, prior_run_id)
    if harness_run_id is None:
        findings.append(
            Finding(
                code="MRS-SPIN-011",
                severity=Severity.ERROR,
                message=(
                    f"run {prior_run_id!r}'s harness_run_id could not be "
                    "recovered from its own journal -- nothing to resume"
                ),
            )
        )
        return _emit(args, data, findings)
    data["harness_run_id"] = harness_run_id

    # --- live escalation-refusal gate (AD-45) --------------------------------
    # NEVER trusts the historical journal for the resolved/unresolved
    # question -- only for discovering which harness_run_id to check (the
    # spec's own Always bullet).
    status_snapshot = harness.run_status_snapshot(home, harness_run_id)
    if status_snapshot is None:
        # Review finding: a read/parse failure at exactly this live gate must
        # never be SILENT -- the gate's whole purpose is to positively
        # confirm the escalation is resolved before letting resume proceed,
        # and an unreadable state.json means it cannot. Mirrors AD-32's own
        # "a stale/unreadable sample degrades to a registered WARN, never a
        # silent pass" precedent for the budget ceilings' identical
        # ambiguity -- proceeding anyway (rather than refusing outright) so
        # a transient hiccup never makes the ordinary, never-escalated
        # resume newly unreliable.
        findings.append(
            Finding(
                code="MRS-SPIN-012",
                severity=Severity.WARN,
                message=(
                    f"could not read run {harness_run_id!r}'s live status -- "
                    "proceeding without confirming any escalation is resolved"
                ),
            )
        )
    elif status_snapshot.finished:
        # Follow-up review finding: `harness.resume` DETACHES (AD-22), so the
        # child's exit code is never visible here -- and `bmad-loop resume`'s
        # own first act is to refuse an already-finished run (`run <id>
        # already finished`, exit 1) AFTER starting normally. Without this
        # gate the command reported a pid, journaled a "run-resume" OUTCOME,
        # and spawned a supervisor for a resume that never happened -- a
        # clean-looking resume in an append-only EVIDENCE journal that is
        # simply false. Refused with MRS-SPIN-011, whose registered meaning
        # ("no resumable run") is exactly this: a finished run is not one.
        findings.append(
            Finding(
                code="MRS-SPIN-011",
                severity=Severity.ERROR,
                message=(
                    f"run {harness_run_id!r} already finished -- nothing to "
                    "resume"
                ),
            )
        )
        return _emit(args, data, findings)

    paused_stage = status_snapshot.paused_stage if status_snapshot is not None else None
    paused_story_key = (
        status_snapshot.paused_story_key if status_snapshot is not None else None
    )
    task_phase = (
        status_snapshot.escalated_task_phase if status_snapshot is not None else None
    )
    escalation_status = evaluate_escalation(paused_stage, paused_story_key, task_phase)
    if escalation_status is EscalationStatus.UNRESOLVED:
        findings.append(
            Finding(
                code="MRS-SPIN-010",
                severity=Severity.ERROR,
                message=(
                    f"resume refused: story {paused_story_key!r} is still "
                    "escalated and unresolved -- resolve it (e.g. "
                    "'bmad-loop resolve') before resuming"
                ),
            )
        )
        return _emit(args, data, findings)

    # Review finding: `paused_story_key` is a GENERIC field shared by every
    # bmad-loop pause reason (spec-approval, epic-boundary, a stories-mode
    # checkpoint, ...), not just escalation. Populating AD-45's back-
    # reference fields for any of those would produce a "run-resume" journal
    # entry that LOOKS like an escalation was resolved when nothing of the
    # sort happened. `EscalationStatus.RESOLVED` is exactly (and only) "this
    # pause WAS an escalation, and it no longer is" -- the one case AD-45's
    # fields describe.
    was_resolved_escalation = escalation_status is EscalationStatus.RESOLVED
    story_key = paused_story_key if was_resolved_escalation else None
    reason = (
        status_snapshot.paused_reason
        if status_snapshot is not None and was_resolved_escalation
        else None
    )
    spec_file = (
        status_snapshot.escalated_spec_file
        if status_snapshot is not None and was_resolved_escalation
        else None
    )
    resolution_reference = (
        harness.resolution_reference(home, harness_run_id, story_key)
        if story_key is not None
        else None
    )
    try:
        resolver = getpass.getuser()
    except (OSError, KeyError):
        # Realistic in a detached/headless automation context -- exactly
        # where `marshal factory resume` is meant to run (AD-22) -- when no
        # pwd entry exists and none of LOGNAME/USER/LNAME/USERNAME is set.
        # AD-45's own attribution is already "attributable, not
        # authenticated" (AD-27/F-4); an unresolvable identity is simply
        # another unattested value, never a reason to crash the command.
        resolver = None
    rendered_story_key = _render_story_key_best_effort(story_key)
    if rendered_story_key is not None:
        data["story_key"] = rendered_story_key
    if resolution_reference is not None:
        # Conditional, exactly like `story_key` above (follow-up review
        # finding): the overwhelmingly common resume is an ordinary,
        # never-escalated one, where a bare `resolution_reference: null`
        # line reports on a field that has no meaning outside a resolved
        # escalation -- and made `_render_text`'s own `"resolution_reference"
        # in data` guard dead as a discriminator. The JOURNAL payload below
        # still carries the field unconditionally (AD-45 names it as one of
        # its four, and an explicit `null` there is the evidence record's own
        # "asked, and there was none").
        data["resolution_reference"] = resolution_reference

    # --- mint a NEW Marshal run id, journal "run-resume" intent (AD-25/AD-45) ---
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

    intent_id = JournalEntryId(writer_id, 0)
    intent_entry = build_entry(
        id=intent_id,
        ts=_format_entry_ts(mint_moment),
        run_id=run_id,
        kind=_RESUME_KIND,
        phase=Phase.INTENT,
        payload={
            "resumed_from_run": prior_run_id,
            "harness_run_id": harness_run_id,
            "story_key": rendered_story_key,
            "reason": reason,
            "spec_file": spec_file,
            "resolution_reference": resolution_reference,
            "resolver": resolver,
        },
    )
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-SPIN-003",
                severity=Severity.ERROR,
                message=f"cannot journal the resume intent: {exc}",
            )
        )
        return _emit(args, data, findings)

    # --- the detached resume itself -------------------------------------------
    log_path = run_dir / _LOG_FILENAME
    data["log"] = str(log_path)
    try:
        pid = harness.resume(home, harness_run_id, log_path=log_path)
    except HarnessError as exc:
        findings.append(
            Finding(
                code="MRS-SPIN-003",
                severity=Severity.ERROR,
                message=f"cannot launch bmad-loop resume: {exc}",
            )
        )
        # AD-6: the attempt is journaled as a FAILED outcome, never as a
        # successful launch -- run id and directory already exist by this
        # point, so the failure must still be recorded against them.
        outcome_entry = build_entry(
            id=JournalEntryId(writer_id, 1),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind=_RESUME_KIND,
            phase=Phase.OUTCOME,
            intent_id=intent_id,
            payload={"pid": None, "harness_run_id": None, "error": str(exc)},
        )
        try:
            _append_entry(fs, run_dir, outcome_entry, fsync=False)
        except FsError:
            pass
        return _emit(args, data, findings)

    data["pid"] = pid

    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, 1),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=_RESUME_KIND,
        phase=Phase.OUTCOME,
        intent_id=intent_id,
        payload={"pid": pid, "harness_run_id": harness_run_id},
    )
    try:
        _append_entry(fs, run_dir, outcome_entry, fsync=False)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-SPIN-006",
                severity=Severity.WARN,
                message=(
                    f"bmad-loop resume launched (pid {pid}) but its "
                    f"outcome could not be journaled: {exc}"
                ),
            )
        )

    # --- spawn a fresh supervisor sidecar -- the LAST step (Story 3.4, AD-9) ---
    _spawn_supervisor_sidecar(
        process,
        findings,
        data,
        home=home,
        slug=slug,
        run_id=run_id,
        watched_pid=pid,
        run_dir=run_dir,
        launched_via="bmad-loop resume",
    )

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


def _render_text(
    data: Mapping[str, object], findings: tuple[Finding, ...], command: str = "factory spin"
) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14), matching every sibling command's
    own ``_render_text`` convention. ``command`` (Story 3.7) is the same
    envelope-command string ``_emit`` derives -- ``run_resume`` shares this
    function with ``run_spin`` rather than a second copy, so it must not
    hardcode "factory spin" as its own header line."""
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
    lines = [f"{command}: {_scalar(data['slug'])}"]
    if "home" in data:
        lines.append(f"home: {_scalar(str(data['home']))}")
    if "resumed_from_run" in data:
        lines.append(f"resumed_from_run: {_scalar(data['resumed_from_run'])}")
    if "story_key" in data:
        lines.append(f"story_key: {_scalar(data['story_key'])}")
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
    if "resolution_reference" in data:
        lines.append(f"resolution_reference: {_scalar(data['resolution_reference'])}")
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
    # `args.factory_command` is the subparsers `dest` (Story 3.7:
    # "spin"/"resume") -- defaulted to "spin" for every test in this module
    # that hand-builds an `argparse.Namespace` and calls `run_spin` directly,
    # bypassing `add_factory_subparser` entirely (this module's own existing
    # convention, predating this story).
    command = f"factory {getattr(args, 'factory_command', 'spin')}"
    verdict_value = compute_verdict(tuple(findings))
    envelope = build_envelope(
        command=command, verdict=verdict_value, data=data, findings=tuple(findings)
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
            print(_render_text(envelope.data, envelope.findings, command), flush=True)
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
