"""Opengrep SAST advisory lens (Story 15.1, CAP-25, suite:AD-4).

Optional scanner enabled via ``WARDEN_OPTIONAL_SCANNERS=opengrep`` when
``pyforge.warden.sast_opengrep`` is ON. Each match becomes one advisory note
(``tool``, ``rule_id``, ``path``, ``line``, ``severity``) in
``context["advisory_notes"]`` — never a ``Finding``, rung, status, or exit
code. Spawns only through ``engines.run_opengrep_engine`` (``_engine_env``).
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from pyforge.core.flags import read_boolean

from .engines import run_opengrep_engine
from .hooks import PR_GATE_SCAN

SAST_OPENGREP_FLAG = "pyforge.warden.sast_opengrep"
OPENGREP_SCANNER_ID = "opengrep"
OPENGREP_BINARY = "opengrep"


class OpengrepRunOutcome(Protocol):
    returncode: int


OpengrepRunner = Callable[[Path, Path, Path], OpengrepRunOutcome | None]


def bundled_sast_rules_dir() -> Path:
    return Path(__file__).resolve().parent / "data" / "sast-rules"


def opengrep_selectable(*, flags_path: Path | None = None) -> bool:
    return read_boolean(SAST_OPENGREP_FLAG, default=False, flags_path=flags_path)


@dataclass(frozen=True, slots=True)
class OpengrepAdvisoryNote:
    tool: str
    rule_id: str
    path: str
    line: int
    severity: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "rule_id": self.rule_id,
            "path": self.path,
            "line": self.line,
            "severity": self.severity,
            "summary": self.summary,
        }


def _note_from_version_or_parse_failure(message: str) -> OpengrepAdvisoryNote:
    return OpengrepAdvisoryNote(
        tool=OPENGREP_SCANNER_ID,
        rule_id="",
        path="",
        line=0,
        severity="INFO",
        summary=message,
    )


def parse_opengrep_json(text: str) -> tuple[tuple[OpengrepAdvisoryNote, ...], str | None]:
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return (), "opengrep produced unparseable JSON output"
    if not isinstance(document, Mapping):
        return (), "opengrep JSON root is not an object"
    raw_results = document.get("results")
    if raw_results is None:
        return (), None
    if not isinstance(raw_results, list):
        return (), "opengrep JSON results is not an array"
    notes: list[OpengrepAdvisoryNote] = []
    for item in raw_results:
        if not isinstance(item, Mapping):
            continue
        rule_id = str(item.get("check_id") or item.get("rule_id") or "")
        path = str(item.get("path") or "")
        start = item.get("start")
        line = 0
        if isinstance(start, Mapping) and isinstance(start.get("line"), int):
            line = int(start["line"])
        extra = item.get("extra")
        severity = "UNKNOWN"
        if isinstance(extra, Mapping):
            sev = extra.get("severity")
            if isinstance(sev, str):
                severity = sev
        if not rule_id and not path:
            continue
        notes.append(
            OpengrepAdvisoryNote(
                tool=OPENGREP_SCANNER_ID,
                rule_id=rule_id,
                path=path,
                line=line,
                severity=severity,
                summary=f"opengrep: rule={rule_id or 'unknown'} path={path or '?'} line={line}",
            )
        )
    return tuple(notes), None


def run_opengrep_advisory(
    target: Path,
    *,
    runner: OpengrepRunner | None = None,
    rules_dir: Path | None = None,
) -> tuple[OpengrepAdvisoryNote, ...]:
    """Run opengrep against ``target`` and return advisory notes only."""
    rules = rules_dir if rules_dir is not None else bundled_sast_rules_dir()
    if runner is None:
        if shutil.which(OPENGREP_BINARY) is None:
            return ()
        text, error, _exit_code = run_opengrep_engine(
            binary=OPENGREP_BINARY,
            rules_dir=rules,
            cwd=target,
        )
        if error is not None:
            return (_note_from_version_or_parse_failure(error.message),)
        if text is None or not text.strip():
            return ()
        notes, parse_error = parse_opengrep_json(text)
        if parse_error is not None:
            return (_note_from_version_or_parse_failure(parse_error),)
        return notes
    import tempfile

    try:
        handle, json_path = tempfile.mkstemp(suffix=".json", prefix="pdos-opengrep-")
    except OSError:
        return ()
    try:
        import os

        os.close(handle)
        outcome = runner(target, rules, Path(json_path))
        if outcome is not None and outcome.returncode not in (0, 1):
            return ()
        try:
            text = Path(json_path).read_text(encoding="utf-8")
        except OSError:
            return (_note_from_version_or_parse_failure("could not read opengrep JSON output"),)
        notes, parse_error = parse_opengrep_json(text)
        if parse_error is not None:
            return (_note_from_version_or_parse_failure(parse_error),)
        return notes
    finally:
        try:
            import os

            os.unlink(json_path)
        except OSError:
            pass


class OpengrepScanPlugin:
    """Optional SAST advisory scanner (Story 15.1). Advisory notes only."""

    hook_spec: str = PR_GATE_SCAN.name
    owner: str = OPENGREP_SCANNER_ID
    is_default: bool = False
    scanner_id: str = OPENGREP_SCANNER_ID

    def __init__(self, *, runner: OpengrepRunner | None = None) -> None:
        self._runner = runner

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point == "around":
            enabled = context.get("enabled_optional") or ()
            if isinstance(enabled, str):
                enabled = (enabled,)
            if self.scanner_id in enabled and opengrep_selectable():
                self._contribute(context)
            nxt = context.get("next")
            if callable(nxt):
                return nxt(context)
        return context

    def _contribute(self, context: MutableMapping[str, Any]) -> None:
        target = context.get("target")
        if not isinstance(target, Path):
            return
        try:
            notes = run_opengrep_advisory(target, runner=self._runner)
        except Exception:  # noqa: BLE001 — fail-open advisory lens
            return
        if not notes:
            return
        channel = context.get("advisory_notes")
        if not isinstance(channel, list):
            channel = []
            context["advisory_notes"] = channel
        channel.extend(note.to_dict() for note in notes)
