"""Steward — the Provisioner's station.

Part of the implicit ``pyforge`` namespace (PEP 420). There is deliberately no
``src/pyforge/__init__.py``; its absence is what lets the sibling stations
coexist in one import root. Pinned by ``tests/meta/``.
"""

from __future__ import annotations

__all__ = ["__version__"]


def _version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("pyforge-steward")
    except PackageNotFoundError:
        return "0.1.0+source"


__version__ = _version()
