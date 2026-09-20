"""Story 18.2 — last fleet pulse on /stations/doctor/ via PortalClient only."""

from __future__ import annotations

import ast
import importlib.util
import subprocess
from pathlib import Path

from pyforge.testing_kit import changed_paths_since

_HTTP_TOPLEVEL = frozenset({"httpx", "requests", "http.client"})


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _portal_root(root: Path) -> Path:
    return root / "src" / "shared" / "packages" / "django-doctor" / "src" / "django_doctor_portal"


def _iter_py(tree: Path) -> list[Path]:
    return sorted(path for path in tree.rglob("*.py") if path.is_file())


def _load_pulse_document(root: Path):
    path = _portal_root(root) / "pulse_document.py"
    spec = importlib.util.spec_from_file_location("django_doctor_portal_pulse_document", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _raw_http_imports(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if (
                    top in _HTTP_TOPLEVEL
                    or alias.name in _HTTP_TOPLEVEL
                    or alias.name.startswith("http.client")
                    or alias.name == "urllib.request"
                ):
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top = module.split(".")[0]
            if (
                top in _HTTP_TOPLEVEL
                or module in _HTTP_TOPLEVEL
                or module.startswith(("urllib.request", "http.client"))
            ):
                found.append(f"from {module} import ...")
            if module == "urllib" and any(alias.name == "request" for alias in node.names):
                found.append("from urllib import request")
    return found


def _pyforge_imports(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(
                f"import {alias.name}"
                for alias in node.names
                if alias.name == "pyforge" or alias.name.startswith("pyforge.")
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "pyforge" or module.startswith("pyforge."):
                found.append(f"from {module} import ...")
    return found


def test_chrome_home_emits_via_portal_client_only():
    root = _repo_root()
    views = ast.parse((_portal_root(root) / "views.py").read_text(encoding="utf-8"))
    pulse = ast.parse((_portal_root(root) / "pulse.py").read_text(encoding="utf-8"))
    view_src = ast.dump(views)
    pulse_src = ast.dump(pulse)
    assert "require_station_role" in view_src
    assert "last_fleet_pulse" in view_src
    assert "PortalClient" in pulse_src
    assert "emit" in pulse_src
    assert "verify_assertion" in pulse_src


def test_present_pulse_renders_last_monitor_fleet_summary():
    module = _load_pulse_document(_repo_root())
    shown = module.present_pulse(
        {
            "summary": {"ok": 2, "warn": 1, "fail": 0, "total": 3},
            "axes": ["staleness"],
            "findings": [{"check": "pkg-a"}],
        }
    )
    assert shown["empty"] is False
    assert shown["advisory"] is True
    assert shown["summary"] == {"ok": 2, "warn": 1, "fail": 0, "total": 3}


def test_empty_last_pulse_is_advisory_empty_state():
    module = _load_pulse_document(_repo_root())
    shown = module.present_pulse(None)
    assert shown["empty"] is True
    assert shown["advisory"] is True
    assert shown["summary"] is None
    html = (_portal_root(_repo_root()) / "templates" / "doctor_portal" / "home.html").read_text(encoding="utf-8")
    assert 'id="doctor-fleet-pulse"' in html
    assert "No last" in html
    assert "advisory" in html.lower()
    assert "second PR gate" in html


def test_wrong_role_stays_require_station_role_doctor():
    root = _repo_root()
    src = (_portal_root(root) / "views.py").read_text(encoding="utf-8")
    assert '@require_station_role("doctor")' in src
    assert "last_fleet_pulse" in src


def test_django_doctor_is_client_only_no_pyforge_no_raw_http():
    root = _repo_root()
    offenders: list[str] = []
    for path in _iter_py(_portal_root(root)):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders.extend(f"{path}: {hit}" for hit in _raw_http_imports(tree))
        offenders.extend(f"{path}: {hit}" for hit in _pyforge_imports(tree))
    assert offenders == []


def test_home_extends_shared_chrome_not_a_copy():
    html = (_portal_root(_repo_root()) / "templates" / "doctor_portal" / "home.html").read_text(encoding="utf-8")
    assert '{% extends "django_pyforge/base.html" %}' in html
    assert 'id="doctor-body"' in html
    chrome_copies = list((_portal_root(_repo_root()) / "templates").rglob("chrome.html"))
    assert chrome_copies == []


def test_story_does_not_add_pyforge_under_src_platform():
    root = _repo_root()
    changed = changed_paths_since(root, pathspec="src/platform")
    offenders: list[str] = []
    for rel in changed:
        path = root / rel
        if path.suffix != ".py" or not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        hits = set(_pyforge_imports(tree)) | set(_raw_http_imports(tree))
        # "does not ADD": an import the file already carried at origin/main is
        # not this story's doing -- a branch that merely touches the file
        # (2026-09-04, PR #1043: a Ruff fix on station_port.py) must not trip it.
        before = subprocess.run(
            ["git", "show", f"origin/main:{rel}"], cwd=root, capture_output=True, text=True, check=False
        )
        if before.returncode == 0:
            base_tree = ast.parse(before.stdout)
            hits -= set(_pyforge_imports(base_tree)) | set(_raw_http_imports(base_tree))
        offenders.extend(f"{rel}: {hit}" for hit in sorted(hits))
    assert not offenders, f"src/platform gate failed: {changed} {offenders}"
