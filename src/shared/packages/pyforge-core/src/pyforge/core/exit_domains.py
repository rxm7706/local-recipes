"""pyforge.core.exit_domains -- every exit-code domain a verdict module projects, by
member name and number (steward Story 137.1, spec-pyforge-steward:CAP-184; the
exit-code half of spec-vocabulary-one-name-one-job CAP-2, DW-VOCAB-2026-09-14-8).

``docs/governance/guild-roster.json``'s ``exit_code_domains`` and
``exit_code_domains_narrowing`` keys are the declaration, read directly by
repo-rooted tooling (``scripts/detectors.py``). This module carries the same table
for in-process station code, which must not gain a filesystem read to learn its own
exit codes -- the ``pyforge.core.roster`` pattern (spec-pyforge-steward:CAP-137).
Nothing here reads the JSON file; ``tests/unit/test_exit_domains_match_the_guild_roster.py``
fails when the two differ.

Each domain maps a member name -- a lattice rung's own enum value where the module
has one -- to the code it exits with. A domain's code set is the set of its values,
and several names may share one code. The numbers are the ones each module already
used; declaring them changed none.

The one trap the declaration exists to make visible: ``2`` is FAIL in ``doctor`` and
could-not-run in ``detectors``, so a code is read in the domain of the surface that
produced it, never another's.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

_DOMAINS: dict[str, dict[str, int]] = {
    "doctor": {"ok": 0, "warn": 0, "fail": 2, "interrupted": 130},
    "warden": {
        "clean": 0,
        "not-applicable": 0,
        "bypassed": 0,
        "warn": 0,
        "warn-as-error": 1,
        "policy-violation": 1,
        "indeterminate": 1,
        "error": 2,
        "interrupted": 130,
    },
    "marshal": {
        "ok": 0,
        "clean": 0,
        "warn": 0,
        "unevaluable": 1,
        "scope-violation": 2,
        "usage": 2,
        "gate-failed": 3,
        "error": 4,
        "interrupted": 130,
    },
    "marshal-seed": {
        "conformance-failure": 1,
        "usage": 2,
        "precondition-failure": 3,
        "never-write-violation": 4,
        "state-invalid": 5,
        "internal-error": 10,
    },
    "detectors": {"pass": 0, "unmeasured": 0, "findings": 1, "could-not-run": 2},
}

EXIT_CODE_DOMAINS: Mapping[str, Mapping[str, int]] = MappingProxyType(
    {name: MappingProxyType(dict(members)) for name, members in _DOMAINS.items()}
)
"""Domain name -> member name -> exit code; read-only. Matches
``guild-roster.json``'s ``exit_code_domains`` exactly."""

EXIT_CODE_DOMAINS_NARROWING: Mapping[str, str] = MappingProxyType({"doctor": "warden"})
"""Each domain whose code set is, by design, a subset of another's: doctor reports
operability, not policy, so it omits warden's policy rung ``1``. Matches
``guild-roster.json``'s ``exit_code_domains_narrowing``."""


def exit_code(domain: str, member: str) -> int:
    """The code ``member`` exits with in ``domain``; a ``KeyError`` naming both when
    either is undeclared, so a misspelt name fails at import, never as a wrong code."""
    try:
        members = EXIT_CODE_DOMAINS[domain]
    except KeyError:
        raise KeyError(f"exit-code domain {domain!r} is not declared; declared: {sorted(EXIT_CODE_DOMAINS)}") from None
    try:
        return members[member]
    except KeyError:
        raise KeyError(
            f"{member!r} is not a member of exit-code domain {domain!r}; declared: {sorted(members)}"
        ) from None


def domain_codes(domain: str) -> frozenset[int]:
    """The code set of ``domain``: every code one of its members exits with."""
    try:
        return frozenset(EXIT_CODE_DOMAINS[domain].values())
    except KeyError:
        raise KeyError(f"exit-code domain {domain!r} is not declared; declared: {sorted(EXIT_CODE_DOMAINS)}") from None
