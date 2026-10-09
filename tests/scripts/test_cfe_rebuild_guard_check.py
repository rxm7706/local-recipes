"""Unit tests for scripts/cfe_rebuild_guard_check.py (Story 6.2) -- covers every
row of the spec's I/O & Edge-Case Matrix against REAL tmp git repositories,
mirroring `test_mason_cfe_surface_check.py`'s fixture pattern (`_isolate_git_env`,
`_git`, `_init_repo`, `_commit_all`) and reaching the module the same way
(`scripts/` has no `__init__.py`).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import cfe_rebuild_guard_check as m  # noqa: E402  (sys.path must be set up first)

CFE_CHANGELOG = m.CFE_CHANGELOG

# A contributor's own git config must not decide whether this suite passes --
# see src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger.py for
# the full rationale.
_LEAKY_GIT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
)


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _LEAKY_GIT_VARS:
        monkeypatch.delenv(var, raising=False)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "cfe-rebuild-guard-test@example.com")
    _git(repo, "config", "user.name", "CFE Rebuild Guard Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")


def _write(repo: Path, rel: str, content: str = "x") -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_brief(repo: Path, rel: str, *, mirrored_shas: tuple[str, ...] = ()) -> None:
    """A schema-shaped skill brief; one `retro-mirror` amendment per SHA in
    `mirrored_shas`, each naming its retro in a `commit:` SHA field."""
    lines = [
        "name: test-skill",
        "version: 1.0.0",
        "source_repo: https://example.com",
        "language: python",
        "description: test",
        "forge_tier: Quick",
        "created: 2026-01-01",
        "created_by: test",
        "scope:",
        "  type: full-library",
        "  include: []",
        "  exclude: []",
        "  notes: test",
    ]
    if mirrored_shas:
        lines.append("  amendments:")
        for sha in mirrored_shas:
            lines.extend([
                "    - action: retro-mirror",
                f"      commit: {sha}",
                "      reason: mirrored a landed CFE retro",
            ])
    _write(repo, rel, "\n".join(lines) + "\n")


def _ensure_briefs_for_state(repo: Path, state: dict, retros: list[str] | None = None) -> None:
    """Write a complete brief for every slice with a `brief_path`, naming its
    `brief_mirrored_through` and every retro in `retros` so clause (b')
    stays quiet unless a test means to trip it."""
    slices = state.get("slices")
    if not isinstance(slices, list):
        return
    for sl in slices:
        if not isinstance(sl, dict):
            continue
        brief_path = sl.get("brief_path")
        if not brief_path:
            continue
        shas = list(retros or [])
        mirrored = sl.get("brief_mirrored_through")
        if isinstance(mirrored, str) and mirrored.strip() and mirrored.strip() not in shas:
            shas.append(mirrored.strip())
        _write_brief(repo, brief_path, mirrored_shas=tuple(shas))


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _slice(**overrides: object) -> dict:
    base = {
        "id": "slice-1",
        "status": "mapped",
        "equivalence": None,
        "brief_path": None,
        "brief_mirrored_through": None,
    }
    base.update(overrides)
    return base


def _state(slices: list[dict], **campaign_overrides: object) -> dict:
    campaign = {"endgame_declared": False, "callers": []}
    campaign.update(campaign_overrides)
    return {"campaign": campaign, "slices": slices}


def _pre_conditions(**overrides: str) -> dict:
    """All four clause-(d) pre-conditions at `status: "closed"` by default,
    one entry per `m.RE_SCOPE_GATE_PRE_CONDITION_KEYS` -- override individual
    keys' status (e.g. `a_ci_enforcement="open"`) to fabricate a partial
    close."""
    result = {key: {"status": "closed", "note": "test"}
              for key in m.RE_SCOPE_GATE_PRE_CONDITION_KEYS}
    for key, status in overrides.items():
        result[key] = {"status": status, "note": "test"}
    return result


# --- I/O & Edge-Case Matrix --------------------------------------------------


def test_clean_campaign_zero_findings(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state([
        _slice(id="slice-1", status="mapped"),
        _slice(id="slice-2", status="briefed", brief_path="briefs/slice-2.md",
               brief_mirrored_through=None),
    ], endgame_declared=False, callers=[])

    retros = m.retro_commits_since(tmp_path, baseline)
    assert retros == []
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_stale_equivalence_red_when_status_parallel_with_wrong_case(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state([_slice(id="slice-1", status="Parallel", equivalence="red")])
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)

    assert len(findings) == 1
    assert findings[0]["kind"] == "stale-equivalence"


def test_stale_equivalence_red(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state([_slice(id="slice-1", status="parallel", equivalence="red")])
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)

    assert len(findings) == 1
    f = findings[0]
    assert f["kind"] == "stale-equivalence"
    assert f["ref"] == "slice-1"


def test_stale_equivalence_missing_null(tmp_path: Path) -> None:
    """`equivalence` missing/null on a gated-status slice is also a finding,
    not only the literal "red"/"stale" strings named in the Intent."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state([_slice(id="slice-1", status="audited", equivalence=None)])
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)

    assert len(findings) == 1
    assert findings[0]["kind"] == "stale-equivalence"


def test_equivalence_green_on_gated_status_is_clean(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state([
        _slice(id="slice-1", status="parallel", equivalence="green"),
        _slice(id="slice-2", status="cut-over", equivalence="green"),
    ])
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_equivalence_ignored_for_non_gated_status(tmp_path: Path) -> None:
    """A `mapped`/`briefed`/`compiled` slice is never checked by clause (a),
    even with a red/stale/missing equivalence value."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state([_slice(id="slice-1", status="compiled", equivalence="red")])
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_unmirrored_retro_subject_independent(tmp_path: Path) -> None:
    """A commit landing after the --since boundary that touches both the CFE
    surface and CHANGELOG.md is a qualifying retro regardless of its subject
    line (deliberately NOT prefixed `retro:`, to prove clause (b) is
    subject-pattern-independent per the story's AC)."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    _write(tmp_path, ".claude/skills/conda-forge-expert/SKILL.md", "updated")
    _write(tmp_path, CFE_CHANGELOG, "## new entry")
    retro_sha = _commit_all(tmp_path, "docs: update the recipe-generation gotcha list")

    state = _state([_slice(id="slice-1", brief_path="briefs/slice-1.md",
                            brief_mirrored_through=None)])
    retros = m.retro_commits_since(tmp_path, baseline)
    assert retros == [retro_sha]

    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert len(findings) == 1
    f = findings[0]
    assert f["kind"] == "unmirrored-retro"
    assert f["ref"] == "slice-1"
    assert retro_sha[:10] in f["refs"]
    assert retro_sha[:10] in f["detail"]


def test_diff_name_status_resolves_rename_line_to_new_path(tmp_path: Path) -> None:
    """`diff_name_status` must resolve a 3-field rename/copy line
    (`R100\\told\\tnew`) to its NEW path, not a mis-split string with an
    embedded tab. Real `git diff-tree`/`git diff --name-status` calls in this
    module never request rename detection (no `-M`/`-C`), so this line shape
    cannot occur through `retro_commits_since` today -- git only emits it
    with `-M`/`-C` explicitly passed, confirmed directly (`git diff-tree
    --name-status -M` vs. without). This test constructs one directly to
    prove the parsing is correct regardless, so the code stays safe if a
    future change (or a differently-invoked git) ever produces one."""
    _init_repo(tmp_path)
    old_path = ".claude/skills/conda-forge-expert/CHANGELOG.md.old"
    _write(tmp_path, old_path, "## content long enough for git's similarity heuristic to match")
    _commit_all(tmp_path, "feat: baseline with old changelog name")

    _git(tmp_path, "mv", old_path, CFE_CHANGELOG)
    sha = _commit_all(tmp_path, "feat: rename changelog into place")

    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", "-M", "--root", sha],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    assert lines and lines[0].startswith("R"), (
        "fixture did not produce a rename line -- test setup assumption broken: "
        f"{result.stdout!r}")

    pairs = m._parse_name_status_lines(lines)
    assert any(path == CFE_CHANGELOG for _status, path in pairs)


def test_retro_without_changelog_touch_not_counted(tmp_path: Path) -> None:
    """A commit touching only the CFE surface (no CHANGELOG.md change) is not
    a qualifying retro -- no finding results from it."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    _write(tmp_path, ".claude/skills/conda-forge-expert/SKILL.md", "updated")
    _commit_all(tmp_path, "feat: surface-only change, no changelog")

    state = _state([_slice(id="slice-1", brief_path="briefs/slice-1.md",
                            brief_mirrored_through=None)])
    retros = m.retro_commits_since(tmp_path, baseline)
    assert retros == []

    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_mirrored_slice_stays_clean(tmp_path: Path) -> None:
    """A slice whose brief_mirrored_through already equals the newest
    qualifying retro's SHA is not a finding."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    _write(tmp_path, ".claude/skills/conda-forge-expert/SKILL.md", "updated")
    _write(tmp_path, CFE_CHANGELOG, "## new entry")
    retro_sha = _commit_all(tmp_path, "feat: mirrors already applied")

    state = _state([_slice(id="slice-1", brief_path="briefs/slice-1.md",
                            brief_mirrored_through=retro_sha)])
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_slice_with_null_brief_path_never_checked(tmp_path: Path) -> None:
    """Slices with brief_path: null are never checked by clause (b), even
    when a qualifying retro lands."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    _write(tmp_path, ".claude/skills/conda-forge-expert/SKILL.md", "updated")
    _write(tmp_path, CFE_CHANGELOG, "## new entry")
    _commit_all(tmp_path, "feat: a retro lands, but slice has no brief yet")

    state = _state([_slice(id="slice-1", brief_path=None, brief_mirrored_through=None)])
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_legacy_caller_at_endgame(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state(
        [_slice(id="slice-1")],
        endgame_declared=True,
        callers=[{"name": "generate_recipe_from_pypi", "resolves_to": "legacy"}],
    )
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)

    assert len(findings) == 1
    f = findings[0]
    assert f["kind"] == "legacy-caller-at-endgame"
    assert f["ref"] == "generate_recipe_from_pypi"


def test_legacy_caller_vacuous_while_endgame_not_declared(tmp_path: Path) -> None:
    """Clause (c) is only evaluated when campaign.endgame_declared is true --
    while false (true throughout Epic 6), a legacy caller is not a finding."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state(
        [_slice(id="slice-1")],
        endgame_declared=False,
        callers=[{"name": "generate_recipe_from_pypi", "resolves_to": "legacy"}],
    )
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_endgame_with_replacement_only_callers_is_clean(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state(
        [_slice(id="slice-1")],
        endgame_declared=True,
        callers=[{"name": "generate_recipe_from_pypi", "resolves_to": "replacement"}],
    )
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_gate_bypassed_order2_brief_with_open_precondition_red(tmp_path: Path) -> None:
    """A `brief_path`-set order-2 slice with even one open pre-condition is a
    `gate-bypassed` finding naming the slice and the unmet key(s)."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state(
        [_slice(id="slice-2", order=2, status="briefed",
                brief_path="briefs/slice-2.md")],
        re_scope_gate={"pre_conditions": _pre_conditions(d_ownership_decision="open")},
    )
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)

    assert len(findings) == 1
    f = findings[0]
    assert f["kind"] == "gate-bypassed"
    assert f["ref"] == "slice-2"
    assert "d_ownership_decision" in f["refs"]
    assert "d_ownership_decision" in f["detail"]


def test_gate_bypassed_order2_brief_with_all_preconditions_closed_is_clean(
        tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state(
        [_slice(id="slice-2", order=2, status="briefed",
                brief_path="briefs/slice-2.md")],
        re_scope_gate={"pre_conditions": _pre_conditions()},
    )
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_gate_bypassed_waived_precondition_counts_as_satisfied(tmp_path: Path) -> None:
    """"waived" (a human explicitly decided to proceed without it) satisfies
    a pre-condition exactly like "closed" -- not only the literal "closed"
    string named in the Intent."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state(
        [_slice(id="slice-2", order=2, status="briefed",
                brief_path="briefs/slice-2.md")],
        re_scope_gate={"pre_conditions": _pre_conditions(d_ownership_decision="waived")},
    )
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_gate_bypassed_order1_slice_never_checked(tmp_path: Path) -> None:
    """Slice 1 (order 1) having `brief_path` set is never a finding, even
    with every pre-condition open -- clause (d) only applies to order >= 2."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state(
        [_slice(id="slice-1", order=1, status="compiled",
                brief_path="briefs/slice-1.md")],
        re_scope_gate={"pre_conditions": _pre_conditions(
            a_ci_enforcement="open", b_skf_setup="open",
            c_cross_slice_rederivation="open", d_ownership_decision="open")},
    )
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_gate_not_checked_when_order2_brief_path_still_null(tmp_path: Path) -> None:
    """Today's real state: no slice of order >= 2 has `brief_path` set --
    clause (d) stays clean regardless of the pre-conditions' status."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state(
        [_slice(id="slice-2", order=2, status="mapped", brief_path=None)],
        re_scope_gate={"pre_conditions": _pre_conditions(
            a_ci_enforcement="open", b_skf_setup="open",
            c_cross_slice_rederivation="open", d_ownership_decision="open")},
    )
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_gate_bypassed_lists_only_the_unmet_keys(tmp_path: Path) -> None:
    """Only the actually-unmet pre-condition keys appear in `refs`/`detail` --
    not the ones already closed."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state(
        [_slice(id="slice-2", order=2, status="briefed",
                brief_path="briefs/slice-2.md")],
        re_scope_gate={"pre_conditions": _pre_conditions(
            c_cross_slice_rederivation="open", d_ownership_decision="open")},
    )
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)

    assert len(findings) == 1
    f = findings[0]
    assert set(f["refs"]) == {"slice-2", "c_cross_slice_rederivation", "d_ownership_decision"}
    assert "a_ci_enforcement" not in f["detail"]
    assert "b_skf_setup" not in f["detail"]


def test_gate_bypassed_missing_re_scope_gate_treated_as_all_open(tmp_path: Path) -> None:
    """No `campaign.re_scope_gate` at all (malformed/absent) must not crash
    clause (d) -- it is treated as every pre-condition unmet, same tolerance
    every other malformed-shape case in this file gets."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state([_slice(id="slice-2", order=2, status="briefed",
                            brief_path="briefs/slice-2.md")])
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)

    assert len(findings) == 1
    assert findings[0]["kind"] == "gate-bypassed"
    assert set(m.RE_SCOPE_GATE_PRE_CONDITION_KEYS) <= set(findings[0]["refs"])


def test_gate_bypassed_non_int_order_not_crashed_and_not_gated(tmp_path: Path) -> None:
    """A malformed (non-int) `order` value must not crash clause (d) -- the
    slice is simply not gated, same tolerance every other malformed-shape
    case in this file gets."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state([_slice(id="slice-x", order="two", status="briefed",
                            brief_path="briefs/slice-x.md")])
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_scan_tolerates_non_dict_slice_entries() -> None:
    """A malformed campaign-state.yaml (e.g. `slices: [1, 2, 3]`, or a slice
    entry that is a scalar rather than a mapping) must not crash scan() with
    an AttributeError -- it is simply ignored, same tolerance every other
    malformed-shape case in this file gets."""
    assert m.scan({"campaign": {}, "slices": [1, 2, 3]}, [], root=REPO_ROOT) == []
    assert m.scan({"campaign": {}, "slices": "not-a-list"}, [], root=REPO_ROOT) == []


def test_scan_tolerates_non_dict_campaign() -> None:
    """`campaign` present but not a mapping (e.g. a string) must not crash
    clause (c)'s lookup."""
    assert m.scan({"campaign": "not-a-dict", "slices": []}, [], root=REPO_ROOT) == []


def test_scan_tolerates_non_dict_re_scope_gate_and_pre_conditions(tmp_path: Path) -> None:
    """`campaign.re_scope_gate` or its `pre_conditions` present but not a
    mapping must not crash clause (d)'s lookup -- treated as every
    pre-condition unmet, same as it being absent entirely."""
    order2_brief = [_slice(id="slice-2", order=2, brief_path="briefs/slice-2.md")]
    state_a = {"campaign": {"re_scope_gate": "not-a-dict"}, "slices": order2_brief}
    _ensure_briefs_for_state(tmp_path, state_a)
    findings_a = m.scan(state_a, [], root=tmp_path)
    assert len(findings_a) == 1 and findings_a[0]["kind"] == "gate-bypassed"

    state_b = {
        "campaign": {"re_scope_gate": {"pre_conditions": "not-a-dict"}},
        "slices": order2_brief,
    }
    _ensure_briefs_for_state(tmp_path, state_b)
    findings_b = m.scan(state_b, [], root=tmp_path)
    assert len(findings_b) == 1 and findings_b[0]["kind"] == "gate-bypassed"


def test_unmirrored_retro_empty_string_brief_path_treated_as_null(tmp_path: Path) -> None:
    """An empty-string `brief_path` (vs. proper `null`) means no real brief
    exists yet -- treated identically to `brief_path: null`, not as a brief
    to check for staleness."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    _write(tmp_path, ".claude/skills/conda-forge-expert/SKILL.md", "updated")
    _write(tmp_path, CFE_CHANGELOG, "## new entry")
    _commit_all(tmp_path, "feat: a retro lands, slice has an empty brief_path")

    state = _state([_slice(id="slice-1", brief_path="", brief_mirrored_through=None)])
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_campaign_state_missing_file(tmp_path: Path) -> None:
    assert m.campaign_state(tmp_path / "does-not-exist.yaml") is None


def test_campaign_state_malformed_yaml(tmp_path: Path) -> None:
    bad = tmp_path / "campaign-state.yaml"
    bad.write_text("this: is: not: valid: yaml: [", encoding="utf-8")
    assert m.campaign_state(bad) is None


def test_campaign_state_not_a_mapping(tmp_path: Path) -> None:
    bad = tmp_path / "campaign-state.yaml"
    bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
    assert m.campaign_state(bad) is None


def test_campaign_state_valid(tmp_path: Path) -> None:
    good = tmp_path / "campaign-state.yaml"
    good.write_text("campaign:\n  endgame_declared: false\nslices: []\n", encoding="utf-8")
    data = m.campaign_state(good)
    assert data == {"campaign": {"endgame_declared": False}, "slices": []}


def test_retro_commits_since_returns_none_when_git_log_cannot_run(tmp_path: Path) -> None:
    # tmp_path is not a git repository at all -- the exit-2 case.
    assert m.retro_commits_since(tmp_path, "deadbeef") is None


def test_retro_commits_since_unknown_sha_also_none(tmp_path: Path) -> None:
    """A real repo, but `--since` names a SHA unreachable from HEAD -- `git
    log <since>..HEAD` itself fails, same exit-2 class as no repo at all."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    _commit_all(tmp_path, "feat: baseline")
    assert m.retro_commits_since(tmp_path, "0" * 40) is None


def test_slice_with_explicit_null_id_renders_unknown_placeholder(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state([_slice(id=None, status="parallel", equivalence="red")])
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)

    assert len(findings) == 1
    assert findings[0]["ref"] == "<unknown-slice>"


def test_gate_bypassed_closed_status_with_trailing_space_is_satisfied(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    pre = _pre_conditions()
    pre["d_ownership_decision"] = {"status": "Closed ", "note": "test"}
    state = _state(
        [_slice(id="slice-2", order=2, status="briefed", brief_path="briefs/slice-2.md")],
        re_scope_gate={"pre_conditions": pre},
    )
    retros = m.retro_commits_since(tmp_path, baseline)
    _ensure_briefs_for_state(tmp_path, state)
    findings = m.scan(state, retros, root=tmp_path)
    assert findings == []


def test_brief_hollow_mapping_is_a_finding(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    brief_rel = "briefs/hollow.yaml"
    _write(tmp_path, brief_rel, "{}\n")
    state = _state([_slice(id="slice-1", brief_path=brief_rel, brief_mirrored_through=None)])
    retros = m.retro_commits_since(tmp_path, baseline)
    findings = m.scan(state, retros, root=tmp_path)

    assert any(f["kind"] == "brief-defect" and "missing required" in f["detail"] for f in findings)


def test_brief_path_missing_file_is_a_finding(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state = _state(
        [_slice(id="slice-1", brief_path="briefs/missing.yaml", brief_mirrored_through=None)],
    )
    retros = m.retro_commits_since(tmp_path, baseline)
    findings = m.scan(state, retros, root=tmp_path)

    assert any(f["kind"] == "brief-defect" for f in findings)


def test_brief_without_retro_mirror_amendment_is_a_finding(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    brief_rel = "briefs/slice-1.yaml"
    _write_brief(tmp_path, brief_rel)
    retro_sha = "a" * 40
    state = _state(
        [_slice(id="slice-1", brief_path=brief_rel, brief_mirrored_through=retro_sha)],
    )
    retros = m.retro_commits_since(tmp_path, baseline)
    findings = m.scan(state, retros, root=tmp_path)

    assert any(f["kind"] == "brief-defect" and retro_sha[:10] in f["detail"] for f in findings)


def _two_retro_repo(tmp_path: Path) -> tuple[str, str, str]:
    """A scratch repo with two qualifying retros; returns (baseline, older, newer)."""
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")
    _write(tmp_path, ".claude/skills/conda-forge-expert/SKILL.md", "first")
    _write(tmp_path, CFE_CHANGELOG, "## first entry")
    older = _commit_all(tmp_path, "docs: first retro")
    _write(tmp_path, ".claude/skills/conda-forge-expert/SKILL.md", "second")
    _write(tmp_path, CFE_CHANGELOG, "## second entry")
    newer = _commit_all(tmp_path, "docs: second retro")
    return baseline, older, newer


def test_brief_must_name_every_retro_at_or_older_than_the_pointer(tmp_path: Path) -> None:
    """Clause (b'): a brief mirrored through the newest of two retros must
    name BOTH; naming only the pointer leaves the older retro unmirrored."""
    baseline, older, newer = _two_retro_repo(tmp_path)
    retros = m.retro_commits_since(tmp_path, baseline)
    assert retros == [newer, older]
    brief_rel = "briefs/slice-1.yaml"
    state = _state([_slice(id="slice-1", brief_path=brief_rel, brief_mirrored_through=newer)])

    _write_brief(tmp_path, brief_rel, mirrored_shas=(newer,))
    findings = m.scan(state, retros, root=tmp_path)
    assert [f["kind"] for f in findings] == ["brief-defect"]
    assert older[:10] in findings[0]["refs"]
    assert newer[:10] not in findings[0]["refs"]

    _write_brief(tmp_path, brief_rel, mirrored_shas=(newer, older[:10]))
    assert m.scan(state, retros, root=tmp_path) == []


def test_brief_pointer_at_the_older_retro_owes_only_that_retro(tmp_path: Path) -> None:
    """A retro NEWER than brief_mirrored_through is clause (b)'s business
    (unmirrored-retro), never a brief-defect."""
    baseline, older, newer = _two_retro_repo(tmp_path)
    retros = m.retro_commits_since(tmp_path, baseline)
    brief_rel = "briefs/slice-1.yaml"
    _write_brief(tmp_path, brief_rel, mirrored_shas=(older,))
    state = _state([_slice(id="slice-1", brief_path=brief_rel, brief_mirrored_through=older)])

    findings = m.scan(state, retros, root=tmp_path)
    assert [f["kind"] for f in findings] == ["unmirrored-retro"]
    assert newer[:10] in findings[0]["refs"]


def test_retro_sha_quoted_in_free_text_does_not_count(tmp_path: Path) -> None:
    """A SHA must be a field's whole value; one quoted inside `reason`
    prose, or a prefix shorter than 10 characters, names nothing."""
    baseline, older, _newer = _two_retro_repo(tmp_path)
    retros = m.retro_commits_since(tmp_path, baseline)
    brief_rel = "briefs/slice-1.yaml"
    state = _state([_slice(id="slice-1", brief_path=brief_rel, brief_mirrored_through=older)])

    _write_brief(tmp_path, brief_rel)
    with (tmp_path / brief_rel).open("a", encoding="utf-8") as handle:
        handle.write(
            "  amendments:\n"
            "    - action: retro-mirror\n"
            f"      reason: mirrored {older} into the brief\n"
            f"      commit: {older[:9]}\n"
        )
    findings = m.scan(state, retros, root=tmp_path)
    assert any(f["kind"] == "brief-defect" and older[:10] in f["refs"] for f in findings)


def test_retro_sha_in_a_list_field_counts(tmp_path: Path) -> None:
    """A list-valued field (feat + merge SHAs of one dual landing) names
    each SHA it carries; a non-`retro-mirror` amendment names none."""
    baseline, older, newer = _two_retro_repo(tmp_path)
    retros = m.retro_commits_since(tmp_path, baseline)
    brief_rel = "briefs/slice-1.yaml"
    state = _state([_slice(id="slice-1", brief_path=brief_rel, brief_mirrored_through=newer)])

    _write_brief(tmp_path, brief_rel)
    with (tmp_path / brief_rel).open("a", encoding="utf-8") as handle:
        handle.write(
            "  amendments:\n"
            "    - action: promoted\n"
            f"      commit: {older}\n"
            "    - action: retro-mirror\n"
            f"      commits: [{newer.upper()}]\n"
        )
    findings = m.scan(state, retros, root=tmp_path)
    assert [f["refs"][1:] for f in findings if f["kind"] == "brief-defect"] == [[older[:10]]]


def test_brief_with_only_a_name_is_a_finding(tmp_path: Path) -> None:
    brief_rel = "briefs/name-only.yaml"
    _write(tmp_path, brief_rel, "name: x\n")
    state = _state([_slice(id="slice-1", brief_path=brief_rel)])
    findings = m.scan(state, [], root=tmp_path)
    assert len(findings) == 1
    assert findings[0]["kind"] == "brief-defect"
    assert "missing required" in findings[0]["detail"]
    assert "'version'" in findings[0]["detail"]
    assert "'name'" not in findings[0]["detail"]


def test_brief_with_all_required_keys_null_is_a_finding(tmp_path: Path) -> None:
    brief_rel = "briefs/all-null.yaml"
    _write(tmp_path, brief_rel, "".join(f"{k}: null\n" for k in m._BRIEF_REQUIRED_TOP_KEYS))
    state = _state([_slice(id="slice-1", brief_path=brief_rel)])
    findings = m.scan(state, [], root=tmp_path)
    assert len(findings) == 1
    assert "missing required" in findings[0]["detail"]
    for key in m._BRIEF_REQUIRED_TOP_KEYS:
        assert repr(key) in findings[0]["detail"]


def test_brief_scope_without_a_type_is_a_finding(tmp_path: Path) -> None:
    brief_rel = "briefs/hollow-scope.yaml"
    _write_brief(tmp_path, brief_rel)
    text = (tmp_path / brief_rel).read_text(encoding="utf-8")
    (tmp_path / brief_rel).write_text(text.replace("  type: full-library\n", ""), encoding="utf-8")
    state = _state([_slice(id="slice-1", brief_path=brief_rel)])
    findings = m.scan(state, [], root=tmp_path)
    assert len(findings) == 1
    assert "hollow or missing scope" in findings[0]["detail"]


def test_non_string_brief_path_is_a_finding_not_a_traceback(tmp_path: Path) -> None:
    state = _state([_slice(id="slice-1", brief_path=["briefs/a.yaml"])])
    findings = m.scan(state, [], root=tmp_path)
    assert [f["kind"] for f in findings] == ["brief-defect"]
    assert "not a path string" in findings[0]["detail"]


def test_stale_equivalence_status_with_trailing_space_is_gated(tmp_path: Path) -> None:
    """Clause (a) strips as well as case-folds: `"parallel "` is gated."""
    state = _state([_slice(id="slice-1", status="parallel ", equivalence="red")])
    findings = m.scan(state, [], root=tmp_path)
    assert [f["kind"] for f in findings] == ["stale-equivalence"]


def test_slice_ref_keeps_an_integer_id(tmp_path: Path) -> None:
    state = _state([_slice(id=7, status="parallel", equivalence="red")])
    findings = m.scan(state, [], root=tmp_path)
    assert findings[0]["ref"] == "7"
    assert m._slice_ref({"id": "  "}) == "<unknown-slice>"


def test_main_skips_git_walk_when_no_slice_has_brief_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_path = tmp_path / "campaign-state.yaml"
    state_path.write_text(
        "campaign:\n  endgame_declared: false\n  callers: []\n"
        "slices:\n"
        "  - id: slice-1\n"
        "    status: mapped\n"
        "    brief_path: null\n",
        encoding="utf-8",
    )

    def _fail_walk(*_args: object, **_kwargs: object) -> list[str]:
        raise AssertionError("retro_commits_since must not run when no slice has brief_path")

    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "CAMPAIGN_STATE_PATH", state_path)
    monkeypatch.setattr(m, "retro_commits_since", _fail_walk)
    monkeypatch.setattr(sys, "argv", ["cfe_rebuild_guard_check.py"])
    assert m.main() == 0


def test_main_text_mode_skipped_history_never_claims_zero_retros(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    state_path = tmp_path / "campaign-state.yaml"
    state_path.write_text(
        "campaign:\n  endgame_declared: false\n  callers: []\n"
        "slices:\n"
        "  - id: slice-1\n"
        "    status: mapped\n"
        "    brief_path: null\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "CAMPAIGN_STATE_PATH", state_path)
    monkeypatch.setattr(sys, "argv", ["cfe_rebuild_guard_check.py"])
    assert m.main() == 0
    out = capsys.readouterr().out
    assert "skipped retro history walk" in out
    assert "qualifying CFE retro commit" not in out


def test_main_json_skipped_history_reports_null_retros_scanned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    state_path = tmp_path / "campaign-state.yaml"
    state_path.write_text(
        "campaign:\n  endgame_declared: false\n  callers: []\n"
        "slices:\n"
        "  - id: slice-1\n"
        "    status: mapped\n"
        "    brief_path: null\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "CAMPAIGN_STATE_PATH", state_path)
    monkeypatch.setattr(sys, "argv", ["cfe_rebuild_guard_check.py", "--json"])
    assert m.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["retros_scanned"] is None


def test_live_repo_today_is_clean() -> None:
    """Confirms the real, unmodified campaign-state.yaml stays clean under the
    new detector the moment this story lands (per the spec's Verification
    section) -- not a synthetic fixture."""
    state = m.campaign_state(m.CAMPAIGN_STATE_PATH)
    assert state is not None
    if m.any_slice_has_brief_path(state):
        retros = m.retro_commits_since(REPO_ROOT, m.DEFAULT_SINCE)
        assert retros is not None
    else:
        retros = []
    findings = m.scan(state, retros, root=REPO_ROOT)
    assert findings == []


# --- main() / CLI wiring -----------------------------------------------------


def test_main_exit_0_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                            capsys: pytest.CaptureFixture[str]) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state_path = tmp_path / "campaign-state.yaml"
    state_path.write_text(
        "campaign:\n  endgame_declared: false\n  callers: []\n"
        "slices:\n"
        "  - id: slice-1\n"
        "    status: mapped\n"
        "    equivalence: null\n"
        "    brief_path: null\n"
        "    brief_mirrored_through: null\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "CAMPAIGN_STATE_PATH", state_path)
    monkeypatch.setattr(sys, "argv", ["cfe_rebuild_guard_check.py", "--since", baseline])
    rc = m.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert "clean" in out


def test_main_exit_1_findings_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                    capsys: pytest.CaptureFixture[str]) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state_path = tmp_path / "campaign-state.yaml"
    state_path.write_text(
        "campaign:\n  endgame_declared: true\n  callers:\n"
        "    - name: some-caller\n      resolves_to: legacy\n"
        "slices:\n"
        "  - id: slice-1\n"
        "    status: mapped\n"
        "    equivalence: null\n"
        "    brief_path: null\n"
        "    brief_mirrored_through: null\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "CAMPAIGN_STATE_PATH", state_path)
    monkeypatch.setattr(sys, "argv",
                         ["cfe_rebuild_guard_check.py", "--json", "--since", baseline])
    rc = m.main()
    out = capsys.readouterr().out

    assert rc == 1
    payload = json.loads(out)
    assert len(payload["findings"]) == 1
    assert payload["findings"][0]["kind"] == "legacy-caller-at-endgame"


def test_main_exit_1_gate_bypassed_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                         capsys: pytest.CaptureFixture[str]) -> None:
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "baseline")
    baseline = _commit_all(tmp_path, "feat: baseline")

    state_path = tmp_path / "campaign-state.yaml"
    state_path.write_text(
        "campaign:\n"
        "  endgame_declared: false\n"
        "  callers: []\n"
        "  re_scope_gate:\n"
        "    pre_conditions:\n"
        "      a_ci_enforcement: {status: closed}\n"
        "      b_skf_setup: {status: closed}\n"
        "      c_cross_slice_rederivation: {status: open}\n"
        "      d_ownership_decision: {status: open}\n"
        "slices:\n"
        "  - id: slice-2\n"
        "    order: 2\n"
        "    status: briefed\n"
        "    equivalence: null\n"
        "    brief_path: briefs/slice-2.md\n"
        "    brief_mirrored_through: null\n",
        encoding="utf-8",
    )
    _write_brief(tmp_path, "briefs/slice-2.md")

    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "CAMPAIGN_STATE_PATH", state_path)
    monkeypatch.setattr(sys, "argv",
                         ["cfe_rebuild_guard_check.py", "--json", "--since", baseline])
    rc = m.main()
    out = capsys.readouterr().out

    assert rc == 1
    payload = json.loads(out)
    assert any(f["kind"] == "gate-bypassed" for f in payload["findings"])
    gate = next(f for f in payload["findings"] if f["kind"] == "gate-bypassed")
    assert gate["ref"] == "slice-2"
    assert payload["findings"][0]["ref"] == "slice-2"


def test_main_exit_2_missing_campaign_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                             capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "CAMPAIGN_STATE_PATH", tmp_path / "nope.yaml")
    monkeypatch.setattr(sys, "argv", ["cfe_rebuild_guard_check.py"])
    rc = m.main()
    captured = capsys.readouterr()

    assert rc == 2
    assert "UNKNOWN" in captured.err


def test_main_exit_2_git_log_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                    capsys: pytest.CaptureFixture[str]) -> None:
    state_path = tmp_path / "campaign-state.yaml"
    state_path.write_text(
        "campaign:\n  endgame_declared: false\n  callers: []\n"
        "slices:\n"
        "  - id: slice-1\n"
        "    brief_path: briefs/slice-1.yaml\n",
        encoding="utf-8",
    )
    _write_brief(tmp_path, "briefs/slice-1.yaml")

    # tmp_path is not a git repository -- `git log` itself fails once a brief_path
    # forces the retro history walk.
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "CAMPAIGN_STATE_PATH", state_path)
    monkeypatch.setattr(sys, "argv", ["cfe_rebuild_guard_check.py"])
    rc = m.main()
    captured = capsys.readouterr()

    assert rc == 2
    assert "UNKNOWN" in captured.err


def test_main_exit_2_json_still_emits_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                            capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "CAMPAIGN_STATE_PATH", tmp_path / "nope.yaml")
    monkeypatch.setattr(sys, "argv", ["cfe_rebuild_guard_check.py", "--json"])
    rc = m.main()
    out = capsys.readouterr().out

    assert rc == 2
    payload = json.loads(out)
    assert payload["findings"] == []
    assert "error" in payload
    # Key parity with mason_cfe_surface_check.py's own _unknown() payload
    # shape (commits_scanned: None on failure) -- a JSON consumer must see a
    # stable key set across exit codes, not one that appears only on success.
    assert payload["retros_scanned"] is None


def _write_brief_with_amendment_yaml(repo: Path, rel: str, amendment_body: str) -> None:
    """Skill brief with a single retro-mirror amendment block (raw YAML lines)."""
    lines = [
        "name: test-skill",
        "version: 1.0.0",
        "source_repo: https://example.com",
        "language: python",
        "description: test",
        "forge_tier: Quick",
        "created: 2026-01-01",
        "created_by: test",
        "scope:",
        "  type: full-library",
        "  include: []",
        "  exclude: []",
        "  notes: test",
        "  amendments:",
        "    - action: retro-mirror",
        amendment_body,
        "      reason: mirrored a landed CFE retro",
    ]
    _write(repo, rel, "\n".join(lines) + "\n")


def _full_retro(prefix: str) -> str:
    return (prefix + "a" * 40)[:40]


def test_int_loaded_commit_field_covers_retro(tmp_path: Path) -> None:
    prefix = "4139357790"
    retro = _full_retro(prefix)
    brief_rel = "briefs/int-field.yaml"
    _write_brief_with_amendment_yaml(tmp_path, brief_rel, f"      commit: {prefix}")
    brief = m._yaml_load((tmp_path / brief_rel).read_text(encoding="utf-8"))
    assert m._brief_covers_retro_sha(brief, retro)


def test_int_loaded_commit_list_item_covers_retro(tmp_path: Path) -> None:
    prefix = "4139357790"
    retro = _full_retro(prefix)
    brief_rel = "briefs/int-list.yaml"
    _write_brief_with_amendment_yaml(tmp_path, brief_rel, f"      commits: [{prefix}]")
    brief = m._yaml_load((tmp_path / brief_rel).read_text(encoding="utf-8"))
    assert m._brief_covers_retro_sha(brief, retro)


def test_octal_shaped_commit_reads_scalar_text(tmp_path: Path) -> None:
    prefix = "0123456701"
    retro = _full_retro(prefix)
    brief_rel = "briefs/octal-field.yaml"
    _write_brief_with_amendment_yaml(tmp_path, brief_rel, f"      commit: {prefix}")
    brief = m._yaml_load((tmp_path / brief_rel).read_text(encoding="utf-8"))
    assert m._brief_covers_retro_sha(brief, retro)


def test_binary_shaped_commit_reads_scalar_text(tmp_path: Path) -> None:
    prefix = "0b10110101"
    retro = _full_retro(prefix)
    brief_rel = "briefs/binary-field.yaml"
    _write_brief_with_amendment_yaml(tmp_path, brief_rel, f"      commit: {prefix}")
    brief = m._yaml_load((tmp_path / brief_rel).read_text(encoding="utf-8"))
    assert m._brief_covers_retro_sha(brief, retro)


def test_leading_zero_string_commit_still_covers_retro(tmp_path: Path) -> None:
    prefix = "0123456789"
    retro = _full_retro(prefix)
    brief_rel = "briefs/lead-zero-str.yaml"
    _write_brief_with_amendment_yaml(tmp_path, brief_rel, f"      commit: {prefix}")
    brief = m._yaml_load((tmp_path / brief_rel).read_text(encoding="utf-8"))
    assert m._brief_covers_retro_sha(brief, retro)


@pytest.mark.parametrize(
    "commit_line",
    [
        "      commit: true",
        "      commit: false",
        "      commit: 1.5",
        "      commit: null",
        "      commit: 413935779",
    ],
)
def test_non_sha_amendment_values_name_no_retro(tmp_path: Path, commit_line: str) -> None:
    retro = _full_retro("4139357790")
    brief_rel = "briefs/non-sha.yaml"
    _write_brief_with_amendment_yaml(tmp_path, brief_rel, commit_line)
    brief = m._yaml_load((tmp_path / brief_rel).read_text(encoding="utf-8"))
    assert not m._brief_covers_retro_sha(brief, retro)


def test_free_text_reason_still_names_no_retro(tmp_path: Path) -> None:
    retro = _full_retro("4139357790")
    brief_rel = "briefs/free-text.yaml"
    _write_brief_with_amendment_yaml(tmp_path, brief_rel, "      commit: deadbeef01")
    with (tmp_path / brief_rel).open("a", encoding="utf-8") as handle:
        handle.write(f"      reason: mirrored {retro} into the brief\n")
    brief = m._yaml_load((tmp_path / brief_rel).read_text(encoding="utf-8"))
    assert not m._brief_covers_retro_sha(brief, retro)


def test_int_brief_mirrored_through_newest_retro_is_clean(tmp_path: Path) -> None:
    prefix = "4139357790"
    newer = _full_retro(prefix)
    older = _full_retro("bbbbbbbbbb")
    brief_rel = "briefs/mirror.yaml"
    _write_brief(tmp_path, brief_rel, mirrored_shas=(newer, older))
    state = _state([_slice(id="slice-1", brief_path=brief_rel, brief_mirrored_through=int(prefix))])
    findings = m.scan(state, [newer, older], root=tmp_path)
    assert not any(f["kind"] == "unmirrored-retro" for f in findings)


def test_int_brief_mirrored_through_empty_brief_is_b_prime_defect(tmp_path: Path) -> None:
    prefix = "4139357790"
    newer = _full_retro(prefix)
    brief_rel = "briefs/empty.yaml"
    _write_brief(tmp_path, brief_rel)
    state = _state([_slice(id="slice-1", brief_path=brief_rel, brief_mirrored_through=int(prefix))])
    findings = m.scan(state, [newer], root=tmp_path)
    assert any(f["kind"] == "brief-defect" for f in findings)


def test_string_prefix_pointer_matches_newest_retro(tmp_path: Path) -> None:
    prefix = "4139357790"
    newer = _full_retro(prefix)
    brief_rel = "briefs/prefix-pointer.yaml"
    _write_brief(tmp_path, brief_rel, mirrored_shas=(newer,))
    state = _state(
        [_slice(id="slice-1", brief_path=brief_rel, brief_mirrored_through=prefix)],
    )
    findings = m.scan(state, [newer], root=tmp_path)
    assert not any(f["kind"] == "unmirrored-retro" for f in findings)


def test_unmirrored_remedy_names_accepted_prefix_value(tmp_path: Path) -> None:
    newer = "c" * 40
    brief_rel = "briefs/stale.yaml"
    _write_brief(tmp_path, brief_rel, mirrored_shas=(newer,))
    state = _state(
        [_slice(id="slice-1", brief_path=brief_rel, brief_mirrored_through="deadbeef01")],
    )
    findings = m.scan(state, [newer], root=tmp_path)
    unmirrored = [f for f in findings if f["kind"] == "unmirrored-retro"]
    assert len(unmirrored) == 1
    assert newer[: m.MIN_SHA_PREFIX] in unmirrored[0]["remedy"]


def test_out_of_range_pointer_covered_by_full_sha_amendment(tmp_path: Path) -> None:
    pointer = "dddddddddd"
    full = pointer + "e" * 30
    brief_rel = "briefs/out-of-range.yaml"
    _write_brief(tmp_path, brief_rel, mirrored_shas=(full,))
    state = _state([_slice(id="slice-1", brief_path=brief_rel, brief_mirrored_through=pointer)])
    findings = m.scan(state, [], root=tmp_path)
    assert not any(f["kind"] == "brief-defect" for f in findings)


@pytest.mark.parametrize(
    ("older_prefix", "newer"),
    [
        ("4139357790", "f" * 40),
        ("0123456701", "e" * 40),
        ("0b10110101", "d" * 40),
        ("0123456789", "c" * 40),
        ("ababababab", "b" * 40),
    ],
)
def test_pointer_shape_pairs_b_prime_deterministic(
    tmp_path: Path, older_prefix: str, newer: str,
) -> None:
    older = _full_retro(older_prefix)
    brief_rel = "briefs/shape.yaml"
    state = _state([_slice(id="slice-1", brief_path=brief_rel, brief_mirrored_through=newer)])

    _write_brief(tmp_path, brief_rel, mirrored_shas=(newer,))
    findings = m.scan(state, [newer, older], root=tmp_path)
    assert [f["kind"] for f in findings] == ["brief-defect"]
    assert older_prefix[:10] in findings[0]["refs"]

    _write_brief(tmp_path, brief_rel, mirrored_shas=(newer, older_prefix))
    assert m.scan(state, [newer, older], root=tmp_path) == []


def test_campaign_state_loads_int_brief_mirrored_through(tmp_path: Path) -> None:
    prefix = "4139357790"
    yaml_text = (
        "campaign:\n  endgame_declared: false\n  callers: []\n"
        "slices:\n  - id: slice-1\n    status: mapped\n    brief_path: briefs/x.yaml\n"
        f"    brief_mirrored_through: {prefix}\n"
    )
    path = tmp_path / "campaign-state.yaml"
    path.write_text(yaml_text, encoding="utf-8")
    state = m.campaign_state(path)
    assert state is not None
    mirrored = m._sha_candidate_from_yaml_value(state["slices"][0]["brief_mirrored_through"])
    assert mirrored == prefix


def test_cli_against_live_repo_exits_zero() -> None:
    """`pixi run -e local-recipes cfe-rebuild-guard-check` -- exact command
    from the spec's Verification section, invoked directly here."""
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "cfe_rebuild_guard_check.py")],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "clean" in proc.stdout
