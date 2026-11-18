"""Generator: ``docs/reference/github-workflows.md`` from the workflow files
under ``.github/workflows/`` (doctor Story 59.1, spec-pyforge-doctor CAP-84:
the sixth reference-page generator, in the Story 30.3 pattern).

One row per workflow file: its ``name:``, its triggers (``on:``), what gates
it, and its job ids. Purely mechanical -- PyYAML reads each file; no workflow
name, trigger, path filter or job id below is typed by hand.

What "gates it" means here is only what the file itself states:

* **path-gated** -- a ``push``/``pull_request`` trigger carries ``paths`` or
  ``paths-ignore``;
* **manual only** -- every trigger is ``workflow_dispatch`` or
  ``workflow_call``;
* **pause switches** -- every ``PAUSE_*`` repository variable an expression
  in the file reads. Whether a switch is *set* is a repository setting, not a
  fact of the file, so this page never says a workflow "is paused".

YAML caveat: YAML 1.1 reads the bare key ``on`` as the boolean ``True``, so
PyYAML hands back ``{True: ...}`` for a workflow's trigger block.
:func:`_triggers` looks the block up under both keys.

Usage::

    python scripts/docs_github_workflows.py            # regenerate + write + stamp
    python scripts/docs_github_workflows.py --check     # exit 0 if current, 1 if stale
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docs_gen_common as common

PAGE_REL = "reference/github-workflows.md"
GENERATOR_REL = "scripts/docs_github_workflows.py"
TASK_NAME = "docs-github-workflows"
WORKFLOWS_REL = ".github/workflows"

_INTRO = """\
# GitHub workflows

Every workflow file under `.github/workflows/`: its `name:`, what triggers
it, what gates it, and its job ids. Read from the files themselves on each
render.

The **Gating** column states only what a file says about itself:

- **path-gated**: a `push` or `pull_request` trigger carries a `paths` (or
  `paths-ignore`) filter, so the workflow starts only for a matching diff.
  The filters are listed under [Path filters](#path-filters).
- **manual only**: every trigger is `workflow_dispatch` or `workflow_call`.
- **pause switches**: the `PAUSE_*` repository variables the file's
  expressions read. Whether a switch is set is a repository setting, not a
  fact of the file: `pixi run -e pyforge-steward pyforge steward ci status`
  reports the live state, and [How to pause CI](../how-to/pause-ci.md)
  explains the switches. The registry of record is
  `docs/governance/ci-surfaces.yaml`.

To run the on-demand recipe builds, see
[GitHub Actions recipe CI](../how-to/github-actions-recipe-ci.md).
"""

# Rendered first, in this order; any other event follows alphabetically.
_EVENT_ORDER = (
    "pull_request",
    "pull_request_target",
    "push",
    "schedule",
    "workflow_dispatch",
    "workflow_call",
)
_PATH_EVENTS = ("pull_request", "pull_request_target", "push")
_MANUAL_EVENTS = frozenset({"workflow_dispatch", "workflow_call"})
_PAUSE_RE = re.compile(r"\bPAUSE_[A-Z0-9_]+\b")


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)]


def _cell(text: str) -> str:
    """Make ``text`` safe inside one Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ")


def _code_list(items: list[str]) -> str:
    return ", ".join(f"`{item}`" for item in items)


def _triggers(doc: dict) -> dict[str, Any]:
    """A workflow's ``on:`` block as ``{event: config-or-None}``.

    Looks under ``True`` first (what PyYAML makes of a bare ``on:`` key) and
    then under the string ``"on"`` (a quoted key). The three spellings GitHub
    accepts -- a string, a list of event names, a mapping -- all come back
    as one mapping."""
    block = doc.get(True) if True in doc else doc.get("on")
    if block is None:
        return {}
    if isinstance(block, str):
        return {block: None}
    if isinstance(block, list):
        return {str(event): None for event in block}
    if isinstance(block, dict):
        return {str(event): config for event, config in block.items()}
    return {}


def _ordered_events(triggers: dict[str, Any]) -> list[str]:
    known = [event for event in _EVENT_ORDER if event in triggers]
    return known + sorted(event for event in triggers if event not in _EVENT_ORDER)


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _describe_event(event: str, config: Any) -> str:
    """One trigger, summarised: branches and crons spelled out, path filters
    counted (they are listed in full under ``## Path filters``)."""
    notes: list[str] = []
    if event == "schedule":
        crons = [
            str(entry.get("cron"))
            for entry in config or []
            if isinstance(entry, dict) and "cron" in entry
        ]
        if crons:
            notes.append("cron " + _code_list(crons))
    elif isinstance(config, dict):
        for key in ("branches", "branches-ignore", "tags", "tags-ignore", "types"):
            values = _as_list(config.get(key))
            if values:
                notes.append(f"{key} {_code_list(values)}")
        for key, noun in (("paths", "path"), ("paths-ignore", "ignored path")):
            values = _as_list(config.get(key))
            if values:
                notes.append(_plural(len(values), noun))
        inputs = config.get("inputs")
        if isinstance(inputs, dict) and inputs:
            notes.append("inputs " + _code_list([str(name) for name in inputs]))
    return f"`{event}` ({'; '.join(notes)})" if notes else f"`{event}`"


def _strings(node: Any):
    """Every string scalar in a parsed YAML document -- values only, so a
    comment that merely mentions a switch never counts as reading it."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings(value)


def _pause_switches(doc: dict) -> list[str]:
    found: set[str] = set()
    for text in _strings(doc):
        found.update(_PAUSE_RE.findall(text))
    return sorted(found)


def _path_filters(triggers: dict[str, Any]) -> list[tuple[list[str], str, list[str]]]:
    """``(events, key, paths)`` rows -- events that carry the identical
    filter are merged into one row, so a ``pull_request``/``push`` pair with
    the same ``paths`` is listed once."""
    rows: list[tuple[list[str], str, list[str]]] = []
    for key in ("paths", "paths-ignore"):
        for event in _PATH_EVENTS:
            config = triggers.get(event)
            if not isinstance(config, dict):
                continue
            paths = _as_list(config.get(key))
            if not paths:
                continue
            for events, row_key, row_paths in rows:
                if row_key == key and row_paths == paths:
                    events.append(event)
                    break
            else:
                rows.append(([event], key, paths))
    return rows


def _gating(triggers: dict[str, Any], switches: list[str]) -> str:
    parts: list[str] = []
    if _path_filters(triggers):
        parts.append("path-gated")
    if triggers and set(triggers) <= _MANUAL_EVENTS:
        parts.append("manual only")
    if switches:
        parts.append("pause switches " + _code_list(switches))
    return "; ".join(parts)


def _jobs(doc: dict) -> str:
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return ""
    cells: list[str] = []
    for job_id, job in jobs.items():
        uses = job.get("uses") if isinstance(job, dict) else None
        if isinstance(uses, str) and uses:
            cells.append(f"`{job_id}` (calls `{uses.rsplit('/', 1)[-1]}`)")
        else:
            cells.append(f"`{job_id}`")
    return ", ".join(cells)


def _workflow_files(root: Path) -> list[Path]:
    directory = root / WORKFLOWS_REL
    if not directory.is_dir():
        return []
    return sorted(
        (
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix in (".yml", ".yaml")
        ),
        key=lambda path: path.name,
    )


def _load(path: Path) -> dict | None:
    """The parsed workflow, or ``None`` when the file is not a YAML mapping
    (rendered as a row that says so, never a crash)."""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    return doc if isinstance(doc, dict) else None


def render(root: Path, stamp: dict[str, str]) -> str:
    workflows = [(path.name, _load(path)) for path in _workflow_files(root)]

    lines = [
        common.render_header(GENERATOR_REL, TASK_NAME, stamp),
        "",
        _INTRO,
        f"{_plural(len(workflows), 'workflow')}, as of this render.\n",
        "| Workflow | Name | Triggers | Gating | Jobs |",
        "|---|---|---|---|---|",
    ]
    filters: list[str] = []
    for filename, doc in workflows:
        if doc is None:
            lines.append(f"| `{filename}` | *(not a YAML mapping)* |  |  |  |")
            continue
        triggers = _triggers(doc)
        name = _cell(str(doc["name"])) if doc.get("name") is not None else "*(none)*"
        described = ", ".join(
            _describe_event(event, triggers[event])
            for event in _ordered_events(triggers)
        )
        gating = _gating(triggers, _pause_switches(doc))
        lines.append(
            f"| `{filename}` | {name} | {_cell(described)} | {_cell(gating)} | {_cell(_jobs(doc))} |"
        )

        rows = _path_filters(triggers)
        if rows:
            filters += [f"### `{filename}`", ""]
            for events, key, paths in rows:
                filters.append(f"- {_code_list(events)} `{key}`: {_code_list(paths)}")
            filters.append("")
    lines.append("")

    lines += ["## Path filters", ""]
    if filters:
        lines += filters
    else:
        lines += ["None -- no workflow carries a `paths` or `paths-ignore` filter.", ""]

    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="report staleness; never write"
    )
    common.configure_root_argument(parser)
    args = parser.parse_args()

    root = common.resolve_root(args)
    stamp, content = common.stamped_render(
        root, PAGE_REL, lambda stamp: render(root, stamp)
    )
    return common.write_generated_page(
        root, PAGE_REL, content, check=args.check, stamp=stamp
    )


if __name__ == "__main__":
    sys.exit(main())
