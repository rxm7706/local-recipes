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
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


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
