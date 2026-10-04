"""Static check catalog + per-check filter (Story 1.3, FR-2).

``doctor check``'s only check source (Story 1.2's ``sources.warden.gather``)
has no way to list its named checks without running them, and no way to run
one check in isolation. This module adds both, as a pure library layer --
CLI flag wiring (``--list``, ``--engines <name>``) is Story 1.5's job:

- :func:`list_checks` is a STATIC catalog -- a hand-maintained mirror of
  ``pyforge.warden.engines.run_doctor_checks``'s own documented fixed order
  (``deptry``, ``osv-scanner``, ``osv-db``, ``kev-feed``, ``epss-feed``,
  ``endoflife-feed``, ``tea``). No warden API returns check names without running
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
never a new taxonomy member. ``"engines"`` (Story 1.2's warden wrapper) and
``"env"`` (Story 1.4's hand-written ``env_hygiene`` detector) are the two
registered categories; any other, not-yet-landed category simply isn't
registered: :func:`list_checks` returns an empty tuple for it, never an
exception.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models import Finding
from ..sources import warden as warden_source
from . import env_hygiene

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
    "tea",
)


@dataclass(frozen=True)
class CheckSpec:
    """One addressable check's identity -- category + name, nothing else.

    Deliberately thin: an introspection handle for ``--list``/``--engines
    <name>`` (Story 1.5), not a duplicate of ``Finding``'s result shape.
    """

    category: str
    name: str


_ENGINE_CHECKS: tuple[CheckSpec, ...] = tuple(CheckSpec(category="engines", name=name) for name in _ENGINE_CHECK_NAMES)

# "env" (Story 1.4): a single hand-written check, env_hygiene.CHECK_NAME
# imported rather than re-literaled here -- unlike _ENGINE_CHECK_NAMES
# above, env_hygiene.py is an in-package sibling module with no external
# tool to duplicate-and-drift-guard against, so importing its own name
# constant is the direct, non-drifting source of truth.
_ENV_CHECKS: tuple[CheckSpec, ...] = (CheckSpec(category="env", name=env_hygiene.CHECK_NAME),)

# category -> its static CheckSpec catalog. "engines" (Story 1.2's warden
# wrapper) and "env" (Story 1.4's env_hygiene detector) are registered; a
# category merely being cataloged here is a separate concern from being
# wired in gather_one's dispatch (see that function's own comment below).
# An unregistered category is simply absent from this dict.
_CATALOG: dict[str, tuple[CheckSpec, ...]] = {
    "engines": _ENGINE_CHECKS,
    "env": _ENV_CHECKS,
}


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


#: Each wired category's degradation-sentinel ``check`` name -- never
#: cataloged, so a named run can still tell "the category degraded" apart
#: from "the named check found nothing".
SENTINEL_CHECK_NAMES: dict[str, str] = {
    "engines": warden_source.SENTINEL_CHECK_NAME,
    "env": env_hygiene.SCAN_INCOMPLETE_CHECK_NAME,
}


def gather_one(category: str, name: str, target: Path) -> tuple[Finding, ...]:
    """Run ``category``'s real gather and return every ``Finding`` named
    ``name``, plus the category's degradation sentinel when the gather
    produced one -- in gather order, each Finding once.

    A filter over the full-suite result, never a separate lookup path: the
    result always equals ``tuple(f for f in <gather>(target) if f.check in
    {name, SENTINEL_CHECK_NAMES[category]})`` -- ``sources.warden.gather``
    for ``category == "engines"``, ``env_hygiene.gather`` for ``"env"``.
    Raises ``ValueError`` for any other (unwired) category -- Story 1.5's
    CLI turns that into a usage error.

    Every match is kept (DW-FU-1-5): ``env_hygiene`` emits one Finding per
    matching file under the same check name, and a first-match filter
    surfaced only the first. The sentinel rides along with the named
    results so a degraded or incomplete gather can never read as clean
    (DW-FU-1-5, DW-FU-1-5-4): for "engines" it carries warden's specific
    degradation message (absent / unimportable / self-check crashed); for
    "env" it says the scan was incomplete or the target was not a
    directory. The sentinel's own name -- one ``list_checks()`` never
    advertises -- stays addressable and returns the sentinel alone.

    ``target`` is forwarded verbatim to the category's gather (for
    "engines": the project directory warden's self-check runs against; for
    "env": the directory tree ``env_hygiene`` scans); it never affects
    which check *names* exist, only their results.
    """
    # Deliberately NOT derived from `_CATALOG` membership: each category
    # needs its own real gather function ("engines" -> warden_source,
    # "env" -> env_hygiene), so a category merely being cataloged doesn't
    # mean it's wired here yet. Adding a category to `_CATALOG` must come
    # with its own dispatch branch in this function too -- review finding,
    # 2026-07-30.
    if category == "engines":
        findings = warden_source.gather(target)
    elif category == "env":
        findings = env_hygiene.gather(target)
    else:
        raise ValueError(
            f"unsupported check category: {category!r} (categories with a wired gather: 'engines', 'env')"
        )
    wanted = {name, SENTINEL_CHECK_NAMES[category]}
    return tuple(finding for finding in findings if finding.check in wanted)
