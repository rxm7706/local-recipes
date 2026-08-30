"""Unit tests for pyforge.scribe.extras.graphify -- the optional graphify
compile_surface extra + its move-list verbs (Story 6.1).

`graphify` (conda-forge `graphifyy`) is NOT a hard pixi run-dep of the lean
`pyforge-scribe` environment (air-gap default) -- every test that needs the
real package `pytest.importorskip`s it first, mirroring
`test_graph_store_plane.py`'s "no duckdb required" precedent for the same
class of optional heavy dependency. Tests that only exercise the off/guard
paths (env-var gating, move-list scanning -- pure text, no `graphify`
import) never skip.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.scribe.extras.graphify import (
    GRAPHIFY_EXTRA_ENV,
    GraphifyExtraUnavailable,
    default_graphify_root,
    graphify_extra_enabled,
    move_list_to_document,
    scan_move_list,
)


# --- graphify_extra_enabled() -------------------------------------------------


def test_extra_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GRAPHIFY_EXTRA_ENV, raising=False)
    assert graphify_extra_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "True", "yes", "YES"])
def test_extra_on_via_env_var(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(GRAPHIFY_EXTRA_ENV, value)
    assert graphify_extra_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", ""])
def test_extra_off_for_falsy_env_values(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(GRAPHIFY_EXTRA_ENV, value)
    assert graphify_extra_enabled() is False


def test_explicit_override_wins_over_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(GRAPHIFY_EXTRA_ENV, "1")
    assert graphify_extra_enabled(override=False) is False
    monkeypatch.delenv(GRAPHIFY_EXTRA_ENV, raising=False)
    assert graphify_extra_enabled(override=True) is True


def test_default_graphify_root_is_src(tmp_path: Path) -> None:
    assert default_graphify_root(tmp_path) == tmp_path / "src"


# --- graphify unavailable degrades cleanly ------------------------------------


def test_ingest_raises_typed_error_when_graphify_not_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulates a lean environment (`graphifyy` never installed) without
    actually needing to uninstall anything -- forces the lazy import to
    fail exactly the way a real missing-package environment would."""
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "graphify" or name.startswith("graphify."):
            raise ImportError(f"simulated missing package: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    from pyforge.scribe.extras.graphify import ingest_graphify_surface

    with pytest.raises(GraphifyExtraUnavailable):
        ingest_graphify_surface(tmp_path, repo_root=tmp_path, cache_dir=tmp_path / "cache")


# --- move-list scan (pure text -- no graphify dependency) ---------------------


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_scan_move_list_finds_all_four_categories(tmp_path: Path) -> None:
    _write(
        tmp_path / "src" / "platform" / "config" / "settings.py",
        "import os\nfrom pyforge.core.errors import PyforgeError\n",
    )
    _write(
        tmp_path / "src" / "shared" / "packages" / "pyforge-atlas" / "conftest.py",
        "import sys\nsys.path.insert(0, 'here')\n",
    )
    _write(
        tmp_path / "src" / "shared" / "packages" / "pyforge-steward" / "five_tier.py",
        "def _packages_root(repo_root):\n    return repo_root\n",
    )
    _write(
        tmp_path / "src" / "shared" / "packages" / "pyforge-mason" / "cfe.py",
        "# the sole conda-forge-expert (CFE) caller\nimport subprocess\n",
    )

    findings = scan_move_list(tmp_path)
    categories = {finding.category for finding in findings}

    assert categories == {
        "host_import_pyforge",
        "sys_path_insert",
        "five_tier_root",
        "cfe_caller",
    }
    host_hit = next(f for f in findings if f.category == "host_import_pyforge")
    assert host_hit.path == "src/platform/config/settings.py"
    assert "pyforge.core.errors" in host_hit.snippet


def test_scan_move_list_import_pyforge_only_flagged_under_host(tmp_path: Path) -> None:
    """`import pyforge.*` OUTSIDE `src/platform/` (e.g. a station package
    importing `pyforge.core`) is normal and not a foundry-cutover
    violation -- only host sites are flagged."""
    _write(
        tmp_path / "src" / "shared" / "packages" / "pyforge-scribe" / "cli.py",
        "from pyforge.scribe import capture\n",
    )

    findings = scan_move_list(tmp_path)

    assert not [f for f in findings if f.category == "host_import_pyforge"]


def test_scan_move_list_excludes_vendored_and_worktree_dirs(tmp_path: Path) -> None:
    _write(
        tmp_path / ".pixi" / "envs" / "x" / "site-packages" / "sys_path_user.py",
        "sys.path.insert(0, 'x')\n",
    )
    _write(tmp_path / ".worktrees" / "other" / "src" / "x.py", "sys.path.append('x')\n")

    findings = scan_move_list(tmp_path)

    assert findings == []


def test_scan_move_list_is_deterministic(tmp_path: Path) -> None:
    _write(
        tmp_path / "src" / "shared" / "packages" / "b.py",
        "sys.path.insert(0, 'b')\n",
    )
    _write(
        tmp_path / "src" / "shared" / "packages" / "a.py",
        "sys.path.insert(0, 'a')\n",
    )

    first = scan_move_list(tmp_path)
    second = scan_move_list(tmp_path)

    assert first == second
    assert [f.path for f in first] == sorted(f.path for f in first)


def test_move_list_to_document_shape(tmp_path: Path) -> None:
    _write(tmp_path / "x.py", "sys.path.insert(0, 'x')\n")

    findings = scan_move_list(tmp_path)
    document = move_list_to_document(findings, repo_root=tmp_path)

    assert document["counts"] == {"sys_path_insert": 1}
    assert document["categories"]["sys_path_insert"] == [
        {"path": "x.py", "line": 1, "snippet": "sys.path.insert(0, 'x')"}
    ]


# --- real graphify ingest / report (skipped when graphifyy is absent) --------


def test_ingest_graphify_surface_writes_code_nodes(tmp_path: Path) -> None:
    pytest.importorskip("graphify", reason="graphifyy not installed in this environment")
    from pyforge.scribe.extras.graphify import ingest_graphify_surface

    scan_root = tmp_path / "pkg"
    _write(scan_root / "mod_a.py", "def helper():\n    return 1\n")

    result = ingest_graphify_surface(scan_root, repo_root=tmp_path, cache_dir=tmp_path / "cache")

    assert result.nodes
    for node in result.nodes:
        assert node.kind == "code"
        assert node.id.startswith("code:")
        assert (tmp_path / node.citation).is_file()
    assert not (tmp_path / "graphify-out").exists()
    assert not (scan_root / "graphify-out").exists()


def test_ingest_graphify_surface_is_idempotent_across_reruns(tmp_path: Path) -> None:
    pytest.importorskip("graphify", reason="graphifyy not installed in this environment")
    from pyforge.scribe.extras.graphify import ingest_graphify_surface

    scan_root = tmp_path / "pkg"
    _write(scan_root / "mod_a.py", "def helper():\n    return 1\n")

    first = ingest_graphify_surface(scan_root, repo_root=tmp_path, cache_dir=tmp_path / "cache")
    second = ingest_graphify_surface(scan_root, repo_root=tmp_path, cache_dir=tmp_path / "cache")

    assert {n.model_dump_json() for n in first.nodes} == {n.model_dump_json() for n in second.nodes}


def test_build_graphify_report_includes_god_nodes(tmp_path: Path) -> None:
    pytest.importorskip("graphify", reason="graphifyy not installed in this environment")
    from pyforge.scribe.extras.graphify import build_graphify_report

    scan_root = tmp_path / "pkg"
    _write(
        scan_root / "mod_a.py",
        "def helper():\n    return 1\n\n\nclass Widget:\n    def render(self):\n        return helper()\n",
    )
    _write(
        scan_root / "mod_b.py",
        "from pkg.mod_a import Widget\n\n\ndef build():\n    return Widget().render()\n",
    )

    report = build_graphify_report(scan_root, repo_root=tmp_path, cache_dir=tmp_path / "cache")

    assert report.node_count > 0
    assert "# GRAPH_REPORT" in report.summary_markdown
    assert "God nodes" in report.summary_markdown
    assert not (tmp_path / "graphify-out").exists()
