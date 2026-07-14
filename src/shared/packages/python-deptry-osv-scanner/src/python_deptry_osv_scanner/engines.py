"""Engine registry + the null engine + the deptry engine (Stories 1.2/1.3).

OWNERSHIP DECISION (recorded): ``engines.py`` is the package's ONLY
subprocess-capable module — the sole subprocess site. Every engine call goes
through ``_engine_env()``, the load-bearing subprocess-normalization seam
(argv **list**, machine output forced to a ``tempfile.mkstemp`` file in
SYSTEM temp — never the scanned tree, ``NO_COLOR=1``, ``stdin=DEVNULL``,
bounded timeout, explicit utf-8 decode → typed ``ErrorRecord``, temp cleanup
on success AND failure). Story 1.5's osv-scanner runner reuses ``_engine_env``
verbatim.

Registry semantics: engines register via ``register_engine(factory)`` at
module-import time; ``registered_engines()`` instantiates them in
registration order — deterministic because module execution is. The 1.3
registry is ``[NullEngine, DeptryEngine]``: ``NullEngine`` is a harmless
no-op retained so its 1.2 unit contract is unchanged, ``DeptryEngine`` is the
first real engine.

``NullEngine`` spawns no subprocess; ``DeptryEngine`` runs ``deptry`` via
``_engine_env``. deptry's exit code is CONTENT (exit 1 = issues found), never
the gate — the verdict reads report content.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from .hygiene import parse_deptry_output
from .interfaces import Engine, EngineResult
from .inventory import ResolvedInventory
from .models import AXIS_HYGIENE, AxisCoverage, ErrorKind, ErrorRecord

# Bounded subprocess timeout (seconds) — a hung engine must fail loud
# (engine-timeout), never wedge the scan. A fixed default in 1.3 (the
# ``_engine_env`` ``timeout`` parameter accepts an override; a user-facing
# config surface arrives with the ConfigLoader in Story 3.1). Not in
# {1, 2, 130}, so the sole-ownership exit-literal guard never mistakes it for
# an exit code.
DEPTRY_TIMEOUT_SECONDS = 120

_ENGINE_FACTORIES: list[Callable[[], Engine]] = []


def register_engine(factory: Callable[[], Engine]) -> Callable[[], Engine]:
    """Register an engine factory (decorator-friendly: returns the factory).

    Order of registration is the order ``engine_factories()`` /
    ``registered_engines()`` yields. Re-registering the SAME factory object
    is a no-op — a defensive guard against a double ``register_engine``
    call. It CANNOT protect across ``importlib.reload(engines)``: reload
    re-executes this module, which RESETS the registry and silently
    discards every previously registered factory — reloading is
    unsupported."""
    if factory not in _ENGINE_FACTORIES:
        _ENGINE_FACTORIES.append(factory)
    return factory


def engine_factories() -> tuple[Callable[[], Engine], ...]:
    """The registered factories, in deterministic (registration) order.

    The CLI instantiates each factory individually under its own seam
    guard: a crashing constructor must yield a typed
    ``engine-unavailable`` ``ErrorRecord`` with the report still emitted,
    never abort the scan (instantiation is part of the seam)."""
    return tuple(_ENGINE_FACTORIES)


def registered_engines() -> tuple[Engine, ...]:
    """Fresh engine instances, in deterministic (registration) order.

    Instantiates EAGERLY and unguarded — direct/test use. The CLI goes
    through ``engine_factories()`` instead so a crashing constructor is
    contained per-factory."""
    return tuple(factory() for factory in _ENGINE_FACTORIES)


def _engine_env(
    build_argv: Callable[[str], list[str]],
    *,
    owner: str,
    cwd: Path,
    timeout: float = DEPTRY_TIMEOUT_SECONDS,
) -> tuple[str | None, ErrorRecord | None]:
    """Run one engine subprocess under a normalized environment.

    ``build_argv(output_path)`` returns the argv **list** (never
    ``shell=True``, never manifest data as a flag); the machine output is
    forced to ``output_path``, a ``tempfile.mkstemp`` file (mode 0600) in
    SYSTEM temp — never the scanned tree (NFR-S4). The child runs with
    ``NO_COLOR=1``, ``stdin=DEVNULL``, and its own stdout/stderr routed to
    ``DEVNULL`` — deptry's human chatter never reaches our contract streams,
    and only the ``-o`` file is read. The subprocess return code is IGNORED
    (deptry's 0/1 are content, not the gate; distinguishing other codes as
    operational failures is Story 1.5's job, designed with osv's 127/128).

    Returns ``(decoded-machine-output-text, None)`` on success, or
    ``(None, ErrorRecord)`` on a typed failure:
    ``FileNotFoundError`` → ``engine-unavailable``; ``TimeoutExpired`` →
    ``engine-timeout``; an undecodable (non-utf-8) machine-output file →
    ``engine-output-unparseable``; any other OS failure spawning the child →
    ``engine-execution-failed``. The temp file is cleaned up on success AND
    failure."""
    try:
        handle, output_path = tempfile.mkstemp(suffix=".json", prefix="pdos-engine-")
    except OSError as exc:
        return (
            None,
            ErrorRecord(
                kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                owner=owner,
                message=f"could not create a temp output file: {exc.__class__.__name__}",
            ),
        )
    os.close(handle)  # the child reopens the path for writing
    try:
        env = dict(os.environ)
        env["NO_COLOR"] = "1"
        try:
            subprocess.run(  # noqa: S603 — argv list, no shell; the sole seam
                build_argv(output_path),
                cwd=str(cwd),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,  # exit code is content, never the gate
            )
        except FileNotFoundError:
            # subprocess raises FileNotFoundError for BOTH a missing executable
            # AND a missing cwd (the pre-exec chdir fails). Disambiguate so a
            # target dir that vanished after discovery (TOCTOU) is not
            # misreported as "engine not installed" — this seam is reused
            # verbatim by Story 1.5's osv runner.
            if not os.path.isdir(cwd):
                return (
                    None,
                    ErrorRecord(
                        kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                        owner=owner,
                        message=(
                            f"scan target {str(cwd)!r} is not an existing "
                            f"directory when engine {owner!r} ran (vanished "
                            "after discovery?)"
                        ),
                    ),
                )
            return (
                None,
                ErrorRecord(
                    kind=ErrorKind.ENGINE_UNAVAILABLE,
                    owner=owner,
                    message=f"engine binary for {owner!r} not found on PATH",
                ),
            )
        except subprocess.TimeoutExpired:
            return (
                None,
                ErrorRecord(
                    kind=ErrorKind.ENGINE_TIMEOUT,
                    owner=owner,
                    message=f"engine {owner!r} exceeded the {timeout}s timeout",
                ),
            )
        except OSError as exc:
            return (
                None,
                ErrorRecord(
                    kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                    owner=owner,
                    message=f"engine {owner!r} could not be executed: {exc.__class__.__name__}",
                ),
            )
        try:
            # utf-8-sig tolerates a leading BOM some tools prepend, then
            # decodes as utf-8; genuinely non-utf-8 bytes still raise below.
            text = Path(output_path).read_bytes().decode("utf-8-sig")
        except UnicodeDecodeError:
            return (
                None,
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner=owner,
                    message=f"engine {owner!r} produced non-utf-8 output",
                ),
            )
        except OSError as exc:
            return (
                None,
                ErrorRecord(
                    kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                    owner=owner,
                    message=f"could not read engine output: {exc.__class__.__name__}",
                ),
            )
        return (text, None)
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass


class NullEngine:
    """The no-op engine: assesses nothing, contributes nothing.

    Retained from 1.2 so its unit contract is unchanged; it exists so the
    pipeline runs end-to-end through the real seam even before a real engine
    contributes."""

    name: str = "null"

    def run(self, target: Path, inventory: ResolvedInventory) -> EngineResult:
        return EngineResult(findings=(), errors=(), coverage=())


class DeptryEngine:
    """The first real engine: dependency-hygiene via ``deptry`` (Story 1.3).

    Runs ``deptry . -o <tempfile> --no-ansi`` with ``cwd=target`` so deptry
    reads the project's OWN ``pyproject.toml`` — honoring ``[tool.deptry]``
    (``ignore``/``per_rule_ignores``/``exclude``) NATIVELY (FR9) — and writes
    its machine output to a system-temp file we read (the pure-JSON-stdout
    seam: deptry's own chatter never touches our streams). deptry's exit code
    is ignored; the DEP001–DEP005 records become ``hygiene:<code>:<module>``
    findings, and on a successful run the hygiene axis reports
    ``deps_assessed == inventory.count``."""

    name: str = "deptry"

    def run(self, target: Path, inventory: ResolvedInventory) -> EngineResult:
        text, error = _engine_env(
            lambda output_path: [
                "deptry",
                ".",
                "-o",
                output_path,
                "--no-ansi",
            ],
            owner=self.name,
            cwd=target,
        )
        if error is not None:
            return EngineResult(findings=(), errors=(error,), coverage=())
        parse = parse_deptry_output(text or "")
        if not parse.output_parsed:
            # Top-level garbage (undecodable/non-array): fail loud, no
            # coverage claim (nothing was assessed).
            return EngineResult(findings=(), errors=parse.errors, coverage=())
        coverage = (
            AxisCoverage(
                axis=AXIS_HYGIENE,
                manifests_found=0,
                manifests_parsed=0,
                deps_total=inventory.count,
                deps_assessed=inventory.count,
                resolution_depth=None,
            ),
        )
        return EngineResult(
            findings=parse.findings,
            errors=parse.errors,
            coverage=coverage,
        )


register_engine(NullEngine)
register_engine(DeptryEngine)
