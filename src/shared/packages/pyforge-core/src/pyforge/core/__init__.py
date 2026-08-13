"""pyforge.core -- the shared leaf every pyforge station may depend on.

Pure stdlib, zero third-party runtime dependencies, and imports nothing
from any pyforge station (SPEC-pyforge-core CAP-1, "the leaf exists and is
provably a leaf"). Story 14.1 scaffolds this empty package and its
structural leaf-constraint guard (`tests/meta/test_leaf_constraint.py`);
the five primitives it will eventually hold (atomic write, verdict lattice,
report envelope, exception root, subprocess guard) are extracted in
Stories 14.2-14.4, not here.
"""

__version__ = "0.1.0"
