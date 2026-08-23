"""Stage 2: post-setup refusals at ``AppConfig.ready()`` (CAP-3).

Invoked from ``platformapp.users.apps.UsersConfig.ready()``. The sentinel is
written *before* the locality check so local/CI paths can prove the hook fired.

CAP-3 ships one deployed-only condition: refuse ``DEBUG=True``, and refuse a
deployed process that loaded ``config.settings.local``. Later stories add
URLconf / migration / claims checks — do not port those here.

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Final

from django.core.exceptions import ImproperlyConfigured

from config.locality import LOCAL
from config.locality import RUNTIME_ENV_VAR
from config.locality import is_deployed

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "LOCAL_SETTINGS_MODULE",
    "STAGE_TWO_OWNER_APP_LABEL",
    "run_stage_two",
    "stage_two_has_run",
]

#: App label of the immovable-core app that owns the stage-2 invocation.
STAGE_TWO_OWNER_APP_LABEL: Final[str] = "users"

LOCAL_SETTINGS_MODULE: Final[str] = "config.settings.local"
PRODUCTION_SETTINGS_MODULE: Final[str] = "config.settings.production"
SETTINGS_MODULE_ENV_VAR: Final[str] = "DJANGO_SETTINGS_MODULE"

_STAGE_TWO_RAN: Final[dict[str, bool]] = {"entered": False}


def stage_two_has_run() -> bool:
    """Return True once ``run_stage_two()`` has been entered in this interpreter."""
    return _STAGE_TWO_RAN["entered"]


def _refuse_debug_true() -> None:
    """Refuse a deployed process with a truthy ``DEBUG``."""
    from django.conf import settings  # noqa: PLC0415

    if not settings.DEBUG:
        return
    message = (
        "DEBUG is enabled in a deployed component. "
        "Set DJANGO_DEBUG=False (or unset it), or set "
        f"{RUNTIME_ENV_VAR}={LOCAL} if this is local development."
    )
    raise ImproperlyConfigured(message)


def _refuse_local_settings_module() -> None:
    """Refuse a deployed process that loaded the local settings module."""
    from django.conf import settings  # noqa: PLC0415

    module = getattr(settings, "SETTINGS_MODULE", "") or ""
    if module != LOCAL_SETTINGS_MODULE:
        return
    message = (
        f"{LOCAL_SETTINGS_MODULE} was loaded by a deployed component. "
        f"Set {RUNTIME_ENV_VAR}={LOCAL} if this is local development, "
        f"or point {SETTINGS_MODULE_ENV_VAR} at {PRODUCTION_SETTINGS_MODULE} "
        "if it is a deployment."
    )
    raise ImproperlyConfigured(message)


_STAGE_TWO: Final[tuple[Callable[[], None], ...]] = (
    _refuse_debug_true,
    _refuse_local_settings_module,
)


def run_stage_two() -> None:
    """Evaluate every stage-2 condition at process startup.

    Raises:
        ImproperlyConfigured: When any condition finds a forbidden state.
    """
    _STAGE_TWO_RAN["entered"] = True

    if not is_deployed():
        return

    for condition in _STAGE_TWO:
        condition()
