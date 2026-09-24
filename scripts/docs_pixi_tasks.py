#!/usr/bin/env python3
"""Generator: ``docs/how-to/pixi-tasks.md`` from ``pixi.toml``'s own task
tables and ``[environments]`` table (Story 30.3, spec-pyforge-doctor
CAP-84).

The page was previously hand-written and already stale (it under-reported
the task surface and had drifted on which stations ship in which
environment -- see the sibling ``docs_station_cli.py``'s docstring for a
concrete instance of that same class of drift). This generator instead
reads ``pixi.toml`` directly via ``tomllib`` (stdlib -- no dependency this
script needs beyond the standard library plus ``docs_gen_common``'s tiny
``yaml``/``git`` surface): every ``[feature.<name>.tasks.<task>]`` table's
``description``, grouped by feature, and every environment's composed
feature list, to answer "which environment(s) run this task" per feature
mechanically rather than by a hand-maintained claim.

Usage::

    python scripts/docs_pixi_tasks.py            # regenerate + write + stamp
    python scripts/docs_pixi_tasks.py --check     # exit 0 if current, 1 if stale

Never generates from a model: every task name, description and environment
membership below comes straight from ``pixi.toml``'s own tables.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docs_gen_common as common  # noqa: E402

PAGE_REL = "how-to/pixi-tasks.md"
GENERATOR_REL = "scripts/docs_pixi_tasks.py"
TASK_NAME = "docs-pixi-tasks"

# A `scripts/`-rooted .sh/.py path referenced from a task's own `cmd` string
# (e.g. `bash scripts/ensure-bmad-preflight.sh`) -- checked for existence so
# a task shelling out to a script that was since deleted is flagged, not
# silently listed as an ordinary task (found live: `bmad-preflight` still
# shells to scripts/ensure-bmad-preflight.sh, which does not exist).
_SCRIPT_REF_RE = re.compile(r"scripts/[A-Za-z0-9_./-]+\.(?:sh|py)")

_INTRO = """\
# Pixi tasks

Task-oriented reference for the pixi task surface. Everything is defined in
`pixi.toml`: a task lives under one or more `[feature.<name>.tasks]` tables,
and an environment (`[environments]`) composes a list of features -- a task
is runnable under an environment only when that environment's feature list
includes the feature the task is declared under. This page groups tasks by
their declaring feature and lists, for each feature, every environment that
composes it.

Pass extra args after `--`:

```bash
pixi run -e <env> <task> -- [args]
```

`docs/reference/environments.md` is the environments-first view of the same
`[environments]` table (composed features per environment); this page is
the tasks-first view (environments per feature).
"""


def _pixi_data(root: Path) -> dict:
    return tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))


def _feature_environments(data: dict) -> dict[str, list[str]]:
    """feature name -> sorted list of environment names that compose it."""
    out: dict[str, set[str]] = {}
    for env_name, env_spec in data.get("environments", {}).items():
        features = env_spec["features"] if isinstance(env_spec, dict) else env_spec
        for feature in features:
            out.setdefault(feature, set()).add(env_name)
    return {feature: sorted(envs) for feature, envs in out.items()}


def _feature_tasks(data: dict) -> dict[str, dict[str, dict]]:
    """feature name -> {task name -> task spec dict}, plus a synthetic
    "(top-level)" feature for any bare ``[tasks]`` table."""
    out: dict[str, dict[str, dict]] = {}
    top_level = data.get("tasks") or {}
    if top_level:
        out["(top-level)"] = {
            name: (spec if isinstance(spec, dict) else {"cmd": spec}) for name, spec in top_level.items()
        }
    for feature_name, feature_body in data.get("feature", {}).items():
        tasks = feature_body.get("tasks") or {}
        if not tasks:
            continue
        out[feature_name] = {
            name: (spec if isinstance(spec, dict) else {"cmd": spec}) for name, spec in tasks.items()
        }
    return out


def _missing_script_refs(root: Path, cmd: object) -> list[str]:
    """`scripts/*.sh`/`scripts/*.py` paths a task's own `cmd` string
    references that do not exist on disk, in first-seen order."""
    if not isinstance(cmd, str):
        return []
    missing: list[str] = []
    for match in _SCRIPT_REF_RE.finditer(cmd):
        ref = match.group(0)
        if ref not in missing and not (root / ref).is_file():
            missing.append(ref)
    return missing


def render(root: Path, stamp: dict[str, str]) -> str:
    data = _pixi_data(root)
    feature_tasks = _feature_tasks(data)
    feature_envs = _feature_environments(data)

    total_tasks = sum(len(tasks) for tasks in feature_tasks.values())
    lines = [
        common.render_header(GENERATOR_REL, TASK_NAME, stamp),
        "",
        _INTRO,
        f"{total_tasks} tasks across {len(feature_tasks)} features, as of this render.\n",
    ]

    for feature_name in sorted(feature_tasks):
        tasks = feature_tasks[feature_name]
        envs = feature_envs.get(feature_name, [])
        env_note = ", ".join(f"`{e}`" for e in envs) if envs else "*(not composed by any environment)*"
        lines.append(f"## Feature: `{feature_name}`")
        lines.append("")
        lines.append(f"Environments: {env_note}")
        lines.append("")
        lines.append("| Task | Description |")
        lines.append("|---|---|")
        for task_name in sorted(tasks):
            description = tasks[task_name].get("description")
            cell = description.replace("|", "\\|").replace("\n", " ") if description else "*(no description)*"
            missing = _missing_script_refs(root, tasks[task_name].get("cmd"))
            if missing:
                refs = ", ".join(f"`{ref}`" for ref in missing)
                cell += f" — ⚠ script not found: {refs}"
            lines.append(f"| `{task_name}` | {cell} |")
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report staleness; never write")
    args = parser.parse_args()

    stamp = common.head_stamp(common.REPO_ROOT)
    content = render(common.REPO_ROOT, stamp)
    return common.write_generated_page(common.REPO_ROOT, PAGE_REL, content, check=args.check, stamp=stamp)


if __name__ == "__main__":
    sys.exit(main())
