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

Story 6.1 slice (Epic 6, `--module`): `_SUPPORTED_MODULES` (bmb via setup-
skill scripts), `provision_module` (assembles `module.yaml`'s own declared
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

Story 15.3 slice (Epic 15 / CAP-3): grows `_SUPPORTED_MODULES` to
`{bmb, tea, cis, utility-skills, manticore}`. The four new names drive each
conda package's `*-install` entry point, skill-name-collision-check before
first wire, and record a `_bmad/config.yaml` manifest section so
`--list-modules` / Story 6.3's post-success gate see them. WDS is an
explicit skip (deprecated upstream, absorbing into bmad-ux) — documented in
`_SKIPPED_MODULES` and `--module` help, never registered.

Story 6.2 slice (Epic 6, `--list-modules`): `module_install_states` (a
pure, read-only membership check -- `_bmad/config.yaml`'s own top-level
keys against `_SUPPORTED_MODULES`'s registered names, the exact
anti-zombie key `merge-config.py`'s own `config[module_code] = ...`
writes; a missing file or a parse result that isn't a `dict` both degrade
to "no modules installed" rather than raising) and `format_module_states`
(mirrors `format_environments`'s own text/`--json` split). No subprocess
call and no new state file -- derive-don't-declare, matching `--list`'s
own `pixi.toml`-derived precedent. Wired as `steward provision
--list-modules [--json]`, the new first precedence check ahead of
`--module`.

Story 6.3 slice (Epic 6, `--module` partial-install naming): a partial
`--module` failure is no longer left for the operator to infer.
`_format_called_process_error` dedupes the `` `{cmd}` exited {code}:
{stderr} `` formatting `ProvisionDuty.run()`'s own except block already
applied inline; `_run_module` now wraps its `provision_module()` call in
a local `try/except (subprocess.CalledProcessError, RuntimeError)` that
appends whether `_bmad/config.yaml` already gained a `<name>` section
before the failure -- reusing `module_install_states` (Story 6.2) as the
one oracle, never a second, divergent check -- and, after a successful
call, consults `module_install_states` once more before reporting
`ok=True`, refusing to trust the wrapped scripts' own "exited 0"
self-report if `<name>` never actually landed (FR-21's "succeeds while
leaving the module unimportable" clause). `FileNotFoundError`
(unregistered name / missing backend dir) is deliberately not caught
locally -- both occur before any subprocess call, so Story 6.1's existing
message via `ProvisionDuty.run()`'s outer boundary already covers it.

Story 46.2 slice (AD-9): `_record_module_manifest` -- the roster writer
SHARED by every `CondaInstallBackend` module (tea/cis/utility-skills/
manticore) -- moves from `_bmad/config.yaml` to `_bmad/custom/config.toml`
`[modules.<name>]`, written via targeted text editing (locate-and-replace
an existing `^[modules.<name>]` block, or append) so this file's own
hand-written prose comments survive byte-for-byte; a full parse-mutate-
reserialize round trip through a TOML library would silently drop them.
`bmb` (`SetupSkillBackend`) is untouched -- `merge-config.py` still writes
`_bmad/config.yaml` itself. `module_install_states` becomes a two-location
read (new `_bmad/custom/config.toml` first, then the legacy `_bmad/
config.yaml`) so `cis`'s still-unmigrated Story 46.8 entry keeps reporting
`installed` alongside every freshly (re-)provisioned module. Nothing
migrates `cis`'s existing entry in place -- the read-side fallback is the
whole fix.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import tomllib
import yaml
from pyforge.core.atomic_write import atomic_write

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


# ── Module provisioning (FR-?, Story 6.1; Story 15.3 grows the registry) ─────

# Story 6.1 registered `bmb` via its setup-skill scripts. Story 15.3 (CAP-3)
# adds tea / cis / utility-skills / manticore via each conda package's
# `*-install` entry point. Skill Forge stays deferred (TTY-only Installer).
# Keep the `--module` help text in `cli.py`'s `_add_provision_subparsers` in
# sync with this set (mirrors this file's own `DUTIES`/`_HELP` precedent in
# `cli.py`, not derived to avoid an eager cross-module import at parser-build
# time -- `resolve_duty` is the one place that imports duty modules lazily).
#
# WDS (bmad-method-wds-expansion / code `wds`) is an explicit SKIP — not in
# `_SUPPORTED_MODULES`. Upstream deprecation citation: install-matrix.md
# ("DEPRECATED upstream — skip wiring") and docs/dreams/bmad-suite-channel-
# product.md (absorbing into bmad-ux). Never wire via `--module`.


@dataclass(frozen=True)
class SetupSkillBackend:
    """Drive BMB's own `bmad-bmb-setup` merge scripts (Story 6.1)."""

    kind: Literal["setup_skill"] = "setup_skill"
    skill_dir: Path = Path()  # relative to repo root


@dataclass(frozen=True)
class CondaInstallBackend:
    """Drive a conda package's `*-install` entry point (Story 15.3).

    `skill_source_dirs` names share/<package>/<dir> children that become
    `.claude/skills/` entries (tea: agents+workflows; utility/manticore:
    skills). `skill_names`, when non-empty, is an explicit allowlist matching
    the installer's own fixed list (cis) — used for collision checks and
    post-install verification instead of directory discovery.
    """

    installer: str
    share_package: str
    skill_source_dirs: tuple[str, ...] = ()
    skill_names: tuple[str, ...] = ()
    kind: Literal["conda_install"] = "conda_install"


ModuleBackend = SetupSkillBackend | CondaInstallBackend

_CIS_SKILL_NAMES: tuple[str, ...] = (
    "bmad-cis-agent-brainstorming-coach",
    "bmad-cis-agent-creative-problem-solver",
    "bmad-cis-agent-design-thinking-coach",
    "bmad-cis-agent-innovation-strategist",
    "bmad-cis-agent-presentation-master",
    "bmad-cis-agent-storyteller",
    "bmad-cis-design-thinking",
    "bmad-cis-innovation-strategy",
    "bmad-cis-problem-solving",
    "bmad-cis-storytelling",
)

_SUPPORTED_MODULES: dict[str, ModuleBackend] = {
    "bmb": SetupSkillBackend(
        skill_dir=Path(".pixi/envs/local-recipes/share/bmad-builder/skills/bmad-bmb-setup"),
    ),
    "tea": CondaInstallBackend(
        installer="bmad-tea-install",
        share_package="bmad-method-test-architecture-enterprise",
        skill_source_dirs=("agents", "workflows"),
    ),
    "cis": CondaInstallBackend(
        installer="bmad-cis-install",
        share_package="bmad-creative-intelligence-suite",
        skill_names=_CIS_SKILL_NAMES,
    ),
    "utility-skills": CondaInstallBackend(
        installer="bmad-utility-skills-install",
        share_package="bmad-utility-skills",
        skill_source_dirs=("skills",),
    ),
    "manticore": CondaInstallBackend(
        installer="bmad-manticore-install",
        share_package="bmad-manticore",
        skill_source_dirs=("skills",),
    ),
}

# Documented skip set — never registered, never provisionable. Citation only.
_SKIPPED_MODULES: dict[str, str] = {
    "wds": (
        "WDS (bmad-method-wds-expansion) is skip-decided: deprecated upstream "
        "(spec-bmad-suite-channel-product/install-matrix.md; Dream "
        "bmad-suite-channel-product — absorbing into bmad-ux). Not in "
        "_SUPPORTED_MODULES."
    ),
}

_MODULE_YAML_RELATIVE_PATH = Path("assets/module.yaml")
_MODULE_HELP_CSV_RELATIVE_PATH = Path("assets/module-help.csv")
_BMAD_RELATIVE_PATH = Path("_bmad")
_BMAD_CUSTOM_CONFIG_TOML_RELATIVE_PATH = Path("_bmad/custom/config.toml")
_CLAUDE_SKILLS_RELATIVE_PATH = Path(".claude/skills")
_LOCAL_RECIPES_ENV_RELATIVE_PATH = Path(".pixi/envs/local-recipes")


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


def _conda_prefix(*, cwd: Path, share_package: str | None = None) -> Path:
    """Resolve the conda/pixi prefix that holds suite share packages.

    Prefer this checkout's `.pixi/envs/local-recipes` when it already holds
    the requested share package — the same convention Story 6.1 used for the
    bmb setup-skill path, and what fresh-clone fixtures stage under. Fall
    back to `CONDA_PREFIX` (set when the operator is inside the env that owns
    the `*-install` entry points). Fresh-clone fixtures must not be defeated
    by an ambient `CONDA_PREFIX` pointing at a lean env (e.g. pyforge-steward)
    that does not ship the suite share trees.
    """
    local = cwd / _LOCAL_RECIPES_ENV_RELATIVE_PATH
    if share_package is not None:
        local_share = local / "share" / share_package
        if local_share.is_dir():
            return local
    elif local.is_dir():
        return local
    env = os.environ.get("CONDA_PREFIX")
    if env:
        return Path(env)
    if local.is_dir():
        return local
    raise FileNotFoundError(
        "CONDA_PREFIX is not set and "
        f"{_LOCAL_RECIPES_ENV_RELATIVE_PATH} is missing under {cwd} — activate "
        "the local-recipes pixi environment (or run via `pixi run -e "
        "local-recipes`) so conda package installers can find their share data."
    )


def _installer_skill_names(backend: CondaInstallBackend, *, share_root: Path) -> tuple[str, ...]:
    """Names the installer will place under `.claude/skills/`."""
    if backend.skill_names:
        return backend.skill_names
    names: list[str] = []
    for source in backend.skill_source_dirs:
        directory = share_root / source
        if not directory.is_dir():
            continue
        names.extend(sorted(p.name for p in directory.iterdir() if p.is_dir()))
    return tuple(names)


def _check_skill_name_collisions(
    name: str,
    skill_names: tuple[str, ...],
    *,
    cwd: Path,
    already_installed: bool,
) -> None:
    """Refuse to overwrite `.claude/skills/<skill>` that already exists when
    this module is not yet manifest-recorded (a foreign skill collision).
    Re-provision of an already-installed module is allowed (idempotent).
    """
    if already_installed or not skill_names:
        return
    skills_root = cwd / _CLAUDE_SKILLS_RELATIVE_PATH
    collisions = sorted(
        skill for skill in skill_names if (skills_root / skill).exists()
    )
    if collisions:
        raise RuntimeError(
            f"module {name!r}: skill-name collision(s) under "
            f"{_CLAUDE_SKILLS_RELATIVE_PATH}: {', '.join(collisions)} — refuse "
            "to overwrite skills that already exist before this module is "
            "manifest-recorded. Remove or rename the colliding skills, then "
            "re-run provision."
        )


def _toml_string(value: str) -> str:
    """A TOML basic-string literal for `value`. Every value this writer ever
    renders (`"steward"`, an installer entry-point name, a skill directory
    name) is a plain ASCII identifier with no quotes/backslashes, so JSON's
    escaping rules (a strict subset of TOML's for this class of string) are
    sufficient without adding a TOML-writing dependency."""
    return json.dumps(value)


def _render_module_toml_section(
    name: str, *, installer: str, skills: tuple[str, ...]
) -> str:
    """Render a `[modules.<name>]` section -- AD-9's target shape, carrying
    exactly the three fields the legacy `_bmad/config.yaml` entry carried
    (`provisioned_by`, `installer`, `skills`). A flat one-line `skills`
    array matches this file's own existing generated scalar-key style
    (`sidecar_path = "..."` etc.) -- no need to match `[modules.skf]`'s
    hand-authored, prose-commented multi-line style."""
    skills_array = ", ".join(_toml_string(s) for s in skills)
    return (
        f"[modules.{name}]\n"
        f"provisioned_by = {_toml_string('steward')}\n"
        f"installer = {_toml_string(installer)}\n"
        f"skills = [{skills_array}]\n"
    )


def _record_module_manifest(
    name: str,
    *,
    cwd: Path,
    installer: str,
    skills: tuple[str, ...],
) -> None:
    """Write/replace `[modules.<name>]` in `_bmad/custom/config.toml` (AD-9)
    -- the roster every `CondaInstallBackend` module's provisioning path
    (tea/cis/utility-skills/manticore) now records, so a fresh-clone
    provision is discoverable via `--list-modules`. `bmb`
    (`SetupSkillBackend`) never calls this function -- `merge-config.py`
    writes `_bmad/config.yaml` itself.

    Targeted text editing only: locate an existing `[modules.<name>]`
    header line and replace it plus its own key=value body lines only --
    stopping at the first blank line, comment line, or the next `[...]`
    header, whichever comes first (line-based, `\r\n`-tolerant) -- or
    append a new section with exactly one blank-line separator if no
    header is found. Never a parse-mutate-reserialize round trip through a
    TOML library, which would silently drop this file's own hand-written
    prose comments (`[core]`'s header block, `[modules.skf]`'s per-key
    explanations). Stopping at the first blank/comment/header line (rather
    than consuming everything up to the next section, as an earlier draft
    did) matters specifically because a blank-line separator or a comment
    describing the *following* section must survive a rewrite of *this*
    section untouched (review finding).

    `cis`'s own pre-existing entry (Story 46.8) still lives only in the
    legacy `_bmad/config.yaml` -- this function never touches that file or
    migrates that entry; the read side (`module_install_states`) checks
    both locations instead.
    """
    config_path = cwd / _BMAD_CUSTOM_CONFIG_TOML_RELATIVE_PATH
    original = config_path.read_text(encoding="utf-8") if config_path.is_file() else ""
    if original.strip():
        # Refuse to text-edit a destination that isn't even valid TOML today
        # -- the line-based editor below doesn't need a full parse to do its
        # job, but writing into an already-broken file would silently make
        # a real problem harder to diagnose (review finding: the legacy
        # YAML writer's own "must be a mapping" refusal had no equivalent
        # here after the AD-9 migration).
        try:
            tomllib.loads(original)
        except tomllib.TOMLDecodeError as exc:
            raise RuntimeError(
                f"cannot record module {name!r}: {_BMAD_CUSTOM_CONFIG_TOML_RELATIVE_PATH} "
                f"is not valid TOML ({exc})"
            ) from exc
    section_text = _render_module_toml_section(name, installer=installer, skills=skills)
    header = f"[modules.{name}]"
    lines = original.splitlines(keepends=True)
    header_idx = next(
        (i for i, line in enumerate(lines) if line.rstrip("\r\n") == header), None
    )
    if header_idx is not None:
        end_idx = header_idx + 1
        while end_idx < len(lines):
            stripped = lines[end_idx].strip()
            if stripped == "" or stripped.startswith("#") or stripped.startswith("["):
                break
            end_idx += 1
        updated = "".join(lines[:header_idx]) + section_text + "".join(lines[end_idx:])
    elif original.strip():
        updated = original.rstrip("\n") + "\n\n" + section_text
    else:
        updated = section_text

    # Atomic replace so a crash mid-write cannot leave a truncated config
    # (Story 14.2, CAP-2: pyforge-core's atomic_write is the sole write-open
    # + os.replace implementation -- also handles the parent mkdir).
    def _write(tmp: Path) -> None:
        tmp.write_text(updated, encoding="utf-8")

    atomic_write(config_path, _write)


def _provision_setup_skill(name: str, backend: SetupSkillBackend, *, cwd: Path) -> dict[str, object]:
    """Story 6.1 path: drive `merge-config.py` + `merge-help-csv.py`."""
    skill_dir = cwd / backend.skill_dir
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
    bmad_dir = cwd / _BMAD_RELATIVE_PATH

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

    output_dirs_created = _materialize_module_output_dirs(module_yaml, cwd=cwd)

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


def _provision_conda_install(
    name: str, backend: CondaInstallBackend, *, cwd: Path
) -> dict[str, object]:
    """Story 15.3 path: drive the package's `*-install` entry point, then
    record a `_bmad/custom/config.toml` `[modules.<name>]` manifest section
    (Story 46.2, AD-9) so `--list-modules` and Story 6.3's post-success gate
    see the module as installed.
    """
    prefix = _conda_prefix(cwd=cwd, share_package=backend.share_package)
    share_root = prefix / "share" / backend.share_package
    if not share_root.is_dir():
        raise FileNotFoundError(
            f"module {name!r}'s share package is missing at {share_root} — "
            f"the {backend.share_package} pixi/conda dependency is not "
            "installed. Fix with `pixi install -e local-recipes`."
        )

    skill_names = _installer_skill_names(backend, share_root=share_root)
    if not skill_names:
        raise RuntimeError(
            f"module {name!r}: no skills discovered under {share_root} "
            f"(sources={backend.skill_source_dirs!r}, names={backend.skill_names!r})"
        )

    already_installed = _module_install_state_or_none(name, cwd=cwd) == "installed"
    _check_skill_name_collisions(
        name, skill_names, cwd=cwd, already_installed=already_installed
    )

    dest = cwd / _CLAUDE_SKILLS_RELATIVE_PATH
    dest.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "CONDA_PREFIX": str(prefix)}
    completed = subprocess.run(
        [backend.installer, str(dest)],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    missing = [s for s in skill_names if not (dest / s).is_dir()]
    if missing:
        raise RuntimeError(
            f"module {name!r}: {backend.installer} exited 0 but skills still "
            f"missing under {_CLAUDE_SKILLS_RELATIVE_PATH}: {', '.join(missing)}"
        )

    _record_module_manifest(
        name, cwd=cwd, installer=backend.installer, skills=skill_names
    )

    return {
        "installer": backend.installer,
        "skills_installed": list(skill_names),
        "stdout": (completed.stdout or "").strip(),
        "output_dirs_created": [],
    }


def provision_module(name: str, *, cwd: str | Path) -> dict[str, object]:
    """Provision the module registered as `name` by driving its own
    non-interactive install path as a subprocess (AD-1) -- Steward never
    reimplements the module's installer.

    Backends:
    - `SetupSkillBackend` (`bmb`): BMB's `merge-config.py` /
      `merge-help-csv.py` (Story 6.1). Deliberately excludes `--legacy-dir`
      and never invokes `cleanup-legacy.py`.
    - `CondaInstallBackend` (tea / cis / utility-skills / manticore): the
      conda package's `*-install` entry point, then a `_bmad/config.yaml`
      manifest record + skill-name collision check (Story 15.3).

    Raises `FileNotFoundError` if the module is skip-decided / unregistered
    or its backend assets are missing, and `subprocess.CalledProcessError`
    if a wrapped script/installer exits non-zero -- both propagated, not
    swallowed. `FileNotFoundError` propagates to `ProvisionDuty`'s boundary;
    `subprocess.CalledProcessError` / `RuntimeError` are caught one level
    earlier inside `_run_module` (Story 6.3).
    """
    if name in _SKIPPED_MODULES:
        raise FileNotFoundError(_SKIPPED_MODULES[name])
    if name not in _SUPPORTED_MODULES:
        raise FileNotFoundError(f"module {name!r} is not registered in _SUPPORTED_MODULES")

    root = Path(cwd)
    backend = _SUPPORTED_MODULES[name]
    if isinstance(backend, SetupSkillBackend):
        return _provision_setup_skill(name, backend, cwd=root)
    return _provision_conda_install(name, backend, cwd=root)


def _format_called_process_error(exc: subprocess.CalledProcessError) -> str:
    """Format a `subprocess.CalledProcessError` as `` `{cmd}` exited {code}:
    {stderr} `` -- the one formatting `ProvisionDuty.run()`'s own except
    block already applied inline (Story 3.1-3.4/6.1); extracted (Story 6.3)
    so `_run_module`'s new local handler below can build the identical base
    message before appending its own already-landed/nothing-written note,
    never a second, divergent copy of the same formatting."""
    stderr = (exc.stderr or "").strip()
    cmd_name = " ".join(str(part) for part in exc.cmd) if exc.cmd else "subprocess"
    return f"`{cmd_name}` exited {exc.returncode}: {stderr}"


def _module_install_state_or_none(name: str, *, cwd: str | Path) -> str | None:
    """`module_install_states(cwd=cwd).get(name)`, degrading a failed read
    (a malformed or unreadable `_bmad/config.yaml` OR, since Story 46.2/
    AD-9, `_bmad/custom/config.toml`) to `None` rather than letting a
    second exception mask whatever failure `_run_module` is already
    reporting, or crash past `ProvisionDuty.run()`'s boundary on the
    success path where nothing else is there to catch it (review finding:
    an earlier draft called `module_install_states` directly in both
    spots, so a malformed `_bmad/config.yaml` replaced a genuinely
    diagnostic subprocess stderr with an unrelated `yaml.YAMLError`).
    `UnicodeDecodeError` (non-UTF-8 bytes in either config file -- raised
    by `tomllib.load`/`.read_text`, not a subclass of `OSError`) is caught
    explicitly alongside the two parse-error types; the old YAML-only
    reader wrapped this exact failure into a `RuntimeError` its caller
    could catch, and this degrade-to-`None` path must cover it too rather
    than letting it propagate uncaught (review finding)."""
    try:
        return module_install_states(cwd=cwd).get(name)
    except (yaml.YAMLError, tomllib.TOMLDecodeError, UnicodeDecodeError, OSError):
        return None


def _manifest_location_label(name: str) -> str:
    """Where `<name>`'s roster entry lives, for `_run_module`'s own
    failure/post-success messages: `_bmad/config.yaml` for the
    `SetupSkillBackend` path (`bmb`, written by `merge-config.py` itself,
    never by `_record_module_manifest`), or `_bmad/custom/config.toml` for
    every `CondaInstallBackend` module (Story 46.2, AD-9). Falls back to
    the legacy path for an unregistered name (unreachable in practice --
    both call sites below only run after `name` is confirmed registered)."""
    backend = _SUPPORTED_MODULES.get(name)
    if isinstance(backend, CondaInstallBackend):
        return str(_BMAD_CUSTOM_CONFIG_TOML_RELATIVE_PATH)
    return str(_BMAD_RELATIVE_PATH / "config.yaml")


def _run_module(ns: argparse.Namespace) -> DutyResult:
    """`provision --module <name>` (Story 6.1; Story 6.3 adds the local
    failure-naming handler and the post-success verification gate below).
    An unrecognized name never reaches `provision_module`/a subprocess
    call -- it is reported directly, honoring `--json` via
    `ProvisionDuty._render_error` exactly like every other failure path
    this duty has (I/O Matrix: `--module <bad> --json` still yields a
    parseable `{"error": ...}` shape).

    `provision_module()`'s own `subprocess.CalledProcessError`/
    `RuntimeError` are caught locally here (not left to `ProvisionDuty.
    run()`'s outer boundary) so the failure can name whether THIS RUN
    already wrote a `<name>` section to `_bmad/config.yaml` before the
    failure -- comparing a state snapshot taken before `provision_module()`
    is called against one taken after it fails (review finding: an earlier
    draft compared only the post-failure state against nothing, so a
    failure against an ALREADY-installed module -- e.g. a transient `uv`
    error that touches no file -- was misreported as "provisioning is
    INCOMPLETE" even though this run changed nothing). Both snapshots reuse
    `module_install_states` (Story 6.2) as the one oracle, never a second,
    divergent check, via `_module_install_state_or_none` so a malformed/
    unreadable `_bmad/config.yaml` degrades to "unknown" instead of
    masking the real failure or crashing past this boundary. `FileNotFoundError`
    (unregistered name / missing backend dir) is deliberately NOT caught
    here: both occur before any subprocess call, so nothing could have
    landed, and Story 6.1's existing message (via `ProvisionDuty.run()`'s
    outer boundary) already covers it.

    After a successful `provision_module()` call, `module_install_states`
    is consulted once more before reporting `ok=True` -- if `<name>` isn't
    actually present in `_bmad/config.yaml`, the scripts' own "exited 0"
    self-report is not trusted at face value (FR-21's "succeeds while
    leaving the module unimportable" clause)."""
    name = ns.module
    if name in _SKIPPED_MODULES:
        return DutyResult(
            ok=False, summary=ProvisionDuty._render_error(ns, _SKIPPED_MODULES[name])
        )
    if name not in _SUPPORTED_MODULES:
        supported = ", ".join(sorted(_SUPPORTED_MODULES))
        message = f"{name!r} is not a supported module. Supported modules: {supported}"
        return DutyResult(ok=False, summary=ProvisionDuty._render_error(ns, message))
    root = repo_root()
    state_before = _module_install_state_or_none(name, cwd=root)
    try:
        steps = provision_module(name, cwd=root)
    except (subprocess.CalledProcessError, RuntimeError) as exc:
        message = (
            _format_called_process_error(exc)
            if isinstance(exc, subprocess.CalledProcessError)
            else str(exc)
        )
        state_after = _module_install_state_or_none(name, cwd=root)
        manifest_label = _manifest_location_label(name)
        if state_after == "installed" and state_before != "installed":
            message += (
                f"; already wrote a {name!r} section to {manifest_label} during this "
                "run before the failure above -- provisioning is INCOMPLETE"
            )
        elif state_after is None:
            message += (
                f"; could not confirm whether {manifest_label} was touched before this "
                "failure (its own state could not be read)"
            )
        elif state_after != "installed":
            message += f"; nothing was written to {manifest_label} before this failure"
        # else: state_after == "installed" and state_before == "installed" --
        # `<name>` was already provisioned by an earlier run and this
        # failure did not change that; no landed-state note is appended,
        # since nothing about THIS run's outcome is newly incomplete.
        return DutyResult(ok=False, summary=ProvisionDuty._render_error(ns, message))
    if _module_install_state_or_none(name, cwd=root) != "installed":
        return DutyResult(
            ok=False,
            summary=ProvisionDuty._render_error(
                ns,
                f"{name!r} exited 0, but {name!r} is not present "
                f"in {_manifest_location_label(name)} afterward -- not counted as provisioned",
            ),
        )
    if getattr(ns, "json", False):
        return DutyResult(ok=True, summary=json.dumps(steps, indent=2))
    dirs_note = (
        f"; created {', '.join(steps['output_dirs_created'])}"
        if steps.get("output_dirs_created")
        else ""
    )
    backend = _SUPPORTED_MODULES[name]
    if isinstance(backend, CondaInstallBackend):
        skill_count = len(steps.get("skills_installed") or ())
        summary = (
            f"provision --module: {name!r} provisioned via {backend.installer} "
            f"({skill_count} skill(s) → {_CLAUDE_SKILLS_RELATIVE_PATH}; manifest recorded)"
            f"{dirs_note}"
        )
    else:
        summary = (
            f"provision --module: {name!r} provisioned (merge-config.py, merge-help-csv.py)"
            f"{dirs_note}"
        )
    return DutyResult(ok=True, summary=summary)


# ── Module discovery (FR-20, Story 6.2) ─────────────────────────────────────


def _custom_config_toml_module_names(*, cwd: str | Path) -> set[str]:
    """Names recorded under `_bmad/custom/config.toml`'s `[modules.<name>]`
    tables -- AD-9's roster location, written by `_record_module_manifest`
    for every `CondaInstallBackend` module. A missing file degrades to an
    empty set, mirroring `module_install_states`'s own missing-`_bmad/
    config.yaml` precedent below. A malformed file is NOT caught here --
    `tomllib.TOMLDecodeError` propagates, matching that same
    propagate-don't-swallow precedent for a malformed manifest. Unrelated
    sections under `[modules.*]` (`bmm`, `skf` -- neither is a registered
    `_SUPPORTED_MODULES` name) are harmless: the caller only checks
    membership for names it already knows about.
    """
    path = Path(cwd) / _BMAD_CUSTOM_CONFIG_TOML_RELATIVE_PATH
    if not path.is_file():
        return set()
    with path.open("rb") as f:
        document = tomllib.load(f)
    modules = document.get("modules", {})
    if not isinstance(modules, dict):
        return set()
    return set(modules)


def module_install_states(*, cwd: str | Path) -> dict[str, str]:
    """Derive each registered module's `installed`/`available` state from a
    two-location read (Story 46.2, AD-9): `_bmad/custom/config.toml`'s
    `[modules.<name>]` tables first, then `_bmad/config.yaml`'s own
    top-level keys -- the exact anti-zombie key `merge-config.py`'s own
    `config[module_code] = module_section` writes (verified against the
    real script; story spec Design Notes) -- as a fallback for a module not
    found in the new location (`cis`'s own Story 46.8 entry still lives
    only there, unmigrated by design; see `_record_module_manifest`).

    A missing `_bmad/config.yaml`, or one that parses to something other
    than a `dict` (e.g. a bare YAML list), both degrade to `{}` rather than
    raising -- both read as "not installed via the legacy path", so a
    module found in neither location reports `available`. A malformed
    (unparseable) `_bmad/config.yaml` or `_bmad/custom/config.toml` is NOT
    caught here -- `yaml.YAMLError` / `tomllib.TOMLDecodeError` propagate to
    `ProvisionDuty.run()`'s existing exception boundary, matching
    `load_pixi_environments`'s own propagate-don't-swallow precedent for a
    malformed `pixi.toml`.
    """
    toml_names = _custom_config_toml_module_names(cwd=cwd)
    config_path = Path(cwd) / _BMAD_RELATIVE_PATH / "config.yaml"
    legacy_config: dict[str, object] = {}
    if config_path.is_file():
        with config_path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
        if isinstance(loaded, dict):
            legacy_config = loaded
    return {
        name: ("installed" if name in toml_names or name in legacy_config else "available")
        for name in _SUPPORTED_MODULES
    }


def format_module_states(states: dict[str, str], *, as_json: bool) -> str:
    """Render `states` for `steward provision --list-modules`.

    Mirrors `format_environments`'s own JSON/text split: `as_json=True` ->
    `{name: state}`, sorted by name (`{}` for no registered modules, the
    correct machine-parseable empty state); `as_json=False` -> aligned
    `name  state` text lines sorted by name, or a plain sentence when no
    modules are registered.
    """
    if as_json:
        return json.dumps({name: states[name] for name in sorted(states)}, indent=2)
    if not states:
        return "provision --list-modules: no modules registered"
    width = max(len(name) for name in states)
    lines = [f"{name:<{width}}  {states[name]}" for name in sorted(states)]
    return "\n".join(lines)


def _run_list_modules(ns: argparse.Namespace) -> DutyResult:
    """`provision --list-modules [--json]` (Story 6.2). Read-only: derives
    state from the filesystem at call time, never writes to `_bmad/
    config.yaml` or any other file."""
    root = repo_root()
    states = module_install_states(cwd=root)
    return DutyResult(
        ok=True, summary=format_module_states(states, as_json=getattr(ns, "json", False))
    )


# ── ProvisionDuty (Duty-protocol adapter) ───────────────────────────────────

_PROVISION_HELP = (
    "available flags: --list-modules [--json] | --module <name> [--json] | "
    "--prove-class-path [--json] | --env <name> | --runner bmad-loop --env <name> | "
    "--list [--json] | --verify"
)


def _run_prove_class_path(ns: argparse.Namespace) -> DutyResult:
    """`provision --prove-class-path` — Story 31.3 / install-class CAP-3."""
    from .fresh_clone import prove

    report = prove()
    if getattr(ns, "json", False):
        return DutyResult(ok=report.ok, summary=report.as_json())
    return DutyResult(ok=report.ok, summary=report.summary())


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
    """The real `provision` duty — dispatches the `--list-modules`/
    `--module`/`--env`/`--runner`/`--list`/`--verify` flags (Epic 3 grew
    this class one flag per story through `--verify`; Epic 6 Story 6.1
    added `--module`, Story 6.2 adds `--list-modules`).

    Unlike `keys`/`deploy`, `provision` has no verb subcommands — every
    action is a flag on the bare `provision` duty parser, matching each
    story's own `steward provision --env <name>` shape. Precedence when
    more than one flag is passed: `--list-modules` > `--module` > `--verify`
    > `--list` > `--runner` > `--env` (a documented judgment call, not a
    silent one — mirrors `DeployDuty`'s own `--build`-wins-over-`--dry-run`
    precedent; no AC defines combining them; `--list-modules` lands at the
    top, matching each new story's flag landing at the top of this
    if-chain). Bare
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
            if getattr(ns, "list_modules", False):
                return _run_list_modules(ns)
            if getattr(ns, "module", None) is not None:
                return _run_module(ns)
            if getattr(ns, "prove_class_path", False):
                return _run_prove_class_path(ns)
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
            return DutyResult(
                ok=False, summary=self._render_error(ns, _format_called_process_error(exc))
            )
        except (
            RuntimeError,
            FileNotFoundError,
            tomllib.TOMLDecodeError,
            yaml.YAMLError,
            UnicodeDecodeError,
        ) as exc:
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
