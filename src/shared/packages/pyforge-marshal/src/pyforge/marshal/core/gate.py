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
"""

from __future__ import annotations

from ..ports.process import ProcessResult
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
