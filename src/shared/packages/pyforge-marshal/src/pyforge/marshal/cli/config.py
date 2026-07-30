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
same path every other malformed value takes. The three list/mapping-typed
fields (``verify_commands``, ``worktree_seed_paths``,
``model_tier_map``) are never exposed as ``--set`` targets -- a caller who
tries anyway gets a plain string value that ``compose()``'s validators will
reject the same way (reported, never raised).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import tomllib
from collections.abc import Mapping
from pathlib import Path

from ..core import policy
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for

ENV_ACTIVE_PROJECT = "BMAD_ACTIVE_PROJECT"

# Only these 3 of the 5 --set-eligible scalar keys are int-typed; the other
# two (gate_mode, merge_subject_template) stay plain strings.
_INT_SET_KEYS = frozenset({"max_dev_attempts", "max_review_cycles", "max_followup_reviews"})

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
    ``=``. A missing ``=`` carries no key to attach a policy value to, so
    silently dropping it (the previous behavior) gave the operator zero
    feedback; a usage error is the correct signal, not a policy-layer
    finding (``compose()`` has nothing to validate for a flag that never
    reached it)."""
    key, sep, raw_value = item.partition("=")
    if not sep:
        raise argparse.ArgumentTypeError(f"--set {item!r} must be KEY=VALUE")
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
    or any ``mkdir``/``mkstemp``/write failure, likewise raises
    ``PolicyIOError`` rather than an uncaught ``OSError``."""
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
        fd, tmp_name = tempfile.mkstemp(dir=target_dir, prefix=".policy-", suffix=".tmp")
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(expected_bytes)
                if hasattr(os, "fchmod"):
                    # mkstemp creates 0600 regardless of umask (its own
                    # temp-file security contract), and os.replace carries
                    # that mode onto the final artifact -- which would make
                    # the materialized policy owner-only-readable, unlike any
                    # ordinarily created file. Re-apply the process umask to
                    # 0666 like a plain open() would.
                    current_umask = os.umask(0)
                    os.umask(current_umask)
                    os.fchmod(handle.fileno(), 0o666 & ~current_umask)
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
    findings = (*findings, *io_findings)

    materialized_path: Path | None = None
    if args.materialize is not None:
        try:
            materialized_path = materialize(effective, args.materialize)
        except PolicyIOError as exc:
            findings = (*findings, exc.finding)

    data: dict[str, object] = {
        "policy": _policy_fields_payload(effective),
        "content_hash": effective.content_hash,
    }
    if materialized_path is not None:
        data["materialized_path"] = str(materialized_path)

    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command="config", verdict=verdict_value, data=data, findings=findings
    )

    try:
        if args.format == "json":
            print(json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True))
        else:
            print(_render_text(envelope.data, envelope.findings))
    except BrokenPipeError:
        _suppress_downstream_pipe_close()

    return exit_code_for(envelope.verdict)


def _suppress_downstream_pipe_close() -> None:
    """A closed stdout (e.g. ``marshal config | head -1``) is the READER's
    choice, not a policy failure -- the compose/materialize work already
    completed by the time the envelope prints. ``BrokenPipeError`` is an
    ``OSError`` that ``main()``'s ``SystemExit``/``KeyboardInterrupt`` relay
    would never catch, so without this guard a piped invocation crashes with
    a traceback in violation of the never-raise exit-relay contract.
    Redirect stdout to devnull (the CPython-documented pattern) so the
    interpreter's final flush does not raise a SECOND BrokenPipeError at
    shutdown; ``run_config`` then returns its verdict-derived exit code.

    Touches process-level FDs only when ``sys.stdout`` IS the real process
    stdout: a replaced stdout (pytest capture, an embedding TUI) has its own
    lifecycle and no interpreter-shutdown flush of the real fd to protect --
    dup2-ing over its fileno() would corrupt the capturing host instead."""
    if sys.stdout is not sys.__stdout__:
        return
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    except (OSError, ValueError):
        # A stdout with no usable fd has no shutdown flush to protect;
        # io.UnsupportedOperation is a ValueError.
        pass
