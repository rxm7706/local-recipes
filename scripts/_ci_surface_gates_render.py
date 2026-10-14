"""Render and completeness checks for CI pause fragments (Story 99.2 / CAP-166)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_RENDER_CMD = "python scripts/ci_surface_gates.py --render"
_RENDER_MARKER = "ci-surfaces:"
_FRAGMENT_DISPATCH = "github.event_name == 'workflow_dispatch'"
_MASTER_CMP = "vars.PAUSE_ALL_CI != 'true'"
_VAR_PAUSE = re.compile(r"vars\.([A-Z0-9_]+)\s*!=\s*['\"]true['\"]")


def workflow_on(data: dict[str, Any]) -> dict[str, Any]:
    """Return the workflow ``on`` mapping (PyYAML reads bare ``on:`` as boolean ``True``)."""
    trigger = data.get("on", data.get(True))
    if trigger is None:
        return {}
    if isinstance(trigger, str):
        return {trigger: None}
    if isinstance(trigger, list):
        return {str(k): None for k in trigger}
    if isinstance(trigger, dict):
        return dict(trigger)
    return {}


def workflow_fires_push_pr_schedule(data: dict[str, Any]) -> bool:
    return bool(set(workflow_on(data).keys()) & {"push", "pull_request", "schedule"})


def stem_to_upper_snake(stem: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_").upper()


def workflow_pause_var(workflow_path: Path) -> str:
    return f"PAUSE_{stem_to_upper_snake(workflow_path.stem)}"


def job_pause_var(workflow_path: Path, job_id: str) -> str:
    wf = stem_to_upper_snake(workflow_path.stem)
    job = stem_to_upper_snake(job_id)
    return f"PAUSE_{wf}_{job}"


def _normalize_if_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (list, tuple)):
        return " ".join(_normalize_if_text(v) for v in value)
    return str(value)


def strip_expression_wrappers(text: str) -> str:
    text = text.strip()
    if text.startswith("${{") and text.endswith("}}"):
        return text[3:-2].strip()
    return text


def parse_fragment_inner(if_text: str) -> str | None:
    """Extract the job's inner condition from a rendered fragment, or ``None`` if not a fragment."""
    raw = strip_expression_wrappers(_normalize_if_text(if_text))
    if _FRAGMENT_DISPATCH not in raw:
        return None
    or_parts = [p.strip() for p in raw.split("||")]
    if len(or_parts) < 2:
        return None
    paren = or_parts[1].strip()
    if not (paren.startswith("(") and paren.endswith(")")):
        return None
    inner = paren[1:-1].strip()
    master = _MASTER_CMP.replace(" ", "")
    compact = inner.replace(" ", "").replace('"', "'")
    if not compact.startswith(master.replace(" ", "")):
        return None
    # Drop leading master && workflow/job pause terms; remainder is inner condition.
    terms = [t.strip() for t in re.split(r"\s*&&\s*", inner)]
    idx = 0
    while idx < len(terms):
        term = terms[idx]
        if term == _MASTER_CMP:
            idx += 1
            continue
        if _VAR_PAUSE.fullmatch(term.replace('"', "'")):
            idx += 1
            continue
        break
    rest = " && ".join(terms[idx:]).strip()
    return rest


def has_render_fragment(if_text: str) -> bool:
    return parse_fragment_inner(if_text) is not None or (
        _FRAGMENT_DISPATCH in _normalize_if_text(if_text) and _MASTER_CMP in _normalize_if_text(if_text)
    )


@dataclass(frozen=True)
class JobRenderPlan:
    workflow_rel: str
    job_id: str
    row_id: str
    cost: str
    workflow_switch: str
    job_switch: str | None
    inner: str


def _registry_index(registry: dict[str, Any]) -> tuple[dict[str, str], dict[tuple[str, str], dict[str, Any]]]:
    """Map workflow path -> workflow pause switch; (workflow, job) -> ci-job row."""
    wf_switch: dict[str, str] = {}
    job_rows: dict[tuple[str, str], dict[str, Any]] = {}
    master = str((registry.get("conventions") or {}).get("master") or "PAUSE_ALL_CI")
    wf_switch["__master__"] = master
    for row in registry.get("surfaces") or []:
        if not isinstance(row, dict):
            continue
        wf = str(row.get("workflow") or "")
        kind = str(row.get("kind") or "")
        if kind == "workflow":
            sw = row.get("switch")
            if isinstance(sw, str) and sw:
                wf_switch[wf] = sw
        elif kind == "ci-job" and row.get("job"):
            job_rows[(wf, str(row["job"]))] = row
    return wf_switch, job_rows


def _active_workflow_states(registry: dict[str, Any]) -> dict[str, str]:
    states: dict[str, str] = {}
    for row in registry.get("surfaces") or []:
        if isinstance(row, dict) and row.get("kind") == "workflow":
            states[str(row.get("workflow") or "")] = str(row.get("state") or "")
    return states


def build_fragment(*, inner: str, workflow_switch: str, job_switch: str | None) -> str:
    pause_terms = [_MASTER_CMP, f"vars.{workflow_switch} != 'true'"]
    if job_switch:
        pause_terms.append(f"vars.{job_switch} != 'true'")
    if inner:
        body = " && ".join([*pause_terms, f"({inner})"])
    else:
        body = " && ".join(pause_terms)
    expr = f"{_FRAGMENT_DISPATCH} || ({body})"
    return f"${{{{ {expr} }}}}"


def _inner_from_job_if(existing_if: Any, job_switch: str | None) -> str:
    if existing_if is None:
        return ""
    parsed = parse_fragment_inner(_normalize_if_text(existing_if))
    if parsed is not None:
        inner = parsed
    else:
        inner = strip_expression_wrappers(_normalize_if_text(existing_if))
    if job_switch:
        lone = f"vars.{job_switch} != 'true'"
        compact = inner.replace(" ", "").replace('"', "'")
        if compact == lone.replace(" ", ""):
            return ""
    return inner


def plan_renders(
    root: Path,
    registry: dict[str, Any],
    *,
    workflows_dir: Path | None = None,
) -> list[JobRenderPlan]:
    wf_dir = workflows_dir or (root / ".github" / "workflows")
    wf_states = _active_workflow_states(registry)
    wf_switch_map, job_rows = _registry_index(registry)
    plans: list[JobRenderPlan] = []
    for path in sorted(wf_dir.glob("*.yml")):
        rel = path.relative_to(root).as_posix()
        state = wf_states.get(rel, "live")
        if state in ("retired", "paused-manually"):
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(doc, dict) or not workflow_fires_push_pr_schedule(doc):
            continue
        wf_var = wf_switch_map.get(rel) or workflow_pause_var(path)
        jobs = doc.get("jobs")
        if not isinstance(jobs, dict):
            continue
        for job_id, job_def in jobs.items():
            if not isinstance(job_def, dict):
                continue
            row = job_rows.get((rel, job_id))
            row_id = str(row.get("id") if row else f"{path.stem}.{job_id}")
            cost = str(row.get("cost") if row else "low")
            job_switch: str | None = None
            if cost == "high":
                sw = row.get("switch") if row else None
                if isinstance(sw, str) and sw:
                    job_switch = sw
                else:
                    job_switch = job_pause_var(path, job_id)
            existing_if = job_def.get("if")
            inner = _inner_from_job_if(existing_if, job_switch)
            plans.append(
                JobRenderPlan(
                    workflow_rel=rel,
                    job_id=job_id,
                    row_id=row_id,
                    cost=cost,
                    workflow_switch=wf_var,
                    job_switch=job_switch,
                    inner=inner,
                )
            )
    return plans


def completeness_findings(
    root: Path,
    registry: dict[str, Any],
    *,
    workflows_dir: Path | None = None,
) -> list[str]:
    findings: list[str] = []
    wf_dir = workflows_dir or (root / ".github" / "workflows")
    wf_states = _active_workflow_states(registry)
    _, job_rows = _registry_index(registry)
    for path in sorted(wf_dir.glob("*.yml")):
        rel = path.relative_to(root).as_posix()
        state = wf_states.get(rel, "live")
        if state in ("retired", "paused-manually"):
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            findings.append(f"cannot read workflow {rel}: {exc}")
            continue
        if not isinstance(doc, dict) or not workflow_fires_push_pr_schedule(doc):
            continue
        jobs = doc.get("jobs")
        if not isinstance(jobs, dict):
            continue
        for job_id, job_def in jobs.items():
            if not isinstance(job_def, dict):
                continue
            row = job_rows.get((rel, job_id))
            if row is None:
                findings.append(
                    f"completeness: {rel} job {job_id!r} has no ci-job registry row"
                )
                continue
            if_text = _normalize_if_text(job_def.get("if"))
            if not has_render_fragment(if_text):
                findings.append(
                    f"completeness: {rel} job {job_id!r} (row {row.get('id')}) lacks pause fragment"
                )
    return findings


def _job_block_indent(lines: list[str], job_line_idx: int) -> str:
    m = re.match(r"^(\s+)", lines[job_line_idx])
    return m.group(1) if m else "    "


def _find_job_if_range(lines: list[str], job_line_idx: int, indent: str) -> tuple[int, int] | None:
    """Return [start, end) line indices of the ``if:`` block for this job, if present."""
    child_indent = indent + "  "
    i = job_line_idx + 1
    while i < len(lines):
        line = lines[i]
        if re.match(r"^  [\w-]+:\s*$", line) and not line.startswith(indent):
            break
        if line.startswith(child_indent) and line.strip().startswith("if:"):
            start = i
            i += 1
            folded = lines[start].strip().endswith(">-") or lines[start].strip().endswith("|")
            while folded and i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    i += 1
                    continue
                if nxt.startswith(child_indent + " ") or nxt.startswith(child_indent + "\t"):
                    i += 1
                    continue
                break
            if not folded:
                i = start + 1
            return start, i
        if line.startswith(child_indent):
            i += 1
            continue
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        break
    return None


def _render_comment_lines(indent: str, row_id: str) -> list[str]:
    return [
        f"{indent}# {_RENDER_MARKER} {row_id}",
        f"{indent}# render: {_RENDER_CMD}",
    ]


def render_workflow_file(
    path: Path,
    plans: list[JobRenderPlan],
    *,
    dry_run: bool = False,
) -> bool:
    """Apply render plans for one workflow file. Returns whether the file changed."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    job_plans = {p.job_id: p for p in plans if p.workflow_rel.endswith(path.name)}
    if not job_plans:
        return False
    changed = False
    in_jobs = False
    i = 0
    while i < len(lines):
        if re.match(r"^jobs:\s*$", lines[i]):
            in_jobs = True
            i += 1
            continue
        if not in_jobs:
            i += 1
            continue
        m = re.match(r"^  ([\w-]+):\s*$", lines[i])
        if not m or m.group(1) not in job_plans:
            i += 1
            continue
        job_id = m.group(1)
        job_line_idx = i
        plan = job_plans[job_id]
        indent = _job_block_indent(lines, job_line_idx)
        child_indent = indent + "  "
        new_if = build_fragment(
            inner=plan.inner,
            workflow_switch=plan.workflow_switch,
            job_switch=plan.job_switch,
        )
        if_range = _find_job_if_range(lines, job_line_idx, indent)
        comment_lines = [
            ln + ("\n" if not ln.endswith("\n") else "")
            for ln in _render_comment_lines(child_indent, plan.row_id)
        ]
        if_line = f"{child_indent}if: {new_if}\n"
        if if_range:
            start, end = if_range
            # Drop existing render comments immediately above if:
            drop = start
            while drop > i + 1:
                prev_line = lines[drop - 1]
                if not prev_line.startswith(child_indent):
                    break
                prev = prev_line.strip()
                if prev.startswith(f"# {_RENDER_MARKER}") or prev.startswith("# render:"):
                    drop -= 1
                    continue
                break
            new_block = comment_lines + [if_line]
            old_block = "".join(lines[drop:end])
            new_text = "".join(new_block)
            if old_block != new_text:
                lines[drop:end] = new_block
                changed = True
            i = job_line_idx + 1
            while i < len(lines) and not re.match(r"^  [\w-]+:\s*$", lines[i]):
                i += 1
            continue
        # Insert if: as the first key under the job (before runs-on, needs, steps, …).
        child_indent = indent + "  "
        insert_at = i + 1
        while insert_at < len(lines):
            line = lines[insert_at]
            if not line.strip():
                insert_at += 1
                continue
            stripped = line.strip()
            if stripped.startswith("#"):
                insert_at += 1
                continue
            if line.startswith(child_indent):
                break
            if re.match(r"^  [\w-]+:\s*$", line):
                break
            insert_at += 1
        insert_block = comment_lines + [if_line]
        lines[insert_at:insert_at] = insert_block
        changed = True
        i = job_line_idx + 1
        while i < len(lines) and not re.match(r"^  [\w-]+:\s*$", lines[i]):
            i += 1
    if changed and not dry_run:
        path.write_text("".join(lines), encoding="utf-8")
    return changed


def render_all(
    root: Path,
    registry: dict[str, Any],
    *,
    workflows_dir: Path | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Render every planned job. Returns workflow relative paths that changed."""
    plans = plan_renders(root, registry, workflows_dir=workflows_dir)
    by_file: dict[str, list[JobRenderPlan]] = {}
    for plan in plans:
        by_file.setdefault(plan.workflow_rel, []).append(plan)
    changed: list[str] = []
    wf_dir = workflows_dir or (root / ".github" / "workflows")
    for rel, file_plans in sorted(by_file.items()):
        path = root / rel
        if not path.is_file():
            path = wf_dir / Path(rel).name
        if render_workflow_file(path, file_plans, dry_run=dry_run):
            changed.append(rel)
    return changed
