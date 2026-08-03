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
  UNION ``unknown_keys``, file order), independent of Marshal's own
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
  multiplexer), blocks until it exits, and returns its exit code verbatim.
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
