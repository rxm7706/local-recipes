"""Story 115.1 (CAP-229, amended 2026-11-10): ``cli/config.py::checkout_root()`` in both layouts.

``cli/land.py``'s two script loaders and ``cli/deploy.py::_load_promote_sprint_status`` used to index
``Path(__file__).resolve().parents[8]``: right only for the editable layout. Under an installed package
that index lands inside the environment prefix, or past its ancestors (an ``IndexError`` after the PR
merged). They now resolve the checkout through ``checkout_root()``, the guarded ``__file__``-anchored half
of ``repo_root()``: the ancestor that carries ``src/shared/packages/pyforge-marshal``, or
``RepoRootUnresolvedError``.

Every layout here is built under ``tmp_path`` by pointing the module's ``__file__`` anchor at it
(``anchor_config_at``; ``config.__file__`` itself is never rebound), so this module reads nothing in the
repository outside the package.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from _config_anchor_support import anchor_config_at

from pyforge.marshal.cli import deploy as deploy_module
from pyforge.marshal.cli import land as land_module
from pyforge.marshal.cli.config import RepoRootUnresolvedError, checkout_root, repo_root
from pyforge.marshal.core.model import Severity

_PACKAGE_RELPATH = Path("src/shared/packages/pyforge-marshal")
_MODULE_RELPATH = _PACKAGE_RELPATH / "src" / "pyforge" / "marshal" / "cli" / "config.py"

# Eight ancestors: the bare `parents[8]` is one past the end. `resolve()` is non-strict.
_SHALLOW_PREFIX_FILE = "/usr/lib/python3.13/site-packages/pyforge/marshal/cli/config.py"


@pytest.fixture(autouse=True)
def _clean_git_env(monkeypatch):
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def off_tree_checkout_anchor() -> bool:
    """This module moves ``cli/config.py``'s checkout anchor itself (``anchor_config_at``), so the suite's off-tree
    anchor (``tests/conftest.py``) stays off and the real ``_editable_checkout_root()`` runs."""
    return False


@pytest.fixture(autouse=True)
def _no_cached_fleet_scan(monkeypatch):
    """``_load_fleet_scan_module`` caches its first load and registers it in ``sys.modules``; every test
    starts from none, and both are restored afterwards."""
    monkeypatch.setattr(land_module, "_fleet_scan_module", None)
    monkeypatch.setitem(sys.modules, "_fleet_scan_land", sys.modules.get("_fleet_scan_land"))


@pytest.fixture
def editable(tmp_path: Path, monkeypatch) -> Path:
    """A source checkout: ``config.py`` at its editable depth below a root that carries the package."""
    root = tmp_path / "checkout"
    module_file = root / _MODULE_RELPATH
    module_file.parent.mkdir(parents=True)
    anchor_config_at(monkeypatch, module_file)
    return root


@pytest.fixture
def installed(tmp_path: Path, monkeypatch) -> Path:
    """A module file outside any checkout: an environment prefix, nothing above it carries the package."""
    module_file = (
        tmp_path / "env" / "lib" / "python3.14" / "site-packages" / "pyforge" / "marshal" / "cli" / "config.py"
    )
    anchor_config_at(monkeypatch, module_file)
    return module_file


def _write_script(root: Path, name: str, body: str) -> None:
    scripts = root / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / name).write_text(body, encoding="utf-8")


# --- the editable anchor returns the repository ------------------------------------------------


def test_the_editable_anchor_returns_the_checkout(editable: Path) -> None:
    assert checkout_root() == editable.resolve()


def test_the_editable_anchor_is_the_same_root_repo_root_gives(editable: Path) -> None:
    assert checkout_root() == repo_root()


def test_the_editable_anchor_ignores_the_invocation_directory(editable: Path, tmp_path: Path, monkeypatch) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    assert checkout_root() == editable.resolve()


def test_the_land_loaders_read_the_scripts_of_the_checkout(editable: Path) -> None:
    _write_script(editable, "fleet_scan.py", "def parse_sprint_status(path):\n    return {'from': 'checkout'}\n")
    _write_script(editable, "promote_sprint_status.py", "def apply_epic_rollups(statuses):\n    return statuses\n")

    fleet_scan = land_module._load_fleet_scan_module()
    promote = land_module._load_promote_sprint_status_module()

    assert fleet_scan is not None
    assert getattr(fleet_scan, "parse_sprint_status")(Path("x")) == {"from": "checkout"}
    assert promote is not None
    assert callable(getattr(promote, "apply_epic_rollups"))


def test_the_deploy_loader_reads_the_checkout_not_the_redirected_repo_root(
    editable: Path, tmp_path: Path, monkeypatch
) -> None:
    """Why ``checkout_root()`` is separate from ``repo_root()``: tests redirect ``deploy.repo_root`` into a
    sandbox, and the script belongs to the checkout, not to the project data root."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    monkeypatch.setattr(deploy_module, "repo_root", lambda: sandbox)
    _write_script(editable, "promote_sprint_status.py", "MARKER = 'checkout'\n")

    module = deploy_module._load_promote_sprint_status()

    assert getattr(module, "MARKER") == "checkout"


# --- a module file outside any checkout --------------------------------------------------------


def test_outside_a_checkout_the_helper_raises_the_typed_error(installed: Path) -> None:
    with pytest.raises(RepoRootUnresolvedError) as excinfo:
        checkout_root()

    assert not isinstance(excinfo.value, IndexError)
    assert excinfo.value.finding.code == "MRS-GATE-016"


def test_a_prefix_with_fewer_than_nine_ancestors_raises_the_typed_error_not_an_index_error(monkeypatch) -> None:
    anchor_config_at(monkeypatch, _SHALLOW_PREFIX_FILE)
    assert len(Path(_SHALLOW_PREFIX_FILE).parents) == 8

    with pytest.raises(RepoRootUnresolvedError):
        checkout_root()


def test_outside_a_checkout_the_helper_never_falls_back_to_the_invocation_repository(
    installed: Path, tmp_path: Path, monkeypatch
) -> None:
    """``repo_root()`` answers with the invocation directory's git root; ``checkout_root()`` does not --
    a repository the operator stands in is not the checkout the package's scripts ship with."""
    repo = tmp_path / "some-repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True, capture_output=True)
    monkeypatch.chdir(repo)

    assert repo_root().resolve() == repo.resolve()
    with pytest.raises(RepoRootUnresolvedError):
        checkout_root()


def test_outside_a_checkout_both_land_loaders_return_none(installed: Path) -> None:
    """``None`` is the absent loader ``_promote_sprint_ledger`` reports as ``MRS-LAND-011``
    (``test_land_epic_rollups.py``, shape ``missing``)."""
    assert land_module._load_fleet_scan_module() is None
    assert land_module._load_promote_sprint_status_module() is None
    assert land_module._parse_sync_sprint_status_text("development_status:\n  1-1-a: done\n") == {}


def test_outside_a_checkout_the_deploy_loader_raises_the_typed_error(installed: Path) -> None:
    with pytest.raises(RepoRootUnresolvedError):
        deploy_module._load_promote_sprint_status()


def test_outside_a_checkout_the_repair_folds_into_mrs_deploy_027(installed: Path, tmp_path: Path) -> None:
    findings: list = []

    deploy_module._repair_tier3_feed(tmp_path, "acme", frozenset({"1-1-a-story"}), findings)

    assert [(finding.code, finding.severity) for finding in findings] == [("MRS-DEPLOY-027", Severity.WARN)]
    assert "no source checkout" in findings[0].message
