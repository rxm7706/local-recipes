"""THE ONLY module permitted to invoke the ``bmad-loop`` harness binary,
import its package, read its policy file, or parse its output (AD-3) --
enforced by an ``import-linter`` "forbidden" contract in ``pyproject.toml``.

Reserved for a later story: this module does not yet resolve or invoke the
harness. It exists this story only to declare the seam -- the one place a
future story wires ``ports.HarnessPort`` to the real ``bmad_loop`` package
(entry point ``bmad-loop = bmad_loop.cli:main``, confirmed via
``recipes/bmad-loop/recipe.yaml``).
"""

from __future__ import annotations
