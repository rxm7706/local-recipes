"""Component locality: local vs deployed, fail-closed.

Single declaration site for the ``COMPONENT_RUNTIME`` contract. Startup
validation (and anything else that must behave differently in a deployment)
imports these predicates rather than re-reading ``os.environ``.

Fail-closed (deployed when the marker is absent or unrecognized): a real
deployment that lost ``COMPONENT_RUNTIME`` must not be treated as local
development. Only an explicit ``COMPONENT_RUNTIME=local`` is local.

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

import os
from typing import Final

__all__ = [
    "LOCAL",
    "RUNTIME_ENV_VAR",
    "is_deployed",
    "is_local",
    "is_serving_process",
]

#: Environment variable that declares whether this process is local development.
RUNTIME_ENV_VAR: Final[str] = "COMPONENT_RUNTIME"

#: The only recognized local value. Anything else (including unset) is deployed.
LOCAL: Final[str] = "local"

#: Optional process-type marker (serving vs management). Absent → serving.
PROCESS_ENV_VAR: Final[str] = "COMPONENT_PROCESS"
SERVING: Final[str] = "serving"
MANAGEMENT: Final[str] = "management"


def is_local() -> bool:
    """Return True only when ``COMPONENT_RUNTIME`` is exactly ``local``."""
    return os.environ.get(RUNTIME_ENV_VAR) == LOCAL


def is_deployed() -> bool:
    """Return True unless locality is explicitly declared local.

    Absent and unrecognized values both mean deployed (fail closed).
    """
    return not is_local()


def is_serving_process() -> bool:
    """Return True unless ``COMPONENT_PROCESS`` is explicitly ``management``.

    Fail-open on process type: an unset marker is treated as serving so a
    mis-labeled management command is the cheaper mistake. Used by later
    stage-2 conditions that need a live database; CAP-3 stage 2 does not
    depend on it yet.
    """
    return os.environ.get(PROCESS_ENV_VAR, SERVING) != MANAGEMENT
