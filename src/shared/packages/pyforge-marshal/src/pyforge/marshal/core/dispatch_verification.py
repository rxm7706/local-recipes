"""Dispatch session independent verification (Story 22.3, FR-193 CAP-3).

Pure functions only: Epic 2 gate outcomes judge whether a dispatched story
may land. Harness self-reports are recorded for diagnostics but never verdict
inputs (never-false-green; unevaluable ≠ pass).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from .gate import _matches_any
from .model import Finding, Severity, Status, status_for
from .verdict import classify, compute_verdict

PRE_EXISTING_GATE_CODE = "MRS-GATE-014"

# Pytest / pixi-task output shapes seen in repo-global verify commands.
_FAILURE_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ERROR collecting (\S+\.py)"),
    re.compile(
        r"(?:^|\s)((?:tests|src|recipes|scripts|\.claude)/[\w./-]+\.py)(?::|\s|$)",
        re.MULTILINE,
    ),
    re.compile(r"importing test module '[^']*/([\w./-]+\.py)'"),
    re.compile(r"([\w./-]+\.py):\d+:"),
)


class DispatchVerificationVerdict(StrEnum):
    """Independent verification outcome before any landing (CAP-3)."""

    VERIFIED = "verified"
    REFUSED = "refused"


@dataclass(frozen=True)
class DispatchVerificationInput:
    """Inputs to the verification judge — gate findings only for the verdict."""

    findings: tuple[Finding, ...]
    # Harness/session self-report — recorded for diagnostics only, never a
    # verdict input (CAP-3 Always bullet; doctor-12.3 refusal fixture).
    harness_self_report_shipped: bool = False


def gate_verdict_is_clean(findings: tuple[Finding, ...]) -> bool:
    """True when Epic 2 gate objects report a fully clean envelope."""
    return status_for(compute_verdict(findings)) is Status.OK


def judge_dispatch_verification(inp: DispatchVerificationInput) -> DispatchVerificationVerdict:
    """Judge verification from gate findings only — never self-report."""
    if gate_verdict_is_clean(inp.findings):
        return DispatchVerificationVerdict.VERIFIED
    return DispatchVerificationVerdict.REFUSED


def primary_gate_failure(findings: tuple[Finding, ...]) -> Finding | None:
    """The most severe non-ok gate finding, for naming in a refusal verdict."""
    verdict = compute_verdict(findings)
    if status_for(verdict) is Status.OK:
        return None
    for finding in findings:
        if status_for(compute_verdict((finding,))) is not Status.OK:
            return finding
    return findings[0] if findings else None


def would_land_on_self_report_only(inp: DispatchVerificationInput) -> bool:
    """True when self-report claims shipped but independent gates refuse."""
    return inp.harness_self_report_shipped and not gate_verdict_is_clean(inp.findings)


def _normalize_repo_path(path: str) -> str:
    return path.lstrip("./").replace("\\", "/")


def extract_failure_paths_from_verify_output(stdout: str, stderr: str) -> tuple[str, ...]:
    """Best-effort repo-relative ``.py`` paths from verify command output."""
    text = f"{stdout}\n{stderr}"
    found: set[str] = set()
    for pattern in _FAILURE_PATH_PATTERNS:
        for match in pattern.finditer(text):
            candidate = _normalize_repo_path(match.group(1))
            if candidate.endswith(".py"):
                found.add(candidate)
    if not found:
        return ()
    # Prefer qualified paths over bare filenames when pytest emits both.
    qualified = {path for path in found if "/" in path}
    if qualified:
        return tuple(sorted(qualified))
    return tuple(sorted(found))


def path_in_story_blast_radius(
    path: str,
    *,
    changed_files: tuple[str, ...],
    effective_surface: tuple[str, ...],
    project_slug: str | None = None,
) -> bool:
    """True when ``path`` is in the story diff or matches effective surface."""
    normalized = _normalize_repo_path(path)
    normalized_changed = tuple(_normalize_repo_path(item) for item in changed_files)
    if normalized in normalized_changed:
        return True
    for changed in normalized_changed:
        if normalized.startswith(changed.rstrip("/") + "/"):
            return True
        if changed.startswith(normalized.rstrip("/") + "/"):
            return True
    candidates = [normalized]
    # Pytest run from a station package cwd often emits `tests/unit/...` without
    # the `src/shared/packages/{slug}/` prefix. Repo-global suites (`tests/
    # packaging/`, `tests/scripts/`, …) must never be remapped — CAP-5.
    if project_slug and normalized.startswith("tests/unit/"):
        candidates.append(f"src/shared/packages/{project_slug}/{normalized}")
    for candidate in candidates:
        if _matches_any(candidate, effective_surface):
            return True
    return False


def _command_from_gate_001_message(message: str) -> str | None:
    prefix = "verify command "
    if not message.startswith(prefix):
        return None
    rest = message[len(prefix) :]
    if not rest.startswith("'"):
        return None
    end = rest.find("' ", 1)
    if end == -1:
        end = rest.rfind("'")
    if end <= 0:
        return None
    return rest[1:end]


def _report_for_command(command: str, command_reports: tuple[dict[str, object], ...]) -> dict[str, object] | None:
    for report in command_reports:
        if report.get("command") == command:
            return report
    return None


def pre_existing_gate_finding(
    *,
    command: str,
    failure_paths: tuple[str, ...],
) -> Finding:
    """``MRS-GATE-014`` (``Verdict.WARN``): verify failed outside story blast radius."""
    paths_text = ", ".join(repr(path) for path in failure_paths[:5])
    if len(failure_paths) > 5:
        paths_text += ", ..."
    return Finding(
        code=PRE_EXISTING_GATE_CODE,
        severity=Severity.WARN,
        message=(
            f"verify command {command!r} failed outside the story diff and "
            f"effective surface (pre-existing-gate); failing paths: "
            f"{paths_text}"
        ),
        path=failure_paths[0] if failure_paths else None,
    )


def reclassify_pre_existing_gate_findings(
    findings: tuple[Finding, ...],
    *,
    command_reports: tuple[dict[str, object], ...],
    changed_files: tuple[str, ...],
    effective_surface: tuple[str, ...],
    project_slug: str | None = None,
) -> tuple[Finding, ...]:
    """Downgrade out-of-blast-radius ``MRS-GATE-001`` to ``MRS-GATE-014`` WARN.

    Story 28.22 (CAP-5): a repo-global verify red unrelated to the story must
    not refuse landing or invite transient redispatch into the same unrelated
    command. When failure paths cannot be extracted, the original
    ``MRS-GATE-001`` stands — never weaken on ambiguity.
    """
    if not findings:
        return findings
    reclassified: list[Finding] = []
    for finding in findings:
        if finding.code != "MRS-GATE-001":
            reclassified.append(finding)
            continue
        command = _command_from_gate_001_message(finding.message)
        if command is None:
            reclassified.append(finding)
            continue
        report = _report_for_command(command, command_reports)
        if report is None:
            reclassified.append(finding)
            continue
        stdout = str(report.get("stdout") or "")
        stderr = str(report.get("stderr") or "")
        failure_paths = extract_failure_paths_from_verify_output(stdout, stderr)
        if not failure_paths:
            reclassified.append(finding)
            continue
        if any(
            path_in_story_blast_radius(
                path,
                changed_files=changed_files,
                effective_surface=effective_surface,
                project_slug=project_slug,
            )
            for path in failure_paths
        ):
            reclassified.append(finding)
            continue
        reclassified.append(pre_existing_gate_finding(command=command, failure_paths=failure_paths))
    return tuple(reclassified)


def is_pre_existing_gate_code(code: str) -> bool:
    return code == PRE_EXISTING_GATE_CODE and status_for(classify(code)) is Status.OK
