"""Shared fixtures and helpers for the conda-forge-expert test suite.

Tests run against the `scripts/` directory in this skill, exercising both
in-process function calls (for underscore-named modules) and CLI subprocess
invocations (for hyphenated scripts and end-to-end smoke).
"""
from __future__ import annotations

import functools
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


@pytest.fixture(scope="session")
def load_module():
    """Import a script as a Python module via importlib.

    Hyphenated filenames (e.g. ``recipe-generator.py``) are loaded under a
    sanitised module name with hyphens converted to underscores. This works
    because the module name is just an internal identifier for importlib —
    we never try ``import recipe-generator`` at the Python level.

    Session-scoped so module-scoped consumer fixtures (e.g. tests that load
    scan_project once per test module) can request it.
    """

    def _load(script: str) -> ModuleType:
        script_path = SCRIPTS_DIR / script
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        module_name = script_path.stem.replace("-", "_")
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        # Make sibling modules importable too
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        # Register before executing — `@dataclass` uses
        # ``sys.modules.get(cls.__module__)`` for forward-reference resolution,
        # which crashes for not-yet-registered modules.
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    return _load


@pytest.fixture
def copy_recipe(tmp_path, monkeypatch):
    """Copy a fixture recipe into a fresh tmp_path and return the new dir.

    Usage:
        recipe_dir = copy_recipe("v1-noarch")
        # recipe_dir contains a clean copy of fixtures/recipes/v1-noarch/

    Also points ``CFE_RECIPES_ROOT`` at ``tmp_path``. The recipe-facing CLIs
    confine writes to the repo's ``recipes/`` tree (AUD-CFE-001/002/006), and
    fixture copies deliberately live outside it — without the override every
    edit against a copied fixture would be rejected as out-of-tree. Set in
    ``os.environ`` so subprocess runs (``script_runner`` copies the env) and
    in-process calls both see it.
    """

    def _copy(name: str) -> Path:
        src = RECIPES_DIR / name
        if not src.exists():
            raise FileNotFoundError(f"Fixture recipe not found: {src}")
        dest = tmp_path / name
        shutil.copytree(src, dest)
        monkeypatch.setenv("CFE_RECIPES_ROOT", str(tmp_path))
        return dest

    return _copy


@functools.cache
def _extra_mirror_env_vars() -> tuple[str, ...]:
    """The non-`*_BASE_URL` mirror vars the credential host gate also scans.

    Read from `_http._EXTRA_MIRROR_ENV_VARS` rather than restated, so this
    fixture cannot drift from the gate. Loaded under a private module name:
    several test modules register their own `_http` copy in `sys.modules`,
    and this lookup must not replace it.
    """
    spec = importlib.util.spec_from_file_location(
        "_cfe_conftest_http", SCRIPTS_DIR / "_http.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(module._EXTRA_MIRROR_ENV_VARS)


@pytest.fixture(scope="session")
def _smithy_stub_sitecustomize_dir(tmp_path_factory):
    """A sitecustomize that stubs conda-smithy maintainer lookups in children."""
    from _smithy_maintainer_stub import sitecustomize_source

    site = tmp_path_factory.mktemp("cfe_smithy_stub_site")
    (site / "sitecustomize.py").write_text(sitecustomize_source(), encoding="utf-8")
    return site


@pytest.fixture(autouse=True)
def stub_smithy_maintainer_lookups(
    request, monkeypatch, _smithy_stub_sitecustomize_dir,
):
    """Replace conda-smithy maintainer lookups unless the test is marked network.

    ``_maintainer_exists`` (and ``_team_exists`` for ``org/team``) ask
    github.com when ``GH_TOKEN`` is unset. The ``cfe-regression-net`` lane
    has no token, so an unauthenticated HEAD from a CI runner flaked
    (2026-10-02) with ``Recipe maintainer "rxm7706" does not exist``.

    Autouse for every test that is not marked ``network`` — the opposite of
    ``clean_mirror_env``, which is opt-in so network tests keep real mirrors.
    In-process ``monkeypatch`` covers tests that import conda-smithy
    directly. ``PYTHONPATH`` sitecustomize covers the conda-smithy child
    that ``validate_recipe.run_external_lint`` starts (``script_runner``
    copies ``os.environ`` via ``_ensure_path``). Runtime lint is unchanged.
    """
    if request.node.get_closest_marker("network"):
        return
    from _smithy_maintainer_stub import (
        CFE_STUB_SMITHY_LOOKUPS_ENV,
        stub_maintainer_exists,
        stub_team_exists,
    )

    try:
        import conda_smithy.lint_recipe as lint_recipe
    except ImportError:
        pass
    else:
        monkeypatch.setattr(lint_recipe, "_maintainer_exists", stub_maintainer_exists)
        monkeypatch.setattr(lint_recipe, "_team_exists", stub_team_exists)
    monkeypatch.setenv(CFE_STUB_SMITHY_LOOKUPS_ENV, "1")
    existing = os.environ.get("PYTHONPATH", "")
    prefix = str(_smithy_stub_sitecustomize_dir)
    monkeypatch.setenv(
        "PYTHONPATH",
        f"{prefix}{os.pathsep}{existing}" if existing else prefix,
    )


@pytest.fixture
def clean_mirror_env(monkeypatch):
    """Remove every ambient mirror-routing env var for one test.

    The credential host gate derives its allowlist from EVERY set
    `*_BASE_URL` var (`_http._configured_enterprise_hosts`,
    `inventory_channel._fallback_configured_enterprise_hosts`,
    `dependency-checker._auth_headers`), plus npm's own registry vars. So any
    such var the developer's shell exports joins the set under test. Inside a
    Claude Code session `ANTHROPIC_BASE_URL` adds `api.anthropic.com`, which
    failed an exact-set assertion in a local `pr-preflight` (2026-09-29)
    while CI, which has no such var, stayed green.

    Opt in with `pytestmark = pytest.mark.usefixtures("clean_mirror_env")`,
    or on a class. Deliberately not autouse suite-wide: the `network`-marked
    tests should keep an operator's real mirror routing. Pixi config is the
    gate's other source; a test asserting the whole allowlist must also stub
    `read_pixi_config` (see `unit/test_http_jfrog_host_gate.py`).
    """
    for key in list(os.environ):
        if key.endswith("_BASE_URL"):
            monkeypatch.delenv(key)
    for key in _extra_mirror_env_vars():
        monkeypatch.delenv(key, raising=False)


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
    """Replace conda_forge_metadata.{conda_forge_bot,autotick_bot}.pypi_to_conda with a fake.

    conda-forge-metadata 0.16.x renamed `autotick_bot` → `conda_forge_bot`.
    Try the new path first, fall back to old for operators pinned to older releases.
    """
    try:
        import conda_forge_metadata.conda_forge_bot.pypi_to_conda as mod
    except ImportError:
        import conda_forge_metadata.autotick_bot.pypi_to_conda as mod  # type: ignore[import-not-found,no-redef]

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
