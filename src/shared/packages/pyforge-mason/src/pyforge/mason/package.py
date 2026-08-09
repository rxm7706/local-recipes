"""`mason package` -- build and ship distributions to PyPI and conda-forge
(FR-15 - FR-24).

Seeded here, docstring-only, solely to prove AD-6's import-safety invariant
(Story 1.7): `package.py` is CFE-independent except for its future
`conda-forge` ship target, which is permitted to import `cfe` *lazily*
(nested inside a function body) but never at module scope -- a `pypi` ship
must succeed with the CFE root absent. `tests/meta/test_capability_tiers.py`
guards this file for exactly that: no module-level `cfe` import, ever.

Epic 3 supplies the real content: wheel/`.conda`/sdist construction
(`engines/pep517`, `engines/pixi`), the `twine` upload path, and the
`conda-forge` ship target that calls into `recipe.py` through the CFE port
(AD-11). Nothing here yet -- no functions, no classes, no CFE import of any
kind.
"""

from __future__ import annotations
