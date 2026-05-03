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
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
        eco = self.ecosystem if self.ecosystem in ("pypi", "conda", "npm") else "generic"
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
            # Format: https://conda.anaconda.org/conda-forge/<subdir>/<name>-<version>-<build>.conda
            m = re.search(r"/([^/]+)-([^-]+)-[^/]+\.(?:conda|tar\.bz2)$", url)
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
    for spec in project.get("dependencies") or []:
        m = re.match(r"^([A-Za-z0-9._-]+)(?:\s*[=<>~!]=?\s*([0-9][^,;\s]*))?", spec)
        if m:
            deps.append(Dep(name=m.group(1).lower(), version=m.group(2),
                            ecosystem="pypi", manifest=path.name))
    for extra_name, extras in (project.get("optional-dependencies") or {}).items():
        for spec in extras or []:
            m = re.match(r"^([A-Za-z0-9._-]+)(?:\s*[=<>~!]=?\s*([0-9][^,;\s]*))?", spec)
            if m:
                deps.append(Dep(name=m.group(1).lower(), version=m.group(2),
                                ecosystem="pypi", manifest=f"{path.name}#extras.{extra_name}"))
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
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # FROM image:tag [AS stage]
        if line.upper().startswith("FROM "):
            parts = line.split()
            if len(parts) >= 2:
                base_images.append(parts[1])
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
    args = parser.parse_args()

    source_status: dict[str, str] = {}

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

        if args.sbom:
            sys.path.insert(0, str(Path(__file__).parent))
            from _sbom import emit_cyclonedx, emit_spdx  # type: ignore[import-not-found]
            emitter = emit_cyclonedx if args.sbom == "cyclonedx" else emit_spdx
            sbom = emitter(deps, vulns_by_dep, project_name=project_dir.name,
                           atlas_records=atlas_records)
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
