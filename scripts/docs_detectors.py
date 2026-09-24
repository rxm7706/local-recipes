#!/usr/bin/env python3
"""Generator: ``docs/reference/detectors.md`` from ``scripts/detectors.py``'s
own registry (Story 30.3, spec-pyforge-doctor CAP-84) -- the SAME
``discover()`` scan and ``_DOCTOR_SOURCE_TASKS`` pairing that
``detectors``/``detectors-ci`` themselves run from, imported directly
(both live under ``scripts/``, so this is a sibling-module import, not a
reach into ``pyforge.doctor`` -- AD-5's "cannot import scripts/ from inside
the installed package" restriction applies the other way around, to
``pyforge.doctor``, not to a plain script importing another plain script).
No detector's name, scope or pixi task is duplicated by hand here; a
registry gap ``discover()`` itself reports is rendered too, not hidden.

Enriches each Doctor-owned source with its declared scope
(``pyforge.doctor.sources.scope_for``) when ``pyforge.doctor`` happens to
be importable in the running environment; degrades to "unknown" for that
column, never a crash or a WARN, when it is not (mirrors
``scripts/detectors.py``'s own ``_doctor_sources()`` fail-open discipline).

Usage::

    python scripts/docs_detectors.py            # regenerate + write + stamp
    python scripts/docs_detectors.py --check     # exit 0 if current, 1 if stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docs_gen_common as common  # noqa: E402
import detectors as detectors_registry  # noqa: E402

PAGE_REL = "reference/detectors.md"
GENERATOR_REL = "scripts/docs_detectors.py"
TASK_NAME = "docs-detectors"

_INTRO = """\
# Detectors

Every detector `pixi run -e pyforge-guild detectors` (or the CI subset,
`detectors-ci`) can run, in two halves: scripts AST-scanned from
`scripts/*_check.py` and `docs/dashboard/check_*.py`, and the ten-plus
sources that live inside the installed `pyforge.doctor` package with no
file left to scan. See `docs/reference/judgement-vocabulary.md` for what
`scope`, exit codes and the `2`-inversion trap mean.
"""


def _scope_lookup() -> dict[str, str]:
    try:
        from pyforge.doctor.models import Source
        from pyforge.doctor.sources import scope_for
    except ImportError:
        return {}
    out: dict[str, str] = {}
    for name, _task in detectors_registry._DOCTOR_SOURCE_TASKS:
        try:
            out[name] = scope_for(Source(name))
        except ValueError:
            out[name] = "unknown"
    return out


def render(root: Path, stamp: dict[str, str]) -> str:
    scanned, registry_findings = detectors_registry.discover()
    doctor_scopes = _scope_lookup()

    lines = [
        common.render_header(GENERATOR_REL, TASK_NAME, stamp),
        "",
        _INTRO,
        f"{len(scanned)} scanned scripts, {len(detectors_registry._DOCTOR_SOURCE_TASKS)} "
        "doctor-owned sources, as of this render.\n",
        "## Registry gaps",
        "",
    ]
    if registry_findings:
        lines += [f"- {finding}" for finding in registry_findings]
    else:
        lines.append("None -- every scanned script declares a valid `DETECTOR` and has a pixi task.")
    lines.append("")

    lines += ["## Scanned scripts (`scripts/*_check.py`, `docs/dashboard/check_*.py`)", ""]
    lines += ["| Name | Scope | Pixi task | Script |", "|---|---|---|---|"]
    for row in sorted(scanned, key=lambda r: r["name"]):
        task = f"`{row['task']}`" if row["task"] else "*(none)*"
        lines.append(f"| `{row['name']}` | `{row['scope']}` | {task} | `{row['path']}` |")
    lines.append("")

    lines += ["## Doctor-owned sources (`pyforge.doctor.sources`, no file to scan)", ""]
    lines += ["| Name | Scope | Pixi task |", "|---|---|---|"]
    for name, task in sorted(detectors_registry._DOCTOR_SOURCE_TASKS):
        scope = doctor_scopes.get(name, "unknown")
        lines.append(f"| `{name}` | `{scope}` | `{task}` |")
    lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report staleness; never write")
    args = parser.parse_args()

    stamp = common.head_stamp(common.REPO_ROOT)
    content = render(common.REPO_ROOT, stamp)
    return common.write_generated_page(common.REPO_ROOT, PAGE_REL, content, check=args.check)


if __name__ == "__main__":
    sys.exit(main())
