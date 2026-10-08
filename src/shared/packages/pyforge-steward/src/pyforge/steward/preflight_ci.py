"""Which preflight lanes would CI run for this diff? (Story 71.2, CAP-159.)

Reads ``.github/workflows/*.yml`` at run time and answers, per lane, the question the
workflow files themselves answer: does a ``pull_request`` workflow carrying this lane's
step fire for the changed paths, and does that step's job condition hold?

Nothing here is a copy of CI's rules. There is no path list, no station list and no
lane-to-workflow table in this module:

* a lane's CI counterpart is found by reading each ``pull_request`` workflow's ``run:``
  steps -- ``pixi run … <task>`` where the task is the lane's own or has it in its
  ``depends-on`` closure, or a step carrying the lane's own command line;
* ``on.pull_request.paths`` is matched by GitHub's filter-pattern rules (``*`` stops at
  ``/``, ``**`` crosses it -- never ``fnmatch``);
* ``needs.<job>.outputs.<x>`` comes from running the workflow's own ``changes`` job shell
  in the repository, with ``github.event_name`` = ``pull_request``, ``GITHUB_BASE_REF`` =
  ``main`` and a scratch ``GITHUB_OUTPUT``.

The changed paths are ``git diff --name-only refs/remotes/origin/main...HEAD`` plus the
working tree's staged, unstaged and untracked paths. A dirty tree can only add lanes: the
workflow rules are evaluated once against the committed diff and, when the tree is dirty,
once more against a throw-away snapshot commit of the working tree; a lane runs if either
evaluation selects it.

Anything the reader cannot evaluate runs the lane and says so: no
``refs/remotes/origin/main``, a ``paths-ignore``, another ``if:`` shape, a matrix it cannot
expand, a ``changes`` step that fails, a lane with no CI counterpart.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import yaml
from pyforge.core.process import PosixProcess, ProcessError, ProcessResult

BASE_BRANCH = "main"
BASE_REF = f"refs/remotes/origin/{BASE_BRANCH}"
WORKFLOWS_RELATIVE = Path(".github") / "workflows"

_SCRIPT_TIMEOUT_S = 300.0
_SEPARATORS = frozenset({"|", "&&", "||", ";", "&"})
_PIXI_VALUE_FLAGS = frozenset({"--manifest-path", "--color"})
_PYTHON_INTERPRETERS = frozenset({"python", "python3"})
_PR_FIRING_TYPES = frozenset({"opened", "synchronize", "reopened"})
_PR_RECOGNISED_KEYS = frozenset({"paths", "branches", "types"})

_EXPRESSION = re.compile(r"\$\{\{(.*?)\}\}", re.DOTALL)
_STRING_LITERAL = re.compile(r"'((?:[^']|'')*)'")
_NEEDS_CONDITION = re.compile(r"needs\.([\w-]+)\.outputs\.([\w-]+)\s*(==|!=)\s*'([^']*)'")
_MATRIX_CONDITION = re.compile(r"matrix\.([\w-]+)\s*(==|!=)\s*'([^']*)'")
_FROM_JSON = re.compile(r"\$\{\{\s*fromJSON\(\s*needs\.([\w-]+)\.outputs\.([\w-]+)\s*\)\s*\}\}", re.IGNORECASE)
_STEP_OUTPUT = re.compile(r"\$\{\{\s*steps\.([\w-]+)\.outputs\.([\w-]+)\s*\}\}")
_OUTPUT_HEREDOC = re.compile(r"([^=<\s]+)<<(\S+)")


class LaneLike(Protocol):
    @property
    def task(self) -> str: ...

    @property
    def environment(self) -> str: ...


class _Unevaluable(Exception):
    """A rule the reader does not recognise; its text is journaled and the lane runs."""


class _SelectAll(Exception):
    """The diff cannot be read; every lane runs and the journal says why."""


@dataclass(frozen=True)
class LaneVerdict:
    task: str
    environment: str
    selected: bool
    reason: str = ""  # why it runs
    workflow: str = ""  # why it is skipped: the workflow(s) ...
    rule: str = ""  # ... and the rule(s)


@dataclass(frozen=True)
class Selection:
    base_ref: str
    all_reason: str | None
    changed_paths: tuple[str, ...]
    dirty_paths: tuple[str, ...]
    verdicts: tuple[LaneVerdict, ...]

    def is_selected(self, lane: LaneLike) -> bool:
        return any(v.selected for v in self.verdicts if v.task == lane.task and v.environment == lane.environment)

    def to_journal(self) -> dict[str, Any]:
        return {
            "mode": "all" if self.all_reason else "diff",
            "all_reason": self.all_reason,
            "base_ref": self.base_ref,
            "changed_paths": len(self.changed_paths),
            "dirty_paths": len(self.dirty_paths),
            "selected": [
                {"lane": v.task, "environment": v.environment, "reason": v.reason} for v in self.verdicts if v.selected
            ],
            "skipped": [
                {"lane": v.task, "environment": v.environment, "workflow": v.workflow, "rule": v.rule}
                for v in self.verdicts
                if not v.selected
            ],
        }


# ---------------------------------------------------------------------------
# GitHub's filter-pattern rules (never fnmatch)
# ---------------------------------------------------------------------------


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """GitHub Actions filter pattern -> regex: ``*`` stops at ``/``, ``**`` crosses it,
    ``?`` / ``+`` quantify the preceding character, ``[...]`` is a class (``[!`` negates)."""
    atoms: list[str] = []
    i, n = 0, len(pattern)
    while i < n:
        char = pattern[i]
        if char == "*":
            j = i
            while j < n and pattern[j] == "*":
                j += 1
            atoms.append(".*" if j - i >= 2 else "[^/]*")
            i = j
            continue
        if char in "?+" and atoms:
            atoms[-1] = f"(?:{atoms[-1]}){char}"
        elif char == "[" and (close := pattern.find("]", i + 2)) != -1:
            body = pattern[i + 1 : close]
            body = "^" + body[1:] if body.startswith("!") else body
            atoms.append("[" + body.replace("\\", "\\\\") + "]")
            i = close
        elif char == "\\" and i + 1 < n:
            i += 1
            atoms.append(re.escape(pattern[i]))
        else:
            atoms.append(re.escape(char))
        i += 1
    return re.compile("".join(atoms), re.DOTALL)


def filter_matches(patterns: Sequence[str], path: str) -> bool:
    """True when ``path`` passes a GitHub ``paths`` / ``branches`` filter: the last pattern
    that matches it decides, a ``!`` pattern excludes."""
    matched = False
    for pattern in patterns:
        negated = pattern.startswith("!")
        if _glob_to_regex(pattern[1:] if negated else pattern).fullmatch(path):
            matched = not negated
    return matched


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Workflow:
    file: str
    data: dict[Any, Any]

    @property
    def jobs(self) -> dict[str, Any]:
        jobs = self.data.get("jobs")
        return jobs if isinstance(jobs, dict) else {}

    @property
    def pull_request(self) -> dict[str, Any] | None:
        """The ``on.pull_request`` block (``{}`` for a bare trigger), or ``None`` without one."""
        # PyYAML (YAML 1.1) reads the bare `on:` key as the boolean True.
        trigger = self.data.get("on", self.data.get(True))
        if trigger == "pull_request":
            return {}
        if isinstance(trigger, list):
            return {} if "pull_request" in trigger else None
        if isinstance(trigger, dict) and "pull_request" in trigger:
            block = trigger["pull_request"]
            if block is None:
                return {}
            return dict(block) if isinstance(block, dict) else {"<not a mapping>": block}
        return None


def load_workflows(repo_root: Path) -> list[Workflow]:
    directory = repo_root / WORKFLOWS_RELATIVE
    workflows: list[Workflow] = []
    for path in sorted([*directory.glob("*.yml"), *directory.glob("*.yaml")]):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise _SelectAll(f"{path.name} cannot be read: {exc}") from exc
        if isinstance(data, dict):
            workflows.append(Workflow(file=path.name, data=data))
    return workflows


def _as_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise _Unevaluable(f"filter {value!r} is neither a string nor a list")


def _pull_request_fires(config: dict[str, Any], paths: Sequence[str]) -> tuple[bool, str]:
    unknown = sorted(str(key) for key in config if key not in _PR_RECOGNISED_KEYS)
    if unknown:
        raise _Unevaluable(f"on.pull_request.{', '.join(unknown)} is not recognised")
    if "types" in config and not _PR_FIRING_TYPES.intersection(_as_list(config["types"])):
        raise _Unevaluable(f"on.pull_request.types {config['types']!r} holds none of {sorted(_PR_FIRING_TYPES)}")
    if "branches" in config and not filter_matches(_as_list(config["branches"]), BASE_BRANCH):
        return False, f"on.pull_request.branches {config['branches']!r} excludes {BASE_BRANCH}"
    if "paths" in config:
        patterns = _as_list(config["paths"])
        if not patterns:
            raise _Unevaluable("on.pull_request.paths is empty")
        if any(filter_matches(patterns, path) for path in paths):
            return True, "on.pull_request.paths matches a changed path"
        return False, f"on.pull_request.paths: none of the {len(paths)} changed paths matches"
    return True, "on.pull_request has no paths filter"


# ---------------------------------------------------------------------------
# Expressions and run: text
# ---------------------------------------------------------------------------


def _eval_expression(expression: str, context: Mapping[str, str]) -> str:
    """``a.b || 'literal'`` chains over known context names -- nothing else."""
    for part in (p.strip() for p in expression.split("||")):
        literal = _STRING_LITERAL.fullmatch(part)
        if literal:
            value = literal.group(1).replace("''", "'")
        elif part in context:
            value = context[part]
        else:
            raise _Unevaluable(f"expression ${{{{ {part} }}}} is not evaluable")
        if value:
            return value
    return ""


def _expand(text: str, context: Mapping[str, str], *, strict: bool) -> str:
    def replace(match: re.Match[str]) -> str:
        try:
            return _eval_expression(match.group(1), context)
        except _Unevaluable:
            if strict:
                raise
            return match.group(0)

    return _EXPRESSION.sub(replace, text)


def _tokens(text: str) -> list[str]:
    lines = [line for line in text.replace("\\\n", " ").splitlines() if not line.lstrip().startswith("#")]
    body = "\n".join(lines)
    try:
        return shlex.split(body)
    except ValueError:
        return body.split()


def _task_def(pixi_data: Mapping[str, Any], name: str) -> Mapping[str, Any] | None:
    for feature in pixi_data.get("feature", {}).values():
        tasks = feature.get("tasks")
        if isinstance(tasks, dict) and name in tasks:
            task = tasks[name]
            return task if isinstance(task, dict) else None
    return None


def _closure(pixi_data: Mapping[str, Any], name: str) -> set[str]:
    seen: set[str] = set()
    pending = [name]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        task = _task_def(pixi_data, current)
        for dep in (task or {}).get("depends-on", []):
            pending.append(dep if isinstance(dep, str) else str(dep.get("task", "")))
    return seen


@dataclass(frozen=True)
class _PixiRun:
    start: int
    env: str | None
    task: str | None
    task_index: int


def _pixi_runs(tokens: Sequence[str]) -> list[_PixiRun]:
    runs: list[_PixiRun] = []
    for i, token in enumerate(tokens):
        if token != "pixi" or tokens[i + 1 : i + 2] != ["run"]:
            continue
        j, env = i + 2, None
        while j < len(tokens):
            current = tokens[j]
            if current in ("-e", "--environment") and j + 1 < len(tokens):
                env, j = tokens[j + 1], j + 2
            elif current.startswith("--environment="):
                env, j = current.split("=", 1)[1], j + 1
            elif current in _PIXI_VALUE_FLAGS:
                j += 2
            elif current.startswith("-"):
                j += 1
            else:
                break
        task = tokens[j] if j < len(tokens) and tokens[j] not in _SEPARATORS else None
        runs.append(_PixiRun(start=i, env=env, task=task, task_index=j))
    return runs


def _split_segments(tokens: Sequence[str]) -> list[list[str]]:
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in _SEPARATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def _lane_segments(cmd: Any) -> list[tuple[list[str], list[tuple[str, str | None]]]]:
    """The lane's own command line as (words, [(flag, value)]) per ``&&`` segment, without
    its leading interpreter."""
    if isinstance(cmd, list):
        cmd = " ".join(str(part) for part in cmd)
    if not isinstance(cmd, str):
        return []
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        return []
    parsed: list[tuple[list[str], list[tuple[str, str | None]]]] = []
    for segment in _split_segments(tokens):
        if segment[0] in _PYTHON_INTERPRETERS:
            segment = segment[1:]
        i, words = 0, []
        if segment[:1] == ["-m"]:
            words, i = segment[:2], 2
        while i < len(segment) and not segment[i].startswith("-"):
            words.append(segment[i])
            i += 1
        flags: list[tuple[str, str | None]] = []
        while i < len(segment):
            if segment[i].startswith("-"):
                has_value = i + 1 < len(segment) and not segment[i + 1].startswith("-")
                flags.append((segment[i], segment[i + 1] if has_value else None))
                i += 2 if has_value else 1
            else:
                i += 1
        if not words:
            return []  # no program words to anchor on: never a vacuous match
        parsed.append((words, flags))
    return parsed


def _dynamic(value: str) -> bool:
    return "$" in value or "{{" in value


def _segment_in_run(lane: LaneLike, words: list[str], flags: list[tuple[str, str | None]], tokens: list[str]) -> bool:
    runs = _pixi_runs(tokens)
    for i in range(len(tokens) - len(words) + 1):
        if tokens[i : i + len(words)] != words:
            continue
        end = i + len(words)
        while end < len(tokens) and tokens[end] not in _SEPARATORS:
            end += 1
        window = tokens[i + len(words) : end]
        if not all(_flag_present(window, flag, value) for flag, value in flags):
            continue
        env = _env_before(tokens, runs, i)
        if env is not None and not _dynamic(env) and env != lane.environment:
            continue
        return True
    return False


def _flag_present(window: Sequence[str], flag: str, value: str | None) -> bool:
    for k, token in enumerate(window):
        if token != flag:
            continue
        if value is None:
            return True
        found = window[k + 1] if k + 1 < len(window) else ""
        if found == value or _dynamic(found):
            return True
    return False


def _env_before(tokens: Sequence[str], runs: Sequence[_PixiRun], index: int) -> str | None:
    for run in reversed(runs):
        if run.task_index <= index:
            if any(token in _SEPARATORS for token in tokens[run.start : index]):
                return None
            return run.env
    return None


def _step_matches(lane: LaneLike, text: str, pixi_data: Mapping[str, Any]) -> bool:
    """Does this ``run:`` text run the lane: its task, a task holding it in ``depends-on``,
    or its own command line?"""
    tokens = _tokens(text)
    for run in _pixi_runs(tokens):
        if run.task and lane.task in _closure(pixi_data, run.task):
            return True
    task = _task_def(pixi_data, lane.task)
    segments = _lane_segments((task or {}).get("cmd"))
    return bool(segments) and all(_segment_in_run(lane, words, flags, tokens) for words, flags in segments)


def _normalize_condition(condition: Any) -> str:
    text = str(condition).strip()
    if text.startswith("${{") and text.endswith("}}"):
        text = text[3:-2].strip()
    return text


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------


def _run(
    process: PosixProcess, argv: Sequence[str], cwd: Path, env: Mapping[str, str] | None, timeout_s: float | None = None
) -> ProcessResult:
    try:
        return process.run(argv, cwd=cwd, env=env, timeout_s=timeout_s)
    except ProcessError as exc:
        return ProcessResult(returncode=127, stdout="", stderr=str(exc))


def _git(process: PosixProcess, root: Path, args: Sequence[str], env: Mapping[str, str]) -> ProcessResult:
    return _run(process, ["git", *args], root, env)


def _git_ok(process: PosixProcess, root: Path, args: Sequence[str], env: Mapping[str, str], what: str) -> str:
    result = _git(process, root, args, env)
    if result.returncode != 0:
        raise _SelectAll(f"{what} failed (git {' '.join(args)} exited {result.returncode}): {result.stderr.strip()}")
    return result.stdout


def _nul_paths(output: str) -> list[str]:
    return [path for path in output.split("\0") if path]


def _git_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("GIT_INDEX_FILE", None)
    return env


def _snapshot_env(
    process: PosixProcess, root: Path, scratch: Path, env: dict[str, str], base_sha: str
) -> dict[str, str]:
    """A git dir whose ``HEAD`` is a snapshot commit of the working tree (tracked + untracked
    files, ignores honoured) on top of ``HEAD``, and whose ``refs/remotes/origin/main`` is the
    real one -- so a workflow's ``git diff "$BASE"...HEAD`` sees the dirty tree too. The real
    repository's refs, index and working tree are never touched."""
    index_src = Path(
        _git_ok(process, root, ["rev-parse", "--path-format=absolute", "--git-path", "index"], env, "snapshot").strip()
    )
    objects = _git_ok(process, root, ["rev-parse", "--path-format=absolute", "--git-path", "objects"], env, "snapshot")
    head = _git_ok(process, root, ["rev-parse", "HEAD"], env, "snapshot").strip()
    snapshot_index = scratch / "snapshot.index"
    index_env = {**env, "GIT_INDEX_FILE": str(snapshot_index)}
    if index_src.is_file():
        shutil.copyfile(index_src, snapshot_index)
    else:
        _git_ok(process, root, ["read-tree", head], index_env, "snapshot")
    _git_ok(process, root, ["add", "-A"], index_env, "snapshot")
    tree = _git_ok(process, root, ["write-tree"], index_env, "snapshot").strip()
    identity = {
        **env,
        "GIT_AUTHOR_NAME": "preflight",
        "GIT_AUTHOR_EMAIL": "preflight@localhost",
        "GIT_COMMITTER_NAME": "preflight",
        "GIT_COMMITTER_EMAIL": "preflight@localhost",
    }
    commit = _git_ok(
        process, root, ["commit-tree", tree, "-p", head, "-m", "preflight snapshot"], identity, "snapshot"
    ).strip()

    bare = scratch / "snapshot.git"
    clean = {k: v for k, v in env.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
    _git_ok(process, scratch, ["init", "--bare", "-q", str(bare)], clean, "snapshot")
    (bare / "objects" / "info").mkdir(parents=True, exist_ok=True)
    (bare / "objects" / "info" / "alternates").write_text(objects.strip() + "\n", encoding="utf-8")
    bare_args = ["--git-dir", str(bare)]
    _git_ok(process, scratch, [*bare_args, "update-ref", BASE_REF, base_sha], clean, "snapshot")
    _git_ok(process, scratch, [*bare_args, "update-ref", "refs/heads/snapshot", commit], clean, "snapshot")
    _git_ok(process, scratch, [*bare_args, "symbolic-ref", "HEAD", "refs/heads/snapshot"], clean, "snapshot")
    return {**clean, "GIT_DIR": str(bare), "GIT_WORK_TREE": str(root)}


# ---------------------------------------------------------------------------
# Evaluating one state of the tree
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Site:
    workflow: str
    job: str
    outcome: str  # run | skip | unknown
    rule: str


@dataclass
class _State:
    """One view of the tree (committed, or committed + dirty): its changed paths and the
    environment its workflow shells run in."""

    root: Path
    process: PosixProcess
    workflows: Sequence[Workflow]
    pixi_data: Mapping[str, Any]
    paths: Sequence[str]
    env: dict[str, str]
    scratch: Path
    _outputs: dict[tuple[str, str], dict[str, str]] = field(default_factory=dict)
    _counter: int = 0

    # -- per lane ----------------------------------------------------------

    def sites_for(self, lane: LaneLike) -> list[_Site]:
        sites: list[_Site] = []
        for workflow in self.workflows:
            if workflow.pull_request is None:
                continue
            for job_id, job in workflow.jobs.items():
                steps = job.get("steps") if isinstance(job, dict) else None
                if not isinstance(steps, list):
                    continue
                matched = [
                    index
                    for index, step in enumerate(steps)
                    if isinstance(step, dict)
                    and isinstance(step.get("run"), str)
                    and _step_matches(lane, step["run"], self.pixi_data)
                ]
                if matched:
                    sites.append(self._site(lane, workflow, job_id, job, matched))
        return sites

    def _site(self, lane: LaneLike, workflow: Workflow, job_id: str, job: dict[str, Any], matched: list[int]) -> _Site:
        try:
            fires, rule = _pull_request_fires(workflow.pull_request or {}, self.paths)
            if not fires:
                return _Site(workflow.file, job_id, "skip", rule)
            holds, rule = self._job_holds(workflow, job_id, job)
            if not holds:
                return _Site(workflow.file, job_id, "skip", rule)
            legs = self._legs(workflow, job)
            if not legs:
                return _Site(workflow.file, job_id, "skip", "strategy.matrix expands to no legs")
            reasons: list[str] = []
            for leg in legs:
                for index in matched:
                    step = job["steps"][index]
                    holds, why = _step_holds(step, leg)
                    if not holds:
                        reasons.append(why)
                        continue
                    text = _expand(step["run"], {f"matrix.{k}": v for k, v in leg.items()}, strict=False)
                    if _step_matches(lane, text, self.pixi_data):
                        return _Site(workflow.file, job_id, "run", f"{workflow.file} job {job_id!r} fires")
                    reasons.append(f"no matrix leg {leg} runs this lane")
            return _Site(workflow.file, job_id, "skip", "; ".join(dict.fromkeys(reasons)) or "no matrix leg runs it")
        except _Unevaluable as exc:
            return _Site(workflow.file, job_id, "unknown", str(exc))

    # -- job conditions, matrix --------------------------------------------

    def _job_holds(self, workflow: Workflow, job_id: str, job: dict[str, Any]) -> tuple[bool, str]:
        if "if" not in job:
            return True, ""
        text = _normalize_condition(job["if"])
        match = _NEEDS_CONDITION.fullmatch(text)
        if not match:
            raise _Unevaluable(f"job {job_id!r} if: {job['if']!r} is not a needs.<job>.outputs.<x> comparison")
        dep, name, operator, literal = match.groups()
        value = self._needs_output(workflow, job, dep, name)
        holds = value == literal if operator == "==" else value != literal
        return holds, f"job {job_id!r} if: {text} is false (needs.{dep}.outputs.{name} = {value!r})"

    def _needs_output(self, workflow: Workflow, job: dict[str, Any], dep: str, name: str) -> str:
        needs = job.get("needs")
        needed = [needs] if isinstance(needs, str) else list(needs or [])
        if dep not in needed:
            raise _Unevaluable(f"needs.{dep}.outputs.{name}: job does not need {dep!r}")
        outputs = self._job_outputs(workflow, dep)
        if name not in outputs:
            raise _Unevaluable(f"needs.{dep}.outputs.{name}: job {dep!r} declares no output {name!r}")
        return outputs[name]

    def _legs(self, workflow: Workflow, job: dict[str, Any]) -> list[dict[str, str]]:
        strategy = job.get("strategy")
        matrix = strategy.get("matrix") if isinstance(strategy, dict) else None
        if matrix is None:
            return [{}]
        if not isinstance(matrix, dict):
            raise _Unevaluable(f"strategy.matrix {matrix!r} is not a mapping")
        legs: list[dict[str, str]] = [{}]
        for key, values in matrix.items():
            if key in ("include", "exclude"):
                raise _Unevaluable(f"strategy.matrix.{key} is not evaluated")
            options = self._matrix_values(workflow, job, key, values)
            legs = [{**leg, key: option} for leg in legs for option in options]
        return legs

    def _matrix_values(self, workflow: Workflow, job: dict[str, Any], key: str, values: Any) -> list[str]:
        if isinstance(values, str):
            match = _FROM_JSON.fullmatch(values.strip())
            if not match:
                raise _Unevaluable(f"strategy.matrix.{key}: {values!r} is not fromJSON(needs.<job>.outputs.<x>)")
            raw = self._needs_output(workflow, job, match.group(1), match.group(2))
            try:
                values = yaml.safe_load(raw) if raw else []
            except yaml.YAMLError as exc:
                raise _Unevaluable(f"strategy.matrix.{key}: {raw!r} is not JSON: {exc}") from exc
        if not isinstance(values, list) or not all(isinstance(v, (str, int)) for v in values):
            raise _Unevaluable(f"strategy.matrix.{key}: {values!r} is not a list of scalars")
        return [str(v) for v in values]

    # -- the workflow's own `changes` job -----------------------------------

    def _context(self) -> dict[str, str]:
        return {
            "github.event_name": "pull_request",
            "github.base_ref": BASE_BRANCH,
            "github.workspace": str(self.root),
        }

    def _job_outputs(self, workflow: Workflow, job_id: str) -> dict[str, str]:
        key = (workflow.file, job_id)
        if key not in self._outputs:
            self._outputs[key] = self._run_job(workflow, job_id)
        return self._outputs[key]

    def _run_job(self, workflow: Workflow, job_id: str) -> dict[str, str]:
        job = workflow.jobs.get(job_id)
        if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
            raise _Unevaluable(f"job {job_id!r} has no steps to run")
        if job.get("needs") or "if" in job:
            raise _Unevaluable(f"job {job_id!r} has its own needs/if; its outputs are not evaluated")
        context = self._context()
        step_outputs: dict[str, dict[str, str]] = {}
        for step in job["steps"]:
            if not isinstance(step, dict) or not isinstance(step.get("run"), str):
                continue  # `uses:` steps (checkout, setup) produce no outputs we read
            if "if" in step:
                raise _Unevaluable(f"job {job_id!r}: a step has an if: {step['if']!r}")
            shell = step.get("shell")
            if shell not in (None, "bash"):
                raise _Unevaluable(f"job {job_id!r}: shell {shell!r} is not bash")
            self._counter += 1
            output_file = self.scratch / f"output-{self._counter}"
            output_file.write_text("", encoding="utf-8")
            env = dict(self.env)
            for source in (workflow.data.get("env"), job.get("env"), step.get("env")):
                if isinstance(source, dict):
                    env.update({str(k): _expand(str(v), context, strict=True) for k, v in source.items()})
            env.update(
                {
                    "GITHUB_OUTPUT": str(output_file),
                    "GITHUB_ENV": str(self.scratch / "github-env"),
                    "GITHUB_PATH": str(self.scratch / "github-path"),
                    "GITHUB_STEP_SUMMARY": str(self.scratch / "github-summary"),
                    "GITHUB_EVENT_NAME": "pull_request",
                    "GITHUB_BASE_REF": env.get("GITHUB_BASE_REF") or BASE_BRANCH,
                    "GITHUB_WORKSPACE": str(self.root),
                }
            )
            argv = ["bash", "--noprofile", "--norc", "-e"]
            if shell == "bash":
                argv += ["-o", "pipefail"]
            argv += ["-c", _expand(step["run"], context, strict=True)]
            result = _run(self.process, argv, self.root, env, _SCRIPT_TIMEOUT_S)
            if result.returncode != 0:
                tail = (result.stderr.strip().splitlines() or [""])[-1]
                raise _Unevaluable(f"job {job_id!r} step {step.get('id', '?')!r} exited {result.returncode}: {tail}")
            if isinstance(step.get("id"), str):
                step_outputs[step["id"]] = _parse_github_output(output_file.read_text(encoding="utf-8"), job_id)
        resolved: dict[str, str] = {}
        for name, expression in (job.get("outputs") or {}).items():
            match = _STEP_OUTPUT.fullmatch(str(expression).strip())
            if not match or match.group(1) not in step_outputs:
                raise _Unevaluable(f"job {job_id!r} output {name!r} = {expression!r} is not a run step's output")
            resolved[str(name)] = step_outputs[match.group(1)].get(match.group(2), "")
        return resolved


def _step_holds(step: dict[str, Any], leg: Mapping[str, str]) -> tuple[bool, str]:
    if "if" not in step:
        return True, ""
    text = _normalize_condition(step["if"])
    match = _MATRIX_CONDITION.fullmatch(text)
    if not match or match.group(1) not in leg:
        raise _Unevaluable(f"step if: {step['if']!r} is not a matrix.<key> comparison")
    key, operator, literal = match.groups()
    holds = leg[key] == literal if operator == "==" else leg[key] != literal
    return holds, f"step if: {text} is false"


def _parse_github_output(text: str, job_id: str) -> dict[str, str]:
    outputs: dict[str, str] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip():
            continue
        heredoc = _OUTPUT_HEREDOC.fullmatch(line.strip())
        if heredoc:
            name, delimiter = heredoc.groups()
            body: list[str] = []
            while i < len(lines) and lines[i] != delimiter:
                body.append(lines[i])
                i += 1
            if i >= len(lines):
                raise _Unevaluable(f"job {job_id!r}: unterminated GITHUB_OUTPUT heredoc {name!r}")
            i += 1
            outputs[name] = "\n".join(body)
        elif "=" in line:
            name, value = line.split("=", 1)
            outputs[name] = value
        else:
            raise _Unevaluable(f"job {job_id!r}: unreadable GITHUB_OUTPUT line {line!r}")
    return outputs


# ---------------------------------------------------------------------------
# The selection
# ---------------------------------------------------------------------------


def _outcome(sites: Sequence[_Site]) -> tuple[bool, str, list[_Site]]:
    if not sites:
        return True, "no CI counterpart in .github/workflows (always runs)", []
    firing = [s for s in sites if s.outcome == "run"]
    if firing:
        return True, firing[0].rule, []
    unknown = [s for s in sites if s.outcome == "unknown"]
    if unknown:
        detail = "; ".join(f"{s.workflow} job {s.job!r}: {s.rule}" for s in unknown)
        return True, f"cannot evaluate, so it runs: {detail}", []
    return False, "", list(sites)


def _select_all(
    lanes: Sequence[LaneLike], reason: str, changed: Sequence[str] = (), dirty: Sequence[str] = ()
) -> Selection:
    return Selection(
        base_ref=BASE_REF,
        all_reason=reason,
        changed_paths=tuple(changed),
        dirty_paths=tuple(dirty),
        verdicts=tuple(LaneVerdict(lane.task, lane.environment, True, f"every lane runs: {reason}") for lane in lanes),
    )


def select_lanes(
    repo_root: Path,
    lanes: Sequence[LaneLike],
    pixi_data: Mapping[str, Any],
    *,
    process: PosixProcess | None = None,
) -> Selection:
    """The lanes CI would run for this diff, read from ``.github/workflows/*.yml``.

    Never raises: a diff or workflow the reader cannot read selects every lane and says why.
    """
    repo_root = repo_root.resolve()
    proc = process or PosixProcess()
    changed: list[str] = []
    dirty: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="preflight-select-") as scratch_name:
            return _select(repo_root, lanes, pixi_data, proc, Path(scratch_name), changed, dirty)
    except _SelectAll as exc:
        return _select_all(lanes, str(exc), changed, dirty)
    except Exception as exc:  # noqa: BLE001 -- a lane that cannot decide runs
        return _select_all(lanes, f"selection failed ({type(exc).__name__}: {exc})", changed, dirty)


def _select(
    root: Path,
    lanes: Sequence[LaneLike],
    pixi_data: Mapping[str, Any],
    process: PosixProcess,
    scratch: Path,
    changed: list[str],
    dirty: list[str],
) -> Selection:
    env = _git_env()
    probe = _git(process, root, ["rev-parse", "--verify", "--quiet", BASE_REF], env)
    if probe.returncode != 0:
        raise _SelectAll(f"{BASE_REF} does not exist")
    base_sha = probe.stdout.strip()
    workflows = load_workflows(root)

    changed.extend(
        _nul_paths(
            _git_ok(
                process,
                root,
                ["diff", "--name-only", "-z", "--no-renames", f"{BASE_REF}...HEAD"],
                env,
                "reading the diff",
            )
        )
    )
    for args in (
        ["diff", "--name-only", "-z", "--no-renames", "--cached"],
        ["diff", "--name-only", "-z", "--no-renames"],
        ["ls-files", "-z", "--others", "--exclude-standard"],
    ):
        dirty.extend(
            p for p in _nul_paths(_git_ok(process, root, args, env, "reading the working tree")) if p not in dirty
        )

    states = [_State(root, process, workflows, pixi_data, tuple(changed), env, scratch)]
    if dirty:
        snapshot_env = _snapshot_env(process, root, scratch, env, base_sha)
        union = tuple(dict.fromkeys([*changed, *dirty]))
        states.append(_State(root, process, workflows, pixi_data, union, snapshot_env, scratch))

    verdicts: list[LaneVerdict] = []
    for lane in lanes:
        outcomes = [_outcome(state.sites_for(lane)) for state in states]
        chosen = next((o for o in outcomes if o[0]), None)
        if chosen is not None:
            verdicts.append(LaneVerdict(lane.task, lane.environment, True, reason=chosen[1]))
            continue
        skipped = outcomes[-1][2]  # the most complete view of the tree decides the journaled rule
        verdicts.append(
            LaneVerdict(
                lane.task,
                lane.environment,
                False,
                workflow="; ".join(dict.fromkeys(s.workflow for s in skipped)),
                rule="; ".join(f"{s.workflow} job {s.job!r}: {s.rule}" for s in skipped),
            )
        )
    return Selection(
        base_ref=BASE_REF,
        all_reason=None,
        changed_paths=tuple(changed),
        dirty_paths=tuple(dirty),
        verdicts=tuple(verdicts),
    )


def _evaluation_states(
    root: Path,
    pixi_data: Mapping[str, Any],
    process: PosixProcess,
    scratch: Path,
) -> list[_State]:
    """Build the same workflow-evaluation states ``_select`` uses (for service mutex keys)."""
    changed: list[str] = []
    dirty: list[str] = []
    env = _git_env()
    probe = _git(process, root, ["rev-parse", "--verify", "--quiet", BASE_REF], env)
    if probe.returncode != 0:
        raise _SelectAll(f"{BASE_REF} does not exist")
    base_sha = probe.stdout.strip()
    workflows = load_workflows(root)
    changed.extend(
        _nul_paths(
            _git_ok(
                process,
                root,
                ["diff", "--name-only", "-z", "--no-renames", f"{BASE_REF}...HEAD"],
                env,
                "reading the diff",
            )
        )
    )
    for args in (
        ["diff", "--name-only", "-z", "--no-renames", "--cached"],
        ["diff", "--name-only", "-z", "--no-renames"],
        ["ls-files", "-z", "--others", "--exclude-standard"],
    ):
        dirty.extend(
            p for p in _nul_paths(_git_ok(process, root, args, env, "reading the working tree")) if p not in dirty
        )
    states = [_State(root, process, workflows, pixi_data, tuple(changed), env, scratch)]
    if dirty:
        snapshot_env = _snapshot_env(process, root, scratch, env, base_sha)
        union = tuple(dict.fromkeys([*changed, *dirty]))
        states.append(_State(root, process, workflows, pixi_data, union, snapshot_env, scratch))
    return states


def _firing_site(states: Sequence[_State], lane: LaneLike) -> _Site | None:
    for state in states:
        sites = state.sites_for(lane)
        selected, _, _ = _outcome(sites)
        if not selected:
            continue
        firing = next((s for s in sites if s.outcome == "run"), None)
        if firing is not None:
            return firing
        if not sites:
            return None
    return None


def _service_mutex_key_from_states(states: Sequence[_State], lane: LaneLike) -> str | None:
    site = _firing_site(states, lane)
    if site is None:
        return None
    workflows = states[0].workflows
    workflow = next((w for w in workflows if w.file == site.workflow), None)
    if workflow is None:
        return None
    job = workflow.jobs.get(site.job)
    if not isinstance(job, dict):
        return None
    services = job.get("services")
    if not isinstance(services, dict) or not services:
        return None
    return f"services:{','.join(sorted(str(k) for k in services))}"


def lane_service_mutex_key(
    repo_root: Path,
    lane: LaneLike,
    pixi_data: Mapping[str, Any],
    *,
    process: PosixProcess | None = None,
) -> str | None:
    """Mutex key when the lane's CI counterpart job declares ``services:``, else ``None``."""
    keys = service_mutex_keys(repo_root, [lane], pixi_data, process=process)
    return keys.get((lane.task, lane.environment))


def _static_service_mutex_key(
    lane: LaneLike,
    workflows: Sequence[Workflow],
    pixi_data: Mapping[str, Any],
) -> str | None:
    for workflow in workflows:
        if workflow.pull_request is None:
            continue
        for job_id, job in workflow.jobs.items():
            if not isinstance(job, dict):
                continue
            steps = job.get("steps")
            if not isinstance(steps, list):
                continue
            if not any(
                isinstance(step, dict)
                and isinstance(step.get("run"), str)
                and _step_matches(lane, step["run"], pixi_data)
                for step in steps
            ):
                continue
            services = job.get("services")
            if isinstance(services, dict) and services:
                return f"services:{','.join(sorted(str(k) for k in services))}"
    return None


def static_service_mutex_keys(
    repo_root: Path,
    lanes: Sequence[LaneLike],
    pixi_data: Mapping[str, Any],
) -> dict[tuple[str, str], str | None]:
    """Map ``(task, environment)`` to a service mutex key by reading workflow YAML only."""
    try:
        workflows = load_workflows(repo_root.resolve())
    except _SelectAll:
        return {(lane.task, lane.environment): None for lane in lanes}
    return {(lane.task, lane.environment): _static_service_mutex_key(lane, workflows, pixi_data) for lane in lanes}


def service_mutex_keys(
    repo_root: Path,
    lanes: Sequence[LaneLike],
    pixi_data: Mapping[str, Any],
    *,
    process: PosixProcess | None = None,
) -> dict[tuple[str, str], str | None]:
    """Map ``(task, environment)`` to a service mutex key (or ``None``).

    Uses the same firing-site logic as lane selection (runs workflow ``changes`` jobs).
    ``run_preflight`` prefers :func:`static_service_mutex_keys` to avoid a second evaluation pass.
    """
    repo_root = repo_root.resolve()
    proc = process or PosixProcess()
    try:
        with tempfile.TemporaryDirectory(prefix="preflight-services-") as scratch_name:
            states = _evaluation_states(repo_root, pixi_data, proc, Path(scratch_name))
    except _SelectAll:
        return {(lane.task, lane.environment): None for lane in lanes}
    return {(lane.task, lane.environment): _service_mutex_key_from_states(states, lane) for lane in lanes}
