"""Data-validation hook + inline pandera contracts (Story F2, FR-10).

This module is the **single data-validation seam**. It provides a *validator-agnostic*
Kedro hook that validates a node's output against a per-dataset contract and **halts the
pipeline BEFORE the output persists** when the contract is violated — by raising a native
Python exception that propagates to Dagster (halting the run) and, on its way out, emitting
an **A2A alert** on E1's channel (AD-20).

Pre-persist hook point (verified against kedro 1.5.0)
-----------------------------------------------------
The hook fires in ``after_node_run``. In kedro 1.5.0 the sequential task calls
``after_node_run`` with the node's COMPLETE ``outputs`` dict from inside
``Task._call_node_run`` **before** the runner's save loop begins — that loop
(``before_dataset_saved`` → ``catalog.save`` → ``after_dataset_saved``) runs afterwards.
So a raise in ``after_node_run`` halts before ANY output of the node persists. It is a
strictly better pre-persist point than ``before_dataset_saved``: for a multi-output node,
``before_dataset_saved`` fires per-output and an earlier output would already be saved
before a later output's guard runs, whereas ``after_node_run`` sees the whole output set
in one place, before the first save. (Confirmed empirically: raising in ``after_node_run``
leaves the catalog un-persisted.)

Validator-agnostic (AC-3, AD-9)
-------------------------------
:class:`Validator` is a tiny protocol — a backend implements ``check(dataset, data)`` and
**reports** violations; it never raises/halts itself. The hook owns the raise + alert in ONE
place, so adding or swapping a backend needs **zero node changes** (the gate proves this with
a stub second validator). :class:`PanderaValidator` is the shipped inline backend.
:class:`GreatExpectationsBoundaryValidator` is the OPTIONAL, version-capped boundary backend
— deferred (DW-F2-1, see its docstring): the shipped path does NOT import
``great_expectations`` at all, because the in-env GX (1.19.0) cannot be statically guaranteed
to stay within conda-forge 1.18.2 features (AD-9). pandera is the shipped default.

Offline / injectable (AD-20)
----------------------------
The A2A alert **payload** is always built via E1's :func:`build_alert_payload` (AD-20 — one
channel, one schema source). *Delivery* is an injectable ``alert_sink`` that defaults to a
no-op, so the in-container default path emits nowhere (no network). The gate injects a sink
that hands the alert to an :class:`~pyforge.atlas.a2a.AuthoringInbox` via
:func:`~pyforge.atlas.a2a.hand_off`, proving the alert rides the real A2A channel. The
``build_stamp`` (AD-17) is injectable and resolved at EMIT time (a real runtime violation),
never at import/construction.

Contracts are DATA (AD-2/AD-6)
------------------------------
Contracts live in :data:`DEFAULT_CONTRACTS` — a per-dataset ``{name: DataFrameSchema}``
registry — never inline in a node body. Nodes stay pure DataFrame→DataFrame. The registry
ships EMPTY: F2 delivers the machinery + seam, not speculative contracts for datasets whose
shape is not verified here (F4 and later waves declare contracts as they land). With zero
contracts the settings-registered hook (AD-23) is a pass-through until a schema is declared,
so it can never false-halt a real run today while still arming every entry point.

Imports are stdlib + ``pandera`` + ``kedro.framework.hooks`` + the in-package ``a2a`` seam
only — NO ``IO_DENYLIST`` client, NO ``openlineage``/``opentelemetry``, NO banned
``kedro_great_expectations`` / ``kedro_pandera`` plugin, and (AD-9) NO ``great_expectations``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable

import pandera.pandas as pa

from kedro.framework.hooks import hook_impl

from pyforge.atlas.a2a import AtlasAlert, Severity, build_alert_payload

logger = logging.getLogger(__name__)

# Per-dataset pandera contract registry (declared as DATA — never inline in a node).
# EMPTY by default (see module docstring): ship the machinery + seam, nothing speculative.
DEFAULT_CONTRACTS: dict[str, pa.DataFrameSchema] = {}

# The single rule identifier a pandera breach reports (named, stable — feeds the alert).
PANDERA_RULE = "pandera_schema"

# How many pandera failure cases to carry as structured alert evidence (bounded so a
# wholesale failure does not produce an unbounded payload).
_MAX_EVIDENCE_CASES = 20


@dataclass(frozen=True)
class ContractViolation:
    """One contract breach: which backend, which dataset, the violated rule, evidence.

    ``evidence`` is JSON-native (str/num/bool/None + list/dict of same) so it can ride
    inside an :class:`~pyforge.atlas.a2a.AtlasAlert` (AD-20 payloads are JSON-native).
    """

    dataset: str
    validator: str
    rule: str
    evidence: dict[str, Any] = field(default_factory=dict)


class DataContractViolation(RuntimeError):
    """The native halting exception raised when a node output violates its contract.

    A plain ``RuntimeError`` subclass, deliberately: Dagster and kedro treat it as an
    ordinary run failure with NO special handling — the run halts and E2's
    ``on_pipeline_error`` (OL FAIL + span ERROR) fires naturally. It carries the
    structured ``violations`` and the emitted ``alert`` for inspection/tests.
    """

    def __init__(
        self, dataset: str, violations: list[ContractViolation], alert: AtlasAlert
    ) -> None:
        self.dataset = dataset
        self.violations = tuple(violations)
        self.alert = alert
        rules = ", ".join(sorted({v.rule for v in violations})) or "unknown"
        super().__init__(
            f"data contract violation on dataset {dataset!r}: {rules} "
            f"— halted before persist (FR-10)"
        )


@runtime_checkable
class Validator(Protocol):
    """The validator-agnostic seam (AC-3).

    A backend exposes a ``name`` and ``check(dataset, data) -> list[ContractViolation]``.
    It REPORTS violations (empty list == pass / not-applicable); it never raises to halt.
    Keeping the raise/alert in the hook means a new backend needs zero node or hook edits.
    """

    name: str

    def check(self, dataset: str, data: Any) -> list[ContractViolation]: ...


def _is_dataframe(data: Any) -> bool:
    """True for a pandas/polars-style 2-D frame (a ``.shape`` 2-tuple + ``.columns``).

    Gates on frame-ness rather than duck-typing, so a non-frame output (a dict/str/scalar)
    is skipped gracefully by a frame validator instead of crashing it (Reviewer-B surface)."""
    shape = getattr(data, "shape", None)
    return isinstance(shape, tuple) and len(shape) == 2 and hasattr(data, "columns")


def _coerce_json_native(obj: Any) -> Any:
    """Blanket-coerce a value to a JSON-native shape, RECURSIVELY. Beyond ``str()``-ing unknowns,
    this maps pandas/numpy nulls (``pd.NA`` / ``NaN`` / ``NaT``) to ``None`` and unwraps numpy
    scalars/arrays to native Python — so pandera/backend evidence carries clean JSON ``null`` and
    native numbers instead of ``"<NA>"`` / ``"nan"`` / numpy reprs (Gemini #91/#93)."""
    if obj is None:
        return None
    if isinstance(obj, bool):  # bool BEFORE int (bool is an int subclass)
        return obj
    if isinstance(obj, dict):
        return {str(k): _coerce_json_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_coerce_json_native(v) for v in obj]
    # numpy scalar/array → native (then recurse in case it became a list/dict).
    if type(obj).__module__.split(".")[0] == "numpy" and hasattr(obj, "tolist"):
        return _coerce_json_native(obj.tolist())
    # scalar pandas/numpy null → JSON null (guard is_scalar so a container doesn't raise).
    import pandas as pd

    if pd.api.types.is_scalar(obj) and pd.isna(obj):
        return None
    if isinstance(obj, (int, str)):
        return obj
    if isinstance(obj, float):
        return obj if (obj == obj and obj not in (float("inf"), float("-inf"))) else str(obj)
    return str(obj)


def _pandera_evidence(exc: pa.errors.SchemaErrors) -> dict[str, Any]:
    """Compact, JSON-native evidence from a pandera ``SchemaErrors`` failure set.

    pandera's ``failure_cases`` is a DataFrame; we distill a bounded list of
    ``{schema_context, column, check, failure_case}`` rows with every value coerced to a
    JSON-native scalar so the evidence is safe to carry in an A2A alert."""
    cases: list[dict[str, Any]] = []
    try:
        fc = exc.failure_cases
        cols = [c for c in ("schema_context", "column", "check", "failure_case") if c in fc.columns]
        for _, row in fc.head(_MAX_EVIDENCE_CASES).iterrows():
            cases.append({c: _coerce_json_native(row[c]) for c in cols})
        total = int(len(fc))
    except Exception:  # noqa: BLE001 - evidence is best-effort; never let it mask the halt
        total = len(cases)
    return {"failure_case_count": total, "failure_cases": cases}


class PanderaValidator:
    """Primary inline validator: per-dataset pandera ``DataFrameSchema`` (FR-10, AD-9)."""

    name = "pandera"

    def __init__(self, contracts: dict[str, pa.DataFrameSchema] | None = None) -> None:
        self._contracts = dict(contracts if contracts is not None else DEFAULT_CONTRACTS)

    def check(self, dataset: str, data: Any) -> list[ContractViolation]:
        schema = self._contracts.get(dataset)
        if schema is None:
            return []  # no contract registered → pass-through (never a false halt)
        if not _is_dataframe(data):
            # a frame contract cannot validate a non-frame output; skip gracefully rather
            # than crash (Reviewer-B). With an empty shipped registry this is gate-only.
            logger.debug("pandera: %r output is not a DataFrame; skipping frame validation", dataset)
            return []
        try:
            schema.validate(data, lazy=True)
        except pa.errors.SchemaErrors as exc:
            return [ContractViolation(dataset, self.name, PANDERA_RULE, _pandera_evidence(exc))]
        except pa.errors.SchemaError as exc:  # non-lazy single-error path
            return [ContractViolation(dataset, self.name, PANDERA_RULE, {"error": str(exc)})]
        return []


class GreatExpectationsBoundaryValidator:
    """OPTIONAL boundary-layer validator — DEFERRED (DW-F2-1), version-capped (AD-9).

    Great Expectations participates ONLY at conda-forge **1.18.2** semantics. The in-env GX
    is 1.19.0, and we cannot *statically guarantee* every code path stays within 1.18.2-only
    features, so — per AD-9's explicit preference — the shipped hook path does **NOT import
    ``great_expectations`` at all**. This class proves the validator-agnostic seam ACCEPTS a
    GX boundary backend with zero node changes (it conforms to :class:`Validator`); its
    ``check`` is a documented stub. Enable a real GX adapter only in an environment where GX
    is pinned to 1.18.2, at which point this stub is replaced by a 1.18.2-feature-only adapter
    — no node or hook change required (that is the point of the seam)."""

    name = "great_expectations"

    def check(self, dataset: str, data: Any) -> list[ContractViolation]:
        raise NotImplementedError(
            "GX boundary layer is deferred (DW-F2-1): it is version-capped at conda-forge "
            "GX 1.18.2, and the in-env GX 1.19.0 cannot be guaranteed to 1.18.2-only "
            "features, so no great_expectations is imported in the shipped path. pandera is "
            "the shipped inline validator (AD-9). This class only proves the seam accepts a "
            "GX backend with zero node changes."
        )


def _default_build_stamp() -> str:
    """AD-17 default: resolved at EMIT time (a real runtime violation), never at import or
    construction — mirrors ``dashboard/app.py``'s wall-clock default. The gate injects a
    fixed stamp for determinism."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class DataValidationHooks:
    """Validator-agnostic data-validation hook (FR-10, AD-9/AD-20/AD-23).

    Registered once in ``settings.HOOKS`` so EVERY entry point validates (AD-23): a
    ``kedro run`` picks it up natively, and the C1 Dagster plane picks it up too because the
    translator runs each node through ``KedroSession.run`` (settings hooks included).

    Parameters
    ----------
    validators:
        Ordered validator backends. ``None`` (default) → a single :class:`PanderaValidator`
        over :data:`DEFAULT_CONTRACTS`. Adding/swapping a backend needs no node change (AC-3).
    alert_sink:
        ``Callable[[AtlasAlert], None]`` delivering the alert on the A2A channel. ``None``
        (default) → no-op (offline). The gate injects a sink that ``hand_off``s to an
        ``AuthoringInbox``, proving AD-20.
    build_stamp:
        A fixed stamp string OR a ``Callable[[], str]`` provider (AD-17). ``None`` → the
        wall-clock provider resolved at emit time.
    severity:
        Alert severity for a contract violation (default ``critical`` — bad data).
    """

    def __init__(
        self,
        validators: list[Validator] | None = None,
        *,
        alert_sink: Callable[[AtlasAlert], None] | None = None,
        build_stamp: str | Callable[[], str] | None = None,
        severity: Severity | str = Severity.critical,
    ) -> None:
        self._validators: list[Validator] = (
            list(validators) if validators is not None else [PanderaValidator()]
        )
        self._sink = alert_sink
        self._stamp = build_stamp if build_stamp is not None else _default_build_stamp
        self._severity = Severity(severity)

    def _resolve_stamp(self) -> str:
        return self._stamp() if callable(self._stamp) else self._stamp

    @hook_impl
    def after_node_run(
        self,
        node: Any,
        catalog: Any,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        is_async: bool,
        run_id: str,
    ) -> None:
        # Pre-persist point: this fires with the full outputs dict BEFORE the runner's save
        # loop, so a raise here halts before ANY output of the node persists. Validate every
        # output of the node; the FIRST output with a violation halts the whole node (and
        # thus the pipeline) before the save loop starts (multi-output correctness).
        for name, data in (outputs or {}).items():
            violations: list[ContractViolation] = []
            for validator in self._validators:
                violations.extend(validator.check(name, data))
            if violations:
                self._halt(name, violations)

    @staticmethod
    def _json_native(obj: Any) -> Any:
        """Blanket-coerce a value to a JSON-native shape so any backend's evidence is safe to put
        in an AtlasAlert — delegates to the shared :func:`_coerce_json_native` (recursive; maps
        pandas/numpy nulls to ``null`` and unwraps numpy scalars, Gemini #93)."""
        return _coerce_json_native(obj)

    def _build_alert(self, dataset: str, violations: list[ContractViolation], rule: str) -> AtlasAlert:
        """Build the A2A alert with JSON-native-coerced evidence + a non-empty rule fallback, so
        an ill-behaved backend's evidence can never crash the halt or drop the alert (AD-20)."""
        evidence = self._json_native(
            {
                "dataset": dataset,
                "validators": sorted({v.validator for v in violations}),
                "violations": [
                    {"validator": v.validator, "rule": v.rule, **v.evidence} for v in violations
                ],
            }
        )
        return build_alert_payload(
            subject=dataset,
            severity=self._severity,
            rule=rule or "data-contract-violation",  # a backend may hand an empty rule
            build_stamp=self._resolve_stamp(),
            evidence=evidence,
        )

    def _halt(self, dataset: str, violations: list[ContractViolation]) -> None:
        """Build the A2A alert (AD-20), emit it on the injected sink, then RAISE the native
        halting exception. A sink failure must never swallow the halt (the halt is the
        load-bearing guarantee), so emission is guarded."""
        first = violations[0]
        # Build the alert DEFENSIVELY. The Validator seam (AC-3) accepts third-party backends,
        # whose ContractViolation.evidence is only DOCUMENTED (not enforced) JSON-native — a
        # backend returning a numpy scalar / set / non-finite float / empty rule would make
        # build_alert_payload's pydantic validators raise INSIDE _halt, converting a clean
        # FR-10 halt into a different exception type AND dropping the A2A alert (both reviewers).
        # str-coerce the evidence + fall back on the rule so the alert is always buildable, the
        # raised exception is always DataContractViolation, and the alert always fires.
        alert = self._build_alert(dataset, violations, first.rule)
        try:
            if self._sink is not None:
                self._sink(alert)
        except Exception:  # noqa: BLE001 - a sink error must not mask the FR-10 halt
            logger.exception(
                "A2A alert sink raised while reporting a data-contract violation on %r; "
                "halting anyway",
                dataset,
            )
        raise DataContractViolation(dataset, violations, alert)
