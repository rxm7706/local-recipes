"""Story 115.3 (CAP-13 amended 2026-11-10): a seed failure exits with the code its taxonomy documents.

At ``82a2b18828`` the seed handlers returned 5 (state invalid) and 10 (internal), and ``cli/main.py`` admitted
only AD-7's frozen ``{0, 1, 2, 3, 4, 130}``, turning both into 2. ``main`` now admits ``seed/errors.py``'s
``SEED_EXIT_CODES`` -- derived from the six leaves -- only when the dispatched command is ``seed``; every other
verb keeps the frozen domain, and ``GUARDED_EXIT_CODES`` does not move.

The literal expectations live here on purpose (an independent copy, like ``test_verdict.py``'s): they catch the
taxonomy or the frozen domain drifting.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.testing_kit.flags import flagd_tree

from pyforge.marshal.cli import main as main_module
from pyforge.marshal.cli import seed as seed_cli
from pyforge.marshal.cli.main import main
from pyforge.marshal.cli.retrofit_flags import VERB_FLAGS
from pyforge.marshal.core.verdict import EXIT_USAGE, GUARDED_EXIT_CODES
from pyforge.marshal.seed.errors import SEED_EXIT_CODES, InternalError, SeedError, StateInvalid
from pyforge.marshal.seed.model.manifest import ManifestError

_SEED_TAXONOMY = frozenset({1, 2, 3, 4, 5, 10})
_FROZEN_DOMAIN = frozenset({0, 1, 2, 3, 4, 130})


def _seed_check_flags_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``seed check``'s kill switches read ON from a tree of the test's own, never the checkout's."""
    keys = {key: "on" for key in VERB_FLAGS.get(("seed", "check"), ())}
    assert keys, "seed check names no kill switch -- this fixture is stale"
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, keys)))


# --- the taxonomy and the frozen domain ---------------------------------------------------------------------


def test_seed_exit_codes_is_the_six_leaves_codes():
    leaves = [leaf for leaf in SeedError.__subclasses__() if leaf.__module__ == SeedError.__module__]
    assert SEED_EXIT_CODES == _SEED_TAXONOMY == frozenset(leaf.exit_code for leaf in leaves)
    assert len(leaves) == len(SEED_EXIT_CODES)


def test_the_frozen_domain_does_not_move():
    assert GUARDED_EXIT_CODES == _FROZEN_DOMAIN


# --- real seed failures, through main --------------------------------------------------------------------------


def test_a_schema_breaking_state_file_exits_5_through_main(tmp_path: Path, capsys):
    """``seed accept`` reads ``.marshal/seed-state.yml`` and refuses a document that breaks its schema."""
    artifact_id = seed_cli._load_packaged_manifest().entries[0].id
    state_file = tmp_path / ".marshal" / "seed-state.yml"
    state_file.parent.mkdir()
    state_file.write_text("not_a_seed_state_field: true\n", encoding="utf-8")

    code = main(["seed", "accept", artifact_id, "--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == StateInvalid.exit_code == 5
    assert "does not match the seed-state schema" in captured.out + captured.err


def test_a_broken_packaged_manifest_exits_10_through_main(tmp_path: Path, monkeypatch, capsys):
    _seed_check_flags_on(tmp_path, monkeypatch)

    def _broken():
        raise ManifestError("manifest: simulated packaging failure")

    monkeypatch.setattr(seed_cli, "_load_packaged_manifest", _broken)

    code = main(["seed", "check", "--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == InternalError.exit_code == 10
    assert "reinstall pyforge-marshal" in captured.out + captured.err


# --- the admission is by dispatched command ----------------------------------------------------------------------


def _replace_subparser(monkeypatch: pytest.MonkeyPatch, module, attribute: str, command: str, value) -> None:
    def fake_add(subparsers):
        parser = subparsers.add_parser(command)
        parser.set_defaults(handler=lambda args: value)

    monkeypatch.setattr(module, attribute, fake_add)


@pytest.mark.parametrize("seed_code", sorted(_SEED_TAXONOMY))
def test_every_seed_code_a_seed_handler_returns_reaches_the_exit(monkeypatch, seed_code):
    _replace_subparser(monkeypatch, main_module.seed_cli, "add_seed_subparser", "seed", seed_code)
    assert main(["seed"]) == seed_code


@pytest.mark.parametrize("value", [77, 6, None, True])
def test_a_seed_handler_outside_its_taxonomy_still_clamps_to_usage(monkeypatch, value):
    _replace_subparser(monkeypatch, main_module.seed_cli, "add_seed_subparser", "seed", value)
    assert main(["seed"]) == EXIT_USAGE


@pytest.mark.parametrize("seed_only_code", sorted(_SEED_TAXONOMY - _FROZEN_DOMAIN))
def test_a_non_seed_handler_that_returns_a_seed_only_code_still_exits_2(monkeypatch, seed_only_code):
    _replace_subparser(monkeypatch, main_module.config_cli, "add_config_subparser", "config", seed_only_code)
    assert main(["config"]) == EXIT_USAGE == 2
