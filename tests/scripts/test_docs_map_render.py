"""Coverage for ``scripts/docs_map_render.py``, the write-side mutator for
docs/MAP.md's generated "## Page registry" section (Story 30.2,
spec-pyforge-doctor CAP-84).

Fixture-helper style matching
``src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_currency.py``:
``tmp_path`` fixtures only, never the live ``docs/`` tree. Unlike that file,
no git repo is needed here -- this script's own logic (schema validation via
``docs_currency.load_map_yaml``, marker splice via
``docs_currency.splice_registry_section``) reads no git history.

Covers the happy-path splice and every error path the script's own
docstring documents ("Exit 0 on a successful write... 1 on any failure"):
``map.yaml`` missing, ``map.yaml`` schema-invalid (malformed YAML, a page
missing a required key, no ``pages`` key at all -- the three shapes review
found crashing uncaught or silently writing an empty registry before this
fix), ``MAP.md`` missing, begin marker missing, end marker missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import docs_map_render as m  # noqa: E402  (sys.path must be set up first)

_POINTER_PAGE = {
    "path": "tutorials/README.md",
    "quadrant": "tutorials",
    "owner": "fleet",
    "kind": "pointer",
}

_POINTER_PAGE_YAML = """\
schema_version: 1
pages:
  - path: tutorials/README.md
    quadrant: tutorials
    owner: fleet
    kind: pointer
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _map_md(section: str = "") -> str:
    return (
        "# map\n\n## Page registry (generated)\n\n"
        "<!-- docs-map:registry:begin -->\n"
        f"{section}"
        "<!-- docs-map:registry:end -->\n"
    )


@pytest.fixture(autouse=True)
def _redirect_to_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Every test operates on ``tmp_path``'s own ``docs/`` tree -- never the
    live repo."""
    monkeypatch.setattr(m, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(m, "_MAP_YAML", tmp_path / "docs" / "map.yaml")
    monkeypatch.setattr(m, "_MAP_MD", tmp_path / "docs" / "MAP.md")
    return tmp_path


# --- happy path ----------------------------------------------------------------


def test_happy_path_splices_the_rendered_section(tmp_path: Path):
    _write(tmp_path / "docs" / "map.yaml", _POINTER_PAGE_YAML)
    _write(tmp_path / "docs" / "MAP.md", _map_md("stale content\n"))

    exit_code = m.main()

    assert exit_code == 0
    text = (tmp_path / "docs" / "MAP.md").read_text(encoding="utf-8")
    assert "stale content" not in text
    assert "[`tutorials/README.md`](tutorials/README.md)" in text
    assert text.startswith("# map\n\n## Page registry (generated)\n\n")


def test_already_current_is_still_exit_0(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    from pyforge.doctor.sources.docs_currency import render_map_registry

    _write(tmp_path / "docs" / "map.yaml", _POINTER_PAGE_YAML)
    _write(tmp_path / "docs" / "MAP.md", _map_md(render_map_registry([_POINTER_PAGE])))

    exit_code = m.main()

    assert exit_code == 0
    assert "already current" in capsys.readouterr().out


# --- schema validation (the crash/silent-write fix) -----------------------------


def test_map_yaml_missing_returns_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _write(tmp_path / "docs" / "MAP.md", _map_md())

    exit_code = m.main()

    assert exit_code == 1
    assert "missing or invalid" in capsys.readouterr().err


def test_map_yaml_malformed_yaml_returns_1_not_a_crash(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    _write(tmp_path / "docs" / "map.yaml", "schema_version: [1\npages: [\n")
    _write(tmp_path / "docs" / "MAP.md", _map_md())

    exit_code = m.main()

    assert exit_code == 1
    assert "missing or invalid" in capsys.readouterr().err


def test_map_yaml_page_missing_required_key_returns_1_not_a_crash(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    _write(
        tmp_path / "docs" / "map.yaml",
        "schema_version: 1\npages:\n"
        "  - path: x.md\n    quadrant: tutorials\n    owner: fleet\n",
    )  # missing the required `kind` key
    _write(tmp_path / "docs" / "MAP.md", _map_md())

    exit_code = m.main()

    assert exit_code == 1
    assert "missing or invalid" in capsys.readouterr().err


def test_map_yaml_no_pages_key_returns_1_never_writes_empty_registry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    _write(tmp_path / "docs" / "map.yaml", "schema_version: 1\n")
    original = _map_md("existing content\n")
    _write(tmp_path / "docs" / "MAP.md", original)

    exit_code = m.main()

    assert exit_code == 1
    assert "missing or invalid" in capsys.readouterr().err
    # Never silently overwritten with an empty registry.
    assert (tmp_path / "docs" / "MAP.md").read_text(encoding="utf-8") == original


# --- MAP.md / marker errors ------------------------------------------------------


def test_map_md_missing_returns_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _write(tmp_path / "docs" / "map.yaml", _POINTER_PAGE_YAML)

    exit_code = m.main()

    assert exit_code == 1
    assert "does not exist" in capsys.readouterr().err


def test_begin_marker_missing_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    _write(tmp_path / "docs" / "map.yaml", _POINTER_PAGE_YAML)
    _write(
        tmp_path / "docs" / "MAP.md",
        "# map\n\n## Page registry (generated)\n\nno markers here\n",
    )

    exit_code = m.main()

    assert exit_code == 1
    assert "registry:begin/end marker" in capsys.readouterr().err


def test_end_marker_missing_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    _write(tmp_path / "docs" / "map.yaml", _POINTER_PAGE_YAML)
    _write(
        tmp_path / "docs" / "MAP.md",
        "# map\n\n<!-- docs-map:registry:begin -->\nno end marker\n",
    )

    exit_code = m.main()

    assert exit_code == 1
    assert "registry:begin/end marker" in capsys.readouterr().err
