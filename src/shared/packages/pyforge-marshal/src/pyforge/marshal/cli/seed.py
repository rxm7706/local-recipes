"""``marshal seed`` (Story 7.1, AD-70) -- the seed-installer noun group's CLI
scaffold. Registers ``seed`` on the SAME ``subparsers`` object every other
noun group uses, with six nested verb actions (``init``/``adopt``/``check``/
``update``/``explain``/``version`` -- the same six verb names architecture
§ 4 assigns one file each under ``seed/verbs/`` in a later story; here they
are stub functions in THIS module, not yet split into that package),
mirroring ``cli/gate.py``'s ``add_gate_subparser`` nested-``evaluate``-action
shape: ``seed_subparsers = parser.add_subparsers(dest="seed_command",
required=True)``, one ``add_parser`` per verb. ``required=True`` means a
bare ``marshal seed`` with no verb is a clean argparse usage error, not a
silent no-op -- same convention as ``gate``'s own ``gate_command``.

Every verb here is a STUB (Story 7.1's own scope -- naming was contested
until the 2026-08-10 correct-course settled it: the installer lives
*inside* ``pyforge-marshal``, no new package, no second binary, no binding
revival of the retired ``genesis`` name): each prints a one-line message
naming itself as not yet implemented and returns ``EXIT_OK``, imported from
``core/verdict.py`` (AD-7's sole-ownership rule -- never a new exit-code
literal here; ``seed``'s own exit-code taxonomy is Story 7.2, gated on
pyforge-core landing first). No Copier import, no manifest/model/state/
detect/plan/apply/engine/derive/migrate logic lands here -- those belong to
Stories 7.2-7.6 and Epics 8-12.
"""

from __future__ import annotations

import argparse

from ..core.verdict import EXIT_OK


def run_init(args: argparse.Namespace) -> int:
    print("marshal seed init: not yet implemented")
    return EXIT_OK


def run_adopt(args: argparse.Namespace) -> int:
    print("marshal seed adopt: not yet implemented")
    return EXIT_OK


def run_check(args: argparse.Namespace) -> int:
    print("marshal seed check: not yet implemented")
    return EXIT_OK


def run_update(args: argparse.Namespace) -> int:
    print("marshal seed update: not yet implemented")
    return EXIT_OK


def run_explain(args: argparse.Namespace) -> int:
    print("marshal seed explain: not yet implemented")
    return EXIT_OK


def run_version(args: argparse.Namespace) -> int:
    print("marshal seed version: not yet implemented")
    return EXIT_OK


def add_seed_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``seed`` subcommand on ``main.py``'s subparser tree, with
    six nested verb actions -- mirrors ``cli/gate.py::add_gate_subparser``'s
    identical nested-subparsers shape, one level down (six verbs instead of
    one ``evaluate`` action)."""
    parser = subparsers.add_parser(
        "seed",
        help="Scaffold/adopt/check/update a project from Marshal's seed templates (AD-70).",
        description=(
            "The seed-installer noun group. Every verb below is a stub in "
            "this story (7.1) -- real detect/plan/apply/Copier logic lands "
            "in Stories 7.2-7.6 and Epics 8-12."
        ),
    )
    seed_subparsers = parser.add_subparsers(dest="seed_command", required=True)

    init_parser = seed_subparsers.add_parser(
        "init",
        help="Scaffold a brand-new project from Marshal's seed templates.",
        description="Stub (Story 7.1) -- greenfield materialization lands in a later story.",
    )
    init_parser.set_defaults(handler=run_init)

    adopt_parser = seed_subparsers.add_parser(
        "adopt",
        help="Adopt an existing project onto Marshal's seed templates.",
        description="Stub (Story 7.1) -- brownfield adoption lands in a later story.",
    )
    adopt_parser.set_defaults(handler=run_adopt)

    check_parser = seed_subparsers.add_parser(
        "check",
        help="Report whether a project's seed state matches its templates.",
        description="Stub (Story 7.1) -- conformance reporting lands in a later story.",
    )
    check_parser.set_defaults(handler=run_check)

    update_parser = seed_subparsers.add_parser(
        "update",
        help="Apply pending seed-template updates to a project.",
        description="Stub (Story 7.1) -- migration/update logic lands in a later story.",
    )
    update_parser.set_defaults(handler=run_update)

    explain_parser = seed_subparsers.add_parser(
        "explain",
        help="Explain what a seed operation would do without applying it.",
        description="Stub (Story 7.1) -- plan rationale rendering lands in a later story.",
    )
    explain_parser.set_defaults(handler=run_explain)

    version_parser = seed_subparsers.add_parser(
        "version",
        help="Report the seed templates' own version.",
        description="Stub (Story 7.1) -- model-version reporting lands in a later story.",
    )
    version_parser.set_defaults(handler=run_version)
