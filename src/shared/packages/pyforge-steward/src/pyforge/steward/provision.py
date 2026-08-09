"""Steward's `provision` duty-adapter module (AD-1/AD-5) — Epic 3's single
file, mirrors `deploy.py`'s "one module per duty" precedent.

Epic 3 is a thin CLI face over the existing pixi estate and
`scripts/bmad-loop-worktree` — this module never reimplements pixi's own
environment-resolution logic, nor `bmad-loop-worktree`'s own worktree
provisioning (AD-1/AD-5). Every primitive below is either a read of
`pixi.toml`'s own declared `[environments]` table, or a thin `subprocess`
wrap of the real `pixi`/`bmad-loop-worktree` binaries.

Story 3.1 slice: `load_pixi_environments` (a read-only `tomllib` parse of
`pixi.toml`'s `[environments]` table — name -> composing features, handling
both the shorthand list form and the explicit `{ features = [...] }` table
form) and `materialize_environment` (a `pixi install -e <name>` subprocess
wrap). Wired as `steward provision --env <name>`.

Story 5.1 RETIRED the Story 3.2 slice. `provision --runner bmad-loop` used to
wrap the LEGACY `scripts/bmad-loop-worktree`; `marshal init` is a strict
superset (worktree + marker/symlink agreement + the AD-11 never-write proof +
an idempotent step report), so two stations were shipping two ways to make the
same thing, one of them the weaker one. `--runner` now REPORTS and points at
`marshal init <slug>`; it never provisions. `run_bmad_loop_worktree` and its
stdout parser are deleted rather than left importable — a retirement that
leaves the old path callable is a deprecation, not a removal.
`_BMAD_LOOP_WORKTREE_RELATIVE_PATH` survives: `repo_root()` locates the
monorepo by finding that script, which is unrelated to running it.

Story 3.3 slice: `format_environments` — read-only text/`--json` rendering
of `load_pixi_environments`'s own output. Wired as `steward provision
--list [--json]`.

Story 3.4 slice: `check_environment_sync` — wraps the EXACT sync-gate
comparison `.github/workflows/scripts/linter.py` already runs on every PR
(read `environment.yaml`, run `pixi project export conda-environment -e
build`, compare both `.rstrip()`'d) rather than reimplementing the
comparison a second way (AD-1). Wired as `steward provision --verify`.

Story 6.1 slice (Epic 6, `--module`): `_SUPPORTED_MODULES` (currently just
`{"bmb"}`), `provision_module` (assembles `module.yaml`'s own declared
variable defaults into an answers JSON, then drives BMB's own
`bmad-bmb-setup` skill scripts -- `merge-config.py` then `merge-help-csv.py`
-- as `uv run` subprocesses; Steward never reimplements their merge/
anti-zombie logic, AD-1) and `_materialize_module_output_dirs` (a read-only
reuse of `merge-config.py`'s own `apply_result_templates` substitution, to
`mkdir -p` any `{project-root}`-prefixed output directory the module
declares -- SKILL.md names this a caller responsibility, not something
either script performs). Deliberately never passes `--legacy-dir` to either
script and never invokes `cleanup-legacy.py` at all: this repo's actual
`_bmad/core/config.yaml` is a *different*, already-governance-owned
module's legacy config, and `cleanup-legacy.py --module-code bmb` would
`shutil.rmtree` it as an unconditional side effect of its own hardcoded
`[module_code, "core"]` removal list (see the story spec's Design Notes for
the full evidence trail). Wired as `steward provision --module <name>
[--json]`, the new first precedence check ahead of `--verify`.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import yaml

from .interfaces import DutyResult

# ── Repo-root resolution (mirrors `deploy.py`'s/`keys.py`'s own walk-up
# precedent, keyed on a marker unique to the repo root that THIS duty
# actually cares about — `pixi.toml` itself is NOT a safe marker, because
# `src/shared/packages/pyforge-steward/pixi.toml` is a second, unrelated
# pixi.toml belonging to this very package, which a naive walk-up would hit
# FIRST when searching from this file's own location) ─────────────────────

_BMAD_LOOP_WORKTREE_RELATIVE_PATH = Path("scripts/bmad-loop-worktree")
_PIXI_TOML_RELATIVE_PATH = Path("pixi.toml")
_ENVIRONMENT_YAML_RELATIVE_PATH = Path("environment.yaml")


def repo_root() -> Path:
    """Return the local-recipes checkout root.

    Walks up from this file's own resolved location looking for
    `scripts/bmad-loop-worktree` — unlike `pixi.toml`, that path exists
    exactly once in this repo, at the true root, so it cannot be confused
    with the package-local `pixi.toml` this very module ships alongside.
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / _BMAD_LOOP_WORKTREE_RELATIVE_PATH).is_file():
            return ancestor
    raise RuntimeError(
        f"provision.py: could not locate {_BMAD_LOOP_WORKTREE_RELATIVE_PATH} "
        f"by walking up from {here} — this module must live inside a "
        "local-recipes checkout."
    )


# ── Environment inventory (FR-12, Story 3.1) ────────────────────────────────


def load_pixi_environments(*, cwd: str | Path) -> dict[str, tuple[str, ...]]:
    """Parse `pixi.toml`'s `[environments]` table into `{name: features}`.

    Read-only — Steward never writes to `pixi.toml` (AD-5). Handles both
    shapes pixi's own manifest allows: the shorthand list form (`name =
    ["feat1", "feat2"]`, where the list doubles as both the environment's
    membership and its feature composition) and the explicit table form
    (`name = { features = [...], no-default-feature = true }`). An entry of
    neither shape degrades to an empty feature tuple rather than raising —
    this primitive reports what pixi.toml declares, it does not validate
    pixi's own manifest schema (that is `pixi`'s job, exercised the moment
    `materialize_environment` actually shells out to it).

    Raises `FileNotFoundError` if `pixi.toml` doesn't exist at `cwd`, and
    `tomllib.TOMLDecodeError` for a malformed manifest — both propagated,
    not swallowed.
    """
    pixi_toml = Path(cwd) / _PIXI_TOML_RELATIVE_PATH
    with pixi_toml.open("rb") as f:
        document = tomllib.load(f)
    raw = document.get("environments", {})
    environments: dict[str, tuple[str, ...]] = {}
    for name, value in raw.items():
        if isinstance(value, list):
            environments[name] = tuple(value)
        elif isinstance(value, dict):
            environments[name] = tuple(value.get("features", ()))
        else:
            environments[name] = ()
    return environments


def format_environments(environments: dict[str, tuple[str, ...]], *, as_json: bool) -> str:
    """Render `environments` for `steward provision --list`.

    `as_json=True`: a JSON object, `{name: [features...]}`, sorted by name —
    `{}` for no environments, the correct machine-parseable empty state.
    `as_json=False`: an aligned text table (name + composing features); a
    plain sentence for no environments.
    """
    if as_json:
        return json.dumps(
            {name: list(environments[name]) for name in sorted(environments)}, indent=2
        )
    if not environments:
        return "provision --list: no environments found in pixi.toml"
    width = max(len(name) for name in environments)
    lines = [
        f"{name:<{width}}  {', '.join(environments[name])}" for name in sorted(environments)
    ]
    return "\n".join(lines)


# ── Environment materialization (FR-12, Story 3.1) ──────────────────────────


def materialize_environment(name: str, *, cwd: str | Path) -> subprocess.CompletedProcess[str]:
    """`pixi install -e <name>` as a subprocess (AD-1/AD-5) — no reimplemented
    environment-resolution logic; this only shells out to the real `pixi`
    binary. `cwd` is the pixi project root to install into — the main repo
    root for `--env`, or a freshly provisioned worktree for `--runner
    bmad-loop --env` (Story 3.2).

    Raises `subprocess.CalledProcessError` on a non-zero exit — propagated,
    not swallowed — caught only at `ProvisionDuty`'s boundary.
    """
    return subprocess.run(
        ["pixi", "install", "-e", name],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


# ── Runner provisioning (FR-13, Story 3.2) ──────────────────────────────────

def _run_list(ns: argparse.Namespace) -> DutyResult:
    """`provision --list [--json]` (Story 3.3)."""
    root = repo_root()
    environments = load_pixi_environments(cwd=root)
    return DutyResult(
        ok=True, summary=format_environments(environments, as_json=getattr(ns, "json", False))
    )


# ── Sync-gate check (FR-15, Story 3.4) ──────────────────────────────────────

_SYNC_EXPORT_CMD: tuple[str, ...] = ("pixi", "project", "export", "conda-environment", "-e", "build")


def check_environment_sync(*, cwd: str | Path) -> tuple[bool, str]:
    """Wrap the EXACT sync-gate check `.github/workflows/scripts/linter.py`
    already runs on every PR to this repo (AD-1: reuse, never reimplement
    the comparison) — reads `environment.yaml`, runs `pixi project export
    conda-environment -e build`, and compares both `.rstrip()`'d, exactly
    like the linter's own logic.

    Returns `(in_sync, diff_text)`. `diff_text` is empty when in sync,
    otherwise a unified diff (`environment.yaml` vs. the freshly exported
    text).

    Raises `FileNotFoundError` if `environment.yaml` doesn't exist at `cwd`,
    and `subprocess.CalledProcessError` if `pixi project export` itself
    fails — both propagated, not swallowed.
    """
    root = Path(cwd)
    original = (root / _ENVIRONMENT_YAML_RELATIVE_PATH).read_text(encoding="utf-8").rstrip()
    exported = subprocess.run(
        list(_SYNC_EXPORT_CMD),
        cwd=str(root),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.rstrip()
    if original == exported:
        return True, ""
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            exported.splitlines(keepends=True),
            fromfile="environment.yaml",
            tofile="pixi project export conda-environment -e build",
        )
    )
    return False, diff


def _run_verify(ns: argparse.Namespace) -> DutyResult:  # noqa: ARG001 -- no flags yet
    """`provision --verify` (Story 3.4)."""
    root = repo_root()
    in_sync, diff = check_environment_sync(cwd=root)
    if in_sync:
        return DutyResult(
            ok=True, summary="provision --verify: environment.yaml is in sync with pixi.toml"
        )
    return DutyResult(
        ok=False,
        summary=(
            "provision --verify: environment.yaml is out of sync with pixi.toml. "
            "Fix by running `pixi project export conda-environment -e build > "
            f"environment.yaml`.\n{diff}"
        ),
    )


# ── Module provisioning (FR-?, Story 6.1) ───────────────────────────────────

# name -> the module's own installed setup-skill dir, relative to repo root.
# `bmb` is the only registered backend as of Story 6.1 -- Skill Forge's own
# `install` has no non-interactive CLI flag (v1.0.0 `STABILITY.md`), so
# wrapping it needs a new, committed headless driver, deferred not dropped.
# Keep the `--module` help text in `cli.py`'s `_add_provision_subparsers` in
# sync with this set (mirrors this file's own `DUTIES`/`_HELP` precedent in
# `cli.py`, not derived to avoid an eager cross-module import at parser-build
# time -- `resolve_duty` is the one place that imports duty modules lazily).
_SUPPORTED_MODULES: dict[str, Path] = {
    "bmb": Path(".pixi/envs/local-recipes/share/bmad-builder/skills/bmad-bmb-setup"),
}

_MODULE_YAML_RELATIVE_PATH = Path("assets/module.yaml")
_MODULE_HELP_CSV_RELATIVE_PATH = Path("assets/module-help.csv")
_BMAD_RELATIVE_PATH = Path("_bmad")


def _module_variable_defaults(module_yaml: dict[str, object]) -> dict[str, object]:
    """Collect `{key: default}` for every top-level `module.yaml` entry that
    is itself a dict declaring a `default` -- the module's own declared
    variable set (`code`, `name`, `module_greeting`, etc. are scalars and are
    skipped). Assembled verbatim into the answers JSON; never prompts (this
    path is non-interactive by construction, AD-1)."""
    return {
        key: value["default"]
        for key, value in module_yaml.items()
        if isinstance(value, dict) and "default" in value
    }


def _materialize_module_output_dirs(
    module_yaml: dict[str, object], *, cwd: str | Path
) -> tuple[str, ...]:
    """`mkdir -p` every `module.yaml` variable whose value -- after the same
    `{value}`-template substitution `merge-config.py`'s own
    `apply_result_templates` performs -- is a `{project-root}`-prefixed
    path. SKILL.md's own "Create Output Directories" step names this a
    caller responsibility; neither merge script creates any directory
    itself. Returns the repo-relative paths created, for reporting.
    """
    root = Path(cwd)
    created: list[str] = []
    for var in module_yaml.values():
        if not (isinstance(var, dict) and "default" in var):
            continue
        default = var["default"]
        if "result" in var and "{project-root}" not in str(default):
            resolved = str(var["result"]).replace("{value}", str(default))
        else:
            resolved = str(default)
        if not resolved.startswith("{project-root}"):
            continue
        relative = resolved.removeprefix("{project-root}").lstrip("/")
        try:
            (root / relative).mkdir(parents=True, exist_ok=True)
        except FileExistsError as exc:
            raise RuntimeError(
                f"module output path {relative!r} already exists and is not a directory"
            ) from exc
        created.append(relative)
    return tuple(created)


def provision_module(name: str, *, cwd: str | Path) -> dict[str, object]:
    """Provision the module registered as `name` by driving its own
    non-interactive setup-skill scripts as subprocesses (AD-1) -- Steward
    assembles their documented CLI arguments from `module.yaml`'s own
    declared variable defaults, never reimplements the scripts' own merge/
    anti-zombie logic.

    Deliberately excludes `--legacy-dir` on both scripts and never invokes
    `cleanup-legacy.py` at all: this repo's actual `_bmad/core/` holds a
    *different*, already-governance-owned module's legacy config, and there
    is no genuine `_bmad/<name>/` legacy directory for `bmb` to migrate from
    in the first place (story spec Design Notes).

    Returns `{"merge_config": <parsed stdout>, "merge_help_csv": <parsed
    stdout>, "output_dirs_created": [...]}` -- each script's own JSON
    result, keyed by step.

    Raises `FileNotFoundError` if the module's setup-skill directory isn't
    installed under `.pixi/envs/local-recipes/...` (the `bmad-builder` pixi
    dependency), and `subprocess.CalledProcessError` if either script exits
    non-zero -- both propagated, not swallowed, caught only at
    `ProvisionDuty`'s existing boundary.
    """
    if name not in _SUPPORTED_MODULES:
        raise FileNotFoundError(f"module {name!r} is not registered in _SUPPORTED_MODULES")

    root = Path(cwd)
    skill_dir = root / _SUPPORTED_MODULES[name]
    if not skill_dir.is_dir():
        raise FileNotFoundError(
            f"module {name!r}'s setup-skill directory is missing at {skill_dir} "
            "-- the bmad-builder pixi dependency is not installed. Fix with "
            "`pixi install -e local-recipes`."
        )

    module_yaml_path = skill_dir / _MODULE_YAML_RELATIVE_PATH
    with module_yaml_path.open("r", encoding="utf-8") as f:
        module_yaml = yaml.safe_load(f)
    if not isinstance(module_yaml, dict):
        raise RuntimeError(f"{module_yaml_path} did not parse to a mapping -- malformed module.yaml")
    if module_yaml.get("code") != name:
        raise RuntimeError(
            f"module.yaml at {module_yaml_path} declares code={module_yaml.get('code')!r}, "
            f"which does not match the registered name {name!r} in _SUPPORTED_MODULES"
        )

    answers = {"module": _module_variable_defaults(module_yaml)}
    bmad_dir = root / _BMAD_RELATIVE_PATH

    with tempfile.TemporaryDirectory(prefix="steward-provision-module-") as tmpdir:
        answers_path = Path(tmpdir) / "answers.json"
        # `default=str`: a module.yaml default that YAML auto-converts to a
        # native type (an unquoted date/timestamp scalar) must not crash the
        # answers-file write; stringify anything json.dumps can't handle.
        answers_path.write_text(json.dumps(answers, default=str), encoding="utf-8")

        merge_config = subprocess.run(
            [
                "uv",
                "run",
                str(skill_dir / "scripts" / "merge-config.py"),
                "--config-path",
                str(bmad_dir / "config.yaml"),
                "--user-config-path",
                str(bmad_dir / "config.user.yaml"),
                "--module-yaml",
                str(module_yaml_path),
                "--answers",
                str(answers_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        merge_help_csv = subprocess.run(
            [
                "uv",
                "run",
                str(skill_dir / "scripts" / "merge-help-csv.py"),
                "--target",
                str(bmad_dir / "module-help.csv"),
                "--source",
                str(skill_dir / _MODULE_HELP_CSV_RELATIVE_PATH),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    output_dirs_created = _materialize_module_output_dirs(module_yaml, cwd=root)

    try:
        merge_config_result = json.loads(merge_config.stdout)
        merge_help_csv_result = json.loads(merge_help_csv.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"module {name!r}'s setup-skill scripts exited 0 but did not emit valid JSON: {exc}"
        ) from exc

    return {
        "merge_config": merge_config_result,
        "merge_help_csv": merge_help_csv_result,
        "output_dirs_created": list(output_dirs_created),
    }


def _run_module(ns: argparse.Namespace) -> DutyResult:
    """`provision --module <name>` (Story 6.1). An unrecognized name never
    reaches `provision_module`/a subprocess call -- it is reported directly,
    honoring `--json` via `ProvisionDuty._render_error` exactly like every
    other failure path this duty has (I/O Matrix: `--module <bad> --json`
    still yields a parseable `{"error": ...}` shape)."""
    name = ns.module
    if name not in _SUPPORTED_MODULES:
        supported = ", ".join(sorted(_SUPPORTED_MODULES))
        message = f"{name!r} is not a supported module. Supported modules: {supported}"
        return DutyResult(ok=False, summary=ProvisionDuty._render_error(ns, message))
    root = repo_root()
    steps = provision_module(name, cwd=root)
    if getattr(ns, "json", False):
        return DutyResult(ok=True, summary=json.dumps(steps, indent=2))
    dirs_note = (
        f"; created {', '.join(steps['output_dirs_created'])}" if steps["output_dirs_created"] else ""
    )
    return DutyResult(
        ok=True,
        summary=(
            f"provision --module: {name!r} provisioned (merge-config.py, merge-help-csv.py)"
            f"{dirs_note}"
        ),
    )


# ── ProvisionDuty (Duty-protocol adapter) ───────────────────────────────────

_PROVISION_HELP = (
    "available flags: --module <name> [--json] | --env <name> | "
    "--runner bmad-loop --env <name> | --list [--json] | --verify"
)


def _run_env(ns: argparse.Namespace) -> DutyResult:
    """`provision --env <name>` (Story 3.1)."""
    root = repo_root()
    environments = load_pixi_environments(cwd=root)
    name = ns.env
    if name not in environments:
        valid = ", ".join(sorted(environments))
        return DutyResult(
            ok=False,
            summary=(
                f"provision --env: {name!r} is not a valid pixi environment. "
                f"Valid environments: {valid}"
            ),
        )
    materialize_environment(name, cwd=root)
    return DutyResult(
        ok=True, summary=f"provision --env: {name!r} materialized (pixi install -e {name})"
    )


def _run_runner(ns: argparse.Namespace) -> DutyResult:
    """`provision --runner bmad-loop` — RETIRED (Story 5.1, AD-5).

    This wrapped the *legacy* `scripts/bmad-loop-worktree` while `marshal init`
    (Marshal Epic 1, 10 shipped stories) is a strict superset: the same worktree
    plus the marker/symlink agreement invariant, the AD-11 never-write proof, and
    an idempotent `done | skipped | failed` step report. Two stations shipping
    two ways to make the same thing, one of them the weaker one.

    It REPORTS rather than DELEGATES, deliberately. This station imports nothing
    from `pyforge.marshal` and shells to no `marshal` binary; proxying the front
    door would create the first cross-station coupling and re-wrap exactly the
    machinery this story removes. The Marshal/Steward seam puts judgment with the
    owning station and the front door with Marshal, so Steward points at it.

    Never silently provisions: the legacy path is gone, not deprecated-but-live.
    `--env <name>` alone (pixi environments, genuinely Steward's) is untouched.
    """
    runner = ns.runner
    if runner != "bmad-loop":
        return DutyResult(
            ok=False,
            summary=f"provision --runner: unknown runner {runner!r} (only 'bmad-loop' is supported)",
        )
    slug = ns.env or "<slug>"
    return DutyResult(
        ok=False,
        summary=(
            f"provision --runner bmad-loop is RETIRED (Story 5.1). Use "
            f"`marshal init {slug}` — it provisions the same worktree plus the "
            f"marker/symlink agreement check, the never-write proof and an "
            f"idempotent step report, none of which the legacy "
            f"scripts/bmad-loop-worktree this wrapped provides. "
            f"`steward provision --env {slug}` still materializes the pixi "
            f"environment, which remains Steward's."
        ),
    )


class ProvisionDuty:
    """The real `provision` duty — dispatches the `--module`/`--env`/
    `--runner`/`--list`/`--verify` flags (Epic 3 grew this class one flag
    per story through `--verify`; Epic 6 Story 6.1 adds `--module`).

    Unlike `keys`/`deploy`, `provision` has no verb subcommands — every
    action is a flag on the bare `provision` duty parser, matching each
    story's own `steward provision --env <name>` shape. Precedence when
    more than one flag is passed: `--module` > `--verify` > `--list` >
    `--runner` > `--env` (a documented judgment call, not a silent one —
    mirrors `DeployDuty`'s own `--build`-wins-over-`--dry-run` precedent;
    no AC defines combining them; `--module` lands at the top, matching
    each new story's flag landing at the top of this if-chain). Bare
    `steward provision` (no flags) degrades to `DutyResult(ok=True, ...)`
    naming the available flags (AD-7), matching `KeysDuty`'s/`DeployDuty`'s
    identical precedent. A subprocess failure (pixi, bmad-loop-worktree,
    `uv run merge-config.py`/`merge-help-csv.py`) is caught here as
    `subprocess.CalledProcessError` and reported as a duty-level failure,
    never conflated with an internal crash (AD-8 — that boundary is
    `cli.main()`'s alone).
    """

    name = "provision"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        try:
            if getattr(ns, "module", None) is not None:
                return _run_module(ns)
            if getattr(ns, "verify", False):
                return _run_verify(ns)
            if getattr(ns, "list", False):
                return _run_list(ns)
            if getattr(ns, "runner", None):
                return _run_runner(ns)
            if getattr(ns, "env", None):
                return _run_env(ns)
            return DutyResult(ok=True, summary=f"provision: {_PROVISION_HELP}")
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            cmd_name = " ".join(str(part) for part in exc.cmd) if exc.cmd else "subprocess"
            message = f"`{cmd_name}` exited {exc.returncode}: {stderr}"
            return DutyResult(ok=False, summary=self._render_error(ns, message))
        except (RuntimeError, FileNotFoundError, tomllib.TOMLDecodeError, yaml.YAMLError) as exc:
            return DutyResult(ok=False, summary=self._render_error(ns, str(exc)))

    @staticmethod
    def _render_error(ns: argparse.Namespace, message: str) -> str:
        """Every success path this duty has (`_run_list`'s own
        `format_environments(..., as_json=...)`) already honors `--json`;
        an error raised on ANY flag's path must too (review finding: an
        earlier draft only formatted the happy path, so `--list --json`
        against e.g. a malformed `pixi.toml` emitted a plain-text summary
        `cli.main()` prints verbatim -- unparseable by a caller that
        `json.loads()`s the output because `--json` was passed)."""
        if getattr(ns, "json", False):
            return json.dumps({"error": message}, indent=2)
        return f"provision: {message}"
