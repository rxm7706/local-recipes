"""Engine registry + the null engine (Story 1.2).

OWNERSHIP DECISION (recorded): ``engines.py`` is the package's ONLY
subprocess-capable module — the sole future subprocess site. The
``_engine_env()`` normalization helper and the real deptry/osv-scanner
runners arrive with Stories 1.3/1.5; the ``NullEngine`` spawns NO subprocess
(and this module currently imports none of the subprocess machinery).

Registry semantics: engines register via ``register_engine(factory)`` at
module-import time; ``registered_engines()`` instantiates them in
registration order — a deterministic order because module execution is.
``NullEngine`` is the only 1.2 registration.

This module performs no I/O and no network in 1.2.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .interfaces import Engine, EngineResult
from .inventory import ResolvedInventory

_ENGINE_FACTORIES: list[Callable[[], Engine]] = []


def register_engine(factory: Callable[[], Engine]) -> Callable[[], Engine]:
    """Register an engine factory (decorator-friendly: returns the factory).

    Order of registration is the order ``registered_engines()`` yields.
    Re-registering the SAME factory is a no-op (idempotent): a module
    re-import/reload must not make every engine run twice."""
    if factory not in _ENGINE_FACTORIES:
        _ENGINE_FACTORIES.append(factory)
    return factory


def registered_engines() -> tuple[Engine, ...]:
    """Fresh engine instances, in deterministic (registration) order."""
    return tuple(factory() for factory in _ENGINE_FACTORIES)


class NullEngine:
    """The no-op engine: assesses nothing, contributes nothing.

    It exists so the 1.2 pipeline runs end-to-end through the real seam;
    the sentinel fixture's findings therefore come from the fail-closed
    inventory path (``DefaultPolicy``), never from an engine."""

    name: str = "null"

    def run(self, target: Path, inventory: ResolvedInventory) -> EngineResult:
        return EngineResult(findings=(), errors=(), coverage=())


register_engine(NullEngine)
