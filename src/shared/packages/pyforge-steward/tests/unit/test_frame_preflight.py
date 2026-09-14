"""Story 53.2 / 53.6 — in-repo Frame preflight (not upstream validate_frames.py).

53.6 moved identity from ``name`` to ``identifier``. v0.3 §4.2.1 makes
``identifier`` the mandatory identity element and recommends a ``qualified-ref``
(``publisher "/" frame-name``, §5.3); ``name`` aliases ``title``, which the
element profile marks *MUST NOT be slug-constrained*. So the live Frames are
``pyforge/company`` and ``pyforge/<station>``, and ``name`` is now the prose
form the Charter's branding law asks for (``PyForge Steward``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.steward.frames import (
    COMPANY_IDENTIFIER,
    EXPECTED_COUNT,
    PUBLISHER,
    STATION_TOKENS,
    _type_is_frame,
    main,
    preflight_frames,
)

REQUIRED = ("type", "identifier", "name", "description", "visibility", "maintainer")
#: The subset that is a plain scalar, so blanking it is a one-line edit.
SCALAR_REQUIRED = ("type", "identifier", "name", "description", "visibility")


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
    identifier: str,
    name: str | None = None,
    description: str = "test frame",
    visibility: str = "private",
    maintainer: list[str] | str | None = None,
    inherits: list[str] | str | None = None,
    extra: str = "",
) -> None:
    """``maintainer``/``inherits`` accept a str so a test can write the scalar
    shape v0.3 §6.2.1 forbids a writer from emitting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"type: {type_}",
        f"identifier: {identifier}",
        f"name: {name if name is not None else identifier}",
        f"description: {description}",
        f"visibility: {visibility}",
    ]
    if maintainer is None:
        maintainer = ["steward"]
    if isinstance(maintainer, str):
        lines.append(f"maintainer: {maintainer}")
    else:
        lines.append("maintainer:")
        lines.extend(f"  - {m}" for m in maintainer)
    if inherits is not None:
        if isinstance(inherits, str):
            lines.append(f"inherits: {inherits}")
        else:
            lines.append("inherits:")
            lines.extend(f"  - {i}" for i in inherits)
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
        identifier=COMPANY_IDENTIFIER,
        name="PyForge",
        maintainer=["steward", "guild"],
        description="company",
    )
    for token in STATION_TOKENS:
        _write_frame(
            frames / "stations" / f"{token}.frame.md",
            identifier=f"{PUBLISHER}/{token}",
            name=f"PyForge {token.capitalize()}",
            maintainer=[token],
            inherits=[COMPANY_IDENTIFIER],
            description=f"{token} station",
        )
    return frames


def test_live_repo_has_exactly_nine_valid_frames() -> None:
    report = preflight_frames(_repo_root())
    assert report.ok, "\n".join(f.message for f in report.findings)
    assert len(report.frames) == EXPECTED_COUNT
    identifiers = {doc.fields["identifier"] for doc in report.frames}
    assert COMPANY_IDENTIFIER in identifiers
    assert {f"{PUBLISHER}/{t}" for t in STATION_TOKENS} <= identifiers
    for doc in report.frames:
        for key in REQUIRED:
            assert doc.fields.get(key), f"{doc.path} missing {key}"
        assert _type_is_frame(doc.fields["type"])


def test_live_frames_carry_a_qualified_ref_identifier() -> None:
    """v0.3 §4.2.1 SHOULD: a URI or a ``qualified-ref`` — exactly one ``/``,
    and no ``@``, which §5.3 reserves as the version separator."""
    report = preflight_frames(_repo_root())
    for doc in report.frames:
        ident = doc.fields["identifier"]
        assert ident.count("/") == 1, f"{doc.path}: {ident!r} is not a qualified-ref"
        assert "@" not in ident, f"{doc.path}: {ident!r} must not contain '@'"
        assert ident.split("/")[0] == PUBLISHER


def test_live_names_are_prose_not_slugs() -> None:
    """The element profile marks ``title`` (aliased ``name``) MUST NOT be
    slug-constrained, and the Charter's branding law wants ``PyForge Steward``
    in prose with ``pyforge-steward`` reserved for code."""
    report = preflight_frames(_repo_root())
    for doc in report.frames:
        name = doc.fields["name"]
        assert name.startswith("PyForge"), f"{doc.path}: {name!r}"
        assert "-" not in name, f"{doc.path}: {name!r} is still a slug"


def test_live_repeatable_fields_are_sequences() -> None:
    """v0.3 §6.2.1: 'A writer MUST emit a sequence' for a repeatable element."""
    report = preflight_frames(_repo_root())
    for doc in report.frames:
        assert isinstance(doc.fields["maintainer"], list), doc.path
        if "inherits" in doc.fields:
            assert isinstance(doc.fields["inherits"], list), doc.path


def test_live_station_frames_inherit_the_company_frame() -> None:
    report = preflight_frames(_repo_root())
    company = next(
        d for d in report.frames if d.fields["identifier"] == COMPANY_IDENTIFIER
    )
    assert company.fields.get("inherits") in (None, [], "")
    stations = [d for d in report.frames if d.fields["identifier"] != COMPANY_IDENTIFIER]
    assert len(stations) == 8
    for doc in stations:
        assert doc.fields.get("inherits") == [COMPANY_IDENTIFIER]


def test_fixture_tree_passes(tmp_path: Path) -> None:
    _seed_valid_tree(tmp_path)
    report = preflight_frames(tmp_path)
    assert report.ok, [f.message for f in report.findings]


def test_missing_required_field_fails(tmp_path: Path) -> None:
    frames = _seed_valid_tree(tmp_path)
    broken = frames / "stations" / "herald.frame.md"
    text = broken.read_text(encoding="utf-8")
    broken.write_text(text.replace("maintainer:\n  - herald\n", ""), encoding="utf-8")
    report = preflight_frames(tmp_path)
    assert not report.ok
    assert any(
        f.code == "missing-field" and "maintainer" in f.message for f in report.findings
    )


@pytest.mark.parametrize("field", SCALAR_REQUIRED)
def test_each_required_scalar_field_blank_fails(tmp_path: Path, field: str) -> None:
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


@pytest.mark.parametrize("field", ("maintainer", "inherits"))
def test_scalar_repeatable_field_is_reported(tmp_path: Path, field: str) -> None:
    """A scalar stays *readable* — the company Frame still resolves and the
    station still inherits — but emitting one is what §6.2.1 forbids, so the
    preflight must say so rather than pass it silently."""
    frames = _seed_valid_tree(tmp_path)
    _write_frame(
        frames / "stations" / "herald.frame.md",
        identifier=f"{PUBLISHER}/herald",
        name="PyForge Herald",
        maintainer="herald" if field == "maintainer" else ["herald"],
        inherits=COMPANY_IDENTIFIER if field == "inherits" else [COMPANY_IDENTIFIER],
    )
    report = preflight_frames(tmp_path)
    assert not report.ok
    finding = next(f for f in report.findings if f.code == "scalar-repeatable")
    assert field in finding.message
    # ...and the scalar did not break resolution: no inherits/identity finding.
    assert not any(
        f.code in {"inherits", "company", "unexpected-identifier"} for f in report.findings
    )


def test_station_without_inherits_fails(tmp_path: Path) -> None:
    frames = _seed_valid_tree(tmp_path)
    _write_frame(
        frames / "stations" / "herald.frame.md",
        identifier=f"{PUBLISHER}/herald",
        name="PyForge Herald",
        maintainer=["herald"],
        inherits=None,
    )
    report = preflight_frames(tmp_path)
    assert not report.ok
    assert any(f.code == "inherits" for f in report.findings)


def test_inherits_relative_path_to_company_passes(tmp_path: Path) -> None:
    """§5.3 classifies ``../pyforge.frame.md`` as a ``path-ref``, which this
    resolver declares it resolves."""
    frames = _seed_valid_tree(tmp_path)
    _write_frame(
        frames / "stations" / "herald.frame.md",
        identifier=f"{PUBLISHER}/herald",
        name="PyForge Herald",
        maintainer=["herald"],
        inherits=["../pyforge.frame.md"],
    )
    report = preflight_frames(tmp_path)
    assert report.ok, [f.message for f in report.findings]


def test_unexpected_identifier_fails(tmp_path: Path) -> None:
    frames = _seed_valid_tree(tmp_path)
    _write_frame(
        frames / "stations" / "herald.frame.md",
        identifier="pyforge/herald-two",
        name="PyForge Herald",
        maintainer=["herald"],
        inherits=[COMPANY_IDENTIFIER],
    )
    report = preflight_frames(tmp_path)
    assert not report.ok
    assert any(f.code == "unexpected-identifier" for f in report.findings)


def test_wrong_count_fails(tmp_path: Path) -> None:
    frames = _seed_valid_tree(tmp_path)
    (frames / "community.frame.md").write_text(
        "---\ntype: frame\nidentifier: pyforge/community\nname: PyForge Community\n"
        "description: no\nvisibility: public\nmaintainer:\n  - nobody\n---\n",
        encoding="utf-8",
    )
    report = preflight_frames(tmp_path)
    assert not report.ok
    assert any(f.code == "count" for f in report.findings)


def test_invalid_type_fails(tmp_path: Path) -> None:
    frames = _seed_valid_tree(tmp_path)
    _write_frame(
        frames / "pyforge.frame.md",
        type_="cog [0.3]",
        identifier=COMPANY_IDENTIFIER,
        name="PyForge",
        maintainer=["steward", "guild"],
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
