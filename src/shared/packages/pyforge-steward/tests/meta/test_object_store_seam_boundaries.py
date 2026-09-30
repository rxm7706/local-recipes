"""Steward Story 74.1 (spec-pyforge-steward CAP-163): the object-store seam's three import rules.

`django_pyforge.object_store` reaches CAP-97's S3 client without either side importing the
other's world:

1. `src/platform/` never imports `pyforge.*` (pap:AD-2; Story 10.1's import-linter contract
   guards `config`, `platformapp` and `tests`). It reaches station code only through
   `pyforge.core.station_port`.
2. `django_pyforge` never imports the host's `config` package (nor `config.*`). The chrome is
   installed beside stations and reaches the host's client factory by the dotted path in
   `OBJECT_STORAGE_CLIENT_FACTORY`, resolved with `import_string`.
3. `django_pyforge/object_store.py` imports neither `boto3` nor `botocore`: the client is the
   factory's, and django-pyforge declares neither dependency, so a portal environment
   without boto3 must still import the module.

The guard reads every `.py` file with `ast` and inspects import statements only -- a
string, a docstring or a comment that merely names a module is not an import, and a
function-local or `TYPE_CHECKING` import counts as one. A relative import (`level > 0`)
stays inside its own package and is never a finding. Because it reads import statements
only, a dynamic load -- `importlib.import_module("pyforge...")` or `import_string` (the
sanctioned ones are in `config/asgi.py` and `config/station_api.py`) -- is out of its scope.

Rule 1 has one known breach, closed and exact: `src/platform/ingest/github_projects` (Story
12.8's dlt lane) still imports `pyforge.steward.keys` and `.sync`; `pixi.toml`
`[feature.platform-ci-test.dependencies]` calls it "the live pap:AD-2 breach". Relocating
that lane out of the host is its own effort. The allowlist below is the four files, and it
can only shrink: a listed file that stops importing `pyforge.*` fails the test until it is
removed from the list, and any other importer reds.
"""

from __future__ import annotations

import ast
from pathlib import Path

_HERE = Path(__file__).resolve()
ROOT = next(p for p in _HERE.parents if (p / "pixi.toml").is_file() and (p / "AGENTS.md").is_file())
PLATFORM = ROOT / "src" / "platform"
DJANGO_PYFORGE = ROOT / "src" / "shared" / "packages" / "django-pyforge" / "src" / "django_pyforge"

#: The four `src/platform` files that import `pyforge.*` today (see the module docstring).
PLATFORM_PYFORGE_IMPORTERS: frozenset[str] = frozenset(
    {
        "src/platform/ingest/github_projects/graphql.py",
        "src/platform/ingest/github_projects/pipeline.py",
        "src/platform/ingest/github_projects/source.py",
        "src/platform/ingest/github_projects/test_github_metrics_dlt.py",
    }
)

#: Directories that hold third-party or generated files, never this repository's own modules.
_SKIP_DIRS = frozenset({"node_modules", "site-packages", ".venv", "staticfiles"})


def _is_package_or_submodule(module: str, package: str) -> bool:
    return module == package or module.startswith(package + ".")


def _imported_modules(py_file: Path) -> list[tuple[int, str]]:
    """Every absolute module a file imports, as (line, dotted name); relative imports excluded."""
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.lineno, node.module))
    return found


def importers_of(tree_root: Path, package: str, *, repo_root: Path) -> dict[str, list[int]]:
    """Files under `tree_root` that import `package` or `package.*`: repo-relative path -> lines."""
    importers: dict[str, list[int]] = {}
    for py_file in sorted(tree_root.rglob("*.py")):
        if _SKIP_DIRS.intersection(py_file.relative_to(tree_root).parts):
            continue
        lines = [line for line, module in _imported_modules(py_file) if _is_package_or_submodule(module, package)]
        if lines:
            importers[py_file.relative_to(repo_root).as_posix()] = lines
    return importers


def platform_findings(importers: dict[str, list[int]], allowlist: frozenset[str]) -> list[str]:
    """Rule 1 against a set of importers: a new importer, and a stale allowlist entry."""
    findings = [
        f"{path}:{', '.join(map(str, lines))}: src/platform imports pyforge.* (pap:AD-2); "
        "reach station code through pyforge.core.station_port"
        for path, lines in sorted(importers.items())
        if path not in allowlist
    ]
    findings.extend(
        f"{path}: allowlisted as a pyforge.* importer but no longer imports it -- remove it from "
        "PLATFORM_PYFORGE_IMPORTERS"
        for path in sorted(allowlist - importers.keys())
    )
    return findings


def chrome_findings(importers: dict[str, list[int]]) -> list[str]:
    """Rule 2: every importer of the host's `config` package is a finding."""
    return [
        f"{path}:{', '.join(map(str, lines))}: django_pyforge imports the host's `config` package; "
        "name the object with a dotted-path setting and resolve it with import_string"
        for path, lines in sorted(importers.items())
    ]


#: The client libraries `object_store.py` must never import (rule 3).
CLIENT_LIBRARIES: tuple[str, ...] = ("boto3", "botocore")


def client_library_findings(py_file: Path) -> list[str]:
    """Rule 3: every boto3 / botocore import in one file, as (line) findings."""
    return [
        f"{py_file.name}:{line}: imports {module}; the client comes from the factory the "
        "OBJECT_STORAGE_CLIENT_FACTORY setting names, and django-pyforge declares no boto3"
        for line, module in _imported_modules(py_file)
        if any(_is_package_or_submodule(module, lib) for lib in CLIENT_LIBRARIES)
    ]


# --- the live tree ---------------------------------------------------------------------


def test_the_trees_under_guard_exist() -> None:
    assert PLATFORM.is_dir(), PLATFORM
    assert (DJANGO_PYFORGE / "object_store.py").is_file(), DJANGO_PYFORGE
    assert len(list(PLATFORM.rglob("*.py"))) > 100  # a moved tree must not pass by scanning nothing
    assert len(list(DJANGO_PYFORGE.rglob("*.py"))) > 20


def test_src_platform_imports_no_pyforge_beyond_the_closed_allowlist() -> None:
    importers = importers_of(PLATFORM, "pyforge", repo_root=ROOT)
    assert not platform_findings(importers, PLATFORM_PYFORGE_IMPORTERS), "\n" + "\n".join(
        platform_findings(importers, PLATFORM_PYFORGE_IMPORTERS)
    )


def test_django_pyforge_imports_nothing_from_the_host_config_package() -> None:
    importers = importers_of(DJANGO_PYFORGE, "config", repo_root=ROOT)
    assert not chrome_findings(importers), "\n" + "\n".join(chrome_findings(importers))


def test_object_store_imports_no_client_library() -> None:
    findings = client_library_findings(DJANGO_PYFORGE / "object_store.py")
    assert not findings, "\n" + "\n".join(findings)


# --- mutation proofs: the guards red on a planted breach, on a tmp tree -------------------


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_the_platform_guard_reds_every_shape_of_pyforge_import(tmp_path: Path) -> None:
    _write(tmp_path, "src/platform/a.py", "import pyforge\n")
    _write(tmp_path, "src/platform/b.py", "import pyforge.core.station_port as port\n")
    _write(tmp_path, "src/platform/c.py", "from pyforge.steward import keys\n")
    _write(tmp_path, "src/platform/d.py", "from pyforge import core\n")
    _write(tmp_path, "src/platform/e.py", "def f():\n    from pyforge.warden import cli\n")
    _write(
        tmp_path, "src/platform/f.py", "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pyforge.core\n"
    )

    importers = importers_of(tmp_path / "src" / "platform", "pyforge", repo_root=tmp_path)

    assert sorted(importers) == [f"src/platform/{name}.py" for name in "abcdef"]
    assert importers["src/platform/e.py"] == [2]
    findings = platform_findings(importers, frozenset())
    assert len(findings) == 6
    assert all("pap:AD-2" in finding for finding in findings)


def test_the_platform_guard_ignores_what_is_not_a_pyforge_import(tmp_path: Path) -> None:
    _write(tmp_path, "src/platform/a.py", "from django_pyforge.flags import evaluate_boolean\nimport django_pyforge\n")
    _write(
        tmp_path,
        "src/platform/b.py",
        'SETUP = "from pyforge.warden.feeds import x"\n"""import pyforge"""\n# import pyforge\n',
    )
    _write(tmp_path, "src/platform/c.py", "from . import pyforge\nfrom .pyforge import x\n")
    _write(tmp_path, "src/platform/d.py", "import pyforge_extras\nfrom pyforgery import x\n")
    _write(tmp_path, "src/platform/node_modules/pkg/e.py", "import pyforge\n")

    assert importers_of(tmp_path / "src" / "platform", "pyforge", repo_root=tmp_path) == {}


def test_the_allowlist_reds_a_new_importer_and_a_stale_entry(tmp_path: Path) -> None:
    _write(tmp_path, "src/platform/ingest/listed.py", "from pyforge.steward.keys import HostScopedCredential\n")
    _write(tmp_path, "src/platform/ingest/stale.py", "import os\n")
    _write(tmp_path, "src/platform/new.py", "import pyforge.core\n")
    importers = importers_of(tmp_path / "src" / "platform", "pyforge", repo_root=tmp_path)
    allowlist = frozenset({"src/platform/ingest/listed.py", "src/platform/ingest/stale.py"})

    findings = platform_findings(importers, allowlist)

    assert len(findings) == 2, findings
    assert findings[0].startswith("src/platform/new.py:1: src/platform imports pyforge.*")
    assert findings[1].startswith("src/platform/ingest/stale.py: allowlisted as a pyforge.* importer but no longer")
    assert platform_findings({"src/platform/ingest/listed.py": [1]}, frozenset({"src/platform/ingest/listed.py"})) == []


def test_the_chrome_guard_reds_a_config_import_in_every_shape(tmp_path: Path) -> None:
    pkg = "src/django_pyforge"
    _write(tmp_path, f"{pkg}/a.py", "import config\n")
    _write(tmp_path, f"{pkg}/b.py", "from config.object_storage import object_storage_client\n")
    _write(tmp_path, f"{pkg}/c.py", "from config import object_storage\n")
    _write(tmp_path, f"{pkg}/d.py", "import config.settings.base\n")
    _write(tmp_path, f"{pkg}/e.py", "def f():\n    from config.object_storage import object_storage_client\n")

    importers = importers_of(tmp_path / pkg, "config", repo_root=tmp_path)

    assert sorted(importers) == [f"{pkg}/{name}.py" for name in "abcde"]
    assert all("import_string" in finding for finding in chrome_findings(importers))


def test_the_chrome_guard_ignores_what_is_not_a_config_import(tmp_path: Path) -> None:
    pkg = "src/django_pyforge"
    _write(
        tmp_path,
        f"{pkg}/a.py",
        'DEFAULT = "config.object_storage.object_storage_client"\nfrom django.conf import settings\n',
    )
    _write(tmp_path, f"{pkg}/b.py", "from . import config\nfrom .config import x\n")
    _write(tmp_path, f"{pkg}/c.py", "import configparser\nfrom config_extras import x\nimport django_pyforge.config\n")

    assert importers_of(tmp_path / pkg, "config", repo_root=tmp_path) == {}


def test_the_client_library_guard_reds_every_shape_and_ignores_non_imports(tmp_path: Path) -> None:
    planted = tmp_path / "planted.py"
    planted.write_text(
        "import boto3\n"
        "from botocore.exceptions import ClientError\n"
        "import botocore.config as cfg\n"
        "def f():\n    from boto3.s3.transfer import TransferConfig\n",
        encoding="utf-8",
    )
    findings = client_library_findings(planted)
    assert [f.split(" imports ")[0] for f in findings] == [
        "planted.py:1:",
        "planted.py:2:",
        "planted.py:3:",
        "planted.py:5:",
    ]

    clean = tmp_path / "clean.py"
    clean.write_text(
        'NAME = "boto3"\n"""import botocore"""\n# import boto3\n'
        "import boto3_extras\nfrom botocore_stubs import x\nfrom . import boto3\n"
        "from django.utils.module_loading import import_string\n",
        encoding="utf-8",
    )
    assert client_library_findings(clean) == []
