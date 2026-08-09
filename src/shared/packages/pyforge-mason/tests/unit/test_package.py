"""Story 1.7 -- AD-6: `package.py` must import cleanly with no CFE anywhere
on the filesystem. This bare-import success is the entire test surface this
story owns for it; Epic 3 supplies real build/ship logic and its own tests.
"""

from __future__ import annotations


def test_package_module_imports_successfully():
    import pyforge.mason.package  # noqa: F401
