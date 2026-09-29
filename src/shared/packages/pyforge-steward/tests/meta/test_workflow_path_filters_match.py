"""DW-10-3-10 (deferred-work-ledger.md): a workflow's `on.pull_request.paths`
and `on.push.paths` filters are meant to stay identical -- GitHub Actions
supports no YAML anchors/aliases in workflow files, so every such pair in
this repo is duplicated by hand, and nothing previously enforced that a
one-sided edit couldn't silently stop gating either PRs or `main`. This
scans every `.github/workflows/*.yml` file that declares BOTH triggers with
a `paths:` filter and asserts the two lists are identical, catching future
drift mechanically instead of relying on someone noticing by eye -- the
`platform-ci.yml` list alone has drifted three times by its own comment's
account.

Deliberately repo-wide, not `platform-ci.yml`-only: the same
hand-duplicated shape recurs in `pyforge-station-tests.yml`, and the
ledger's own entry names a repo-wide detector as the durable remedy rather
than a one-file patch.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[6]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def _paths_filter(trigger: object) -> list[str] | None:
    """The `paths:` list of one `on.<event>` trigger block, or `None` when
    that trigger is absent, not a mapping (e.g. bare `push:` with no
    filter), or carries no `paths:` key -- any of which means this
    workflow's pair is not the shape this test polices.
    """
    if not isinstance(trigger, dict):
        return None
    paths = trigger.get("paths")
    if paths is None:
        return None
    return list(paths)


def test_workflow_pull_request_and_push_path_filters_match():
    workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    assert workflow_files, f"no workflow files found under {WORKFLOWS_DIR}"

    mismatches: dict[str, tuple[list[str], list[str]]] = {}
    checked: list[str] = []
    for workflow_path in workflow_files:
        document = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        # PyYAML's YAML-1.1 resolver parses the bare `on:` key as the
        # boolean `True`, not the string `"on"` -- GitHub's own trigger
        # key collides with a YAML boolean literal. Falling back to the
        # `True` key is not optional here; every workflow in this repo
        # hits it.
        triggers = document.get("on", document.get(True))
        if not isinstance(triggers, dict):
            continue
        pr_paths = _paths_filter(triggers.get("pull_request"))
        push_paths = _paths_filter(triggers.get("push"))
        if pr_paths is None or push_paths is None:
            continue
        checked.append(workflow_path.name)
        if pr_paths != push_paths:
            mismatches[workflow_path.name] = (pr_paths, push_paths)

    # A regression in the scan itself (e.g. the `True`-key fallback above
    # breaking) would otherwise silently pass by finding nothing to check --
    # this repo has had this exact duplicated-filter shape in at least two
    # workflows since before this test existed.
    assert checked, (
        "no workflow declared both a pull_request and a push paths filter -- "
        "this test's premise (DW-10-3-10) no longer holds, or the scan above "
        "is broken"
    )
    assert not mismatches, (
        f"on.pull_request.paths and on.push.paths must be identical (DW-10-3-10); mismatched workflow(s): {mismatches}"
    )
