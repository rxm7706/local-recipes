"""Story 25.5 (CAP-5): the 0.11 status-vocabulary pin against the INSTALLED
``bmad_loop`` package -- the drift guard.

Marshal mirrors bmad-loop 0.11.0's status vocabulary verbatim (never invents
field names): the ``"awaiting-operator"`` phase token, the 4-member terminal
set, the per-task ``"preserve_ref"`` key, the run-level ``"sweeps_refused"``
key with its CLOSED ``SWEEP_REFUSED_*`` reason slugs, and
``STATUS_SCHEMA_VERSION == 1``. A future bmad-loop bump that widens or
respells any of these must red THIS test rather than surface as a silently
mislabeled fleet row -- the same precedent Story 25.4's
``test_enum_frozensets_mirror_the_installed_bmad_loop_vocabularies``
establishes for the policy knobs. A direct ``bmad_loop`` import is fine IN A
TEST: AD-3's import-linter contract binds the installed package's modules,
not test code (``test_harness_bmadloop_preflight.py``'s own bounds).
"""

from __future__ import annotations

import pytest

from pyforge.marshal.core import status as status_core


def test_awaiting_operator_phase_token_mirrors_the_installed_package():
    model = pytest.importorskip("bmad_loop.model")
    assert str(model.Phase.AWAITING_OPERATOR) == "awaiting-operator"
    assert status_core._AWAITING_OPERATOR_PHASE == str(model.Phase.AWAITING_OPERATOR)


def test_terminal_set_mirrors_the_installed_terminal_phases_exactly():
    """`_TERMINAL_TASK_PHASES` CLAIMS to mirror `bmad_loop.model.
    TERMINAL_PHASES` exactly ({done, deferred, escalated,
    awaiting-operator}) -- assert set equality against the live installed
    package, so a fifth terminal phase (or a respelling) reds here instead
    of re-opening the 'stuck work reported as running' mislabel."""
    model = pytest.importorskip("bmad_loop.model")
    assert status_core._TERMINAL_TASK_PHASES == frozenset(str(phase) for phase in model.TERMINAL_PHASES)


def test_sweep_refused_reason_slugs_mirror_the_installed_package():
    model = pytest.importorskip("bmad_loop.model")
    assert model.SWEEP_REFUSED_NOT_STARTED == "not-started"
    assert model.SWEEP_REFUSED_FAILED == "failed"
    assert model.SWEEP_REFUSED_DIRTY == "dirty"


def test_status_schema_version_is_pinned_at_1():
    """The spec's own Block If: marshal's reading of `status --json`'s
    per-task `preserve_ref` / run-level `sweeps_refused` keys is only known
    valid against schema version 1 -- a bump means the contract moved and
    this story's mirror must be re-verified."""
    cli = pytest.importorskip("bmad_loop.cli")
    assert cli.STATUS_SCHEMA_VERSION == 1


def test_status_document_carries_the_two_mirrored_keys():
    """The installed writer's own `status_document` carries per-task
    `preserve_ref` and always-present run-level `sweeps_refused` (`{}` when
    clean) -- the exact spellings marshal's snapshot seam reads."""
    model = pytest.importorskip("bmad_loop.model")
    documents = pytest.importorskip("bmad_loop.documents")

    state = model.RunState(run_id="vocab-pin-run", project="acme", started_at="2026-08-22T00:00:00Z")
    state.tasks["25-5-vocab"] = model.StoryTask(
        story_key="25-5-vocab",
        epic=25,
        phase=model.Phase.AWAITING_OPERATOR,
        preserve_ref="attempt-preserve/vocab-pin",
    )
    doc = documents.status_document(state)

    assert doc["schema_version"] == documents.STATUS_SCHEMA_VERSION
    assert doc["sweeps_refused"] == {}
    (task_row,) = doc["tasks"]
    assert task_row["preserve_ref"] == "attempt-preserve/vocab-pin"
    assert task_row["phase"] == "awaiting-operator"


def test_state_json_round_trip_keeps_the_mirrored_keys():
    """`RunState.to_dict` -> `from_dict` (the persistence pair the snapshot
    seam reads through `journal.load_state`) preserves both vocabularies --
    the fixture-writer contract every 25.5 test relies on."""
    model = pytest.importorskip("bmad_loop.model")

    state = model.RunState(run_id="vocab-pin-run", project="acme", started_at="2026-08-22T00:00:00Z")
    state.sweeps_refused["epic-1"] = model.SWEEP_REFUSED_DIRTY
    state.tasks["25-5-vocab"] = model.StoryTask(
        story_key="25-5-vocab",
        epic=25,
        phase=model.Phase.AWAITING_OPERATOR,
        preserve_ref="attempt-preserve/vocab-pin",
    )

    raw = state.to_dict()
    assert raw["sweeps_refused"] == {"epic-1": "dirty"}
    assert raw["tasks"]["25-5-vocab"]["preserve_ref"] == "attempt-preserve/vocab-pin"
    assert raw["tasks"]["25-5-vocab"]["phase"] == "awaiting-operator"

    round_tripped = model.RunState.from_dict(raw)
    assert round_tripped.sweeps_refused == {"epic-1": "dirty"}
    task = round_tripped.tasks["25-5-vocab"]
    assert task.preserve_ref == "attempt-preserve/vocab-pin"
    assert task.phase is model.Phase.AWAITING_OPERATOR
    assert task.terminal is True
