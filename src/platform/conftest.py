"""Platform-root pytest hooks.

CAP-3 / steward 16.2: unit and CI tests are a local runtime. setdefault so a
developer shell that already exported COMPONENT_RUNTIME=local is untouched, and
so deployed-only startup refusals do not fire under ``--ds=config.settings.test``.
"""

from __future__ import annotations

import os

os.environ.setdefault("COMPONENT_RUNTIME", "local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
