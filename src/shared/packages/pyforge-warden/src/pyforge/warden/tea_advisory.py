"""``tea-test-review`` is a warden advisory finding (Story 11.2, AD-4).

Wraps steward 46.3's ``tea-test-review`` pixi task (TEA's headless
test-review CLI, ``bmad-method-test-architecture-enterprise``) as a
fail-open advisory lens beside Warden's compliance gate: the score and
findings are surfaced, but they NEVER move a rung, the composed status, or
the exit code (AD-4: advisory lenses never gate). The scanner is optional
-- registered in ``scanner_plugins.OPTIONAL_SCANNER_IDS``, enabled only via
``WARDEN_OPTIONAL_SCANNERS=tea-test-review`` -- because a present
``tea-test-review`` binary spawns a real (possibly LLM-backed) review
process; it must never run in the default bundle or inside this repo's own
test suite.

Fail-open contract: ANY subprocess/parse/binary problem (a PROVISIONED tool
whose binary happens to be absent from PATH, non-zero exit, timeout,
malformed JSON, an unreadable ``--json`` file) degrades to
``TeaAdvisoryResult(ran=False, ...)`` -- never raises, and
``TeaAdvisoryScanPlugin.call`` never raises either for any of THOSE cases
(belt-and-suspenders: a defect in this module must never crash a PR-gate
scan).

Fail-CLOSED exception -- ``TeaRosterMissingError`` (AD-10, resolved
2026-09-07, DW-FU-11-2): "31.1 / 11.2 refuse when the AD-9 roster lacks
tea" is architecture-mandated and distinct in KIND from the fail-open cases
above. When the scanner is explicitly enabled
(``WARDEN_OPTIONAL_SCANNERS=tea-test-review``) but the AD-9 module roster
(``target/_bmad/custom/config.toml``'s ``[modules.tea]`` table) has no
``tea`` entry at all, that is not an environmental blip -- it means
``steward provision --module tea`` never ran here, i.e. this station never
adopted the tool the operator just asked it to run. A compliance-adjacent
scanner must not paper over that with a silent no-op (the same reasoning
this repo applies to an unauthenticated GitHub probe failing open as
"ok" -- see ``feedback_unauthenticated_github_probes_fail_open``): it
refuses loudly instead, via ``run_tea_test_review`` raising
``TeaRosterMissingError``, which ``TeaAdvisoryScanPlugin._contribute``
deliberately does NOT swallow (unlike every other exception) so it
propagates out of the PR-gate scan; ``cli.py``'s ``_run_scan`` records it
as a ``CONFIG_VALIDATION`` error (the same treatment
``select_scanner_plugins``'s ``PluginError`` already gets), a real ERROR
rung -- never AD-4's advisory-lens exit-code exemption, because this is a
tool-misconfiguration refusal, not a scored finding about the scanned
code. A roster entry that DOES name ``tea`` but whose binary is merely not
on THIS process's PATH remains fail-open exactly as before -- that is the
environmental case AD-10 does not govern.

Testing seam: ``run_tea_test_review``'s ``runner`` parameter replaces the
ENTIRE default-resolution path -- both the AD-9 roster check and the
``shutil.which`` presence probe run only when ``runner is None``; an
injected ``runner`` stands in for "TEA is present and behaves this way",
bypassing both checks. The "TEA roster missing" / "binary absent" fail-open
scenarios therefore exercise the real roster/PATH probes directly (no
stub); the "low score" / "runner errors" scenarios inject a ``runner``
that writes (or fails to write) the ``--json`` file directly, without ever
resolving or spawning the real binary.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import tempfile
import tomllib
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from pyforge.core.errors import PyforgeError

from .hooks import PR_GATE_SCAN

TEA_TEST_REVIEW_BINARY = "tea-test-review"

# steward 46.3's own pixi task defaults ("tea-test-review --base origin/main
# --min-score 80") -- this module never gates on --min-score (AD-4: the
# advisory contributes a note, never a verdict), so it is deliberately not
# passed here. --agent claude mirrors the CLI's own documented default.
_DEFAULT_BASE_REF = "origin/main"
_DEFAULT_AGENT = "claude"
_DEFAULT_TIMEOUT_SECONDS = 1800  # mirrors the CLI's own --timeout-ms default

# The low-level runner seam: (target, json_path) -> a CompletedProcess (or
# None -- the return value itself is never consulted, only whatever the
# runner left at json_path). A fake test runner writes its canned JSON
# verdict to json_path as its only required side effect.
TeaRunner = Callable[[Path, Path], "subprocess.CompletedProcess[str] | None"]


class TeaRosterMissingError(PyforgeError, RuntimeError):
    """Raised by ``run_tea_test_review`` (default-resolution path only --
    ``runner is None``) when the AD-9 module roster
    (``target/_bmad/custom/config.toml``'s ``[modules.tea]`` table) has no
    ``tea`` entry at all. Fail-CLOSED by architecture mandate (AD-10:
    "31.1 / 11.2 refuse when the AD-9 roster lacks tea", resolved
    2026-09-07 per DW-FU-11-2) -- distinct from the fail-open case where the
    roster DOES carry ``tea`` but the binary is merely absent from THIS
    process's PATH (an environmental blip, not a governance gap).
    Deliberately NOT caught by ``TeaAdvisoryScanPlugin``'s
    belt-and-suspenders fail-open net -- it must propagate out of the
    PR-gate scan so ``cli.py`` can record it as a loud ``CONFIG_VALIDATION``
    error rather than a silent no-op.

    Story 52.1, SPEC-pyforge-core CAP-5: gains ``PyforgeError`` as an
    additional base -- ``RuntimeError`` stays in the MRO."""


def _ad9_roster_has_tea(target: Path) -> bool:
    """Read the AD-9 module roster exactly as ``engines._doctor_check_tea``
    does: ``target/_bmad/custom/config.toml``'s ``[modules.tea]`` table,
    written by ``steward provision --module tea``. A missing, unreadable,
    or malformed config file degrades to "no roster entry" -- the same
    fail-open posture ``_doctor_check_tea`` uses for I/O problems; only a
    CONFIRMED absent ``tea`` key in an actually-readable roster reports
    ``False`` here with any confidence, but either way this function never
    raises (the raising happens one level up, deliberately, in
    ``run_tea_test_review``)."""
    config_path = target / "_bmad" / "custom" / "config.toml"
    if not config_path.is_file():
        return False
    try:
        with config_path.open("rb") as handle:
            document = tomllib.load(handle)
    except OSError, tomllib.TOMLDecodeError, UnicodeDecodeError:
        return False
    modules = document.get("modules")
    return isinstance(modules, Mapping) and "tea" in modules


@dataclass(frozen=True, slots=True)
class TeaAdvisoryResult:
    """One ``tea-test-review`` run's advisory outcome. Never a ``Finding``:
    this result flows only into ``context["advisory_notes"]``, never
    ``context["plugin_findings"]`` -- it cannot move a rung, the composed
    status, or the exit code."""

    ran: bool
    score: int | None
    recommendation: str | None
    summary: str
    skipped_reason: str | None


def _default_runner(binary: str, target: Path, json_path: Path) -> subprocess.CompletedProcess[str]:
    """Shell out to the real ``tea-test-review`` binary. Both the markdown
    report and the JSON verdict are written into ``json_path``'s own
    scratch directory -- never into ``target`` -- an advisory scanner must
    not litter the scanned tree with a stray ``test-review.md``. NEVER
    exercised inside this repo's own test suite: the "TEA absent" test
    relies on the real absent binary, and the "low score"/"runner errors"
    tests inject their own ``runner`` instead."""
    report_path = json_path.with_name("test-review.md")
    return subprocess.run(
        [
            binary,
            "--base",
            _DEFAULT_BASE_REF,
            "--output",
            str(report_path),
            "--json",
            str(json_path),
            "--agent",
            _DEFAULT_AGENT,
        ],
        cwd=target,
        capture_output=True,
        text=True,
        timeout=_DEFAULT_TIMEOUT_SECONDS,
        check=False,
    )


def run_tea_test_review(
    target: Path,
    *,
    runner: TeaRunner | None = None,
) -> TeaAdvisoryResult:
    """Wrapper over the ``tea-test-review`` CLI -- fail-open for an
    environmental problem, fail-CLOSED for a governance gap (AD-10).

    No ``runner`` injected (the real default-resolution path): the AD-9
    roster is checked FIRST -- a roster with no ``tea`` entry at all raises
    ``TeaRosterMissingError`` (never caught by this function; it is meant
    to propagate) regardless of whether a same-named binary happens to be
    reachable on PATH anyway (a leaked/ambient copy from an unrelated
    environment is exactly the ungoverned state AD-10 refuses, not a reason
    to proceed). Only once the roster confirms ``tea`` is provisioned does
    an absent binary degrade to the ordinary fail-open ``ran=False`` (no
    subprocess spawned) -- that combination is a transient environmental
    gap, not a governance one. A present binary that errors (an exit code
    outside ``{0, 1}``, a timeout, no/garbled ``--json`` output) ALSO
    degrades to ``ran=False`` -- the advisory contract for an environmental
    problem is "contribute nothing, never error", not "assume the tool
    works". Exit 0 and exit 1 are BOTH trusted (``test-review.js``'s own
    documented semantics: exit 1 is a legitimate "verdict fail" -- a real
    score below ``--min-score`` -- never a subprocess failure); only an
    exit code outside that pair is treated as untrusted, regardless of
    whatever JSON happens to exist at ``json_path``. A
    ``{"skipped": true, ...}`` or ``{"promptOnly": true, ...}`` verdict
    (the CLI's own documented shapes for "no changed test files" /
    ``--agent none``) is likewise treated as nothing-to-report, not a
    failure.
    """
    if runner is None:
        if not _ad9_roster_has_tea(target):
            raise TeaRosterMissingError(
                "tea-test-review: the AD-9 module roster "
                "(_bmad/custom/config.toml [modules.tea]) has no `tea` "
                "entry -- run `steward provision --module tea` before "
                "enabling WARDEN_OPTIONAL_SCANNERS=tea-test-review "
                "(AD-10: an unprovisioned tool refuses loudly; a "
                "provisioned tool merely absent from this process's PATH "
                "still fails open)"
            )
        binary = shutil.which(TEA_TEST_REVIEW_BINARY)
        if binary is None:
            return TeaAdvisoryResult(
                ran=False,
                score=None,
                recommendation=None,
                summary="",
                skipped_reason=f"{TEA_TEST_REVIEW_BINARY} not found on PATH",
            )
        active_runner: TeaRunner = partial(_default_runner, binary)
    else:
        active_runner = runner
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = Path(tmp_dir) / "tea-test-review.json"
            completed = active_runner(target, json_path)
            # test-review.js's own documented semantics: exit 0 = clean pass,
            # exit 1 = a legitimate "verdict fail" (score below --min-score)
            # carrying a real, trustworthy score -- neither is a subprocess
            # failure. Any OTHER exit code is untrusted (defense in depth,
            # belt-and-suspenders per the module docstring): whatever JSON
            # happens to exist at json_path is not read at all.
            if completed is not None and completed.returncode not in (0, 1):
                raise RuntimeError(f"tea-test-review exited {completed.returncode} -- verdict not trusted")
            with json_path.open("r", encoding="utf-8") as handle:
                raw: Any = json.load(handle)
    except Exception as exc:  # noqa: BLE001 -- fail-open: any runner/parse
        # failure (missing binary side effect, non-zero exit that wrote no
        # file, a timeout, invalid JSON, ...) is "skipped", never raised.
        return TeaAdvisoryResult(
            ran=False,
            score=None,
            recommendation=None,
            summary="",
            skipped_reason=(f"tea-test-review run failed: {type(exc).__name__}: {exc}"),
        )
    if not isinstance(raw, Mapping):
        return TeaAdvisoryResult(
            ran=False,
            score=None,
            recommendation=None,
            summary="",
            skipped_reason="tea-test-review produced a non-object verdict",
        )
    if raw.get("skipped") or raw.get("promptOnly"):
        reason = raw.get("reason")
        return TeaAdvisoryResult(
            ran=False,
            score=None,
            recommendation=None,
            summary="",
            skipped_reason=(str(reason) if reason else "tea-test-review reported nothing to review"),
        )
    score_raw = raw.get("qualityScore")
    score = (
        int(score_raw)
        if isinstance(score_raw, (int, float)) and not isinstance(score_raw, bool) and math.isfinite(score_raw)
        else None
    )
    recommendation_raw = raw.get("recommendation")
    recommendation = str(recommendation_raw) if isinstance(recommendation_raw, str) else None
    violations = raw.get("violations")
    violations_text = ""
    if isinstance(violations, Mapping):
        violations_text = ", ".join(f"{severity}={count}" for severity, count in sorted(violations.items()))
    summary = (
        f"tea-test-review: recommendation={recommendation or 'unknown'} "
        f"score={score if score is not None else 'unknown'}"
    )
    if violations_text:
        summary += f" violations({violations_text})"
    return TeaAdvisoryResult(
        ran=True,
        score=score,
        recommendation=recommendation,
        summary=summary,
        skipped_reason=None,
    )


class TeaAdvisoryScanPlugin:
    """Optional advisory scanner (Story 11.2). Mirrors
    ``scanner_plugins.OptionalScanPlugin.call``'s "around"-only shape, but
    appends to ``context["advisory_notes"]`` -- NEVER
    ``context["plugin_findings"]`` -- so a SCORED note can never become a
    ``Finding``, move a rung, or change the composed status/exit code.
    Registered OPTIONAL-only (``scanner_plugins.OPTIONAL_SCANNER_IDS``);
    enabled only via ``WARDEN_OPTIONAL_SCANNERS=tea-test-review``.

    Exception to the above (AD-10, DW-FU-11-2): ``TeaRosterMissingError``
    is deliberately let through ``_contribute``'s otherwise-total
    fail-open net -- an unprovisioned AD-9 roster is a tool-misconfiguration
    refusal, not a scored finding, so ``cli.py`` records it as a
    ``CONFIG_VALIDATION`` error (a real ERROR rung) rather than swallowing
    it. That is the only path by which this plugin's own state can ever
    reach the exit code.

    ``runner`` (defaults to ``None``, forwarded verbatim to
    ``run_tea_test_review``) is the sole test-injection seam -- production
    code never supplies one, so a shipped scan always resolves the real
    AD-9 roster + binary via ``_ad9_roster_has_tea``/``shutil.which``."""

    hook_spec: str = PR_GATE_SCAN.name
    owner: str = "tea-test-review"
    is_default: bool = False
    scanner_id: str = "tea-test-review"

    def __init__(self, *, runner: TeaRunner | None = None) -> None:
        self._runner = runner

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point == "around":
            enabled = context.get("enabled_optional") or ()
            if isinstance(enabled, str):
                enabled = (enabled,)
            if self.scanner_id in enabled:
                self._contribute(context)
            nxt = context.get("next")
            if callable(nxt):
                return nxt(context)
        return context

    def _contribute(self, context: MutableMapping[str, Any]) -> None:
        """Fail-open at the plugin boundary too (belt-and-suspenders): any
        subprocess/parse/binary defect degrades silently. The ONE
        deliberate exception is ``TeaRosterMissingError`` (AD-10,
        DW-FU-11-2) -- re-raised, not swallowed, so a genuinely
        unprovisioned AD-9 roster propagates out of the PR-gate scan for
        ``cli.py`` to record as a loud ``CONFIG_VALIDATION`` error instead
        of a silent no-op."""
        target = context.get("target")
        if not isinstance(target, Path):
            return
        try:
            result = run_tea_test_review(target, runner=self._runner)
        except TeaRosterMissingError:
            raise
        except Exception:  # noqa: BLE001 -- fail-open: never raise (except
            # the roster-missing refusal above, which AD-10 requires loud)
            return
        if not result.ran:
            return
        notes = context.get("advisory_notes")
        if not isinstance(notes, list):
            notes = []
            context["advisory_notes"] = notes
        notes.append(
            {
                "tool": self.scanner_id,
                "score": result.score,
                "recommendation": result.recommendation,
                "summary": result.summary,
            }
        )
