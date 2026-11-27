"""Story 95.1 — target_version_check three surfaces (AC3, AC7); Story 124.3 (spec-pyforge-steward:CAP-153) adds the
fourth, every pyforge-* package pixi.toml's host and run ``python`` floor. Every case runs ``main()`` over a fixture
tree under tmp_path; nothing here reads a live package manifest."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _check_script() -> Path:
    # The repository root is derived when a test runs, never at import time (the live_tree split guards); the one
    # live-tree read is the script itself, the path steward's live-half trigger already names.
    return Path(__file__).resolve().parents[6] / "scripts" / "target_version_check.py"


def _load():
    name = "_target_version_check_surfaces"
    spec = importlib.util.spec_from_file_location(name, _check_script())
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _write_pyforge(root: Path, name: str, *, ruff: str = "py314", mypy: str = "3.14", req: str = ">=3.14") -> None:
    pkg = root / "src" / "shared" / "packages" / name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nrequires-python = "{req}"\n\n'
        f'[tool.ruff]\ntarget-version = "{ruff}"\n\n'
        f'[tool.mypy]\npython_version = "{mypy}"\n',
        encoding="utf-8",
    )


def _write_manifest(root: Path, name: str, *, host: str | None = '"3.14.10.*"', run: str | None = '">=3.14"') -> Path:
    """A package pixi.toml in the members' shape; ``None`` leaves that table's ``python`` line out."""
    pkg = root / "src" / "shared" / "packages" / name
    pkg.mkdir(parents=True, exist_ok=True)
    host_line = f"python = {host}\n" if host is not None else ""
    run_line = f"python = {run}\n" if run is not None else ""
    manifest = pkg / "pixi.toml"
    manifest.write_text(
        f'[package]\nname = "{name}"\nversion = "0.1.0"\n\n'
        f'[package.build.backend]\nname = "pixi-build-python"\nversion = "0.*"\n\n'
        f'[package.host-dependencies]\n{host_line}hatchling = "*"\n\n'
        f'[package.run-dependencies]\n{run_line}pyyaml = "*"\n',
        encoding="utf-8",
    )
    return manifest


def _write_django(root: Path, name: str, *, ruff: str = "py314", req: str = ">=3.14", with_ruff: bool = True) -> None:
    pkg = root / "src" / "shared" / "packages" / name
    pkg.mkdir(parents=True, exist_ok=True)
    ruff_block = f'[tool.ruff]\ntarget-version = "{ruff}"\n' if with_ruff else ""
    (pkg / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nrequires-python = "{req}"\n\n{ruff_block}',
        encoding="utf-8",
    )


def _write_platform(root: Path, *, ruff: str = "py314", mypy: str = "3.14") -> None:
    plat = root / "src" / "platform"
    plat.mkdir(parents=True, exist_ok=True)
    (plat / "pyproject.toml").write_text(
        f'[tool.ruff]\ntarget-version = "{ruff}"\n\n[tool.mypy]\npython_version = "{mypy}"\n',
        encoding="utf-8",
    )


_ESTATE_ACTION = """runs:
  using: composite
  steps:
    - uses: actions/setup-python@v7
      with:
        python-version: ${{ steps.version.outputs.python }}
"""


def _write_lock(
    root: Path,
    pythons: dict[str, str],
    *,
    family: dict[str, str] | None = None,
    hosts: dict[str, str] | None = None,
) -> None:
    """A pixi.lock whose environments section locks ``env -> python version`` on linux-64, with ``libpython``,
    ``cpython`` and ``python-gil`` at the same version unless ``family`` names another, and one pixi-build source
    record per ``hosts`` entry (``record -> its host python``)."""
    lines = ["version: 7", "environments:"]
    for env, version in pythons.items():
        lines += [
            f"  {env}:",
            "    channels:",
            "    - url: https://conda.anaconda.org/conda-forge/",
            "    packages:",
            "      linux-64:",
            f"      - conda: https://conda.anaconda.org/conda-forge/linux-64/python-{version}-h0_cp3.conda",
        ]
        for package in ("libpython", "cpython", "python-gil"):
            got = (family or {}).get(package, version)
            lines.append(f"      - conda: https://conda.anaconda.org/conda-forge/noarch/{package}-{got}-h0_cp3.conda")
    lines.append("packages:")
    for record, version in (hosts or {}).items():
        lines += [
            f"- conda_source: {record} @ src/shared/packages/{record.split('[')[0]}",
            "  host_packages:",
            f"  - conda: https://conda.anaconda.org/conda-forge/linux-64/python-{version}-h0_cp3.conda",
        ]
    (root / "pixi.lock").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_workflow(root: Path, name: str, body: str) -> None:
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / name).write_text(body, encoding="utf-8")


def _seed_tree(root: Path, *, pin: str = "3.14.10.*") -> None:
    (root / "pixi.toml").write_text(
        f'[feature.interpreter.dependencies]\npython = "{pin}"\n\n'
        '[feature.tools.dependencies]\ngit = "*"\n\n'
        '[environments]\ndefault = ["interpreter", "tools"]\n'
        'guild = { features = ["interpreter"], no-default-feature = true }\n',
        encoding="utf-8",
    )
    version = pin.removesuffix(".*")
    _write_lock(root, {"default": version, "guild": version})
    action = root / ".github" / "actions" / "setup-estate-python"
    action.mkdir(parents=True, exist_ok=True)
    (action / "action.yml").write_text(_ESTATE_ACTION, encoding="utf-8")
    for i in range(1, 11):
        _write_pyforge(root, f"pyforge-p{i}")
        _write_manifest(root, f"pyforge-p{i}")
    for i in range(1, 10):
        _write_django(root, f"django-p{i}")
    _write_platform(root)


def _run_main(mod, root: Path) -> int:
    old_root = mod.ROOT
    old_pkg = mod.PACKAGES_DIR
    old_plat = mod.PLATFORM_PYPROJECT
    mod.ROOT = root
    mod.PACKAGES_DIR = root / "src" / "shared" / "packages"
    mod.PLATFORM_PYPROJECT = root / "src" / "platform" / "pyproject.toml"
    try:
        return mod.main()
    finally:
        mod.ROOT = old_root
        mod.PACKAGES_DIR = old_pkg
        mod.PLATFORM_PYPROJECT = old_plat


def test_clean_tree_exits_zero(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    assert _run_main(mod, tmp_path) == 0


def test_portal_ruff_py312_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_django(tmp_path, "django-p1", ruff="py312")
    assert _run_main(mod, tmp_path) == 1


def test_portal_requires_python_below_pin_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_django(tmp_path, "django-p1", req=">=3.12")
    assert _run_main(mod, tmp_path) == 1


def test_portal_missing_ruff_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_django(tmp_path, "django-p1", with_ruff=False)
    assert _run_main(mod, tmp_path) == 1


def test_platform_ruff_py312_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_platform(tmp_path, ruff="py312")
    assert _run_main(mod, tmp_path) == 1


def test_platform_mypy_312_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_platform(tmp_path, mypy="3.12")
    assert _run_main(mod, tmp_path) == 1


def test_pyforge_requires_python_below_pin_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_pyforge(tmp_path, "pyforge-p1", req=">=3.12")
    assert _run_main(mod, tmp_path) == 1


def test_eight_portal_packages_could_not_run(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    import shutil

    shutil.rmtree(tmp_path / "src/shared/packages/django-p9")
    assert _run_main(mod, tmp_path) == 2


def test_missing_platform_pyproject_could_not_run(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    (tmp_path / "src/platform/pyproject.toml").unlink()
    assert _run_main(mod, tmp_path) == 2


def test_pin_315_moves_expected_targets(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path, pin="3.15.0.*")
    assert _run_main(mod, tmp_path) == 1
    _write_pyforge(tmp_path, "pyforge-p1", ruff="py315", mypy="3.15", req=">=3.15")
    for i in range(2, 11):
        _write_pyforge(tmp_path, f"pyforge-p{i}", ruff="py315", mypy="3.15", req=">=3.15")
    for i in range(1, 10):
        _write_django(tmp_path, f"django-p{i}", ruff="py315", req=">=3.15")
    _write_platform(tmp_path, ruff="py315", mypy="3.15")
    # Story 124.3: the package manifests are still at 3.14, so the 3.15 pin reds them alone.
    assert _run_main(mod, tmp_path) == 1
    for i in range(1, 11):
        _write_manifest(tmp_path, f"pyforge-p{i}", host='"3.15.0.*"', run='">=3.15"')
    assert _run_main(mod, tmp_path) == 0


def test_mutation_dropping_django_glob_could_not_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: no django-* packages — same exit 2 as test_eight_portal_packages_could_not_run."""
    mod = _load()
    _seed_tree(tmp_path)
    _orig_glob = Path.glob

    def _only_pyforge(self: Path, pattern: str):
        if pattern == "django-*":
            return iter(())
        return _orig_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", _only_pyforge, raising=False)
    assert _run_main(mod, tmp_path) == 2


def test_mutation_dropping_platform_check_would_hide_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_platform(tmp_path, ruff="py312")
    assert _run_main(mod, tmp_path) == 1
    monkeypatch.setattr(mod, "findings_for_platform", lambda *a, **k: [])
    assert _run_main(mod, tmp_path) == 0


def test_mutation_hard_coding_py314_would_fail_on_315_pin(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path, pin="3.15.0.*")
    for i in range(1, 11):
        _write_pyforge(tmp_path, f"pyforge-p{i}", ruff="py314", mypy="3.14", req=">=3.14")
    for i in range(1, 10):
        _write_django(tmp_path, f"django-p{i}", ruff="py314", req=">=3.14")
    _write_platform(tmp_path, ruff="py314", mypy="3.14")
    assert _run_main(mod, tmp_path) == 1


def test_mutation_removing_requires_python_check_would_hide_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_django(tmp_path, "django-p1", req=">=3.12")
    assert _run_main(mod, tmp_path) == 1
    monkeypatch.setattr(mod, "_requires_python_floor", lambda *a, **k: [])
    assert _run_main(mod, tmp_path) == 0


# --- Story 124.3 (spec-pyforge-steward:CAP-153): every pyforge-* package pixi.toml's host and run python floor ---


@pytest.mark.parametrize("table", ["host", "run"])
def test_package_manifest_python_312_drifts_and_names_the_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], table: str
) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    floors = {"host": '"3.14.10.*"', "run": '">=3.14"'}
    floors[table] = '">=3.12"'
    _write_manifest(tmp_path, "pyforge-p3", **floors)
    assert _run_main(mod, tmp_path) == 1
    out = capsys.readouterr().out
    assert "src/shared/packages/pyforge-p3/pixi.toml" in out
    assert f"[package.{table}-dependencies] python = '>=3.12'" in out
    assert "pyforge-p1/pixi.toml" not in out


def test_package_manifest_table_form_python_is_read(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_manifest(tmp_path, "pyforge-p2", run='{ version = ">=3.12" }')
    assert _run_main(mod, tmp_path) == 1
    _write_manifest(tmp_path, "pyforge-p2", run='{ version = ">=3.14" }')
    assert _run_main(mod, tmp_path) == 0


def test_package_manifest_without_python_drifts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_manifest(tmp_path, "pyforge-p4", host=None)
    assert _run_main(mod, tmp_path) == 1
    assert "pyforge-p4/pixi.toml: [package.host-dependencies] has no python" in capsys.readouterr().out


def test_package_manifest_unparseable_python_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_manifest(tmp_path, "pyforge-p5", run='"*"')
    assert _run_main(mod, tmp_path) == 1


def test_nine_package_manifests_could_not_run(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    (tmp_path / "src/shared/packages/pyforge-p10/pixi.toml").unlink()
    assert _run_main(mod, tmp_path) == 2


def test_mutation_dropping_manifest_check_would_hide_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_manifest(tmp_path, "pyforge-p1", host='">=3.12"', run='">=3.12"')
    assert _run_main(mod, tmp_path) == 1
    monkeypatch.setattr(mod, "findings_for_package_manifest", lambda *a, **k: [])
    assert _run_main(mod, tmp_path) == 0


# --- Story 148.1 / 148.3 (spec-pyforge-steward:CAP-153): python is declared once and used everywhere ------------


def test_a_second_python_declaration_drifts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    manifest = tmp_path / "pixi.toml"
    manifest.write_text(manifest.read_text(encoding="utf-8").replace('git = "*"', 'git = "*"\npython = "3.14.*"'))
    assert _run_main(mod, tmp_path) == 1
    assert "[feature.tools.dependencies] declares python" in capsys.readouterr().out


def test_a_per_target_or_default_python_declaration_drifts(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    manifest = tmp_path / "pixi.toml"
    base = manifest.read_text(encoding="utf-8")
    manifest.write_text('[dependencies]\npython = "3.14.*"\n\n' + base, encoding="utf-8")
    assert _run_main(mod, tmp_path) == 1
    manifest.write_text(base + '\n[feature.tools.target.win-64.dependencies]\npython = "3.13.*"\n', encoding="utf-8")
    assert _run_main(mod, tmp_path) == 1


def test_an_environment_without_the_interpreter_feature_drifts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    manifest = tmp_path / "pixi.toml"
    manifest.write_text(manifest.read_text(encoding="utf-8").replace('features = ["interpreter"]', "features = []"))
    assert _run_main(mod, tmp_path) == 1
    assert "environment 'guild' does not list the 'interpreter' feature" in capsys.readouterr().out


def test_a_lock_off_the_declared_python_drifts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The case that left pyforge-marshal on 3.15.0 while every other environment locked 3.14.7."""
    mod = _load()
    _seed_tree(tmp_path)
    _write_lock(tmp_path, {"default": "3.14.10", "guild": "3.15.0"})
    assert _run_main(mod, tmp_path) == 1
    assert "guild on linux-64 resolves python 3.15.0, pixi.toml declares 3.14.10" in capsys.readouterr().out
    _write_lock(tmp_path, {"default": "3.14.10"})
    assert _run_main(mod, tmp_path) == 1


def test_a_declaration_without_an_exact_version_could_not_run(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path, pin="3.14.*")
    assert _run_main(mod, tmp_path) == 2


def test_a_missing_lock_or_estate_action_could_not_run(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    (tmp_path / ".github" / "actions" / "setup-estate-python" / "action.yml").unlink()
    assert _run_main(mod, tmp_path) == 2
    _seed_tree(tmp_path)
    (tmp_path / "pixi.lock").unlink()
    assert _run_main(mod, tmp_path) == 2


def test_a_workflow_setting_python_up_another_way_drifts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_workflow(
        tmp_path,
        "lint.yml",
        "jobs:\n  lint:\n    steps:\n      - uses: actions/checkout@v7\n      - uses: actions/setup-python@v7\n"
        "        with:\n          python-version: '3.14'\n      - run: python -m lint\n",
    )
    assert _run_main(mod, tmp_path) == 1
    assert ".github/workflows/lint.yml:5 sets Python up with actions/setup-python" in capsys.readouterr().out


def test_a_python_step_before_any_interpreter_drifts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_workflow(
        tmp_path,
        "deploy.yml",
        "jobs:\n  deploy:\n    steps:\n      - uses: actions/checkout@v7\n"
        "      - name: Verify\n        run: python scripts/verify.py\n"
        "      - uses: ./.github/actions/setup-estate-python\n",
    )
    assert _run_main(mod, tmp_path) == 1
    assert "job 'deploy' runs python before it sets up the estate's Python" in capsys.readouterr().out


@pytest.mark.parametrize(
    "steps",
    [
        "      - uses: ./.github/actions/setup-estate-python\n      - run: python scripts/verify.py\n",
        "      - uses: prefix-dev/setup-pixi@v0.11.3\n        with:\n          activate-environment: build\n"
        "      - run: |\n          set -euo pipefail\n          python -m pytest\n",
        "      - run: |\n          docker run --rm image \\\n            python manage.py migrate\n",
        "      - run: |\n          podman run --rm image \\\n            python manage.py migrate\n",
        "      - run: pixi run --frozen -e build python scripts/verify.py\n",
    ],
    ids=["estate-action", "activated-pixi", "docker", "continuation", "pixi-run"],
)
def test_a_python_step_with_an_interpreter_is_clean(tmp_path: Path, steps: str) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_workflow(tmp_path, "ok.yml", "jobs:\n  ok:\n    steps:\n      - uses: actions/checkout@v7\n" + steps)
    assert _run_main(mod, tmp_path) == 0


def test_a_container_job_may_run_python(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_workflow(
        tmp_path,
        "build.yml",
        "jobs:\n  build:\n    container:\n      image: python:3.14\n    steps:\n      - run: python -V\n",
    )
    assert _run_main(mod, tmp_path) == 0


def test_a_local_action_that_activates_pixi_provides_the_interpreter(tmp_path: Path) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    setup = tmp_path / ".github" / "actions" / "test-setup"
    setup.mkdir(parents=True)
    (setup / "action.yml").write_text(
        "runs:\n  using: composite\n  steps:\n    - uses: prefix-dev/setup-pixi@v0.11.3\n      with:\n"
        "        activate-environment: test\n",
        encoding="utf-8",
    )
    _write_workflow(
        tmp_path,
        "test.yml",
        "jobs:\n  test:\n    steps:\n      - uses: ./.github/actions/test-setup\n      - run: python -m pytest\n",
    )
    assert _run_main(mod, tmp_path) == 0


def test_mutation_dropping_the_lock_check_would_hide_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_lock(tmp_path, {"default": "3.14.10", "guild": "3.15.0"})
    assert _run_main(mod, tmp_path) == 1
    monkeypatch.setattr(mod, "findings_for_lock", lambda *a, **k: [])
    assert _run_main(mod, tmp_path) == 0


# --- Story 149.1 (spec-pyforge-steward:CAP-153): the station builds and the Python family run the declared Python ---


def test_a_build_host_on_another_python_drifts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The case that left the station packages building on 3.14.7, 3.14.8, 3.15.0 and 3.15.2."""
    mod = _load()
    _seed_tree(tmp_path)
    _write_lock(
        tmp_path,
        {"default": "3.14.10", "guild": "3.14.10"},
        hosts={"pyforge-p1[aa]": "3.14.10", "pyforge-p2[bb]": "3.15.0"},
    )
    assert _run_main(mod, tmp_path) == 1
    out = capsys.readouterr().out
    assert "the build host of pyforge-p2[bb] runs python 3.15.0, pixi.toml declares 3.14.10" in out
    assert "pyforge-p1[aa]" not in out


def test_a_python_family_package_off_the_declaration_drifts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """cpython and python-gil stayed at 3.14.7 beside python 3.14.10, since nothing made the lock move them."""
    mod = _load()
    _seed_tree(tmp_path)
    _write_lock(tmp_path, {"default": "3.14.10", "guild": "3.14.10"}, family={"cpython": "3.14.7"})
    assert _run_main(mod, tmp_path) == 1
    out = capsys.readouterr().out
    assert "default on linux-64 locks cpython 3.14.7, not 3.14.10" in out
    assert 'lock once with cpython = "3.14.10.*"' in out


@pytest.mark.parametrize("host", ['">=3.14"', '"*"', '"3.14.7.*"'])
def test_a_build_host_not_pinned_to_the_declaration_drifts(tmp_path: Path, host: str) -> None:
    """A floor or a star leaves the locked build host where it is when the declaration moves; only the exact pin
    makes pixi lock solve it again."""
    mod = _load()
    _seed_tree(tmp_path)
    _write_manifest(tmp_path, "pyforge-p6", host=host)
    assert _run_main(mod, tmp_path) == 1


def test_mutation_dropping_the_build_host_check_would_hide_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load()
    _seed_tree(tmp_path)
    _write_lock(tmp_path, {"default": "3.14.10", "guild": "3.14.10"}, hosts={"pyforge-p1[aa]": "3.15.2"})
    assert _run_main(mod, tmp_path) == 1
    monkeypatch.setattr(mod, "lock_build_hosts", lambda *a, **k: {})
    assert _run_main(mod, tmp_path) == 0
