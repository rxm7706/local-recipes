"""pyforge.core.errors -- the shared exception root (Story 14.3,
SPEC-pyforge-core CAP-5).

``PyforgeError`` is a bare marker with no ``__init__`` override -- matching
herald's own ``HeraldError`` shape exactly -- so it never interferes with
any subclass's own constructor. This is critical for classes like mason's
``CfeUnresolvedError``/``CfeTimeoutError``, which carry custom
``__init__``/``__reduce__`` signatures that must survive re-parenting
unchanged.

``except PyforgeError`` is the one new sentence CAP-5 gives every station's
caller: a single base every re-parented exception (herald's ``HeraldError``,
mason's ``MasonError``, and the 37 scattered family-root classes across
warden/marshal/atlas) shares, without changing any existing ``except``
clause's behaviour -- each re-parented class keeps its original stdlib base
in its MRO via multiple inheritance, so every pre-existing catch site still
catches it.
"""

from __future__ import annotations


class PyforgeError(Exception):
    """Root of every exception a pyforge station raises deliberately."""
