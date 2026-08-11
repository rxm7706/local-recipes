"""Smoke test for Story 7.1's ``pyforge.marshal.seed`` scaffold + ``marshal
seed`` CLI wiring: the module tree imports cleanly, and each of the six
stub verbs reports not-yet-implemented and exits clean. Mirrors
``tests/unit/test_cli.py``'s ``main([...])``/``capsys`` style -- no real
detect/plan/apply/Copier logic exists yet to exercise (Stories 7.2-7.6).
"""

from __future__ import annotations

import pytest
from pyforge.marshal.cli.main import main
from pyforge.marshal.core.verdict import EXIT_USAGE


def test_seed_package_imports_with_no_side_effects():
    import pyforge.marshal.seed  # noqa: F401


@pytest.mark.parametrize(
    "subpackage",
    [
        "model",
        "state",
        "regions",
        "detect",
        "plan",
        "apply",
        "engine",
        "derive",
        "migrate",
        "verbs",
        "templates",
    ],
)
def test_each_architecture_subpackage_imports(subpackage):
    """Architecture § 4's module tree names eleven stub subpackages -- a
    typo in any one directory name would otherwise pass silently, since
    the top-level `import pyforge.marshal.seed` above doesn't touch them."""
    import importlib

    importlib.import_module(f"pyforge.marshal.seed.{subpackage}")


@pytest.mark.parametrize(
    "verb", ["init", "adopt", "check", "update", "explain", "version"]
)
def test_seed_verb_stub_exits_zero_and_names_itself(verb, capsys):
    exit_code = main(["seed", verb])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == f"marshal seed {verb}: not yet implemented\n"


def test_bare_seed_is_a_usage_error(capsys):
    exit_code = main(["seed"])
    assert exit_code == EXIT_USAGE
    captured = capsys.readouterr()
    assert captured.err


def test_unknown_seed_verb_is_a_usage_error(capsys):
    exit_code = main(["seed", "bogus"])
    assert exit_code == EXIT_USAGE
    captured = capsys.readouterr()
    assert captured.err
