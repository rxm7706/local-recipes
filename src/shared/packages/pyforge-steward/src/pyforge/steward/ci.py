"""``steward ci`` — read-only CI pause visibility (Story 99.3 / CAP-166 FR-39).

Reaches GitHub through ``gh`` by subprocess (AD-1). Returns ``DutyResult`` only (AD-8).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from .bootstrap import repo_root
from .interfaces import DutyResult

CI_FLAG_KEY = "pyforge.steward.ci_pause_control"
DEFAULT_REPO = "rxm7706/local-recipes"
CI_VARS_REL = Path(".steward/ci-vars.json")
CI_PAUSES_LOG_REL = Path(".steward/ci-pauses.log")
SCHEMA_ID = "urn:local-recipes:pyforge-steward:ci-status-schema"
EXIT_CI_REFUSAL = 3
EXIT_CI_GH_FAILED = 1  # gh variable set/delete failed (AD-8; same domain as EXIT_FAILED)

VERDICTS = (
    "live",
    "paused",
    "opt-in-off",
    "paused-manually",
    "retired",
    "drift",
    "stuck",
    "overdue",
)


class _Completed(Protocol):
    args: list[str] | str
    returncode: int
    stdout: str
    stderr: str


SubprocessRunner = Callable[[list[str], Path], _Completed]


@dataclass
class CiDeps:
    root: Path
    runner: SubprocessRunner
    repo: str = DEFAULT_REPO
    flag_on: Callable[[], bool] = field(default=lambda: True)
    now: Callable[[], datetime] = field(default=lambda: datetime.now(timezone.utc))
    registry_path: Path | None = None


@dataclass
class _GhSnapshot:
    rate_limit: dict[str, int]
    variables: dict[str, tuple[str, str | None]]  # name -> (value, updatedAt)
    workflow_states: dict[str, str]  # basename -> state
    runs_by_workflow: dict[str, list[dict[str, Any]]]
    pending_deploy_run_ids: set[int]
    run_list_errors: list[str]


def _default_runner(argv: list[str], cwd: Path) -> _Completed:
    import subprocess

    return subprocess.run(  # noqa: S603
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _production_deps(root: Path) -> CiDeps:
    from pyforge.core.flags import read_boolean

    return CiDeps(
        root=root,
        runner=_default_runner,
        flag_on=lambda: read_boolean(CI_FLAG_KEY, default=False),
    )


def _refusal(summary: str) -> DutyResult:
    return DutyResult(ok=False, summary=summary, details={"exit_code": EXIT_CI_REFUSAL})


def _ensure_flag(deps: CiDeps) -> DutyResult | None:
    if not deps.flag_on():
        return _refusal(f"ci: refused — flag {CI_FLAG_KEY} is off")
    return None


def _load_registry(deps: CiDeps) -> dict[str, Any]:
    loader_root = deps.root
    scripts = loader_root / "scripts"
    if not (scripts / "_ci_surface_gates_lib.py").is_file():
        loader_root = repo_root()
        scripts = loader_root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from _ci_surface_gates_lib import REGISTRY_REL, load_registry  # noqa: PLC0415

    path = deps.registry_path or (deps.root / REGISTRY_REL)
    return load_registry(path)


def _gh_json(deps: CiDeps, api_path: str) -> tuple[Any | None, str]:
    proc = deps.runner(["gh", "api", api_path], deps.root)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        return None, err
    try:
        return json.loads(proc.stdout), ""
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON from gh api: {exc}"


def _check_rate_limit(deps: CiDeps) -> tuple[bool, str, dict[str, int]]:
    data, err = _gh_json(deps, "rate_limit")
    if data is None:
        return False, err or "gh api rate_limit failed", {"core_limit": 0, "core_remaining": 0}
    core = (data.get("resources") or {}).get("core") or {}
    limit = int(core.get("limit") or 0)
    remaining = int(core.get("remaining") or 0)
    rl = {"core_limit": limit, "core_remaining": remaining}
    if limit <= 60:
        return False, "gh api rate_limit shows no authenticated quota (core limit 60)", rl
    if remaining <= 0:
        return False, "gh api rate_limit core remaining is 0", rl
    return True, "", rl


def _fetch_variables(deps: CiDeps) -> tuple[dict[str, tuple[str, str | None]] | None, str]:
    proc = deps.runner(
        ["gh", "variable", "list", "--repo", deps.repo, "--json", "name,value,updatedAt"],
        deps.root,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        return None, err
    try:
        rows = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON from gh variable list: {exc}"
    if not isinstance(rows, list):
        return None, "gh variable list did not return a JSON array"
    out: dict[str, tuple[str, str | None]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        if not isinstance(name, str):
            continue
        val = row.get("value")
        value = "" if val is None else str(val)
        updated = row.get("updatedAt")
        updated_s = str(updated) if updated is not None else None
        out[name] = (value, updated_s)
    return out, ""


def _fetch_workflow_states(deps: CiDeps) -> tuple[dict[str, str] | None, str]:
    data, err = _gh_json(deps, f"repos/{deps.repo}/actions/workflows")
    if data is None:
        return None, err
    workflows = data.get("workflows")
    if not isinstance(workflows, list):
        return None, "workflows response missing workflows array"
    by_base: dict[str, str] = {}
    for wf in workflows:
        if not isinstance(wf, dict):
            continue
        path = wf.get("path")
        state = wf.get("state")
        if isinstance(path, str) and isinstance(state, str):
            by_base[Path(path).name] = state
    return by_base, ""


def _fetch_runs(deps: CiDeps, workflow_file: str) -> tuple[list[dict[str, Any]] | None, str]:
    proc = deps.runner(
        [
            "gh",
            "run",
            "list",
            "--repo",
            deps.repo,
            "--workflow",
            workflow_file,
            "--limit",
            "20",
            "--json",
            "databaseId,conclusion,status,createdAt,event",
        ],
        deps.root,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        return None, err
    try:
        runs = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON from gh run list: {exc}"
    if not isinstance(runs, list):
        return None, "gh run list did not return a JSON array"
    return runs, ""


def _fetch_pending_deployments(deps: CiDeps, run_id: int) -> bool:
    data, _err = _gh_json(deps, f"repos/{deps.repo}/actions/runs/{run_id}/pending_deployments")
    if data is None:
        return False
    if isinstance(data, list):
        return len(data) > 0
    return False


def _collect_snapshot(deps: CiDeps, registry: dict[str, Any]) -> tuple[_GhSnapshot | None, DutyResult | None]:
    ok, err, rl = _check_rate_limit(deps)
    if not ok:
        return None, _refusal(f"ci: {err}")

    variables, verr = _fetch_variables(deps)
    if variables is None:
        return None, _refusal(f"ci: {verr}")

    wf_states, werr = _fetch_workflow_states(deps)
    if wf_states is None:
        return None, _refusal(f"ci: {werr}")

    workflow_files: set[str] = set()
    for row in registry.get("surfaces") or []:
        if isinstance(row, dict) and row.get("workflow"):
            workflow_files.add(str(row["workflow"]))

    runs_by_wf: dict[str, list[dict[str, Any]]] = {}
    run_errors: list[str] = []
    pending_ids: set[int] = set()

    for wf in sorted(workflow_files):
        runs, rerr = _fetch_runs(deps, wf)
        if runs is None:
            run_errors.append(f"{wf}: {rerr}")
            runs_by_wf[wf] = []
            continue
        runs_by_wf[wf] = runs
        for run in runs:
            if str(run.get("status") or "") == "waiting":
                rid = run.get("databaseId")
                if isinstance(rid, int) and _fetch_pending_deployments(deps, rid):
                    pending_ids.add(rid)

    snap = _GhSnapshot(
        rate_limit=rl,
        variables=variables,
        workflow_states=wf_states,
        runs_by_workflow=runs_by_wf,
        pending_deploy_run_ids=pending_ids,
        run_list_errors=run_errors,
    )
    return snap, None


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() == "true"


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _review_days_left(review_by: str | None, today: date) -> int | None:
    d = _parse_date(review_by)
    if d is None:
        return None
    return (d - today).days


def _switch_names_in_registry(registry: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for row in registry.get("surfaces") or []:
        if not isinstance(row, dict):
            continue
        sw = row.get("switch")
        if sw is not None:
            names.add(str(sw))
    master = (registry.get("conventions") or {}).get("master")
    if master:
        names.add(str(master))
    return names


def _grandfathered(registry: dict[str, Any]) -> set[str]:
    raw = registry.get("grandfathered_names") or []
    return {str(x) for x in raw if x}


def _last_green(runs: list[dict[str, Any]]) -> str | None:
    for run in runs:
        if str(run.get("conclusion") or "") == "success":
            return str(run.get("createdAt") or "") or None
    return None


def _consecutive_cancelled(runs: list[dict[str, Any]], n: int) -> bool:
    if len(runs) < n:
        return False
    head = runs[:n]
    return all(str(r.get("conclusion") or "") == "cancelled" for r in head)


def _waiting_deploy_stuck(
    runs: list[dict[str, Any]],
    pending_ids: set[int],
    *,
    hours: int,
    now: datetime,
) -> bool:
    threshold = now - timedelta(hours=hours)
    for run in runs:
        rid = run.get("databaseId")
        if not isinstance(rid, int) or rid not in pending_ids:
            continue
        if str(run.get("status") or "") != "waiting":
            continue
        created = run.get("createdAt")
        if not isinstance(created, str):
            continue
        try:
            ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts < threshold:
            return True
    return False


def _live_switch_value(
    switch: str | None,
    variables: dict[str, tuple[str, str | None]],
) -> tuple[str | None, str | None]:
    if switch is None:
        return None, None
    val, updated = variables.get(switch, ("", None))
    live = None if val == "" and switch not in variables else val
    paused_since = updated if _truthy(live) else None
    return live, paused_since


def _state_verdict(
    row: dict[str, Any],
    *,
    live_val: str | None,
    wf_state: str | None,
    workflow_exists: bool,
) -> str:
    declared = str(row.get("state") or "live")
    switch_class = str(row.get("switch_class") or "")
    switch = row.get("switch")

    if declared == "retired":
        return "retired"
    if declared == "paused-manually":
        return "paused-manually"
    if switch_class == "enable":
        if _truthy(live_val):
            return "live"
        return "opt-in-off"
    if switch_class == "pause" and switch is not None:
        if declared == "paused":
            return "paused" if _truthy(live_val) else "live"
        if _truthy(live_val):
            return "paused"
        return "live"
    if declared == "paused":
        return "paused"
    if declared == "opt-in-off":
        return "opt-in-off"
    if declared == "paused-manually":
        return "paused-manually"
    if not workflow_exists and declared == "retired":
        return "retired"
    return declared if declared in VERDICTS else "live"


def _is_drift(
    row: dict[str, Any],
    *,
    live_val: str | None,
    wf_state: str | None,
    workflow_exists: bool,
    state_verdict: str,
) -> tuple[bool, str]:
    declared = str(row.get("state") or "live")
    row_id = str(row.get("id") or "")
    wf = str(row.get("workflow") or "")
    base = Path(wf).name

    if declared == "retired" and workflow_exists:
        return True, f"registry row {row_id} is retired but {wf} still exists"

    if declared == "paused-manually":
        if wf_state == "active":
            return True, f"registry row {row_id} declares paused-manually but {base} is active on GitHub"
        if wf_state not in (None, "disabled_manually"):
            return True, f"registry row {row_id} declares paused-manually but GitHub reports {wf_state}"

    if declared == "paused" and not _truthy(live_val):
        return True, f"registry row {row_id} declares paused but {row.get('switch')} is not true"

    if declared == "live" and _truthy(live_val) and str(row.get("switch_class") or "") == "pause":
        return True, f"registry row {row_id} declares live but pause switch is true"

    if declared == "opt-in-off" and _truthy(live_val) and str(row.get("switch_class") or "") == "enable":
        return True, f"registry row {row_id} declares opt-in-off but enable switch is true"

    if state_verdict != declared and declared in ("live", "paused", "opt-in-off", "paused-manually", "retired"):
        if declared == "opt-in-off" and state_verdict == "opt-in-off":
            pass
        elif declared == "paused" and state_verdict == "paused":
            pass
        elif declared == "live" and state_verdict == "live":
            pass
        elif declared == "paused-manually" and state_verdict == "paused-manually":
            pass
        else:
            return True, f"registry row {row_id} declared {declared} but live state reads {state_verdict}"

    return False, ""


def _row_stuck(
    row: dict[str, Any],
    runs: list[dict[str, Any]],
    snap: _GhSnapshot,
    *,
    now: datetime,
) -> bool:
    rules = row.get("stuck_rules") or {}
    if not isinstance(rules, dict):
        return False
    cancel_n = rules.get("consecutive_cancelled_runs")
    if isinstance(cancel_n, int) and cancel_n > 0 and _consecutive_cancelled(runs, cancel_n):
        return True
    deploy_h = rules.get("deploy_waiting_hours")
    if isinstance(deploy_h, int) and deploy_h > 0:
        if _waiting_deploy_stuck(runs, snap.pending_deploy_run_ids, hours=deploy_h, now=now):
            return True
    return False


def _build_rows(registry: dict[str, Any], snap: _GhSnapshot, deps: CiDeps) -> list[dict[str, Any]]:
    today = deps.now().date()
    rows_out: list[dict[str, Any]] = []

    registered_switches = _switch_names_in_registry(registry)
    pause_prefix = str((registry.get("conventions") or {}).get("pause_prefix") or "PAUSE_")
    enable_prefix = str((registry.get("conventions") or {}).get("enable_prefix") or "ENABLE_")
    grandfather = _grandfathered(registry)

    for row in registry.get("surfaces") or []:
        if not isinstance(row, dict):
            continue
        row_id = str(row.get("id") or "")
        wf = str(row.get("workflow") or "")
        base = Path(wf).name
        wf_path = deps.root / wf
        wf_state = snap.workflow_states.get(base)
        workflow_exists = wf_path.is_file()

        switch = row.get("switch")
        switch_s = str(switch) if switch is not None else None
        live_val, paused_since = _live_switch_value(switch_s, snap.variables)
        if paused_since is None and row.get("paused_since"):
            paused_since = str(row.get("paused_since"))

        runs = snap.runs_by_workflow.get(wf, [])
        last_green = _last_green(runs)
        if snap.run_list_errors and any(wf in e for e in snap.run_list_errors):
            last_green = "unknown"

        state_v = _state_verdict(
            row,
            live_val=live_val,
            wf_state=wf_state,
            workflow_exists=workflow_exists,
        )
        drift, detail = _is_drift(
            row,
            live_val=live_val,
            wf_state=wf_state,
            workflow_exists=workflow_exists,
            state_verdict=state_v,
        )
        review_by = row.get("review_by")
        review_s = str(review_by) if review_by else None
        days_left = _review_days_left(review_s, today)

        verdict = state_v
        if drift:
            verdict = "drift"
        elif _row_stuck(row, runs, snap, now=deps.now()):
            verdict = "stuck"
        elif days_left is not None and days_left < 0:
            verdict = "overdue"
        elif str(row.get("state") or "") == "paused" and _truthy(live_val):
            verdict = "paused"

        rows_out.append(
            {
                "id": row_id,
                "switch": switch_s,
                "declared_state": str(row.get("state") or "live"),
                "live_switch_value": live_val,
                "paused_since": paused_since,
                "review_by": review_s,
                "review_days_left": days_left,
                "owner": row.get("owner"),
                "last_green_run": last_green,
                "verdict": verdict,
                **({"detail": detail} if detail else {}),
            }
        )

    # Unregistered variables that look like CI switches.
    for name, (value, _updated) in snap.variables.items():
        if name in registered_switches:
            continue
        looks_like = name.startswith(pause_prefix) or name.startswith(enable_prefix) or name in grandfather
        if not looks_like:
            continue
        rows_out.append(
            {
                "id": f"unregistered:{name}",
                "switch": name,
                "declared_state": "—",
                "live_switch_value": value or None,
                "paused_since": None,
                "review_by": None,
                "review_days_left": None,
                "owner": None,
                "last_green_run": None,
                "verdict": "drift",
                "detail": f"repository variable {name} is not declared in the CI surface registry",
            }
        )

    # disabled_manually workflows without a registry row.
    manual_bases = {
        Path(str(r.get("workflow") or "")).name
        for r in registry.get("surfaces") or []
        if isinstance(r, dict) and str(r.get("state") or "") == "paused-manually"
    }
    for base, state in snap.workflow_states.items():
        if state != "disabled_manually" or base in manual_bases:
            continue
        rows_out.append(
            {
                "id": f"unregistered-workflow:{base}",
                "switch": None,
                "declared_state": "—",
                "live_switch_value": None,
                "paused_since": None,
                "review_by": None,
                "review_days_left": None,
                "owner": None,
                "last_green_run": None,
                "verdict": "drift",
                "detail": f"workflow {base} is disabled_manually on GitHub but has no paused-manually registry row",
            }
        )

    return rows_out


def _format_table(rows: list[dict[str, Any]]) -> str:
    headers = ("id", "verdict", "switch", "declared", "live", "review_by", "days", "last_green")
    lines = ["\t".join(headers)]
    for row in rows:
        days = row.get("review_days_left")
        days_s = "" if days is None else str(days)
        lines.append(
            "\t".join(
                [
                    str(row.get("id") or ""),
                    str(row.get("verdict") or ""),
                    str(row.get("switch") or ""),
                    str(row.get("declared_state") or ""),
                    str(row.get("live_switch_value") or ""),
                    str(row.get("review_by") or ""),
                    days_s,
                    str(row.get("last_green_run") or ""),
                ]
            )
        )
    return "\n".join(lines)


def _status_payload(
    deps: CiDeps,
    snap: _GhSnapshot,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "fetched_at": deps.now().isoformat(),
        "repo": deps.repo,
        "rate_limit": snap.rate_limit,
        "rows": rows,
    }


def run_status(deps: CiDeps, *, json_out: bool) -> DutyResult:
    refused = _ensure_flag(deps)
    if refused is not None:
        return refused
    registry = _load_registry(deps)
    snap, err = _collect_snapshot(deps, registry)
    if err is not None:
        return err
    assert snap is not None
    rows = _build_rows(registry, snap, deps)
    payload = _status_payload(deps, snap, rows)
    partial = bool(snap.run_list_errors)
    if json_out:
        summary = json.dumps(payload, indent=2)
    else:
        summary = _format_table(rows)
    ok = not partial
    details: dict[str, object] = {"payload": payload, "partial": partial}
    if partial:
        details["run_list_errors"] = snap.run_list_errors
    return DutyResult(ok=ok, summary=summary, details=details)


def _vars_path(deps: CiDeps) -> Path:
    return deps.root / CI_VARS_REL


def _write_vars_snapshot(deps: CiDeps, variables: dict[str, tuple[str, str | None]]) -> Path:
    path = _vars_path(deps)
    path.parent.mkdir(parents=True, exist_ok=True)
    flat = {name: val for name, (val, _u) in variables.items()}
    doc = {
        "fetched_at": deps.now().isoformat(),
        "repo": deps.repo,
        "variables": flat,
    }
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return path


def _read_vars_snapshot(deps: CiDeps) -> tuple[dict[str, Any] | None, str]:
    path = _vars_path(deps)
    if not path.is_file():
        return None, "no snapshot yet (run ci vars --refresh)"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, "snapshot file is corrupt JSON"
    if not isinstance(doc, dict):
        return None, "snapshot file has invalid shape"
    return doc, ""


def run_vars(deps: CiDeps, *, refresh: bool) -> DutyResult:
    refused = _ensure_flag(deps)
    if refused is not None:
        return refused
    if refresh:
        ok, err, _rl = _check_rate_limit(deps)
        if not ok:
            return _refusal(f"ci: {err}")
        variables, verr = _fetch_variables(deps)
        if variables is None:
            return _refusal(f"ci: {verr}")
        path = _write_vars_snapshot(deps, variables)
        return DutyResult(ok=True, summary=f"ci vars: wrote {path.relative_to(deps.root)}")
    doc, msg = _read_vars_snapshot(deps)
    if doc is None:
        return DutyResult(ok=False, summary=f"ci vars: {msg}")
    fetched = doc.get("fetched_at")
    age = ""
    if isinstance(fetched, str):
        try:
            ts = datetime.fromisoformat(fetched.replace("Z", "+00:00"))
            delta = deps.now() - ts
            age = f" (age {int(delta.total_seconds() // 3600)}h)"
        except ValueError:
            age = ""
    n = len(doc.get("variables") or {})
    return DutyResult(ok=True, summary=f"ci vars: snapshot from {fetched}{age}, {n} variables")


def _registry_file(deps: CiDeps) -> Path:
    if deps.registry_path is not None:
        return deps.registry_path
    loader_root = deps.root
    scripts = loader_root / "scripts"
    if not (scripts / "_ci_surface_gates_lib.py").is_file():
        loader_root = repo_root()
        scripts = loader_root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from _ci_surface_gates_lib import REGISTRY_REL  # noqa: PLC0415

    return loader_root / REGISTRY_REL


def _save_registry(deps: CiDeps, registry: dict[str, Any]) -> None:
    import yaml

    path = _registry_file(deps)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(registry, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _operator_name(deps: CiDeps) -> str:
    proc = deps.runner(["git", "config", "user.name"], deps.root)
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    return "operator"


def _resolve_surface_rows(registry: dict[str, Any], target: str) -> list[dict[str, Any]]:
    surfaces = registry.get("surfaces") or []
    by_id: list[dict[str, Any]] = []
    by_switch: list[dict[str, Any]] = []
    for row in surfaces:
        if not isinstance(row, dict):
            continue
        if str(row.get("id") or "") == target:
            by_id.append(row)
        sw = row.get("switch")
        if sw is not None and str(sw) == target:
            by_switch.append(row)
    if by_id:
        return by_id
    return by_switch


def _pause_gh_argv(deps: CiDeps, switch: str) -> list[str]:
    return [
        "gh",
        "variable",
        "set",
        switch,
        "--body",
        "true",
        "--repo",
        deps.repo,
    ]


def _resume_gh_argv(deps: CiDeps, switch: str) -> list[str]:
    return ["gh", "variable", "delete", switch, "--repo", deps.repo]


def _capture_argv(text: str) -> list[str]:
    return [
        "pixi",
        "run",
        "-e",
        "pyforge-guild",
        "scribe",
        "capture",
        "--type",
        "project",
        "--text",
        text,
    ]


def _build_capture_text(
    *,
    action: str,
    switch: str,
    surface_ids: list[str],
    reason: str | None,
    review_by: str | None,
) -> str:
    ids = ", ".join(surface_ids)
    if action == "pause":
        return (
            f"CI pause: set {switch} for {ids}; reason: {reason}; "
            f"review by {review_by}; registry updated in checkout — land via PR"
        )
    return f"CI resume: delete {switch} for {ids}; registry updated in checkout — land via PR"


def _format_pause_diff(
    rows: list[dict[str, Any]],
    *,
    today: str,
    by: str,
    reason: str,
    review_by: str,
) -> str:
    lines = ["registry diff:"]
    for row in rows:
        rid = str(row.get("id") or "")
        lines.append(f"  {rid}: state: paused, paused_since: {today}, paused_by: {by}")
        lines.append(f"    reason: {reason}, review_by: {review_by}")
    return "\n".join(lines)


def _format_resume_diff(rows: list[dict[str, Any]]) -> str:
    lines = ["registry diff:"]
    for row in rows:
        rid = str(row.get("id") or "")
        switch_class = str(row.get("switch_class") or "pause")
        new_state = "opt-in-off" if switch_class == "enable" else "live"
        lines.append(f"  {rid}: state: {new_state} (cleared pause metadata)")
    return "\n".join(lines)


def _append_journal(deps: CiDeps, record: dict[str, Any]) -> None:
    path = deps.root / CI_PAUSES_LOG_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def _apply_pause_row(row: dict[str, Any], *, today: str, by: str, reason: str, review_by: str) -> None:
    row["state"] = "paused"
    row["paused_since"] = today
    row["paused_by"] = by
    row["reason"] = reason
    row["review_by"] = review_by


def _apply_resume_row(row: dict[str, Any]) -> None:
    switch_class = str(row.get("switch_class") or "pause")
    row["state"] = "opt-in-off" if switch_class == "enable" else "live"
    for key in ("paused_since", "paused_by", "reason", "review_by"):
        row.pop(key, None)


def run_pause(
    deps: CiDeps,
    *,
    target: str,
    reason: str,
    review_by: str,
    yes: bool,
    remove_merge_gate: bool,
) -> DutyResult:
    refused = _ensure_flag(deps)
    if refused is not None:
        return refused

    reason = reason.strip()
    review_d = _parse_date(review_by)
    today = deps.now().date().isoformat()

    registry = _load_registry(deps)
    rows = _resolve_surface_rows(registry, target)
    if not rows:
        return _refusal(f"ci pause: no registry row for {target!r}")

    switches = {str(r.get("switch")) for r in rows if r.get("switch") is not None}
    if len(switches) != 1:
        return _refusal("ci pause: target must resolve to exactly one switch")
    switch = switches.pop()

    for row in rows:
        if str(row.get("state") or "") == "retired":
            return _refusal(f"ci pause: refused — row {row.get('id')} is retired")
        if row.get("gate") is True and not remove_merge_gate:
            return _refusal(
                f"ci pause: refused — row {row.get('id')} has gate: true "
                f"(pass --i-am-removing-a-merge-gate to override)"
            )
        if str(row.get("switch_class") or "") == "enable":
            return _refusal(f"ci pause: refused — {switch} is an enable opt-in, not a pause switch")
        if str(row.get("state") or "") == "paused":
            since = row.get("paused_since") or "unknown"
            rb = row.get("review_by") or "unknown"
            return _refusal(f"ci pause: already paused since {since}, review_by {rb}")
        if not reason:
            return _refusal("ci pause: refused — --reason must not be empty")
        if review_d is None:
            return _refusal(f"ci pause: refused — invalid --review-by {review_by!r}")
        if review_d < deps.now().date():
            return _refusal(f"ci pause: refused — review_by {review_by} is in the past")

    by = _operator_name(deps)
    surface_ids = [str(r.get("id") or "") for r in rows]
    gh_argv = _pause_gh_argv(deps, switch)
    capture_text = _build_capture_text(
        action="pause",
        switch=switch,
        surface_ids=surface_ids,
        reason=reason,
        review_by=review_by,
    )
    diff = _format_pause_diff(rows, today=today, by=by, reason=reason, review_by=review_by)
    capture_argv = _capture_argv(capture_text)

    if not yes:
        summary = "\n".join(
            [
                "ci pause (dry run):",
                "gh: " + " ".join(gh_argv),
                diff,
                "scribe: " + " ".join(capture_argv),
            ]
        )
        return DutyResult(ok=True, summary=summary)

    proc = deps.runner(gh_argv, deps.root)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        return DutyResult(
            ok=False,
            summary=f"ci pause: gh variable set failed: {err}",
            details={"exit_code": EXIT_CI_GH_FAILED},
        )

    for row in rows:
        _apply_pause_row(row, today=today, by=by, reason=reason, review_by=review_by)
    _save_registry(deps, registry)

    journal = {
        "ts": deps.now().isoformat(),
        "action": "pause",
        "switch": switch,
        "surface": surface_ids if len(surface_ids) > 1 else surface_ids[0],
        "reason": reason,
        "review_by": review_by,
        "by": by,
    }
    _append_journal(deps, journal)

    cap = deps.runner(capture_argv, deps.root)
    if cap.returncode != 0:
        err = (cap.stderr or cap.stdout or f"exit {cap.returncode}").strip()
        return DutyResult(
            ok=False,
            summary=f"ci pause: registry updated but scribe capture failed: {err}",
            details={"exit_code": EXIT_CI_GH_FAILED},
        )

    return DutyResult(
        ok=True,
        summary=(
            f"ci pause: set {switch} on GitHub; updated registry for {', '.join(surface_ids)}; "
            "journaled; captured — land the registry change via PR"
        ),
    )


def run_resume(deps: CiDeps, *, target: str, yes: bool) -> DutyResult:
    refused = _ensure_flag(deps)
    if refused is not None:
        return refused

    registry = _load_registry(deps)
    rows = _resolve_surface_rows(registry, target)
    if not rows:
        return _refusal(f"ci resume: no registry row for {target!r}")

    switches = {str(r.get("switch")) for r in rows if r.get("switch") is not None}
    if len(switches) != 1:
        return _refusal("ci resume: target must resolve to exactly one switch")
    switch = switches.pop()

    for row in rows:
        if str(row.get("state") or "") == "retired":
            return _refusal(f"ci resume: refused — row {row.get('id')} is retired")
        if str(row.get("switch_class") or "") == "enable":
            return _refusal(f"ci resume: refused — {switch} is an enable opt-in")
        state = str(row.get("state") or "live")
        if state != "paused":
            return _refusal(f"ci resume: refused — row {row.get('id')} is {state}, not paused")

    surface_ids = [str(r.get("id") or "") for r in rows]
    gh_argv = _resume_gh_argv(deps, switch)
    capture_text = _build_capture_text(
        action="resume",
        switch=switch,
        surface_ids=surface_ids,
        reason=None,
        review_by=None,
    )
    diff = _format_resume_diff(rows)
    capture_argv = _capture_argv(capture_text)

    if not yes:
        summary = "\n".join(
            [
                "ci resume (dry run):",
                "gh: " + " ".join(gh_argv),
                diff,
                "scribe: " + " ".join(capture_argv),
            ]
        )
        return DutyResult(ok=True, summary=summary)

    proc = deps.runner(gh_argv, deps.root)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        return DutyResult(
            ok=False,
            summary=f"ci resume: gh variable delete failed: {err}",
            details={"exit_code": EXIT_CI_GH_FAILED},
        )

    for row in rows:
        _apply_resume_row(row)
    _save_registry(deps, registry)

    journal = {
        "ts": deps.now().isoformat(),
        "action": "resume",
        "switch": switch,
        "surface": surface_ids if len(surface_ids) > 1 else surface_ids[0],
        "reason": None,
        "review_by": None,
        "by": _operator_name(deps),
    }
    _append_journal(deps, journal)

    cap = deps.runner(capture_argv, deps.root)
    if cap.returncode != 0:
        err = (cap.stderr or cap.stdout or f"exit {cap.returncode}").strip()
        return DutyResult(
            ok=False,
            summary=f"ci resume: registry updated but scribe capture failed: {err}",
            details={"exit_code": EXIT_CI_GH_FAILED},
        )

    return DutyResult(
        ok=True,
        summary=(
            f"ci resume: deleted {switch} on GitHub; updated registry for {', '.join(surface_ids)}; "
            "journaled; captured — land the registry change via PR"
        ),
    )


class CiDuty:
    name = "ci"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        root = repo_root()
        deps: CiDeps = getattr(ns, "_ci_deps", None) or _production_deps(root)
        verb = getattr(ns, "ci_verb", None)
        if verb == "status":
            return run_status(deps, json_out=bool(getattr(ns, "json", False)))
        if verb == "vars":
            return run_vars(deps, refresh=bool(getattr(ns, "refresh", False)))
        if verb == "pause":
            return run_pause(
                deps,
                target=str(getattr(ns, "target", "")),
                reason=str(getattr(ns, "reason", "")),
                review_by=str(getattr(ns, "review_by", "")),
                yes=bool(getattr(ns, "yes", False)),
                remove_merge_gate=bool(getattr(ns, "remove_merge_gate", False)),
            )
        if verb == "resume":
            return run_resume(
                deps,
                target=str(getattr(ns, "target", "")),
                yes=bool(getattr(ns, "yes", False)),
            )
        return DutyResult(ok=False, summary="ci: need status, vars, pause, or resume")
