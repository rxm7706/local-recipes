#!/usr/bin/env python3
"""
Generate conda-forge recipes from various sources.

Supports:
- PyPI packages
- GitHub repositories
- Local source directories
- Templates

Usage:
    python recipe-generator.py pypi requests
    python recipe-generator.py github owner/repo
    python recipe-generator.py template python-noarch --name mypackage
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Inject OS trust store before requests import so corporate CA roots are
# honored on PyPI calls in air-gapped JFrog environments. Idempotent.
try:
    import truststore  # type: ignore[import-not-found]
    truststore.inject_into_ssl()
except ImportError:
    pass

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None  # type: ignore[assignment]
    REQUESTS_AVAILABLE = False


def _pypi_to_conda_name(pypi_name: str) -> str:
    """Translate a PyPI dep name to its conda-forge equivalent.

    Routes through ``name_resolver.resolve_name`` so the local mapping
    cache (`data/pypi_conda_map.json`) and the conda-forge-metadata API
    catch the well-known divergences — e.g. PyPI ``redis`` is conda-forge
    ``redis-py``; PyPI ``soundfile`` is conda-forge ``pysoundfile``. The
    common identity case (where conda and PyPI names match) and any
    resolver failure both fall through to the input name unchanged, so
    this is safe to apply unconditionally to every emitted dep.
    """
    # Lazy import so a missing resolver / cache never breaks the
    # generator. The script directory is on sys.path because the tests
    # add it via the `load_module` fixture, and CLI invocation runs the
    # script directly with its own dir as cwd.
    try:
        from pathlib import Path as _Path
        _scripts_dir = str(_Path(__file__).resolve().parent)
        if _scripts_dir not in sys.path:
            sys.path.insert(0, _scripts_dir)
        from name_resolver import resolve_name
    except Exception:
        return pypi_name

    try:
        result = resolve_name(pypi_name)
    except Exception:
        return pypi_name

    if result.get("success") and result.get("conda_name"):
        return result["conda_name"]
    return pypi_name


@dataclass
class PackageInfo:
    """Package metadata."""
    name: str
    version: str
    summary: str = ""
    description: str = ""
    homepage: str = ""
    repository: str = ""
    documentation: str = ""
    license: str = ""
    license_file: str = "LICENSE"
    source_url: str = ""
    sha256: str = ""
    dependencies: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    python_requires: str = ">=3.10"
    author: str = ""
    build_backend: str = "setuptools" # Default to setuptools
    # v8.9.0 additions — populated from sdist inspection when available.
    import_name: str = ""               # actual top-level Python import name
    has_abi3: bool = False              # Cargo.toml declares pyo3 abi3 feature
    sys_platform_deps: dict[str, list[str]] = field(default_factory=dict)
    # ^ maps "win"/"linux"/"osx" → list of conda-mapped run deps; sourced
    # from requires_dist markers like `colorama ; sys_platform == 'win32'`.


_PEP508_NAME_SPEC_RE = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)"          # name
    r"\s*(?:\[[^\]]*\])?"                         # [extras] discarded
    r"\s*(?P<spec>[<>=!~][^;]*)?"                 # version spec (optional)
)


def _parse_requires_dist_specs(requires_dist: list[str]) -> list[str]:
    """Parse PyPI requires_dist entries into conda specifier strings.

    Preserves PEP 440 version ranges (``>=X.Y``, ``<Z``) and translates them
    into the space-separated conda form (``- pkg >=X.Y,<Z``). Skips entries
    that are extras-only (``; extra == ``) and applies these rules to env
    markers:

    * ``; extra == 'X'`` — always dropped (recipe ships the base extras only).
    * ``; sys_platform == 'win32'`` (and friends) — currently dropped; the
      caller already runs ``_classify_sys_platform_deps`` to produce a
      ``win:`` selector dict. (Future: collapse to ``if: win then:`` block.)
    * ``; python_version`` markers — kept; if multiple variants for the same
      package appear, the loosest combined range wins (so the conda solver
      can pick a version that works on every supported Python).

    Each surviving entry is then routed through ``_pypi_to_conda_name``.
    """
    # First pass: collect (conda_name, spec_str) tuples, deduplicating by name.
    by_name: dict[str, list[str]] = {}
    for raw in requires_dist:
        # Drop deps that ONLY exist under an extra (e.g. `pytest; extra == "dev"`)
        if "extra ==" in raw:
            continue
        # Strip env marker tail for spec parsing; we already filtered extras.
        # Drop sys_platform markers — handled separately by selectors.
        before_semi = raw.split(";", 1)[0]
        marker = raw[len(before_semi) + 1:] if ";" in raw else ""
        if "sys_platform" in marker or "platform_system" in marker:
            continue
        m = _PEP508_NAME_SPEC_RE.match(before_semi)
        if not m:
            continue
        pypi_name = m.group(1).lower()
        # Skip degenerate matches that captured nothing
        if not pypi_name:
            continue
        spec_raw = (m.group("spec") or "").strip()
        # Normalize whitespace inside the spec — `>=5.0 , <6` → `>=5.0,<6`
        spec = re.sub(r"\s+", "", spec_raw)
        conda_name = _pypi_to_conda_name(pypi_name)
        by_name.setdefault(conda_name, []).append(spec)

    out: list[str] = []
    for name, specs in by_name.items():
        # Drop empty-string entries; if multiple non-empty specs, take the
        # one with the LOWEST floor (loosest lower bound) so the solver can
        # pick anything ≥ that. Heuristic but covers the common variant-
        # marker case (`lxml >=4.8 (py310)` vs `lxml >=4.9 (py311)`).
        non_empty = [s for s in specs if s]
        if not non_empty:
            out.append(name)
            continue
        if len(non_empty) == 1:
            chosen = non_empty[0]
        else:
            # Pick the spec with the lowest >= bound (string-compare is OK
            # for the common case of >=N.M.P where N is single-digit).
            def _lo(s: str) -> tuple[int, ...]:
                m = re.search(r">=([\d.]+)", s)
                if not m:
                    return (0,)
                parts = m.group(1).split(".")
                try:
                    return tuple(int(p) for p in parts)
                except ValueError:
                    return (0,)
            chosen = min(non_empty, key=_lo)
        # Convert PEP 440 `>=X.Y` syntax to conda's ` >=X.Y` (space-separated)
        out.append(f"{name} {chosen}" if chosen else name)
    return out


def determine_build_backend(requires_dist: list[str]) -> str:
    """Attempt to guess the build backend from requirements if possible, else default.

    Detected backends, in priority order: hatchling, flit-core, poetry-core,
    pdm-backend, scikit-build-core, maturin. Falls back to setuptools.
    """
    for req in requires_dist:
        req_lower = req.lower()
        if "hatchling" in req_lower:
            return "hatchling"
        elif "flit" in req_lower:
            return "flit-core"
        elif "poetry" in req_lower:
            return "poetry-core"
        elif "pdm-backend" in req_lower or "pdm_backend" in req_lower:
            return "pdm-backend"
        elif "scikit-build-core" in req_lower or "scikit_build_core" in req_lower:
            return "scikit-build-core"
        elif "maturin" in req_lower:
            return "maturin"
    return "setuptools"


# conda-forge global Python floor (CFEP-25 + Aug 2025 build-matrix drop of 3.9).
# Never emit a recipe with python_min below this value, even when the upstream
# package declares a lower floor in its python_requires.
_CONDA_FORGE_PYTHON_FLOOR = "3.10"


def _resolve_python_min(python_requires: str) -> str:
    """Parse ``python_requires`` and clamp to the conda-forge floor.

    Returns the higher of the parsed ``>=X.Y`` and ``3.10``. Defaults to
    ``3.10`` when ``python_requires`` is empty or unparseable.
    """
    match = re.search(r">=\s*(\d+)\.(\d+)", python_requires or "")
    if not match:
        return _CONDA_FORGE_PYTHON_FLOOR
    detected = (int(match.group(1)), int(match.group(2)))
    floor = tuple(int(p) for p in _CONDA_FORGE_PYTHON_FLOOR.split("."))
    return ".".join(str(p) for p in max(detected, floor))


# --- v8.9.0 sdist cache + extraction helpers ----------------------------
# Driven by the conda-forge-expert v8.9.0 spec (docs/specs/conda-forge-expert-v8.9.md).
# When the generator routes a maturin/PyO3 package, several authoritative
# facts (import name, abi3 feature, [project.scripts] entry points) live in
# the sdist's pyproject.toml + Cargo.toml + src/lib.rs and are NOT exposed
# via PyPI's JSON API. We download the sdist once per run, cache it under
# /tmp, and inspect on demand.

import tarfile as _tarfile
import tempfile as _tempfile

_SDIST_CACHE_DIR = Path(_tempfile.gettempdir()) / "cfe-sdist-cache"


def _sdist_cache_path(name: str, version: str) -> Path:
    """Return where the sdist tarball is cached for (name, version)."""
    _SDIST_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", f"{name}-{version}.tar.gz")
    return _SDIST_CACHE_DIR / safe


def _ensure_sdist_cached(source_url: str, name: str, version: str) -> Path | None:
    """Download the sdist to the cache directory if not already present.

    Returns the cache path, or None when download fails. Idempotent — re-runs
    in the same generator invocation hit the cache. Network errors return
    None rather than raising so the generator can fall back to heuristics.
    """
    if not source_url or not source_url.endswith(".tar.gz"):
        return None
    target = _sdist_cache_path(name, version)
    if target.exists() and target.stat().st_size > 0:
        return target
    if not REQUESTS_AVAILABLE or requests is None:
        return None
    try:
        # Reuse the same _http auth path as fetch_pypi_info for JFrog mirrors.
        headers = {}
        try:
            from _http import auth_headers_for  # type: ignore[import-not-found]
            headers = auth_headers_for(source_url) or {}
        except ImportError:
            pass
        r = requests.get(source_url, timeout=60, headers=headers or None)
        r.raise_for_status()
        target.write_bytes(r.content)
        return target
    except Exception:  # noqa: BLE001 — network/IO failure → fallback path
        return None


def _read_sdist_files(sdist_path: Path, suffixes: tuple[str, ...]) -> dict[str, str]:
    """Return a mapping of <inside-tarball-path> → file-text for files
    whose name ends with any suffix in ``suffixes``.

    Only reads small text files (<256 KB) to bound memory. Tar layout
    assumed: ``<name>-<version>/<rest>``.
    """
    result: dict[str, str] = {}
    try:
        with _tarfile.open(sdist_path, "r:gz") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                if member.size > 256 * 1024:
                    continue
                if not any(member.name.endswith(s) for s in suffixes):
                    continue
                f = tf.extractfile(member)
                if f is None:
                    continue
                try:
                    result[member.name] = f.read().decode("utf-8", errors="replace")
                except Exception:  # noqa: BLE001
                    continue
    except (_tarfile.TarError, OSError):
        return {}
    return result


_PYMODULE_RE = re.compile(r"#\[pymodule(?:_init|\([^)]*\))?\]\s*(?:pub\s+)?fn\s+(\w+)")
_CARGO_LIB_NAME_RE = re.compile(r"^\s*name\s*=\s*\"([^\"]+)\"", re.MULTILINE)
_CARGO_ABI3_FEATURE_RE = re.compile(
    r"^\s*abi3\s*=\s*\[[^\]]*pyo3/abi3-py3\d+|^\s*default\s*=\s*\[[^\]]*\"abi3\"|"
    r"pyo3\s*=\s*\{[^}]*features\s*=\s*\[[^\]]*\"abi3-py3\d+\"",
    re.MULTILINE,
)
_PYPROJECT_BUILD_SYSTEM_RE = re.compile(
    r"\[build-system\][^\[]*?requires\s*=\s*\[([^\]]*)\]",
    re.DOTALL,
)
_PYPROJECT_SCRIPTS_RE = re.compile(
    r"\[project\.scripts\]\s*\n([^\[]*)",
    re.DOTALL,
)


def _extract_import_name_from_sdist(sdist_path: Path, distribution_name: str) -> str:
    """Return the actual top-level Python import name.

    Strategy:
    1. PyO3/maturin packages: read Cargo.toml ``[lib] name`` and verify against
       ``src/lib.rs`` ``#[pymodule] pub fn <X>()`` — both agree → that's the import.
    2. Pure-Python: find the first ``<root>/<X>/__init__.py`` path and return ``<X>``.
       Handles namespace packages by returning the deepest single-init path.
    3. Fall back to empty string when ambiguous; caller uses naive
       ``distribution_name.replace("-", "_")`` heuristic.

    Driven by SKILL.md G7 (Grayskull's inferred import name can be wrong).
    """
    files = _read_sdist_files(sdist_path, ("Cargo.toml", "lib.rs"))
    cargo_text = next((v for k, v in files.items() if k.endswith("/Cargo.toml")), "")
    librs_text = next((v for k, v in files.items() if k.endswith("/src/lib.rs")), "")
    if cargo_text:
        # Find [lib] section's name = "..." (not the package name).
        lib_section_match = re.search(r"\[lib\]\s*([^\[]*)", cargo_text, re.DOTALL)
        if lib_section_match:
            lib_name_match = _CARGO_LIB_NAME_RE.search(lib_section_match.group(1))
            if lib_name_match:
                cargo_lib_name = lib_name_match.group(1)
                if librs_text:
                    pymod = _PYMODULE_RE.search(librs_text)
                    if pymod and pymod.group(1) == cargo_lib_name:
                        return cargo_lib_name
                # Cargo says X, src/lib.rs unreadable or doesn't agree → trust Cargo.
                return cargo_lib_name
    # Pure-Python: locate __init__.py paths.
    init_files = _read_sdist_files(sdist_path, ("__init__.py",))
    if init_files:
        # Each path is like ``<name>-<version>/<module>/__init__.py`` or deeper.
        # Strip the root prefix + trailing __init__.py.
        candidates: list[str] = []
        for path in init_files:
            parts = path.split("/")
            if len(parts) < 3:
                continue
            module_parts = parts[1:-1]  # drop root + drop __init__.py
            if not module_parts:
                continue
            candidates.append(".".join(module_parts))
        if candidates:
            # Prefer the shortest (top-level) candidate — usually the package root.
            candidates.sort(key=lambda c: (c.count("."), len(c)))
            return candidates[0]
    return ""


def _extract_abi3_from_sdist(sdist_path: Path) -> bool:
    """Return True when Cargo.toml declares the pyo3 abi3 feature.

    Three forms match:
    - ``default = ["abi3"]`` + ``abi3 = ["pyo3/abi3-py3XX"]`` (feature-flag style; py-yaml12)
    - ``pyo3 = { features = ["abi3-py3XX"] }`` (inline-feature style)
    - ``abi3 = ["pyo3/abi3-py3XX"]`` (bare feature, no default — opt-in)
    """
    files = _read_sdist_files(sdist_path, ("Cargo.toml",))
    cargo_text = next((v for k, v in files.items() if k.endswith("/Cargo.toml")), "")
    if not cargo_text:
        return False
    return bool(_CARGO_ABI3_FEATURE_RE.search(cargo_text))


def _extract_build_system_requires_from_sdist(sdist_path: Path) -> list[str]:
    """Return the list of strings from pyproject.toml [build-system].requires.

    This is the authoritative source for the build backend (G2). PyPI's
    ``requires_dist`` only contains runtime deps, not build-system requires.
    """
    files = _read_sdist_files(sdist_path, ("pyproject.toml",))
    pyproject = next((v for k, v in files.items() if k.endswith("/pyproject.toml")), "")
    if not pyproject:
        return []
    match = _PYPROJECT_BUILD_SYSTEM_RE.search(pyproject)
    if not match:
        return []
    raw_list = match.group(1)
    items = re.findall(r'["\']([^"\']+)["\']', raw_list)
    return items


def _extract_entry_points_from_sdist(sdist_path: Path) -> list[str]:
    """Return console-script entry points from pyproject.toml [project.scripts].

    Format: ``["my-cli = my_package.cli:main", ...]``. Per knowledge_base,
    only console_scripts need recipe-level declaration.
    """
    files = _read_sdist_files(sdist_path, ("pyproject.toml",))
    pyproject = next((v for k, v in files.items() if k.endswith("/pyproject.toml")), "")
    if not pyproject:
        return []
    match = _PYPROJECT_SCRIPTS_RE.search(pyproject)
    if not match:
        return []
    block = match.group(1)
    points: list[str] = []
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'([A-Za-z0-9_\-.]+)\s*=\s*"([^"]+)"', line)
        if m:
            points.append(f"{m.group(1)} = {m.group(2)}")
    return points


def _build_source_url_template(name: str, version: str, sdist_filename: str) -> str:
    """Return a literal PyPI sdist URL with only ``${{ version }}`` templated.

    Matches the convention grayskull and conda-forge maintainers have adopted
    in 2026: path segments (first letter, distribution name, sdist filename
    stem) are written literally so they survive version bumps unchanged, and
    only ``${{ version }}`` interpolates. Drops the older ``${{ name[0] }}`` /
    ``${{ name }}`` / ``${{ name | replace("-", "_") }}`` chain — the literal
    form is more legible, removes a class of jinja-typo bugs, and pairs with
    the matching change to omit ``name`` from ``context:`` entirely.

    Example:
    - ``("py-yaml12", "0.1.0", "py_yaml12-0.1.0.tar.gz")`` →
      ``https://pypi.org/packages/source/p/py-yaml12/py_yaml12-${{ version }}.tar.gz``

    Returns the empty string only when the sdist filename doesn't end in the
    expected ``-<version>.tar.gz`` shape; the caller falls back to the
    concrete URL in that case.
    """
    suffix = f"-{version}.tar.gz"
    if not sdist_filename.endswith(suffix):
        return ""
    stem = sdist_filename[: -len(suffix)]
    first_letter = name[0].lower()
    return (
        f"https://pypi.org/packages/source/{first_letter}/{name}/"
        f"{stem}-${{{{ version }}}}.tar.gz"
    )


# Maturin-routing rule (G1+G2): treat the package as maturin/PyO3 when EITHER
# (a) the build_backend was detected as "maturin" by sdist [build-system].requires,
# OR (b) classifier "Programming Language :: Rust" appears AND a wheel matrix
# in releases is platform-specific. (b) is the fallback when (a) fails.
def _is_maturin_pyo3(info: dict, sdist_path: Path | None) -> bool:
    """Return True when the package should route to the maturin recipe path."""
    if sdist_path is not None:
        requires = _extract_build_system_requires_from_sdist(sdist_path)
        for r in requires:
            if "maturin" in r.lower():
                return True
    classifiers = info.get("classifiers", []) or []
    if any("Rust" in c for c in classifiers):
        # Check at least one platform-specific wheel exists in the latest release.
        version = info.get("version", "")
        # data["releases"] not visible here; signal via classifier alone (admin
        # may set it without uploading wheels, but PyPI normally requires both).
        return True
    return False


def _can_noarch_python(info: dict, build_backend: str, sdist_path: Path | None) -> tuple[bool, list[str]]:
    """Advisory check — should this recipe be ``noarch: python``?

    Returns (verdict, reasons). Verdict is True only when ALL knowledge_base
    requirements are met:
    - No compiled extensions (maturin/scikit-build-core/meson-python ⇒ False).
    - No Rust/C/C++ classifier.
    - No OS-specific markers in requires_dist that need __win/__unix selectors.
      (Note: those *can* be handled in noarch:python via virtual packages;
       this validator flags them as a hint to use the selectors-aware path.)
    """
    reasons: list[str] = []
    if build_backend in ("maturin", "scikit-build-core", "meson-python"):
        reasons.append(f"build backend {build_backend!r} produces compiled extensions")
    classifiers = info.get("classifiers", []) or []
    if any("Rust" in c for c in classifiers):
        reasons.append("'Programming Language :: Rust' classifier present")
    if any("C++" in c for c in classifiers):
        reasons.append("'Programming Language :: C++' classifier present")
    requires_dist = info.get("requires_dist") or []
    has_platform_markers = any(
        "sys_platform" in r or "platform_system" in r for r in requires_dist
    )
    if has_platform_markers:
        reasons.append("requires_dist has sys_platform markers (use __win/__unix selectors)")
    return (not reasons, reasons)


def _classify_sys_platform_deps(requires_dist: list[str]) -> dict[str, list[str]]:
    """Map sys_platform markers to platform-keyed dep lists.

    Example: ``colorama ; sys_platform == 'win32'`` → ``{"win": ["colorama"]}``.
    Used by the noarch generator to emit ``if: win / then:`` selector blocks.
    """
    result: dict[str, list[str]] = {}
    platform_map = {
        "'win32'": "win",
        '"win32"': "win",
        "'linux'": "linux",
        '"linux"': "linux",
        "'darwin'": "osx",
        '"darwin"': "osx",
    }
    for req in requires_dist:
        if "sys_platform" not in req:
            continue
        # Split spec from marker: "pkg ; sys_platform == 'win32'"
        if ";" not in req:
            continue
        spec, marker = req.split(";", 1)
        marker = marker.strip()
        m = re.search(r"sys_platform\s*==\s*(['\"][^'\"]+['\"])", marker)
        if not m:
            continue
        platform = platform_map.get(m.group(1))
        if not platform:
            continue
        pkg_match = re.match(r"^([a-zA-Z0-9_-]+)", spec.strip())
        if not pkg_match:
            continue
        conda_name = _pypi_to_conda_name(pkg_match.group(1).lower())
        result.setdefault(platform, []).append(conda_name)
    return result


# PyPI project_urls key variations seen in the wild. PEP 621 doesn't fix
# the spelling, so packages use Repository/Source/Source Code/Code interchangeably
# and Documentation/Docs interchangeably. Order matters — first match wins.
_REPOSITORY_KEYS = ("Repository", "Source", "Source Code", "Code", "GitHub", "source")
_DOCUMENTATION_KEYS = ("Documentation", "Docs", "documentation")
_HOMEPAGE_KEYS = ("Homepage", "Home", "homepage", "home")


def _extract_project_urls(info: dict) -> tuple[str, str, str]:
    """Return (homepage, repository, documentation) from PyPI ``info`` dict.

    Prefers ``info["project_urls"]`` (PEP 621 / modern packaging); falls back
    to legacy top-level ``home_page`` for homepage. Returns empty strings when
    a URL is not present rather than ``None`` so callers can plug into f-strings.
    """
    project_urls = info.get("project_urls") or {}
    if not isinstance(project_urls, dict):
        project_urls = {}

    def _pick(keys: tuple[str, ...]) -> str:
        for k in keys:
            v = project_urls.get(k)
            if v:
                return v
        return ""

    homepage = _pick(_HOMEPAGE_KEYS) or info.get("home_page") or info.get("project_url") or ""
    repository = _pick(_REPOSITORY_KEYS)
    documentation = _pick(_DOCUMENTATION_KEYS)
    return homepage, repository, documentation


def fetch_pypi_info(package_name: str, version: Optional[str] = None) -> PackageInfo:
    """Fetch package info from PyPI.

    Uses `_http.resolve_pypi_json_urls` when available so air-gapped users
    behind JFrog can route via `PYPI_JSON_BASE_URL` env or pixi
    `pypi-config.index-url`. Falls back to bare `requests` against pypi.org
    for external clones.
    """
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests library required: pip install requests")
    assert requests is not None  # for the type checker — REQUESTS_AVAILABLE implies bound

    # Try the resolver chain (JFrog → public). If _http isn't importable,
    # fall back to the original direct-pypi.org path. auth_headers_for picks
    # up JFROG_API_KEY / .netrc / GitHub-token headers so private artifactory
    # remotes that require authentication work too.
    _auth_for = None
    try:
        import sys as _sys
        from pathlib import Path as _P
        _sys.path.insert(0, str(_P(__file__).parent))
        from _http import (  # type: ignore[import-not-found]
            resolve_pypi_json_urls,
            inject_ssl_truststore,
            auth_headers_for as _auth_for,
        )
        inject_ssl_truststore()
        urls = resolve_pypi_json_urls(package_name, version)
    except ImportError:
        urls = [
            f"https://pypi.org/pypi/{package_name}/json"
            if not version
            else f"https://pypi.org/pypi/{package_name}/{version}/json"
        ]

    last_err: Exception | None = None
    data = None
    for url in urls:
        headers = _auth_for(url) if _auth_for is not None else {}
        try:
            response = requests.get(url, timeout=30, headers=headers or None)
            if response.status_code == 404:
                last_err = requests.HTTPError(f"404 at {url}")
                continue  # try next source
            response.raise_for_status()
            data = response.json()
            break
        except requests.RequestException as exc:
            last_err = exc
            continue
    if data is None:
        raise RuntimeError(
            f"Failed to fetch PyPI metadata for {package_name!r} from any of "
            f"{len(urls)} source(s); last error: {last_err}"
        )

    info = data["info"]
    version = version or info["version"]
    assert version is not None  # narrow Optional[str] for the PackageInfo init below

    # Find source distribution. Prefer sdist; fall back to wheel for
    # wheel-only packages.
    #
    # IMPORTANT: do NOT use release["url"] directly — PyPI's JSON API
    # returns the hashed files.pythonhosted.org URL (e.g.
    # /packages/86/8c/3d6c.../foo-1.0.tar.gz) which bypasses the standard
    # JFrog Artifactory PyPI Remote Repository proxy in air-gapped
    # corporate setups. Instead, construct the canonical pypi.org URL,
    # which Artifactory proxies transparently. See
    # docs/enterprise-deployment.md §3 for the full rationale.
    pkg_name = info["name"]
    first_letter = pkg_name[0].lower()
    source_url = ""           # templated URL emitted into the recipe (v8.9.1)
    concrete_source_url = ""  # literal URL used by _ensure_sdist_cached
    sha256 = ""
    for release in data["releases"].get(version, []):
        if release["packagetype"] == "sdist":
            filename = release["filename"]
            concrete_source_url = (
                f"https://pypi.org/packages/source/{first_letter}/{pkg_name}/{filename}"
            )
            # v8.9.1: emit grayskull-style interpolated URL when the filename
            # follows the normal `<stem>-<version>.tar.gz` form, so version
            # bumps only change `${{ version }}`. Falls back to the literal
            # URL when the filename doesn't parse cleanly.
            source_url = (
                _build_source_url_template(pkg_name, version, filename)
                or concrete_source_url
            )
            sha256 = release["digests"]["sha256"]
            break
    if not source_url:
        # Wheel-only fallback: synthesise a pypi.org wheel URL from the
        # first wheel in the release. The Python-tag segment (`py3`,
        # `py2.py3`, `cp310`, …) is extracted from the wheel filename per
        # PEP 425; it is upstream-specific, so a comment in the recipe
        # should flag that the URL needs revisiting on version bump.
        for release in data["releases"].get(version, []):
            if release["packagetype"] == "bdist_wheel":
                filename = release["filename"]
                # Wheel filename: <name>-<ver>(-<build>)?-<py>-<abi>-<plat>.whl
                stem = filename.removesuffix(".whl")
                parts = stem.split("-")
                if len(parts) >= 5:
                    py_tag = parts[-3]
                    source_url = f"https://pypi.org/packages/{py_tag}/{first_letter}/{pkg_name}/{filename}"
                    sha256 = release["digests"]["sha256"]
                    break

    # Parse dependencies. Each PyPI dep name is routed through
    # `_pypi_to_conda_name` so well-known PyPI↔conda-forge name
    # divergences (e.g. PyPI `redis` → conda-forge `redis-py`,
    # PyPI `soundfile` → conda-forge `pysoundfile`) are translated
    # automatically. Identity-mapped names pass through unchanged.
    #
    # v8.10.1: capture PEP 508 version specifiers (>=X, <Y) so upstream's
    # declared compatibility ranges flow into the recipe. Previously only
    # the bare package name was extracted, producing `- django` instead of
    # `- django >=5.0` — breaks downstream solvers and triggers reviewer
    # comments. Also handles `; python_version >= 'X'` env markers by
    # collapsing variant entries into a single conda spec (loosest range).
    requires_dist = info.get("requires_dist") or []
    dependencies = _parse_requires_dist_specs(requires_dist)

    # v8.9.0: download sdist for authoritative metadata when source_url is available.
    # This unlocks: maturin detection from pyproject.toml [build-system].requires,
    # accurate import-name from Cargo.toml [lib] / __init__.py, abi3 feature detection,
    # [project.scripts] entry-point extraction.
    # Download via the CONCRETE url; recipe-emitted `source_url` may be templated.
    sdist_path = (
        _ensure_sdist_cached(concrete_source_url, info["name"], version)
        if concrete_source_url
        else None
    )

    # Prefer pyproject.toml [build-system].requires when sdist is available (G2 fix).
    build_backend = "setuptools"
    if sdist_path is not None:
        build_system_requires = _extract_build_system_requires_from_sdist(sdist_path)
        if build_system_requires:
            build_backend = determine_build_backend(build_system_requires)
    if build_backend == "setuptools":
        # Fallback: check classifiers + requires_dist heuristic (legacy path).
        build_backend = determine_build_backend(requires_dist)
    # Maturin override via classifier (G1 disambiguation): if Rust classifier
    # is present but build_backend didn't match maturin from requires, force it.
    classifiers = info.get("classifiers", []) or []
    if build_backend == "setuptools" and any("Rust" in c for c in classifiers):
        if sdist_path is not None:
            # Confirm by looking for src/lib.rs + Cargo.toml in the sdist.
            cargo_files = _read_sdist_files(sdist_path, ("Cargo.toml",))
            if cargo_files:
                build_backend = "maturin"

    # Parse python_requires
    python_requires = info.get("requires_python", ">=3.10") or ">=3.10"

    # Entry points from sdist's [project.scripts] (G4 / Wave D S18).
    entry_points = _extract_entry_points_from_sdist(sdist_path) if sdist_path else []

    # Import name from sdist (G4 / SKILL.md G7 canonical fix).
    import_name = ""
    if sdist_path is not None:
        import_name = _extract_import_name_from_sdist(sdist_path, info["name"])

    # abi3 detection for PyO3 packages (Wave B / G3.c gated emission).
    has_abi3 = bool(sdist_path and _extract_abi3_from_sdist(sdist_path))

    # OS-conditional run deps from sys_platform markers (Wave D / S16).
    sys_platform_deps = _classify_sys_platform_deps(requires_dist)

    homepage, repository, documentation = _extract_project_urls(info)

    return PackageInfo(
        name=info["name"],
        version=version,
        summary=info.get("summary", ""),
        description=info.get("description", "")[:500],
        homepage=homepage,
        repository=repository,
        documentation=documentation,
        license=info.get("license", ""),
        source_url=source_url,
        sha256=sha256,
        dependencies=dependencies,
        entry_points=entry_points,
        python_requires=python_requires,
        author=info.get("author", ""),
        build_backend=build_backend,
        import_name=import_name,
        has_abi3=has_abi3,
        sys_platform_deps=sys_platform_deps,
    )


def generate_recipe_yaml(info: PackageInfo, output_dir: Path) -> Path:
    """Generate recipe.yaml (v1 format).

    Aligned with conda-forge.org/docs/maintainer/example_recipes/pure-python/
    (May 2026). Notable choices:

    - ``python_min`` is emitted in ``context:`` only when > 3.10. At the
      conda-forge floor the default from ``conda-forge-pinning`` is used,
      so an explicit declaration is no-op churn.
    - ``tests[].python.python_version`` uses the CFEP-25 dual-version
      ``[${{ python_min }}.*, "*"]`` list (staged-recipes#32857 r3039190932)
      so both the floor and the top of the build matrix are exercised.
    - ``about:`` emits ``description``, ``repository``, ``documentation``
      when the PyPI metadata exposes them via project_urls.
    - **v8.9.0**: routes maturin/PyO3 packages to ``_generate_maturin_recipe_yaml``
      instead of producing an incorrect ``noarch: python`` recipe.
    """
    # v8.9.0: route to maturin-pyo3 path when detected. The maturin generator
    # produces a compiled-extension recipe (no noarch, Rust toolchain in build,
    # maturin in host) modelled on the phonors PR pattern (modal 27-PR sample).
    if info.build_backend == "maturin":
        return _generate_maturin_recipe_yaml(info, output_dir)

    # Parse python_min from python_requires, then clamp to the conda-forge
    # floor (3.10) — Python 3.9 was dropped from the build matrix in Aug 2025
    # so any upstream-declared floor below 3.10 is moot for conda-forge.
    python_min = _resolve_python_min(info.python_requires)
    # CFEP-25 floor: only declare in context when overriding the default 3.10.
    context_python_min_line = f'  python_min: "{python_min}"\n' if python_min != "3.10" else ""

    # Canonical 2026 shape: ``context:`` only carries ``version`` (+ optional
    # ``python_min`` override); ``package.name`` is the literal distribution
    # name; ``source.url`` interpolates only ``${{ version }}``. Matches what
    # current grayskull emits and what conda-forge reviewers expect.
    literal_name = info.name.lower()
    fallback_url = (
        f"https://pypi.org/packages/source/{literal_name[0]}/{literal_name}/"
        f"{literal_name}-${{{{ version }}}}.tar.gz"
    )
    recipe = f'''# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1

context:
  version: "{info.version}"
{context_python_min_line}
package:
  name: {literal_name}
  version: ${{{{ version }}}}

source:
  url: {info.source_url or fallback_url}
  sha256: {info.sha256 or "REPLACE_SHA256"}

build:
  number: 0
  noarch: python
  script: ${{{{ PYTHON }}}} -m pip install . -vv --no-deps --no-build-isolation

requirements:
  host:
    - python ${{{{ python_min }}}}.*
    - pip
    - {info.build_backend}
  run:
    - python >=${{{{ python_min }}}}
'''

    # Add dependencies
    for dep in info.dependencies[:10]:  # Limit to avoid huge lists
        recipe += f"    - {dep}\n"

    # v8.9.0: emit OS-conditional run deps when requires_dist had sys_platform markers.
    if info.sys_platform_deps:
        # Insert virtual-package selector block before the closing of run section.
        for platform, deps in info.sys_platform_deps.items():
            recipe += f"    - if: {platform}\n      then:\n"
            for dep in deps:
                recipe += f"        - {dep}\n"

    # v8.9.0: prefer extracted import_name from sdist (G7 fix); fall back to heuristic.
    import_name = info.import_name or info.name.replace("-", "_").lower()

    recipe += f'''
tests:
  - python:
      imports:
        - {import_name}
      pip_check: true
      python_version:
        - ${{{{ python_min }}}}.*
        - "*"

about:
  homepage: {info.homepage or "REPLACE_HOMEPAGE"}
  license: {info.license or "REPLACE_LICENSE"}
  license_file: {info.license_file}
  summary: {info.summary or "REPLACE_SUMMARY"}
  description: |
    {info.summary or "REPLACE_DESCRIPTION"}
'''
    if info.repository:
        recipe += f"  repository: {info.repository}\n"
    if info.documentation:
        recipe += f"  documentation: {info.documentation}\n"

    recipe += '''
extra:
  recipe-maintainers:
    - REPLACE_MAINTAINER
'''

    # Write recipe
    output_dir.mkdir(parents=True, exist_ok=True)
    recipe_path = output_dir / "recipe.yaml"
    recipe_path.write_text(recipe)

    return recipe_path


def _generate_maturin_recipe_yaml(info: PackageInfo, output_dir: Path) -> Path:
    """Generate a maturin/PyO3 recipe.yaml (v8.9.0).

    Models the **phonors** pattern (modal 27-PR PyO3 sample):
    - No ``noarch: python`` (compiled extension is platform-specific).
    - Build deps: ``${{ stdlib('c') }}``, ``${{ compiler('c') }}``,
      ``${{ compiler('rust') }}``, ``cargo-bundle-licenses``.
    - Host deps: ``maturin >=1.7,<2.0``, ``pip``, ``python``.
    - Script: 2-liner (``cargo-bundle-licenses`` + ``pip install``).
    - ``THIRDPARTY.yml`` added to ``about.license_file``.
    - ``build.python.version_independent: true`` emitted ONLY when sdist's
      Cargo.toml declares the abi3 feature (info.has_abi3 = True).
    - No Windows CARGO_HOME block (0/25 CLI Rust adoption + 1/27 PyO3
      adoption with package-specific cause; not canonical).
    - No CFEP-25 dual-version test matrix (1/27 PyO3 adoption; the build
      matrix already exercises each Python version).
    """
    python_min = _resolve_python_min(info.python_requires)
    context_python_min_line = f'  python_min: "{python_min}"\n' if python_min != "3.10" else ""

    # Source URL: sdist filename may use underscore-form even when PyPI name uses hyphens.
    # Prefer the actual filename from info.source_url; otherwise synthesise a
    # literal URL with only ``${{ version }}`` templated (matches the 2026
    # grayskull / conda-forge convention).
    literal_name = info.name.lower()
    fallback_url = (
        f"https://pypi.org/packages/source/{literal_name[0]}/{literal_name}/"
        f"{literal_name.replace('-', '_')}-${{{{ version }}}}.tar.gz"
    )
    source_url = info.source_url or fallback_url

    # version_independent block: gated on Cargo.toml abi3 feature (v8.9.0 G3.c).
    # Includes the trailing blank line that separates the `build:` section
    # from `requirements:` in the assembled f-string when this block is emitted.
    version_independent_block = ""
    if info.has_abi3:
        version_independent_block = (
            "  python:\n"
            "    # Cargo.toml declares pyo3 abi3 feature — wheel is\n"
            "    # CPython-stable-ABI and works across Python versions.\n"
            "    version_independent: true\n"
            "\n"
        )
    else:
        version_independent_block = "\n"

    recipe = f'''# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
# Generated from python-maturin path; PyO3/maturin detected via sdist
# pyproject.toml [build-system].requires. Modelled on phonors PR pattern
# (modal 27-PR PyO3 sample, Mar 2020 – May 2026). Recipe shape follows the
# 2026 grayskull / conda-forge convention: literal ``package.name``, literal
# ``source.url`` (only ``${{ version }}`` templated), no ``name`` in context.
schema_version: 1

context:
  version: "{info.version}"
{context_python_min_line}
package:
  name: {literal_name}
  version: ${{{{ version }}}}

source:
  url: {source_url}
  sha256: {info.sha256 or "REPLACE_SHA256"}

build:
  number: 0
  script:
    env:
      # Per conda-forge.org/docs/maintainer/example_recipes/rust/ — applies to
      # any Rust build (CLI binary OR maturin/PyO3 cdylib). maturin invokes
      # cargo build internally and inherits these env vars.
      CARGO_PROFILE_RELEASE_STRIP: symbols
      CARGO_PROFILE_RELEASE_LTO: fat
    content:
      - cargo-bundle-licenses --format yaml --output THIRDPARTY.yml
      - ${{{{ PYTHON }}}} -m pip install . -vv --no-deps --no-build-isolation
{version_independent_block}requirements:
  build:
    - if: build_platform != target_platform
      then:
        - python
        - cross-python_${{{{ target_platform }}}}
        - crossenv
        - maturin >=1,<2
    - ${{{{ compiler("c") }}}}
    - ${{{{ stdlib("c") }}}}
    - ${{{{ compiler("rust") }}}}
    - cargo-bundle-licenses
  host:
    - python
    - pip
    - maturin >=1.7,<2.0
  run:
    - python
'''

    # Add runtime dependencies (skip optional/extra markers).
    for dep in info.dependencies[:10]:
        recipe += f"    - {dep}\n"

    # Prefer sdist-extracted import_name (G4 fix). For maturin packages this is
    # nearly always different from the PyPI distribution name (e.g. py-yaml12 → yaml12).
    import_name = info.import_name or info.name.replace("-", "_").lower()

    recipe += f'''
tests:
  - python:
      imports:
        - {import_name}
      pip_check: true

about:
  homepage: {info.homepage or "REPLACE_HOMEPAGE"}
  license: {info.license or "REPLACE_LICENSE"}
  license_file:
    - LICENSE
    - THIRDPARTY.yml
  summary: {info.summary or "REPLACE_SUMMARY"}
  description: |
    {info.summary or "REPLACE_DESCRIPTION"}
'''
    if info.repository:
        recipe += f"  repository: {info.repository}\n"
    if info.documentation:
        recipe += f"  documentation: {info.documentation}\n"

    recipe += '''
extra:
  recipe-maintainers:
    - REPLACE_MAINTAINER
'''

    output_dir.mkdir(parents=True, exist_ok=True)
    recipe_path = output_dir / "recipe.yaml"
    recipe_path.write_text(recipe)
    return recipe_path


def generate_meta_yaml(info: PackageInfo, output_dir: Path) -> Path:
    """Generate meta.yaml (legacy v0 format).

    Mirrors the v1 ``generate_recipe_yaml`` patterns where v0 syntax supports
    them: emits ``{% set python_min %}`` only when above the 3.10 floor,
    includes ``description``/``dev_url``/``doc_url`` from project_urls, and
    uses the CFEP-25 dual-version test stanza via the conda-build ``test.requires``
    machinery (``python ={python_min}`` for the floor build).
    """
    python_min = _resolve_python_min(info.python_requires)
    # Only declare ``python_min`` jinja var when overriding the 3.10 default.
    set_python_min_line = (
        f'{{% set python_min = "{python_min}" %}}\n' if python_min != "3.10" else ""
    )
    # In v0 the python_min jinja variable defaults to 3.10 from conda-forge-pinning
    # via the recipe's CBC; when omitted from the recipe, fall through to using
    # the literal floor in the run requirement so the recipe remains valid even
    # without a CBC override.
    py_host = "{{ python_min }}" if set_python_min_line else "3.10"
    py_run = "{{ python_min }}" if set_python_min_line else "3.10"

    # ``info.source_url`` carries v1 ``${{ version }}`` syntax; translate
    # to v0 ``{{ version }}`` so the meta.yaml renders correctly under
    # conda-build's jinja.
    v0_source_url = (info.source_url or "").replace("${{ version }}", "{{ version }}")
    v0_fallback = (
        "https://pypi.org/packages/source/"
        f"{{{{ name[0] }}}}/{{{{ name }}}}/"
        f"{{{{ name }}}}-{{{{ version }}}}.tar.gz"
    )
    recipe = f'''{{% set name = "{info.name}" %}}
{{% set version = "{info.version}" %}}
{set_python_min_line}
package:
  name: {{{{ name|lower }}}}
  version: {{{{ version }}}}

source:
  url: {v0_source_url or v0_fallback}
  sha256: {info.sha256 or "REPLACE_SHA256"}

build:
  number: 0
  noarch: python
  script: {{{{ PYTHON }}}} -m pip install . -vv --no-deps --no-build-isolation

requirements:
  host:
    - python {py_host}
    - pip
    - {info.build_backend}
  run:
    - python >={py_run}
'''

    for dep in info.dependencies[:10]:
        recipe += f"    - {dep}\n"

    recipe += f'''
test:
  imports:
    - {info.name.replace("-", "_").lower()}
  commands:
    - pip check
  requires:
    - pip
    - python {py_host}

about:
  home: {info.homepage or "REPLACE_HOMEPAGE"}
  license: {info.license or "REPLACE_LICENSE"}
  license_file: {info.license_file}
  summary: {info.summary or "REPLACE_SUMMARY"}
  description: |
    {info.summary or "REPLACE_DESCRIPTION"}'''
    if info.repository:
        recipe += f"\n  dev_url: {info.repository}"
    if info.documentation:
        recipe += f"\n  doc_url: {info.documentation}"
    recipe += '''

extra:
  recipe-maintainers:
    - REPLACE_MAINTAINER
'''

    output_dir.mkdir(parents=True, exist_ok=True)
    recipe_path = output_dir / "meta.yaml"
    recipe_path.write_text(recipe)

    return recipe_path


def copy_template(template_name: str, output_dir: Path, **replacements) -> Path:
    """Copy and customize a template."""
    # Find template
    skill_dir = Path(__file__).parent.parent
    templates_dir = skill_dir / "templates"

    # Map template names to files
    template_map = {
        "python-noarch": "python/noarch-recipe.yaml",
        "python-compiled": "python/compiled-recipe.yaml",
        "python-maturin": "python/maturin-recipe.yaml",
        "rust-cli": "rust/cli-recipe.yaml",
        "go-pure": "go/pure-recipe.yaml",
        "go-cgo": "go/cgo-recipe.yaml",
        "c-cmake": "c-cpp/cmake-recipe.yaml",
    }

    template_path = templates_dir / template_map.get(template_name, f"{template_name}.yaml")

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_name}")

    content = template_path.read_text()

    # Apply replacements
    for key, value in replacements.items():
        content = content.replace(f"REPLACE_{key.upper()}", str(value))

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "recipe.yaml"
    output_path.write_text(content)

    return output_path


@dataclass
class NpmPackageInfo:
    """npm package metadata extracted from registry.npmjs.org."""
    # Naming. ``raw_name`` is the npm name as the user typed it (may include
    # ``@scope/`` prefix); ``conda_name`` is the conda-forge package name (the
    # un-scoped basename per CFEP-26 / canonical pattern).
    raw_name: str  # e.g. "@openai/codex"
    conda_name: str  # e.g. "codex"
    version: str
    description: str = ""
    readme_excerpt: str = ""
    license: str = ""
    homepage: str = ""
    repository_url: str = ""
    bugs_url: str = ""
    documentation_url: str = ""
    # Source tarball. ``tarball_url`` is the npm registry URL; ``tarball_filename``
    # is what the file is named once it lands in SRC_DIR (e.g. ``openai-codex-1.2.3.tgz``
    # for ``@openai/codex``, ``husky-9.1.5.tgz`` for plain ``husky``).
    tarball_url: str = ""
    tarball_filename: str = ""
    # Source URL emitted into recipe.yaml. Defaults to the npm registry tarball
    # (canonical conda-forge pattern); only differs if --source github is used.
    source_url: str = ""
    sha256: str = ""
    license_filename: str = "LICENSE"  # detected from the tarball; falls back to LICENSE
    bin_entries: dict = field(default_factory=dict)
    node_major: int = 20
    is_scoped: bool = False
    is_github_source: bool = False  # True only when --source github was used
    has_runtime_deps: bool = True   # True when npm metadata declares dependencies
    has_native_build: bool = False  # True when package.json declares gypfile or node-gyp install

    @property
    def name(self) -> str:
        """Backwards-compat alias used by older tests."""
        return self.conda_name


def _normalize_repo_url(repo_field) -> str:
    """Convert npm's repository field into a plain https github.com URL."""
    if not repo_field:
        return ""
    if isinstance(repo_field, str):
        url = repo_field
    elif isinstance(repo_field, dict):
        url = repo_field.get("url", "")
    else:
        return ""
    # Strip git+ prefix and .git suffix; convert ssh form
    url = re.sub(r"^git\+", "", url)
    url = re.sub(r"^git:", "https:", url)
    url = re.sub(r"\.git$", "", url)
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url[len("git@github.com:"):]
    return url


def _strip_url_fragment(url: str) -> str:
    """Remove '#readme' / '#anchor' fragments from a URL."""
    if not url:
        return ""
    return url.split("#", 1)[0].rstrip("/")


# Common SPDX identifiers that match what npm packages typically declare.
# This is not exhaustive — it covers the long tail of recipes well enough
# that we can tell strict-SPDX from non-strict.
_SPDX_KNOWN = frozenset({
    "0BSD", "AFL-2.0", "AGPL-3.0-only", "AGPL-3.0-or-later",
    "Apache-1.1", "Apache-2.0", "Artistic-1.0", "Artistic-2.0",
    "BSD-1-Clause", "BSD-2-Clause", "BSD-3-Clause", "BSD-3-Clause-Clear",
    "BSD-4-Clause", "BSL-1.0", "CC-BY-3.0", "CC-BY-4.0", "CC-BY-SA-3.0",
    "CC-BY-SA-4.0", "CC0-1.0", "CDDL-1.0", "CDDL-1.1",
    "CECILL-2.1", "CECILL-B", "CECILL-C", "CPL-1.0",
    "ECL-2.0", "EPL-1.0", "EPL-2.0", "EUPL-1.1", "EUPL-1.2",
    "GFDL-1.3-only", "GFDL-1.3-or-later",
    "GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only", "GPL-3.0-or-later",
    "ISC", "LGPL-2.0-only", "LGPL-2.0-or-later", "LGPL-2.1-only",
    "LGPL-2.1-or-later", "LGPL-3.0-only", "LGPL-3.0-or-later",
    "LPPL-1.3c", "MIT", "MIT-0", "MPL-1.0", "MPL-1.1", "MPL-2.0",
    "MS-PL", "MS-RL", "NCSA", "OFL-1.1", "OSL-2.1", "OSL-3.0",
    "PostgreSQL", "Python-2.0", "Ruby", "SISSL", "Sleepycat",
    "TCL", "Unlicense", "UPL-1.0", "Vim", "W3C", "WTFPL",
    "X11", "Zlib", "ZPL-2.0", "ZPL-2.1",
})

# npm packages routinely use these non-strict labels. Map to the most
# likely SPDX identifier.
_SPDX_FIXUPS = {
    "apache 2.0": "Apache-2.0",
    "apache-2": "Apache-2.0",
    "apache2": "Apache-2.0",
    "bsd": "BSD-3-Clause",
    "bsd2": "BSD-2-Clause",
    "bsd3": "BSD-3-Clause",
    "gpl": "GPL-3.0-or-later",
    "gpl2": "GPL-2.0-or-later",
    "gpl3": "GPL-3.0-or-later",
    "gplv2": "GPL-2.0-or-later",
    "gplv3": "GPL-3.0-or-later",
    "lgpl": "LGPL-3.0-or-later",
    "mit license": "MIT",
}


def _check_spdx_license(license_str: str) -> tuple[str, str | None]:
    """Validate an npm-reported license against common SPDX identifiers.

    Returns (final_license, warning_message_or_None). If the license is
    already SPDX-canonical or a well-known compound expression (e.g.
    "(MIT OR Apache-2.0)"), we return it unchanged. If it's a known
    non-strict label (e.g. "Apache 2.0"), we suggest the SPDX form via the
    warning but keep the original — the user can decide whether to accept
    the suggestion.
    """
    if not license_str:
        return license_str, None
    stripped = license_str.strip()
    # SPDX expressions look like "(MIT OR Apache-2.0)" — accept compound
    # forms wholesale; conda-forge's linter validates the components.
    if "(" in stripped and ")" in stripped:
        return stripped, None
    if stripped in _SPDX_KNOWN:
        return stripped, None
    suggestion = _SPDX_FIXUPS.get(stripped.lower())
    if suggestion:
        return stripped, (
            f"npm-reported license {stripped!r} is not a strict SPDX "
            f"identifier — conda-forge expects {suggestion!r}. "
            f"The recipe will keep {stripped!r}; consider replacing it "
            f"manually."
        )
    return stripped, (
        f"npm-reported license {stripped!r} is not in the common SPDX list. "
        f"Verify against https://spdx.org/licenses/ before submitting."
    )


_MARKDOWN_NOISE_RE = re.compile(
    r"^\s*(?:"
    r"!\[[^\]]*\]\([^)]*\)"               # bare images:        ![alt](url)
    r"|\[!\[[^\]]*\]\([^)]*\)\][^\n]*"     # linked badges:      [![alt](src)](href)
    r"|<img[^>]*>"                         # raw HTML images
    r"|<a[^>]*>\s*<img[^>]*>\s*</a>"       # html link-wrapped images
    r"|<p[^>]*>|</p>|<div[^>]*>|</div>"    # html block tags
    r"|<br\s*/?>|<hr\s*/?>"                # html breaks/rules
    r")\s*$",
    re.IGNORECASE,
)


def _extract_readme_paragraph(raw_readme: str, *, max_length: int = 700) -> str:
    """Pull a clean prose paragraph from a markdown readme.

    Skips ATX headings, image/badge lines, and HTML wrappers. Returns the
    first paragraph that contains real prose (truncated to ``max_length``).
    Returns ``""`` if no prose paragraph is found.
    """
    if not raw_readme:
        return ""

    paragraphs = re.split(r"\n\s*\n", raw_readme)
    for para in paragraphs:
        # Drop heading/noise lines, then check if anything substantive remains
        kept_lines = []
        for line in para.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue  # ATX heading
            if _MARKDOWN_NOISE_RE.match(stripped):
                continue
            kept_lines.append(stripped)
        if not kept_lines:
            continue
        text = " ".join(kept_lines).strip()
        # A paragraph that's just a single URL or shorter than 20 chars is
        # rarely useful — skip and try the next one.
        if len(text) < 20 or re.match(r"^https?://\S+$", text):
            continue
        if len(text) > max_length:
            text = text[: max_length - 3].rstrip() + "..."
        return text
    return ""


def _parse_node_major(engine_constraint: str) -> int:
    """Extract the major version from an npm engines.node string.

    >>> _parse_node_major(">=20.0.0")
    20
    >>> _parse_node_major("^18.17.0")
    18
    >>> _parse_node_major("")
    20
    """
    if not engine_constraint:
        return 20
    match = re.search(r"(\d+)", engine_constraint)
    if not match:
        return 20
    major = int(match.group(1))
    # Conda-forge nodejs LTS floor is 20; clamp anything older.
    return max(major, 20)


_LICENSE_FILE_PRIORITY = [
    "LICENSE", "LICENSE.txt", "LICENSE.md",
    "LICENSE-MIT", "LICENSE-APACHE", "LICENSE.MIT", "LICENSE.APACHE",
    "LICENCE", "LICENCE.md", "LICENCE.txt",  # British spelling
    "COPYING", "COPYING.txt", "COPYING.md",
]


def _detect_license_filename(tar_bytes: bytes) -> str | None:
    """Inspect a tarball's member list and return the actual license filename
    (e.g. ``LICENSE.md``), or None if no recognisable license file is found.

    Handles both npm-style tarballs (top-level ``package/``) and GitHub
    release tarballs (top-level ``<repo>-<version>/``).
    """
    import io
    import tarfile

    try:
        # Most npm/github tarballs are gzip-compressed
        tf = tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:*")
    except (tarfile.ReadError, OSError):
        return None

    try:
        # Map from upper-case basename → actual basename, preserving the first
        # match (in case the same filename appears multiple times).
        seen: dict[str, str] = {}
        for member in tf.getmembers():
            if not member.isfile():
                continue
            # `member.name` looks like ``package/LICENSE`` or
            # ``BMAD-METHOD-6.4.0/LICENSE.md``. We only care about top-level
            # license files (one segment of nesting).
            parts = member.name.split("/")
            if len(parts) != 2:
                continue
            basename = parts[1]
            seen.setdefault(basename.upper(), basename)

        for candidate in _LICENSE_FILE_PRIORITY:
            if candidate.upper() in seen:
                return seen[candidate.upper()]

        # Fallback: any file whose upper-case name starts with LICENSE/LICENCE/COPYING
        for upper, actual in seen.items():
            if upper.startswith(("LICENSE", "LICENCE", "COPYING")):
                return actual
    finally:
        tf.close()
    return None


def _fetch_tarball_bytes(url: str) -> bytes:
    """Download a tarball into memory, or return b'' on failure."""
    if not REQUESTS_AVAILABLE:
        return b""
    assert requests is not None
    try:
        resp = requests.get(url, timeout=180)
        resp.raise_for_status()
        return resp.content
    except requests.RequestException as exc:
        print(f"Warning: could not fetch {url}: {exc}", file=sys.stderr)
        return b""


def _hash_tarball(url: str) -> str:
    """Compute sha256 of a remote tarball, or '' on failure.

    Kept for back-compat with callers that don't need license detection.
    """
    data = _fetch_tarball_bytes(url)
    if not data:
        return ""
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _hash_and_inspect_tarball(url: str) -> tuple[str, str | None]:
    """Download a tarball once and return (sha256, license_filename).

    ``license_filename`` is None when no recognisable license file is found
    (caller falls back to the default ``LICENSE``).
    """
    data = _fetch_tarball_bytes(url)
    if not data:
        return "", None
    import hashlib
    sha = hashlib.sha256(data).hexdigest()
    license_name = _detect_license_filename(data)
    return sha, license_name


def _parse_npm_name(raw: str) -> tuple[str, str, bool]:
    """Split an npm package name into (raw, conda_name, is_scoped).

    ``@openai/codex`` → (``@openai/codex``, ``codex``, True)
    ``husky``        → (``husky``, ``husky``, False)
    """
    if raw.startswith("@") and "/" in raw:
        _, basename = raw.split("/", 1)
        return raw, basename, True
    return raw, raw, False


def _npm_tarball_filename(raw_name: str, version: str) -> str:
    """The filename `npm pack` produces when you run it on this package.

    ``@openai/codex@1.2.3`` → ``openai-codex-1.2.3.tgz``  (scope-name)
    ``husky@9.1.5``         → ``husky-9.1.5.tgz``
    """
    if raw_name.startswith("@") and "/" in raw_name:
        scope, basename = raw_name[1:].split("/", 1)
        return f"{scope}-{basename}-{version}.tgz"
    return f"{raw_name}-{version}.tgz"


def _template_npm_source_url(url: str, version: str) -> str:
    """Replace the literal version in an npm-source tarball URL with the
    ``${{ version }}`` template so autotick-style ``context.version`` bumps
    actually flow through to ``source.url``.

    Handles the two URL shapes the npm path emits:
      - npm registry: ``.../-/<basename>-<version>.tgz``
      - GitHub archive (when ``--source github``): ``.../v<version>.tar.gz``

    Falls back to the literal URL if neither suffix matches — autotick will
    still recompute the hash, but the URL will not auto-bump. Better than
    silently mangling an unrecognized URL shape.
    """
    npm_suffix = f"-{version}.tgz"
    if url.endswith(npm_suffix):
        return url[: -len(npm_suffix)] + "-${{ version }}.tgz"
    gh_suffix = f"v{version}.tar.gz"
    if url.endswith(gh_suffix):
        return url[: -len(gh_suffix)] + "v${{ version }}.tar.gz"
    return url


def _template_npm_tarball_filename(filename: str, version: str) -> str:
    """Replace the literal version in an ``npm pack`` output filename with
    the ``${PKG_VERSION}`` env var (injected by rattler-build into build
    scripts), so ``build.sh`` survives version bumps.

    ``bmalph-2.11.0.tgz``           → ``bmalph-${PKG_VERSION}.tgz``
    ``openai-codex-1.2.3.tgz``      → ``openai-codex-${PKG_VERSION}.tgz``
    """
    suffix = f"-{version}.tgz"
    if filename.endswith(suffix):
        return filename[: -len(suffix)] + "-${PKG_VERSION}.tgz"
    return filename


def fetch_npm_info(
    package_name: str,
    version: Optional[str] = None,
    *,
    source: str = "npm",
) -> NpmPackageInfo:
    """Fetch package metadata from the npm registry.

    Uses `_http.resolve_npm_urls` when available so air-gapped users behind
    JFrog can route via `NPM_BASE_URL` env or the npm CLI standard
    `npm_config_registry` env. Falls back to bare `requests` against
    `registry.npmjs.org` for external clones.

    ``source`` selects which tarball is referenced in the generated recipe:
      - ``"npm"`` (default, canonical): the npm registry tarball. Matches the
        pattern used by 5/6 merged staged-recipes nodejs PRs.
      - ``"github"``: force GitHub release tarball (use when the package
        isn't published to npm or the upstream prefers it).
      - ``"auto"``: GitHub release if ``repository`` is on github.com,
        otherwise npm registry. Legacy behavior; kept for back-compat.

    Network required.
    """
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests library required: pip install requests")
    assert requests is not None

    raw_name, conda_name, is_scoped = _parse_npm_name(package_name)

    # Try the resolver chain (JFrog → public). If _http isn't importable,
    # fall back to the original direct-registry.npmjs.org path.
    _auth_for = None
    try:
        import sys as _sys
        from pathlib import Path as _P
        _sys.path.insert(0, str(_P(__file__).parent))
        from _http import (  # type: ignore[import-not-found]
            resolve_npm_urls,
            inject_ssl_truststore,
            auth_headers_for as _auth_for,
        )
        inject_ssl_truststore()
        urls = resolve_npm_urls(raw_name)
    except ImportError:
        urls = [f"https://registry.npmjs.org/{raw_name}"]

    last_err: Exception | None = None
    data = None
    for url in urls:
        headers = _auth_for(url) if _auth_for is not None else {}
        try:
            response = requests.get(url, timeout=30, headers=headers or None)
            if response.status_code == 404:
                last_err = requests.HTTPError(f"404 at {url}")
                continue  # try next source
            response.raise_for_status()
            data = response.json()
            break
        except requests.RequestException as exc:
            last_err = exc
            continue
    if data is None:
        raise RuntimeError(
            f"Failed to fetch npm metadata for {raw_name!r} from any of "
            f"{len(urls)} source(s); last error: {last_err}"
        )

    if version is None:
        version = data["dist-tags"]["latest"]
    assert version is not None  # narrow Optional[str] for downstream calls
    if version not in data["versions"]:
        raise ValueError(f"npm: version {version!r} of {raw_name!r} not found")

    v = data["versions"][version]

    # Bin entries — npm allows {command: path} OR string (single-bin shortcut)
    bin_entries: dict = {}
    raw_bin = v.get("bin")
    if isinstance(raw_bin, dict):
        bin_entries = raw_bin
    elif isinstance(raw_bin, str):
        bin_entries = {conda_name: raw_bin}

    tarball_url = v.get("dist", {}).get("tarball", "")
    repository_url = _normalize_repo_url(v.get("repository"))
    homepage = _strip_url_fragment(v.get("homepage", ""))
    bugs = v.get("bugs")
    bugs_url = bugs.get("url", "") if isinstance(bugs, dict) else ""

    is_github_repo = bool(repository_url) and "github.com/" in repository_url
    if source == "github" and not is_github_repo:
        raise ValueError(
            f"npm: --source github requested but {raw_name} has no "
            f"github.com repository in its npm metadata."
        )
    if source == "auto":
        prefer_github = is_github_repo
    elif source == "github":
        prefer_github = True
    else:  # source == "npm"
        prefer_github = False

    if prefer_github:
        concrete_source_url = f"{repository_url}/archive/refs/tags/v{version}.tar.gz"
        sha256, license_filename = _hash_and_inspect_tarball(concrete_source_url)
        source_url = _template_npm_source_url(concrete_source_url, version)
    else:
        source_url = _template_npm_source_url(tarball_url, version) if tarball_url else ""
        if tarball_url:
            sha256, license_filename = _hash_and_inspect_tarball(tarball_url)
        else:
            sha256, license_filename = "", None

    node_major = _parse_node_major((v.get("engines") or {}).get("node", ""))

    readme_excerpt = _extract_readme_paragraph(data.get("readme") or "")
    # If the readme is just badges/banners (cleanup yielded nothing), fall
    # back to the short `description` field so generated recipes still get
    # an `about.description` block instead of leaving it empty.
    if not readme_excerpt:
        npm_description = v.get("description") or ""
        if len(npm_description.strip()) >= 20:
            readme_excerpt = npm_description.strip()

    has_runtime_deps = bool(v.get("dependencies") or {})

    # Native-compilation detection. npm marks packages with binding.gyp via
    # ``gypfile: true``; some packages instead invoke node-gyp via the
    # ``install``/``preinstall`` script. Either signal means the recipe needs
    # a C/C++ toolchain at build time.
    install_script = (v.get("scripts") or {}).get("install", "") or ""
    preinstall_script = (v.get("scripts") or {}).get("preinstall", "") or ""
    has_native_build = bool(
        v.get("gypfile") is True
        or "node-gyp" in install_script
        or "node-gyp" in preinstall_script
        or "prebuild-install" in install_script  # common pattern (sharp, sqlite3)
    )
    if has_native_build:
        print(
            f"Note: {raw_name} declares native compilation (gypfile or "
            f"node-gyp install) — emitting compiler/stdlib build deps and "
            f"dropping noarch:generic.",
            file=sys.stderr,
        )

    raw_license = v.get("license", "") or ""
    license_value, license_warning = _check_spdx_license(raw_license)
    if license_warning:
        print(f"Warning: {license_warning}", file=sys.stderr)

    return NpmPackageInfo(
        raw_name=raw_name,
        conda_name=conda_name,
        version=version,
        description=v.get("description", ""),
        readme_excerpt=readme_excerpt,
        license=license_value,
        homepage=homepage,
        repository_url=repository_url,
        bugs_url=bugs_url,
        documentation_url=homepage if homepage and homepage != repository_url else "",
        tarball_url=tarball_url,
        tarball_filename=_npm_tarball_filename(raw_name, version),
        source_url=source_url,
        sha256=sha256,
        license_filename=license_filename or "LICENSE",
        bin_entries=bin_entries,
        node_major=node_major,
        is_scoped=is_scoped,
        is_github_source=prefer_github,
        has_runtime_deps=has_runtime_deps,
        has_native_build=has_native_build,
    )


def _build_sh_template(
    info: NpmPackageInfo,
    *,
    prepare_fix: bool = False,
    no_bin_links: bool = False,
    third_party_licenses: bool = True,
) -> str:
    """Canonical ``build.sh`` for an npm conda-forge recipe.

    Pattern source: PRs 28481 / 29752 / 32368 / 32549. ``npm pack`` then
    ``npm install --global`` lets npm itself create the bin shims; we just
    add the Windows ``.cmd`` wrapper for the noarch-on-Linux build host.
    """
    bin_lines = []
    for command in sorted(info.bin_entries):
        bin_lines += [
            f'tee "${{PREFIX}}"/bin/{command}.cmd << EOF',
            f"call %CONDA_PREFIX%\\bin\\node %CONDA_PREFIX%\\bin\\{command} %*",
            "EOF",
            "",
        ]

    no_bin_links_flag = " \\\n    --no-bin-links" if no_bin_links else ""
    prepare_block = ""
    if prepare_fix:
        prepare_block = (
            "# Strip upstream's prepare script — it can run husky/git hooks\n"
            "# that aren't available in the conda-forge build sandbox.\n"
            "mv package.json package.json.bak\n"
            'jq \'del(.scripts.prepare)\' package.json.bak > package.json\n\n'
        )

    pnpm_block = ""
    if third_party_licenses:
        pnpm_block = (
            "# Generate the third-party license disclaimer (required by conda-forge\n"
            "# for npm packages with runtime dependencies — declared in\n"
            "# `about.license_file`).\n"
            "pnpm install\n"
            "pnpm-licenses generate-disclaimer --prod --output-file=third-party-licenses.txt\n\n"
        )

    return (
        "#!/usr/bin/env bash\n"
        "\n"
        "set -o xtrace -o nounset -o pipefail -o errexit\n"
        "\n"
        f"{prepare_block}"
        f"# Pack the package and install it globally into the conda prefix.\n"
        f"# `npm install --global` creates the bin shims for us.\n"
        f"npm pack --ignore-scripts\n"
        f"npm install -ddd \\\n"
        f"    --global \\\n"
        f"    --build-from-source{no_bin_links_flag} \\\n"
        f'    "${{SRC_DIR}}/{_template_npm_tarball_filename(info.tarball_filename, info.version)}"\n'
        f"\n"
        f"{pnpm_block}"
        f"# Windows .cmd wrappers (the noarch build runs on Linux but the\n"
        f"# package needs to be usable on Windows once installed).\n"
        + "\n".join(bin_lines)
    )


def _inline_build_script(
    info: NpmPackageInfo,
    *,
    prepare_fix: bool,
    third_party_licenses: bool = True,
) -> list[str]:
    """Return the lines for a v1 inline ``build.script:`` block (openspec-style)."""
    cmds: list[str] = []
    if prepare_fix:
        cmds += [
            "mv package.json package.json.bak",
            "jq 'del(.scripts.prepare)' package.json.bak > package.json",
        ]
    templated_tarball = _template_npm_tarball_filename(info.tarball_filename, info.version)
    cmds += [
        "npm pack --ignore-scripts",
        f'npm install -ddd --global --build-from-source "${{SRC_DIR}}/{templated_tarball}"',
    ]
    if third_party_licenses:
        cmds += [
            "pnpm install",
            "pnpm-licenses generate-disclaimer --prod --output-file=third-party-licenses.txt",
        ]
    for command in sorted(info.bin_entries):
        cmds.append(
            f"tee \"${{PREFIX}}\"/bin/{command}.cmd <<< 'call %CONDA_PREFIX%\\bin\\node %CONDA_PREFIX%\\bin\\{command} %*'"
        )
    out = ["  script:"]
    for c in cmds:
        out.append(f"    - {c}")
    return out


def _tests_block(info: NpmPackageInfo, *, mode: str) -> list[str]:
    """Build the ``tests:`` section for the recipe.

    Modes:
      - ``"script"`` (default): runs ``<cmd> --help`` for each bin entry
      - ``"package_contents"``: just asserts the bin file exists (claude-agent-acp pattern)
    """
    if not info.bin_entries:
        return []
    sorted_cmds = sorted(info.bin_entries)
    if mode == "package_contents":
        out = ["tests:", "  - package_contents:", "      bin:"]
        for cmd in sorted_cmds:
            out.append(f"        - {cmd}")
        return out
    out = ["tests:", "  - script:"]
    for cmd in sorted_cmds:
        out.append(f"      - {cmd} --help")
    return out


def generate_npm_recipe_yaml(
    info: NpmPackageInfo,
    output_dir: Path,
    *,
    prepare_fix: bool = False,
    test_mode: str = "script",
    inline_build: bool = False,
    with_build_bat: bool = False,
    no_bin_links: bool = False,
    third_party_licenses: bool = True,
    feedstock_mode: bool = False,
) -> Path:
    """Generate a v1 npm recipe matching the canonical conda-forge pattern.

    Default output: ``<output_dir>/<conda-name>/{recipe.yaml, build.sh, conda-forge.yml}``.
    ``build.bat`` is only written when ``with_build_bat=True`` (rare — noarch:generic
    builds run on Linux only, so build.sh creates both unix and Windows wrappers).
    ``inline_build=True`` puts the build script directly inside ``recipe.yaml`` and
    skips the separate ``build.sh`` (openspec-style single-file recipe).

    ``third_party_licenses=False`` produces the husky-style minimal recipe
    (PR 28481) for packages with no runtime dependencies — drops `pnpm` /
    `pnpm-licenses` from the build deps, makes ``license_file`` a single
    string, and skips the disclaimer step in the build script.

    Pattern source: PRs 28481 / 29752 / 32368 / 32549.
    """
    pkg_dir = output_dir / info.conda_name
    pkg_dir.mkdir(parents=True, exist_ok=True)

    sha = info.sha256 or ("0" * 64) + "  # TODO compute sha256 of tarball"
    license_block = info.license if info.license else "REPLACE_LICENSE  # TODO SPDX identifier"
    raw_desc = info.description or "TODO replace summary"
    desc = f'"{raw_desc[:200]}"' if ":" in raw_desc else raw_desc[:200]
    homepage = info.homepage or info.repository_url or ""

    # Source URL — npm registry by default, GitHub release if --source github
    if info.is_github_source and info.repository_url:
        source_url_line = (
            f"  url: {info.repository_url}/archive/refs/tags/v"
            "${{ version }}.tar.gz"
        )
    else:
        source_url_line = f"  url: {info.source_url}"

    # ``schema_version: 1`` is technically optional for v1 recipes (rattler-build
    # defaults to it) — many merged conda-forge npm recipes omit it. We emit it
    # explicitly so our validate_recipe.py is happy without bending its rules.
    # The yaml-language-server comment gives editors (VS Code, Helix, etc.) live
    # schema validation against prefix-dev/recipe-format.
    recipe_lines = [
        "# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json",
        "schema_version: 1",
        "",
        "context:",
        f'  version: "{info.version}"',
        "",
        "package:",
        f"  name: {info.conda_name}",
        "  version: ${{ version }}",
        "",
        "source:",
        source_url_line,
        f"  sha256: {sha}",
        "",
    ]

    # Native packages need platform-specific builds — drop noarch:generic.
    # We still emit `build.script:` (inline) or rely on build.sh.
    noarch_line = None if info.has_native_build else "  noarch: generic"

    if inline_build:
        build_block = [
            "build:",
            *_inline_build_script(
                info,
                prepare_fix=prepare_fix,
                third_party_licenses=third_party_licenses,
            ),
            "  number: 0",
        ]
        if noarch_line:
            build_block.append(noarch_line)
        build_block.append("")
        recipe_lines += build_block
    else:
        build_block = [
            "build:",
            "  number: 0",
        ]
        if noarch_line:
            build_block.append(noarch_line)
        build_block.append("")
        recipe_lines += build_block

    build_reqs = []
    # Native compilation: emit C/C++ compilers, stdlib, python (node-gyp uses
    # python), and make. These are required when gypfile or node-gyp install
    # scripts are present in the package.
    if info.has_native_build:
        build_reqs += [
            "    - ${{ compiler('c') }}",
            "    - ${{ compiler('cxx') }}",
            "    - ${{ stdlib('c') }}",
            "    - python",
            "    - make",
        ]
    build_reqs.append("    - nodejs")
    if third_party_licenses:
        build_reqs += ["    - pnpm", "    - pnpm-licenses"]
    recipe_lines += [
        "requirements:",
        "  build:",
        *build_reqs,
        "  run:",
        "    - nodejs",
        "",
    ]

    tests_block = _tests_block(info, mode=test_mode)
    if tests_block:
        recipe_lines += tests_block + [""]

    recipe_lines += [
        "about:",
        f"  license: {license_block}",
    ]
    if third_party_licenses:
        recipe_lines += [
            "  license_file:",
            f"    - {info.license_filename}",
            "    - third-party-licenses.txt",
        ]
    else:
        recipe_lines.append(f"  license_file: {info.license_filename}")
    recipe_lines.append(f"  summary: {desc}")

    if info.readme_excerpt:
        recipe_lines.append("  description: |")
        for line in info.readme_excerpt.splitlines():
            recipe_lines.append(f"    {line}".rstrip())

    if homepage:
        recipe_lines.append(f"  homepage: {homepage}")
    if info.documentation_url and info.documentation_url != info.repository_url:
        recipe_lines.append(f"  documentation: {info.documentation_url}")
    if info.repository_url:
        recipe_lines.append(f"  repository: {info.repository_url}")

    recipe_lines += [
        "",
        "extra:",
        "  recipe-maintainers:",
        "    - MAINTAINER  # TODO replace with your GitHub handle",
        "",
    ]

    recipe_path = pkg_dir / "recipe.yaml"
    recipe_path.write_text("\n".join(recipe_lines), encoding="utf-8")

    # ── build.sh ──────────────────────────────────────────────────────────
    if not inline_build:
        (pkg_dir / "build.sh").write_text(
            _build_sh_template(
                info,
                prepare_fix=prepare_fix,
                no_bin_links=no_bin_links,
                third_party_licenses=third_party_licenses,
            ),
            encoding="utf-8",
        )

    # ── build.bat (opt-in only) ───────────────────────────────────────────
    # Most canonical npm recipes don't ship build.bat — noarch:generic builds
    # run on Linux only, so build.sh handles both unix and Windows wrappers.
    # claude-agent-acp (PR 32549) does ship one, but it's optional.
    if with_build_bat and not inline_build:
        bat_lines = [
            "@echo on",
            "",
            "call npm pack --ignore-scripts || goto :error",
            f"call npm install -ddd --global --build-from-source {'--no-bin-links ' if no_bin_links else ''}%SRC_DIR%\\{info.tarball_filename} || goto :error",
            "",
            ":: Generate third-party license disclaimer",
            "call pnpm install || goto :error",
            "call pnpm-licenses generate-disclaimer --prod --output-file=third-party-licenses.txt || goto :error",
            "",
            "goto :eof",
            "",
            ":error",
            "echo Failed with error #%errorlevel%.",
            "exit 1",
        ]
        (pkg_dir / "build.bat").write_text("\r\n".join(bat_lines), encoding="utf-8")

    # ── conda-forge.yml ───────────────────────────────────────────────────
    if feedstock_mode:
        # Full feedstock-style conda-forge.yml — for updating an existing
        # <pkg>-feedstock repo. Adds bot/github/output_validation/conda_build
        # fields that only take effect post-merge. Mirrors the shape used by
        # conda-forge/bmad-method-feedstock (/recipe/recipe.yaml's sibling).
        cfy_lines = [
            "# Feedstock-level conda-forge.yml. See:",
            "# https://conda-forge.org/docs/maintainer/conda_forge_yml",
            "conda_build_tool: rattler-build",
            "conda_install_tool: pixi",
            "noarch_platforms:",
            "  - linux_64",
            "  - win_64",
            "github:",
            "  branch_name: main",
            "  tooling_branch_name: main",
            "conda_build:",
            "  error_overlinking: true",
            "conda_forge_output_validation: true",
            "shellcheck:",
            "  enabled: true",
            "bot:",
            "  automerge: true",
            "  inspection: hint-all",
            "  check_solvable: true",
            "  run_deps_from_wheel: true",
            "",
        ]
    else:
        # Staged-recipes-friendly subset — bot/github/etc. take effect only
        # after staged-recipes merges into a feedstock anyway, so we keep
        # the file minimal during PR review.
        cfy_lines = [
            "# Per-recipe conda-forge.yml — merged into the rendered feedstock",
            "# at PR-merge time. See https://conda-forge.org/docs/maintainer/conda_forge_yml",
            "conda_build_tool: rattler-build",
            "noarch_platforms:",
            "  - linux_64",
            "shellcheck:",
            "  enabled: true",
            "",
        ]
    (pkg_dir / "conda-forge.yml").write_text("\n".join(cfy_lines), encoding="utf-8")

    return recipe_path


def _run_preflight_validation(recipe_dir: Path) -> None:
    """Run validate_recipe.py and recipe_optimizer.py against a freshly
    generated recipe and print their summary lines to stderr.

    Findings are informational — generation has already completed. The user
    can fix anything flagged before submitting.
    """
    import subprocess
    scripts_dir = Path(__file__).parent
    python = os.environ.get("CONDA_PYTHON_EXE") or sys.executable
    print("\n--- Pre-flight checks ---", file=sys.stderr)
    for script_name, label in (
        ("validate_recipe.py", "validate"),
        ("recipe_optimizer.py", "optimize"),
    ):
        script_path = scripts_dir / script_name
        if not script_path.exists():
            print(f"  [{label}] {script_name} not found — skipped",
                  file=sys.stderr)
            continue
        try:
            proc = subprocess.run(
                [python, str(script_path), str(recipe_dir)],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            print(f"  [{label}] failed to run: {exc}", file=sys.stderr)
            continue
        # Print a short summary — both scripts are noisy, so just last few lines
        out = (proc.stdout or "").rstrip()
        err = (proc.stderr or "").rstrip()
        body = out or err
        if body:
            tail = "\n".join(body.splitlines()[-12:])
            print(f"  [{label}]\n{tail}", file=sys.stderr)


def _run_rattler_generate(ecosystem: str, args: list[str], output_dir: Path) -> Path:
    """Invoke ``rattler-build generate-recipe <ecosystem> ...`` in output_dir.

    Returns the path to the generated recipe.yaml. Raises on failure.

    rattler-build's generate-recipe writes to ``<conda-name>/recipe.yaml``
    relative to the current working directory; we cd into output_dir so the
    user-visible artifact lands where they asked.
    """
    import shutil
    import subprocess

    rattler = shutil.which("rattler-build")
    if not rattler:
        raise RuntimeError(
            "rattler-build is not on PATH. Run via the local-recipes pixi env."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [rattler, "generate-recipe", ecosystem, *args],
        cwd=str(output_dir),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"rattler-build generate-recipe {ecosystem} failed:\n{proc.stderr}"
        )

    # rattler-build prints the path it wrote to in stderr / stdout
    candidates = sorted(output_dir.glob("*/recipe.yaml"))
    if not candidates:
        raise RuntimeError(
            f"rattler-build did not produce a recipe.yaml in {output_dir}.\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    # Newest match — handles re-runs in same dir
    recipe_path = max(candidates, key=lambda p: p.stat().st_mtime)
    _ensure_yaml_language_server_header(recipe_path)
    return recipe_path


_YAML_LS_HEADER = (
    "# yaml-language-server: "
    "$schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json"
)


def _ensure_yaml_language_server_header(recipe_path: Path) -> None:
    """Prepend the yaml-language-server schema comment if missing.

    rattler-build generate-recipe does not emit this comment; without it
    editors lose live schema validation against prefix-dev/recipe-format.
    Idempotent — bails out if the file already starts with the directive.
    """
    text = recipe_path.read_text(encoding="utf-8")
    if text.lstrip().startswith("# yaml-language-server:"):
        return
    recipe_path.write_text(_YAML_LS_HEADER + "\n" + text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Generate conda-forge recipes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s pypi requests
  %(prog)s pypi numpy==1.26.0
  %(prog)s template python-noarch --name mypackage --version 1.0.0
  %(prog)s github owner/repo --version v1.0.0
  %(prog)s cran ggplot2
  %(prog)s cpan Moose
  %(prog)s luarocks lua-cjson
  %(prog)s npm bmad-method
        """
    )

    subparsers = parser.add_subparsers(dest="source", required=True)

    # PyPI source
    pypi_parser = subparsers.add_parser("pypi", help="Generate from PyPI")
    pypi_parser.add_argument("package", help="Package name (optionally with version: pkg==1.0)")
    pypi_parser.add_argument("--output", "-o", type=Path, default=None,
                             help="Output directory")
    pypi_parser.add_argument("--format", choices=["v1", "legacy"], default="v1",
                             help="Recipe format")

    # Template source
    tmpl_parser = subparsers.add_parser("template", help="Generate from template")
    tmpl_parser.add_argument("template", help="Template name (e.g., python-noarch)")
    tmpl_parser.add_argument("--name", required=True, help="Package name")
    tmpl_parser.add_argument("--version", default="1.0.0", help="Package version")
    tmpl_parser.add_argument("--output", "-o", type=Path, default=None,
                             help="Output directory")
    tmpl_parser.add_argument("--maintainer", default="MAINTAINER",
                             help="GitHub username")

    # GitHub source
    gh_parser = subparsers.add_parser("github", help="Generate from GitHub repo")
    gh_parser.add_argument("repo", help="Repository (owner/name)")
    gh_parser.add_argument("--version", "-v", help="Version/tag")
    gh_parser.add_argument("--output", "-o", type=Path, default=None,
                             help="Output directory")

    # CRAN source (rattler-build native)
    cran_parser = subparsers.add_parser(
        "cran", help="Generate an R recipe from CRAN (via rattler-build)"
    )
    cran_parser.add_argument("package", help="CRAN package name (e.g., ggplot2)")
    cran_parser.add_argument(
        "--universe", "-u", default=None,
        help="R Universe to fetch from (default: cran)",
    )
    cran_parser.add_argument(
        "--tree", "-t", action="store_true",
        help="Generate recipes for the whole dependency tree",
    )
    cran_parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Output directory (default: recipes/)",
    )

    # CPAN source (rattler-build native)
    cpan_parser = subparsers.add_parser(
        "cpan", help="Generate a Perl recipe from CPAN (via rattler-build)"
    )
    cpan_parser.add_argument("package", help="CPAN package name (e.g., Moose)")
    cpan_parser.add_argument(
        "--version", default=None,
        help="Specific version (default: latest)",
    )
    cpan_parser.add_argument(
        "--tree", "-t", action="store_true",
        help="Generate recipes for the whole dependency tree",
    )
    cpan_parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Output directory (default: recipes/)",
    )

    # LuaRocks source (rattler-build native)
    lua_parser = subparsers.add_parser(
        "luarocks",
        help="Generate a Lua recipe from LuaRocks (via rattler-build)",
    )
    lua_parser.add_argument(
        "rock",
        help="LuaRocks rock — module / module/version / author/module/version / rockspec URL",
    )
    lua_parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Output directory (default: recipes/)",
    )

    # npm source (canonical conda-forge pattern: npm pack + npm install --global)
    npm_parser = subparsers.add_parser(
        "npm",
        help="Generate a v1 recipe for an npm package (via registry.npmjs.org)",
    )
    npm_parser.add_argument(
        "package",
        help="npm package name (e.g. husky, @openai/codex; optionally @version)",
    )
    npm_parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Output directory (default: recipes/)",
    )
    npm_parser.add_argument(
        "--source-mode", choices=["npm", "github", "auto"], default="npm",
        dest="source_mode",
        help="Source tarball: npm registry (default), GitHub release, "
             "or auto (github when repo is on github.com).",
    )
    npm_parser.add_argument(
        "--prepare-fix", action="store_true",
        help="Strip upstream's `scripts.prepare` from package.json before build "
             "(release-please / codex pattern — needed when prepare runs husky).",
    )
    npm_parser.add_argument(
        "--test-mode", choices=["script", "package_contents"], default="script",
        help="Test style: `<cmd> --help` (default) or assert bin file exists "
             "(claude-agent-acp pattern — for non-runnable CLIs).",
    )
    npm_parser.add_argument(
        "--inline-build", action="store_true",
        help="Embed build script in recipe.yaml's `build.script` block "
             "(openspec pattern — single-file recipe; no separate build.sh).",
    )
    npm_parser.add_argument(
        "--with-build-bat", action="store_true",
        help="Also emit build.bat (rare — noarch:generic builds run on "
             "Linux only, so build.sh handles both unix + Windows wrappers).",
    )
    npm_parser.add_argument(
        "--no-bin-links", action="store_true",
        help="Pass --no-bin-links to npm install (claude-agent-acp pattern — "
             "use when bin entries are inside scoped paths).",
    )
    npm_parser.add_argument(
        "--no-third-party-licenses", action="store_true",
        dest="no_third_party_licenses",
        help="Skip pnpm-licenses third-party-licenses.txt generation (husky "
             "pattern). Use for packages with zero runtime dependencies — "
             "drops pnpm/pnpm-licenses from build deps and makes "
             "license_file a single string.",
    )
    npm_parser.add_argument(
        "--validate", action="store_true",
        help="After generating files, run validate_recipe.py and "
             "recipe_optimizer.py against the new recipe and surface their "
             "findings (does not block generation).",
    )
    npm_parser.add_argument(
        "--feedstock-mode", action="store_true", dest="feedstock_mode",
        help="Emit the full feedstock-style conda-forge.yml with bot, "
             "github, conda_forge_output_validation, and conda_build fields. "
             "Use when updating an existing <pkg>-feedstock repo (default "
             "is the smaller staged-recipes-friendly subset).",
    )

    args = parser.parse_args()

    try:
        if args.source == "pypi":
            # Parse package name and version
            if "==" in args.package:
                name, version = args.package.split("==")
            else:
                name, version = args.package, None

            print(f"Fetching info for {name}...")
            info = fetch_pypi_info(name, version)

            output_dir = args.output or Path(f"recipes/{info.name}")

            if args.format == "v1":
                path = generate_recipe_yaml(info, output_dir)
            else:
                path = generate_meta_yaml(info, output_dir)

            print(f"Generated: {path}")

        elif args.source == "template":
            output_dir = args.output or Path(f"recipes/{args.name}")

            path = copy_template(
                args.template,
                output_dir,
                name=args.name,
                version=args.version,
                maintainer=args.maintainer,
            )
            print(f"Generated from template: {path}")

        elif args.source == "github":
            # Fetch GitHub release info
            if not REQUESTS_AVAILABLE:
                print("Error: requests library required")
                sys.exit(1)
            assert requests is not None

            owner, name = args.repo.split("/")
            version = args.version

            if not version:
                # Get latest release
                url = f"https://api.github.com/repos/{owner}/{name}/releases/latest"
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    version = response.json().get("tag_name", "1.0.0")
                else:
                    version = "1.0.0"

            output_dir = args.output or Path(f"recipes/{name}")

            info = PackageInfo(
                name=name,
                version=version.lstrip("v"),
                homepage=f"https://github.com/{owner}/{name}",
                source_url=f"https://github.com/{owner}/{name}/archive/refs/tags/{version}.tar.gz",
                build_backend="setuptools", # Fallback for github source
            )

            path = generate_recipe_yaml(info, output_dir)
            print(f"Generated: {path}")
            print("Note: SHA256 and license need to be filled in manually")

        elif args.source == "cran":
            extra = ["-w"]
            if args.universe:
                extra += ["--universe", args.universe]
            if args.tree:
                extra += ["--tree"]
            extra += [args.package]
            output_dir = args.output or Path("recipes")
            path = _run_rattler_generate("cran", extra, output_dir)
            print(f"Generated: {path}")

        elif args.source == "cpan":
            extra = ["-w"]
            if args.version:
                extra += ["--version", args.version]
            if args.tree:
                extra += ["--tree"]
            extra += [args.package]
            output_dir = args.output or Path("recipes")
            path = _run_rattler_generate("cpan", extra, output_dir)
            print(f"Generated: {path}")

        elif args.source == "luarocks":
            # luarocks subcommand uses --write-to instead of -w
            output_dir = args.output or Path("recipes")
            extra = ["--write-to", ".", args.rock]
            path = _run_rattler_generate("luarocks", extra, output_dir)
            print(f"Generated: {path}")

        elif args.source == "npm":
            # Parse name@version. Care: scoped packages start with `@scope/name`,
            # then optional `@version` after.
            pkg_arg = args.package
            if pkg_arg.startswith("@"):
                # @scope/name OR @scope/name@version
                if pkg_arg.count("@") >= 2:
                    # @scope/name@version
                    at_idx = pkg_arg.rindex("@")
                    npm_name = pkg_arg[:at_idx]
                    npm_version = pkg_arg[at_idx + 1:]
                else:
                    npm_name, npm_version = pkg_arg, None
            elif "@" in pkg_arg:
                npm_name, npm_version = pkg_arg.rsplit("@", 1)
            else:
                npm_name, npm_version = pkg_arg, None

            print(f"Fetching npm registry info for {npm_name}...")
            npm_info = fetch_npm_info(
                npm_name, npm_version, source=args.source_mode,
            )

            # Third-party licenses default:
            #   - explicit --no-third-party-licenses always wins (force off)
            #   - else: include ONLY when npm metadata declares runtime deps
            # This auto-detects zero-dep packages (e.g. husky) and emits the
            # cleaner husky-style recipe without requiring the flag.
            if args.no_third_party_licenses:
                third_party_licenses = False
                auto_zero_dep_note = ""
            elif not npm_info.has_runtime_deps:
                third_party_licenses = False
                auto_zero_dep_note = (
                    "auto-detected zero runtime deps; emitting husky-style "
                    "minimal recipe (pass --third-party-licenses to override)"
                )
            else:
                third_party_licenses = True
                auto_zero_dep_note = ""

            output_dir = args.output or Path("recipes")
            path = generate_npm_recipe_yaml(
                npm_info,
                output_dir,
                prepare_fix=args.prepare_fix,
                test_mode=args.test_mode,
                inline_build=args.inline_build,
                with_build_bat=args.with_build_bat,
                no_bin_links=args.no_bin_links,
                third_party_licenses=third_party_licenses,
                feedstock_mode=args.feedstock_mode,
            )
            print(f"Generated: {path}")
            if not npm_info.sha256:
                print(
                    "Warning: tarball sha256 could not be computed; recipe.yaml "
                    "contains a placeholder you must replace.",
                    file=sys.stderr,
                )
            extras = []
            if args.inline_build:
                extras.append("inline-build")
            if args.prepare_fix:
                extras.append("prepare-fix")
            if args.test_mode != "script":
                extras.append(f"test-mode={args.test_mode}")
            mode_note = f" [{', '.join(extras)}]" if extras else ""
            print(
                f"Note: canonical npm pattern{mode_note} — replace MAINTAINER "
                f"placeholder and review the summary/description before submission.",
                file=sys.stderr,
            )
            if auto_zero_dep_note:
                print(f"Note: {auto_zero_dep_note}", file=sys.stderr)
            if args.validate:
                _run_preflight_validation(path.parent)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()