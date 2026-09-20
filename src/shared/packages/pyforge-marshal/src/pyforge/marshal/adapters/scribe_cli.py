"""THE ONLY module permitted to invoke the ``scribe`` CLI (Story 28.8,
SPEC-marshal-token-economy CAP-5; Story 28.9 CAP-6 extends with ``recall``)
-- the same sole-ownership discipline ``adapters/harness_bmadloop.py`` has
for ``bmad-loop`` and ``adapters/harness_bmadbuild.py`` has for a
session-harness CLI.

The ``derived-context`` layer's freshness engine is Scribe's
``compile_surface`` cocoindex extra (scribe Story 6.2). The
``planning-graph`` layer's retrieval engine is Scribe's ``recall`` grammar
(scribe Story 2.4/6.3 -- stale nodes never surface). Marshal binds both
through the scribe CLI grammar that station's SKILL.md declares -- never
``import cocoindex`` or ``import graphify`` (these stories' Block-If),
never ``import pyforge.scribe`` (that SKILL's own "the CLI is the public
contract; do not import pyforge.scribe internals"). Everything
subprocess-shaped for those bindings lives here and only here: binary
probing across ``PATH`` plus the repo's pixi env bin dirs, the bounded
invocation, and turning a failure into a REASON rather than an exception.

**Every failure degrades; none blocks.** SPEC-marshal-token-economy's own
constraint is "an unavailable instrument disables its layer with a named
finding, never blocks a run", and this story's ACs require the layer-off
fallback (today's compile-on-hunch behavior) to be the proven degradation
target. So a missing ``scribe`` binary, a scribe whose ``index refresh``
does not accept caller declarations, a non-zero exit, a launch failure, a
timeout, and an unparseable report ALL return
``ScribeRefreshOutcome(ok=False, reason=...)``. The caller reports the
reason as a WARN finding and falls back; nothing here raises.

**Why the caller-declaration grammar can be absent.** Scribe 6.2 shipped
the generic "declare sources -> derived artifact" ENGINE
(``DerivedArtifact``/``refresh_incremental``) and wired its own two
registrations into ``scribe index refresh``; its Design Notes name marshal
Story 28.8 as the next consumer to "register its epic-context/continuity
distills against the same grammar", and its SKILL.md tells that consumer to
bind "to this ``scribe index refresh``-shaped CLI grammar only". The
caller-declaration option itself is scribe-side surface that had not landed
when this story was implemented, and marshal may not add it (this story is
the CONSUMER side; the producer is scribe's). Rather than guess, this
adapter treats "the shipped scribe did not accept the declaration" as one
more ordinary degradation -- so marshal lights up with zero further change
the moment scribe exposes it, and until then the layer is visibly, named-ly
off instead of silently wrong. The dependency is recorded in the story
record and the deferred-work ledger.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from ..core.derived_context import parse_refresh_report, render_scribe_refresh_argv
from ..core.planning_graph import parse_recall_output, render_scribe_recall_argv

__all__ = (
    "SCRIBE_BINARY",
    "SCRIBE_FALLBACK_BIN_DIRS",
    "ScribeCli",
    "ScribeRecallOutcome",
    "ScribeRefreshOutcome",
)

#: The console script ``pyforge-scribe`` installs
#: (``scribe = pyforge.scribe.cli:main``).
SCRIBE_BINARY = "scribe"

#: Repo-root-relative directories probed after ``PATH``. The pixi-env CLIs
#: are invisible to a bare operator ``PATH`` -- the same honest-probing
#: reason ``adapters/harness_bmadbuild.py::_resolve_binary`` gives, and the
#: same shape the packaged harness profiles' own ``fallback_bin_dirs``
#: use. ``pyforge-scribe`` first (its own env), then the Guild default --
#: the only env that exists at runtime (Story 46.12, spec-pyforge-marshal
#: CAP-263; `local-recipes` is the recipe factory, never a runtime).
SCRIBE_FALLBACK_BIN_DIRS: tuple[str, ...] = (
    ".pixi/envs/pyforge-scribe/bin",
    ".pixi/envs/pyforge-guild/bin",
)

#: Ceiling for one refresh. The declared work is stat-only fingerprinting
#: over a handful of planning documents, so this is generous; it exists to
#: bound a wedged or prompting CLI, never to cut short real work.
_REFRESH_TIMEOUT_S = 120.0
_RECALL_TIMEOUT_S = 60.0


@dataclass(frozen=True)
class ScribeRecallOutcome:
    """What one ``scribe recall`` invocation produced.

    ``ok`` is true ONLY when the grammar ran and its output parsed --
    every other shape is ``ok=False`` with a human ``reason``. ``grounded``
    is meaningful only when ``ok`` is true; a miss (including stale-only
    candidates excluded by scribe Story 6.3) is ``grounded=False`` with
    ``ok=True`` -- the consumer falls back to epic-context files."""

    ok: bool
    grounded: bool = False
    text: str = ""
    citation: str | None = None
    reason: str | None = None
    argv: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ScribeRefreshOutcome:
    """What one ``scribe index refresh`` invocation produced.

    ``ok`` is true ONLY when the grammar ran and its report line parsed --
    every other shape (binary absent, non-zero exit, launch failure,
    timeout, unparseable output) is ``ok=False`` with a human ``reason``
    naming what happened. ``refreshed``/``skipped`` are the artifact names
    the extra reported, verbatim; mapping them back onto declarations is
    ``core/derived_context.py::resolve_freshness``'s pure job, never this
    adapter's."""

    ok: bool
    refreshed: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    reason: str | None = None
    argv: tuple[str, ...] = field(default_factory=tuple)


class ScribeCli:
    """The scribe-CLI seam. ``process`` is injectable so tests drive the
    grammar through a fake ``ProcessPort`` without a real scribe install --
    the same DI idiom every other adapter in this package uses."""

    def __init__(self, process: ProcessPort | None = None) -> None:
        self._process: ProcessPort = process if process is not None else PosixProcess()

    def resolve_binary(
        self,
        repo_root: Path | None = None,
        *,
        fallback_bin_dirs: Sequence[str] = SCRIBE_FALLBACK_BIN_DIRS,
    ) -> str | None:
        """``PATH`` first, then the repo-relative fallback dirs. ``None``
        when scribe does not resolve anywhere."""
        on_path = shutil.which(SCRIBE_BINARY)
        if on_path is not None:
            return on_path
        if repo_root is None:
            return None
        for rel_dir in fallback_bin_dirs:
            candidate = Path(repo_root) / rel_dir / SCRIBE_BINARY
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        return None

    def refresh(
        self,
        *,
        repo_root: Path,
        manifest_path: Path,
        binary_path: str | None = None,
    ) -> ScribeRefreshOutcome:
        """Run the declared grammar over ``manifest_path`` and return what
        the extra reported. Never raises.

        ``cwd`` is ``repo_root``: the scribe CLI's own documented contract
        is "run from the repository root (never a hardcoded absolute
        path)", and its fingerprint index and derived artifacts are all
        resolved relative to that root."""
        resolved = binary_path if binary_path is not None else self.resolve_binary(repo_root)
        if resolved is None:
            return ScribeRefreshOutcome(
                ok=False,
                reason=(
                    f"the {SCRIBE_BINARY!r} CLI did not resolve on PATH or in "
                    f"{list(SCRIBE_FALLBACK_BIN_DIRS)!r} -- the derived-context "
                    "layer is off for this iteration and today's "
                    "compile-on-hunch behavior applies"
                ),
            )
        argv = render_scribe_refresh_argv(resolved, str(manifest_path))
        try:
            result = self._process.run(argv, cwd=Path(repo_root), timeout_s=_REFRESH_TIMEOUT_S)
        except ProcessError as exc:
            return ScribeRefreshOutcome(
                ok=False,
                argv=argv,
                reason=(
                    f"the scribe refresh grammar {list(argv)!r} could not run "
                    f"({exc}) -- the derived-context layer is off for this "
                    "iteration and today's compile-on-hunch behavior applies"
                ),
            )
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            tail = output.strip().splitlines()[-1] if output.strip() else "<no output>"
            return ScribeRefreshOutcome(
                ok=False,
                argv=argv,
                reason=(
                    f"the scribe refresh grammar {list(argv)!r} exited "
                    f"{result.returncode} ({tail}) -- the installed scribe may "
                    f"not accept caller-declared artifacts yet; the "
                    "derived-context layer is off for this iteration and "
                    "today's compile-on-hunch behavior applies"
                ),
            )
        parsed = parse_refresh_report(output)
        if parsed is None:
            return ScribeRefreshOutcome(
                ok=False,
                argv=argv,
                reason=(
                    f"the scribe refresh grammar {list(argv)!r} exited 0 but "
                    "printed no 'refreshed: ...; skipped (unchanged): ...' "
                    "report -- the derived-context layer is off for this "
                    "iteration and today's compile-on-hunch behavior applies"
                ),
            )
        refreshed, skipped = parsed
        return ScribeRefreshOutcome(ok=True, refreshed=refreshed, skipped=skipped, argv=argv)

    def recall(
        self,
        *,
        repo_root: Path,
        query: str,
        scope: str | None = None,
        binary_path: str | None = None,
    ) -> ScribeRecallOutcome:
        """Run the declared ``scribe recall`` grammar and return what it
        reported. Never raises."""
        resolved = binary_path if binary_path is not None else self.resolve_binary(repo_root)
        if resolved is None:
            return ScribeRecallOutcome(
                ok=False,
                reason=(
                    f"the {SCRIBE_BINARY!r} CLI did not resolve on PATH or in "
                    f"{list(SCRIBE_FALLBACK_BIN_DIRS)!r} -- the planning-graph "
                    "layer is off for this iteration and Story 28.8's "
                    "epic-context-file fallback applies"
                ),
            )
        argv = render_scribe_recall_argv(resolved, query, scope=scope)
        try:
            result = self._process.run(argv, cwd=Path(repo_root), timeout_s=_RECALL_TIMEOUT_S)
        except ProcessError as exc:
            return ScribeRecallOutcome(
                ok=False,
                argv=argv,
                reason=(
                    f"the scribe recall grammar {list(argv)!r} could not run "
                    f"({exc}) -- the planning-graph layer is off for this "
                    "iteration and Story 28.8's epic-context-file fallback "
                    "applies"
                ),
            )
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            tail = output.strip().splitlines()[-1] if output.strip() else "<no output>"
            return ScribeRecallOutcome(
                ok=False,
                argv=argv,
                reason=(
                    f"the scribe recall grammar {list(argv)!r} exited "
                    f"{result.returncode} ({tail}) -- the planning-graph "
                    "layer is off for this iteration and Story 28.8's "
                    "epic-context-file fallback applies"
                ),
            )
        parsed = parse_recall_output(output)
        return ScribeRecallOutcome(
            ok=True,
            grounded=parsed.grounded,
            text=parsed.text,
            citation=parsed.citation,
            argv=argv,
        )
