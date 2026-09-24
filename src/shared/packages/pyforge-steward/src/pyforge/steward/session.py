"""``steward session check`` — one verdict for session preconditions (Epic 63, Story 63.4).

A session begins on any harness (Claude Code, Cursor, GitHub Copilot cloud agent, a
`marshal factory dispatch` launch, ...) — local or cloud. This module composes seven
findings that answer "is this session ready to do planning-chain work?" as data, not
prose:

1. pixi is present and ``pyforge-guild`` is materialized at the frozen lock.
2. bmad-method sits at the pinned version — reuses doctor's own drift verdict
   (``pyforge.doctor.sources.bmad_method.gather``) verbatim; never re-implemented.
3. the token-economy kit — reuses marshal's own ``seed check --json`` verdict.
4. ``gh`` is authenticated and has API budget left — this probe must NEVER fail
   open (see ``feedback_unauthenticated_github_probes_fail_open`` in team memory).
5. the codegraph structure-graph index is present — the same ``seed check --json``
   call that answers (3) also answers this.
6. the Tier-3 sprint-status feed exists for the active project, if any.
7. scribe recall is reachable — reported, never gates the exit code (AC #8).

Findings (2), (3) and (5) delegate to another station's already-published verdict
rather than re-deriving pin/kit logic (Design Notes). New code is confined to the
three probes nothing already exposes: gh, the Tier-3 feed, and scribe reachability.

``session.py`` is a peer of ``bootstrap.py``, not an extension of it — mirrors its
``ValidateFastStep`` / ``validate_fast_steps`` / ``format_validate_fast_report`` /
``ValidateFastDuty`` shape (AD-8: a duty never calls ``sys.exit``).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .bootstrap import repo_root
from .interfaces import DutyResult

_DEFAULT_PIXI_ENV = "pyforge-guild"
_GUILD_ENV_RELATIVE_PATH = Path(".pixi/envs") / _DEFAULT_PIXI_ENV
_ACTIVE_PROJECT_MARKER_RELATIVE_PATH = Path("_bmad/custom/.active-project")
_SEED_CHECK_ARGV = ("pixi", "run", "-e", _DEFAULT_PIXI_ENV, "marshal", "seed", "check", "--json")
_SEED_CHECK_TIMEOUT_S = 60.0
_GH_TIMEOUT_S = 20.0
_TIER3_FEED_REMEDY = "cp planning-artifacts/sprint-status-ledger.yaml implementation-artifacts/sprint-status.yaml"


@dataclass(frozen=True)
class SessionFinding:
    """One session-precondition finding — evidence, not prose."""

    name: str
    ok: bool
    detail: str
    remedy: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "ok": self.ok,
            "detail": self.detail,
            "remedy": self.remedy,
        }


def _pixi_guild_finding(root: Path) -> SessionFinding:
    """Finding (1): pixi present + pyforge-guild materialized at the frozen lock."""
    if shutil.which("pixi") is None:
        return SessionFinding(
            name="pixi-guild",
            ok=False,
            detail="pixi is not on PATH",
            remedy="install-pixi: curl -fsSL https://pixi.sh/install.sh | bash",
        )
    env_dir = root / _GUILD_ENV_RELATIVE_PATH
    if not env_dir.is_dir():
        return SessionFinding(
            name="pixi-guild",
            ok=False,
            detail=f"{env_dir} is not materialized",
            remedy=f"pixi install --frozen -e {_DEFAULT_PIXI_ENV}",
        )
    return SessionFinding(name="pixi-guild", ok=True, detail=f"{env_dir} is materialized")


def _bmad_method_finding(root: Path) -> SessionFinding:
    """Finding (2): bmad-method at the pinned version — doctor's verdict, verbatim.

    AC3: when ``pyforge.doctor`` is importable, this is
    ``pyforge.doctor.sources.bmad_method.gather``'s own verdict, never re-implemented.
    AC4: when it is not importable, falls back to the exact subprocess
    ``upgrade.py::run_bmad_drift_integrity`` already runs, rather than raising.
    """
    try:
        from pyforge.doctor.models import DoctorStatus
        from pyforge.doctor.sources.bmad_method import gather as bmad_method_gather
    except ImportError:
        from .upgrade import run_bmad_drift_integrity

        result = run_bmad_drift_integrity(root)
        return SessionFinding(
            name="bmad-method",
            ok=result.ok,
            detail=result.detail,
            remedy=None if result.ok else f"pixi run -e {_DEFAULT_PIXI_ENV} bmad-drift-check",
        )

    findings = bmad_method_gather(root)
    failed = [row for row in findings if row.status is DoctorStatus.FAIL]
    if failed:
        detail = "; ".join(f"{row.check}: {row.message}" for row in failed[:5])
        return SessionFinding(
            name="bmad-method",
            ok=False,
            detail=detail,
            remedy=f"pixi run -e {_DEFAULT_PIXI_ENV} bmad-drift-check",
        )
    return SessionFinding(name="bmad-method", ok=True, detail="bmad-method drift verdict: no FAIL findings")


def _run_seed_check(root: Path) -> subprocess.CompletedProcess[str]:
    """Shells ``marshal seed check --json`` inside the Guild env. May raise OSError/TimeoutExpired."""
    return subprocess.run(
        list(_SEED_CHECK_ARGV),
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=_SEED_CHECK_TIMEOUT_S,
    )


def _seed_kit_findings(root: Path) -> tuple[SessionFinding, SessionFinding]:
    """Findings (3) token-kit and (5) codegraph-index — ONE ``marshal seed check --json`` call.

    AC5: any of the three ``kit`` entries at layer-off/missing/stale surfaces as a
    non-ok token-kit finding; the same call's ``codegraph-index`` entry drives the
    codegraph-index finding.
    """
    kit_remedy = f"pixi run -e {_DEFAULT_PIXI_ENV} marshal seed kit"
    try:
        result = _run_seed_check(root)
    except (OSError, subprocess.TimeoutExpired) as exc:
        detail = f"{' '.join(_SEED_CHECK_ARGV)} could not run: {exc}"
        unreachable = SessionFinding(name="token-kit", ok=False, detail=detail, remedy=kit_remedy)
        return unreachable, SessionFinding(name="codegraph-index", ok=False, detail=detail, remedy=kit_remedy)

    try:
        payload = json.loads(result.stdout)
        kit = payload["kit"]
    except (json.JSONDecodeError, KeyError, TypeError):
        tail_lines = (result.stderr or result.stdout or "").strip().splitlines()
        tail = "; ".join(tail_lines[-3:]) if tail_lines else "no output"
        detail = f"{' '.join(_SEED_CHECK_ARGV)} returned unparseable output: {tail}"
        unreachable = SessionFinding(name="token-kit", ok=False, detail=detail, remedy=kit_remedy)
        return unreachable, SessionFinding(name="codegraph-index", ok=False, detail=detail, remedy=kit_remedy)

    non_ok = [item for item in kit if item.get("status") != "ok"]
    if non_ok:
        detail = "; ".join(f"{item.get('item')}: {item.get('status')}" for item in non_ok)
        kit_finding = SessionFinding(name="token-kit", ok=False, detail=detail, remedy=kit_remedy)
    else:
        detail = "; ".join(f"{item.get('item')}: ok" for item in kit) or "no kit items reported"
        kit_finding = SessionFinding(name="token-kit", ok=True, detail=detail)

    codegraph_item = next((item for item in kit if item.get("item") == "codegraph-index"), None)
    if codegraph_item is None:
        codegraph_finding = SessionFinding(
            name="codegraph-index",
            ok=False,
            detail="marshal seed check --json reported no codegraph-index entry",
            remedy=kit_remedy,
        )
    elif codegraph_item.get("status") != "ok":
        codegraph_finding = SessionFinding(
            name="codegraph-index",
            ok=False,
            detail=f"codegraph-index: {codegraph_item.get('status')} -- {codegraph_item.get('detail', '')}".strip(),
            remedy=kit_remedy,
        )
    else:
        codegraph_finding = SessionFinding(
            name="codegraph-index",
            ok=True,
            detail=codegraph_item.get("detail") or "codegraph-index: ok",
        )
    return kit_finding, codegraph_finding


def _gh_auth_finding() -> SessionFinding:
    """Finding (4): gh auth status + gh api rate_limit.

    AC6: an unauthenticated or exhausted session is a finding — every failure mode
    (missing binary, launch error, non-zero exit, unparseable output, 0 remaining)
    degrades to non-ok. Never defaults to ok on a probe failure.
    """
    gh = shutil.which("gh")
    if gh is None:
        return SessionFinding(
            name="gh-auth",
            ok=False,
            detail="gh is not on PATH",
            remedy="install-gh: https://github.com/cli/cli#installation (or apt/snap install gh)",
        )

    try:
        auth = subprocess.run([gh, "auth", "status"], capture_output=True, text=True, timeout=_GH_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return SessionFinding(
            name="gh-auth", ok=False, detail=f"gh auth status could not run: {exc}", remedy="gh auth login"
        )
    if auth.returncode != 0:
        tail_lines = (auth.stderr or auth.stdout or "").strip().splitlines()
        detail = tail_lines[-1] if tail_lines else "gh auth status reported an unauthenticated session"
        return SessionFinding(name="gh-auth", ok=False, detail=detail, remedy="gh auth login")

    try:
        rate = subprocess.run([gh, "api", "rate_limit"], capture_output=True, text=True, timeout=_GH_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return SessionFinding(
            name="gh-auth", ok=False, detail=f"gh api rate_limit could not run: {exc}", remedy="gh auth login"
        )
    if rate.returncode != 0:
        tail_lines = (rate.stderr or rate.stdout or "").strip().splitlines()
        detail = tail_lines[-1] if tail_lines else "gh api rate_limit failed"
        return SessionFinding(name="gh-auth", ok=False, detail=detail, remedy="gh auth login")

    try:
        payload = json.loads(rate.stdout)
        remaining = int(payload["resources"]["core"]["remaining"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return SessionFinding(
            name="gh-auth",
            ok=False,
            detail=f"gh api rate_limit returned unparseable output: {exc}",
            remedy="gh auth login",
        )
    if remaining <= 0:
        return SessionFinding(
            name="gh-auth",
            ok=False,
            detail="gh api rate_limit is exhausted (0 remaining)",
            remedy="wait for the rate limit to reset, or authenticate a second token",
        )
    return SessionFinding(name="gh-auth", ok=True, detail=f"gh authenticated; {remaining} API calls remaining")


def _active_project_slug(*, project: str | None, root: Path) -> str | None:
    """Resolution priority: ``--project`` flag > ``BMAD_ACTIVE_PROJECT`` env > the marker file."""
    if project:
        return project
    env_slug = os.environ.get("BMAD_ACTIVE_PROJECT")
    if env_slug:
        return env_slug
    marker = root / _ACTIVE_PROJECT_MARKER_RELATIVE_PATH
    try:
        text = marker.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def _tier3_feed_finding(*, root: Path, project: str | None) -> SessionFinding:
    """Finding (6): the Tier-3 sprint-status feed for the project in hand.

    AC7: when absent, the remedy is EXACTLY ``cp planning-artifacts/sprint-status-ledger.yaml
    implementation-artifacts/sprint-status.yaml``.
    """
    slug = _active_project_slug(project=project, root=root)
    if slug is None:
        return SessionFinding(
            name="tier3-feed",
            ok=True,
            detail="no active project resolved (--project, BMAD_ACTIVE_PROJECT, or "
            f"{_ACTIVE_PROJECT_MARKER_RELATIVE_PATH}) -- nothing to check",
        )
    feed = root / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "sprint-status.yaml"
    if feed.is_file():
        return SessionFinding(name="tier3-feed", ok=True, detail=f"{feed} is present")
    return SessionFinding(
        name="tier3-feed",
        ok=False,
        detail=f"{feed} is absent for active project {slug!r}",
        remedy=_TIER3_FEED_REMEDY,
    )


def _scribe_reachability_finding(root: Path) -> SessionFinding:
    """Finding (7): scribe recall reachability — reported, NEVER fails the run (AC8)."""
    scribe = shutil.which("scribe")
    if scribe is not None:
        return SessionFinding(name="scribe-recall", ok=True, detail=f"scribe is on PATH ({scribe})")
    if (root / _GUILD_ENV_RELATIVE_PATH).is_dir():
        return SessionFinding(
            name="scribe-recall",
            ok=True,
            detail=f"scribe is not on PATH directly; reachable via `pixi run -e {_DEFAULT_PIXI_ENV} scribe recall`",
        )
    return SessionFinding(
        name="scribe-recall",
        ok=True,
        detail=f"scribe is not reachable -- {_DEFAULT_PIXI_ENV} is not materialized",
        remedy=f"pixi install --frozen -e {_DEFAULT_PIXI_ENV}",
    )


def gather_session_findings(*, root: Path, project: str | None = None) -> tuple[SessionFinding, ...]:
    """Compose all seven session-precondition findings. Never raises for an ordinary probe failure."""
    kit_finding, codegraph_finding = _seed_kit_findings(root)
    return (
        _pixi_guild_finding(root),
        _bmad_method_finding(root),
        kit_finding,
        _gh_auth_finding(),
        codegraph_finding,
        _tier3_feed_finding(root=root, project=project),
        _scribe_reachability_finding(root),
    )


def format_session_report(findings: tuple[SessionFinding, ...], *, as_json: bool) -> str:
    all_ok = all(finding.ok for finding in findings)
    if as_json:
        return json.dumps({"ok": all_ok, "findings": [f.to_dict() for f in findings]}, indent=2)
    lines = ["steward session check: gate report"]
    for finding in findings:
        prefix = "ok  " if finding.ok else "FAIL"
        lines.append(f"  {prefix} {finding.name}: {finding.detail}")
        if not finding.ok and finding.remedy:
            lines.append(f"       remedy: {finding.remedy}")
    lines.append("steward session check: PASS" if all_ok else "steward session check: FAIL")
    return "\n".join(lines)


class SessionDuty:
    """``steward session`` — one verdict for the session preconditions (Story 63.4)."""

    name = "session"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "session_verb", None)
        if verb != "check":
            return DutyResult(ok=False, summary="steward session: available verbs are 'check'")
        root = Path(ns.repo).expanduser().resolve() if getattr(ns, "repo", None) else repo_root()
        project = getattr(ns, "project", None)
        findings = gather_session_findings(root=root, project=project)
        all_ok = all(finding.ok for finding in findings)
        return DutyResult(
            ok=all_ok,
            summary=format_session_report(findings, as_json=bool(getattr(ns, "json", False))),
            details={"findings": [f.to_dict() for f in findings]},
        )
