"""The central finding-code registry (Story 1.1, architecture spine AD-15).

Every failure or warning Marshal ever emits carries a stable machine code
from this one registry, plus a human message (AD-15). Codes are never
reused or renumbered. Format: ``MRS-<AREA>-<NNN>`` (Consistency Conventions'
``Findings`` row) -- e.g. ``MRS-GATE-001``.

``REGISTERED_CODES`` shipped Story 1.1 as an empty ``frozenset()`` --
``marshal --version``/``--help`` bypass the envelope entirely (mirrors
``pyforge-doctor``), so nothing emitted a real finding yet. Story 1.2's
``core/identity.py`` is the first real caller: ``MRS-IDENT-001`` (a
malformed story key) and ``MRS-IDENT-002`` (a non-conforming merge subject)
are its two registered codes. Story 1.3's ``core/policy.py``/``cli/config.py``
add the registry's second real caller: ``MRS-POLICY-001`` (an unknown
top-level policy key), ``MRS-POLICY-002`` (a malformed STATIC field value),
``MRS-POLICY-003`` (a malformed SEED field value), ``MRS-POLICY-004``
(a CLI-boundary I/O failure resolving or writing policy -- an unreadable
``--project-policy`` file or an unwritable ``--materialize`` target),
``MRS-POLICY-005`` (no project slug supplied -- the composed policy omits
its project-derived seed path), and ``MRS-POLICY-006`` (a malformed project
slug -- not usable as a single path segment). 001-004 and 006 classify
``Verdict.UNEVALUABLE``; 005 classifies ``Verdict.WARN`` (a bare
no-active-project invocation legitimately shows the defaults and exits 0)
-- see ``core/verdict.py``. Story 1.4's ``cli/init.py`` adds the registry's
third real caller: ``MRS-INIT-001`` (a malformed project slug -- the shape
check itself is shared with ``core/policy.py`` via
``_is_valid_project_slug``, but ``init`` registers its own code since
``marshal init`` is a distinct command with its own envelope),
``MRS-INIT-002`` (the slug names no known BMAD project -- no
``_bmad-output/projects/<slug>/planning-artifacts`` in the main checkout),
``MRS-INIT-003`` (the loop home's active-project marker and
``planning-artifacts`` symlink already disagree with each other, or the
symlink carries a target shape this command never writes -- a prior partial
failure or hand configuration, blocked before any further write rather
than silently overwritten), and ``MRS-INIT-004`` (a ``git``/filesystem
operation failed -- worktree add, marker write, or symlink repoint -- or a
blocking in-home check found the provisioned tree missing the project the
symlink would target). 001-002 classify ``Verdict.UNEVALUABLE`` (Marshal
could not determine what to provision); 003-004 classify ``Verdict.ERROR``
(a real operation was attempted and failed, or was blocked to avoid
compounding an existing failure) -- see ``core/verdict.py``. Story 1.5's
``tier3_backlink`` step (still ``cli/init.py``) adds a fifth code,
``MRS-INIT-005``: a real, non-empty directory already occupies the loop
home's local Tier-3 path
(``_bmad-output/projects/<slug>/implementation-artifacts``) -- the safe,
structural refusal to silently
replace it with a backlink to the main checkout's canonical copy (see the
spec's Design Notes on why this is a distinct code from ``MRS-INIT-004``
rather than a message a caller would need to string-match). It classifies
``Verdict.ERROR``, the same tier as 003-004: a real operation was attempted
and blocked, not "could not evaluate". Story 1.6's read-only ``cli/init.py::run_homes``
(``marshal homes``, FR-4/FR-8) adds the registry's fourth real caller and its
own three codes: ``MRS-HOMES-001`` (a discovered home's marker slug, symlink
slug, or branch-derived slug disagree -- the three-way check that closes
``MRS-INIT-003``'s own narrower two-way blind spot named in deferred-work,
scoped to this NEW command only; the SAME code also names the main
checkout's own marker/symlink pair disagreeing, checked by the identical
two-way rule with no branch-derived third leg), ``MRS-HOMES-002`` (a home's
local Tier-3 backlink resolves, BY REALPATH, to a directory other than its
expected canonical store), and ``MRS-HOMES-003`` (a ``git``/filesystem
operation failed while gathering state -- the same "real operation attempted
and did not complete" tier as ``MRS-INIT-004``, not "could not evaluate").
All three classify ``Verdict.ERROR``, following ``MRS-INIT-003/004/005``'s
precedent: a real isolation check ran and found (or could not complete)
a real violation. Story 1.7's ``cli/init.py::run_preflight``
(``marshal preflight``, FR-7/FR-47/FR-52) adds the registry's fifth real
caller and its own ten codes, one per report check plus one shared by two
pre-provisioning gates, plus a pre-I/O slug-shape gate: ``MRS-PREFLIGHT-001``
(the ``bmad-loop`` harness binary is not on ``PATH``), ``MRS-PREFLIGHT-002``
(the harness's ``--version`` is outside the declared ``>=0.9.0,<0.10`` range,
or could not be determined at all), ``MRS-PREFLIGHT-003`` (no multiplexer
backend is available), ``MRS-PREFLIGHT-004`` (the configured adapter cannot
be resolved, or its binary is not on ``PATH``), ``MRS-PREFLIGHT-005`` (the
story feed is missing or unparseable), ``MRS-PREFLIGHT-006`` (a configured
verify command's executable is not on ``PATH``), ``MRS-PREFLIGHT-007``
(``main`` is checked out in more than one worktree, or that could not be
verified), ``MRS-PREFLIGHT-008`` (the configured adapter's first-run
requirement is unacknowledged, OR the acknowledgement state path could not
be resolved, OR a requested acknowledgement could not be recorded -- all
three are "the first-run gate is not satisfiably recorded"), and
``MRS-PREFLIGHT-009`` (a seed-file copy failed, OR the loop-home ROOT could
not be resolved, OR the loop home named on the command line is not
provisioned at all -- the latter two checked before any of the other eight,
sharing this code rather than adding more: each is "a real filesystem
precondition this command needs is not met", the same tier as the seed-copy
failure). All nine
classify ``Verdict.ERROR`` -- a real prerequisite check ran and failed, the
same tier as ``MRS-INIT-003/004/005``/``MRS-HOMES-*``, never "could not
evaluate". ``MRS-PREFLIGHT-010`` (a malformed project slug, checked before
any filesystem read/write -- review finding: an unvalidated slug could
resolve OUTSIDE the loop home via ``..``/an absolute path, and the seed-copy
step would then write real bytes there) classifies ``Verdict.UNEVALUABLE``
instead, mirroring ``MRS-INIT-001``'s own tier for the identical shape check:
a malformed slug means Marshal cannot determine what to preflight, not that
a gate failed. Story 1.8's ``cli/init.py::run_teardown`` (``marshal
teardown``, NFR-6/AD-29) adds the registry's sixth real caller and its own
three codes: ``MRS-TEARDOWN-001`` (a malformed project slug, including a
shape git rejects as a branch-name component -- the same pre-I/O shape gate
``run_init`` already applies, reusing its identical checks rather than a
third slug regex; ``run_preflight`` does not apply this same git-ref-shape
guard today, a pre-existing gap this story surfaced but did not cause),
``MRS-TEARDOWN-002`` (a git operation
failed -- resolving the current working directory or the loop-home root,
resolving worktree/branch state, or the removal itself -- or an on-disk
state git can no longer account for: a deregistered home path that still
exists and was never checked for uncommitted work), and
``MRS-TEARDOWN-003`` (refused: the home has uncommitted changes, the
branch's content is not yet safely captured on ``main``, or the AD-29
promotion-reachability stub names something unreachable -- and ``--force``
was not supplied; the one finding names every triggering condition).
``MRS-TEARDOWN-001`` classifies ``Verdict.UNEVALUABLE`` (Marshal cannot
determine what to tear down), the same tier as ``MRS-INIT-001``/
``MRS-PREFLIGHT-010``'s identical shape check; ``MRS-TEARDOWN-002/003``
classify ``Verdict.ERROR``, the same tier as every other story's
real-operation-attempted-and-did-not-complete codes -- see
``core/verdict.py``. Story 1.9's ``cli/init.py::run_preflight`` (packaging,
FR-52/FR-57) graduates the harness-version check and adds an eleventh
code, ``MRS-PREFLIGHT-011`` (a resolvable, same-major harness version that
lies outside the declared minor range, ``>=0.9.0,<0.10``) -- previously
this state shared ``MRS-PREFLIGHT-002`` with the undeterminable/
major-mismatch case; it is now split into its own code because it does
NOT block: ``MRS-PREFLIGHT-002`` remains for ``harness_version is None``
or a genuine major-version mismatch (``Verdict.ERROR``, blocking,
unchanged), while ``MRS-PREFLIGHT-011`` classifies ``Verdict.WARN``
(non-blocking) -- see ``core/verdict.py``. Story 2.1's ``cli/gate.py``/
``core/gate.py`` (``marshal gate evaluate``, FR-20) add the registry's
seventh real caller and its own five codes: ``MRS-GATE-001`` (a configured
verify command ran and exited non-zero), ``MRS-GATE-002`` (a verify
command's executable could not be launched at all -- surfaced by the
injected ``ProcessPort``, never a pre-flight ``shutil.which`` check),
``MRS-GATE-003`` (a verify command's string could not be ``shlex.split``,
e.g. an unterminated quote), ``MRS-GATE-004`` (``verify_commands`` composed
to the empty tuple -- Marshal's own ``DEFAULT_POLICY`` value, not a
project's declared intent to skip gating), and ``MRS-GATE-005`` (``--run
<id>`` was supplied but no run-journal fold exists yet -- ``core/journal``
is Story 3.1/3.2, both ``backlog``). ``MRS-GATE-001`` classifies
``Verdict.GATE_FAILED`` -- the table's first classification into that rung,
distinct from every prior code's ``Verdict.ERROR``/``Verdict.UNEVALUABLE``
tier: a REAL check ran and failed, not "an internal Marshal operation
failed" or "could not evaluate". ``MRS-GATE-002``/``003``/``005`` classify
``Verdict.UNEVALUABLE`` (Marshal could not run the check at all -- the same
tier as ``MRS-PREFLIGHT-006``'s own verify-command-resolvability code);
``MRS-GATE-004`` classifies ``Verdict.WARN``, the same tier as
``MRS-POLICY-005``/``MRS-PREFLIGHT-011`` -- a legitimate, non-blocking
bootstrap state, never a silent ``clean`` -- see ``core/verdict.py``. Story
2.4's ``core/gate.py::classify_doc_only_declaration`` adds a sixth code,
``MRS-GATE-006`` (the worktree has no changes AND the story was not
declared doc-only -- the one combination indistinguishable from a story
that silently failed to do its work). It classifies ``Verdict.GATE_FAILED``,
the same tier as ``MRS-GATE-001``: a real, determinable outcome (Marshal
evaluated and found nothing produced while no doc-only exemption was
claimed), never "could not evaluate" -- see ``core/verdict.py``. Story
3.2's ``core/journal.py::fold`` adds the registry's eighth real caller and
its own two codes: ``MRS-JOURNAL-001`` (a journal line that failed to
parse as JSON, or parsed but failed one of ``build_entry``'s own shape
invariants) and ``MRS-JOURNAL-002`` (a ``sidecar_ref`` payload whose blob
is missing from the caller-supplied ``sidecars`` mapping, or whose text is
not valid JSON, or whose decoded value is not itself a JSON object). Both
classify ``Verdict.UNEVALUABLE`` (AD-8): a quarantined line's own story key
and decision domain could not be evaluated, never a gate that failed --
see ``core/verdict.py``. Story 3.3's ``cli/spin.py`` (``marshal factory
spin``/``attach``, FR-9/FR-17) adds the registry's ninth real caller and its
own six codes: ``MRS-SPIN-001`` (a malformed project slug, checked before
any I/O -- the same pre-I/O shape gate every sibling command's own
``MRS-INIT-001``/``MRS-PREFLIGHT-010``/``MRS-TEARDOWN-001`` applies),
``MRS-SPIN-002`` (the loop home is not provisioned -- ``fs.is_dir(home)`` is
``False``, its Tier-3 backlink is absent, or that backlink dangles),
``MRS-SPIN-003`` (NO harness process was started, and none can have been --
covers ``spin``'s detached launch, ``run_foreground``'s synchronous one, and
``attach``'s exec failing to launch at all (a missing binary, a launch-time
``OSError``), AND ``run_spin``'s two pre-spawn filesystem setup failures,
creating the run directory and journaling the ``intent``, which abort before
``HarnessPort.spin`` is ever called. Review finding, Blind Hunter: the
earlier wording said "could not be LAUNCHED at all", which was false for
those latter two of its six emit sites. One code serves them all because
they share the property a caller acts on -- nothing is running, so a retry
is safe -- and each site's own message names which one it was), ``MRS-SPIN-004`` (the
harness's own self-minted ``harness_run_id`` could not be recovered within
``spin``'s bounded poll window -- the detached spawn itself still
succeeded), ``MRS-SPIN-005`` (the story feed is missing or unparseable --
``HarnessPort.story_feed_error`` returned non-``None``), and ``MRS-SPIN-006``
(the detached spawn itself SUCCEEDED, but its ``outcome`` entry could not be
journaled -- review finding, Blind Hunter, verified live: this case
originally reused ``MRS-SPIN-003``, conflating "never launched, safe to
retry" with "a live process now exists, unaccounted for in the journal" --
a caller treating either alike as safe-to-retry could double-spawn a second
concurrent run). ``MRS-SPIN-001`` classifies ``Verdict.UNEVALUABLE``, the
same tier as every sibling pre-I/O shape gate: Marshal cannot determine what
to launch. ``MRS-SPIN-002``/``003``/``005`` classify ``Verdict.ERROR``, the
same tier as every other real-precondition-checked-and-failed code
(``MRS-INIT-003/004/005``, ``MRS-PREFLIGHT-001``-``009``,
``MRS-TEARDOWN-002/003``): a real operation was attempted (or a real
precondition was checked) and did not converge, never "could not evaluate".
``MRS-SPIN-004``/``006`` classify ``Verdict.WARN``, the same tier as
``MRS-POLICY-005``/``MRS-PREFLIGHT-011``/``MRS-GATE-004`` -- and, for
``006`` specifically, the SAME tier AD-21's amendment (F-17) already assigns
a lone unclosed journal ``intent`` generally ("an unclosed intent... stays
open and is reported... classifies WARN, not error... escalating it is an
operator decision, never automatic"): a launch that already succeeded is
never re-classified as a failure over a paper-trail gap this codebase's own
architecture already treats as WARN system-wide. A malformed raw feed key
surfaces via the EXISTING ``MRS-IDENT-001`` (``core/identity.py``, already
``Verdict.UNEVALUABLE``) -- no new code was needed for that scenario, per
this story's own spec. Story 3.4's ``cli/spin.py`` (the supervisor's own
process lifecycle, AD-9/AD-20/AD-25) adds a SEVENTH code to the SAME
caller: ``MRS-SPIN-007`` (``ProcessPort.spawn_detached`` raised
``ProcessError`` spawning the supervisor sidecar, after the harness itself
already launched successfully). It classifies ``Verdict.WARN``, the same
tier as ``MRS-SPIN-006`` and for the identical reason: a live,
already-launched process is never re-classified as a failure over a
paper-trail gap -- here "no supervisor is watching this run" rather than
"the outcome entry could not be journaled." Story 3.5's
``supervisor/__main__.py`` (idle-strand detection, AD-9/AD-20) adds the
registry's tenth real caller and a NEW area, ``MRS-SUPV-*``, its own three
codes: ``MRS-SUPV-001`` (the idle ladder's ``nudge`` rung resolved no
window to deliver its text to, or delivery otherwise failed --
``SessionObserverPort.send_text`` returned ``False``), ``MRS-SUPV-002``
(the ``stop-and-retry`` rung's ``HarnessPort.stop``/``.resume`` call
raised ``HarnessError`` -- the tick loop continues watching the
possibly-still-wedged original pid rather than crashing), and
``MRS-SUPV-003`` (the run-launch outcome entry's ``harness_run_id`` field
is unavailable, so the ladder cannot act at all for this run -- journaled
once at attach; the tick loop continues heartbeat-only). All three
classify ``Verdict.WARN``, the same tier as ``MRS-SPIN-004``/``006``/
``007``: each names a DEGRADED-but-still-supervised condition (a nudge that
could not be delivered, a stop-and-retry that could not complete, a ladder
that cannot act at all) over a run that is never itself invalidated by it.
Later stories append further real codes here as they gain their own real
callers. The registry MECHANISM (format check, then membership check) is
separately proven via ``monkeypatch``-injected synthetic codes in
``tests/unit/test_findings.py``.

This module is pure data: no I/O, no subprocess, no network, no clock
(AD-4).
"""

from __future__ import annotations

import re

# No ^/$ anchors -- matched with .fullmatch(), not .match(), so a trailing
# newline can never sneak a malformed code past the check (a known Python
# `re` pitfall: `$` alone matches immediately before a trailing "\n"; see
# pyforge-warden's models.py docstring, which calls out this exact gotcha).
# [0-9], never \d: Python's \d matches any Unicode decimal digit, while the
# packaged JSON schema's ECMA-262 pattern treats \d as [0-9] -- spelling
# [0-9] in both keeps the two independent copies behaviorally identical.
CODE_PATTERN = re.compile(r"MRS-[A-Z][A-Z0-9]*-[0-9]{3}")

# Story 1.2's core/identity.py -- the registry's first real registrations.
# Story 1.3's core/policy.py/cli/config.py add the second real caller's six codes.
# Story 1.4's cli/init.py adds the third real caller's four codes.
# Story 1.5's cli/init.py tier3_backlink step adds a fifth code.
# Story 1.6's cli/init.py::run_homes adds the fourth real caller's three codes.
# Story 1.7's cli/init.py::run_preflight adds the fifth real caller's ten codes.
# Story 1.8's cli/init.py::run_teardown adds the sixth real caller's three codes.
# Story 1.9's cli/init.py::run_preflight adds an eleventh code, graduating
# the harness-version check into two tiers.
# Story 2.1's cli/gate.py/core/gate.py add the seventh real caller's five codes.
# Story 2.4's core/gate.py::classify_doc_only_declaration adds a sixth code.
# Story 3.2's core/journal.py::fold adds the eighth real caller's two codes.
# Story 3.3's cli/spin.py adds the ninth real caller's SIX codes (MRS-SPIN-006
# joined 001-005 in review, splitting "launched but its outcome could not be
# journaled" off MRS-SPIN-003's "never launched, safe to retry").
# Story 3.4's cli/spin.py adds a SEVENTH code to the same caller,
# MRS-SPIN-007 (the supervisor sidecar could not be spawned).
# Story 3.5's supervisor/__main__.py adds the tenth real caller's own NEW
# area, MRS-SUPV-* (three codes: nudge-send failure, stop/resume failure,
# harness-run-id-unavailable).
REGISTERED_CODES: frozenset[str] = frozenset(
    {
        "MRS-IDENT-001",
        "MRS-IDENT-002",
        "MRS-POLICY-001",
        "MRS-POLICY-002",
        "MRS-POLICY-003",
        "MRS-POLICY-004",
        "MRS-POLICY-005",
        "MRS-POLICY-006",
        "MRS-INIT-001",
        "MRS-INIT-002",
        "MRS-INIT-003",
        "MRS-INIT-004",
        "MRS-INIT-005",
        "MRS-HOMES-001",
        "MRS-HOMES-002",
        "MRS-HOMES-003",
        "MRS-PREFLIGHT-001",
        "MRS-PREFLIGHT-002",
        "MRS-PREFLIGHT-003",
        "MRS-PREFLIGHT-004",
        "MRS-PREFLIGHT-005",
        "MRS-PREFLIGHT-006",
        "MRS-PREFLIGHT-007",
        "MRS-PREFLIGHT-008",
        "MRS-PREFLIGHT-009",
        "MRS-PREFLIGHT-010",
        "MRS-PREFLIGHT-011",
        "MRS-TEARDOWN-001",
        "MRS-TEARDOWN-002",
        "MRS-TEARDOWN-003",
        "MRS-GATE-001",
        "MRS-GATE-002",
        "MRS-GATE-003",
        "MRS-GATE-004",
        "MRS-GATE-005",
        "MRS-GATE-006",
        "MRS-JOURNAL-001",
        "MRS-JOURNAL-002",
        "MRS-SPIN-001",
        "MRS-SPIN-002",
        "MRS-SPIN-003",
        "MRS-SPIN-004",
        "MRS-SPIN-005",
        "MRS-SPIN-006",
        "MRS-SPIN-007",
        "MRS-SUPV-001",
        "MRS-SUPV-002",
        "MRS-SUPV-003",
    }
)


class UnregisteredFindingCodeError(ValueError):
    """Raised when a ``Finding`` is constructed with a code that either does
    not match ``CODE_PATTERN`` or is not a member of ``REGISTERED_CODES``."""


def require_registered(code: str) -> str:
    """Return ``code`` unchanged if it is well-formed AND registered; raise
    ``UnregisteredFindingCodeError`` otherwise. Format is checked first -- a
    malformed code fails before the membership check ever runs."""
    if not CODE_PATTERN.fullmatch(code):
        raise UnregisteredFindingCodeError(
            f"malformed finding code {code!r} -- expected MRS-<AREA>-<NNN>"
        )
    if code not in REGISTERED_CODES:
        raise UnregisteredFindingCodeError(
            f"unregistered finding code {code!r} -- not in REGISTERED_CODES"
        )
    return code
