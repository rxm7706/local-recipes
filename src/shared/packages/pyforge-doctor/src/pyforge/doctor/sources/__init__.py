"""Doctor's own source registry — scope + subject + owner per ``Source`` (Story 6.2).

``pyforge.doctor.sources`` was empty: nothing declared which station's artifact
each ``models.Source`` member judges (``subject_station``) or which station
implements the gather that judges it (``owning_station``). Two consumers need
that declaration and had no place to read it from:

1. The fleet's detector-ownership audit (Charter §6 / INV-4 — "the station
   that owns an artifact must not be the final word on judging it") has
   nowhere to check subject-vs-owner other than reading source code by hand.
2. ``scripts/detectors.py``'s registry is built by AST-scanning
   ``scripts/*_check.py`` files on disk — a source that already lives inside
   Doctor's own package (e.g. ``marshal-durability``) is invisible to it,
   because there is no file for it to scan.

This module is that registry: a validated, exhaustive ``REGISTRY`` tuple, one
``SourceRegistration`` per current ``Source`` member. ``SourceRegistration``
mirrors ``checks.registry.CheckSpec``'s thin frozen-dataclass-plus-``list_*``
shape, but adds a ``__post_init__`` that FAILS LOUD rather than accepting a
default: a registration with no declared subject or owner, or a scope outside
the closed ``{"repo", "runtime"}`` pair, is a bug in this file, not a value
worth storing.

``tests/unit/test_sources_registry.py`` enforces the other half — that
``REGISTRY`` and ``Source`` stay in exact set-equality, in both directions —
mirroring ``checks/registry.py``'s own
``test_every_cataloged_category_is_dispatchable_by_gather_one`` tripwire.
Registering a *new* ``Source`` member is each of Stories 6.4-6.9's own job
(their own ``gather()`` lands alongside their own registration); this module
built the mechanism, and Story 6.4 was the first to land registrations of its
own on top of it (``LEDGER_REGRESSION``, ``STORY_STATUS``). The count itself
is deliberately NOT written down in prose here: ``REGISTRY`` is the count, and
``test_sources_registry.py`` pins it to ``Source`` in both directions, so a
number in this docstring could only ever be a second source of truth that goes
stale the next time a story appends a row (it already did once, at 9).

``scripts/detectors.py``'s consumption of this module (its ``_doctor_sources``
helper) degrades to ``(False, [])`` when ``pyforge.doctor`` isn't importable
in the active environment. That is DELIBERATELY not the same discipline as
``discover()``'s own "unknown, never green" handling of a detector it cannot
run — a Doctor-owned source's absence from the active environment is a normal,
expected outcome (Doctor is a dedicated lean package, not installed in every
env that runs this script), not a detector failing to execute. The caller
still needs to tell "the package is here and reports zero" apart from "the
package isn't here," which is what the leading ``bool`` is for, not a
registry finding.

Story 6.3 adds two consumers of this same ``REGISTRY``: ``scope_for`` is the
one canonical per-source scope lookup — the CLI's ``doctor check --scope
{repo,runtime,all}`` filter reads every category's scope through it, rather
than a second hand-rolled scope list that would drift the moment a
``SourceRegistration``'s ``scope`` changes. ``degrade_on_exception`` is a
reusable "cannot evaluate here" wrapper for a future ``scope="runtime"``
source's own gather (e.g. Story 6.5's ``dashboard_drift``, which reads tmux/
``~/.bmad-loops`` state absent in CI) — see Story 6.3's OWN spec Design Notes
(review finding: this used to point at Story 6.5, which is the source named
in the example, not the story that wrote this rationale) for why it is
deliberately NOT wired into today's three existing (``scope="repo"``)
dispatch calls, whose own gather functions already promise never to raise.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..models import DoctorStatus, Finding, Source

__all__ = (
    "SourceRegistration",
    "REGISTRY",
    "list_sources",
    "scope_for",
    "degrade_on_exception",
)

_VALID_SCOPES = frozenset({"repo", "runtime"})


@dataclass(frozen=True)
class SourceRegistration:
    """One ``Source`` member's scope, judged subject, and implementing owner.

    ``scope`` is ``"repo"`` (reads only tracked files/git history, runs
    anywhere) or ``"runtime"`` (reads host state, cannot run in CI) — the same
    two values ``scripts/detectors.py``'s own ``DETECTOR = {"scope": ...}``
    declares. Every source registered here today is ``"repo"``; Story 6.3
    builds the scope-selection mechanism (``scope_for``,
    ``degrade_on_exception``) without registering one — Story 6.5's
    ``dashboard_drift`` is what introduces the first ``"runtime"`` member.

    ``subject_station`` is the station whose artifact this source judges;
    ``owning_station`` is the station whose ``gather()`` implements the
    judgement (always ``"doctor"`` today — Doctor holds every verdict).

    Fails loud at construction rather than accepting a default: a
    registration with no declared subject or owner, or a scope outside the
    closed pair above, is a defect in THIS FILE, not a value worth storing.
    """

    source: Source
    scope: str
    subject_station: str
    owning_station: str

    def __post_init__(self) -> None:
        if not isinstance(self.source, Source):
            raise ValueError(
                f"source must be a models.Source member, got {self.source!r}"
            )
        if not self.subject_station or not self.subject_station.strip():
            raise ValueError(
                f"{self.source!r}: subject_station must be a non-empty "
                f"station name, got {self.subject_station!r}"
            )
        if not self.owning_station or not self.owning_station.strip():
            raise ValueError(
                f"{self.source!r}: owning_station must be a non-empty "
                f"station name, got {self.owning_station!r}"
            )
        if self.scope not in _VALID_SCOPES:
            raise ValueError(
                f"{self.source!r}: scope must be one of "
                f"{sorted(_VALID_SCOPES)}, got {self.scope!r}"
            )

    def to_json_dict(self) -> dict[str, str]:
        """Serialize to the plain-dict shape ``scripts/detectors.py`` and any
        future consumer (the detector-ownership audit) both need — mirrors
        ``models.Finding.to_json_dict()``'s own convention rather than making
        each consumer hand-rebuild this dataclass's four fields."""
        return {
            "source": self.source.value,
            "scope": self.scope,
            "subject_station": self.subject_station,
            "owning_station": self.owning_station,
        }


# Subject/owner assignment, one row per Source member (each story's own Design
# Notes carries the full rationale per row). Every entry is
# owning_station="doctor" (Doctor holds every verdict) and scope="repo" --
# Story 6.3 builds the scope-selection mechanism without registering a
# "runtime" entry; Story 6.5's dashboard_drift is the first one. "repo" means
# "declares itself CI-safe," not "never reads host state": Story 6.4's
# STORY_STATUS is scope="repo" (matching its own script's DETECTOR
# declaration) despite reading `~/.bmad-loops` -- see its own row's comment
# below for why that classification is preserved rather than corrected here.
REGISTRY: tuple[SourceRegistration, ...] = (
    SourceRegistration(
        source=Source.WARDEN_DOCTOR,
        scope="repo",
        subject_station="warden",
        owning_station="doctor",
    ),  # relays warden's own self-report -- AD-11's existing exception
    SourceRegistration(
        source=Source.STALENESS_REPORT,
        scope="repo",
        subject_station="atlas",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.CVE_WATCHER,
        scope="repo",
        subject_station="atlas",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.BEHIND_UPSTREAM,
        scope="repo",
        subject_station="atlas",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.FEEDSTOCK_HEALTH,
        scope="repo",
        subject_station="atlas",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.RELEASE_CADENCE,
        scope="repo",
        subject_station="atlas",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.ENV_HYGIENE,
        scope="repo",
        subject_station="doctor",
        owning_station="doctor",
    ),  # Doctor's own repo-wide scan -- no other station's artifact judged
    SourceRegistration(
        source=Source.MARSHAL_DURABILITY,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.ADOPTION,
        scope="repo",
        subject_station="atlas",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.LEDGER_REGRESSION,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 6.4 -- ported from scripts/ledger_regression_check.py
    SourceRegistration(
        source=Source.STORY_STATUS,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 6.4 -- ported from scripts/story_status_check.py; scope stays
    # "repo" per the original script's own DETECTOR declaration even though
    # gather_story_status reads host state (~/.bmad-loops) -- preserve, don't
    # redesign (see the story spec's Design Notes).
)


def list_sources() -> tuple[SourceRegistration, ...]:
    """Return the full registered ``REGISTRY``.

    The one place both the detector-ownership audit and
    ``scripts/detectors.py``'s ``_doctor_sources()`` read from.
    """
    return REGISTRY


def scope_for(source: Source) -> str:
    """Return ``source``'s registered scope (``"repo"`` or ``"runtime"``).

    The one canonical per-source scope lookup — Story 6.3's ``doctor check
    --scope`` filter reads through THIS function rather than a second
    hand-rolled loop over ``REGISTRY``, so a future ``SourceRegistration``'s
    scope change (e.g. a source moving from ``"repo"`` to ``"runtime"``)
    cannot silently desync a duplicated call site.

    Raises ``ValueError`` if ``source`` has no ``REGISTRY`` entry — this
    module's own exhaustiveness test
    (``test_every_source_member_has_exactly_one_registry_entry``) already
    guarantees every current ``Source`` member resolves; a ``source`` that
    reaches this branch is a bug in ``REGISTRY``, not a value worth
    defaulting past.
    """
    for registration in REGISTRY:
        if registration.source is source:
            return registration.scope
    raise ValueError(f"{source!r} has no REGISTRY entry")


def degrade_on_exception(
    source: Source,
    check: str,
    gather: Callable[[], tuple[Finding, ...]],
) -> tuple[Finding, ...]:
    """Run ``gather()``; convert any raised ``Exception`` into exactly one
    WARN ``Finding`` naming it, rather than letting it propagate.

    This is the reusable "cannot evaluate here" path a ``scope="runtime"``
    source needs (Story 6.5+'s ``dashboard_drift`` and whatever follows it):
    unlike ``sources/warden.py``, ``sources/marshal.py``, and
    ``checks/env_hygiene.py`` — whose own ``gather`` functions already
    document and enforce their own "degrades, never crashes" contract (see
    ``sources/marshal.py``'s module docstring) — a source whose inputs are
    host state (tmux, ``~/.bmad-loops``) that is simply ABSENT outside an
    operator's own machine has no such contract to lean on yet. This helper
    is that contract, generalized, for a caller that wraps its own raw
    host-state read with it.

    Deliberately NOT wired into today's three existing (repo-scope)
    dispatch calls in ``__main__.py`` — an exception escaping one of THOSE
    today would be a real bug in a module that already promises never to
    raise, and must keep propagating to ``main()``'s own top-level
    exception net (exit 2), never get silently reclassified as WARN (see
    the story spec's Design Notes).

    Catches ``Exception``, never ``BaseException`` — a ``KeyboardInterrupt``
    or ``SystemExit`` raised inside ``gather`` must still propagate
    untouched, mirroring ``main()``'s own three-tier handler ordering.
    """
    try:
        return gather()
    except Exception as exc:  # noqa: BLE001 -- this IS the degrade
        # boundary this function exists to provide, not a suppressed bug.
        return (
            Finding(
                source=source,
                check=check,
                status=DoctorStatus.WARN,
                message=(
                    f"{check} could not be evaluated here — "
                    f"{exc.__class__.__name__}: {exc}"
                ),
                evidence={"exception": exc.__class__.__name__},
            ),
        )
