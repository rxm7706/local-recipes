"""Integration-test bootstrap for optional Django-backed checks."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
_PLATFORM = REPO_ROOT / "src" / "platform"
_EXTRA_PATHS = (
    REPO_ROOT / "src" / "shared" / "packages" / "django-pyforge" / "src",
    REPO_ROOT / "src" / "shared" / "packages" / "pyforge-core" / "src",
    _PLATFORM,
)
for entry in _EXTRA_PATHS:
    text = str(entry)
    if text not in sys.path:
        sys.path.insert(0, text)

os.environ.setdefault("COMPONENT_RUNTIME", "local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
