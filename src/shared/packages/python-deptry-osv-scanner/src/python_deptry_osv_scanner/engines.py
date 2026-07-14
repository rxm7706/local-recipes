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

    Order of registration is the order ``engine_factories()`` /
    ``registered_engines()`` yields. Re-registering the SAME factory object
    is a no-op — a defensive guard against a double ``register_engine``
    call. It CANNOT protect across ``importlib.reload(engines)``: reload
    re-executes this module, which RESETS the registry and silently
    discards every previously registered factory (and re-registers a fresh
    ``NullEngine`` class object) — reloading this module is unsupported."""
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


class NullEngine:
    """The no-op engine: assesses nothing, contributes nothing.

    It exists so the 1.2 pipeline runs end-to-end through the real seam;
    the sentinel fixture's findings therefore come from the fail-closed
    inventory path (``DefaultPolicy``), never from an engine."""

    name: str = "null"

    def run(self, target: Path, inventory: ResolvedInventory) -> EngineResult:
        return EngineResult(findings=(), errors=(), coverage=())


register_engine(NullEngine)
