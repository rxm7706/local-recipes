"""The central finding-code registry (Story 1.1, architecture spine AD-15).

Every failure or warning Marshal ever emits carries a stable machine code
from this one registry, plus a human message (AD-15). Codes are never
reused or renumbered. Format: ``MRS-<AREA>-<NNN>`` (Consistency Conventions'
``Findings`` row) -- e.g. ``MRS-GATE-001``.

``REGISTERED_CODES`` shipped Story 1.1 as an empty ``frozenset()`` --
``marshal --version``/``--help`` bypass the envelope entirely (mirrors
``pyforge-doctor``), so nothing emitted a real finding yet. Story 1.2's
``core/identity.py`` is the first real caller: ``MRS-IDENT-001`` (a
malformed story key) and ``MRS-IDENT-002`` (a non-conforming merge subject)
are its two registered codes. Story 1.3's ``core/policy.py``/``cli/config.py``
add the registry's second real caller: ``MRS-POLICY-001`` (an unknown
top-level policy key), ``MRS-POLICY-002`` (a malformed STATIC field value),
``MRS-POLICY-003`` (a malformed SEED field value), ``MRS-POLICY-004``
(a CLI-boundary I/O failure resolving or writing policy -- an unreadable
``--project-policy`` file or an unwritable ``--materialize`` target),
``MRS-POLICY-005`` (no project slug supplied -- the composed policy omits
its project-derived seed path), and ``MRS-POLICY-006`` (a malformed project
slug -- not usable as a single path segment). 001-004 and 006 classify
``Verdict.UNEVALUABLE``; 005 classifies ``Verdict.WARN`` (a bare
no-active-project invocation legitimately shows the defaults and exits 0)
-- see ``core/verdict.py``. Story 1.4's ``cli/init.py`` adds the registry's
third real caller: ``MRS-INIT-001`` (a malformed project slug -- the shape
check itself is shared with ``core/policy.py`` via
``_is_valid_project_slug``, but ``init`` registers its own code since
``marshal init`` is a distinct command with its own envelope),
``MRS-INIT-002`` (the slug names no known BMAD project -- no
``_bmad-output/projects/<slug>/`` on ``main``), ``MRS-INIT-003`` (the loop
home's active-project marker and ``planning-artifacts`` symlink already
disagree with each other -- a prior partial failure, blocked before any
further write rather than silently overwritten), and ``MRS-INIT-004`` (a
``git``/filesystem operation failed -- worktree add, marker write, or
symlink repoint). 001-002 classify ``Verdict.UNEVALUABLE`` (Marshal could
not determine what to provision); 003-004 classify ``Verdict.ERROR`` (a
real operation was attempted and failed, or was blocked to avoid
compounding an existing failure) -- see ``core/verdict.py``. Later stories
append further real codes here as they gain their own real callers. The
registry MECHANISM
(format check, then membership check) is separately proven via
``monkeypatch``-injected synthetic codes in ``tests/unit/test_findings.py``.

This module is pure data: no I/O, no subprocess, no network, no clock
(AD-4).
"""

from __future__ import annotations

import re

# No ^/$ anchors -- matched with .fullmatch(), not .match(), so a trailing
# newline can never sneak a malformed code past the check (a known Python
# `re` pitfall: `$` alone matches immediately before a trailing "\n"; see
# pyforge-warden's models.py docstring, which calls out this exact gotcha).
# [0-9], never \d: Python's \d matches any Unicode decimal digit, while the
# packaged JSON schema's ECMA-262 pattern treats \d as [0-9] -- spelling
# [0-9] in both keeps the two independent copies behaviorally identical.
CODE_PATTERN = re.compile(r"MRS-[A-Z][A-Z0-9]*-[0-9]{3}")

# Story 1.2's core/identity.py -- the registry's first real registrations.
# Story 1.3's core/policy.py/cli/config.py add the second real caller's six codes.
# Story 1.4's cli/init.py adds the third real caller's four codes.
REGISTERED_CODES: frozenset[str] = frozenset(
    {
        "MRS-IDENT-001",
        "MRS-IDENT-002",
        "MRS-POLICY-001",
        "MRS-POLICY-002",
        "MRS-POLICY-003",
        "MRS-POLICY-004",
        "MRS-POLICY-005",
        "MRS-POLICY-006",
        "MRS-INIT-001",
        "MRS-INIT-002",
        "MRS-INIT-003",
        "MRS-INIT-004",
    }
)


class UnregisteredFindingCodeError(ValueError):
    """Raised when a ``Finding`` is constructed with a code that either does
    not match ``CODE_PATTERN`` or is not a member of ``REGISTERED_CODES``."""


def require_registered(code: str) -> str:
    """Return ``code`` unchanged if it is well-formed AND registered; raise
    ``UnregisteredFindingCodeError`` otherwise. Format is checked first -- a
    malformed code fails before the membership check ever runs."""
    if not CODE_PATTERN.fullmatch(code):
        raise UnregisteredFindingCodeError(
            f"malformed finding code {code!r} -- expected MRS-<AREA>-<NNN>"
        )
    if code not in REGISTERED_CODES:
        raise UnregisteredFindingCodeError(
            f"unregistered finding code {code!r} -- not in REGISTERED_CODES"
        )
    return code
