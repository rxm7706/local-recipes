"""Unit tests for roster-derived constitutive slugs in ``sources/chain.py``
(Story 21.4).
"""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import chain


def _write_roster(
    target: Path,
    *,
    guild_dreams: list[str] | None = None,
    malformed: bool = False,
) -> None:
    path = target / "docs" / "governance" / "guild-roster.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if malformed:
        path.write_text("{not json", encoding="utf-8")
        return
    payload = {
        "stations": [
            "herald",
            "marshal",
            "atlas",
            "warden",
            "mason",
            "doctor",
            "scribe",
            "steward",
        ],
        "guild_dreams": guild_dreams if guild_dreams is not None else ["pyforge-charter"],
        "dream_statuses": [
            "dreamt",
            "pitched",
            "specified",
            "realized",
            "archived",
        ],
        "dream_types": ["dream", "practice"],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_dream(target: Path, slug: str, owner: str) -> None:
    path = target / "docs" / "dreams" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nowner: {owner}\nstatus: draft\n---\n\nbody\n",
        encoding="utf-8",
    )


def _write_spec(target: Path, project: str, spec_dir: str, *, owner_dream: str) -> None:
    path = target / "_bmad-output" / "projects" / project / "planning-artifacts" / "specs" / spec_dir / "SPEC.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nowner-dream: docs/dreams/{owner_dream}.md\n---\n",
        encoding="utf-8",
    )


def test_constitutive_from_single_entry_roster_exempts_charter(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(tmp_path, "pyforge-charter", "guild")
    _write_spec(
        tmp_path,
        "docs/governance",
        "spec-pyforge-charter",
        owner_dream="pyforge-charter",
    )

    findings = chain.gather_dream_chain(tmp_path)

    assert not any(f.check == "owner-unassigned" for f in findings)
    assert not any(f.check == "constitutive-roster-degraded" for f in findings)


def test_constitutive_honors_second_guild_dreams_entry(tmp_path: Path) -> None:
    _write_roster(tmp_path, guild_dreams=["pyforge-charter", "another-constitutive"])
    _write_dream(tmp_path, "another-constitutive", "guild")
    _write_spec(
        tmp_path,
        "docs/governance",
        "spec-another-constitutive",
        owner_dream="another-constitutive",
    )

    findings = chain.gather_dream_chain(tmp_path)

    assert not any(f.check == "owner-unassigned" for f in findings)


def test_constitutive_missing_roster_degrades_with_named_warn(tmp_path: Path) -> None:
    _write_dream(tmp_path, "pyforge-charter", "guild")
    _write_spec(
        tmp_path,
        "docs/governance",
        "spec-pyforge-charter",
        owner_dream="pyforge-charter",
    )

    findings = chain.gather_dream_chain(tmp_path)

    degraded = [f for f in findings if f.check == "constitutive-roster-degraded"]
    assert len(degraded) == 1
    finding = degraded[0]
    assert finding.source is Source.DREAM_CHAIN
    assert finding.status is DoctorStatus.WARN
    assert "pyforge-charter" in finding.message
    assert not any(f.check == "owner-unassigned" for f in findings)


def test_constitutive_malformed_roster_degrades_with_named_warn(tmp_path: Path) -> None:
    _write_roster(tmp_path, malformed=True)
    _write_dream(tmp_path, "unassigned", "guild")

    findings = chain.gather_dream_chain(tmp_path)

    degraded = [f for f in findings if f.check == "constitutive-roster-degraded"]
    assert len(degraded) == 1
    assert degraded[0].status is DoctorStatus.WARN
    assert any(f.check == "owner-unassigned" for f in findings)
