"""pyforge.core -- the shared leaf every pyforge station may depend on.

Pure stdlib, zero third-party runtime dependencies, and imports nothing
from any pyforge station (SPEC-pyforge-core CAP-1). Stories 14.1-14.4
landed the leaf plus atomic write, verdict lattice, report envelope,
exception root, and subprocess guard. Story 32.1 adds the shared hook-spec
and plugin registration surface (``pyforge.core.hooks``) in this same
package -- no ninth package, no station-local loader.
"""

__version__ = "0.1.0"
