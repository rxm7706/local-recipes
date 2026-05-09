#!/usr/bin/env python3
"""
scan-project — Vulnerability scan a project's dependency manifests.

Discovers and parses pixi.lock, pixi.toml, requirements.txt, pyproject.toml,
environment.yml, Containerfile/Dockerfile, and (optionally) container base
image OS packages. Looks up CVEs across all of them via the local vdb DB
and the cf_atlas.db (for conda-forge match enrichment).

  Lock-file priority: pixi.lock ALWAYS wins over pixi.toml when both exist.
  Container scanning: parses FROM + RUN apt/dnf/apk/pip lines; with --trivy,
                       delegates full image scan to trivy if installed.
  OS CVE lookups:     gated behind --os (requires `vdb --cache-os` data).

CLI:
  scan-project [PATH_OR_URL]
               [--github]              # treat input as github URL → clone
               [--ref REF]             # checkout specific branch/tag/sha
               [--os]                  # include OS-level (apt/dnf) CVE lookups
               [--no-trivy]            # don't try trivy even if installed
               [--keep-clone]          # don't delete the temp clone after
               [--brief]               # show aggregate + top-5 only
               [--json]                # machine-readable output

Pixi:
  pixi run -e vuln-db scan-project -- .                    # local cwd
  pixi run -e vuln-db scan-project -- --github rxm7706/local-recipes
  pixi run -e vuln-db scan-project -- /path/to/project --os --brief
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _make_req(url: str, extra_headers: dict | None = None
              ) -> urllib.request.Request:
    """Tiny local make_req for OCI registry probes; conda_forge_atlas has
    a richer enterprise-aware version."""
    headers: dict = {"User-Agent": "scan-project/cf-atlas"}
    if extra_headers:
        headers.update(extra_headers)
    return urllib.request.Request(url, headers=headers)


def _get_data_dir() -> Path:
    """Get skill-scoped data directory: .claude/data/conda-forge-expert/"""
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"


DATA_DIR = _get_data_dir()
ATLAS_DB = DATA_DIR / "cf_atlas.db"
RULE = "─" * 74
DOUBLE_RULE = "═" * 74
TRIVY_BIN = shutil.which("trivy")

# Path segments to skip when discovering manifests — avoids picking up
# build artifacts, extracted source caches, test environments, vendored deps.
_SKIP_PATH_PARTS = frozenset({
    ".git", "node_modules", ".pixi", ".venv", "venv", "env",
    "output", "src_cache", "bld", "work",
    "_bmad-output", "build_artifacts",
    "test_env", "test_run_env",
    ".pytest_cache", ".mypy_cache", "__pycache__",
    "gopath",  # Go module cache
    "site-packages",  # Python install dir
    "target", "vendor", ".cargo",  # Rust/Cargo build/cache
})


@dataclass
class Dep:
    name: str
    version: str | None
    ecosystem: str  # conda / pypi / npm / apt / dnf / apk / generic
    manifest: str   # source file (relative path)
    extras: dict[str, Any] = field(default_factory=dict)

    def purl(self) -> str | None:
        if not self.name:
            return None
        # purl ecosystem mapping. The set here mirrors what `vdb` and the
        # broader CycloneDX ecosystem accepts as `pkg:<type>/...` prefixes.
        # Anything outside this set falls through to 'generic' which won't
        # match vdb but is still a valid purl-spec.
        known = {"pypi", "conda", "npm", "cargo", "maven", "gem",
                 "composer", "golang", "nuget", "deb", "rpm", "apk"}
        eco = self.ecosystem if self.ecosystem in known else "generic"
        if self.version:
            return f"pkg:{eco}/{self.name}@{self.version}"
        return f"pkg:{eco}/{self.name}"


# ── Manifest parsers ────────────────────────────────────────────────────────

def parse_pixi_lock(path: Path) -> list[Dep]:
    """pixi.lock is YAML; needs PyYAML. Returns resolved deps from default env."""
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return []
    try:
        data = yaml.safe_load(path.read_text())
    except Exception:
        return []
    deps: list[Dep] = []
    # pixi.lock layout: packages: [{conda: ..., pypi: ...}], envs: {<env>: {channels, packages: [...]}}
    for pkg in (data or {}).get("packages", []) or []:
        if not isinstance(pkg, dict):
            continue
        if "conda" in pkg:
            url = pkg.get("conda", "")
            # Format: https://conda.anaconda.org/<channel>/<subdir>/<name>-<version>-<build>.conda
            # Extract basename FIRST so the regex doesn't accidentally match
            # the subdir segment (e.g., 'linux-64/_openmp_mutex-4.5-2_gnu.tar.bz2'
            # would otherwise capture name='linux', version='64/_openmp_mutex').
            basename = url.rsplit("/", 1)[-1]
            m = re.match(r"^(.+)-([^-]+)-[^-]+\.(?:conda|tar\.bz2)$", basename)
            if m:
                deps.append(Dep(
                    name=m.group(1).lower(), version=m.group(2),
                    ecosystem="conda", manifest=path.name,
                    extras={"sha256": pkg.get("sha256"), "url": url},
                ))
        elif "pypi" in pkg:
            url = pkg.get("pypi", "")
            name = pkg.get("name") or ""
            ver = pkg.get("version") or ""
            if not name and url:
                m = re.search(r"/([^/]+?)[-_]([\d][^/]*?)-[^/]+\.(?:whl|tar\.gz|zip)$", url.rsplit("/", 1)[-1] if "/" in url else url)
                if m:
                    name, ver = m.group(1).lower(), m.group(2)
            if name:
                deps.append(Dep(
                    name=name.lower(), version=ver or None,
                    ecosystem="pypi", manifest=path.name,
                    extras={"url": url},
                ))
    return deps


def parse_pixi_toml(path: Path) -> list[Dep]:
    """pixi.toml — only used when pixi.lock is missing. Less precise (no resolved versions)."""
    try:
        import tomllib  # py 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[import-not-found,no-redef]
        except ImportError:
            return []
    try:
        data = tomllib.loads(path.read_text())
    except Exception:
        return []
    deps: list[Dep] = []
    for section_name, section in data.items():
        if not isinstance(section, dict):
            continue
        # Top-level [dependencies] = conda, [pypi-dependencies] = pypi
        if section_name == "dependencies":
            for n, v in (section or {}).items():
                deps.append(Dep(name=n.lower(), version=str(v) if v else None,
                                ecosystem="conda", manifest=path.name))
        elif section_name == "pypi-dependencies":
            for n, v in (section or {}).items():
                ver = v.get("version") if isinstance(v, dict) else (str(v) if v else None)
                deps.append(Dep(name=n.lower(), version=ver,
                                ecosystem="pypi", manifest=path.name))
        elif section_name in ("feature", "environments"):
            # nested per-feature dependencies
            for sub_name, sub in (section or {}).items():
                if not isinstance(sub, dict):
                    continue
                for k in ("dependencies", "pypi-dependencies"):
                    eco = "conda" if k == "dependencies" else "pypi"
                    for n, v in (sub.get(k) or {}).items():
                        ver = v.get("version") if isinstance(v, dict) else (str(v) if v else None)
                        deps.append(Dep(name=n.lower(), version=ver,
                                        ecosystem=eco, manifest=f"{path.name}#feature.{sub_name}"))
    return deps


def parse_requirements_txt(path: Path) -> list[Dep]:
    deps: list[Dep] = []
    for line in path.read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9._-]+)(?:\s*[=<>~!]=?\s*([0-9][^,;\s]*))?", line)
        if m:
            deps.append(Dep(name=m.group(1).lower(), version=m.group(2),
                            ecosystem="pypi", manifest=path.name))
    return deps


def parse_pyproject_toml(path: Path) -> list[Dep]:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[import-not-found,no-redef]
        except ImportError:
            return []
    try:
        data = tomllib.loads(path.read_text())
    except Exception:
        return []
    deps: list[Dep] = []
    project = data.get("project") or {}
    spec_re = re.compile(r"^([A-Za-z0-9._-]+)(?:\s*[=<>~!]=?\s*([0-9][^,;\s]*))?")

    def _add(spec: Any, manifest: str) -> None:
        if not isinstance(spec, str):
            return
        m = spec_re.match(spec)
        if m:
            deps.append(Dep(name=m.group(1).lower(), version=m.group(2),
                            ecosystem="pypi", manifest=manifest))

    # PEP 621 standard
    for spec in project.get("dependencies") or []:
        _add(spec, path.name)
    for extra_name, extras in (project.get("optional-dependencies") or {}).items():
        for spec in extras or []:
            _add(spec, f"{path.name}#extras.{extra_name}")

    # PEP 735 dependency-groups (top-level [dependency-groups], not under
    # [project]). Each group is a list[str | dict]; the dict form supports
    # `{include-group = "..."}` references which we resolve transitively.
    dgroups = data.get("dependency-groups") or {}
    if isinstance(dgroups, dict):
        def _resolve_group(group_name: str, seen: set[str]) -> list[str]:
            if group_name in seen:
                return []
            seen.add(group_name)
            entries = dgroups.get(group_name) or []
            out: list[str] = []
            for entry in entries:
                if isinstance(entry, str):
                    out.append(entry)
                elif isinstance(entry, dict):
                    inc = entry.get("include-group")
                    if isinstance(inc, str):
                        out.extend(_resolve_group(inc, seen))
            return out
        for gname in dgroups.keys():
            for spec in _resolve_group(gname, set()):
                _add(spec, f"{path.name}#dep-groups.{gname}")

    # Tool-specific sections beyond PEP 621 / 735.
    tool = data.get("tool") or {}

    # Poetry [tool.poetry.dependencies] and [tool.poetry.dev-dependencies] +
    # [tool.poetry.group.<name>.dependencies] (Poetry 1.2+)
    poetry = tool.get("poetry") or {}
    for section_name, section in (
        ("dependencies", poetry.get("dependencies")),
        ("dev-dependencies", poetry.get("dev-dependencies")),
    ):
        if not isinstance(section, dict):
            continue
        for n, v in section.items():
            if n.lower() == "python":
                continue  # Python interpreter constraint, not a dep
            ver = (v.get("version") if isinstance(v, dict)
                   else (v if isinstance(v, str) else None))
            ver = (re.sub(r"^[\^~>=<*]+\s*", "", ver) or None) if ver else None
            deps.append(Dep(name=n.lower(), version=ver, ecosystem="pypi",
                            manifest=f"{path.name}#poetry.{section_name}"))
    poetry_groups = poetry.get("group") or {}
    if isinstance(poetry_groups, dict):
        for gname, gdef in poetry_groups.items():
            gdeps = (gdef or {}).get("dependencies") or {}
            if not isinstance(gdeps, dict):
                continue
            for n, v in gdeps.items():
                if n.lower() == "python":
                    continue
                ver = (v.get("version") if isinstance(v, dict)
                       else (v if isinstance(v, str) else None))
                ver = (re.sub(r"^[\^~>=<*]+\s*", "", ver) or None) if ver else None
                deps.append(Dep(name=n.lower(), version=ver, ecosystem="pypi",
                                manifest=f"{path.name}#poetry.group.{gname}"))

    # PDM [tool.pdm.dev-dependencies] — dict of groups, each a list[str]
    pdm = tool.get("pdm") or {}
    pdm_dev = pdm.get("dev-dependencies") or {}
    if isinstance(pdm_dev, dict):
        for gname, gspecs in pdm_dev.items():
            for spec in gspecs or []:
                _add(spec, f"{path.name}#pdm.dev.{gname}")

    # Hatch [tool.hatch.envs.<env>.dependencies]
    hatch = tool.get("hatch") or {}
    hatch_envs = (hatch.get("envs") or {})
    if isinstance(hatch_envs, dict):
        for env_name, env_def in hatch_envs.items():
            if not isinstance(env_def, dict):
                continue
            for spec in env_def.get("dependencies") or []:
                _add(spec, f"{path.name}#hatch.envs.{env_name}")

    return deps


def parse_cargo_lock(path: Path) -> list[Dep]:
    """Cargo.lock — TOML; [[package]] arrays. Extracts full dep-tree into
    Dep.extras['depends_on'] (used by SBOM dependencies[] graph)."""
    try:
        import tomllib  # py 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[import-not-found,no-redef]
        except ImportError:
            return []
    try:
        data = tomllib.loads(path.read_text())
    except Exception:
        return []
    deps: list[Dep] = []
    for pkg in data.get("package", []) or []:
        if not isinstance(pkg, dict):
            continue
        name, version = pkg.get("name"), pkg.get("version")
        if not name or not version:
            continue
        # Cargo.lock dep entries look like "serde_derive 1.0.219" or
        # "serde 1.0.219 (registry+https://github.com/rust-lang/crates.io-index)"
        depends_on: list[str] = []
        for dep_str in pkg.get("dependencies", []) or []:
            m = re.match(r"^([\w-]+)\s+([\w.+\-]+)", dep_str)
            if m:
                depends_on.append(f"{m.group(1)}@{m.group(2)}")
        deps.append(Dep(
            name=name.lower(), version=version,
            ecosystem="cargo", manifest=path.name,
            extras={"depends_on": depends_on, "source": pkg.get("source")},
        ))
    return deps


def parse_cargo_toml(path: Path) -> list[Dep]:
    """Cargo.toml — only when Cargo.lock missing. Top-level deps only (no resolution)."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[import-not-found,no-redef]
        except ImportError:
            return []
    try:
        data = tomllib.loads(path.read_text())
    except Exception:
        return []
    deps: list[Dep] = []
    for section in ("dependencies", "dev-dependencies", "build-dependencies"):
        for n, v in (data.get(section) or {}).items():
            if isinstance(v, str):
                ver = v.lstrip("=^~<>* ") or None
            elif isinstance(v, dict):
                ver = (v.get("version") or "").lstrip("=^~<>* ") or None
            else:
                ver = None
            deps.append(Dep(
                name=n.lower(), version=ver,
                ecosystem="cargo", manifest=f"{path.name}#{section}",
            ))
    return deps


def parse_package_json(path: Path) -> list[Dep]:
    """npm package.json — read `dependencies` + `devDependencies` + `peerDependencies`."""
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    deps: list[Dep] = []
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        d = data.get(section) or {}
        if not isinstance(d, dict):
            continue
        for n, v in d.items():
            if not n:
                continue
            ver = v if isinstance(v, str) else None
            # Strip semver-range prefixes for the version field; keep raw in extras
            stripped = re.sub(r"^[\^~>=<]+\s*", "", ver) if ver else None
            deps.append(Dep(
                name=n.lower(), version=stripped,
                ecosystem="npm", manifest=f"{path.name}#{section}",
                extras={"version_range": ver},
            ))
    return deps


def parse_uv_lock(path: Path) -> list[Dep]:
    """uv lock format — TOML with [[package]] entries."""
    try:
        import tomllib  # py 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[import-not-found,no-redef]
        except ImportError:
            return []
    try:
        data = tomllib.loads(path.read_text())
    except Exception:
        return []
    deps: list[Dep] = []
    for pkg in data.get("package", []) or []:
        if not isinstance(pkg, dict):
            continue
        name = pkg.get("name")
        ver = pkg.get("version")
        if not name:
            continue
        deps.append(Dep(
            name=name.lower(), version=ver,
            ecosystem="pypi", manifest=path.name,
        ))
    return deps


def parse_poetry_lock(path: Path) -> list[Dep]:
    """Poetry lock file — TOML with [[package]] entries (slightly different than uv)."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[import-not-found,no-redef]
        except ImportError:
            return []
    try:
        data = tomllib.loads(path.read_text())
    except Exception:
        return []
    deps: list[Dep] = []
    for pkg in data.get("package", []) or []:
        if not isinstance(pkg, dict):
            continue
        name = pkg.get("name")
        ver = pkg.get("version")
        if not name:
            continue
        deps.append(Dep(
            name=name.lower(), version=ver,
            ecosystem="pypi", manifest=path.name,
        ))
    return deps


def parse_sbom_cyclonedx(path: Path) -> list[Dep]:
    """CycloneDX 1.4+ JSON SBOM. Reads `components` array; classifies by purl."""
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    deps: list[Dep] = []
    for comp in data.get("components", []) or []:
        if not isinstance(comp, dict):
            continue
        purl = comp.get("purl") or ""
        name = comp.get("name") or ""
        version = comp.get("version") or None
        # Derive ecosystem from purl, fall back to type
        eco = "generic"
        if purl.startswith("pkg:pypi/"):
            eco = "pypi"
        elif purl.startswith("pkg:conda/"):
            eco = "conda"
        elif purl.startswith("pkg:npm/"):
            eco = "npm"
        elif purl.startswith("pkg:deb/"):
            eco = "apt"
        elif purl.startswith("pkg:rpm/"):
            eco = "dnf"
        elif purl.startswith("pkg:apk/"):
            eco = "apk"
        elif purl.startswith("pkg:cargo/"):
            eco = "cargo"
        elif purl.startswith("pkg:maven/"):
            eco = "maven"
        elif purl.startswith("pkg:gem/"):
            eco = "gem"
        if not name:
            continue
        deps.append(Dep(
            name=name.lower(), version=version,
            ecosystem=eco, manifest=path.name,
            extras={"purl": purl, "bom-ref": comp.get("bom-ref")},
        ))
    return deps


def parse_sbom_spdx(path: Path) -> list[Dep]:
    """SPDX 2.3+ JSON SBOM. Reads `packages` array."""
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    deps: list[Dep] = []
    for pkg in data.get("packages", []) or []:
        if not isinstance(pkg, dict):
            continue
        name = pkg.get("name") or ""
        version = pkg.get("versionInfo") or None
        # SPDX externalRefs has purl-style packageManager refs
        eco = "generic"
        for ref in pkg.get("externalRefs", []) or []:
            if not isinstance(ref, dict):
                continue
            locator = (ref.get("referenceLocator") or "").lower()
            if locator.startswith("pkg:pypi/"):
                eco = "pypi"
                break
            if locator.startswith("pkg:conda/"):
                eco = "conda"
                break
            if locator.startswith("pkg:npm/"):
                eco = "npm"
                break
            if locator.startswith("pkg:deb/"):
                eco = "apt"
                break
        if not name:
            continue
        deps.append(Dep(
            name=name.lower(), version=version,
            ecosystem=eco, manifest=path.name,
            extras={"spdx_id": pkg.get("SPDXID")},
        ))
    return deps


def extract_sbom_from_image(image: str, prefer: str = "auto"
                            ) -> tuple[list[Dep] | None, str | None]:
    """Run `syft <image> -o cyclonedx-json` (preferred) or `trivy image
    --format cyclonedx <image>` (fallback) and parse the resulting SBOM.

    Returns (deps, error_msg). deps=None when neither tool is installed
    or when the run failed.
    """
    syft = shutil.which("syft")
    trivy = TRIVY_BIN
    tools: list[tuple[str, str]] = []
    if prefer == "syft" and syft:
        tools.append(("syft", syft))
    elif prefer == "trivy" and trivy:
        tools.append(("trivy", trivy))
    else:
        if syft:
            tools.append(("syft", syft))
        if trivy:
            tools.append(("trivy", trivy))
    if not tools:
        return (None, "neither syft nor trivy is installed (try `pixi run -e vuln-db ...` or `conda install -c conda-forge syft`)")

    for tool_name, tool_bin in tools:
        try:
            if tool_name == "syft":
                cmd = [tool_bin, image, "-o", "cyclonedx-json", "-q"]
            else:  # trivy
                cmd = [tool_bin, "image", "--format", "cyclonedx", "--quiet", image]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                continue  # try next tool
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
                tmp.write(result.stdout)
                tmp_path = Path(tmp.name)
            try:
                deps = parse_sbom_cyclonedx(tmp_path)
            finally:
                tmp_path.unlink(missing_ok=True)
            if deps:
                # Tag the manifest field with the image ref so users can trace
                for d in deps:
                    d.manifest = f"{tool_name}({image})"
                return (deps, None)
        except subprocess.TimeoutExpired:
            return (None, f"{tool_name} timed out (>300s) on {image}")
        except Exception:
            # try next tool
            continue
    return (None, "all available tools failed to extract SBOM")


def parse_package_lock_json(path: Path) -> list[Dep]:
    """npm package-lock.json (lockfileVersion 1, 2, 3).

    v2/v3 use top-level `packages` keyed by relative path; the empty-key
    `""` is the project itself, all others are deps. Each entry has
    `version`. v1 uses nested `dependencies`. We support both.
    """
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    deps: list[Dep] = []
    seen: set[tuple[str, str]] = set()
    # v2/v3 path
    pkgs = data.get("packages")
    if isinstance(pkgs, dict):
        for key, info in pkgs.items():
            if not isinstance(info, dict):
                continue
            if key == "" or info.get("link"):
                continue
            # Key is "node_modules/<name>" or "node_modules/<scope>/<name>"
            name = info.get("name")
            if not name:
                # Derive from key
                if key.startswith("node_modules/"):
                    name = key[len("node_modules/"):]
                else:
                    name = key
            ver = info.get("version")
            if not name:
                continue
            tup = (name.lower(), ver or "")
            if tup in seen:
                continue
            seen.add(tup)
            deps.append(Dep(name=name.lower(), version=ver, ecosystem="npm",
                            manifest=path.name))
        if deps:
            return deps
    # v1 fallback
    def walk(tree: Any, depth: int = 0) -> None:
        if not isinstance(tree, dict):
            return
        for n, info in tree.items():
            if not isinstance(info, dict):
                continue
            ver = info.get("version")
            tup = (n.lower(), ver or "")
            if tup not in seen:
                seen.add(tup)
                deps.append(Dep(name=n.lower(), version=ver, ecosystem="npm",
                                manifest=path.name))
            walk(info.get("dependencies") or {}, depth + 1)
    walk(data.get("dependencies") or {})
    return deps


def parse_yarn_lock(path: Path) -> list[Dep]:
    """yarn.lock — handles both v1 (custom format) and v2+ Berry (YAML).

    v1 layout (no `__metadata` key, headers like `name@^X:` followed by
    `  version "Y.Y"`). v2+ layout is real YAML with `__metadata` block
    and `name@npm:^X` resolution keys. We try YAML first; if it fails
    (v1 isn't valid YAML), fall through to the v1 line parser.
    """
    try:
        text = path.read_text()
    except OSError:
        return []
    deps: list[Dep] = []
    seen: set[tuple[str, str]] = set()

    # v2+ Berry: real YAML
    try:
        import yaml  # type: ignore[import-untyped]
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "__metadata" in data:
            for resolution_key, info in data.items():
                if resolution_key == "__metadata":
                    continue
                if not isinstance(info, dict):
                    continue
                ver = info.get("version")
                # resolution_key looks like "name@npm:^1.2.3" or
                # "@scope/name@npm:^1.2.3, @scope/name@npm:^1.3"
                first_key = str(resolution_key).split(",")[0].strip()
                # Strip "@npm:" and trailing "@version-spec"
                if first_key.startswith("@"):
                    # scoped package, find second @
                    idx = first_key.find("@", 1)
                else:
                    idx = first_key.find("@")
                if idx > 0:
                    name = first_key[:idx]
                else:
                    name = first_key
                tup = (name.lower(), ver or "")
                if tup not in seen:
                    seen.add(tup)
                    deps.append(Dep(name=name.lower(), version=ver,
                                    ecosystem="npm", manifest=path.name))
            if deps:
                return deps
    except ImportError:
        pass
    except Exception:
        pass

    # v1 line parser
    current_names: list[str] = []
    for line in text.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" "):
            # Section header: "name@^X, name@~Y:" — strip trailing ':'
            header = stripped.rstrip(":").strip()
            current_names = []
            for part in header.split(","):
                part = part.strip().strip('"').strip("'")
                if not part:
                    continue
                if part.startswith("@"):
                    idx = part.find("@", 1)
                else:
                    idx = part.find("@")
                if idx > 0:
                    current_names.append(part[:idx])
                else:
                    current_names.append(part)
        elif line.lstrip().startswith("version "):
            ver = line.lstrip()[len("version "):].strip().strip('"').strip("'")
            for name in current_names:
                tup = (name.lower(), ver)
                if tup not in seen:
                    seen.add(tup)
                    deps.append(Dep(name=name.lower(), version=ver,
                                    ecosystem="npm", manifest=path.name))
            current_names = []
    return deps


def parse_pnpm_lock(path: Path) -> list[Dep]:
    """pnpm-lock.yaml — YAML. Keys under `packages:` look like
    `/<name>@<version>` or `/@<scope>/<name>@<version>`."""
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return []
    try:
        data = yaml.safe_load(path.read_text())
    except Exception:
        return []
    deps: list[Dep] = []
    seen: set[tuple[str, str]] = set()
    pkgs = (data or {}).get("packages") or {}
    for key in pkgs.keys():
        if not isinstance(key, str) or not key.startswith("/"):
            continue
        body = key[1:]  # strip leading /
        # Strip pnpm peer-dep tail "(name@x.y)" BEFORE @-splitting,
        # because the tail can contain @s that confuse rfind.
        if "(" in body:
            body = body[:body.index("(")]
        # Find the @ that separates name from version. For scoped pkgs
        # the leading @ at index 0 is part of the name; skip past it.
        if body.startswith("@"):
            sep = body.find("@", 1)
        else:
            sep = body.rfind("@")
        if sep <= 0:
            continue
        name = body[:sep]
        version = body[sep + 1:]
        if not name:
            continue
        tup = (name.lower(), version)
        if tup not in seen:
            seen.add(tup)
            deps.append(Dep(name=name.lower(), version=version, ecosystem="npm",
                            manifest=path.name))
    return deps


def parse_go_mod(path: Path) -> list[Dep]:
    """go.mod — Go module file. Reads the `require` block(s) for direct deps;
    module names are like 'github.com/user/repo'."""
    try:
        text = path.read_text()
    except OSError:
        return []
    deps: list[Dep] = []
    seen: set[tuple[str, str]] = set()
    in_require = False
    for raw in text.splitlines():
        line = raw.split("//", 1)[0].rstrip()  # drop comments
        if not line.strip():
            continue
        if line.strip() == "require (":
            in_require = True
            continue
        if in_require:
            if line.strip() == ")":
                in_require = False
                continue
            parts = line.strip().split()
            if len(parts) >= 2:
                name, ver = parts[0], parts[1]
                tup = (name.lower(), ver)
                if tup not in seen:
                    seen.add(tup)
                    deps.append(Dep(name=name.lower(), version=ver,
                                    ecosystem="golang", manifest=path.name))
        else:
            # Single-line `require name version`
            if line.startswith("require "):
                parts = line[len("require "):].split()
                if len(parts) >= 2:
                    name, ver = parts[0], parts[1]
                    tup = (name.lower(), ver)
                    if tup not in seen:
                        seen.add(tup)
                        deps.append(Dep(name=name.lower(), version=ver,
                                        ecosystem="golang", manifest=path.name))
    return deps


def parse_go_sum(path: Path) -> list[Dep]:
    """go.sum — checksum file with one or two entries per (name, version).
    Lines look like:
        github.com/foo/bar v1.2.3 h1:hash...
        github.com/foo/bar v1.2.3/go.mod h1:hash...
    Use module-line entries (no /go.mod suffix) for resolved deps.
    """
    try:
        text = path.read_text()
    except OSError:
        return []
    deps: list[Dep] = []
    seen: set[tuple[str, str]] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        name, ver = parts[0], parts[1]
        if ver.endswith("/go.mod"):
            continue
        tup = (name.lower(), ver)
        if tup not in seen:
            seen.add(tup)
            deps.append(Dep(name=name.lower(), version=ver,
                            ecosystem="golang", manifest=path.name))
    return deps


def parse_pipfile_lock(path: Path) -> list[Dep]:
    """Pipfile.lock (pipenv) — JSON with `default` + `develop` sections.
    Each entry: { "<name>": { "version": "==X.Y.Z", ... } }.
    """
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    deps: list[Dep] = []
    for section in ("default", "develop"):
        sec = data.get(section) or {}
        if not isinstance(sec, dict):
            continue
        for name, info in sec.items():
            if not isinstance(info, dict):
                continue
            ver_raw = info.get("version") or ""
            ver = ver_raw.lstrip("=").strip() or None
            deps.append(Dep(name=name.lower(), version=ver, ecosystem="pypi",
                            manifest=f"{path.name}#{section}"))
    return deps


def parse_conda_lock(path: Path) -> list[Dep]:
    """conda-lock.yml — `package:` is a list with platform-specific entries."""
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return []
    try:
        data = yaml.safe_load(path.read_text())
    except Exception:
        return []
    deps: list[Dep] = []
    seen: set[tuple[str, str, str]] = set()  # (name, version, ecosystem)
    for entry in (data or {}).get("package", []) or []:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        ver = entry.get("version")
        manager = (entry.get("manager") or "").lower()
        eco = "pypi" if manager == "pip" else "conda"
        if not name:
            continue
        tup = (name.lower(), ver or "", eco)
        if tup in seen:
            continue
        seen.add(tup)
        deps.append(Dep(name=name.lower(), version=ver, ecosystem=eco,
                        manifest=path.name))
    return deps


def parse_gemfile_lock(path: Path) -> list[Dep]:
    """Gemfile.lock — text format with GEM/PATH/GIT sections containing
    `specs:` blocks. Each spec line: `  name (version)` or `    name`."""
    try:
        text = path.read_text()
    except OSError:
        return []
    deps: list[Dep] = []
    seen: set[tuple[str, str]] = set()
    in_specs = False
    for raw in text.splitlines():
        if not raw.strip():
            in_specs = False
            continue
        if raw.strip() == "specs:":
            in_specs = True
            continue
        if in_specs:
            stripped = raw.strip()
            # Top-level spec lines start with 2 leading spaces in raw (4 spaces for sub-deps)
            indent = len(raw) - len(raw.lstrip(" "))
            if indent != 4:
                continue
            m = re.match(r"^([A-Za-z0-9_\-]+)\s*\(([^)]+)\)\s*$", stripped)
            if m:
                name, ver = m.group(1), m.group(2)
                tup = (name.lower(), ver)
                if tup not in seen:
                    seen.add(tup)
                    deps.append(Dep(name=name.lower(), version=ver,
                                    ecosystem="gem", manifest=path.name))
    return deps


def parse_composer_lock(path: Path) -> list[Dep]:
    """composer.lock (PHP/Composer) — JSON with `packages` + `packages-dev` arrays."""
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    deps: list[Dep] = []
    for section in ("packages", "packages-dev"):
        for pkg in data.get(section, []) or []:
            if not isinstance(pkg, dict):
                continue
            name = pkg.get("name")
            ver = pkg.get("version")
            if not name:
                continue
            deps.append(Dep(name=name.lower(), version=ver, ecosystem="composer",
                            manifest=f"{path.name}#{section}"))
    return deps


def parse_sbom_spdx_3(path: Path) -> list[Dep]:
    """SPDX 3.0 JSON-LD format. Different shape than 2.x — uses `@graph`
    array with element `type` discrimination.

    Each `software_Package` element has `name`, `software_packageVersion`,
    optional `externalIdentifier` containing purls.
    """
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    deps: list[Dep] = []
    elements = data.get("@graph") or data.get("elements") or []
    for el in elements:
        if not isinstance(el, dict):
            continue
        el_type = el.get("type") or ""
        if "software_Package" not in el_type and el_type != "Package":
            continue
        name = el.get("name") or ""
        version = el.get("software_packageVersion") or el.get("packageVersion") or None
        # externalIdentifier may have purls
        eco = "generic"
        for ext in el.get("externalIdentifier", []) or []:
            if not isinstance(ext, dict):
                continue
            ident = (ext.get("identifier") or "").lower()
            if ident.startswith("pkg:pypi/"):
                eco = "pypi"
                break
            if ident.startswith("pkg:conda/"):
                eco = "conda"
                break
            if ident.startswith("pkg:npm/"):
                eco = "npm"
                break
            if ident.startswith("pkg:golang/"):
                eco = "golang"
                break
        if not name:
            continue
        deps.append(Dep(name=name.lower(), version=version, ecosystem=eco,
                        manifest=path.name))
    return deps


def parse_pipfile(path: Path) -> list[Dep]:
    """Pipfile (pipenv manifest, no lock). TOML with [packages] + [dev-packages]."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[import-not-found,no-redef]
        except ImportError:
            return []
    try:
        data = tomllib.loads(path.read_text())
    except Exception:
        return []
    deps: list[Dep] = []
    for section in ("packages", "dev-packages"):
        sec = data.get(section) or {}
        if not isinstance(sec, dict):
            continue
        for n, v in sec.items():
            if isinstance(v, dict):
                ver = v.get("version")
                if ver and isinstance(ver, str):
                    ver = ver.lstrip("=").strip() or None
            elif isinstance(v, str):
                ver = v.lstrip("=*~^>< ").strip() or None
            else:
                ver = None
            deps.append(Dep(name=n.lower(), version=ver, ecosystem="pypi",
                            manifest=f"{path.name}#{section}"))
    return deps


def parse_requirements_in(path: Path) -> list[Dep]:
    """pip-tools requirements.in — same format as requirements.txt."""
    return parse_requirements_txt(path)


def _extract_images_recursive(node: Any, images: list[str]) -> None:
    """Walk a YAML/JSON tree and collect every `image: <str>` value seen.

    Handles k8s patterns (containers[].image), Helm patterns (image as
    string or {repository, tag}), Docker Compose, and arbitrary nested
    YAML.
    """
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "image" and isinstance(v, str) and v.strip():
                images.append(v.strip())
            elif k == "image" and isinstance(v, dict):
                # Helm-style {repository, tag, [registry]}
                repo = v.get("repository")
                tag = v.get("tag")
                registry = v.get("registry")
                if isinstance(repo, str):
                    img = repo
                    if isinstance(registry, str) and registry:
                        img = f"{registry}/{repo}"
                    if isinstance(tag, str) and tag:
                        img = f"{img}:{tag}"
                    images.append(img)
            else:
                _extract_images_recursive(v, images)
    elif isinstance(node, list):
        for item in node:
            _extract_images_recursive(item, images)


def parse_kubernetes_manifest(path: Path) -> list[Dep]:
    """Parse Kubernetes / OpenShift manifests for container image references.

    Handles multi-document YAML (---) and the standard kinds: Deployment,
    StatefulSet, DaemonSet, CronJob, Job, Pod, ReplicaSet, ReplicationController,
    plus generic walk for unrecognized kinds (covers Knative, Argo Rollouts,
    custom CRDs, etc.). Output Dep objects use ecosystem='oci-image' and
    name=<image-ref>; downstream `--image` mode can scan each.
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return []
    try:
        text = path.read_text()
    except OSError:
        return []
    images: list[str] = []
    try:
        for doc in yaml.safe_load_all(text):
            if not isinstance(doc, dict):
                continue
            kind = doc.get("kind") or ""
            if kind in (
                "Deployment", "StatefulSet", "DaemonSet", "CronJob", "Job",
                "Pod", "ReplicaSet", "ReplicationController",
                "Service", "Configuration", "Revision",  # Knative
                "Rollout",  # Argo Rollouts
            ) or doc.get("spec"):
                _extract_images_recursive(doc, images)
            else:
                # Still walk — covers CRDs that embed PodSpecs
                _extract_images_recursive(doc, images)
    except yaml.YAMLError:
        return []
    deps: list[Dep] = []
    seen: set[str] = set()
    for img in images:
        if img in seen:
            continue
        seen.add(img)
        # Split image reference into name + tag (or name + sha digest)
        name, version = img, None
        if "@sha256:" in img:
            name, _, digest = img.partition("@sha256:")
            version = f"sha256:{digest[:16]}"  # short digest
        elif ":" in img:
            # Last colon is tag separator (registry may have ports though)
            # Heuristic: a tag is at most ~64 chars without slashes
            after_colon = img.rsplit(":", 1)
            if len(after_colon) == 2 and "/" not in after_colon[1]:
                name, version = after_colon[0], after_colon[1]
        deps.append(Dep(
            name=name, version=version, ecosystem="oci-image",
            manifest=path.name, extras={"image_ref": img},
        ))
    return deps


def parse_helm_values(path: Path) -> list[Dep]:
    """Helm chart values.yaml — best-effort image extraction from any
    `image:` keys at any depth. Templated values (e.g., {{ .Values.X }})
    will produce noisy entries; use with `helm template` first for accuracy.
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return []
    try:
        data = yaml.safe_load(path.read_text())
    except Exception:
        return []
    images: list[str] = []
    _extract_images_recursive(data, images)
    deps: list[Dep] = []
    seen: set[str] = set()
    for img in images:
        if img in seen or "{{" in img:
            continue  # skip Jinja-templated placeholders
        seen.add(img)
        name, version = img, None
        if "@sha256:" in img:
            name, _, digest = img.partition("@sha256:")
            version = f"sha256:{digest[:16]}"
        elif ":" in img:
            after_colon = img.rsplit(":", 1)
            if len(after_colon) == 2 and "/" not in after_colon[1]:
                name, version = after_colon[0], after_colon[1]
        deps.append(Dep(
            name=name, version=version, ecosystem="oci-image",
            manifest=path.name, extras={"image_ref": img, "approximate": True},
        ))
    return deps


def parse_conda_meta_dir(env_path: Path) -> list[Dep]:
    """Read every conda-meta/*.json from a live conda env directory.

    Each file contains a single package's full metadata (name, version,
    channel, depends, ...). This is the most accurate snapshot of an
    installed conda env — exactly what `conda list --json` would emit
    but read directly from disk (offline-safe).

    Also picks up pip-installed packages by walking
    <env>/lib/python*/site-packages/*.dist-info/METADATA.
    """
    deps: list[Dep] = []
    seen: set[tuple[str, str, str]] = set()
    meta_dir = env_path / "conda-meta"
    if meta_dir.is_dir():
        for jf in meta_dir.glob("*.json"):
            try:
                data = json.loads(jf.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            name = data.get("name")
            ver = data.get("version")
            if not name:
                continue
            key = (name.lower(), ver or "", "conda")
            if key in seen:
                continue
            seen.add(key)
            deps.append(Dep(
                name=name.lower(), version=ver, ecosystem="conda",
                manifest=f"conda-env:{env_path.name}",
                extras={"channel": data.get("channel"),
                        "build": data.get("build")},
            ))
    # pip-installed packages inside the env
    deps.extend(_walk_dist_info(env_path, manifest_label=f"conda-env:{env_path.name}"))
    return deps


def _walk_dist_info(env_path: Path, manifest_label: str) -> list[Dep]:
    """Find lib/python*/site-packages/*.dist-info/METADATA and parse RFC822."""
    deps: list[Dep] = []
    seen: set[tuple[str, str]] = set()
    # Try common venv layouts: lib/python<X.Y>/site-packages, Lib/site-packages (Windows)
    candidates = list(env_path.glob("lib/python*/site-packages/*.dist-info/METADATA"))
    candidates += list(env_path.glob("Lib/site-packages/*.dist-info/METADATA"))
    candidates += list(env_path.glob("lib/python*/site-packages/*.egg-info/PKG-INFO"))
    for meta in candidates:
        name = None
        ver = None
        try:
            for line in meta.read_text(errors="replace").splitlines():
                if line.startswith("Name:"):
                    name = line[5:].strip()
                elif line.startswith("Version:"):
                    ver = line[8:].strip()
                elif line == "" and name and ver:
                    break  # blank line ends headers
        except OSError:
            continue
        if not name:
            continue
        key = (name.lower(), ver or "")
        if key in seen:
            continue
        seen.add(key)
        deps.append(Dep(
            name=name.lower(), version=ver, ecosystem="pypi",
            manifest=manifest_label,
        ))
    return deps


def parse_python_venv(env_path: Path) -> list[Dep]:
    """Live Python virtualenv (created by venv / virtualenv / uv / pipenv)."""
    return _walk_dist_info(env_path, manifest_label=f"venv:{env_path.name}")


# ── License compatibility check ─────────────────────────────────────────────
# Conservative compatibility matrix. The output is "license CAN be used in a
# project licensed as TARGET". This is decision support, not a legal opinion.
# Values:
#   'compatible'        — combine freely
#   'permissive'        — permissive, no obligations beyond attribution
#   'weak-copyleft'     — link OK; modifications must remain under the dep's license
#   'strong-copyleft'   — viral; downstream must be GPL/AGPL too
#   'attribution'       — needs notice file
#   'review'            — case-by-case (mixed / unknown / proprietary)
#   'incompatible'      — known to conflict with target

_LICENSE_FAMILY = {
    # Permissive
    "MIT":              "permissive",
    "BSD-2-Clause":     "permissive",
    "BSD-3-Clause":     "permissive",
    "ISC":              "permissive",
    "Apache-2.0":       "attribution",
    "0BSD":             "permissive",
    "Unlicense":        "permissive",
    "PSF-2.0":          "permissive",
    "Python-2.0":       "permissive",
    "CC0-1.0":          "permissive",
    "Zlib":             "permissive",
    # Weak copyleft
    "LGPL-2.1-only":    "weak-copyleft",
    "LGPL-2.1-or-later":"weak-copyleft",
    "LGPL-3.0-only":    "weak-copyleft",
    "LGPL-3.0-or-later":"weak-copyleft",
    "MPL-2.0":          "weak-copyleft",
    "EPL-1.0":          "weak-copyleft",
    "EPL-2.0":          "weak-copyleft",
    "CDDL-1.0":         "weak-copyleft",
    # Strong copyleft
    "GPL-2.0-only":     "strong-copyleft",
    "GPL-2.0-or-later": "strong-copyleft",
    "GPL-3.0-only":     "strong-copyleft",
    "GPL-3.0-or-later": "strong-copyleft",
    "AGPL-3.0-only":    "strong-copyleft",
    "AGPL-3.0-or-later":"strong-copyleft",
}


def _license_compatibility(dep_license: str | None,
                           target_license: str | None) -> str:
    """Classify one dep's license against the project's chosen target.

    Returns one of: 'compatible' / 'review' / 'incompatible' / 'unknown'.
    Conservative — anything not in the matrix is 'review' (manual decision).
    """
    if not dep_license:
        return "unknown"
    # Normalize: split on AND/OR (compound licenses), classify worst case
    raw = dep_license.replace("(", "").replace(")", "")
    parts = re.split(r"\s+(?:AND|OR|and|or)\s+", raw)
    fams = [_LICENSE_FAMILY.get(p.strip()) for p in parts]
    if all(f is None for f in fams):
        return "review"
    # Worst-case across an OR (we conservatively assume the strictest,
    # because the dep maintainer can pick which license applies to a given
    # downstream — but only the strict form is guaranteed-allowed)
    fam_priority = {
        None: 0, "permissive": 1, "attribution": 2, "weak-copyleft": 3,
        "strong-copyleft": 4,
    }
    worst_fam = None
    for f in fams:
        if fam_priority.get(f, 0) > fam_priority.get(worst_fam, 0):
            worst_fam = f
    if not target_license:
        # No target specified — surface the dep's family for review
        return f"review:{worst_fam or 'unknown'}"
    target_fam = _LICENSE_FAMILY.get(target_license)
    if target_fam is None:
        return f"review:{worst_fam or 'unknown'}"
    # Compatibility rules:
    #   - permissive/attribution targets accept anything but viral copyleft
    #     (which would force re-licensing)
    #   - weak-copyleft targets accept permissive + their own family + weaker;
    #     strong-copyleft is incompatible
    #   - strong-copyleft targets accept everything (their own viral terms cover)
    if worst_fam in ("permissive", "attribution"):
        return "compatible"
    if worst_fam == "weak-copyleft":
        if target_fam in ("permissive", "attribution"):
            return "incompatible"  # would trigger LGPL obligations
        return "compatible"
    if worst_fam == "strong-copyleft":
        if target_fam in ("strong-copyleft",):
            return "compatible"
        return "incompatible"
    return f"review:{worst_fam}"


def render_license_check(deps: list[Dep],
                         atlas_records: dict[str, dict[str, Any]],
                         target_license: str | None) -> str:
    """Tabulate license compatibility per dep against a target license."""
    out: list[str] = []
    out.append(f"  License compatibility check (target: "
               f"{target_license or '— (review-only mode)'})")
    out.append("  " + "─" * 110)
    out.append(f"  {'STATUS':<14} {'PACKAGE':<37} {'LICENSE':<25} ECOSYSTEM")
    out.append("  " + "─" * 110)
    counts: dict[str, int] = {}
    rows: list[tuple[str, str, str, str]] = []
    for d in deps:
        if d.ecosystem not in ("conda", "pypi"):
            continue
        atlas = atlas_records.get(d.name) or {}
        lic = atlas.get("conda_license")
        status = _license_compatibility(lic, target_license)
        # Normalize "review:..." into a single "review" bucket for counts
        bucket = status.split(":", 1)[0]
        counts[bucket] = counts.get(bucket, 0) + 1
        rows.append((status, d.name, lic or "—", d.ecosystem))
    # Sort: incompatible first, then review, then unknown, then compatible
    order = {"incompatible": 0, "review": 1, "unknown": 2, "compatible": 3}
    rows.sort(key=lambda r: (order.get(r[0].split(":", 1)[0], 9), r[1]))
    for status, name, lic, eco in rows[:40]:
        out.append(f"  {status:<14} {name[:36]:<37} {lic[:24]:<25} {eco}")
    if len(rows) > 40:
        out.append(f"  ... and {len(rows) - 40} more")
    out.append("")
    out.append(f"  Counts: {counts}")
    return "\n".join(out) + "\n"


def _dt_iso_now() -> str:
    """ISO 8601 timestamp for SPDX annotations."""
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_atlas_vuln_summary(deps: list[Dep],
                              _atlas_records: dict[str, dict[str, Any]]
                              ) -> dict[str, dict[str, int]]:
    """Pull cached Phase G counts from cf_atlas (no vdb env required).

    Returns {dep_name: {total, critical, high, kev, scanned_at}}.
    Used by --enrich-vulns-from-atlas to annotate SBOMs without needing
    the heavy vuln-db env.
    """
    if not ATLAS_DB.exists():
        return {}
    out: dict[str, dict[str, int]] = {}
    try:
        conn = sqlite3.connect(ATLAS_DB)
    except sqlite3.Error:
        return {}
    names = [d.name for d in deps if d.ecosystem in ("conda", "pypi")]
    if not names:
        return {}
    placeholders = ",".join("?" for _ in names)
    sql = (
        "SELECT conda_name, vuln_total, vuln_critical_affecting_current, "
        "       vuln_high_affecting_current, vuln_kev_affecting_current, "
        "       vdb_scanned_at "
        f"FROM packages WHERE conda_name IN ({placeholders})"
    )
    for r in conn.execute(sql, names):
        if r[5] is None:
            continue
        out[r[0]] = {
            "total": r[1] or 0,
            "critical_affecting_current": r[2] or 0,
            "high_affecting_current": r[3] or 0,
            "kev_affecting_current": r[4] or 0,
            "scanned_at": r[5],
        }
    return out


def _images_from_yaml_text(text: str, manifest_label: str) -> list[Dep]:
    """Render-multi-document YAML text → Dep list with ecosystem='oci-image'."""
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return []
    images: list[str] = []
    try:
        for doc in yaml.safe_load_all(text):
            _extract_images_recursive(doc, images)
    except yaml.YAMLError:
        return []
    deps: list[Dep] = []
    seen: set[str] = set()
    for img in images:
        if img in seen or "{{" in img:
            continue
        seen.add(img)
        name, version = img, None
        if "@sha256:" in img:
            name, _, digest = img.partition("@sha256:")
            version = f"sha256:{digest[:16]}"
        elif ":" in img:
            after_colon = img.rsplit(":", 1)
            if len(after_colon) == 2 and "/" not in after_colon[1]:
                name, version = after_colon[0], after_colon[1]
        deps.append(Dep(
            name=name, version=version, ecosystem="oci-image",
            manifest=manifest_label, extras={"image_ref": img},
        ))
    return deps


def oci_manifest_probe(image_ref: str
                        ) -> tuple[dict[str, Any] | None, str | None]:
    """Direct OCI Distribution v2 manifest probe — no syft/trivy needed.

    Tag verification + digest pinning for air-gapped scenarios. Reads
    ONLY the manifest (no layers, no SBOM extraction). Useful for:
      - confirming a tag exists in a registry without pulling
      - getting the SHA256 digest for a tag-pin → digest-pin migration
      - listing platforms in a multi-arch manifest list

    Auth: anonymous registries work directly. Authenticated registries
    (private GHCR, ECR, ACR, Artifactory) need credentials in
    `~/.docker/config.json` OR the env var `OCI_REGISTRY_TOKEN`.
    Falls back to a Bearer token challenge dance for ghcr.io / Docker Hub.

    Returns the parsed manifest dict on success.
    """
    from urllib.parse import urlparse, quote
    if "://" not in image_ref:
        # Default to docker.io for bare names like "alpine:3.19"
        if "/" not in image_ref or image_ref.split("/", 1)[0] not in (
            "ghcr.io", "quay.io", "gcr.io", "registry.k8s.io",
            "public.ecr.aws", "mcr.microsoft.com", "registry.gitlab.com",
        ) and "." not in image_ref.split("/", 1)[0]:
            registry = "registry-1.docker.io"
            repo = image_ref
            if "/" not in repo:
                repo = f"library/{repo}"
            tag_or_digest = "latest"
            if ":" in repo:
                repo, tag_or_digest = repo.rsplit(":", 1)
        else:
            registry, _, rest = image_ref.partition("/")
            repo = rest
            tag_or_digest = "latest"
            if "@sha256:" in repo:
                repo, _, dig = repo.partition("@sha256:")
                tag_or_digest = f"sha256:{dig}"
            elif ":" in repo:
                repo, tag_or_digest = repo.rsplit(":", 1)
    else:
        parsed = urlparse(image_ref)
        registry = parsed.netloc
        repo = parsed.path.lstrip("/")
        tag_or_digest = "latest"
        if ":" in repo:
            repo, tag_or_digest = repo.rsplit(":", 1)
    base = f"https://{registry}/v2/{quote(repo, safe='/')}"
    url = f"{base}/manifests/{tag_or_digest}"
    headers = {
        "Accept":
            "application/vnd.oci.image.manifest.v1+json,"
            "application/vnd.oci.image.index.v1+json,"
            "application/vnd.docker.distribution.manifest.v2+json,"
            "application/vnd.docker.distribution.manifest.list.v2+json",
    }
    tok = os.environ.get("OCI_REGISTRY_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    try:
        with urllib.request.urlopen(_make_req(url, extra_headers=headers),
                                     timeout=20) as resp:
            return (json.load(resp), None)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            # Bearer challenge — parse Www-Authenticate, fetch token,
            # retry. Common for ghcr.io and docker.io.
            challenge = e.headers.get("Www-Authenticate") or ""
            params = dict(re.findall(r'(\w+)="([^"]+)"', challenge))
            realm = params.get("realm")
            service = params.get("service")
            scope = params.get("scope") or f"repository:{repo}:pull"
            if not realm:
                return (None, f"HTTP 401 with no auth challenge realm")
            tok_url = f"{realm}?service={quote(service or registry)}&scope={quote(scope)}"
            try:
                with urllib.request.urlopen(_make_req(tok_url),
                                             timeout=20) as tresp:
                    tdata = json.load(tresp)
                bearer = tdata.get("token") or tdata.get("access_token")
            except Exception as te:
                return (None,
                        f"failed Bearer token fetch: "
                        f"{type(te).__name__}: {te}")
            if not bearer:
                return (None, "Bearer token endpoint returned no token")
            headers["Authorization"] = f"Bearer {bearer}"
            try:
                with urllib.request.urlopen(_make_req(url, extra_headers=headers),
                                             timeout=20) as resp:
                    return (json.load(resp), None)
            except Exception as re2:
                return (None,
                        f"manifest fetch after auth failed: "
                        f"{type(re2).__name__}: {re2}")
        return (None, f"HTTP {e.code}: {e.reason}")
    except Exception as e:
        return (None, f"{type(e).__name__}: {str(e)[:200]}")


def kubectl_pod_images(context: str | None = None,
                       namespace: str | None = None
                       ) -> tuple[list[Dep] | None, str | None]:
    """Live cluster scan: `kubectl get pods -A -o json` (or one ns).

    Auto-skips if kubectl is unavailable or the cluster is unreachable.
    Returns Dep list with ecosystem='oci-image'; downstream `--image` mode
    can be chained to pull each.
    """
    kubectl = shutil.which("kubectl")
    if not kubectl:
        return (None, "kubectl not installed")
    cmd = [kubectl, "get", "pods", "-o", "json"]
    if namespace:
        cmd.extend(["-n", namespace])
    else:
        cmd.append("--all-namespaces")
    if context:
        cmd.extend(["--context", context])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return (None, "kubectl timed out (>60s)")
    if result.returncode != 0:
        return (None, f"kubectl failed: {result.stderr[:200]}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return (None, "kubectl output not parseable JSON")
    images: list[str] = []
    _extract_images_recursive(data, images)
    deps: list[Dep] = []
    seen: set[str] = set()
    label = f"kubectl({context or 'current'}/{namespace or 'all-ns'})"
    for img in images:
        if img in seen:
            continue
        seen.add(img)
        name, version = img, None
        if "@sha256:" in img:
            name, _, digest = img.partition("@sha256:")
            version = f"sha256:{digest[:16]}"
        elif ":" in img:
            after_colon = img.rsplit(":", 1)
            if len(after_colon) == 2 and "/" not in after_colon[1]:
                name, version = after_colon[0], after_colon[1]
        deps.append(Dep(name=name, version=version, ecosystem="oci-image",
                        manifest=label, extras={"image_ref": img}))
    return (deps, None)


def helm_template_images(chart_path: Path,
                          values: list[Path] | None = None
                          ) -> tuple[list[Dep] | None, str | None]:
    """Render a Helm chart via `helm template` and extract image refs.

    Equivalent to invoking the user's normal helm chart deploy with default
    values + any user-provided values files. More accurate than scanning
    raw values.yaml because templated `{{ … }}` values get resolved.
    """
    helm = shutil.which("helm")
    if not helm:
        return (None, "helm not installed")
    cmd = [helm, "template", str(chart_path)]
    if values:
        for v in values:
            cmd.extend(["-f", str(v)])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return (None, "helm template timed out (>120s)")
    if result.returncode != 0:
        return (None, f"helm template failed: {result.stderr[:300]}")
    deps = _images_from_yaml_text(result.stdout, f"helm({chart_path})")
    return (deps, None)


def argo_application_images(cr_path: Path
                             ) -> tuple[list[Dep] | None, str | None]:
    """Resolve an Argo CD `Application` CR → image list.

    Reads `spec.source.{repoURL, path, targetRevision, helm{}, kustomize{}}`.
    Strategy:
      - If `helm.values` or `helm.valueFiles` are inline: render whatever
        chart is present *locally* via `helm template`. Remote `repoURL`
        cloning is out of scope (no git fetcher inside scan-project).
      - If `kustomize` is set or path looks like a kustomize overlay:
        run `kustomize build` against the local path.
      - Otherwise: parse the local manifests directly via
        parse_kubernetes_manifest.
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return (None, "PyYAML not installed")
    try:
        cr = yaml.safe_load(cr_path.read_text())
    except (OSError, yaml.YAMLError) as e:
        return (None, f"failed to read CR: {e}")
    if not isinstance(cr, dict) or cr.get("kind") != "Application":
        return (None, "not an Argo Application CR")
    spec = (cr or {}).get("spec") or {}
    src = spec.get("source") or {}
    if not isinstance(src, dict):
        return (None, "spec.source missing")
    repo_url = src.get("repoURL") or ""
    path_in_repo = src.get("path") or ""
    helm = src.get("helm") or {}
    kustomize = src.get("kustomize") or {}
    # Best-effort local resolution: assume the repo is already cloned in
    # the project's working tree at `<cwd>/<path>` or alongside the CR
    # (common GitOps monorepo layout).
    candidate_paths = [
        cr_path.parent / path_in_repo if path_in_repo else cr_path.parent,
        Path.cwd() / path_in_repo if path_in_repo else Path.cwd(),
    ]
    local_path: Path | None = None
    for p in candidate_paths:
        if p.is_dir():
            local_path = p
            break
    if local_path is None and repo_url:
        # Auto-clone fallback: if a repoURL is set and we can find git, clone
        # to a tmpdir and use that. Caller can keep the clone via
        # --keep-clone if they want to inspect.
        git = shutil.which("git")
        if git:
            tmpdir = Path(tempfile.mkdtemp(prefix="argo-clone-"))
            target_rev = src.get("targetRevision") or "HEAD"
            try:
                subprocess.run(
                    [git, "clone", "--depth", "1", repo_url, str(tmpdir)],
                    check=True, capture_output=True, timeout=120,
                )
                if target_rev != "HEAD":
                    subprocess.run(
                        [git, "-C", str(tmpdir), "fetch", "--depth", "1",
                         "origin", target_rev],
                        check=False, capture_output=True, timeout=60,
                    )
                    subprocess.run(
                        [git, "-C", str(tmpdir), "checkout", target_rev],
                        check=False, capture_output=True, timeout=30,
                    )
                local_path = (tmpdir / path_in_repo) if path_in_repo else tmpdir
                if not local_path.is_dir():
                    return (None,
                            f"cloned {repo_url} but path '{path_in_repo}' not found in checkout")
            except subprocess.CalledProcessError as e:
                shutil.rmtree(tmpdir, ignore_errors=True)
                return (None, f"git clone {repo_url} failed: {e.stderr[:200]}")
            except subprocess.TimeoutExpired:
                shutil.rmtree(tmpdir, ignore_errors=True)
                return (None, f"git clone {repo_url} timed out")
    if local_path is None:
        return (None,
                f"could not find local path for Argo source "
                f"(repoURL={repo_url}, path={path_in_repo}); "
                f"clone the repo and re-run from the chart directory, "
                f"or install git so auto-clone can run")
    # Pick handler
    if helm or any(local_path.glob("Chart.yaml")):
        values_files: list[Path] = []
        for vf in (helm.get("valueFiles") or []):
            cand = local_path / vf
            if cand.is_file():
                values_files.append(cand)
        return helm_template_images(local_path, values_files)
    if kustomize or any(local_path.glob("kustomization.yaml")) \
            or any(local_path.glob("kustomization.yml")):
        return kustomize_build_images(local_path)
    # Plain manifests
    deps: list[Dep] = []
    for ext in ("*.yaml", "*.yml"):
        for path in local_path.rglob(ext):
            if any(part in _SKIP_PATH_PARTS for part in path.parts):
                continue
            deps.extend(parse_kubernetes_manifest(path))
    if not deps:
        return (None, f"no manifests found under {local_path}")
    return (deps, None)


def flux_cr_images(cr_path: Path) -> tuple[list[Dep] | None, str | None]:
    """Resolve a Flux CD `HelmRelease` or `Kustomization` CR → image list.

    HelmRelease: reads `spec.chart.spec.{chart, sourceRef}` + `spec.values`,
    runs `helm template <local-chart-path>` if a local copy is reachable.

    Kustomization: reads `spec.path` and runs `kustomize build` against it.
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return (None, "PyYAML not installed")
    try:
        cr = yaml.safe_load(cr_path.read_text())
    except (OSError, yaml.YAMLError) as e:
        return (None, f"failed to read CR: {e}")
    if not isinstance(cr, dict):
        return (None, "CR is not a YAML mapping")
    kind = cr.get("kind") or ""
    spec = cr.get("spec") or {}
    if kind == "HelmRelease":
        chart_spec = (spec.get("chart") or {}).get("spec") or {}
        chart = chart_spec.get("chart") or ""
        # Local resolution: same as Argo — best-effort
        candidates = [
            cr_path.parent / chart if chart else cr_path.parent,
            Path.cwd() / chart if chart else Path.cwd(),
        ]
        local: Path | None = next((p for p in candidates if p.is_dir()), None)
        if local is None:
            return (None,
                    f"could not find local Helm chart path for "
                    f"HelmRelease (chart={chart})")
        # Inline values: write them out and pass to helm template
        values = spec.get("values")
        values_files: list[Path] = []
        if values is not None:
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            )
            yaml.safe_dump(values, tmp)
            tmp.close()
            values_files.append(Path(tmp.name))
        try:
            return helm_template_images(local, values_files)
        finally:
            for f in values_files:
                f.unlink(missing_ok=True)
    if kind == "Kustomization":
        path = spec.get("path") or "."
        candidates = [cr_path.parent / path, Path.cwd() / path]
        local = next((p for p in candidates if p.is_dir()), None)
        if local is None:
            return (None,
                    f"could not find local Kustomization path (path={path})")
        return kustomize_build_images(local)
    return (None, f"unsupported Flux kind: {kind}")


def kustomize_build_images(kust_dir: Path
                            ) -> tuple[list[Dep] | None, str | None]:
    """Render a Kustomize overlay via `kustomize build` and extract images."""
    kust = shutil.which("kustomize") or shutil.which("kubectl")
    if not kust:
        return (None, "neither kustomize nor kubectl is installed")
    if "kubectl" in kust:
        cmd = [kust, "kustomize", str(kust_dir)]
    else:
        cmd = [kust, "build", str(kust_dir)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return (None, "kustomize timed out (>60s)")
    if result.returncode != 0:
        return (None, f"kustomize failed: {result.stderr[:300]}")
    deps = _images_from_yaml_text(result.stdout, f"kustomize({kust_dir})")
    return (deps, None)


def parse_sbom_cyclonedx_xml(path: Path) -> list[Dep]:
    """CycloneDX XML 1.4+. Built-in xml.etree — no external deps.

    Layout: <bom><components><component type="library">...
    Each component has <name>, <version>, optional <purl>.
    Namespace-agnostic: matches `{*}name` to handle any CycloneDX schema
    namespace (1.4 / 1.5 / 1.6 differ in the URL).
    """
    try:
        import xml.etree.ElementTree as ET
    except ImportError:
        return []
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError):
        return []
    root = tree.getroot()
    deps: list[Dep] = []
    seen: set[tuple[str, str]] = set()

    def _localname(elem: ET.Element, tag: str) -> str | None:
        # Find the first descendant with localname == tag, regardless of ns.
        for child in elem.iter():
            ctag = child.tag
            local = ctag.split("}", 1)[-1] if "}" in ctag else ctag
            if local == tag:
                return (child.text or "").strip() or None
        return None

    # Find <component> elements anywhere under root
    for comp in root.iter():
        local = comp.tag.split("}", 1)[-1] if "}" in comp.tag else comp.tag
        if local != "component":
            continue
        name = _localname(comp, "name")
        version = _localname(comp, "version")
        purl = _localname(comp, "purl") or ""
        if not name:
            continue
        eco = "generic"
        if purl.startswith("pkg:pypi/"):
            eco = "pypi"
        elif purl.startswith("pkg:conda/"):
            eco = "conda"
        elif purl.startswith("pkg:npm/"):
            eco = "npm"
        elif purl.startswith("pkg:cargo/"):
            eco = "cargo"
        elif purl.startswith("pkg:maven/"):
            eco = "maven"
        elif purl.startswith("pkg:gem/"):
            eco = "gem"
        elif purl.startswith("pkg:composer/"):
            eco = "composer"
        elif purl.startswith("pkg:golang/"):
            eco = "golang"
        elif purl.startswith("pkg:nuget/"):
            eco = "nuget"
        elif purl.startswith("pkg:deb/"):
            eco = "apt"
        elif purl.startswith("pkg:rpm/"):
            eco = "dnf"
        elif purl.startswith("pkg:apk/"):
            eco = "apk"
        key = (name.lower(), version or "")
        if key in seen:
            continue
        seen.add(key)
        deps.append(Dep(
            name=name.lower(), version=version, ecosystem=eco,
            manifest=path.name, extras={"purl": purl},
        ))
    return deps


def parse_sbom_spdx_tagvalue(path: Path) -> list[Dep]:
    """SPDX 2.x tag-value format — plain text with `Key: Value` pairs.

    Each `PackageName:` line begins a new package block; `PackageVersion:`
    + `ExternalRef:` (purl) follow. Tag-value is the original SPDX format,
    much rarer than JSON but still produced by some scanners.
    """
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []
    deps: list[Dep] = []
    seen: set[tuple[str, str]] = set()
    cur_name: str | None = None
    cur_version: str | None = None
    cur_purl: str | None = None

    def _flush() -> None:
        nonlocal cur_name, cur_version, cur_purl
        if cur_name:
            eco = "generic"
            if cur_purl:
                if cur_purl.startswith("pkg:pypi/"): eco = "pypi"
                elif cur_purl.startswith("pkg:conda/"): eco = "conda"
                elif cur_purl.startswith("pkg:npm/"): eco = "npm"
                elif cur_purl.startswith("pkg:cargo/"): eco = "cargo"
                elif cur_purl.startswith("pkg:maven/"): eco = "maven"
                elif cur_purl.startswith("pkg:gem/"): eco = "gem"
                elif cur_purl.startswith("pkg:composer/"): eco = "composer"
                elif cur_purl.startswith("pkg:golang/"): eco = "golang"
                elif cur_purl.startswith("pkg:nuget/"): eco = "nuget"
                elif cur_purl.startswith("pkg:deb/"): eco = "apt"
                elif cur_purl.startswith("pkg:rpm/"): eco = "dnf"
                elif cur_purl.startswith("pkg:apk/"): eco = "apk"
            key = (cur_name.lower(), cur_version or "")
            if key not in seen:
                seen.add(key)
                deps.append(Dep(
                    name=cur_name.lower(), version=cur_version,
                    ecosystem=eco, manifest=path.name,
                    extras={"purl": cur_purl} if cur_purl else {},
                ))
        cur_name = cur_version = cur_purl = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("PackageName:"):
            _flush()
            cur_name = line[len("PackageName:"):].strip()
        elif line.startswith("PackageVersion:") and cur_name:
            cur_version = line[len("PackageVersion:"):].strip() or None
        elif line.startswith("ExternalRef:") and cur_name:
            # Format: ExternalRef: PACKAGE_MANAGER purl pkg:pypi/foo@1.2.3
            payload = line[len("ExternalRef:"):].strip().split()
            for token in payload:
                if token.startswith("pkg:"):
                    cur_purl = token
                    break
    _flush()
    return deps


def parse_sbom_relationships(path: Path) -> dict[str, list[str]]:
    """Parse the dependency tree from a CycloneDX or SPDX 2.x JSON SBOM.

    Returns {ref_or_id: [child_ref_or_id, …]} representing the
    parent-→-child relationship graph. CycloneDX uses
    `dependencies[].{ref, dependsOn[]}`; SPDX uses
    `relationships[].{spdxElementId, relatedSpdxElement, relationshipType}`
    (we treat DEPENDS_ON / DEPENDS_FOR / CONTAINS as parent→child).

    Used by the renderer to show transitive dep counts when an imported
    SBOM carries relationship info (most syft / trivy / OWASP DT exports do).
    """
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[str, list[str]] = {}
    # CycloneDX
    for d in data.get("dependencies", []) or []:
        if not isinstance(d, dict):
            continue
        ref = d.get("ref")
        if not ref:
            continue
        children = d.get("dependsOn") or []
        if isinstance(children, list):
            out[ref] = [str(c) for c in children if c]
    if out:
        return out
    # SPDX 2.x
    for r in data.get("relationships", []) or []:
        if not isinstance(r, dict):
            continue
        rtype = (r.get("relationshipType") or "").upper()
        if rtype not in ("DEPENDS_ON", "DEPENDS_FOR", "CONTAINS"):
            continue
        parent = r.get("spdxElementId")
        child = r.get("relatedSpdxElement")
        if not parent or not child:
            continue
        out.setdefault(parent, []).append(child)
    return out


def parse_vex_cyclonedx(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Read VEX statements from a CycloneDX 1.5+ SBOM.

    Returns {component_ref: [{cve_id, state, justification, response, detail}]}.
    `state` ∈ {'exploitable', 'not_affected', 'false_positive', 'in_triage',
              'resolved', 'resolved_with_pedigree'}.

    The caller can use this to suppress CVEs marked `not_affected` /
    `false_positive` from the final risk view, implementing
    Vulnerability-Exploitability eXchange filtering.
    """
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for vuln in data.get("vulnerabilities", []) or []:
        if not isinstance(vuln, dict):
            continue
        cve_id = vuln.get("id") or ""
        analysis = vuln.get("analysis") or {}
        state = analysis.get("state")
        if not state:
            continue
        statement = {
            "cve_id": cve_id,
            "state": state,
            "justification": analysis.get("justification"),
            "response": analysis.get("response"),
            "detail": analysis.get("detail"),
        }
        # affects[] points back to bom-refs of components
        for affect in vuln.get("affects", []) or []:
            ref = (affect or {}).get("ref")
            if not ref:
                continue
            out.setdefault(ref, []).append(statement)
    return out


def parse_syft_json(path: Path) -> list[Dep]:
    """Native syft JSON — different shape than CycloneDX.

    Layout: top-level `artifacts[]` with each entry `{type, name, version,
    purl?, metadata, ...}`. The `type` field maps to ecosystem (python →
    pypi, npm → npm, deb → apt, rpm → dnf, apk → apk, go-module → golang,
    rust-crate → cargo, etc.).
    """
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, dict) or "artifacts" not in data:
        return []
    type_to_eco = {
        "python": "pypi", "python-package": "pypi",
        "npm": "npm", "npm-package": "npm",
        "go-module": "golang", "go-package": "golang",
        "rust-crate": "cargo",
        "java-archive": "maven", "java-package": "maven",
        "deb": "apt", "deb-package": "apt",
        "rpm": "dnf", "rpm-package": "dnf",
        "apk": "apk", "apk-package": "apk",
        "gem": "gem", "ruby-gem": "gem",
        "php-composer": "composer", "composer": "composer",
        "conda": "conda", "conda-package": "conda",
        "nuget": "nuget", "dotnet": "nuget",
    }
    deps: list[Dep] = []
    seen: set[tuple[str, str, str]] = set()
    for art in data.get("artifacts", []) or []:
        if not isinstance(art, dict):
            continue
        name = art.get("name") or ""
        ver = art.get("version") or None
        atype = (art.get("type") or "").lower()
        eco = type_to_eco.get(atype, "generic")
        # purl gives a more reliable ecosystem signal when type is missing
        purl = art.get("purl") or ""
        if eco == "generic" and isinstance(purl, str):
            for prefix, e in (
                ("pkg:pypi/", "pypi"), ("pkg:npm/", "npm"),
                ("pkg:conda/", "conda"), ("pkg:deb/", "apt"),
                ("pkg:rpm/", "dnf"), ("pkg:apk/", "apk"),
                ("pkg:cargo/", "cargo"), ("pkg:maven/", "maven"),
                ("pkg:gem/", "gem"), ("pkg:composer/", "composer"),
                ("pkg:golang/", "golang"), ("pkg:nuget/", "nuget"),
            ):
                if purl.startswith(prefix):
                    eco = e
                    break
        if not name:
            continue
        key = (name.lower(), ver or "", eco)
        if key in seen:
            continue
        seen.add(key)
        deps.append(Dep(
            name=name.lower(), version=ver, ecosystem=eco,
            manifest=path.name, extras={"purl": purl, "syft_id": art.get("id")},
        ))
    return deps


def parse_trivy_json(path: Path) -> list[Dep]:
    """Native trivy JSON — different shape than CycloneDX.

    Layout: top-level `Results[]` with each entry `{Target, Class, Type,
    Packages?, Vulnerabilities?}`. We extract from `Packages` (when
    present) using `Type` for ecosystem mapping.
    """
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, dict):
        return []
    type_to_eco = {
        "pip": "pypi", "python-pkg": "pypi",
        "npm": "npm", "node-pkg": "npm", "yarn": "npm", "pnpm": "npm",
        "gomod": "golang",
        "cargo": "cargo",
        "jar": "maven", "pom": "maven",
        "debian": "apt", "ubuntu": "apt",
        "redhat": "dnf", "centos": "dnf", "amazon": "dnf", "rocky": "dnf",
        "alpine": "apk",
        "rubygems": "gem", "bundler": "gem",
        "composer": "composer", "composer-installed.json": "composer",
        "conda-pkg": "conda",
        "nuget": "nuget", "dotnet-deps": "nuget",
    }
    deps: list[Dep] = []
    seen: set[tuple[str, str, str]] = set()
    for result in data.get("Results", []) or []:
        if not isinstance(result, dict):
            continue
        atype = (result.get("Type") or "").lower()
        eco = type_to_eco.get(atype, "generic")
        for pkg in result.get("Packages", []) or []:
            if not isinstance(pkg, dict):
                continue
            name = pkg.get("Name") or pkg.get("PkgName") or ""
            ver = pkg.get("Version") or pkg.get("InstalledVersion") or None
            if not name:
                continue
            key = (name.lower(), ver or "", eco)
            if key in seen:
                continue
            seen.add(key)
            deps.append(Dep(
                name=name.lower(), version=ver, ecosystem=eco,
                manifest=f"{path.name}#{result.get('Target', '?')}",
            ))
    return deps


def parse_environment_yml(path: Path) -> list[Dep]:
    try:
        import yaml
    except ImportError:
        return []
    try:
        data = yaml.safe_load(path.read_text())
    except Exception:
        return []
    deps: list[Dep] = []
    for entry in (data or {}).get("dependencies", []) or []:
        if isinstance(entry, str):
            m = re.match(r"^([A-Za-z0-9._-]+)(?:\s*[=<>~!]=?\s*([0-9][^,;\s]*))?", entry)
            if m:
                deps.append(Dep(name=m.group(1).lower(), version=m.group(2),
                                ecosystem="conda", manifest=path.name))
        elif isinstance(entry, dict) and "pip" in entry:
            for spec in entry.get("pip") or []:
                if isinstance(spec, str):
                    m = re.match(r"^([A-Za-z0-9._-]+)(?:\s*[=<>~!]=?\s*([0-9][^,;\s]*))?", spec)
                    if m:
                        deps.append(Dep(name=m.group(1).lower(), version=m.group(2),
                                        ecosystem="pypi", manifest=f"{path.name}#pip"))
    return deps


def parse_containerfile(path: Path) -> tuple[list[Dep], list[str]]:
    """Parse Containerfile/Dockerfile for FROM image + RUN install lines.

    Returns (deps, base_images). base_images is a list of "image:tag" strings.
    """
    deps: list[Dep] = []
    base_images: list[str] = []
    try:
        text = path.read_text()
    except Exception:
        return (deps, base_images)
    # Multi-stage support: FROM <image> AS <stage> registers the stage,
    # and COPY --from=<stage|n|external-image> references can pull in
    # external image bases that aren't otherwise visible.
    stage_to_image: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # FROM image:tag [AS stage]
        if line.upper().startswith("FROM "):
            parts = line.split()
            if len(parts) >= 2:
                image = parts[1]
                base_images.append(image)
                if len(parts) >= 4 and parts[2].upper() == "AS":
                    stage_to_image[parts[3]] = image
            continue
        # COPY --from=<ref> — only adds new attribution when ref is an
        # external image (not a numeric index nor a known stage name).
        if line.upper().startswith("COPY ") and "--from=" in line:
            m = re.search(r"--from=([A-Za-z0-9_.:/\-]+)", line)
            if m:
                ref = m.group(1)
                if (not ref.isdigit() and ref not in stage_to_image
                        and ref not in base_images):
                    base_images.append(ref)
            continue
        # RUN apt-get install -y pkg1 pkg2  (also handle 'apt install', dnf, yum, apk, pip)
        if line.upper().startswith("RUN "):
            cmd = line[4:].strip()
            # Match install commands
            for installer, eco in (
                (r"apt(?:-get)?\s+install\s+(?:-[a-zA-Z]+\s+)*", "apt"),
                (r"dnf\s+install\s+(?:-[a-zA-Z]+\s+)*", "dnf"),
                (r"yum\s+install\s+(?:-[a-zA-Z]+\s+)*", "yum"),
                (r"apk\s+add\s+(?:-[a-zA-Z]+\s+)*", "apk"),
                (r"pip3?\s+install\s+(?:-[a-zA-Z]+\s+)*", "pypi"),
                (r"uv\s+pip\s+install\s+", "pypi"),
            ):
                for m in re.finditer(installer + r"([^\\\n&|;]+)", cmd):
                    pkgs_str = m.group(1).strip()
                    for pkg in pkgs_str.split():
                        pkg = pkg.strip().rstrip(",")
                        if pkg.startswith("-") or "=" in pkg:
                            # version-pinned; split
                            n_ver = re.match(r"^([A-Za-z0-9._-]+)(?:[=<>~!]+([\d][^,;\s]*))?", pkg)
                        else:
                            n_ver = re.match(r"^([A-Za-z0-9._-]+)$", pkg)
                        if n_ver:
                            ver = n_ver.group(2) if n_ver.lastindex and n_ver.lastindex >= 2 else None
                            deps.append(Dep(
                                name=n_ver.group(1).lower(),
                                version=ver,
                                ecosystem=eco, manifest=path.name,
                            ))
    return (deps, base_images)


# ── Vuln lookup ─────────────────────────────────────────────────────────────

def lookup_vulns(
    deps: list[Dep],
    atlas_records: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], str | None]:
    """Returns (vulns_by_purl, error). Each vuln is a normalized dict with id/severity/score/cwe/desc.

    For conda deps, also probes the pypi-equivalent purl since vdb indexes upstream
    advisories by `pkg:pypi/...`, not `pkg:conda/...`. The pypi name comes from atlas
    when known, otherwise falls back to the conda name (most upstream packages match).
    """
    try:
        from vdb.lib import search as vdb_search  # type: ignore[import-untyped]
    except ImportError:
        return ({}, "vdb library not installed (run from `vuln-db` env)")

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from detail_cf_atlas import _extract_vuln_fields  # type: ignore[import-not-found]
    except ImportError:
        return ({}, "detail_cf_atlas._extract_vuln_fields missing")

    atlas_records = atlas_records or {}
    vulns_by_purl: dict[str, list[dict[str, Any]]] = {}
    seen_dep_keys: set[str] = set()
    for dep in deps:
        primary_purl = dep.purl()
        if not primary_purl:
            continue
        dep_key = f"{dep.ecosystem}:{dep.name}@{dep.version}"
        if dep_key in seen_dep_keys:
            continue
        seen_dep_keys.add(dep_key)

        purls_to_probe = [primary_purl]
        if dep.ecosystem == "conda":
            atlas_key = f"conda:{dep.name}"
            atlas = atlas_records.get(atlas_key) or {}
            pypi_name = atlas.get("pypi_name") or dep.name
            pypi_purl = (
                f"pkg:pypi/{pypi_name}@{dep.version}" if dep.version else f"pkg:pypi/{pypi_name}"
            )
            if pypi_purl != primary_purl:
                purls_to_probe.append(pypi_purl)

        seen_vuln_ids: set[str] = set()
        extracted: list[dict[str, Any]] = []
        for purl in purls_to_probe:
            try:
                results = list(vdb_search.search_by_purl_like(purl, with_data=True) or [])
            except Exception:
                continue
            for raw in results:
                v = _extract_vuln_fields(raw)
                vid = v.get("id")
                if vid and vid in seen_vuln_ids:
                    continue
                if vid:
                    seen_vuln_ids.add(vid)
                extracted.append(v)
        vulns_by_purl[dep_key] = extracted
    return (vulns_by_purl, None)


# ── Atlas enrichment ────────────────────────────────────────────────────────

def enrich_with_atlas(deps: list[Dep]) -> dict[str, dict[str, Any]]:
    """For conda/pypi deps, look up atlas record by name. Returns {dep_key: atlas_record}."""
    if not ATLAS_DB.exists():
        return {}
    conn = sqlite3.connect(ATLAS_DB)
    conn.row_factory = sqlite3.Row
    out: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for dep in deps:
        if dep.ecosystem not in ("conda", "pypi"):
            continue
        key = f"{dep.ecosystem}:{dep.name}"
        if key in seen:
            continue
        seen.add(key)
        col = "conda_name" if dep.ecosystem == "conda" else "pypi_name"
        row = conn.execute(
            f"SELECT conda_name, pypi_name, latest_conda_version, conda_license, "
            f"feedstock_archived, latest_status FROM packages WHERE {col} = ? LIMIT 1",
            (dep.name,),
        ).fetchone()
        if row:
            out[key] = dict(row)
    return out


# ── Trivy delegation (optional) ──────────────────────────────────────────────

def run_trivy_image(image: str) -> tuple[dict[str, Any] | None, str | None]:
    """Run `trivy image --format json --severity HIGH,CRITICAL <image>` if trivy is installed."""
    if not TRIVY_BIN:
        return (None, "trivy not installed (install via conda-forge or pip)")
    try:
        result = subprocess.run(
            [TRIVY_BIN, "image", "--format", "json", "--severity", "HIGH,CRITICAL",
             "--quiet", "--timeout", "120s", image],
            capture_output=True, text=True, timeout=180, check=False,
        )
        if result.returncode != 0:
            return (None, f"trivy failed: {result.stderr[:200]}")
        return (json.loads(result.stdout), None)
    except subprocess.TimeoutExpired:
        return (None, "trivy timed out (>180s)")
    except (json.JSONDecodeError, OSError) as e:
        return (None, f"trivy error: {type(e).__name__}: {e}")


# ── Project resolution (clone or local) ─────────────────────────────────────

def resolve_project(input_arg: str, is_github: bool, ref: str | None) -> tuple[Path, bool, str | None]:
    """Returns (working_dir, is_temp_clone, error)."""
    if is_github or input_arg.startswith(("https://github.com/", "git@github.com:", "github.com/")):
        # Normalize URL
        url = input_arg
        if not url.startswith(("https://", "git@")):
            url = f"https://github.com/{url.lstrip('/')}"
        if not url.endswith(".git"):
            url = url + ".git"
        tmpdir = Path(tempfile.mkdtemp(prefix="scan-project-"))
        cmd = ["git", "clone", "--depth", "1"]
        if ref:
            cmd.extend(["--branch", ref])
        cmd.extend([url, str(tmpdir)])
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            shutil.rmtree(tmpdir, ignore_errors=True)
            return (Path("."), False, f"git clone failed: {result.stderr[:200]}")
        return (tmpdir, True, None)
    p = Path(input_arg).expanduser().resolve()
    if not p.is_dir():
        return (p, False, f"path not a directory: {p}")
    return (p, False, None)


# ── Render ──────────────────────────────────────────────────────────────────

def render(project_dir: Path,
           manifests_found: list[str],
           deps: list[Dep],
           base_images: list[str],
           vulns_by_dep: dict[str, list[dict[str, Any]]],
           atlas_records: dict[str, dict[str, Any]],
           trivy_results: dict[str, dict[str, Any] | None],
           source_status: dict[str, str],
           brief: bool) -> str:
    out: list[str] = []
    p = out.append

    # ── Header ────────────────────────────────────────────────────────────
    p(DOUBLE_RULE)
    p(f"  Project scan: {project_dir}")
    p(DOUBLE_RULE)
    p("")
    p(f"  Manifests discovered:")
    for m in manifests_found:
        n_deps = sum(1 for d in deps if d.manifest.startswith(m))
        p(f"    {m:<30} {n_deps} dep(s)")
    if base_images:
        p("")
        p(f"  Container base images:")
        for img in base_images:
            p(f"    {img}")
    if atlas_records:
        n_eligible = sum(1 for d in deps if d.ecosystem in ("conda", "pypi"))
        p("")
        p(f"  Atlas matches:    {len(atlas_records):,} of {n_eligible:,} conda/pypi deps")

    # ── Aggregate risk ────────────────────────────────────────────────────
    p("")
    p(RULE)
    p("  Aggregate risk")
    p(RULE)
    sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Unknown": 0}
    sev_affecting = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Unknown": 0}
    kev_count = 0
    pkg_risk: list[tuple[str, int, int, int, int, list[dict[str, Any]]]] = []  # (dep_key, crit, high, med, low, vulns)
    for dep_key, vulns in vulns_by_dep.items():
        c = h = m = l = 0
        for v in vulns:
            sev = v["severity"] if v["severity"] in sev_counts else "Unknown"
            sev_counts[sev] += 1
            sev_affecting[sev] += 1  # all vulns from version-pinned purl affect locked
            if v["kev"]:
                kev_count += 1
            if sev == "Critical":
                c += 1
            elif sev == "High":
                h += 1
            elif sev == "Medium":
                m += 1
            elif sev == "Low":
                l += 1
        if vulns:
            pkg_risk.append((dep_key, c, h, m, l, vulns))

    crit, high = sev_affecting["Critical"], sev_affecting["High"]
    if crit:
        risk = "CRITICAL"
    elif high:
        risk = "HIGH"
    elif sev_counts["Medium"]:
        risk = "MEDIUM"
    elif sev_counts["Low"] or sev_counts["Unknown"]:
        risk = "LOW"
    else:
        risk = "CLEAN (no CVEs found)"
    p(f"  RISK: {risk} — {crit} Critical, {high} High, {sev_counts['Medium']} Medium, "
      f"{sev_counts['Low']} Low, {kev_count} KEV-listed")
    p(f"        across {len(deps)} dependencies in {len(manifests_found)} manifest(s)")
    p("")
    p("  Severity     Total")
    for s in ("Critical", "High", "Medium", "Low", "Unknown"):
        if sev_counts[s]:
            p(f"  {s:<12} {sev_counts[s]}")

    # ── Top N risk-prioritized ────────────────────────────────────────────
    pkg_risk.sort(key=lambda x: (-x[1], -x[2], -x[3], -x[4]))
    top_n = 5 if brief else 10
    if pkg_risk:
        p("")
        p(RULE)
        p(f"  Top {min(top_n, len(pkg_risk))} risk-prioritized packages")
        p(RULE)
        for dep_key, c, h, m, l, vulns in pkg_risk[:top_n]:
            counts = []
            if c: counts.append(f"{c} Critical")
            if h: counts.append(f"{h} High")
            if m: counts.append(f"{m} Medium")
            if l: counts.append(f"{l} Low")
            p(f"  {dep_key:<40} {', '.join(counts)}")
            sev_rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Unknown": 4}
            top_vuln = sorted(vulns, key=lambda v: (sev_rank.get(v["severity"], 4),
                                                    -(float(v["cvss_score"]) if v["cvss_score"] else 0)))[:1]
            for v in top_vuln:
                score = f"{v['cvss_score']}" if v["cvss_score"] else "—"
                cwe = v["cwe"] or ""
                p(f"    └─ {v['id']:<22} {score:<5} {v['severity']:<9} {cwe:<10} {v['description'][:55]}")

    # ── SBOM relationships — render the dep tree when an SBOM input
    # carries CycloneDX dependencies[] / SPDX relationships[] data ────
    rel_deps = [d for d in deps if isinstance(d.extras, dict)
                and d.extras.get("depends_on")]
    if rel_deps:
        p("")
        p(RULE)
        p(f"  SBOM dependency tree ({len(rel_deps)} parent component(s))")
        p(RULE)
        for d in rel_deps[:15]:
            children = d.extras.get("depends_on") or []
            label = f"{d.ecosystem}:{d.name}@{d.version or '?'}"
            p(f"  {label}")
            for child in children[:8]:
                p(f"    └─ {child}")
            if len(children) > 8:
                p(f"    ... and {len(children) - 8} more")

    # ── VEX (suppressions) — only when an SBOM input carried VEX data ────
    vex_deps = [d for d in deps if isinstance(d.extras, dict) and d.extras.get("vex")]
    if vex_deps:
        p("")
        p(RULE)
        p(f"  VEX statements ({len(vex_deps)} component(s) with analysis)")
        p(RULE)
        for d in vex_deps[:10]:
            stmts = d.extras.get("vex") or []
            for s in stmts:
                state = s.get("state") or "?"
                cve = s.get("cve_id") or "?"
                just = s.get("justification") or "—"
                p(f"  {d.ecosystem}:{d.name}  {cve}  state={state}  ({just})")

    # ── By manifest detail (skip in --brief) ──────────────────────────────
    if not brief:
        p("")
        p(RULE)
        p("  By manifest")
        p(RULE)
        for m in manifests_found:
            m_deps = [d for d in deps if d.manifest.startswith(m)]
            n_with_vulns = sum(1 for d in m_deps if vulns_by_dep.get(f"{d.ecosystem}:{d.name}@{d.version}"))
            n_total_vulns = sum(len(vulns_by_dep.get(f"{d.ecosystem}:{d.name}@{d.version}", [])) for d in m_deps)
            p(f"  {m}: {len(m_deps)} deps, {n_with_vulns} with CVEs, {n_total_vulns} total CVE matches")

    # ── Trivy results ─────────────────────────────────────────────────────
    if trivy_results:
        p("")
        p(RULE)
        p("  Container OS-level scan (trivy)")
        p(RULE)
        for img, result in trivy_results.items():
            if result is None:
                p(f"  {img}: (no trivy data)")
                continue
            os_info = (result.get("Metadata", {}) or {}).get("OS", {})
            p(f"  {img}: {os_info.get('Family', '?')} {os_info.get('Name', '?')}")
            for tres in result.get("Results", []) or []:
                vulns = tres.get("Vulnerabilities", []) or []
                if vulns:
                    crit_n = sum(1 for v in vulns if v.get("Severity") == "CRITICAL")
                    high_n = sum(1 for v in vulns if v.get("Severity") == "HIGH")
                    p(f"    {tres.get('Target', '?'):<40} {crit_n} Critical, {high_n} High")

    # ── Source summary ────────────────────────────────────────────────────
    p("")
    p(DOUBLE_RULE)
    p("  Source summary")
    p(DOUBLE_RULE)
    sym = {"ok": "✓", "fail": "✗", "skip": "—"}
    for src, status in source_status.items():
        if src.endswith("_msg"):
            continue
        msg = source_status.get(f"{src}_msg", "")
        p(f"  {sym.get(status, '?')} {src:<35} {msg}")
    p("")
    p("  Hints:")
    p("  • For OS-level CVE scans: run `vdb --cache-os` then re-scan with `--os`")
    p("  • For full container scans: install trivy (conda-forge has it)")
    p("  • For air-gapped: vdb works offline once cached at .claude/data/conda-forge-expert/vdb/")
    p(DOUBLE_RULE)

    return "\n".join(out)


def _scan_deps(deps: list[Dep], manifest_labels: list[str],
               source_status: dict[str, str], args: argparse.Namespace) -> int:
    """Common post-discovery flow for image/SBOM input modes.

    Runs the same atlas + vdb enrichment as the manifest-discovery path
    in main(), but skipping project_dir-anchored work (containerfile parse,
    git-clone bookkeeping). Used by --image and --sbom-in modes.
    """
    project_label = manifest_labels[0] if manifest_labels else "<unknown>"
    project_dir = Path("/")  # placeholder; not used for I/O in this path

    if not deps:
        print("No dependencies extracted.", file=sys.stderr)
        return 1

    # Atlas enrichment
    if ATLAS_DB.exists():
        atlas_records = enrich_with_atlas(deps)
        source_status["atlas (cf_atlas.db)"] = "ok"
        n_conda_pypi = sum(1 for d in deps if d.ecosystem in ("conda", "pypi"))
        source_status["atlas (cf_atlas.db)_msg"] = (
            f"— matched {len(atlas_records)} of {n_conda_pypi} conda/pypi deps"
        )
    else:
        atlas_records = {}
        source_status["atlas (cf_atlas.db)"] = "fail"
        source_status["atlas (cf_atlas.db)_msg"] = "— atlas DB missing; run `build-cf-atlas`"

    # Vuln lookup (vdb library auto-skip handled inside)
    t1 = time.monotonic()
    vulns_by_dep, vdb_err = lookup_vulns(deps, atlas_records)
    if vdb_err:
        source_status["vdb (vulnerability DB)"] = "fail"
        source_status["vdb (vulnerability DB)_msg"] = f"— {vdb_err}"
    else:
        affected = sum(1 for v in vulns_by_dep.values() if v)
        source_status["vdb (vulnerability DB)"] = "ok"
        source_status["vdb (vulnerability DB)_msg"] = (
            f"— {affected} dep(s) have vulns indexed; query took "
            f"{time.monotonic() - t1:.1f}s"
        )

    # OS-level + trivy not applicable in image/SBOM input mode (no Containerfile)
    base_images_all: list[str] = []
    trivy_results: dict[str, dict[str, Any] | None] = {}

    # License compatibility check (atlas-only; no SBOM/vdb needed)
    if args.license_check:
        sys.stdout.write(render_license_check(
            deps, atlas_records, args.target_license,
        ))
        return 0
    if args.sbom:
        sys.path.insert(0, str(Path(__file__).parent))
        from _sbom import emit_cyclonedx, emit_spdx  # type: ignore[import-not-found]
        emitter = emit_cyclonedx if args.sbom == "cyclonedx" else emit_spdx
        # Atlas-cached vuln enrichment: pull Phase G counts as CycloneDX
        # properties on the matching components, regardless of whether vdb
        # data is also present. They're complementary — vdb has full CVE
        # rows; atlas has rolled-up severity counts that survive offline
        # use (no vuln-db env needed).
        if args.enrich_atlas_vulns:
            atlas_vulns = fetch_atlas_vuln_summary(deps, atlas_records)
            if atlas_vulns:
                source_status["atlas vuln cache"] = "ok"
                source_status["atlas vuln cache_msg"] = (
                    f"— annotated {len(atlas_vulns)} component(s) with "
                    f"Phase G counts (offline-safe; complementary to vdb)"
                )
                # Stamp each component directly with CycloneDX properties.
                # The base SBOM emitter doesn't know about Phase G, so we
                # post-process below after `emitter()` runs.
                pass
        sbom = emitter(deps, vulns_by_dep, project_name=project_label,
                       atlas_records=atlas_records)
        # Post-process: stamp Phase G atlas counts as CycloneDX properties
        # / SPDX annotations on the matching components.
        if args.enrich_atlas_vulns:
            atlas_vulns_post = fetch_atlas_vuln_summary(deps, atlas_records)
            if args.sbom == "cyclonedx":
                for c in sbom.get("components", []) or []:
                    name = (c.get("name") or "").lower()
                    av = atlas_vulns_post.get(name)
                    if not av:
                        continue
                    props = c.setdefault("properties", [])
                    for k, v in (
                        ("cdx:atlas:vuln_total", av["total"]),
                        ("cdx:atlas:vuln_critical_affecting_current",
                         av["critical_affecting_current"]),
                        ("cdx:atlas:vuln_high_affecting_current",
                         av["high_affecting_current"]),
                        ("cdx:atlas:vuln_kev_affecting_current",
                         av["kev_affecting_current"]),
                        ("cdx:atlas:vdb_scanned_at", av["scanned_at"]),
                    ):
                        props.append({"name": k, "value": str(v)})
            else:  # spdx
                for pkg in sbom.get("packages", []) or []:
                    name = (pkg.get("name") or "").lower()
                    av = atlas_vulns_post.get(name)
                    if not av:
                        continue
                    annots = pkg.setdefault("annotations", [])
                    for k, v in (
                        ("vuln_total", av["total"]),
                        ("vuln_critical_affecting_current",
                         av["critical_affecting_current"]),
                        ("vuln_high_affecting_current",
                         av["high_affecting_current"]),
                        ("vuln_kev_affecting_current",
                         av["kev_affecting_current"]),
                    ):
                        annots.append({
                            "annotationType": "OTHER",
                            "annotator": "Tool: cf_atlas Phase G",
                            "annotationDate": _dt_iso_now(),
                            "annotationComment": f"{k}={v}",
                        })
        sbom_json = json.dumps(sbom, indent=2, default=str)
        if args.sbom_out:
            Path(args.sbom_out).write_text(sbom_json)
            print(f"SBOM ({args.sbom}) written to {args.sbom_out}", file=sys.stderr)
        else:
            print(sbom_json)
        return 0
    if args.as_json:
        print(json.dumps({
            "project_dir": project_label,
            "manifests": manifest_labels,
            "deps": [d.__dict__ for d in deps],
            "base_images": [],
            "vulns_by_dep": vulns_by_dep,
            "atlas_records": atlas_records,
            "trivy_results": {},
            "source_status": {k: v for k, v in source_status.items()
                              if not k.endswith("_msg")},
        }, indent=2, default=str))
        return 0
    # Use the regular render. project_dir is purely cosmetic (printed in header).
    print(render(project_dir, manifest_labels, deps, base_images_all,
                 vulns_by_dep, atlas_records, trivy_results,
                 source_status, args.brief))
    return 0


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "scan-project").split("\n")[1])
    parser.add_argument("input", nargs="?", default=".",
                        help="Path or GitHub URL/owner-repo (default: cwd)")
    parser.add_argument("--github", action="store_true", help="Treat input as GitHub URL")
    parser.add_argument("--ref", help="With --github, checkout specific branch/tag/sha")
    parser.add_argument("--os", action="store_true", help="Include OS-level CVE lookups")
    parser.add_argument("--no-trivy", dest="no_trivy", action="store_true",
                        help="Don't try trivy even if installed")
    parser.add_argument("--keep-clone", dest="keep_clone", action="store_true",
                        help="Don't delete temp clone after")
    parser.add_argument("--brief", action="store_true", help="Show aggregate + top-5 only")
    parser.add_argument("--json", dest="as_json", action="store_true",
                        help="Output raw JSON instead of formatted card")
    parser.add_argument("--sbom", choices=["cyclonedx", "spdx"],
                        help="Emit SBOM (CycloneDX 1.6 or SPDX 2.3 JSON) instead of card")
    parser.add_argument("--sbom-out", dest="sbom_out",
                        help="Write SBOM to file instead of stdout")
    parser.add_argument("--sbom-in", dest="sbom_in",
                        help="Read deps from a CycloneDX or SPDX JSON file. "
                             "Auto-detects format. Combine with other "
                             "manifest sources or use stand-alone.")
    parser.add_argument("--image", dest="image", action="append",
                        help="Container image reference (e.g., python:3.12). "
                             "Repeat or comma-separate for multiple images. "
                             "Uses syft (preferred) or trivy to extract an "
                             "SBOM, then enriches with cf_atlas + vdb.")
    parser.add_argument("--image-tool", dest="image_tool",
                        choices=["auto", "syft", "trivy"], default="auto",
                        help="Which SBOM extractor to prefer (default: auto)")
    parser.add_argument("--oci-archive", dest="oci_archive",
                        help="OCI image archive (.tar / dir). Passes through "
                             "to syft/trivy with the appropriate scheme.")
    parser.add_argument("--conda-env", dest="conda_env",
                        help="Live conda environment directory. Reads "
                             "conda-meta/*.json + site-packages dist-info "
                             "directly from disk (offline-safe).")
    parser.add_argument("--venv", dest="venv",
                        help="Live Python virtualenv directory (venv / "
                             "virtualenv / uv / pipenv). Walks "
                             "lib/python*/site-packages/*.dist-info/METADATA.")
    parser.add_argument("--kubectl-context", dest="kubectl_ctx",
                        help="Live cluster scan via `kubectl get pods -A`. "
                             "Optional context name (default: current).")
    parser.add_argument("--kubectl-namespace", dest="kubectl_ns",
                        help="With --kubectl-context, restrict to one namespace.")
    parser.add_argument("--kubectl-all", dest="kubectl_all", action="store_true",
                        help="Shortcut for `kubectl get pods -A` against the "
                             "current context (no need to name it).")
    parser.add_argument("--helm-chart", dest="helm_chart",
                        help="Path to a Helm chart directory; runs "
                             "`helm template` and extracts images.")
    parser.add_argument("--helm-values", dest="helm_values", action="append",
                        help="With --helm-chart, additional values files "
                             "(repeatable).")
    parser.add_argument("--kustomize", dest="kustomize",
                        help="Path to a Kustomize overlay directory; runs "
                             "`kustomize build` and extracts images.")
    parser.add_argument("--argo-app", dest="argo_app",
                        help="Argo CD Application CR YAML; resolves source "
                             "to local helm/kustomize/manifests path and scans.")
    parser.add_argument("--flux-cr", dest="flux_cr",
                        help="Flux CD HelmRelease or Kustomization CR YAML; "
                             "renders via helm/kustomize against local path.")
    parser.add_argument("--oci-manifest", dest="oci_manifest",
                        help="Probe OCI registry for image manifest only "
                             "(tag verification / digest pinning, no SBOM "
                             "extraction). Output mode = JSON.")
    parser.add_argument("--license-check", action="store_true", dest="license_check",
                        help="Tabulate license compatibility per dep against "
                             "--target-license. Without --target-license, "
                             "groups deps by license family for review.")
    parser.add_argument("--target-license", dest="target_license",
                        help="Compare each dep's license against this target "
                             "(e.g., 'Apache-2.0', 'MIT', 'GPL-3.0-only').")
    parser.add_argument("--enrich-vulns-from-atlas", action="store_true",
                        dest="enrich_atlas_vulns",
                        help="When emitting --sbom, annotate components with "
                             "cf_atlas Phase G vuln counts as CycloneDX "
                             "properties (no vdb env required).")
    args = parser.parse_args()

    source_status: dict[str, str] = {}

    # ── Container image input mode (multi-image supported) ─────────────────
    # `--image` is `action="append"`, so it's a list. Each value may also
    # be comma-separated. Extracts deps from each via syft/trivy and merges.
    if args.image:
        all_images: list[str] = []
        for entry in args.image:
            for piece in entry.split(","):
                p = piece.strip()
                if p:
                    all_images.append(p)
        merged_deps: list[Dep] = []
        labels: list[str] = []
        for img in all_images:
            t0 = time.monotonic()
            ideps, ierr = extract_sbom_from_image(img, args.image_tool)
            if ideps is None:
                print(f"ERROR ({img}): {ierr}", file=sys.stderr)
                continue
            print(f"Extracted {len(ideps):,} deps from image {img} "
                  f"in {time.monotonic() - t0:.1f}s", file=sys.stderr)
            merged_deps.extend(ideps)
            labels.append(f"image:{img}")
        if not merged_deps:
            print("ERROR: no deps extracted from any image", file=sys.stderr)
            return 1
        return _scan_deps(merged_deps, labels, source_status, args)

    # ── OCI archive input ────────────────────────────────────────────────
    if args.oci_archive:
        archive_path = Path(args.oci_archive)
        if not archive_path.exists():
            print(f"ERROR: archive not found: {archive_path}", file=sys.stderr)
            return 1
        # syft accepts dir:, tar:, oci-archive:, oci-dir: schemes
        if archive_path.is_dir():
            ref = f"dir:{archive_path}"
        elif archive_path.suffix == ".tar":
            ref = f"oci-archive:{archive_path}"
        else:
            ref = str(archive_path)  # let syft auto-detect
        t0 = time.monotonic()
        adeps, aerr = extract_sbom_from_image(ref, args.image_tool)
        if adeps is None:
            print(f"ERROR: {aerr}", file=sys.stderr)
            return 1
        print(f"Extracted {len(adeps):,} deps from archive {archive_path} "
              f"in {time.monotonic() - t0:.1f}s", file=sys.stderr)
        return _scan_deps(adeps, [f"oci-archive:{archive_path}"],
                          source_status, args)

    # ── Live conda env input ─────────────────────────────────────────────
    if args.conda_env:
        env_path = Path(args.conda_env)
        if not env_path.is_dir():
            print(f"ERROR: not a directory: {env_path}", file=sys.stderr)
            return 1
        cdeps = parse_conda_meta_dir(env_path)
        print(f"Loaded {len(cdeps):,} packages from conda env {env_path}",
              file=sys.stderr)
        return _scan_deps(cdeps, [f"conda-env:{env_path}"], source_status, args)

    # ── Live Python venv input ───────────────────────────────────────────
    if args.venv:
        venv_path = Path(args.venv)
        if not venv_path.is_dir():
            print(f"ERROR: not a directory: {venv_path}", file=sys.stderr)
            return 1
        vdeps = parse_python_venv(venv_path)
        print(f"Loaded {len(vdeps):,} packages from venv {venv_path}",
              file=sys.stderr)
        return _scan_deps(vdeps, [f"venv:{venv_path}"], source_status, args)

    # ── Live cluster scan via kubectl ────────────────────────────────────
    if args.kubectl_ctx or args.kubectl_all:
        ctx = args.kubectl_ctx if not args.kubectl_all else None
        kdeps, kerr = kubectl_pod_images(context=ctx, namespace=args.kubectl_ns)
        if kdeps is None:
            print(f"ERROR: {kerr}", file=sys.stderr)
            return 1
        print(f"Found {len(kdeps):,} unique images in cluster "
              f"({ctx or 'current'}/{args.kubectl_ns or 'all-ns'})",
              file=sys.stderr)
        return _scan_deps(kdeps, [f"kubectl({ctx or 'current'})"],
                          source_status, args)

    # ── helm template chart rendering ────────────────────────────────────
    if args.helm_chart:
        chart_path = Path(args.helm_chart)
        if not chart_path.exists():
            print(f"ERROR: chart path not found: {chart_path}", file=sys.stderr)
            return 1
        values_paths = [Path(p) for p in (args.helm_values or [])]
        hdeps, herr = helm_template_images(chart_path, values_paths)
        if hdeps is None:
            print(f"ERROR: {herr}", file=sys.stderr)
            return 1
        print(f"Helm template rendered {len(hdeps):,} unique images from "
              f"{chart_path}", file=sys.stderr)
        return _scan_deps(hdeps, [f"helm({chart_path})"], source_status, args)

    # ── kustomize build rendering ────────────────────────────────────────
    if args.kustomize:
        kust_path = Path(args.kustomize)
        if not kust_path.is_dir():
            print(f"ERROR: kustomize dir not found: {kust_path}", file=sys.stderr)
            return 1
        kdeps2, kerr2 = kustomize_build_images(kust_path)
        if kdeps2 is None:
            print(f"ERROR: {kerr2}", file=sys.stderr)
            return 1
        print(f"Kustomize build extracted {len(kdeps2):,} unique images from "
              f"{kust_path}", file=sys.stderr)
        return _scan_deps(kdeps2, [f"kustomize({kust_path})"],
                          source_status, args)

    # ── Argo CD Application CR ───────────────────────────────────────────
    if args.argo_app:
        cr_path = Path(args.argo_app)
        if not cr_path.exists():
            print(f"ERROR: Argo CR not found: {cr_path}", file=sys.stderr)
            return 1
        adeps, aerr = argo_application_images(cr_path)
        if adeps is None:
            print(f"ERROR: {aerr}", file=sys.stderr)
            return 1
        print(f"Argo Application extracted {len(adeps):,} images from "
              f"{cr_path}", file=sys.stderr)
        return _scan_deps(adeps, [f"argo({cr_path})"], source_status, args)

    # ── Flux CD HelmRelease / Kustomization CR ───────────────────────────
    if args.flux_cr:
        cr_path = Path(args.flux_cr)
        if not cr_path.exists():
            print(f"ERROR: Flux CR not found: {cr_path}", file=sys.stderr)
            return 1
        fdeps, ferr = flux_cr_images(cr_path)
        if fdeps is None:
            print(f"ERROR: {ferr}", file=sys.stderr)
            return 1
        print(f"Flux CR extracted {len(fdeps):,} images from {cr_path}",
              file=sys.stderr)
        return _scan_deps(fdeps, [f"flux({cr_path})"], source_status, args)

    # ── OCI manifest probe (no SBOM, just digest / tag verification) ─────
    if args.oci_manifest:
        manifest, merr = oci_manifest_probe(args.oci_manifest)
        if manifest is None:
            print(f"ERROR: {merr}", file=sys.stderr)
            return 1
        print(json.dumps(manifest, indent=2, default=str))
        return 0

    # ── SBOM input mode ───────────────────────────────────────────────────
    if args.sbom_in:
        sbom_path = Path(args.sbom_in)
        if not sbom_path.exists():
            print(f"ERROR: SBOM file not found: {sbom_path}", file=sys.stderr)
            return 1
        # Non-JSON formats first (XML / tag-value) by extension
        suffix = sbom_path.suffix.lower()
        if suffix == ".xml":
            sbom_deps = parse_sbom_cyclonedx_xml(sbom_path)
            print(f"Loaded {len(sbom_deps):,} deps from CycloneDX XML at {sbom_path}",
                  file=sys.stderr)
            return _scan_deps(sbom_deps, [str(sbom_path)], source_status, args)
        if suffix in (".spdx", ".tag"):
            sbom_deps = parse_sbom_spdx_tagvalue(sbom_path)
            print(f"Loaded {len(sbom_deps):,} deps from SPDX tag-value at {sbom_path}",
                  file=sys.stderr)
            return _scan_deps(sbom_deps, [str(sbom_path)], source_status, args)
        # JSON shape auto-detection: CycloneDX bomFormat / SPDX 2.x / SPDX 3.0 /
        # syft / trivy
        try:
            head = json.loads(sbom_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            print(f"ERROR: failed to parse SBOM file: {e}", file=sys.stderr)
            return 1
        if isinstance(head, dict) and head.get("bomFormat") == "CycloneDX":
            sbom_deps = parse_sbom_cyclonedx(sbom_path)
            fmt = "CycloneDX"
            # Relationship traversal (CycloneDX dependencies[] →
            # SPDX-style {parent_ref: [child_refs]}). Stash on dep.extras
            # so the renderer can show the dep tree.
            rels = parse_sbom_relationships(sbom_path)
            if rels:
                source_status["sbom_relationships"] = "ok"
                source_status["sbom_relationships_msg"] = (
                    f"— {sum(len(c) for c in rels.values())} dep edge(s) "
                    f"across {len(rels)} component(s)"
                )
                # Map by component name (best-effort — use bom-ref → name)
                ref_to_dep: dict[str, Dep] = {}
                for d in sbom_deps:
                    bom_ref = d.extras.get("bom-ref")
                    if bom_ref:
                        ref_to_dep[bom_ref] = d
                for parent_ref, child_refs in rels.items():
                    parent = ref_to_dep.get(parent_ref)
                    if parent is None:
                        continue
                    children = [
                        ref_to_dep[c].name for c in child_refs
                        if c in ref_to_dep
                    ]
                    if children:
                        parent.extras["depends_on"] = children
            # VEX statements (CycloneDX 1.5+ vulnerabilities[] with
            # analysis.state). Stash on dep.extras so the renderer / SBOM
            # emitter can suppress 'not_affected' / 'false_positive' rows.
            vex = parse_vex_cyclonedx(sbom_path)
            if vex:
                source_status["vex"] = "ok"
                n_suppressed = sum(
                    1 for stmts in vex.values() for s in stmts
                    if s["state"] in ("not_affected", "false_positive")
                )
                source_status["vex_msg"] = (
                    f"— {len(vex)} component(s) carry VEX statements; "
                    f"{n_suppressed} CVE-component pair(s) marked "
                    f"not_affected/false_positive"
                )
                # Map by component name (best-effort — VEX bom-refs are
                # opaque to us; we use the bom-ref → name lookup we already
                # built during component parsing).
                for d in sbom_deps:
                    bom_ref = d.extras.get("bom-ref")
                    if bom_ref and bom_ref in vex:
                        d.extras["vex"] = vex[bom_ref]
        elif isinstance(head, dict) and head.get("spdxVersion"):
            sbom_deps = parse_sbom_spdx(sbom_path)
            fmt = "SPDX 2.x"
        elif isinstance(head, dict) and (
            "@graph" in head
            or head.get("type") in ("SoftwareSpdxDocument", "SpdxDocument")
            or any(("spdx" in (k.lower() if isinstance(k, str) else ""))
                   for k in head.keys())
            and "@context" in head
        ):
            sbom_deps = parse_sbom_spdx_3(sbom_path)
            fmt = "SPDX 3.0 (JSON-LD)"
        elif isinstance(head, dict) and "artifacts" in head and (
            head.get("descriptor", {}).get("name", "").lower() == "syft"
            or "schema" in head.get("descriptor", {})
        ):
            # Native syft JSON: top-level has `artifacts` + a `descriptor`
            # block naming the producing tool.
            sbom_deps = parse_syft_json(sbom_path)
            fmt = "syft (native JSON)"
        elif isinstance(head, dict) and "Results" in head and isinstance(
            head["Results"], list
        ):
            # Native trivy JSON: top-level has `Results` array with
            # `Class`/`Type` per result.
            sbom_deps = parse_trivy_json(sbom_path)
            fmt = "trivy (native JSON)"
        else:
            print("ERROR: SBOM format not recognized "
                  "(need CycloneDX / SPDX 2.x / SPDX 3.0 / syft / trivy JSON).",
                  file=sys.stderr)
            return 1
        print(f"Loaded {len(sbom_deps):,} deps from {fmt} SBOM at {sbom_path}",
              file=sys.stderr)
        return _scan_deps(sbom_deps, [str(sbom_path)], source_status, args)

    # Resolve project
    t0 = time.monotonic()
    project_dir, is_temp, err = resolve_project(args.input, args.github, args.ref)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1
    if is_temp:
        source_status["git clone"] = "ok"
        source_status["git clone_msg"] = f"— cloned to {project_dir} in {time.monotonic() - t0:.1f}s"
    else:
        source_status["git clone"] = "skip"
        source_status["git clone_msg"] = "— local path used directly"

    try:
        # Discover manifests
        candidates = [
            ("pixi.lock", parse_pixi_lock),
            ("requirements.txt", parse_requirements_txt),
            ("pyproject.toml", parse_pyproject_toml),
            ("environment.yml", parse_environment_yml),
            ("environment.yaml", parse_environment_yml),
        ]
        # pixi.toml only if pixi.lock missing (per locked spec)
        has_pixi_lock = (project_dir / "pixi.lock").exists()
        if not has_pixi_lock:
            candidates.append(("pixi.toml", parse_pixi_toml))
        # Cargo.lock priority over Cargo.toml (same lock-first rule)
        candidates.append(("Cargo.lock", parse_cargo_lock))
        has_cargo_lock = any(project_dir.glob("**/Cargo.lock"))
        if not has_cargo_lock:
            candidates.append(("Cargo.toml", parse_cargo_toml))
        # Python ecosystem locks (uv / poetry / pipenv) — alternatives to
        # pip-tools' requirements.txt. Lock files preferred over manifest
        # files for accuracy (same rule as pixi.lock vs pixi.toml).
        candidates.append(("uv.lock", parse_uv_lock))
        candidates.append(("poetry.lock", parse_poetry_lock))
        candidates.append(("Pipfile.lock", parse_pipfile_lock))
        # npm — package-lock.json is preferred over package.json (transitive
        # resolution); we still parse package.json if no lock is present.
        has_npm_lock = any(project_dir.glob("**/package-lock.json"))
        candidates.append(("package-lock.json", parse_package_lock_json))
        if not has_npm_lock:
            candidates.append(("package.json", parse_package_json))
        # yarn (v1 + v2+ Berry are auto-detected by parse_yarn_lock)
        candidates.append(("yarn.lock", parse_yarn_lock))
        # pnpm
        candidates.append(("pnpm-lock.yaml", parse_pnpm_lock))
        # Go
        has_go_sum = any(project_dir.glob("**/go.sum"))
        candidates.append(("go.sum", parse_go_sum))
        if not has_go_sum:
            candidates.append(("go.mod", parse_go_mod))
        # Ruby
        candidates.append(("Gemfile.lock", parse_gemfile_lock))
        # PHP / Composer
        candidates.append(("composer.lock", parse_composer_lock))
        # conda-lock
        candidates.append(("conda-lock.yml", parse_conda_lock))
        candidates.append(("conda-lock.yaml", parse_conda_lock))
        # Pipfile manifest (no lock)
        has_pipfile_lock = any(project_dir.glob("**/Pipfile.lock"))
        if not has_pipfile_lock:
            candidates.append(("Pipfile", parse_pipfile))
        # pip-tools input
        candidates.append(("requirements.in", parse_requirements_in))
        # Helm chart values (best-effort image extraction)
        candidates.append(("values.yaml", parse_helm_values))
        # SBOMs in the project tree (CycloneDX 1.x / SPDX 2.x / SPDX 3.0).
        # The auto-detect in each parser handles wrong-format files gracefully.
        candidates.append(("bom.json", parse_sbom_cyclonedx))
        candidates.append(("cyclonedx.json", parse_sbom_cyclonedx))
        candidates.append(("sbom.cyclonedx.json", parse_sbom_cyclonedx))
        candidates.append(("sbom.spdx.json", parse_sbom_spdx))
        candidates.append(("sbom.spdx3.json", parse_sbom_spdx_3))
        candidates.append(("sbom.jsonld", parse_sbom_spdx_3))
        # Native syft / trivy outputs (both have distinctive top-level shapes
        # — see parse_syft_json / parse_trivy_json for details).
        candidates.append(("sbom.syft.json", parse_syft_json))
        candidates.append(("syft.json", parse_syft_json))
        candidates.append(("sbom.trivy.json", parse_trivy_json))
        candidates.append(("trivy.json", parse_trivy_json))
        candidates.append(("trivy-report.json", parse_trivy_json))
        # Rare SBOM forms: CycloneDX XML and SPDX 2.x tag-value
        candidates.append(("bom.xml", parse_sbom_cyclonedx_xml))
        candidates.append(("cyclonedx.xml", parse_sbom_cyclonedx_xml))
        candidates.append(("sbom.cyclonedx.xml", parse_sbom_cyclonedx_xml))
        candidates.append(("sbom.spdx", parse_sbom_spdx_tagvalue))
        candidates.append(("sbom.spdx.tag", parse_sbom_spdx_tagvalue))

        manifests_found: list[str] = []
        deps: list[Dep] = []
        for fname, fn in candidates:
            for path in project_dir.glob(f"**/{fname}"):
                # Skip nested vendored stuff
                if any(part in _SKIP_PATH_PARTS for part in path.parts):
                    continue
                manifests_found.append(str(path.relative_to(project_dir)))
                deps.extend(fn(path))

        # Containerfile / Dockerfile
        base_images_all: list[str] = []
        for cf_pattern in ("Containerfile", "Dockerfile", "*.Containerfile", "*.Dockerfile"):
            for path in project_dir.glob(f"**/{cf_pattern}"):
                if any(part in _SKIP_PATH_PARTS for part in path.parts):
                    continue
                manifests_found.append(str(path.relative_to(project_dir)))
                cf_deps, cf_imgs = parse_containerfile(path)
                deps.extend(cf_deps)
                base_images_all.extend(cf_imgs)

        # Kubernetes / OpenShift / Knative / Helm — match by conventional
        # directory names. Generic **/*.yaml matching would be too noisy
        # in monorepos, so restrict to common locations. Users with custom
        # layouts can always supply --sbom-in or scan individual files.
        _k8s_dirs = ("k8s", "kubernetes", "manifests", "deploy",
                     "deployment", "openshift", "ocp", "helm",
                     "charts", "kustomize", "overlays", "argo",
                     "kustomization")
        for k8s_dir in _k8s_dirs:
            for path in project_dir.glob(f"**/{k8s_dir}/**/*.yaml"):
                if any(part in _SKIP_PATH_PARTS for part in path.parts):
                    continue
                manifests_found.append(str(path.relative_to(project_dir)))
                deps.extend(parse_kubernetes_manifest(path))
            for path in project_dir.glob(f"**/{k8s_dir}/**/*.yml"):
                if any(part in _SKIP_PATH_PARTS for part in path.parts):
                    continue
                manifests_found.append(str(path.relative_to(project_dir)))
                deps.extend(parse_kubernetes_manifest(path))

        source_status["manifest discovery"] = "ok"
        source_status["manifest discovery_msg"] = f"— {len(manifests_found)} manifest(s), {len(deps)} dep(s)"

        # Atlas enrichment
        if ATLAS_DB.exists():
            atlas_records = enrich_with_atlas(deps)
            source_status["atlas (cf_atlas.db)"] = "ok"
            n_conda_pypi = sum(1 for d in deps if d.ecosystem in ("conda", "pypi"))
            source_status["atlas (cf_atlas.db)_msg"] = f"— matched {len(atlas_records)} of {n_conda_pypi} conda/pypi deps"
        else:
            atlas_records = {}
            source_status["atlas (cf_atlas.db)"] = "fail"
            source_status["atlas (cf_atlas.db)_msg"] = "— atlas DB missing; run `build-cf-atlas`"

        # Vuln lookup
        t1 = time.monotonic()
        vulns_by_dep, vdb_err = lookup_vulns(deps, atlas_records)
        if vdb_err:
            source_status["vdb (vulnerability DB)"] = "fail"
            source_status["vdb (vulnerability DB)_msg"] = f"— {vdb_err}"
        else:
            n_with_vulns = sum(1 for v in vulns_by_dep.values() if v)
            source_status["vdb (vulnerability DB)"] = "ok"
            source_status["vdb (vulnerability DB)_msg"] = (
                f"— scanned {len(vulns_by_dep)} unique deps, {n_with_vulns} with vulns "
                f"in {time.monotonic() - t1:.1f}s"
            )

        # Trivy (optional)
        trivy_results: dict[str, dict[str, Any] | None] = {}
        if base_images_all and not args.no_trivy and TRIVY_BIN:
            for img in base_images_all[:3]:  # limit to first 3 to keep runtime bounded
                t2 = time.monotonic()
                tres, terr = run_trivy_image(img)
                trivy_results[img] = tres
                key = f"trivy ({img})"
                if terr:
                    source_status[key] = "fail"
                    source_status[f"{key}_msg"] = f"— {terr}"
                else:
                    source_status[key] = "ok"
                    source_status[f"{key}_msg"] = f"— scanned in {time.monotonic() - t2:.1f}s"
        elif base_images_all and args.no_trivy:
            source_status["trivy"] = "skip"
            source_status["trivy_msg"] = "— --no-trivy passed"
        elif base_images_all and not TRIVY_BIN:
            source_status["trivy"] = "skip"
            source_status["trivy_msg"] = "— trivy not installed (apt install trivy or conda)"

        # OS-level CVE lookup status
        if args.os:
            os_deps = [d for d in deps if d.ecosystem in ("apt", "dnf", "yum", "apk")]
            source_status["OS-level CVE lookups"] = "ok" if os_deps else "skip"
            source_status["OS-level CVE lookups_msg"] = (
                f"— {len(os_deps)} OS package(s) queried via vdb (requires `vdb --cache-os` data)"
                if os_deps else "— no OS deps found"
            )
        else:
            source_status["OS-level CVE lookups"] = "skip"
            source_status["OS-level CVE lookups_msg"] = "— --os not requested"

        if args.license_check:
            sys.stdout.write(render_license_check(
                deps, atlas_records, args.target_license,
            ))
        elif args.sbom:
            sys.path.insert(0, str(Path(__file__).parent))
            from _sbom import emit_cyclonedx, emit_spdx  # type: ignore[import-not-found]
            emitter = emit_cyclonedx if args.sbom == "cyclonedx" else emit_spdx
            sbom = emitter(deps, vulns_by_dep, project_name=project_dir.name,
                           atlas_records=atlas_records)
            # Optional Phase G atlas annotations
            if args.enrich_atlas_vulns:
                atlas_vulns_post = fetch_atlas_vuln_summary(deps, atlas_records)
                if args.sbom == "cyclonedx":
                    for c in sbom.get("components", []) or []:
                        n = (c.get("name") or "").lower()
                        av = atlas_vulns_post.get(n)
                        if not av:
                            continue
                        props = c.setdefault("properties", [])
                        for k, v in (
                            ("cdx:atlas:vuln_total", av["total"]),
                            ("cdx:atlas:vuln_critical_affecting_current",
                             av["critical_affecting_current"]),
                            ("cdx:atlas:vuln_high_affecting_current",
                             av["high_affecting_current"]),
                            ("cdx:atlas:vuln_kev_affecting_current",
                             av["kev_affecting_current"]),
                            ("cdx:atlas:vdb_scanned_at", av["scanned_at"]),
                        ):
                            props.append({"name": k, "value": str(v)})
                else:
                    for pkg in sbom.get("packages", []) or []:
                        n = (pkg.get("name") or "").lower()
                        av = atlas_vulns_post.get(n)
                        if not av:
                            continue
                        annots = pkg.setdefault("annotations", [])
                        for k, v in (
                            ("vuln_total", av["total"]),
                            ("vuln_critical_affecting_current",
                             av["critical_affecting_current"]),
                            ("vuln_high_affecting_current",
                             av["high_affecting_current"]),
                            ("vuln_kev_affecting_current",
                             av["kev_affecting_current"]),
                        ):
                            annots.append({
                                "annotationType": "OTHER",
                                "annotator": "Tool: cf_atlas Phase G",
                                "annotationDate": _dt_iso_now(),
                                "annotationComment": f"{k}={v}",
                            })
            sbom_json = json.dumps(sbom, indent=2, default=str)
            if args.sbom_out:
                Path(args.sbom_out).write_text(sbom_json)
                print(f"SBOM ({args.sbom}) written to {args.sbom_out}", file=sys.stderr)
            else:
                print(sbom_json)
        elif args.as_json:
            print(json.dumps({
                "project_dir": str(project_dir),
                "manifests": manifests_found,
                "deps": [d.__dict__ for d in deps],
                "base_images": base_images_all,
                "vulns_by_dep": vulns_by_dep,
                "atlas_records": atlas_records,
                "trivy_results": trivy_results,
                "source_status": {k: v for k, v in source_status.items() if not k.endswith("_msg")},
            }, indent=2, default=str))
        else:
            print(render(project_dir, manifests_found, deps, base_images_all,
                         vulns_by_dep, atlas_records, trivy_results,
                         source_status, args.brief))
    finally:
        if is_temp and not args.keep_clone:
            shutil.rmtree(project_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
