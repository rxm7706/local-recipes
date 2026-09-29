"""The four exit-code domains are pinned, and `docs/reference/judgement-vocabulary.md`
is what declares them (DW-VOCAB-2026-09-14-8).

The estate projects exit codes through four independent lattices, and **`2` means
opposite things in two of them**: a doctor source exits `2` for FAIL, while
`scripts/detectors.py` exits `2` for could-not-run. That inversion is not
theoretical — on 2026-09-14 a real FAIL from `chain-completeness` was read as
"the check couldn't run", because `CLAUDE.md` documented only the aggregator's
domain while telling the reader to run individual doctor sources.

Unifying the four is a cross-station re-architecture and is not what this test
does. This pins the domains **as documented**, so that changing one without
updating the glossary fails here rather than silently re-opening the same
misread. The glossary is the declaration; this is the check that reads it.

Doctor's subset of warden's domain is deliberate and documented
(`doctor/verdict.py`: it omits warden's policy rung `1` because Doctor reports
operability, not policy). The collision with the aggregator's `2` is not.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GLOSSARY = REPO / "docs" / "reference" / "judgement-vocabulary.md"


def test_the_glossary_that_declares_the_domains_exists():
    """Every assertion below reads this file. If it is moved or renamed without
    updating this test, the domains stop being declared anywhere."""
    assert GLOSSARY.is_file(), (
        f"{GLOSSARY.relative_to(REPO)} is the declared home of the exit-code "
        "domains (DW-VOCAB-2026-09-14-8). Moving it means moving this test too."
    )


def test_doctor_projects_fail_to_2_and_never_uses_1():
    """`{0, 2, 130}` — and `warn` must stay exit 0, or every advisory finding
    starts reddening CI."""
    doctor = pytest.importorskip("pyforge.doctor.verdict")
    assert doctor.EXIT_SIGINT == 130
    assert doctor._EXIT_OK == 0
    assert doctor._EXIT_FAIL == 2, "doctor's FAIL must project to 2, not 1"
    by_member = doctor.LATTICE.exit_by_member
    assert set(by_member.values()) == {0, 2}, (
        "doctor's domain is deliberately a SUBSET of warden's, omitting warden's "
        f"policy rung 1 — got {sorted(set(by_member.values()))}"
    )
    warn = next(m for m in by_member if m.value == "warn")
    assert by_member[warn] == 0, "a warn finding must never change the exit code"


def test_warden_keeps_1_for_policy_and_2_for_error():
    """`{0, 1, 2, 130}` — the domain doctor's is a subset of."""
    # Skips in envs without warden installed (e.g. `local-recipes`); it runs
    # for real in `pyforge-warden`, which is where this contract matters.
    warden = pytest.importorskip("pyforge.warden.verdict")
    codes = set(warden._EXIT_BY_STATUS.values())
    assert codes <= {0, 1, 2}, f"warden's projected codes drifted: {sorted(codes)}"
    assert 1 in codes, (
        "warden's policy rung projects to 1; doctor's docstring justifies its own "
        "omission of 1 by reference to this"
    )


def test_the_aggregator_uses_2_for_could_not_run_not_for_fail():
    """This is the inversion. `scripts/detectors.py` is the ONLY surface where
    `2` means "could not run"; every lattice above means something else by it."""
    text = (REPO / "scripts" / "detectors.py").read_text(encoding="utf-8")
    # Assert the CODE, not its prose: `1` for findings, `2` only for a detector
    # that could not run. Reading the wording instead would pass on a comment
    # while the projection underneath it changed.
    assert re.search(r'if\s+registry_findings\s+or\s+any\(.*?FINDINGS.*?\):\s*\n\s*return 1',
                     text, re.S), "detectors.py no longer returns 1 for findings"
    assert re.search(r'if\s+any\(.*?status.*?==\s*"unknown".*?\):\s*\n\s*return 2',
                     text, re.S), (
        "scripts/detectors.py no longer projects 2 from `unknown`. If the "
        "aggregator's domain changed, the glossary and CLAUDE.md both need "
        "updating — this inversion is what caused a real misread on 2026-09-14."
    )
    assert "unknown, never green" in text, (
        "the aggregator's own never-a-false-green rationale is gone; that "
        "sentence is why `2` exists here at all"
    )


def test_the_glossary_records_the_inversion_explicitly():
    """A reader must be able to learn the trap from the docs, not from being
    bitten by it."""
    text = GLOSSARY.read_text(encoding="utf-8")
    assert "could not run" in text.lower()
    assert re.search(r"\bFAIL\b", text), "the glossary must say a doctor source's 2 is FAIL"
    assert "{0, 2, 130}" in text and "{0, 1, 2, 130}" in text, (
        "the glossary must show doctor's and warden's domains side by side — "
        "that adjacency is what makes the subset relationship legible"
    )


def test_the_glossary_warns_against_reading_a_detector_through_a_pipe():
    """`cmd | grep | head` then `$?` reports the pipe's last command, not the
    detector's — the second half of the same 2026-09-14 misread."""
    text = GLOSSARY.read_text(encoding="utf-8")
    assert "pipe" in text.lower(), (
        "the glossary must carry the never-read-a-detector-through-a-pipe rule"
    )
