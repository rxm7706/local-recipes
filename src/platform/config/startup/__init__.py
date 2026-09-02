"""Two-stage fail-fast misconfiguration contract (CAP-3 / steward 16.2).

**Stage 1 — settings import (validation).** Runs before app import side effects
deepen. Leaf settings that must refuse when deployed call ``run_stage_one`` as
their last statement; ``production.py`` also calls ``refuse_required_settings``
*before* django-environ reads required keys so operators get a named setting +
remedy instead of an opaque mid-import failure. ``base.py`` must never call
stage 1: it is a composition fragment, not a leaf.

**Stage 2 — process startup (later boot).** Owned by ``platformapp.users``
``AppConfig.ready()`` via ``run_stage_two``. Fires inside ``django.setup()`` for
ASGI/WSGI and management commands alike.

**Locality.** Both stages are deployed-only: when ``COMPONENT_RUNTIME=local``
they return before any condition runs, so CI and local/test settings stay
usable. Locality is ``config.locality`` (re-exported here by identity).

Public surface: ``run_stage_one``, ``run_stage_two``, ``is_deployed``,
``is_serving_process``. Story 41.4 / CAP-12 added the one celery-scoped
refusal there is — ``refuse_unverified_broker_tls`` (broker TLS is verified or
the deployed component does not boot); do not add OIDC/JWKS/OTEL/claims or
further feature-scoped refusals here, those belong to later stories.

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

from config.locality import is_deployed
from config.locality import is_serving_process
from config.startup.stage_one import refuse_required_settings
from config.startup.stage_one import refuse_unverified_broker_tls
from config.startup.stage_one import run_stage_one
from config.startup.stage_two import run_stage_two

__all__ = [
    "is_deployed",
    "is_serving_process",
    "refuse_required_settings",
    "refuse_unverified_broker_tls",
    "run_stage_one",
    "run_stage_two",
]
