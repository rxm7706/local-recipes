"""Story 6.9: one thin, target-less CLI dispatcher for Doctor's ported
sources -- ``python -m pyforge.doctor.sources <name> [--json] [--groundtruth]``.
Twelve total today: the ten Story 6.9 originally dispatched, plus Story
11.1's ``due-for-verification`` and Story 10.1's
``bmad-method-version-drift`` -- both genuinely NEW (non-ported) members
(see their own DISPATCH rows below).

WHY THIS EXISTS. Stories 6.4-6.8 ported ten ``scripts/*_check.py`` (plus
``docs/dashboard/check_layout.py``) verdicts into library ``gather(target)``
filters, but none of them ever gained a CLI entrypoint, and none is wired
into ``__main__.py``'s ``check``/``monitor``/``diagnose`` verb dispatch
(deliberately -- see ``sources/__init__.py``'s own docstring; that axis
system serves Doctor's OWN self-check, a closed category set unrelated to
these Marshal-artifact verdicts). Story 6.9 retires the eleven pixi
tasks that used to invoke the origin scripts directly; this module is what
those tasks invoke instead, one source at a time.

NO --target/--path ARGUMENT, ON PURPOSE. Every origin script judged the repo
it physically lived inside, resolved via its own ``Path(__file__)`` (e.g.
``scripts/*_check.py``'s ``ROOT = Path(__file__).resolve().parent.parent``).
This module cannot mirror that literally: once ``pyforge-doctor`` is built
and installed as a conda package (which is how every pixi task that will
invoke this module gets it), ``__file__`` resolves somewhere under
``.pixi/envs/<env>/lib/python3.14/site-packages/...`` -- a path with no
fixed, portable relationship to whichever checkout is running it. The
equivalent that actually holds is the CURRENT WORKING DIRECTORY: pixi runs
every task from the workspace root unless the task sets its own ``cwd``
(none of the eleven re-pointed here do), and ``doctor check``'s own ``path``
positional already defaults the identical way (``nargs="?", default="."``).
So ``target = Path(".")`` below -- always the repo this was invoked from,
achieved by CWD rather than by ``__file__``, which is what "always judges
the repo it runs in" means for a module that ships as a built package.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from collections.abc import Callable
from pathlib import Path

from ..models import Finding, Source
from ..verdict import EXIT_SIGINT, exit_code_for
from . import bmad_method, board, chain, deps, factory, ledger, marshal, sibling_dreams

__all__ = ("main", "DISPATCH")

# One entry per retiring `scripts/*_check.py` (+ `docs/dashboard/check_layout.py`)
# origin -- the ten Sources these eleven pixi tasks address (bmad-drift is
# reached by two tasks: plain, and `--groundtruth`). Deliberately NOT every
# `sources.REGISTRY` member: most of those (warden-doctor, staleness-report,
# env-hygiene, ...) never had a `scripts/*_check.py` twin and are out of this
# story's surface. PUBLIC (no leading underscore) and imported directly by
# `scripts/detectors.py`'s own real-run-path threading, so that file's
# "which 10 sources does this cover" never becomes a second, driftable list.
DISPATCH: dict[str, Callable[[Path], tuple[Finding, ...]]] = {
    Source.LEDGER_REGRESSION.value: ledger.gather,
    Source.STORY_STATUS.value: marshal.gather_story_status,
    Source.CHAIN_COMPLETENESS.value: board.gather_chain_completeness,
    Source.DASHBOARD_DRIFT.value: board.gather_dashboard_drift,
    Source.CHECK_LAYOUT.value: board.gather_check_layout,
    Source.DREAM_CHAIN.value: chain.gather_dream_chain,
    Source.SPEC_SURFACE.value: chain.gather_spec_surface,
    Source.DEFERRED_WORK.value: chain.gather_deferred_work,
    Source.FORWARD_DEPENDENCY.value: deps.gather_forward_dependency,
    Source.BMAD_DRIFT.value: factory.gather,
    # Story 11.1 (Epic 11/CAP-1) -- the first genuinely NEW (non-ported)
    # DISPATCH member: no retiring `scripts/*_check.py` origin, same
    # `Callable[[Path], tuple[Finding, ...]]` shape as every ported entry
    # above (Design Notes).
    Source.DUE_FOR_VERIFICATION.value: chain.gather_due_for_verification,
    # Story 10.1 (Epic 10/CAP-1) -- another genuinely NEW (non-ported)
    # DISPATCH member, same shape as DUE_FOR_VERIFICATION above.
    Source.BMAD_METHOD_VERSION_DRIFT.value: bmad_method.gather,
    # Story 16.1 (Epic 16/CAP-1) -- sibling Dream title drift; fail-open,
    # warn-only; fleet-picture ATTENTION probes this DISPATCH name.
    Source.SIBLING_DREAMS_DRIFT.value: sibling_dreams.gather,
    # Story 15.2 (marshal Epic 15 / FR-137..138) -- ledger-vs-git drift
    # WITH DIRECTION; reads merge history + tracked twin, never the feed.
    Source.LEDGER_STALENESS.value: ledger.gather_ledger_staleness,
}

# `--groundtruth` is bmad-drift-only -- it prints `factory.ground_truth`'s six
# live-fact keys (the `bmad-groundtruth` pixi task's replacement), not a
# Finding gather. No other source has an equivalent ground-truth export.
_GROUNDTRUTH_SOURCE = Source.BMAD_DRIFT.value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pyforge.doctor.sources",
        description=(
            "Run one ported Doctor source against the repo this is invoked "
            "from (no --target/path argument -- see module docstring)."
        ),
    )
    parser.add_argument(
        "source",
        choices=sorted(DISPATCH),
        help="the Source to gather (argparse rejects any other name, exit 2)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the gathered findings as a JSON array (Finding.to_json_dict())",
    )
    parser.add_argument(
        "--groundtruth",
        action="store_true",
        help=(
            f"print {_GROUNDTRUTH_SOURCE!r}'s live ground-truth facts as "
            "JSON instead of gathering findings -- valid only for that one "
            "source (the bmad-groundtruth pixi task's replacement)"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.groundtruth and args.source != _GROUNDTRUTH_SOURCE:
        parser.error(
            f"argument --groundtruth: only valid for source "
            f"{_GROUNDTRUTH_SOURCE!r}, got {args.source!r}"
        )

    target = Path(".")

    if args.groundtruth:
        try:
            gt = factory.ground_truth(target)
        except Exception as exc:
            # Unlike every DISPATCH entry (wrapped by `gather()`'s own
            # degrade_on_exception), this call goes straight through --
            # a bad-but-present pixi.toml/CHANGELOG.md/SKILL.md raises
            # rather than degrading. Never a raw traceback here.
            print(f"could not gather ground truth: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(gt, indent=2, sort_keys=True))
        return 0

    findings = DISPATCH[args.source](target)

    if args.json:
        print(json.dumps([finding.to_json_dict() for finding in findings], indent=2))
    else:
        for finding in findings:
            print(
                f"[{finding.source.value}] {finding.check}: "
                f"{finding.status.value} -- {finding.message}"
            )

    return exit_code_for(findings)


if __name__ == "__main__":
    # check-layout drives a real browser and can hang; the retired
    # docs/dashboard/check_layout.py had this same suppress-and-130
    # handling directly in its own __main__ block.
    with contextlib.suppress(KeyboardInterrupt):
        sys.exit(main())
    sys.exit(EXIT_SIGINT)
