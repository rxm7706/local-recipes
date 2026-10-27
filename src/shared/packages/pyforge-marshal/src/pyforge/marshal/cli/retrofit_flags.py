"""Kill switches for marshal's pre-rule runtime capabilities (Epic 110; ``spec-feature-flag-governance`` CAP-7).

Every capability the flag inventory (``docs/governance/flag-inventory/pyforge-marshal.md``) reads as reachable at
runtime and minted before the rule date sits behind one flag that defaults ON (Q6: one flag per CAP). Two shapes
live here; the behaviour-shaped switches read their key at the one site the behaviour lives (``core/policy.py``,
``cli/status.py``, ...) and are not in this table.

* **A verb switch (Q3).** ``VERB_FLAGS`` maps a verb path -- ``("status",)``, ``("factory", "spin")`` -- to the keys
  that gate it. With a key OFF the verb stays listed in ``--help`` marked disabled (:func:`mark_disabled_help`)
  and refuses with marshal's usage code: :func:`require_verb_flags` raises ``pyforge.core.flags.FlagOff``, which
  ``cli/main.py`` already projects to ``EXIT_USAGE``. No new exit code (the frozen domain holds).
* **An invariant switch.** A capability whose OFF state would re-open a defect it closed (``branch_merged`` on
  ancestry alone, landing on a self-report) is wired the same way: the verb that depends on it refuses, and the
  defect never reopens (operator ruling 2026-10-26, R3).

Every key is spelled literally here so the gate's orphan check and the retirement walk can find it, and every read
goes through ``pyforge.core.flags`` (``canopy:AD-11``: one tree, no second reader). A checkout with no tree reads
every switch ON -- the retrofit default -- with no read and no warning; a tree that lacks a key reads ``default``
(ON) with ``read_boolean``'s one named WARN.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path

from pyforge.core.cutover_root import resolve_flags_path
from pyforge.core.flags import disabled_help, require

RETROFIT_DEFAULT = True  # a kill switch: ON until the operator turns it off

# The landing invariants gate every verb that lands a story by hand: `land` and `deploy land-story` (finding 15
# of the retrofit review). A supervisor or finalize process already running is not stopped: a switch turned OFF
# refuses the next landing, never one in flight.
_LANDING_VERBS: tuple[tuple[str, ...], ...] = (("land",), ("deploy", "land-story"))

_DISPATCH_VERBS: tuple[tuple[str, ...], ...] = (
    ("factory", "dispatch"),
    ("factory", "dispatch-attach"),
    ("factory", "dispatch-resume"),
    ("factory", "drain"),
)

# key -> the verb paths it gates (one row per CAP; the inventory's reach column names the module).
KEY_VERBS: Mapping[str, tuple[tuple[str, ...], ...]] = {
    "pyforge.marshal.loop_homes": (("factory", "spin"),),  # CAP-1
    "pyforge.marshal.supervised_runs": (
        ("factory", "attach"),
        ("factory", "resume"),
        ("factory", "checkpoint"),
    ),  # CAP-2
    "pyforge.marshal.gate_evaluate": (("gate", "evaluate"),),  # CAP-3
    "pyforge.marshal.fleet_status": (("status",),),  # CAP-5
    "pyforge.marshal.policy_composition": (("init",), ("preflight",), ("homes",), ("teardown",)),  # CAP-7
    "pyforge.marshal.seed_explain": (("seed", "explain"),),  # CAP-10
    "pyforge.marshal.managed_regions": (("seed", "update"),),  # CAP-11
    "pyforge.marshal.seed_adopt": (("seed", "adopt"),),  # CAP-12
    "pyforge.marshal.seed_check": (("seed", "check"),),  # CAP-13
    "pyforge.marshal.genesis_state_file": (("seed", "init"), ("seed", "adopt"), ("seed", "update")),  # CAP-17
    "pyforge.marshal.watch": (("watch",),),  # CAP-154
    "pyforge.marshal.completion_from_facts": _DISPATCH_VERBS,  # CAP-160
    "pyforge.marshal.verify_before_landing": (*_DISPATCH_VERBS, *_LANDING_VERBS),  # CAP-161
    "pyforge.marshal.dispatch_lands_via_land": _DISPATCH_VERBS,  # CAP-162
    "pyforge.marshal.branch_merged_divergence": _DISPATCH_VERBS,  # CAP-167
    "pyforge.marshal.single_followup_review": _DISPATCH_VERBS,  # CAP-169
    "pyforge.marshal.promotion_on_landing": _LANDING_VERBS,  # CAP-229
    "pyforge.marshal.guild_env_shellouts": (("watch",), ("gate", "evaluate")),  # CAP-263
    "pyforge.marshal.ledger_promotion_to_origin": _LANDING_VERBS,  # CAP-277
    "pyforge.marshal.switch_script_placement": _LANDING_VERBS,  # CAP-278
    "pyforge.marshal.seed_check_rendered_paths": (("seed", "check"),),  # CAP-279
    "pyforge.marshal.drain_followup_review": (("factory", "drain"),),  # CAP-281
    "pyforge.marshal.landing_memlog_union": _LANDING_VERBS,  # CAP-283
    "pyforge.marshal.model_list_refresh": (("adapters", "models"),),  # CAP-285
}


def _verb_flags() -> dict[tuple[str, ...], tuple[str, ...]]:
    table: dict[tuple[str, ...], list[str]] = {}
    for key, paths in KEY_VERBS.items():
        for path in paths:
            table.setdefault(path, []).append(key)
    return {path: tuple(keys) for path, keys in table.items()}


# verb path -> the keys that gate it, derived once from KEY_VERBS.
VERB_FLAGS: Mapping[tuple[str, ...], tuple[str, ...]] = _verb_flags()


def verb_path(args: argparse.Namespace) -> tuple[str, ...]:
    """The invoked verb path: ``command`` plus its ``<command>_command`` sub-verb when the parser set one."""
    command = getattr(args, "command", None)
    if not isinstance(command, str):
        return ()
    sub = getattr(args, f"{command}_command", None)
    return (command, sub) if isinstance(sub, str) else (command,)


def require_verb_flags(args: argparse.Namespace, *, flags_path: Path | str | None = None) -> None:
    """Raise ``FlagOff`` naming the first OFF key that gates the invoked verb; return when every one reads ON.

    No tree (``resolve_flags_path`` finds none and no ``flags_path`` is given) reads every switch ON without a read.
    """
    keys = VERB_FLAGS.get(verb_path(args), ())
    if not keys:
        return
    path = resolve_flags_path(flags_path)
    if path is None:
        return
    for key in keys:
        require(key, RETROFIT_DEFAULT, flags_path=path)


def _subparsers_action(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
    for action in parser._actions:  # noqa: SLF001 -- argparse keeps its subparser action private
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            return action
    return None


def mark_disabled_help(parser: argparse.ArgumentParser, *, flags_path: Path | str | None = None) -> None:
    """Append ``disabled_help``'s marker to the help of every gated verb whose key reads OFF (Q3: still listed).

    Walks ``VERB_FLAGS`` through argparse's choice actions (the entries ``--help`` lists); a path the parser does
    not know is skipped. With no tree nothing is marked.
    """
    path = resolve_flags_path(flags_path)
    if path is None:
        return
    for verb, keys in VERB_FLAGS.items():
        action = _subparsers_action(parser)
        choice = None
        for depth, name in enumerate(verb):
            if action is None:
                choice = None
                break
            choice = next((c for c in action._choices_actions if c.dest == name), None)  # noqa: SLF001
            if choice is None:
                break
            if depth + 1 < len(verb):
                action = _subparsers_action(action.choices[name])
        if choice is None:
            continue
        text = choice.help or ""
        for key in keys:
            text = disabled_help(text, key, RETROFIT_DEFAULT, flags_path=path)
        choice.help = text


def gated_verbs(key: str) -> Sequence[tuple[str, ...]]:
    """The verb paths ``key`` gates (the two-state tests read this, so a row cannot drift from its test)."""
    return KEY_VERBS.get(key, ())
