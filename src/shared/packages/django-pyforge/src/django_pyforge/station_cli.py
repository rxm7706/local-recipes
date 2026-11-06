"""One closed table from a start tool to a station CLI verb (Epic 119, canopy:AD-24).

A worker that shells out sits outside ``.claude/hooks/pre-shell.py``, so this
table is the whole guard. A caller passes a target; the row fixes the verb, its
flags, the pixi environment and the exit codes that count as a result. Nothing
here runs a shell, and a CLI does not inherit the worker's environment: that
holds the database and signing secrets. The scrub stops inheritance only. A CLI
runs as the worker's own user, so it can still read what that user can.

``STATION_CLI_ROOT`` names the checkout whose pixi environments hold the CLIs. It
is empty on the platform image, which has no checkout and most stations' CLIs
missing, so a start tool there ends its run ``FAILED`` and says so.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from django.conf import settings

from django_pyforge.assertion.schema import CLAIM_ROLES
from django_pyforge.queues import queue_for, time_limit_for_queue
from django_pyforge.roles import ROLE_ADMIN, parse_role_claims, role_names
from django_pyforge.supervisor import StartRefusedError, StationVerbFailedError, refuse_unwired_run

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

logger = logging.getLogger(__name__)

START_TOOL_CLI_FLAG_KEY = "pyforge.steward.start_tool_cli"
START_LOOP_DISPATCH_FLAG_KEY = "pyforge.steward.start_loop_dispatch"
SETTING_STATION_CLI_ROOT = "STATION_CLI_ROOT"

GUILD_ENVIRONMENT = "pyforge-guild"
MASON_ENVIRONMENT = "pyforge-mason"
WARDEN_ENVIRONMENT = "pyforge-warden"

#: Seconds a verb, the task's soft limit and its hard limit stop short of the queue's limit.
VERB_MARGIN_SECONDS = 30
SOFT_LIMIT_MARGIN_SECONDS = 15
HARD_LIMIT_MARGIN_SECONDS = 5

#: The most a run keeps of stdout or of a JSON report, and of stderr.
OUTPUT_CAP_BYTES = 256 * 1024
STDERR_TAIL_BYTES = 4 * 1024

QUERY_CAP_CHARS = 2000
GIT_LOOKUP_SECONDS = 30

#: All a CLI sees of the worker's environment, with a row's own ``passthrough``.
#: ``PATH`` is built, never inherited.
ENVIRONMENT_ALLOWLIST: tuple[str, ...] = (
    "CURL_CA_BUNDLE",
    "HOME",
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "LOGNAME",
    "NODE_EXTRA_CA_CERTS",
    "NO_PROXY",
    "PYFORGE_ENVIRONMENT",
    "PYFORGE_FLAGS_PATH",
    "REQUESTS_CA_BUNDLE",
    "SSL_CERT_DIR",
    "SSL_CERT_FILE",
    "TMPDIR",
    "TZ",
    "USER",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "http_proxy",
    "https_proxy",
    "no_proxy",
)
SYSTEM_PATH = "/usr/local/bin:/usr/bin:/bin"

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_RECIPE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,127}")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")

STEWARD_DUTIES: dict[str, tuple[str, ...]] = {
    "ci-status": ("ci", "status", "--json"),
    "estate-plan": ("estate", "plan", "--json"),
    "estate-status": ("estate", "status", "--json"),
}


class TargetRefusedError(ValueError):
    """A target its row's validator refuses. Nothing runs."""


def _token(target: str) -> str:
    """One name: it cannot read as a flag or a path."""
    if _TOKEN.fullmatch(target) is None:
        msg = f"{target!r} is not one name"
        raise TargetRefusedError(msg)
    return target


def _doctor_scan(target: str, _root: Path) -> tuple[str, ...]:
    return ("diagnose", "--target", _token(target), "--json")


def _herald_notice(target: str, _root: Path) -> tuple[str, ...]:
    return ("notice", "get", _token(target))


def _scribe_recall(target: str, _root: Path) -> tuple[str, ...]:
    query = target.strip()
    if not query or len(query) > QUERY_CAP_CHARS or _CONTROL.search(query):
        msg = f"a recall query is 1 to {QUERY_CAP_CHARS} characters with no control character"
        raise TargetRefusedError(msg)
    return ("recall", "--", query)


def _steward_duty(target: str, _root: Path) -> tuple[str, ...]:
    try:
        return STEWARD_DUTIES[target]
    except KeyError:
        msg = f"{target!r} is not one of {sorted(STEWARD_DUTIES)}"
        raise TargetRefusedError(msg) from None


def _warden_audit(target: str, root: Path) -> tuple[str, ...]:
    if not target or _CONTROL.search(target):
        msg = "a path is not empty and has no control character"
        raise TargetRefusedError(msg)
    path = (root / target).resolve()
    if not path.is_relative_to(root) or not path.is_dir():
        msg = f"{target!r} is not a directory under the checkout"
        raise TargetRefusedError(msg)
    return ("scan", str(path), "--format", "json")


def _tracked_recipe(slug: str, root: Path) -> str:
    if _RECIPE.fullmatch(slug) is None:
        msg = f"{slug!r} is not a recipe name"
        raise TargetRefusedError(msg)
    recipe = f"recipes/{slug}"
    try:
        tracked = subprocess.run(  # noqa: S603 -- no shell; the slug has been validated
            ["git", "-C", str(root), "ls-files", "--", f"{recipe}/recipe.yaml", f"{recipe}/meta.yaml"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
            env={"PATH": SYSTEM_PATH},
            timeout=GIT_LOOKUP_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        msg = f"could not check {slug!r}: {exc}"
        raise TargetRefusedError(msg) from None
    if tracked.returncode != 0 or not tracked.stdout.strip():
        msg = f"{slug!r} is not a tracked recipe"
        raise TargetRefusedError(msg)
    return recipe


def _mason_build(target: str, root: Path) -> tuple[str, ...]:
    return ("recipe", "build", _tracked_recipe(target, root), "--format", "json")


def _marshal_loop(target: str, _root: Path) -> tuple[str, ...]:
    slug, separator, story = target.partition("/")
    if not separator:
        msg = "a loop target is <slug>/<story>"
        raise TargetRefusedError(msg)
    return ("factory", "dispatch", _token(slug), _token(story), "--format", "json")


@dataclass(frozen=True)
class StationVerb:
    """One row: all a start tool may run, and what counts as a result."""

    station: str
    run_tool: str
    start_tool: str
    environment: str
    args: Callable[[str, Path], tuple[str, ...]]
    #: A non-zero code here is a result only with a JSON report on stdout.
    result_codes: frozenset[int] = frozenset({0})
    #: Worker variables this row's CLI needs beyond ``ENVIRONMENT_ALLOWLIST``.
    passthrough: tuple[str, ...] = ()
    #: The verb spends, or a second run collides: a redelivery never starts it again.
    at_most_once: bool = False
    admin_only: bool = False
    flag: str | None = None


#: The closed table. A test pins it; a row joins only with a story and a review.
STATION_VERBS: dict[tuple[str, str], StationVerb] = {
    (verb.station, verb.run_tool): verb
    for verb in (
        StationVerb(
            "doctor",
            "run_scan",
            "start_scan",
            GUILD_ENVIRONMENT,
            _doctor_scan,
            result_codes=frozenset({0, 2}),  # doctor's frozen domain: a fail finding is a result
        ),
        StationVerb("herald", "run_notice", "start_notice", GUILD_ENVIRONMENT, _herald_notice),
        StationVerb(
            "marshal",
            "run_loop",
            "start_loop",
            GUILD_ENVIRONMENT,
            _marshal_loop,
            at_most_once=True,
            admin_only=True,
            flag=START_LOOP_DISPATCH_FLAG_KEY,
        ),
        StationVerb("mason", "run_build", "start_build", MASON_ENVIRONMENT, _mason_build, at_most_once=True),
        StationVerb(
            "scribe",
            "run_recall",
            "start_recall",
            GUILD_ENVIRONMENT,
            _scribe_recall,
            passthrough=("SCRIBE_GRAPH_DSN",),
        ),
        StationVerb(
            "steward",
            "run_duty",
            "start_duty",
            GUILD_ENVIRONMENT,
            _steward_duty,
            result_codes=frozenset({0, 1}),  # `ci status` prints its envelope on a partial read
        ),
        StationVerb(
            "warden",
            "run_audit",
            "start_audit",
            WARDEN_ENVIRONMENT,
            _warden_audit,
            result_codes=frozenset({0, 1}),  # warden's frozen gate: 2 is ERROR, an audit that did not finish
            passthrough=("OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY", "PYFORGE_WARDEN_FEED_CACHE_DIR"),
        ),
    )
}


def _flag_on(key: str) -> bool:
    # Lazy: the mcp-host image imports this module through marshal's face and carries
    # no pyforge.core. A gated start there fails closed.
    from pyforge.core.flags import read_boolean  # noqa: PLC0415

    return read_boolean(key)


def _kill_switch_on() -> bool:
    from pyforge.core.flags import kill_switch_on  # noqa: PLC0415

    return kill_switch_on(START_TOOL_CLI_FLAG_KEY)


def check_start(station: str, tool: str, claims: Mapping[str, Any]) -> None:
    """Refuse a gated row's caller before a run row exists (Story 119.4)."""
    verb = STATION_VERBS.get((station, tool))
    if verb is None:
        return
    if verb.admin_only and not parse_role_claims(role_names(claims.get(CLAIM_ROLES))).is_admin:
        msg = f"{station} {verb.start_tool} needs the {ROLE_ADMIN} role"
        raise StartRefusedError(msg)
    if verb.flag is not None and not _flag_on(verb.flag):
        msg = f"{station} {verb.start_tool} is off: flag {verb.flag}"
        raise StartRefusedError(msg)


def runs_at_most_once(station: str, tool: str) -> bool:
    """Whether a redelivered run of this tool must not start its verb again."""
    verb = STATION_VERBS.get((station, tool))
    return verb is not None and verb.at_most_once


def _queue_limit(verb: StationVerb) -> int:
    return time_limit_for_queue(queue_for(verb.station, verb.run_tool))


def task_limits(station: str, tool: str) -> dict[str, int]:
    """Celery limits for a row's run; the verb's own timeout fires first.

    The soft limit in the settings is 60 seconds, and ``estate plan`` alone takes
    longer, so a row's run names its own. A run that is not a row names none.
    """
    verb = STATION_VERBS.get((station, tool))
    if verb is None:
        return {}
    limit = _queue_limit(verb)
    return {
        "soft_time_limit": limit - SOFT_LIMIT_MARGIN_SECONDS,
        "time_limit": limit - HARD_LIMIT_MARGIN_SECONDS,
    }


def _cli_environment(verb: StationVerb, env_bin: Path) -> dict[str, str]:
    names = (*ENVIRONMENT_ALLOWLIST, *verb.passthrough)
    environment = {name: os.environ[name] for name in names if name in os.environ}
    user_bin = Path.home() / ".local" / "bin"  # where a harness a dispatch launches lives
    environment["PATH"] = os.pathsep.join((str(env_bin), str(user_bin), SYSTEM_PATH))
    return environment


def _capped(text: str) -> tuple[str, bool]:
    encoded = text.encode("utf-8", "replace")
    if len(encoded) <= OUTPUT_CAP_BYTES:
        return text, False
    return encoded[:OUTPUT_CAP_BYTES].decode("utf-8", "replace"), True


def _refuse_constant(name: str) -> None:
    msg = f"{name} is not a JSON value the run store can hold"
    raise ValueError(msg)


def _json_report(stdout: str) -> dict[str, Any] | None:
    """A JSON object the run store can hold, or ``None``.

    The store is JSONB: it refuses ``NaN`` and a NUL, and a refused write would
    leave the run ``RUNNING`` until the sweep.
    """
    if "\\u0000" in stdout:
        return None
    try:
        report = json.loads(stdout, parse_constant=_refuse_constant)
    except ValueError:
        return None
    return report if isinstance(report, dict) else None


def _fit_report(report: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, int]]]:
    """Keep the smallest top-level values that fit; say what the rest held."""
    kept: dict[str, Any] = {}
    omitted: dict[str, dict[str, int]] = {}
    used = 0
    sizes = {key: len(json.dumps(value, default=str)) for key, value in report.items()}
    for key, size in sorted(sizes.items(), key=lambda item: item[1]):
        value = report[key]
        if used + size <= OUTPUT_CAP_BYTES:
            kept[key] = value
            used += size
            continue
        omitted[key] = {"bytes": size}
        if isinstance(value, list | dict):
            omitted[key]["items"] = len(value)
    return kept, omitted


def _result(verb: StationVerb, argv: list[str], stdout: str, stderr: str, code: int) -> dict[str, Any]:
    """What ``get_*`` carries."""
    report = _json_report(stdout)
    if code != 0 and report is None:
        tail = stderr[-STDERR_TAIL_BYTES:].strip()
        msg = f"{verb.station} {verb.start_tool} exited {code} with no report: {tail}"
        raise StationVerbFailedError(msg)
    result: dict[str, Any] = {
        "station": verb.station,
        "argv": argv[1:],
        "exit_code": code,
        "stderr": stderr[-STDERR_TAIL_BYTES:].replace("\x00", ""),
    }
    if report is not None:
        result["report"], result["omitted"] = _fit_report(report)
        return result
    result["stdout"], result["truncated"] = _capped(stdout.replace("\x00", ""))
    return result


def _kill_group(process: subprocess.Popen[str]) -> None:
    """Stop the verb, not only its ``pyforge`` wrapper: the wrapper waits on the station CLI."""
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(process.pid, signal.SIGKILL)
    process.communicate()


def _run_verb(verb: StationVerb, argv: list[str], root: Path, env_bin: Path) -> tuple[str, str, int]:
    seconds = _queue_limit(verb) - VERB_MARGIN_SECONDS
    try:
        process = subprocess.Popen(  # noqa: S603 -- no shell; the row fixes all but a validated target
            argv,
            cwd=root,
            encoding="utf-8",
            env=_cli_environment(verb, env_bin),
            errors="replace",
            start_new_session=True,  # its own process group, so a timeout can stop all of it
            stdin=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
    except OSError as exc:
        msg = f"{verb.station} {verb.start_tool} could not start: {exc}"
        raise StationVerbFailedError(msg) from None
    try:
        stdout, stderr = process.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        _kill_group(process)
        msg = f"{verb.station} {verb.start_tool} timed out after {seconds} s"
        raise StationVerbFailedError(msg) from None
    except BaseException:  # Celery's soft limit raises here: the verb stops with the task
        _kill_group(process)
        raise
    return stdout, stderr, process.returncode


def run_start_tool(station: str, run_tool: str, payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Run one row. Anything short of a result raises, so the run ends ``FAILED``."""
    verb = STATION_VERBS[(station, run_tool)]
    if not _kill_switch_on():
        refuse_unwired_run(station, verb.start_tool, f"the kill switch {START_TOOL_CLI_FLAG_KEY} is off")
    if verb.flag is not None and not _flag_on(verb.flag):
        # It can flip between the start and this run.
        refuse_unwired_run(station, verb.start_tool, f"flag {verb.flag} is off")
    configured = getattr(settings, SETTING_STATION_CLI_ROOT, "")
    if not configured:
        reason = f"this worker has no station CLI ({SETTING_STATION_CLI_ROOT} is unset)"
        refuse_unwired_run(station, verb.start_tool, reason)
    root = Path(configured).resolve()
    executable = root / ".pixi" / "envs" / verb.environment / "bin" / "pyforge"
    if not os.access(executable, os.X_OK):
        refuse_unwired_run(station, verb.start_tool, f"this worker has no {verb.environment} environment under {root}")
    target = str((payload or {}).get("target", ""))
    try:
        args = verb.args(target, root)
    except TargetRefusedError as exc:
        refuse_unwired_run(station, verb.start_tool, f"target refused: {exc}")
    argv = [str(executable), station, *args]
    stdout, stderr, code = _run_verb(verb, argv, root, executable.parent)
    if code not in verb.result_codes:
        tail = stderr[-STDERR_TAIL_BYTES:].strip()
        msg = f"{station} {verb.start_tool} exited {code}: {tail}"
        raise StationVerbFailedError(msg)
    logger.info(
        "station_cli.ran",
        extra={"event": "station_cli.ran", "station": station, "exit_code": code},
    )
    return _result(verb, argv, stdout, stderr, code)
