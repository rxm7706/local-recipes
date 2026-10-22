"""Local stand-ins for the network reads conda-smithy's lint makes.

CFE tests must not ask github.com whether a recipe maintainer exists
(``cfe-regression-net`` has no ``GH_TOKEN``; an unauthenticated HEAD from a
CI runner flaked on 2026-10-02), and must not fetch conda-smithy's two
remote lint files (mason Story 26.2: a DNS failure for
``raw.githubusercontent.com`` failed a local ``pr-preflight`` on 2026-10-22):

- ``linter.utils.load_linter_toml_metdata_internal`` fetches
  conda-forge-pinning's ``linter_hints/hints.toml``. The stub returns an
  empty hints table. It cannot return ``None``, conda-smithy's answer when the
  fetch fails: 3.62.0 then reads ``{}.get("hints", [])``, gets a list, and
  ``run_conda_forge_specific`` raises ``AttributeError`` for any recipe with
  requirements.
- ``validate_schema.validate_json_schema`` resolves the ``bot`` property of a
  recipe's ``conda-forge.yml`` through a ``$ref`` to regro/cf-scripts'
  ``cf_tick_schema.json``. ``CONDA_SMITHY_BOT_SCHEMA_URI`` (conda-smithy's own
  override) points it at the vendored copy in
  ``tests/fixtures/conda_smithy/``, so a malformed ``bot`` block still fails.

``tests/conftest.py`` installs these in-process and, via a ``PYTHONPATH``
sitecustomize, in the conda-smithy child that
``validate_recipe.run_external_lint`` starts.
"""
from __future__ import annotations

from pathlib import Path

CFE_STUB_SMITHY_LOOKUPS_ENV = "CFE_STUB_SMITHY_MAINTAINER_LOOKUPS"
BOT_SCHEMA_URI_ENV = "CONDA_SMITHY_BOT_SCHEMA_URI"
VENDORED_BOT_SCHEMA = (
    Path(__file__).resolve().parent / "fixtures" / "conda_smithy" / "cf_tick_schema.json"
)


def stub_maintainer_exists(maintainer: str) -> bool:
    """Local answer: the named maintainer exists."""
    return True


def stub_team_exists(org_team: str) -> bool:
    """Local answer: the named org/team exists."""
    return True


def stub_linter_hints(time_salt: int) -> dict:
    """Local answer: a hints file with no entries."""
    return {"hints": {}}


def bot_schema_uri() -> str:
    """The ``file://`` URI of the vendored ``cf_tick_schema.json``."""
    return VENDORED_BOT_SCHEMA.as_uri()


def apply_smithy_maintainer_stubs() -> None:
    """Replace conda-smithy's network reads. No-op if smithy is absent."""
    try:
        import conda_smithy.lint_recipe as lint_recipe
        import conda_smithy.linter.utils as linter_utils
    except ImportError:
        return
    lint_recipe._maintainer_exists = stub_maintainer_exists
    lint_recipe._team_exists = stub_team_exists
    linter_utils.load_linter_toml_metdata_internal = stub_linter_hints


def sitecustomize_source() -> str:
    """Self-contained sitecustomize that applies the stubs on interpreter start.

    The bot-schema URI travels in the environment, so the child needs no code
    for it.
    """
    return (
        "from __future__ import annotations\n\n"
        "def stub_maintainer_exists(maintainer: str) -> bool:\n"
        "    return True\n\n"
        "def stub_team_exists(org_team: str) -> bool:\n"
        "    return True\n\n"
        "def stub_linter_hints(time_salt: int) -> dict:\n"
        "    return {\"hints\": {}}\n\n"
        "def apply_smithy_maintainer_stubs() -> None:\n"
        "    try:\n"
        "        import conda_smithy.lint_recipe as lint_recipe\n"
        "        import conda_smithy.linter.utils as linter_utils\n"
        "    except ImportError:\n"
        "        return\n"
        "    lint_recipe._maintainer_exists = stub_maintainer_exists\n"
        "    lint_recipe._team_exists = stub_team_exists\n"
        "    linter_utils.load_linter_toml_metdata_internal = stub_linter_hints\n\n"
        "apply_smithy_maintainer_stubs()\n"
    )
