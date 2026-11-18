"""Unit tests for ``sources.docs_currency`` (Story 30.2 / spec-pyforge-doctor CAP-84).

Covers the story's I/O & Edge-Case Matrix (six rows) against temp fixture
trees + real tmp git repos only -- never the live ``docs/`` tree (mirrors
``test_sources_pixi_currency.py``'s / ``test_sources_docs_map_hygiene.py``'s
own fixture-helper style), plus ``render_map_registry``'s pure round-trip
and the schema-rejects-a-malformed-file case.

The registry is enforced (2026-11-17): an unstamped ``kind: authored`` page, a
stale or missing source, a dead reference, a stale generated page and a stale
MAP.md render each read FAIL; every could-not-measure path stays one WARN.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import jsonschema
import pytest
import yaml

from pyforge.doctor.models import DoctorStatus, Source, is_gather_failure
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


#: A current stamp: ``docs/map.yaml`` is committed in every fixture tree and never touched after 2099.
_STAMP = "sources:\n  - docs/map.yaml\nverified: 2099-01-01\n"


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


def test_map_render_mismatch_emits_one_fail(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [_POINTER_PAGE]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, "### Tutorials\n\nstale hand-edited content\n")
    _commit_all(tmp_path, "seed")

    findings = docs_currency.gather(tmp_path)
    render_findings = [f for f in findings if f.check == "docs-currency-map-render"]
    assert len(render_findings) == 1
    assert render_findings[0].status == DoctorStatus.FAIL
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
    assert render_findings[0].status == DoctorStatus.FAIL
    assert render_findings[0].evidence["markers_present"] is False


def test_map_md_missing_stays_one_warn(tmp_path: Path):
    """No MAP.md to compare is could-not-measure, never a stale render."""
    _init_repo(tmp_path)
    pages = [_POINTER_PAGE]
    _write_map_yaml(tmp_path, pages)
    _commit_all(tmp_path, "seed")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.check == "docs-currency-map-render"
    assert finding.status == DoctorStatus.WARN


# --- authored-page-stale: sources/verified frontmatter -----------------------


def test_authored_page_with_stale_source_emits_fail(tmp_path: Path):
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
    assert stale[0].status == DoctorStatus.FAIL
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


def test_authored_page_with_missing_source_path_emits_fail(tmp_path: Path):
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
        # never-committed.txt is named but never created -- a typo, or a
        # source that moved. A stronger signal than staleness, not
        # "silently current".
        frontmatter="sources:\n  - never-committed.txt\nverified: 2020-01-01\n",
    )
    _commit_all(tmp_path, "seed (never-committed.txt does not exist)")

    findings = docs_currency.gather(tmp_path)
    stale = [f for f in findings if f.check == "docs-currency-authored-stale"]
    assert len(stale) == 1
    assert stale[0].status == DoctorStatus.FAIL
    assert stale[0].evidence["stale_sources"] == [
        {
            "source": "never-committed.txt",
            "reason": "source does not exist",
            "verified": "2020-01-01",
        }
    ]
    assert not [f for f in findings if f.check == "docs-currency-authored-unstamped"]


def test_authored_page_with_source_on_disk_but_never_committed_emits_fail(tmp_path: Path):
    """A source git has no history for (untracked, or ignored) can never be measured against ``verified:``."""
    _authored_tree(tmp_path, "content\n", frontmatter="sources:\n  - scratch.txt\nverified: 2099-01-01\n")
    (tmp_path / "scratch.txt").write_text("not committed\n", encoding="utf-8")

    stale = [f for f in docs_currency.gather(tmp_path) if f.check == "docs-currency-authored-stale"]
    assert len(stale) == 1
    assert stale[0].status == DoctorStatus.FAIL
    assert stale[0].evidence["stale_sources"] == [
        {"source": "scratch.txt", "reason": "source not found in git history", "verified": "2099-01-01"}
    ]


@pytest.mark.parametrize("source", ["../outside.txt", "/etc/hosts"])
def test_a_source_that_is_not_repo_relative_emits_fail_and_never_reaches_git(tmp_path: Path, source: str):
    """Such a path would make ``git log`` refuse; it is a FAIL on the page, never a degraded gather."""
    _authored_tree(tmp_path / "repo", "content\n", frontmatter=f"sources:\n  - {source}\nverified: 2099-01-01\n")
    (tmp_path / "outside.txt").write_text("x\n", encoding="utf-8")

    finding = _only(docs_currency.gather(tmp_path / "repo"))
    assert finding.check == "docs-currency-authored-stale"
    assert finding.status == DoctorStatus.FAIL
    assert finding.evidence["stale_sources"] == [
        {"source": source, "reason": "source is not a repo-relative path", "verified": "2099-01-01"}
    ]


def _commit_on(repo: Path, message: str, day: str, monkeypatch: pytest.MonkeyPatch) -> None:
    stamp = f"{day}T12:00:00+00:00"
    monkeypatch.setenv("GIT_AUTHOR_DATE", stamp)
    monkeypatch.setenv("GIT_COMMITTER_DATE", stamp)
    _commit_all(repo, message)


@pytest.mark.parametrize(
    ("verified", "status"),
    [("2021-06-15", DoctorStatus.OK), ("2021-06-14", DoctorStatus.FAIL), ("2021-06-16", DoctorStatus.OK)],
)
def test_a_source_touched_on_the_verified_date_is_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, verified: str, status: DoctorStatus
):
    """Same-day edits pass: only a source touched on a LATER date than ``verified:`` is stale."""
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {"path": "how-to/example.md", "quadrant": "how-to", "owner": "fleet", "kind": "authored"},
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    (tmp_path / "tracked.txt").write_text("v1\n", encoding="utf-8")
    _write_authored_page(
        tmp_path, "how-to/example.md", frontmatter=f"sources:\n  - tracked.txt\nverified: {verified}\n"
    )
    _commit_on(tmp_path, "seed", "2021-06-01", monkeypatch)
    (tmp_path / "tracked.txt").write_text("v2\n", encoding="utf-8")
    _commit_on(tmp_path, "tracked.txt touched on 2021-06-15", "2021-06-15", monkeypatch)

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == status
    if status is DoctorStatus.FAIL:
        assert finding.check == "docs-currency-authored-stale"
        assert finding.evidence["stale_sources"] == [
            {"source": "tracked.txt", "source_touched": "2021-06-15", "verified": verified}
        ]


def test_git_that_cannot_be_read_degrades_to_one_warn(tmp_path: Path):
    """No git history to read is could-not-measure: one WARN for the gather, never a FAIL per source."""
    pages = [
        _POINTER_PAGE,
        {"path": "how-to/example.md", "quadrant": "how-to", "owner": "fleet", "kind": "authored"},
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/example.md", frontmatter=_STAMP)
    (tmp_path / ".git").write_text("gitdir: /nonexistent/not-a-repository\n", encoding="utf-8")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.WARN
    assert finding.check == "docs-currency-authored-stale"
    assert is_gather_failure(finding)


def test_git_that_cannot_be_read_does_not_hide_an_unstamped_page(tmp_path: Path):
    """An unstamped page needs no git to be seen (Story 60.2): it still FAILs beside the one could-not-measure
    WARN, and is reported before it."""
    pages = [
        _POINTER_PAGE,
        {"path": "how-to/a-stamped.md", "quadrant": "how-to", "owner": "fleet", "kind": "authored"},
        {"path": "how-to/b-unstamped.md", "quadrant": "how-to", "owner": "fleet", "kind": "authored"},
        {"path": "how-to/c-stamped.md", "quadrant": "how-to", "owner": "fleet", "kind": "authored"},
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/a-stamped.md", frontmatter=_STAMP)
    _write_authored_page(tmp_path, "how-to/b-unstamped.md")
    _write_authored_page(tmp_path, "how-to/c-stamped.md", frontmatter=_STAMP)
    (tmp_path / ".git").write_text("gitdir: /nonexistent/not-a-repository\n", encoding="utf-8")

    findings = docs_currency.gather(tmp_path)
    assert [(f.check, f.status) for f in findings] == [
        ("docs-currency-authored-unstamped", DoctorStatus.FAIL),
        ("docs-currency-authored-stale", DoctorStatus.WARN),
    ]
    assert findings[0].evidence["page"] == "docs/how-to/b-unstamped.md"
    assert is_gather_failure(findings[1])


def test_git_that_cannot_be_read_still_reports_a_source_that_does_not_exist(tmp_path: Path):
    """A missing source path is read from the tree, not from git: it FAILs whether or not git answers."""
    pages = [
        _POINTER_PAGE,
        {"path": "how-to/example.md", "quadrant": "how-to", "owner": "fleet", "kind": "authored"},
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(
        tmp_path, "how-to/example.md", frontmatter="sources:\n  - docs/map.yaml\n  - gone.txt\nverified: 2099-01-01\n"
    )
    (tmp_path / ".git").write_text("gitdir: /nonexistent/not-a-repository\n", encoding="utf-8")

    findings = docs_currency.gather(tmp_path)
    assert [(f.check, f.status) for f in findings] == [
        ("docs-currency-authored-stale", DoctorStatus.FAIL),
        ("docs-currency-authored-stale", DoctorStatus.WARN),
    ]
    assert findings[0].evidence["stale_sources"] == [
        {"source": "gone.txt", "reason": "source does not exist", "verified": "2099-01-01"}
    ]


def _shallow_clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, extra_pages: tuple[str, ...] = ()) -> Path:
    """A depth-1 clone of a two-commit repository whose stamped page cites a source last touched in the FIRST
    commit, before the page's ``verified:`` date. Full history reads it current; the shallow clone cannot."""
    origin = tmp_path / "origin"
    _init_repo(origin)
    pages = [
        _POINTER_PAGE,
        {"path": "how-to/example.md", "quadrant": "how-to", "owner": "fleet", "kind": "authored"},
        *({"path": rel, "quadrant": "how-to", "owner": "fleet", "kind": "authored"} for rel in extra_pages),
    ]
    _write_map_yaml(origin, pages)
    _write_map_md(origin, docs_currency.render_map_registry(pages))
    (origin / "tracked.txt").write_text("v1\n", encoding="utf-8")
    _write_authored_page(origin, "how-to/example.md", frontmatter="sources:\n  - tracked.txt\nverified: 2021-06-10\n")
    for rel in extra_pages:
        _write_authored_page(origin, rel)
    _commit_on(origin, "seed", "2021-06-01", monkeypatch)
    (origin / "unrelated.txt").write_text("later\n", encoding="utf-8")
    _commit_on(origin, "an unrelated later commit", "2021-07-01", monkeypatch)
    if not extra_pages:
        assert _only(docs_currency.gather(origin)).status == DoctorStatus.OK  # full history: current

    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", "--depth", "1", origin.as_uri(), str(clone))
    assert _git(clone, "rev-parse", "--is-shallow-repository").strip() == "true"
    return clone


def test_a_shallow_repository_is_could_not_measure_not_a_fail_per_page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A shallow clone has no last-touch history to read (git attributes every path to the graft boundary, or
    to nothing), so the stale-source check reads one WARN, never a FAIL per stamped page (Story 60.2)."""
    clone = _shallow_clone(tmp_path, monkeypatch)

    finding = _only(docs_currency.gather(clone))
    assert finding.check == "docs-currency-authored-stale"
    assert finding.status == DoctorStatus.WARN
    assert "shallow" in finding.message
    assert is_gather_failure(finding)


def test_a_shallow_repository_does_not_hide_an_unstamped_page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    clone = _shallow_clone(tmp_path, monkeypatch, extra_pages=("how-to/unstamped.md",))

    findings = docs_currency.gather(clone)
    assert [(f.check, f.status) for f in findings] == [
        ("docs-currency-authored-unstamped", DoctorStatus.FAIL),
        ("docs-currency-authored-stale", DoctorStatus.WARN),
    ]
    assert findings[0].evidence["page"] == "docs/how-to/unstamped.md"


# --- authored-unstamped: the registry is enforced ----------------------------


@pytest.mark.parametrize(
    ("frontmatter", "missing"),
    [
        ("", ["sources", "verified"]),
        ("title: Example\n", ["sources", "verified"]),
        ("verified: 2099-01-01\n", ["sources"]),
        ("sources: []\nverified: 2099-01-01\n", ["sources"]),
        ("sources: docs/map.yaml\nverified: 2099-01-01\n", ["sources"]),
        ("sources:\n  - 7\nverified: 2099-01-01\n", ["sources"]),
        ("sources:\n  - docs/map.yaml\n", ["verified"]),
        ("sources:\n  - docs/map.yaml\nverified: last tuesday\n", ["verified"]),
    ],
)
def test_an_authored_page_without_a_stamp_emits_fail(tmp_path: Path, frontmatter: str, missing: list[str]):
    _authored_tree(tmp_path, "content\n", frontmatter=frontmatter)

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.check == "docs-currency-authored-unstamped"
    assert finding.status == DoctorStatus.FAIL
    assert finding.source == Source.DOCS_CURRENCY
    assert finding.evidence == {"page": "docs/how-to/example.md", "missing": missing}
    assert "docs/how-to/example.md" in finding.message


def test_an_unstamped_page_with_a_dead_reference_emits_both_findings(tmp_path: Path):
    _authored_tree(tmp_path, "See `docs/does-not-exist.md`.\n", frontmatter="")

    findings = docs_currency.gather(tmp_path)
    assert sorted(f.check for f in findings) == ["docs-currency-authored-stale", "docs-currency-authored-unstamped"]
    assert {f.status for f in findings} == {DoctorStatus.FAIL}


def test_a_pointer_or_generated_page_needs_no_stamp(tmp_path: Path):
    _init_repo(tmp_path)
    pages = [_POINTER_PAGE]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "tutorials/README.md")
    _commit_all(tmp_path, "seed")

    assert _only(docs_currency.gather(tmp_path)).status == DoctorStatus.OK


_PIXI_WITH_TASKS = (
    '[tasks]\ninline-check = "python -m x"\n\n'
    '[feature.guild-tasks.tasks.owner-check]\ncmd = "python -m y"\n\n'
    '[feature.guild-tasks.tasks]\ntable-check = { cmd = "python -m z" }\n\n'
    '[dependencies]\nsome-dep = "*"\n'
)


@pytest.mark.parametrize("task", ["owner-check", "inline-check", "table-check"])
def test_checked_by_naming_a_pixi_task_stands_in_for_the_stamp(tmp_path: Path, task: str):
    _authored_tree(tmp_path, "content\n", frontmatter=f"checked_by: {task}\n", pixi_toml=_PIXI_WITH_TASKS)

    assert _only(docs_currency.gather(tmp_path)).status == DoctorStatus.OK


@pytest.mark.parametrize(
    ("checked_by", "pixi_toml", "why"),
    [
        ("no-such-check", _PIXI_WITH_TASKS, "names no task in pixi.toml"),
        ("some-dep", _PIXI_WITH_TASKS, "names no task in pixi.toml"),
        ("owner-check", "", "pixi.toml does not exist"),
        ("[owner-check]", _PIXI_WITH_TASKS, "is not a task name"),
        ("''", _PIXI_WITH_TASKS, "is not a task name"),
    ],
)
def test_checked_by_that_does_not_resolve_emits_fail(tmp_path: Path, checked_by: str, pixi_toml: str, why: str):
    _authored_tree(tmp_path, "content\n", frontmatter=f"checked_by: {checked_by}\n", pixi_toml=pixi_toml)

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.check == "docs-currency-authored-unstamped"
    assert finding.status == DoctorStatus.FAIL
    assert why in finding.message
    assert finding.evidence["page"] == "docs/how-to/example.md"
    assert why in finding.evidence["reason"]


def test_checked_by_skips_the_stale_source_check_but_not_the_dead_reference_check(tmp_path: Path):
    _authored_tree(
        tmp_path,
        "See `docs/does-not-exist.md`.\n",
        frontmatter="checked_by: owner-check\nsources:\n  - never-there.txt\nverified: 2000-01-01\n",
        pixi_toml=_PIXI_WITH_TASKS,
    )

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.check == "docs-currency-authored-stale"
    assert finding.status == DoctorStatus.FAIL
    assert finding.evidence == {"page": "docs/how-to/example.md", "dead_references": ["docs/does-not-exist.md"]}


def test_a_pixi_toml_that_does_not_parse_degrades_to_one_warn(tmp_path: Path):
    _authored_tree(tmp_path, "content\n", frontmatter="checked_by: owner-check\n", pixi_toml="[tasks\n")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.WARN
    assert is_gather_failure(finding)


# --- authored-page-stale: dead body references --------------------------------


def test_authored_page_with_dead_reference_emits_fail(tmp_path: Path):
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
        frontmatter=_STAMP,
        body="See `docs/does-not-exist.md` for detail.\n",
    )
    _commit_all(tmp_path, "seed")

    stale = _only(docs_currency.gather(tmp_path))
    assert stale.check == "docs-currency-authored-stale"
    assert stale.status == DoctorStatus.FAIL
    assert stale.evidence["dead_references"] == ["docs/does-not-exist.md"]


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
        frontmatter=_STAMP,
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
        frontmatter=_STAMP,
        body="See `docs/generated-ignored.md` for detail.\n",
    )
    _commit_all(tmp_path, "seed with .gitignore rule (ignored path never created)")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.OK


# --- generated-page-stale (Story 30.3, spec-pyforge-doctor CAP-84) -----------


def _write_checkout_stub_generator(
    checkout: Path,
    rel: str,
    *,
    exit_code: int,
    probe: Path | None = None,
) -> Path:
    path = checkout / rel
    probe_line = ""
    if probe is not None:
        probe_line = f"    Path({str(probe)!r}).write_text('executed')\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "import argparse\nimport sys\nfrom pathlib import Path\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('--check', action='store_true')\n"
        "parser.add_argument('--root', type=Path, default=None)\n"
        "args = parser.parse_args()\n"
        "if args.check:\n"
        f"{probe_line}"
        f"    sys.exit({exit_code})\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    return path


def _write_generator_script(repo: Path, rel: str, *, exit_code: int) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"import sys\nsys.exit({exit_code})\n", encoding="utf-8")


def test_generated_page_current_reports_no_finding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    doctor_script = _write_checkout_stub_generator(checkout, "scripts/docs_fixture_tasks.py", exit_code=0)
    monkeypatch.setattr(
        docs_currency,
        "locate_checkout_script",
        lambda name: (
            doctor_script
            if name == "docs_fixture_tasks.py"
            else (_ for _ in ()).throw(FileNotFoundError(f"scripts/{name} not found"))
        ),
    )

    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/fixture-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
            "generator": "scripts/docs_fixture_tasks.py",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/fixture-tasks.md", body="generated content\n")
    probe = tmp_path / "probe.txt"
    _write_generator_script(tmp_path, "scripts/docs_fixture_tasks.py", exit_code=1)
    (tmp_path / "scripts" / "docs_fixture_tasks.py").write_text(
        f"from pathlib import Path\nPath({str(probe)!r}).write_text('executed')\nimport sys\nsys.exit(1)\n",
        encoding="utf-8",
    )
    _commit_all(tmp_path, "seed")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.OK
    assert not probe.exists()


def test_generated_page_stale_emits_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    doctor_script = _write_checkout_stub_generator(checkout, "scripts/docs_fixture_tasks.py", exit_code=1)
    monkeypatch.setattr(
        docs_currency,
        "locate_checkout_script",
        lambda name: (
            doctor_script
            if name == "docs_fixture_tasks.py"
            else (_ for _ in ()).throw(FileNotFoundError(f"scripts/{name} not found"))
        ),
    )

    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/fixture-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
            "generator": "scripts/docs_fixture_tasks.py",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/fixture-tasks.md", body="stale content\n")
    _write_generator_script(tmp_path, "scripts/docs_fixture_tasks.py", exit_code=0)
    _commit_all(tmp_path, "seed")

    findings = docs_currency.gather(tmp_path)
    stale = [f for f in findings if f.check == "docs-currency-generated-stale"]
    assert len(stale) == 1
    assert stale[0].status == DoctorStatus.FAIL
    assert stale[0].source == Source.DOCS_CURRENCY
    assert stale[0].evidence["page"] == "docs/how-to/fixture-tasks.md"
    assert stale[0].evidence["generator"] == "scripts/docs_fixture_tasks.py"


def test_generated_page_with_no_generator_declared_emits_fail(tmp_path: Path):
    """A registry defect, not could-not-measure (Story 60.2): the row can never be checked until it is fixed."""
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/fixture-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/fixture-tasks.md", body="content\n")
    _commit_all(tmp_path, "seed")

    findings = docs_currency.gather(tmp_path)
    stale = [f for f in findings if f.check == "docs-currency-generated-stale"]
    assert len(stale) == 1
    assert stale[0].status == DoctorStatus.FAIL
    assert "declares no" in stale[0].message


def test_generated_page_with_disallowed_generator_path_emits_fail(tmp_path: Path):
    """A generator outside ``scripts/docs_*.py`` is a registry defect too, and is never run."""
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/fixture-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
            "generator": "scripts/does_not_exist.py",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/fixture-tasks.md", body="content\n")
    _commit_all(tmp_path, "seed")

    findings = docs_currency.gather(tmp_path)
    stale = [f for f in findings if f.check == "docs-currency-generated-stale"]
    assert len(stale) == 1
    assert stale[0].status == DoctorStatus.FAIL
    assert "not an allowed" in stale[0].message


def test_generated_page_with_parent_segment_in_generator_is_not_executed(tmp_path: Path):
    _init_repo(tmp_path)
    probe = tmp_path / "probe.txt"
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/fixture-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
            "generator": "scripts/../probe.py",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/fixture-tasks.md", body="content\n")
    (tmp_path / "probe.py").write_text(
        f"from pathlib import Path\nPath({str(probe)!r}).write_text('executed')\n",
        encoding="utf-8",
    )
    _commit_all(tmp_path, "seed")

    findings = docs_currency.gather(tmp_path)
    stale = [f for f in findings if f.check == "docs-currency-generated-stale"]
    assert len(stale) == 1
    assert stale[0].status == DoctorStatus.FAIL
    assert "not an allowed" in stale[0].message
    assert not probe.exists()


def test_generated_page_missing_in_doctor_checkout_emits_warn_without_target_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _init_repo(tmp_path)
    probe = tmp_path / "probe.txt"
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/fixture-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
            "generator": "scripts/docs_fixture_tasks.py",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/fixture-tasks.md", body="content\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "docs_fixture_tasks.py").write_text(
        f"from pathlib import Path\nPath({str(probe)!r}).write_text('executed')\nimport sys\nsys.exit(0)\n",
        encoding="utf-8",
    )
    _commit_all(tmp_path, "seed")

    def _no_checkout(name: str) -> Path:
        raise FileNotFoundError(f"scripts/{name} not found above /nowhere")

    monkeypatch.setattr(docs_currency, "locate_checkout_script", _no_checkout)

    findings = docs_currency.gather(tmp_path)
    stale = [f for f in findings if f.check == "docs-currency-generated-stale"]
    assert len(stale) == 1
    assert stale[0].status == DoctorStatus.WARN
    assert "could not run generator" in stale[0].message
    assert not probe.exists()


def test_generated_page_never_yet_generated_is_skipped(tmp_path: Path):
    # No page file on disk at all -- docs-map-hygiene's territory, not this
    # check's -- mirrors the authored-page-stale check's same discretion.
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/fixture-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
            "generator": "scripts/docs_fixture_tasks.py",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_generator_script(tmp_path, "scripts/docs_fixture_tasks.py", exit_code=1)
    _commit_all(tmp_path, "seed")

    finding = _only(docs_currency.gather(tmp_path))
    assert finding.status == DoctorStatus.OK


# --- generator trust (Story 40.2, DW-doctor-40-1-2) -------------------------


def test_the_judged_trees_declared_generator_is_data_never_executed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    doctor_script = _write_checkout_stub_generator(checkout, "scripts/docs_fixture_tasks.py", exit_code=0)
    monkeypatch.setattr(
        docs_currency,
        "locate_checkout_script",
        lambda name: (
            doctor_script
            if name == "docs_fixture_tasks.py"
            else (_ for _ in ()).throw(FileNotFoundError(f"scripts/{name} not found"))
        ),
    )

    _init_repo(tmp_path)
    probe = tmp_path / "probe.txt"
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/fixture-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
            "generator": "scripts/docs_fixture_tasks.py",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/fixture-tasks.md", body="generated content\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "docs_fixture_tasks.py").write_text(
        f"from pathlib import Path\nPath({str(probe)!r}).write_text('executed')\nimport sys\nsys.exit(1)\n",
        encoding="utf-8",
    )
    _commit_all(tmp_path, "seed")

    docs_currency.gather(tmp_path)

    assert not probe.exists(), "the judged tree's scripts/docs_fixture_tasks.py was executed"


def test_the_probe_runs_when_the_locator_resolves_from_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sensitivity twin (mutation): re-point the locator at `target` -- the pre-fix
    behaviour -- and the same planted script runs, so the test above can fail."""
    _init_repo(tmp_path)
    probe = tmp_path / "probe.txt"
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/fixture-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
            "generator": "scripts/docs_fixture_tasks.py",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/fixture-tasks.md", body="content\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "docs_fixture_tasks.py").write_text(
        f"from pathlib import Path\nPath({str(probe)!r}).write_text('executed')\nimport sys\nsys.exit(0)\n",
        encoding="utf-8",
    )
    _commit_all(tmp_path, "seed")

    monkeypatch.setattr(
        docs_currency,
        "locate_checkout_script",
        lambda name: tmp_path / "scripts" / name,
    )

    docs_currency.gather(tmp_path)

    assert probe.read_text(encoding="utf-8") == "executed"


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
    assert is_gather_failure(finding)


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


# --- Story 30.5 (DW-doctor-30-4-1, DW-doctor-30-4-2) -------------------------


def _generated_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, exit_code: int) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    doctor_script = _write_checkout_stub_generator(checkout, "scripts/docs_fixture_tasks.py", exit_code=exit_code)
    monkeypatch.setattr(docs_currency, "locate_checkout_script", lambda name: doctor_script)
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {
            "path": "how-to/fixture-tasks.md",
            "quadrant": "how-to",
            "owner": "steward",
            "kind": "generated",
            "generator": "scripts/docs_fixture_tasks.py",
        },
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    _write_authored_page(tmp_path, "how-to/fixture-tasks.md", body="generated content\n")
    _commit_all(tmp_path, "seed")


@pytest.mark.parametrize("exit_code", [2, 3])
def test_a_generator_that_cannot_run_reads_could_not_run_not_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int
):
    _generated_tree(tmp_path, monkeypatch, exit_code=exit_code)
    findings = [f for f in docs_currency.gather(tmp_path) if f.check == "docs-currency-generated-stale"]
    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.WARN
    assert "could not run generator scripts/docs_fixture_tasks.py" in findings[0].message
    assert f"exited {exit_code}" in findings[0].message
    assert "stale against its generator" not in findings[0].message
    assert findings[0].evidence["exit"] == exit_code


def test_a_generator_exit_1_still_reads_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _generated_tree(tmp_path, monkeypatch, exit_code=1)
    findings = [f for f in docs_currency.gather(tmp_path) if f.check == "docs-currency-generated-stale"]
    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.FAIL
    assert "stale against its generator" in findings[0].message


def test_a_generator_that_crashes_reads_could_not_run_not_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """An uncaught exception exits 1 too, the stale code; its traceback marks a crash, not a hand edit."""
    _generated_tree(tmp_path, monkeypatch, exit_code=1)
    stub = tmp_path / "checkout" / "scripts" / "docs_fixture_tasks.py"
    stub.write_text("raise RuntimeError('no head to stamp')\n", encoding="utf-8")
    findings = [f for f in docs_currency.gather(tmp_path) if f.check == "docs-currency-generated-stale"]
    assert len(findings) == 1
    assert "could not run generator scripts/docs_fixture_tasks.py" in findings[0].message
    assert "crashed" in findings[0].message
    assert findings[0].status == DoctorStatus.WARN
    assert "stale against its generator" not in findings[0].message
    assert findings[0].evidence["exit"] == 1


def _authored_tree(
    tmp_path: Path, body: str, *, gitignore: str = "", pixi_toml: str = "", frontmatter: str = _STAMP
) -> None:
    _init_repo(tmp_path)
    pages = [
        _POINTER_PAGE,
        {"path": "how-to/example.md", "quadrant": "how-to", "owner": "fleet", "kind": "authored"},
    ]
    _write_map_yaml(tmp_path, pages)
    _write_map_md(tmp_path, docs_currency.render_map_registry(pages))
    if gitignore:
        (tmp_path / ".gitignore").write_text(gitignore, encoding="utf-8")
    if pixi_toml:
        (tmp_path / "pixi.toml").write_text(pixi_toml, encoding="utf-8")
    _write_authored_page(tmp_path, "how-to/example.md", frontmatter=frontmatter, body=body)
    _commit_all(tmp_path, "seed")


def test_an_absent_directory_matched_only_by_a_directory_rule_is_not_dead(tmp_path: Path):
    """`docs/dashboard/kedro-viz/` is ignored by a directory-only rule and staged only at build time.

    Only a reference the page writes with the slash is retried; written without it, the same path reads
    as a file, and a deleted file is dead.
    """
    dead_by_body = {}
    for name, body in {
        "directory": "The export lands in `docs/build-export/`; `docs/never-there/` is a typo.\n",
        "file": "`docs/build-export` named as a file is dead.\n",
    }.items():
        _authored_tree(tmp_path / name, body, gitignore="docs/build-export/\n")
        findings = [f for f in docs_currency.gather(tmp_path / name) if f.check == "docs-currency-authored-stale"]
        assert len(findings) == 1
        dead_by_body[name] = findings[0].evidence["dead_references"]
    assert dead_by_body == {"directory": ["docs/never-there"], "file": ["docs/build-export"]}


def test_a_bmad_token_naming_a_check_task_is_not_dead(tmp_path: Path):
    """`bmad-output-hygiene` is a Doctor source whose detector task is `bmad-output-hygiene-check`."""
    _authored_tree(
        tmp_path,
        "Run `bmad-foo` for its verdict; `bmad-bar` names nothing.\n",
        pixi_toml='[feature.guild-tasks.tasks.bmad-foo-check]\ncmd = "python -m pyforge.doctor.sources bmad-foo"\n',
    )
    findings = [f for f in docs_currency.gather(tmp_path) if f.check == "docs-currency-authored-stale"]
    assert len(findings) == 1
    assert findings[0].evidence["dead_references"] == ["bmad-bar"]
