"""Optional station packages — skip absent installs at host boot (Story 87.1)."""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

_logger = logging.getLogger(__name__)

_absent_reasons: dict[str, str] = {}
_logged_absent: set[str] = set()


def _is_provided_by_absent(exc_name: str | None, provided_by: str) -> bool:
    if exc_name is None:
        return False
    if exc_name == provided_by:
        return True
    if provided_by.startswith(f"{exc_name}."):
        return True
    return exc_name.startswith(f"{provided_by}.")


def import_optional(
    module: str,
    *,
    component: str,
    provided_by: str,
    remedy: str,
) -> ModuleType | None:
    """Import ``module`` when ``provided_by`` is installed; else record and skip."""
    try:
        return importlib.import_module(module)
    except ModuleNotFoundError as exc:
        if not _is_provided_by_absent(exc.name, provided_by):
            raise
        reason = (
            f"{component} is not installed on this host: "
            f"No module named '{exc.name}'"
        )
        _absent_reasons[component] = reason
        if component not in _logged_absent:
            _logged_absent.add(component)
            _logger.warning("%s %s", reason, remedy)
        return None


def absent_reason(component: str) -> str | None:
    """Return the recorded skip reason for ``component``, if any."""
    return _absent_reasons.get(component)
