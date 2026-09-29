"""Smoke test for Story 7.1's ``pyforge.marshal.seed`` scaffold + ``marshal
seed`` CLI wiring: the module tree imports cleanly, and each verb dispatches
through ``main()`` to its real implementation (no stubs remain after Story
11.6). Mirrors ``tests/unit/test_cli.py``'s ``main([...])``/``capsys`` style.

``check`` (Story 10.5), ``adopt`` (Story 10.6), ``init`` (Story 10.7),
``update`` (Story 11.4), ``explain``, and ``version`` (Story 11.6) are no
longer stubs -- each is excluded from the parametrized stub-verb test below
and gets its own smoke test proving the full ``main()`` dispatch path
reaches the real verb; dedicated CLI unit tests cover exit-code/rendering
behavior in full.
"""

from __future__ import annotations

import pytest

from pyforge.marshal.cli.main import main
from pyforge.marshal.core.verdict import EXIT_USAGE
from pyforge.marshal.seed.errors import (
    ConformanceFailure,
    PreconditionFailure,
    UsageError,
)


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


def test_seed_explain_is_no_longer_a_stub(capsys):
    exit_code = main(["seed", "explain", "agents-md"])

    captured = capsys.readouterr()
    assert "not yet implemented" not in captured.out
    assert "marshal seed explain" in captured.out
    assert exit_code == 0


def test_seed_version_is_no_longer_a_stub(tmp_path, capsys):
    exit_code = main(["seed", "version", "--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert "not yet implemented" not in captured.out
    assert "marshal seed version" in captured.out
    assert "bundled_model_version:" in captured.out
    assert exit_code == 0


def test_bare_seed_explain_is_a_usage_error(capsys):
    exit_code = main(["seed", "explain"])
    assert exit_code == EXIT_USAGE
    captured = capsys.readouterr()
    assert captured.err


def test_seed_check_is_no_longer_a_stub(tmp_path, capsys):
    """The first verb this test file's own stub loop no longer covers (Story
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


def test_seed_adopt_is_no_longer_a_stub(tmp_path, capsys):
    """The second verb this test file's own stub loop no longer covers
    (Story 10.6): dispatched through the real ``main()`` against an
    explicit ``--repo-root`` (mirroring ``test_seed_check_is_no_longer_a_
    stub``'s own convention exactly, and for the identical reason -- a bare
    ``main(["seed", "adopt"])`` would default ``--repo-root`` to wherever
    pytest happens to be invoked from). ``tmp_path`` is not a git repo at
    all, so ``adopt`` -- a MUTATING verb, unlike ``check`` -- reaches
    ``verbs.preconditions.check_preconditions``'s rung 1 and refuses before
    writing anything: exit code 3 (``PreconditionFailure``), never 0."""
    exit_code = main(["seed", "adopt", "--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert "not yet implemented" not in captured.out
    assert "not-a-git-repo" in captured.out
    assert exit_code == PreconditionFailure.exit_code
    assert not (tmp_path / ".marshal").exists()


def test_seed_init_is_no_longer_a_stub(tmp_path, capsys):
    """The third verb this test file's own stub loop no longer covers
    (Story 10.7): dispatched through the real ``main()`` against an
    explicit target directory (``init``'s own positional ``<path>``, unlike
    ``check``/``adopt``'s ``--repo-root`` flag). Exercises FR-78's own
    non-empty-directory refusal rather than a real bootstrap+materialize
    run: `init` (unlike `adopt`) WOULD bootstrap a fresh git repo and
    proceed all the way to `run_apply` against the real packaged manifest,
    whose whole-file content the packaged template tree does not yet ship
    (`verbs/adopt.py`'s own documented "known limitations" (1)) -- a
    deterministic, side-effect-free refusal proves the real verb is wired
    without depending on that still-incomplete content."""
    (tmp_path / "something.txt").write_text("pre-existing\n", encoding="utf-8")

    exit_code = main(["seed", "init", str(tmp_path)])

    captured = capsys.readouterr()
    assert "not yet implemented" not in captured.out
    assert "adopt" in captured.out
    assert exit_code == UsageError.exit_code
    assert not (tmp_path / ".git").exists()


def test_seed_update_is_no_longer_a_stub(tmp_path, capsys):
    """The fourth verb this test file's own stub loop no longer covers
    (Story 11.4): dispatched through the real ``main()`` against an
    explicit ``--repo-root`` (mirroring ``test_seed_adopt_is_no_longer_a_
    stub``'s own convention exactly, for the identical reason).
    ``tmp_path`` is not a git repo at all, so ``update`` -- a MUTATING verb,
    like ``adopt`` -- reaches ``verbs.preconditions.check_preconditions``'s
    rung 1 and refuses before writing anything: exit code 3
    (``PreconditionFailure``), never 0."""
    exit_code = main(["seed", "update", "--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert "not yet implemented" not in captured.out
    assert "not-a-git-repo" in captured.out
    assert exit_code == PreconditionFailure.exit_code
    assert not (tmp_path / ".marshal").exists()


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
