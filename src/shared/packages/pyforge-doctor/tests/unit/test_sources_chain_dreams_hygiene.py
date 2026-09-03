"""Unit tests for ``pyforge.doctor.sources.chain.gather_dreams_hygiene``
(Story 17.2 / FR-147) — Dream-tier hygiene mode invoked as
``python -m pyforge.doctor.sources dream-chain --dreams``.

Covers the story I/O matrix against temp fixture trees only. Does not
mutate the live Dream tree. Does not assert INV-0..3 findings (those stay
on ``gather_dream_chain``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import __main__ as dispatch
from pyforge.doctor.sources import chain

# --- fixture helpers ---------------------------------------------------------


def _write_roster(target: Path) -> None:
    path = target / "docs" / "governance" / "guild-roster.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
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
                "guild_dreams": ["pyforge-charter"],
                "dream_statuses": [
                    "dreamt",
                    "pitched",
                    "specified",
                    "realized",
                    "archived",
                ],
                "dream_types": ["dream", "practice"],
            }
        ),
        encoding="utf-8",
    )


def _write_dream(
    target: Path,
    slug: str,
    *,
    owner: str = "marshal",
    status: str = "dreamt",
    title: str | None = "A Dream",
    dtype: str = "dream",
    realization_log: bool = False,
) -> Path:
    path = target / "docs" / "dreams" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"owner: {owner}", f"status: {status}", f"type: {dtype}"]
    if title is not None:
        lines.append(f"title: {title}")
    lines += ["---", "", "body"]
    if realization_log:
        lines += ["", "## Realization log", "", "- noted"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_readme(target: Path, rows: list[tuple[str, str]]) -> None:
    path = target / "docs" / "dreams" / "README.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Dreams",
        "",
        "| Dream | Status | What it is |",
        "|---|---|---|",
    ]
    for filename, status in rows:
        lines.append(f"| [`{filename}`]({filename}) | {status} | desc |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _clean_hygiene_tree(target: Path) -> None:
    """One conformant Dream + matching README row + roster."""
    _write_roster(target)
    _write_dream(
        target,
        "foo",
        status="realized",
        title="Foo",
        realization_log=True,
    )
    _write_readme(target, [("foo.md", "realized")])


# --- matrix -----------------------------------------------------------------


def test_happy_path_reports_ok(tmp_path: Path) -> None:
    _clean_hygiene_tree(tmp_path)
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert len(findings) == 1
    assert findings[0].source is Source.DREAMS_HYGIENE
    assert findings[0].check == "dreams-hygiene"
    assert findings[0].status is DoctorStatus.OK


def test_bad_status_reports_dream_vocab(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(tmp_path, "foo", status="building", realization_log=True)
    _write_readme(tmp_path, [])
    findings = chain.gather_dreams_hygiene(tmp_path)
    kinds = {f.check for f in findings}
    assert "dream-vocab" in kinds
    assert all(f.source is Source.DREAMS_HYGIENE for f in findings)


def test_bad_owner_reports_dream_unowned(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(tmp_path, "foo", owner="crew", realization_log=True)
    _write_readme(tmp_path, [])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert any(f.check == "dream-unowned" for f in findings)


def test_missing_title_reports(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(tmp_path, "foo", title=None, realization_log=False)
    _write_readme(tmp_path, [])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert any(f.check == "missing-title" for f in findings)


def test_realized_without_realization_log_reports(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(
        tmp_path, "foo", status="realized", title="Foo", realization_log=False
    )
    _write_readme(tmp_path, [])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert any(f.check == "realization-log-missing" for f in findings)


def test_historical_section_too_long_on_fixture(tmp_path: Path) -> None:
    """Story 43.1: fires on a long *historical* section, not on conformant Dreams."""
    _write_roster(tmp_path)
    body_lines = [
        "---",
        "owner: steward",
        "status: specified",
        "type: dream",
        "title: Hist",
        "---",
        "",
        "intro",
        "",
        "## Historical illustration (do not build)",
    ]
    body_lines += [f"line {i}" for i in range(25)]
    body_lines += ["", "## Realization log", "", "- noted"]
    path = tmp_path / "docs" / "dreams" / "hist-fixture.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body_lines) + "\n", encoding="utf-8")
    _write_readme(tmp_path, [])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert any(f.check == "historical-section-too-long" for f in findings)


def test_living_unifying_strategy_has_no_historical_section_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: post-43.1 living Dream must not trip its own detector."""
    repo = Path(__file__).resolve().parents[6]
    monkeypatch.chdir(repo)
    findings = chain.gather_dreams_hygiene(repo)
    hist = [f for f in findings if f.check == "historical-section-too-long"]
    assert not any(
        f.evidence.get("subject") == "pyforge-unifying-strategy" for f in hist
    )


def test_dreamt_may_omit_realization_log(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(
        tmp_path, "foo", status="dreamt", title="Foo", realization_log=False
    )
    _write_readme(tmp_path, [])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert not any(f.check == "realization-log-missing" for f in findings)
    assert findings[0].check == "dreams-hygiene"
    assert findings[0].status is DoctorStatus.OK


def test_readme_table_orphan_reports(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(
        tmp_path, "foo", status="dreamt", title="Foo", realization_log=False
    )
    _write_readme(tmp_path, [("missing.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert any(f.check == "readme-table-orphan" for f in findings)


def test_readme_table_status_drift_reports(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(
        tmp_path, "foo", status="realized", title="Foo", realization_log=True
    )
    _write_readme(tmp_path, [("foo.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert any(f.check == "readme-table-drift" for f in findings)


def test_default_dream_chain_does_not_emit_hygiene_kinds(tmp_path: Path) -> None:
    """INV gather stays INV-only — no hygiene kinds leak into default mode."""
    _write_roster(tmp_path)
    _write_dream(tmp_path, "foo", status="building", title="Foo")
    _write_readme(tmp_path, [("foo.md", "dreamt")])
    findings = chain.gather_dream_chain(tmp_path)
    hygiene_kinds = {
        "dream-vocab",
        "dream-unowned",
        "missing-title",
        "realization-log-missing",
        "readme-table-drift",
        "readme-table-orphan",
        "dreams-hygiene",
    }
    assert not hygiene_kinds.intersection({f.check for f in findings})
    assert any(f.check == "dream-without-spec" for f in findings)


def test_cli_dreams_flag_dispatches_hygiene(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clean_hygiene_tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = dispatch.main(["dream-chain", "--dreams", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    assert "dreams-hygiene" in out
    assert "dream-without-spec" not in out


def test_cli_dreams_flag_rejected_on_other_source() -> None:
    with pytest.raises(SystemExit) as excinfo:
        dispatch.main(["bmad-drift", "--dreams"])
    assert excinfo.value.code == 2
