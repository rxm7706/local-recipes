#!/usr/bin/env python3
"""Bulk recipe-refresh driver for the CFE refresh waves (mason Story 25.3).

Reads a wave manifest and refreshes each ``recipes/<name>/`` to its feedstock's
published version through ``recipe_editor.execute_actions``. A separate
``--repair`` mode undoes three defects an earlier wave left behind (hashed PyPI
URLs, FMT-001 list indentation, a hidden ``meta.yaml``) and changes nothing else.

Manifest (YAML or JSON)::

    schema_version: 1
    track: B              # A (sole-maintainer) | B (co-maintained)
    wave: B1              # free-form wave id; names the report folder
    recipes:
      - name: billiard    # recipes/<name>/ (confined by _path_guard)
        feedstock: billiard   # optional; default: name
        version: "4.2.4"      # optional; default: the feedstock recipe's version

CLI::

    refresh_wave.py MANIFEST [--repair] [--apply] [--gates] [--build]
                    [--report-dir DIR] [--force] [--json]

Dry-run is the default: it reads, plans and writes only the report. ``--apply``
writes; ``--gates`` and ``--build`` run only with ``--apply``. The report
(``report.json`` is the resume state, ``report.md`` the per-bucket summary) goes
to ``.claude/data/conda-forge-expert/refresh-waves/<track>-<wave>/`` unless
``--report-dir`` says otherwise; a report directory under ``recipes/`` is refused.

Exit codes: 0 the run completed (``needs-review`` and ``blocked`` are data);
1 at least one recipe ended ``failed``; 2 the manifest or the environment made
the run impossible.

Everything the driver does stays on the local disk. It reads feedstocks only
through ``feedstock_lookup`` and runs no version-control command, no write to
any remote repository and no submission step. Its one subprocess seam, ``_run``,
serves the CFE gates and the isolated local build.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform as _platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Sibling helpers. Guarded so a re-import in a long-lived process does not
# front-load this directory once per import.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from _path_guard import recipes_root, validate_recipe_name  # noqa: E402
from _paths import get_data_dir, get_repo_root  # noqa: E402
import recipe_editor  # noqa: E402
from feedstock_enrich import _merge_maintainers  # noqa: E402
from feedstock_lookup import feedstock_lookup  # noqa: E402

TRACKS = ("A", "B")
MANIFEST_KEYS = frozenset({"schema_version", "track", "wave", "recipes"})
ENTRY_KEYS = frozenset({"name", "feedstock", "version"})

#: Outcomes that let a rerun skip a recipe whose file is unchanged. ``refreshed``
#: and ``repaired`` are deliberately absent: the next run re-evaluates them and
#: lands on ``already-current`` / ``already-clean``, which then are terminal.
TERMINAL_OUTCOMES = frozenset({"already-current", "already-clean", "needs-review", "blocked"})
#: Terminal outcomes that never write, so a dry-run record is as good as an applied one.
NO_WRITE_OUTCOMES = frozenset({"already-current", "already-clean", "blocked"})

_WAVE_RE = re.compile(r"\A[A-Za-z0-9._-]+\Z")
_SHA256_RE = re.compile(r"\b[0-9a-f]{64}\b")
_HASHED_URL_RE = re.compile(
    r"^https://files\.pythonhosted\.org/packages/[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{20,}/(?P<file>[^/?#]+)$"
)
_SDIST_EXTS = (".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".zip")
_V0_VERSION_RE = re.compile(r"""\{%-?\s*set\s+version\s*=\s*["']([^"']+)["']""")
_FS_PYPI_DIST_RE = re.compile(
    r"pypi\.(?:org|io)/packages/source/(?:[A-Za-z0-9]|\{\{[^}]*\}\})/([A-Za-z0-9._-]+)/"
)
_DIST_RE = re.compile(r"\A[A-Za-z0-9._-]+\Z")
_JINJA_OPEN_RE = re.compile(r"\$?\{[{%#]")
_PLACEHOLDER = "JINJA_PLACEHOLDER"

#: The four CFE gates, each run through its CFE wrapper script.
GATE_SCRIPTS = (
    ("validate", "validate_recipe.py"),
    ("optimize", "recipe_optimizer.py"),
    ("check-deps", "dependency-checker.py"),
    ("scan", "vulnerability_scanner.py"),
)
GATE_TIMEOUT_S = 900
BUILD_TIMEOUT_S = 7200


class ManifestError(Exception):
    """The manifest or the invocation makes the run impossible (exit 2)."""


# ──────────────────────────────────────────────────────────────────────────
# Small helpers
# ──────────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_hash(path: Path) -> Optional[str]:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError:
        return None


def _read_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def _pep440(value: Any):
    try:
        from packaging.version import InvalidVersion, Version
    except ImportError:  # pragma: no cover - packaging ships in every CFE env
        return None
    try:
        return Version(str(value).strip())
    except InvalidVersion:
        return None


def _rt_yaml():
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 4096
    return yaml


def _load_rt(text: str) -> Any:
    return _rt_yaml().load(text)


def _safe_load(text: str) -> Any:
    try:
        import yaml  # type: ignore[import-not-found]

        return yaml.safe_load(text)
    except ImportError:  # pragma: no cover - PyYAML ships in every CFE env
        from ruamel.yaml import YAML

        return YAML(typ="safe").load(text)


def _is_under(path: Path, root: Path) -> bool:
    path = path.resolve()
    root = root.resolve()
    return path == root or path.is_relative_to(root)


def _sanitize_comment(text: str) -> str:
    """CFE comment lines must carry no renderable jinja (landmine 7)."""
    return _JINJA_OPEN_RE.sub("(", text).replace("\n", " ")


# ──────────────────────────────────────────────────────────────────────────
# Manifest
# ──────────────────────────────────────────────────────────────────────────

def load_manifest(path: Path) -> dict[str, Any]:
    """Parse and validate a wave manifest. Raises ``ManifestError`` (exit 2)."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestError(f"cannot read manifest {path}: {exc}") from exc
    try:
        from ruamel.yaml import YAML

        data = YAML(typ="safe").load(raw)
    except ImportError as exc:
        raise ManifestError("ruamel.yaml is required to read a manifest") from exc
    except Exception as exc:
        raise ManifestError(f"manifest is not valid YAML or JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestError("manifest must be a mapping")
    unknown = sorted(set(map(str, data)) - MANIFEST_KEYS)
    if unknown:
        raise ManifestError(f"unknown manifest key(s): {', '.join(unknown)}")
    if data.get("schema_version") != 1:
        raise ManifestError("schema_version must be 1")
    track = data.get("track")
    if track not in TRACKS:
        raise ManifestError(f"track must be one of {TRACKS}, got {track!r}")
    wave = data.get("wave")
    if not isinstance(wave, str) or not _WAVE_RE.match(wave) or wave in (".", ".."):
        raise ManifestError(f"wave must be a flat id of letters, digits, '.', '_', '-', got {wave!r}")
    recipes = data.get("recipes")
    if not isinstance(recipes, list) or not recipes:
        raise ManifestError("recipes must be a non-empty list")

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, item in enumerate(recipes):
        if not isinstance(item, dict):
            raise ManifestError(f"recipes[{i}] must be a mapping")
        bad = sorted(set(map(str, item)) - ENTRY_KEYS)
        if bad:
            raise ManifestError(f"recipes[{i}]: unknown key(s): {', '.join(bad)}")
        name = item.get("name")
        try:
            validate_recipe_name(name)  # type: ignore[arg-type]
        except ValueError as exc:
            raise ManifestError(f"recipes[{i}]: {exc}") from exc
        feedstock = item.get("feedstock", name)
        try:
            validate_recipe_name(feedstock)
        except ValueError as exc:
            raise ManifestError(f"recipes[{i}]: feedstock: {exc}") from exc
        version = item.get("version")
        if version is not None and (not isinstance(version, str) or not version.strip()):
            raise ManifestError(f"recipes[{i}]: version must be a quoted string, got {version!r}")
        if name in seen:
            raise ManifestError(f"recipes[{i}]: duplicate recipe {name!r}")
        seen.add(name)
        entries.append({"name": name, "feedstock": feedstock, "version": version})

    return {"schema_version": 1, "track": track, "wave": wave, "recipes": entries}


# ──────────────────────────────────────────────────────────────────────────
# Subprocess seam (gates and the local build only)
# ──────────────────────────────────────────────────────────────────────────

def _run(argv: list[str], *, timeout: Optional[int] = None) -> tuple[int, str, str]:
    """The driver's one subprocess seam. Returns ``(returncode, stdout, stderr)``."""
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, check=False
        )
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s"
    return proc.returncode, proc.stdout, proc.stderr


def _lookup(feedstock: str):
    """The driver's one feedstock seam (``feedstock_lookup`` reads via GET only)."""
    return feedstock_lookup(feedstock)


# ──────────────────────────────────────────────────────────────────────────
# Feedstock facts
# ──────────────────────────────────────────────────────────────────────────

def _requirement_strings(items: Any) -> list[str]:
    """Flatten a requirements list to plain strings, descending if/then/else."""
    if isinstance(items, str):
        return [items]
    out: list[str] = []
    if isinstance(items, dict):
        for key in ("then", "else"):
            if key in items:
                out.extend(_requirement_strings(items[key]))
    elif isinstance(items, (list, tuple)):
        for item in items:
            out.extend(_requirement_strings(item))
    return out


def _req_name(spec: str) -> Optional[str]:
    spec = spec.strip()
    if not spec or spec.startswith(("$", "{", "#")) or spec.split()[0].startswith(_PLACEHOLDER):
        return None
    name = re.split(r"[\s<>=!~;]", spec, maxsplit=1)[0]
    if not name:
        return None
    return name.lower().replace("_", "-")


def _norm_spec(spec: str) -> str:
    return " ".join(str(spec).split())


def _fs_info(res: Any) -> dict[str, Any]:
    """Reduce a ``FeedstockLookupResult`` to the facts the driver compares."""
    info: dict[str, Any] = {
        "readable": False, "error": None, "format": None, "raw": None,
        "version": None, "sha256": None, "maintainers": [], "requirements": {},
    }
    if res is None or not getattr(res, "exists", False):
        info["error"] = "no-feedstock"
        return info
    if getattr(res, "error", None) or not getattr(res, "raw_text", None):
        info["error"] = "feedstock-unread"
        return info
    info["readable"] = True
    raw = res.raw_text
    parsed = res.parsed if isinstance(res.parsed, dict) else {}
    info["raw"] = raw
    info["format"] = "v1" if res.format == "recipe.yaml" else "v0"

    version: Any = None
    if info["format"] == "v1":
        context = parsed.get("context")
        version = context.get("version") if isinstance(context, dict) else None
    else:
        m = _V0_VERSION_RE.search(raw)
        if m:
            version = m.group(1)
        elif isinstance(parsed.get("package"), dict):
            version = parsed["package"].get("version")
    if version is not None and _PLACEHOLDER not in str(version) and "{{" not in str(version):
        info["version"] = str(version)

    sha: Optional[str] = None
    src = parsed.get("source")
    for node in (src if isinstance(src, list) else [src]):
        if isinstance(node, dict) and isinstance(node.get("sha256"), str) and _SHA256_RE.fullmatch(node["sha256"]):
            sha = node["sha256"]
            break
    if sha is None:
        m2 = _SHA256_RE.search(raw)
        sha = m2.group(0) if m2 else None
    info["sha256"] = sha

    extra = parsed.get("extra") if isinstance(parsed.get("extra"), dict) else {}
    info["maintainers"] = [str(m) for m in (extra.get("recipe-maintainers") or [])]
    reqs = parsed.get("requirements") if isinstance(parsed.get("requirements"), dict) else {}
    info["requirements"] = {sec: _requirement_strings(reqs.get(sec)) for sec in ("host", "run")}
    return info


# ──────────────────────────────────────────────────────────────────────────
# Local recipe facts
# ──────────────────────────────────────────────────────────────────────────

def _sources(data: Any) -> list[tuple[str, dict]]:
    """``(editor path, node)`` for every mapping under ``source``."""
    src = data.get("source") if hasattr(data, "get") else None
    if isinstance(src, dict):
        return [("source", src)]
    if isinstance(src, list):
        return [(f"source.{i}", n) for i, n in enumerate(src) if isinstance(n, dict)]
    return []


def _first_url(node: dict) -> Optional[str]:
    url = node.get("url")
    if isinstance(url, list):
        url = url[0] if url else None
    return str(url) if url is not None else None


def _render_url(url: str, context: Any) -> str:
    """Render ``${{ var }}`` the way ``recipe_editor``'s calculate_hash does."""
    if hasattr(context, "items"):
        for var_name, var_value in context.items():
            url = url.replace(f"${{{{ {var_name} }}}}", str(var_value))
    return url


def _url_problem(url: str, version: str) -> Optional[tuple[str, str]]:
    """``(code, detail)`` when a source URL cannot be refreshed by a version bump."""
    if _HASHED_URL_RE.match(url):
        return (
            "hashed-url",
            "source.url is a hashed files.pythonhosted.org URL; run refresh-wave --repair to restore the canonical pypi.org form",
        )
    if not re.search(r"\$\{\{\s*version\b", url):
        return (
            "url-version-baked",
            "source.url is not templated on ${{ version }}; run --repair for a hashed URL, otherwise edit it by hand",
        )
    literal = re.sub(r"\$\{\{.*?\}\}", "", url)
    if version and version in literal:
        return ("url-version-baked", "source.url bakes the current version in literally; edit it by hand")
    return None


def _dependency_diff(data: Any, fs: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Compare host/run names (and commented pins) against the feedstock (G96)."""
    reqs = data.get("requirements") if hasattr(data, "get") else None
    if not isinstance(reqs, dict):
        reqs = {}
    diff: dict[str, Any] = {"names": {}, "pins": []}
    for section in ("host", "run"):
        seq = reqs.get(section)
        local_specs = _requirement_strings(seq)
        local = {n: s for s in local_specs if (n := _req_name(s)) is not None}
        feed = {n: s for s in fs["requirements"].get(section, []) if (n := _req_name(s)) is not None}
        only_local = sorted(set(local) - set(feed))
        only_feed = sorted(set(feed) - set(local))
        if only_local or only_feed:
            diff["names"][section] = {"only_local": only_local, "only_feedstock": only_feed}
        # A pin a maintainer commented on (landmine 12) that differs from the feedstock.
        ca_items = getattr(getattr(seq, "ca", None), "items", None) or {}
        if isinstance(seq, list):
            for idx, item in enumerate(seq):
                if not isinstance(item, str):
                    continue
                comment = ca_items.get(idx)
                # ruamel keeps a sequence item's end-of-line comment at slot 0.
                if not comment or all(c is None for c in comment):
                    continue
                name = _req_name(item)
                if name is None or name not in feed:
                    continue
                a, b = _norm_spec(item), _norm_spec(feed[name])
                if "${{" in a or "${{" in b or _PLACEHOLDER in b or a == b:
                    continue
                diff["pins"].append({"section": section, "name": name, "local": a, "feedstock": b})
    if not diff["names"] and not diff["pins"]:
        return None
    return diff


def _dependency_summary(diff: dict[str, Any]) -> str:
    parts: list[str] = []
    for section, d in diff["names"].items():
        bits = [f"+{n}" for n in d["only_feedstock"]] + [f"-{n}" for n in d["only_local"]]
        parts.append(f"{section} {' '.join(bits)}")
    for pin in diff["pins"]:
        parts.append(f"{pin['section']} pin {pin['name']} ({pin['local']} vs {pin['feedstock']})")
    return "; ".join(parts)


# ──────────────────────────────────────────────────────────────────────────
# Text-level CFE block edits (the block is comments and metadata, not body)
# ──────────────────────────────────────────────────────────────────────────

def _replace_key_line(text: str, key: str, value: str) -> tuple[str, bool]:
    """Set ``key: value`` on the one indented line that carries ``key``."""
    pat = re.compile(rf"^([ \t]+{re.escape(key)}:)[ \t]*[^\n]*$", re.MULTILINE)
    matches = pat.findall(text)
    if len(matches) != 1:
        return text, False
    return pat.sub(lambda m: f"{m.group(1)} {value}", text, count=1), True


def _add_updates_needed_token(text: str, token: str) -> str:
    """Add ``token`` to ``cfe-forge-recipe-updates-needed`` (scalar, flow or block list)."""
    pat = re.compile(r"^([ \t]*)cfe-forge-recipe-updates-needed:([^\n]*)$", re.MULTILINE)
    matches = list(pat.finditer(text))
    if len(matches) != 1:
        return text
    m = matches[0]
    indent, rest = m.group(1), m.group(2)
    value = rest.split(" #", 1)[0].strip()
    prefix = f"{indent}cfe-forge-recipe-updates-needed:"
    if value in ("", "~", "null"):
        lines = text.split("\n")
        start = text[: m.start()].count("\n")
        j = start + 1
        last_item = None
        item_indent = None
        while j < len(lines):
            mm = re.match(r"^([ \t]*)-[ \t]+(.*)$", lines[j])
            if mm and len(mm.group(1)) >= len(indent):
                item_indent = mm.group(1)
                if mm.group(2).strip().strip("\"'") == token:
                    return text
                last_item = j
                j += 1
                continue
            break
        if last_item is None:
            return text[: m.start()] + f"{prefix} [{token}]" + text[m.end():]
        lines.insert(last_item + 1, f"{item_indent}- {token}")
        return "\n".join(lines)
    if value.startswith("["):
        inner = value[1:value.rfind("]")] if "]" in value else value[1:]
        items = [i.strip() for i in inner.split(",") if i.strip()]
        if token in [i.strip("\"'") for i in items]:
            return text
        return text[: m.start()] + f"{prefix} [{', '.join(items + [token])}]" + text[m.end():]
    if value == "none":
        return text[: m.start()] + f"{prefix} [{token}]" + text[m.end():]
    if value.strip("\"'") == token:
        return text
    return text[: m.start()] + f"{prefix} [{value}, {token}]" + text[m.end():]


def _append_header_comment(text: str, message: str) -> str:
    """Append one ``#    # …`` line under ``# CFE comments`` → ``# Header:``."""
    line = f"#    # {_sanitize_comment(message)}"
    lines = text.split("\n")
    if line in lines:
        return text
    idx = next((i for i, l in enumerate(lines) if re.match(r"^# Header:[ \t]*$", l)), None)
    if idx is None:
        tail = lines[-1] == ""
        body = lines[:-1] if tail else lines
        body += ["# CFE comments", "# Header:", line, "####"]
        return "\n".join(body + ([""] if tail else []))
    j = idx + 1
    while j < len(lines) and lines[j].startswith("#    "):
        j += 1
    lines.insert(j, line)
    return "\n".join(lines)


def _cfe_edit(text: str, *, comment: str, token: Optional[str] = None, stamp: bool = True) -> str:
    if stamp:
        text, _ = _replace_key_line(text, "cfe-last-checked", _iso(_now()))
    if token:
        text = _add_updates_needed_token(text, token)
    return _append_header_comment(text, comment)


# ──────────────────────────────────────────────────────────────────────────
# Write check (step 8)
# ──────────────────────────────────────────────────────────────────────────

def _fmt001_keys(text: str) -> set[str]:
    import recipe_optimizer

    keys: set[str] = set()
    for m in recipe_optimizer._FMT_LIST_INDENT_RE.finditer(text):
        if m.group("indent"):
            keys.add(m.group("key"))
    return keys


def _write_check(before: str, after: str) -> list[str]:
    """Problems with a freshly written recipe; empty means it is sound."""
    problems: list[str] = []
    try:
        _safe_load(after)
    except Exception as exc:
        problems.append(f"does-not-parse: {str(exc).splitlines()[0] if str(exc) else type(exc).__name__}")
    for token, label in (("#### CFE metadata", "cfe-metadata-block"), ("cfe-conda-name", "cfe-conda-name")):
        n = after.count(token)
        if n != 1:
            problems.append(f"{label}-count={n}")
    new_fmt = _fmt001_keys(after) - _fmt001_keys(before)
    if new_fmt:
        problems.append(f"FMT-001: {', '.join(sorted(new_fmt))}")
    return problems


# ──────────────────────────────────────────────────────────────────────────
# Records
# ──────────────────────────────────────────────────────────────────────────

def _new_record(entry: dict[str, Any], *, apply: bool) -> dict[str, Any]:
    return {
        "name": entry["name"],
        "feedstock": entry["feedstock"],
        "manifest_entry": dict(entry),
        "applied": apply,
        "outcome": None,
        "reasons": [],
        "notes": [],
        "from_version": None,
        "to_version": None,
        "maintainers_added": [],
        "dependency_diff": None,
        "gates": {},
        "build": None,
        "meta_yaml": None,
        "repairs": [],
        "recipe_sha256": None,
    }


def _finish(rec: dict[str, Any], outcome: str, *reasons: str) -> dict[str, Any]:
    rec["outcome"] = outcome
    rec["reasons"].extend(r for r in reasons if r)
    return rec


def _recipe_hash(name: str) -> Optional[str]:
    return _file_hash(recipes_root() / name / "recipe.yaml")


# ──────────────────────────────────────────────────────────────────────────
# Gates and build
# ──────────────────────────────────────────────────────────────────────────

def _wrapper_dir() -> Path:
    root = get_repo_root()
    base = root if root is not None else Path(_SCRIPTS_DIR).parents[3]
    return base / ".claude" / "scripts" / "conda-forge-expert"


def _run_gates(recipe_yaml: Path, rec: dict[str, Any]) -> None:
    for gate, script in GATE_SCRIPTS:
        rc, _out, _err = _run(
            [sys.executable, str(_wrapper_dir() / script), str(recipe_yaml)],
            timeout=GATE_TIMEOUT_S,
        )
        rec["gates"][gate] = rc
        if rc != 0:
            rec["notes"].append(f"gate {gate} exited {rc}")


def _host_subdir() -> str:
    system, machine = _platform.system(), _platform.machine().lower()
    arm = machine in ("arm64", "aarch64")
    if system == "Linux":
        return "linux-aarch64" if arm else "linux-64"
    if system == "Darwin":
        return "osx-arm64" if arm else "osx-64"
    if system == "Windows":
        return "win-64"
    return f"{system.lower()}-{machine}"


def _ci_config_stem() -> str:
    return {
        "linux-64": "linux64", "linux-aarch64": "linux_aarch64",
        "osx-arm64": "osxarm64", "osx-64": "osx64", "win-64": "win64",
    }.get(_host_subdir(), "linux64")


def _build_argv(recipe_yaml: Path, name: str) -> tuple[list[str], Path]:
    """rattler-build argv aimed at ``recipe.yaml`` itself, into its own output dir (G52)."""
    root = get_repo_root() or Path.cwd()
    out_dir = root / "build_artifacts" / name
    argv = ["rattler-build", "build", "--recipe", str(recipe_yaml)]
    platform_cfg = root / ".ci_support" / f"{_ci_config_stem()}.yaml"
    pinning = root / ".pixi" / "envs" / "local-recipes" / "conda_build_config.yaml"
    for cfg in (platform_cfg, pinning):
        if cfg.is_file():
            argv += ["--variant-config", str(cfg)]
    recipe_cbc = recipe_yaml.parent / "conda_build_config.yaml"
    if recipe_cbc.is_file():  # last wins (landmine 8)
        argv += ["--variant-config", str(recipe_cbc)]
    argv += ["--output-dir", str(out_dir)]
    return argv, out_dir


_TEST_BLOCK_RE = re.compile(
    r"(?i)(could not solve|unsolvable|failed to solve|solver.*(?:test|environment)|test (?:env|environment).*(?:solve|fail))"
)


def _classify_build(rc: int, output: str, out_dir: Path) -> str:
    """``success`` | ``build-clean-test-blocked`` (G95) | ``failed``."""
    if rc == 0:
        return "success"
    built = out_dir.is_dir() and any(
        p.suffix == ".conda" or p.name.endswith(".tar.bz2") for p in out_dir.rglob("*") if p.is_file()
    )
    if built and _TEST_BLOCK_RE.search(output):
        return "build-clean-test-blocked"
    return "failed"


def _run_build(recipe_yaml: Path, name: str, rec: dict[str, Any]) -> None:
    argv, out_dir = _build_argv(recipe_yaml, name)
    rc, out, err = _run(argv, timeout=BUILD_TIMEOUT_S)
    status = _classify_build(rc, out + "\n" + err, out_dir)
    rec["build"] = {"status": status, "returncode": rc, "output_dir": str(out_dir)}
    if status != "success":
        rec["notes"].append(f"build {status} (exit {rc})")
    # Stamp the real outcome into the CFE block (meta.yaml stays where it is).
    try:
        text = _read_text(recipe_yaml)
    except OSError:
        return
    stamped = text
    for key, value in (
        ("cfe-local-build-status", status),
        ("cfe-local-build-datetime", _iso(_now())),
        ("cfe-local-build-platform", _host_subdir()),
        ("cfe-local-build-tool", "rattler-build"),
    ):
        stamped, _ = _replace_key_line(stamped, key, value)
    if stamped != text:
        problems = _write_check(text, stamped)
        if problems:
            rec["notes"].append("build stamp skipped: " + "; ".join(problems))
        else:
            _write_text(recipe_yaml, stamped)


# ──────────────────────────────────────────────────────────────────────────
# Refresh path
# ──────────────────────────────────────────────────────────────────────────

def _version_node(ctx: Any, target: str) -> Any:
    """The new ``context.version`` scalar, keeping the file's quoting style."""
    from ruamel.yaml.scalarstring import DoubleQuotedScalarString, SingleQuotedScalarString

    current = ctx.get("version")
    if isinstance(current, (DoubleQuotedScalarString, SingleQuotedScalarString)):
        return type(current)(target)
    try:
        plain_is_str = isinstance(_safe_load(f"v: {target}")["v"], str)
    except Exception:
        plain_is_str = False
    return target if plain_is_str else DoubleQuotedScalarString(target)


def refresh_recipe(
    entry: dict[str, Any], *, track: str, wave: str, apply: bool, gates: bool, build: bool
) -> dict[str, Any]:
    name = entry["name"]
    rec = _new_record(entry, apply=apply)
    rdir = recipes_root() / name
    recipe_path = rdir / "recipe.yaml"

    if not rdir.is_dir():
        return _finish(rec, "blocked", "no-local-mirror")
    if not recipe_path.is_file():
        return _finish(rec, "blocked", "no-recipe-yaml")

    orig_bytes = recipe_path.read_bytes()
    rec["recipe_sha256"] = _sha256_bytes(orig_bytes)
    try:
        orig_text = orig_bytes.decode("utf-8")
        data = _load_rt(orig_text)
    except Exception as exc:
        return _finish(rec, "needs-review", f"recipe-unparseable: {type(exc).__name__}")
    if not hasattr(data, "get"):
        return _finish(rec, "needs-review", "recipe-unparseable: not a mapping")
    ctx = data.get("context")
    local_version = ctx.get("version") if hasattr(ctx, "get") else None
    if local_version is None:
        return _finish(rec, "needs-review", "no-context-version")
    local_version = str(local_version)
    rec["from_version"] = local_version

    # Step 1: the feedstock.
    fs = _fs_info(_lookup(entry["feedstock"]))

    # Step 2: target version.
    manifest_version = entry.get("version")
    target = manifest_version if manifest_version else fs["version"]
    if target is None:
        return _finish(rec, "needs-review", fs["error"] or "feedstock-version-unknown")
    target = str(target)
    rec["to_version"] = target
    lv, tv = _pep440(local_version), _pep440(target)
    if lv is None or tv is None:
        return _finish(rec, "needs-review", f"non-pep440-version: local {local_version!r}, target {target!r}")
    if lv >= tv:
        rec["to_version"] = local_version
        return _finish(rec, "already-current")
    if not fs["readable"]:
        return _finish(rec, "needs-review", fs["error"] or "feedstock-unread")
    if fs["version"] is None:
        return _finish(rec, "needs-review", "feedstock-version-unknown")
    fv = _pep440(fs["version"])
    if manifest_version and (fv is None or fv != tv):
        return _finish(
            rec, "needs-review",
            f"tag-numbering: feedstock publishes {fs['version']!r} but the manifest names {manifest_version!r} (landmine 1)",
        )

    if orig_text.count("#### CFE metadata") != 1 or orig_text.count("cfe-conda-name") != 1:
        return _finish(rec, "needs-review", "no-cfe-block: the recipe lacks exactly one CFE metadata block")

    # Source URLs: never rewritten here.
    sources = _sources(data)
    if not sources or "url" not in sources[0][1]:
        return _finish(rec, "needs-review", "no-source-url")
    for _path, node in sources:
        url = _first_url(node)
        if url is None:
            continue
        problem = _url_problem(url, local_version) if node is sources[0][1] else (
            ("url-version-baked", "a secondary source bakes the current version in literally; edit it by hand")
            if local_version in re.sub(r"\$\{\{.*?\}\}", "", url) else None
        )
        if problem:
            return _finish(rec, "needs-review", f"{problem[0]}: {problem[1]}")
    probe_ctx = dict(ctx)
    probe_ctx["version"] = target
    for _path, node in sources:
        url = _first_url(node)
        if url is not None and re.search(r"\$\{\{\s*version\b", url) and "${{" in _render_url(url, probe_ctx):
            return _finish(rec, "needs-review", f"url-unrenderable: {url} uses a variable outside context")

    # Dependencies: the feedstock is the authority (G96); the body never changes here.
    diff = _dependency_diff(data, fs)
    if diff is not None:
        rec["dependency_diff"] = diff
        summary = _dependency_summary(diff)
        _finish(rec, "needs-review", f"dependency-fix: {summary}")
        if apply:
            comment = f"{_now():%Y-%m-%d} refresh_wave {track}-{wave}: needs-review, dependency-fix ({summary})"
            new_text = _cfe_edit(orig_text, comment=comment, token="dependency-fix")
            problems = _write_check(orig_text, new_text)
            if problems:
                rec["notes"].append("cfe block not written: " + "; ".join(problems))
            elif new_text != orig_text:
                _write_text(recipe_path, new_text)
                rec["recipe_sha256"] = _file_hash(recipe_path)
        return rec

    # Maintainers: union, local order first (G53, landmine 10).
    local_list = [str(m) for m in ((data.get("extra") or {}).get("recipe-maintainers") or [])]
    had_list = bool((data.get("extra") or {}).get("recipe-maintainers") is not None)
    merged, additions = _merge_maintainers(local_list, fs["maintainers"])
    rec["maintainers_added"] = list(additions)

    shape = "mirror-meta-yaml" if fs["format"] == "v0" else ("remove-meta-yaml" if (rdir / "meta.yaml").exists() else None)

    if not apply:
        rec["notes"].append("dry-run: sha256 not recomputed, gates and build not run")
        if shape:
            rec["meta_yaml"] = "would-mirror" if shape == "mirror-meta-yaml" else "would-remove"
        return _finish(rec, "would-refresh")

    # Step 4: edit through recipe_editor so the canonical indent and width hold.
    actions: list[dict[str, Any]] = [
        {"action": "update", "path": "context.version", "value": _version_node(ctx, target)},
        {"action": "update", "path": "build.number", "value": 0},
    ]
    for path, node in sources:
        url = _first_url(node)
        if url is not None and re.search(r"\$\{\{\s*version\b", url):
            actions.append({"action": "calculate_hash", "path": path})
    if additions:
        if had_list:
            actions.extend({"action": "add_to_list", "path": "extra.recipe-maintainers", "value": h} for h in additions)
        else:
            actions.append({"action": "update", "path": "extra.recipe-maintainers", "value": merged})

    def _restore() -> None:
        recipe_path.write_bytes(orig_bytes)

    result = recipe_editor.execute_actions(recipe_path, actions)
    if not result.get("success"):
        _restore()
        rec["recipe_sha256"] = _sha256_bytes(orig_bytes)
        return _finish(rec, "failed", f"edit-failed: {result.get('error', 'unknown error')}")

    try:
        edited_text = _read_text(recipe_path)
        edited = _load_rt(edited_text)
        new_sha = _sources(edited)[0][1].get("sha256")
    except Exception as exc:
        _restore()
        rec["recipe_sha256"] = _sha256_bytes(orig_bytes)
        return _finish(rec, "failed", f"edit-unreadable: {type(exc).__name__}")
    if fs["sha256"] and str(new_sha).lower() != fs["sha256"].lower():
        _restore()
        rec["recipe_sha256"] = _sha256_bytes(orig_bytes)
        rec["maintainers_added"] = []
        return _finish(rec, "needs-review", f"sha256-mismatch: recomputed {new_sha} != feedstock {fs['sha256']}")
    if not fs["sha256"]:
        rec["notes"].append("feedstock sha256 unavailable; recomputed hash not cross-checked")

    comment = f"{_now():%Y-%m-%d} refresh_wave {track}-{wave}: refreshed {local_version} -> {target}"
    if additions:
        comment += f"; maintainers added: {', '.join(additions)}"
    final_text = _cfe_edit(edited_text, comment=comment)
    problems = _write_check(orig_text, final_text)
    if problems:
        _restore()
        rec["recipe_sha256"] = _sha256_bytes(orig_bytes)
        rec["maintainers_added"] = []
        return _finish(rec, "failed", "write-check: " + "; ".join(problems))
    _write_text(recipe_path, final_text)

    # Step 3's shape actions run once the recipe write is sound; nothing is ever moved.
    try:
        if fs["format"] == "v0":
            _write_text(rdir / "meta.yaml", fs["raw"])
            rec["meta_yaml"] = "mirrored"
            rec["notes"].append("meta.yaml mirrored byte-for-byte from the v0 feedstock (C1)")
        elif (rdir / "meta.yaml").exists():
            (rdir / "meta.yaml").unlink()
            rec["meta_yaml"] = "removed"
            rec["notes"].append("local meta.yaml removed: the feedstock is already v1 (C2, G94)")
    except OSError as exc:
        rec["recipe_sha256"] = _file_hash(recipe_path)
        return _finish(rec, "failed", f"meta-yaml-write-failed: {exc}")

    _finish(rec, "refreshed")
    if gates:
        _run_gates(recipe_path, rec)
    if build:
        _run_build(recipe_path, name, rec)
    rec["recipe_sha256"] = _file_hash(recipe_path)
    return rec


# ──────────────────────────────────────────────────────────────────────────
# Repair path
# ──────────────────────────────────────────────────────────────────────────

def _reindent_fmt001(text: str) -> str:
    """Move FMT-001 list blocks two spaces deeper, line by line (whitespace only)."""
    lines = text.split("\n")
    key_re = re.compile(r"^([ ]*)[A-Za-z_][A-Za-z0-9_\-]*:[ \t]*$")
    for _ in range(500):
        hit = None
        for i, line in enumerate(lines[:-1]):
            m = key_re.match(line)
            if not m or not m.group(1):
                continue
            indent = m.group(1)
            nxt = lines[i + 1]
            if nxt.startswith(indent + "- "):
                hit = (i, len(indent))
                break
        if hit is None:
            break
        i, n = hit
        end = i  # last line index belonging to the block
        j = i + 1
        while j < len(lines):
            line = lines[j]
            stripped = line.strip()
            if not stripped:
                j += 1
                continue
            lead = len(line) - len(line.lstrip(" "))
            if stripped.startswith("#"):
                if lead >= n:
                    j += 1
                    continue
                break
            if lead > n or (lead == n and (stripped.startswith("- ") or stripped == "-")):
                end = j
                j += 1
                continue
            break
        for k in range(i + 1, end + 1):
            if lines[k].strip():
                lines[k] = "  " + lines[k]
    return "\n".join(lines)


def _whitespace_only_change(before: str, after: str) -> Optional[str]:
    """``None`` when ``after`` differs from ``before`` by indentation alone, else the reason."""
    if [l.strip() for l in before.split("\n")] != [l.strip() for l in after.split("\n")]:
        return "non-whitespace text changed"
    try:
        if _safe_load(before) != _safe_load(after):
            return "parsed value changed"
    except Exception as exc:
        return f"does-not-parse: {type(exc).__name__}"
    for token in ("#### CFE metadata", "cfe-conda-name"):
        if after.count(token) != before.count(token) or after.count(token) != 1:
            return f"{token} count changed"
    if _fmt001_keys(after):
        return "FMT-001 remains"
    return None


def _dist_from_feedstock(entry: dict[str, Any]) -> Optional[str]:
    res = _lookup(entry["feedstock"])
    raw = getattr(res, "raw_text", None) if res is not None and getattr(res, "exists", False) else None
    if not raw:
        return None
    m = _FS_PYPI_DIST_RE.search(raw)
    return m.group(1) if m else None


def _repair_urls(
    entry: dict[str, Any], text: str, data: Any, *, apply: bool
) -> tuple[str, list[str], list[str]]:
    """Return ``(new_text, repairs, review_reasons)`` for hashed PyPI URLs."""
    repairs: list[str] = []
    reviews: list[str] = []
    ctx = data.get("context") if hasattr(data, "get") else None
    version = str(ctx.get("version")) if hasattr(ctx, "get") and ctx.get("version") is not None else None
    for _path, node in _sources(data):
        url = _first_url(node)
        if not url:
            continue
        m = _HASHED_URL_RE.match(url)
        if not m:
            continue
        if version is None:
            reviews.append("url-repair: no context.version")
            continue
        file = m.group("file")
        stem = ext = None
        for e in _SDIST_EXTS:
            suffix = f"-{version}{e}"
            if file.endswith(suffix) and len(file) > len(suffix):
                stem, ext = file[: -len(suffix)], e
                break
        if stem is None or ext is None:
            reviews.append(f"url-file-shape: {file!r} is not an sdist named <stem>-{version}.<ext>")
            continue
        extra = data.get("extra") if hasattr(data, "get") else None
        dist = extra.get("cfe-upstream-name") if hasattr(extra, "get") else None
        dist = str(dist) if dist is not None and str(dist).lower() != "none" else None
        if dist is None or not _DIST_RE.match(dist):
            dist = _dist_from_feedstock(entry)
        if not dist:
            reviews.append("no-dist-name: neither extra.cfe-upstream-name nor the feedstock's PyPI URL names the project")
            continue
        new_url = f"https://pypi.org/packages/source/{dist[0].lower()}/{dist}/{stem}-${{{{ version }}}}{ext}"
        if apply:
            sha = node.get("sha256")
            try:
                got = recipe_editor.calculate_sha256_from_url(new_url.replace("${{ version }}", version))
            except Exception as exc:
                reviews.append(f"url-fetch-failed: {type(exc).__name__}")
                continue
            if sha is None or str(got).lower() != str(sha).lower():
                reviews.append(f"url-hash-mismatch: canonical URL hashes to {got}, recipe records {sha}")
                continue
        if text.count(url) < 1:
            reviews.append("url-not-found-in-text")
            continue
        text = text.replace(url, new_url)
        repairs.append("url")
    return text, repairs, reviews


def _repair_meta(
    entry: dict[str, Any], rdir: Path, rec: dict[str, Any], *, apply: bool
) -> tuple[list[str], list[str]]:
    """Hidden ``meta.yaml`` repair. Returns ``(repairs, review_reasons)``."""
    holds = sorted(p for p in rdir.glob(".meta.yaml*") if p.is_file())
    if not holds:
        return [], []
    meta = rdir / "meta.yaml"
    if len(holds) > 1:
        return [], [f"multiple-hold-files: {', '.join(h.name for h in holds)}"]
    hold = holds[0]
    if meta.exists():
        return [], [f"hold-and-meta-both-present: {hold.name} beside meta.yaml; neither touched"]

    fs = _fs_info(_lookup(entry["feedstock"]))
    hold_bytes = hold.read_bytes()
    if not fs["readable"]:
        if apply:
            os.replace(hold, meta)  # byte-for-byte; nothing is lost
        rec["meta_yaml"] = "would-restore-from-hold" if not apply else "restored-from-hold"
        return ["meta-yaml"], [f"feedstock-unread: {hold.name} restored as meta.yaml for review"]
    if fs["format"] == "v0":
        new_bytes = fs["raw"].encode("utf-8")
        rec["meta_matches_hold"] = new_bytes == hold_bytes
        if apply:
            meta.write_bytes(new_bytes)
            hold.unlink()
        rec["meta_yaml"] = "mirrored" if apply else "would-mirror"
        return ["meta-yaml"], []
    if apply:
        hold.unlink()
    rec["meta_yaml"] = "hold-removed" if apply else "would-remove-hold"
    return ["meta-yaml"], []


def repair_recipe(
    entry: dict[str, Any], *, track: str, wave: str, apply: bool, gates: bool
) -> dict[str, Any]:
    name = entry["name"]
    rec = _new_record(entry, apply=apply)
    rdir = recipes_root() / name
    recipe_path = rdir / "recipe.yaml"
    if not rdir.is_dir():
        return _finish(rec, "needs-review", "no-local-mirror")

    repairs: list[str] = []
    reviews: list[str] = []
    failed: list[str] = []

    if recipe_path.is_file():
        orig_bytes = recipe_path.read_bytes()
        rec["recipe_sha256"] = _sha256_bytes(orig_bytes)
        try:
            orig_text = orig_bytes.decode("utf-8")
            data = _load_rt(orig_text)
            _safe_load(orig_text)
        except Exception as exc:
            reviews.append(f"recipe-unparseable: {type(exc).__name__}")
            data = None
            orig_text = ""
        if data is not None and hasattr(data, "get"):
            text = orig_text
            # 1. Hashed URL.
            text, url_repairs, url_reviews = _repair_urls(entry, text, data, apply=apply)
            repairs += url_repairs
            reviews += url_reviews
            # 2. List indentation.
            if _fmt001_keys(text):
                candidate = _reindent_fmt001(text)
                why = _whitespace_only_change(text, candidate)
                if why is None:
                    text = candidate
                    repairs.append("indent")
                else:
                    reviews.append(f"indent-repair-refused: {why}")
            if text != orig_text and apply:
                problems = _write_check(orig_text, text)
                if problems:
                    failed.append("write-check: " + "; ".join(problems))
                else:
                    _write_text(recipe_path, text)
            rec["recipe_sha256"] = _file_hash(recipe_path)

    # 3. Hidden meta.yaml.
    try:
        meta_repairs, meta_reviews = _repair_meta(entry, rdir, rec, apply=apply)
    except OSError as exc:
        meta_repairs, meta_reviews = [], []
        failed.append(f"meta-yaml-repair-failed: {exc}")
    repairs += meta_repairs
    reviews += meta_reviews

    rec["repairs"] = repairs
    if failed:
        return _finish(rec, "failed", *failed)
    if reviews:
        return _finish(rec, "needs-review", *reviews)
    if not repairs:
        return _finish(rec, "already-clean")
    _finish(rec, "repaired" if apply else "would-repair")
    if apply and gates and recipe_path.is_file():
        _run_gates(recipe_path, rec)
    return rec


# ──────────────────────────────────────────────────────────────────────────
# Report
# ──────────────────────────────────────────────────────────────────────────

def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _summarise(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in records:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    return counts


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# refresh_wave {report['mode']} — track {report['track']}, wave {report['wave']}",
        "",
        f"- generated: {report['generated_at']}",
        f"- mode: {'apply' if report['applied'] else 'dry-run'}",
        "- summary: " + (", ".join(f"{k} {v}" for k, v in sorted(report["summary"].items())) or "no recipes"),
        "",
    ]
    buckets: dict[str, list[dict[str, Any]]] = {}
    for r in report["recipes"]:
        buckets.setdefault(r["outcome"], []).append(r)
    for outcome in sorted(buckets):
        lines.append(f"## {outcome} ({len(buckets[outcome])})")
        lines.append("")
        for r in buckets[outcome]:
            ver = f" {r['from_version']} -> {r['to_version']}" if r.get("from_version") else ""
            extra: list[str] = []
            if r.get("resumed"):
                extra.append("resumed")
            if r.get("repairs"):
                extra.append("repairs: " + ", ".join(r["repairs"]))
            if r.get("maintainers_added"):
                extra.append("maintainers added: " + ", ".join(r["maintainers_added"]))
            if r.get("meta_yaml"):
                extra.append(f"meta.yaml: {r['meta_yaml']}")
            if r.get("gates"):
                extra.append("gates: " + ", ".join(f"{g}={rc}" for g, rc in r["gates"].items()))
            if r.get("build"):
                extra.append(f"build: {r['build']['status']}")
            if r.get("dependency_diff"):
                extra.append("dependency diff: " + _dependency_summary(r["dependency_diff"]))
            tail = f" — {'; '.join(r['reasons'])}" if r.get("reasons") else ""
            lines.append(f"- `{r['name']}`{ver}{tail}" + (f" ({'; '.join(extra)})" if extra else ""))
            for note in r.get("notes", []):
                lines.append(f"  - {note}")
        lines.append("")
    return "\n".join(lines)


def _load_prev(report_dir: Path, mode: str, track: str, wave: str) -> dict[str, dict[str, Any]]:
    path = report_dir / "report.json"
    try:
        prev = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(prev, dict) or prev.get("mode") != mode or prev.get("track") != track or prev.get("wave") != wave:
        return {}
    return {r["name"]: r for r in prev.get("recipes", []) if isinstance(r, dict) and "name" in r}


def _resumable(prev: Optional[dict[str, Any]], entry: dict[str, Any], *, apply: bool) -> bool:
    if not prev or prev.get("outcome") not in TERMINAL_OUTCOMES:
        return False
    if prev.get("manifest_entry") != entry:
        return False
    if prev.get("recipe_sha256") != _recipe_hash(entry["name"]):
        return False
    if apply and prev.get("outcome") not in NO_WRITE_OUTCOMES and not prev.get("applied"):
        return False
    return True


def run_wave(
    manifest: dict[str, Any], *, repair: bool, apply: bool, gates: bool, build: bool,
    report_dir: Path, force: bool, echo: Any = None,
) -> dict[str, Any]:
    mode = "repair" if repair else "refresh"
    track, wave = manifest["track"], manifest["wave"]
    report_dir.mkdir(parents=True, exist_ok=True)
    prev = {} if force else _load_prev(report_dir, mode, track, wave)
    report: dict[str, Any] = {
        "schema_version": 1,
        "tool": "refresh_wave",
        "mode": mode,
        "track": track,
        "wave": wave,
        "applied": apply,
        "generated_at": _iso(_now()),
        "recipes": [],
        "summary": {},
    }
    for entry in manifest["recipes"]:
        if _resumable(prev.get(entry["name"]), entry, apply=apply):
            rec = dict(prev[entry["name"]])
            rec["resumed"] = True
        else:
            try:
                if repair:
                    rec = repair_recipe(entry, track=track, wave=wave, apply=apply, gates=gates and apply)
                else:
                    rec = refresh_recipe(
                        entry, track=track, wave=wave, apply=apply,
                        gates=gates and apply, build=build and apply,
                    )
            except Exception as exc:  # one recipe never takes the wave down
                rec = _finish(_new_record(entry, apply=apply), "failed", f"unexpected: {type(exc).__name__}: {exc}")
        report["recipes"].append(rec)
        report["summary"] = _summarise(report["recipes"])
        _write_json_atomic(report_dir / "report.json", report)
        if echo is not None:
            echo(f"{rec['name']}: {rec['outcome']}" + (" (resumed)" if rec.get("resumed") else ""))
    (report_dir / "report.md").write_text(_render_markdown(report), encoding="utf-8")
    return report


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="refresh-wave",
        description=(
            "Refresh local recipes to their feedstock's published version from a wave manifest "
            "(dry-run by default), or repair Wave H damage with --repair. Local only."
        ),
    )
    parser.add_argument("manifest", type=Path, help="Wave manifest (YAML or JSON).")
    parser.add_argument("--repair", action="store_true",
                        help="Undo hashed PyPI URLs, FMT-001 list indentation and a hidden meta.yaml; change nothing else.")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run, report only).")
    parser.add_argument("--gates", action="store_true",
                        help="With --apply, run validate, optimize, check-deps and scan on each written recipe.")
    parser.add_argument("--build", action="store_true",
                        help="With --apply, build each refreshed recipe into build_artifacts/<name> (refused with --repair).")
    parser.add_argument("--report-dir", type=Path, default=None,
                        help="Report directory (default: .claude/data/conda-forge-expert/refresh-waves/<track>-<wave>/).")
    parser.add_argument("--force", action="store_true", help="Reprocess recipes a previous run recorded as terminal.")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON on stdout.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.repair and args.build:
        parser.error("--build is refused with --repair")

    try:
        manifest = load_manifest(args.manifest)
        if args.report_dir is not None:
            report_dir = Path(args.report_dir).expanduser()
        else:
            data_dir = get_data_dir()
            if data_dir is None:
                raise ManifestError("cannot resolve the data directory; pass --report-dir")
            report_dir = data_dir / "refresh-waves" / f"{manifest['track']}-{manifest['wave']}"
        if _is_under(report_dir, recipes_root()):
            raise ManifestError(f"report directory must not be under recipes/: {report_dir}")
        if not recipes_root().is_dir():
            raise ManifestError(f"recipes root does not exist: {recipes_root()}")
        try:
            import ruamel.yaml  # noqa: F401
        except ImportError as exc:
            raise ManifestError("ruamel.yaml is required") from exc
    except ManifestError as exc:
        print(f"refresh-wave: {exc}", file=sys.stderr)
        return 2

    report = run_wave(
        manifest,
        repair=args.repair, apply=args.apply, gates=args.gates, build=args.build,
        report_dir=report_dir.resolve(), force=args.force,
        echo=None if args.json else (lambda line: print(line, file=sys.stderr)),
    )
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        counts = ", ".join(f"{k} {v}" for k, v in sorted(report["summary"].items()))
        print(f"refresh-wave {report['mode']} {'apply' if args.apply else 'dry-run'}: {counts}")
        print(f"report: {report_dir.resolve() / 'report.md'}")
    return 1 if any(r["outcome"] == "failed" for r in report["recipes"]) else 0


if __name__ == "__main__":
    sys.exit(main())
