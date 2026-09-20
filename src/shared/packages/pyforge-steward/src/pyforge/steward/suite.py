"""Steward's ``suite`` duty — bmad-suite channel pipeline truth (Epic 15 / CAP-1).

Story 15.1: one command reports, for each of the 13 suite packages, upstream
latest (npm and/or GitHub per package class), recipe version, SelfExplainML
channel version, installed version, and wired-or-not — with drift named per
stage. Every probe is fail-open: one failure never aborts the whole report.

Consumes the same probe shapes doctor already uses (npm registry, GitHub
releases/tags, ``recipe.yaml`` parse, ``api.anaconda.org``, conda-meta /
installed-version scan, ``.claude/skills`` + ``_bmad`` census) without
importing ``pyforge.doctor`` (steward stays free of a doctor run-dependency).

Verb: ``steward suite pipeline-truth``. Never implements Epic 15 CAP-2
autotick advance (Story 15.2). Story 31.2 extends the wired-or-not column
with per-class predicates for the six non-module pieces.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .interfaces import DutyResult
from .provision import module_install_states

_BMAD_LOOP_WORKTREE_RELATIVE_PATH = Path("scripts/bmad-loop-worktree")
_ANACONDA_CHANNEL = "SelfExplainML"
_NPM_LATEST_URL = "https://registry.npmjs.org/{package}/latest"
_ANACONDA_PACKAGE_URL = "https://api.anaconda.org/package/{channel}/{package}"
_GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/{owner_repo}/releases/latest"
_GITHUB_TAGS_URL = "https://api.github.com/repos/{owner_repo}/tags"
_FETCH_TIMEOUT_SECONDS = 5.0
_RELEASE_TRIPLE_RE = re.compile(r"(?:\d+!)?(\d+)\.(\d+)\.(\d+)")
_USER_AGENT = "pyforge-steward/suite-pipeline-truth"

# The Dream / install-matrix roster — the operator's 13, never derived from
# pixi pins (skill-forge has no pin; doctor's watched set is a different cut).
BASELINE_ID_2026_08_22 = "2026-08-22-research-matrix"


class SuiteError(RuntimeError):
    """A suite-duty request failed in a duty-level (ok=False) way."""


def repo_root() -> Path:
    """Return the local-recipes checkout root (same marker as provision/upgrade)."""
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / _BMAD_LOOP_WORKTREE_RELATIVE_PATH).is_file():
            return candidate
    raise SuiteError(
        "cannot locate repo root (scripts/bmad-loop-worktree not found walking up)"
    )


# Story 31.2 / install-class CAP-2 — not a boolean only --module targets satisfy.
INSTALL_CLASS_MODULE = "module"
INSTALL_CLASS_SKIP = "skip"
INSTALL_CLASS_INSTALLER_TREE = "installer-tree"
INSTALL_CLASS_RUNNER_HOME = "runner-home"
INSTALL_CLASS_OWN_INSTALLER = "own-installer"
INSTALL_CLASS_PLUGIN_PATH = "plugin-path"
INSTALL_CLASS_VSCODE_EXTENSION = "vscode-extension"
INSTALL_CLASS_SCAFFOLD_NA = "scaffold-n/a"
# Story 45.1 — a bare CLI with nothing to wire into _bmad (eval-quality).
INSTALL_CLASS_CLI = "cli"
# Story 46.9 — manticore's own class (AD-3): a module installed OUTSIDE this
# repo, into a dedicated studio root, never the generic "module" fallback.
INSTALL_CLASS_STUDIO_MODULE = "studio-module"

# Story 46.9: the APPLIED core version `_bmad/_config/manifest.yaml` records
# for `installation.version` — the installer-tree class's `installed` stage
# reads this FIRST, falling back to the generic conda-meta scan only when the
# manifest is absent (I/O Matrix).
_BMAD_CORE_MANIFEST_RELATIVE_PATH = Path("_bmad/_config/manifest.yaml")

# Story 46.9: manticore's studio root (AD-3) — declared once per machine,
# outside this repo, never provisioned into `.claude/skills/` here.
_PYFORGE_STUDIO_ROOT_ENV = "PYFORGE_STUDIO_ROOT"
_PYFORGE_STUDIO_ROOT_DEFAULT = "~/pyforge-studio"

INSTALL_CLASS_PLAYBOOK_REL = (
    "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/"
    "spec-bmad-suite-install-class-wiring/install-class-playbook.md"
)
INSTALL_MATRIX_REL = (
    "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/"
    "spec-bmad-suite-channel-product/install-matrix.md"
)

# Values that are class-correct "not unwired" — not a module census miss.
_WIRED_SETTLED_VALUES = frozenset(
    {
        "wired",
        "skip",
        "n/a",
        "provisionable",
        "documented",
        "runnable",
        "present",
    }
)


@dataclass(frozen=True)
class SuitePackageDef:
    """One of the 13 bmad-suite packages and how to probe it."""

    name: str
    npm_name: str | None = None  # None => skip npm (invisible / collision)
    github_repo: str | None = None  # owner/repo; None => skip GitHub
    wire_policy: str = "census"  # census | skip | n/a
    wire_bmad_dirs: tuple[str, ...] = ()
    wire_skill_prefixes: tuple[str, ...] = ()
    wire_skill_names: tuple[str, ...] = ()
    # Story 46.9: ALL of these must be present (vs. wire_skill_names's ANY).
    wire_skill_names_all: tuple[str, ...] = ()
    wire_bmad_config_keys: tuple[str, ...] = ()
    install_class: str = INSTALL_CLASS_MODULE
    wire_pixi_task: str | None = None  # vscode-extension class: pixi task name
    cli_bin: str | None = None  # cli class: executable expected on PATH (default: name)
    # Story 46.9: the provision.py `_SUPPORTED_MODULES` key (AD-9 roster read).
    module_code: str | None = None


# install-matrix.md + Dream grounding (2026-08-22) — package class → probes.
SUITE_PACKAGES: tuple[SuitePackageDef, ...] = (
    SuitePackageDef(
        name="bmad-method",
        npm_name="bmad-method",
        github_repo="bmad-code-org/BMAD-METHOD",
        wire_bmad_dirs=("core", "bmm"),
        install_class=INSTALL_CLASS_INSTALLER_TREE,
    ),
    SuitePackageDef(
        name="bmad-loop",
        npm_name=None,  # npm-invisible
        github_repo="bmad-code-org/bmad-loop",
        install_class=INSTALL_CLASS_RUNNER_HOME,
    ),
    SuitePackageDef(
        name="bmad-method-test-architecture-enterprise",
        npm_name="bmad-method-test-architecture-enterprise",
        github_repo="bmad-code-org/bmad-method-test-architecture-enterprise",
        wire_skill_prefixes=("bmad-testarch-", "bmad-tea", "bmad-teach-me-testing"),
        wire_skill_names=("bmad-tea",),
        module_code="tea",
    ),
    SuitePackageDef(
        name="bmad-builder",
        npm_name="bmad-builder",
        github_repo="bmad-code-org/bmad-builder",
        wire_bmad_config_keys=("bmb",),
        wire_skill_names_all=(
            "bmad-bmb-setup",
            "bmad-agent-builder",
            "bmad-workflow-builder",
            "bmad-module-builder",
            "bmad-eval-runner",
        ),
    ),
    SuitePackageDef(
        name="bmad-creative-intelligence-suite",
        npm_name="bmad-creative-intelligence-suite",
        github_repo="bmad-code-org/bmad-module-creative-intelligence-suite",
        wire_skill_prefixes=("bmad-cis-",),
        module_code="cis",
    ),
    SuitePackageDef(
        name="bmad-module-skill-forge",
        npm_name="bmad-module-skill-forge",
        github_repo="armelhbobdad/bmad-module-skill-forge",
        wire_bmad_dirs=("skf",),
        wire_skill_prefixes=("skf-",),
        install_class=INSTALL_CLASS_OWN_INSTALLER,
    ),
    # 2026-09-05 (Story 45.1): bmad-method-wds-expansion retired from the roster —
    # upstream deprecated (folded into bmm as the bmad-ux skill); provision still
    # refuses `--module wds`. bmad-eval-quality took its seat.
    SuitePackageDef(
        name="bmad-eval-quality",
        npm_name="eval-quality",  # npm 0.1.0 lags the commit-pinned 0.2.0 line
        github_repo="bmad-code-org/bmad-eval-quality",
        install_class=INSTALL_CLASS_CLI,
        cli_bin="eval-quality",
    ),
    SuitePackageDef(
        name="bmad-utility-skills",
        npm_name=None,
        github_repo="bmad-code-org/bmad-utility-skills",
        wire_skill_prefixes=("bmad-os-",),
        module_code="utility-skills",
    ),
    SuitePackageDef(
        name="bmad-labs-skills",
        npm_name=None,
        github_repo="bmad-labs/skills",
        install_class=INSTALL_CLASS_PLUGIN_PATH,
        wire_skill_names_all=(
            "mcp-builder",
            "slides-generator",
            "multi-repo-git-ops",
            "release-please",
        ),
    ),
    SuitePackageDef(
        name="bmad-module-template",
        npm_name=None,
        github_repo="bmad-code-org/bmad-module-template",
        wire_policy="n/a",
        install_class=INSTALL_CLASS_SCAFFOLD_NA,
    ),
    SuitePackageDef(
        name="bmad-manticore",
        npm_name=None,
        github_repo="bmad-code-org/bmad-manticore",
        wire_skill_prefixes=("mc-",),
        install_class=INSTALL_CLASS_STUDIO_MODULE,
    ),
    SuitePackageDef(
        name="bmad-dashboard",
        npm_name=None,  # npm bmad-dashboard is an unrelated collision
        github_repo="bmad-code-org/bmad-method-ui",
        install_class=INSTALL_CLASS_VSCODE_EXTENSION,
        wire_pixi_task="bmad-dashboard-install",
    ),
    SuitePackageDef(
        name="mybmad-dashboard",
        npm_name=None,
        github_repo="bmad-code-org/bmad-method-ui",
        install_class=INSTALL_CLASS_VSCODE_EXTENSION,
        wire_pixi_task="mybmad",
    ),
)

assert len(SUITE_PACKAGES) == 13


@dataclass(frozen=True)
class StageProbe:
    """One stage's probe outcome — fail-open: ``ok=False`` never raises."""

    value: str | None
    ok: bool
    detail: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {"value": self.value, "ok": self.ok, "detail": self.detail}


@dataclass(frozen=True)
class PackageTruth:
    """Per-package five-stage truth + named drifts."""

    name: str
    upstream_npm: StageProbe
    upstream_github: StageProbe
    recipe: StageProbe
    channel: StageProbe
    installed: StageProbe
    wired: StageProbe
    drifts: tuple[str, ...] = ()
    install_class: str = INSTALL_CLASS_MODULE

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "install_class": self.install_class,
            "upstream_npm": self.upstream_npm.to_dict(),
            "upstream_github": self.upstream_github.to_dict(),
            "recipe": self.recipe.to_dict(),
            "channel": self.channel.to_dict(),
            "installed": self.installed.to_dict(),
            "wired": self.wired.to_dict(),
            "drifts": list(self.drifts),
        }


@dataclass(frozen=True)
class PipelineTruthReport:
    """The whole-pipeline report across all 13 suite packages."""

    packages: tuple[PackageTruth, ...]
    baseline_id: str | None = None
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "baseline_id": self.baseline_id,
            "package_count": len(self.packages),
            "packages": [p.to_dict() for p in self.packages],
            "notes": list(self.notes),
        }


def _parse_release_triple(text: str) -> tuple[int, int, int] | None:
    match = _RELEASE_TRIPLE_RE.match(text.strip())
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _strip_leading_v(text: str) -> str:
    if text[:1] in ("v", "V"):
        return text[1:]
    return text


def _url_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})


def _fail_open_get_json(url: str, *, timeout: float = _FETCH_TIMEOUT_SECONDS) -> Any | None:
    try:
        with urllib.request.urlopen(_url_request(url), timeout=timeout) as response:
            return json.loads(response.read())
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        http.client.HTTPException,
        OSError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None


def fetch_npm_latest(package: str, *, timeout: float = _FETCH_TIMEOUT_SECONDS) -> str | None:
    """Fail-open npm ``/latest`` version string (or None)."""
    url = _NPM_LATEST_URL.format(package=urllib.parse.quote(package, safe=""))
    body = _fail_open_get_json(url, timeout=timeout)
    if not isinstance(body, dict):
        return None
    version = body.get("version")
    return str(version) if version is not None else None


def fetch_github_latest(
    owner_repo: str,
    package: str | None = None,
    *,
    timeout: float = _FETCH_TIMEOUT_SECONDS,
) -> str | None:
    """Fail-open GitHub latest release tag, else newest parseable tag.

    ``package`` is accepted so ProbeHooks can be package-aware (baseline
    replay for shared ``owner/repo`` rows like bmad-dashboard /
    mybmad-dashboard); the live network path ignores it.
    """
    del package  # live fetch is repo-scoped only
    release_url = _GITHUB_LATEST_RELEASE_URL.format(owner_repo=owner_repo)
    try:
        with urllib.request.urlopen(
            _url_request(release_url), timeout=timeout
        ) as response:
            body = json.loads(response.read())
        if not isinstance(body, dict):
            return None
        tag = body.get("tag_name")
        if isinstance(tag, str) and tag.strip():
            return _strip_leading_v(tag)
        # Empty / missing tag_name → fall through to /tags.
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            return None
    except (
        urllib.error.URLError,
        http.client.HTTPException,
        OSError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ):
        return None

    tags_url = _GITHUB_TAGS_URL.format(owner_repo=owner_repo)
    body = _fail_open_get_json(tags_url, timeout=timeout)
    if not isinstance(body, list):
        return None
    parsed: list[tuple[tuple[int, int, int], str]] = []
    for entry in body:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if name is None:
            continue
        raw = _strip_leading_v(str(name))
        triple = _parse_release_triple(raw)
        if triple is not None:
            parsed.append((triple, raw))
    if not parsed:
        return None
    return max(parsed, key=lambda item: item[0])[1]


def fetch_channel_version(
    package: str, *, timeout: float = _FETCH_TIMEOUT_SECONDS
) -> str | None:
    """Fail-open SelfExplainML ``latest_version`` from anaconda.org."""
    url = _ANACONDA_PACKAGE_URL.format(
        channel=_ANACONDA_CHANNEL,
        package=urllib.parse.quote(package, safe=""),
    )
    body = _fail_open_get_json(url, timeout=timeout)
    if not isinstance(body, dict):
        return None
    latest = body.get("latest_version")
    return str(latest) if latest is not None else None


def read_recipe_version(repo: Path, package: str) -> str | None:
    """Fail-open ``recipes/<package>/recipe.yaml`` ``context.version``.

    Only ``str`` and ``int`` (not ``bool``) are accepted — YAML floats must
    not be coerced via ``str()`` (float-lossy for version-like numbers).
    """
    try:
        data = yaml.safe_load(
            (repo / "recipes" / package / "recipe.yaml").read_text(encoding="utf-8")
        )
        version = data["context"]["version"]
        if isinstance(version, str):
            return version
        if isinstance(version, int) and not isinstance(version, bool):
            return str(version)
        return None
    except (OSError, ValueError, yaml.YAMLError, KeyError, TypeError, AttributeError):
        return None


def read_installed_version(repo: Path, package: str) -> str | None:
    """Fail-open newest conda-meta filename version across ``.pixi/envs/*/``."""
    envs_dir = repo / ".pixi" / "envs"
    best: tuple[tuple[int, int, int], str] | None = None
    try:
        env_dirs = list(envs_dir.iterdir())
    except OSError:
        return None
    for env_dir in env_dirs:
        try:
            meta_files = list((env_dir / "conda-meta").iterdir())
        except OSError:
            continue
        for meta_file in meta_files:
            if meta_file.suffix != ".json":
                continue
            parts = meta_file.stem.rsplit("-", 2)
            if len(parts) != 3:
                continue
            name, version_text, _build = parts
            if name != package:
                continue
            triple = _parse_release_triple(version_text)
            if triple is None:
                continue
            candidate = (triple, version_text)
            if best is None or candidate > best:
                best = candidate
    return best[1] if best is not None else None


def read_applied_core_version(repo: Path) -> str | None:
    """Fail-open ``_bmad/_config/manifest.yaml``'s ``installation.version`` --
    the APPLIED bmad-method core version (what ``_bmad/`` actually runs), as
    opposed to ``read_installed_version``'s pixi-env conda-meta scan (what is
    pinned). Mirrors ``read_recipe_version``'s own try/except/isinstance
    shape: only ``str``/non-bool ``int`` are accepted -- a YAML float must
    not be coerced via ``str()`` (float-lossy for version-like numbers).
    """
    try:
        data = yaml.safe_load(
            (repo / _BMAD_CORE_MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8")
        )
        version = data["installation"]["version"]
        if isinstance(version, str):
            return version
        if isinstance(version, int) and not isinstance(version, bool):
            return str(version)
        return None
    except (OSError, ValueError, yaml.YAMLError, KeyError, TypeError, AttributeError):
        return None


def _skills_census(repo: Path) -> set[str]:
    skills = repo / ".claude" / "skills"
    try:
        return {p.name for p in skills.iterdir() if p.is_dir() or p.is_symlink()}
    except OSError:
        return set()


def _bmad_config_keys(repo: Path) -> set[str]:
    path = repo / "_bmad" / "config.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return set()
    if not isinstance(data, dict):
        return set()
    return {str(k) for k in data}


def _pixi_task_declared(repo: Path, task: str) -> bool:
    """True when pixi.toml declares ``[*.tasks.<task>]`` (install-task runnable)."""
    path = repo / "pixi.toml"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return f"[feature.bmad-ui.tasks.{task}]" in text


def _plugin_path_documented(repo: Path) -> bool:
    """Labs is wired-or-not by documented plugin path, never skill census."""
    for rel in (INSTALL_CLASS_PLAYBOOK_REL, INSTALL_MATRIX_REL):
        path = repo / rel
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "bmad-labs/skills" in text:
            return True
    return False


def _module_census_hit(repo: Path, pkg: SuitePackageDef) -> str | None:
    """CAP-3 ``--module`` census only. Returns a detail string on hit.

    Story 46.9 review finding (HIGH, reproduced live against this repo's own
    `_bmad/config.yaml`): ``wire_skill_names_all``, when declared, is the
    SOLE, EXCLUSIVE signal for that package -- it returns immediately,
    whether it hits or misses, rather than merely being "checked first."
    An earlier draft let a miss fall through to `bmad-builder`'s own
    auxiliary `wire_bmad_config_keys=("bmb",)` check, which independently
    reports a hit from the `bmb:` key `merge-config.py` writes regardless
    of whether all five skill dirs actually landed -- silently reintroducing
    the exact "wired on partial provisioning" false-positive this field was
    added to eliminate, live-reproducible against this repo's own real
    `_bmad/config.yaml` (which genuinely carries that key). No other
    package declares `wire_skill_names_all` alongside a second wire_* field
    today, so this exclusivity has no effect on any other row.
    """
    skills = _skills_census(repo)
    if pkg.wire_skill_names_all:
        if all(name in skills for name in pkg.wire_skill_names_all):
            return f".claude/skills has all of {', '.join(pkg.wire_skill_names_all)}"
        return None
    if pkg.wire_bmad_dirs:
        if all((repo / "_bmad" / d).is_dir() for d in pkg.wire_bmad_dirs):
            return f"_bmad dirs: {', '.join(pkg.wire_bmad_dirs)}"
    if pkg.wire_bmad_config_keys:
        keys = _bmad_config_keys(repo)
        if any(k in keys for k in pkg.wire_bmad_config_keys):
            return f"_bmad/config.yaml keys: {', '.join(pkg.wire_bmad_config_keys)}"
    for name in pkg.wire_skill_names:
        if name in skills:
            return f".claude/skills has {name}"
    for prefix in pkg.wire_skill_prefixes:
        if any(s.startswith(prefix) or s == prefix.rstrip("-") for s in skills):
            return f".claude/skills matches prefix {prefix!r}"
    return None


def probe_wired(repo: Path, pkg: SuitePackageDef) -> StageProbe:
    """Per-class wired-or-not (Story 31.2). Fail-open, never raises."""
    try:
        if (
            pkg.install_class == INSTALL_CLASS_SKIP
            or pkg.wire_policy == "skip"
        ):
            return StageProbe(
                value="skip",
                ok=True,
                detail="deprecated upstream; wiring deliberately skipped",
            )
        if (
            pkg.install_class == INSTALL_CLASS_SCAFFOLD_NA
            or pkg.name == "bmad-module-template"
            or pkg.wire_policy == "n/a"
        ):
            return StageProbe(
                value="n/a",
                ok=True,
                detail="scaffold N/A — template is not a wireable module",
            )
        if pkg.install_class == INSTALL_CLASS_INSTALLER_TREE:
            dirs = pkg.wire_bmad_dirs or ("core", "bmm")
            if all((repo / "_bmad" / d).is_dir() for d in dirs):
                return StageProbe(
                    value="present",
                    ok=True,
                    detail=f"installer tree: _bmad/{', _bmad/'.join(dirs)}",
                )
            return StageProbe(
                value="missing",
                ok=True,
                detail="installer tree: _bmad/core + _bmad/bmm not both present",
            )
        if pkg.install_class == INSTALL_CLASS_RUNNER_HOME:
            locator = repo / "scripts" / "bmad-loop-worktree"
            if locator.is_file():
                return StageProbe(
                    value="provisionable",
                    ok=True,
                    detail="runner home: scripts/bmad-loop-worktree present",
                )
            return StageProbe(
                value="missing",
                ok=True,
                detail="runner home: scripts/bmad-loop-worktree absent",
            )
        if pkg.install_class == INSTALL_CLASS_OWN_INSTALLER:
            hit = _module_census_hit(repo, pkg)
            if hit:
                return StageProbe(
                    value="present",
                    ok=True,
                    detail=f"own installer: {hit}",
                )
            return StageProbe(
                value="missing",
                ok=True,
                detail="own installer: skf tree/skills not present",
            )
        if pkg.install_class == INSTALL_CLASS_PLUGIN_PATH:
            # Story 46.9: a real .claude/skills census (the consented names
            # actually landed) outranks the playbook-text-only check below —
            # Story 46.5's real provisioning must not stay forever invisible.
            hit = _module_census_hit(repo, pkg)
            if hit:
                return StageProbe(value="wired", ok=True, detail=hit)
            if _plugin_path_documented(repo):
                return StageProbe(
                    value="documented",
                    ok=True,
                    detail="plugin path documented (operator consent to enable)",
                )
            return StageProbe(
                value="missing",
                ok=True,
                detail="plugin path not documented in playbook/matrix",
            )
        if pkg.install_class == INSTALL_CLASS_STUDIO_MODULE:
            # Story 46.9 (AD-3): manticore is installed OUTSIDE this repo,
            # into a dedicated studio root — never the in-repo mc-* census
            # the old generic fallback branch used to consult.
            #
            # Review finding (medium): `os.environ.get(key, default)` only
            # falls back to `default` when the key is ABSENT, not when it is
            # present-but-empty (`PYFORGE_STUDIO_ROOT=""`) — that classic
            # gotcha would resolve to `Path("").expanduser()` (the process's
            # cwd, which almost always exists), silently reintroducing the
            # exact in-repo signal AD-3 retired if this duty ever runs from
            # this repo's own root with an accidentally-blank env value.
            # `or` treats an empty string the same as "unset."
            studio_root = Path(
                os.environ.get(_PYFORGE_STUDIO_ROOT_ENV) or _PYFORGE_STUDIO_ROOT_DEFAULT
            ).expanduser()
            if not studio_root.is_dir():
                return StageProbe(
                    value="unwired",
                    ok=True,
                    detail=f"studio module: {studio_root} does not exist",
                )
            has_bmad = (studio_root / "_bmad").is_dir()
            try:
                has_mc_skill = any(
                    p.is_dir() and p.name.startswith("mc-")
                    for p in (studio_root / ".claude" / "skills").iterdir()
                )
            except OSError:
                has_mc_skill = False
            if has_bmad and has_mc_skill:
                return StageProbe(
                    value="wired",
                    ok=True,
                    detail=f"studio module: {studio_root}/_bmad + mc-* skill present",
                )
            return StageProbe(
                value="unwired",
                ok=True,
                detail=(
                    f"studio module: {studio_root} present but _bmad/ and/or a "
                    "mc-* skill is missing"
                ),
            )
        if pkg.install_class == INSTALL_CLASS_CLI:
            exe_name = pkg.cli_bin or pkg.name
            exe = shutil.which(exe_name)
            if exe:
                return StageProbe(value="runnable", ok=True, detail=f"cli: {exe}")
            # Story 63.6 (spec-pyforge-steward CAP-152): a CLI-only bmad-suite tool is
            # pinned in the station env that wields it (bmad-eval-quality in
            # pyforge-steward since 63.5) AND in the Guild default -- the only env that
            # exists at runtime. pixi isolates each env's PATH, so a probe run under
            # another station never sees it via `shutil.which`; fall back to the Guild
            # env's bin dir before declaring it missing. Never `local-recipes`.
            guild_exe = repo / ".pixi" / "envs" / "pyforge-guild" / "bin" / exe_name
            if guild_exe.is_file():
                return StageProbe(
                    value="runnable", ok=True, detail=f"cli: {guild_exe}"
                )
            return StageProbe(
                value="missing",
                ok=True,
                detail=f"cli: {exe_name} not on PATH (no pixi pin yet?)",
            )
        if pkg.install_class == INSTALL_CLASS_VSCODE_EXTENSION:
            task = pkg.wire_pixi_task
            if task and _pixi_task_declared(repo, task):
                return StageProbe(
                    value="runnable",
                    ok=True,
                    detail=f"VS Code extension / web: pixi task {task} declared",
                )
            return StageProbe(
                value="missing",
                ok=True,
                detail="VS Code extension / web: pixi install task not declared",
            )
        # Story 46.9 (AD-9): a registered module_code reads the roster
        # `--list-modules` and provision.py's own post-success gate already
        # treat as the single source of truth, instead of re-deriving an
        # imprecise skills/_bmad census a second way. `bmb` (no module_code)
        # still falls through to the (now five-name-aware) census below.
        if pkg.module_code is not None:
            installed = module_install_states(cwd=repo).get(pkg.module_code) == "installed"
            if installed:
                return StageProbe(
                    value="wired",
                    ok=True,
                    detail=f"AD-9 roster: modules.{pkg.module_code} installed",
                )
            return StageProbe(
                value="unwired",
                ok=True,
                detail=f"AD-9 roster: modules.{pkg.module_code} not installed",
            )
        # CAP-3 five: module census boolean.
        hit = _module_census_hit(repo, pkg)
        if hit:
            return StageProbe(value="wired", ok=True, detail=hit)
        return StageProbe(value="unwired", ok=True, detail="skills/_bmad census miss")
    except Exception as exc:  # noqa: BLE001 — probe fail-open
        return StageProbe(value=None, ok=False, detail=f"wired probe failed: {exc}")


def _stage_from_value(
    value: str | None, *, skipped: bool = False, skip_detail: str = ""
) -> StageProbe:
    if skipped:
        return StageProbe(value=None, ok=True, detail=skip_detail or "probe skipped for class")
    if value is None:
        return StageProbe(value=None, ok=False, detail="probe returned nothing")
    return StageProbe(value=value, ok=True)


def _installer_tree_installed_stage(
    repo: Path, name: str, *, hooks: ProbeHooks
) -> StageProbe:
    """The installer-tree class's ``installed`` stage (Story 46.9): the
    APPLIED core version (``read_applied_core_version``) wins over the
    pixi-env conda-meta scan (``hooks.installed``) whenever both are present
    and disagree -- naming the disagreement via a documented, stable
    ``detail`` sentinel (``name_drifts`` matches on it) rather than a new
    ``StageProbe`` field. Falls back to the conda-meta read, unchanged,
    when the manifest is absent (a non-``bmad-method`` checkout state)."""
    applied = read_applied_core_version(repo)
    env = hooks.installed(repo, name)
    if applied is None:
        return _stage_from_value(env)
    if env is not None and applied != env:
        return StageProbe(
            value=applied,
            ok=True,
            detail=f"applied {applied} / env {env} -- core-applied-env-drift",
        )
    return StageProbe(value=applied, ok=True)


def _behind(left: str | None, right: str | None) -> bool:
    """True when *left* release triple is strictly behind *right*."""
    if left is None or right is None:
        return False
    lt = _parse_release_triple(left)
    rt = _parse_release_triple(right)
    if lt is None or rt is None:
        return left != right
    return lt < rt


def name_drifts(pkg: PackageTruth) -> tuple[str, ...]:
    """Name per-stage drifts (CAP-1: drift named per stage)."""
    drifts: list[str] = []
    npm_v = pkg.upstream_npm.value
    gh_v = pkg.upstream_github.value
    recipe_v = pkg.recipe.value
    channel_v = pkg.channel.value
    installed_v = pkg.installed.value
    wired_v = pkg.wired.value

    if (
        pkg.upstream_npm.ok
        and pkg.upstream_github.ok
        and npm_v
        and gh_v
        and _parse_release_triple(npm_v) != _parse_release_triple(gh_v)
        and npm_v != gh_v
    ):
        drifts.append("upstream_npm_github_divergence")

    upstream_for_recipe = gh_v or npm_v
    if recipe_v and upstream_for_recipe and _behind(recipe_v, upstream_for_recipe):
        drifts.append("recipe")

    if recipe_v and channel_v and _behind(channel_v, recipe_v):
        drifts.append("channel")

    if recipe_v and installed_v and _behind(installed_v, recipe_v):
        drifts.append("installed")

    # Story 46.9: the installer-tree class's applied-vs-env disagreement,
    # named via `_installer_tree_installed_stage`'s own stable `detail`
    # sentinel substring (never a new `StageProbe` field).
    if pkg.installed.detail and "core-applied-env-drift" in pkg.installed.detail:
        drifts.append("core_applied_env_drift")

    # Unwired / missing / failed wired probe name the wired stage.
    if not pkg.wired.ok or wired_v not in _WIRED_SETTLED_VALUES:
        drifts.append("wired")

    return tuple(drifts)


@dataclass
class ProbeHooks:
    """Injectable probe callables — tests stub these; live uses module defaults.

    ``github`` takes ``(owner_repo, package)`` so baseline replay can disambiguate
    packages that share one GitHub repo (bmad-dashboard / mybmad-dashboard).
    """

    npm: Callable[[str], str | None] = field(default=fetch_npm_latest)
    github: Callable[[str, str | None], str | None] = field(default=fetch_github_latest)
    channel: Callable[[str], str | None] = field(default=fetch_channel_version)
    recipe: Callable[[Path, str], str | None] = field(default=read_recipe_version)
    installed: Callable[[Path, str], str | None] = field(default=read_installed_version)
    wired: Callable[[Path, SuitePackageDef], StageProbe] = field(default=probe_wired)


def build_package_truth(
    repo: Path,
    pkg: SuitePackageDef,
    *,
    hooks: ProbeHooks | None = None,
) -> PackageTruth:
    """Probe one package — every stage fail-open."""
    hooks = hooks or ProbeHooks()

    if pkg.npm_name is None:
        npm_stage = _stage_from_value(
            None, skipped=True, skip_detail="npm probe skipped for package class"
        )
    else:
        try:
            npm_stage = _stage_from_value(hooks.npm(pkg.npm_name))
        except Exception as exc:  # noqa: BLE001
            npm_stage = StageProbe(value=None, ok=False, detail=str(exc))

    if pkg.github_repo is None:
        gh_stage = _stage_from_value(
            None, skipped=True, skip_detail="GitHub probe skipped for package class"
        )
    else:
        try:
            gh_stage = _stage_from_value(hooks.github(pkg.github_repo, pkg.name))
        except Exception as exc:  # noqa: BLE001
            gh_stage = StageProbe(value=None, ok=False, detail=str(exc))

    try:
        recipe_stage = _stage_from_value(hooks.recipe(repo, pkg.name))
    except Exception as exc:  # noqa: BLE001
        recipe_stage = StageProbe(value=None, ok=False, detail=str(exc))

    try:
        channel_stage = _stage_from_value(hooks.channel(pkg.name))
    except Exception as exc:  # noqa: BLE001
        channel_stage = StageProbe(value=None, ok=False, detail=str(exc))

    try:
        if pkg.install_class == INSTALL_CLASS_INSTALLER_TREE:
            installed_stage = _installer_tree_installed_stage(repo, pkg.name, hooks=hooks)
        else:
            installed_stage = _stage_from_value(hooks.installed(repo, pkg.name))
    except Exception as exc:  # noqa: BLE001
        installed_stage = StageProbe(value=None, ok=False, detail=str(exc))

    try:
        wired_stage = hooks.wired(repo, pkg)
    except Exception as exc:  # noqa: BLE001
        wired_stage = StageProbe(value=None, ok=False, detail=str(exc))

    partial = PackageTruth(
        name=pkg.name,
        upstream_npm=npm_stage,
        upstream_github=gh_stage,
        recipe=recipe_stage,
        channel=channel_stage,
        installed=installed_stage,
        wired=wired_stage,
        install_class=pkg.install_class,
    )
    return PackageTruth(
        name=partial.name,
        upstream_npm=partial.upstream_npm,
        upstream_github=partial.upstream_github,
        recipe=partial.recipe,
        channel=partial.channel,
        installed=partial.installed,
        wired=partial.wired,
        install_class=partial.install_class,
        drifts=name_drifts(partial),
    )


def build_pipeline_truth_report(
    repo: Path,
    *,
    packages: Sequence[SuitePackageDef] = SUITE_PACKAGES,
    hooks: ProbeHooks | None = None,
    baseline_id: str | None = None,
) -> PipelineTruthReport:
    """Report all suite packages; never aborts on a single probe failure."""
    rows = tuple(build_package_truth(repo, pkg, hooks=hooks) for pkg in packages)
    notes: list[str] = []
    if baseline_id:
        notes.append(f"baseline: {baseline_id}")
    failed_stages = sum(
        1
        for row in rows
        for stage in (
            row.upstream_npm,
            row.upstream_github,
            row.recipe,
            row.channel,
            row.installed,
            row.wired,
        )
        if not stage.ok
    )
    if failed_stages:
        notes.append(f"fail-open stages with no value: {failed_stages}")
    return PipelineTruthReport(
        packages=rows,
        baseline_id=baseline_id,
        notes=tuple(notes),
    )


# ── 2026-08-22 research matrix (recorded baseline shape) ───────────────────

# Values from docs/dreams/bmad-suite-channel-product.md + install-matrix.md
# (channel bmad-method 6.3.0 relic; TEA tag-unreleased 1.23.3; npm-stale
# builder/CIS/WDS; wired vs unwired census from the Dream).
BASELINE_2026_08_22: dict[str, dict[str, str | None]] = {
    "bmad-method": {
        "upstream_npm": "6.11.0",
        "upstream_github": "6.11.0",
        "recipe": "6.11.0",
        "channel": "6.3.0",
        "installed": "6.11.0",
        "wired": "wired",
    },
    "bmad-loop": {
        "upstream_npm": None,
        "upstream_github": "0.11.0",
        "recipe": "0.11.0",
        "channel": "0.11.0",
        "installed": "0.11.0",
        "wired": "wired",
    },
    "bmad-method-test-architecture-enterprise": {
        "upstream_npm": "1.23.2",
        "upstream_github": "1.23.3",
        "recipe": "1.23.2",
        "channel": "1.23.2",
        "installed": "1.23.2",
        "wired": "unwired",
    },
    "bmad-builder": {
        "upstream_npm": "1.1.0",
        "upstream_github": "2.2.1",
        "recipe": "2.2.1",
        "channel": "2.2.1",
        "installed": "2.2.1",
        "wired": "unwired",
    },
    "bmad-creative-intelligence-suite": {
        "upstream_npm": "0.1.9",
        "upstream_github": "0.3.1",
        "recipe": "0.3.1",
        "channel": "0.3.1",
        "installed": "0.3.1",
        "wired": "unwired",
    },
    "bmad-module-skill-forge": {
        "upstream_npm": "2.1.0",
        "upstream_github": "2.1.0",
        "recipe": "2.1.0",
        "channel": "2.1.0",
        "installed": None,
        "wired": "wired",
    },
    # Joined 2026-09-05 (Story 45.1) in WDS's seat — this row is recorded
    # 2026-09-05, not 2026-08-22: upstream tag/npm still v0.1.0; recipe, channel
    # (SelfExplainML upload 2026-09-05) and the pixi-installed bin all on the
    # commit-pinned 0.2.0 line; eval-quality on PATH -> runnable.
    "bmad-eval-quality": {
        "upstream_npm": "0.1.0",
        "upstream_github": "0.1.0",
        "recipe": "0.2.0.dev0",
        "channel": "0.2.0.dev0",
        "installed": "0.2.0.dev0",
        "wired": "runnable",
    },
    "bmad-utility-skills": {
        "upstream_npm": None,
        "upstream_github": "2.0.0",
        "recipe": "2.0.0",
        "channel": "2.0.0",
        "installed": "2.0.0",
        "wired": "unwired",
    },
    "bmad-labs-skills": {
        "upstream_npm": None,
        "upstream_github": "1.0.0",
        "recipe": "1.0.0.dev0",
        "channel": "1.0.0.dev0",
        "installed": "1.0.0.dev0",
        "wired": "wired",
    },
    "bmad-module-template": {
        "upstream_npm": None,
        "upstream_github": "0.1.0",
        "recipe": "0.1.0",
        "channel": "0.1.0",
        "installed": "0.1.0",
        "wired": "n/a",
    },
    "bmad-manticore": {
        "upstream_npm": None,
        "upstream_github": "3.1.0",
        "recipe": "3.1.0.dev0",
        "channel": "3.1.0.dev0",
        "installed": "3.1.0.dev0",
        "wired": "unwired",
    },
    "bmad-dashboard": {
        "upstream_npm": None,
        "upstream_github": "1.2.2",
        "recipe": "1.2.2.dev0",
        "channel": "1.2.2.dev0",
        "installed": "1.2.2.dev0",
        "wired": "wired",
    },
    "mybmad-dashboard": {
        "upstream_npm": None,
        "upstream_github": "0.1.0",
        "recipe": "0.1.0.dev0",
        "channel": "0.1.0.dev0",
        "installed": "0.1.0.dev0",
        "wired": "wired",
    },
}

assert set(BASELINE_2026_08_22) == {p.name for p in SUITE_PACKAGES}


def hooks_from_baseline(
    baseline: Mapping[str, Mapping[str, str | None]],
) -> ProbeHooks:
    """Build ProbeHooks that replay a recorded matrix (no network)."""

    def npm(name: str) -> str | None:
        for pkg_name, row in baseline.items():
            defn = next((p for p in SUITE_PACKAGES if p.name == pkg_name), None)
            if defn is None:
                continue
            if defn.npm_name == name:
                return row.get("upstream_npm")
        return None

    def github(owner_repo: str, package: str | None = None) -> str | None:
        # Package-aware lookup — shared GitHub repos (dashboard / mybmad) must
        # not collide on first-match-by-repo.
        if package is not None:
            row = baseline.get(package)
            return None if row is None else row.get("upstream_github")
        for pkg_name, row in baseline.items():
            defn = next((p for p in SUITE_PACKAGES if p.name == pkg_name), None)
            if defn is None:
                continue
            if defn.github_repo == owner_repo:
                return row.get("upstream_github")
        return None

    def channel(package: str) -> str | None:
        row = baseline.get(package)
        return None if row is None else row.get("channel")

    def recipe(_repo: Path, package: str) -> str | None:
        row = baseline.get(package)
        return None if row is None else row.get("recipe")

    def installed(_repo: Path, package: str) -> str | None:
        row = baseline.get(package)
        return None if row is None else row.get("installed")

    def wired(_repo: Path, pkg: SuitePackageDef) -> StageProbe:
        row = baseline.get(pkg.name) or {}
        value = row.get("wired")
        if value is None:
            return StageProbe(value=None, ok=False, detail="baseline missing wired")
        return StageProbe(value=value, ok=True, detail="baseline recorded")

    return ProbeHooks(
        npm=npm,
        github=github,
        channel=channel,
        recipe=recipe,
        installed=installed,
        wired=wired,
    )


def format_pipeline_truth(report: PipelineTruthReport, *, as_json: bool) -> str:
    if as_json:
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)

    lines: list[str] = [
        "steward suite pipeline-truth — CAP-1 whole-pipeline report",
        f"packages: {len(report.packages)}",
    ]
    if report.baseline_id:
        lines.append(f"baseline: {report.baseline_id}")
    lines.append("")

    for pkg in report.packages:
        drift = ",".join(pkg.drifts) if pkg.drifts else "-"
        lines.append(f"## {pkg.name}")
        lines.append(f"  upstream_npm:     {_fmt_stage(pkg.upstream_npm)}")
        lines.append(f"  upstream_github:  {_fmt_stage(pkg.upstream_github)}")
        lines.append(f"  recipe:           {_fmt_stage(pkg.recipe)}")
        lines.append(f"  channel:          {_fmt_stage(pkg.channel)}")
        lines.append(f"  installed:        {_fmt_stage(pkg.installed)}")
        lines.append(f"  wired:            {_fmt_wired(pkg)}")
        lines.append(f"  drifts:           {drift}")
        lines.append("")

    if report.notes:
        lines.append("## Notes")
        for note in report.notes:
            lines.append(f"- {note}")
    return "\n".join(lines).rstrip() + "\n"


def _fmt_wired(pkg: PackageTruth) -> str:
    stage = _fmt_stage(pkg.wired)
    if pkg.install_class in (
        INSTALL_CLASS_MODULE,
        INSTALL_CLASS_SKIP,
    ):
        return stage
    return f"{pkg.install_class} | {stage}"


def _fmt_stage(stage: StageProbe) -> str:
    if stage.value is not None:
        return stage.value
    if stage.ok:
        return "(skipped)"
    return f"(unavailable{': ' + stage.detail if stage.detail else ''})"


class SuiteDuty:
    """``steward suite …`` — Epic 15 CAP-1 pipeline-truth + CAP-2 advance."""

    name = "suite"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "suite_verb", None)
        if not verb:
            return DutyResult(
                ok=True,
                summary=(
                    "suite: available verbs are pipeline-truth "
                    "(CAP-1 report-only whole-pipeline truth) and advance "
                    "(CAP-2 one-command stale-package advance → reviewable PR, "
                    "never auto-merged)"
                ),
            )
        try:
            if verb == "pipeline-truth":
                return self._pipeline_truth(ns)
            if verb == "advance":
                from .suite_advance import advance_from_namespace

                return advance_from_namespace(ns)
            return DutyResult(ok=False, summary=f"suite: unknown verb {verb!r}")
        except SuiteError as exc:
            return DutyResult(ok=False, summary=f"suite: {exc}")
        except (OSError, yaml.YAMLError) as exc:
            return DutyResult(ok=False, summary=f"suite: {exc}")

    def _pipeline_truth(self, ns: argparse.Namespace) -> DutyResult:
        repo = Path(ns.repo_root) if getattr(ns, "repo_root", None) else repo_root()
        as_json = bool(getattr(ns, "json", False))
        use_baseline = bool(getattr(ns, "baseline", False))
        hooks: ProbeHooks | None = None
        baseline_id: str | None = None
        if use_baseline:
            hooks = hooks_from_baseline(BASELINE_2026_08_22)
            baseline_id = BASELINE_ID_2026_08_22
        report = build_pipeline_truth_report(
            repo, hooks=hooks, baseline_id=baseline_id
        )
        return DutyResult(
            ok=True,
            summary=format_pipeline_truth(report, as_json=as_json),
            details={"report": report.to_dict()},
        )
