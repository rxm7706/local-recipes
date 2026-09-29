"""Story 53.4 — Guard library without a second verdict (hub:CAP-4)."""

from __future__ import annotations

from pathlib import Path

from pyforge.steward.cli import DUTIES, build_parser, resolve_duty
from pyforge.steward.guards import (
    FIRST_LIBRARY_CATEGORY,
    LIBRARY,
    PAPER_CATEGORIES,
    VERDICT,
    GuardsDuty,
    catalog,
    library_gaps,
    parse_hub_guards,
    source_ground,
    spec_gaps,
)

_REPO = Path(__file__).resolve().parents[6]
_DETECTORS = _REPO / "scripts" / "detectors.py"
_PIXI = _REPO / "pixi.toml"


def test_paper_seven_are_named() -> None:
    assert PAPER_CATEGORIES == (
        "algorithmic",
        "consensus",
        "expert",
        "policy_and_safety",
        "regression_and_drift",
        "source_grounding",
        "outcome",
    )
    assert set(LIBRARY) == set(PAPER_CATEGORIES)


def test_source_grounding_is_first_library_addition() -> None:
    assert FIRST_LIBRARY_CATEGORY == "source_grounding"
    assert LIBRARY["source_grounding"].in_library is True
    present = [name for name in PAPER_CATEGORIES if LIBRARY[name].in_library]
    assert present[-1] == "source_grounding"


def test_outcome_is_the_library_gap() -> None:
    assert library_gaps() == ("outcome",)
    assert LIBRARY["outcome"].in_library is False
    assert LIBRARY["outcome"].blocked_on == "docs/dreams/build-league-scorecard.md"


def test_every_row_refuses_a_second_verdict() -> None:
    for row in catalog():
        assert row["verdict"] == VERDICT == "never"


def test_spec_can_name_what_it_lacks() -> None:
    declared = frozenset(
        {
            "algorithmic",
            "consensus",
            "expert",
            "policy_and_safety",
            "regression_and_drift",
            "source_grounding",
        }
    )
    assert spec_gaps(declared) == ("outcome",)


def test_parse_hub_guards_from_spec_text() -> None:
    text = "---\nhub_guards:\n  - algorithmic\n  - source_grounding\n---\n# SPEC\n"
    assert parse_hub_guards(text) == frozenset({"algorithmic", "source_grounding"})
    assert spec_gaps(parse_hub_guards(text) or frozenset()) == (
        "consensus",
        "expert",
        "policy_and_safety",
        "regression_and_drift",
        "outcome",
    )


def test_source_ground_requires_resolvable_citation(tmp_path: Path) -> None:
    cited = tmp_path / "notes.md"
    cited.write_text("fact\n", encoding="utf-8")
    bare = source_ground("The build is green.", tmp_path)
    assert bare.grounded is False
    assert bare.reason == "no [source: path] citation"
    ok = source_ground("The build is green. [source: notes.md]", tmp_path)
    assert ok.grounded is True
    assert ok.citations == ("notes.md",)
    missing = source_ground("Claim. [source: no-such.md]", tmp_path)
    assert missing.grounded is False
    assert missing.reason is not None
    assert "unresolvable" in missing.reason


def test_source_ground_rejects_path_escape(tmp_path: Path) -> None:
    result = source_ground("x [source: ../outside.md]", tmp_path)
    assert result.grounded is False
    assert result.reason is not None
    assert "escapes" in result.reason or "unresolvable" in result.reason


def test_guards_duty_is_registered() -> None:
    assert "guards" in DUTIES
    impl = resolve_duty("guards")
    assert isinstance(impl, GuardsDuty)
    assert impl.name == "guards"


def test_bare_guards_lists_verbs() -> None:
    result = GuardsDuty().run(build_parser().parse_args(["guards"]))
    assert result.ok is True
    assert "catalog" in result.summary
    assert "lacking" in result.summary
    assert "source-ground" in result.summary


def test_lacking_without_spec_is_outcome() -> None:
    result = GuardsDuty().run(build_parser().parse_args(["guards", "lacking"]))
    assert result.ok is True
    assert result.details["lacking"] == ["outcome"]


def test_lacking_reads_spec(tmp_path: Path) -> None:
    spec = tmp_path / "SPEC.md"
    spec.write_text("hub_guards:\n  - algorithmic\n", encoding="utf-8")
    result = GuardsDuty().run(build_parser().parse_args(["guards", "lacking", "--spec", str(spec)]))
    assert result.ok is True
    assert "outcome" in result.details["lacking"]
    assert "source_grounding" in result.details["lacking"]


def test_not_a_detectors_ci_member() -> None:
    pixi = _PIXI.read_text(encoding="utf-8")
    detectors = _DETECTORS.read_text(encoding="utf-8") if _DETECTORS.is_file() else ""
    assert "steward guards" not in pixi
    assert "source-ground" not in detectors
    # detectors-ci lives in feature.guild-tasks since steward 63.1 (moved from
    # feature.local-recipes); a missed anchor made this assertion vacuously true.
    start = pixi.find("[feature.guild-tasks.tasks.detectors-ci]")
    assert start != -1, "detectors-ci task block not found in pixi.toml"
    ci_block = pixi[start : start + 800]
    assert "guards" not in ci_block
