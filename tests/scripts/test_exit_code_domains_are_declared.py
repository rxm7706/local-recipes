"""Every exit-code domain matches its declaration (steward Story 137.1, spec-pyforge-steward:CAP-184;
DW-VOCAB-2026-09-14-8).

The estate projects exit codes through five domains, and **`2` means opposite things in two of
them**: a doctor source exits `2` for FAIL, while `scripts/detectors.py` exits `2` for could-not-run.
That inversion is not theoretical -- on 2026-09-14 a real FAIL from `chain-completeness` was read as
"the check couldn't run", because `CLAUDE.md` documented only the aggregator's domain while telling
the reader to run individual doctor sources.

Since 2026-11-25 the domains are declared once, by member name and number, in
`docs/governance/guild-roster.json`'s `exit_code_domains`; `pyforge.core.exit_domains` carries the
same table for in-process code, and each verdict module takes its numbers from it. This file holds
every surface to the declaration -- the modules (each where its package is installed), the
aggregator's source, and the human-facing table in `docs/reference/judgement-vocabulary.md` -- so a
number changed in one place without the declaration fails here instead of silently re-opening the
same misread.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GLOSSARY = REPO / "docs" / "reference" / "judgement-vocabulary.md"
ROSTER = REPO / "docs" / "governance" / "guild-roster.json"


def _roster() -> dict:
    return json.loads(ROSTER.read_text(encoding="utf-8"))


def _declared() -> dict[str, dict[str, int]]:
    return _roster()["exit_code_domains"]


def _codes(domain: str) -> set[int]:
    return set(_declared()[domain].values())


def test_the_declaration_and_the_glossary_exist():
    """Every assertion below reads these two files. Moving either means moving this test too."""
    assert ROSTER.is_file() and GLOSSARY.is_file()
    assert set(_declared()) == {"doctor", "warden", "marshal", "marshal-seed", "detectors"}


def test_the_core_mirror_is_the_declaration():
    core = pytest.importorskip("pyforge.core.exit_domains")
    assert {name: dict(members) for name, members in core.EXIT_CODE_DOMAINS.items()} == _declared()
    assert dict(core.EXIT_CODE_DOMAINS_NARROWING) == _roster()["exit_code_domains_narrowing"]


def test_doctor_projects_fail_to_2_and_never_uses_1():
    """`{0, 2, 130}` -- and `warn` must stay exit 0, or every advisory finding starts reddening CI."""
    doctor = pytest.importorskip("pyforge.doctor.verdict")
    declared = _declared()["doctor"]
    assert doctor.EXIT_SIGINT == declared["interrupted"] == 130
    assert doctor._EXIT_OK == declared["ok"] == 0
    assert doctor._EXIT_FAIL == declared["fail"] == 2, "doctor's FAIL must project to 2, not 1"
    by_member = doctor.LATTICE.exit_by_member
    assert set(by_member.values()) | {doctor.EXIT_SIGINT} == _codes("doctor")
    assert 1 not in _codes("doctor"), "doctor's domain omits warden's policy rung 1"
    warn = next(m for m in by_member if m.value == "warn")
    assert by_member[warn] == 0, "a warn finding must never change the exit code"


def test_warden_keeps_1_for_policy_and_2_for_error():
    """`{0, 1, 2, 130}` -- the domain doctor's is a subset of."""
    # Skips wherever warden is not installed, including `pyforge-ci` and `pyforge-guild`, the two envs CI runs
    # this file in; warden's own `meta/test_verdict_reads_the_exit_declaration.py` holds it in `-e pyforge-warden`.
    warden = pytest.importorskip("pyforge.warden.verdict")
    assert {status.value: code for status, code in warden._EXIT_BY_STATUS.items()} == {
        name: code for name, code in _declared()["warden"].items() if name not in ("warn-as-error", "interrupted")
    }
    assert set(warden.LATTICE.exit_codes) | {warden.EXIT_SIGINT} == _codes("warden")


def test_marshal_and_seed_match_their_domains():
    verdict = pytest.importorskip("pyforge.marshal.core.verdict")
    errors = pytest.importorskip("pyforge.marshal.seed.errors")
    assert set(verdict.GUARDED_EXIT_CODES) == _codes("marshal")
    assert set(errors.SEED_EXIT_CODES) == _codes("marshal-seed")


def test_doctor_narrows_warden_by_declaration():
    assert _roster()["exit_code_domains_narrowing"] == {"doctor": "warden"}
    assert _codes("doctor") <= _codes("warden")


def test_the_aggregator_reads_its_codes_from_the_declaration():
    """`scripts/detectors.py` is the ONLY surface where `2` means "could not run"; it takes 0, 1 and 2
    from the `detectors` domain rather than spelling them."""
    text = (REPO / "scripts" / "detectors.py").read_text(encoding="utf-8")
    assert 'roster["exit_code_domains"]' in text and 'domains["detectors"]' in text
    assert "exit_code_for(findings) != DOCTOR_EXIT_OK" in text, "a doctor row is compared to doctor's declared ok"
    # Assert the CODE, not its prose: findings return the findings code, an unknown row the
    # could-not-run code, and no bare 0, 1 or 2 is returned.
    assert re.search(r"if\s+registry_findings\s+or\s+any\(.*?FINDINGS.*?\):\s*\n\s*return EXIT_FINDINGS", text, re.S)
    assert re.search(r'if\s+any\(.*?status.*?==\s*"unknown".*?\):\s*\n\s*return EXIT_COULD_NOT_RUN', text, re.S)
    assert not re.search(r"(?m)^\s+return [012]$", text), "the aggregator spells an exit number of its own"
    assert "unknown, never green" in text, (
        "the aggregator's own never-a-false-green rationale is gone; that sentence is why `2` exists here at all"
    )
    assert _declared()["detectors"] == {"pass": 0, "unmeasured": 0, "findings": 1, "could-not-run": 2}


_GLOSSARY_ROWS = {
    "doctor": "a doctor source",
    "detectors": "`scripts/detectors.py`",
    "warden": "`pyforge-warden`",
    "marshal": "`pyforge-marshal`",
    "marshal-seed": "`pyforge-marshal seed`",
}


@pytest.mark.parametrize("domain", sorted(_GLOSSARY_ROWS))
def test_the_glossary_table_shows_each_declared_domain(domain: str):
    """The human-facing table is checked against the declaration, row by row."""
    label = _GLOSSARY_ROWS[domain]
    rows = [
        line
        for line in GLOSSARY.read_text(encoding="utf-8").splitlines()
        if line.startswith("| ") and line.split("|")[1].strip().split(" (")[0] == label
    ]
    assert len(rows) == 1, f"one glossary row for {label}, got {rows}"
    cell = rows[0].split("|")[2].strip().strip("`")
    shown = {int(n) for n in re.findall(r"\d+", cell)}
    assert shown == _codes(domain), f"{label}: the glossary shows {sorted(shown)}, declared {sorted(_codes(domain))}"


def test_the_glossary_records_the_inversion_and_the_declaration():
    """A reader must be able to learn the trap from the docs, not from being bitten by it."""
    text = GLOSSARY.read_text(encoding="utf-8")
    assert "could not run" in text.lower()
    assert re.search(r"\bFAIL\b", text), "the glossary must say a doctor source's 2 is FAIL"
    assert "{0, 2, 130}" in text and "{0, 1, 2, 130}" in text, (
        "the glossary must show doctor's and warden's domains side by side -- "
        "that adjacency is what makes the subset relationship legible"
    )
    assert "exit_code_domains" in text, "the glossary must name the declaration it describes"


def test_the_glossary_warns_against_reading_a_detector_through_a_pipe():
    """`cmd | grep | head` then `$?` reports the pipe's last command, not the detector's -- the second
    half of the same 2026-09-14 misread."""
    text = GLOSSARY.read_text(encoding="utf-8")
    assert "pipe" in text.lower(), "the glossary must carry the never-read-a-detector-through-a-pipe rule"
