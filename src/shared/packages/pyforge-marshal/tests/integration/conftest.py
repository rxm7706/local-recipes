"""Integration-test bootstrap for optional Django-backed checks."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Import-path plumbing, never a read of what is under these directories: each goes straight onto sys.path (Story
# 116.2, spec-pyforge-marshal:CAP-305), the form steward's trigger-map derivation sees as plumbing; the last one
# inserted is first on the path.
REPO_ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "packages" / "django-pyforge" / "src"))
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "packages" / "pyforge-core" / "src"))
sys.path.insert(0, str(REPO_ROOT / "src" / "platform"))

os.environ.setdefault("COMPONENT_RUNTIME", "local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
