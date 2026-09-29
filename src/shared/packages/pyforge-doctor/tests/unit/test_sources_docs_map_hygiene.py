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

from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import docs_map_hygiene

_CHECK = "docs-map-hygiene"


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
    docs = tmp_path / "docs"
    _write_page(docs, "how-to/only.md")
    _write_map(docs, "how-to/only.md")

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
