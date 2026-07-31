"""Static check catalog + per-check filter (Story 1.3, FR-2).

``doctor check``'s only check source (Story 1.2's ``sources.warden.gather``)
has no way to list its named checks without running them, and no way to run
one check in isolation. This module adds both, as a pure library layer --
CLI flag wiring (``--list``, ``--engines <name>``) is Story 1.5's job:

- :func:`list_checks` is a STATIC catalog -- a hand-maintained mirror of
  ``pyforge.warden.engines.run_doctor_checks``'s own documented fixed order
  (``deptry``, ``osv-scanner``, ``osv-db``, ``kev-feed``, ``epss-feed``,
  ``endoflife-feed``). No warden API returns check names without running
  them, and the architecture spine's import allowlist (AD-1) sanctions only
  ``run_doctor_checks`` itself -- no metadata-only sibling exists to query
  instead. This catalog is therefore Doctor's OWN duplicate of warden's
  order, safety-netted by a test that calls the real
  ``sources.warden.gather()`` once and compares the two check-name tuples
  in order: a future warden rename, reorder, addition, or removal fails
  that test loudly instead of letting ``--list`` silently drift.
- :func:`gather_one` is a filter, not a second code path: it always calls
  the real category's gather function (today only ``sources.warden.gather``)
  and picks the one ``Finding`` whose ``check`` matches -- never a
  duplicated per-check lookup that could drift from the full-suite result.

Both functions stay inside the existing closed ``DoctorStatus``/``Source``
contract (``models.py``, Story 1.1) -- this module produces ``Finding``s,
never a new taxonomy member. ``"env"`` (Story 1.4) and any other future
category simply aren't registered yet: :func:`list_checks` returns an empty
tuple for them, never an exception, until they land.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models import Finding
from ..sources import warden as warden_source

# Mirrors ``pyforge.warden.engines.run_doctor_checks``'s own documented
# fixed order (stated in that function's docstring; deliberately cited by
# name, not line numbers, which rot) -- see the module docstring for why
# this is hand-maintained rather than queried, and how drift is caught.
_ENGINE_CHECK_NAMES: tuple[str, ...] = (
    "deptry",
    "osv-scanner",
    "osv-db",
    "kev-feed",
    "epss-feed",
    "endoflife-feed",
)


@dataclass(frozen=True)
class CheckSpec:
    """One addressable check's identity -- category + name, nothing else.

    Deliberately thin: an introspection handle for ``--list``/``--engines
    <name>`` (Story 1.5), not a duplicate of ``Finding``'s result shape.
    """

    category: str
    name: str


_ENGINE_CHECKS: tuple[CheckSpec, ...] = tuple(
    CheckSpec(category="engines", name=name) for name in _ENGINE_CHECK_NAMES
)

# category -> its static CheckSpec catalog. Today only "engines" (Story
# 1.2's warden wrapper) is registered; Story 1.4 adds "env" here when it
# lands. An unregistered category is simply absent from this dict.
_CATALOG: dict[str, tuple[CheckSpec, ...]] = {"engines": _ENGINE_CHECKS}


def list_checks(category: str | None = None) -> tuple[CheckSpec, ...]:
    """Return the known ``CheckSpec`` catalog, optionally filtered by
    ``category``.

    PURE and STATIC -- never calls ``sources.warden.gather()``,
    ``run_doctor_checks``, or any subprocess (FR-2's explicit "without
    running them"). An unknown/unregistered category returns an empty
    tuple, never an exception -- callers (Story 1.5's ``--list``) don't
    need a try/except for a typo'd category name.
    """
    if category is not None:
        return _CATALOG.get(category, ())
    return tuple(spec for specs in _CATALOG.values() for spec in specs)


def gather_one(category: str, name: str, target: Path) -> Finding | None:
    """Run ``category``'s real gather and return the ``Finding`` named
    ``name``, or ``None`` if no such check ran.

    A filter over the full-suite result, never a separate lookup path: the
    result always equals ``next((f for f in sources.warden.gather(target)
    if f.check == name), None)`` for ``category == "engines"``. Raises
    ``ValueError`` for any other category (today's only registered one) --
    Story 1.5's CLI turns that into a usage error.

    ``target`` is forwarded verbatim to the category's gather (for
    "engines": the project directory warden's self-check runs against); it
    never affects which check *names* exist, only their results.

    Filter semantics cut both ways when the category's gather DEGRADES to
    its single sentinel ``Finding`` (``check == "pyforge-warden"``, Story
    1.2's three failure shapes): every cataloged name then returns
    ``None``, while the sentinel's own name -- one ``list_checks()`` never
    advertises -- IS addressable here and returns the sentinel itself.
    Whether a CLI validates names against the catalog or passes them
    through is Story 1.5's decision (see ``deferred-work.md``).
    """
    # Deliberately NOT derived from `_CATALOG` membership: each category
    # needs its own real gather function (only "engines" -> warden_source
    # exists today), so a category merely being cataloged doesn't mean it's
    # wired here yet. Adding a category to `_CATALOG` (Story 1.4's "env")
    # must come with its own dispatch branch in this function too -- review
    # finding, 2026-07-30.
    if category != "engines":
        raise ValueError(
            f"unsupported check category: {category!r} "
            "(categories with a wired gather: 'engines')"
        )
    return next(
        (
            finding
            for finding in warden_source.gather(target)
            if finding.check == name
        ),
        None,
    )
