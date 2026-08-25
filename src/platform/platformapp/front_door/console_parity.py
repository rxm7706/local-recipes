"""FR-6 inventory as a machine-checked Canopy home map (steward 30.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Kind = Literal["runtime", "mixed", "build"]
HomeKind = Literal["lane1", "portal"]


@dataclass(frozen=True, slots=True)
class Surface:
    surface_id: str
    classification: Kind
    title: str


@dataclass(frozen=True, slots=True)
class Home:
    kind: HomeKind
    path: str
    label: str


SURFACES: tuple[Surface, ...] = (
    Surface("dreams", "runtime", "Dreams"),
    Surface("specs", "runtime", "The Specs"),
    Surface("story_specs", "runtime", "Story Specs"),
    Surface("campaigns", "runtime", "Campaigns"),
    Surface("command_center", "runtime", "Command Center"),
    Surface("launch_readiness", "runtime", "Launch Readiness"),
    Surface("fleet_progress_tracked", "runtime", "Fleet picture (tracked)"),
    Surface("pitch", "runtime", "The Pitch"),
    Surface("guild", "runtime", "The Guild"),
    Surface("backlog", "runtime", "Backlog"),
    Surface("open_work", "runtime", "Open work"),
    Surface("archived", "runtime", "Archived"),
    Surface("fleet_table", "runtime", "Fleet"),
    Surface("program_story_status", "runtime", "Program story status"),
    Surface("fleet_chain_audit_badge", "mixed", "Fleet chain audit badge"),
    Surface("health_ci_overlay", "mixed", "Sync & Health on production"),
    Surface("in_build_realized_membership", "mixed", "In Build / Realized membership"),
    Surface("running_chip", "build", "Status chip (running)"),
    Surface("inflight_card", "build", "In-flight card"),
    Surface("fleet_live_overlay", "build", "Fleet picture live overlay"),
    Surface("detector_verdicts", "build", "Sync & Health detectors"),
    Surface("editorial_blocks", "build", "Curated narrative blocks"),
    Surface("journal_timing", "build", "Derived timing and velocity"),
)

HOMES: dict[str, Home] = {
    "dreams": Home("lane1", "/console/dreams/", "Lane 1 dreams"),
    "specs": Home("lane1", "/console/specs/", "Lane 1 specs"),
    "story_specs": Home("lane1", "/console/story-specs/", "Lane 1 story specs"),
    "campaigns": Home("portal", "/stations/marshal/", "Marshal portal"),
    "command_center": Home("portal", "/stations/steward/", "Steward portal"),
    "launch_readiness": Home("portal", "/stations/steward/", "Steward portal"),
    "fleet_progress_tracked": Home("portal", "/stations/doctor/", "Doctor portal"),
    "pitch": Home("portal", "/stations/herald/", "Herald portal"),
    "guild": Home("lane1", "/console/guild/", "Lane 1 guild"),
    "backlog": Home("lane1", "/console/backlog/", "Lane 1 backlog"),
    "open_work": Home("lane1", "/console/open-work/", "Lane 1 open work"),
    "archived": Home("lane1", "/console/archived/", "Lane 1 archived"),
    "fleet_table": Home("portal", "/stations/doctor/", "Doctor portal"),
    "program_story_status": Home("lane1", "/console/programs/", "Lane 1 programs"),
    "fleet_chain_audit_badge": Home("portal", "/stations/doctor/", "Doctor portal"),
    "health_ci_overlay": Home("lane1", "/console/health/", "Lane 1 health cache"),
    "in_build_realized_membership": Home(
        "lane1",
        "/console/programs/",
        "Lane 1 programs",
    ),
    "running_chip": Home("lane1", "/runs/", "Supervisor run board"),
    "inflight_card": Home("lane1", "/runs/", "Supervisor run board"),
    "fleet_live_overlay": Home("lane1", "/runs/", "Supervisor run board"),
    "detector_verdicts": Home("lane1", "/console/health/", "Lane 1 health cache"),
    "editorial_blocks": Home("lane1", "/console/editorial/", "Lane 1 CMS editorial"),
    "journal_timing": Home("lane1", "/runs/", "Supervisor run board"),
}

PARITY_CLASSIFICATIONS: frozenset[Kind] = frozenset({"runtime", "mixed"})


def inventory_ids() -> frozenset[str]:
    return frozenset(row.surface_id for row in SURFACES)


def parity_ids() -> frozenset[str]:
    return frozenset(
        row.surface_id
        for row in SURFACES
        if row.classification in PARITY_CLASSIFICATIONS
    )


class MissingParityHomeError(RuntimeError):
    """A runtime-reproducible or mixed inventory row has no named home."""


def require_parity_homes() -> dict[str, Home]:
    """Raise if any runtime-reproducible or mixed row lacks a named home."""
    missing = sorted(parity_ids() - frozenset(HOMES))
    if missing:
        joined = ", ".join(missing)
        raise MissingParityHomeError(joined)
    return {surface_id: HOMES[surface_id] for surface_id in sorted(parity_ids())}


def directory_rows() -> list[tuple[Surface, Home]]:
    extra = ("detector_verdicts", "editorial_blocks", "running_chip")
    wanted = parity_ids() | frozenset(extra)
    by_id = {row.surface_id: row for row in SURFACES}
    rows: list[tuple[Surface, Home]] = []
    for surface_id in sorted(wanted):
        home = HOMES.get(surface_id)
        surface = by_id.get(surface_id)
        if home is None or surface is None:
            continue
        rows.append((surface, home))
    return rows
