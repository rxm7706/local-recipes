"""Pure decision over the Guild's flag gate's answer (Story 74.2,
``spec-feature-flag-governance`` CAP-3).

``marshal factory dispatch`` consults ``scripts/flag_gate_check.py --spec <path>``
in its preflight -- before any worktree or harness session exists -- and refuses
a story the gate would red. The gate belongs to no station (Charter Section 6:
the hand that builds is never the gate that judges), so this module never
restates its rules: it never reads a spec's frontmatter, never opens a file, and
never decides what makes a spec red. It only turns the gate's answer -- the exit
code and its one JSON object -- into a finding (AD-4, pure decision; the process
call is ``cli/dispatch.py::_consult_flag_gate``'s, the impure edge).

Every unevaluable answer is a refusal (AD-8): exit 2, any other exit code, a
timeout, output that is not the gate's JSON, or a verdict the exit code
contradicts. Never a silent green.

Two codes, not one: ``MRS-DISP-052`` (ERROR) refuses; ``MRS-DISP-055`` (WARN) is
the proceeds-with-a-warning half -- a pre-rule spec, or a repository without the
gate script. ``compute_verdict`` classifies by code alone (AD-31), so a WARN
under the ERROR-tier code would red a dispatch that proceeds.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from .model import Finding, Severity

#: The refusing code: the gate reds the spec, or could not judge it.
REFUSED_CODE = "MRS-DISP-052"
#: The advisory code: the gate warned, or the gate script is absent.
WARNED_CODE = "MRS-DISP-055"

#: Where the gate lives, relative to the repository root.
GATE_SCRIPT_REL = "scripts/flag_gate_check.py"
#: The block's documentation, the refusal's remedy.
FLAG_BLOCK_DOC = "docs/reference/story-spec-flag-block.md"

_REMEDY = (
    f"give the spec a `flag:` block or a `flag-exempt:` value from the closed list (see {FLAG_BLOCK_DOC}), "
    "then dispatch again"
)

# The gate's documented contract: `red` <-> exit 1; `pass` / `warn` <-> exit 0.
_EXIT_OK = 0
_EXIT_RED = 1


def decide_gate_result(spec: str, *, returncode: int, stdout: str, stderr: str) -> Finding | None:
    """The finding for one completed ``flag_gate_check.py --spec`` run (pure).

    ``red`` (exit 1) -> ERROR ``MRS-DISP-052`` naming ``spec``, each ``fail``
    finding and the remedy; ``warn`` (exit 0) -> WARN ``MRS-DISP-055``; ``pass``
    (exit 0) -> ``None``. Anything else -- another exit code, non-JSON, a
    non-object, a missing or ``unknown`` verdict, a verdict the exit code
    contradicts -- is ERROR ``MRS-DISP-052`` naming the gate's failure."""
    payload = _parse_object(stdout)
    verdict = payload.get("verdict") if payload is not None else None
    if payload is not None:
        if returncode == _EXIT_RED and verdict == "red":
            return _red(spec, payload)
        if returncode == _EXIT_OK and verdict == "warn":
            return _warn(spec, payload)
        if returncode == _EXIT_OK and verdict == "pass":
            return None
    return _unevaluable(spec, _failure_detail(payload, verdict, returncode, stderr))


def decide_gate_failure(spec: str, failure: str) -> Finding:
    """ERROR ``MRS-DISP-052`` for a gate that could not be run to completion:
    ``failure`` is the process port's error text, the timeout included (pure)."""
    return _unevaluable(spec, f"it could not be run to completion: {failure}")


def gate_absent_finding(script_rel: str = GATE_SCRIPT_REL) -> Finding:
    """WARN ``MRS-DISP-055`` for a repository without the gate script -- one that
    has not adopted the rule. The dispatch proceeds (pure)."""
    return Finding(
        code=WARNED_CODE,
        severity=Severity.WARN,
        message=(
            f"{script_rel} is not in this repository -- the feature-flag gate was not consulted and the "
            "dispatch proceeds (a repository that has not adopted the flag rule)"
        ),
    )


def _parse_object(stdout: str) -> Mapping[str, object] | None:
    try:
        payload = json.loads(stdout)
    except ValueError, TypeError:
        return None
    return payload if isinstance(payload, Mapping) else None


def _gate_findings(payload: Mapping[str, object], severity: str) -> list[str]:
    """``kind: message`` for each of the gate's findings at ``severity`` (``fail`` / ``warn``)."""
    raw = payload.get("findings")
    if not isinstance(raw, list):
        return []
    lines: list[str] = []
    for item in raw:
        if not isinstance(item, Mapping) or item.get("severity") != severity:
            continue
        kind = str(item.get("kind") or "finding")
        message = str(item.get("message") or "").strip()
        lines.append(f"{kind}: {message}" if message else kind)
    return lines


def _red(spec: str, payload: Mapping[str, object]) -> Finding:
    named = _gate_findings(payload, "fail")
    detail = "; ".join(named) if named else "the gate reported no finding text"
    return Finding(
        code=REFUSED_CODE,
        severity=Severity.ERROR,
        message=(
            f"the feature-flag gate reds {spec}: {detail} -- dispatch is refused before any session starts; {_REMEDY}"
        ),
    )


def _warn(spec: str, payload: Mapping[str, object]) -> Finding:
    named = _gate_findings(payload, "warn")
    detail = f" ({'; '.join(named)})" if named else ""
    return Finding(
        code=WARNED_CODE,
        severity=Severity.WARN,
        message=(
            f"the feature-flag gate warns on {spec}{detail}: a pre-rule spec that carries neither a `flag:` "
            f"block nor a `flag-exempt:` value -- the dispatch proceeds until it is retrofitted ({FLAG_BLOCK_DOC})"
        ),
    )


def _unevaluable(spec: str, detail: str) -> Finding:
    return Finding(
        code=REFUSED_CODE,
        severity=Severity.ERROR,
        message=(
            f"the feature-flag gate could not judge {spec}: {detail} -- dispatch is refused "
            "(an unevaluable gate is a failure, never a silent green)"
        ),
    )


def _failure_detail(payload: Mapping[str, object] | None, verdict: object, returncode: int, stderr: str) -> str:
    """Why the answer is not a verdict: the gate's own ``error`` field, else the
    last stderr line, else the exit code -- with the exit code always named."""
    if payload is None:
        reason = _last_line(stderr) or "its output is not the gate's JSON object"
    else:
        error = payload.get("error")
        if isinstance(error, str) and error.strip():
            reason = error.strip()
        elif verdict in ("red", "pass", "warn"):
            reason = f"its verdict {verdict!r} contradicts its exit code"
        else:
            reason = _last_line(stderr) or f"its verdict is {verdict!r}, not pass, warn or red"
    return f"{reason} (exit {returncode})"


def _last_line(text: str) -> str:
    lines = (text or "").strip().splitlines()
    return lines[-1].strip() if lines else ""
