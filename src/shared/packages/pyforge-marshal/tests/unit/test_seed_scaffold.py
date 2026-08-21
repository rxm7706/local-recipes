"""Smoke test for Story 7.1's ``pyforge.marshal.seed`` scaffold + ``marshal
seed`` CLI wiring: the module tree imports cleanly, and each of the five
still-stub verbs reports not-yet-implemented and exits clean. Mirrors
``tests/unit/test_cli.py``'s ``main([...])``/``capsys`` style -- no real
detect/plan/apply/Copier logic exists yet to exercise (Epics 8, 10.6, 10.7,
11, 12).

``check`` (Story 10.5) is no longer a stub -- it is excluded from the
parametrized stub-verb test below (unlike its five siblings, it never
prints "not yet implemented") and gets its own smoke test proving the full
``main()`` dispatch path reaches the real verb; ``tests/unit/
test_seed_cli_seed_check.py`` covers its exit-code/rendering behavior in
full.
"""

from __future__ import annotations

import pytest
from pyforge.marshal.cli.main import main
from pyforge.marshal.core.verdict import EXIT_USAGE
from pyforge.marshal.seed.errors import ConformanceFailure


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


@pytest.mark.parametrize("verb", ["init", "adopt", "update", "explain", "version"])
def test_seed_verb_stub_exits_zero_and_names_itself(verb, capsys):
    exit_code = main(["seed", verb])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == f"marshal seed {verb}: not yet implemented\n"


def test_seed_check_is_no_longer_a_stub(tmp_path, capsys):
    """The one verb this test file's own stub loop no longer covers (Story
    10.5): dispatched through the real ``main()`` -- not a hand-built
    ``argparse.Namespace`` -- against an explicit ``--repo-root`` so the
    result does not depend on wherever pytest happens to be invoked from."""
    exit_code = main(["seed", "check", "--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert "not yet implemented" not in captured.out
    assert "marshal seed check" in captured.out
    # A bare tmp_path is not a git repo at all -- `run_check`'s own
    # `classify()`/`build_plan()` calls run fine against a non-git target
    # (P-03: no VCS dependency anywhere in the detect/plan primitives this
    # command composes), so this still exercises the real verb end to end
    # rather than a git-specific precondition this command never checks
    # (`verbs.preconditions` is a mutating-verb gate `check` never calls).
    # The specific exit code is asserted, not just non-zero (review
    # finding): a never-adopted repo reports every manifest artifact as
    # `ARTIFACT_MISSING` (HARD), so this must be exactly
    # `ConformanceFailure.exit_code` -- a regression that silently changed
    # it to, say, `UsageError`'s 2 would pass a bare `!= 0` assertion
    # unnoticed, even though this story's whole point is wiring the
    # six-leaf exit-code taxonomy correctly.
    assert exit_code == ConformanceFailure.exit_code


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
