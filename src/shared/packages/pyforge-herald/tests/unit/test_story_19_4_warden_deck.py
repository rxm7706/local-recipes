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

from pyforge.herald import cli, pptx_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[6]
_WARDEN_SRC = _REPO_ROOT / "presentations" / "pyforge-warden" / "src"
_CONTENT_PLAN = _WARDEN_SRC / "content_plan.json"
_PIPELINE_PPTX = _WARDEN_SRC / "pptx" / "pyforge-warden-deck-2026-09-10.pptx"
_MARP_PPTX = _WARDEN_SRC / "pptx" / "pyforge-warden-deck-2026-07-15.pptx"


def _slide_xml(pptx_path: Path, slide_number: int) -> str:
    with zipfile.ZipFile(pptx_path) as archive:
        return archive.read(f"ppt/slides/slide{slide_number}.xml").decode("utf-8")


def test_warden_content_plan_exists_and_parses():
    assert _CONTENT_PLAN.is_file()
    plan = json.loads(_CONTENT_PLAN.read_text(encoding="utf-8"))
    assert isinstance(plan.get("slides"), list)
    assert len(plan["slides"]) >= 6


def test_committed_pipeline_pptx_has_editable_text_runs_not_marp_images():
    """I/O matrix: content_plan filled -> real editable text runs."""
    assert _PIPELINE_PPTX.is_file()
    full_xml = ""
    for slide_number in range(1, 16):
        xml = _slide_xml(_PIPELINE_PPTX, slide_number)
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


def test_dense_slide_exercises_shape_api():
    """I/O matrix: dense slide via add_card / add_metric_box / add_table /
    add_section_label."""
    dense_xml = _slide_xml(_PIPELINE_PPTX, 9)
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


def test_pipeline_output_is_not_marp_export_provenance():
    """I/O matrix: provenance — the committed file is pipeline output from
    ``content_plan.json`` (15 slides, shape API on slide 9), not the dated
    Marp export (28 slides, no ``content_plan.json`` source)."""
    assert _MARP_PPTX.is_file()
    assert _PIPELINE_PPTX.stat().st_size < _MARP_PPTX.stat().st_size // 5
    with zipfile.ZipFile(_MARP_PPTX) as marp:
        marp_slides = [n for n in marp.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
    with zipfile.ZipFile(_PIPELINE_PPTX) as pipeline:
        pipeline_slides = [n for n in pipeline.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
    assert len(pipeline_slides) == 15
    assert len(marp_slides) == 28
    assert "Six axes of dependency trust" in _slide_xml(_PIPELINE_PPTX, 9)
    assert "Six axes of dependency trust" not in _slide_xml(_MARP_PPTX, 9)


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


def test_run_fill_uses_bundled_interim_template():
    """I/O matrix: template choice — default bundled template, no custom .potx."""
    template_path = pptx_pipeline.default_template_path()
    assert template_path.is_file()
    out_path = _WARDEN_SRC / "pptx" / ".story-19-4-regen-check.pptx"
    try:
        pptx_pipeline.run_fill(template_path, _CONTENT_PLAN, out_path)
        assert out_path.is_file()
    finally:
        out_path.unlink(missing_ok=True)
