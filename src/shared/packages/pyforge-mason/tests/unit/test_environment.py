"""Story 1.7 -- AD-6: `environment.py` must import cleanly with no CFE
anywhere on the filesystem. This bare-import success is the entire test
surface this story owns for it; Epic 4 supplies real lock/check logic and
its own tests.
"""

from __future__ import annotations


def test_environment_module_imports_successfully():
    import pyforge.mason.environment  # noqa: F401
