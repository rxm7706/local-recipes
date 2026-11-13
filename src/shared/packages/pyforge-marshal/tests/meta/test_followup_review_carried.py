"""Meta-test: every ``done`` tracked story spec with ``followup_review_recommended: true`` is carried
in its own project's deferred-work ledger (Story 66.2, spec-pyforge-marshal CAP-275)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.marshal.core.deferred_work import followup_review_orphans

# Story 116.2 (spec-pyforge-marshal:CAP-305): this module reads the repository outside this package, so it runs in
# the live-tree half; it finds the repository root when a test runs, never at import, so the module imports off
# the tree (the package half collects it before the marker deselects it).
pytestmark = pytest.mark.live_tree


def _repo_root() -> Path:
    # tests/meta -> tests -> pyforge-marshal -> packages -> shared -> src -> repo root
    return Path(__file__).resolve().parents[6]


_STATIONS = (
    "pyforge-atlas",
    "pyforge-doctor",
    "pyforge-herald",
    "pyforge-marshal",
    "pyforge-mason",
    "pyforge-scribe",
    "pyforge-steward",
    "pyforge-warden",
)


def list_followup_review_orphans(repo_root: Path | None = None) -> list[tuple[str, str]]:
    """Every (project slug, spec basename) that is ``done``+flagged and not carried."""
    if repo_root is None:
        repo_root = _repo_root()
    orphans: list[tuple[str, str]] = []
    for slug in _STATIONS:
        planning = repo_root / "_bmad-output" / "projects" / slug / "planning-artifacts"
        ledger_path = planning / "deferred-work-ledger.md"
        ledger_text = ledger_path.read_text(encoding="utf-8") if ledger_path.is_file() else ""
        specs_dir = planning / "specs"
        if not specs_dir.is_dir():
            continue
        for spec_path in sorted(specs_dir.glob("spec-*.md")):
            text = spec_path.read_text(encoding="utf-8")
            if followup_review_orphans(
                spec_basename=spec_path.name,
                spec_text=text,
                ledger_text=ledger_text,
            ):
                orphans.append((slug, spec_path.name))
    return orphans


def test_no_done_and_flagged_spec_is_uncarried_across_the_eight_projects():
    orphans = list_followup_review_orphans()
    assert orphans == [], f"uncarried follow-up recommendations: {orphans!r}"


def test_followup_review_orphans_predicate_on_a_fixture_tree(tmp_path: Path) -> None:
    slug = "pyforge-demo"
    specs = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts" / "specs"
    specs.mkdir(parents=True)
    ledger = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts" / "deferred-work-ledger.md"
    spec_name = "spec-1-1-demo.md"
    spec_text = "---\nstatus: done\nfollowup_review_recommended: true\n---\n"
    (specs / spec_name).write_text(spec_text, encoding="utf-8")
    ledger.write_text("# Ledger\n", encoding="utf-8")

    assert followup_review_orphans(spec_basename=spec_name, spec_text=spec_text, ledger_text=ledger.read_text())

    ledger.write_text(
        "# Ledger\n\n### DW-FRR-1-1: x\n\n- source_spec: `" + spec_name + "`\n  origin: dispatch-followup-review\n",
        encoding="utf-8",
    )
    assert not followup_review_orphans(spec_basename=spec_name, spec_text=spec_text, ledger_text=ledger.read_text())

    ledger.write_text(
        "# Ledger\n\n### DW-FU-1-1: x\n\n- source_spec: `" + spec_name + "`\n  origin: review-budget-followup\n",
        encoding="utf-8",
    )
    assert not followup_review_orphans(spec_basename=spec_name, spec_text=spec_text, ledger_text=ledger.read_text())

    ledger.write_text(
        "# Ledger\n\n### DW-X-1: x\n\n- source_spec: `" + spec_name + "`\n  origin: spec-deferred\n",
        encoding="utf-8",
    )
    assert followup_review_orphans(spec_basename=spec_name, spec_text=spec_text, ledger_text=ledger.read_text())
