"""Story 53.2 — in-repo Frame preflight (not upstream validate_frames.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.steward.frames import (
    COMPANY_NAME,
    EXPECTED_COUNT,
    STATION_TOKENS,
    VALID_TYPES,
    main,
    preflight_frames,
)

REQUIRED = ("type", "name", "description", "visibility", "owner")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / "docs" / "dreams").is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def _write_frame(
    path: Path,
    *,
    type_: str = "frame [0.2]",
    name: str,
    description: str = "test frame",
    visibility: str = "private",
    owner: str = "steward",
    inherits: str | None = None,
    extra: str = "",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"type: {type_}",
        f"name: {name}",
        f"description: {description}",
        f"visibility: {visibility}",
        f"owner: {owner}",
    ]
    if inherits is not None:
        lines.append(f"inherits: {inherits}")
    if extra:
        lines.append(extra.rstrip())
    lines.append("---")
    lines.append("")
    lines.append("# body")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _seed_valid_tree(root: Path) -> Path:
    frames = root / "docs" / "foundry" / "frames"
    _write_frame(
        frames / "pyforge.frame.md",
        name=COMPANY_NAME,
        owner="steward/guild",
        description="company",
    )
    for token in STATION_TOKENS:
        _write_frame(
            frames / "stations" / f"{token}.frame.md",
            name=f"pyforge-{token}",
            owner=token,
            inherits=COMPANY_NAME,
            description=f"{token} station",
        )
    return frames


def test_live_repo_has_exactly_nine_valid_frames() -> None:
    report = preflight_frames(_repo_root())
    assert report.ok, "\n".join(f.message for f in report.findings)
    assert len(report.frames) == EXPECTED_COUNT
    names = {doc.fields["name"] for doc in report.frames}
    assert COMPANY_NAME in names
    assert {f"pyforge-{t}" for t in STATION_TOKENS} <= names
    for doc in report.frames:
        for key in REQUIRED:
            assert doc.fields.get(key), f"{doc.path} missing {key}"
        assert doc.fields["type"] in VALID_TYPES


def test_live_station_frames_inherit_company_by_name() -> None:
    report = preflight_frames(_repo_root())
    company = next(d for d in report.frames if d.fields["name"] == COMPANY_NAME)
    assert company.fields.get("inherits") in (None, [], "")
    stations = [d for d in report.frames if d.fields["name"] != COMPANY_NAME]
    assert len(stations) == 8
    for doc in stations:
        assert doc.fields.get("inherits") == COMPANY_NAME


def test_fixture_tree_passes(tmp_path: Path) -> None:
    _seed_valid_tree(tmp_path)
    report = preflight_frames(tmp_path)
    assert report.ok, [f.message for f in report.findings]


def test_missing_required_field_fails(tmp_path: Path) -> None:
    frames = _seed_valid_tree(tmp_path)
    broken = frames / "stations" / "herald.frame.md"
    text = broken.read_text(encoding="utf-8")
    broken.write_text(text.replace("owner: herald\n", ""), encoding="utf-8")
    report = preflight_frames(tmp_path)
    assert not report.ok
    assert any(f.code == "missing-field" and "owner" in f.message for f in report.findings)


@pytest.mark.parametrize("field", REQUIRED)
def test_each_required_field_blank_fails(tmp_path: Path, field: str) -> None:
    frames = _seed_valid_tree(tmp_path)
    path = frames / "pyforge.frame.md"
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{field}:"):
            lines.append(f"{field}:")
        else:
            lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = preflight_frames(tmp_path)
    assert not report.ok
    assert any(f.code == "missing-field" and field in f.message for f in report.findings)


def test_station_without_inherits_fails(tmp_path: Path) -> None:
    frames = _seed_valid_tree(tmp_path)
    _write_frame(
        frames / "stations" / "herald.frame.md",
        name="pyforge-herald",
        owner="herald",
        inherits=None,
    )
    report = preflight_frames(tmp_path)
    assert not report.ok
    assert any(f.code == "inherits" for f in report.findings)


def test_inherits_relative_path_to_company_passes(tmp_path: Path) -> None:
    frames = _seed_valid_tree(tmp_path)
    _write_frame(
        frames / "stations" / "herald.frame.md",
        name="pyforge-herald",
        owner="herald",
        inherits="../pyforge.frame.md",
    )
    report = preflight_frames(tmp_path)
    assert report.ok, [f.message for f in report.findings]


def test_wrong_count_fails(tmp_path: Path) -> None:
    frames = _seed_valid_tree(tmp_path)
    (frames / "community.frame.md").write_text(
        "---\ntype: frame\nname: community\ndescription: no\n"
        "visibility: public\nowner: nobody\n---\n",
        encoding="utf-8",
    )
    report = preflight_frames(tmp_path)
    assert not report.ok
    assert any(f.code == "count" for f in report.findings)


def test_invalid_type_fails(tmp_path: Path) -> None:
    frames = _seed_valid_tree(tmp_path)
    _write_frame(
        frames / "pyforge.frame.md",
        type_="frame [0.2.0]",
        name=COMPANY_NAME,
        owner="steward/guild",
    )
    report = preflight_frames(tmp_path)
    assert not report.ok
    assert any(f.code == "type" for f in report.findings)


def test_cli_exits_one_on_findings(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp_path.mkdir(exist_ok=True)
    assert main(["--repo", str(tmp_path)]) == 1
    assert "frame-preflight:" in capsys.readouterr().out


def test_cli_exits_zero_on_ok(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _seed_valid_tree(tmp_path)
    assert main(["--repo", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "ok" in out
    assert "9 Frames" in out
