"""pyforge.core -- the shared leaf every pyforge station may depend on.

Pure stdlib at import, zero third-party runtime dependencies, and imports
nothing from any pyforge station (spec-pyforge-core:CAP-1). A caller imports
from a module of this package, never from the package itself, which binds
only ``__version__`` (not part of the contract).

Every module, with the capability that governs it and the public names a
station may import, is listed in the Spec's companion ``contract.md``
(``_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/``,
spec-pyforge-core:CAP-12); ``tests/meta/test_public_contract.py`` fails the
core suite when the source and that contract differ.
"""

__version__ = "0.1.0"
