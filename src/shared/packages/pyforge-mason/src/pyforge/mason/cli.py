"""Mason's command surface.

Story 1.2 replaces Story 1.1's flat, single-level dispatcher with a two-level
noun -> verb argparse tree. The three noun groups were declared in Story 1.1
because the seam is a **capability** decision, not an implementation one
(chain decision D-1, "Option C"):

* ``recipe``       — WRAPS the conda-forge-expert craft by subprocess. The skill
                     stays canonical for recipe semantics and keeps improving
                     through the Rule-2 retro loop. Never forked: a fork is
                     structurally adversarial, because Rule 2 mandates that every
                     conda-forge effort *edits the skill*.
* ``package``      — built natively; no wheel-build/upload path exists to wrap.
* ``environment``  — built natively; no lock orchestration exists to wrap.

``doctor`` is a fourth, top-level leaf (OQ-A4) with no verb level — its real
diagnosis lands in Story 1.8; here it is a stub, same pattern as the other
nouns were in Story 1.1.

No verb was registered under any noun through Story 1.2 — later stories
populate them by editing ``build_parser()`` directly: capture the return
value of that noun's ``add_subparsers()`` call and register real verbs on
it there, in the same function. (argparse forbids calling
``add_subparsers()`` a second time on one parser, so this cannot be done
from outside ``build_parser()`` after the fact.) A single generic loop
builds the three verb-bearing nouns, capturing each one's verb-subparsers
action into a local ``_noun_verbs`` dict; ``doctor`` has no verb level by
design (OQ-A4) and is built separately, immediately after that loop. Story
2.7 is the first to use that seam, registering ``recipe diagnose`` on
``_noun_verbs["recipe"]`` right after the loop — ``package``/``environment``
stay behavior-identical (their own captured actions are never given a verb).
Story 2.8 registers two more verbs on that same noun, ``recipe optimize``
and ``recipe scan``, each a single required ``recipe_path`` positional
mirroring ``diagnose``'s own ``log_path`` shape.

argparse, not click/typer: FR-41 forbids a CLI-framework dependency, and the
sibling stations dispatch the same way.
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import math
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__, doctor, recipe, render
from .errors import CfeUnresolvedError, MasonError
from .exit_codes import (
    EXIT_CFE_UNAVAILABLE, EXIT_FAILED, EXIT_INTERRUPTED, EXIT_OK, EXIT_USAGE,
)

# main() is the sole owner of the process exit code. A verb never calls
# sys.exit() directly; it returns an int and main() projects it. The
# exit-code contract lives in exit_codes.py (AD-7), and an argparse-raised
# SystemExit's own code (0 or 2) passes through in main()'s handler.

_NOUNS = {
    "recipe": "author, validate and build conda recipes (wraps the conda-forge-expert craft)",
    "package": "build and ship distributions to PyPI and conda-forge",
    "environment": "resolve conflicting worlds into one lockfile",
}
_DOCTOR_HELP = "diagnose the installed Mason: version, CFE resolution, engine presence"
_RECIPE_DIAGNOSE_HELP = "diagnose a build-failure log via CFE's failure analyzer"
_RECIPE_OPTIMIZE_HELP = "lint a recipe for quality findings via CFE's recipe optimizer"
_RECIPE_SCAN_HELP = "scan a recipe's dependencies for known vulnerabilities via CFE's scanner"

# AD-13: every global setting has a flag and an environment-variable form,
# resolved uniformly flag -> environment -> default. These names are the
# public surface `_resolve_str`/`_resolve_bool` read from `os.environ`.
_ENV_CFE_ROOT = "MASON_CFE_ROOT"
_ENV_CFE_PYTHON = "MASON_CFE_PYTHON"
_ENV_CFE_TIMEOUT = "MASON_CFE_TIMEOUT"
_ENV_FORMAT = "MASON_FORMAT"
_ENV_VERBOSE = "MASON_VERBOSE"
_ENV_QUIET = "MASON_QUIET"

# Falsy env-var spellings for the boolean resolver, case-insensitive, after
# stripping whitespace. An unset env var is handled by falling back to
# `default` rather than being matched against this set.
_FALSY_ENV_VALUES = frozenset({"", "0", "false", "no"})


def _resolve_str(flag_value: str | None, env_var_name: str, default: str) -> str:
    """Resolve a string setting: flag -> environment -> default (AD-13).

    A whitespace-only value is treated as though it were absent at whichever
    step supplied it, so resolution falls through to the next step in the
    chain; a value that survives is returned with surrounding whitespace
    stripped. Both rules apply uniformly to the flag and the environment
    variable.
    """
    if flag_value is not None and flag_value.strip():
        return flag_value.strip()
    raw = os.environ.get(env_var_name)
    if raw is not None and raw.strip():
        return raw.strip()
    return default


def _resolve_bool(flag_value: bool | None, env_var_name: str, default: bool) -> bool:
    """Resolve a boolean setting: flag -> environment -> default (AD-13).

    The environment value is stripped and lowercased before comparison
    against `_FALSY_ENV_VALUES`; anything else present is truthy.
    """
    if flag_value is not None:
        return flag_value
    raw = os.environ.get(env_var_name)
    if raw is None:
        return default
    return raw.strip().lower() not in _FALSY_ENV_VALUES


def _parse_finite_float(raw: str) -> float:
    """`argparse`'s `type=` callable for `--cfe-timeout`: parses like `float`,
    but rejects `nan`/`inf`/`-inf` and non-positive values, and reports a
    non-numeric value in Mason's own words (review pass, 2026-08-09;
    extended 2026-08-10).

    Letting the bare `ValueError` from `float()` escape would make argparse
    fall back to naming the `type=` callable itself -- `invalid
    _parse_finite_float value: '30s'`, leaking a private helper's name into
    a user-facing usage error. Every rejection path here therefore raises
    `argparse.ArgumentTypeError` with the flag's real name.

    Python's `float()` happily parses `nan`/`inf`/`-inf` -- they are not a
    malformed value, so `_resolve_optional_float`'s "unparseable -> None"
    fallback below would never catch them, and a `nan`/`inf` deadline handed
    to a future `subprocess.wait(timeout=...)` call is either meaningless
    (`nan` compares false against everything, effectively never expiring) or
    silently defeats the whole point of a mandatory timeout (`inf`). Zero
    and negative values are equally unusable, just via the opposite failure
    mode: they expire before the delegated operation has any chance to run
    at all. Raising `argparse.ArgumentTypeError` here gives the same clean
    usage-error behavior argparse already produces for a non-numeric
    `--cfe-timeout` value, rather than accepting a value that is well-formed
    but unusable.
    """
    try:
        value = float(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid --cfe-timeout value: {raw!r} (must be a number of seconds)"
        ) from None
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(
            f"invalid --cfe-timeout value: {raw!r} (must be a finite, positive number)"
        )
    return value


def _resolve_optional_float(flag_value: float | None, env_var_name: str) -> float | None:
    """Resolve an optional float setting: flag -> environment -> `None` (AD-13).

    Unlike `_resolve_str`/`_resolve_bool`, there is no Mason-wide `default`
    parameter here: `--cfe-timeout`'s terminal fallback is always `None` --
    PRD FR-4's "per-operation default" lives at a future call site (Story
    2.1's CFE adapter), not in this resolver. The environment value is
    stripped before parsing; a value that is unset, whitespace-only, not
    parseable as `float`, or parses to a non-finite or non-positive value
    (`nan`/`inf`/`-inf`/`0`/negative -- review pass, 2026-08-09, extended
    2026-08-10, mirroring `_parse_finite_float`'s flag-side guard above)
    all fall back to `None` rather than raising -- matching `_resolve_str`'s
    treatment of a malformed/absent environment value as "not supplied,"
    not a usage error.

    The *flag* value is held to the identical finite-and-positive standard
    (review pass, 2026-08-10). Validating only the environment half left the
    two halves of one knob disagreeing: `nan`/`inf`/`0`/negative resolved to
    `None` from the environment but passed straight through from the flag
    parameter -- so this resolver could hand a caller exactly the value
    `_parse_finite_float` and `cfe.run_streamed` both reject as unusable.
    `--cfe-timeout` itself cannot deliver one (argparse runs
    `_parse_finite_float` first), but a direct, non-argparse caller can, and
    the resolver is the wrong place to launder it. An unusable flag value
    falls *through* to the environment rather than short-circuiting to
    `None` -- the same "absent at whichever step supplied it" rule
    `_resolve_str` applies to a whitespace-only flag value. A flag value
    that is not a real number at all (a `str` that never went through
    `_parse_finite_float`, a `Decimal`) falls through the same way rather
    than reaching `math.isfinite` and raising its bare "must be real number,
    not str" -- a message naming neither this function nor the parameter,
    and exactly the defect `cfe.run_streamed`'s own `timeout` guard was
    given an isinstance check for (review pass, 2026-08-10, third).
    """
    if (
        flag_value is not None
        # `bool` is a subclass of `int`, so `True` clears both numeric checks
        # below and would be returned verbatim -- and `cfe.run_streamed`
        # rejects a bool `timeout` outright, which is exactly the
        # disagreement between this resolver and its consumer that the
        # paragraph above claims to have closed (review pass, 2026-08-10,
        # second). The `(int, float)` check must likewise precede
        # `math.isfinite`, which raises on anything else.
        and not isinstance(flag_value, bool)
        and isinstance(flag_value, (int, float))
        and math.isfinite(flag_value)
        and flag_value > 0
    ):
        return flag_value
    raw = os.environ.get(env_var_name)
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        parsed = float(raw)
    except ValueError:
        return None
    if not math.isfinite(parsed) or parsed <= 0:
        return None
    return parsed


def _configure_logging(verbose: bool, quiet: bool) -> None:
    """Configure stdlib `logging` to stderr, level per verbosity (FR-49, AD-25).

    Called once, in `main()`, immediately after `parser.parse_args(argv)`
    returns successfully and before any noun dispatch, so every command path
    that reaches that point (bare invocation, `doctor`, the custom bare-noun
    usage error) is covered uniformly. This does NOT cover a usage error
    `argparse` itself raises *during* `parse_args` (an invalid `--format`
    choice, a non-numeric `--cfe-timeout`, an unrecognized flag) -- those
    raise `SystemExit` before this call is ever reached, and today that is
    harmless because nothing on that path calls into `logging`; a future
    change that logs from inside a custom argparse validator would need its
    own configuration, not assume this one already ran (review pass,
    2026-08-09). `--quiet` wins when both `--verbose` and `--quiet` are
    given -- a documented tie-break; the spec's Acceptance Criteria don't
    specify one, so `quiet` (the more conservative choice) was picked.

    That tie-break is applied to the two *resolved* values, after each knob
    has independently run AD-13's flag -> environment -> default chain --
    so `MASON_QUIET=1` in the environment beats an explicit `--verbose` on
    the command line (review pass, 2026-08-10). This follows from AD-13's
    per-knob precedence rule rather than contradicting it (`--verbose` did
    win its own chain; `quiet` then won the tie-break), but it is
    surprising enough to state outright: a stale `MASON_QUIET` in a shell
    profile silently mutes a `--verbose` run, and clearing it -- not adding
    a flag -- is the fix.

    `force=True` is load-bearing, not cosmetic: `logging.basicConfig` only
    configures the root logger the *first* time it is called in a process by
    default, so a second `main()` invocation within one process (as happens
    repeatedly in this test suite) would silently no-op without it, leaving
    an earlier test's level/stream configuration in place. Its cost, for
    whoever writes the first test that asserts on a real log record: `force`
    *removes* every existing root handler, including the one pytest's
    `caplog` fixture installs -- so records emitted after a `main()` call in
    the same test do not reach `caplog.text` (they reach stderr, where
    `capsys` sees them). Assert via `capsys`. Re-entering
    `caplog.at_level(...)` after the `main()` call does NOT restore capture
    and was wrong advice (review pass, 2026-08-10, third): `at_level` only
    adjusts levels, and the handler itself is gone, so `caplog.text` stays
    empty while the record is plainly visible on stderr. Re-attaching it by
    hand (`logging.getLogger().addHandler(caplog.handler)`) does work, and
    only because `caplog`'s handler wraps a `StringIO` whose `close()` is a
    no-op -- which is not true of every handler `force` closes (see below).
    `tests/conftest.py`'s `_restore_root_logging` fixture keeps this from
    leaking between tests (review pass, 2026-08-10).

    `force` also `close()`s each handler it removes, not merely detaches it,
    and that is not undoable (review pass, 2026-08-10, second). Two
    consequences worth knowing before relying on this function: a
    write-mode `FileHandler` -- what `pytest --log-file` installs -- stays
    dead for the rest of the process and silently drops every later record;
    and `main()`, though importable, is therefore not safe to call
    in-process from a host that owns the root logger, since it destroys that
    host's logging rather than borrowing it. Mason is a CLI whose real
    consumer gets a fresh process per invocation, so `force=True` remains
    the right call here (spec Design Notes); a future in-process embedding
    story should configure a `pyforge.mason` logger instead of the root.
    """
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(
        stream=sys.stderr,
        level=level,
        format="%(levelname)s: %(message)s",
        force=True,
    )


def _build_global_flags_parser() -> argparse.ArgumentParser:
    """The six global flags (AD-13's closed v1 knob set), shared by the
    top-level parser and every noun.

    `add_help=False` is mandatory: a parent parser with its own `-h/--help`
    would collide with the child parser's when used via `parents=[...]`.

    Every flag defaults to `argparse.SUPPRESS`, not `None`. This is load-
    bearing, not cosmetic: `_SubParsersAction.__call__` parses a noun's
    remaining tokens into a *fresh* namespace and then copies every one of
    that namespace's attributes onto the parent — so if the noun subparser's
    copy of `--format` fell back to a plain `None` default, that `None`
    would silently clobber a value already set by a flag given *before* the
    noun (e.g. `mason --format json recipe`). `SUPPRESS` means the
    attribute is only set on the sub-namespace when the flag actually
    appears among that noun's own tokens, so a value set earlier survives.
    Callers must therefore read a resolved flag via
    `getattr(ns, "format", None)`, never `ns.format` directly — the
    attribute may not exist at all when the flag was never given anywhere.
    """
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--cfe-root", default=argparse.SUPPRESS, metavar="PATH",
        help=f"conda-forge-expert skill root (flag -> {_ENV_CFE_ROOT} -> auto-discovery)",
    )
    parent.add_argument(
        "--cfe-python", default=argparse.SUPPRESS, metavar="PATH",
        help=f"interpreter used to run CFE scripts (flag -> {_ENV_CFE_PYTHON} -> running interpreter)",
    )
    parent.add_argument(
        "--cfe-timeout", type=_parse_finite_float, default=argparse.SUPPRESS, metavar="SECONDS",
        help=f"per-operation CFE subprocess timeout in seconds (flag -> {_ENV_CFE_TIMEOUT} -> none)",
    )
    parent.add_argument(
        "--format", choices=("text", "json"), default=argparse.SUPPRESS,
        help=f'output format (flag -> {_ENV_FORMAT} -> "text")',
    )
    parent.add_argument(
        "--verbose", action="store_true", default=argparse.SUPPRESS,
        help=f"increase log verbosity (flag -> {_ENV_VERBOSE} -> off)",
    )
    parent.add_argument(
        "--quiet", action="store_true", default=argparse.SUPPRESS,
        help=f"decrease log verbosity (flag -> {_ENV_QUIET} -> off)",
    )
    return parent


def build_parser() -> argparse.ArgumentParser:
    # One shared parent, reused across the top-level parser and every noun
    # subparser, so a global flag parses whether it appears before or after
    # the noun (`mason --format json recipe` and `mason recipe --format
    # json` both work) — plain argparse `parents=` behaviour, nothing bespoke.
    global_flags = _build_global_flags_parser()

    parser = argparse.ArgumentParser(
        prog="mason",
        description="Mason — forge the blocks, bind the environment, ship the structure.",
        parents=[global_flags],
    )
    parser.add_argument("--version", action="version", version=f"mason {__version__}")

    noun_names = (*_NOUNS, "doctor")
    nouns = parser.add_subparsers(dest="noun", metavar="{" + ",".join(noun_names) + "}")

    # Captured per noun (Story 2.7) so a verb can be registered on it below,
    # in this same function — argparse forbids calling add_subparsers() a
    # second time on one parser, so this cannot be done from outside
    # build_parser() after the fact (module docstring's documented seam).
    _noun_verbs: dict[str, argparse._SubParsersAction] = {}

    for name, help_text in _NOUNS.items():
        noun_parser = nouns.add_parser(
            name, help=help_text, description=help_text, parents=[global_flags],
        )
        _noun_verbs[name] = noun_parser.add_subparsers(dest="verb", metavar="{}")
        # Remembered so main() can print this noun's own help on the
        # bare-noun usage error without re-parsing or rebuilding a parser.
        noun_parser.set_defaults(_noun_parser=noun_parser)

    doctor_parser = nouns.add_parser(
        "doctor", help=_DOCTOR_HELP, description=_DOCTOR_HELP, parents=[global_flags],
    )
    doctor_parser.set_defaults(_noun_parser=doctor_parser)

    # Story 2.7: mason recipe diagnose <log_path> — the first verb
    # registered under any noun (FR-10). package/environment stay
    # behavior-identical to Story 1.2: their verb-subparsers actions above
    # are captured but never given a verb, so they remain usage errors.
    diagnose_parser = _noun_verbs["recipe"].add_parser(
        "diagnose",
        help=_RECIPE_DIAGNOSE_HELP,
        description=_RECIPE_DIAGNOSE_HELP,
        parents=[global_flags],
    )
    diagnose_parser.add_argument("log_path", help="path to the build-failure log file")

    # Story 2.8: mason recipe optimize/scan <recipe_path> -- both take a
    # single required recipe_path positional, mirroring diagnose's own
    # log_path shape (spec Code Map). `recipe_path` is passed straight
    # through to CFE with no Mason-side existence check or interpretation
    # (spec Always boundary), same as `log_path` above.
    optimize_parser = _noun_verbs["recipe"].add_parser(
        "optimize",
        help=_RECIPE_OPTIMIZE_HELP,
        description=_RECIPE_OPTIMIZE_HELP,
        parents=[global_flags],
    )
    optimize_parser.add_argument(
        "recipe_path", help="path to a recipe file (recipe.yaml/meta.yaml) or its directory",
    )

    scan_parser = _noun_verbs["recipe"].add_parser(
        "scan",
        help=_RECIPE_SCAN_HELP,
        description=_RECIPE_SCAN_HELP,
        parents=[global_flags],
    )
    scan_parser.add_argument(
        "recipe_path", help="path to a recipe file (recipe.yaml/meta.yaml) or its directory",
    )

    # Review pass (2026-08-12): `metavar="{}"` was never updated once a verb
    # was actually registered, so `mason recipe <bad-verb>` printed the
    # literal token `{}` in its usage/error text instead of `{diagnose}`.
    # Derived from `.choices` (populated in registration order by the
    # `add_parser()` calls above), not hardcoded, so a future story adding
    # another `recipe` verb updates this automatically. Run once here, after
    # every `recipe` verb above is registered, rather than after each one.
    _noun_verbs["recipe"].metavar = "{" + ",".join(_noun_verbs["recipe"].choices) + "}"

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        # build_parser() is INSIDE the try deliberately: a KeyboardInterrupt (or
        # any failure) during parser construction must project like every other
        # exit, not escape as a traceback. Caught by tests/unit/test_cli.py.
        parser = build_parser()
        ns = parser.parse_args(argv)

        # FR-49/AD-25: configure logging immediately, before any noun
        # dispatch, so every command path that reaches this point (bare
        # invocation, doctor, the custom bare-noun usage error) is covered --
        # not just the ones that reach a use-case. (A usage error argparse
        # itself raises during parse_args, above, never reaches this line --
        # see _configure_logging's docstring.)
        _configure_logging(
            _resolve_bool(getattr(ns, "verbose", None), _ENV_VERBOSE, False),
            _resolve_bool(getattr(ns, "quiet", None), _ENV_QUIET, False),
        )

        if not ns.noun:
            # A true bare top-level invocation is help output, not a
            # diagnostic — stdout, EXIT_OK. Unchanged from Story 1.1.
            parser.print_help()
            return EXIT_OK

        if ns.noun == "doctor":
            # This branch must stay ahead of the verb check: `doctor` has no
            # verb level, so its namespace carries no `verb` attribute at
            # all, and a verb-less `doctor` is a complete command (EXIT_OK),
            # not a usage error.
            #
            # FR-34 frames `doctor` as a reporting command, so its result
            # goes through the one formatter (AD-8) to stdout, not a raw
            # stderr print(). `doctor.build_report` never raises (Story
            # 1.8), so this branch always reports EXIT_OK, even with CFE or
            # an engine absent -- the gap is data in the report, not a
            # failure of the `doctor` command itself.
            fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
            report = doctor.build_report(
                getattr(ns, "cfe_root", None),
                getattr(ns, "cfe_python", None),
                os.environ,
                Path.cwd(),
            )
            render.write(fmt, sys.stdout, "doctor", "ok", dataclasses.asdict(report), [])
            return EXIT_OK

        if not getattr(ns, "verb", None):
            # A noun invoked with no verb is a usage error: stderr, EXIT_USAGE —
            # matching argparse's own native stream/exit-code convention for an
            # unrecognized verb (e.g. `mason recipe sometypo`). See the spec's
            # 2026-07-30 contract amendment: this row was stdout, corrected to
            # stderr so both exit-2 paths agree on stream.
            ns._noun_parser.print_help(file=sys.stderr)
            return EXIT_USAGE

        if ns.noun == "recipe" and ns.verb == "diagnose":
            # FR-10: delegates to CFE's failure analyzer via recipe.py.
            # `recipe.diagnose` raises CfeUnresolvedError before any
            # subprocess spawns if the CFE root is unresolved (spec Always
            # boundary) -- caught by the dedicated branch below, same as
            # every other CFE-dependent path. `--cfe-timeout` is resolved
            # here (the first real caller of `_resolve_optional_float`) and
            # passed through; `cfe.diagnose_failure`'s own per-operation
            # default applies only when that resolves to `None`.
            #
            # Review pass (2026-08-12): `_invoke_captured` fixes the child's
            # stdin to DEVNULL (existing, unchanged), so `-` -- which CFE's
            # own failure_analyzer.py documents as its stdin sentinel --
            # would silently read an empty log and report a confident-looking
            # "no known error pattern matched" rather than the piped content.
            # Rejected as a usage error before any subprocess spawns, mirror-
            # ing `recipe build`'s own pre-resolution --docker/--config
            # pairing check, rather than let it silently produce a wrong
            # answer (spec Never boundary already scopes stdin out; this only
            # makes that boundary loud instead of silent).
            if ns.log_path.strip() == "-":
                print(
                    "mason recipe diagnose: '-' (stdin) is not supported -- pass a real "
                    "log file path",
                    file=sys.stderr,
                )
                return EXIT_USAGE
            fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
            result = recipe.diagnose(
                ns.log_path,
                cfe_root_arg=getattr(ns, "cfe_root", None),
                cfe_python_arg=getattr(ns, "cfe_python", None),
                cfe_timeout_arg=_resolve_optional_float(
                    getattr(ns, "cfe_timeout", None), _ENV_CFE_TIMEOUT
                ),
                environ=os.environ,
                start_directory=Path.cwd(),
            )
            render.write(
                fmt, sys.stdout, "recipe diagnose", "ok", dataclasses.asdict(result), [],
            )
            return EXIT_OK

        if ns.noun == "recipe" and ns.verb == "optimize":
            # FR-11: delegates to CFE's recipe optimizer via recipe.py.
            # `recipe.optimize` raises `CfeUnresolvedError` (unresolved CFE
            # root) or `CfeImportFloorError` (interpreter missing
            # `ruamel.yaml`) before any subprocess spawns (spec Always
            # boundary) -- both are `MasonError` subclasses, caught by the
            # dedicated/generic branches below respectively.
            fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
            result = recipe.optimize(
                ns.recipe_path,
                cfe_root_arg=getattr(ns, "cfe_root", None),
                cfe_python_arg=getattr(ns, "cfe_python", None),
                cfe_timeout_arg=_resolve_optional_float(
                    getattr(ns, "cfe_timeout", None), _ENV_CFE_TIMEOUT
                ),
                environ=os.environ,
                start_directory=Path.cwd(),
            )
            render.write(
                fmt, sys.stdout, "recipe optimize", "ok", dataclasses.asdict(result), [],
            )
            return EXIT_OK

        if ns.noun == "recipe" and ns.verb == "scan":
            # FR-12: delegates to CFE's vulnerability scanner via recipe.py.
            # Same CfeUnresolvedError/CfeImportFloorError gating as
            # `optimize` above (interpreter missing `requests`/`pyyaml`).
            fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
            result = recipe.scan(
                ns.recipe_path,
                cfe_root_arg=getattr(ns, "cfe_root", None),
                cfe_python_arg=getattr(ns, "cfe_python", None),
                cfe_timeout_arg=_resolve_optional_float(
                    getattr(ns, "cfe_timeout", None), _ENV_CFE_TIMEOUT
                ),
                environ=os.environ,
                start_directory=Path.cwd(),
            )
            render.write(
                fmt, sys.stdout, "recipe scan", "ok", dataclasses.asdict(result), [],
            )
            return EXIT_OK

        # Unreachable now for every verb-noun pair except `recipe
        # diagnose`/`recipe optimize`/`recipe scan` above, each handled by
        # its own branch: `package`/`environment` still register no verbs at
        # all, and `recipe` registers no verb beyond those three, so
        # argparse itself rejects any other token here as an invalid choice
        # before `ns.verb` could ever hold it. Kept only so a later story
        # that populates another verb has somewhere to land its dispatch.
        return EXIT_OK  # pragma: no cover
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    except SystemExit as exc:
        # argparse raises SystemExit for --help/--version/usage errors. Those are
        # legitimate; anything else is projected rather than trusted verbatim.
        code = exc.code
        if code is None:
            return EXIT_OK
        return code if isinstance(code, int) else EXIT_USAGE
    except CfeUnresolvedError as exc:
        # A CfeUnresolvedError is a MasonError subclass (AD-7): this branch
        # must precede `except MasonError` below, since Python matches the
        # first except clause the raised exception is an instance of, and
        # this one maps to the distinct EXIT_CFE_UNAVAILABLE (3), not the
        # generic EXIT_FAILED the MasonError branch produces (Story 1.7,
        # FR-5). Same print-to-stderr/no-traceback pattern as MasonError.
        print(str(exc), file=sys.stderr)
        return EXIT_CFE_UNAVAILABLE
    except MasonError as exc:
        # Anticipated failure (AD-7): the identifier + message is the whole
        # diagnostic, no traceback. Must precede the bare `Exception` catch
        # below, since MasonError is a subclass of it.
        print(str(exc), file=sys.stderr)
        return EXIT_FAILED
    except Exception:                              # noqa: BLE001 — deliberate boundary
        import traceback
        traceback.print_exc()
        return EXIT_FAILED


if __name__ == "__main__":                          # pragma: no cover
    raise SystemExit(main())
