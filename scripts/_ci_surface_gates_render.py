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


def _unwrap_redundant_parens(expr: str) -> str:
    """Strip outer ``(…)`` wrappers when the whole expression is one parenthesized group."""
    expr = expr.strip()
    while len(expr) >= 2 and expr.startswith("(") and expr.endswith(")"):
        depth = 0
        for i, ch in enumerate(expr):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i != len(expr) - 1:
                    return expr
        expr = expr[1:-1].strip()
    return expr


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
    return _unwrap_redundant_parens(rest)


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
        compact_inner = inner.replace(" ", "").replace('"', "'")
        if f"vars.{job_switch}" not in compact_inner:
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
        inner = _unwrap_redundant_parens(parsed)
    else:
        inner = _unwrap_redundant_parens(strip_expression_wrappers(_normalize_if_text(existing_if)))
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


def _render_block_for_plan(plan: JobRenderPlan) -> str:
    child_indent = "    "
    new_if = build_fragment(
        inner=plan.inner,
        workflow_switch=plan.workflow_switch,
        job_switch=plan.job_switch,
    )
    lines = _render_comment_lines(child_indent, plan.row_id) + [f"{child_indent}if: {new_if}"]
    return "\n".join(lines) + "\n"


def render_workflow_file(
    path: Path,
    plans: list[JobRenderPlan],
    *,
    dry_run: bool = False,
) -> bool:
    """Apply render plans for one workflow file. Returns whether the file changed."""
    text = path.read_text(encoding="utf-8")
    job_plans = {p.job_id: p for p in plans if p.workflow_rel.endswith(path.name)}
    if not job_plans:
        return False
    changed = False
    for job_id, plan in sorted(job_plans.items(), key=lambda kv: (-len(kv[0]), -text.find(f"  {kv[0]}:\n"))):
        new_if = build_fragment(
            inner=plan.inner,
            workflow_switch=plan.workflow_switch,
            job_switch=plan.job_switch,
        )
        block = _render_block_for_plan(plan)
        marker = f"    # {_RENDER_MARKER} {plan.row_id}"
        if marker in text:
            pattern = (
                rf"(    # {_RENDER_MARKER} {re.escape(plan.row_id)}\n"
                rf"    # render: {re.escape(_RENDER_CMD)}\n"
                rf"    if: )(\$\{{\{{.*?\}}\}} *\n)"
            )
            m = re.search(pattern, text, flags=re.DOTALL)
            if m and _normalize_if_text(m.group(2)) == _normalize_if_text(new_if):
                continue
            new_text, n = re.subn(pattern, rf"\1{new_if}\n", text, count=1, flags=re.DOTALL)
            if n and new_text != text:
                text = new_text
                changed = True
            continue
        # Replace an existing job if: (single-line ${{ }} or folded >- block).
        if_pat = (
            rf"(  {re.escape(job_id)}:\n"
            rf"(?:    #[^\n]*\n)*"
            rf"    if: (?:>\-\n(?:      .+\n)+?|\$\{{\{{[^{{}}]*\}}\}} *\n))"
        )
        new_text, n = re.subn(if_pat, rf"  {job_id}:\n{block}", text, count=1)
        if n:
            text = new_text
            changed = True
            continue
        # Insert before the first job property (runs-on / needs / steps / …).
        insert_pat = (
            rf"(  {re.escape(job_id)}:\n)"
            rf"((?:    #[^\n]*\n)*)"
            rf"(    (?:name|runs-on|needs|if|steps|strategy|env|timeout-minutes):)"
        )
        new_text, n = re.subn(insert_pat, rf"\1\2{block}\3", text, count=1)
        if n:
            text = new_text
            changed = True
    # Drop a legacy if: line left beside the rendered fragment (needs/if ordering in some workflows).
    deduped, n = re.subn(
        r"(    if: \$\{\{ github\.event_name == 'workflow_dispatch' \|\| \(vars\.PAUSE_ALL_CI[^\n]+\n)"
        r"(    needs:[^\n]+\n)?"
        r"    if: (?!.*PAUSE_ALL_CI)([^\n]+\n)",
        r"\1\2",
        text,
    )
    if n:
        text = deduped
        changed = True
    if changed and not dry_run:
        path.write_text(text, encoding="utf-8")
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
