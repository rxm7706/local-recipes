"""``marshal gate evaluate``'s pure aggregation core (Story 2.1, FR-20,
AD-4/AD-7/AD-17/AD-26).

Given each configured verify command's ALREADY-OBTAINED outcome -- a
``ProcessResult`` (Story 2.1's own ``ports/process.py`` value type) or a
documented reason it never ran at all -- classifies it into a per-command
report dict plus zero-or-one ``Finding``, via ``core.findings``'s registered
codes. No I/O, no subprocess, no clock, no ``pyforge.marshal.adapters``
import (AD-4, enforced by the AD-3/AD-4 import-linter contract): this module
does not hold a ``ProcessPort`` reference at all, only the ``ProcessResult``
value type ``ports/process.py`` also defines.

**Why this module never calls ``ProcessPort`` directly.** The AC says the
aggregation "lives in ``core/gate.py`` as a pure function over exit codes,
with all process spawning behind ``ProcessPort``" -- read together with AD-4
and this package's established split (``core/policy.py``'s own docstring:
"never reads a file or an env var ... the CLI boundary does the I/O and
calls this"), the spawning itself belongs in ``cli/gate.py``.
``cli/gate.py`` builds each command's ``ProcessResult | None`` (via
``shlex.split`` + ``ProcessPort.run``, catching the adapter's
``ProcessError``), then calls ``classify_outcome`` per command and folds the
returned findings with ``verdict.compute_verdict`` -- the SAME
pure-core/impure-boundary split ``core/status.py`` uses for ``marshal
homes``.

**The ``failure_code``/``failure_reason`` split from the spec's own Design
Notes sketch.** That sketch's ``result is None`` branch writes
``Finding(code=..., ...)`` with an unfilled placeholder: this module has no
way to know WHICH of the two distinct "never ran" reasons applied (a
``shlex.split`` parse failure, ``MRS-GATE-003``, vs. a
``ProcessPort.run``-raised launch failure, ``MRS-GATE-002``) without being
told -- only ``cli/gate.py``, which caught the specific exception, knows
that. ``classify_outcome`` therefore takes an explicit ``failure_code``
(required whenever ``result`` is ``None``) rather than guessing or hiding a
second concept behind one code.

Five real codes register here (the registry's seventh real caller, joining
``core/identity.py``/``core/policy.py`` and ``cli/init.py``'s five commands
-- see ``core/findings.py``'s own docstring for the exact per-code mapping):
``MRS-GATE-001`` (a command ran and exited non-zero) classifies
``Verdict.GATE_FAILED`` -- a REAL check that ran and failed, the lattice's
dedicated "a gate failed" rung, distinct from every ``ERROR``-tier code
before it (those are all "an internal Marshal operation failed", not "a
project's own gate failed"). ``MRS-GATE-002``/``003`` (the command's
executable could not be launched, or its string could not be
``shlex.split``) classify ``Verdict.UNEVALUABLE`` -- Marshal could not run
the check at all. ``MRS-GATE-004`` (``verify_commands`` composed to the
empty tuple) classifies ``Verdict.WARN`` -- see
``no_commands_configured_finding``'s own docstring for why this is a
distinct, non-blocking case from ``MRS-GATE-002``/``003``. Story 2.4's
``classify_doc_only_declaration`` adds the fifth, ``MRS-GATE-006`` (the
worktree has no changes AND the story was not declared doc-only -- the one
combination indistinguishable from a story that silently failed to do its
work) -- classifies ``Verdict.GATE_FAILED``, the same tier as
``MRS-GATE-001``: a real, determinable outcome, never "could not evaluate".
See ``core/verdict.py`` for the classification table itself.

Story 2.5's ``describe_gate_mode`` (FR-24) registers no sixth finding code.
It shapes the already-selected ``gate_mode`` into an autonomy-label report
by looking up ``core/policy.py``'s ``GATE_MODE_AUTONOMY_LABELS``, and raises
``ValueError`` -- never a ``Finding`` -- for a value outside the closed
3-mode vocabulary ``core/policy.compose()`` already restricts at
composition time: the same precedent ``core/verdict.py::classify()`` sets
for a registered-but-unclassified code.

Story 2.3's ``compute_effective_surface``/``check_scope`` (AD-4/AD-26/AD-27)
add two more real codes, this table's first classifications into the
``Verdict.SCOPE_VIOLATION`` rung (reserved since Story 1.1, never used
until now): ``MRS-GATE-007`` (a changed path matches no glob in the
effective surface -- ``policy_surface ∩ spec_surface``, AD-27's own
intersection-only combinator) and ``MRS-GATE-008`` (a changed path matches
a glob in the live frozen set -- ``core/journal.py::FoldResult.
live_frozen_surfaces``, AD-26's fold-is-the-only-producer rule -- naming
both the path and the freezing story, or "policy" for a policy-seeded
freeze). Both pure, both driven entirely by already-resolved inputs
(``core/journal``'s ``FrozenPath`` and a caller-supplied ``changed_files``
tuple -- this module still performs no VCS I/O itself, matching
``classify_outcome``'s own already-obtained-``ProcessResult`` shape).

Story 2.7's ``check_spec_binding`` (AD-4/AD-31/AD-49) adds two more real
codes, reusing ``Verdict.SCOPE_VIOLATION`` -- the same rung ``MRS-GATE-
007``/``008`` classify -- per AD-49's own text ("an untraceable or
mismatched binding cannot itself be waived to green", the same closed
lattice every other admission criterion participates in). ``MRS-GATE-010``
(``declared_commands is None`` -- no tracked spec, or a tracked spec with
no parseable ``## Verification`` -> ``**Commands:**`` Success signal) and
``MRS-GATE-011`` (one per declared command absent from ``policy_commands``
-- narrowed or removed from the policy since the spec was tracked) are
both pure, driven entirely by already-resolved inputs (``core.spec_binding.
parse_success_signal``'s already-parsed ``declared_commands`` tuple and the
caller's own ``policy_commands`` -- this module performs no spec-file read
itself, matching every other function in this module's "caller already
gathered the fact" shape).
"""

from __future__ import annotations

import fnmatch

from ..ports.process import ProcessResult
from . import policy
from .journal import FrozenPath
from .model import Finding, Severity, Status, status_for
from .verdict import classify


def classify_outcome(
    command: str,
    result: ProcessResult | None,
    *,
    failure_code: str | None = None,
    failure_reason: str | None = None,
) -> tuple[dict[str, object], Finding | None]:
    """Classify ONE verify command's already-obtained outcome.

    ``result is None`` means the command never ran at all -- both
    ``failure_code`` (a registered ``core.findings`` code that classifies to
    a non-ok status, e.g. ``MRS-GATE-002``/``MRS-GATE-003``) and
    ``failure_reason`` (the human-readable message) are then REQUIRED
    (``ValueError`` otherwise): this function has no other way to know why
    the command is missing an outcome, and a silent default would hide a
    real caller bug. The returned report carries ``resolvable: False`` and
    ``returncode: None``, with no ``stdout``/``stderr`` keys (there is no
    captured output for a process that never ran).

    A non-``None`` ``result`` always classifies via ``result.returncode``:
    ``0`` reports ``resolvable: True``, the captured output, and no finding
    (a passing command is not itself news); non-zero reports the same shape
    plus one ``MRS-GATE-001`` finding naming the command and how it ended.
    Passing a ``result`` AND a declared failure is a caller bug and raises
    ``ValueError``: silently preferring the result would DROP the caller's
    failure and report a pass, the one direction this function must never
    fail quietly in.
    """
    if result is not None and (failure_code is not None or failure_reason is not None):
        raise ValueError(
            "failure_code/failure_reason are only meaningful when result is "
            "None (the command never ran) -- passing both a result and a "
            "declared failure would silently drop the failure"
        )

    if result is None:
        if failure_code is None or failure_reason is None:
            raise ValueError(
                "failure_code and failure_reason are both required when "
                "result is None (the command never ran)"
            )
        if status_for(classify(failure_code)) is Status.OK:
            # The LAST silent direction left in this function (review
            # finding, verified live). The finding below is stamped
            # Severity.ERROR unconditionally, but AD-39 forbids an
            # ok-status envelope from carrying an error-severity finding --
            # so a WARN- or CLEAN-classified failure_code (MRS-GATE-004,
            # MRS-POLICY-005, ...) produced a perfectly ordinary-looking
            # report here and then crashed build_envelope with a ValueError
            # main() does not catch, several frames away from the caller
            # that actually made the mistake. classify() also raises for an
            # unregistered code, so this same check closes that hole too.
            raise ValueError(
                f"failure_code {failure_code!r} classifies to "
                f"{classify(failure_code).value!r}, whose status is ok -- "
                "classify_outcome stamps Severity.ERROR, and an ok-status "
                "envelope may carry no error-severity finding, so this would "
                "crash build_envelope downstream instead of failing here"
            )
        report: dict[str, object] = {
            "command": command,
            "resolvable": False,
            "returncode": None,
        }
        return report, Finding(
            code=failure_code, severity=Severity.ERROR, message=failure_reason
        )

    if result.returncode != 0:
        # A NEGATIVE returncode is POSIX for "terminated by signal N"
        # (subprocess reports -N), not an exit status any process can
        # return -- "exited -9" reads as an exit code and tells an operator
        # their check failed when the OOM killer or a CI SIGTERM ended it
        # before it produced any result at all. The classification stays
        # MRS-GATE-001/GATE_FAILED either way: the command really did run
        # and really did not pass, and re-routing a killed check toward
        # UNEVALUABLE would move the verdict TOWARD green, which this
        # module never does on an ambiguity.
        outcome = (
            f"was terminated by signal {-result.returncode}"
            if result.returncode < 0
            else f"exited {result.returncode}"
        )
        return (
            {
                "command": command,
                "resolvable": True,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
            Finding(
                code="MRS-GATE-001",
                severity=Severity.ERROR,
                message=f"verify command {command!r} {outcome}",
            ),
        )

    return (
        {
            "command": command,
            "resolvable": True,
            "returncode": 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
        None,
    )


def no_commands_configured_finding() -> Finding:
    """``MRS-GATE-004`` (``Verdict.WARN``): ``verify_commands`` composed to
    the empty tuple -- Marshal's own ``DEFAULT_POLICY`` value, the state
    every brand-new project with no ``marshal-policy.toml`` override starts
    in, not a project's deliberate declaration to skip gating. Classifying
    this ``unevaluable`` (like ``MRS-GATE-002``/``003``) would make every
    not-yet-configured project fail ``gate evaluate`` by default -- a
    harsher bar than the identical-shaped precedent ``MRS-POLICY-005``
    already sets for "no active project supplied" (``Verdict.WARN``); see
    the spec's Design Notes for the full reasoning."""
    return Finding(
        code="MRS-GATE-004",
        severity=Severity.WARN,
        message=(
            "no verify commands configured -- verify_commands composed to "
            "the empty tuple; nothing was run"
        ),
    )


def classify_doc_only_declaration(
    *, declared_doc_only: bool, has_uncommitted_changes: bool
) -> tuple[dict[str, object], Finding | None]:
    """Classify a story's already-established doc-only declaration against
    the worktree's already-established change state (Story 2.4, FR-23).

    Both inputs are facts a caller already gathered -- ``declared_doc_only``
    from the story's own declaration, ``has_uncommitted_changes`` from
    something like ``VcsPort.has_uncommitted_changes`` (Story 1.8) -- never
    gathered here (AD-4): this function does no I/O, no VCS call, no
    spec-file read, exactly like ``classify_outcome`` takes an
    already-obtained ``ProcessResult``.

    Fails ONLY when the worktree has no changes AND the story was not
    declared doc-only -- that is the one combination indistinguishable from
    a story that silently failed to do its work, and it reports one
    ``MRS-GATE-006`` finding naming the exact condition. Every other
    combination -- declared with no changes (the exemption this function
    exists for), declared with changes (nothing to suppress), or undeclared
    with changes (an ordinary story) -- returns ``(report, None)``: a
    doc-only declaration never produces a worse outcome than an undeclared
    one, and a story with real changes is never penalized regardless of its
    declaration.

    The returned ``report`` always carries both input facts
    (``declared_doc_only``, ``has_uncommitted_changes``), regardless of
    which branch ran, so a future caller has something to fold into its own
    output/record either way -- mirroring ``classify_outcome``'s own report
    shape.
    """
    report: dict[str, object] = {
        "declared_doc_only": declared_doc_only,
        "has_uncommitted_changes": has_uncommitted_changes,
    }
    if not has_uncommitted_changes and not declared_doc_only:
        return report, Finding(
            code="MRS-GATE-006",
            severity=Severity.ERROR,
            message=(
                "no worktree changes and the story was not declared "
                "doc-only -- a story must either produce a change or "
                "declare its deliverable as doc-only"
            ),
        )
    return report, None


def describe_gate_mode(gate_mode: str) -> dict[str, object]:
    """Shape an already-selected ``gate_mode`` into its FR-24 autonomy-label
    report (Story 2.5).

    Pure, no I/O: the caller already read ``gate_mode`` from policy (e.g.
    ``EffectivePolicy.seed_view()["gate_mode"].value``) -- mirrors
    ``classify_outcome``/``classify_doc_only_declaration``'s own "caller
    already gathered the fact" shape. Returns a FRESH, JSON-serializable
    plain dict -- never an alias into ``policy.GATE_MODE_AUTONOMY_LABELS``
    -- e.g. ``{"gate_mode": "per-epic", "autonomy_label": {"level": "L3",
    "name": "Conditional / Context Gates", "meaning": "..."}}``.

    ``gate_mode`` must be one of the 3 keys ``policy.GATE_MODE_AUTONOMY_
    LABELS`` defines -- the same closed vocabulary ``core/policy.compose()``
    already restricts any composed ``EffectivePolicy`` to at composition
    time (``_valid_gate_mode``). An out-of-vocabulary value is therefore an
    internal-consistency violation, not a real-world outcome an operator
    needs a machine-readable ``Finding`` for, so this raises ``ValueError``
    naming the invalid value -- mirroring ``core/verdict.py::classify()``'s
    own precedent for a registered-but-unclassified code, never a silent
    default and never a new ``MRS-GATE-*`` code.
    """
    try:
        label = policy.GATE_MODE_AUTONOMY_LABELS[gate_mode]
    except KeyError as exc:
        raise ValueError(
            f"gate_mode {gate_mode!r} is not one of the known autonomy-"
            f"labeled modes {sorted(policy.GATE_MODE_AUTONOMY_LABELS)}"
        ) from exc
    return {"gate_mode": gate_mode, "autonomy_label": dict(label)}


# --- Story 2.3: frozen-surface scope check, narrowing only (AD-4/AD-26/AD-27) -


def _valid_glob_tuple(value: object, *, name: str) -> None:
    if not isinstance(value, tuple) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{name} must be a tuple of str, got {value!r}")


def compute_effective_surface(
    policy_surface: tuple[str, ...], spec_surface: tuple[str, ...] | None
) -> tuple[str, ...]:
    """The AD-27 combinator: ``policy_surface`` narrowed by
    ``spec_surface``, and ONLY narrowed -- never widened, never any other
    combinator. Pure, no I/O.

    ``spec_surface is None`` (no story spec, or no ``surface:`` field) means
    there is nothing to narrow against, so the effective surface is
    ``policy_surface`` unchanged. Otherwise the effective surface is the
    INTERSECTION of the two glob tuples, literally ``set(a) & set(b)`` --
    never ``spec_surface`` alone, never a union. A glob the spec declares
    that ``policy_surface`` does not already carry is silently excluded
    here (never a widening, never itself a finding) -- a change that later
    lands only on a path matching that excluded glob is what turns into a
    real, named finding, in ``check_scope`` below.

    The result is sorted for a deterministic, reproducible return value
    (set iteration order is not otherwise guaranteed) -- callers that care
    about declaration order have ``spec_surface``/``policy_surface``
    themselves to consult."""
    _valid_glob_tuple(policy_surface, name="policy_surface")
    if spec_surface is None:
        return policy_surface
    _valid_glob_tuple(spec_surface, name="spec_surface")
    return tuple(sorted(set(policy_surface) & set(spec_surface)))


def _matches_any(path: str, globs: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, glob) for glob in globs)


def check_scope(
    effective_surface: tuple[str, ...],
    frozen_paths: tuple[FrozenPath, ...],
    changed_files: tuple[str, ...],
) -> tuple[Finding, ...]:
    """The pure scope-check core (Story 2.3, epics.md's own ACs): classify
    every path in ``changed_files`` against ``frozen_paths`` (checked
    FIRST -- a frozen path is a hard failure regardless of whether it also
    sits inside the effective surface) and ``effective_surface``. Pure, no
    I/O.

    Two independent finding classes, both possible across one call (one
    ``Finding`` per offending path, never one finding naming several):

    - ``MRS-GATE-008`` -- ``path`` matches a glob in some ``FrozenPath``'s
      own ``path`` -- names both the offending path AND the story that
      froze it (``story_key``), or that it was policy-seeded when
      ``story_key`` is ``None``.
    - ``MRS-GATE-007`` -- ``path`` is not frozen, but matches no glob in
      ``effective_surface`` -- names the offending path.

    A path matched by neither carries no finding at all: it is squarely
    inside the effective surface and untouched by any freeze."""
    if not isinstance(frozen_paths, tuple) or not all(
        isinstance(item, FrozenPath) for item in frozen_paths
    ):
        raise TypeError(f"frozen_paths must be a tuple of FrozenPath, got {frozen_paths!r}")
    if not isinstance(changed_files, tuple) or not all(
        isinstance(item, str) for item in changed_files
    ):
        raise TypeError(f"changed_files must be a tuple of str, got {changed_files!r}")
    _valid_glob_tuple(effective_surface, name="effective_surface")

    result: list[Finding] = []
    for path in changed_files:
        frozen = next(
            (fp for fp in frozen_paths if fnmatch.fnmatch(path, fp.path)), None
        )
        if frozen is not None:
            owner = f"story {frozen.story_key}" if frozen.story_key is not None else "policy"
            result.append(
                Finding(
                    code="MRS-GATE-008",
                    severity=Severity.ERROR,
                    message=(
                        f"changed path {path!r} touches a frozen surface "
                        f"(frozen by {owner})"
                    ),
                    path=path,
                )
            )
            continue
        if not _matches_any(path, effective_surface):
            result.append(
                Finding(
                    code="MRS-GATE-007",
                    severity=Severity.ERROR,
                    message=(
                        f"changed path {path!r} is outside the effective "
                        f"surface {effective_surface!r}"
                    ),
                    path=path,
                )
            )
    return tuple(result)


# --- Story 2.7: a gate binds to the spec's Success signal (AD-4/AD-31/AD-49) -


def check_spec_binding(
    declared_commands: tuple[str, ...] | None,
    policy_commands: tuple[str, ...],
) -> tuple[Finding, ...]:
    """Confirm the commands a tracked spec's own Success signal declared are
    still among the ones policy currently runs (AD-49). Pure, no I/O.

    ``declared_commands is None`` -- no tracked spec, or a tracked spec with
    no parseable ``## Verification`` -> ``**Commands:**`` section (``core.
    spec_binding.parse_success_signal`` returned ``None``) -- reports ONE
    ``MRS-GATE-010`` finding naming the missing binding (AC2: "reported
    explicitly ... never evaluated silently against nothing").

    Otherwise, ONE-DIRECTIONAL (AC per the spec's own Boundaries):
    every command in ``declared_commands`` NOT present in ``policy_commands``
    gets its own ``MRS-GATE-011`` finding, naming the narrowed/removed
    command. A ``policy_commands`` that runs commands ``declared_commands``
    never named is NOT itself a finding -- the spec's Success signal is a
    floor policy must still clear, never a ceiling policy may not exceed. An
    empty ``declared_commands`` (the spec's own ``## Verification`` section
    exists but declares no commands at all) therefore reports no findings:
    there is nothing declared to miss.

    Two normalizations happen before that comparison, both review findings
    (P2/P6):

    - ``declared_commands`` is DEDUPLICATED first (order-preserving, via
      ``dict.fromkeys``) -- a spec that accidentally repeats the same
      command string in two bullets reports exactly ONE ``MRS-GATE-011``
      for it, not one per repetition (the same command missing is one fact,
      not several).
    - The membership test collapses incidental whitespace runs to a single
      space on BOTH sides (``" ".join(command.split())``) before comparing
      -- a spec bullet and a policy entry that differ only by, say, a
      double space are the same command in effect and must not be reported
      as narrowed/removed. This is intentionally SHALLOW: no shell-aware
      argument parsing, just whitespace collapse.
    """
    if declared_commands is None:
        return (
            Finding(
                code="MRS-GATE-010",
                severity=Severity.ERROR,
                message=(
                    "no Success signal to bind against -- the story has no "
                    "tracked spec, or its tracked spec has no parseable "
                    "## Verification -> **Commands:** section"
                ),
            ),
        )
    normalized_policy = {" ".join(command.split()) for command in policy_commands}
    return tuple(
        Finding(
            code="MRS-GATE-011",
            severity=Severity.ERROR,
            message=(
                f"verify command {command!r} is named in the story's "
                "tracked spec Success signal but is no longer among the "
                "policy's verify_commands -- narrowed or removed since the "
                "spec was tracked"
            ),
        )
        for command in dict.fromkeys(declared_commands)
        if " ".join(command.split()) not in normalized_policy
    )
