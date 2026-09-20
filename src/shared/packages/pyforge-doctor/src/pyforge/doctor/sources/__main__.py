"""Story 6.9: one thin, target-less CLI dispatcher for Doctor's ported
sources -- ``python -m pyforge.doctor.sources <name> [--json] [--groundtruth]``.
The ten Story 6.9 originally dispatched, plus every genuinely NEW
(non-ported) member a later story has added since (``due-for-verification``,
``bmad-method-version-drift``, ...) -- see ``DISPATCH`` below for the
current, exhaustive roster; the member COUNT is deliberately not written
down in prose here, mirroring ``sources/__init__.py``'s own REGISTRY
docstring rationale (a number here would only ever be a second source of
truth that goes stale the next time a story appends an entry -- it already
did once).

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
from . import (
    bmad_config,
    bmad_method,
    board,
    capability_effect,
    capability_ledger,
    chain,
    deps,
    docs_currency,
    docs_map_hygiene,
    docs_shelf,
    factory,
    frozen_path,
    general_docs_consistency,
    ledger,
    live_proof_surfaces,
    marshal,
    one_chain,
    pixi_currency,
    platform_policy,
    sibling_dreams,
    status_body_consistency,
)

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
    Source.LEDGER_DIRECTION.value: ledger.gather_direction,
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
    # Retro action item 3 (retro-pyforge-steward-2026-09-04.md, 2026-09-05)
    # -- another genuinely NEW (non-ported) DISPATCH member, same shape as
    # DUE_FOR_VERIFICATION/SIBLING_DREAMS_DRIFT above.
    Source.PLATFORM_POLICY_SUITE.value: platform_policy.gather,
    # Story 20.2 (Epic 20) -- another genuinely NEW (non-ported) DISPATCH
    # member, same shape as PLATFORM_POLICY_SUITE/SIBLING_DREAMS_DRIFT above.
    Source.BMAD_RENDER_CONFIG_AMBIGUITY.value: bmad_config.gather,
    # Story 20.3 (Epic 20) -- another genuinely NEW (non-ported) DISPATCH
    # member, same shape as BMAD_RENDER_CONFIG_AMBIGUITY above.
    Source.FROZEN_PATH_CHANGED.value: frozen_path.gather,
    # Story 21.11 (Epic 21) -- capability-effect beside story-status in
    # detectors; same shape as FROZEN_PATH_CHANGED above.
    Source.CAPABILITY_EFFECT.value: capability_effect.gather,
    # Story 21.16 (Epic 21) -- status-body-consistency beside capability-effect
    # in detectors; same shape as CAPABILITY_EFFECT above.
    Source.STATUS_BODY_CONSISTENCY.value: status_body_consistency.gather,
    # Story 21.7 (Epic 21 / spec-pixi-candidate-currency CAP-4) -- advisory
    # ledger staleness vs ``pixi.toml`` commit history; same shape as
    # STATUS_BODY_CONSISTENCY above.
    Source.PIXI_CURRENCY_LEDGER.value: pixi_currency.gather,
    # Story 22.3 (Epic 22) -- general-docs-consistency beside status-body-
    # consistency in detectors; same shape as PIXI_CURRENCY_LEDGER above.
    Source.GENERAL_DOCS_CONSISTENCY.value: general_docs_consistency.gather,
    # Story 55.2 -- extract detector vs capability-ledger.yaml.
    Source.CAPABILITY_LEDGER.value: capability_ledger.gather,
    # Doctor Epic 25 (spec-one-chain-per-station CAP-2 / CAP-5): both
    # repo-scope, offline, deterministic -- in detectors-ci from day one.
    Source.CHAIN_SPRAWL.value: one_chain.gather_chain_sprawl,
    Source.FR_WITHOUT_CAP.value: one_chain.gather_fr_without_cap,
    # Story 30.1 (spec-pyforge-doctor CAP-83): docs/MAP.md vs the four
    # Diátaxis quadrants -- missing link FAIL, unmapped page FAIL (promoted
    # by Story 30.2).
    Source.DOCS_MAP_HYGIENE.value: docs_map_hygiene.gather,
    # Story 30.2 (spec-pyforge-doctor CAP-84): docs/map.yaml vs its render
    # (docs/MAP.md's generated Page registry section), authored-page
    # staleness, and skill-dir hygiene -- same shape as DOCS_MAP_HYGIENE
    # above, warn-only, fail-open.
    Source.DOCS_CURRENCY.value: docs_currency.gather,
    # Story 23.7 (Epic 23/spec-pyforge-doctor CAP-54) -- leftover-shelf
    # occupancy vs the docs/MAP.md allow-list; same shape as
    # GENERAL_DOCS_CONSISTENCY above.
    Source.DOCS_SHELF_OCCUPANCY.value: docs_shelf.gather,
    # Story 26.1 (spec-pyforge-doctor CAP-77) -- a touched surface
    # catalogued in live-proof-surfaces.md gets an advisory finding naming
    # it; same shape as DOCS_SHELF_OCCUPANCY above.
    Source.LIVE_PROOF_SURFACE.value: live_proof_surfaces.gather,
}

# `--groundtruth` is bmad-drift-only -- it prints `factory.ground_truth`'s six
# live-fact keys (the `bmad-groundtruth` pixi task's replacement), not a
# Finding gather. No other source has an equivalent ground-truth export.
_GROUNDTRUTH_SOURCE = Source.BMAD_DRIFT.value
_DREAMS_HYGIENE_SOURCE = Source.DREAM_CHAIN.value  # --dreams flag host
_LAYERS_AUDIT_SOURCE = Source.CHAIN_COMPLETENESS.value  # --layers flag host


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
    parser.add_argument(
        "--dreams",
        action="store_true",
        help=(
            f"valid only for source {_DREAMS_HYGIENE_SOURCE!r}: run the "
            "Dream-tier hygiene mode (frontmatter validity, README table "
            "sync, realization-log presence) instead of INV-0..3 chain "
            "completeness. Story 17-2 / FR-147 — CLI spelling chosen over "
            "folding into --inv."
        ),
    )
    parser.add_argument(
        "--layers",
        action="store_true",
        help=(
            f"valid only for source {_LAYERS_AUDIT_SOURCE!r}: run the "
            "per-project CAP-3 chain audit (layer presence + coherence + "
            "staleness + orphan-freedom checkpoints), seeded from "
            "pyforge.doctor.sources.fleet_scan. Requires --project. "
            "Stories 17-3 + 21-1 / FR-150 + FR-192 CAP-3."
        ),
    )
    parser.add_argument(
        "--project",
        metavar="SLUG",
        default=None,
        help=("BMAD project slug for --layers (e.g. pyforge-marshal). Required with --layers; ignored otherwise."),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.groundtruth and args.source != _GROUNDTRUTH_SOURCE:
        parser.error(f"argument --groundtruth: only valid for source {_GROUNDTRUTH_SOURCE!r}, got {args.source!r}")

    if args.dreams and args.source != _DREAMS_HYGIENE_SOURCE:
        parser.error(f"argument --dreams: only valid for source {_DREAMS_HYGIENE_SOURCE!r}, got {args.source!r}")

    if args.layers and args.source != _LAYERS_AUDIT_SOURCE:
        parser.error(f"argument --layers: only valid for source {_LAYERS_AUDIT_SOURCE!r}, got {args.source!r}")

    if args.layers and not args.project:
        parser.error("argument --layers: requires --project SLUG")

    if args.project and not args.layers:
        parser.error("argument --project: only valid together with --layers")

    if args.groundtruth and args.dreams:
        parser.error("argument --dreams: not valid together with --groundtruth")

    if args.layers and (args.dreams or args.groundtruth):
        parser.error("argument --layers: not valid together with --dreams or --groundtruth")

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

    if args.dreams:
        findings = chain.gather_dreams_hygiene(target)
    elif args.layers:
        findings = board.gather_chain_layers_audit(target, args.project)
    else:
        findings = DISPATCH[args.source](target)

    if args.json:
        print(json.dumps([finding.to_json_dict() for finding in findings], indent=2))
    else:
        for finding in findings:
            print(f"[{finding.source.value}] {finding.check}: {finding.status.value} -- {finding.message}")

    return exit_code_for(findings)


if __name__ == "__main__":
    # check-layout drives a real browser and can hang; the retired
    # docs/dashboard/check_layout.py had this same suppress-and-130
    # handling directly in its own __main__ block.
    with contextlib.suppress(KeyboardInterrupt):
        sys.exit(main())
    sys.exit(EXIT_SIGINT)
