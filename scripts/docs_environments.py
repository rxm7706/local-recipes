#!/usr/bin/env python3
"""Generator: ``docs/reference/environments.md`` from ``pixi.toml``'s
``[environments]`` table (Story 30.3, spec-pyforge-doctor CAP-84).

The environments-first complement to ``docs_pixi_tasks.py``'s tasks-first
view: for every declared environment, its composed feature list and
whether it opts out of the fat default `[dependencies]` table
(``no-default-feature``). Purely mechanical -- ``tomllib`` reads
``pixi.toml`` directly; no environment name, feature list or flag below is
typed by hand.

Usage::

    python scripts/docs_environments.py            # regenerate + write + stamp
    python scripts/docs_environments.py --check     # exit 0 if current, 1 if stale
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docs_gen_common as common  # noqa: E402

PAGE_REL = "reference/environments.md"
GENERATOR_REL = "scripts/docs_environments.py"
TASK_NAME = "docs-environments"

_INTRO = """\
# Pixi environments

Every environment `pixi.toml` declares under `[environments]`, and the
feature list it composes. A task declared under `[feature.<name>.tasks]`
runs under every environment whose feature list includes `<name>` --
`docs/how-to/pixi-tasks.md` is the tasks-first view of the same data.

"no-default-feature" means the environment excludes the fat default
`[dependencies]` table (python 3.14 + pixi + conda + pip + uv) -- a lean,
purpose-built environment carrying only its own declared features.
"""


def _environments(root: Path) -> dict[str, dict]:
    data = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for name, spec in data.get("environments", {}).items():
        if isinstance(spec, dict):
            out[name] = {
                "features": list(spec.get("features", [])),
                "no_default_feature": bool(spec.get("no-default-feature", False)),
            }
        else:
            out[name] = {"features": list(spec), "no_default_feature": False}
    return out


def render(root: Path, stamp: dict[str, str]) -> str:
    environments = _environments(root)

    lines = [
        common.render_header(GENERATOR_REL, TASK_NAME, stamp),
        "",
        _INTRO,
        f"{len(environments)} environments, as of this render.\n",
        "| Environment | Features | no-default-feature |",
        "|---|---|---|",
    ]
    for name in sorted(environments):
        env = environments[name]
        features = ", ".join(f"`{f}`" for f in env["features"])
        flag = "yes" if env["no_default_feature"] else ""
        lines.append(f"| `{name}` | {features} | {flag} |")
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
