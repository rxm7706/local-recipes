"""Story 15.1, CAP-1: template-parse-then-fill produces a genuinely
editable deck.

Covers the story spec's I/O & Edge-Case Matrix directly:
``extract_spec``/``fill_template`` validation, the ``run_spec``/``run_fill``
file-path wrappers, the CLI's ``pptx-spec``/``pptx-fill`` subcommands, and
the flagship round-trip proof (real ``<a:t>`` runs, no ``<p:pic>``, and an
independent ``soffice --headless --convert-to pptx`` round-trip) using 3
real slides transcribed from
``presentations/pyforge-herald/src/marp/pyforge-herald-deck-2026-07-24.md``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from pptx import Presentation

from pyforge.herald import cli, errors, pptx_pipeline

# === shared fixtures/helpers =================================================


@pytest.fixture(scope="module")
def template_path() -> Path:
    return pptx_pipeline.default_template_path()


def _write_content_plan(tmp_path: Path, plan: dict) -> Path:
    path = tmp_path / "content_plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    return path


def _slide_xml(pptx_path: Path, slide_number: int) -> str:
    with zipfile.ZipFile(pptx_path) as archive:
        return archive.read(f"ppt/slides/slide{slide_number}.xml").decode("utf-8")


class _FakePlaceholderFormat:
    """Stand-in for python-pptx's ``PlaceholderFormat`` -- just the two
    attributes ``extract_spec``/``_resolve_placeholder_values`` read."""

    def __init__(self, idx: int, type_: object) -> None:
        self.idx = idx
        self.type = type_


class _FakePlaceholder:
    """Stand-in for a python-pptx layout placeholder shape, minimal enough
    to drive ``extract_spec``'s geometry/type fallbacks and
    ``_resolve_placeholder_values``'s ``has_text_frame`` guard without a
    real ``.pptx`` -- neither branch is reachable via the bundled default
    template (every one of its placeholders has an explicit type, explicit
    geometry, and ``has_text_frame=True``)."""

    def __init__(
        self,
        idx: int,
        type_: object = None,
        name: str = "Fake Placeholder",
        has_text_frame: bool = True,
        left: int | None = None,
        top: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        self.placeholder_format = _FakePlaceholderFormat(idx, type_)
        self.name = name
        self.has_text_frame = has_text_frame
        self.left = left
        self.top = top
        self.width = width
        self.height = height


class _FakeLayout:
    """Stand-in for a python-pptx ``SlideLayout``: just ``name`` +
    ``placeholders``, the two attributes ``extract_spec``/
    ``_resolve_layout``/``_resolve_placeholder_values`` read."""

    def __init__(self, name: str, placeholders: list[_FakePlaceholder]) -> None:
        self.name = name
        self.placeholders = placeholders


class _FakePresentation:
    """Stand-in for python-pptx's ``Presentation``: just ``slide_layouts``,
    swapped in for ``_open_template``'s real return value via monkeypatch
    so ``extract_spec``/``fill_template`` run their real logic against a
    fake in-memory template."""

    def __init__(self, layouts: list[_FakeLayout]) -> None:
        self.slide_layouts = layouts


# The 3 real slides (cover, "Invisible engineering is failed engineering",
# "The Design-Code bridge -- realized" bullets), transcribed verbatim (minus
# markdown ** bold markers) from
# presentations/pyforge-herald/src/marp/pyforge-herald-deck-2026-07-24.md.
_THREE_REAL_SLIDES_PLAN = {
    "slides": [
        {
            "layout": 0,  # Title Slide
            "placeholders": {
                "0": "capture the dream. proclaim the release.",
                "1": (
                    "Herald is the visual media and communications engine "
                    "of the Dream-to-Code factory — the first to touch the "
                    "Dream and the last voice in the pipeline. Its first "
                    "organ, the Design↔Code bridge, is already real."
                ),
            },
        },
        {
            "layout": 1,  # Title and Content
            "placeholders": {
                "0": "Invisible engineering is failed engineering",
                "1": (
                    "Herald rejects dry, unreadable raw logs — pipeline "
                    "telemetry becomes scannable, visually striking "
                    "dashboards and briefings that reflect the original "
                    "vision."
                ),
            },
        },
        {
            "layout": 1,  # Title and Content
            "placeholders": {
                "0": "The Design–Code bridge — realized",
                "1": [
                    "seed a Design project from the repo — Modernist-bound, "
                    "runtime included",
                    "design visually in Claude Design",
                    "pull the prototype back — extract → build → export, "
                    "zero downloads",
                    "etags catch conflicts; the loop is specced as the "
                    "herald CLI (5 CAPs)",
                ],
            },
        },
    ]
}


# === extract_spec / spec_to_dict =============================================


def test_emu_normalizes_none_to_zero():
    assert pptx_pipeline._emu(None) == 0


def test_emu_passes_through_an_explicit_value():
    assert pptx_pipeline._emu(12345) == 12345


def test_extract_spec_unset_placeholder_type_falls_back_to_unknown(monkeypatch):
    """python-pptx returns ``None`` for ``placeholder_format.type`` only
    when a ``<p:ph>`` element carries no ``type`` attribute at all --
    unreachable via the bundled default template (every one of its
    placeholders has an explicit type), so this pins the ``"UNKNOWN"``
    fallback with a constructed fake layout instead."""
    fake_prs = _FakePresentation(
        [_FakeLayout("Fake Layout", [_FakePlaceholder(idx=0, type_=None)])]
    )
    monkeypatch.setattr(pptx_pipeline, "_open_template", lambda path: fake_prs)

    spec = pptx_pipeline.extract_spec(Path("unused-template.pptx"))

    assert spec.layouts[0].placeholders[0].type == "UNKNOWN"


def test_extract_spec_matches_python_pptx_for_every_layout(template_path: Path):
    spec = pptx_pipeline.extract_spec(template_path)
    prs = Presentation(str(template_path))

    assert len(spec.layouts) == len(prs.slide_layouts)
    for layout_spec, layout in zip(spec.layouts, prs.slide_layouts, strict=True):
        assert layout_spec.name == layout.name
        # `LayoutPlaceholders.__getitem__` is positional (list index), NOT
        # keyed by the placeholder's own `idx` attribute -- unlike
        # `SlidePlaceholders.__getitem__`, which fill_template relies on.
        # Build our own idx-keyed map here rather than indexing by idx.
        by_idx = {ph.placeholder_format.idx: ph for ph in layout.placeholders}
        actual_idxs = {p.idx for p in layout_spec.placeholders}
        assert actual_idxs == set(by_idx)
        for ph_spec in layout_spec.placeholders:
            ph = by_idx[ph_spec.idx]
            assert ph_spec.type == ph.placeholder_format.type.name
            assert ph_spec.name == ph.name
            assert ph_spec.left == ph.left
            assert ph_spec.top == ph.top
            assert ph_spec.width == ph.width
            assert ph_spec.height == ph.height


def test_extract_spec_raises_pptx_template_error_when_template_missing(tmp_path: Path):
    with pytest.raises(errors.PptxTemplateError):
        pptx_pipeline.extract_spec(tmp_path / "does-not-exist.pptx")


def test_extract_spec_raises_pptx_template_error_on_unopenable_file(tmp_path: Path):
    bad = tmp_path / "not-a-pptx.pptx"
    bad.write_text("not a zip file at all", encoding="utf-8")
    with pytest.raises(errors.PptxTemplateError):
        pptx_pipeline.extract_spec(bad)


def test_spec_to_dict_round_trips_as_json(template_path: Path):
    spec = pptx_pipeline.extract_spec(template_path)
    parsed = json.loads(json.dumps(pptx_pipeline.spec_to_dict(spec)))
    assert len(parsed["layouts"]) == len(spec.layouts)


# === fill_template validation =================================================


def test_fill_template_unknown_layout_index_raises(template_path: Path):
    plan = {"slides": [{"layout": 999, "placeholders": {}}]}
    with pytest.raises(errors.InvalidContentPlanError):
        pptx_pipeline.fill_template(template_path, plan)


def test_fill_template_unknown_layout_name_raises(template_path: Path):
    plan = {"slides": [{"layout": "Not A Real Layout", "placeholders": {}}]}
    with pytest.raises(errors.InvalidContentPlanError):
        pptx_pipeline.fill_template(template_path, plan)


def test_fill_template_unknown_placeholder_idx_raises(template_path: Path):
    plan = {"slides": [{"layout": 0, "placeholders": {"99": "no such placeholder"}}]}
    with pytest.raises(errors.InvalidContentPlanError):
        pptx_pipeline.fill_template(template_path, plan)


@pytest.mark.parametrize(
    "value", [123, None, {"nested": "dict"}, [], [1, 2], ["ok", 3]]
)
def test_fill_template_malformed_placeholder_value_raises(template_path: Path, value):
    plan = {"slides": [{"layout": 0, "placeholders": {"0": value}}]}
    with pytest.raises(errors.InvalidContentPlanError):
        pptx_pipeline.fill_template(template_path, plan)


def test_fill_template_non_text_placeholder_raises_invalid_content_plan_error(
    monkeypatch,
):
    """A placeholder whose ``has_text_frame`` is ``False`` must raise
    ``InvalidContentPlanError`` cleanly during validation, not crash
    ``_set_placeholder_text`` with an unhandled exception -- validation
    happens before any slide is added (I/O matrix's "No file written"
    invariant). Unreachable via the bundled default template as generated
    by python-pptx 1.0.2: even its "Picture with Caption" layout's idx-1
    ``PICTURE`` placeholder reports ``has_text_frame=True`` while unfilled
    (an empty picture placeholder is backed by a plain ``<p:sp>`` element,
    identical in kind to a text placeholder, until an image is actually
    inserted via ``insert_picture()``) -- so this pins the guard with a
    constructed fake layout whose placeholder genuinely cannot hold text."""
    fake_prs = _FakePresentation(
        [
            _FakeLayout(
                "Fake Picture Layout",
                [_FakePlaceholder(idx=1, type_="PICTURE", has_text_frame=False)],
            )
        ]
    )
    monkeypatch.setattr(pptx_pipeline, "_open_template", lambda path: fake_prs)

    plan = {"slides": [{"layout": 0, "placeholders": {"1": "a caption"}}]}
    with pytest.raises(errors.InvalidContentPlanError):
        pptx_pipeline.fill_template(Path("unused-template.pptx"), plan)


def test_fill_template_bool_layout_ref_raises(template_path: Path):
    """``bool`` is an ``int`` subclass in Python -- ``true``/``false`` must
    still be rejected as a layout reference, not silently treated as 1/0."""
    plan = {"slides": [{"layout": True, "placeholders": {}}]}
    with pytest.raises(errors.InvalidContentPlanError):
        pptx_pipeline.fill_template(template_path, plan)


def test_fill_template_missing_layout_key_raises(template_path: Path):
    plan = {"slides": [{"placeholders": {}}]}
    with pytest.raises(errors.InvalidContentPlanError):
        pptx_pipeline.fill_template(template_path, plan)


def test_fill_template_non_dict_content_plan_raises(template_path: Path):
    with pytest.raises(errors.InvalidContentPlanError):
        pptx_pipeline.fill_template(template_path, ["not", "a", "dict"])


def test_fill_template_missing_slides_key_raises(template_path: Path):
    with pytest.raises(errors.InvalidContentPlanError):
        pptx_pipeline.fill_template(template_path, {})


def test_fill_template_produces_one_slide_per_entry_with_real_text(
    template_path: Path,
):
    plan = {
        "slides": [
            {"layout": 0, "placeholders": {"0": "Title A", "1": "Subtitle A"}},
            {
                "layout": 1,
                "placeholders": {"0": "Title B", "1": ["line one", "line two"]},
            },
        ]
    }
    prs = pptx_pipeline.fill_template(template_path, plan)
    assert len(prs.slides) == 2
    slide0, slide1 = prs.slides
    assert slide0.placeholders[0].text_frame.text == "Title A"
    assert slide0.placeholders[1].text_frame.text == "Subtitle A"
    assert slide1.placeholders[0].text_frame.text == "Title B"
    assert slide1.placeholders[1].text_frame.text == "line one\nline two"


# === run_spec / run_fill (file-path orchestration) ===========================


def test_run_spec_returns_spec_and_optionally_writes_json(
    template_path: Path, tmp_path: Path
):
    spec = pptx_pipeline.run_spec(template_path)
    assert len(spec.layouts) == 11

    out_path = tmp_path / "spec.json"
    spec_written = pptx_pipeline.run_spec(template_path, out_path=out_path)
    assert out_path.is_file()
    assert json.loads(out_path.read_text(encoding="utf-8")) == pptx_pipeline.spec_to_dict(
        spec_written
    )


def test_run_fill_missing_template_raises_and_writes_no_output(tmp_path: Path):
    plan_path = _write_content_plan(tmp_path, {"slides": []})
    out_path = tmp_path / "out.pptx"
    with pytest.raises(errors.PptxTemplateError):
        pptx_pipeline.run_fill(tmp_path / "no-such-template.pptx", plan_path, out_path)
    assert not out_path.exists()


def test_run_fill_unreadable_content_plan_path_raises(
    template_path: Path, tmp_path: Path
):
    out_path = tmp_path / "out.pptx"
    with pytest.raises(errors.InvalidContentPlanError):
        pptx_pipeline.run_fill(template_path, tmp_path / "no-such-plan.json", out_path)
    assert not out_path.exists()


def test_run_fill_malformed_json_content_plan_raises(
    template_path: Path, tmp_path: Path
):
    plan_path = tmp_path / "content_plan.json"
    plan_path.write_text("{not valid json", encoding="utf-8")
    out_path = tmp_path / "out.pptx"
    with pytest.raises(errors.InvalidContentPlanError):
        pptx_pipeline.run_fill(template_path, plan_path, out_path)
    assert not out_path.exists()


def test_run_fill_invalid_utf8_content_plan_raises_and_writes_no_output(
    template_path: Path, tmp_path: Path
):
    """``UnicodeDecodeError`` is a ``ValueError`` subclass, not an
    ``OSError`` subclass -- a non-UTF-8 content plan must still raise the
    module's own ``InvalidContentPlanError``, not the raw stdlib
    exception."""
    plan_path = tmp_path / "content_plan.json"
    plan_path.write_bytes(b"\xff\xfe not valid utf-8")
    out_path = tmp_path / "out.pptx"
    with pytest.raises(errors.InvalidContentPlanError):
        pptx_pipeline.run_fill(template_path, plan_path, out_path)
    assert not out_path.exists()


def test_run_fill_unknown_placeholder_idx_writes_no_output_file(
    template_path: Path, tmp_path: Path
):
    plan_path = _write_content_plan(
        tmp_path, {"slides": [{"layout": 0, "placeholders": {"99": "nope"}}]}
    )
    out_path = tmp_path / "out.pptx"
    with pytest.raises(errors.InvalidContentPlanError):
        pptx_pipeline.run_fill(template_path, plan_path, out_path)
    assert not out_path.exists()


def test_run_fill_writes_a_real_pptx_file(template_path: Path, tmp_path: Path):
    plan_path = _write_content_plan(
        tmp_path, {"slides": [{"layout": 0, "placeholders": {"0": "Hi", "1": "There"}}]}
    )
    out_path = tmp_path / "out.pptx"
    pptx_pipeline.run_fill(template_path, plan_path, out_path)
    assert out_path.is_file()
    prs = Presentation(str(out_path))
    assert len(prs.slides) == 1


# === CLI wiring ================================================================


def test_deck_pptx_spec_help_exits_zero():
    assert cli.main(["deck", "pptx-spec", "--help"]) == 0


def test_deck_pptx_fill_help_exits_zero():
    assert cli.main(["deck", "pptx-fill", "--help"]) == 0


def test_deck_pptx_spec_prints_json_to_stdout_by_default(capsys):
    exit_code = cli.main(["deck", "pptx-spec"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["layouts"]) == 11


def test_deck_pptx_spec_writes_to_out_path(tmp_path: Path, capsys):
    out_path = tmp_path / "spec.json"
    exit_code = cli.main(["deck", "pptx-spec", "-o", str(out_path)])
    assert exit_code == 0
    assert out_path.is_file()
    assert "wrote" in capsys.readouterr().out


def test_deck_pptx_spec_missing_template_exits_1(tmp_path: Path, capsys):
    exit_code = cli.main(["deck", "pptx-spec", "--template", str(tmp_path / "nope.pptx")])
    assert exit_code == 1
    assert "PptxTemplateError" in capsys.readouterr().err


def test_deck_pptx_fill_writes_pptx(tmp_path: Path, capsys):
    plan_path = _write_content_plan(
        tmp_path, {"slides": [{"layout": 0, "placeholders": {"0": "Hi", "1": "There"}}]}
    )
    out_path = tmp_path / "out.pptx"
    exit_code = cli.main(["deck", "pptx-fill", str(plan_path), "-o", str(out_path)])
    assert exit_code == 0
    assert out_path.is_file()
    assert "wrote" in capsys.readouterr().out


def test_deck_pptx_fill_unknown_placeholder_idx_exits_1_and_writes_nothing(
    tmp_path: Path, capsys
):
    plan_path = _write_content_plan(
        tmp_path, {"slides": [{"layout": 0, "placeholders": {"99": "nope"}}]}
    )
    out_path = tmp_path / "out.pptx"
    exit_code = cli.main(["deck", "pptx-fill", str(plan_path), "-o", str(out_path)])
    assert exit_code == 1
    assert not out_path.exists()
    assert "InvalidContentPlanError" in capsys.readouterr().err


def test_deck_pptx_subcommands_never_construct_an_mcp_transport(
    monkeypatch, tmp_path: Path
):
    """Mirrors ``test_cli_deck_qa.py``'s regression: these subcommands are
    fully local/offline and must never reach Claude Design."""

    class _ExplodingTransport:
        def __init__(self, *args, **kwargs):
            raise AssertionError(
                "pptx-spec/pptx-fill must never construct McpTransport"
            )

    monkeypatch.setattr(cli, "McpTransport", _ExplodingTransport)

    assert cli.main(["deck", "pptx-spec"]) == 0

    plan_path = _write_content_plan(
        tmp_path, {"slides": [{"layout": 0, "placeholders": {"0": "Hi"}}]}
    )
    out_path = tmp_path / "out.pptx"
    assert cli.main(["deck", "pptx-fill", str(plan_path), "-o", str(out_path)]) == 0


# === the flagship round-trip proof ============================================


def test_round_trip_three_real_slides_produce_genuinely_editable_text(
    template_path: Path, tmp_path: Path
):
    """Given the bundled default template and a content_plan.json built
    from 3 real slides transcribed from
    presentations/pyforge-herald/src/marp/pyforge-herald-deck-2026-07-24.md
    (cover, "Invisible engineering is failed engineering", "The
    Design-Code bridge -- realized" bullets), when run_fill is invoked,
    the output .pptx contains those exact strings as real <a:t> text runs
    (no <p:pic> covering the filled placeholders) AND the same text
    survives an independent `soffice --headless --convert-to pptx`
    round-trip."""
    plan_path = _write_content_plan(tmp_path, _THREE_REAL_SLIDES_PLAN)
    out_path = tmp_path / "herald-deck.pptx"

    pptx_pipeline.run_fill(template_path, plan_path, out_path)

    expected_strings = [
        "capture the dream. proclaim the release.",
        "Invisible engineering is failed engineering",
        "The Design–Code bridge — realized",
        "seed a Design project from the repo",
        "design visually in Claude Design",
        "pull the prototype back",
        "etags catch conflicts",
    ]

    # (1) direct OOXML proof: real <a:t> runs, no <p:pic> anywhere in any
    # of the 3 slides (Design Notes' "Round-trip proven" test proxy, step 1
    # -- catches the exact old Marp-pipeline defect directly).
    full_xml = ""
    for slide_number in (1, 2, 3):
        xml = _slide_xml(out_path, slide_number)
        assert "<p:pic" not in xml
        assert "<a:t>" in xml
        full_xml += xml
    for text in expected_strings:
        assert text in full_xml

    # (2) an independent, third-party OOXML-consuming application must
    # genuinely interpret and re-emit the same text (Design Notes, step 2,
    # the "surface-anchored" proof) -- skipped gracefully (not a story
    # failure) only if soffice is unexpectedly absent from the test
    # environment.
    soffice = shutil.which("soffice")
    if soffice is None:
        pytest.skip(
            "soffice not found on PATH -- skipping the independent "
            "round-trip proof (Design Notes: not this story's failure)"
        )

    round_trip_dir = tmp_path / "round-trip"
    round_trip_dir.mkdir()
    result = subprocess.run(
        [
            soffice,
            "--headless",
            "--convert-to",
            "pptx",
            "--outdir",
            str(round_trip_dir),
            str(out_path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr

    round_tripped_path = round_trip_dir / out_path.name
    assert round_tripped_path.is_file()
    round_tripped_prs = Presentation(str(round_tripped_path))
    round_tripped_text = "\n".join(
        shape.text_frame.text
        for slide in round_tripped_prs.slides
        for shape in slide.shapes
        if shape.has_text_frame
    )
    for text in expected_strings:
        assert text in round_tripped_text
