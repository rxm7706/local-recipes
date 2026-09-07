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

Fail-open contract: ANY subprocess/parse/binary problem (absent binary,
non-zero exit, timeout, malformed JSON, an unreadable ``--json`` file)
degrades to ``TeaAdvisoryResult(ran=False, ...)`` -- ``run_tea_test_review``
never raises, and ``TeaAdvisoryScanPlugin.call`` never raises either
(belt-and-suspenders: a defect in this module must never crash a PR-gate
scan).

Testing seam: ``run_tea_test_review``'s ``runner`` parameter replaces ONLY
the ``subprocess.run`` step -- the ``shutil.which`` presence probe always
runs for real. The "TEA absent" scenario therefore needs no stub at all
(this repo's own ``pyforge-warden`` pixi environment genuinely does not
depend on the ``bmad-method-test-architecture-enterprise`` conda package,
so the probe returns ``None`` for real); the "low score" / "runner errors"
scenarios inject a ``runner`` that writes (or fails to write) the
``--json`` file directly, without ever resolving or spawning the real
binary.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

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


def _default_runner(
    binary: str, target: Path, json_path: Path
) -> subprocess.CompletedProcess[str]:
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
    """Fail-open wrapper over the ``tea-test-review`` CLI.

    TEA absent (binary not on PATH, and no ``runner`` was injected) ->
    ``ran=False``, no subprocess spawned. A present binary that errors
    (an exit code outside ``{0, 1}``, a timeout, no/garbled ``--json``
    output) ALSO degrades to ``ran=False`` -- the advisory contract is
    "contribute nothing, never error", not "assume the tool works". Exit 0
    and exit 1 are BOTH trusted (``test-review.js``'s own documented
    semantics: exit 1 is a legitimate "verdict fail" -- a real score below
    ``--min-score`` -- never a subprocess failure); only an exit code
    outside that pair is treated as untrusted, regardless of whatever JSON
    happens to exist at ``json_path``. A ``{"skipped": true, ...}`` or
    ``{"promptOnly": true, ...}`` verdict (the CLI's own documented shapes
    for "no changed test files" / ``--agent none``) is likewise treated as
    nothing-to-report, not a failure.
    """
    if runner is None:
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
                raise RuntimeError(
                    f"tea-test-review exited {completed.returncode} -- "
                    "verdict not trusted"
                )
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
            skipped_reason=(
                f"tea-test-review run failed: {type(exc).__name__}: {exc}"
            ),
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
            skipped_reason=(
                str(reason)
                if reason
                else "tea-test-review reported nothing to review"
            ),
        )
    score_raw = raw.get("qualityScore")
    score = (
        int(score_raw)
        if isinstance(score_raw, (int, float))
        and not isinstance(score_raw, bool)
        and math.isfinite(score_raw)
        else None
    )
    recommendation_raw = raw.get("recommendation")
    recommendation = (
        str(recommendation_raw) if isinstance(recommendation_raw, str) else None
    )
    violations = raw.get("violations")
    violations_text = ""
    if isinstance(violations, Mapping):
        violations_text = ", ".join(
            f"{severity}={count}" for severity, count in sorted(violations.items())
        )
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
    ``context["plugin_findings"]`` -- so it can never become a ``Finding``,
    move a rung, or change the composed status/exit code. Registered
    OPTIONAL-only (``scanner_plugins.OPTIONAL_SCANNER_IDS``); enabled only
    via ``WARDEN_OPTIONAL_SCANNERS=tea-test-review``.

    ``runner`` (defaults to ``None``, forwarded verbatim to
    ``run_tea_test_review``) is the sole test-injection seam -- production
    code never supplies one, so a shipped scan always resolves the real
    binary via ``shutil.which``."""

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
        """Fail-open at the plugin boundary too (belt-and-suspenders):
        ``run_tea_test_review`` already never raises, but a defect here
        must still never escape into the PR-gate scan."""
        target = context.get("target")
        if not isinstance(target, Path):
            return
        try:
            result = run_tea_test_review(target, runner=self._runner)
        except Exception:  # noqa: BLE001 -- fail-open: never raise
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
