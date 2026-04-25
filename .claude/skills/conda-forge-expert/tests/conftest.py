"""Shared fixtures and helpers for the conda-forge-expert test suite.

Tests run against the `scripts/` directory in this skill, exercising both
in-process function calls (for underscore-named modules) and CLI subprocess
invocations (for hyphenated scripts and end-to-end smoke).
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
RECIPES_DIR = FIXTURES_DIR / "recipes"
ERROR_LOGS_DIR = FIXTURES_DIR / "error_logs"
MOCKED_RESPONSES_DIR = FIXTURES_DIR / "mocked_responses"


def _ensure_path() -> dict[str, str]:
    """Build an env that includes /usr/bin so subprocess can find awk/grep/etc."""
    env = os.environ.copy()
    extra = ["/usr/bin", "/bin"]
    current = env.get("PATH", "")
    parts = current.split(":") if current else []
    for p in extra:
        if p not in parts:
            parts.insert(0, p)
    env["PATH"] = ":".join(parts)
    return env


@pytest.fixture(scope="session")
def scripts_dir() -> Path:
    return SCRIPTS_DIR


@pytest.fixture(scope="session")
def recipes_dir() -> Path:
    return RECIPES_DIR


@pytest.fixture(scope="session")
def error_logs_dir() -> Path:
    return ERROR_LOGS_DIR


@pytest.fixture(scope="session")
def mocked_responses_dir() -> Path:
    return MOCKED_RESPONSES_DIR


@pytest.fixture
def script_runner():
    """Run a script in the scripts/ directory and return (rc, stdout, stderr).

    Usage:
        rc, out, err = script_runner("validate_recipe.py", "recipes/foo")
    """

    def _run(script: str, *args: str, cwd: Path | None = None,
             timeout: int = 60, input_text: str | None = None) -> tuple[int, str, str]:
        script_path = SCRIPTS_DIR / script
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        cmd = [sys.executable, str(script_path), *args]
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_ensure_path(),
            input=input_text,
        )
        return proc.returncode, proc.stdout, proc.stderr

    return _run


@pytest.fixture
def load_module():
    """Import a script as a Python module via importlib.

    Only works for scripts with valid Python identifiers (underscore-named).
    Hyphenated scripts must be invoked via script_runner.
    """

    def _load(script: str) -> ModuleType:
        script_path = SCRIPTS_DIR / script
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        module_name = script_path.stem
        if not module_name.replace("_", "").isalnum():
            raise ValueError(
                f"Cannot import {script} as a module — use script_runner instead."
            )
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        # Make sibling modules importable too
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        spec.loader.exec_module(module)
        return module

    return _load


@pytest.fixture
def copy_recipe(tmp_path):
    """Copy a fixture recipe into a fresh tmp_path and return the new dir.

    Usage:
        recipe_dir = copy_recipe("v1-noarch")
        # recipe_dir contains a clean copy of fixtures/recipes/v1-noarch/
    """

    def _copy(name: str) -> Path:
        src = RECIPES_DIR / name
        if not src.exists():
            raise FileNotFoundError(f"Fixture recipe not found: {src}")
        dest = tmp_path / name
        shutil.copytree(src, dest)
        return dest

    return _copy


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    """Redirect the skill's data/ directory (CVE DB, mapping cache) into tmp_path.

    Most scripts compute DATA_DIR via ``Path(__file__).parent.parent.parent / "data"``.
    We can't easily intercept that without monkey-patching each module.
    Tests that need to exercise cache reads should load the module via
    ``load_module`` and monkeypatch ``MAPPING_CACHE_FILE`` / ``PYPI_DB_PATH``
    directly.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def stub_responses(monkeypatch):
    """Stub `requests.get` / `requests.post` so tests never hit the network.

    Returns a registry where tests can pre-register URL → response mappings.
    """
    import requests

    registry: dict[tuple[str, str], dict] = {}

    class _StubResp:
        def __init__(self, status_code: int, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = (
                payload if isinstance(payload, str) else json.dumps(payload)
            )

        def json(self):
            if isinstance(self._payload, str):
                return json.loads(self._payload)
            return self._payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(f"{self.status_code}")

    def _fake_request(method: str, url: str, *args, **kwargs):
        key = (method.upper(), url)
        if key not in registry:
            raise AssertionError(
                f"Unmocked {method} {url}. Pre-register via stub_responses.register()."
            )
        spec = registry[key]
        return _StubResp(spec.get("status", 200), spec.get("body", {}))

    def _fake_get(url, *args, **kwargs):
        return _fake_request("GET", url, *args, **kwargs)

    def _fake_post(url, *args, **kwargs):
        return _fake_request("POST", url, *args, **kwargs)

    monkeypatch.setattr(requests, "get", _fake_get)
    monkeypatch.setattr(requests, "post", _fake_post)

    class _Registry:
        def register(self, method: str, url: str, *, status: int = 200, body=None):
            registry[(method.upper(), url)] = {"status": status, "body": body}

        def clear(self):
            registry.clear()

    return _Registry()


@pytest.fixture
def stub_metadata_api(monkeypatch):
    """Replace conda_forge_metadata.autotick_bot.pypi_to_conda with a fake."""
    import conda_forge_metadata.autotick_bot.pypi_to_conda as mod

    fake_mapping = [
        {"pypi_name": "pillow", "conda_name": "pillow", "import_name": "PIL"},
        {"pypi_name": "msrest", "conda_name": "msrest", "import_name": "msrest"},
        {"pypi_name": "21cmfast", "conda_name": "21cmfast", "import_name": "py21cmfast"},
    ]

    rename_map = {
        "pillow": "pillow",
        "msrest": "msrest",
        "21cmfast": "21cmfast",
    }

    def _fake_get_mapping():
        return list(fake_mapping)

    def _fake_map(name: str):
        return rename_map.get(name.lower(), name)

    monkeypatch.setattr(mod, "get_pypi_name_mapping", _fake_get_mapping)
    monkeypatch.setattr(mod, "map_pypi_to_conda", _fake_map)
    return {"mapping": fake_mapping, "rename_map": rename_map}


def _cleanup_pycache():
    """Remove __pycache__ directories the import tests may have created."""
    for p in SCRIPTS_DIR.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)


@pytest.fixture(autouse=True, scope="session")
def _session_cleanup():
    yield
    _cleanup_pycache()
