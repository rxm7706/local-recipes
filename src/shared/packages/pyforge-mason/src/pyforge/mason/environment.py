"""`mason environment` -- resolve conflicting worlds into one lockfile
(FR-25 - FR-29).

Seeded here, docstring-only, solely to prove AD-6's import-safety invariant
(Story 1.7): unlike `package.py`, `environment.py` has no CFE-dependent
target at all -- every verb here must import cleanly with no CFE anywhere on
the filesystem. `tests/meta/test_capability_tiers.py` guards this file for
exactly that: no module-level `cfe` import, ever.

Epic 4 supplies the real content: lock/check orchestration over
`engines/condalock`. Nothing here yet -- no functions, no classes, no CFE
import of any kind.
"""

from __future__ import annotations
