"""Local stand-in for conda-smithy's GitHub maintainer lookups.

CFE tests must not ask github.com whether a recipe maintainer exists
(``cfe-regression-net`` has no ``GH_TOKEN``; an unauthenticated HEAD from a
CI runner flaked on 2026-10-02). ``tests/conftest.py`` installs this module
in-process and, via a ``PYTHONPATH`` sitecustomize, in the conda-smithy
child that ``validate_recipe.run_external_lint`` starts.
"""
from __future__ import annotations

CFE_STUB_SMITHY_LOOKUPS_ENV = "CFE_STUB_SMITHY_MAINTAINER_LOOKUPS"


def stub_maintainer_exists(maintainer: str) -> bool:
    """Local answer: the named maintainer exists."""
    return True


def stub_team_exists(org_team: str) -> bool:
    """Local answer: the named org/team exists."""
    return True


def apply_smithy_maintainer_stubs() -> None:
    """Replace conda-smithy's two GitHub lookups. No-op if smithy is absent."""
    try:
        import conda_smithy.lint_recipe as lint_recipe
    except ImportError:
        return
    lint_recipe._maintainer_exists = stub_maintainer_exists
    lint_recipe._team_exists = stub_team_exists


def sitecustomize_source() -> str:
    """Self-contained sitecustomize that applies the stubs on interpreter start."""
    return (
        "from __future__ import annotations\n\n"
        "def stub_maintainer_exists(maintainer: str) -> bool:\n"
        "    return True\n\n"
        "def stub_team_exists(org_team: str) -> bool:\n"
        "    return True\n\n"
        "def apply_smithy_maintainer_stubs() -> None:\n"
        "    try:\n"
        "        import conda_smithy.lint_recipe as lint_recipe\n"
        "    except ImportError:\n"
        "        return\n"
        "    lint_recipe._maintainer_exists = stub_maintainer_exists\n"
        "    lint_recipe._team_exists = stub_team_exists\n\n"
        "apply_smithy_maintainer_stubs()\n"
    )
