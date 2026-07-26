"""Mason — the Artisan Builder's station.

Part of the implicit ``pyforge`` namespace (PEP 420). There is deliberately no
``src/pyforge/__init__.py``: its **absence** is what lets ``pyforge.mason``,
``pyforge.warden``, ``pyforge.atlas``, ``pyforge.herald``, ``pyforge.scribe`` and
``pyforge.doctor`` coexist in one import root when installed independently. A
regression here is silent — it only surfaces when two of them are installed
together — so `tests/meta/test_namespace_is_implicit.py` pins it.
"""

from __future__ import annotations

__all__ = ["__version__"]


def _version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("pyforge-mason")
    except PackageNotFoundError:      # running from a source tree, not installed
        return "0.1.0+source"


__version__ = _version()
