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

from ..core import policy
from ..core.model import Finding, Severity, Status, build_envelope, status_for
from ..core.verdict import compute_verdict, exit_code_for

ENV_ACTIVE_PROJECT = "BMAD_ACTIVE_PROJECT"

# Only these 3 of the 5 --set-eligible scalar keys are int-typed; the other
# two (gate_mode, merge_subject_template) stay plain strings.
_INT_SET_KEYS = frozenset({"max_dev_attempts", "max_review_cycles", "max_followup_reviews"})

# The 4 list/mapping-typed fields --set cannot express (no string value
# could ever satisfy their validators); naming one is a usage error, not a
# misleading "malformed value" policy finding. See the module docstring.
_UNSETTABLE_KEYS = frozenset(
    {"verify_commands", "worktree_seed_paths", "model_tier_map", "frozen_surfaces"}
)

# Field render order: the 4 static keys, then the 5 seed keys -- matches the
# spec's own enumeration order (Boundaries & Constraints, second bullet).
_FIELD_ORDER: tuple[str, ...] = (
    "verify_commands",
    "worktree_seed_paths",
    "merge_subject_template",
    "model_tier_map",
    "gate_mode",
    "frozen_surfaces",
    "max_dev_attempts",
    "max_review_cycles",
    "max_followup_reviews",
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
        raise argparse.ArgumentTypeError(
            f"--set cannot target the list/mapping-typed key {key!r}; "
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
    """Yield ``(key, PolicyField)`` for all 9 keys in ``_FIELD_ORDER``. Seed
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
    return value


def _policy_fields_payload(effective: policy.EffectivePolicy) -> dict[str, object]:
    """The flat 9-key document matching ``schemas/policy.json`` exactly:
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
    """Read ``--project-policy`` via ``tomllib``. Wraps every failure mode
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
        raise PolicyIOError(f"cannot read --project-policy {path}: {exc}") from exc


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
    if args.project_policy is not None:
        try:
            project_data = _read_project_policy(args.project_policy)
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

    data: dict[str, object] = {
        "policy": _policy_fields_payload(effective),
        "content_hash": effective.content_hash,
    }
    if materialized_path is not None:
        data["materialized_path"] = str(materialized_path)
    if materialize_skipped is not None:
        data["materialize_skipped"] = materialize_skipped

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
