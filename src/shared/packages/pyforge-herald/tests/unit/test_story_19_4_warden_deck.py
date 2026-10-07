"""Story 19.4: one real station deck renders through the pptx pipeline.

Exercises the committed ``presentations/pyforge-warden/src/content_plan.json``
against PyForge's bundled interim template and proves the output is pipeline
rendered (real ``<a:t>`` runs, shape API on the dense slide) — not a Marp
image export.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from pyforge.herald import cli, deck_versions, pptx_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[6]
_PRESENTATIONS = _REPO_ROOT / "presentations"
_WARDEN_SRC = _PRESENTATIONS / "pyforge-warden" / "src"
_CONTENT_PLAN = _WARDEN_SRC / "content_plan.json"
_TOPIC = "pyforge-warden"


def _regenerated_pipeline_pptx(tmp_path: Path) -> Path:
    out_path = tmp_path / "pyforge-warden-deck-pipeline.pptx"
    template_path = pptx_pipeline.default_template_path()
    pptx_pipeline.run_fill(template_path, _CONTENT_PLAN, out_path)
    return out_path


def _current_marp_deck_pptx() -> Path:
    path = deck_versions.newest_export(
        _PRESENTATIONS,
        _TOPIC,
        "src/pptx",
        "pyforge-warden-deck",
        ".pptx",
    )
    assert path is not None
    return path


def _slide_xml(pptx_path: Path, slide_number: int) -> str:
    with zipfile.ZipFile(pptx_path) as archive:
        return archive.read(f"ppt/slides/slide{slide_number}.xml").decode("utf-8")


def test_warden_content_plan_exists_and_parses():
    assert _CONTENT_PLAN.is_file()
    plan = json.loads(_CONTENT_PLAN.read_text(encoding="utf-8"))
    assert isinstance(plan.get("slides"), list)
    assert len(plan["slides"]) >= 6


def test_regenerated_pipeline_pptx_has_editable_text_runs_not_marp_images(tmp_path: Path):
    """I/O matrix: content_plan filled -> real editable text runs."""
    pipeline_pptx = _regenerated_pipeline_pptx(tmp_path)
    full_xml = ""
    for slide_number in range(1, 16):
        xml = _slide_xml(pipeline_pptx, slide_number)
        assert "<p:pic" not in xml
        assert "<a:t>" in xml
        full_xml += xml
    for text in (
        "never false-green",
        "ACT I",
        "The green check that lies",
        "ACT VI",
        "A green check should mean it was actually checked.",
    ):
        assert text in full_xml


def test_dense_slide_exercises_shape_api(tmp_path: Path):
    """I/O matrix: dense slide via add_card / add_metric_box / add_table /
    add_section_label."""
    pipeline_pptx = _regenerated_pipeline_pptx(tmp_path)
    dense_xml = _slide_xml(pipeline_pptx, 9)
    for text in (
        "Six axes of dependency trust",
        "Hygiene",
        "deptry",
        "6",
        "axes of dependency trust",
        "Never false-green",
        "indeterminate sits above",
    ):
        assert text in dense_xml


def test_pipeline_output_is_not_marp_export_provenance(tmp_path: Path):
    """I/O matrix: provenance — pipeline output from ``content_plan.json`` (15
    slides, shape API on slide 9), not the dated Marp export (more slides, no
    shape-API text on slide 9)."""
    pipeline_pptx = _regenerated_pipeline_pptx(tmp_path)
    marp_pptx = _current_marp_deck_pptx()
    assert pipeline_pptx.stat().st_size < marp_pptx.stat().st_size // 5
    with zipfile.ZipFile(marp_pptx) as marp:
        marp_slides = [n for n in marp.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
    with zipfile.ZipFile(pipeline_pptx) as pipeline:
        pipeline_slides = [n for n in pipeline.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
    assert len(pipeline_slides) == 15
    assert len(marp_slides) > len(pipeline_slides)
    assert "Six axes of dependency trust" in _slide_xml(pipeline_pptx, 9)
    assert "Six axes of dependency trust" not in _slide_xml(marp_pptx, 9)


def test_cli_pptx_fill_regenerates_warden_deck(tmp_path: Path, capsys):
    """I/O matrix: herald deck pptx-fill against the bundled interim template."""
    out_path = tmp_path / "regenerated.pptx"
    exit_code = cli.main(
        [
            "deck",
            "pptx-fill",
            str(_CONTENT_PLAN),
            "-o",
            str(out_path),
        ]
    )
    assert exit_code == 0
    assert out_path.is_file()
    assert "wrote" in capsys.readouterr().out
    xml = _slide_xml(out_path, 9)
    assert "Never false-green" in xml


def test_run_fill_uses_bundled_interim_template(tmp_path: Path):
    """I/O matrix: template choice — default bundled template, no custom .potx."""
    template_path = pptx_pipeline.default_template_path()
    assert template_path.is_file()
    out_path = tmp_path / "story-19-4-regen-check.pptx"
    pptx_pipeline.run_fill(template_path, _CONTENT_PLAN, out_path)
    assert out_path.is_file()
