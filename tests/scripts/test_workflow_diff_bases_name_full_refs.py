"""marshal Story 63.1 (spec-pyforge-core CAP-10), with mason Story 18.1 and doctor Story 32.1: no workflow builds a diff
base from a short ``origin/<base>``.

Git resolves a short name to ``refs/tags/<n>`` and ``refs/heads/<n>`` before ``refs/remotes/<n>``, and a checkout with
``fetch-depth: 0`` fetches tags, so a pushed tag named ``origin/main`` would stand in for the remote-tracking ref: the
station-tests lane would select no suite, the coverage gate no station, the recipe CI no recipe. Every base built from
the PR's base branch therefore names ``refs/remotes/origin/<base>``. Stdlib only: this runs in ``pyforge-ci``."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github" / "workflows"

#: ``origin/`` followed by a GitHub expression (``${{ github.base_ref }}``) or a shell variable (``${GITHUB_BASE_REF}``,
#: ``$BASE``) -- the shapes a workflow builds a base-branch ref from -- unless it already sits under ``refs/remotes/``.
SHORT_BASE = re.compile(r"(?<!refs/remotes/)(?<![\w/.-])origin/\$(?:\{\{|\{|[A-Za-z_])")


def _offenders(text: str) -> list[tuple[int, str]]:
    return [
        (number, line.strip())
        for number, line in enumerate(text.splitlines(), 1)
        if not line.lstrip().startswith("#") and SHORT_BASE.search(line)
    ]


def test_no_workflow_builds_a_diff_base_from_a_short_origin_name() -> None:
    workflows = sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")])
    assert workflows, f"no workflows found under {WORKFLOWS}"
    found = [
        f"{path.name}:{number}: {line}"
        for path in workflows
        for number, line in _offenders(path.read_text(encoding="utf-8"))
    ]
    assert found == [], "diff bases must name refs/remotes/origin/<base>, not origin/<base>:\n" + "\n".join(found)


def test_the_scan_sees_each_short_shape_and_passes_the_full_ref() -> None:
    assert _offenders('BASE="origin/${GITHUB_BASE_REF}"')
    assert _offenders("git diff --name-only origin/${{ github.base_ref }}...HEAD -- 'recipes/*'")
    assert _offenders("git diff origin/$BASE_BRANCH...HEAD")
    assert not _offenders('BASE="refs/remotes/origin/${GITHUB_BASE_REF}"')
    assert not _offenders("git diff --name-only refs/remotes/origin/${{ github.base_ref }}...HEAD")
    assert not _offenders('# was BASE="origin/${GITHUB_BASE_REF}"')
    assert not _offenders("git fetch --no-tags --depth=1 origin +refs/heads/main:refs/remotes/origin/main")
