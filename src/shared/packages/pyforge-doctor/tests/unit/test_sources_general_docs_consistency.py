"""Unit tests for ``sources.general_docs_consistency`` (Story 22.3)."""

from __future__ import annotations

from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import general_docs_consistency

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "general_docs_consistency"


def _write_station_tree(
    target: Path,
    *,
    station: str,
    readme_text: str,
    skill_brief_text: str,
) -> None:
    package = target / "src" / "shared" / "packages" / f"pyforge-{station}"
    package.mkdir(parents=True, exist_ok=True)
    (package / "README.md").write_text(readme_text, encoding="utf-8")
    brief_dir = target / ".claude" / "skills" / f"pyforge-{station}"
    brief_dir.mkdir(parents=True, exist_ok=True)
    (brief_dir / "skill-brief.yaml").write_text(skill_brief_text, encoding="utf-8")


def _write_agents_and_herald_dream(
    target: Path,
    *,
    agents_text: str,
    dream_text: str,
) -> None:
    target.joinpath("AGENTS.md").write_text(agents_text, encoding="utf-8")
    dreams = target / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    (dreams / "pyforge-herald.md").write_text(dream_text, encoding="utf-8")


def test_pre_story_22_1_doctor_readme_fires_against_skill_brief(tmp_path: Path):
    readme = (_FIXTURES / "pre" / "doctor" / "README.md").read_text(encoding="utf-8")
    brief = (_FIXTURES / "doctor-skill-brief.yaml").read_text(encoding="utf-8")
    _write_station_tree(tmp_path, station="doctor", readme_text=readme, skill_brief_text=brief)

    findings = general_docs_consistency.find_station_gate_advisory_contradictions(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.source == Source.GENERAL_DOCS_CONSISTENCY
    assert finding.check == "general-docs-station-gate-advisory"
    assert finding.status == DoctorStatus.WARN
    assert "exit-code gate" in finding.evidence["readme_quote"]
    assert "not a second PR gate" in finding.evidence["skill_brief_quote"]


def test_post_story_22_1_doctor_readme_is_silent(tmp_path: Path):
    readme = (_FIXTURES / "post" / "doctor" / "README.md").read_text(encoding="utf-8")
    brief = (_FIXTURES / "doctor-skill-brief.yaml").read_text(encoding="utf-8")
    _write_station_tree(tmp_path, station="doctor", readme_text=readme, skill_brief_text=brief)

    findings = general_docs_consistency.find_station_gate_advisory_contradictions(tmp_path)
    assert findings == ()


def test_pre_story_22_1_agents_herald_fires_against_herald_dream(tmp_path: Path):
    agents = (_FIXTURES / "pre" / "AGENTS.md").read_text(encoding="utf-8")
    dream = (_FIXTURES / "pyforge-herald-dream.md").read_text(encoding="utf-8")
    _write_agents_and_herald_dream(tmp_path, agents_text=agents, dream_text=dream)

    findings = general_docs_consistency.find_agents_herald_marshal_contradiction(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "general-docs-agents-herald-marshal"
    assert finding.status == DoctorStatus.WARN
    assert "Herald's" in finding.evidence["agents_quote"]
    assert "pyforge-marshal" in finding.evidence["dream_quote"]


def test_post_story_22_1_agents_herald_is_silent(tmp_path: Path):
    agents = (_FIXTURES / "post" / "AGENTS.md").read_text(encoding="utf-8")
    dream = (_FIXTURES / "pyforge-herald-dream.md").read_text(encoding="utf-8")
    _write_agents_and_herald_dream(tmp_path, agents_text=agents, dream_text=dream)

    findings = general_docs_consistency.find_agents_herald_marshal_contradiction(tmp_path)
    assert findings == ()


def test_clean_station_warden_does_not_false_positive(tmp_path: Path):
    readme = (_FIXTURES / "clean" / "warden" / "README.md").read_text(encoding="utf-8")
    brief = (_FIXTURES / "clean" / "warden" / "skill-brief.yaml").read_text(encoding="utf-8")
    _write_station_tree(tmp_path, station="warden", readme_text=readme, skill_brief_text=brief)
    agents = (_FIXTURES / "post" / "AGENTS.md").read_text(encoding="utf-8")
    dream = (_FIXTURES / "pyforge-herald-dream.md").read_text(encoding="utf-8")
    _write_agents_and_herald_dream(tmp_path, agents_text=agents, dream_text=dream)

    findings = general_docs_consistency.gather(tmp_path)
    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.OK


def test_unreadable_source_emits_named_finding(tmp_path: Path):
    package = tmp_path / "src" / "shared" / "packages" / "pyforge-doctor"
    package.mkdir(parents=True, exist_ok=True)
    readme = package / "README.md"
    readme.write_text("placeholder", encoding="utf-8")
    brief_dir = tmp_path / ".claude" / "skills" / "pyforge-doctor"
    brief_dir.mkdir(parents=True, exist_ok=True)
    brief = brief_dir / "skill-brief.yaml"
    brief.write_text(
        (_FIXTURES / "doctor-skill-brief.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    readme.chmod(0o000)
    try:
        findings = general_docs_consistency.find_station_gate_advisory_contradictions(tmp_path)
    finally:
        readme.chmod(0o644)
    assert len(findings) == 1
    assert findings[0].check == "general-docs-unreadable"
    assert findings[0].status == DoctorStatus.WARN


def test_ambiguous_station_without_comparable_claims_is_silent(tmp_path: Path):
    _write_station_tree(
        tmp_path,
        station="atlas",
        readme_text="# pyforge-atlas\n\nProvides data pipelines.\n",
        skill_brief_text="name: pyforge-atlas\ndescription: Atlas station.\n",
    )

    findings = general_docs_consistency.find_station_gate_advisory_contradictions(tmp_path)
    assert findings == ()


def test_live_repo_gather_no_longer_fires_after_story_22_1_landed():
    """Live proof, mirroring Story 21.9's discipline (never validate only
    against a fully-synthetic fixture): at authoring time this detector fired
    against the real, live Story 22.1 contradictions (doctor's own
    README.md/AGENTS.md). Story 22.1 has since landed and corrected both --
    the stronger live proof now available is that the corrected repo produces
    neither warn, confirmed against the real files, not a frozen copy. The
    `pre`/`post` fixtures (test_pre_story_22_1_doctor_readme_fires_against_
    skill_brief / test_post_story_22_1_doctor_readme_is_silent and their
    AGENTS/Herald counterparts above) remain the authoritative, stable
    regression coverage for the fire/no-fire behavior itself."""
    repo_root = Path(__file__).resolve().parents[6]
    findings = general_docs_consistency.gather(repo_root)
    warns = [f for f in findings if f.status == DoctorStatus.WARN]
    checks = {f.check for f in warns}
    assert "general-docs-station-gate-advisory" not in checks
    assert "general-docs-agents-herald-marshal" not in checks
