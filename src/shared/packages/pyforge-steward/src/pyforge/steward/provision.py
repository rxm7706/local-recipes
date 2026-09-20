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

Story 46.3 slice (CAP-4 half): TEA's own upstream `*-install` layout nests
its nine workflow skills one level too deep (`workflows/testarch/bmad-
testarch-*`), invisible to Claude Code's own one-level `.claude/skills/
<name>/SKILL.md` discovery -- `CondaInstallBackend.flatten_nested_dirs`
(opt-in, only set for `tea`) names which `skill_source_dirs` entries need
this post-install fixup; `_flatten_nested_skill_dirs` moves each leaf
skill up to `.claude/skills/<name>` and removes the now-empty container,
operating only on files the (untouched, vendored) installer already
wrote. Separately, `CondaInstallBackend.module_yaml_relative_path`
(opt-in, only set for `tea`, whose `module.yaml` sits at the share root,
unlike bmb's `assets/module.yaml`) drives a new module.yaml-answers
mechanism for `_provision_conda_install`: `_module_yaml_answers` reuses
`_module_variable_defaults` verbatim and overrides only `test_artifacts`
to the unresolved template `"{output_folder}/planning-artifacts"` (every
other TEA variable keeps its own declared default), merged by
`_record_module_manifest` into `[modules.tea]` alongside `provisioned_by`/
`installer`/`skills`. Neither mechanism touches `cis`/`utility-skills`/
`manticore` -- both fields default to `()`/`None`.

Story 46.4 slice (CAP-1 half): closes bmb's own long-standing gap --
`SetupSkillBackend` only ever drove `merge-config.py`/`merge-help-csv.py`
(the `_bmad/config.yaml` merge), never copied bmad-builder's five skill
directories (`bmad-bmb-setup`, `bmad-agent-builder`, `bmad-workflow-builder`,
`bmad-module-builder`, `bmad-eval-runner`) into `.claude/skills/` at all.
`SetupSkillBackend.skills_source_dir` (opt-in, only `bmb` sets it) names the
`share/bmad-builder/skills` directory whose immediate child directories
`_setup_skill_names` discovers (directory-only, mirroring
`_installer_skill_names`'s own filter -- the two sibling files, `module.yaml`
and `module-help.csv`, are excluded for free); `_provision_setup_skill` gates
the copy on the SAME `_check_skill_name_collisions` every `CondaInstallBackend`
module already uses (reused verbatim, never a second, divergent check), then
`_copy_setup_skill_dirs` lands each one under `.claude/skills/<name>` --
overwrite-in-place on a re-provision, matching every other backend's own
idempotent-overwrite convention. A plain `shutil.copytree`-class operation,
never a subprocess call, so it cannot introduce a `cleanup-legacy.py`/
`--legacy-dir` invocation by construction -- the existing Story 6.1 argv
guard test needs no change. `_bmad/config.yaml` still gains the `bmb` section
via the unchanged `merge-config.py` mechanism; `bmb` is still explicitly NOT
part of the Story 46.2 AD-9 migration to `_bmad/custom/config.toml`.

Story 46.5 slice (the plugin-path install class's first real wiring):
`bmad-labs-skills` had `wire_policy` = "documented" everywhere (register row
10, `install-class-playbook.md`, `suite.py`'s `probe_wired`) -- the upstream
README's own by-name-or-marketplace commands were only ever cited, never run
by any steward mechanism. `_SUPPORTED_PLUGINS` (`PluginBackend`, today just
`labs`) is a small, deliberately separate registry from `_SUPPORTED_MODULES`:
every `CondaInstallBackend`/`SetupSkillBackend` module installs its ENTIRE
declared skill set atomically in one call, while the plugin-path class
installs exactly ONE named skill per invocation, gated by a fixed four-name
operator consent list (`_LABS_CONSENT_SKILLS` -- the 2026-09-06 decision,
register row 10 / § 2 rows 43-46 -- refused for any of the package's other
18 skills even though the share tree makes them technically copyable).
`provision_plugin_skill` reuses `_check_skill_name_collisions` and
`_copy_setup_skill_dirs` verbatim (never `npx skills add` -- AD-1's "never
both"), resolving the copy source from the conda package's own pinned share
tree (`_conda_prefix`) rather than a second, redundant runtime commit-check.
Unlike every `CondaInstallBackend` module's `_record_module_manifest` call
(which replaces `skills` wholesale with the one full set the installer just
wrote), the plugin path must ACCUMULATE: `_module_toml_skills` reads
`[modules.labs]`'s currently-recorded `skills` array back out of `_bmad/
custom/config.toml` so the caller can union it with the newly-installed name
before calling `_record_module_manifest` -- a previously-installed sibling
skill (e.g. `mcp-builder`) must never be wiped by installing a second one
(e.g. `release-please`). `suite.py`'s `probe_wired` for
`INSTALL_CLASS_PLUGIN_PATH` is untouched by this story (still `"documented"`,
a playbook-text check with zero filesystem inspection) -- Story 46.9 owns
correcting that probe; `adoption-register.md` row 10's Wired cell
deliberately stays `documented` here, not `wired`, so it does not disagree
with that still-unfixed live probe.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
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
    """Drive BMB's own `bmad-bmb-setup` merge scripts (Story 6.1).

    `skills_source_dir` (Story 46.4, opt-in -- unset for any future
    `SetupSkillBackend` module) names a directory, relative to repo root,
    whose immediate child directories are copied into `.claude/skills/<name>`
    -- gated by the same `_check_skill_name_collisions` every
    `CondaInstallBackend` module already uses. `None` skips the copy step
    entirely (the pre-Story-46.4 behavior).
    """

    kind: Literal["setup_skill"] = "setup_skill"
    skill_dir: Path = Path()  # relative to repo root
    skills_source_dir: Path | None = None  # relative to repo root


@dataclass(frozen=True)
class CondaInstallBackend:
    """Drive a conda package's `*-install` entry point (Story 15.3).

    `skill_source_dirs` names share/<package>/<dir> children that become
    `.claude/skills/` entries (tea: agents+workflows; utility/manticore:
    skills). `skill_names`, when non-empty, is an explicit allowlist matching
    the installer's own fixed list (cis) — used for collision checks and
    post-install verification instead of directory discovery.

    `flatten_nested_dirs` (Story 46.3, opt-in) names which `skill_source_dirs`
    entries land one level too deep from the installer (each immediate child
    is itself a container of leaf skills, not a leaf skill itself) — only
    `tea` sets this (`("workflows",)`); `cis`/`utility-skills`/`manticore`
    are unaffected. `module_yaml_relative_path` (Story 46.3, opt-in), when
    set, drives the module.yaml-answers mechanism in
    `_provision_conda_install` — relative to `share_root`, NOT `bmb`'s own
    `assets/module.yaml` convention (`_MODULE_YAML_RELATIVE_PATH`), since
    TEA's `module.yaml` sits at the share root. Only `tea` sets this today.
    """

    installer: str
    share_package: str
    skill_source_dirs: tuple[str, ...] = ()
    skill_names: tuple[str, ...] = ()
    flatten_nested_dirs: tuple[str, ...] = ()
    module_yaml_relative_path: Path | None = None
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
        skill_dir=Path(".pixi/envs/pyforge-guild/share/bmad-builder/skills/bmad-bmb-setup"),
        skills_source_dir=Path(".pixi/envs/pyforge-guild/share/bmad-builder/skills"),
    ),
    "tea": CondaInstallBackend(
        installer="bmad-tea-install",
        share_package="bmad-method-test-architecture-enterprise",
        skill_source_dirs=("agents", "workflows"),
        flatten_nested_dirs=("workflows",),
        module_yaml_relative_path=Path("module.yaml"),
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
_TEMPLATE_AUTHORING_ONLY = (
    "bmad-module-template is an authoring tool only (adoption-register "
    "row 11; Story 52.1). Never steward provision --module into "
    ".claude/skills/. Use bmad-builder beside this scaffold."
)

_SKIPPED_MODULES: dict[str, str] = {
    "wds": (
        "WDS (bmad-method-wds-expansion) is skip-decided: deprecated upstream "
        "(spec-bmad-suite-channel-product/install-matrix.md; Dream "
        "bmad-suite-channel-product — absorbing into bmad-ux). Not in "
        "_SUPPORTED_MODULES."
    ),
    "module-template": _TEMPLATE_AUTHORING_ONLY,
    "bmad-module-template": _TEMPLATE_AUTHORING_ONLY,
    "template": _TEMPLATE_AUTHORING_ONLY,
}


@dataclass(frozen=True)
class PluginBackend:
    """A plugin-path install-class backend (Story 46.5) — a small, deliberately
    separate registry from `_SUPPORTED_MODULES`/`ModuleBackend`. Every
    `ModuleBackend` module installs its ENTIRE declared skill set atomically
    in one call; the plugin-path class installs exactly ONE named skill per
    invocation, gated by a fixed operator consent list. `share_package`
    names the conda share package whose `skills/<name>` subdirectories are
    copyable; `allowed_skills` is the consent list — a `--skill` name
    outside it is refused even though the package's share tree may make it
    technically copyable.
    """

    share_package: str
    allowed_skills: tuple[str, ...]


# Story 46.5: the operator's 2026-09-06 consent decision (adoption-register.md
# row 10 / § 2 rows 43-46) — exactly these four of the 22 skills
# bmad-labs-skills ships. A fixed constant, never derived from the share tree
# (deriving it would silently consent to whatever upstream ships next).
_LABS_CONSENT_SKILLS: tuple[str, ...] = (
    "mcp-builder",
    "slides-generator",
    "multi-repo-git-ops",
    "release-please",
)

_SUPPORTED_PLUGINS: dict[str, PluginBackend] = {
    "labs": PluginBackend(share_package="bmad-labs-skills", allowed_skills=_LABS_CONSENT_SKILLS),
}

# Relative to the share root: share/bmad-labs-skills/skills/<name>.
_LABS_SKILLS_SOURCE_SUBDIR = Path("skills")

# There is no real subprocess entry-point binary for the plugin-path class —
# the mechanism is a plain `shutil` copy (never `npx skills add`, AD-1's
# "never both"). This fixed literal is recorded as the `[modules.labs]`
# manifest's `installer` field so the manifest schema stays uniform (every
# module has SOME string there) while being honest that no external binary
# runs underneath — it matches, verbatim, the Provisioning-path cell text
# adoption-register.md row 10 already carries.
_LABS_INSTALLER_LABEL = "steward provision --plugin labs --skill <name>"

_MODULE_YAML_RELATIVE_PATH = Path("assets/module.yaml")
_MODULE_HELP_CSV_RELATIVE_PATH = Path("assets/module-help.csv")
_BMAD_RELATIVE_PATH = Path("_bmad")
_BMAD_CUSTOM_CONFIG_TOML_RELATIVE_PATH = Path("_bmad/custom/config.toml")
_CLAUDE_SKILLS_RELATIVE_PATH = Path(".claude/skills")
# Story 63.6 (spec-pyforge-steward CAP-152): only pyforge-guild exists at runtime; the suite
# share trees (bmad-builder, bmad-labs-skills, TEA) are Guild-feature deps, so the Guild env
# is where the provisioner reads them. `local-recipes` is the recipe factory, never a runtime.
_GUILD_ENV_RELATIVE_PATH = Path(".pixi/envs/pyforge-guild")
_LOCAL_RECIPES_ENV_RELATIVE_PATH = _GUILD_ENV_RELATIVE_PATH  # legacy name kept for callers; same path


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


# Story 46.3: TEA's own module.yaml default (`"{output_folder}/test-artifacts"`)
# is overridden so the epic's "test_artifacts ... pointed at each station's
# planning-artifacts/" lands -- stored as this UNRESOLVED template string,
# never a pre-resolved absolute path (resolution happens per-active-project
# at skill-render time against that project's own `.bmad-config.toml`
# `output_folder`, not at provisioning time).
_TEST_ARTIFACTS_ANSWER_OVERRIDE = "{output_folder}/planning-artifacts"
_TEST_ARTIFACTS_ANSWER_KEY = "test_artifacts"


def _module_yaml_answers(module_yaml: dict[str, object]) -> dict[str, object]:
    """TEA's module.yaml-answers (Story 46.3): reuses `_module_variable_defaults`
    verbatim, then overrides only `test_artifacts` -- every other declared
    variable (`tea_use_playwright_utils`, `ci_platform`, `risk_threshold`,
    etc.) keeps its own module.yaml `default` untouched. This story does not
    decide any of those; it only closes the `test_artifacts` gap the epic
    names."""
    answers = _module_variable_defaults(module_yaml)
    if _TEST_ARTIFACTS_ANSWER_KEY in answers:
        answers[_TEST_ARTIFACTS_ANSWER_KEY] = _TEST_ARTIFACTS_ANSWER_OVERRIDE
    return answers


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

    Prefer this checkout's `.pixi/envs/pyforge-guild` when it already holds
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
        "the pyforge-guild pixi environment (or run via `pixi run -e "
        "pyforge-guild`) so conda package installers can find their share data."
    )


def _installer_skill_names(backend: CondaInstallBackend, *, share_root: Path) -> tuple[str, ...]:
    """Names the installer will place under `.claude/skills/`.

    For a `flatten_nested_dirs` source (Story 46.3, TEA's own `workflows`
    entry), predicts the POST-flatten leaf names -- each immediate child of
    that source is itself a container (e.g. `testarch`) whose OWN children
    are the real leaf skills -- rather than the container's own name, which
    is what the installer actually writes before `_flatten_nested_skill_dirs`
    runs. This function is used for BOTH pre-install collision checking and
    the post-install missing-skills check, so it must predict the flattened
    end state either way."""
    if backend.skill_names:
        return backend.skill_names
    names: list[str] = []
    for source in backend.skill_source_dirs:
        directory = share_root / source
        if not directory.is_dir():
            continue
        if source in backend.flatten_nested_dirs:
            for container in sorted(p for p in directory.iterdir() if p.is_dir()):
                names.extend(sorted(c.name for c in container.iterdir() if c.is_dir()))
        else:
            names.extend(sorted(p.name for p in directory.iterdir() if p.is_dir()))
    return tuple(names)


def _setup_skill_names(skills_source_dir: Path) -> tuple[str, ...]:
    """Names of `skills_source_dir`'s own immediate child directories (Story
    46.4) -- the skills a `SetupSkillBackend` module (`bmb`) copies into
    `.claude/skills/`. Directory-only `iterdir()` discovery, mirroring
    `_installer_skill_names`'s own filter, so files sitting alongside the
    skill dirs (bmb's own `module.yaml`/`module-help.csv` at this level --
    distinct from `bmad-bmb-setup`'s own `assets/module.yaml`) are excluded
    without a second, divergent discovery convention. A missing directory
    degrades to an empty tuple; the caller decides whether that is an
    error."""
    if not skills_source_dir.is_dir():
        return ()
    return tuple(sorted(p.name for p in skills_source_dir.iterdir() if p.is_dir()))


def _check_skill_name_collisions(
    name: str,
    skill_names: tuple[str, ...],
    *,
    cwd: Path,
    already_installed: bool,
    kind: str = "module",
) -> None:
    """Refuse to overwrite `.claude/skills/<skill>` that already exists when
    this module is not yet manifest-recorded (a foreign skill collision).
    Re-provision of an already-installed module is allowed (idempotent).

    `kind` (Story 46.5, opt-in) names the noun the error message uses --
    every `_SUPPORTED_MODULES` caller keeps the default `"module"`; the
    plugin-path caller (`provision_plugin_skill`) passes `"plugin"` so the
    message never calls `labs` a "module" (it is never a `--module` target
    -- review finding: the reused-verbatim message previously said `module
    'labs'`, contradicting that guarantee and pointing an operator at
    `--list-modules`/`--module labs`, neither of which shows it).
    """
    if already_installed or not skill_names:
        return
    skills_root = cwd / _CLAUDE_SKILLS_RELATIVE_PATH
    collisions = sorted(
        skill for skill in skill_names if (skills_root / skill).exists()
    )
    if collisions:
        raise RuntimeError(
            f"{kind} {name!r}: skill-name collision(s) under "
            f"{_CLAUDE_SKILLS_RELATIVE_PATH}: {', '.join(collisions)} — refuse "
            f"to overwrite skills that already exist before this {kind} is "
            "manifest-recorded. Remove or rename the colliding skills, then "
            "re-run provision."
        )


def _flatten_nested_skill_dirs(
    name: str, backend: CondaInstallBackend, *, share_root: Path, dest: Path
) -> None:
    """Post-install fixup for a `flatten_nested_dirs` source (Story 46.3):
    `bmad-tea-install`'s own upstream layout copies each `workflows/<container>`
    (e.g. `testarch`, holding all nine workflow skills) to `dest/<container>`
    verbatim -- one level too deep for Claude Code's own one-level
    `.claude/skills/<name>/SKILL.md` discovery. Moves each leaf skill up to
    `dest/<leaf>` and removes the now-empty container, operating only on
    files the (untouched, vendored) installer already wrote -- never a patch
    to `bmad-tea-install` itself.

    Idempotent AND refreshing: a re-provision re-runs the installer, which
    does not know Story 46.3 already moved the previous nested copy out
    from under it, so it writes a fresh one right back to
    `dest/<container>/<leaf>` -- reflecting whatever the currently-pinned
    TEA package version now ships. A leaf already flattened by a prior run
    (`dest/<leaf>` already present) is REPLACED by that fresh nested copy
    (never the reverse) -- a re-provision after a real TEA version bump
    must pick up the new content, exactly like every other conda-install
    module's own plain rmtree+copytree refresh (review finding: an earlier
    draft discarded the fresh copy and kept the stale flattened one,
    silently freezing every flattened skill at whatever was installed the
    very first time). If neither the nested location nor an
    already-flattened leaf can be found at all, raises a `RuntimeError`
    naming what was expected vs. found -- never silently leaves the nested
    layout in place (I/O Matrix: "Fresh TEA provision").
    """
    for source in backend.flatten_nested_dirs:
        source_dir = share_root / source
        if not source_dir.is_dir():
            continue
        for container in sorted(p.name for p in source_dir.iterdir() if p.is_dir()):
            container_share = source_dir / container
            container_dest = dest / container
            leaves = sorted(p.name for p in container_share.iterdir() if p.is_dir())
            for leaf in leaves:
                target = dest / leaf
                nested = container_dest / leaf
                if nested.is_dir():
                    # This run's installer wrote (or rewrote) the nested
                    # copy -- it is always the authoritative, freshest
                    # content. Replace any stale already-flattened target.
                    if target.is_dir():
                        shutil.rmtree(target)
                    shutil.move(str(nested), str(target))
                    continue
                if not target.is_dir():
                    raise RuntimeError(
                        f"module {name!r}: flattening {container!r} expected "
                        f"{nested} to exist, found neither it nor an "
                        f"already-flattened {target}"
                    )
                # No fresh nested copy this run (e.g. a share-only dry
                # re-check with an installer that skipped this leaf); the
                # already-flattened target from a prior run is kept as-is.
            if container_dest.is_dir():
                remaining = sorted(p.name for p in container_dest.iterdir())
                if remaining:
                    raise RuntimeError(
                        f"module {name!r}: {container_dest} still has "
                        f"unexpected entries after flattening: {remaining!r}"
                    )
                container_dest.rmdir()


def _toml_string(value: str) -> str:
    """A TOML basic-string literal for `value`. Every value this writer ever
    renders (`"steward"`, an installer entry-point name, a skill directory
    name) is a plain ASCII identifier with no quotes/backslashes, so JSON's
    escaping rules (a strict subset of TOML's for this class of string) are
    sufficient without adding a TOML-writing dependency."""
    return json.dumps(value)


def _toml_value(value: object) -> str:
    """A TOML scalar literal for `value` -- the only two shapes a module.yaml
    answer (Story 46.3) or this file's own existing generated fields ever
    produce: a plain ASCII string (`_toml_string`) or a bool. Bools are
    rendered lowercase (`true`/`false`) -- Python's own `str()` would wrongly
    emit `True`/`False`, which is not valid TOML."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return _toml_string(value)
    raise TypeError(f"unsupported module.yaml answer type for TOML rendering: {type(value)!r}")


def _render_module_toml_section(
    name: str,
    *,
    installer: str,
    skills: tuple[str, ...],
    answers: dict[str, object] | None = None,
) -> str:
    """Render a `[modules.<name>]` section -- AD-9's target shape, carrying
    the three fields the legacy `_bmad/config.yaml` entry carried
    (`provisioned_by`, `installer`, `skills`), plus (Story 46.3) any
    module.yaml answers for a backend that declares
    `module_yaml_relative_path` -- rendered as additional scalar keys,
    sorted by name for deterministic output. A flat one-line `skills`
    array matches this file's own existing generated scalar-key style
    (`sidecar_path = "..."` etc.) -- no need to match `[modules.skf]`'s
    hand-authored, prose-commented multi-line style."""
    reserved = {"provisioned_by", "installer", "skills"}
    collisions = reserved & set(answers or {})
    if collisions:
        raise RuntimeError(
            f"module {name!r}: module.yaml declares reserved manifest key(s) "
            f"{sorted(collisions)!r} -- would duplicate the fixed "
            "provisioned_by/installer/skills fields in [modules."
            f"{name}]"
        )
    skills_array = ", ".join(_toml_string(s) for s in skills)
    lines = [
        f"[modules.{name}]\n",
        f"provisioned_by = {_toml_string('steward')}\n",
        f"installer = {_toml_string(installer)}\n",
        f"skills = [{skills_array}]\n",
    ]
    for key in sorted(answers or {}):
        try:
            lines.append(f"{key} = {_toml_value(answers[key])}\n")
        except TypeError as exc:
            raise TypeError(
                f"module {name!r}: module.yaml variable {key!r}: {exc}"
            ) from exc
    return "".join(lines)


def _record_module_manifest(
    name: str,
    *,
    cwd: Path,
    installer: str,
    skills: tuple[str, ...],
    answers: dict[str, object] | None = None,
) -> None:
    """Write/replace `[modules.<name>]` in `_bmad/custom/config.toml` (AD-9)
    -- the roster every `CondaInstallBackend` module's provisioning path
    (tea/cis/utility-skills/manticore) now records, so a fresh-clone
    provision is discoverable via `--list-modules`. `bmb`
    (`SetupSkillBackend`) never calls this function -- `merge-config.py`
    writes `_bmad/config.yaml` itself.

    `answers` (Story 46.3, opt-in -- only `tea` populates it today) merges a
    backend's module.yaml-derived answers dict as additional scalar keys
    into the same section, alongside `provisioned_by`/`installer`/`skills`.

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
    section_text = _render_module_toml_section(
        name, installer=installer, skills=skills, answers=answers
    )
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


def _copy_setup_skill_dirs(
    skills_source_dir: Path, skill_names: tuple[str, ...], *, dest: Path
) -> None:
    """Copy each of `skill_names` from `skills_source_dir` into `dest/<name>`
    (Story 46.4) -- a full `rmtree`-then-`copytree` replace, never a merge,
    so a re-provision after a real bmad-builder version bump picks up
    renamed/removed files too, matching `_flatten_nested_skill_dirs`'s own
    "fresh content always wins" precedent. A plain file operation, never a
    subprocess call, so it cannot introduce a `cleanup-legacy.py`/
    `--legacy-dir` invocation by construction. A `target` that exists but is
    NOT a directory (a foreign plain file/symlink at that exact path) is a
    clean, named `RuntimeError` rather than an unclear `shutil.copytree`
    `FileExistsError` (review finding)."""
    for skill_name in skill_names:
        target = dest / skill_name
        if target.exists() and not target.is_dir():
            raise RuntimeError(
                f"cannot copy skill {skill_name!r}: {target} exists and is "
                "not a directory"
            )
        if target.is_dir():
            shutil.rmtree(target)
        shutil.copytree(skills_source_dir / skill_name, target)


def _provision_setup_skill(name: str, backend: SetupSkillBackend, *, cwd: Path) -> dict[str, object]:
    """Story 6.1 path: drive `merge-config.py` + `merge-help-csv.py`. Story
    46.4 (bmb only) inserts an opt-in skills-copy step below, gated by the
    same `_check_skill_name_collisions` every `CondaInstallBackend` module
    already uses -- before the two subprocess calls, matching
    `_provision_conda_install`'s own collision-check-before-install-side-
    effects ordering."""
    skill_dir = cwd / backend.skill_dir
    if not skill_dir.is_dir():
        raise FileNotFoundError(
            f"module {name!r}'s setup-skill directory is missing at {skill_dir} "
            "-- the bmad-builder pixi dependency is not installed. Fix with "
            "`pixi install -e pyforge-guild`."
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

    # Story 46.4 (review finding): the collision check runs here, BEFORE any
    # side effect -- so a genuine foreign collision refuses with nothing
    # written, matching this function's own pre-existing guarantee. The
    # actual copy (`_copy_setup_skill_dirs`) is deferred until AFTER both
    # subprocess calls below succeed (see the second half of the merge, past
    # `merge_help_csv`): copying here, before the subprocess calls, meant a
    # `merge-config.py` failure left the freshly-copied skill dirs behind
    # with `_bmad/config.yaml` never gaining the `bmb` key, so a retry's own
    # `already_installed` check still read `False` and treated the module's
    # own leftover directories from the failed attempt as a foreign
    # collision -- permanently self-locking every retry until a human
    # manually removed them. Deferring the copy closes that class of bug:
    # a failed subprocess call now leaves nothing new behind to collide with.
    skills_copied: tuple[str, ...] = ()
    skill_names: tuple[str, ...] = ()
    skills_source: Path | None = None
    if backend.skills_source_dir is not None:
        skills_source = cwd / backend.skills_source_dir
        skill_names = _setup_skill_names(skills_source)
        if not skill_names:
            raise RuntimeError(
                f"module {name!r}: no skills discovered under {skills_source} "
                f"(skills_source_dir={backend.skills_source_dir!r})"
            )
        already_installed = _module_install_state_or_none(name, cwd=cwd) == "installed"
        _check_skill_name_collisions(
            name, skill_names, cwd=cwd, already_installed=already_installed
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

    # Copy the skills only now that both scripts above have actually
    # succeeded (see the ordering note above `skills_copied` for why).
    if skills_source is not None:
        dest = cwd / _CLAUDE_SKILLS_RELATIVE_PATH
        dest.mkdir(parents=True, exist_ok=True)
        _copy_setup_skill_dirs(skills_source, skill_names, dest=dest)
        skills_copied = skill_names

    return {
        "merge_config": merge_config_result,
        "merge_help_csv": merge_help_csv_result,
        "output_dirs_created": list(output_dirs_created),
        "skills_copied": list(skills_copied),
    }


def _provision_conda_install(
    name: str, backend: CondaInstallBackend, *, cwd: Path
) -> dict[str, object]:
    """Story 15.3 path: drive the package's `*-install` entry point, then
    record a `_bmad/custom/config.toml` `[modules.<name>]` manifest section
    (Story 46.2, AD-9) so `--list-modules` and Story 6.3's post-success gate
    see the module as installed.

    Story 46.3 adds two opt-in post-subprocess steps for a backend that
    declares them (only `tea` today): `_flatten_nested_skill_dirs` runs
    BEFORE the missing-skills check, so that check validates the flattened
    end state rather than the installer's own one-level-too-deep layout;
    the module.yaml-answers computation runs after the missing-skills check
    passes and is merged into the manifest section by `_record_module_manifest`.
    """
    prefix = _conda_prefix(cwd=cwd, share_package=backend.share_package)
    share_root = prefix / "share" / backend.share_package
    if not share_root.is_dir():
        raise FileNotFoundError(
            f"module {name!r}'s share package is missing at {share_root} — "
            f"the {backend.share_package} pixi/conda dependency is not "
            "installed. Fix with `pixi install -e pyforge-guild`."
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

    if backend.flatten_nested_dirs:
        _flatten_nested_skill_dirs(name, backend, share_root=share_root, dest=dest)

    missing = [s for s in skill_names if not (dest / s).is_dir()]
    if missing:
        raise RuntimeError(
            f"module {name!r}: {backend.installer} exited 0 but skills still "
            f"missing under {_CLAUDE_SKILLS_RELATIVE_PATH}: {', '.join(missing)}"
        )

    answers: dict[str, object] | None = None
    if backend.module_yaml_relative_path is not None:
        module_yaml_path = share_root / backend.module_yaml_relative_path
        if not module_yaml_path.is_file():
            raise FileNotFoundError(
                f"module {name!r}'s module.yaml is missing at {module_yaml_path} — "
                f"the {backend.share_package} pixi/conda dependency does not ship "
                "a module.yaml at the declared path."
            )
        with module_yaml_path.open("r", encoding="utf-8") as f:
            module_yaml = yaml.safe_load(f)
        if not isinstance(module_yaml, dict):
            raise RuntimeError(
                f"{module_yaml_path} did not parse to a mapping -- malformed module.yaml"
            )
        answers = _module_yaml_answers(module_yaml)

    _record_module_manifest(
        name, cwd=cwd, installer=backend.installer, skills=skill_names, answers=answers
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
        skills_copied = steps.get("skills_copied") or ()
        skills_note = (
            f" ({len(skills_copied)} skill(s) → {_CLAUDE_SKILLS_RELATIVE_PATH})"
            if skills_copied
            else ""
        )
        summary = (
            f"provision --module: {name!r} provisioned (merge-config.py, merge-help-csv.py)"
            f"{skills_note}{dirs_note}"
        )
    return DutyResult(ok=True, summary=summary)


# ── Plugin-path provisioning (Story 46.5, the plugin-path class's first real
# wiring) ─────────────────────────────────────────────────────────────────


def provision_plugin_skill(plugin: str, skill: str, *, cwd: str | Path) -> dict[str, object]:
    """Provision exactly ONE named skill from a registered plugin-path
    backend (Story 46.5) — the plugin-path counterpart to `provision_module`.

    Validates `plugin` is a registered key of `_SUPPORTED_PLUGINS`
    (`FileNotFoundError` naming the supported plugins if not), validates
    `skill` is on the backend's `allowed_skills` consent list (`RuntimeError`
    naming the allowed names if not — even a real, share-tree-present skill
    outside the four-name consent list is refused), resolves the share root
    via the existing `_conda_prefix`, and asserts the named skill's share
    directory exists (`FileNotFoundError` if not — mirrors
    `_provision_setup_skill`'s own missing-share-dir message shape).

    Collision-checks PER SKILL, not per module: `already_installed` reflects
    only whether THIS skill name is already on `[modules.<plugin>]`'s
    roster, so `_check_skill_name_collisions` is called with just `(skill,)`
    — a previously-installed sibling skill's own directory is never treated
    as something this call needs to re-check, but a genuine foreign
    collision on THIS skill's own directory still refuses.

    Records the roster BEFORE copying (review finding, mirroring
    `_provision_setup_skill`'s own documented ordering fix): accumulates the
    currently-recorded `skills` array (`_module_toml_skills`) with the
    newly-installed name and writes it via `_record_module_manifest` FIRST,
    then copies via `_copy_setup_skill_dirs` (reused verbatim — an
    idempotent rmtree+copytree). Copying first (an earlier draft's order)
    reintroduced the exact self-locking-retry bug `_provision_setup_skill`
    already found and fixed: a manifest-write failure AFTER a successful
    copy left the copied directory behind with the roster never gaining the
    skill, so a retry's `already_installed` read `False` and treated the
    prior attempt's own leftover directory as a foreign collision —
    permanently refusing until a human manually deleted it (reproduced
    empirically in review). Writing the roster first means any failure
    *after* it (a `_copy_setup_skill_dirs` error) leaves `already_installed`
    reading `True` on retry, so `_check_skill_name_collisions` is skipped
    entirely and the retry just re-runs the (idempotent) copy — the correct
    self-healing outcome. Never a wholesale replacement that would wipe a
    previously-installed sibling skill.

    Raises `FileNotFoundError` for an unregistered plugin or a missing share
    directory, and `RuntimeError` for a consent-list refusal or a skill-name
    collision — both propagated, not swallowed; `_run_plugin` catches both
    locally, mirroring `_run_module`'s own precedent.
    """
    if plugin not in _SUPPORTED_PLUGINS:
        supported = ", ".join(sorted(_SUPPORTED_PLUGINS))
        raise FileNotFoundError(
            f"plugin {plugin!r} is not registered. Supported plugins: {supported}"
        )
    backend = _SUPPORTED_PLUGINS[plugin]
    if skill not in backend.allowed_skills:
        allowed = ", ".join(backend.allowed_skills)
        raise RuntimeError(
            f"skill {skill!r} is not on the {plugin!r} consent list. "
            f"Allowed skills: {allowed}"
        )

    root = Path(cwd)
    prefix = _conda_prefix(cwd=root, share_package=backend.share_package)
    share_root = prefix / "share" / backend.share_package
    skill_dir = share_root / _LABS_SKILLS_SOURCE_SUBDIR / skill
    if not skill_dir.is_dir():
        raise FileNotFoundError(
            f"plugin {plugin!r}'s skill {skill!r} is missing at {skill_dir} — "
            f"the {backend.share_package} pixi/conda dependency is not "
            "installed. Fix with `pixi install -e pyforge-guild`."
        )

    already_installed = skill in _module_toml_skills(plugin, cwd=root)
    _check_skill_name_collisions(
        plugin, (skill,), cwd=root, already_installed=already_installed, kind="plugin"
    )

    # Record the roster BEFORE copying — see the docstring's "review finding"
    # paragraph for why the reverse order self-locks a retry after a
    # manifest-write failure.
    accumulated = tuple(sorted({*_module_toml_skills(plugin, cwd=root), skill}))
    _record_module_manifest(
        plugin, cwd=root, installer=_LABS_INSTALLER_LABEL, skills=accumulated
    )

    dest = root / _CLAUDE_SKILLS_RELATIVE_PATH
    dest.mkdir(parents=True, exist_ok=True)
    _copy_setup_skill_dirs(share_root / _LABS_SKILLS_SOURCE_SUBDIR, (skill,), dest=dest)

    return {
        "installer": _LABS_INSTALLER_LABEL,
        "skill_installed": skill,
        "skills_on_roster": list(accumulated),
    }


def _run_plugin(ns: argparse.Namespace) -> DutyResult:
    """`provision --plugin <name> --skill <name>` (Story 46.5).

    Argparse-level validation stays permissive (Boundaries) — an
    unregistered `--plugin` name, a `--skill` name outside the consent
    list, or `--plugin` given without `--skill` are all reported through
    `DutyResult(ok=False, ...)` here, never an argparse crash. `ns.plugin`'s
    registration is checked FIRST, then `ns.skill`'s presence (review
    finding: checking `--skill` first meant `--plugin bogus` with no
    `--skill` reported "--skill is required" instead of naming `bogus` as
    unsupported — an operator adding `--skill x` would only then discover
    the real problem). `provision_plugin_skill` is called with its own
    `(RuntimeError, FileNotFoundError)` caught locally — mirroring
    `_run_module`'s own local-handler precedent — so a genuine consent-list
    refusal or skill-name collision is never masked as an unrelated crash by
    `ProvisionDuty.run()`'s outer boundary.
    """
    plugin = ns.plugin
    if plugin not in _SUPPORTED_PLUGINS:
        supported = ", ".join(sorted(_SUPPORTED_PLUGINS))
        message = f"{plugin!r} is not a supported plugin. Supported plugins: {supported}"
        return DutyResult(ok=False, summary=ProvisionDuty._render_error(ns, message))
    skill = getattr(ns, "skill", None)
    if skill is None:
        return DutyResult(
            ok=False,
            summary=ProvisionDuty._render_error(
                ns, "--skill is required together with --plugin"
            ),
        )
    root = repo_root()
    try:
        steps = provision_plugin_skill(plugin, skill, cwd=root)
    except (RuntimeError, FileNotFoundError) as exc:
        return DutyResult(ok=False, summary=ProvisionDuty._render_error(ns, str(exc)))
    if getattr(ns, "json", False):
        return DutyResult(ok=True, summary=json.dumps(steps, indent=2))
    roster = ", ".join(steps["skills_on_roster"])
    summary = (
        f"provision --plugin: {plugin!r} skill {skill!r} provisioned "
        f"({_CLAUDE_SKILLS_RELATIVE_PATH}/{skill}; roster: {roster})"
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


def _module_toml_skills(name: str, *, cwd: str | Path) -> tuple[str, ...]:
    """Read `_bmad/custom/config.toml`'s `[modules.<name>].skills` array back
    out (Story 46.5) — the small reader the plugin-path roster-accumulation
    mechanism needs; no existing function reads a specific module's `skills`
    field back out (`_custom_config_toml_module_names` above only reads
    section NAMES, not a section's field values). Degrades to `()` on a
    missing file, a missing `[modules.<name>]` section, or a non-list
    `skills` value — never raises, mirroring
    `_custom_config_toml_module_names`'s own missing-file/malformed-shape
    degrade precedent.
    """
    path = Path(cwd) / _BMAD_CUSTOM_CONFIG_TOML_RELATIVE_PATH
    if not path.is_file():
        return ()
    with path.open("rb") as f:
        document = tomllib.load(f)
    modules = document.get("modules", {})
    if not isinstance(modules, dict):
        return ()
    section = modules.get(name)
    if not isinstance(section, dict):
        return ()
    skills = section.get("skills")
    if not isinstance(skills, list):
        return ()
    return tuple(skills)


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
    "--plugin labs --skill <name> [--json] | "
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
            if getattr(ns, "plugin", None) is not None:
                # Story 46.5: a new provisioning-class flag joins the group of
                # provisioning flags at the top of this precedence chain —
                # matching how each prior story's own new flag landed at the
                # top of its own group (a documented judgment call, not a
                # silent one; no AC defines combining --plugin with --module
                # or --list-modules).
                return _run_plugin(ns)
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
