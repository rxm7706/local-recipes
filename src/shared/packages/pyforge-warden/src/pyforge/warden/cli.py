"""The real argparse CLI + scan orchestration (Story 1.2).

(The scaffold stub's docstring credited this to Story 4.1 — stale; the real
CLI landed with 1.2. Renderers proper are Story 1.8; typed errors 1.7; full
discovery 1.9.)

* D2's split (Story 1.9): the ``if not manifests:`` branch (discovery found
  NOTHING, no exception) splits on ``has_adjacent_python_source(target)`` —
  Python signals present means the recursive walk should have found
  something recognizable, so the run fails closed (``Status.ERROR``/exit 2,
  ``ErrorKind.UNPARSABLE_MANIFEST``); no Python source anywhere keeps the
  unchanged not-applicable/exit 0 stderr-only path. A SEPARATE, independent
  D2 case (c): at least one manifest parses but the whole scan feeds zero
  rungs (no components, no engine findings, no errors) — checked via
  ``manifests_parsed > 0 and not rungs`` after policy evaluation — injects
  one ``Status.INDETERMINATE`` rung with a paired ``Finding`` (the
  ratified Story 1.7 two-namespace contract: every non-error driver must
  reference an emitted finding) whose id is the FIXED literal
  ``indeterminate:empty-extraction:scan`` — never ``args.path`` — so
  ``warden scan .`` and ``warden scan <absolute path>`` against the same
  condition produce the SAME id (invocation-stability; this driver is
  whole-scan-scoped, not per-package, unlike the ``<pkg>``-shaped siblings
  in this finding-id family). ``--allow-empty`` downgrades ONLY that exit
  to 0 (``verdict.exit_code_for``'s sole-owned knob); ``status`` stays
  ``indeterminate``, never ``clean``, and ``empty_extraction=True`` is
  passed to ``assemble_report`` regardless of the flag, so ``coverage:
  none`` is recorded whether or not the downgrade fired.

Ownership decisions recorded:

* Stream discipline (NFR-I3): in ``--format json`` stdout carries EXACTLY
  one schema-valid ``ComplianceReport`` document or NOTHING; every
  diagnostic — including the empty-scan-set notice — goes to stderr.
  ``--format text`` emits ``report.render_text``'s non-contract human
  summary (a verdict line, then a driver line and one line per finding/
  error as applicable — Story 1.8) via the SAME ``sys.stdout.write`` call
  json already used, inside the try/except that already guarded both
  branches pre-1.8 — this story changed WHAT is printed on the text
  branch, not the guard structure around it.
* Exit codes come ONLY from ``verdict.exit_code_for`` / ``verdict.
  EXIT_SIGINT`` (the sole-ownership rule). argparse's own exits
  (``--version``/``--help`` → 0, usage errors → 2, never 0) surface via the
  caught ``SystemExit``'s code — ``None`` → success, an int passes through,
  and a non-int code (argparse never produces one under this parser config)
  projects via ``exit_code_for(error)``, never ``int()``-crashes.
* Last-resort net: any unexpected ``Exception`` escaping the scan (an
  internal defect, ``render_json``'s fail-loud self-validation, a crashing
  future engine hook) returns ``exit_code_for(error)`` with the traceback
  on stderr — NEVER the interpreter's default exit 1, which would collide
  with the ``indeterminate``/``policy-violation`` projection and read as
  "scan completed, findings found" to an exit-code-only CI consumer.
  ``SystemExit`` raised INSIDE the scan region (a component calling
  ``sys.exit`` — a sole-ownership violation, even ``sys.exit(0)``) is
  likewise projected to ``exit_code_for(error)``: nothing inside the scan
  may dictate the gate's exit, so its carried code is never trusted.
* ``--deterministic`` is accepted as a DOCUMENTED NO-OP: the 1.2 report
  carries no volatile fields, so default output is already byte-identical;
  volatile-field pinning arrives with ``determinism.py``.
* Early-fatal boundary: an empty/whitespace path (which would otherwise
  Path-normalize to ``"."`` and silently scan the CWD) or a nonexistent/
  undiscoverable target (not an existing directory) emits a stderr
  diagnostic and exits ``exit_code_for(error)`` with stdout EMPTY — no
  report exists to emit. The gate stats EXPLICITLY (``Path.is_dir()``
  swallows every ``OSError``): "could not look" (permission-denied parent,
  ELOOP) is diagnosed as could-not-stat, never as "not there". Every
  failure PAST that boundary still emits the report: the exit code is
  orthogonal to emission (a ``render_json`` self-validation failure is the
  recorded exception — an invalid report must not reach stdout, so the
  last-resort net returns the error exit with stdout empty).
* Error taxonomy (only genuine manifest problems are labeled
  ``unparsable-manifest``): a structurally-broken manifest raises
  ``UnparsableManifestError`` and an OS failure READING the manifest
  (chmod-000, TOCTOU deletion) is also a manifest problem (the errno is
  stated SYMBOLICALLY — ``EACCES`` — because strerror text is
  locale-dependent and ``OSError.__str__`` embeds the absolute path;
  report bytes must not vary by locale or scan location). Everything else
  on the discovery/extract/routing path — an unknown manifest kind, ANY
  unexpected exception out of an extractor (the extractor seam gets the
  same catch-all doctrine as the engine seam: 1.3+ plug implementations
  in), a discovery ``OSError`` — is ``internal-error``. A crashing engine
  constructor (instantiation is part of the seam) is
  ``engine-unavailable``; a crashing ``engine.run`` is
  ``engine-execution-failed``. Each yields a typed ``ErrorRecord`` + an
  error rung; the report is emitted (status ``error``, exit
  ``exit_code_for(error)``). Error-driver id segments are sanitized like
  component-derived segments (``_sanitize_id_segment``).
* Error-status drivers use the ``error:<kind>:<subject>`` grammar and do
  NOT reference ``findings[]`` — the error report's driver is a dangling
  id by design (``findings`` may be empty; the report stays schema-valid).
  Story 1.7 ratified this as the final error-driver grammar, with the
  driver's axis set to the actually-failing stage/engine (``AXIS_INGESTION``
  for a pre-engine discovery/extract/routing failure, ``AXIS_HYGIENE``/
  ``AXIS_VULNERABILITY`` for a crashing engine's own axis) — never a
  blanket default.
* ``KeyboardInterrupt`` ANYWHERE in ``main`` — argument parsing, the scan,
  or mid-emission — returns ``EXIT_SIGINT``; any partial stdout must not
  be consumed.
* ``BrokenPipeError`` during stdout emission is absorbed (the consumer went
  away, e.g. ``| head``): the report's already-computed exit code is still
  returned and no traceback contaminates stderr. Stdout is FLUSHED inside
  the guarded region so a block-buffered pipe surfaces the error to the
  absorber instead of exploding at interpreter-exit flush (CPython exit
  120). Any OTHER stdout ``OSError`` (ENOSPC, EIO) is environmental, not
  an internal defect: absorbed with a stderr notice, computed exit code
  preserved. Stderr diagnostics absorb every write failure the same way
  (``_stderr`` — including ``ValueError`` on a CLOSED stderr, which
  ``print`` raises instead of ``OSError``; ``_stderr`` runs inside
  exception handlers, where a raise would escape ``main`` as interpreter
  exit 1) — a vanished diagnostic stream must not replace the computed
  exit code.
* Strictly non-interactive: no prompts, stdin is never read.
* ``has_locked_closure`` (Story 2.6): the extraction loop tracks
  ``parsed_kinds`` — the set of manifest KINDS that actually parsed, not
  just the count — and passes ``bool(parsed_kinds & {PIXI_LOCK_KIND,
  CONDA_LOCK_KIND})`` to ``assemble_report``. ``report.py`` has no
  lockfile-kind vocabulary of its own (that's ``discovery.py``'s domain),
  so the caller states the claim.
* ``hygiene_applicable`` (Story 2.4, AC3): computed ONCE, via
  ``hygiene.has_adjacent_python_source(target)``, right before
  ``engines_to_run`` — a source-less scan target (the fleet's majority
  feedstock shape) makes deptry flag every conda-sourced dependency
  reaching the front-door as "unused" (a noise wall, never a signal), so
  ``DeptryEngine`` is filtered out of ``engines_to_run`` when it is
  ``False`` and the same value is threaded into ``assemble_report`` so the
  hygiene axis honestly reports not-applicable. Deliberately NOT a check
  inside ``DeptryEngine.run`` itself — ``tests/unit/
  test_engine_env_deptry.py`` calls the engine directly against bare
  ``tmp_path`` dirs to test its own argv/error-handling logic in isolation,
  and embedding the skip there would exercise the wrong branch in every one
  of those tests.
* Waiver wiring (Story 3.2, FR24-FR26): ``target / ".warden-waivers.yaml"``
  is read AFTER the D2(c) empty-extraction append and BEFORE
  ``assemble_report`` — every rung fed by ``DefaultPolicy``/D2(c) up to
  that point (including the D2(c) driver) is present, so waiver matching
  and ``--bypass`` see that picture. NOT covered (review finding,
  documented rather than silently overclaimed): the
  ``indeterminate:coverage-floor:<axis>`` rung ``report.assemble_report``
  computes internally, strictly AFTER this point — that axis is
  out-of-scope for waiver-matching in this story (opt-in, defaults off;
  see the story's spec) and neither a committed waiver nor ``--bypass``
  can suppress it. A malformed/schema-invalid file surfaces through the
  SAME ``_record_error`` seam as every other ingestion-stage failure
  (``owner="waiver"``); a missing file is normal (zero waivers, no error).
  ``--bypass`` force-bypasses every remaining non-clean, Finding-backed
  rung it can see (the same coverage-floor exclusion applies) and prints
  ``waiver.emit_bypass_stanza``'s output to stdout BEFORE the report
  itself — never to a file (the tool never writes into the scanned tree);
  ``--bypass`` without ``--reason`` is the ONE usage error this module
  adds beyond argparse's own (``scan_parser.error(...)``, exit 2, never
  0). Under ``--format json``, the stanza is NOT written to stdout (NFR-I3:
  stdout carries exactly one schema-valid document or nothing) — it is
  written to stderr instead, so the audit-trail affordance is never
  silently lost regardless of output format.
* Waiver-expiry visibility + ``--warn-only`` (Story 3.3, FR23/FR25):
  ``apply_waivers`` now returns a 3-tuple; the new ``expired_waivers`` list
  is threaded into ``render_text`` unchanged in MEANING (a distinct
  ``[waiver-expired]`` line per expired match — the already-correct
  re-block fall-through itself is untouched, only its visibility is new).
  ``--warn-only`` (``store_true``, next to ``--bypass``) calls
  ``waiver.warn_blocking`` AFTER the existing ``apply_waivers``/
  ``--bypass`` block, downgrading every still-blocking ``policy-
  violation``/``indeterminate`` rung it sees to ``warn`` (never ``error``)
  — the ``indeterminate:coverage-floor:<axis>`` rung ``report.
  assemble_report`` computes internally is added strictly AFTER this
  point, so it structurally survives ``--warn-only`` untouched (the FR19
  guardrail). The downgraded-rung count feeds ``render_text``'s
  graduate-to-enforcing nudge, gated on ALL of ``warn_only``,
  ``status["value"] == "warn"``, and ``warn_only_downgraded > 0`` — see
  ``report.py``'s own docstring for why ``status == "warn"`` alone is not
  sufficient.
* ``--sbom-output`` (Story 4.1): an independent sibling artifact, written
  right after ``report = assemble_report(...)`` — the report is ALREADY
  fully assembled by this point, so NO failure here (rendering OR writing)
  may suppress its emission below or alter ``report.exit_code`` (review
  finding, 2026-07-18: an earlier revision let a non-``(OSError, ValueError)``
  rendering defect — e.g. ``sbom.SbomValidationError`` — escape uncaught to
  ``main``'s last-resort net, which discarded the already-valid report
  entirely and overrode the exit code; live-reproduced, now closed).
  Rendering and writing are two separate ``try`` blocks so the stderr
  diagnostic correctly names which phase failed; BOTH catch broadly
  (``Exception``, not just ``OSError``/``ValueError``) — an unrelated
  artifact's internal bug must degrade to a loud stderr line, never a
  silent report loss.
* ``--allow-licenses``/``--deny-licenses`` (Story 6.2, FR33): threaded into
  ``ConfigLoader().load(...)`` the SAME way ``--fail-on``/
  ``--fail-under-coverage`` already are (CLI wins over either TOML file),
  and into ``LicenseEngine(allow_licenses=..., deny_licenses=...)`` in the
  engine-instantiation loop (mirrors this same loop's pre-existing
  ``OsvEngine(fail_on_kev=...)`` special case). ``config.license_gating``
  is threaded into ``assemble_report`` for the license axis's own
  ``AxisCoverage.gating``. Story 6.5 threads ``config.license_policy``
  (the gating-aware table) through ``DefaultPolicy.evaluate`` into
  ``license_rung`` too, so a set flag now escalates the RUNG
  (denied->policy-violation / unknown->indeterminate) while
  ``license_findings`` output stays identical.
* ``--max-lag``/``--require-lts``/``--fail-on-eol`` (Story 6.3, FR35) mirror
  the license flags' treatment: threaded into ``ConfigLoader().load(...)``
  (CLI wins over either TOML file). ``config.currency_gating`` is threaded
  into ``assemble_report`` for the currency axis's own ``AxisCoverage.
  gating``, AND (Story 6.5) into ``CurrencyEngine(gating=...)`` in the
  engine-instantiation loop (mirrors this same loop's ``OsvEngine
  (fail_on_kev=...)``/``LicenseEngine(...)`` special cases) so the engine's
  NFR-S9 freshness precondition fires only under an active gate. The rung
  escalation itself is threaded through ``DefaultPolicy.evaluate``'s
  ``currency_rung(finding, policy=config.currency_policy, max_lag=config.
  max_lag)`` call — findings-generation is unchanged (the two-mode diff
  runs identical fixtures, differing only in rungs/exit). ``--max-lag`` uses
  ``_max_lag_type`` (mirrors ``_coverage_floor``'s argparse ``type=`` shape);
  ``--require-lts``/``--fail-on-eol`` are ``store_true`` flags with
  ``default=None`` (tri-state).
* ``--warn-as-error`` (Story 6.5) is a ``store_true`` flag with
  ``default=None`` (tri-state, mirrors ``--fail-on-eol``): threaded into
  ``ConfigLoader().load(...)`` as ``cli_warn_as_error`` (CLI wins over the
  ``[tool.pyforge-warden]`` ``warn-as-error`` TOML key), then ``config.
  warn_as_error`` is threaded into ``assemble_report(warn_as_error=...)`` ->
  ``verdict.exit_code_for(warn_is_error=...)``. A pure exit-projection knob:
  a composed ``warn`` status exits non-zero while the status itself stays
  ``warn`` (orthogonal to ``--warn-only``, which downgrades blocking rungs
  BEFORE the verdict composes).
* ``--min-epss`` (Story 6.7) mirrors ``--max-lag``'s treatment exactly: a
  real, two-mode CLI flag, threaded into ``ConfigLoader().load(...)`` (CLI
  wins over either TOML file) via ``_min_epss_type`` (mirrors
  ``_max_lag_type``'s argparse ``type=`` shape). ``config.min_epss`` is
  threaded into ``OsvEngine(min_epss=...)`` in the engine-instantiation loop
  (mirrors this same loop's ``fail_on_kev=...`` special case) AND into
  ``DefaultPolicy.evaluate``'s ``vuln_rung(min_epss=...)`` call (mirrors
  ``fail_on_kev``'s own threading — an at-or-above-threshold EPSS score
  forces policy-violation independent of the CVSS/KEV-derived status).
  ``epss_data`` is selected the same first-non-``None``-across-
  ``engine_results`` way ``kev_data`` is, and threaded into
  ``assemble_report(epss_data=...)``.
"""

from __future__ import annotations

import argparse
import errno as errno_module
import getpass
import os
import stat as stat_module
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .config import (
    ConfigLoader,
    ConfigParseError,
    ConfigValidationError,
    EffectiveConfig,
)
from .discovery import CONDA_LOCK_KIND, PIXI_LOCK_KIND, discover
from .engines import (
    CurrencyEngine,
    DeptryEngine,
    LicenseEngine,
    OsvEngine,
    engine_factories,
)
from .extract import UnparsableManifestError, extractor_for
from .hygiene import has_adjacent_python_source
from .interfaces import DefaultPolicy, EngineResult, _sanitize_id_segment
from .inventory import Component, ResolvedInventory, merge_components
from .models import (
    AXIS_HYGIENE,
    AXIS_INGESTION,
    EMPTY_EXTRACTION_DRIVER_ID,
    ErrorKind,
    ErrorRecord,
    Finding,
    Status,
    StatusDriver,
    SuppressedFinding,
    VulnData,
)
from .report import TOOL_NAME, assemble_report, render_json, render_text
from .routing import DefaultRouter
from .sbom import render_cyclonedx
from .verdict import EXIT_SIGINT, exit_code_for
from .waiver import (
    WaiverParseError,
    WaiverValidationError,
    apply_waivers,
    bypass_blocking,
    emit_bypass_stanza,
    load_waivers,
    warn_blocking,
)

# D2(c) empty-extraction (Story 1.9): one shared message stem for both the
# stderr notice and the paired Finding below — kept as ONE literal so a
# future wording edit can't silently drift the two apart.
_EMPTY_EXTRACTION_MESSAGE = (
    "manifest(s) parsed but zero dependencies/components extracted under "
    "{path!r}"
)

# Story 3.2: the one waiver-file name this tool ever reads, relative to the
# scan target -- never written by the tool itself (--bypass prints its
# stanza to stdout only, for a human to commit).
_WAIVER_FILENAME = ".warden-waivers.yaml"


def _coverage_floor(value: str) -> float:
    """``argparse`` ``type=`` for ``--fail-under-coverage``: a float in
    ``[0, 100]`` — an out-of-range or unparsable value is a usage error
    (argparse's own exit 2), not a scan-time ``ConfigValidationError`` (the
    CLI flag is validated at parse time, before ``ConfigLoader.load`` ever
    runs; a TOML-sourced value goes through ``config.py``'s own coercion
    instead)."""
    try:
        numeric = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--fail-under-coverage must be a number in [0, 100], got {value!r}"
        ) from None
    if not (0.0 <= numeric <= 100.0):
        raise argparse.ArgumentTypeError(
            f"--fail-under-coverage must be in [0, 100], got {value!r}"
        )
    return numeric


def _max_lag_type(value: str) -> int:
    """``argparse`` ``type=`` for ``--max-lag`` (Story 6.3): a non-negative
    int — mirrors ``_coverage_floor``'s shape exactly (an out-of-range or
    unparsable value is a usage error, argparse's own exit 2, never
    reaching ``ConfigLoader.load``/``ConfigValidationError``)."""
    try:
        numeric = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--max-lag must be a non-negative integer, got {value!r}"
        ) from None
    if numeric < 0:
        raise argparse.ArgumentTypeError(
            f"--max-lag must be a non-negative integer, got {value!r}"
        )
    return numeric


def _min_epss_type(value: str) -> float:
    """``argparse`` ``type=`` for ``--min-epss`` (Story 6.7): a number in
    ``[0.0, 1.0]`` — mirrors ``_max_lag_type``'s shape exactly (an
    out-of-range or unparsable value is a usage error, argparse's own exit
    2, never reaching ``ConfigLoader.load``/``ConfigValidationError``)."""
    try:
        numeric = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--min-epss must be a number in [0, 1], got {value!r}"
        ) from None
    if not (0.0 <= numeric <= 1.0):
        raise argparse.ArgumentTypeError(
            f"--min-epss must be a number in [0, 1], got {value!r}"
        )
    return numeric


def _build_parser() -> tuple[argparse.ArgumentParser, argparse.ArgumentParser]:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description=(
            "Unified dependency-hygiene + vulnerability scanner emitting one "
            "schema-validated ComplianceReport and a strict exit-code gate."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser(
        "scan", help="scan a project directory and emit the compliance report"
    )
    scan.add_argument(
        "path",
        nargs="?",
        default=".",
        help="target directory to scan (default: current directory)",
    )
    scan.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help=(
            "output format: 'json' emits the ComplianceReport document "
            "(the contract) on stdout; 'text' emits one non-contract "
            "summary line (default: text)"
        ),
    )
    scan.add_argument(
        "--sbom-output",
        metavar="PATH",
        default=None,
        help=(
            "write a schema-valid CycloneDX 1.6 SBOM to PATH, as an "
            "independent sibling artifact alongside the report -- a "
            "rendering or write failure is a non-fatal stderr diagnostic "
            "and never alters the scan's exit code or suppresses the "
            "report"
        ),
    )
    scan.add_argument(
        "--deterministic",
        action="store_true",
        help=(
            "byte-identical output mode — currently a documented no-op: the "
            "report carries no volatile fields yet, so default output is "
            "already byte-identical (volatile-field pinning arrives with "
            "determinism.py)"
        ),
    )
    scan.add_argument(
        "--allow-empty",
        action="store_true",
        help=(
            "downgrade the exit code to 0 when at least one manifest "
            "parses but extraction yields zero components/findings/errors "
            "(D2(c)) — status stays 'indeterminate', never 'clean', and "
            "coverage still records no resolution-depth claim"
        ),
    )
    scan.add_argument(
        "--fail-on",
        choices=("critical", "high", "medium", "low", "none"),
        default=None,
        help=(
            "the vulnerability-axis severity tier at-or-above which a "
            "finding composes 'policy-violation' rather than 'warn' "
            "(default: critical — overrides any [tool.pyforge-warden] "
            "fail-on config value)"
        ),
    )
    scan.add_argument(
        "--fail-under-coverage",
        type=_coverage_floor,
        default=None,
        help=(
            "per-axis coverage floor, 0-100 (default: 0/off) — an axis "
            "whose deps_assessed/deps_total*100 falls below this composes "
            "one 'indeterminate' rung (overrides any [tool.pyforge-warden] "
            "fail-under-coverage config value)"
        ),
    )
    scan.add_argument(
        "--allow-licenses",
        default=None,
        metavar="SPDX_IDS",
        help=(
            "comma-separated SPDX license id allow-list; a resolved "
            "component license NOT in this list is denied (overrides any "
            "[tool.pyforge-warden] allow-licenses config value) -- "
            "activates license-axis gating (FR33): a denied verdict composes "
            "'policy-violation' (exit 1) and an unresolvable license composes "
            "'indeterminate' (Story 6.5)"
        ),
    )
    scan.add_argument(
        "--deny-licenses",
        default=None,
        metavar="SPDX_IDS",
        help=(
            "comma-separated SPDX license id deny-list; a resolved "
            "component license IN this list is denied, taking priority "
            "over --allow-licenses (overrides any [tool.pyforge-warden] "
            "deny-licenses config value) -- activates license-axis gating "
            "(FR33): a denied verdict composes 'policy-violation', an "
            "unresolvable license composes 'indeterminate' (Story 6.5)"
        ),
    )
    scan.add_argument(
        "--max-lag",
        type=_max_lag_type,
        default=None,
        metavar="N",
        help=(
            "the currency-axis releases-behind-latest threshold, a "
            "non-negative integer (overrides any [tool.pyforge-warden] "
            "max-lag config value) -- activates currency-axis gating "
            "(FR35). The gate now ENFORCES this threshold (Story 6.5): an "
            "over-lag finding whose lag EXCEEDS N composes 'policy-violation' "
            "(exit 1); an over-lag at or below N stays 'warn' (visible, not "
            "blocking). An 'eol' verdict blocks regardless of N; 'unknown' "
            "composes 'indeterminate'"
        ),
    )
    scan.add_argument(
        "--require-lts",
        action="store_true",
        default=None,
        help=(
            "require an LTS-policy currency resolution where one exists "
            "(overrides any [tool.pyforge-warden] require-lts config "
            "value) -- activates currency-axis gating (FR35): an 'eol' "
            "verdict composes 'policy-violation', 'unknown' composes "
            "'indeterminate' (Story 6.5). Note: this flag only ACTIVATES the "
            "generic gate; it performs no LTS-specific enforcement -- the "
            "frozen v1 schema carries no per-component LTS boolean, so "
            "blocking on a non-LTS resolution is unexpressible (a documented "
            "carried limitation)"
        ),
    )
    scan.add_argument(
        "--fail-on-eol",
        action="store_true",
        default=None,
        help=(
            "block on an eol currency verdict (overrides any "
            "[tool.pyforge-warden] fail-on-eol config value) -- activates "
            "currency-axis gating (FR35): an 'eol' verdict composes "
            "'policy-violation' (exit 1) and 'unknown' composes "
            "'indeterminate' (Story 6.5)"
        ),
    )
    scan.add_argument(
        "--warn-as-error",
        action="store_true",
        default=None,
        help=(
            "make a composed 'warn' status exit non-zero (the strict-shop "
            "on-ramp, Story 6.5) -- overrides any [tool.pyforge-warden] "
            "warn-as-error config value. A pure exit-projection knob: it "
            "never changes the composed status or any rung (status stays "
            "'warn'), only its exit code. Orthogonal to --warn-only, which "
            "instead DOWNGRADES blocking rungs to warn before the verdict "
            "composes"
        ),
    )
    scan.add_argument(
        "--min-epss",
        type=_min_epss_type,
        default=None,
        metavar="N",
        help=(
            "the FIRST.org EPSS exploit-probability threshold, a number in "
            "[0, 1] (overrides any [tool.pyforge-warden] min-epss config "
            "value) -- activates EPSS consultation (Story 6.7): a "
            "vulnerability finding whose EPSS score is AT OR ABOVE N "
            "composes 'policy-violation' (exit 1), independent of its own "
            "CVSS tier; a score below N leaves CVSS/KEV-only gating "
            "untouched. An absent or stale EPSS feed while this is set "
            "composes at least 'indeterminate' (exit 1; a stale feed's "
            "still-matchable scores may escalate further, to "
            "'policy-violation') -- never a silent pass"
        ),
    )
    scan.add_argument(
        "--bypass",
        action="store_true",
        help=(
            "force every still-non-clean finding to 'bypassed' and print a "
            ".warden-waivers.yaml-ready stanza to stdout for a human to "
            "commit (requires --reason; never writes into the scanned "
            "tree)"
        ),
    )
    scan.add_argument(
        "--reason",
        default=None,
        help=(
            "the waiver reason recorded in the --bypass stanza (required "
            "alongside --bypass; no prompts, ever)"
        ),
    )
    scan.add_argument(
        "--warn-only",
        action="store_true",
        help=(
            "downgrade every still-blocking rung ('policy-violation'/"
            "'indeterminate') to 'warn' before the verdict composes -- "
            "never a tool error -- a non-blocking on-ramp for adopting "
            "the gate over a repo's pre-existing findings (FR23). The "
            "composed status/exit code are unaffected by --fail-on while "
            "this is set (only dropping --warn-only re-enables "
            "enforcement); --fail-on still decides which findings compose "
            "'policy-violation' before this downgrade runs, so the text "
            "report's downgraded-finding count can still differ across "
            "--fail-on values even when the final status/exit code do not. "
            "Composed with --warn-as-error (flag or TOML), the downgraded "
            "'warn' still exits 1: warn-as-error projects ANY composed warn "
            "non-zero"
        ),
    )
    return parser, scan


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    try:
        parser, scan_parser = _build_parser()
        try:
            args = parser.parse_args(argv)
            if args.command == "scan" and args.bypass and args.reason is None:
                # --bypass's own subparser (never the top-level parser) so
                # the usage message names 'scan', not the whole tool.
                scan_parser.error("--bypass requires --reason")
        except SystemExit as exc:
            # argparse exits itself: --version/--help -> 0, usage error -> 2
            # (never 0). Surface its code as a return value — a caught
            # variable, never an exit literal of the scan projection. A
            # non-int code (argparse never produces one under this parser
            # config) projects as an error, never an int() crash.
            if exc.code is None:
                return 0
            if isinstance(exc.code, int):
                return exc.code
            return exit_code_for(Status.ERROR)
        return _run_scan(args)
    except KeyboardInterrupt:
        # This handler wraps ALL of main — parse_args included — so no
        # interrupt window escapes as a traceback. Emission may already have
        # partially happened, so the honest claim is consumption guidance,
        # never "no report emitted".
        _stderr(
            f"{TOOL_NAME}: interrupted (SIGINT); any partial stdout must "
            "not be consumed"
        )
        return EXIT_SIGINT
    except SystemExit:
        # Exit-code sole ownership: argparse's own exits were already
        # handled at parse_args, so a SystemExit reaching here was raised
        # INSIDE the scan region — a component calling sys.exit (even
        # sys.exit(0)) must never dictate the gate's verdict. Its carried
        # code is not trusted; projected as an internal error.
        _stderr(
            f"{TOOL_NAME}: internal error: SystemExit raised inside the "
            "scan (exit-code sole-ownership violation); any partial "
            "stdout must not be consumed"
        )
        return exit_code_for(Status.ERROR)
    except Exception as exc:  # noqa: BLE001 — the last-resort net
        # An internal defect must NEVER surface as the interpreter's default
        # exit 1 (it collides with the indeterminate/policy-violation
        # projection) or as an uncaught traceback. Diagnostics to stderr;
        # stdout may hold a partial document, so the same consumption
        # guidance as SIGINT applies.
        _stderr("".join(traceback.format_exception(exc)).rstrip("\n"))
        _stderr(
            f"{TOOL_NAME}: internal error: {exc!r}; any partial stdout "
            "must not be consumed"
        )
        return exit_code_for(Status.ERROR)


def _run_scan(args: argparse.Namespace) -> int:
    if not args.path.strip():
        # "" Path-normalizes to "." — an empty/whitespace target must be
        # early-fatal, never a silent scan of the CWD.
        _stderr(
            f"{TOOL_NAME}: scan target {args.path!r} is empty — not an "
            "existing directory"
        )
        return exit_code_for(Status.ERROR)
    target = Path(args.path)
    # Explicit stat (is_dir() swallows every OSError): "could not look" is
    # diagnosed as could-not-stat, never as "not there".
    try:
        target_stat = target.stat()
    except (FileNotFoundError, NotADirectoryError):
        _stderr(
            f"{TOOL_NAME}: scan target {args.path!r} is not an existing "
            "directory"
        )
        return exit_code_for(Status.ERROR)
    except ValueError as exc:
        # A path with an embedded NUL (or otherwise unrepresentable to the OS)
        # raises ValueError, not OSError — a user-input error, not an internal
        # defect. Diagnose it here, not via main's last-resort traceback net.
        _stderr(
            f"{TOOL_NAME}: scan target {args.path!r} is not a valid path: {exc}"
        )
        return exit_code_for(Status.ERROR)
    except OSError as exc:
        _stderr(f"{TOOL_NAME}: cannot stat scan target {args.path!r}: {exc}")
        return exit_code_for(Status.ERROR)
    if not stat_module.S_ISDIR(target_stat.st_mode):
        _stderr(
            f"{TOOL_NAME}: scan target {args.path!r} exists but is not a "
            "directory"
        )
        return exit_code_for(Status.ERROR)

    components: list[Component] = []
    errors: list[ErrorRecord] = []
    rungs: list[tuple[Status, StatusDriver | None]] = []
    manifests_parsed = 0
    parsed_kinds: set[str] = set()
    # Story 3.1: config loads BEFORE discovery — DefaultPolicy/assemble_
    # report below both need the resolved EffectiveConfig, and a config
    # failure must not abort the scan (it still runs, report still emits,
    # on EffectiveConfig.default() — see config.py's module docstring for
    # the parse-vs-validation error taxonomy this maps).
    try:
        config, config_warnings = ConfigLoader().load(
            target,
            cli_fail_on=args.fail_on,
            cli_fail_under_coverage=args.fail_under_coverage,
            cli_allow_licenses=args.allow_licenses,
            cli_deny_licenses=args.deny_licenses,
            cli_max_lag=args.max_lag,
            cli_require_lts=args.require_lts,
            cli_fail_on_eol=args.fail_on_eol,
            cli_warn_as_error=args.warn_as_error,
            cli_min_epss=args.min_epss,
        )
    except (ConfigParseError, ConfigValidationError) as exc:
        # Review finding: an unrelated config-file error must not silently
        # discard an already-argparse-validated CLI flag the user
        # explicitly passed (--fail-on/--fail-under-coverage/
        # --allow-licenses/--deny-licenses/--max-lag/--require-lts/
        # --fail-on-eol/--min-epss are unrelated to WHY the TOML failed to
        # load).
        try:
            config = EffectiveConfig.default_with_cli_overrides(
                cli_fail_on=args.fail_on,
                cli_fail_under_coverage=args.fail_under_coverage,
                cli_allow_licenses=args.allow_licenses,
                cli_deny_licenses=args.deny_licenses,
                cli_max_lag=args.max_lag,
                cli_require_lts=args.require_lts,
                cli_fail_on_eol=args.fail_on_eol,
                cli_warn_as_error=args.warn_as_error,
                cli_min_epss=args.min_epss,
            )
        except ConfigValidationError:
            # Fix 5 follow-up (review finding, 2026-07-18): `exc` above may
            # ITSELF be the bad CLI flag's own error (--allow-licenses/
            # --deny-licenses have no argparse-level pre-validation, unlike
            # --fail-on/--fail-under-coverage) -- re-applying the SAME bad
            # value here raised a SECOND, uncaught ConfigValidationError,
            # misprojecting as `internal error` + a traceback instead of the
            # clean config-validation exit `exc` (recorded below, its
            # message already names the exact bad flag/value) already
            # provides. Fall back to the plain built-in default rather than
            # re-attempting a reconstruction that is already known to fail.
            config = EffectiveConfig.default()
        # Review finding: warnings gathered before the raise (e.g. a
        # malformed-but-non-fatal pixi.toml) must still reach stderr.
        for warning in exc.warnings:
            _stderr(f"{TOOL_NAME}: {warning}")
        kind = (
            ErrorKind.CONFIG_PARSE
            if isinstance(exc, ConfigParseError)
            else ErrorKind.CONFIG_VALIDATION
        )
        _record_error(
            errors,
            rungs,
            kind=kind,
            owner="config",
            subject=str(target),
            message=str(exc),
            axis=AXIS_INGESTION,
        )
    else:
        for warning in config_warnings:
            _stderr(f"{TOOL_NAME}: {warning}")
    try:
        manifests = discover(target)
    except OSError as exc:
        # Discovery propagates non-absence stat failures: a permission-denied
        # target must never read as "no manifest" (a false green). Report
        # still emitted; the exit code is orthogonal to emission.
        manifests = ()
        # An OS-minted errno is stated SYMBOLICALLY (locale-independent,
        # no strerror text, no OSError.__str__ absolute path); discovery's
        # own fail-closed OSErrors carry no errno and their crafted message
        # is already deterministic.
        detail = (
            f"[errno {errno_module.errorcode.get(exc.errno, str(exc.errno))}] "
            f"{exc.__class__.__name__}"
            if exc.errno is not None
            else str(exc)
        )
        _record_error(
            errors,
            rungs,
            kind=ErrorKind.INTERNAL_ERROR,
            owner="discovery",
            subject=args.path,
            message=f"discovery failed under {args.path!r}: {detail}",
            axis=AXIS_INGESTION,
        )
    else:
        if not manifests:
            if has_adjacent_python_source(target):
                # D2's misconfiguration guard (Story 1.9): the recursive
                # walk found NOTHING recognizable anywhere in the tree, yet
                # Python source exists — never silently "nothing to scan"
                # (exit 0); a fail-closed operational error (exit 2).
                _record_error(
                    errors,
                    rungs,
                    kind=ErrorKind.UNPARSABLE_MANIFEST,
                    owner="discovery",
                    subject=args.path,
                    message=(
                        f"no recognized manifest found under {args.path!r} "
                        "despite Python source present (D2 misconfiguration "
                        "guard)"
                    ),
                    axis=AXIS_INGESTION,
                )
            else:
                # The not-applicable path says so on stderr; stdout stays
                # pure.
                _stderr(
                    f"{TOOL_NAME}: no manifest found under {args.path!r}; "
                    "nothing to scan"
                )
    router = DefaultRouter()
    for manifest in manifests:
        try:
            # extractor_for lives INSIDE the guarded region: an unknown
            # manifest kind is an internal-error report, never a crash.
            extractor = extractor_for(manifest.kind, router)
            extracted = extractor.extract(target / manifest.path, manifest)
        except UnparsableManifestError as exc:
            _record_error(
                errors,
                rungs,
                kind=ErrorKind.UNPARSABLE_MANIFEST,
                owner="extract",
                subject=manifest.path,
                message=str(exc),
                axis=AXIS_INGESTION,
            )
        except OSError as exc:
            # Reading the manifest failed (chmod-000, TOCTOU deletion): a
            # genuine manifest problem. The errno is stated SYMBOLICALLY
            # (EACCES) — strerror text is locale-dependent and
            # OSError.__str__ embeds the absolute path; report bytes must
            # not vary by locale or scan location.
            code = (
                errno_module.errorcode.get(exc.errno, str(exc.errno))
                if exc.errno is not None
                else exc.__class__.__name__
            )
            _record_error(
                errors,
                rungs,
                kind=ErrorKind.UNPARSABLE_MANIFEST,
                owner="extract",
                subject=manifest.path,
                message=(
                    f"unreadable manifest {manifest.path}: [errno {code}] "
                    f"{exc.__class__.__name__}"
                ),
                axis=AXIS_INGESTION,
            )
        except (SystemExit, Exception) as exc:  # noqa: BLE001 — the seam
            # doctrine applies to the EXTRACTOR seam exactly as to the
            # engine seam (1.3+ plug implementations into both): any other
            # exception out of the extract/routing path — unknown manifest
            # kind (ValueError), a 1.3+ extractor bug (TypeError,
            # KeyError), even a sys.exit — is NOT a manifest problem;
            # typed internal-error record, report STILL emitted, never a
            # traceback with no report (KeyboardInterrupt still
            # propagates).
            _record_error(
                errors,
                rungs,
                kind=ErrorKind.INTERNAL_ERROR,
                owner="extract",
                subject=manifest.path,
                message=f"internal error extracting {manifest.path}: {exc!r}",
                axis=AXIS_INGESTION,
            )
        else:
            components.extend(extracted)
            manifests_parsed += 1
            parsed_kinds.add(manifest.kind)

    inventory = ResolvedInventory(
        components=merge_components(components),
        resolved_scan_set=manifests,
    )
    if manifests and manifests_parsed > 0 and not inventory.components:
        # A parsed manifest with nothing extractable must be distinguishable
        # on stderr from the empty-dir case (the coverage block already
        # distinguishes them). Manifest-kind-agnostic wording (Story 1.9):
        # this notice now accompanies D2(c)'s actual gate failure
        # (indeterminate/exit 1 by default) for ANY of the discovered
        # manifest kinds, not just pyproject.toml — naming a specific
        # section/format here would misdescribe 7 of 8 kinds.
        _stderr(
            f"{TOOL_NAME}: "
            f"{_EMPTY_EXTRACTION_MESSAGE.format(path=args.path)}; "
            "nothing to scan"
        )
    engine_results: list[EngineResult] = []
    # AC3: a source-less scan target makes deptry flag every conda-sourced
    # dependency reaching the front-door as "unused" (DEP002) -- a noise
    # wall, never a signal -- so DeptryEngine is filtered out when no
    # adjacent .py file exists anywhere under target. Computed once, up
    # front, so both the engine filter below and the assemble_report call
    # see the same value. Gated on manifests_parsed like the engine seam
    # itself below (review finding, 2026-07-17): with nothing extractable,
    # engines_to_run is already () and inventory.count is already 0, so the
    # walk's result can never affect the output -- skip the wasted I/O.
    hygiene_applicable = (
        has_adjacent_python_source(target) if manifests_parsed > 0 else True
    )
    # The engine seam runs only when a manifest actually parsed: with nothing
    # extractable (empty dir, or a manifest that failed to parse) there is no
    # project for a subprocess engine (deptry) to assess, and running it on an
    # absent/malformed manifest would only double the extractor's own error.
    engines_to_run = (
        tuple(
            factory
            for factory in engine_factories()
            if hygiene_applicable or factory is not DeptryEngine
        )
        if manifests_parsed > 0
        else ()
    )
    for factory in engines_to_run:
        try:
            # Story 6.4: OsvEngine's fail_on_kev needs the resolved config
            # value -- mirrors this same loop's pre-existing DeptryEngine
            # special case (hygiene_applicable filter above), never widening
            # the shared zero-arg Engine.run() seam every other factory
            # still uses (config.py's Design Notes). Story 6.2:
            # LicenseEngine's allow_licenses/deny_licenses need the same
            # treatment. Story 6.5: CurrencyEngine now takes gating=config.
            # currency_gating so its NFR-S9 freshness precondition (emit a
            # currency-registry-stale/unavailable finding when the bundled
            # registry can't be trusted under an active gate) fires only when
            # a currency gate is active -- gated exactly as OsvEngine's
            # fail_on_kev gates the parallel KEV-provenance finding. Story
            # 6.7: OsvEngine also takes min_epss=config.min_epss, the same
            # way -- consulted only when the gate is active.
            engine = (
                OsvEngine(fail_on_kev=config.fail_on_kev, min_epss=config.min_epss)
                if factory is OsvEngine
                else LicenseEngine(
                    allow_licenses=config.allow_licenses,
                    deny_licenses=config.deny_licenses,
                )
                if factory is LicenseEngine
                else CurrencyEngine(gating=config.currency_gating)
                if factory is CurrencyEngine
                else factory()
            )
        except (SystemExit, Exception) as exc:  # noqa: BLE001 —
            # instantiation is PART of the seam: a crashing constructor (a
            # misconfigured 1.3/1.5 runner) is the engine-unavailable
            # class — typed record + error rung, report STILL emitted,
            # never a traceback with no report.
            factory_name = getattr(factory, "__name__", repr(factory))
            # `factory` is typed as Callable[[] , Engine] (the registry's
            # shape), but every REAL factory is the engine class itself, so
            # `axis` is readable as a class attribute without instantiating
            # (mirrors `factory_name` above) — getattr, not a direct
            # attribute access, keeps mypy honest about the narrower
            # Callable type while still reading the real class attribute.
            factory_axis = getattr(factory, "axis", AXIS_INGESTION)
            _record_error(
                errors,
                rungs,
                kind=ErrorKind.ENGINE_UNAVAILABLE,
                owner="engines",
                subject=factory_name,
                message=(
                    f"engine factory {factory_name!r} crashed at "
                    f"instantiation: {exc!r}"
                ),
                axis=factory_axis,
            )
            continue
        try:
            engine_results.append(engine.run(target, inventory))
        except (SystemExit, Exception) as exc:  # noqa: BLE001 — the seam
            # doctrine: a crashing engine must yield a typed ErrorRecord +
            # error rung with the report STILL emitted, never a traceback
            # with no report — and a sys.exit-calling engine must never
            # dictate the process exit (sole ownership; SystemExit is
            # caught HERE so the report survives). KeyboardInterrupt still
            # propagates.
            engine_name = getattr(engine, "name", engine.__class__.__name__)
            _record_error(
                errors,
                rungs,
                kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                owner=engine_name,
                subject=engine_name,
                message=f"engine {engine_name!r} crashed: {exc!r}",
                axis=engine.axis,
            )
    for result in engine_results:
        errors.extend(result.errors)
    findings, policy_rungs = DefaultPolicy(config).evaluate(inventory, engine_results)
    if not hygiene_applicable:
        # AC3 (review finding, 2026-07-17): DefaultPolicy derives a
        # per-component `indeterminate:uncovered:<pkg>` (axis=hygiene)
        # finding from `component.hygiene_covered` alone -- independent of
        # whether any engine ran -- so a RAW_MALFORMED component still
        # produced a hygiene-axis finding even though the axis's own
        # AxisCoverage now honestly claims deps_total=0 (verified live: a
        # source-less manifest with an unresolvable dep reported
        # `hygiene: deps_total=0` alongside a `hygiene`-axis finding, a
        # self-contradiction the not-applicable claim must not carry).
        # Safe to drop unconditionally: a component whose name/version
        # extraction failed badly enough to be hygiene-uncovered also has
        # no resolved identity+version, so it independently produces its
        # own vulnerability-axis indeterminate signal -- this filter never
        # removes the sole driver of a non-clean verdict.
        findings = tuple(f for f in findings if f.axis != AXIS_HYGIENE)
        policy_rungs = tuple(
            (status, driver)
            for status, driver in policy_rungs
            if driver is None or driver.axis != AXIS_HYGIENE
        )
    rungs.extend(policy_rungs)

    # D2(c) (Story 1.9): at least one manifest parsed but the whole scan fed
    # ZERO rungs (no components, no engine findings, no errors) — ambiguous/
    # partial discovery, never a silent clean/not-applicable. A paired
    # Finding is added (not just a driver) so the ratified Story 1.7
    # two-namespace contract holds (every non-error status driver must
    # reference an emitted finding). The id is the FIXED literal
    # EMPTY_EXTRACTION_DRIVER_ID (models.py; verdict.py's exit_code_for and
    # ComplianceReport.__post_init__ both match it EXACTLY, never a prefix)
    # -- this driver is whole-scan-scoped, not per-package, and the id must
    # stay invocation-stable (`warden scan .` vs `warden scan <absolute
    # path>` are the SAME condition).
    empty_extraction = manifests_parsed > 0 and not rungs
    if empty_extraction:
        findings = (
            *findings,
            Finding(
                id=EMPTY_EXTRACTION_DRIVER_ID,
                axis=AXIS_INGESTION,
                message=_EMPTY_EXTRACTION_MESSAGE.format(path=args.path),
                subject=args.path,
                severity=None,
            ),
        )
        rungs.append(
            (
                Status.INDETERMINATE,
                StatusDriver(
                    axis=AXIS_INGESTION, finding_id=EMPTY_EXTRACTION_DRIVER_ID
                ),
            )
        )

    # Story 3.2 (FR24-FR26): a missing waiver file is normal (empty tuple,
    # no error) -- mirrors config.py's own missing-file handling. A
    # malformed/schema-invalid one is fail-closed: zero waivers apply, and
    # a typed error rung/record surfaces via the SAME _record_error seam
    # every other ingestion-stage failure uses.
    try:
        waivers = load_waivers(target / _WAIVER_FILENAME)
    except (WaiverParseError, WaiverValidationError) as exc:
        waivers = ()
        _record_error(
            errors,
            rungs,
            kind=(
                ErrorKind.CONFIG_PARSE
                if isinstance(exc, WaiverParseError)
                else ErrorKind.CONFIG_VALIDATION
            ),
            owner="waiver",
            subject=str(target),
            message=str(exc),
            axis=AXIS_INGESTION,
        )
    now = datetime.now(UTC)
    rungs, applied_waivers, expired_waivers = apply_waivers(rungs, waivers, now=now)
    # Story 6.1: echo each applied waiver into the JSON contract's
    # suppressions[] (WaiverNotice -> SuppressedFinding, origin="waiver").
    # Until now applied waivers echoed in --format text only; the baseline
    # half (origin="baseline") is Story 6.8. Every notice.id exact-matched a
    # blocking rung's driver.finding_id, which references a real findings[]
    # entry, so ComplianceReport's suppressions[]<->findings[] cross-check holds.
    suppressions = tuple(
        SuppressedFinding(
            finding_id=notice.id,
            origin="waiver",
            reason=notice.reason,
            authorized_by=notice.authorized_by,
            expires_at=notice.expires_at,
        )
        for notice in applied_waivers
    )
    bypass_stanza: str | None = None
    if args.bypass:
        try:
            authorized_by = getpass.getuser()
        except Exception:  # noqa: BLE001 — no CLI flag exists for this;
            # fall back rather than let an unusual host environment
            # (no /etc/passwd entry, no *_NAME env vars) crash the scan.
            authorized_by = "unknown"
        bypass_stanza = emit_bypass_stanza(
            rungs,
            reason=args.reason,
            authorized_by=authorized_by,
            accepted_at=now,
            expiry_days=config.waiver_default_expiry_days,
        )
        rungs = bypass_blocking(rungs)

    # Story 3.3 (FR23/FR25): --warn-only runs AFTER apply_waivers/--bypass
    # above -- a waiver still shows as bypassed distinctly, and warn-only
    # only mops up whatever is still blocking (policy-violation/
    # indeterminate, never error). warn_only_downgraded is threaded into
    # render_text's nudge below -- the nudge's exact count, never the
    # report's total finding count.
    warn_only_downgraded = 0
    if args.warn_only:
        rungs, warn_only_downgraded = warn_blocking(rungs)

    # The first non-None vuln_data across engine results, in engine-
    # registration order (Story 1.5: OsvEngine populates it on a completed
    # 0/1 run; every other engine/path leaves it None) — else an all-None
    # VulnData (no vulnerability-axis DB was consulted at all).
    vuln_data = next(
        (result.vuln_data for result in engine_results if result.vuln_data is not None),
        VulnData(source=None, snapshot_at=None, max_age_ok=None),
    )
    # Story 6.4: the same first-non-None-across-engine-results selection
    # vuln_data already uses above -- OsvEngine populates kev_data only when
    # fail_on_kev is active and the KEV feed was actually consulted; every
    # other engine/path leaves it None (mirrors vuln_data's own None-when-
    # never-consulted default).
    kev_data = next(
        (result.kev_data for result in engine_results if result.kev_data is not None),
        None,
    )
    # Story 6.7: the same first-non-None-across-engine-results selection
    # kev_data/vuln_data already use -- OsvEngine populates epss_data only
    # when min_epss is set and the FIRST.org EPSS feed was actually
    # consulted; every other engine/path leaves it None (mirrors kev_data's
    # own fail_on_kev-gated default).
    epss_data = next(
        (result.epss_data for result in engine_results if result.epss_data is not None),
        None,
    )
    # Story 6.3: the same first-non-None-across-engine-results selection
    # kev_data/vuln_data already use -- no CLI/config gating flag disables
    # CurrencyEngine's own attempt to populate currency_data (unlike
    # kev_data's fail_on_kev gate above). That does NOT mean currency_data
    # is always non-None, though: currency_findings() itself returns
    # currency_data=None whenever the bundled registry can't yield a
    # trustworthy FeedProvenance -- the registry file is absent/unreadable/
    # unparsable YAML (_load_registry degrades to {}), OR it loads fine but
    # its own `updated:` date is missing/unparsable (_registry_feed_
    # provenance's own None return). A None currency_data here does not by
    # itself distinguish "no currency policy is active" from "the shipped
    # registry file has a problem" -- every other engine/path also leaves
    # it None, so this slot alone can't tell the two apart.
    currency_data = next(
        (
            result.currency_data
            for result in engine_results
            if result.currency_data is not None
        ),
        None,
    )
    report = assemble_report(
        inventory=inventory,
        findings=findings,
        rungs=rungs,
        errors=tuple(errors),
        manifests_found=len(manifests),
        manifests_parsed=manifests_parsed,
        vuln_data=vuln_data,
        engine_results=engine_results,
        has_locked_closure=bool(parsed_kinds & {PIXI_LOCK_KIND, CONDA_LOCK_KIND}),
        hygiene_applicable=hygiene_applicable,
        allow_empty=args.allow_empty,
        empty_extraction=empty_extraction,
        fail_under_coverage=config.fail_under_coverage,
        suppressions=suppressions,
        kev_data=kev_data,
        epss_data=epss_data,
        license_gating=config.license_gating,
        currency_data=currency_data,
        currency_gating=config.currency_gating,
        warn_as_error=config.warn_as_error,
    )
    if args.sbom_output is not None:
        # Story 4.1: an independent sibling artifact -- rendering and
        # writing are separate try blocks (own module docstring) so
        # NEITHER can suppress the already-assembled report below or
        # alter report.exit_code; both catch broadly (Exception), not
        # just OSError/ValueError -- a rendering defect must degrade to
        # a loud stderr line, never a silent report loss.
        try:
            rendered_sbom = render_cyclonedx(inventory, report)
        except Exception as exc:
            _stderr(
                f"{TOOL_NAME}: --sbom-output rendering failed "
                f"({exc.__class__.__name__}): {exc}"
            )
        else:
            try:
                Path(args.sbom_output).write_text(rendered_sbom, encoding="utf-8")
            except OSError as exc:
                _stderr(
                    f"{TOOL_NAME}: --sbom-output write to "
                    f"{args.sbom_output!r} failed "
                    f"({exc.__class__.__name__}): {exc}"
                )
    try:
        if args.format == "json":
            # NFR-I3 (Story 1.2, unchanged by this story): json-format
            # stdout carries EXACTLY one schema-valid document or nothing --
            # the stanza is a human-facing affordance (something to copy
            # into a committed .warden-waivers.yaml) that would otherwise
            # corrupt that guarantee for a machine consumer. The report
            # itself already reflects the bypass fully (status=bypassed,
            # exit_code=0); the stanza text itself still goes to stderr
            # (review finding: silently dropping it entirely would leave a
            # json-consuming caller with no way to recover the waiver text
            # to commit) -- stderr carries no such purity contract.
            if bypass_stanza is not None:
                _stderr(bypass_stanza.rstrip("\n"))
            sys.stdout.write(render_json(report) + "\n")
        else:
            if bypass_stanza is not None:
                # Printed BEFORE the report itself, for a human to copy
                # into a committed .warden-waivers.yaml -- the tool never
                # writes it into the scanned tree.
                sys.stdout.write(bypass_stanza)
            sys.stdout.write(
                render_text(
                    report,
                    applied_waivers=applied_waivers,
                    expired_waivers=expired_waivers,
                    warn_only=args.warn_only,
                    warn_only_downgraded=warn_only_downgraded,
                )
                + "\n"
            )
        # Flush INSIDE the guarded region: on a block-buffered pipe whose
        # consumer vanished, the BrokenPipeError must surface HERE (absorbed
        # below) — not at interpreter-exit flush (CPython exit 120).
        sys.stdout.flush()
    except BrokenPipeError:
        _absorb_broken_pipe()
    except (OSError, ValueError) as exc:
        # A non-EPIPE stdout failure is environmental, not an internal defect:
        # the verdict is already computed and must NOT be replaced by the
        # error exit or misdiagnosed as an internal error. Two families:
        #   * OSError (ENOSPC full disk, EIO hung-up terminal), and
        #   * ValueError ("I/O operation on closed file") — an in-process
        #     embedder that closed/replaced sys.stdout, the exact swapped-
        #     stream case _absorb_broken_pipe supports. CPython raises
        #     ValueError, not OSError, for a closed stream, so it must be
        #     caught here or it escapes to main's last-resort net and
        #     overrides the verdict with exit 2 (exit-code sole-ownership
        #     violation). Stdout may hold a partial document — same
        #     consumption guidance as SIGINT.
        _stderr(
            f"{TOOL_NAME}: stdout emission failed "
            f"({exc.__class__.__name__}); any partial stdout must not be "
            "consumed"
        )
    return report.exit_code


def _record_error(
    errors: list[ErrorRecord],
    rungs: list[tuple[Status, StatusDriver | None]],
    *,
    kind: ErrorKind,
    owner: str,
    subject: str,
    message: str,
    axis: str,
) -> None:
    """Surface one operational error: typed record + error rung + stderr
    diagnostic. The rung's driver id uses the ``error:<kind>:<subject>``
    grammar and deliberately does NOT reference ``findings[]`` (see the
    module docstring; Story 1.7 ratified this as the final grammar). The
    caller states ``axis`` — the actually-failing stage/engine
    (``AXIS_INGESTION`` for a pre-engine discovery/extract/routing failure,
    or the crashing engine's/factory's own axis) — never a blanket default.
    The subject segment is sanitized like every component-derived id
    segment — the id grammar is single-line by contract even when the
    subject is a user-supplied path."""
    errors.append(ErrorRecord(kind=kind, owner=owner, message=message))
    rungs.append(
        (
            Status.ERROR,
            StatusDriver(
                axis=axis,
                finding_id=f"error:{kind}:{_sanitize_id_segment(subject)}",
            ),
        )
    )
    _stderr(f"{TOOL_NAME}: {message}")


def _stderr(message: str) -> None:
    """Print one stderr diagnostic, absorbing ANY stream failure — a
    vanished consumer raises ``OSError``, but a CLOSED stderr raises
    ``ValueError`` from ``print``. This helper runs INSIDE exception
    handlers (the SIGINT/SystemExit/last-resort nets), where a raise would
    escape ``main`` as an uncaught traceback with interpreter exit 1 —
    the exact exit-1 collision the module docstring forbids. A diagnostic
    stream failure must never replace the computed exit code.

    ``sys.stderr is None`` (pythonw / GUI / embedded hosts) is guarded
    explicitly: ``print(..., file=None)`` falls back to ``sys.stdout`` and
    would leak the diagnostic onto the contract stdout (NFR-I3) WITHOUT
    raising, so the try/except cannot catch it — drop the diagnostic
    instead."""
    try:
        if sys.stderr is not None:
            print(message, file=sys.stderr)
    except Exception:  # noqa: BLE001 — see docstring: absorb everything
        pass


def _absorb_broken_pipe() -> None:
    """The stdout consumer vanished mid-emission (e.g. ``| head``): the
    verdict's exit code is already computed, so the pipe error is absorbed —
    never a traceback.

    Process-stream path (``sys.stdout`` IS ``sys.__stdout__``): fd 1 is
    re-pointed at ``os.devnull`` so the interpreter's exit-time flush
    cannot raise a second BrokenPipeError (CPython exit 120). This is a
    PROCESS-GLOBAL redirect — correct for the console script (about to
    exit) and documented for in-process embedders sharing the real stream:
    their pipe is equally dead, and the redirect trades EPIPE-on-every-
    later-write for silence.

    Swapped-stream path (test captures, embedders that replaced
    ``sys.stdout``): the broken stream OBJECT is closed instead — fd 1 is
    left alone, exit-time flush skips a closed stream, and a later write
    through the object fails LOUD (``ValueError``) rather than vanishing
    into a silent process-wide devnull redirect."""
    stream = sys.stdout
    if stream is sys.__stdout__:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            try:
                os.dup2(devnull, stream.fileno())
            finally:
                os.close(devnull)
        except (OSError, ValueError, AttributeError):
            # No usable descriptor behind the stream (AttributeError = a
            # fileno-less stream object aliased onto sys.__stdout__): nothing
            # will flush at interpreter exit, nothing to do.
            pass
        return
    try:
        stream.close()
    except Exception:  # noqa: BLE001 — best effort: the absorber must
        # never raise (a fake test stream may lack close(), or close's
        # final flush re-raises the pipe error).
        pass


if __name__ == "__main__":
    raise SystemExit(main())
