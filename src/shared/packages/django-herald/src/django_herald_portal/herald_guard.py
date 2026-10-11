"""Skip herald portal routes when pyforge.herald is absent (Story 37.1)."""

from __future__ import annotations

import importlib
import logging

_logger = logging.getLogger(__name__)

_HERALD_MODULE = "pyforge.herald"
_COMPONENT = "herald"
_REMEDY = "Install pyforge-herald on this host to enable herald routes."

_decided: bool = False
_herald_installed: bool = False
_absent_reason: str | None = None
_logged_absent: bool = False


def _is_provided_by_absent(exc_name: str | None, provided_by: str) -> bool:
    if exc_name is None:
        return False
    if exc_name == provided_by:
        return True
    if provided_by.startswith(f"{exc_name}."):
        return True
    return exc_name.startswith(f"{provided_by}.")


def herald_is_installed() -> bool:
    """Return whether ``pyforge.herald`` is importable; decide and log once."""
    global _decided, _herald_installed, _absent_reason, _logged_absent
    if _decided:
        return _herald_installed
    _decided = True
    try:
        importlib.import_module(_HERALD_MODULE)
    except ModuleNotFoundError as exc:
        if not _is_provided_by_absent(exc.name, _HERALD_MODULE):
            raise
        _herald_installed = False
        _absent_reason = (
            f"{_COMPONENT} is not installed on this host: No module named '{exc.name}'"
        )
        if not _logged_absent:
            _logged_absent = True
            _logger.warning("%s %s", _absent_reason, _REMEDY)
        return False
    else:
        _herald_installed = True
        return True


def portal_absent_reason() -> str:
    """Return the skip reason after :func:`herald_is_installed` has run."""
    herald_is_installed()
    if _absent_reason is None:
        msg = "portal_absent_reason called while herald is installed"
        raise RuntimeError(msg)
    return _absent_reason
