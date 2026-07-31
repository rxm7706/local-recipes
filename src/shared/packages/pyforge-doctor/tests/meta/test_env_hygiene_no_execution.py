"""Meta test -- no-execution guard for ``checks/env_hygiene.py`` (Story
1.4). ``env_hygiene.py`` reads OTHER Python source as untrusted data (an
env-var-credential-injection scanner), so it must never itself
``exec``/``eval`` that source, nor reach for ``importlib``/``__import__``
to dynamically load it -- mirroring ``sources/warden.py``'s own
no-subprocess discipline (AD-1) for the analogous no-execution concern.

Positively proves the detector fires on synthetic violations -- the guard
is alive, not vacuous -- mirroring
``test_sources_warden_no_subprocess.py``'s own style.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pyforge.doctor

_PACKAGE_FILE = pyforge.doctor.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
ENV_HYGIENE_SOURCE_PATH = PACKAGE_DIR / "checks" / "env_hygiene.py"

_EXEC_LIKE_CALL_NAMES = frozenset({"exec", "eval", "__import__"})


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _no_execution_violations(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _EXEC_LIKE_CALL_NAMES
        ):
            violations.append(node.lineno)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "importlib" or alias.name.startswith(
                    "importlib."
                ):
                    violations.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "importlib" or module.startswith("importlib."):
                violations.append(node.lineno)
    return sorted(set(violations))


def test_env_hygiene_module_exists():
    assert ENV_HYGIENE_SOURCE_PATH.is_file(), (
        f"expected {ENV_HYGIENE_SOURCE_PATH} -- the Story 1.4 env-hygiene "
        "detector module is missing"
    )


def test_env_hygiene_has_no_exec_eval_or_dynamic_import_call_sites():
    violations = _no_execution_violations(_parse(ENV_HYGIENE_SOURCE_PATH))
    assert not violations, (
        f"env_hygiene.py uses exec/eval/dynamic-import at line(s) "
        f"{violations} -- this scanner must stay ast.parse-only, never "
        "running the untrusted source it scans"
    )


# --- synthetic-violation positive proof (the guard is alive, not vacuous) --


def test_guard_fires_on_synthetic_exec_call():
    assert _no_execution_violations(ast.parse("exec('import os')\n")) == [1]


def test_guard_fires_on_synthetic_eval_call():
    assert _no_execution_violations(ast.parse("eval('1 + 1')\n")) == [1]


def test_guard_fires_on_synthetic_dunder_import_call():
    assert _no_execution_violations(ast.parse("__import__('os')\n")) == [1]


def test_guard_fires_on_synthetic_importlib_import():
    plain = "import importlib\n"
    assert _no_execution_violations(ast.parse(plain)) == [1]
    from_import = "from importlib import import_module\n"
    assert _no_execution_violations(ast.parse(from_import)) == [1]
    submodule = "import importlib.util\n"
    assert _no_execution_violations(ast.parse(submodule)) == [1]


def test_guard_does_not_fire_on_benign_ast_parse_usage():
    benign = (
        "import ast\n"
        "from pathlib import Path\n"
        "tree = ast.parse('x = 1')\n"
    )
    assert _no_execution_violations(ast.parse(benign)) == []
