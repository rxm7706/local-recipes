"""The dossier's A→B control plane is checkable (herald Story 26.1, fnd:CAP-14).

`docs-site/src/content/dossier/dossier.yml` states where the cutover stands. Its Verified
section (§ 10) lists only what the case list, the capability ledger and CI
prove, so every claim row carries a `source` that resolves to one of them:
a `docs/foundry/capability-ledger.yaml` id, a case-list id, or a GitHub
Actions run URL. The Estate section never calls `local-recipes` archived or
read-only, and no claim reads the cutover as flipped or B as a mirror of A.

Story 55.1 (spec-pyforge-herald CAP-64): the dossier states the present. Its sections are the A→B cutover, the
shared spine, the eight stations and § 10, and nothing else; each station section follows one outline; no block's
text tells of an earlier read of the source; no running text types a line-count-sized figure; and each station stats
band shows the stories its ledger holds open and blocked.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

# Story 52.1 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

REPO = Path(__file__).resolve().parents[6]
DOSSIER = REPO / "docs-site" / "src" / "content" / "dossier" / "dossier.yml"
LEDGER = REPO / "docs" / "foundry" / "capability-ledger.yaml"
CASE_LIST = (
    REPO
    / "_bmad-output"
    / "projects"
    / "pyforge-steward"
    / "planning-artifacts"
    / "specs"
    / "spec-foundry-regenerate-not-fold"
    / "case-list.md"
)
CI_RUN = re.compile(r"^https://github\.com/rxm7706/[\w.-]+/actions/runs/\d+$")
CASE_ROW = re.compile(r"^\|\s*(k-[a-z0-9-]+)\s*\|", re.MULTILINE)
NEGATED = re.compile(r"\b(never|not|no|nothing|none|until|without)\b", re.IGNORECASE)
SENTENCE_END = re.compile(r"(?<=[.;:])\s+")


def _dossier() -> dict[str, Any]:
    return yaml.safe_load(DOSSIER.read_text(encoding="utf-8"))


def _section(doc: dict[str, Any], section_id: str) -> dict[str, Any]:
    matches = [s for s in doc["sections"] if s.get("id") == section_id]
    assert len(matches) == 1, f"dossier has {len(matches)} sections with id {section_id!r}"
    return matches[0]


def _claim_rows(section: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for block in section["blocks"] if block["type"] == "table" for row in block["rows"]]


def _ledger_ids() -> set[str]:
    ledger = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    return {row["id"] for row in ledger["capabilities"]}


def _case_ids() -> set[str]:
    return set(CASE_ROW.findall(CASE_LIST.read_text(encoding="utf-8")))


def _source_problems(rows: list[dict[str, Any]], ledger_ids: set[str], case_ids: set[str]) -> list[str]:
    problems = []
    for index, row in enumerate(rows):
        claim = str(row.get("cells", ["?"])[0])[:60]
        source = str(row.get("source") or "").strip()
        if not source:
            problems.append(f"row {index} ({claim!r}) has no source")
        elif not (source in ledger_ids or source in case_ids or CI_RUN.match(source)):
            problems.append(
                f"row {index} ({claim!r}) cites {source!r}, which is not a capability-ledger id, "
                "a case-list id or a CI run URL"
            )
    return problems


def _texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [t for v in value.values() for t in _texts(v)]
    if isinstance(value, list):
        return [t for v in value for t in _texts(v)]
    return []


def _affirmations(texts: list[str], term: str, context: str | None = None) -> list[str]:
    """Sentences that use `term` (and `context`, when given) without negating it."""
    term_re = re.compile(term, re.IGNORECASE)
    context_re = re.compile(context, re.IGNORECASE) if context else None
    found = []
    for text in texts:
        for sentence in SENTENCE_END.split(" ".join(text.split())):
            if not term_re.search(sentence):
                continue
            if context_re and not context_re.search(sentence):
                continue
            if not NEGATED.search(sentence):
                found.append(sentence)
    return found


def _control_plane_texts(doc: dict[str, Any]) -> list[str]:
    return (
        _texts(doc.get("eyebrow"))
        + _texts(doc.get("summary"))
        + _texts(_section(doc, "estate"))
        + _texts(_section(doc, "verified"))
    )


def test_verified_section_lists_claims() -> None:
    assert _claim_rows(_section(_dossier(), "verified")), "§ 10 has no claim rows"


def test_every_verified_claim_names_resolvable_evidence() -> None:
    rows = _claim_rows(_section(_dossier(), "verified"))
    assert _source_problems(rows, _ledger_ids(), _case_ids()) == []


def test_a_verified_claim_without_a_source_reds() -> None:
    rows = copy.deepcopy(_claim_rows(_section(_dossier(), "verified")))
    rows.append({"cells": ["B already serves the platform.", "—"]})
    problems = _source_problems(rows, _ledger_ids(), _case_ids())
    assert len(problems) == 1
    assert "B already serves the platform" in problems[0]
    assert "no source" in problems[0]


def test_a_source_that_resolves_nowhere_reds() -> None:
    rows = [{"cells": ["claim", "evidence"], "source": "fcl:CAP-999999"}]
    assert _source_problems(rows, _ledger_ids(), _case_ids())


def test_verified_positive_claims_are_rows_not_callouts() -> None:
    """A green callout in § 10 would be a positive claim without a source."""
    blocks = _section(_dossier(), "verified")["blocks"]
    assert [b for b in blocks if b["type"] == "callout" and b.get("tone") == "green"] == []


def test_estate_never_calls_local_recipes_archived_or_read_only() -> None:
    texts = _texts(_section(_dossier(), "estate"))
    assert _affirmations(texts, r"\b(archived|read-only)\b") == []


def test_no_claim_reads_the_cutover_as_flipped_or_b_as_a_mirror_of_a() -> None:
    texts = _control_plane_texts(_dossier())
    assert _affirmations(texts, r"\bflipped\b") == []
    assert _affirmations(texts, r"\bmirror(s|ed|ing)?\b") == []


def test_affirmative_archive_and_flip_claims_red() -> None:
    planted = ["`local-recipes` is archived.", "The cutover has flipped to B.", "B mirrors A."]
    assert _affirmations(planted, r"\b(archived|read-only)\b") == ["`local-recipes` is archived."]
    assert _affirmations(planted, r"\bflipped\b") == ["The cutover has flipped to B."]
    assert _affirmations(planted, r"\bmirror(s|ed|ing)?\b") == ["B mirrors A."]
    assert _affirmations(["It is never archived."], r"\b(archived|read-only)\b") == []


# ------------------------------------------------------------------ Story 55.1 (CAP-64): the dossier states the present

STATION_IDS = ["atlas", "doctor", "herald", "marshal", "mason", "scribe", "steward", "warden"]
SECTION_IDS = ["estate", "foundation", *STATION_IDS, "verified"]
OUTLINE = ["Commands", "MCP face", "State", "Relationships", "Held by tests"]
#: the closed list of phrases that tell of an earlier read of the source (CAP-64 success)
EARLIER_READ = re.compile(
    r"\b(last pass|earlier pass(es)?|previous pass|prior pass|first pass|second pass|third pass|since the last|up from)\b",
    re.IGNORECASE,
)
#: the block types that are running text, where a comma-grouped figure is a typed count
RUNNING_TEXT = ("lede", "prose", "note", "finding", "callout", "quote", "relations", "verify", "engines")
TYPED_FIGURE = re.compile(r"(?<![\w.])\d{1,3},\d{3}\b")


def _section_id_problems(doc: dict[str, Any]) -> list[str]:
    ids = [str(s.get("id")) for s in doc["sections"]]
    return [] if ids == SECTION_IDS else [f"the dossier's sections are {ids}, not {SECTION_IDS}"]


def _earlier_read_problems(doc: dict[str, Any]) -> list[str]:
    problems = []
    for section in doc["sections"]:
        for block in section.get("blocks", []):
            for text in _texts(block):
                for match in EARLIER_READ.finditer(text):
                    problems.append(f"section {section['id']!r}, a {block['type']} block: {match.group(0)!r}")
    return problems


def _typed_figure_problems(doc: dict[str, Any]) -> list[str]:
    problems = []
    for section in doc["sections"]:
        for block in section.get("blocks", []):
            if block.get("type") in RUNNING_TEXT:
                for text in _texts(block):
                    for match in TYPED_FIGURE.finditer(text):
                        problems.append(f"section {section['id']!r}, a {block['type']} block types {match.group(0)!r}")
    return problems


def _outline_problems(doc: dict[str, Any]) -> list[str]:
    problems = []
    for section in doc["sections"]:
        if section.get("kind") != "station":
            continue
        headings = [str(b.get("text")) for b in section.get("blocks", []) if b.get("type") == "h3"]
        if headings != OUTLINE:
            problems.append(f"station section {section['id']!r} has the headings {headings}, not {OUTLINE}")
    return problems


def _stories_open_problems(doc: dict[str, Any]) -> list[str]:
    problems = []
    for section in doc["sections"]:
        if section.get("kind") != "station":
            continue
        checks = [s.get("check") for b in section.get("blocks", []) if b.get("type") == "stats" for s in b["stats"]]
        if "stories_open" not in checks:
            problems.append(f"station section {section['id']!r} has no stat with check: stories_open")
    return problems


def test_55_1_the_sections_are_the_cutover_the_spine_the_eight_stations_and_what_is_verified() -> None:
    assert _section_id_problems(_dossier()) == []
    assert [s["id"] for s in _dossier()["sections"] if s.get("kind") == "station"] == STATION_IDS


def test_55_1_no_block_tells_of_an_earlier_read_of_the_source() -> None:
    assert _earlier_read_problems(_dossier()) == []


def test_55_1_no_running_text_types_a_comma_grouped_figure() -> None:
    assert _typed_figure_problems(_dossier()) == []


def test_55_1_every_station_section_follows_the_one_outline() -> None:
    assert _outline_problems(_dossier()) == []


def test_55_1_every_station_stats_band_shows_stories_open() -> None:
    assert _stories_open_problems(_dossier()) == []


def _planted(section_id: str, block: dict[str, Any]) -> dict[str, Any]:
    doc = copy.deepcopy(_dossier())
    _section(doc, section_id)["blocks"].append(block)
    return doc


def test_55_1_planted_a_cross_fleet_section_is_named() -> None:
    doc = copy.deepcopy(_dossier())
    doc["sections"].insert(-1, {"id": "synthesis", "kind": "section", "measured": "2026-11-26", "blocks": []})
    assert len(_section_id_problems(doc)) == 1
    assert "synthesis" in _section_id_problems(doc)[0]


@pytest.mark.parametrize(
    "phrase",
    [
        "What arrived since the last pass",
        "The earlier passes found a README that contradicted itself.",
        "the second pass settled it",
        "twelve named surfaces, up from six",
        "A previous pass described a bridge.",
    ],
)
def test_55_1_planted_an_earlier_read_is_named(phrase: str) -> None:
    problems = _earlier_read_problems(_planted("scribe", {"type": "prose", "body": [phrase]}))
    assert len(problems) == 1 and "'scribe'" in problems[0], problems


def test_55_1_planted_a_typed_figure_in_running_text_is_named_and_a_version_range_is_not() -> None:
    planted = _planted("marshal", {"type": "prose", "body": ["Marshal is 115,025 lines across its files."]})
    assert _typed_figure_problems(planted) == ["section 'marshal', a prose block types '115,025'"]
    ranged = _planted("marshal", {"type": "relations", "items": [{"glyph": "→", "md": "declared `>=0.11.0,<0.13`"}]})
    assert _typed_figure_problems(ranged) == []


def test_55_1_planted_a_station_heading_outside_the_outline_is_named() -> None:
    planted = _planted("atlas", {"type": "h3", "num": "A.6", "text": "What arrived"})
    problems = _outline_problems(planted)
    assert len(problems) == 1 and "'atlas'" in problems[0] and "What arrived" in problems[0], problems


def test_55_1_planted_a_station_band_without_stories_open_is_named() -> None:
    doc = copy.deepcopy(_dossier())
    band = next(b for b in _section(doc, "warden")["blocks"] if b["type"] == "stats")
    band["stats"] = [s for s in band["stats"] if s.get("check") != "stories_open"]
    assert _stories_open_problems(doc) == ["station section 'warden' has no stat with check: stories_open"]
