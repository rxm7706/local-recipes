"""THE ONLY module permitted to invoke the ``bmad-loop`` harness binary,
import its package, read its policy file, or parse its output (AD-3) --
enforced by an ``import-linter`` "forbidden" contract in ``pyproject.toml``.

Story 1.10 (AD-10/AD-12/AD-35, FR-49/50/51) gives this module its first real
job: rendering the harness's ``.bmad-loop/policy.toml`` from Marshal's own
composed ``EffectivePolicy`` (Story 1.3, ``core/policy.py``). ``bmad-loop``
0.9.0 hard-codes ``POLICY_FILE = .bmad-loop/policy.toml`` with no
policy-path flag, and that file was git-tracked and hand-edited per loop
home -- the F-1 cross-project bleed where one loop home's edit rode
``git push origin HEAD:main`` onto every other project. ``render_policy_toml``
and ``write_policy_toml`` close that hazard structurally: the file becomes a
DERIVED artifact (AD-12) -- always rendered whole from the canonical
policy, never patched or hand-edited, and (as of this story) gitignored so
it can never again ride a commit onto another project.

``_POLICY_TEMPLATE`` is a vendored, project-agnostic default ``policy.toml``
covering every section of the installed ``bmad_loop`` 0.9.0 schema at stock
defaults -- but deliberately NOT its every key: instance-local keys the
harness itself persists into a live policy.toml (the ``[tui]``
pane-geometry keys, the ``[mux].backend`` line written by
``bmad-loop mux set``), reserved or per-profile knobs that fall back
correctly when absent (``gates.on_escalation``, adapter/stage
``usage_grace_s`` / ``stop_without_result_nudges`` / ``extra_args``), and
dynamic per-plugin sub-tables are all omitted, and the harness applies its
own default for any absent key. The template was verified once against the
installed package's own ``policy.py`` (its dataclasses and its own
``POLICY_TEMPLATE`` constant) rather than imported at runtime -- importing
``bmad_loop`` is permitted by this module's own seam but not required by this
story's ACs, and would force an unrelated root ``pixi.lock`` re-solve (Story
1.9 owns declaring ``bmad-loop`` as a real dependency). Placeholder baselines
in this template are overwritten by ``render_policy_toml()`` from Marshal's
composed ``EffectivePolicy`` (the 4-layer fold: code DEFAULT_POLICY -> repo
defaults from `_bmad-output/policy-defaults.toml` -> project layer from
marshal-policy.toml -> invocation --set flags). The 6 hardcoded template
constants ``review.trigger``, ``scm.isolation``, ``scm.merge_strategy``,
``scm.rollback_on_failure``, ``limits.session_timeout_min``, and the
baseline ``[adapter].model``/``[adapter.review].model`` pair are repo-wide
overrides verified by diffing against stock defaults -- these are the ONLY
keys edited directly in this constant; changing them requires editing this
file, not a rendered .bmad-loop/policy.toml. All other Marshal-composed keys
(``gate_mode``, ``max_followup_reviews``, etc.) flow through
``EffectivePolicy`` composition and are rendered by Story 1.10.

``frozen_surfaces`` and ``merge_subject_template`` -- 2 of Marshal's 9
composed policy keys -- are deliberately NOT rendered here: neither has a
real ``bmad_loop`` policy.toml counterpart (confirmed against the installed
0.9.0 schema -- no ``frozen`` key anywhere, and ``scm.commit_message_template``
governs the per-story dev-session commit, not the landing merge subject,
which ``bmad_loop`` hardcodes unconditionally). Both stay Marshal-internal,
consumed by ``core/gate``/``core/identity`` in later stories, not by the
harness.

Story 1.7 (AD-3/AD-19, FR-7/FR-52) closes the "reserved for a later story"
gap above: ``BmadLoopHarness`` (``ports.HarnessPort``'s sole implementation)
resolves and invokes the ``bmad-loop`` binary (``--version`` only -- never
the adapter's own CLI, which could itself trigger the first-run dialog
``marshal preflight`` exists to gate ahead of time) and lazily imports
``bmad_loop.adapters.multiplexer``/``bmad_loop.adapters.profile``/
``bmad_loop.bmadconfig``/``bmad_loop.sprintstatus`` -- one import per method,
inside the method body, never at module top level, so ``marshal config``/
``marshal init``/``marshal homes`` keep working even if the installed
``bmad_loop`` is broken or absent, and so ``ImportError``/the harness's own
typed errors (``ProfileError``, ``MultiplexerError``, ``BmadConfigError``,
``SprintStatusError``) never escape this module raw -- every one is caught
and re-raised as ``HarnessError``, except in the three methods documented to
never raise, which degrade instead: ``binary_present`` (a pure
``shutil.which`` check, no failure mode), ``harness_version`` (``None``),
and ``story_feed_error`` (the error TEXT is the return value; ``None`` means
success).
``bmad-loop`` is now a declared runtime dependency (``pyproject.toml``,
``pixi.toml``) -- see those files' own comments for why the range is
``>=0.9.0,<0.10``.

Story 1.9 (packaging, FR-52) gives this module its declared-range job:
``_HARNESS_MIN_VERSION``/``_HARNESS_MAX_MINOR_EXCLUSIVE``/
``HARNESS_VERSION_RANGE_TEXT`` and the public ``harness_version_tuple``/
``harness_version_in_range`` functions relocate here from ``cli/init.py``
(which defined its own copy when Story 1.7 first needed one). Both
``cli/init.py``'s ``run_preflight`` and ``cli/main.py``'s ``--version``
import ``harness_version_in_range``, ``harness_version_tuple``, and
``HARNESS_VERSION_RANGE_TEXT`` -- each name directly (a constant is never
available "through" a function import) -- for their own out-of-range and
could-not-be-parsed wording. The new
``harness_version_is_major_mismatch`` function is ``run_preflight``'s
alone -- it is what lets that command split "undeterminable or a different
major version" (still blocking) from "a determinable, same-major version
outside the declared minor range" (now a non-blocking warning); see that
call site's own docstring for how it uses the split. ``--version`` has no
blocking tier at all -- it only ever prints warning lines, since it never
blocks (informational, not a gate).

Story 3.3 (``marshal factory spin``/``attach``, FR-9/FR-17, AD-3/AD-22/
AD-25/AD-38) gives this module its first job that actually LAUNCHES a real
``bmad-loop`` process rather than only probing or configuring one:
``story_feed_keys`` (the raw, pre-parse population of story references --
``sprintstatus.SprintStatus.stories[*].key`` UNION ``unknown_keys``, file
order), ``spin`` (the ONE detached-launch primitive -- ``subprocess.Popen``
with ``start_new_session=True``, closed stdin, both streams redirected to a
caller-given log path, never waited on), ``attach`` (execs ``bmad-loop
attach``, inheriting this process's own stdio, blocking until it exits),
and ``run_foreground`` (the ``--foreground`` counterpart to ``spin`` --
``bmad-loop run`` inheriting stdio synchronously, beyond the spec's own
literal three-method Code Map enumeration for the reason ``ports/harness.py``'s
own docstring gives). ``spin``/``attach``/``run_foreground`` are the ONLY
methods on this class that raise ``HarnessError`` for a plain launch
failure (mirrors ``ports/process.py::ProcessPort.run``'s "a non-zero exit is
the ordinary shape, a launch failure is the exceptional one" split) rather
than degrading or raising for a wider failure class -- every prior method
on this class either never raises (``binary_present``, ``harness_version``,
``story_feed_error``) or raises for "unimportable/unresolvable", a
categorically different condition from "the OS could not start this
process".

Story 3.5 (idle-strand detection, AD-9/AD-20) adds ``stop``/``resume`` --
the supervisor's own ``stop-and-retry`` ladder rung, confirmed live as the
one intended pairing for recovering an unresponsive engine (never a bare
re-``bmad-loop run``, which mints an unrelated run id with no in-flight
lock and would double-dispatch): ``stop`` runs ``["bmad-loop", "stop",
run_id]`` SYNCHRONOUSLY (mirrors ``attach``'s captured-output shape, not
``spin``'s detached one -- a hard stop is a quick, bounded operation, never
a long-running engine loop) and returns whether it actually stopped a live
run; ``resume`` detach-launches ``["bmad-loop", "resume", run_id]``
(mirrors ``spin``'s own recipe exactly -- a resumed engine run is
synchronous and unbounded in the child, exactly like a fresh ``bmad-loop
run``) and returns the new pid. Both join ``spin``/``attach``/
``run_foreground`` as the only methods on this class raising
``HarnessError`` for a plain launch failure.

Story 3.6 (budget ceilings, AD-9/AD-32, FR-13) adds ``usage_snapshot`` -- the
first method on this class that reads ``bmad_loop``'s own PER-RUN state
(``<project>/.bmad-loop/runs/<run_id>/state.json``, never a project-wide
file) rather than its packaged profile/config surface. Lazily imports
``bmad_loop.journal.load_state`` (the SAME "one import per method, inside
the method body" discipline every other method on this class already
follows), finds the sole ``StoryTask`` with ``not task.terminal`` (zero or
more than one such task yields ``story_key=None`` -- ``UsageSnapshot``'s own
"no single current story" shape), and computes each weighted total via
``TokenUsage.weighted_total(state.cache_read_weight())`` -- bmad-loop's OWN
cost-proportional metric, already computed by the installed harness for its
own in-session budget guard (the ``[limits]`` block this module's
``_POLICY_TEMPLATE`` above renders, deliberately never widened or
duplicated by this story -- see the spec's own Never clause). Joins
``story_feed_error``/``harness_version``/``binary_present`` as a method that
NEVER raises: ``(OSError, ValueError, KeyError, TypeError)`` covers every
plausible read/parse failure (a missing file, malformed JSON, a missing or
wrong-typed field), and all of them degrade to ``None`` rather than
propagating -- this is a supplementary, best-effort reporting input (AD-32),
never a precondition an enforcement ceiling can block on.

Story 3.7 (escalation, deferral, and resume, AD-9/AD-45, FR-15/16/17) adds
``run_status_snapshot``/``resolution_reference``. ``run_status_snapshot``
reads the SAME ``state.json`` ``usage_snapshot`` reads (the identical lazy
``bmad_loop.journal.load_state`` import, the identical widened
``(OSError, ValueError, KeyError, TypeError, AttributeError,
ArithmeticError, RecursionError)`` guard -- reused verbatim, not re-derived
narrower, per this story's own Always bullet), collecting the run-level
pause fields plus every ``Phase.DEFERRED`` task. ``paused_reason`` and each
deferred task's own ``defer_reason`` are redacted at capture (AD-34), via
the SAME ``to_redacted({"k": text}); json.loads(redacted.text)["k"]``
wrap/unwrap round-trip ``adapters/observer_mux.py::pane_content`` already
established for this same purpose -- a per-field, narrowly-guarded helper
(``(ValueError, LookupError, TypeError)``) so one field's redaction failure
degrades only that field to ``None``, never the whole snapshot.
``resolution_reference`` lazily imports ``bmad_loop.resolve.
resolution_path`` -- AD-3 confines every ``bmad_loop`` import to this one
module, so this is the seam ``cli/spin.py``'s ``marshal factory resume``
must call through rather than importing ``bmad_loop.resolve`` itself (the
spec's own intent-contract literally names a direct import site in
``cli/spin.py`` -- a genuine inaccuracy about this package's own AD-3
import-linter contract, recorded in the spec's Spec Change Log and
corrected here).

Story 3.8 (stage-bound durability, AD-46/FR-61) widens
``run_status_snapshot`` rather than adding a new method: the SAME per-task
loop that already builds ``deferred`` also builds ``tasks`` --
``TaskPhaseSnapshot(story_key, phase, commit_sha)`` for EVERY task in
``state.tasks``, not only the ``Phase.DEFERRED`` ones. No new import, no new
guard: this reuses the identical widened exception tuple and the identical
lazy ``bmad_loop.journal.load_state`` seam Story 3.7 already established.
``commit_sha`` carries no redaction (a commit hash is never session-derived
free text).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

import tomlkit

from ..core import policy
from ..core.egress import to_redacted
from ..ports.harness import (
    AdapterProbe,
    DeferredStory,
    RunStatusSnapshot,
    SmokeRunResult,
    SpinResult,
    TaskPhaseSnapshot,
    UsageSnapshot,
)

# --- the vendored, project-agnostic harness policy template ----------------
#
# Covers every section of the installed bmad_loop 0.9.0 schema at its own
# stock default (deliberately not every key -- the module docstring names
# the omitted instance-local/reserved ones). Keys that are rendered from
# Marshal's EffectivePolicy composition (the 4-layer fold: code DEFAULT_POLICY
# -> repo-defaults from `_bmad-output/policy-defaults.toml` -> project-layer
# from marshal-policy.toml -> invocation --set flags) carry placeholder
# baselines here -- render_policy_toml() always overwrites them, so their
# template value never reaches a caller. These include gates.mode,
# max_dev_attempts/.max_review_cycles/.max_followup_reviews, verify.commands,
# and scm.worktree_seed.
_POLICY_TEMPLATE = """\
# bmad-loop orchestration policy -- the harness's own vocabulary (bmad_loop
# 0.9.0). This file is a DERIVED artifact: Marshal renders it whole from the
# canonical EffectivePolicy every time it is written. Never hand-edit it --
# a per-project setting belongs in Marshal's own policy source, and a
# repo-wide default belongs in this template (adapters/harness_bmadloop.py's
# _POLICY_TEMPLATE), never in this rendered file. All keys optional; the
# harness applies its own stock default for anything absent.

[gates]
mode = "per-epic"            # none | per-epic | per-story-spec-approval -- overwritten per render from EffectivePolicy
retrospective = "notify"     # never | notify | auto (auto unsupported in v1)

[limits]
max_review_cycles = 3        # overwritten per render from EffectivePolicy
max_dev_attempts = 2         # overwritten per render from EffectivePolicy
max_followup_reviews = 1     # overwritten per render from EffectivePolicy
session_timeout_min = 180    # repo-wide override (stock default: 90) -- keystone stories need the headroom
git_timeout_s = 120
teardown_grace_s = 20
stop_without_result_nudges = 1
dev_stall_grace_s = 600
dev_stall_nudges = 2
dev_stall_nudges_cap = 6
workflow_stall_nudges_cap = 3
max_tokens_per_story = 2000000
cache_read_weight = 0.1
session_budget_mode = "warn"  # off | warn | enforce
max_tokens_per_session = 4000000
session_budget_grace_s = 240

[verify]
commands = []                 # overwritten per render from EffectivePolicy

[notify]
desktop = true
file = true

[review]
enabled = true
# repo-wide override, stock default: "recommended" (2026-08-02: switched back to
# stock from "always" -- operator call, paired with raising [adapter.review].model
# to opus: fewer review passes, stronger when they happen. Trusts the dev pass's
# own self-assessment of whether it needs review -- the exact self-grading "always"
# existed to not depend on; revisit if that trust turns out to be misplaced.
trigger = "recommended"       # recommended | always

[stories]
source = "sprint-status"      # sprint-status | stories
spec_folder = ""

[dev]
skill = "bmad-dev-auto"

[adapter]
name = "claude"               # claude | codex | gemini | copilot | antigravity | opencode-http | <custom .bmad-loop/profiles/*.toml>
model = "sonnet"               # repo-wide override (stock default: "" = CLI default model). 2026-08-02: briefly opus, reverted same day (operator token-budget call) -- dev stays sonnet, review alone carries the opus raise (see [adapter.review]).
cleanup_session_on_finish = true
# extra_args replaces the profile's default permission-bypass flags when set:
# extra_args = ["--permission-mode", "bypassPermissions"]

# Per-stage overrides for the dev, review and sweep-triage passes. Unset
# keys inherit from [adapter] when the stage runs the same client.
# [adapter.dev] and [adapter.triage] are intentionally absent here -- FR-51
# tier-batching writes a stage's table in only when that stage is present
# in the resolved difficulty's model map; an absent stage inherits
# [adapter].model.
[adapter.review]
model = "opus"                 # repo-wide override -- review misses ship false-greens; strongest model where it pays

[sweep]
auto = "never"                 # never | per-epic | run-end
max_bundles = 5
max_triage_attempts = 2
max_migration_attempts = 2
repeat = false
max_cycles = 5

[cleanup]
run_retention = 10
retention_days = 0
trim_artifacts = true
archive_old = true
auto_clean_on_finish = true
clean_tmp = true

[scm]
isolation = "worktree"         # repo-wide override (stock default: "none") -- the per-story-branch workflow every loop home depends on
branch_per = "story"           # story | run
target_branch = ""
merge_strategy = "squash"      # repo-wide override (stock default: "merge")
delete_branch = true
keep_failed = true
rollback_on_failure = true     # repo-wide override (stock default: false)
preserve_keep = 20
failed_diff_max_mb = 5
failed_diff_unlimited = false
commit_message_template = ""
max_parallel = 1
seed_adapter_defaults = true
worktree_seed = []             # overwritten per render from EffectivePolicy

[plugins]
enabled = []

[tui]
low_frame_rate = false

[mux]
# backend = "tmux"
"""

_ADAPTER_STAGES: tuple[str, ...] = ("dev", "review", "triage")


def render_policy_toml(
    effective: policy.EffectivePolicy,
    *,
    difficulty: str | None = None,
    adapter: str | None = None,
) -> str:
    """Pure string builder (no I/O): parse ``_POLICY_TEMPLATE``, overwrite
    Marshal's 6 mapped keys from ``effective``, apply FR-51 tier-batching,
    and return ``tomlkit.dumps(...)``. Identical ``(effective, difficulty)``
    produces byte-identical output (AD-12/AD-35 "derived artifact"
    discipline).

    The 6 mapped keys: ``gate_mode`` -> ``[gates].mode``,
    ``max_dev_attempts``/``max_review_cycles``/``max_followup_reviews`` ->
    ``[limits]``'s same-named keys (all four SEED fields, read exclusively
    via ``seed_view()`` per AD-26), ``verify_commands`` -> ``[verify].commands``,
    ``worktree_seed_paths`` -> ``[scm].worktree_seed`` (both STATIC fields).
    Seed fields carry the INITIAL composed values: during a live run the
    operative value of a seed field (``gate_mode`` above all) comes solely
    from the journal fold (AD-26), so a mid-run re-render reproduces
    run-START state, never the live one.

    FR-51 tier-batching: when ``difficulty`` is given and is a key of
    ``effective.model_tier_map.value``, each of ``dev``/``review``/``triage``
    present in that difficulty's stage map gets ``[adapter.<stage>].model``
    set to the mapped model name; a stage absent from the map (or
    ``difficulty`` being ``None``/unknown) keeps the template's baseline --
    no override table is written for it. Never an error: resolving which
    difficulty applies to a story/batch is a later story's concern.

    Raises ``ValueError`` when ``max_dev_attempts`` or ``max_review_cycles``
    is 0: Marshal's own composition permits 0, but ``bmad_loop`` 0.9.0
    rejects either key < 1 at policy load, so rendering it would produce a
    file that bricks the loop home's next run (``max_followup_reviews = 0``
    is legal on both sides and renders fine). A plain exception, not an
    ``MRS-*`` finding -- no CLI caller exists yet to convert one.

    ``adapter`` (Story 6.5, FR-44): when given, overwrites ``[adapter].name``
    -- the template's own hardcoded ``"claude"`` baseline is otherwise NEVER
    derived from ``effective`` (confirmed live: no existing composed field
    names the configured adapter at all). Mirrors ``difficulty``'s own
    additive, backward-compatible keyword shape; every existing caller that
    never passes it renders byte-identically unaffected. Applied
    independently of ``difficulty``'s own tier-batching (which touches only
    ``[adapter.<stage>].model`` sub-tables, never ``[adapter].name``).
    """
    doc = tomlkit.parse(_POLICY_TEMPLATE)

    seed = effective.seed_view()
    # bmad_loop 0.9.0's load-time floor is stricter than Marshal's own
    # composition for exactly these two keys (its loader raises PolicyError
    # on limits.max_review_cycles/.max_dev_attempts < 1, while Marshal's
    # _valid_attempt_count accepts 0; max_followup_reviews >= 0 is legal on
    # both sides). Refuse at the projection boundary rather than write a
    # file the harness rejects wholesale at next run start.
    for key in ("max_dev_attempts", "max_review_cycles"):
        if seed[key].value < 1:
            raise ValueError(
                f"cannot render policy.toml: {key}={seed[key].value}, but "
                f"bmad-loop 0.9.0 rejects limits.{key} < 1 at policy load"
            )
    doc["gates"]["mode"] = seed["gate_mode"].value
    doc["limits"]["max_dev_attempts"] = seed["max_dev_attempts"].value
    doc["limits"]["max_review_cycles"] = seed["max_review_cycles"].value
    doc["limits"]["max_followup_reviews"] = seed["max_followup_reviews"].value
    doc["verify"]["commands"] = list(effective.verify_commands.value)
    doc["scm"]["worktree_seed"] = list(effective.worktree_seed_paths.value)

    if adapter is not None:
        doc["adapter"]["name"] = adapter

    tier_map = effective.model_tier_map.value
    if difficulty is not None and difficulty in tier_map:
        stage_models = tier_map[difficulty]
        adapter_table = doc["adapter"]
        for stage in _ADAPTER_STAGES:
            if stage not in stage_models:
                continue
            if stage not in adapter_table:
                adapter_table[stage] = tomlkit.table()
            adapter_table[stage]["model"] = stage_models[stage]

    return tomlkit.dumps(doc)


class HarnessPolicyWriteError(Exception):
    """Raised by ``write_policy_toml`` when the atomic write to
    ``<loop_home>/.bmad-loop/policy.toml`` fails (an unwritable loop home, a
    non-directory occupying ``.bmad-loop``, or any other ``OSError`` during
    the temp-file-then-``os.replace`` sequence). No ``MRS-*`` finding code is
    registered for this -- there is no CLI caller yet to convert an I/O
    failure into a ``Finding`` (that is a later story's concern); a plain
    exception is sufficient until one exists.
    """


def write_policy_toml(
    effective: policy.EffectivePolicy,
    loop_home: Path,
    *,
    difficulty: str | None = None,
    adapter: str | None = None,
) -> Path:
    """The I/O boundary: render via ``render_policy_toml`` and atomically
    write ``<loop_home>/.bmad-loop/policy.toml`` whole, mirroring
    ``cli/config.py::materialize``'s temp-file-then-``os.replace`` mechanics
    -- MINUS its write-once/content-hash/no-op logic, since this artifact is
    a fresh projection on every call, never content-addressed, never skipped.
    Never reads an existing file at that path first: every call fully
    replaces any prior content, including hand-edited or unrelated bytes.
    Creates ``<loop_home>/.bmad-loop`` if it does not already exist. Any
    ``OSError`` during the sequence is wrapped in ``HarnessPolicyWriteError``
    rather than propagating raw.

    Like ``cli/config.py::materialize``, THE CALLER owns the gate deciding
    whether a given composition may be persisted at all (e.g. only
    OK-status compositions) -- this function writes whatever
    ``EffectivePolicy`` it is handed, subject only to
    ``render_policy_toml``'s own attempt-count floor.

    ``adapter`` (Story 6.5, FR-44) passes straight through to
    ``render_policy_toml``.
    """
    text = render_policy_toml(effective, difficulty=difficulty, adapter=adapter)
    bmad_loop_dir = Path(loop_home) / ".bmad-loop"
    try:
        bmad_loop_dir.mkdir(parents=True, exist_ok=True)
        target_path = bmad_loop_dir / "policy.toml"
        # pid+thread-id suffixed, O_EXCL-guarded, no pre-unlink -- the same
        # collision-safety reasoning as cli/config.py::materialize's own temp
        # file (see that function's comment for the full rationale).
        tmp_path = bmad_loop_dir / (
            f".policy.toml.pid{os.getpid()}.t{threading.get_native_id()}.tmp"
        )
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(text.encode("utf-8"))
            os.replace(tmp_path, target_path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise
        return target_path
    except OSError as exc:
        raise HarnessPolicyWriteError(
            f"cannot write policy.toml to {bmad_loop_dir}: {exc}"
        ) from exc


# =====================================================================
# Harness version range (Story 1.9, FR-52: "the seam declares the harness
# version range it supports"). Relocated here from ``cli/init.py``, which
# defined its own copy when Story 1.7 first needed it for
# ``run_preflight`` -- moving it into the seam itself means
# ``cli/init.py``'s ``run_preflight`` and ``cli/main.py``'s ``--version``
# share ONE source of truth instead of a second copy that could drift out
# of sync with the ``pyproject.toml``/``pixi.toml`` pin these constants
# mirror. Pure (no I/O, no ``bmad_loop`` import) -- placed ABOVE the
# ``BmadLoopHarness`` section boundary below rather than inside it.
#
# The declared supported harness range: pre-1.0, so the upper bound
# excludes a minor bump that could rename/remove any of the ``bmad_loop``
# modules this module reads. Tuple comparison, not the ``packaging``
# library -- this package has no dependency on it and the range is a
# fixed, simple two-point interval.
_HARNESS_MIN_VERSION: tuple[int, ...] = (0, 9, 0)
_HARNESS_MAX_MINOR_EXCLUSIVE: tuple[int, ...] = (0, 10)
HARNESS_VERSION_RANGE_TEXT = ">=0.9.0,<0.10"


def harness_version_tuple(text: str) -> tuple[int, ...] | None:
    """Parse a dotted version string's leading numeric run per component
    (``"0.9.0"`` -> ``(0, 9, 0)``, ``"0.9.0rc1"`` -> ``(0, 9, 0)``, stopping
    at the first component with no leading digit). ``None`` if the FIRST
    component carries no digits at all. Public (Story 1.9 -- renamed from
    the private ``_version_tuple`` this replaces, since ``harness_version_in_range``
    and ``harness_version_is_major_mismatch``, both cross-module callers'
    entry points into this parsing, now live outside ``cli/init.py``
    alongside it)."""
    parts: list[int] = []
    for chunk in text.split("."):
        digits = ""
        for char in chunk:
            # ASCII-only, not str.isdigit(): isdigit() accepts Unicode
            # digit characters (e.g. "²") that int() then rejects with
            # ValueError -- an uncaught crash escaping the frozen exit-code
            # domain, for input this function does not control (it parses
            # ``bmad-loop --version``'s stdout). Review-caught, reproduced
            # live.
            if not ("0" <= char <= "9"):
                break
            digits += char
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts) if parts else None


def harness_version_in_range(text: str) -> bool:
    """``True`` iff ``text`` parses and falls within
    ``[_HARNESS_MIN_VERSION, _HARNESS_MAX_MINOR_EXCLUSIVE)``. Public (Story
    1.9 -- renamed from the private ``_harness_version_in_range`` this
    replaces)."""
    parsed = harness_version_tuple(text)
    if parsed is None:
        return False
    padded = parsed + (0, 0, 0)
    return padded[:3] >= _HARNESS_MIN_VERSION and padded[:2] < _HARNESS_MAX_MINOR_EXCLUSIVE


def harness_version_is_major_mismatch(text: str | None) -> bool:
    """Story 1.9's graduated-tier split (FR-57): ``True`` for ``None`` or
    unparseable ``text``, or a parsed version whose MAJOR component (the
    first element of ``harness_version_tuple``'s result) differs from
    ``_HARNESS_MIN_VERSION[0]`` -- these are exactly the cases
    ``cli/init.py``'s ``run_preflight`` still BLOCKS on, via
    ``MRS-PREFLIGHT-002``. ``False`` for any other determinable version,
    including one that is same-major but outside the declared minor range
    -- that case now warns via the new ``MRS-PREFLIGHT-011`` instead,
    non-blocking (see ``cli/init.py``'s own docstring)."""
    if text is None:
        return True
    parsed = harness_version_tuple(text)
    if parsed is None:
        return True
    return parsed[0] != _HARNESS_MIN_VERSION[0]


# =====================================================================
# ``BmadLoopHarness`` (Story 1.7) -- ``ports.HarnessPort``'s sole
# implementation. Everything below this line is the only code in this
# package that imports ``bmad_loop`` for anything beyond rendering
# ``policy.toml`` (AD-3).
# =====================================================================

# A quick `--version` call, not a checkout-populating operation like
# `vcs_git.py`'s `_GIT_CHECKOUT_TIMEOUT_S` tier -- NFR-14's 10s preflight
# budget has no room for a generous timeout here, so this must sit WELL
# BELOW that budget (review finding: this was 10.0, the entire budget --
# a hung binary alone exhausted it before the other checks even started).
# A healthy argparse `action="version"` responds in milliseconds.
_VERSION_TIMEOUT_S = 5.0

# Story 3.3's `spin` -- a BOUNDED, best-effort poll for the harness's own
# self-minted run id, never an indefinite wait (the spec's own Never
# clause: "do not block indefinitely waiting for harness_run_id"). "A few
# seconds" per the spec's Always bullet; short enough that a caller's own
# CLI invocation still "returns promptly" (AD-22) even in the degrading
# case where the window elapses with no match.
_SPIN_LOG_POLL_INTERVAL_S = 0.2
_SPIN_LOG_POLL_TIMEOUT_S = 5.0

# `bmad-loop run`'s own `cmd_run` prints exactly this line to stdout the
# instant a run starts (verified live against the installed 0.9.0 `cli.py`:
# `print(f"run {run_id} starting (attach: bmad-loop attach)")`) -- the ONE
# text this module is permitted to parse (AD-3), matched with `.match()`
# (anchors at line start) against each line of `spin`'s own redirected log.
_RUN_STARTING_RE = re.compile(r"^run (\S+) starting\b")

# Story 3.5's `stop` -- a synchronous SIGTERM-then-force-kill against a
# possibly-wedged engine plus its tmux session teardown, confirmed live
# against the installed 0.9.0 `cmd_stop`/`runs.stop_run`. Bounded rather than
# unbounded (unlike `_VERSION_TIMEOUT_S`'s tight preflight budget, this call
# has no shared budget to protect, but an unresponsive `bmad-loop` binary
# must still degrade to a reported failure rather than hang the supervisor's
# own tick loop indefinitely).
_STOP_TIMEOUT_S = 30.0

# Story 6.4's `adapter_probe` -- `bmad-loop probe-adapter --json`'s own
# default SCAN mode is documented (confirmed live against the installed
# 0.9.0 `bmad_loop/probe.py` module docstring) as "zero process launch
# beyond `--version`/`--help`", so this sits well above `_VERSION_TIMEOUT_S`
# (a single `--version` call) without approaching `--probe` mode's own
# interactive, tmux-launching budget -- which this story never invokes at
# all (see the spec's own Boundaries & Constraints).
_PROBE_TIMEOUT_S = 30.0

# Story 6.4 (FR-43) -- the curated, read-only subset of the resolved
# `CLIProfile`'s own already-declared fields this story reports as an
# adapter's "declared capabilities" (the AC's own phrasing; `CLIProfile` has
# no literal `capabilities` attribute -- see the spec's Design Notes for
# why each of these five, and no others, was chosen).
def _profile_capabilities(profile: object) -> dict[str, object]:
    return {
        "hookless": profile.hookless,
        "hook_dialect": profile.hooks.dialect,
        "usage_parser": profile.usage_parser,
        "skill_tree": profile.skill_tree,
        "model_flag": profile.model_flag,
    }


class HarnessError(Exception):
    """Raised by ``BmadLoopHarness`` methods that are documented to raise
    (``multiplexer_backend_available``, ``adapter_binary``,
    ``adapter_seed_files``, ``adapter_first_run_note``) when the lazy
    ``bmad_loop`` import fails, or the harness's own typed error
    (``ProfileError``, a ``bmad_loop.adapters.multiplexer.MultiplexerError``)
    is raised. Never a raw ``ImportError``/harness-internal exception type --
    ``cli/init.py`` only ever needs to catch this ONE class (AD-3's own
    seam: nothing outside this module names a ``bmad_loop`` exception
    type)."""


def _run(args: list[str], *, timeout_s: float = _VERSION_TIMEOUT_S) -> subprocess.CompletedProcess[str] | None:
    """Mirrors ``vcs_git.py``'s ``_run``: same ``encoding="utf-8"``/
    ``errors="replace"`` decode discipline. Unlike that module's version,
    every failure mode here (missing binary, launch failure, a hung
    process) degrades to ``None`` rather than raising -- ``harness_version``
    is documented to never raise, so there is no typed exception for a
    caller to catch."""
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


class BmadLoopHarness:
    """``ports.HarnessPort``'s sole implementation."""

    def binary_present(self, binary: str) -> bool:
        return shutil.which(binary) is not None

    def harness_version(self) -> str | None:
        result = _run(["bmad-loop", "--version"])
        if result is None or result.returncode != 0:
            return None
        # argparse's `action="version"` prints "bmad-loop 0.9.0" to stdout --
        # the version is the token after the last space.
        text = result.stdout.strip()
        _prog, _sep, version = text.rpartition(" ")
        return version or None

    def multiplexer_backend_available(self) -> tuple[str, bool]:
        try:
            from bmad_loop.adapters.multiplexer import (
                MultiplexerError,
                detect_multiplexers,
            )
        except ImportError as exc:
            raise HarnessError(f"bmad_loop is not importable: {exc}") from exc
        # detect_multiplexers documents "never raises", but this module's own
        # contract ("no bmad_loop exception type escapes raw") must not rest
        # on an upstream promise -- catch its seam-level error type anyway
        # (review finding: HarnessError's docstring named MultiplexerError as
        # caught while nothing actually caught it).
        try:
            rows = detect_multiplexers()
        except MultiplexerError as exc:
            raise HarnessError(f"multiplexer detection failed: {exc}") from exc
        selected = next((row for row in rows if row.selected), None)
        if selected is None:
            return "", False
        return selected.name, selected.available

    def _get_profile(self, adapter_name: str, project: Path):
        try:
            from bmad_loop.adapters.profile import ProfileError, get_profile
        except ImportError as exc:
            raise HarnessError(f"bmad_loop is not importable: {exc}") from exc
        try:
            return get_profile(adapter_name, project=project)
        except ProfileError as exc:
            raise HarnessError(str(exc)) from exc
        # get_profile reads a project-local `.bmad-loop/profiles/*.toml`
        # overlay via plain `Path.read_text(encoding="utf-8")`, which raises
        # OSError/UnicodeDecodeError RAW for an unreadable or non-UTF-8
        # overlay file -- neither is caught by bmad_loop's own ProfileError
        # (review finding: this port's own docstring promises "raises
        # HarnessError for an unknown adapter_name or an unimportable
        # bmad_loop", not a raw traceback for a corrupt overlay file).
        # ValueError/TypeError/AttributeError: _parse_profile coerces overlay
        # values with bare float()/int()/.items() (e.g. usage_grace_s = "x"),
        # so a VALID-TOML overlay with a wrong-typed field raises those RAW
        # past ProfileError too -- same class, second review pass.
        except (OSError, UnicodeDecodeError, ValueError, TypeError, AttributeError) as exc:
            raise HarnessError(f"cannot read adapter profile overlay: {exc}") from exc

    def adapter_binary(self, adapter_name: str, project: Path) -> str:
        return self._get_profile(adapter_name, project).binary

    def adapter_seed_files(self, adapter_name: str, project: Path) -> tuple[str, ...]:
        return self._get_profile(adapter_name, project).seed_files

    def adapter_first_run_note(self, adapter_name: str, project: Path) -> str:
        return self._get_profile(adapter_name, project).first_run_note

    def adapter_probe(self, adapter_name: str, project: Path) -> AdapterProbe:
        """Story 6.4 (FR-43): observe ``adapter_name``'s support on this
        machine. Resolves the SAME profile ``adapter_binary`` does (the
        identical ``HarnessError`` contract), then never raises again --
        every subprocess failure below degrades to a field on the returned
        ``AdapterProbe``, mirroring ``harness_version``'s own convention."""
        profile = self._get_profile(adapter_name, project)
        capabilities = _profile_capabilities(profile)
        binary_present = self.binary_present(profile.binary)
        if not binary_present:
            return AdapterProbe(
                adapter=adapter_name,
                binary=profile.binary,
                binary_present=False,
                binary_version=None,
                capabilities=capabilities,
                probe_output=None,
                probe_note="binary not found on PATH",
            )

        version_result = _run([profile.binary, "--version"])
        binary_version: str | None = None
        if version_result is not None and version_result.returncode == 0:
            text = version_result.stdout.strip()
            # Mirrors `harness_version`'s own "prog, then the version token"
            # parse -- the same argparse `action="version"` convention most
            # of these CLIs share; a shape that does not fit degrades to the
            # whole stripped line rather than `None` (the version SUBPROCESS
            # itself succeeded, so *something* was reported).
            _prog, _sep, parsed = text.rpartition(" ")
            binary_version = parsed or text or None

        probe_result = _run(
            ["bmad-loop", "probe-adapter", "--cli", adapter_name, "--json"],
            timeout_s=_PROBE_TIMEOUT_S,
        )
        probe_output: str | None = None
        probe_note: str | None = None
        if probe_result is None:
            probe_note = "bmad-loop probe-adapter could not be launched or timed out"
        elif probe_result.returncode != 0:
            probe_note = f"bmad-loop probe-adapter exited {probe_result.returncode}"
        else:
            redacted = self._redact_probe_output(probe_result.stdout)
            if redacted is None:
                probe_note = "probe output could not be redacted"
            else:
                probe_output = redacted

        return AdapterProbe(
            adapter=adapter_name,
            binary=profile.binary,
            binary_present=True,
            binary_version=binary_version,
            capabilities=capabilities,
            probe_output=probe_output,
            probe_note=probe_note,
        )

    def adapter_skill_trees(self, project: Path) -> dict[str, str]:
        try:
            from bmad_loop.adapters.profile import ProfileError, load_profiles
        except ImportError as exc:
            raise HarnessError(f"bmad_loop is not importable: {exc}") from exc
        try:
            profiles = load_profiles(project)
        except ProfileError as exc:
            raise HarnessError(str(exc)) from exc
        # Same guard as _get_profile's own identical review-discovered
        # convention: an unreadable/non-UTF-8/wrong-typed project-local
        # overlay must not escape as a raw traceback.
        except (OSError, UnicodeDecodeError, ValueError, TypeError, AttributeError) as exc:
            raise HarnessError(f"cannot read adapter profile overlay: {exc}") from exc
        return {name: profile.skill_tree for name, profile in profiles.items()}

    def story_feed_error(self, project: Path) -> str | None:
        try:
            from bmad_loop import bmadconfig, sprintstatus
        except ImportError as exc:
            return f"bmad_loop is not importable: {exc}"
        # Both bmadconfig.load_paths and sprintstatus.load read a config/feed
        # file via plain Path.read_text(encoding="utf-8") before their own
        # typed error handling begins, so an unreadable or non-UTF-8 file
        # raises OSError/UnicodeDecodeError RAW past BmadConfigError/
        # SprintStatusError (review finding: this method's own docstring
        # promises "never raises" -- the message text IS the return value).
        try:
            paths = bmadconfig.load_paths(project)
        except bmadconfig.BmadConfigError as exc:
            return str(exc)
        except (OSError, UnicodeDecodeError) as exc:
            return f"cannot read bmad-config: {exc}"
        # load_paths calls `doc.get(...)` on whatever yaml.safe_load returned
        # without an isinstance check, so a config.yaml whose top level is a
        # list or scalar raises AttributeError RAW past BmadConfigError
        # (review finding -- sprintstatus.load is shape-safe, it isinstance-
        # checks its own doc, so only this call needs the extra catch).
        except (AttributeError, TypeError) as exc:
            return f"invalid bmad-config shape: {exc}"
        try:
            sprintstatus.load(paths.sprint_status)
        except sprintstatus.SprintStatusError as exc:
            return str(exc)
        except (OSError, UnicodeDecodeError) as exc:
            return f"cannot read story feed: {exc}"
        return None

    def story_feed_keys(self, project: Path) -> tuple[str, ...]:
        """AD-38's ``M``: the raw, pre-parse population of story references
        in ``project``'s configured feed. Callers are expected to have
        already checked ``story_feed_error`` (this method's own
        preconditions ARE that method's own reads, repeated); the same
        defensive catches that method's docstring explains apply here too,
        but raise ``HarnessError`` rather than returning error text -- this
        method's return type has no "error" slot, and silently degrading to
        ``()`` would misreport a real read failure as "zero non-empty
        records", exactly the false-green AD-8 exists to forbid."""
        try:
            from bmad_loop import bmadconfig, sprintstatus
        except ImportError as exc:
            raise HarnessError(f"bmad_loop is not importable: {exc}") from exc
        try:
            paths = bmadconfig.load_paths(project)
        except bmadconfig.BmadConfigError as exc:
            raise HarnessError(str(exc)) from exc
        except (OSError, UnicodeDecodeError) as exc:
            raise HarnessError(f"cannot read bmad-config: {exc}") from exc
        except (AttributeError, TypeError) as exc:
            raise HarnessError(f"invalid bmad-config shape: {exc}") from exc
        try:
            feed = sprintstatus.load(paths.sprint_status)
        except sprintstatus.SprintStatusError as exc:
            raise HarnessError(str(exc)) from exc
        except (OSError, UnicodeDecodeError) as exc:
            raise HarnessError(f"cannot read story feed: {exc}") from exc
        # `stories` then `unknown_keys`, each already in the feed's own file
        # order (sprintstatus.load's single ordered-dict iteration keeps
        # both -- see that module's own `load`) -- the union this port's
        # docstring promises, not a re-derived interleaving (which would
        # need re-parsing the raw YAML ourselves, exactly the second
        # independent notion of feed shape FR-52 forbids).
        return tuple(story.key for story in feed.stories) + feed.unknown_keys

    @staticmethod
    def _run_argv(
        *, epic: int | None, story: str | None, max_count: int | None
    ) -> list[str]:
        """The one argv builder shared by ``spin``/``run_foreground`` --
        ``["bmad-loop", "run"]`` plus ``--epic``/``--story``/``--max-stories``
        when given, EXACTLY the flag names the installed 0.9.0 ``cli.py``
        registers (verified live) -- never Marshal's own ``--max-count``
        spelling (``cli/spin.py``'s CLI-facing name), which only this
        function translates. ``--project`` is deliberately never appended:
        both callers set ``cwd=project`` on the subprocess instead, and
        ``bmad-loop run --project`` defaults to ``"."`` (the installed
        ``cli.py``'s own ``add()`` helper), so the two are equivalent and
        the caller-supplied ``project`` never needs to round-trip through a
        second, string-rendered form."""
        argv = ["bmad-loop", "run"]
        if epic is not None:
            argv += ["--epic", str(epic)]
        if story is not None:
            argv += ["--story", story]
        if max_count is not None:
            argv += ["--max-stories", str(max_count)]
        return argv

    def _poll_for_harness_run_id(self, log_path: Path) -> str | None:
        """A bounded poll (``_SPIN_LOG_POLL_INTERVAL_S`` steps, never past
        ``_SPIN_LOG_POLL_TIMEOUT_S``) of ``log_path`` for ``_RUN_STARTING_RE``
        -- never indefinite (the spec's own Never clause). Re-reads the whole
        file each step (the file is at most a handful of KiB by the time this
        line appears -- `bmad-loop run` prints it before any per-story
        adapter output); a missing/unreadable file at any step is treated
        the same as "not there yet", not a fatal error -- the file may not
        exist for the first instant after ``Popen`` returns."""
        deadline = time.monotonic() + _SPIN_LOG_POLL_TIMEOUT_S
        while True:
            try:
                text = log_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            for line in text.splitlines():
                match = _RUN_STARTING_RE.match(line)
                if match:
                    return match.group(1)
            if time.monotonic() >= deadline:
                return None
            time.sleep(_SPIN_LOG_POLL_INTERVAL_S)

    def spin(
        self,
        project: Path,
        *,
        epic: int | None,
        story: str | None,
        max_count: int | None,
        log_path: Path,
    ) -> SpinResult:
        argv = self._run_argv(epic=epic, story=story, max_count=max_count)
        try:
            log_file = open(log_path, "wb")
        except OSError as exc:
            raise HarnessError(f"cannot open spin log {log_path}: {exc}") from exc
        # A `with` block over the ALREADY-OPENED file (not `with open(...) as
        # log_file:` wrapping both steps): opening and launching are two
        # distinct failure modes with two distinct messages ("cannot open
        # spin log" vs "cannot launch bmad-loop run"), so the open above must
        # stay outside this block's own exception handling -- the `with`
        # here exists solely to guarantee the close, mirroring the
        # try/finally this replaces.
        with log_file:
            try:
                process = subprocess.Popen(
                    argv,
                    cwd=project,
                    start_new_session=True,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=log_file,
                    # Review finding (Blind Hunter, verified live): CPython's
                    # stdout is FULLY block-buffered -- not line-buffered --
                    # the instant it is redirected to a regular file rather
                    # than a tty, and `bmad-loop run`'s own "starting" print
                    # (verified against the installed cli.py) carries no
                    # `flush=True`. Left to the AMBIENT environment, this
                    # module's own poll below would only see that line once
                    # the child's stdio buffer fills or the whole (possibly
                    # minutes-long) run exits -- defeating both the poll AND
                    # AD-22's "returns promptly" in any shell that does not
                    # happen to already export PYTHONUNBUFFERED (this
                    # session's own dev environment does, which is exactly
                    # what let the bug through undetected). Forcing it here,
                    # on the CHILD's own env, makes the poll's promptness a
                    # property of this call, never of whatever invoked it.
                    env={**os.environ, "PYTHONUNBUFFERED": "1"},
                )
            except OSError as exc:
                raise HarnessError(f"cannot launch bmad-loop run: {exc}") from exc
            # The child already holds its own duplicated descriptor
            # (Popen's own fork+exec dance) -- closing this end in the
            # parent (as the `with` block exits) is safe, and correct: an
            # unclosed copy here would leak across every future subprocess
            # this LONG-LIVED CLI process spawns.

        harness_run_id = self._poll_for_harness_run_id(log_path)
        return SpinResult(pid=process.pid, harness_run_id=harness_run_id)

    @staticmethod
    def _normalize_returncode(returncode: int) -> int:
        """``subprocess.CompletedProcess.returncode`` is NEGATIVE when the
        child was killed by a signal (``-N`` for signal ``N``, POSIX
        convention) -- review finding (Edge Case Hunter, verified live): a
        raw negative value handed to ``sys.exit``/``SystemExit`` gets
        OS-truncated (``exit()`` takes a byte), silently producing a
        different, misleading process exit status for a caller checking
        ``$?`` than the negative Python value itself claims. Mirrors the
        128+signal POSIX shell convention (the same one every plain shell
        reports for a signal-killed job) rather than inventing a new one."""
        return 128 - returncode if returncode < 0 else returncode

    def attach(self, project: Path) -> int:
        try:
            result = subprocess.run(["bmad-loop", "attach"], cwd=project)
        except OSError as exc:
            raise HarnessError(f"cannot launch bmad-loop attach: {exc}") from exc
        return self._normalize_returncode(result.returncode)

    def run_foreground(
        self,
        project: Path,
        *,
        epic: int | None,
        story: str | None,
        max_count: int | None,
    ) -> int:
        argv = self._run_argv(epic=epic, story=story, max_count=max_count)
        try:
            result = subprocess.run(argv, cwd=project)
        except OSError as exc:
            raise HarnessError(f"cannot launch bmad-loop run: {exc}") from exc
        return self._normalize_returncode(result.returncode)

    def run_smoke(
        self,
        project: Path,
        *,
        adapter_name: str,
        story: str,
        timeout_s: float,
        log_path: Path,
    ) -> SmokeRunResult:
        """Story 6.5 (FR-44/AD-37): drive ONE bounded ``bmad-loop run
        --story <story> --max-stories 1`` attempt against ``adapter_name``.
        Resolves the profile via the EXISTING ``_get_profile`` seam (raises
        ``HarnessError`` for an unknown adapter or an unimportable
        ``bmad_loop``, the SAME contract ``adapter_probe``/``adapter_binary``
        already have). An absent binary short-circuits to NO subprocess call
        at all (mirrors ``adapter_probe``'s identical short-circuit); a
        present binary gets exactly one bounded, log-redirected
        ``subprocess.run`` call (mirrors ``spin``'s own log-redirection
        recipe, but synchronous and bounded rather than detached -- there is
        no supervisor watching an unattended ephemeral smoke run)."""
        profile = self._get_profile(adapter_name, project)
        binary = profile.binary
        binary_present = self.binary_present(binary)
        if not binary_present:
            return SmokeRunResult(
                adapter=adapter_name,
                binary=binary,
                binary_present=False,
                launched=False,
                returncode=None,
                timed_out=False,
            )
        argv = self._run_argv(epic=None, story=story, max_count=1)
        try:
            log_file = open(log_path, "wb")
        except OSError:
            return SmokeRunResult(
                adapter=adapter_name,
                binary=binary,
                binary_present=True,
                launched=False,
                returncode=None,
                timed_out=False,
            )
        with log_file:
            try:
                result = subprocess.run(
                    argv,
                    cwd=project,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=log_file,
                    timeout=timeout_s,
                )
            except subprocess.TimeoutExpired:
                return SmokeRunResult(
                    adapter=adapter_name,
                    binary=binary,
                    binary_present=True,
                    launched=True,
                    returncode=None,
                    timed_out=True,
                )
            except OSError:
                return SmokeRunResult(
                    adapter=adapter_name,
                    binary=binary,
                    binary_present=True,
                    launched=False,
                    returncode=None,
                    timed_out=False,
                )
        return SmokeRunResult(
            adapter=adapter_name,
            binary=binary,
            binary_present=True,
            launched=True,
            returncode=self._normalize_returncode(result.returncode),
            timed_out=False,
        )

    def stop(self, project: Path, run_id: str) -> bool:
        # Synchronous, capturing output like `attach`/`run_foreground` do NOT
        # (those inherit stdio by design) -- `stop` is not interactive, and
        # capturing keeps this call's own stdout/stderr from leaking into
        # the supervisor's own redirected log uninterpreted.
        try:
            result = subprocess.run(
                ["bmad-loop", "stop", run_id],
                cwd=project,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=_STOP_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired as exc:
            raise HarnessError(
                f"bmad-loop stop {run_id} timed out after {_STOP_TIMEOUT_S}s: {exc}"
            ) from exc
        except (OSError, ValueError) as exc:
            # `ValueError` alongside `OSError` (the same CPython split this
            # module's own `spin`/`spawn_detached` sibling already guards):
            # `subprocess.run` raises a plain `ValueError` -- not an
            # `OSError` -- for an embedded NUL byte in an argv element.
            raise HarnessError(f"cannot launch bmad-loop stop: {exc}") from exc
        # A non-zero exit is the ordinary "did not stop" shape (already
        # finished, or some other non-launch failure the installed 0.9.0
        # `cmd_stop` reports) -- never raised, matching this Protocol's own
        # documented split.
        return result.returncode == 0

    def resume(self, project: Path, run_id: str, *, log_path: Path) -> int:
        # Mirrors `spin`'s own detached-launch recipe exactly: `bmad-loop
        # resume` drives a resumed engine run synchronously and
        # unboundedly in the child (confirmed live against the installed
        # 0.9.0 `_resume_paused_run`, which calls `engine.run()` directly),
        # so it must never be waited on here either.
        #
        # APPEND, never "wb" (review finding): on the supervisor's own
        # stop-and-retry path `log_path` is the WEDGED run's own
        # `harness.log` -- the same file `cli/spin.py` created and the
        # original engine attempt has been writing to for however long it
        # ran. Truncating it destroys the only record of what the run was
        # doing when it stopped producing output, which is the single most
        # valuable artifact at exactly the moment `stop-and-retry` fires.
        # `spin`'s own `"wb"` is correct there because that file is brand
        # new. Appending is also correct for `marshal factory resume`'s own
        # brand-new run-directory log (Story 3.7's second caller), where
        # "ab" simply creates it.
        try:
            log_file = open(log_path, "ab")
        except (OSError, ValueError) as exc:
            raise HarnessError(
                f"cannot open resume log {str(log_path)!r}: {exc}"
            ) from exc
        with log_file:
            # A visible seam between the two attempts (review finding): the
            # append above preserves the wedged attempt's output, but without
            # a delimiter the resumed engine's output is byte-concatenated
            # onto it, so the operator reading this file after a
            # stop-and-retry cannot tell where the record they came for ends.
            # Deliberately NOT labelled "stop-and-retry" (follow-up review
            # finding): this method has two callers, and `cli/spin.py`'s own
            # `marshal factory resume` is an operator-driven resume, never
            # the supervisor's automatic idle recovery -- attributing one to
            # the other in the log is a false diagnostic. Which caller it
            # was stays recoverable from the journal (`idle-stop-and-retry`
            # vs `run-resume`), where the two are already distinct kinds.
            # Best-effort only -- a marker that cannot be written must never
            # be the reason a recovery does not happen, and the `flush` keeps
            # it ordered ahead of the child's own writes to the same fd.
            try:
                log_file.write(
                    f"\n--- marshal: resuming {run_id} ---\n".encode("utf-8")
                )
                log_file.flush()
            except (OSError, ValueError):
                pass
            try:
                process = subprocess.Popen(
                    ["bmad-loop", "resume", run_id],
                    cwd=project,
                    start_new_session=True,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=log_file,
                    # Same env hardening `spin` applies, for the same
                    # reasons (stdout block-buffers once redirected to a
                    # regular file; `cwd` must never influence which code a
                    # detached `python`-less `bmad-loop` child resolves --
                    # this one execs the installed `bmad-loop` binary
                    # directly, not `python -m`, but the env is inherited
                    # unconditionally regardless).
                    env={**os.environ, "PYTHONUNBUFFERED": "1"},
                )
            except (FileNotFoundError, ValueError, OSError) as exc:
                raise HarnessError(f"cannot launch bmad-loop resume: {exc}") from exc
        return process.pid

    def usage_snapshot(self, project: Path, run_id: str) -> UsageSnapshot | None:
        # Lazy import, this method's own instance -- see the module
        # docstring's Story 3.6 paragraph. `bmad_loop.journal.load_state`
        # reads `<project>/.bmad-loop/runs/<run_id>/state.json` whole via
        # `json.loads(target.read_text(...))`, then `RunState.from_dict`
        # coerces every field -- an unreadable file raises `OSError`, a
        # malformed document raises `json.JSONDecodeError` (a `ValueError`
        # subclass), and a missing/wrong-typed field inside `from_dict`
        # raises `KeyError` (a required key absent) or `TypeError`/
        # `ValueError` (e.g. `int(d["epic"])` on a non-numeric value,
        # `Phase(d["phase"])` on an unknown phase string); a wrong-TYPED
        # (but present) `policy_snapshot` field (e.g. a JSON string instead
        # of an object) survives `from_dict` unvalidated and raises
        # `AttributeError` only once `cache_read_weight()` calls `.get()`
        # on it below.
        try:
            from bmad_loop.journal import load_state
        except ImportError:
            return None
        run_dir = Path(project) / ".bmad-loop" / "runs" / run_id
        # Review finding: EVERYTHING derived from `state` -- not just
        # `load_state` itself -- must stay inside this guard. `cache_read_
        # weight()` is normally self-guarded (it catches KeyError/TypeError/
        # ValueError internally and floors to 0.1), but that guard assumes
        # `policy_snapshot` is itself a Mapping; `RunState.from_dict` never
        # validates that assumption (`policy_snapshot=d.get("policy_
        # snapshot", {})` accepts whatever JSON type was present), so a
        # syntactically-valid `state.json` carrying e.g.
        # `"policy_snapshot": "corrupted"` makes `.get("limits")` raise a
        # bare `AttributeError` -- outside every exception this method
        # previously caught, escaping to `supervisor/__main__.py`'s tick
        # loop uncaught and killing the sidecar with a dangling
        # `supervisor-attach` and no matching `supervisor-detach` (exactly
        # the AD-9 "never silent" failure this whole port promises never to
        # produce). This method's own contract is "never raises"; the try
        # now covers every read this method performs against `state`, not
        # only its initial load.
        try:
            state = load_state(run_dir)
            cache_read_weight = state.cache_read_weight()
            non_terminal = [task for task in state.tasks.values() if not task.terminal]
            story_key: str | None = None
            story_weighted_tokens: int | None = None
            if len(non_terminal) == 1:
                task = non_terminal[0]
                # `if task.story_key` guards the pair, not just the tally
                # (review finding). `UsageSnapshot`'s own docstring states
                # `story_weighted_tokens` is `None` in LOCKSTEP with
                # `story_key` -- "never a number attributed to 'no story'".
                # `bmad_loop`'s `StoryTask.from_dict` does not reject a null
                # or empty `story_key`, so a state.json carrying one made the
                # sole non-terminal task set the tally while leaving the key
                # `None`, publishing exactly the shape the docstring promises
                # cannot occur. Both current supervisor consumers happen to
                # re-check `usage.story_key is not None` independently, so
                # nothing misbehaves today -- but an exposed invariant that
                # only holds because every caller redundantly re-verifies it
                # is a trap for the next one that reads the docstring and
                # trusts it. Such a task's consumption still counts toward
                # `run_weighted_tokens` below (it is summed over ALL tasks);
                # it simply cannot be attributed to a story.
                if task.story_key:
                    story_key = task.story_key
                    story_weighted_tokens = task.tokens.weighted_total(cache_read_weight)
            run_weighted_tokens = sum(
                task.tokens.weighted_total(cache_read_weight) for task in state.tasks.values()
            )
        # `ArithmeticError` and `RecursionError` alongside the rest (review
        # finding): neither is a `ValueError`, and both are reachable from a
        # syntactically-valid `state.json` this method promises never to
        # raise on. `json.loads` raises `RecursionError` on a deeply nested
        # document; `OverflowError` (an `ArithmeticError`) comes out of
        # `round(cache_read * weight)` when the file carries a non-finite
        # weight, and out of `int(d["epic"])`/`int(d["attempt"])` inside
        # `from_dict` when it carries a value like `1e400`. Escaping here
        # kills the sidecar with a dangling `supervisor-attach` and no
        # matching `supervisor-detach` -- the exact AD-9 "never silent"
        # failure the paragraph above says this port must never produce.
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            ArithmeticError,
            RecursionError,
        ):
            return None
        return UsageSnapshot(
            story_key=story_key,
            story_weighted_tokens=story_weighted_tokens,
            run_weighted_tokens=run_weighted_tokens,
            sample_path=run_dir / "state.json",
        )

    @staticmethod
    def _redact_text(text: str) -> str | None:
        """AD-34's own redaction-at-capture idiom
        (``adapters/observer_mux.py::pane_content``'s wrap/unwrap round-trip,
        reused verbatim), applied to one ``state.json`` free-text field at a
        time. Narrowly guarded (``(ValueError, LookupError, TypeError)``,
        the SAME tuple that method's own transform lines catch) so a single
        field's redaction failure degrades only that field to ``None``,
        never the whole snapshot ``run_status_snapshot`` is building."""
        try:
            redacted = to_redacted({"text": text})
            return json.loads(redacted.text)["text"]
        except (ValueError, LookupError, TypeError):
            return None

    @staticmethod
    def _redact_probe_output(text: str) -> str | None:
        """Story 6.4's own probe-output redaction -- review finding: wrapping
        the WHOLE ``bmad-loop probe-adapter --json`` document as one opaque
        string (``_redact_text``'s own shape) means ``to_redacted``'s
        field-NAME-based redaction half never sees the document's actual
        keys -- it only ever recurses into a real ``Mapping``, and a single
        giant string value is not one. A secret-shaped field inside that
        JSON (e.g. a literal ``api_key``/``session_token`` key) would then be
        invisible to anything except the five hardcoded token-shape regexes,
        a real narrowing of protection for a document ``tests/meta/
        test_probe_json_contract.py`` already proves is well-formed JSON.

        Parses ``text`` first; a ``dict`` payload is redacted via
        ``to_redacted`` DIRECTLY (both halves: field-name AND shape), then
        re-serialized -- the full-coverage path this document's own proven
        shape makes the common case. Anything that fails to parse as a JSON
        object (unexpected for this contract, but never assumed) falls back
        to ``_redact_text``'s opaque-string wrap, so a shape surprise still
        degrades to reduced-but-real coverage rather than an exception
        escaping this always-degrades-never-raises method."""
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            return BmadLoopHarness._redact_text(text)
        if not isinstance(parsed, dict):
            return BmadLoopHarness._redact_text(text)
        try:
            return to_redacted(parsed).text
        except (ValueError, LookupError, TypeError):
            return None

    def run_status_snapshot(self, project: Path, run_id: str) -> RunStatusSnapshot | None:
        # Lazy import, this method's own instance -- see the module
        # docstring's Story 3.7 paragraph. Reads the SAME state.json
        # `usage_snapshot` reads, via the SAME seam.
        try:
            from bmad_loop.journal import load_state
        except ImportError:
            return None
        run_dir = Path(project) / ".bmad-loop" / "runs" / run_id
        # The identical widened guard `usage_snapshot` documents at length --
        # reused verbatim (this story's own Always bullet), covering every
        # read this method performs against `state`, not only its initial
        # load.
        try:
            state = load_state(run_dir)
            # `RunState.finished` -- bmad-loop's own `_resume_paused_run`
            # refuses on it before doing anything else, so `cli/spin.py`'s
            # `marshal factory resume` must be able to see it too (a
            # detached launch never surfaces the child's exit code).
            finished = bool(state.finished)
            paused_stage = state.paused_stage
            paused_story_key = state.paused_story_key
            paused_reason = (
                self._redact_text(state.paused_reason)
                if state.paused_reason is not None
                else None
            )
            escalated_spec_file: str | None = None
            escalated_task_phase: str | None = None
            if paused_story_key is not None:
                paused_task = state.tasks.get(paused_story_key)
                if paused_task is not None:
                    escalated_spec_file = paused_task.spec_file
                    escalated_task_phase = paused_task.phase.value
            deferred: list[DeferredStory] = []
            # Story 3.8 (AD-46/FR-61): EVERY task's phase/commit_sha, not
            # only the deferred ones -- `supervisor/durability.py::
            # classify_push_triggers` needs the full population to detect a
            # story crossing `Phase.REVIEW_VERIFY`/`Phase.DONE` or its
            # `commit_sha` turning non-`None` between two consecutive reads.
            # Built in the SAME loop as `deferred` below rather than a
            # second pass over `state.tasks`.
            tasks: list[TaskPhaseSnapshot] = []
            for task in state.tasks.values():
                tasks.append(
                    TaskPhaseSnapshot(
                        story_key=task.story_key,
                        phase=task.phase.value,
                        commit_sha=task.commit_sha,
                        branch=task.branch,
                    )
                )
                # `StrEnum` members compare equal to their own value, but a
                # plain string comparison against the literal is used here
                # (rather than importing `bmad_loop.model.Phase`) -- AD-3
                # reserves that import for the seam alone; this module
                # already names bmad-loop-owned raw values by their known-
                # live shape elsewhere (e.g. `_RUN_STARTING_RE`).
                if task.phase.value != "deferred":
                    continue
                deferred.append(
                    DeferredStory(
                        story_key=task.story_key,
                        reason=(
                            self._redact_text(task.defer_reason)
                            if task.defer_reason is not None
                            else None
                        ),
                        attempt=task.attempt,
                        branch=task.branch,
                        worktree_path=task.worktree_path,
                        spec_file=task.spec_file,
                    )
                )
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            ArithmeticError,
            RecursionError,
        ):
            return None
        return RunStatusSnapshot(
            paused_stage=paused_stage,
            paused_story_key=paused_story_key,
            paused_reason=paused_reason,
            escalated_spec_file=escalated_spec_file,
            escalated_task_phase=escalated_task_phase,
            deferred=tuple(deferred),
            finished=finished,
            tasks=tuple(tasks),
        )

    def resolution_reference(
        self, project: Path, run_id: str, story_key: str
    ) -> str | None:
        # Lazy import, this method's own instance -- the seam AD-3 reserves
        # for the one call `cli/spin.py`'s `marshal factory resume` could
        # not otherwise make (see the module docstring's Story 3.7
        # paragraph).
        try:
            from bmad_loop.resolve import resolution_path
        except ImportError:
            return None
        run_dir = Path(project) / ".bmad-loop" / "runs" / run_id
        try:
            path = resolution_path(run_dir, story_key)
            return path.as_posix() if path.is_file() else None
        except (OSError, ValueError, TypeError):
            return None

    def ledger_story_statuses(self, path: Path) -> tuple[tuple[str, str], ...]:
        """Story 5.4 (FR-39/FR-40): reads the sprint-status-shaped YAML file
        at ``path`` DIRECTLY via ``bmad_loop.sprintstatus.load`` -- the SAME
        parser ``story_feed_keys``/``story_feed_error`` already import --
        never a hand-rolled second YAML reader. Unlike those two methods,
        this one never consults ``bmad_loop.bmadconfig.load_paths``: the
        caller passes an explicit path (the TRACKED
        ``sprint-status-ledger.yaml`` twin, never a loop home's own
        configured Tier-3 feed), so there is no ``project`` directory to
        resolve a config from in the first place."""
        try:
            from bmad_loop import sprintstatus
        except ImportError as exc:
            raise HarnessError(f"bmad_loop is not importable: {exc}") from exc
        # sprintstatus.load calls Path.read_text(encoding="utf-8") before its
        # own SprintStatusError handling begins, so an unreadable/non-UTF-8
        # file raises OSError/UnicodeDecodeError raw past that type -- the
        # same gap `story_feed_error`'s own docstring already documents for
        # the identical call.
        try:
            feed = sprintstatus.load(path)
        except sprintstatus.SprintStatusError as exc:
            raise HarnessError(str(exc)) from exc
        except (OSError, UnicodeDecodeError) as exc:
            raise HarnessError(f"cannot read ledger: {exc}") from exc
        return tuple((story.key, story.status) for story in feed.stories)
