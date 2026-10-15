"""Story 31.3 / install-class CAP-3 — prove the documented fresh-clone class-path.

A recorded/scripted walk, never a chat transcript driving npm Installer
classes. Native commands must appear in install-matrix.md. After 30.2 the
dashboard class path is Kedro-Viz (operator console is Lane 1 ``/console/``),
not Guildhall generate.py. After atlas Story 30.1 the Kedro-Viz export is a
build product, never tracked: it is produced by ``viz-publish-stage`` and
reaches Pages as the ``kedro-viz-export`` workflow artifact, so the class is
runnable when that producer is wired -- a fresh clone has no export to find.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .suite import (
    INSTALL_CLASS_PLAYBOOK_REL,
    INSTALL_MATRIX_REL,
    SUITE_PACKAGES,
    probe_wired,
)
from .suite import (
    repo_root as suite_repo_root,
)

FRESH_CLONE_HEADING = "## Fresh-clone class-path (CAP-3)"
_NATIVE_CMD = re.compile(r"`((?:npx |uv tool install |corepack |pnpm |cd )[^`]+)`")
_IMPROVISED_INSTALLER = re.compile(r"\bnew\s+Installer\b|\bInstaller\s*\(")
_MODULE_SKF_COMMAND = re.compile(r"steward\s+provision\s+--module\s+skf\b", re.IGNORECASE)
_DELETED_DASHBOARD_TASKS = (
    "dashboard-gen",
    "dashboard-watch",
    "dashboard-check",
    "dashboard-drift-check",
)
#: The Kedro-Viz producer (atlas Story 30.1): the pixi task that stages the export and the
#: workflow that uploads it. The bmad-dashboard class is runnable when both are wired.
_KEDRO_VIZ_STAGE_TASK = "[feature.pyforge-atlas.tasks.viz-publish-stage]"
_KEDRO_VIZ_WORKFLOW_REL = ".github/workflows/kedro-viz-publish.yml"
_KEDRO_VIZ_ARTIFACT = "kedro-viz-export"
_SIX = (
    "bmad-method",
    "bmad-loop",
    "bmad-module-skill-forge",
    "bmad-labs-skills",
    "bmad-dashboard",
    "bmad-module-template",
)
_EXPECTED_WIRED = {
    "bmad-method": "present",
    "bmad-loop": "provisionable",
    "bmad-module-skill-forge": "present",
    # Story 46.9: the plugin-path probe now reads the real .claude/skills
    # census (Story 46.5's four consented dirs are actually provisioned in
    # this repo) instead of only the playbook-text check -- "wired", not the
    # stale "documented".
    "bmad-labs-skills": "wired",
    "bmad-module-template": "n/a",
}


class FreshCloneError(RuntimeError):
    """The documented class-path is missing, invented, or improvised."""


@dataclass(frozen=True)
class ClassOutcome:
    name: str
    expected: str
    actual: str | None
    ok: bool
    detail: str


@dataclass(frozen=True)
class FreshCloneReport:
    outcomes: tuple[ClassOutcome, ...]
    failures: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.failures

    def summary(self) -> str:
        if self.ok:
            rows = ", ".join(f"{o.name}={o.actual}" for o in self.outcomes)
            return f"provision --prove-class-path: PASS ({rows})"
        joined = "; ".join(self.failures)
        return f"provision --prove-class-path: FAIL ({joined})"

    def as_json(self) -> str:
        return json.dumps(
            {
                "ok": self.ok,
                "failures": list(self.failures),
                "outcomes": [
                    {
                        "name": o.name,
                        "expected": o.expected,
                        "actual": o.actual,
                        "ok": o.ok,
                        "detail": o.detail,
                    }
                    for o in self.outcomes
                ],
            },
            indent=2,
        )


def playbook_path(repo: Path) -> Path:
    return repo / INSTALL_CLASS_PLAYBOOK_REL


def matrix_path(repo: Path) -> Path:
    return repo / INSTALL_MATRIX_REL


def fresh_clone_section(playbook_text: str) -> str:
    idx = playbook_text.find(FRESH_CLONE_HEADING)
    if idx < 0:
        raise FreshCloneError(f"playbook missing {FRESH_CLONE_HEADING!r} — CAP-3 path is undocumented")
    rest = playbook_text[idx:]
    nxt = rest.find("\n## ", 1)
    return rest if nxt < 0 else rest[:nxt]


def native_fragments_in_section(section: str) -> tuple[str, ...]:
    return tuple(_NATIVE_CMD.findall(section))


def _pixi_task_table_present(pixi: str, task: str) -> bool:
    return f"[feature.local-recipes.tasks.{task}]" in pixi


def _scan_improvised(section: str) -> list[str]:
    failures: list[str] = []
    if _IMPROVISED_INSTALLER.search(section):
        failures.append("improvised npm Installer class in the documented class-path")
    if _MODULE_SKF_COMMAND.search(section):
        failures.append("documented class-path drives --module skf (Spec non-goal)")
    for task in _DELETED_DASHBOARD_TASKS:
        if re.search(rf"`pixi run {re.escape(task)}`", section):
            failures.append(f"documented class-path runs deleted pixi task {task}")
    return failures


def _uploads_artifact(workflow: Path, name: str) -> bool:
    """True when ``workflow`` has an ``actions/upload-artifact`` step uploading ``name``."""
    try:
        document = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    except OSError, yaml.YAMLError:
        return False
    jobs = document.get("jobs") if isinstance(document, dict) else None
    for job in (jobs or {}).values():
        for step in (job or {}).get("steps") or []:
            if (
                isinstance(step, dict)
                and str(step.get("uses", "")).startswith("actions/upload-artifact")
                and (step.get("with") or {}).get("name") == name
            ):
                return True
    return False


def _kedro_viz_producer_failures(repo: Path, pixi: str) -> list[str]:
    """Why the Kedro-Viz producer is not wired; empty when it is (atlas Story 30.1)."""
    failures: list[str] = []
    if _KEDRO_VIZ_STAGE_TASK not in pixi:
        failures.append(f"pixi task table {_KEDRO_VIZ_STAGE_TASK} missing (the Kedro-Viz producer)")
    workflow = repo / _KEDRO_VIZ_WORKFLOW_REL
    if not workflow.is_file():
        failures.append(f"{_KEDRO_VIZ_WORKFLOW_REL} missing (the Kedro-Viz producer)")
    elif not _uploads_artifact(workflow, _KEDRO_VIZ_ARTIFACT):
        failures.append(f"{_KEDRO_VIZ_WORKFLOW_REL} uploads no {_KEDRO_VIZ_ARTIFACT} artifact")
    return failures


def _dashboard_runnable(repo: Path, playbook: str, pixi: str) -> ClassOutcome:
    """Runnable when the playbook documents the Kedro-Viz path and its producer is wired.

    The export itself (``docs/dashboard/kedro-viz/``) is a gitignored build product since atlas
    Story 30.1, so a fresh clone never has it and the proof never asks for it."""
    probe = probe_wired(repo, next(p for p in SUITE_PACKAGES if p.name == "bmad-dashboard"))
    failures: list[str] = []
    if _KEDRO_VIZ_ARTIFACT not in playbook:
        failures.append(f"playbook does not name the {_KEDRO_VIZ_ARTIFACT} workflow artifact")
    if "/console/" not in playbook:
        failures.append("playbook does not name Lane 1 /console/")
    failures.extend(_kedro_viz_producer_failures(repo, pixi))
    for task in _DELETED_DASHBOARD_TASKS:
        if _pixi_task_table_present(pixi, task):
            failures.append(f"resurrected pixi task table {task}")
    ok = not failures
    detail = probe.detail or ""
    if failures:
        detail = "; ".join(failures)
    return ClassOutcome(
        name="bmad-dashboard",
        expected="runnable",
        # Never "runnable" on a failure: the probe's own value is "runnable" whenever its pixi
        # task exists, which made the CI line read "expected 'runnable' got 'runnable'".
        actual="runnable" if ok else "not-runnable",
        ok=ok,
        detail=detail,
    )


def _resolve_repo(repo: Path | None) -> Path:
    """Prefer an explicit path, then cwd (CI checkout), then the installed-package walk."""
    if repo is not None:
        return Path(repo)
    cwd = Path.cwd()
    if (cwd / "pixi.toml").is_file() and (cwd / "_bmad-output").is_dir():
        return cwd
    return suite_repo_root()


def prove(repo: Path | None = None) -> FreshCloneReport:
    """Prove the six-class fresh-clone path against *repo* (default: this checkout)."""
    root = _resolve_repo(repo)
    failures: list[str] = []
    playbook = playbook_path(root)
    matrix = matrix_path(root)
    if not playbook.is_file():
        failures.append(f"missing playbook {INSTALL_CLASS_PLAYBOOK_REL}")
    if not matrix.is_file():
        failures.append("missing install-matrix.md")
    playbook_text = playbook.read_text(encoding="utf-8") if playbook.is_file() else ""
    matrix_text = matrix.read_text(encoding="utf-8") if matrix.is_file() else ""
    section = ""
    if playbook_text:
        try:
            section = fresh_clone_section(playbook_text)
        except FreshCloneError as exc:
            failures.append(str(exc))
    if section:
        failures.extend(_scan_improvised(section))
        for fragment in native_fragments_in_section(section):
            if fragment not in matrix_text:
                failures.append(f"invented native fragment {fragment!r} not in install-matrix.md")
        if "steward provision --runner bmad-loop" not in section:
            failures.append("class-path does not cite steward provision --runner bmad-loop")
        if _KEDRO_VIZ_ARTIFACT not in section:
            failures.append(f"class-path does not cite the {_KEDRO_VIZ_ARTIFACT} workflow artifact (Kedro-Viz)")
        if "npx bmad-module-skill-forge install" not in section:
            failures.append("class-path does not cite skill-forge's own installer")

    pixi_text = (root / "pixi.toml").read_text(encoding="utf-8") if (root / "pixi.toml").is_file() else ""
    by_name = {p.name: p for p in SUITE_PACKAGES}
    outcomes: list[ClassOutcome] = []
    for name in _SIX:
        if name == "bmad-dashboard":
            outcomes.append(_dashboard_runnable(root, playbook_text, pixi_text))
            continue
        pkg = by_name[name]
        probe = probe_wired(root, pkg)
        expected = _EXPECTED_WIRED[name]
        actual = probe.value
        ok = actual == expected
        outcomes.append(
            ClassOutcome(
                name=name,
                expected=expected,
                actual=actual,
                ok=ok,
                detail=probe.detail or "",
            )
        )
    for outcome in outcomes:
        if not outcome.ok:
            failures.append(f"{outcome.name}: expected {outcome.expected!r} got {outcome.actual!r} ({outcome.detail})")
    return FreshCloneReport(outcomes=tuple(outcomes), failures=tuple(failures))
