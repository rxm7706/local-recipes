"""``HarnessPort`` -- the seam ``cli/init.py``'s ``run_preflight`` depends on
(Story 1.7, architecture spine AD-11/AD-19). A Protocol definition only
(Structural Seed: ``ports/`` declares shapes, never implementations);
implemented solely by ``adapters/harness_bmadloop.py`` (AD-3: the only
module permitted to invoke the ``bmad-loop`` binary or import its package).
Not an egress port: every check stays local to this host.

Seven methods, each a thin seam over one piece of the installed ``bmad_loop``
package's own detection/profile/config surface (FR-52: one seam, never a
second independent notion of any of these facts):

- ``binary_present`` -- the ONE generic ``shutil.which``-backed presence
  primitive, shared by the harness binary itself (``"bmad-loop"``), the
  resolved adapter binary, and each verify command's first token (no
  adapter-specific branching, per the spec's own Always bullet). Never
  raises.
- ``harness_version`` -- issues the single sanctioned ``bmad-loop --version``
  subprocess call (never the adapter's own CLI); ``None`` on any failure
  (binary absent, non-zero exit, timeout, unparseable output). Never raises.
- ``multiplexer_backend_available`` -- ``(backend_name, available)`` for the
  multiplexer ``bmad_loop.adapters.multiplexer.detect_multiplexers`` would
  select. Raises ``HarnessError`` only if ``bmad_loop`` itself is not
  importable.
- ``adapter_binary``/``adapter_seed_files``/``adapter_first_run_note`` --
  each one field of the adapter's declarative ``CLIProfile``
  (``bmad_loop.adapters.profile.get_profile``, packaged TOML overlaid by the
  project's own ``.bmad-loop/profiles/*.toml``). Raise ``HarnessError`` for
  an unknown adapter name or an unimportable ``bmad_loop``.
- ``story_feed_error`` -- ``None`` when ``project``'s configured
  ``sprint-status.yaml`` resolves and parses, else the harness's own error
  text (never raises -- the message text IS the return value FR-52 needs).

Beyond the Code Map's plain enumeration (``binary_present``,
``harness_version``, ``multiplexer_backend_available``,
``adapter_seed_files``, ``adapter_first_run_note``, ``story_feed_error``):
``adapter_binary`` is added because the intent-contract's own ``adapter``
data field requires ``binary_present`` for the adapter's REAL binary (e.g.
``agy`` for the ``antigravity`` profile, ``opencode`` for
``opencode-http`` -- name and binary diverge for two of the six packaged
profiles), and the generic ``binary_present`` primitive must stay a dumb
PATH check with no adapter-specific branching -- so resolving the binary
NAME needs its own seam, symmetric with ``adapter_seed_files``/
``adapter_first_run_note``.

Story 3.3 (``marshal factory spin``/``attach``, FR-9/FR-17, AD-3/AD-22/
AD-25/AD-38) adds four more methods -- the first ones that actually LAUNCH
the harness rather than merely probing it:

- ``story_feed_keys`` -- the raw, pre-parse population of story references
  in ``project``'s configured feed (bmad_loop's ``SprintStatus.stories[*].key``
  UNION ``unknown_keys`` -- each group in the feed's own file order, the two
  groups concatenated rather than interleaved back together, since
  re-deriving a true file-order interleaving would need a second
  independent parse of the raw YAML, exactly what FR-52 forbids), independent
  of Marshal's own
  ``core.identity.normalize()`` -- AD-38's ``M`` (the denominator of
  "resolved N of M") must be counted before any parsing this package does,
  or a silently-dropped key would report a false "N of N" (see
  ``core/identity.py``'s own ``resolve_feed`` docstring). Callers are
  expected to check ``story_feed_error`` first; this method still raises
  ``HarnessError`` (never silently degrades to an empty tuple, which would
  misreport a real read failure as "zero non-empty records" -- AD-8) for
  any failure a caller reaches it despite that gate (a TOCTOU window, or a
  caller that skips the gate).
- ``spin`` -- the ONE detached-launch primitive (AD-3, AD-22): builds
  ``["bmad-loop", "run"]`` plus ``--epic``/``--story``/``--max-stories``
  when given, launches it detached (new session, ``stdin`` closed, both
  streams redirected to ``log_path``), and returns immediately without
  waiting -- never blocks the invoking shell. Also makes a bounded,
  best-effort attempt to read the harness's own self-minted run id back out
  of that redirected log (``bmad-loop run``'s own ``"run {id} starting"``
  line) so it can be recorded as the ``harness_run_id`` correlation field
  (AD-25) -- degrading to ``None`` if the window elapses first, never
  hanging the caller. Raises ``HarnessError`` only when the process could
  not be LAUNCHED at all.
- ``attach`` -- execs ``bmad-loop attach``, inheriting this process's own
  stdio (interactive by design -- it hands the terminal to the
  multiplexer), blocks until it exits, and returns its exit code, normalized
  for a signal-killed child (the shell's ``128 + N`` convention -- a raw
  negative ``returncode`` would be OS-truncated by ``sys.exit``). Callers
  that surface it to a shell project it further through
  ``core.verdict.relay_exit_code``; see ``cli/spin.py``.
  Raises ``HarnessError`` only when the process could not be LAUNCHED at
  all -- the SAME split ``spin`` uses, deliberately distinct from every
  OTHER method on this Protocol, which never raises for anything but an
  unimportable ``bmad_loop`` or a resolution failure (see
  ``ports/process.py::ProcessPort.run``'s identical convention, which this
  mirrors: a non-zero exit is the ordinary, expected shape here, never an
  exceptional one).
- ``run_foreground`` -- beyond the Code Map's own literal three-method
  enumeration, for the same reason ``adapter_binary`` was added above it:
  the spec's own Always bullet requires ``--foreground`` to call "a
  synchronous, stdio-inheriting HarnessPort path INSTEAD OF the detached
  one" (explicitly two distinct paths) and "relay its exit code" --
  language ``spin``'s own always-detached, always-``SpinResult``-returning
  contract cannot satisfy no matter how it is called. Mirrors ``attach``'s
  shape exactly (inherits stdio, blocks, returns the real exit code, raises
  ``HarnessError`` only on a launch failure) but drives ``bmad-loop run``
  instead of ``bmad-loop attach``, with the SAME ``--epic``/``--story``/
  ``--max-stories`` selector flags ``spin`` accepts. AD-3 requires every
  invocation of ``bmad-loop run`` -- detached or foreground alike -- to
  funnel through this one module; a second, CLI-side subprocess call would
  violate that as surely as skipping the seam entirely.

Story 3.5 (idle-strand detection, AD-9/AD-20) adds two more methods --
``stop``/``resume``, the supervisor's own ``stop-and-retry`` ladder rung
primitive, confirmed live as the one intended, supported pairing for
recovering an unresponsive engine: ``stop`` synchronously halts it (SIGTERM,
then force-kill, tearing down its tmux session) and ``resume`` detach-
launches a fresh engine attempt against the SAME ``run_id``, which
re-derives its own state and self-clears any stale session left behind.
Both share ``run_id`` naming the HARNESS's own self-minted run id, never
Marshal's own journal ``run_id`` -- see each method's own docstring.

Story 3.6 (budget ceilings, AD-9/AD-32, FR-13) adds ``usage_snapshot`` --
the "adapter-reported usage read from files the session wrote" AD-9's own
docstring already names, and AD-32's own carve-out: session-authored usage
is read for REPORTING and cost attribution only, never as an enforcement
ceiling's stop condition (that half rests solely on wall-clock/process-
liveness, evaluable without this method at all -- see
``core/supervise.py::evaluate_ceiling``). Reads ``bmad_loop``'s own
``state.json`` (``bmad_loop.journal.load_state``, the SAME lazy-import seam
``multiplexer_backend_available``/``adapter_binary`` already use) and never
raises -- any read/parse failure (a missing file, malformed JSON, a
missing/wrong-typed field) degrades to ``None``, mirroring
``harness_version``'s own "never raises" convention: a usage read is a
supplementary, best-effort input, never a precondition an enforcement
decision can block on.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SpinResult:
    """The result of a detached ``HarnessPort.spin`` launch (Story 3.3,
    AD-25): mirrors ``ports/process.py``'s ``ProcessResult`` -- a plain,
    frozen value type carrying only facts the caller could not have known in
    advance. ``pid`` is the spawned process's OS process id (always known --
    a constructed ``SpinResult`` always represents a launch that actually
    started; a launch that could not start raises ``HarnessError`` instead
    and never produces one). ``harness_run_id`` is the harness's own
    self-minted run identifier, recovered from its redirected log within a
    bounded poll window, or ``None`` when that window elapsed first without
    a match -- never used as a key, a path segment, or a grouping field
    (AD-25); it is a plain correlation fact for the journal's ``outcome``
    entry."""

    pid: int
    harness_run_id: str | None


@dataclass(frozen=True)
class UsageSnapshot:
    """One tick's worth of adapter-reported usage (Story 3.6, AD-9/AD-32) --
    a plain, frozen value type ``HarnessPort.usage_snapshot`` returns,
    mirroring ``SpinResult``'s own "facts the caller could not have known in
    advance" convention. ``story_key`` is the sole ``StoryTask`` with
    ``not task.terminal`` in bmad-loop's own ``state.json``, or ``None``
    when zero or more than one such task exists (the run is between
    stories, or -- a shape this story's own Never clause does not rule out
    -- concurrently driving more than one; either way there is no single
    story to attribute per-story consumption to this tick).
    ``story_weighted_tokens`` is ``None`` in lockstep with ``story_key``
    (never a number attributed to "no story"); when ``story_key`` is set it
    is that task's own ``TokenUsage.weighted_total(cache_read_weight)``.
    ``run_weighted_tokens`` is the run-wide sum of that SAME weighted total
    across every task in ``RunState.tasks`` (terminal and non-terminal
    alike -- a completed story's consumption still counted against the
    run's own ceiling). ``sample_path`` is the ``state.json`` path this
    snapshot was read from, for a caller that wants to independently check
    its own freshness via ``SessionObserverPort.mtime`` -- never a freshness
    notion this dataclass carries itself.

    Corrected (review finding): the wording here used to claim Story 3.6's
    staleness gate consumes this field. It does not -- ``supervisor/
    __main__.py`` recomputes the same path from ``home``/``harness_run_id``,
    because it must stat the sample even on a tick where ``usage_snapshot``
    returned ``None`` and there is no snapshot to read a path off. The two
    derivations are a genuine duplication, now pinned by
    ``tests/meta/test_supervisor_run_path_agreement.py`` (a divergence would
    otherwise make every sample look permanently stale, silently disabling
    both token ceilings for a run's whole life behind nothing but a WARN)."""

    story_key: str | None
    story_weighted_tokens: int | None
    run_weighted_tokens: int
    sample_path: Path


class HarnessPort(Protocol):
    def binary_present(self, binary: str) -> bool:
        """``True`` iff ``binary`` resolves on ``PATH``. Never raises."""
        ...

    def harness_version(self) -> str | None:
        """The installed ``bmad-loop``'s version string (e.g. ``"0.9.0"``),
        or ``None`` if it cannot be determined (binary absent, the
        ``--version`` subprocess call fails or times out, or its output is
        unparseable). Never raises."""
        ...

    def multiplexer_backend_available(self) -> tuple[str, bool]:
        """``(backend_name, available)`` for the multiplexer backend the
        harness would select (env var / policy / platform-default /
        first-match / fallback precedence, entirely the harness's own).
        Raises ``HarnessError`` only when ``bmad_loop`` itself cannot be
        imported."""
        ...

    def adapter_binary(self, adapter_name: str, project: Path) -> str:
        """The configured adapter's CLI binary name (e.g. ``"claude"``,
        ``"agy"`` for the ``antigravity`` profile). Raises ``HarnessError``
        for an unknown ``adapter_name`` or an unimportable ``bmad_loop``."""
        ...

    def adapter_seed_files(self, adapter_name: str, project: Path) -> tuple[str, ...]:
        """The adapter's declared gitignored config paths (project-relative,
        e.g. ``".mcp.json"``) that a fresh worktree lacks. Raises
        ``HarnessError`` for an unknown ``adapter_name`` or an unimportable
        ``bmad_loop``."""
        ...

    def adapter_first_run_note(self, adapter_name: str, project: Path) -> str:
        """The adapter's first-run trust-dialog instructions (``""`` if the
        profile declares none). Raises ``HarnessError`` for an unknown
        ``adapter_name`` or an unimportable ``bmad_loop``."""
        ...

    def story_feed_error(self, project: Path) -> str | None:
        """``None`` if ``project``'s configured ``sprint-status.yaml``
        resolves and parses; otherwise the harness's own error text (a
        missing config, a missing feed file, or invalid YAML/shape). Never
        raises."""
        ...

    def story_feed_keys(self, project: Path) -> tuple[str, ...]:
        """The RAW, pre-parse population of story references in
        ``project``'s configured feed (bmad_loop's own
        ``SprintStatus.stories[*].key`` UNION ``unknown_keys``, in file
        order) -- AD-38's ``M``, independent of ``core.identity.normalize()``.
        Callers should check ``story_feed_error`` first; raises
        ``HarnessError`` for any failure (an unimportable ``bmad_loop``, an
        unresolvable config, or an unparseable feed) reached despite that
        gate."""
        ...

    def spin(
        self,
        project: Path,
        *,
        epic: int | None,
        story: str | None,
        max_count: int | None,
        log_path: Path,
    ) -> SpinResult:
        """Detach-launch ``bmad-loop run`` against ``project`` (``--epic``/
        ``--story``/``--max-stories`` appended when given), redirecting both
        streams to ``log_path`` and closing stdin -- new session, never
        waited on, returns as soon as the process starts. Makes a bounded,
        best-effort attempt to recover the harness's own self-minted run id
        from ``log_path`` before returning; ``SpinResult.harness_run_id`` is
        ``None`` if that window elapses first. Raises ``HarnessError`` only
        when the process could not be LAUNCHED at all (missing binary, a
        launch-time ``OSError``) -- distinct from every other method on this
        Protocol except ``attach``/``run_foreground``, which share this
        convention."""
        ...

    def attach(self, project: Path) -> int:
        """Exec ``bmad-loop attach`` against ``project``, inheriting this
        process's own stdio, and return its exit code once it exits --
        interactive by design; hands the terminal to the multiplexer. Raises
        ``HarnessError`` only when the process could not be LAUNCHED at all."""
        ...

    def run_foreground(
        self,
        project: Path,
        *,
        epic: int | None,
        story: str | None,
        max_count: int | None,
    ) -> int:
        """Run ``bmad-loop run`` against ``project`` (the SAME selector flags
        ``spin`` accepts) synchronously, inheriting this process's own stdio,
        and return its exit code once it exits -- the ``--foreground``
        counterpart to ``spin``'s always-detached launch. Raises
        ``HarnessError`` only when the process could not be LAUNCHED at
        all."""
        ...

    def stop(self, project: Path, run_id: str) -> bool:
        """The idle ladder's ``stop-and-retry`` first half (Story 3.5,
        AD-9/AD-20): synchronously run ``bmad-loop stop <run_id>`` against
        ``project`` (``run_id`` is the HARNESS's own self-minted run id --
        ``SpinResult.harness_run_id``/the run-launch outcome entry's field of
        the same name -- never Marshal's own journal ``run_id``). Confirmed
        live as the intended hard-stop primitive against an unresponsive
        engine: it SIGTERMs then force-kills the engine and tears down its
        tmux session, needing no cooperation from the target. ``True`` iff
        the stop itself succeeded (the exit code the installed 0.9.0
        ``cmd_stop`` reports for "stopped"); ``False`` for any other
        determinable outcome (e.g. the run had already finished) -- NOT an
        exceptional shape, the same "a non-zero/negative result is the
        ordinary answer" split every other method on this Protocol not
        documented to raise for it uses. Raises ``HarnessError`` only when
        the process could not be LAUNCHED (or run to completion) at all,
        mirroring ``spin``'s own convention."""
        ...

    def resume(self, project: Path, run_id: str, *, log_path: Path) -> int:
        """The idle ladder's ``stop-and-retry`` second half (Story 3.5,
        AD-9/AD-20): detach-launch ``bmad-loop resume <run_id>`` against
        ``project`` (the SAME ``run_id`` ``stop`` was given), redirecting
        both streams to ``log_path`` and closing stdin -- new session, never
        waited on, mirroring ``spin``'s own detached-launch recipe exactly
        (this is a resumed engine run, which the installed 0.9.0
        ``_resume_paused_run`` drives exactly like a fresh ``bmad-loop run``
        -- synchronous and unbounded in the child, so it must never be
        waited on here either). Confirmed live as the intended recovery
        primitive: it re-derives the run's state from ``run_id`` alone and
        self-clears any stale tmux session left behind by ``stop``, so it
        needs no other input from this call. ``log_path`` is APPENDED to,
        never truncated (review finding): unlike ``spin``'s own brand-new
        log, the file this method is given is the WEDGED run's existing
        ``harness.log``, whose accumulated content is the only evidence of
        why the run stopped producing output -- and a one-line boundary
        marker is written ahead of the resumed child's own output (review
        finding), so the two attempts' streams are separable rather than
        byte-concatenated. Returns the newly spawned process's pid. Raises ``HarnessError`` only when the process could
        not be LAUNCHED at all -- the SAME split ``spin``/``attach``/
        ``run_foreground`` share."""
        ...

    def usage_snapshot(self, project: Path, run_id: str) -> UsageSnapshot | None:
        """The current per-story/per-run token consumption bmad-loop's own
        ``state.json`` reports for the run ``run_id`` names (Story 3.6,
        AD-9/AD-32) -- ``run_id`` is the HARNESS's own self-minted run id,
        the SAME one ``stop``/``resume`` take, never Marshal's own journal
        ``run_id``. Never raises: any failure reading or parsing
        ``<project>/.bmad-loop/runs/<run_id>/state.json`` (a missing file, a
        malformed JSON document, a missing or wrong-typed field) returns
        ``None`` -- this is a supplementary, best-effort reporting input
        (AD-32: "recorded for reporting and cost attribution only"), never a
        precondition an enforcement ceiling can block on."""
        ...
