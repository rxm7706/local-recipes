"""CI surface registry load, workflow vars scan, and offline/live checks (Story 99.1)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sys
import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _ci_surface_gates_render import completeness_findings
from _ci_surface_gates_render import render_all as render_all

REGISTRY_REL = Path("docs/governance/ci-surfaces.yaml")
SCHEMA_REL = Path("docs/governance/ci-surfaces.schema.json")
WORKFLOWS_GLOB = ".github/workflows/*.yml"

# Match vars.NAME with optional surrounding ${{ }} and common comparisons.
_VAR_REF = re.compile(
    r"(?:\$\{\{\s*)?vars\.([A-Z0-9_]+)(?:\s*\}\})?"
    r"(?:\s*(==|!=)\s*['\"]true['\"])?",
    re.MULTILINE,
)


@dataclass(frozen=True)
class VarUse:
    workflow_file: str
    job: str | None
    step: str | None
    name: str
    comparison: str | None  # "== 'true'" | "!= 'true'" | None
    in_if: bool


def load_registry(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: registry root must be a mapping")
    return data


def validate_registry_schema(data: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        return [f"jsonschema unavailable: {exc}"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    findings: list[str] = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path) or "(root)"
        findings.append(f"schema: {loc}: {err.message}")
    return findings


def _flatten_if(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten_if(v) for v in value)
    return str(value)


def _scan_text_for_vars(
    text: str,
    *,
    workflow_file: str,
    job: str | None,
    step: str | None,
    in_if: bool,
) -> list[VarUse]:
    uses: list[VarUse] = []
    for match in _VAR_REF.finditer(text):
        name = match.group(1)
        op = match.group(2)
        comparison = None
        if op == "==":
            comparison = "== 'true'"
        elif op == "!=":
            comparison = "!= 'true'"
        uses.append(
            VarUse(
                workflow_file=workflow_file,
                job=job,
                step=step,
                name=name,
                comparison=comparison,
                in_if=in_if,
            )
        )
    return uses


def collect_var_uses(root: Path, workflows_dir: Path | None = None) -> list[VarUse]:
    wf_dir = workflows_dir or (root / ".github" / "workflows")
    uses: list[VarUse] = []
    for path in sorted(wf_dir.glob("*.yml")):
        rel = path.relative_to(root).as_posix()
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise OSError(f"cannot read workflow {rel}: {exc}") from exc
        if not isinstance(doc, dict):
            continue
        jobs = doc.get("jobs")
        if not isinstance(jobs, dict):
            continue
        for job_name, job_def in jobs.items():
            if not isinstance(job_def, dict):
                continue
            if "if" in job_def:
                text = _flatten_if(job_def["if"])
                uses.extend(
                    _scan_text_for_vars(
                        text,
                        workflow_file=rel,
                        job=job_name,
                        step=None,
                        in_if=True,
                    )
                )
            steps = job_def.get("steps")
            if isinstance(steps, list):
                for step in steps:
                    if not isinstance(step, dict):
                        continue
                    step_name = step.get("name") or step.get("id") or "unnamed-step"
                    if "if" in step:
                        text = _flatten_if(step["if"])
                        uses.extend(
                            _scan_text_for_vars(
                                text,
                                workflow_file=rel,
                                job=job_name,
                                step=str(step_name),
                                in_if=True,
                            )
                        )
                    for key in ("env", "with"):
                        block = step.get(key)
                        if isinstance(block, dict):
                            block_text = yaml.safe_dump(block)
                            uses.extend(
                                _scan_text_for_vars(
                                    block_text,
                                    workflow_file=rel,
                                    job=job_name,
                                    step=str(step_name),
                                    in_if=False,
                                )
                            )
    return uses


def _workflow_jobs(root: Path, workflow_rel: str, workflows_dir: Path | None) -> set[str]:
    wf_dir = workflows_dir or (root / ".github" / "workflows")
    path = root / workflow_rel if not Path(workflow_rel).is_absolute() else Path(workflow_rel)
    if not path.is_file():
        path = wf_dir / Path(workflow_rel).name
    if not path.is_file():
        return set()
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    jobs = doc.get("jobs") if isinstance(doc, dict) else None
    if not isinstance(jobs, dict):
        return set()
    return set(str(k) for k in jobs)


def _conventions(data: dict[str, Any]) -> tuple[str, str, frozenset[str]]:
    conv = data.get("conventions") or {}
    pause_prefix = str(conv.get("pause_prefix") or "PAUSE_")
    enable_prefix = str(conv.get("enable_prefix") or "ENABLE_")
    grandfathered = frozenset(str(x) for x in (data.get("grandfathered_names") or []))
    return pause_prefix, enable_prefix, grandfathered


def _switch_names_in_registry(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_switch: dict[str, list[dict[str, Any]]] = {}
    for row in data.get("surfaces") or []:
        if not isinstance(row, dict):
            continue
        sw = row.get("switch")
        if sw is None:
            continue
        by_switch.setdefault(str(sw), []).append(row)
    return by_switch


def _if_text_for_row(
    root: Path,
    row: dict[str, Any],
    workflows_dir: Path | None,
) -> str:
    wf = str(row.get("workflow") or "")
    job = row.get("job")
    step = row.get("step")
    wf_dir = workflows_dir or (root / ".github" / "workflows")
    path = root / wf
    if not path.is_file():
        path = wf_dir / Path(wf).name
    if not path.is_file():
        return ""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    jobs = doc.get("jobs") if isinstance(doc, dict) else None
    if not isinstance(jobs, dict) or not job:
        return ""
    job_def = jobs.get(job)
    if not isinstance(job_def, dict):
        return ""
    if step:
        steps = job_def.get("steps")
        if not isinstance(steps, list):
            return ""
        for st in steps:
            if not isinstance(st, dict):
                continue
            st_name = st.get("name") or st.get("id") or "unnamed-step"
            if str(st_name) == str(step) or st.get("id") == step:
                return _flatten_if(st.get("if"))
        return ""
    return _flatten_if(job_def.get("if"))


def offline_check(
    root: Path,
    registry: dict[str, Any],
    *,
    workflows_dir: Path | None = None,
) -> list[str]:
    findings: list[str] = []
    pause_prefix, enable_prefix, grandfathered = _conventions(registry)
    switch_rows = _switch_names_in_registry(registry)
    declared_switches = set(switch_rows)
    master = str((registry.get("conventions") or {}).get("master") or "")
    if master:
        declared_switches.add(master)

    try:
        var_uses = collect_var_uses(root, workflows_dir)
    except OSError as exc:
        return [str(exc)]

    for use in var_uses:
        if use.name not in declared_switches:
            where = f"{use.workflow_file} job={use.job}"
            if use.step:
                where += f" step={use.step}"
            findings.append(
                f"unregistered vars.{use.name} in {where} (no registry row declares switch {use.name})"
            )
        elif not use.in_if:
            rows = switch_rows.get(use.name, [])
            if not any(str(r.get("switch_class")) == "value" for r in rows):
                where = f"{use.workflow_file} job={use.job} step={use.step}"
                findings.append(
                    f"vars.{use.name} in env/with at {where} requires a value row (switch_class: value)"
                )

    for row in registry.get("surfaces") or []:
        if not isinstance(row, dict):
            continue
        kind = str(row.get("kind") or "")
        switch = row.get("switch")
        switch_class = str(row.get("switch_class") or "")
        wf = str(row.get("workflow") or "")
        job = row.get("job")
        row_id = str(row.get("id") or wf)

        wf_path = root / wf
        wf_dir = workflows_dir or (root / ".github" / "workflows")
        if not wf_path.is_file() and not (wf_dir / Path(wf).name).is_file():
            findings.append(f"registry row {row_id}: workflow file missing ({wf})")
            continue

        if job is not None:
            jobs = _workflow_jobs(root, wf, workflows_dir)
            if str(job) not in jobs:
                findings.append(
                    f"registry row {row_id}: job {job!r} not found in {wf}"
                )

        if switch is not None and switch_class in ("pause", "enable"):
            if kind not in ("ci-job", "ci-step"):
                continue
            if_text = _if_text_for_row(root, row, workflows_dir)
            if switch not in if_text:
                loc = f"{wf} job={job}"
                if row.get("step"):
                    loc += f" step={row.get('step')}"
                findings.append(
                    f"registry row {row_id}: switch {switch} not read in if: of {loc}"
                )
            else:
                if switch_class == "pause" and f"vars.{switch} != 'true'" not in if_text.replace(
                    " ", ""
                ).replace('"', "'"):
                    # Allow flexible spacing; require != 'true' substring
                    if f"vars.{switch}" in if_text and "!= 'true'" not in if_text.replace('"', "'"):
                        findings.append(
                            f"registry row {row_id}: pause switch {switch} must use != 'true' comparison in {wf}"
                        )
                if switch_class == "enable" and f"vars.{switch} == 'true'" not in if_text.replace(
                    '"', "'"
                ):
                    if f"vars.{switch}" in if_text and "== 'true'" not in if_text.replace('"', "'"):
                        findings.append(
                            f"registry row {row_id}: enable switch {switch} must use == 'true' comparison in {wf}"
                        )

        if switch is not None and switch_class not in ("pause", "enable", "value"):
            findings.append(f"registry row {row_id}: invalid switch_class {switch_class!r}")

        if switch is not None and switch_class != "value":
            name = str(switch)
            ok = (
                name.startswith(pause_prefix)
                or name.startswith(enable_prefix)
                or name in grandfathered
            )
            if not ok:
                findings.append(
                    f"registry row {row_id}: switch {name} violates naming convention "
                    f"(expected {pause_prefix}*, {enable_prefix}*, or grandfathered)"
                )

        state = str(row.get("state") or "")
        if state == "paused" and not row.get("review_by"):
            findings.append(f"registry row {row_id}: paused row missing review_by")

        if str(row.get("cost") or "") == "high" and not row.get("canary"):
            findings.append(f"registry row {row_id}: cost: high row missing canary")

    findings.extend(completeness_findings(root, registry, workflows_dir=workflows_dir))

    return findings


def live_check(
    registry: dict[str, Any],
    *,
    workflows_payload: list[dict[str, Any]],
) -> list[str]:
    findings: list[str] = []
    by_path: dict[str, str] = {}
    for wf in workflows_payload:
        path = wf.get("path")
        state = wf.get("state")
        if isinstance(path, str) and isinstance(state, str):
            by_path[path] = state

    manual_rows: dict[str, dict[str, Any]] = {}
    for row in registry.get("surfaces") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("state")) == "paused-manually":
            wf = str(row.get("workflow") or "")
            manual_rows[Path(wf).name] = row

    for path, state in by_path.items():
        if state == "disabled_manually":
            base = Path(path).name
            if base not in manual_rows:
                findings.append(
                    f"live: workflow {path} is disabled_manually but no paused-manually registry row"
                )

    for base, row in manual_rows.items():
        state = by_path.get(base) or by_path.get(f".github/workflows/{base}")
        if state == "active":
            findings.append(
                f"live: registry row {row.get('id')} declares paused-manually for {base} "
                f"but GitHub reports state active"
            )
    return findings
