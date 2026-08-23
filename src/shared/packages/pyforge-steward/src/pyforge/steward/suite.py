"""Steward's ``suite`` duty — bmad-suite channel pipeline truth (Epic 15 / CAP-1).

Story 15.1: one command reports, for each of the 13 suite packages, upstream
latest (npm and/or GitHub per package class), recipe version, SelfExplainML
channel version, installed version, and wired-or-not — with drift named per
stage. Every probe is fail-open: one failure never aborts the whole report.

Consumes the same probe shapes doctor already uses (npm registry, GitHub
releases/tags, ``recipe.yaml`` parse, ``api.anaconda.org``, conda-meta /
installed-version scan, ``.claude/skills`` + ``_bmad`` census) without
importing ``pyforge.doctor`` (steward stays free of a doctor run-dependency).

Verb: ``steward suite pipeline-truth``. Never implements CAP-2 autotick
advance (Story 15.2) or later CAP stories.
"""

from __future__ import annotations

import argparse
import http.client
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .interfaces import DutyResult

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
    wire_bmad_config_keys: tuple[str, ...] = ()


# install-matrix.md + Dream grounding (2026-08-22) — package class → probes.
SUITE_PACKAGES: tuple[SuitePackageDef, ...] = (
    SuitePackageDef(
        name="bmad-method",
        npm_name="bmad-method",
        github_repo="bmad-code-org/BMAD-METHOD",
        wire_bmad_dirs=("core", "bmm"),
    ),
    SuitePackageDef(
        name="bmad-loop",
        npm_name=None,  # npm-invisible
        github_repo="bmad-code-org/bmad-loop",
        wire_skill_prefixes=("bmad-loop-",),
    ),
    SuitePackageDef(
        name="bmad-method-test-architecture-enterprise",
        npm_name="bmad-method-test-architecture-enterprise",
        github_repo="bmad-code-org/bmad-method-test-architecture-enterprise",
        wire_skill_prefixes=("bmad-testarch-", "bmad-tea", "bmad-teach-me-testing"),
        wire_skill_names=("bmad-tea",),
    ),
    SuitePackageDef(
        name="bmad-builder",
        npm_name="bmad-builder",
        github_repo="bmad-code-org/bmad-builder",
        wire_bmad_config_keys=("bmb",),
        wire_skill_prefixes=("bmad-bmb-", "bmad-agent-builder", "bmad-module-builder"),
    ),
    SuitePackageDef(
        name="bmad-creative-intelligence-suite",
        npm_name="bmad-creative-intelligence-suite",
        github_repo="bmad-code-org/bmad-module-creative-intelligence-suite",
        wire_skill_prefixes=("bmad-cis-",),
    ),
    SuitePackageDef(
        name="bmad-module-skill-forge",
        npm_name="bmad-module-skill-forge",
        github_repo="armelhbobdad/bmad-module-skill-forge",
        wire_bmad_dirs=("skf",),
        wire_skill_prefixes=("skf-",),
    ),
    SuitePackageDef(
        name="bmad-method-wds-expansion",
        npm_name="bmad-wds",  # install-matrix: npm name ≠ recipe name
        github_repo="bmad-code-org/bmad-method-wds-expansion",
        wire_policy="skip",
    ),
    SuitePackageDef(
        name="bmad-utility-skills",
        npm_name=None,
        github_repo="bmad-code-org/bmad-utility-skills",
        wire_skill_prefixes=("bmad-os-",),
    ),
    SuitePackageDef(
        name="bmad-labs-skills",
        npm_name=None,
        github_repo="bmad-labs/skills",
        # Distinctive share skill names — presence in .claude/skills => wired.
        wire_skill_names=(
            "ai-multimodal",
            "ultrathink-protocol",
            "architecture-viz-studio",
        ),
    ),
    SuitePackageDef(
        name="bmad-module-template",
        npm_name=None,
        github_repo="bmad-code-org/bmad-module-template",
        wire_policy="n/a",
    ),
    SuitePackageDef(
        name="bmad-manticore",
        npm_name=None,
        github_repo="bmad-code-org/bmad-manticore",
        wire_skill_prefixes=("mc-",),
    ),
    SuitePackageDef(
        name="bmad-dashboard",
        npm_name=None,  # npm bmad-dashboard is an unrelated collision
        github_repo="bmad-code-org/bmad-method-ui",
        # UI package — "wired" when the fleet's dashboard surface exists.
        wire_skill_names=(),
        wire_skill_prefixes=(),
        wire_policy="census",
        wire_bmad_dirs=(),
    ),
    SuitePackageDef(
        name="mybmad-dashboard",
        npm_name=None,
        github_repo="bmad-code-org/bmad-method-ui",
        wire_policy="census",
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

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
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


def _dashboard_wired(repo: Path, package: str) -> StageProbe:
    """Dashboards are not skills-modules; treat fleet UI presence as wired."""
    # presentations/pyforge-* decks + package recipe existence ≈ "in the fleet".
    presentations = repo / "presentations"
    try:
        names = {p.name for p in presentations.iterdir()} if presentations.is_dir() else set()
    except OSError:
        names = set()
    if package == "bmad-dashboard" and (
        "pyforge-steward" in names or "agentic-sdlc" in names or (repo / "docs" / "dashboard").is_dir()
    ):
        return StageProbe(value="wired", ok=True, detail="fleet dashboard surface present")
    if package == "mybmad-dashboard" and (repo / "docs" / "dashboard").is_dir():
        return StageProbe(value="wired", ok=True, detail="docs/dashboard present")
    # Fall back: installed package alone does not count as wired.
    return StageProbe(value="unwired", ok=True, detail="no fleet dashboard surface")


def probe_wired(repo: Path, pkg: SuitePackageDef) -> StageProbe:
    """``.claude/skills`` + ``_bmad`` census — fail-open, never raises."""
    try:
        if pkg.wire_policy == "skip":
            return StageProbe(
                value="skip",
                ok=True,
                detail="deprecated upstream; wiring deliberately skipped",
            )
        if pkg.wire_policy == "n/a":
            return StageProbe(
                value="n/a",
                ok=True,
                detail="template/scaffold — not a wireable module",
            )
        if pkg.name in ("bmad-dashboard", "mybmad-dashboard"):
            return _dashboard_wired(repo, pkg.name)

        if pkg.wire_bmad_dirs:
            if all((repo / "_bmad" / d).is_dir() for d in pkg.wire_bmad_dirs):
                return StageProbe(
                    value="wired",
                    ok=True,
                    detail=f"_bmad dirs: {', '.join(pkg.wire_bmad_dirs)}",
                )

        if pkg.wire_bmad_config_keys:
            keys = _bmad_config_keys(repo)
            if any(k in keys for k in pkg.wire_bmad_config_keys):
                return StageProbe(
                    value="wired",
                    ok=True,
                    detail=f"_bmad/config.yaml keys: {', '.join(pkg.wire_bmad_config_keys)}",
                )

        skills = _skills_census(repo)
        for name in pkg.wire_skill_names:
            if name in skills:
                return StageProbe(
                    value="wired",
                    ok=True,
                    detail=f".claude/skills has {name}",
                )
        for prefix in pkg.wire_skill_prefixes:
            if any(s.startswith(prefix) or s == prefix.rstrip("-") for s in skills):
                return StageProbe(
                    value="wired",
                    ok=True,
                    detail=f".claude/skills matches prefix {prefix!r}",
                )

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

    # Unwired OR a failed wired probe both name the wired stage.
    if wired_v == "unwired" or not pkg.wired.ok:
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
    )
    return PackageTruth(
        name=partial.name,
        upstream_npm=partial.upstream_npm,
        upstream_github=partial.upstream_github,
        recipe=partial.recipe,
        channel=partial.channel,
        installed=partial.installed,
        wired=partial.wired,
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
    "bmad-method-wds-expansion": {
        "upstream_npm": "0.3.1",
        "upstream_github": "0.4.3",
        "recipe": "0.4.3",
        "channel": "0.4.3",
        "installed": "0.4.3",
        "wired": "skip",
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
        lines.append(f"  wired:            {_fmt_stage(pkg.wired)}")
        lines.append(f"  drifts:           {drift}")
        lines.append("")

    if report.notes:
        lines.append("## Notes")
        for note in report.notes:
            lines.append(f"- {note}")
    return "\n".join(lines).rstrip() + "\n"


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
