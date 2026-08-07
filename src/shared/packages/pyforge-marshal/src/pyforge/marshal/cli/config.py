"""``marshal config`` (Story 1.3, FR-54) -- the CLI's I/O boundary for
``core/policy.py``: resolves the project slug, reads an optional
``--project-policy`` TOML file, parses repeatable ``--set KEY=VALUE``
flags, calls ``policy.compose()``, and renders the result through the
envelope (AD-14) with secret redaction applied. Also owns ``materialize()``
-- the write-once, content-addressed policy artifact writer (AD-35). File
reads, env var reads, and disk writes all belong here, never in
``core/policy.py`` (AD-4).

``project_slug`` resolution order: ``--project`` flag, then the
``BMAD_ACTIVE_PROJECT`` env var (AD-2's one sanctioned env var), then an
empty string if neither is set. Slug SHAPE validation lives in
``compose()`` (FR-53's shape-only spirit): a missing slug still composes
and prints every field but reports the registered ``MRS-POLICY-005``
(warn -- exit 0) and omits the project-derived worktree seed path rather
than generating a ``projects//`` garbage path; a malformed slug (path
separators, ``.``/``..``) reports ``MRS-POLICY-006`` (error) and likewise
omits the project-derived path.

``--set`` accepts only the 5 SCALAR fields
(``gate_mode``/``merge_subject_template``/``max_dev_attempts``/
``max_review_cycles``/``max_followup_reviews``) meaningfully: the 3
int-typed fields are ``int()``-coerced here; a coercion failure is left as
the raw string rather than raised, so ``policy.compose()``'s own uniform
validation reports it as a malformed value (``MRS-POLICY-003``) through the
same path every other malformed value takes. The FOUR list/mapping-typed
fields (``verify_commands``, ``worktree_seed_paths``, ``model_tier_map``,
``frozen_surfaces``) are not ``--set`` targets at all: a ``--set`` naming
one is a clean usage error at the flag boundary (``EXIT_USAGE``) telling
the operator to supply it via the ``--project-policy`` TOML layer --
letting it flow into ``compose()`` as a plain string would come back as a
"malformed value" finding, a categorically wrong diagnostic for a key no
string value could ever satisfy. Unknown keys still flow through to
``compose()`` and report ``MRS-POLICY-001`` like any other layer's unknown
key.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import tomllib
from collections.abc import Mapping
from pathlib import Path

from ..adapters.harness_bmadloop import HarnessPolicyWriteError, write_policy_toml
from ..core import policy
from ..core.landing import LandingRule, landing_rule_to_dict
from ..core.model import Finding, Severity, Status, build_envelope, status_for
from ..core.verdict import compute_verdict, exit_code_for

ENV_ACTIVE_PROJECT = "BMAD_ACTIVE_PROJECT"

# Only these 3 of the 5 --set-eligible scalar keys are int-typed; the other
# two (gate_mode, merge_subject_template) stay plain strings.
_INT_SET_KEYS = frozenset({"max_dev_attempts", "max_review_cycles", "max_followup_reviews"})

# The subset of `_UNSETTABLE_KEYS` that is scalar-typed but excluded from
# `--set` for the "no AC asks for a CLI override surface" reason, never the
# "no string value could satisfy this validator" reason the 4 list/
# mapping-typed keys share (`_parse_set_item`'s own reason-branching
# message). `idle_threshold_minutes` (Story 3.5) plus Story 3.6's 4 budget
# ceilings.
_PROJECT_POLICY_ONLY_KEYS = frozenset(
    {
        "idle_threshold_minutes",
        "max_tokens_per_story",
        "max_tokens_per_run",
        "max_wall_clock_minutes_per_story",
        "max_wall_clock_minutes_per_run",
        # Story 4.7's 3 scalar-typed landing keys (AD-40) -- same reason as
        # the 5 above: no AC asks for a CLI override surface for any of
        # them, so `--project-policy` is the only way to set them.
        # `landing_rules` is excluded from THIS set (it is list/mapping-
        # typed, joining `_UNSETTABLE_KEYS`'s other 5 for that reason
        # instead -- see the frozenset below).
        "landing_merge_strategy",
        "landing_branch_retirement",
        "landing_resync",
        # Story 4.4's `landing_base_branch` (AD-40) -- same reason as the 3
        # above: no AC asks for a CLI override surface for it.
        "landing_base_branch",
    }
)

# The 4 list/mapping-typed fields --set cannot express (no string value
# could ever satisfy their validators) PLUS `idle_threshold_minutes` (Story
# 3.5, review finding) PLUS Story 3.6's 4 budget-ceiling keys: a scalar this
# codebase deliberately excludes from `--set` for a DIFFERENT reason (no AC
# asks for a CLI override surface for any of these 5 -- see the
# `_FIELD_ORDER` comment below), but the comment there had said so for a
# while before this frozenset actually enforced it -- an unenforced
# `--set idle_threshold_minutes=...` reached `compose()` as a raw string and
# came back as a misleading "malformed value" finding (MRS-POLICY-003)
# instead of this same clean usage error. Naming any of these 9 keys on
# `--set` is a usage error, not a policy finding. See the module docstring.
_UNSETTABLE_KEYS = frozenset(
    {
        "verify_commands",
        "worktree_seed_paths",
        "model_tier_map",
        "frozen_surfaces",
        "idle_threshold_minutes",
        "max_tokens_per_story",
        "max_tokens_per_run",
        "max_wall_clock_minutes_per_story",
        "max_wall_clock_minutes_per_run",
        # Story 2.3's 5th list/mapping-typed field (AD-27) -- no string
        # value could satisfy `_valid_epic_surfaces`'s
        # `Mapping[str, tuple[str, ...]]` shape either, the same reason the
        # other 4 list/mapping-typed keys above are excluded.
        "epic_surfaces",
        # Story 4.7's `landing_rules` (AD-40) -- a tuple of LandingRule
        # objects, the same "no string value could ever satisfy this
        # validator" reason. `landing_merge_strategy`/`landing_branch_
        # retirement`/`landing_resync` are plain scalars excluded for the
        # OTHER reason instead (`_PROJECT_POLICY_ONLY_KEYS`, above).
        "landing_rules",
        "landing_merge_strategy",
        "landing_branch_retirement",
        "landing_resync",
        "landing_base_branch",
        # Story 4.5's `landing_resync_commands` (AD-40) -- a tuple of str,
        # the same "no string value could ever satisfy this validator"
        # reason `verify_commands` itself is excluded for.
        "landing_resync_commands",
        # Story 6.9's `mcp_servers` (AD-43) -- Mapping[str, {command, args?,
        # env?}], the same "no string value could ever satisfy this
        # validator" reason `model_tier_map`/`epic_surfaces` are excluded
        # for.
        "mcp_servers",
    }
)

# Field render order: the 9 static keys, then the 10 seed keys -- matches
# the spec's own enumeration order (Boundaries & Constraints, second
# bullet). `idle_threshold_minutes` (Story 3.5) and Story 3.6's 4 budget
# ceilings are deliberately NOT `--set` targets (unlike the other 5 scalar
# seed keys) -- no AC asks for a CLI override surface for any of them, and
# `marshal-policy.toml`'s project layer already covers "configurable"
# (FR-12/FR-13's own AC wording). Story 4.7's 4 landing keys (AD-40) follow
# `epic_surfaces` -- the spec's own Code Map enumeration order -- for the
# same reason: no `--set` surface, `marshal-policy.toml` only.
_FIELD_ORDER: tuple[str, ...] = (
    "verify_commands",
    "worktree_seed_paths",
    "merge_subject_template",
    "model_tier_map",
    "epic_surfaces",
    "landing_rules",
    "landing_merge_strategy",
    "landing_branch_retirement",
    "landing_resync",
    "landing_base_branch",
    "landing_resync_commands",
    "mcp_servers",
    "gate_mode",
    "frozen_surfaces",
    "max_dev_attempts",
    "max_review_cycles",
    "max_followup_reviews",
    "idle_threshold_minutes",
    "max_tokens_per_story",
    "max_tokens_per_run",
    "max_wall_clock_minutes_per_story",
    "max_wall_clock_minutes_per_run",
)


def add_config_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``config`` subcommand on ``main.py``'s subparser tree."""
    parser = subparsers.add_parser(
        "config",
        help="Compose and print Marshal's effective policy (AD-10/AD-16).",
        description=(
            "Composes Marshal's built-in defaults, an optional "
            "--project-policy TOML file, and repeated --set KEY=VALUE "
            "overrides into one EffectivePolicy, then prints every key's "
            "effective value and winning layer."
        ),
    )
    parser.add_argument(
        "--project-policy",
        type=Path,
        default=None,
        metavar="PATH",
        help="A TOML file supplying the project policy layer.",
    )
    parser.add_argument(
        "--project",
        default=None,
        metavar="SLUG",
        help=f"The active project slug; falls back to ${ENV_ACTIVE_PROJECT} when omitted.",
    )
    parser.add_argument(
        "--set",
        dest="set_",
        action="append",
        default=[],
        type=_parse_set_item,
        metavar="KEY=VALUE",
        help=(
            "Override one scalar policy key (gate_mode, "
            "merge_subject_template, max_dev_attempts, max_review_cycles, "
            "max_followup_reviews). Repeatable."
        ),
    )
    parser.add_argument(
        "--materialize",
        type=Path,
        default=None,
        metavar="DIR",
        help="Write the composed policy to DIR as a content-addressed, write-once JSON file.",
    )
    parser.add_argument(
        "--write-harness-policy",
        type=Path,
        default=None,
        metavar="LOOP_HOME",
        help=(
            "Render the composed policy into LOOP_HOME/.bmad-loop/policy.toml "
            "(the file bmad-loop hard-codes). Overwrites it whole."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.set_defaults(handler=run_config)


def _parse_set_item(item: str) -> tuple[str, str]:
    """``argparse`` ``type=`` validator for one ``--set`` occurrence: splits
    ``KEY=VALUE`` and raises ``argparse.ArgumentTypeError`` (a clean usage
    error, ``EXIT_USAGE`` -- argparse's own mechanism, matching how every
    other malformed flag on this CLI is already handled) if there is no
    ``=`` or the key is one of the 4 list/mapping-typed fields. A missing
    ``=`` carries no key to attach a policy value to, so silently dropping
    it (the previous behavior) gave the operator zero feedback. A
    list/mapping-typed key is rejected HERE, with the fix named, because
    the alternative -- letting the plain string reach ``compose()`` -- came
    back as "malformed value ... in the flag layer", sending the operator
    chasing value-format variations for a key that is not flag-settable at
    all."""
    key, sep, raw_value = item.partition("=")
    if not sep:
        raise argparse.ArgumentTypeError(f"--set {item!r} must be KEY=VALUE")
    if key in _UNSETTABLE_KEYS:
        # The message branches on WHY the key is unsettable (review finding):
        # 4 of the 9 are genuinely list/mapping-typed (no string value could
        # satisfy their validators), but `idle_threshold_minutes` and Story
        # 3.6's 4 budget ceilings are plain positive numbers excluded for an
        # entirely different reason -- no AC asks for a CLI override surface
        # for any of them. Telling an operator that a numeric key is
        # "list/mapping-typed" is a false statement about their own policy
        # vocabulary, and sends them looking for a type error that does not
        # exist.
        reason = (
            "the project-policy-only key"
            if key in _PROJECT_POLICY_ONLY_KEYS
            else "the list/mapping-typed key"
        )
        raise argparse.ArgumentTypeError(
            f"--set cannot target {reason} {key!r}; "
            "supply it via the --project-policy TOML layer"
        )
    return key, raw_value


def _parse_set_flags(raw_items: list[tuple[str, str]]) -> dict[str, object]:
    flags: dict[str, object] = {}
    for key, raw_value in raw_items:
        value: object = raw_value
        if key in _INT_SET_KEYS:
            try:
                value = int(raw_value)
            except ValueError:
                pass  # left as the raw str -- compose() reports it (MRS-POLICY-003)
        flags[key] = value
    return flags


def _iter_fields(effective: policy.EffectivePolicy):
    """Yield ``(key, PolicyField)`` for all 14 keys in ``_FIELD_ORDER``. Seed
    fields are read exclusively through ``seed_view()`` -- never through
    ``effective._seed`` directly (AD-26; guarded by
    ``tests/meta/test_ad26_seed_field_access_guard.py``)."""
    seed = effective.seed_view()
    for key in _FIELD_ORDER:
        if key in seed:
            yield key, seed[key]
        else:
            yield key, getattr(effective, key)


def _json_safe(value: object) -> object:
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, LandingRule):
        # Story 4.7 (AD-40): a LandingRule is a frozen dataclass, not a
        # Mapping/tuple -- render it explicitly rather than let json.dumps
        # crash on an unserializable object. Shared with `core/policy.py`'s
        # own `_to_plain` via `core/landing.py::landing_rule_to_dict`
        # (review finding P4) -- never hand-roll this field list a second
        # time.
        return landing_rule_to_dict(value)
    return value


def _policy_fields_payload(effective: policy.EffectivePolicy) -> dict[str, object]:
    """The flat 22-key document matching ``schemas/policy.json`` exactly:
    one ``{value, layer, raw_source}`` object per policy key, with any
    secret-shaped field's ``value``/``raw_source`` redacted."""
    payload: dict[str, object] = {}
    for key, field in _iter_fields(effective):
        payload[key] = {
            "value": _json_safe(policy.redact(key, field.value)),
            "layer": field.layer.value,
            "raw_source": _json_safe(policy.redact(key, field.raw_source)),
        }
    return payload


#: Where a project's policy layer lives, relative to the repo root. Tracked, so
#: a fresh clone and a newly provisioned loop home both have it -- unlike the
#: rendered `.bmad-loop/policy.toml`, which is a derived artifact (AD-12/AD-35)
#: and gitignored.
PROJECT_POLICY_RELPATH = "_bmad-output/projects/{slug}/planning-artifacts/marshal-policy.toml"


def repo_root() -> Path:
    """The repo root, resolved from this module's own location.

    `cli/config.py` -> ... -> `<repo>/src/shared/packages/pyforge-marshal/src/
    pyforge/marshal/cli/config.py`, so the root is 8 parents up. Derived rather
    than taken from CWD: `marshal config` is run from a loop home, from the main
    checkout, and from a story worktree, and a CWD-relative root would silently
    resolve to a different project's policy in two of the three.

    The index is asserted by `test_conventional_project_policy_path_lands_on_the_repo_root`
    -- an off-by-one here resolves to `<repo>/src` and every lookup silently
    misses, falling back to bare defaults with no verify command.
    """
    return Path(__file__).resolve().parents[8]


def conventional_project_policy_path(slug: str) -> Path:
    """The conventional project-policy path for ``slug``."""
    return repo_root() / PROJECT_POLICY_RELPATH.format(slug=slug)


class PolicyIOError(Exception):
    """Raised by ``materialize()``/``run_config()`` when a CLI-boundary I/O
    step fails (an unwritable ``--materialize`` target, an unreadable or
    non-UTF-8 ``--project-policy`` file, a foreign artifact squatting on the
    content-addressed path) -- registers as ``MRS-POLICY-004``. Never lets a
    raw ``OSError``/``UnicodeDecodeError``/``tomllib.TOMLDecodeError``
    propagate out of ``run_config()``, matching ``cli/main.py``'s own "never
    raise, clamp anything foreign" exit-relay contract."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.finding = Finding(code="MRS-POLICY-004", severity=Severity.ERROR, message=message)


def materialize(effective_policy: policy.EffectivePolicy, target_dir: Path) -> Path:
    """Write ``<target_dir>/policy-<content_hash>.json`` via
    write-to-a-temp-file-then-``os.replace`` (atomic) -- AD-35's write-once
    artifact. A no-op if that exact path already exists AS A FILE **with the
    expected bytes** -- content-addressing only guarantees identical content
    for files written by a cooperating atomic writer, so the existing bytes
    are compared rather than trusted: a truncated, hand-edited, or foreign
    file squatting on the content-addressed name raises ``PolicyIOError``
    instead of being blessed as a successful materialization forever. On the
    true no-op path the existing file's mtime is left untouched and no write
    is attempted at all. A non-file (e.g. a directory) occupying the path,
    or any ``mkdir``/temp-file/write failure, likewise raises
    ``PolicyIOError`` rather than an uncaught ``OSError``.

    THE CALLER owns the persist-only-ok-compositions gate: this function
    takes no findings (the spec pins the ``(policy, target_dir)``
    signature) and will durably write whatever composition it is handed.
    ``run_config`` checks ``status_for(compute_verdict(findings))`` before
    calling; any future direct caller (Story 1.4's loop-home resolution)
    must apply the same gate or an error-class composition outlives its
    non-zero exit code as a content-addressed artifact."""
    target_dir = Path(target_dir)
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"policy-{effective_policy.content_hash}.json"
        payload = _policy_fields_payload(effective_policy)
        expected_bytes = (
            json.dumps(payload, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        if target_path.exists():
            if not target_path.is_file():
                raise PolicyIOError(
                    f"cannot materialize policy: {target_path} exists and is not a file"
                )
            if target_path.read_bytes() != expected_bytes:
                raise PolicyIOError(
                    f"cannot materialize policy: {target_path} already exists "
                    "with content that does not match its content-addressed "
                    "name -- refusing to bless a foreign or corrupt artifact"
                )
            return target_path
        # os.open with mode 0o666 lets the KERNEL apply the process umask
        # (exactly like a plain open() would), so the final artifact gets
        # ordinary permissions after os.replace. The previous
        # mkstemp+fchmod approach needed an os.umask(0)/restore probe to
        # learn the umask -- a process-GLOBAL toggle that briefly zeroed the
        # umask for every other thread on each write. The tmp name is
        # pid+thread-suffixed so no two live writers can ever share it, and
        # O_EXCL-guarded with NO pre-unlink: a pre-unlink could only ever
        # collide with (and destroy) a SAME-process sibling's in-flight temp
        # -- a SIGKILLed earlier run has a different pid, so its leftover
        # never collides here; if pid+tid recycling ever does land on a
        # stale leftover, O_EXCL surfaces it as an explicit PolicyIOError
        # (delete the stale file and re-run) instead of a silent publish of
        # a half-written artifact.
        tmp_path = target_dir / (
            f".policy-{effective_policy.content_hash}"
            f".pid{os.getpid()}.t{threading.get_native_id()}.tmp"
        )
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(expected_bytes)
            os.replace(tmp_path, target_path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise
        return target_path
    except PolicyIOError:
        raise
    except OSError as exc:
        raise PolicyIOError(f"cannot materialize policy to {target_dir}: {exc}") from exc


def _render_text(data: Mapping[str, object], findings: tuple[Finding, ...]) -> str:
    """The text format: a pure projection of the SAME envelope ``data``/
    ``findings`` the ``--format json`` path prints (AD-14 -- "human
    rendering is a pure projection of the envelope; no human-only
    information exists"). Never reads ``EffectivePolicy`` directly."""
    policy_fields = data["policy"]
    lines = ["policy:"]
    for key in _FIELD_ORDER:
        field = policy_fields[key]
        lines.append(f"  {key}: {field['value']!r} (layer={field['layer']})")
    lines.append(f"content_hash: {data['content_hash']}")
    if "materialized_path" in data:
        lines.append(f"materialized: {data['materialized_path']}")
    if "materialize_skipped" in data:
        lines.append(f"materialized: skipped -- {data['materialize_skipped']}")
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)


def _read_project_policy(path: Path) -> Mapping[str, object]:
    """Read a project policy file via ``tomllib`` -- either ``marshal
    config``'s ``--project-policy`` override or, for every other caller, the
    CONVENTIONAL project path. Wraps every failure mode
    (missing file, a directory, unreadable, malformed TOML, bytes that are
    not valid UTF-8) into ``PolicyIOError`` rather than letting a raw
    exception propagate out of ``run_config()``. ``UnicodeDecodeError`` must
    be listed explicitly: ``tomllib.load`` decodes the bytes itself and lets
    it propagate, and it is a ``ValueError`` SIBLING of ``TOMLDecodeError``
    -- caught by neither ``OSError`` nor the TOML catch (a UTF-16-saved or
    binary file would otherwise crash straight through ``main()``)."""
    try:
        with open(path, "rb") as handle:
            return tomllib.load(handle)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        # "project policy", NOT "--project-policy" (review finding, verified
        # live): this helper serves the CONVENTIONAL path for every caller
        # except `marshal config`'s own override flag, and `marshal gate
        # evaluate` deliberately has no such flag at all -- so a TOML syntax
        # error in a project's conventional policy told the operator to fix
        # a flag that command rejects with a usage error.
        #
        # `!r` on the path (review finding, verified live): `gate evaluate`'s
        # default `--format text` renders finding messages one per line, so a
        # newline in the path forged a `findings:` block that no finding
        # produced. A POSIX filename may contain a newline, and for the
        # conventional path this string can be a symlink TARGET -- chosen by
        # whoever can write inside the projects tree.
        raise PolicyIOError(f"cannot read project policy {str(path)!r}: {exc}") from exc


def run_config(args: argparse.Namespace) -> int:
    # `is not None`, never `or` -- an explicit `--project ""` must win over
    # BMAD_ACTIVE_PROJECT (Python truthiness would otherwise treat an empty
    # flag value as "omitted" and silently fall through to the env var).
    project_slug = (
        args.project if args.project is not None else os.environ.get(ENV_ACTIVE_PROJECT, "")
    )

    # `--project-policy` is read BEFORE compose() -- a read failure here
    # means compose() never ran with real project data, so it reruns with an
    # empty project layer, matching every other "reported, never raised"
    # path in this module. Kept OUTSIDE the block below on purpose: a LATER
    # materialize() failure must never discard an already-successful
    # compose() and silently swap the operator's real project layer for
    # Marshal's bare defaults -- only the read step earns that fallback.
    project_data: Mapping[str, object] = {}
    io_findings: list[Finding] = []
    policy_source: Path | None = args.project_policy
    if policy_source is None and project_slug:
        # CONVENTION LOOKUP. Without this, composing needs `--project-policy`
        # passed by hand every time, so the common invocation silently returns
        # Marshal's bare defaults -- `verify_commands = ()`, i.e. NO gate, which
        # is worse than the wrong gate. AD-16 fixes the precedence but not where
        # the middle layer lives; this fixes that at
        # `<project>/planning-artifacts/marshal-policy.toml`, tracked so a fresh
        # clone has it. An explicit --project-policy still wins.
        candidate = conventional_project_policy_path(project_slug)
        if candidate.is_file():
            policy_source = candidate
    if policy_source is not None:
        try:
            project_data = _read_project_policy(policy_source)
        except PolicyIOError as exc:
            io_findings.append(exc.finding)

    flags = _parse_set_flags(args.set_)
    effective, findings = policy.compose(
        project_slug=project_slug, project=project_data, flags=flags
    )
    # io_findings FIRST: the --project-policy read happens before compose(),
    # and its failure is the root CAUSE of every "layer=default" symptom
    # compose() then reports -- the operator scanning top-down should meet
    # cause before consequence.
    findings = (*io_findings, *findings)

    materialized_path: Path | None = None
    materialize_skipped: str | None = None
    if args.materialize is not None:
        # Persist ONLY an ok-status composition ({clean, warn}). An
        # error-class one (a malformed slug, a bogus --set, an unreadable
        # --project-policy silently replaced by bare defaults) means Marshal
        # could not determine what the operator intended -- writing a
        # durable, content-addressed artifact born of that invocation would
        # let downstream consumers bless it long after the non-zero exit
        # code scrolled away.
        if status_for(compute_verdict(findings)) is Status.OK:
            try:
                materialized_path = materialize(effective, args.materialize)
            except PolicyIOError as exc:
                findings = (*findings, exc.finding)
        else:
            materialize_skipped = (
                "composition carried error-severity findings; nothing was written"
            )

    # The OPERATOR path to the harness projection. Story 1.10 untracked and
    # gitignored `.bmad-loop/policy.toml` and shipped `write_policy_toml`, but
    # nothing reachable CALLED it: `marshal config` only printed, the writer's
    # sole callers were its own tests, and no pixi task rendered it. Since
    # bmad-loop hard-codes POLICY_FILE with no path flag, that left a fresh
    # clone or a newly provisioned loop home with no policy and no way to make
    # one -- exactly the hazard 1.10's own SEQUENCING (hard) note forbade
    # ("untracking must not precede rendering"). This closes it.
    harness_policy_path: Path | None = None
    harness_policy_skipped: str | None = None
    if args.write_harness_policy is not None:
        # Same ok-status gate as --materialize, for the same reason and one
        # sharper: this artifact is what the harness READS on its next run, so
        # writing a composition Marshal could not determine the intent of would
        # hand bmad-loop a policy born of a failed invocation.
        if status_for(compute_verdict(findings)) is Status.OK:
            try:
                harness_policy_path = write_policy_toml(
                    effective, args.write_harness_policy
                )
            except HarnessPolicyWriteError as exc:
                # Reuses MRS-POLICY-004, whose registered meaning is exactly
                # this: "a CLI-boundary I/O step fails (an unwritable
                # --materialize target ...)". A new code would have to be added
                # to REGISTERED_CODES, and Finding() raises
                # UnregisteredFindingCodeError otherwise -- inventing one here
                # would be a second concept for one condition.
                findings = (*findings, PolicyIOError(str(exc)).finding)
        else:
            harness_policy_skipped = (
                "composition carried error-severity findings; the harness policy "
                "was not written"
            )

    data: dict[str, object] = {
        "policy": _policy_fields_payload(effective),
        "content_hash": effective.content_hash,
    }
    if materialized_path is not None:
        data["materialized_path"] = str(materialized_path)
    if materialize_skipped is not None:
        data["materialize_skipped"] = materialize_skipped
    if harness_policy_path is not None:
        data["harness_policy_path"] = str(harness_policy_path)
    if harness_policy_skipped is not None:
        data["harness_policy_skipped"] = harness_policy_skipped

    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command="config", verdict=verdict_value, data=data, findings=findings
    )

    # flush=True is load-bearing, not stylistic: with stdout piped or
    # redirected it is BLOCK-buffered, so a plain print() never touches the
    # fd here -- the write happens at interpreter shutdown, AFTER main()
    # returns, where CPython converts a failed flush into exit status 120
    # plus an "Exception ignored" traceback, bypassing both except clauses
    # entirely (`marshal config | head -1` exited 120 before this flush).
    # Forcing the flush inside the try makes the EPIPE/EIO/ENOSPC surface
    # where the guard can actually catch it.
    try:
        if args.format == "json":
            print(json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True), flush=True)
        else:
            print(_render_text(envelope.data, envelope.findings), flush=True)
    except OSError:
        # BrokenPipeError (the reader hung up) and its non-pipe siblings
        # (EIO on a vanished pty, ENOSPC on a full-disk redirect) all take
        # the same path: the compose/materialize work already completed and
        # there is nothing left to print to, so neutralize stdout and
        # return the verdict-derived exit code instead of crashing through
        # main()'s relay. The devnull redirect is required for the non-pipe
        # cases too -- a failed flush leaves the unwritten bytes IN the
        # buffer, and the interpreter's shutdown re-flush would re-raise
        # the same OSError (-> exit 120) if stdout still pointed at the
        # broken destination.
        _suppress_downstream_pipe_close()

    return exit_code_for(envelope.verdict)


def _suppress_downstream_pipe_close() -> None:
    """A dead stdout -- a closed pipe (``marshal config | head -1``), a
    vanished pty (EIO), a full disk (ENOSPC) -- is not a policy failure:
    the compose/materialize work already completed by the time the envelope
    prints. These are all ``OSError``\\s that ``main()``'s
    ``SystemExit``/``KeyboardInterrupt`` relay would never catch, so
    without this guard the invocation crashes (or, worse, exits 120 from
    the interpreter's shutdown flush of the still-dirty buffer -- see the
    ``flush=True`` comment at the call site). Redirect stdout to devnull
    (the CPython-documented pattern) so the shutdown re-flush of any
    retained bytes lands harmlessly; ``run_config`` then returns its
    verdict-derived exit code.

    Touches process-level FDs only when ``sys.stdout`` IS the real process
    stdout: a replaced stdout (pytest capture, an embedding TUI) has its own
    lifecycle and no interpreter-shutdown flush of the real fd to protect --
    dup2-ing over its fileno() would corrupt the capturing host instead."""
    if sys.stdout is not sys.__stdout__:
        return
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
    except OSError:
        return
    try:
        os.dup2(devnull, sys.stdout.fileno())
    except (OSError, ValueError):
        # A stdout with no usable fd has no shutdown flush to protect;
        # io.UnsupportedOperation is a ValueError.
        pass
    finally:
        # dup2 duplicated the descriptor onto stdout's fd; the original
        # devnull fd must be closed or every suppression leaks one fd.
        os.close(devnull)
