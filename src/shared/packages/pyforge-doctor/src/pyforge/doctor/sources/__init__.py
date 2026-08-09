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
only builds the mechanism and covers today's 9.

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
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import Source

__all__ = ("SourceRegistration", "REGISTRY", "list_sources")

_VALID_SCOPES = frozenset({"repo", "runtime"})


@dataclass(frozen=True)
class SourceRegistration:
    """One ``Source`` member's scope, judged subject, and implementing owner.

    ``scope`` is ``"repo"`` (reads only tracked files/git history, runs
    anywhere) or ``"runtime"`` (reads host state, cannot run in CI) — the same
    two values ``scripts/detectors.py``'s own ``DETECTOR = {"scope": ...}``
    declares. Every source registered here today is ``"repo"``; Story 6.3
    is what introduces the first ``"runtime"`` member.

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


# Subject/owner assignment for today's 9 sources (story's Design Notes carries
# the full rationale per row). All nine are owning_station="doctor" (Doctor
# holds every verdict) and scope="repo" (none reads host/tmux state yet --
# Story 6.3 is what introduces "runtime").
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
)


def list_sources() -> tuple[SourceRegistration, ...]:
    """Return the full registered ``REGISTRY``.

    The one place both the detector-ownership audit and
    ``scripts/detectors.py``'s ``_doctor_sources()`` read from.
    """
    return REGISTRY
