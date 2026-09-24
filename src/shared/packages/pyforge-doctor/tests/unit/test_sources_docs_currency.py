"""Unit tests for ``sources.docs_currency`` (Story 30.2 / spec-pyforge-doctor CAP-84).

Covers the story's I/O & Edge-Case Matrix (six rows) against temp fixture
trees + real tmp git repos only -- never the live ``docs/`` tree (mirrors
``test_sources_pixi_currency.py``'s / ``test_sources_docs_map_hygiene.py``'s
own fixture-helper style), plus ``render_map_registry``'s pure round-trip
and the schema-rejects-a-malformed-file case.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import jsonschema
import pytest
import yaml

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import docs_currency

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


# --- fixture helpers (mirrors test_sources_pixi_currency.py) ----------------


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return result.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


_POINTER_PAGE = {
    "path": "tutorials/README.md",
    "quadrant": "tutorials",
    "owner": "fleet",
    "kind": "pointer",
}


def _write_map_yaml(repo: Path, pages: list[dict]) -> None:
    docs = repo / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "map.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "pages": pages}, sort_keys=False),
        encoding="utf-8",
    )


def _write_map_md(repo: Path, registry_section: str | None) -> None:
    docs = repo / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    body = "# map\n\nsome narrative\n\n## Page registry (generated)\n\n"
    if registry_section is not None:
        body += "<!-- docs-map:registry:begin -->\n" + registry_section + "<!-- docs-map:registry:end -->\n"
    (docs / "MAP.md").write_text(body, encoding="utf-8")


def _write_authored_page(repo: Path, rel: str, *, frontmatter: str = "", body: str = "content\n") -> None:
    path = repo / "docs" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (f"---\n{frontmatter}---\n\n" if frontmatter else "") + body
    path.write_text(text, encoding="utf-8")


def _only(findings: tuple) -> object:
    assert len(findings) == 1, [f.message for f in findings]
    return findings[0]


# --- map-render --------------------------------------------------------------


def test_map_render_matching_registry_contributes_no_finding(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [_POINTER_PAGE]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _commit_all(tmp_path, "seed")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.OK
    assert finding.evidence["pages_checked"] == 1


def test_map_render_mismatch_emits_one_warn(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [_POINTER_PAGE]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, "### Tutorials\n\nstale hand-edited content\n")
    _commit_all(tmp_path, "seed")

    findings = docs_currency.gather(tmp_path)
    render_findings = [f for f in findings if f.check == "docs-currency-map-render"]
    assert len(render_findings) == 1
    assert render_findings[0].status == DoctorStatus.WARN
    assert render_findings[0].source == Source.DOCS_CURRENCY


def test_map_render_missing_markers_counts_as_mismatch(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [_POINTER_PAGE]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, None)
    _commit_all(tmp_path, "seed")

    findings = docs_currency.gather(tmp_path)
    render_findings = [f for f in findings if f.check == "docs-currency-map-render"]
    assert len(render_findings) == 1
    assert render_findings[0].evidence["markers_present"] is False


# --- authored-page-stale: sources/verified frontmatter -----------------------


def test_authored_page_with_stale_source_emits_warn(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/example.md",
            "quadrant": "how-to",
            "owner": "fleet",
            "kind": "authored",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("v1\n", encoding="utf-8")
    _write_authored_page(
        tmp_path,
        "how-to/example.md",
        frontmatter="sources:\n  - tracked.txt\nverified: 2020-01-01\n",
    )
    _commit_all(tmp_path, "seed at verified date")
    tracked.write_text("v2\n", encoding="utf-8")
    _commit_all(tmp_path, "tracked.txt moved past verified:")

    findings = docs_currency.gather(tmp_path)
    stale = [f for f in findings if f.check == "docs-currency-authored-stale"]
    assert len(stale) == 1
    assert stale[0].status == DoctorStatus.WARN
    assert stale[0].evidence["page"] == "docs/how-to/example.md"
    assert stale[0].evidence["stale_sources"][0]["source"] == "tracked.txt"
    assert stale[0].evidence["stale_sources"][0]["verified"] == "2020-01-01"


def test_authored_page_with_current_source_reports_no_stale_finding(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/example.md",
            "quadrant": "how-to",
            "owner": "fleet",
            "kind": "authored",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    (tmp_path / "tracked.txt").write_text("v1\n", encoding="utf-8")
    _write_authored_page(
        tmp_path,
        "how-to/example.md",
        frontmatter="sources:\n  - tracked.txt\nverified: 2099-01-01\n",
    )
    _commit_all(tmp_path, "seed, verified far in the future")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.OK


def test_authored_page_with_source_never_in_git_history_emits_warn(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/example.md",
            "quadrant": "how-to",
            "owner": "fleet",
            "kind": "authored",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(
        tmp_path,
        "how-to/example.md",
        # never-committed.txt is named but never created/committed -- a
        # typo, or a source that moved. A stronger signal than staleness,
        # not "silently current".
        frontmatter="sources:\n  - never-committed.txt\nverified: 2020-01-01\n",
    )
    _commit_all(tmp_path, "seed (never-committed.txt does not exist)")

    findings = docs_currency.gather(tmp_path)
    stale = [f for f in findings if f.check == "docs-currency-authored-stale"]
    assert len(stale) == 1
    assert stale[0].evidence["stale_sources"] == [
        {
            "source": "never-committed.txt",
            "reason": "source not found in git history",
            "verified": "2020-01-01",
        }
    ]


# --- authored-page-stale: dead body references --------------------------------


def test_authored_page_with_dead_reference_emits_warn(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/example.md",
            "quadrant": "how-to",
            "owner": "fleet",
            "kind": "authored",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(
        tmp_path,
        "how-to/example.md",
        body="See `docs/does-not-exist.md` for detail.\n",
    )
    _commit_all(tmp_path, "seed")

    findings = docs_currency.gather(tmp_path)
    stale = [f for f in findings if f.check == "docs-currency-authored-stale"]
    assert len(stale) == 1
    assert stale[0].evidence["dead_references"] == ["docs/does-not-exist.md"]


def test_authored_page_dead_reference_inside_ignore_marker_is_skipped(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/example.md",
            "quadrant": "how-to",
            "owner": "fleet",
            "kind": "authored",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(
        tmp_path,
        "how-to/example.md",
        body=(
            "<!-- governance-currency:ignore-start (historical) -->\n"
            "See `docs/does-not-exist.md` for detail.\n"
            "<!-- governance-currency:ignore-end -->\n"
        ),
    )
    _commit_all(tmp_path, "seed")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.OK


def test_dead_looking_reference_covered_by_gitignore_is_not_flagged(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/example.md",
            "quadrant": "how-to",
            "owner": "fleet",
            "kind": "authored",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    (tmp_path / ".gitignore").write_text("docs/generated-ignored.md\n", encoding="utf-8")
    _write_authored_page(
        tmp_path,
        "how-to/example.md",
        # Never written to disk, but covered by .gitignore -- a legitimately
        # absent generated artifact, not a dead reference.
        body="See `docs/generated-ignored.md` for detail.\n",
    )
    _commit_all(tmp_path, "seed with .gitignore rule (ignored path never created)")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.OK


# --- generated-page-stale (Story 30.3, spec-pyforge-doctor CAP-84) -----------


def _write_generator_script(repo: Path, rel: str, *, exit_code: int) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"import sys\nsys.exit({exit_code})\n", encoding="utf-8")


def test_generated_page_current_reports_no_finding(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/pixi-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
            "generator": "scripts/docs_pixi_tasks.py",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/pixi-tasks.md", body="generated content\n")
    _write_generator_script(tmp_path, "scripts/docs_pixi_tasks.py", exit_code=0)
    _commit_all(tmp_path, "seed")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.OK


def test_generated_page_stale_emits_warn(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/pixi-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
            "generator": "scripts/docs_pixi_tasks.py",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/pixi-tasks.md", body="stale content\n")
    _write_generator_script(tmp_path, "scripts/docs_pixi_tasks.py", exit_code=1)
    _commit_all(tmp_path, "seed")

    findings = docs_currency.gather(tmp_path)
    stale = [f for f in findings if f.check == "docs-currency-generated-stale"]
    assert len(stale) == 1
    assert stale[0].status == DoctorStatus.WARN
    assert stale[0].source == Source.DOCS_CURRENCY
    assert stale[0].evidence["page"] == "docs/how-to/pixi-tasks.md"
    assert stale[0].evidence["generator"] == "scripts/docs_pixi_tasks.py"


def test_generated_page_with_no_generator_declared_emits_warn(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/pixi-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/pixi-tasks.md", body="content\n")
    _commit_all(tmp_path, "seed")

    findings = docs_currency.gather(tmp_path)
    stale = [f for f in findings if f.check == "docs-currency-generated-stale"]
    assert len(stale) == 1
    assert "declares no" in stale[0].message


def test_generated_page_with_missing_generator_script_emits_warn(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/pixi-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
            "generator": "scripts/does_not_exist.py",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/pixi-tasks.md", body="content\n")
    _commit_all(tmp_path, "seed")

    findings = docs_currency.gather(tmp_path)
    stale = [f for f in findings if f.check == "docs-currency-generated-stale"]
    assert len(stale) == 1
    assert "does not exist" in stale[0].message


def test_generated_page_never_yet_generated_is_skipped(tmp_path: Path):
    # No page file on disk at all -- docs-map-hygiene's territory, not this
    # check's -- mirrors the authored-page-stale check's same discretion.
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/pixi-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
            "generator": "scripts/docs_pixi_tasks.py",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_generator_script(tmp_path, "scripts/docs_pixi_tasks.py", exit_code=1)
    _commit_all(tmp_path, "seed")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.OK


# --- skill-dir-hygiene --------------------------------------------------------


def test_skill_dir_stray_readme_emits_warn(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [_POINTER_PAGE]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    skill_dir = tmp_path / ".claude" / "skills" / "bmad-example"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    (skill_dir / "README.md").write_text("stub\n", encoding="utf-8")
    _commit_all(tmp_path, "seed")

    findings = docs_currency.gather(tmp_path)
    hygiene = [f for f in findings if f.check == "docs-currency-skill-dir-hygiene"]
    assert len(hygiene) == 1
    assert hygiene[0].status == DoctorStatus.WARN
    assert hygiene[0].evidence["paths"] == [".claude/skills/bmad-example/README.md"]


def test_unmanaged_skill_dir_prefix_is_ignored(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [_POINTER_PAGE]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    skill_dir = tmp_path / ".claude" / "skills" / "conda-forge-expert"
    skill_dir.mkdir(parents=True)
    (skill_dir / "README.md").write_text("stub\n", encoding="utf-8")
    _commit_all(tmp_path, "seed")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.OK


# --- fail-open: docs/map.yaml missing / schema-invalid -----------------------


def test_map_yaml_missing_degrades_to_one_warn(tmp_path: Path):
    _init_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    # No commit needed -- load_map_yaml raises before any git call happens.

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.WARN
    assert finding.source == Source.DOCS_CURRENCY


def test_map_yaml_schema_invalid_degrades_to_one_warn(tmp_path: Path):
    _init_repo(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "map.yaml").write_text(
        "schema_version: 1\npages:\n  - path: x.md\n", encoding="utf-8"
    )  # missing required quadrant/owner/kind
    _commit_all(tmp_path, "invalid map.yaml")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.WARN


def test_load_map_yaml_raises_value_error_when_missing(tmp_path: Path):
    with pytest.raises(ValueError, match="does not exist"):
        docs_currency.load_map_yaml(tmp_path)


def test_load_map_yaml_raises_validation_error_on_malformed_file(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "map.yaml").write_text(
        "schema_version: 1\npages:\n  - path: x.md\n    quadrant: not-a-real-quadrant\n"
        "    owner: fleet\n    kind: authored\n",
        encoding="utf-8",
    )
    with pytest.raises(jsonschema.ValidationError):
        docs_currency.load_map_yaml(tmp_path)


# --- render_map_registry: pure round-trip -------------------------------------


def test_render_map_registry_groups_by_quadrant_sorted_by_path():
    pages = [
        {"path": "how-to/b.md", "quadrant": "how-to", "owner": "fleet", "kind": "authored"},
        {"path": "how-to/a.md", "quadrant": "how-to", "owner": "doctor", "kind": "pointer"},
        {"path": "tutorials/z.md", "quadrant": "tutorials", "owner": "fleet", "kind": "authored"},
    ]

    rendered = docs_currency.render_map_registry(pages)

    assert rendered == (
        "### Tutorials\n\n"
        "| Page | Owner | Kind |\n"
        "|---|---|---|\n"
        "| [`tutorials/z.md`](tutorials/z.md) | fleet | authored |\n\n"
        "### How-to\n\n"
        "| Page | Owner | Kind |\n"
        "|---|---|---|\n"
        "| [`how-to/a.md`](how-to/a.md) | doctor | pointer |\n"
        "| [`how-to/b.md`](how-to/b.md) | fleet | authored |\n\n"
        "### Reference\n\n"
        "| Page | Owner | Kind |\n"
        "|---|---|---|\n\n"
        "### Explanation\n\n"
        "| Page | Owner | Kind |\n"
        "|---|---|---|\n"
    )


def test_render_map_registry_is_deterministic():
    pages = [_POINTER_PAGE]
    assert docs_currency.render_map_registry(pages) == docs_currency.render_map_registry(list(pages))
