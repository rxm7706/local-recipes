"""Smoke test — the package imports and the argparse CLI skeleton answers
(Story 1.1).

Only the build-wiring shape is asserted here: version exposure, a clean
``deck --help`` exit, and a bare-invocation usage error. The real
``seed``/``pull``/``status``/``watch`` subcommands land in later stories.
"""

import pyforge.herald
from pyforge.herald.cli import main


def test_version_exposed():
    assert pyforge.herald.__version__ == "0.1.0"


def test_deck_help_exits_zero():
    assert main(["deck", "--help"]) == 0


def test_bare_invocation_is_a_usage_error():
    assert main([]) == 2


def test_deck_bare_invocation_is_a_usage_error():
    assert main(["deck"]) == 2


def test_version_flag_exits_zero():
    assert main(["--version"]) == 0
