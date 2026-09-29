"""The dossier's A→B control plane is checkable (herald Story 26.1, fnd:CAP-14).

`docsite/content/dossier.yml` states where the cutover stands. Its Verified
section (§ 10) lists only what the case list, the capability ledger and CI
prove, so every claim row carries a `source` that resolves to one of them:
a `docs/foundry/capability-ledger.yaml` id, a case-list id, or a GitHub
Actions run URL. The Estate section never calls `local-recipes` archived or
read-only, and no claim reads the cutover as flipped or B as a mirror of A.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[6]
DOSSIER = REPO / "docsite" / "content" / "dossier.yml"
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
