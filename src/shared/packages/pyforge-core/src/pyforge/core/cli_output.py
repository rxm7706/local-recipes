"""pyforge.core.cli_output -- one way to ask any station for JSON (steward Story 144.1).

The fleet grew two spellings for the same request: ``--json`` (doctor, herald, steward) and
``--format json`` (marshal, mason, warden), with some verbs holding both. A caller scripting
several stations had to know which each verb took.

``align_json_options(parser)`` walks a built ``argparse`` tree once and gives every parser that
accepts ONE spelling the other, writing to the same destination, so both mean the same thing on
every verb:

* a parser with a ``--json`` flag and no ``--format`` gains ``--format {text,json}``;
* a parser whose ``--format`` takes exactly ``text`` and ``json`` and that has no ``--json``
  gains ``--json``.

A ``--format`` with any other choice set (a list of formatter names, say) is another option
that happens to share the name and is left alone, as is a parser that already holds both.
Nothing is renamed or removed: every invocation that parsed before parses the same way. That includes
abbreviations. ``argparse`` accepts any unambiguous prefix of an option, so a new ``--format`` would make
``--f`` ambiguous on a parser that has ``--fleet``. A twin is therefore matched only when spelled in full:
it never takes part in prefix matching, so every prefix resolves as it did before.

A parser whose own subcommand has a ``--format`` of another kind (``glass export --format csv``) gets no
``--format`` twin, so one command line never carries two meanings of the word.

Stdlib only (``argparse``): the leaf rule holds.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sequence
from typing import Any

JSON_FLAG = "--json"
FORMAT_FLAG = "--format"
TEXT, JSON = "text", "json"
FORMAT_CHOICES = (TEXT, JSON)

_TWINS_ATTR = "_pyforge_json_twins"


class _FormatSetsJson(argparse.Action):
    """``--format text|json`` on a parser whose own option is the ``--json`` flag: sets that
    flag's destination to whether ``json`` was asked for."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        setattr(namespace, self.dest, values == JSON)


def iter_parsers(parser: argparse.ArgumentParser) -> Iterator[argparse.ArgumentParser]:
    """``parser`` and every subparser beneath it, each once (an alias names its parser twice)."""
    seen: set[int] = set()
    stack = [parser]
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        for action in current._actions:  # noqa: SLF001 -- argparse offers no public walk of its subparsers
            if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
                stack.extend(action.choices.values())


def _option(parser: argparse.ArgumentParser, flag: str) -> argparse.Action | None:
    for action in parser._actions:  # noqa: SLF001
        if flag in action.option_strings:
            return action
    return None


def _is_text_json(action: argparse.Action | None) -> bool:
    """Whether an option's choices are exactly ``text`` and ``json``, in either order."""
    return action is not None and action.choices is not None and set(action.choices) == set(FORMAT_CHOICES)


def json_spellings(parser: argparse.ArgumentParser) -> frozenset[str]:
    """Which of ``--json`` and ``--format`` (taking ``text``/``json``) one parser accepts."""
    found = set()
    if _option(parser, JSON_FLAG) is not None:
        found.add(JSON_FLAG)
    if _is_text_json(_option(parser, FORMAT_FLAG)):
        found.add(FORMAT_FLAG)
    return frozenset(found)


def json_twins(parser: argparse.ArgumentParser) -> tuple[argparse.Action, ...]:
    """The options ``align_json_options`` added to this one parser."""
    return tuple(getattr(parser, _TWINS_ATTR, ()))


def _a_subcommand_has_another_format(parser: argparse.ArgumentParser) -> bool:
    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            for child in action.choices.values():
                fmt = _option(child, FORMAT_FLAG)
                if fmt is not None and not _is_text_json(fmt):
                    return True
    return False


def _add_twin(parser: argparse.ArgumentParser, *flags: str, **kwargs: Any) -> None:
    """Add one twin and keep it out of prefix matching, so no abbreviation that resolved before turns ambiguous."""
    twin = parser.add_argument(*flags, **kwargs)
    twins: list[argparse.Action] | None = getattr(parser, _TWINS_ATTR, None)
    if twins is None:
        twins = []
        setattr(parser, _TWINS_ATTR, twins)
        original = parser._get_option_tuples  # noqa: SLF001 -- argparse's one prefix-matching hook

        def without_twins(option_string: str) -> list[Any]:
            return [match for match in original(option_string) if match[0] not in twins]

        parser._get_option_tuples = without_twins  # type: ignore[method-assign]  # noqa: SLF001
    twins.append(twin)


def align_json_options(parser: argparse.ArgumentParser) -> int:
    """Give every parser under ``parser`` that accepts one JSON spelling the other; return how many gained one."""
    gained = 0
    for current in iter_parsers(parser):
        json_flag = _option(current, JSON_FLAG)
        fmt = _option(current, FORMAT_FLAG)
        if json_flag is not None and fmt is None:
            if not isinstance(json_flag, argparse._StoreTrueAction):  # noqa: SLF001 -- only a plain flag has a twin
                continue
            if _a_subcommand_has_another_format(current):
                continue
            _add_twin(
                current,
                FORMAT_FLAG,
                choices=FORMAT_CHOICES,
                action=_FormatSetsJson,
                dest=json_flag.dest,
                default=argparse.SUPPRESS,
                help=f"output format; `{FORMAT_FLAG} {JSON}` is `{JSON_FLAG}`",
            )
            gained += 1
        elif json_flag is None and fmt is not None:
            if not _is_text_json(fmt):
                continue
            _add_twin(
                current,
                JSON_FLAG,
                action="store_const",
                const=JSON,
                dest=fmt.dest,
                default=argparse.SUPPRESS,
                help=f"`{FORMAT_FLAG} {JSON}`",
            )
            gained += 1
    return gained
