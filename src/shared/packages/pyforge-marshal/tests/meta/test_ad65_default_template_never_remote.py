"""Meta test -- AD-65's default-template path never constructs a remote
source (Story 12.3).

The only reachable network path for Genesis is Copier's git fetch, and that
must be reachable ONLY via an explicit ``--template <url>`` override. The
production CLI does not expose ``--template`` yet; this guard proves the
four shipped seed verbs never pass a non-default ``template_path`` into their
verb layer, and that ``engine/copier.py``'s ``_template_source(None)`` resolves
to the in-package ``seed/templates/`` tree (never a URL-shaped string).

Two independent checks:

1. AST-scan ``cli/seed.py``'s four real dispatchers (``run_init``/``run_adopt``/
   ``run_check``/``run_update``) and fail if any ``_run_*_verb(...)`` call
   passes ``template_path=``.
2. Assert ``_template_source(None)`` yields a filesystem path under the
   installed package's ``seed/templates`` directory (unit-level behavioral
   proof, duplicated here so this meta module stands alone as the AC's
   "default path" gate).
"""

from __future__ import annotations

import ast
from importlib import resources
from pathlib import Path

import pyforge.marshal
from pyforge.marshal.seed.engine.copier import _template_source

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
_SEED_CLI = PACKAGE_DIR / "cli" / "seed.py"

_DISPATCHERS = frozenset({"run_init", "run_adopt", "run_check", "run_update"})
_VERB_CALLEES = frozenset(
    {
        "_run_init_verb",
        "_run_adopt_verb",
        "_run_check_verb",
        "_run_update_verb",
    }
)


def _seed_cli_tree() -> ast.Module:
    return ast.parse(_SEED_CLI.read_text(encoding="utf-8"), filename=str(_SEED_CLI))


def _dispatcher_template_path_kwarg_violations(tree: ast.Module) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in _DISPATCHERS:
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            callee = child.func
            if not (isinstance(callee, ast.Name) and callee.id in _VERB_CALLEES):
                continue
            for keyword in child.keywords:
                if keyword.arg == "template_path":
                    violations.append(f"{node.name} passes template_path= to {callee.id}")
    return violations


def test_production_seed_cli_never_passes_template_path_to_verbs():
    violations = _dispatcher_template_path_kwarg_violations(_seed_cli_tree())
    assert not violations, "\n".join(violations)


def test_default_template_source_is_the_packaged_templates_dir():
    expected_root = resources.files("pyforge.marshal.seed.templates")
    with resources.as_file(expected_root) as expected_path, _template_source(None) as actual:
        assert Path(actual).resolve() == expected_path.resolve()


def test_default_template_source_is_never_url_shaped():
    with _template_source(None) as actual:
        lowered = actual.lower()
        assert not (
            lowered.startswith("http://")
            or lowered.startswith("https://")
            or lowered.startswith("git@")
            or lowered.startswith("ssh://")
        ), f"default template resolved to a remote-looking source: {actual!r}"
