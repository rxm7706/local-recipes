"""Unit tests for ``sources.docs_map_hygiene`` (Story 30.1 / spec-pyforge-doctor CAP-83).

Covers the story I/O matrix against temp fixture trees only -- never the
live ``docs/`` tree. Scope under test: the four Diátaxis quadrants
(``docs/tutorials``, ``docs/how-to``, ``docs/reference``,
``docs/explanation``) vs the links in ``docs/MAP.md``; ``missing`` is FAIL,
``unmapped`` is FAIL (promoted from WARN by Story 30.2 / CAP-84),
quadrant-level ``README.md`` index pages are exempt, and MAP.md §
"Outside this map" layers are never scanned.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import jsonschema
import pytest
import yaml

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import docs_currency, docs_map_hygiene

_CHECK = "docs-map-hygiene"

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
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return result.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


_MINT_SECTIONS = [
    {
        "key": "herald",
        "label": "Herald",
        "href": "herald/",
        "owner": "herald",
        "order": 10,
        "entries": [
            {"key": "overview", "label": "Overview", "href": "herald/"},
            {"key": "dossier", "label": "Dossier", "href": "herald/dossier/"},
        ],
    },
    {"key": "pipelines", "label": "Kedro-Viz", "href": "dashboard/kedro-viz/", "owner": "atlas", "order": 30},
]


def _write_map_yaml(docs: Path, *, sections: list | None = None) -> None:
    pages = [
        {"path": rel, "quadrant": rel.split("/", 1)[0], "owner": "fleet", "kind": "authored"}
        for rel in (
            "tutorials/getting-started.md",
            "how-to/pixi-tasks.md",
            "reference/developer-guide.md",
            "explanation/the-detector-framework.md",
        )
    ]
    payload: dict = {"schema_version": 1, "pages": pages}
    if sections is not None:
        payload["sections"] = sections
    (docs / "map.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


# --- fixture helpers ---------------------------------------------------------


def _write_page(docs: Path, rel: str, text: str = "# page\n\nbody\n") -> Path:
    path = docs / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_map(docs: Path, *links: str, extra: str = "") -> Path:
    """Write ``docs/MAP.md`` with one ``[x](link)`` row per link."""
    rows = "\n".join(f"| [`{link}`]({link}) | role |" for link in links)
    text = f"# map\n\n| Page | Role |\n|---|---|\n{rows}\n{extra}"
    return _write_page(docs, "MAP.md", text)


def _green_tree(tmp_path: Path) -> Path:
    """A fully mapped four-quadrant tree; returns the ``docs/`` dir."""
    _init_repo(tmp_path)
    docs = tmp_path / "docs"
    pages = (
        "tutorials/getting-started.md",
        "how-to/pixi-tasks.md",
        "reference/developer-guide.md",
        "explanation/the-detector-framework.md",
    )
    for rel in pages:
        _write_page(docs, rel)
    _write_map(docs, *pages)
    _write_map_yaml(docs, sections=[])
    outside = (
        "## Outside this map (untouched)\n\n"
        "| Layer | Paths | Why excluded |\n"
        "|-------|-------|--------------|\n"
        "| Docs | `docs/` | Diátaxis shelf |\n"
    )
    (docs / "MAP.md").write_text((docs / "MAP.md").read_text(encoding="utf-8") + outside, encoding="utf-8")
    _commit_all(tmp_path, "seed")
    return docs


def _only(findings: tuple) -> object:
    assert len(findings) == 1, [f.message for f in findings]
    return findings[0]


# --- tests -------------------------------------------------------------------


def test_all_green_emits_one_ok_with_mapped_count(tmp_path: Path):
    _green_tree(tmp_path)

    finding = _only(docs_map_hygiene.gather(tmp_path))
    assert finding.source == Source.DOCS_MAP_HYGIENE
    assert finding.check == _CHECK
    assert finding.status == DoctorStatus.OK
    assert finding.evidence["mapped_count"] == 4
    assert finding.evidence["page_count"] == 4
    assert finding.evidence["sections_count"] == 0
    assert finding.evidence["unnamed_top_level"] == []


def test_unmapped_quadrant_page_emits_one_fail_naming_it(tmp_path: Path):
    docs = _green_tree(tmp_path)
    _write_page(docs, "how-to/detect-concurrent-agent-activity.md")
    _write_page(docs, "reference/sync-jira-github-workflow-templates/README.md")

    finding = _only(docs_map_hygiene.gather(tmp_path))
    assert finding.status == DoctorStatus.FAIL
    assert finding.evidence["class"] == "unmapped"
    # Sorted; a deeper README.md is NOT exempt -- only quadrant-level ones.
    assert finding.evidence["paths"] == [
        "how-to/detect-concurrent-agent-activity.md",
        "reference/sync-jira-github-workflow-templates/README.md",
    ]
    assert "2 quadrant page(s)" in finding.message


def test_map_link_to_missing_page_emits_one_fail(tmp_path: Path):
    docs = _green_tree(tmp_path)
    _write_map(
        docs,
        "tutorials/getting-started.md",
        "how-to/pixi-tasks.md",
        "reference/developer-guide.md",
        "explanation/the-detector-framework.md",
        "how-to/does-not-exist.md",
        "governance/also-gone.md",
    )

    finding = _only(docs_map_hygiene.gather(tmp_path))
    assert finding.status == DoctorStatus.FAIL
    assert finding.evidence["class"] == "missing"
    # Any docs/-relative link is checked, not only quadrant ones.
    assert finding.evidence["paths"] == [
        "governance/also-gone.md",
        "how-to/does-not-exist.md",
    ]


def test_missing_and_unmapped_together_emit_one_finding_per_class(tmp_path: Path):
    docs = _green_tree(tmp_path)
    _write_page(docs, "explanation/orphan.md")
    _write_map(docs, "tutorials/getting-started.md", "how-to/gone.md")

    findings = docs_map_hygiene.gather(tmp_path)
    assert [f.status for f in findings] == [DoctorStatus.FAIL, DoctorStatus.FAIL]
    assert findings[0].evidence == {"class": "missing", "paths": ["how-to/gone.md"]}
    assert findings[1].evidence["class"] == "unmapped"
    assert "explanation/orphan.md" in findings[1].evidence["paths"]


def test_quadrant_readme_index_pages_are_exempt(tmp_path: Path):
    docs = _green_tree(tmp_path)
    for quadrant in ("tutorials", "how-to", "reference", "explanation"):
        _write_page(docs, f"{quadrant}/README.md", "# index\n")

    finding = _only(docs_map_hygiene.gather(tmp_path))
    assert finding.status == DoctorStatus.OK
    assert finding.evidence["page_count"] == 4


def test_outside_the_map_layers_are_ignored(tmp_path: Path):
    docs = _green_tree(tmp_path)
    # Every layer MAP.md § "Outside this map" excludes, plus the map's own
    # siblings at docs/ root -- none of these may surface as `unmapped`.
    for rel in (
        "governance/policy.md",
        "intake/README.md",
        "dreams/pyforge-doctor.md",
        "specs/legacy.md",
        "dashboard/README.md",
        "foundry/frames/x.md",
        "README.md",
    ):
        _write_page(docs, rel)
    (tmp_path / "src" / "platform").mkdir(parents=True)
    (tmp_path / "src" / "platform" / "README.md").write_text("# p\n", encoding="utf-8")
    (tmp_path / "src" / "shared" / "packages" / "pyforge-doctor").mkdir(parents=True)
    (tmp_path / "src" / "shared" / "packages" / "pyforge-doctor" / "README.md").write_text(
        "# station\n", encoding="utf-8"
    )

    finding = _only(docs_map_hygiene.gather(tmp_path))
    assert finding.status == DoctorStatus.OK


def test_links_escaping_docs_are_ignored(tmp_path: Path):
    docs = _green_tree(tmp_path)
    _write_map(
        docs,
        "tutorials/getting-started.md",
        "how-to/pixi-tasks.md",
        "reference/developer-guide.md",
        "explanation/the-detector-framework.md",
        "../README.md",
        "../archive/docs/specs/gone.md",
        "../../outside-the-repo.md",
        extra="\n[Diátaxis](https://diataxis.fr/) [ext md](https://example.org/x.md)\n",
    )

    finding = _only(docs_map_hygiene.gather(tmp_path))
    assert finding.status == DoctorStatus.OK
    # Only the four in-docs links count toward mapped_count.
    assert finding.evidence["mapped_count"] == 4


def test_map_link_with_fragment_resolves_to_the_page(tmp_path: Path):
    docs = _green_tree(tmp_path)
    (docs / "MAP.md").write_text(
        "[a](tutorials/getting-started.md#setup) [b](how-to/pixi-tasks.md)\n"
        "[c](reference/developer-guide.md) [d](explanation/the-detector-framework.md)\n",
        encoding="utf-8",
    )

    finding = _only(docs_map_hygiene.gather(tmp_path))
    assert finding.status == DoctorStatus.OK


def test_missing_map_is_fail(tmp_path: Path):
    (tmp_path / "docs" / "how-to").mkdir(parents=True)
    _write_page(tmp_path / "docs", "how-to/orphan.md")

    finding = _only(docs_map_hygiene.gather(tmp_path))
    assert finding.status == DoctorStatus.FAIL
    assert finding.message == "docs/MAP.md is missing"
    assert finding.evidence == {"path": "docs/MAP.md"}


def test_quadrant_dirs_may_be_absent(tmp_path: Path):
    _init_repo(tmp_path)
    docs = tmp_path / "docs"
    _write_page(docs, "how-to/only.md")
    _write_map(docs, "how-to/only.md")
    _write_map_yaml(docs, sections=[])
    _commit_all(tmp_path, "seed")

    finding = _only(docs_map_hygiene.gather(tmp_path))
    assert finding.status == DoctorStatus.OK
    assert finding.evidence["page_count"] == 1


def test_gather_degrades_to_warn_on_exception(tmp_path: Path, monkeypatch):
    _green_tree(tmp_path)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("synthetic")

    monkeypatch.setattr(docs_map_hygiene, "_quadrant_pages", _boom)

    finding = _only(docs_map_hygiene.gather(tmp_path))
    assert finding.status == DoctorStatus.WARN
    assert finding.check == _CHECK
    assert "synthetic" in finding.message


# --- Story 48.1: sections + unnamed-top-level --------------------------------


def _fixture_tree_with_map_sections(tmp_path: Path, map_data: dict) -> None:
    _init_repo(tmp_path)
    docs = tmp_path / "docs"
    _write_page(docs, "how-to/pixi-tasks.md")
    _write_map(docs, "how-to/pixi-tasks.md")
    (docs / "map.yaml").write_text(yaml.safe_dump(map_data, sort_keys=False), encoding="utf-8")
    _commit_all(tmp_path, "map")


def test_sections_mint_rows_emit_no_warnings(tmp_path: Path):
    _fixture_tree_with_map_sections(
        tmp_path,
        {"schema_version": 1, "pages": [], "sections": _MINT_SECTIONS},
    )
    findings = docs_map_hygiene.gather(tmp_path)
    section_warns = [f for f in findings if f.evidence.get("class") == "sections"]
    assert section_warns == []


def test_sections_duplicate_key_warns_once(tmp_path: Path):
    sections = [
        {"key": "herald", "label": "A", "href": "herald/", "owner": "herald", "order": 10},
        {"key": "herald", "label": "B", "href": "herald/", "owner": "herald", "order": 20},
    ]
    _fixture_tree_with_map_sections(tmp_path, {"schema_version": 1, "pages": [], "sections": sections})
    warns = [f for f in docs_map_hygiene.gather(tmp_path) if f.evidence.get("class") == "sections"]
    assert len(warns) == 1
    assert "duplicate key" in warns[0].message
    assert warns[0].status == DoctorStatus.WARN


def test_sections_duplicate_order_warns_naming_both_keys(tmp_path: Path):
    sections = [
        {"key": "herald", "label": "A", "href": "herald/", "owner": "herald", "order": 10},
        {"key": "pipelines", "label": "B", "href": "dashboard/kedro-viz/", "owner": "atlas", "order": 10},
    ]
    _fixture_tree_with_map_sections(tmp_path, {"schema_version": 1, "pages": [], "sections": sections})
    warns = [f for f in docs_map_hygiene.gather(tmp_path) if f.evidence.get("defect") == "duplicate-order"]
    assert len(warns) == 1
    assert set(warns[0].evidence["keys"]) == {"herald", "pipelines"}


@pytest.mark.parametrize(
    ("href", "snippet"),
    [
        ("/herald/", "leading slash"),
        ("http://example/herald/", "absolute URL"),
        ("../dashboard/kedro-viz/", "parent segment"),
        ("herald", "missing trailing slash"),
    ],
)
def test_sections_href_defects_warn(tmp_path: Path, href: str, snippet: str):
    sections = [{"key": "herald", "label": "H", "href": href, "owner": "herald", "order": 10}]
    _fixture_tree_with_map_sections(tmp_path, {"schema_version": 1, "pages": [], "sections": sections})
    warns = [f for f in docs_map_hygiene.gather(tmp_path) if f.evidence.get("section_key") == "herald"]
    assert any(snippet in w.message for w in warns)
    assert all(w.status == DoctorStatus.WARN for w in warns)


def test_sections_entry_href_defect_names_section_and_entry(tmp_path: Path):
    sections = [
        {
            "key": "herald",
            "label": "H",
            "href": "herald/",
            "owner": "herald",
            "order": 10,
            "entries": [{"key": "dash", "label": "D", "href": "../dashboard/kedro-viz/"}],
        }
    ]
    _fixture_tree_with_map_sections(tmp_path, {"schema_version": 1, "pages": [], "sections": sections})
    warns = [f for f in docs_map_hygiene.gather(tmp_path) if f.evidence.get("entry_key") == "dash"]
    assert len(warns) == 1
    assert "herald" in warns[0].message and "dash" in warns[0].message


def test_map_yaml_invalid_yields_one_sections_warn(tmp_path: Path):
    _init_repo(tmp_path)
    docs = tmp_path / "docs"
    _write_page(docs, "how-to/pixi-tasks.md")
    _write_map(docs, "how-to/pixi-tasks.md")
    (docs / "map.yaml").write_text("schema_version: 1\nsections:\n  - key: BAD\n", encoding="utf-8")
    _commit_all(tmp_path, "bad map")

    finding = _only(docs_map_hygiene.gather(tmp_path))
    assert finding.status == DoctorStatus.WARN
    assert finding.evidence["class"] == "sections"


def _unnamed_fixture_tree(tmp_path: Path, *, map_extra: str = "") -> None:
    _init_repo(tmp_path)
    docs = tmp_path / "docs"
    _write_page(docs, "how-to/pixi-tasks.md")
    map_body = (
        "# map\n\n## Outside this map (untouched)\n\n"
        "| Layer | Paths | Why excluded |\n"
        "|-------|-------|--------------|\n"
        f"| Docs | `docs/` | root |\n{map_extra}"
    )
    _write_page(docs, "MAP.md", map_body + "\n| Page | Role |\n|---|---|\n| [`how-to/pixi-tasks.md`](how-to/pixi-tasks.md) | x |\n")
    _write_map_yaml(docs, sections=[])
    (tmp_path / "docsite" / "x.html").parent.mkdir(parents=True)
    (tmp_path / "docsite" / "x.html").write_text("x\n", encoding="utf-8")
    (tmp_path / "widgets" / "x.md").parent.mkdir(parents=True)
    (tmp_path / "widgets" / "x.md").write_text("# w\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    _commit_all(tmp_path, "tree")


def test_unnamed_top_level_warns_on_widgets_not_in_map(tmp_path: Path):
    _unnamed_fixture_tree(tmp_path, map_extra="| Site | `docsite/` | built |\n")
    warns = [f for f in docs_map_hygiene.gather(tmp_path) if f.evidence.get("class") == "unnamed-top-level"]
    assert len(warns) == 1
    assert warns[0].evidence["directory"] == "widgets"


def test_unnamed_top_level_quiet_when_map_names_directory(tmp_path: Path):
    _unnamed_fixture_tree(
        tmp_path,
        map_extra="| Site | `docsite/` | built |\n| Widgets | `widgets/` | test |\n",
    )
    warns = [f for f in docs_map_hygiene.gather(tmp_path) if f.evidence.get("class") == "unnamed-top-level"]
    assert warns == []


def test_unnamed_top_level_allow_list_clears_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _unnamed_fixture_tree(tmp_path, map_extra="| Site | `docsite/` | built |\n")
    allow = docs_map_hygiene._INFRASTRUCTURE_DIRS | {"widgets"}
    monkeypatch.setattr(docs_map_hygiene, "_INFRASTRUCTURE_DIRS", frozenset(allow))
    warns = [f for f in docs_map_hygiene.gather(tmp_path) if f.evidence.get("class") == "unnamed-top-level"]
    assert warns == []


def test_unnamed_top_level_ignores_dot_directories(tmp_path: Path):
    _unnamed_fixture_tree(tmp_path)
    warns = [f for f in docs_map_hygiene.gather(tmp_path) if f.evidence.get("directory") == ".github"]
    assert warns == []


def test_unnamed_top_level_git_failure_warns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _green_tree(tmp_path)

    def _fail(_target: Path):
        return None, "git unavailable"

    monkeypatch.setattr(docs_map_hygiene, "_tracked_top_level_dirs", _fail)

    finding = _only(docs_map_hygiene.gather(tmp_path))
    assert finding.status == DoctorStatus.WARN
    assert finding.evidence["class"] == "unnamed-top-level"


def test_sections_finding_never_emits_fail(tmp_path: Path):
    sections = [{"key": "herald", "label": "H", "href": "/bad/", "owner": "herald", "order": 10}]
    _fixture_tree_with_map_sections(tmp_path, {"schema_version": 1, "pages": [], "sections": sections})
    for finding in docs_map_hygiene.gather(tmp_path):
        if finding.evidence.get("class") == "sections":
            assert finding.status == DoctorStatus.WARN


def test_unnamed_top_level_never_emits_fail(tmp_path: Path):
    _unnamed_fixture_tree(tmp_path)
    for finding in docs_map_hygiene.gather(tmp_path):
        if finding.evidence.get("class") == "unnamed-top-level":
            assert finding.status == DoctorStatus.WARN


def test_dot_directory_never_unnamed_top_level(tmp_path: Path):
    _unnamed_fixture_tree(tmp_path)
    findings = docs_map_hygiene.gather(tmp_path)
    assert not any(f.evidence.get("directory", "").startswith(".") for f in findings)


def test_duplicate_order_mutation_fails_test_if_passed(tmp_path: Path):
    """AC9: duplicate order must WARN, not pass silently."""
    sections = [
        {"key": "a", "label": "A", "href": "a/", "owner": "herald", "order": 1},
        {"key": "b", "label": "B", "href": "b/", "owner": "herald", "order": 1},
    ]
    _fixture_tree_with_map_sections(tmp_path, {"schema_version": 1, "pages": [], "sections": sections})
    warns = [f for f in docs_map_hygiene.gather(tmp_path) if f.evidence.get("defect") == "duplicate-order"]
    assert warns, "duplicate order must surface a sections WARN"


def test_href_without_trailing_slash_mutation_fails_test_if_passed(tmp_path: Path):
    sections = [{"key": "herald", "label": "H", "href": "herald", "owner": "herald", "order": 10}]
    _fixture_tree_with_map_sections(tmp_path, {"schema_version": 1, "pages": [], "sections": sections})
    warns = [f for f in docs_map_hygiene.gather(tmp_path) if "trailing slash" in f.message]
    assert warns


# --- load_map_yaml schema (AC1) ----------------------------------------------


def test_load_map_yaml_accepts_mint_sections_and_empty(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    base = {"schema_version": 1, "pages": []}
    for sections in (_MINT_SECTIONS, [], None):
        payload = dict(base)
        if sections is not None:
            payload["sections"] = sections
        (docs / "map.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        docs_currency.load_map_yaml(tmp_path)


def test_load_map_yaml_refuses_malformed_section(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    bad_cases = [
        {"schema_version": 1, "pages": [], "sections": [{"label": "x", "href": "x/", "owner": "h", "order": 1}]},
        {"schema_version": 1, "pages": [], "sections": [{"key": "x", "label": "x", "href": "x/", "owner": "h", "order": "1"}]},
        {"schema_version": 1, "pages": [], "sections": [{"key": "Bad", "label": "x", "href": "x/", "owner": "h", "order": 1}]},
        {
            "schema_version": 1,
            "pages": [],
            "sections": [{"key": "x", "label": "x", "href": "x/", "owner": "h", "order": 1, "extra": 1}],
        },
        {
            "schema_version": 1,
            "pages": [],
            "sections": [
                {
                    "key": "x",
                    "label": "x",
                    "href": "x/",
                    "owner": "h",
                    "order": 1,
                    "entries": [{"key": "e", "label": "E", "href": "x/", "bogus": True}],
                }
            ],
        },
    ]
    for payload in bad_cases:
        (docs / "map.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        with pytest.raises(jsonschema.ValidationError):
            docs_currency.load_map_yaml(tmp_path)
