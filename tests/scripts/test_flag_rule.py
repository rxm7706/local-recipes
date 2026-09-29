"""Unit tests for ``scripts/flag_rule.py`` and ``scripts/flag_rule_baseline.py`` -- the flag rule's
machine form (doctor Story 34.1, spec-feature-flag-governance CAP-1).

One test per acceptance-criteria row and per I/O-matrix row of the story spec, plus the scan that
pins the roster as the one declared source of the exemption list.

``pytest.importorskip("yaml")`` mirrors ``test_docs_gen_common.py``: PyYAML is not a declared
dependency of ``pyforge-ci``, so the suite skips there and runs for real from ``pyforge-guild``
(``pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_rule.py -q``).
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import flag_rule  # noqa: E402
import flag_rule_baseline  # noqa: E402

# The Spec's Q2, in order. The roster owns the list; this literal is the oracle's own copy.
Q2_EXEMPTIONS = [
    "flag-infrastructure",
    "docs-only",
    "recipe-build",
    "planning-ledger-only",
    "detector-or-gate",
]

FLAG_BLOCK = """\
flag:
  key: pyforge.atlas.dependency_history
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "the legacy behaviour"
  cleanup: 90 days after ON in every environment (Q4)
"""

SPECS_DIR = "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs"


def _spec(tmp_path: Path, frontmatter: str, name: str = "spec-1-1-a-story.md") -> Path:
    path = tmp_path / SPECS_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ntitle: a story\ntype: feature\n{frontmatter}---\n\nbody\n", encoding="utf-8")
    return path


def _repo(tmp_path: Path, exemptions=("alpha", "beta"), baseline=None) -> Path:
    """A tmp repo root with its own roster and (optionally) baseline."""
    gov = tmp_path / "docs" / "governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "guild-roster.json").write_text(json.dumps({"flag_exemptions": list(exemptions)}), encoding="utf-8")
    if baseline is not None:
        (gov / "flag-rule-baseline.json").write_text(json.dumps({"specs": list(baseline)}), encoding="utf-8")
    return tmp_path


# --- the roster (AC 1) ---------------------------------------------------------------------


def test_roster_flag_exemptions_are_the_five_of_q2_in_order():
    roster = json.loads((REPO_ROOT / "docs/governance/guild-roster.json").read_text(encoding="utf-8"))

    assert roster["flag_exemptions"] == Q2_EXEMPTIONS
    assert list(flag_rule.load_exemptions()) == Q2_EXEMPTIONS


def test_roster_comment_names_a_change_a_governance_act():
    roster = json.loads((REPO_ROOT / "docs/governance/guild-roster.json").read_text(encoding="utf-8"))

    assert "governance act" in " ".join(roster["$comment_flag_exemptions"])


# --- classify ------------------------------------------------------------------------------


def test_a_full_block_is_flag_with_no_reasons(tmp_path: Path):
    root = _repo(tmp_path)

    result = flag_rule.classify(_spec(root, FLAG_BLOCK), repo_root=root)

    assert result.verdict == flag_rule.FLAG
    assert result.reasons == ()


def test_the_live_atlas_block_is_flag():
    atlas = REPO_ROOT / (
        "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/"
        "spec-25-1-a-per-repo-dependency-history-dataset-from-git-pkgs-and-an-estate-pixi-parser.md"
    )

    assert flag_rule.classify(atlas).verdict == flag_rule.FLAG


def test_a_block_missing_cleanup_and_fallback_is_neither_with_one_reason_each(tmp_path: Path):
    root = _repo(tmp_path)
    block = "".join(ln for ln in FLAG_BLOCK.splitlines(keepends=True) if "fallback" not in ln and "cleanup" not in ln)

    result = flag_rule.classify(_spec(root, block), repo_root=root)

    assert result.verdict == flag_rule.NEITHER
    assert len(result.reasons) == 2
    assert any("`cleanup`" in r for r in result.reasons)
    assert any("`fallback`" in r for r in result.reasons)


def test_a_partial_block_of_key_and_provider_has_four_reasons(tmp_path: Path):
    root = _repo(tmp_path)
    block = "flag:\n  key: pyforge.x.y\n  provider: openfeature-file\n"

    result = flag_rule.classify(_spec(root, block), repo_root=root)

    assert result.verdict == flag_rule.NEITHER
    assert len(result.reasons) == 4
    for field in ("default", "scope", "fallback", "cleanup"):
        assert any(f"`{field}`" in r for r in result.reasons)


def test_an_empty_field_is_a_reason_but_a_scalar_off_default_is_a_value(tmp_path: Path):
    root = _repo(tmp_path)
    empty = FLAG_BLOCK.replace("scope: global", "scope:")
    # YAML 1.1 reads an unquoted `off` as False; that is a value, not an empty field.
    off = FLAG_BLOCK.replace("{production: off, staging: on, dev: on}", "off")

    assert flag_rule.classify(_spec(root, empty), repo_root=root).reasons == ("`flag:` block field `scope` is empty",)
    assert flag_rule.classify(_spec(root, off), repo_root=root).verdict == flag_rule.FLAG


def test_a_flag_that_is_not_a_mapping_is_neither(tmp_path: Path):
    root = _repo(tmp_path)

    for body in ("flag:\n", "flag: true\n", "flag: [a, b]\n"):
        result = flag_rule.classify(_spec(root, body), repo_root=root)
        assert result.verdict == flag_rule.NEITHER
        assert len(result.reasons) == 1


@pytest.mark.parametrize("value", flag_rule.load_exemptions())
def test_every_listed_exemption_is_exempt(tmp_path: Path, value: str):
    result = flag_rule.classify(_spec(tmp_path, f"flag-exempt: {value}   # a trailing comment\n"))

    assert result == (flag_rule.EXEMPT, ())


def test_an_unknown_exemption_is_neither_and_names_the_value(tmp_path: Path):
    for value in ("no-flag-needed", "later"):
        result = flag_rule.classify(_spec(tmp_path, f"flag-exempt: {value}\n"))

        assert result.verdict == flag_rule.NEITHER
        assert len(result.reasons) == 1
        assert value in result.reasons[0]


def test_an_empty_exemption_is_neither(tmp_path: Path):
    result = flag_rule.classify(_spec(tmp_path, "flag-exempt:\n"))

    assert result.verdict == flag_rule.NEITHER
    assert len(result.reasons) == 1


def test_a_block_and_an_exemption_together_is_neither_naming_the_conflict(tmp_path: Path):
    result = flag_rule.classify(_spec(tmp_path, FLAG_BLOCK + "flag-exempt: docs-only\n"))

    assert result.verdict == flag_rule.NEITHER
    assert len(result.reasons) == 1
    assert "both" in result.reasons[0]


def test_a_spec_with_neither_is_neither(tmp_path: Path):
    result = flag_rule.classify(_spec(tmp_path, ""))

    assert result.verdict == flag_rule.NEITHER
    assert len(result.reasons) == 1


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("# just a body, no fence\n", "no frontmatter"),
        ("", "no frontmatter"),
        ("---\ntype: feature\nnever closed\n", "no frontmatter"),
        ("---\n---\n", "empty"),
        ("---\n- a\n- b\n---\n", "not a mapping"),
        ("---\nkey: [unclosed\n---\n", "not valid YAML"),
    ],
)
def test_a_spec_without_usable_frontmatter_is_neither_never_a_crash(tmp_path: Path, text: str, reason: str):
    path = tmp_path / "spec-1-1-x.md"
    path.write_text(text, encoding="utf-8")

    result = flag_rule.classify(path)

    assert result.verdict == flag_rule.NEITHER
    assert reason in result.reasons[0]


def test_a_missing_spec_file_is_neither_never_a_crash(tmp_path: Path):
    result = flag_rule.classify(tmp_path / "spec-9-9-absent.md")

    assert result.verdict == flag_rule.NEITHER
    assert "cannot read" in result.reasons[0]


def test_a_relative_path_is_read_against_the_repo_root(tmp_path: Path):
    root = _repo(tmp_path)
    spec = _spec(root, FLAG_BLOCK)

    assert flag_rule.classify(spec.relative_to(root), repo_root=root).verdict == flag_rule.FLAG


def test_the_roster_is_the_only_source_of_the_exemption_list(tmp_path: Path):
    root = _repo(tmp_path, exemptions=("alpha", "beta"))

    assert flag_rule.classify(_spec(root, "flag-exempt: beta\n"), repo_root=root).verdict == flag_rule.EXEMPT
    result = flag_rule.classify(_spec(root, "flag-exempt: docs-only\n", "spec-1-2-x.md"), repo_root=root)
    assert result.verdict == flag_rule.NEITHER
    assert "alpha, beta" in result.reasons[0]


def test_passed_exemptions_skip_the_roster_read(tmp_path: Path):
    # No roster under tmp_path: with `exemptions` given, classify never reads it.
    spec = _spec(tmp_path, "flag-exempt: whatever\n")

    assert flag_rule.classify(spec, exemptions=("whatever",), repo_root=tmp_path).verdict == flag_rule.EXEMPT


# --- an unreadable roster or baseline (named errors, never exit codes) ---------------------


def test_a_missing_roster_raises_a_named_error(tmp_path: Path):
    with pytest.raises(flag_rule.RosterUnreadable) as info:
        flag_rule.classify(_spec(tmp_path, FLAG_BLOCK), repo_root=tmp_path)

    assert isinstance(info.value, flag_rule.FlagRuleError)


@pytest.mark.parametrize("content", ["not json", "[]", '{"other": 1}', '{"flag_exemptions": []}', '{"flag_exemptions": [1]}'])
def test_a_roster_without_a_usable_list_raises_a_named_error(tmp_path: Path, content: str):
    gov = tmp_path / "docs" / "governance"
    gov.mkdir(parents=True)
    (gov / "guild-roster.json").write_text(content, encoding="utf-8")

    with pytest.raises(flag_rule.RosterUnreadable):
        flag_rule.load_exemptions(tmp_path)


def test_a_roster_error_is_raised_even_for_a_spec_with_no_frontmatter(tmp_path: Path):
    path = tmp_path / "spec-1-1-x.md"
    path.write_text("no fence\n", encoding="utf-8")

    with pytest.raises(flag_rule.RosterUnreadable):
        flag_rule.classify(path, repo_root=tmp_path)


def test_a_missing_baseline_raises_a_named_error(tmp_path: Path):
    with pytest.raises(flag_rule.BaselineUnreadable) as info:
        flag_rule.is_post_rule("spec-1-1-x.md", repo_root=tmp_path)

    assert isinstance(info.value, flag_rule.FlagRuleError)


@pytest.mark.parametrize("content", ["not json", "[]", '{"specs": "a"}', '{"specs": [1]}'])
def test_a_baseline_without_a_usable_list_raises_a_named_error(tmp_path: Path, content: str):
    gov = tmp_path / "docs" / "governance"
    gov.mkdir(parents=True)
    (gov / "flag-rule-baseline.json").write_text(content, encoding="utf-8")

    with pytest.raises(flag_rule.BaselineUnreadable):
        flag_rule.load_baseline(tmp_path)


# --- is_post_rule --------------------------------------------------------------------------


def test_a_baselined_spec_is_pre_rule_and_any_other_is_post_rule(tmp_path: Path):
    old = f"{SPECS_DIR}/spec-1-1-old.md"
    root = _repo(tmp_path, baseline=[old])

    assert flag_rule.is_post_rule(old, repo_root=root) is False
    assert flag_rule.is_post_rule(root / old, repo_root=root) is False
    assert flag_rule.is_post_rule(f"{SPECS_DIR}/spec-1-2-new.md", repo_root=root) is True
    assert flag_rule.is_post_rule("./" + old, repo_root=root) is False


def test_the_specs_own_created_date_never_decides_post_rule(tmp_path: Path):
    old = f"{SPECS_DIR}/spec-1-1-old.md"
    root = _repo(tmp_path, baseline=[old])
    spec = _spec(root, "created: '2020-01-01'\n", "spec-1-2-claims-to-be-old.md")

    assert flag_rule.is_post_rule(spec, repo_root=root) is True


def test_is_post_rule_reads_the_live_baseline():
    baselined = "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-1-1-generate-legacy-contextual-skill.md"
    this_story = (
        "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/"
        "spec-34-1-the-flag-rule-has-a-closed-exemption-list-a-rule-date-baseline-and-one-block-shape.md"
    )

    assert flag_rule.is_post_rule(baselined) is False
    assert flag_rule.is_post_rule(REPO_ROOT / baselined) is False
    assert flag_rule.is_post_rule(this_story) is True


def test_repo_relative_normalises_the_forms_a_caller_passes(tmp_path: Path):
    assert flag_rule.repo_relative(tmp_path / "a" / "b.md", tmp_path) == "a/b.md"
    assert flag_rule.repo_relative("a/../a/b.md", tmp_path) == "a/b.md"
    assert flag_rule.repo_relative("/elsewhere/b.md", tmp_path) == "/elsewhere/b.md"


# --- in_scope (Q1) -------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["fix", "chore", "docs"])
def test_fix_chore_and_docs_are_out_of_scope(tmp_path: Path, kind: str):
    path = tmp_path / "spec-1-1-x.md"
    path.write_text(f"---\ntype: {kind}\n---\n", encoding="utf-8")

    assert flag_rule.in_scope(path) is False
    assert flag_rule.in_scope({"type": kind}) is False


def test_a_feature_is_in_scope_by_path_or_by_mapping(tmp_path: Path):
    path = tmp_path / "spec-1-1-x.md"
    path.write_text("---\ntype: 'feature'\n---\n", encoding="utf-8")

    assert flag_rule.in_scope(path) is True
    assert flag_rule.in_scope({"type": "feature"}) is True


def test_a_spec_with_no_type_or_no_frontmatter_is_out_of_scope(tmp_path: Path):
    bare = tmp_path / "spec-1-1-x.md"
    bare.write_text("no fence\n", encoding="utf-8")

    assert flag_rule.in_scope(bare) is False
    assert flag_rule.in_scope({}) is False
    assert flag_rule.in_scope(tmp_path / "absent.md") is False


# --- the population ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        (f"{SPECS_DIR}/spec-34-1-a-story.md", True),
        (f"{SPECS_DIR}/spec-34-1-a-story.memlog.md", False),
        (f"{SPECS_DIR}/spec-19-1-a-folder-spec/.memlog.md", False),
        (f"{SPECS_DIR}/spec-pyforge-doctor/SPEC.md", False),
        (f"{SPECS_DIR}/spec-22-prep-no-story-number.md", False),
        ("docs/specs/spec-1-1-legacy.md", False),
    ],
)
def test_is_story_spec(rel: str, expected: bool):
    assert flag_rule.is_story_spec(rel) is expected


# --- one declared source, and outside every station ----------------------------------------


def _hardcoded(source: str, values) -> list[str]:
    return [v for v in values if v in source]


def test_no_exemption_value_is_hard_coded_in_the_scripts():
    values = flag_rule.load_exemptions()

    for script in ("flag_rule.py", "flag_rule_baseline.py"):
        source = (_SCRIPTS_DIR / script).read_text(encoding="utf-8")
        assert _hardcoded(source, values) == [], f"{script} holds a copy of the roster's exemption list"


def test_the_hard_coded_scan_catches_a_copy():
    values = flag_rule.load_exemptions()

    assert _hardcoded('EXEMPT = {"docs-only"}\n', values) == ["docs-only"]
    assert _hardcoded("# nothing to see\n", values) == []


def test_the_scripts_import_no_station_module():
    for script in ("flag_rule.py", "flag_rule_baseline.py"):
        tree = ast.parse((_SCRIPTS_DIR / script).read_text(encoding="utf-8"))
        imported = [
            alias.name if isinstance(node, ast.Import) else (node.module or "")
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in (node.names if isinstance(node, ast.Import) else [node])
        ]
        assert not [m for m in imported if m == "pyforge" or m.startswith("pyforge.")], script


def test_flag_rule_never_exits():
    tree = ast.parse((_SCRIPTS_DIR / "flag_rule.py").read_text(encoding="utf-8"))

    calls = [ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)]
    assert not [c for c in calls if c in {"sys.exit", "exit", "quit", "os._exit"}]


# --- the stamper ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")
    _git(repo, "config", "commit.gpgsign", "false")


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _touch(repo: Path, rel: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\ntype: feature\n---\n", encoding="utf-8")


ACCENTED = f"{SPECS_DIR}/spec-22-4-a-diátaxis-adapted-layer.md"


@pytest.fixture
def stamped_repo(tmp_path: Path):
    """(repo, ruling sha): two story specs, an accented one, a memlog and a non-spec at the SHA;
    one more story spec committed after it."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    for rel in (f"{SPECS_DIR}/spec-1-1-old.md", ACCENTED, f"{SPECS_DIR}/spec-1-1-old.memlog.md", "docs/readme.md"):
        _touch(repo, rel)
    sha = _commit_all(repo, "the ruling commit")
    _touch(repo, f"{SPECS_DIR}/spec-2-1-minted-after.md")
    _commit_all(repo, "a later story")
    return repo, sha


def test_snapshot_reads_the_ruling_commits_tree_not_the_working_tree(stamped_repo):
    repo, sha = stamped_repo
    (repo / f"{SPECS_DIR}/spec-1-1-old.md").unlink()

    data = flag_rule_baseline.snapshot(repo, sha[:10])

    assert data["ruling_sha"] == sha
    assert data["specs"] == sorted([f"{SPECS_DIR}/spec-1-1-old.md", ACCENTED])
    assert f"{SPECS_DIR}/spec-2-1-minted-after.md" not in data["specs"]


def test_snapshot_defaults_to_the_recorded_ruling_sha():
    assert flag_rule_baseline.RULING_SHA == "5e977accb9643ff81f02ef9feca3e435d86816f9"
    assert flag_rule_baseline.RULE_DATE == "2026-09-28"


def test_main_snapshots_once_and_refuses_a_second(stamped_repo, capsys):
    repo, sha = stamped_repo
    baseline = repo / flag_rule.BASELINE_REL
    baseline.parent.mkdir(parents=True, exist_ok=True)

    assert flag_rule_baseline.main(["--snapshot", "--ruling-sha", sha], repo_root=repo) == 0
    written = baseline.read_text(encoding="utf-8")
    assert flag_rule_baseline.main(["--snapshot", "--ruling-sha", sha], repo_root=repo) == 1
    assert "refusing" in capsys.readouterr().out
    assert baseline.read_text(encoding="utf-8") == written
    assert flag_rule_baseline.main(["--snapshot", "--force", "--ruling-sha", sha], repo_root=repo) == 0

    assert flag_rule.load_baseline(repo) == {f"{SPECS_DIR}/spec-1-1-old.md", ACCENTED}
    assert flag_rule.is_post_rule(f"{SPECS_DIR}/spec-2-1-minted-after.md", repo_root=repo) is True


def test_main_reports_a_sha_it_cannot_resolve(stamped_repo):
    repo, _ = stamped_repo
    (repo / flag_rule.BASELINE_REL).parent.mkdir(parents=True, exist_ok=True)

    assert flag_rule_baseline.main(["--snapshot", "--ruling-sha", "0" * 40], repo_root=repo) == 2


def test_prune_only_removes_a_path_that_no_longer_exists(stamped_repo, capsys):
    repo, sha = stamped_repo
    (repo / flag_rule.BASELINE_REL).parent.mkdir(parents=True, exist_ok=True)
    flag_rule_baseline.main(["--snapshot", "--ruling-sha", sha], repo_root=repo)
    capsys.readouterr()

    assert flag_rule_baseline.main(["--prune"], repo_root=repo) == 0
    assert "nothing to remove" in capsys.readouterr().out

    (repo / f"{SPECS_DIR}/spec-1-1-old.md").unlink()
    assert flag_rule_baseline.main(["--prune"], repo_root=repo) == 0
    assert flag_rule.load_baseline(repo) == {ACCENTED}
    assert json.loads((repo / flag_rule.BASELINE_REL).read_text(encoding="utf-8"))["ruling_sha"] == sha


def test_prune_never_adds_a_path(stamped_repo):
    repo, sha = stamped_repo
    (repo / flag_rule.BASELINE_REL).parent.mkdir(parents=True, exist_ok=True)
    flag_rule_baseline.main(["--snapshot", "--ruling-sha", sha], repo_root=repo)
    # A brand-new story spec on disk is post-rule; pruning must not fold it into the baseline.
    newer = f"{SPECS_DIR}/spec-3-1-brand-new.md"
    _touch(repo, newer)
    (repo / f"{SPECS_DIR}/spec-1-1-old.md").unlink()

    flag_rule_baseline.main(["--prune"], repo_root=repo)

    assert newer not in flag_rule.load_baseline(repo)


def test_prune_without_a_baseline_exits_2(tmp_path: Path):
    assert flag_rule_baseline.main(["--prune"], repo_root=tmp_path) == 2


def test_the_live_baseline_records_the_ruling_sha_and_a_sorted_story_spec_population():
    data = flag_rule.read_baseline()

    assert data["ruling_sha"] == flag_rule_baseline.RULING_SHA
    assert data["rule_date"] == flag_rule_baseline.RULE_DATE
    assert data["specs"] == sorted(data["specs"])
    assert all(flag_rule.is_story_spec(s) for s in data["specs"])
    assert len(set(data["specs"])) == len(data["specs"])
