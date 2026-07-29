"""Story F2 gate (FR-10, AD-9/AD-20/AD-23) — the data-validation hook.

Wave F's F2 verify gate is ``kedro-test`` (this package is collected there). The gate runs a
tiny REAL Kedro pipeline (``SequentialRunner`` + a real hook manager, so node/dataset hooks
fire in the real order) and asserts the load-bearing F2 behaviours:

- a malformed-payload output **halts execution by raising a native Python exception BEFORE the
  output persists** (FR-10 core) and **emits an A2A alert** carrying the severity + violated
  rule + evidence (AD-20), delivered on E1's real ``a2a`` channel (``hand_off`` →
  ``AuthoringInbox``);
- a valid output passes through untouched and persists (no false halt);
- the hook is **validator-agnostic** — a STUB second validator validates the SAME node with
  ZERO node changes (AC-3);
- the banned ``kedro_great_expectations`` / ``kedro_pandera`` plugins are absent and the GX
  boundary is a version-capped deferred stub (AD-9 — see also
  ``tests/catalog/test_no_inline_io.py``);
- edge cases: no contract → pass-through; a non-frame output skips gracefully; empty frames;
  a broken validator halts (never silently passes); the default no-op sink never crashes;
  multi-output nodes halt before ANY persist; the default hook is deepcopy-safe (the C1
  translator deep-copies ``settings.HOOKS``).
"""

from __future__ import annotations

import copy

import pandas as pd
import pandera.pandas as pa
import pytest
from kedro.framework.hooks.manager import _create_hook_manager, _register_hooks
from kedro.io import DataCatalog, MemoryDataset
from kedro.pipeline import Pipeline, node
from kedro.runner import SequentialRunner
from pandera.pandas import Check, Column, DataFrameSchema

from pyforge.atlas.a2a import AtlasAlert, AuthoringInbox, Severity, hand_off
from pyforge.atlas.observability import AtlasObservabilityHooks
from pyforge.atlas.validation import (
    ContractViolation,
    DataContractViolation,
    DataValidationHooks,
    GreatExpectationsBoundaryValidator,
    PanderaValidator,
    Validator,
)

STAMP = "2026-07-18T00:00:00Z"

# A "PyPI current-versions" contract: name + a NON-EMPTY version string (the AC's
# "PyPI JSON missing a version field" example).
PYPI_SCHEMA = DataFrameSchema(
    {
        "name": Column(str),
        "version": Column(str, Check.str_length(min_value=1)),
    }
)
GOOD = pd.DataFrame({"name": ["numpy", "pandas"], "version": ["1.0", "2.0"]})
MISSING_VERSION = pd.DataFrame({"name": ["numpy"]})  # malformed: no version column


# --------------------------------------------------------------------------- #
# Harness: run a real one-node pipeline with the validation hook registered, and
# track whether the output dataset actually persisted (the pre-persist proof).
# --------------------------------------------------------------------------- #
class _TrackingDataset(MemoryDataset):
    """A MemoryDataset that records every save — so a test can prove the output was
    NOT persisted when validation halted (the pre-persist guarantee)."""

    def __init__(self, saves: list[str], name: str) -> None:
        super().__init__()
        self._saves = saves
        self._name = name

    def save(self, data) -> None:  # type: ignore[override]
        self._saves.append(self._name)
        super().save(data)


def _identity(df: pd.DataFrame) -> pd.DataFrame:
    return df


def _run(hooks: DataValidationHooks, output_value: pd.DataFrame, *, out_name: str = "pypi_current_versions"):
    """Run a real one-node pipeline whose node emits ``output_value`` as ``out_name``.
    Returns (raised_exception_or_None, saved_dataset_names)."""
    saves: list[str] = []
    pipe = Pipeline([node(_identity, inputs="raw_in", outputs=out_name, name="emit")])
    catalog = DataCatalog(
        {
            "raw_in": MemoryDataset(output_value),
            out_name: _TrackingDataset(saves, out_name),
        }
    )
    hm = _create_hook_manager()
    _register_hooks(hm, (hooks,))
    raised: BaseException | None = None
    try:
        SequentialRunner().run(pipe, catalog, hook_manager=hm)
    except BaseException as exc:  # noqa: BLE001 - the gate inspects the raised type
        raised = exc
    return raised, saves


def _capturing_sink() -> tuple[list[AtlasAlert], "callable"]:
    captured: list[AtlasAlert] = []
    return captured, captured.append


# --------------------------------------------------------------------------- #
# AC-1 / AC-2 — malformed payload HALTS via a native raise, BEFORE persist, + alert
# --------------------------------------------------------------------------- #
def test_malformed_payload_halts_via_native_raise_before_persist_and_alerts():
    alerts, sink = _capturing_sink()
    hooks = DataValidationHooks(
        [PanderaValidator({"pypi_current_versions": PYPI_SCHEMA})],
        alert_sink=sink,
        build_stamp=STAMP,
    )
    raised, saves = _run(hooks, MISSING_VERSION)

    # (1) a NATIVE python exception halted the run…
    assert isinstance(raised, DataContractViolation)
    assert isinstance(raised, Exception)  # native — Dagster/kedro treat it as a run failure
    # (2) …BEFORE the bad output persisted (the save loop never ran).
    assert saves == [], "output persisted despite a contract violation — halt was NOT pre-persist"
    # (3) an A2A alert was emitted carrying severity + the violated rule + evidence.
    assert len(alerts) == 1
    alert = alerts[0]
    assert isinstance(alert, AtlasAlert)
    assert alert.severity is Severity.critical
    assert alert.rule == "pandera_schema"
    assert alert.subject == "pypi_current_versions"
    assert alert.build_stamp == STAMP
    assert alert.evidence["dataset"] == "pypi_current_versions"
    assert alert.evidence["validators"] == ["pandera"]
    # the evidence names the violated column ("version") somewhere in the failure cases.
    blob = str(alert.evidence["violations"])
    assert "version" in blob


def test_alert_rides_the_real_a2a_channel_e1():
    """AD-20: the alert is delivered on E1's real A2A channel — hand_off serializes it to a
    genuine a2a Message and the AuthoringInbox decodes it back to the exact AtlasAlert."""
    inbox = AuthoringInbox()
    hooks = DataValidationHooks(
        [PanderaValidator({"pypi_current_versions": PYPI_SCHEMA})],
        alert_sink=lambda alert: hand_off(alert, inbox),
        build_stamp=STAMP,
    )
    raised, saves = _run(hooks, MISSING_VERSION)
    assert isinstance(raised, DataContractViolation)
    assert saves == []
    # the authoring agent received exactly one AtlasAlert over the real channel.
    assert len(inbox.payloads) == 1
    received = inbox.payloads[0]
    assert isinstance(received, AtlasAlert)
    assert received.rule == "pandera_schema"
    assert received.severity is Severity.critical
    # it round-tripped identically to what the hook attached to the raise.
    assert received == raised.alert


# --------------------------------------------------------------------------- #
# Valid payload passes through untouched (no false halt) and persists.
# --------------------------------------------------------------------------- #
def test_valid_payload_passes_and_persists():
    alerts, sink = _capturing_sink()
    hooks = DataValidationHooks(
        [PanderaValidator({"pypi_current_versions": PYPI_SCHEMA})],
        alert_sink=sink,
        build_stamp=STAMP,
    )
    raised, saves = _run(hooks, GOOD)
    assert raised is None
    assert saves == ["pypi_current_versions"]  # persisted normally
    assert alerts == []  # no alert on a clean run


# --------------------------------------------------------------------------- #
# AC-3 — validator-agnostic: a STUB second validator validates the SAME node with
# ZERO node changes.
# --------------------------------------------------------------------------- #
class _StubValidator:
    """A trivial SECOND validator backend (not pandera, not GX): flags any dataset whose frame
    carries a forbidden column. Proves the seam is validator-agnostic — it plugs in with no
    node/hook edits, purely by conforming to the Validator protocol."""

    name = "stub_forbidden_column"

    def __init__(self, forbidden: str) -> None:
        self._forbidden = forbidden

    def check(self, dataset: str, data) -> list[ContractViolation]:
        cols = getattr(data, "columns", [])
        if self._forbidden in list(cols):
            return [
                ContractViolation(
                    dataset,
                    self.name,
                    "forbidden_column",
                    {"forbidden": self._forbidden},
                )
            ]
        return []


def test_validator_agnostic_stub_second_validator_no_node_change():
    # SAME node/pipeline as every other test — the frame is VALID for pandera (name+version)
    # but the stub second validator forbids the "version" column. The identical node validates
    # through a different backend with ZERO node edits.
    alerts, sink = _capturing_sink()
    hooks = DataValidationHooks(
        [
            PanderaValidator({"pypi_current_versions": PYPI_SCHEMA}),  # would PASS this frame
            _StubValidator(forbidden="version"),                       # but the stub flags it
        ],
        alert_sink=sink,
        build_stamp=STAMP,
    )
    raised, saves = _run(hooks, GOOD)
    assert isinstance(raised, DataContractViolation)
    assert saves == []  # halted before persist, via the SECOND backend
    assert len(alerts) == 1
    assert alerts[0].rule == "forbidden_column"
    assert alerts[0].evidence["validators"] == ["stub_forbidden_column"]


class _HostileEvidenceValidator:
    """A backend that returns NON-JSON-native evidence (a set) + an EMPTY rule — the exact
    shapes that would crash build_alert_payload's pydantic validators inside _halt on the
    older code, converting a clean halt into a pydantic error AND dropping the alert."""

    name = "hostile_backend"

    def check(self, dataset: str, data) -> list[ContractViolation]:
        return [ContractViolation(dataset, self.name, "", {"cases": {1, 2, 3}, "score": float("nan")})]


def test_hostile_backend_evidence_still_halts_with_contract_violation_and_alerts():
    """Reviewer finding (both): a third-party backend's non-JSON-native evidence / empty rule
    must NOT crash the halt or drop the A2A alert. _build_alert coerces evidence JSON-native and
    falls back on the rule, so the raised type is always DataContractViolation and the alert
    always fires (AD-20)."""
    alerts, sink = _capturing_sink()
    hooks = DataValidationHooks([_HostileEvidenceValidator()], alert_sink=sink, build_stamp=STAMP)
    raised, saves = _run(hooks, GOOD)
    assert isinstance(raised, DataContractViolation)  # NOT a pydantic ValueError
    assert saves == []                                 # still halted before persist
    assert len(alerts) == 1                            # alert still delivered
    assert alerts[0].rule == "data-contract-violation"  # empty rule → safe fallback
    # the set/NaN were coerced to strings, so the alert round-trips through the a2a channel:
    from pyforge.atlas.a2a import to_message, from_message
    assert from_message(to_message(alerts[0])) == alerts[0]


def test_stub_validator_alone_proves_pandera_is_not_special():
    # No pandera at all — ONLY the stub backend. The same hook + same node halts, showing the
    # hook hardcodes nothing about pandera (AC-3).
    alerts, sink = _capturing_sink()
    hooks = DataValidationHooks([_StubValidator(forbidden="name")], alert_sink=sink, build_stamp=STAMP)
    raised, saves = _run(hooks, GOOD)  # GOOD has a "name" column
    assert isinstance(raised, DataContractViolation)
    assert saves == []
    assert alerts[0].evidence["validators"] == ["stub_forbidden_column"]


def test_backends_conform_to_the_validator_protocol():
    # runtime_checkable protocol: the shipped + boundary + stub backends all satisfy it.
    assert isinstance(PanderaValidator(), Validator)
    assert isinstance(GreatExpectationsBoundaryValidator(), Validator)
    assert isinstance(_StubValidator("x"), Validator)


# --------------------------------------------------------------------------- #
# AD-9 — GX is a version-capped DEFERRED boundary stub (no GX import in shipped path)
# --------------------------------------------------------------------------- #
def test_gx_boundary_is_a_deferred_version_capped_stub():
    gx = GreatExpectationsBoundaryValidator()
    assert gx.name == "great_expectations"
    with pytest.raises(NotImplementedError) as ei:
        gx.check("pypi_current_versions", GOOD)
    msg = str(ei.value)
    assert "1.18.2" in msg and "deferred" in msg.lower()  # honest DW note


def test_shipped_validation_module_imports_no_great_expectations():
    # Belt-and-suspenders alongside tests/catalog/test_no_inline_io.py: the shipped module
    # must not have pulled GX into sys.modules by importing it at module load.
    import pyforge.atlas.validation as val

    src = __import__("inspect").getsource(val)
    assert "import great_expectations" not in src
    assert "from great_expectations" not in src


# --------------------------------------------------------------------------- #
# Edge cases (Reviewer-B surface)
# --------------------------------------------------------------------------- #
def test_no_registered_contract_is_passthrough():
    # a dataset the pandera validator has NO contract for must pass through, not fail.
    alerts, sink = _capturing_sink()
    hooks = DataValidationHooks([PanderaValidator({"some_other_dataset": PYPI_SCHEMA})], alert_sink=sink, build_stamp=STAMP)
    raised, saves = _run(hooks, MISSING_VERSION)  # malformed, but no contract for this name
    assert raised is None
    assert saves == ["pypi_current_versions"]
    assert alerts == []


def test_non_dataframe_output_skips_gracefully():
    # a contract IS registered but the node emits a non-frame → the frame validator skips
    # gracefully (no crash, no false halt).
    out = "not-a-frame"
    saves: list[str] = []
    pipe = Pipeline([node(lambda x: out, inputs="raw_in", outputs="pypi_current_versions", name="emit")])
    catalog = DataCatalog(
        {"raw_in": MemoryDataset("seed"), "pypi_current_versions": _TrackingDataset(saves, "pypi_current_versions")}
    )
    hm = _create_hook_manager()
    _register_hooks(hm, (DataValidationHooks([PanderaValidator({"pypi_current_versions": PYPI_SCHEMA})], build_stamp=STAMP),))
    SequentialRunner().run(pipe, catalog, hook_manager=hm)  # must NOT raise
    assert saves == ["pypi_current_versions"]  # persisted (skipped, not halted)


def test_empty_frame_with_valid_columns_passes():
    # explicit `string[pyarrow]` (not `dtype=str`): pandera dtype-checks an EMPTY column's
    # literal declared dtype (there are no values to infer a type from), and `Column(str)`
    # always expects `string[pyarrow]` there, independent of pyforge.atlas's
    # `future.infer_string` pin (__init__.py, AUD-ATLAS-011). NOTE: this is a narrow fix for
    # THIS test's empty frame, not a general answer -- `DEFAULT_CONTRACTS` ships empty today,
    # but a future `Column(str)` contract validated against a naturally-empty `object`-dtype
    # frame (the pin's normal output) will hit the same mismatch. Tracked in
    # deferred-work.md rather than fixed here (out of scope for this bugfix).
    empty_ok = pd.DataFrame(
        {"name": pd.Series([], dtype="string[pyarrow]"), "version": pd.Series([], dtype="string[pyarrow]")}
    )
    hooks = DataValidationHooks([PanderaValidator({"pypi_current_versions": PYPI_SCHEMA})], build_stamp=STAMP)
    raised, saves = _run(hooks, empty_ok)
    assert raised is None
    assert saves == ["pypi_current_versions"]


def test_empty_frame_missing_a_required_column_halts():
    # same `string[pyarrow]` note as above -- keeps this test isolated to the missing-column
    # failure it's named for, instead of also (incidentally) tripping the dtype mismatch.
    empty_bad = pd.DataFrame({"name": pd.Series([], dtype="string[pyarrow]")})  # no version column
    hooks = DataValidationHooks([PanderaValidator({"pypi_current_versions": PYPI_SCHEMA})], build_stamp=STAMP)
    raised, saves = _run(hooks, empty_bad)
    assert isinstance(raised, DataContractViolation)
    assert saves == []


def test_a_broken_validator_halts_never_silently_passes():
    # a validator whose check() blows up (a broken schema/backend) must HALT the run, never
    # silently let unvalidated data persist. The unexpected error propagates (a real halt).
    class _BrokenValidator:
        name = "broken"

        def check(self, dataset, data):
            raise RuntimeError("schema is broken")

    saves: list[str] = []
    pipe = Pipeline([node(_identity, inputs="raw_in", outputs="pypi_current_versions", name="emit")])
    catalog = DataCatalog(
        {"raw_in": MemoryDataset(GOOD), "pypi_current_versions": _TrackingDataset(saves, "pypi_current_versions")}
    )
    hm = _create_hook_manager()
    _register_hooks(hm, (DataValidationHooks([_BrokenValidator()], build_stamp=STAMP),))
    with pytest.raises(Exception):
        SequentialRunner().run(pipe, catalog, hook_manager=hm)
    assert saves == []  # broken backend halts loudly rather than passing bad data


def test_default_no_op_sink_does_not_crash():
    # DataValidationHooks() default: no sink injected → the alert is built but delivered
    # nowhere; the violation still raises natively and nothing crashes.
    hooks = DataValidationHooks([PanderaValidator({"pypi_current_versions": PYPI_SCHEMA})], build_stamp=STAMP)
    raised, saves = _run(hooks, MISSING_VERSION)
    assert isinstance(raised, DataContractViolation)
    assert isinstance(raised.alert, AtlasAlert)  # payload built even with no sink
    assert saves == []


def test_a_failing_sink_never_masks_the_halt():
    # a sink that itself raises must not turn the FR-10 halt into a different (non-halting)
    # outcome — the DataContractViolation still propagates.
    def _boom(alert):
        raise RuntimeError("sink down")

    hooks = DataValidationHooks(
        [PanderaValidator({"pypi_current_versions": PYPI_SCHEMA})], alert_sink=_boom, build_stamp=STAMP
    )
    raised, saves = _run(hooks, MISSING_VERSION)
    assert isinstance(raised, DataContractViolation)  # the halt survived the sink failure
    assert saves == []


def test_multi_output_node_halts_before_any_output_persists():
    # a 2-output node where ONE output violates its contract: neither output persists (the
    # halt fires in after_node_run, before the save loop touches the first output).
    saves: list[str] = []

    def _two(df):
        return GOOD, MISSING_VERSION

    pipe = Pipeline([node(_two, inputs="raw_in", outputs=["clean_out", "pypi_current_versions"], name="emit")])
    catalog = DataCatalog(
        {
            "raw_in": MemoryDataset("seed"),
            "clean_out": _TrackingDataset(saves, "clean_out"),
            "pypi_current_versions": _TrackingDataset(saves, "pypi_current_versions"),
        }
    )
    hm = _create_hook_manager()
    _register_hooks(hm, (DataValidationHooks([PanderaValidator({"pypi_current_versions": PYPI_SCHEMA})], build_stamp=STAMP),))
    with pytest.raises(DataContractViolation):
        SequentialRunner().run(pipe, catalog, hook_manager=hm)
    assert saves == []  # NEITHER output persisted


# --------------------------------------------------------------------------- #
# AD-23 — registered on every entry point; deepcopy-safe (C1 translator copies HOOKS)
# --------------------------------------------------------------------------- #
def test_hook_registered_in_settings_beside_the_others():
    from pyforge.atlas import settings

    kinds = {type(h).__name__ for h in settings.HOOKS}
    assert "DataValidationHooks" in kinds
    # rides beside the A3 + E2 hooks (AD-23: one registration, every entry point).
    assert {"ProjectHooks", "AtlasObservabilityHooks"} <= kinds


def test_default_hook_is_deepcopy_safe():
    # C1's KedroProjectTranslator deep-copies settings.HOOKS at to_dagster() build time; the
    # shipped default must survive it (no un-deepcopyable state).
    dup = copy.deepcopy(DataValidationHooks())
    assert isinstance(dup, DataValidationHooks)
    # and it still functions after the copy.
    raised, saves = _run(dup, GOOD, out_name="unregistered_dataset")
    assert raised is None


def test_co_registered_with_observability_still_halts_order_independent():
    # both the E2 observability hook AND the validation hook registered together: the run
    # still halts before persist regardless of hook order (the save loop never starts).
    saves: list[str] = []
    pipe = Pipeline([node(_identity, inputs="raw_in", outputs="pypi_current_versions", name="emit")])
    catalog = DataCatalog(
        {"raw_in": MemoryDataset(MISSING_VERSION), "pypi_current_versions": _TrackingDataset(saves, "pypi_current_versions")}
    )
    hm = _create_hook_manager()
    _register_hooks(
        hm,
        (
            AtlasObservabilityHooks(),
            DataValidationHooks([PanderaValidator({"pypi_current_versions": PYPI_SCHEMA})], build_stamp=STAMP),
        ),
    )
    with pytest.raises(DataContractViolation):
        SequentialRunner().run(pipe, catalog, hook_manager=hm)
    assert saves == []
