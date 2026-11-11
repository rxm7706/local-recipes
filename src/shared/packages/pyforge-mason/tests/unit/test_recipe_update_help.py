"""Story 37.3 -- `mason recipe update`'s verb help and its `--dry-run` help say the same thing.

The operator ruled on 2026-09-14 that `recipe update` writes by default and `--dry-run` is the
plan-only path. The verb help used to promise the plan "in both the default and --dry-run paths",
against its own `--dry-run` line. These tests read the parser `build_parser()` builds, so they pin
what `mason recipe update --help` prints, not a module constant.
"""

from __future__ import annotations

import argparse

from pyforge.mason.cli import build_parser


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise AssertionError(f"{parser.prog!r} has no subcommands")


def _update_parser() -> argparse.ArgumentParser:
    recipe = _subparsers(build_parser()).choices["recipe"]
    return _subparsers(recipe).choices["update"]


def _update_listing_help() -> str:
    # The `help=` string `mason recipe --help` lists against `update`.
    recipe = _subparsers(build_parser()).choices["recipe"]
    for choice in _subparsers(recipe)._choices_actions:
        if choice.dest == "update":
            return str(choice.help)
    raise AssertionError("`mason recipe` lists no `update` verb")


def _dry_run_help() -> str:
    for action in _update_parser()._actions:
        if "--dry-run" in action.option_strings:
            return str(action.help)
    raise AssertionError("`mason recipe update` has no --dry-run option")


def test_update_description_names_the_default_write() -> None:
    description = str(_update_parser().description)
    assert "writes the field-scoped update by default" in description


def test_update_description_names_dry_run_as_the_plan_only_path() -> None:
    description = str(_update_parser().description)
    assert "--dry-run computes and shows the plan without writing" in description


def test_update_description_never_promises_the_plan_in_both_paths() -> None:
    description = str(_update_parser().description)
    assert "shows the plan before writing" not in description
    assert "both" not in description


def test_update_listing_help_is_the_description() -> None:
    # One string serves `mason recipe --help` and `mason recipe update --help`.
    assert _update_listing_help() == _update_parser().description


def test_update_description_agrees_with_the_dry_run_help() -> None:
    description = str(_update_parser().description)
    dry_run = _dry_run_help()
    # Both say the plan-only path does not write, and both say the default writes.
    assert "without writing" in description
    assert "without writing" in dry_run
    assert "writes the field-scoped update" in description
    assert "writes the field-scoped update" in dry_run
