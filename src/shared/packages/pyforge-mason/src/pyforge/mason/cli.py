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
design (OQ-A4) and is built separately, immediately after that loop.

Story 2.4 registers the first real verb, ``recipe new`` (FR-7), on
``_noun_verbs["recipe"]`` right after the loop -- the pattern the paragraph
above describes, now exercised for real. Its own required, mutually
exclusive ``--from-pypi``/``--from-github``/``--from-cran``/``--from-npm``
group plus required ``--output``/``-o`` land there too. ``main()``'s
dispatch replaces the ``# Unreachable in Story 1.2`` block below with the
first real branch, guarded by both ``ns.noun == "recipe"`` and ``ns.verb ==
"new"`` so a future second recipe verb does not fall into it by noun alone.

Story 2.5 registers the second verb, ``recipe validate`` (FR-8), on the
same noun, right after ``new`` above (hand-landed 2026-08-13 after this
story's own dev pass deferred on a spec-surface gate, not a code defect --
see ``recipe.py``'s own module docstring and this Spec's memlog for the
same reconciliation applied there). ``main()``'s dispatch adds a second
guarded branch, ``ns.verb == "validate"`` -- the one verb whose own
pass/fail outcome also projects onto the process exit code (FR-8).

Story 2.6 is the next to use that seam, registering ``recipe build`` on
``_noun_verbs["recipe"]``. Story 2.7 registers ``recipe diagnose`` on the
same noun — ``package``/``environment`` stay behavior-identical (their own
captured actions are never given a verb). Story 2.8 registers two more
verbs on that same noun, ``recipe optimize`` and ``recipe scan``, each a
single required ``recipe_path`` positional mirroring ``diagnose``'s own
``log_path`` shape.

Story 2.9 registers a fifth verb, ``recipe submit``: the same
``recipe_path`` positional, plus two verb-own boolean flags, ``--yes`` and
``--prepare-only`` -- both live only on ``submit_parser`` itself, never on
the shared ``global_flags`` parent (that parent is AD-13's closed six-flag
set only), so they need none of ``_build_global_flags_parser``'s
``argparse.SUPPRESS``/``getattr`` dance and read back as plain ``bool``s
off the namespace.

Story 2.10 registers a sixth verb, ``recipe update``: the same
``recipe_path`` positional, plus three verb-own flags -- ``--dry-run``/
``--github`` (``action="store_true"``) and ``--repo`` (an optional string,
``metavar="OWNER/REPO"``) -- and a fourth, ``--pre`` (``action=
"store_true"``), none part of the shared ``global_flags`` parent, same
reasoning as ``submit``'s own two flags above.

Story 3.2 registers the first verb under a DIFFERENT noun, `package build`,
on `_noun_verbs["package"]` (previously captured but never given a verb) --
the same registration/dispatch shape as every `recipe` verb above, but
CFE-independent: `package.build()` never resolves a CFE root/interpreter,
so its dispatch branch reads no `--cfe-root`/`--cfe-python`/`--cfe-timeout`
flags at all.

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

from . import __version__, doctor, environment, package, recipe, render
from .errors import CfeUnresolvedError, MasonError
from .exit_codes import (
    EXIT_CFE_UNAVAILABLE,
    EXIT_FAILED,
    EXIT_INTERRUPTED,
    EXIT_OK,
    EXIT_USAGE,
)
from .models import ShipState

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
_RECIPE_NEW_HELP = "generate a recipe from PyPI/GitHub/CRAN/npm via conda-forge-expert"
_RECIPE_VALIDATE_HELP = (
    "validate a recipe against conda-forge policy via CFE's validator (process exit code "
    "reflects the pass/fail outcome)"
)
_RECIPE_BUILD_HELP = "build a recipe (native by default; --docker + --config for CI-parity)"
_RECIPE_DIAGNOSE_HELP = "diagnose a build-failure log via CFE's failure analyzer"
_RECIPE_OPTIMIZE_HELP = "lint a recipe for quality findings via CFE's recipe optimizer"
_RECIPE_SCAN_HELP = (
    "scan a recipe's exactly-pinned dependencies for known vulnerabilities via CFE's scanner "
    "(range-pinned/unpinned deps are not scanned; makes an outbound network call to "
    "api.osv.dev by default)"
)
_RECIPE_SUBMIT_HELP = (
    "submit a recipe to conda-forge/staged-recipes via CFE's two-phase flow (dry run by "
    "default; --yes to confirm a real push/PR, --prepare-only to stop after pushing the branch)"
)
_RECIPE_UPDATE_HELP = (
    "bump a recipe to its latest upstream version via CFE's autotick scripts (PyPI by "
    "default; --github for GitHub Releases; shows the plan before writing, in both the "
    "default and --dry-run paths)"
)
_PACKAGE_BUILD_HELP = (
    "build a project's distributable artifacts: wheel+sdist via PEP 517, and a .conda "
    "package via pixi build (--target library only in v1; CFE-independent)"
)
_PACKAGE_SHIP_HELP = (
    "ship a project's built artifacts to pypi, pypi-test (TestPyPI rehearsal), conda-forge, "
    "and/or a named channel (comma-separated; dry run by default, --yes to confirm; a "
    "pypi-test target requested alongside pypi always runs first and gates it)"
)
_ENVIRONMENT_LOCK_HELP = (
    "resolve one or more dependency manifests into a single lockfile via conda-lock "
    "(--platform comma-separated; omit for conda-lock's own default; CFE-independent)"
)
_ENVIRONMENT_CHECK_HELP = (
    "check whether an existing lockfile is stale relative to one or more manifests via "
    "conda-lock (--platform comma-separated; pass the same platforms the lockfile was "
    "locked with; exit code is non-zero when the lockfile is stale OR the check itself "
    "failed; CFE-independent)"
)

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
        raise argparse.ArgumentTypeError(f"invalid --cfe-timeout value: {raw!r} (must be a finite, positive number)")
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
        "--cfe-root",
        default=argparse.SUPPRESS,
        metavar="PATH",
        help=f"conda-forge-expert skill root (flag -> {_ENV_CFE_ROOT} -> auto-discovery)",
    )
    parent.add_argument(
        "--cfe-python",
        default=argparse.SUPPRESS,
        metavar="PATH",
        help=f"interpreter used to run CFE scripts (flag -> {_ENV_CFE_PYTHON} -> running interpreter)",
    )
    parent.add_argument(
        "--cfe-timeout",
        type=_parse_finite_float,
        default=argparse.SUPPRESS,
        metavar="SECONDS",
        help=f"per-operation CFE subprocess timeout in seconds (flag -> {_ENV_CFE_TIMEOUT} -> none)",
    )
    parent.add_argument(
        "--format",
        choices=("text", "json"),
        default=argparse.SUPPRESS,
        help=f'output format (flag -> {_ENV_FORMAT} -> "text")',
    )
    parent.add_argument(
        "--verbose",
        action="store_true",
        default=argparse.SUPPRESS,
        help=f"increase log verbosity (flag -> {_ENV_VERBOSE} -> off)",
    )
    parent.add_argument(
        "--quiet",
        action="store_true",
        default=argparse.SUPPRESS,
        help=f"decrease log verbosity (flag -> {_ENV_QUIET} -> off)",
    )
    return parent


def _add_ship_flags(parser: argparse.ArgumentParser, *, targets_flag: str) -> None:
    """Register `ship`'s four flags onto `parser` (Story 3.9, FR-16, FR-24,
    FR-50, D-12): `--target`, `--yes`, `--recipe-path`, and one flag named
    by `targets_flag`.

    Called TWICE, on two DIFFERENT parser objects (`build_parser`'s own
    registration comment explains why both are needed): once on `ship`'s
    own verb subparser, with `targets_flag="--to"` (the canonical form),
    and once directly on the `package` NOUN parser itself, with
    `targets_flag="--ship"` (the one documented bare-noun exception, D-12
    -- `mason package --target library --ship pypi,conda-forge`). argparse
    scoping requires two separate registrations: a noun-level flag cannot
    be read after a verb token has already consumed the remaining argv, and
    a verb-level flag cannot be read when no verb token was ever given --
    this helper exists so the shared `add_argument` bodies are written
    once, not duplicated at both call sites.

    `--target`/`--yes`/`--recipe-path` all default to `argparse.SUPPRESS`,
    NOT a plain `"library"`/implicit-`False`/`None` (**corrected, review
    pass 1** -- this docstring previously claimed these three "need no
    `argparse.SUPPRESS`/`getattr` dance" because they are "per-verb-shaped
    flags, not part of that closed six-knob AD-13 set." That was wrong: the
    hazard `_build_global_flags_parser`'s own docstring documents above has
    nothing to do with AD-13's six-knob set -- it applies to ANY flag
    registered on both an ancestor and a descendant parser in this
    codebase's noun/verb subparser tree, and these three flags are
    registered on exactly that shape (once on the `package` NOUN parser
    here, once on `ship`'s own verb subparser, both reachable in the SAME
    invocation via `mason package --yes ship --to pypi`). Exactly as that
    docstring explains: `_SubParsersAction.__call__` parses the verb
    subparser's remaining tokens into a *fresh* namespace and copies every
    one of that namespace's attributes onto the parent -- so if
    `ship_parser`'s own copy of `--yes` fell back to a plain `False`
    default, that `False` would silently clobber a `True` already set by
    the noun parser's own `--yes`, given *before* the verb token (the
    natural place to put a confirming flag when composing a command
    left-to-right). `SUPPRESS` means the attribute is only set on the
    sub-namespace when the flag actually appears among that parser's own
    tokens, so a value set by the OTHER registration survives untouched.
    Callers must therefore read a resolved value via `getattr(ns, "yes",
    False)` / `getattr(ns, "target", "library")` / `getattr(ns,
    "recipe_path", None)`, never `ns.yes`/`ns.target`/`ns.recipe_path`
    directly -- `_dispatch_package_ship` (below) is the ONE place this
    resolution happens now, not `main()`'s two call sites. `--to`/`--ship`
    need no such change and stay as before: `--to` is `required=True` (the
    canonical verb form has no other way to name a target, so there is
    nothing for a missing value to clobber), and `--ship` is registered
    exactly ONCE, only on the noun parser, so there is no second
    registration for its `default=None` to ever disagree with.
    """
    parser.add_argument(
        "--target",
        choices=("library",),
        default=argparse.SUPPRESS,
        help="what to build (v1 scope: library only)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        default=argparse.SUPPRESS,
        help="confirm a real ship (default: dry run -- prints the plan, ships nothing)",
    )
    parser.add_argument(
        "--recipe-path",
        default=argparse.SUPPRESS,
        metavar="RECIPE_PATH",
        help="recipe directory for the conda-forge target (inert for every other target; "
        "omitting it while targeting conda-forge is not a usage error -- ship_conda_forge's "
        "own precondition error reports it per-target instead)",
    )
    if targets_flag == "--to":
        parser.add_argument(
            "--to",
            required=True,
            metavar="TARGETS",
            help="comma-separated ship targets: pypi, pypi-test, conda-forge, channel:<name>",
        )
    else:
        parser.add_argument(
            targets_flag,
            default=None,
            metavar="TARGETS",
            help="comma-separated ship targets -- same vocabulary as `package ship --to` (D-12 bare-noun alias)",
        )


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

    # Each noun's own verb-subparsers object, keyed by noun name — captured
    # so a verb can be registered on it right after this loop, in this same
    # function (argparse forbids calling add_subparsers() a second time on
    # one parser, so this cannot be done from outside build_parser() after
    # the fact — see module docstring's documented seam).
    _noun_verbs: dict[str, argparse._SubParsersAction] = {}
    # Story 3.9: each noun's own ArgumentParser object, keyed by noun name
    # — mirrors `_noun_verbs` above, captured for the same reason: so a
    # FLAG (not a verb) can be registered directly on a noun parser after
    # this loop, addressed by name rather than re-parsed or rebuilt. Only
    # `package` uses this today (`--ship`'s bare-noun alias, D-12), but
    # every noun is captured, mirroring `_noun_verbs`'s own
    # capture-everything precedent for future stories.
    _noun_parsers: dict[str, argparse.ArgumentParser] = {}

    for name, help_text in _NOUNS.items():
        noun_parser = nouns.add_parser(
            name,
            help=help_text,
            description=help_text,
            parents=[global_flags],
        )
        _noun_verbs[name] = noun_parser.add_subparsers(dest="verb", metavar="{}")
        _noun_parsers[name] = noun_parser
        # Remembered so main() can print this noun's own help on the
        # bare-noun usage error without re-parsing or rebuilding a parser.
        noun_parser.set_defaults(_noun_parser=noun_parser)

    doctor_parser = nouns.add_parser(
        "doctor",
        help=_DOCTOR_HELP,
        description=_DOCTOR_HELP,
        parents=[global_flags],
    )
    doctor_parser.set_defaults(_noun_parser=doctor_parser)

    # Story 2.4: mason recipe new --from-{pypi,github,cran,npm} <pkg> --output
    # <path> — the first verb registered under any noun in epic order (FR-7).
    # Required, mutually exclusive `--from-*` group (spec Always boundary):
    # exactly one source must be named, so `recipe.py::new` never has to
    # guess which the caller meant. A plain string per flag — no secondary
    # per-source flags (GitHub's --version, npm's various modes, ...) are in
    # this story's AC scope (spec Never boundary).
    new_parser = _noun_verbs["recipe"].add_parser(
        "new",
        help=_RECIPE_NEW_HELP,
        description=_RECIPE_NEW_HELP,
        parents=[global_flags],
    )
    source_group = new_parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--from-pypi",
        metavar="PACKAGE",
        help="generate from a PyPI package, optionally with an embedded version spec",
    )
    source_group.add_argument(
        "--from-github",
        metavar="OWNER/REPO",
        help="generate from a GitHub repository",
    )
    source_group.add_argument(
        "--from-cran",
        metavar="PACKAGE",
        help="generate from a CRAN package",
    )
    source_group.add_argument(
        "--from-npm",
        metavar="PACKAGE",
        help="generate from an npm package",
    )
    # Required, not defaulted to CFE's own omitted-`--output` behavior (spec
    # Design Notes): FR-7 frames this feature as output "at a user-specified
    # path", and letting it fall through to a CFE-side naming convention
    # would make Mason's CLI contract depend on a policy that could change
    # independently.
    new_parser.add_argument(
        "--output",
        "-o",
        required=True,
        metavar="PATH",
        help="path to write the generated recipe to (required)",
    )

    # Story 2.5: mason recipe validate <recipe_path> — the first verb
    # registered under any noun (FR-8), numerically: Story 2.5 precedes
    # every other `recipe` verb below, even though `build`/`diagnose`/
    # `optimize`/`scan`/`submit`/`update` (Stories 2.6-2.10) landed first in
    # this worktree (spec Design Notes — this repository's `main` branch
    # already reconciled Story 2.4's `new()` into this same first position
    # after an analogous out-of-order landing; `new()` itself is not present
    # in this file, since this worktree's baseline predates that merge).
    # `parents=[global_flags]` mirrors every other verb parser below —
    # without it, a global flag given AFTER `validate` would be rejected as
    # unrecognized, for the same reason `build`'s own comment (next) spells
    # out.
    validate_parser = _noun_verbs["recipe"].add_parser(
        "validate",
        help=_RECIPE_VALIDATE_HELP,
        description=_RECIPE_VALIDATE_HELP,
        parents=[global_flags],
    )
    validate_parser.add_argument(
        "recipe_path",
        help="path to a recipe file (recipe.yaml/meta.yaml) or its directory",
    )

    # Story 2.6: mason recipe build <recipe_path> [--docker --config] — the
    # next verb registered under any noun (FR-9), right after `validate`
    # above. package/environment stay behavior-identical to Story 1.2: their
    # verb-subparsers actions above are captured but never given a verb, so
    # they remain usage errors. `parents=[global_flags]` here too, mirroring
    # every other parser level — without it, a global flag given AFTER
    # `build` (`mason recipe build <path> --format json`) would be rejected
    # as unrecognized, since argparse hands the tokens following `build` to
    # THIS parser, not an ancestor one.
    recipe_build_parser = _noun_verbs["recipe"].add_parser(
        "build",
        help=_RECIPE_BUILD_HELP,
        description=_RECIPE_BUILD_HELP,
        parents=[global_flags],
    )
    recipe_build_parser.add_argument(
        "recipe_path",
        metavar="RECIPE_PATH",
        help="path to the recipe (file or directory)",
    )
    recipe_build_parser.add_argument(
        "--docker",
        action="store_true",
        help="run the Docker/CI-parity build instead of the native default (requires --config)",
    )
    recipe_build_parser.add_argument(
        "--config",
        metavar="CONFIG",
        help="platform-variant config name for --docker (e.g. linux64)",
    )

    # Story 2.7: mason recipe diagnose <log_path>.
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
        "recipe_path",
        help="path to a recipe file (recipe.yaml/meta.yaml) or its directory",
    )

    scan_parser = _noun_verbs["recipe"].add_parser(
        "scan",
        help=_RECIPE_SCAN_HELP,
        description=_RECIPE_SCAN_HELP,
        parents=[global_flags],
    )
    scan_parser.add_argument(
        "recipe_path",
        help="path to a recipe file (recipe.yaml/meta.yaml) or its directory",
    )

    # Story 2.9: mason recipe submit <recipe_path> [--yes] [--prepare-only]
    # -- `recipe_path` is the recipe's OWN directory (unlike diagnose/
    # optimize/scan's `recipe_path`, this one IS interpreted, by recipe.py,
    # not here -- spec Always boundary). `--yes`/`--prepare-only` are
    # per-verb flags, not part of the shared `global_flags` parent (AD-13's
    # closed six-knob set), so they need no `argparse.SUPPRESS`/`getattr`
    # dance -- `ns.yes`/`ns.prepare_only` default to plain `False`.
    submit_parser = _noun_verbs["recipe"].add_parser(
        "submit",
        help=_RECIPE_SUBMIT_HELP,
        description=_RECIPE_SUBMIT_HELP,
        parents=[global_flags],
    )
    submit_parser.add_argument(
        "recipe_path",
        help="path to the recipe's own directory (its basename becomes the CFE slug -- "
        "unlike diagnose/optimize/scan's recipe_path, this must be the directory itself, "
        "not a recipe.yaml/meta.yaml file)",
    )
    submit_parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm a real submission (default: dry run -- --dry-run forwarded to CFE)",
    )
    submit_parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="stop after pushing the branch to the fork; do not open a PR (still a no-op "
        "dry run unless --yes is also given)",
    )

    # Story 2.10: mason recipe update <recipe_path> [--dry-run] [--github]
    # [--repo OWNER/REPO] [--pre] -- `recipe_path` is passed straight through
    # with no Mason-side existence check or interpretation (spec Always
    # boundary), mirroring diagnose/optimize/scan's own recipe_path, not
    # submit's one disclosed exception. `--dry-run`/`--github`/`--repo`/
    # `--pre` are per-verb flags, not part of the shared `global_flags`
    # parent (AD-13's closed six-knob set), so they need no
    # `argparse.SUPPRESS`/`getattr` dance -- `ns.dry_run`/`ns.github`/
    # `ns.pre` default to plain `False`, `ns.repo` to `None`.
    update_parser = _noun_verbs["recipe"].add_parser(
        "update",
        help=_RECIPE_UPDATE_HELP,
        description=_RECIPE_UPDATE_HELP,
        parents=[global_flags],
    )
    update_parser.add_argument(
        "recipe_path",
        help="path to a v1 recipe.yaml file (CFE's autotick scripts parse its context "
        "block -- a Jinja-templated v0 meta.yaml is not valid YAML on its own and will "
        "not parse); with --github, a directory is also accepted",
    )
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="compute and show the plan without writing (default: writes the field-scoped update for real)",
    )
    update_parser.add_argument(
        "--github",
        action="store_true",
        help="use CFE's GitHub Releases autotick bot instead of the default PyPI one",
    )
    update_parser.add_argument(
        "--repo",
        default=None,
        metavar="OWNER/REPO",
        help="GitHub repo override (only forwarded to CFE with --github; inert otherwise)",
    )
    update_parser.add_argument(
        "--pre",
        action="store_true",
        help="include pre-release versions (only forwarded to CFE with --github; inert otherwise)",
    )

    # Review pass (2026-08-12): `metavar="{}"` was never updated once a verb
    # was actually registered, so `mason recipe <bad-verb>` printed the
    # literal token `{}` in its usage/error text instead of `{diagnose}`.
    # Derived from `.choices` (populated in registration order by the
    # `add_parser()` calls above), not hardcoded, so a future story adding
    # another `recipe` verb updates this automatically. Run once here, after
    # every `recipe` verb above is registered, rather than after each one.
    _noun_verbs["recipe"].metavar = "{" + ",".join(_noun_verbs["recipe"].choices) + "}"

    # Story 3.2: mason package build PROJECT_PATH [--target {library}] --
    # the `package` noun's first verb (FR-15, FR-21). Mirrors `recipe
    # build`'s own registration shape (parents=[global_flags], for the same
    # "a global flag given after the verb and its positional" reason
    # documented on that registration above). `--target` mirrors the shared
    # `--format` flag's `choices=` pattern -- no new error class needed
    # (spec Always boundary) -- and is a plain per-verb default (`"library"`),
    # not `argparse.SUPPRESS`: that dance is reserved for the shared
    # `global_flags` parent (see `_build_global_flags_parser`'s own
    # docstring), never a verb-own flag like `--docker`/`--yes`/`--dry-run`
    # above.
    package_build_parser = _noun_verbs["package"].add_parser(
        "build",
        help=_PACKAGE_BUILD_HELP,
        description=_PACKAGE_BUILD_HELP,
        parents=[global_flags],
    )
    package_build_parser.add_argument(
        "project_path",
        metavar="PROJECT_PATH",
        help="path to the project to build (its own pyproject.toml/pixi.toml)",
    )
    package_build_parser.add_argument(
        "--target",
        choices=("library",),
        default="library",
        help="what to build (v1 scope: library only)",
    )

    # Story 3.9: mason package ship --to <targets> [--yes] [--target
    # library] [--recipe-path PATH] -- the canonical shipping verb (FR-16,
    # FR-24, FR-50, D-12), dispatching to package.ship()'s own multi-target
    # orchestrator. `_add_ship_flags` (above) factors the four-flag
    # registration this verb shares with the bare-noun `--ship` alias
    # immediately below, so the `add_argument` bodies are not duplicated.
    ship_parser = _noun_verbs["package"].add_parser(
        "ship",
        help=_PACKAGE_SHIP_HELP,
        description=_PACKAGE_SHIP_HELP,
        parents=[global_flags],
    )
    _add_ship_flags(ship_parser, targets_flag="--to")

    # D-12/FR-30: `mason package --target library --ship pypi,conda-forge`
    # is the ONE documented bare-noun exception to "a noun with no verb is
    # a usage error" (main()'s own dispatch check, below) -- registered
    # directly on the `package` NOUN parser itself (`_noun_parsers
    # ["package"]`, captured in the loop above), since a noun-level flag
    # cannot be read after a verb token has already consumed the remaining
    # argv, and vice versa (argparse scoping; `_add_ship_flags`'s own
    # docstring). Both registrations share the SAME `_add_ship_flags` body
    # — only the targets flag's own name/required-ness differs.
    _add_ship_flags(_noun_parsers["package"], targets_flag="--ship")

    # Same `.choices`-derived metavar fixup as `recipe` above, now that
    # `package` has two real verbs registered (`build`, `ship`).
    _noun_verbs["package"].metavar = "{" + ",".join(_noun_verbs["package"].choices) + "}"

    # Story 4.3: mason environment lock <manifest_path>... --output/-o PATH
    # [--platform PLATFORMS] -- the `environment` noun's first verb (FR-25,
    # FR-27, FR-29). Mirrors `package build`'s own registration shape
    # (parents=[global_flags], for the same "a global flag given after the
    # verb and its positionals" reason documented on that registration
    # above). `--output`/`-o` mirrors `recipe new --output`'s exact
    # required-flag shape (Story 2.4). `--platform` is optional and takes a
    # single comma-separated string, mirroring `--to`'s established
    # "repeatable via comma-separation" idiom -- no `action="append"`
    # precedent exists anywhere in this file (spec Always boundary);
    # `environment.lock()` does the splitting, not this registration.
    #
    # Story 4.2: `manifest_path` is `nargs="*"` -- when the caller gives
    # none, `main()`'s own dispatch branch below calls `environment.
    # discover_manifests(Path.cwd())` and uses the result, so omitting
    # `manifest_path` is no longer a usage error.
    environment_lock_parser = _noun_verbs["environment"].add_parser(
        "lock",
        help=_ENVIRONMENT_LOCK_HELP,
        description=_ENVIRONMENT_LOCK_HELP,
        parents=[global_flags],
    )
    environment_lock_parser.add_argument(
        "manifest_path",
        metavar="MANIFEST_PATH",
        nargs="*",
        help="dependency manifest paths (pyproject.toml, environment.yml, "
        "requirements*.txt, pixi.toml); omit to auto-discover them in the current directory",
    )
    environment_lock_parser.add_argument(
        "--output",
        "-o",
        required=True,
        metavar="PATH",
        help="path to write the lockfile to",
    )
    environment_lock_parser.add_argument(
        "--platform",
        metavar="PLATFORMS",
        default=None,
        help="comma-separated platforms to lock for (e.g. linux-64,osx-arm64); omit to let "
        "conda-lock apply its own default",
    )

    # Story 4.4: mason environment check <manifest_path>... --lockfile/-l PATH
    # [--platform PLATFORMS] -- the `environment` noun's second verb (FR-25,
    # FR-27, FR-29), CI's own companion to `lock` above: reports whether an
    # EXISTING lockfile has gone stale relative to its manifests, rather than
    # producing one. Mirrors `lock`'s own registration shape
    # (parents=[global_flags], `manifest_path` positional -- identical
    # rationale, spec Always boundary) with one deliberate difference:
    # `--lockfile`/`-l` names the EXISTING lockfile to verify (required,
    # deliberately not `--output`/`-o` -- nothing is written to it, and that
    # name would misleadingly imply a write, spec Always boundary); there is
    # no `--output` flag on this verb at all. `--platform` mirrors `lock`'s
    # own identical single comma-separated-flag idiom exactly --
    # `environment.check()` does the splitting, not this registration, same
    # as `lock`'s own.
    #
    # Story 4.2: `manifest_path` is `nargs="*"`, same discovery fallback as
    # `lock` above -- see that registration's comment for the rationale.
    environment_check_parser = _noun_verbs["environment"].add_parser(
        "check",
        help=_ENVIRONMENT_CHECK_HELP,
        description=_ENVIRONMENT_CHECK_HELP,
        parents=[global_flags],
    )
    environment_check_parser.add_argument(
        "manifest_path",
        metavar="MANIFEST_PATH",
        nargs="*",
        help="dependency manifest paths (pyproject.toml, environment.yml, "
        "requirements*.txt, pixi.toml); omit to auto-discover them in the current directory",
    )
    environment_check_parser.add_argument(
        "--lockfile",
        "-l",
        required=True,
        metavar="PATH",
        help="path to the EXISTING lockfile to verify (not written to)",
    )
    environment_check_parser.add_argument(
        "--platform",
        metavar="PLATFORMS",
        default=None,
        help="comma-separated platforms to check (e.g. linux-64,osx-arm64); pass the same "
        "platforms the lockfile was locked with -- omitting this delegates to conda-lock's "
        "own default (linux-64,osx-arm64,osx-64,win-64 when the manifests name none), which "
        "reports a narrower lockfile as stale",
    )

    # Same `.choices`-derived metavar fixup as `recipe`/`package` above, now
    # that `environment` has two real verbs registered (`lock`, `check`).
    _noun_verbs["environment"].metavar = "{" + ",".join(_noun_verbs["environment"].choices) + "}"

    return parser


def _dispatch_package_ship(ns: argparse.Namespace, *, raw_targets: str) -> int:
    """Shared dispatch body for BOTH `mason package ship --to <targets>`
    (the canonical verb) and `mason package --ship <targets>` (the one
    documented bare-noun exception, D-12/FR-30) -- both call sites in
    `main()` below pass their own namespace's `--to`/`--ship` value through
    as `raw_targets`, and everything past that point is byte-identical
    (spec I/O matrix: "Alias happy path... identical dispatch/result to the
    canonical form above").

    **Corrected, review pass 1:** `confirm`/`target`/`recipe_path` are no
    longer parameters a caller resolves and passes in -- this function
    resolves all three itself, via `getattr(ns, "yes", False)`, `getattr(
    ns, "target", "library")`, `getattr(ns, "recipe_path", None)`, mirroring
    how `--cfe-root`/`--cfe-python`/`--cfe-timeout` are already read a few
    lines below and exactly how `_add_ship_flags`'s own docstring now
    documents these three flags must be read (`argparse.SUPPRESS`
    defaults on BOTH of their registration sites -- never `ns.yes`/
    `ns.target`/`ns.recipe_path` directly, which would raise
    `AttributeError` whenever the flag was never given anywhere in the
    parsed argv at all, and previously -- before this correction -- read a
    value that a sibling registration could silently overwrite back to its
    default). This is the ONE place that resolution happens now: both call
    sites in `main()` below pass only `ns` and `raw_targets`, nothing else.

    Resolves `--format` the same way every other dispatch branch does, then
    calls `package.ship(...)`, forwarding the real `os.environ` and
    `Path.cwd()` (mirrors every CFE-dependent verb's own established
    contract) plus the unresolved `--cfe-root`/`--cfe-python` flag values
    and `--cfe-timeout` resolved via the shared `_resolve_optional_float`
    helper. `package build`'s established "never reads CFE flags"
    precedent does NOT apply here: `ship`'s own `conda-forge` target needs
    them for its `resolve_cfe_root` call, unlike `package.build()`, which
    touches no CFE state at all.

    Renders `{"targets": [{**dataclasses.asdict(r), "state": r.state.value}
    for r in results]}` under the command name `"package ship"` -- a LIST,
    not a single result object, unlike every prior dispatch branch's `data`
    payload: `ship()` always returns a *tuple* of per-target results, since
    one invocation can name several targets at once. The `"state":
    r.state.value` override (**corrected, review pass 2** -- this was
    previously a bare `dataclasses.asdict(r)` per target) stringifies each
    result's `ShipState` member to its plain value BEFORE it reaches either
    renderer: `render_text`'s `f"{data[key]}"` line only strips
    `StrEnum`'s own `__str__` wrapper for a value sitting directly at
    `data`'s own top level -- `str()`/`format()` on the ENUM MEMBER itself
    prints its plain value, but formatting a `list` (or `dict`) containing
    one falls back to each element's `repr()`, not `str()`, which is
    exactly the Python-level mechanism that rendered the raw
    `<ShipState.TERMINAL: 'terminal'>` fragment for every `package ship`
    result before this fix -- no prior dispatch branch in this codebase
    ever rendered a list, so this gap in `render_text` was never exercised
    before this story. `render_json`'s `json.dumps` was never affected
    either way (it already serializes a bare `StrEnum` member as its plain
    string value regardless of nesting depth) -- this fix is purely for
    `render_text`'s benefit, and is harmless to leave in place for JSON
    mode too (`r.state.value` is already the exact string `json.dumps`
    would have produced from the bare member).

    The aggregate exit code is the ONE genuinely data-dependent exit code
    in this whole file (spec Design Notes, AD-9): `EXIT_FAILED` if ANY
    returned `ShipTargetResult.state == ShipState.FAILED`, else `EXIT_OK`
    -- unlike every other dispatch branch above, which always reports
    `EXIT_OK` for a Mason-successful invocation regardless of a delegated
    tool's own failure (AD-4), because a multi-target command has no
    single delegated-tool returncode to defer to. This also means
    `EXIT_CFE_UNAVAILABLE` never reaches this function's return value, even
    for a lone `--to conda-forge` with an unresolved CFE root:
    `package.ship()`'s own per-target `MasonError` catch (see that
    function's own docstring) already converted the exception into a
    `FAILED` result before it ever got here, so there is no
    `CfeUnresolvedError` left for this function -- or `main()`'s dedicated
    except-clause below -- to catch. The render's own `status` field stays
    the literal `"ok"` regardless (matches every existing dispatch
    branch's "Mason ran successfully" convention; AD-9 governs the exit
    code, not this field).
    """
    fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
    results = package.ship(
        raw_targets,
        confirm=getattr(ns, "yes", False),
        environ=os.environ,
        target=getattr(ns, "target", "library"),
        recipe_path=getattr(ns, "recipe_path", None),
        cfe_root_arg=getattr(ns, "cfe_root", None),
        cfe_python_arg=getattr(ns, "cfe_python", None),
        cfe_timeout_arg=_resolve_optional_float(
            getattr(ns, "cfe_timeout", None),
            _ENV_CFE_TIMEOUT,
        ),
        start_directory=Path.cwd(),
    )
    render.write(
        fmt,
        sys.stdout,
        "package ship",
        "ok",
        {"targets": [{**dataclasses.asdict(r), "state": r.state.value} for r in results]},
        [],
    )
    return EXIT_FAILED if any(r.state == ShipState.FAILED for r in results) else EXIT_OK


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

        if ns.noun == "package" and getattr(ns, "ship", None) is not None and getattr(ns, "verb", None):
            # Review pass 3: `--ship <targets>` is registered on the `package`
            # NOUN parser (needed for D-12's bare-noun alias below), so it
            # parses successfully even when an explicit verb is ALSO given --
            # `mason package --ship pypi build .` or `mason package --ship
            # pypi ship --to conda-forge` both used to parse with `ns.ship`
            # silently discarded (the `build`/`ship` branches below never
            # read it). Rejected here, before either branch, rather than
            # silently ignored: two independent review passes (3 total
            # reviewer instances) flagged this as a plausible real trigger
            # (editing a previous `--ship ...` invocation in shell history to
            # add an explicit verb, leaving the old `--ship` in place) whose
            # silent-drop outcome is indistinguishable from a typo the user
            # never notices.
            print(
                "package: --ship cannot be combined with an explicit verb "
                "(`build`/`ship`) -- use either `mason package ship --to "
                "<targets>` or the bare `mason package --ship <targets>` "
                "alias, not both",
                file=sys.stderr,
            )
            return EXIT_USAGE

        if ns.noun == "package" and not getattr(ns, "verb", None) and getattr(ns, "ship", None) is not None:
            # D-12/FR-30: the ONE documented bare-noun exception to "a noun
            # with no verb is a usage error" (the generic check immediately
            # below) -- `mason package --target library --ship
            # pypi,conda-forge` dispatches through the SAME
            # `_dispatch_package_ship` helper the canonical `package ship
            # --to` verb branch (below) calls, so the two forms are
            # byte-identical past this point (spec I/O matrix: "Alias
            # happy path... identical dispatch/result to the canonical
            # form"). This check must stay ahead of the generic one: every
            # OTHER bare noun -- `recipe`, `environment`, and `package`
            # itself with no `--ship` given -- falls through unaffected,
            # since `getattr(ns, "ship", None)` is `None` for all of them
            # (`--ship` is registered with a plain `default=None`, always
            # present on the namespace).
            #
            # **Corrected, review pass 1:** was a truthy check
            # (`getattr(ns, "ship", None)`), which mishandled an explicit
            # `--ship ""` (empty string) -- falsy, so it silently fell
            # through to the generic bare-noun usage error below instead of
            # reaching `package.ship("")`'s own `InvalidShipTargetError`,
            # contradicting this command's own "byte-identical dispatch"
            # contract with `--to ""`. `is not None` treats only a truly
            # ABSENT `--ship` as "not this invocation shape."
            return _dispatch_package_ship(ns, raw_targets=ns.ship)

        if not getattr(ns, "verb", None):
            # A noun invoked with no verb is a usage error: stderr, EXIT_USAGE —
            # matching argparse's own native stream/exit-code convention for an
            # unrecognized verb (e.g. `mason recipe sometypo`). See the spec's
            # 2026-07-30 contract amendment: this row was stdout, corrected to
            # stderr so both exit-2 paths agree on stream.
            ns._noun_parser.print_help(file=sys.stderr)
            return EXIT_USAGE

        if ns.noun == "recipe" and ns.verb == "new":
            # FR-7: `--from-pypi`/`--from-github`/`--from-cran`/`--from-npm`
            # is a required mutually exclusive group, so exactly one of the
            # four is non-None here -- argparse itself guarantees that before
            # this line is ever reached. `source` is CFE's own subcommand
            # name (spec Always boundary: command routing, not recipe
            # knowledge, AD-1 Design Notes) selected 1:1 from which flag the
            # user gave.
            sources = (
                ("pypi", getattr(ns, "from_pypi", None)),
                ("github", getattr(ns, "from_github", None)),
                ("cran", getattr(ns, "from_cran", None)),
                ("npm", getattr(ns, "from_npm", None)),
            )
            source, package_name = next((s, p) for s, p in sources if p is not None)

            fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
            result = recipe.new(
                source,
                package_name,
                ns.output,
                cfe_root_arg=getattr(ns, "cfe_root", None),
                cfe_python_arg=getattr(ns, "cfe_python", None),
                cfe_timeout_arg=_resolve_optional_float(getattr(ns, "cfe_timeout", None), _ENV_CFE_TIMEOUT),
                environ=os.environ,
                start_directory=Path.cwd(),
            )
            render.write(fmt, sys.stdout, "recipe new", "ok", dataclasses.asdict(result), [])
            return EXIT_OK

        if ns.noun == "recipe" and ns.verb == "validate":
            # FR-8: delegates to CFE's recipe validator via recipe.py.
            # `recipe.validate` raises CfeUnresolvedError before any
            # subprocess spawns if the CFE root is unresolved (spec Always
            # boundary) -- caught by the dedicated branch below, same as
            # every other CFE-dependent path. `--cfe-timeout` is resolved
            # here and passed through; `cfe.validate_recipe`'s own
            # per-operation default applies only when that resolves to
            # `None`.
            #
            # Unlike every sibling verb, this branch alone projects the
            # wrapped validator's own pass/fail outcome onto the process
            # exit code (spec Intent/FR-8): `EXIT_OK` when `result.
            # returncode == 0`, else `EXIT_FAILED`. This is `cli.py`'s own
            # dispatch-time decision (AD-7's exit-code ownership) -- the
            # JSON envelope's `status` field stays "ok" regardless (spec I/O
            # matrix), and `recipe.validate` itself still never raises for a
            # validation failure (AD-4), identical to every other verb here.
            fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
            result = recipe.validate(
                ns.recipe_path,
                cfe_root_arg=getattr(ns, "cfe_root", None),
                cfe_python_arg=getattr(ns, "cfe_python", None),
                cfe_timeout_arg=_resolve_optional_float(getattr(ns, "cfe_timeout", None), _ENV_CFE_TIMEOUT),
                environ=os.environ,
                start_directory=Path.cwd(),
            )
            render.write(
                fmt,
                sys.stdout,
                "recipe validate",
                "ok",
                dataclasses.asdict(result),
                [],
            )
            return EXIT_OK if result.returncode == 0 else EXIT_FAILED

        if ns.noun == "recipe" and ns.verb == "build":
            # A manual post-parse cross-check, not argparse-declarative
            # (spec Always boundary): `--docker`/`--config` pairing is a
            # relationship BETWEEN two flags, which argparse's own
            # declarative validators (`required=`, `choices=`, a mutually
            # exclusive group) cannot express directly. Checked, and
            # rejected as EXIT_USAGE, before any CFE resolution is
            # attempted — mirroring the bare-noun usage error's
            # stderr/EXIT_USAGE convention above.
            docker = ns.docker
            # A whitespace-only `--config` is treated as absent (review
            # pass), matching `_resolve_str`'s established "whitespace-only
            # counts as not supplied" convention elsewhere in this file —
            # so `--config ""`/`--config " "` reports the same clear
            # "requires --config" message as omitting the flag entirely,
            # rather than a misleading one claiming it was never given.
            config = ns.config.strip() if ns.config is not None and ns.config.strip() else None
            if docker and not config:
                print("recipe build: --docker requires --config", file=sys.stderr)
                return EXIT_USAGE
            if config and not docker:
                print("recipe build: --config requires --docker", file=sys.stderr)
                return EXIT_USAGE

            fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
            result = recipe.build(
                ns.recipe_path,
                docker=docker,
                config=config,
                cfe_root_arg=getattr(ns, "cfe_root", None),
                cfe_python_arg=getattr(ns, "cfe_python", None),
                cfe_timeout_arg=_resolve_optional_float(
                    getattr(ns, "cfe_timeout", None),
                    _ENV_CFE_TIMEOUT,
                ),
                environ=os.environ,
                start_directory=Path.cwd(),
            )
            # A non-zero delegated build returncode is DATA on `result`,
            # never raised (AD-4) — this branch always reports "ok"/
            # EXIT_OK for a Mason-successful invocation, mirroring
            # `doctor`'s "the gap is data" precedent above; `data.
            # returncode` is the signal, not this command's own status.
            render.write(fmt, sys.stdout, "recipe build", "ok", dataclasses.asdict(result), [])
            return EXIT_OK

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
                    "mason recipe diagnose: '-' (stdin) is not supported -- pass a real log file path",
                    file=sys.stderr,
                )
                return EXIT_USAGE
            fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
            result = recipe.diagnose(
                ns.log_path,
                cfe_root_arg=getattr(ns, "cfe_root", None),
                cfe_python_arg=getattr(ns, "cfe_python", None),
                cfe_timeout_arg=_resolve_optional_float(getattr(ns, "cfe_timeout", None), _ENV_CFE_TIMEOUT),
                environ=os.environ,
                start_directory=Path.cwd(),
            )
            render.write(
                fmt,
                sys.stdout,
                "recipe diagnose",
                "ok",
                dataclasses.asdict(result),
                [],
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
                cfe_timeout_arg=_resolve_optional_float(getattr(ns, "cfe_timeout", None), _ENV_CFE_TIMEOUT),
                environ=os.environ,
                start_directory=Path.cwd(),
            )
            render.write(
                fmt,
                sys.stdout,
                "recipe optimize",
                "ok",
                dataclasses.asdict(result),
                [],
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
                cfe_timeout_arg=_resolve_optional_float(getattr(ns, "cfe_timeout", None), _ENV_CFE_TIMEOUT),
                environ=os.environ,
                start_directory=Path.cwd(),
            )
            render.write(
                fmt,
                sys.stdout,
                "recipe scan",
                "ok",
                dataclasses.asdict(result),
                [],
            )
            return EXIT_OK

        if ns.noun == "recipe" and ns.verb == "submit":
            # FR-13: delegates to CFE's two-phase submission flow via
            # recipe.py. `recipe.submit` raises `CfeUnresolvedError` before
            # any subprocess spawns if the CFE root is unresolved (spec
            # Always boundary) -- caught by the dedicated branch below, same
            # as every other CFE-dependent path. `ns.yes`/`ns.prepare_only`
            # are plain `bool`s (not `getattr`-guarded: these two flags live
            # only on this verb's own parser, never on the shared
            # `global_flags` parent -- see their registration comment
            # above), passed straight through as `confirm`/`prepare_only`;
            # `recipe.submit` does the `--dry-run` inversion itself.
            fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
            result = recipe.submit(
                ns.recipe_path,
                confirm=ns.yes,
                prepare_only=ns.prepare_only,
                cfe_root_arg=getattr(ns, "cfe_root", None),
                cfe_python_arg=getattr(ns, "cfe_python", None),
                cfe_timeout_arg=_resolve_optional_float(getattr(ns, "cfe_timeout", None), _ENV_CFE_TIMEOUT),
                environ=os.environ,
                start_directory=Path.cwd(),
            )
            render.write(
                fmt,
                sys.stdout,
                "recipe submit",
                "ok",
                dataclasses.asdict(result),
                [],
            )
            return EXIT_OK

        if ns.noun == "recipe" and ns.verb == "update":
            # FR-14: delegates to CFE's autotick scripts via recipe.py.
            # `recipe.update` raises `CfeUnresolvedError` before any
            # subprocess spawns if the CFE root is unresolved (spec Always
            # boundary) -- caught by the dedicated branch below, same as
            # every other CFE-dependent path. `ns.dry_run`/`ns.github`/
            # `ns.repo`/`ns.pre` are plain values (not `getattr`-guarded:
            # these four flags live only on this verb's own parser, never on
            # the shared `global_flags` parent -- see their registration
            # comment above), passed straight through; `recipe.update` does
            # its own dispatch/argv composition.
            #
            # Review pass (2026-08-12): `--repo`/`--pre` are silently inert
            # without `--github` (spec Always boundary -- intentional, not a
            # bug), but a user who forgets `--github` gets no signal that
            # their flag was ignored and the PyPI path ran instead. A
            # `logging.warning` (stderr, same channel every other diagnostic
            # uses) makes that silence loud rather than changing the
            # underlying inert-not-rejected contract.
            if (ns.repo or ns.pre) and not ns.github:
                logging.warning("mason recipe update: --repo/--pre have no effect without --github -- ignored")
            fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
            result = recipe.update(
                ns.recipe_path,
                dry_run=ns.dry_run,
                github=ns.github,
                github_repo=ns.repo,
                allow_prerelease=ns.pre,
                cfe_root_arg=getattr(ns, "cfe_root", None),
                cfe_python_arg=getattr(ns, "cfe_python", None),
                cfe_timeout_arg=_resolve_optional_float(getattr(ns, "cfe_timeout", None), _ENV_CFE_TIMEOUT),
                environ=os.environ,
                start_directory=Path.cwd(),
            )
            render.write(
                fmt,
                sys.stdout,
                "recipe update",
                "ok",
                dataclasses.asdict(result),
                [],
            )
            return EXIT_OK

        if ns.noun == "package" and ns.verb == "build":
            # FR-15/FR-21/FR-22: drives Story 3.1's engine protocol through
            # package.py's own two adapters (engines.pep517/engines.pixi).
            # Unlike every `recipe` verb, `package.build()` never touches
            # CFE at all (spec Always boundary) -- no cfe-root/cfe-python/
            # cfe-timeout flags are read here.
            fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
            result = package.build(ns.project_path, target=ns.target)
            # A non-zero delegated engine returncode is DATA on `result`,
            # never raised (AD-4) -- this branch always reports "ok"/
            # EXIT_OK for a Mason-successful invocation, mirroring `recipe
            # build`'s established "the gap is data" precedent above;
            # `PackageVersionMismatchError` is the one exception `package.
            # build()` can still raise, propagating to main()'s existing
            # `except MasonError` handler below.
            render.write(fmt, sys.stdout, "package build", "ok", dataclasses.asdict(result), [])
            return EXIT_OK

        if ns.noun == "package" and ns.verb == "ship":
            # FR-16/FR-24/FR-50/D-12: the canonical shipping verb --
            # dispatches through the SAME `_dispatch_package_ship` helper
            # the bare-noun `--ship` alias branch above calls, so the two
            # forms are byte-identical past this point (spec I/O matrix).
            return _dispatch_package_ship(ns, raw_targets=ns.to)

        if ns.noun == "environment" and ns.verb == "lock":
            # FR-25/FR-27/FR-29: drives Story 4.1's engine protocol through
            # environment.py's own single adapter (engines.condalock). Like
            # `package build`, `environment.lock()` never touches CFE at
            # all (spec Always boundary) -- no cfe-root/cfe-python/
            # cfe-timeout flags are read here.
            fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
            # Story 4.2: an empty `manifest_path` (nargs="*") triggers
            # discovery against Path.cwd() -- an explicit manifest_path
            # always skips this entirely (spec Intent: "explicit paths
            # override discovery entirely"). The discovered list is printed
            # to stderr as a plain print(), not logging (the default
            # WARNING level would silently hide it from a non-`--verbose`
            # run) -- and never gated behind --verbose/--quiet (spec Never
            # boundary). `EnvironmentManifestsNotFoundError` propagates to
            # main()'s existing `except MasonError` handler below.
            manifest_paths = ns.manifest_path
            if not manifest_paths:
                manifest_paths = environment.discover_manifests(Path.cwd())
                print(f"discovered manifests: {', '.join(manifest_paths)}", file=sys.stderr)
            result = environment.lock(manifest_paths, ns.output, platforms=ns.platform)
            # A non-zero delegated engine returncode is DATA on `result`,
            # never raised (AD-4) -- this branch always reports "ok"/
            # EXIT_OK for a Mason-successful invocation, mirroring `package
            # build`'s identical "the gap is data" precedent above.
            # `EngineAbsentError`/`EnvironmentLockTimeoutError` are the
            # exceptions `environment.lock()` can still raise, propagating
            # to main()'s existing `except MasonError` handler below.
            render.write(
                fmt,
                sys.stdout,
                "environment lock",
                "ok",
                dataclasses.asdict(result),
                [],
            )
            return EXIT_OK

        if ns.noun == "environment" and ns.verb == "check":
            # FR-25/FR-27/FR-29: CI's own companion to `environment lock`
            # above -- drives `engines.condalock.check()` through
            # `environment.py`'s own use-case wrapper. Like `environment
            # lock`, `environment.check()` never touches CFE at all (spec
            # Always boundary) -- no cfe-root/cfe-python/cfe-timeout flags
            # are read here.
            #
            # Unlike `environment lock`, this branch projects the delegated
            # staleness verdict onto the process exit code (spec Intent,
            # mirrors `recipe validate`'s own "wrapped tool's pass/fail
            # outcome becomes the process exit code" precedent -- the ONE
            # other verb in this codebase that does this): `EXIT_OK` when
            # `result.stale` is `False` AND `result.returncode == 0`, else
            # `EXIT_FAILED`. The `returncode` half (review pass, 2026-08-15)
            # guards against a genuine `conda-lock` failure (bad manifest,
            # solver crash, network error during the real re-solve a hash
            # mismatch triggers) leaving the temp copy unrewritten, which
            # would otherwise make `before == after` trivially hold and
            # silently report `stale=False` for a check that never actually
            # ran to completion -- a CI gate must not green-light on its own
            # internal failure. The JSON envelope's own `status` field stays
            # "ok" regardless (spec I/O matrix), and `environment.check()`
            # itself never raises for either a stale verdict or a non-zero
            # `returncode` (AD-4) -- `EnvironmentLockfileMissingError`/
            # `EnvironmentLockfileMalformedError`/`EngineAbsentError`/
            # `EnvironmentCheckTimeoutError` are the exceptions it can still
            # raise, propagating to main()'s existing `except MasonError`
            # handler below.
            fmt = _resolve_str(getattr(ns, "format", None), _ENV_FORMAT, "text")
            # Story 4.2: identical discovery fallback to `environment lock`
            # above -- see that branch's comment for the full rationale.
            manifest_paths = ns.manifest_path
            if not manifest_paths:
                manifest_paths = environment.discover_manifests(Path.cwd())
                print(f"discovered manifests: {', '.join(manifest_paths)}", file=sys.stderr)
            result = environment.check(ns.lockfile, manifest_paths, platforms=ns.platform)
            render.write(
                fmt,
                sys.stdout,
                "environment check",
                "ok",
                dataclasses.asdict(result),
                [],
            )
            return EXIT_OK if not result.stale and result.returncode == 0 else EXIT_FAILED

        # Unreachable now for every verb-noun pair except `recipe new`/
        # `recipe validate`/`recipe build`/`recipe diagnose`/`recipe
        # optimize`/`recipe scan`/`recipe submit`/`recipe update`/`package
        # build`/`package ship`/`environment lock`/`environment check`
        # above, each handled by its own branch: `environment` registers no
        # verb beyond `lock`/`check`, `package` registers no verb beyond
        # `build`/`ship`, and `recipe` registers no verb beyond those eight,
        # so argparse itself rejects any other token here as an invalid
        # choice before `ns.verb` could ever hold it. Kept only so a later
        # story that populates another verb has somewhere to land its
        # dispatch.
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
    except Exception:  # noqa: BLE001 — deliberate boundary
        import traceback

        traceback.print_exc()
        return EXIT_FAILED


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
