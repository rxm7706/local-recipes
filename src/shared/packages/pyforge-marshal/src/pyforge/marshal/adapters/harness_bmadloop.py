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

Story 3.12 (retry escalation, AD-26) widens ``run_status_snapshot`` a third
time, in the SAME per-task loop that already builds ``deferred``/``tasks``:
each ``DeferredStory`` now also carries ``review_cycle=task.review_cycle``,
read the identical way ``attempt`` is one line above it (``StoryTask``'s own
same-named field, no new import, no new guard). This is the fact
``core.supervise.evaluate_retry_escalation`` needs to tell a story stuck on
review cycles apart from one stuck on dev attempts. This story ALSO adds
``write_policy_document`` below (see that function's own docstring) --
``cli/spin.py::run_resume``'s narrow, single-key floor-raise write, sharing
``write_policy_toml``'s atomic-write mechanics via the new private
``_atomic_write_policy_text`` helper both now call.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import time
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any

import tomlkit
from pyforge.core.atomic_write import atomic_write_bytes
from pyforge.core.errors import PyforgeError
from pyforge.core.hooks import HookSpec, PluginRegistry
from pyforge.core.process import PosixProcess, ProcessError, ProcessResult

from ..core import policy
from ..core.egress import to_redacted
from ..core.harness_profile import (
    PROFILE_BY_BMADLOOP_ADAPTER,
    WireWrap,
    bmadloop_adapter_for_preference,
    load_packaged_profiles,
    resolve_wire_enabled,
    resolve_wire_wrap,
    substitute_wire_port,
)
from ..core.model_cost import (
    TokenCounts,
    adapter_provider,
    catalog_declared,
    estimate_layer_savings_usd,
    estimate_spend_usd,
    provider_declaring_model,
    resolve_cache_read_ratio,
    resolve_model_price,
    weighted_total,
)
from ..core.tier_routing import TierLaunchResolution, resolve_tier_launch
from ..ports.harness import (
    AdapterProbe,
    DeferredStory,
    EngineLiveness,
    HarnessPort,
    HarnessRunTerminalVerdict,
    LayerSavings,
    RunStatusSnapshot,
    SmokeRunResult,
    SpinResult,
    TaskPhaseSnapshot,
    UsageSnapshot,
)

LOOP_RUNNER_HOOK_SPEC = HookSpec(name="pyforge.marshal.loop_runner", owner="marshal")
DEFAULT_LOOP_RUNNER_PLUGIN_ID = "bmad-loop"
_MODEL_COST_CATALOG_SIDECAR = "marshal-model-cost-catalog.json"

# --- the vendored, project-agnostic harness policy template ----------------
#
# Covers every section of the installed bmad_loop 0.11.0 schema at its own
# stock default (deliberately not every key -- the module docstring names
# the omitted instance-local/reserved ones). Keys that are rendered from
# Marshal's EffectivePolicy composition (the 4-layer fold: code DEFAULT_POLICY
# -> repo-defaults from `_bmad-output/policy-defaults.toml` -> project-layer
# from marshal-policy.toml -> invocation --set flags) carry placeholder
# baselines here -- render_policy_toml() always overwrites them, so their
# template value never reaches a caller. These include gates.mode,
# max_dev_attempts/.max_review_cycles/.max_followup_reviews/
# .dev_contract_nudge, verify.commands/.stream_capture_kb,
# review.on_timeout/.on_status_contradiction, operator.enabled, and
# scm.worktree_seed (Story 25.4 added the five bmad-loop 0.10/0.11 knobs,
# CAP-4).
_POLICY_TEMPLATE = """\
# bmad-loop orchestration policy -- the harness's own vocabulary (bmad_loop
# 0.11.0). This file is a DERIVED artifact: Marshal renders it whole from the
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
# Deliberate repo default = stock true: the marker-repair nudge closes the
# exact `## Auto Run Result` omission this fleet's own detectors chase.
dev_contract_nudge = true    # overwritten per render from EffectivePolicy
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
# Deliberate repo default = stock 256 KiB per stream: generous for real
# pytest/ruff failure tails, bounds a runaway chatty verifier; 0 = capture
# nothing (legal on both sides).
stream_capture_kb = 256       # overwritten per render from EffectivePolicy

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
# Deliberate repo default = stock "retry": re-review up to
# limits.max_review_cycles before deferring; salvage-if-done / defer are the
# alternative modes.
on_timeout = "retry"          # overwritten per render from EffectivePolicy
# Deliberate repo default = stock "escalate": matches the fleet's
# escalate-don't-silently-retry posture (escalate | retry).
on_status_contradiction = "escalate"  # overwritten per render from EffectivePolicy
# Story 31.3 (CAP-4): the tea-test-review marshal review lens's own
# --min-score threshold. An extra key bmad_loop's own [review] parser
# ignores (verified live against the installed package); consumed only by
# the lens's own instruction (_bmad/custom/bmad-review.toml) at review
# time, never by the harness itself.
min_score = 80                # overwritten per render from EffectivePolicy

[stories]
source = "sprint-status"      # sprint-status | stories
spec_folder = ""

[dev]
skill = "bmad-dev-auto"

[operator]
# Deliberate repo default = stock true: the fleet WANTS parked-not-dead
# semantics -- `awaiting-operator` is the honest outcome for a story whose
# remaining acceptance criteria are human-only actions.
enabled = true                # overwritten per render from EffectivePolicy

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


#: S-13.7 (FR-174): the repo-wide surface-reconciliation guard, APPENDED to every
#: station's own verify commands at render time.
#:
#: bmad-loop writes governed code all day with no knowledge of the repo's
#: spec-surface contract, so every loop-produced story that touches governed
#: files reds the spec-surface verdict until a human names the changed paths in
#: the owning Spec's `.memlog.md`. Measured 2026-08-09 on the first loop stories
#: ever landed (doctor 6.2-6.4, then 6.5): 14 governed paths, then 9 more, all
#: named by hand AT LANDING. This makes the producer pay it instead.
#:
#: APPENDED AT RENDER, deliberately not added as a policy layer: `verify_commands`
#: composes last-wins across the four layers (AD-16), so a repo-wide default would
#: be silently DROPPED the moment any project layer sets its own -- which all eight
#: stations do. Rendering appends, so a new station inherits this automatically and
#: nobody has to remember to declare it in a ninth place (derive, don't declare).
#:
#: Plain `python`, not a pixi task, and (Story 6.9 REVIEW PASS 1, 2026-08-10) no
#: longer `scripts/spec_surface_check.py` either -- that script's own read-only
#: verdict retired into `pyforge.doctor.sources.chain::gather_spec_surface`, whose
#: package needs `pyforge-doctor` importable. `scripts/spec_surface_reconcile.py`
#: reaches it WITHOUT installing anything: it puts this checkout's own
#: `src/shared/packages/pyforge-doctor/src` onto `sys.path` directly (always
#: present on disk in any worktree of this repo), the same install-free trick
#: `tests/scripts/test_detectors_doctor_sources.py` already uses. Still pure
#: stdlib once that's done (git + hashlib, via the Doctor package), so it still
#: needs no environment, and it still avoids the deep-worktree pixi path-length
#: panic that breaks other gates inside bmad-loop run worktrees.
#:
#: NEVER `--write-baseline`. A producer that can stamp its own baseline is exactly
#: the laundering S-13.2 exists to end: the loop must RECONCILE by naming the paths
#: it changed, never accept its own drift as correct -- `spec_surface_reconcile.py`
#: doesn't even expose the flag; only the mutation-only residual
#: `scripts/spec_surface_check.py` (a human-invoked command, never bmad-loop's own)
#: still can.
_SURFACE_RECONCILE_COMMAND = "python scripts/spec_surface_reconcile.py"


def render_policy_toml(
    effective: policy.EffectivePolicy,
    *,
    difficulty: str | None = None,
    adapter: str | None = None,
    tier_resolution: object | None = None,
) -> str:
    """Pure string builder (no I/O): parse ``_POLICY_TEMPLATE``, overwrite
    Marshal's 12 mapped keys from ``effective``, apply FR-51 tier-batching,
    conditionally render Story 28.1's ``[context]`` block, and return
    ``tomlkit.dumps(...)``. Identical ``(effective, difficulty)``
    produces byte-identical output (AD-12/AD-35 "derived artifact"
    discipline).

    Story 28.1 (SPEC-marshal-token-economy CAP-1): when
    ``effective.context.value`` is non-empty (something was declared),
    a ``[context.<layer>]`` sub-table is written for each of
    ``policy.CONTEXT_LAYER_NAMES``, carrying the SAME
    ``{enabled, aggressiveness}`` payload ``policy.resolve_context_layers``
    computes -- the one composition site both this function and
    ``cli/dispatch.py::dispatch_once`` consume (no second parser, no
    engine-specific fork). ``_POLICY_TEMPLATE`` carries no ``[context]``
    table at all and nothing is written when the declaration is absent (the
    default, empty-mapping ``context`` value): this is what keeps a run
    with no ``[context]`` block byte-identical to pre-Story-28.1 output.
    ``bmad_loop`` 0.11's own loader (``policy.py::loads``) reads only its
    own known top-level tables and never rejects an unrecognized one, so an
    unread ``[context]`` table is inert to the harness today -- a later
    story (CAP-2) is what wires actual behavior at the launch seam.

    The 12 mapped keys: ``gate_mode`` -> ``[gates].mode``,
    ``max_dev_attempts``/``max_review_cycles``/``max_followup_reviews`` ->
    ``[limits]``'s same-named keys, ``verify_commands`` -> ``[verify].commands``,
    ``worktree_seed_paths`` -> ``[scm].worktree_seed`` (the only two STATIC
    fields in the mapped set), plus Story 25.4's five bmad-loop 0.10/0.11
    knobs (CAP-4): ``review_on_timeout`` -> ``[review].on_timeout``,
    ``review_on_status_contradiction`` -> ``[review].on_status_contradiction``,
    ``dev_contract_nudge`` -> ``[limits].dev_contract_nudge``,
    ``operator_enabled`` -> ``[operator].enabled``,
    ``stream_capture_kb`` -> ``[verify].stream_capture_kb``, and Story
    31.3's ``review_min_score`` -> ``[review].min_score`` (CAP-4,
    spec-bmad-suite-lifecycle). 10 of the 12 are SEED fields, every one
    read exclusively via ``seed_view()`` (AD-26). The six knobs (five from
    Story 25.4, plus Story 31.3's) are each written as their native Python
    type (bool/int/str), which tomlkit preserves as the exact TOML scalar
    type. Marshal validates all six strictly at compose; at load only
    ``limits.dev_contract_nudge`` is strict (``_limit_bool`` rejects a
    coercible mismatch), while ``operator.enabled`` and
    ``verify.stream_capture_kb`` are ``bool()``/``int()``-coerced by the
    harness, and ``review.min_score`` is not read by the harness at all
    (an inert extra key to its lenient ``[review]`` parser) -- exact types
    are emitted for all six regardless.
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

    ``adapter`` (Story 6.5, FR-44): when given, overwrites ``[adapter].name``.
    When OMITTED, Story 22.8 (FR-193 CAP-8, "one preference, two engines")
    derives it from ``effective.harness_preference`` -- the first preference
    entry with a bmad-loop counterpart (``core/harness_profile.py::
    bmadloop_adapter_for_preference``, a pure code-constant translation, no
    file I/O). A preference with NO counterpart keeps the template baseline
    (the ``--write-harness-policy`` boundary reports that as
    ``MRS-POLICY-008``). The derived name is only assigned when it DIFFERS
    from the document's current value, so the default preference (whose
    first counterpart-bearing entry is ``claude``, deliberately equal to the
    template baseline -- see ``DEFAULT_POLICY``'s own comment) renders
    byte-identically to every pre-22.8 caller. An explicit ``adapter``
    argument still wins (Story 6.5's smoke path forces arbitrary names).
    Applied independently of ``difficulty``'s own tier-batching (which
    touches only ``[adapter.<stage>].model`` sub-tables, never
    ``[adapter].name``).
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
    # Story 25.4 (CAP-4): the five bmad-loop 0.10/0.11 knobs, each projected
    # onto the harness's table-qualified name, plus Story 31.3's
    # review_min_score below. The composed values are native Python
    # bool/int/str (marshal's own validators reject coercible mismatches
    # before this point), so tomlkit emits exact TOML scalar types for all
    # six -- required by 0.11's strict `_limit_bool` for dev_contract_nudge,
    # kept exact anyway for the two keys the harness's loader would
    # silently coerce (`operator.enabled` via bool(), `stream_capture_kb`
    # via int()), and inert for `review.min_score` (the harness never reads
    # it at all).
    doc["limits"]["dev_contract_nudge"] = seed["dev_contract_nudge"].value
    doc["verify"]["stream_capture_kb"] = seed["stream_capture_kb"].value
    doc["review"]["on_timeout"] = seed["review_on_timeout"].value
    doc["review"]["on_status_contradiction"] = seed["review_on_status_contradiction"].value
    doc["review"]["min_score"] = seed["review_min_score"].value
    doc["operator"]["enabled"] = seed["operator_enabled"].value
    # S-13.7 (FR-174): the station's own commands, THEN the repo-wide surface
    # guard. Appended rather than composed (see _SURFACE_RECONCILE_COMMAND), and
    # de-duplicated so re-rendering an already-rendered home stays idempotent --
    # `marshal config --write-harness-policy` is run repeatedly by design.
    _verify = [c for c in effective.verify_commands.value if c != _SURFACE_RECONCILE_COMMAND]
    doc["verify"]["commands"] = [*_verify, _SURFACE_RECONCILE_COMMAND]
    doc["scm"]["worktree_seed"] = list(effective.worktree_seed_paths.value)

    if adapter is not None:
        doc["adapter"]["name"] = adapter
    else:
        resolved_tier = tier_resolution
        if resolved_tier is None and difficulty is not None:
            resolved_tier = resolve_tier_launch(effective, difficulty)
        if isinstance(resolved_tier, TierLaunchResolution) and resolved_tier.adapter_name:
            doc["adapter"]["name"] = resolved_tier.adapter_name
        else:
            derived = bmadloop_adapter_for_preference(effective.harness_preference.value)
            if derived is not None and str(doc["adapter"]["name"]) != derived:
                doc["adapter"]["name"] = derived

    tier_map = effective.model_tier_map.value
    stage_models: dict[str, str] = {}
    if isinstance(tier_resolution, TierLaunchResolution) and tier_resolution.resolved_models:
        stage_models = dict(tier_resolution.resolved_models)
    elif tier_resolution is None and difficulty is not None:
        launch = resolve_tier_launch(effective, difficulty)
        if launch.resolved_models:
            stage_models = dict(launch.resolved_models)
    elif difficulty is not None and difficulty in tier_map:
        raw_stages = tier_map[difficulty]
        if isinstance(raw_stages, Mapping):
            for stage in _ADAPTER_STAGES:
                entry = raw_stages.get(stage)
                if isinstance(entry, str) and entry:
                    stage_models[stage] = entry

    if stage_models:
        adapter_table = doc["adapter"]
        # FR-51 tier-batching only ever means "use this model under whichever
        # adapter actually launches" -- `doc["adapter"]["name"]` above is
        # already the FINAL, real adapter (explicit arg, tier-resolved,
        # harness_preference-derived, or the template's own baseline). When
        # a stage's tier-mapped model is catalogued under a DIFFERENT
        # provider than that adapter, writing it anyway launches a real
        # adapter binary with a model it was never meant to receive -- the
        # exact hybrid, invalid dispatch found 2026-09-12
        # (dispatch-tier-routing-fails-safe): a Cursor model
        # (`composer-2.5-fast`) with no explicit `harness` key landed on the
        # `claude` adapter because `harness_preference` (`cursor`) has no
        # bmad-loop counterpart and silently fell back to the template
        # baseline, while the model override applied unchanged. Skip the
        # override for that stage instead -- it keeps the baseline
        # [adapter]/[adapter.review] model, which is always launchable.
        resolved_adapter_provider = adapter_provider(str(doc["adapter"]["name"]))
        catalog_for_stage_check = effective.model_cost_catalog.value
        for stage in _ADAPTER_STAGES:
            model = stage_models.get(stage)
            if model is None:
                continue
            implied_provider = provider_declaring_model(catalog_for_stage_check, model)
            if implied_provider is not None and implied_provider != resolved_adapter_provider:
                continue
            if stage not in adapter_table:
                adapter_table[stage] = tomlkit.table()
            adapter_table[stage]["model"] = model

    # Story 28.1 (CAP-1): only rendered when something was actually
    # declared -- see this function's own docstring for why an absent
    # `context` field (DEFAULT_POLICY's empty-mapping default) must render
    # NO `[context]` table at all, byte-identical to pre-28.1 output.
    if effective.context.value:
        resolved_layers = policy.resolve_context_layers(effective)
        context_table = tomlkit.table()
        for layer_name in policy.CONTEXT_LAYER_NAMES:
            layer_table = tomlkit.table()
            layer_table["enabled"] = resolved_layers[layer_name]["enabled"]
            layer_table["aggressiveness"] = resolved_layers[layer_name]["aggressiveness"]
            context_table[layer_name] = layer_table
        doc["context"] = context_table

    # Story 28.10 (CAP-11): derive cache-read weight from declared catalog.
    catalog = effective.model_cost_catalog.value
    if catalog_declared(catalog):
        resolved_adapter = adapter
        if resolved_adapter is None:
            resolved_adapter = bmadloop_adapter_for_preference(effective.harness_preference.value)
        if resolved_adapter is None:
            resolved_adapter = str(doc["adapter"]["name"])
        provider = adapter_provider(resolved_adapter)
        ratio = resolve_cache_read_ratio(catalog, provider=provider)
        doc["limits"]["cache_read_weight"] = ratio

    return tomlkit.dumps(doc)


def _plain_json(value: object) -> object:
    """Recursively coerce policy mappings into JSON-serializable plain data."""
    if isinstance(value, Mapping):
        return {str(key): _plain_json(entry) for key, entry in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json(entry) for entry in value]
    return value


def _write_model_cost_catalog_sidecar(effective: policy.EffectivePolicy, loop_home: Path) -> None:
    """Persist declared catalog beside policy.toml for runtime telemetry."""
    sidecar_path = Path(loop_home) / ".bmad-loop" / _MODEL_COST_CATALOG_SIDECAR
    catalog = effective.model_cost_catalog.value
    if not catalog_declared(catalog):
        try:
            if sidecar_path.is_file():
                sidecar_path.unlink()
        except OSError:
            pass
        return
    try:
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(
            sidecar_path,
            json.dumps(_plain_json(catalog), sort_keys=True).encode("utf-8"),
        )
    except OSError, TypeError:
        return


def _load_model_cost_catalog(project: Path) -> dict[str, object] | None:
    sidecar_path = Path(project) / ".bmad-loop" / _MODEL_COST_CATALOG_SIDECAR
    try:
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError:
        return None
    if not catalog_declared(payload):
        return None
    return payload


def _read_policy_adapter_and_model(project: Path) -> tuple[str | None, str | None]:
    policy_path = Path(project) / ".bmad-loop" / "policy.toml"
    try:
        doc = tomlkit.parse(policy_path.read_text(encoding="utf-8"))
    except OSError, UnicodeDecodeError:
        return None, None
    adapter_table = doc.get("adapter")
    if not isinstance(adapter_table, tomlkit.items.Table):
        return None, None
    adapter_name = adapter_table.get("name")
    model_name = adapter_table.get("model")
    dev_table = adapter_table.get("dev")
    if isinstance(dev_table, tomlkit.items.Table):
        dev_model = dev_table.get("model")
        if isinstance(dev_model, str) and dev_model:
            model_name = dev_model
    adapter = adapter_name if isinstance(adapter_name, str) and adapter_name else None
    model = model_name if isinstance(model_name, str) and model_name else None
    return adapter, model


def _token_counts_from_task(task: object) -> TokenCounts | None:
    tokens = getattr(task, "tokens", None)
    if tokens is None:
        return None
    return TokenCounts(
        input_tokens=int(getattr(tokens, "input_tokens", 0) or 0),
        output_tokens=int(getattr(tokens, "output_tokens", 0) or 0),
        cache_read_tokens=int(getattr(tokens, "cache_read_tokens", 0) or 0),
        cache_creation_tokens=int(getattr(tokens, "cache_creation_tokens", 0) or 0),
    )


def _usage_dollar_fields(
    *,
    catalog: dict[str, object],
    adapter_name: str | None,
    model_name: str | None,
    story_tokens: TokenCounts | None,
    layer_savings: LayerSavings | None,
) -> tuple[float | None, dict[str, float] | None]:
    provider = adapter_provider(adapter_name)
    if provider is None or story_tokens is None:
        return None, None
    price = resolve_model_price(catalog, provider=provider, model=model_name)
    if price is None:
        return None, None
    cost_usd = estimate_spend_usd(story_tokens, price)
    savings_usd: dict[str, float] | None = None
    if layer_savings is not None:
        savings_dict: dict[str, object] = {}
        if layer_savings.output_compression_saved is not None:
            savings_dict["output_compression_saved"] = layer_savings.output_compression_saved
        if layer_savings.wire_compression_saved is not None:
            savings_dict["wire_compression_saved"] = layer_savings.wire_compression_saved
        graph_stats = layer_savings.graph_hits_vs_file_reads
        if isinstance(graph_stats, tuple):
            hits, reads = graph_stats
            savings_dict["graph_hits"] = hits
            savings_dict["file_reads"] = reads
        elif isinstance(graph_stats, str):
            savings_dict["graph_hits_vs_file_reads"] = graph_stats
        if layer_savings.derived_context_cache_hits is not None:
            savings_dict["derived_context_cache_hits"] = layer_savings.derived_context_cache_hits
        if layer_savings.planning_graph_tokens_saved is not None:
            savings_dict["planning_graph_tokens_saved"] = layer_savings.planning_graph_tokens_saved
        if savings_dict:
            computed = estimate_layer_savings_usd(savings_dict, price)
            savings_usd = computed or None
    return cost_usd, savings_usd


class HarnessPolicyWriteError(PyforgeError, Exception):
    """Raised by ``write_policy_toml`` when the atomic write to
    ``<loop_home>/.bmad-loop/policy.toml`` fails (an unwritable loop home, a
    non-directory occupying ``.bmad-loop``, or any other ``OSError`` during
    the temp-file-then-``os.replace`` sequence). No ``MRS-*`` finding code is
    registered for this -- there is no CLI caller yet to convert an I/O
    failure into a ``Finding`` (that is a later story's concern); a plain
    exception is sufficient until one exists.

    Story 14.3, SPEC-pyforge-core CAP-5: gains ``PyforgeError`` as an
    additional base -- ``Exception`` stays in the MRO.
    """


def write_policy_toml(
    effective: policy.EffectivePolicy,
    loop_home: Path,
    *,
    difficulty: str | None = None,
    adapter: str | None = None,
    tier_resolution: TierLaunchResolution | None = None,
) -> Path:
    """The I/O boundary: render via ``render_policy_toml`` and atomically
    write ``<loop_home>/.bmad-loop/policy.toml`` whole via
    ``pyforge.core.atomic_write_bytes`` (Story 14.2, CAP-2 -- the one shared
    temp-file-then-``os.replace`` primitive, mkstemp-based) -- MINUS
    ``cli/config.py::materialize``'s write-once/content-hash/no-op logic,
    since this artifact is a fresh projection on every call, never
    content-addressed, never skipped. Never reads an existing file at that
    path first: every call fully replaces any prior content, including
    hand-edited or unrelated bytes. Creates ``<loop_home>/.bmad-loop`` if it
    does not already exist. Any ``OSError`` during the sequence is wrapped
    in ``HarnessPolicyWriteError`` rather than propagating raw.

    Like ``cli/config.py::materialize``, THE CALLER owns the gate deciding
    whether a given composition may be persisted at all (e.g. only
    OK-status compositions) -- this function writes whatever
    ``EffectivePolicy`` it is handed, subject only to
    ``render_policy_toml``'s own attempt-count floor.

    ``adapter`` (Story 6.5, FR-44) passes straight through to
    ``render_policy_toml``.
    """
    text = render_policy_toml(
        effective,
        difficulty=difficulty,
        adapter=adapter,
        tier_resolution=tier_resolution,
    )
    path = _atomic_write_policy_text(text, loop_home)
    _write_model_cost_catalog_sidecar(effective, loop_home)
    return path


def _atomic_write_policy_text(text: str, loop_home: Path) -> Path:
    """The shared temp-file-then-``os.replace`` mechanics ``write_policy_toml``
    (Story 1.10, a fresh whole render) and ``write_policy_document`` (Story
    3.12, a single-key patch of an already-on-disk document) both need to
    persist ``<loop_home>/.bmad-loop/policy.toml`` -- factored out of
    ``write_policy_toml``'s own prior body (its sole caller until this
    story) so the two writers cannot drift out of agreement over how the
    write is made durable or how a failure is wrapped. Creates
    ``<loop_home>/.bmad-loop`` if it does not already exist; any ``OSError``
    during the sequence is wrapped in ``HarnessPolicyWriteError`` rather than
    propagating raw. Mirrors ``cli/config.py::materialize``'s temp-file-
    then-``os.replace`` mechanics -- MINUS its write-once/content-hash/no-op
    logic, since this artifact is a fresh projection on every call, never
    content-addressed, never skipped."""
    bmad_loop_dir = Path(loop_home) / ".bmad-loop"
    target_path = bmad_loop_dir / "policy.toml"
    try:
        atomic_write_bytes(target_path, text.encode("utf-8"))
        return target_path
    except OSError as exc:
        raise HarnessPolicyWriteError(f"cannot write policy.toml to {bmad_loop_dir}: {exc}") from exc


def _resolve_wrapper_binary(binary: str, fallback_bin_dirs: tuple[str, ...], repo_root: Path | None) -> str | None:
    """Resolve a wire-wrapper binary the same way dispatch does."""
    on_path = shutil.which(binary)
    if on_path is not None:
        return on_path
    if repo_root is None:
        return None
    for rel_dir in fallback_bin_dirs:
        candidate = Path(repo_root) / rel_dir / binary
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _render_bmadloop_wire_profile_overlay(
    *,
    adapter_name: str,
    wrapper_binary: str,
    wrapper_argv: tuple[str, ...],
    wire_env: Mapping[str, str],
) -> str:
    """Build a complete bmad-loop profile overlay that prepends headroom.

    Project overlays replace the packaged profile wholesale, so this copies
    the packaged ``bmad_loop.data.profiles/<adapter>.toml`` and rewrites only
    ``binary``, ``launch_args``, and ``env`` -- the three fields
    ``adapters/profile.py`` exposes at the launch seam (Story 33.3).
    """
    from importlib import resources

    packaged = resources.files("bmad_loop.data").joinpath(f"profiles/{adapter_name}.toml")
    doc = tomlkit.parse(packaged.read_text(encoding="utf-8"))
    doc["binary"] = wrapper_binary
    doc["launch_args"] = list(wrapper_argv)
    env_table = doc.get("env")
    if not isinstance(env_table, tomlkit.items.Table):
        env_table = tomlkit.table()
    for key, value in wire_env.items():
        env_table[key] = value
    doc["env"] = env_table
    header = (
        "# marshal Story 33.3 wire-compression overlay — written by factory spin\n"
        "# Do not hand-edit; the next spin overwrites this file when the wire layer is on.\n"
    )
    return header + tomlkit.dumps(doc)


def write_spin_wire_profile_overlay(loop_home: Path, adapter_name: str, text: str) -> Path:
    """Atomically write ``<loop_home>/.bmad-loop/profiles/<adapter>.toml``."""
    profiles_dir = Path(loop_home) / ".bmad-loop" / "profiles"
    target = profiles_dir / f"{adapter_name}.toml"
    try:
        atomic_write_bytes(target, text.encode("utf-8"))
    except OSError as exc:
        raise HarnessPolicyWriteError(f"cannot write wire profile overlay to {target}: {exc}") from exc
    return target


def attempt_spin_wire_layer(
    *,
    loop_home: Path,
    adapter_name: str,
    wire_layer: Mapping[str, object] | None,
    repo_root: Path | None,
) -> WireWrap:
    """Story 33.3: try to enable wire compression on ``factory spin``.

    When the declared ``wire`` layer is enabled and the configured bmad-loop
    adapter has a marshal harness profile with a reversible ``[wrapper]``,
    render a loop-home profile overlay that points ``binary`` at headroom and
    sets ``launch_args`` to the wrapper argv prefix. Otherwise degrade with a
    named reason -- never a silent no-op.
    """
    profile_stem = PROFILE_BY_BMADLOOP_ADAPTER.get(adapter_name)
    if profile_stem is None:
        enabled = resolve_wire_enabled((wire_layer or {}).get("enabled", False), wrapper_declared=False)
        if not enabled:
            return WireWrap(applied=False)
        return WireWrap(
            applied=False,
            reason=(
                f"bmad-loop adapter {adapter_name!r} has no marshal harness "
                "profile with a wire-compression wrapper declaration"
            ),
            aggressiveness=(
                wire_layer.get("aggressiveness") if isinstance((wire_layer or {}).get("aggressiveness"), str) else None
            ),
        )

    marshal_profiles = load_packaged_profiles()
    profile = marshal_profiles.get(profile_stem)
    if profile is None:
        enabled = resolve_wire_enabled((wire_layer or {}).get("enabled", False), wrapper_declared=False)
        if not enabled:
            return WireWrap(applied=False)
        return WireWrap(
            applied=False,
            reason=f"marshal harness profile {profile_stem!r} is missing",
            aggressiveness=(
                wire_layer.get("aggressiveness") if isinstance((wire_layer or {}).get("aggressiveness"), str) else None
            ),
        )

    wrapper_binary_path = None
    if profile.wrapper is not None:
        wrapper_binary_path = _resolve_wrapper_binary(
            profile.wrapper.binary,
            profile.wrapper.fallback_bin_dirs,
            repo_root,
        )

    wire = resolve_wire_wrap(
        profile,
        wire_layer=wire_layer,
        home=loop_home,
        wrapper_binary_path=wrapper_binary_path,
    )
    if not wire.applied or profile.wrapper is None:
        return wire

    if wire.store_dir is not None:
        try:
            Path(wire.store_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return WireWrap(
                applied=False,
                reason=(
                    f"wire-compression store {wire.store_dir!r} could not be "
                    f"created: {exc} -- the layer is off for this launch"
                ),
                aggressiveness=wire.aggressiveness,
            )

    try:
        resolved_wrapper_argv = substitute_wire_port(profile.wrapper.argv, worktree=loop_home)
        overlay = _render_bmadloop_wire_profile_overlay(
            adapter_name=adapter_name,
            wrapper_binary=profile.wrapper.binary,
            wrapper_argv=resolved_wrapper_argv,
            wire_env=wire.env,
        )
        write_spin_wire_profile_overlay(loop_home, adapter_name, overlay)
    except (HarnessPolicyWriteError, OSError, KeyError, ValueError) as exc:
        return WireWrap(
            applied=False,
            reason=(f"could not write bmad-loop wire profile overlay for {adapter_name!r}: {exc}"),
            aggressiveness=wire.aggressiveness,
        )

    return wire


# Story 3.12 (retry escalation, AD-26) -- _POLICY_TEMPLATE's own baseline
# [adapter.review].model value (see that constant's [adapter.review] block
# above), exposed here so cli/spin.py::run_resume can fall back to it on the
# rare on-disk policy.toml that is somehow missing [adapter.review]/its
# model key entirely. Never expected in practice: every rendered
# policy.toml carries [adapter.review].model unconditionally (the template's
# own static baseline, only ever OVERWRITTEN by FR-51 tier-batching, never
# removed) -- but a hand-edited or pre-this-story file is not a case this
# story's own read-back may crash on. Named without a leading underscore
# (unlike _POLICY_TEMPLATE itself) because it is consumed cross-module,
# mirroring HARNESS_VERSION_RANGE_TEXT's identical "a constant this module
# owns, exported for a cross-module caller" convention.
#
# DERIVED from _POLICY_TEMPLATE itself, never hand-duplicated (review
# finding): this baseline has already changed once in this project's
# history (see _POLICY_TEMPLATE's own "[adapter.review]" comment,
# "2026-08-02: ..."), and a second, independent literal here would silently
# desync on the next such change. Parsed once at import time -- a malformed
# _POLICY_TEMPLATE is a module-load-time failure everywhere else in this
# file already assumes cannot happen (it is a hardcoded source constant,
# never user input).
ADAPTER_REVIEW_MODEL_STOCK_DEFAULT: str = tomlkit.parse(_POLICY_TEMPLATE)["adapter"]["review"]["model"]


def write_policy_document(doc: tomlkit.TOMLDocument, loop_home: Path) -> Path:
    """Story 3.12's own narrow sibling to ``write_policy_toml`` (retry
    escalation, AD-26): atomically writes an ALREADY-MUTATED ``tomlkit``
    document -- ``cli/spin.py::run_resume``'s own ``tomlkit.parse()`` of the
    loop home's EXISTING ``.bmad-loop/policy.toml``, with exactly one key
    patched in place (``[adapter].model``, floor-raised to
    ``[adapter.review].model``) -- rather than a document this module
    freshly rendered end to end from an ``EffectivePolicy``.

    ``write_policy_toml``'s own signature does not fit this shape: it always
    calls ``render_policy_toml`` first, which re-derives the WHOLE file from
    Marshal's own composed policy and would silently discard any
    instance-local content the running harness itself persisted into the
    on-disk file since the last render (the ``[tui]`` pane-geometry keys,
    the ``[mux].backend`` line -- see this module's own docstring). A caller
    that already holds the on-disk document (read via ``tomlkit.parse``,
    preserving every comment and every harness-owned key untouched) and has
    mutated only the one key it means to change needs a WRITE primitive that
    re-derives nothing else -- this is that primitive, reusing the exact
    same temp-file-then-``os.replace`` mechanics and the exact same
    ``HarnessPolicyWriteError``-wrapping contract ``write_policy_toml``
    already has (``_atomic_write_policy_text`` above, so the two writers
    cannot drift out of agreement over how a policy.toml write is made
    durable).

    This is a narrow, deliberate exception to this module's own "always
    rendered whole, never patched or hand-edited" derived-artifact
    discipline (AD-12): Story 3.12's floor-raise touches exactly one
    already-existing key, never introduces a new one, and the caller is
    responsible for reading the SAME file this writes back to, never
    composing a divergent view of it (see that story's own spec Design
    Notes for why a resume's own floor-raise reads and rewrites the SAME
    on-disk file rather than re-composing from ``EffectivePolicy``)."""
    text = tomlkit.dumps(doc)
    return _atomic_write_policy_text(text, loop_home)


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
_HARNESS_MIN_VERSION: tuple[int, ...] = (0, 11, 0)
_HARNESS_MAX_MINOR_EXCLUSIVE: tuple[int, ...] = (0, 13)
HARNESS_VERSION_RANGE_TEXT = ">=0.11.0,<0.13"


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

# Story 24.1 (FR-195 CAP-1): ``bmad-loop list --json``'s per-run ``status`` is
# ``discover_runs``' liveness-aware vocabulary (``engine_liveness`` applied
# internally upstream). ``status --json``'s own ``status`` field is run-state
# only and cannot distinguish alive from interrupted engines.
_LIST_STATUS_TO_ENGINE_LIVENESS: dict[str, EngineLiveness] = {
    "running": "alive",
    "interrupted": "dead",
    "finished": "dead",
    "stopped": "dead",
    "crashed": "dead",
    "paused": "dead",
    "unknown": "unknown",
}

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


class HarnessError(PyforgeError, Exception):
    """Raised by ``BmadLoopHarness`` methods that are documented to raise
    (``multiplexer_backend_available``, ``adapter_binary``,
    ``adapter_seed_files``, ``adapter_first_run_note``) when the lazy
    ``bmad_loop`` import fails, or the harness's own typed error
    (``ProfileError``, a ``bmad_loop.adapters.multiplexer.MultiplexerError``)
    is raised. Never a raw ``ImportError``/harness-internal exception type --
    ``cli/init.py`` only ever needs to catch this ONE class (AD-3's own
    seam: nothing outside this module names a ``bmad_loop`` exception
    type).

    Story 14.3, SPEC-pyforge-core CAP-5: gains ``PyforgeError`` as an
    additional base -- ``Exception`` stays in the MRO."""


def _run(args: list[str], *, timeout_s: float = _VERSION_TIMEOUT_S) -> ProcessResult | None:
    """Story 14.4, SPEC-pyforge-core CAP-6: delegates the actual launch to
    ``pyforge.core.process.PosixProcess().run(...)`` -- mirrors
    ``adapters/vcs_git.py::_run``'s identical delegation (``cwd=Path.cwd()``,
    never relying on a caller-supplied working directory). Unlike that
    module's version, every failure mode here (missing binary, launch
    failure, a hung process) degrades to ``None`` rather than raising --
    ``harness_version`` is documented to never raise, so there is no typed
    exception for a caller to catch."""
    try:
        return PosixProcess().run(args, cwd=Path.cwd(), timeout_s=timeout_s)
    except ProcessError:
        return None


class BmadLoopHarness:
    """``ports.HarnessPort``'s sole in-tree implementation and the default
    loop/runner plugin on ``pyforge.core.hooks`` (Story 26.1)."""

    hook_spec: str = LOOP_RUNNER_HOOK_SPEC.name
    owner: str = LOOP_RUNNER_HOOK_SPEC.owner
    plugin_id: str = DEFAULT_LOOP_RUNNER_PLUGIN_ID

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        """Named ``before`` / ``after`` / ``around`` point. ``around`` may
        run ``context["next"]``. A passed loop is not a Warden PR-gate
        verdict. Point names are recorded on ``self.calls`` (DummyPlugin
        shape) so invoke coverage is not vacuous."""
        self.calls = getattr(self, "calls", [])
        self.calls.append(point)
        if point == "around":
            nxt = context.get("next")
            if callable(nxt):
                return nxt(context)
        return context

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
    def _run_argv(*, epic: int | None, story: str | None, max_count: int | None) -> list[str]:
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
        # Story 14.4, SPEC-pyforge-core CAP-6: delegates the log-open +
        # detached-``Popen`` recipe to ``pyforge.core.process.PosixProcess.
        # spawn_detached`` -- the generic primitive that recipe was itself
        # modeled on (that primitive's own docstring names this method as
        # its mirror). ``spawn_detached`` forces the identical
        # ``PYTHONUNBUFFERED=1`` env fix this method always has (see the
        # review finding below, still true) PLUS ``PYTHONSAFEPATH=1`` -- a
        # no-op for this call (``bmad-loop`` is an installed console-script
        # entry point, not a ``python -m`` invocation, so ``project`` never
        # lands on its ``sys.path[0]`` either way), harmless to inherit from
        # the now-shared recipe. ``spawn_detached`` raises ONE
        # ``ProcessError`` for either of the two distinct failures the
        # original two-step open-then-Popen code raised separately (a log
        # that could not be opened, or a launch failure) -- distinguished
        # here by its own message prefix so both original ``HarnessError``
        # messages survive unchanged.
        try:
            pid = PosixProcess().spawn_detached(argv, cwd=project, log_path=log_path)
        except ProcessError as exc:
            cause = exc.__cause__
            # `cause` is `None` for `PosixProcess`'s own empty-argv guard (it
            # raises with no `from` clause) -- `exc` itself already carries
            # that message, so fall back to it rather than stringifying/
            # chaining from a bare `None` (Story 14.4 review finding, mirrors
            # vcs_git.py/forge_gh.py's own `_run`).
            if str(exc).startswith("cannot open log"):
                raise HarnessError(f"cannot open spin log {log_path}: {cause or exc}") from (cause or exc)
            raise HarnessError(f"cannot launch bmad-loop run: {cause or exc}") from (cause or exc)

        harness_run_id = self._poll_for_harness_run_id(log_path)
        return SpinResult(pid=pid, harness_run_id=harness_run_id)

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
        # Story 14.4, SPEC-pyforge-core CAP-6: a SANCTIONED exception, left
        # unmigrated -- `pyforge.core.process.PosixProcess.run` always
        # captures stdout/stderr/stdin, but `attach` must inherit this
        # process's OWN stdio so an operator can interact with the attached
        # session; the shared primitive offers no interactive-passthrough
        # mode (CAP-6's own "no primitive earns a place on one caller").
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
        # Story 14.4, SPEC-pyforge-core CAP-6: a SANCTIONED exception, left
        # unmigrated -- the ``--foreground`` counterpart to ``spin``, same
        # interactive-stdio-passthrough reason as ``attach`` above (an
        # operator watches/interrupts the run live); the shared
        # ``PosixProcess.run`` always captures.
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
        no supervisor watching an unattended ephemeral smoke run).

        Story 14.4, SPEC-pyforge-core CAP-6: a SANCTIONED exception, left
        unmigrated -- this call's bounded ``timeout_s`` PLUS its
        already-open, caller-owned ``log_file`` redirect fits neither
        ``PosixProcess.run`` (captures to its own return value, not a
        caller's file handle) nor ``.spawn_detached`` (fire-and-forget, no
        timeout, no returncode) cleanly; forcing it into either risks a
        behavior regression this story does not need to take on (spec's own
        Never section)."""
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
        # Story 14.4, SPEC-pyforge-core CAP-6: delegates to
        # ``pyforge.core.process.PosixProcess().run(...)``, which already
        # applies the identical ``stdin=DEVNULL`` discipline this call used
        # to spell out itself, and folds every launch failure (a timeout, an
        # embedded NUL byte, any other launch ``OSError``) into ONE
        # ``ProcessError`` -- distinguished below by cause type so both
        # original ``HarnessError`` messages survive unchanged.
        try:
            result = PosixProcess().run(["bmad-loop", "stop", run_id], cwd=project, timeout_s=_STOP_TIMEOUT_S)
        except ProcessError as exc:
            cause = exc.__cause__
            if isinstance(cause, subprocess.TimeoutExpired):
                raise HarnessError(f"bmad-loop stop {run_id} timed out after {_STOP_TIMEOUT_S}s: {cause}") from cause
            raise HarnessError(f"cannot launch bmad-loop stop: {cause}") from cause
        # A non-zero exit is the ordinary "did not stop" shape (already
        # finished, or some other non-launch failure the installed 0.9.0
        # `cmd_stop` reports) -- never raised, matching this Protocol's own
        # documented split.
        return result.returncode == 0

    def resume(self, project: Path, run_id: str, *, log_path: Path) -> int:
        # Story 14.4, SPEC-pyforge-core CAP-6: a SANCTIONED exception, left
        # unmigrated -- this Popen's own log open below is APPEND ("ab"),
        # never truncate, because `log_path` may be a wedged run's own
        # existing `harness.log` (see that open's own comment); `PosixProcess
        # .spawn_detached` hardcodes `"wb"` truncate, so routing through it
        # would destroy the prior run's output at the exact moment it is
        # most valuable. The shared primitive offers no append-mode
        # parameter (CAP-6's own "no primitive earns a place on one caller").
        #
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
            raise HarnessError(f"cannot open resume log {str(log_path)!r}: {exc}") from exc
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
                log_file.write(f"\n--- marshal: resuming {run_id} ---\n".encode("utf-8"))
                log_file.flush()
            except OSError, ValueError:
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

    def engine_liveness(self, project: Path, run_id: str) -> EngineLiveness:
        """Story 24.1 (FR-195 CAP-1): tri-state engine probe via the supported
        ``bmad-loop`` CLI ``--json`` surfaces only -- never ``engine.pid``,
        never ``bmad_loop`` imports. See ``HarnessPort.engine_liveness``."""
        try:
            status_result = PosixProcess().run(
                ["bmad-loop", "status", run_id, "--json"],
                cwd=project,
                timeout_s=_STOP_TIMEOUT_S,
            )
        except ProcessError:
            return "unknown"
        if status_result.returncode != 0:
            return "unknown"
        try:
            list_result = PosixProcess().run(
                ["bmad-loop", "list", "--json"],
                cwd=project,
                timeout_s=_STOP_TIMEOUT_S,
            )
        except ProcessError:
            return "unknown"
        if list_result.returncode != 0:
            return "unknown"
        try:
            document = json.loads(list_result.stdout)
        except json.JSONDecodeError, ValueError:
            return "unknown"
        runs = document.get("runs")
        if not isinstance(runs, list):
            return "unknown"
        for entry in runs:
            if not isinstance(entry, dict):
                continue
            if entry.get("run_id") != run_id:
                continue
            status = entry.get("status")
            if isinstance(status, str):
                mapped = _LIST_STATUS_TO_ENGINE_LIVENESS.get(status)
                if mapped is not None:
                    return mapped
            return "unknown"
        return "unknown"

    def run_terminal_verdict(self, project: Path, run_id: str) -> HarnessRunTerminalVerdict:
        """Story 5.11 (FR-196/AD-5): classify a launch-pid-less harness run via
        bmad-loop's own ``state.json`` only -- see ``HarnessPort.run_terminal_
        verdict``."""
        run_dir = Path(project) / ".bmad-loop" / "runs" / run_id
        try:
            from bmad_loop.journal import load_state
        except ImportError:
            return "unknown"
        try:
            state = load_state(run_dir)
        except OSError, ValueError, KeyError, TypeError:
            return "unknown"
        if bool(state.finished):
            return "terminal"
        return "non_terminal"

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
            catalog = _load_model_cost_catalog(project)
            adapter_name, model_name = _read_policy_adapter_and_model(project)
            cache_read_weight = state.cache_read_weight()
            if catalog is not None:
                provider = adapter_provider(adapter_name)
                cache_read_weight = resolve_cache_read_ratio(
                    catalog,
                    provider=provider,
                    model=model_name,
                    default=cache_read_weight,
                )
            if not math.isfinite(cache_read_weight):
                return None
            non_terminal = [task for task in state.tasks.values() if not task.terminal]
            story_key: str | None = None
            story_weighted_tokens: int | None = None
            story_token_counts: TokenCounts | None = None
            if len(non_terminal) == 1:
                task = non_terminal[0]
                if task.story_key:
                    story_key = task.story_key
                    story_token_counts = _token_counts_from_task(task)
                    if story_token_counts is not None:
                        story_weighted_tokens = weighted_total(story_token_counts, cache_read_weight)
                    else:
                        story_weighted_tokens = task.tokens.weighted_total(cache_read_weight)
            run_weighted_tokens = 0
            for task in state.tasks.values():
                counts = _token_counts_from_task(task)
                if counts is not None:
                    run_weighted_tokens += weighted_total(counts, cache_read_weight)
                else:
                    run_weighted_tokens += task.tokens.weighted_total(cache_read_weight)
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
        # Story 28.4: Gather per-layer savings telemetry (CAP-7)
        # This collects available savings stats where layers are active
        layer_savings = self._gather_layer_savings(run_dir)

        cost_estimate_usd: float | None = None
        layer_savings_usd: dict[str, float] | None = None
        if catalog is not None:
            cost_estimate_usd, layer_savings_usd = _usage_dollar_fields(
                catalog=catalog,
                adapter_name=adapter_name,
                model_name=model_name,
                story_tokens=story_token_counts,
                layer_savings=layer_savings,
            )

        return UsageSnapshot(
            story_key=story_key,
            story_weighted_tokens=story_weighted_tokens,
            run_weighted_tokens=run_weighted_tokens,
            sample_path=run_dir / "state.json",
            layer_savings=layer_savings,
            cost_estimate_usd=cost_estimate_usd,
            layer_savings_usd=layer_savings_usd,
        )

    def _gather_layer_savings(self, run_dir: Path) -> LayerSavings | None:
        """Story 28.4 / 33.1: Gather per-layer savings telemetry (CAP-7)."""
        try:
            from ..core import layer_savings_sources as sources

            home = sources.loop_home_from_run_dir(run_dir)
            output_compression_saved = self._get_caveman_savings(home)
            wire_compression_saved = self._get_headroom_savings(home)
            graph_hits_vs_file_reads = self._get_codegraph_stats(home)
            derived_context_cache_hits = self._get_cocoindex_stats(home)
            planning_graph_tokens_saved = self._get_graphifyy_savings(home)

            fields = (
                output_compression_saved,
                wire_compression_saved,
                graph_hits_vs_file_reads,
                derived_context_cache_hits,
                planning_graph_tokens_saved,
            )
            if not any(value is not None for value in fields):
                return None
            return LayerSavings(
                output_compression_saved=output_compression_saved,
                wire_compression_saved=wire_compression_saved,
                graph_hits_vs_file_reads=graph_hits_vs_file_reads,
                derived_context_cache_hits=derived_context_cache_hits,
                planning_graph_tokens_saved=planning_graph_tokens_saved,
            )
        except Exception:
            return None

    def _get_caveman_savings(self, home: Path) -> int | str | None:
        from ..core.layer_savings_sources import read_caveman_output_saved

        return read_caveman_output_saved(home)

    def _get_headroom_savings(self, home: Path) -> int | str | None:
        from ..core.layer_savings_sources import read_headroom_wire_saved

        return read_headroom_wire_saved(home)

    def _get_codegraph_stats(self, home: Path) -> tuple[int, int] | str | None:
        from ..core.layer_savings_sources import read_codegraph_hits_vs_reads

        return read_codegraph_hits_vs_reads(home)

    def _get_cocoindex_stats(self, home: Path) -> int | str | None:
        from ..core.layer_savings_sources import read_cocoindex_cache_hits

        return read_cocoindex_cache_hits(home)

    def _get_graphifyy_savings(self, home: Path) -> int | str | None:
        from ..core.layer_savings_sources import read_planning_graph_tokens_saved

        return read_planning_graph_tokens_saved(home)

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
        except ValueError, LookupError, TypeError:
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
        except ValueError, TypeError:
            return BmadLoopHarness._redact_text(text)
        if not isinstance(parsed, dict):
            return BmadLoopHarness._redact_text(text)
        try:
            return to_redacted(parsed).text
        except ValueError, LookupError, TypeError:
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
            paused_reason = self._redact_text(state.paused_reason) if state.paused_reason is not None else None
            escalated_spec_file: str | None = None
            escalated_task_phase: str | None = None
            escalated_preserve_ref: str | None = None
            if paused_story_key is not None:
                paused_task = state.tasks.get(paused_story_key)
                if paused_task is not None:
                    escalated_spec_file = paused_task.spec_file
                    escalated_task_phase = paused_task.phase.value
                    # Story 25.5 (CAP-5): the escalated story's own recovery
                    # pointer -- `StoryTask.preserve_ref` VERBATIM (a git
                    # ref like `commit_sha`, never session-authored free
                    # text, so no redaction; never re-validated against git
                    # here -- bmad-loop's own `status_document` documents
                    # the identical report-verbatim contract).
                    escalated_preserve_ref = paused_task.preserve_ref
            # Story 25.5 (CAP-5): `RunState.sweeps_refused` verbatim --
            # trigger -> reason slug, the CLOSED `model.SWEEP_REFUSED_*`
            # vocabulary (slugs by upstream design, precisely so run state
            # stays sanitizer-safe -- never free text). `{}` = nothing
            # refused; an unreadable state.json degrades this WHOLE
            # snapshot to None via the widened guard below, never to a
            # fabricated `{}`-clean.
            sweeps_refused = dict(state.sweeps_refused)
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
                        # Story 25.5: verbatim, unredacted -- a git ref
                        # (see `escalated_preserve_ref` above).
                        preserve_ref=task.preserve_ref,
                        # Story 20.4: proactive intent-gap capture reads
                        # these off every task each tick.
                        worktree_path=task.worktree_path,
                        baseline_commit=task.baseline_commit,
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
                        reason=(self._redact_text(task.defer_reason) if task.defer_reason is not None else None),
                        attempt=task.attempt,
                        branch=task.branch,
                        worktree_path=task.worktree_path,
                        spec_file=task.spec_file,
                        review_cycle=task.review_cycle,
                        preserve_ref=task.preserve_ref,
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
            escalated_preserve_ref=escalated_preserve_ref,
            sweeps_refused=sweeps_refused,
        )

    def resolution_reference(self, project: Path, run_id: str, story_key: str) -> str | None:
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
        except OSError, ValueError, TypeError:
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


def resolve_loop_runner(
    plugin_id: str = DEFAULT_LOOP_RUNNER_PLUGIN_ID,
    *,
    registry: PluginRegistry | None = None,
) -> HarnessPort:
    """Production default factory for an injected ``HarnessPort``.

    Selects a plugin registered on ``LOOP_RUNNER_HOOK_SPEC`` by
    ``plugin_id`` (``PluginRegistry`` does not store entry-point names).
    When ``registry`` is omitted, loads ``pyforge.core.hooks`` entry
    points and in-tree-registers ``BmadLoopHarness()`` (idempotent) so
    unit tests still resolve when the wheel's entry point is not visible.
    A missing id falls back to a new ``BmadLoopHarness()``.
    """
    if registry is None:
        registry = PluginRegistry()
        registry.load_entry_points()
        registry.register(BmadLoopHarness())
    for plugin in registry.plugins:
        if getattr(plugin, "hook_spec", None) != LOOP_RUNNER_HOOK_SPEC.name:
            continue
        if getattr(plugin, "plugin_id", None) == plugin_id:
            return plugin  # type: ignore[return-value]
    return BmadLoopHarness()
