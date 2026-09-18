"""The Spec ladder's eight statuses are pinned against
``docs/governance/guild-roster.json`` (steward Story 59.1).

Eight Spec statuses are live in the estate, and until this story only one --
``extension-point`` -- was defined anywhere: in prose, in
``docs/dreams/README.md``. The other seven existed only as hardcoded sets
split across two Doctor modules: ``pyforge.doctor.sources.board``
(``OPEN_SPEC_STATUSES`` / ``DELIVERED_SPEC_STATUSES``, covering ``draft`` /
``ready`` / ``in-progress`` / ``shipped``) and
``pyforge.doctor.sources.one_chain`` (``_CLOSED_SPEC_STATUSES``, covering
``archived`` / ``absorbed`` / ``superseded``), so a reader had to open both
modules' source to learn what ``shipped`` or ``absorbed`` even meant.

This test pins the new declaration's shape so that renaming, dropping, or
re-collapsing a value fails here rather than silently drifting from the
Charter's own prose (``docs/dreams/pyforge-charter.md`` § The Lexicon, "The
Spec ladder -- eight states, three ended acts"). Wiring ``board.py`` /
``chain.py`` / ``one_chain.py`` / ``status_body_consistency.py`` to *consume*
this declaration is Story 59.2 and is out of scope here -- this test only
reads the declaration and the Charter text, nothing that imports
``pyforge.doctor``.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROSTER = REPO / "docs" / "governance" / "guild-roster.json"
CHARTER = REPO / "docs" / "dreams" / "pyforge-charter.md"


def _load_roster() -> dict:
    return json.loads(ROSTER.read_text(encoding="utf-8"))


def test_the_roster_that_declares_the_spec_ladder_exists():
    """Every assertion below reads this file. If it is moved or renamed
    without updating this test, the Spec ladder stops being declared
    anywhere."""
    assert ROSTER.is_file(), (
        f"{ROSTER.relative_to(REPO)} is the declared home of the Spec "
        "ladder (spec_statuses). Moving it means moving this test too."
    )


def test_all_eight_statuses_are_present_in_declared_order():
    """The eight live Spec statuses, in the order the Charter names them."""
    data = _load_roster()
    assert data["spec_statuses"] == [
        "draft",
        "ready",
        "in-progress",
        "shipped",
        "archived",
        "absorbed",
        "superseded",
        "extension-point",
    ]
    # One prose definition per value, plus the ruling paragraphs -- a
    # missing/renamed value fails here rather than reading as merely stale.
    comment = " ".join(data["$comment_spec_statuses"])
    for status in data["spec_statuses"]:
        assert f"`{status}`" in comment, (
            f"$comment_spec_statuses has no definition for `{status}`"
        )


def test_the_three_ended_acts_stay_distinct():
    """`archived`, `absorbed`, and `superseded` all mean the Spec stopped
    without shipping, but they answer different questions -- they must never
    collapse into one value."""
    data = _load_roster()
    ended_acts = data["spec_statuses_ended_acts"]
    assert set(ended_acts) == {"archived", "absorbed", "superseded"}
    assert len(set(ended_acts)) == 3


def test_shipped_is_terminal_but_not_an_ended_act():
    """`shipped` is grouped as Spec-terminal alongside the three ended acts,
    but is explicitly NOT one of them -- it is the one terminal value that
    delivered rather than ended."""
    data = _load_roster()
    ended_acts = set(data["spec_statuses_ended_acts"])
    terminal = set(data["spec_statuses_terminal"])
    assert terminal == ended_acts | {"shipped"}
    assert "shipped" not in ended_acts


def test_in_progress_is_the_sole_grandfathered_status():
    """`in-progress` is grandfathered: no new Spec may be minted at it, and
    it is the only value in that state."""
    data = _load_roster()
    assert tuple(data["spec_statuses_grandfathered"]) == ("in-progress",)


def test_extension_point_is_neither_terminal_nor_an_ended_act():
    """`extension-point` is a standing seam, not a deliverable and not an
    ended act -- it belongs to neither derived group."""
    data = _load_roster()
    assert "extension-point" not in set(data["spec_statuses_terminal"])
    assert "extension-point" not in set(data["spec_statuses_ended_acts"])


def test_the_charter_cites_the_declaration():
    """§ The Lexicon must cite the declaration file and name the key it
    reads, not merely restate its rulings in prose."""
    text = CHARTER.read_text(encoding="utf-8")
    assert "guild-roster.json" in text
    assert "spec_statuses" in text


def test_the_charter_states_all_four_rulings():
    """Each ruling gets its own substring check, tied to that ruling's
    substance rather than incidental wording -- a future edit that strips a
    ruling while leaving the file's other `guild-roster.json`/`spec_statuses`
    mentions intact must still fail here."""
    text = CHARTER.read_text(encoding="utf-8")
    # Ruling 1: the three ended acts stay distinct, never collapsed.
    assert "never collapsed into one value" in text
    # Ruling 2: `shipped` stays Spec-terminal, not an ended act.
    assert "shipped` remains Spec-terminal" in text
    # Ruling 3: `in-progress` is grandfathered.
    assert "`in-progress` is grandfathered" in text
    # Ruling 4: the enum is recommended, not required.
    assert "The enum is recommended, not required." in text
