"""Shared pin-policy registry I/O, pixi.toml dependency walks, and diff logic."""
from __future__ import annotations

import json
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import yaml
from jsonschema import Draft202012Validator
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO_ROOT / "docs" / "governance" / "pin-policy.yaml"
SCHEMA_PATH = REPO_ROOT / "docs" / "governance" / "pin-policy.schema.json"
MANIFEST_PATH = REPO_ROOT / "pixi.toml"
LOCK_PATH = REPO_ROOT / "pixi.lock"
STATION_PACKAGES = REPO_ROOT / "src" / "shared" / "packages"

_CONDA_PKG_VER = re.compile(r"/([a-z0-9][a-z0-9_-]*)-(\d+(?:\.\d+)*)-\d+")
_CAP_RE = re.compile(r"(<|<=)\s*([^,\s]+)")


@dataclass(frozen=True)
class Finding:
    kind: str
    package: str
    feature: str
    detail: str
    severity: str = "error"  # error | warning

    def format_line(self) -> str:
        return f"{self.kind}: {self.package} @ {self.feature}: {self.detail}"


@dataclass(frozen=True)
class DepDecl:
    """One dependency declaration in a feature table."""

    feature: str
    package: str
    spec: str  # normalized string form for diff/compare
    raw: object  # tomllib value
    has_cap: bool
    has_channel: bool
    has_exact: bool


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: policy root must be a mapping")
    return data


def validate_policy(policy: dict[str, Any], schema_path: Path = SCHEMA_PATH) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    return sorted(f"{e.message} @ {list(e.path)}" for e in validator.iter_errors(policy))


def _feature_path(parts: list[str]) -> str:
    """Turn TOML key path into a feature label like python or pyforge-marshal.target.linux-64."""
    if not parts:
        return "workspace"
    if parts[0] != "feature":
        return ".".join(parts)
    if len(parts) == 1:
        return parts[0]
    feat = parts[1]
    rest = parts[2:]
    if rest and rest[0] == "target" and len(rest) >= 2:
        return f"{feat}.target.{rest[1]}"
    return feat


def iter_dependency_decls(manifest: dict[str, Any]) -> Iterator[DepDecl]:
    """Every (feature, package) declaration in dependency tables."""

    def walk(node: object, path: list[str]) -> None:
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            here = [*path, str(key)]
            if str(key).endswith("dependencies") and isinstance(value, dict):
                feature = _feature_path(path)
                for name, spec in value.items():
                    if not isinstance(name, str):
                        continue
                    has_channel = isinstance(spec, dict) and "channel" in spec
                    spec_str = _spec_to_str(spec)
                    has_cap = "<" in spec_str or "<=" in spec_str
                    has_exact = _is_exact_pin(spec_str)
                    yield DepDecl(
                        feature=feature,
                        package=name,
                        spec=spec_str,
                        raw=spec,
                        has_cap=has_cap,
                        has_channel=has_channel,
                        has_exact=has_exact,
                    )
            elif isinstance(value, dict):
                walk(value, here)

    walk(manifest, [])


def _spec_to_str(spec: object) -> str:
    if isinstance(spec, dict):
        parts = []
        if "version" in spec:
            parts.append(f'version = "{spec["version"]}"')
        if "channel" in spec:
            parts.append(f'channel = "{spec["channel"]}"')
        return "{" + ", ".join(parts) + "}"
    return str(spec)


def _is_exact_pin(spec_str: str) -> bool:
    if spec_str.startswith("{") and "version" in spec_str:
        m = re.search(r'version\s*=\s*"([^"]+)"', spec_str)
        if m and "*" in m.group(1):
            return True
    return bool(re.fullmatch(r"\d+\.\d+\.\d+\.\*", spec_str.strip('"')) or (
        ".*" in spec_str and not spec_str.startswith(">=")
    ))


def _cap_clause(spec_str: str) -> str | None:
    m = _CAP_RE.search(spec_str)
    if not m:
        return None
    return f"{m.group(1)}{m.group(2)}" if m.group(1) == "<" else f"{m.group(1)} {m.group(2)}"


def _channel_name(spec: object) -> str | None:
    if isinstance(spec, dict) and "channel" in spec:
        return str(spec["channel"])
    return None


def _row_covers_feature(row_features: object, feature: str) -> bool:
    if row_features == "*":
        return True
    if isinstance(row_features, list):
        return feature in row_features or any(
            feature == f or feature.startswith(f + ".") for f in row_features
        )
    return False


def _matching_rows(policy: dict[str, Any], package: str, feature: str) -> list[dict[str, Any]]:
    holds = policy.get("holds") or []
    return [
        h
        for h in holds
        if isinstance(h, dict)
        and h.get("package") == package
        and _row_covers_feature(h.get("features"), feature)
    ]


def render_upgrade_command(policy: dict[str, Any]) -> str:
    defaults = policy.get("defaults") or {}
    strategy = defaults.get("pinning_strategy", "latest-up")
    never = sorted(
        {
            str(h["package"])
            for h in policy.get("holds") or []
            if isinstance(h, dict) and h.get("hold") == "never-move"
        }
    )
    parts = ["pixi", "upgrade", f"--pinning-strategy={strategy}"]
    for pkg in never:
        parts.extend(["--exclude", pkg])
    return " ".join(parts)


def read_pointer_line(manifest_text: str) -> str | None:
    for line in manifest_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") and "pin-policy.yaml" in stripped:
            return stripped.lstrip("#").strip()
    return None


def check_static(
    policy: dict[str, Any],
    manifest: dict[str, Any],
    manifest_text: str,
) -> list[Finding]:
    findings: list[Finding] = []
    schema_errs = validate_policy(policy)
    for msg in schema_errs:
        findings.append(Finding("schema-violation", "", "", msg))

    decls = list(iter_dependency_decls(manifest))
    declared_packages: dict[str, set[str]] = {}
    for d in decls:
        declared_packages.setdefault(d.package, set()).add(d.feature)

    for d in decls:
        needs_row = d.has_cap or d.has_channel or d.has_exact
        if not needs_row:
            continue
        rows = _matching_rows(policy, d.package, d.feature)
        if not rows:
            clause = d.spec
            findings.append(
                Finding(
                    "undeclared-hold",
                    d.package,
                    d.feature,
                    f"declaration {clause!r} has no registry row",
                )
            )

    for row in policy.get("holds") or []:
        if not isinstance(row, dict):
            continue
        pkg = row.get("package", "")
        feats = row.get("features")
        if feats == "*":
            if pkg not in declared_packages:
                findings.append(
                    Finding(
                        "dangling-hold",
                        pkg,
                        "*",
                        "row features * but no feature declares this package",
                    )
                )
            continue
        if isinstance(feats, list):
            covered = any(f in declared_packages.get(pkg, set()) for f in feats)
            if not covered:
                findings.append(
                    Finding(
                        "dangling-hold",
                        pkg,
                        ",".join(feats),
                        "no listed feature declares this package",
                    )
                )

    rendered = render_upgrade_command(policy)
    pointer = (policy.get("pointer") or "").strip()
    expected_comment = pointer if pointer else ""
    actual = read_pointer_line(manifest_text)
    if expected_comment and actual != expected_comment:
        findings.append(
            Finding(
                "stale-pointer",
                "pixi.toml",
                "pointer",
                f"expected comment {expected_comment!r}, got {actual!r}",
            )
        )

    for row in policy.get("holds") or []:
        if isinstance(row, dict) and row.get("until") == "unknown":
            findings.append(
                Finding(
                    "until-unknown",
                    str(row.get("package", "")),
                    str(row.get("features", "")),
                    "registry row has until: unknown",
                    severity="warning",
                )
            )

    for row in policy.get("holds") or []:
        if not isinstance(row, dict):
            continue
        hold = row.get("hold")
        if hold == "never-move":
            if not str(row.get("reason", "")).strip():
                findings.append(
                    Finding(
                        "schema-violation",
                        str(row.get("package", "")),
                        "",
                        "never-move row missing reason",
                    )
                )
            if not str(row.get("authority", "")).strip():
                findings.append(
                    Finding(
                        "schema-violation",
                        str(row.get("package", "")),
                        "",
                        "never-move row missing authority",
                    )
                )

    return findings


def _floor_from_spec(spec_str: str) -> Version | None:
    m = re.search(r">=\s*(\d+(?:\.\d+)*)", spec_str)
    if not m:
        m = re.search(r">\s*(\d+(?:\.\d+)*)", spec_str)
    if not m:
        return None
    try:
        return Version(m.group(1))
    except InvalidVersion:
        return None


def _read_manifest_at_ref(ref: str, root: Path = REPO_ROOT) -> tuple[dict[str, Any] | None, str]:
    try:
        proc = subprocess.run(
            ["git", "show", f"{ref}:pixi.toml"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return None, str(exc)
    if proc.returncode != 0:
        return None, proc.stderr.strip() or f"git show {ref}:pixi.toml failed"
    try:
        return tomllib.loads(proc.stdout), proc.stdout
    except tomllib.TOMLDecodeError as exc:
        return None, str(exc)


def check_diff(
    policy: dict[str, Any],
    base_ref: str,
    current_manifest: dict[str, Any],
    *,
    root: Path = REPO_ROOT,
) -> tuple[list[Finding], str | None]:
    base_manifest, err = _read_manifest_at_ref(base_ref, root=root)
    if base_manifest is None:
        return [], err

    floors_never_lower = bool((policy.get("defaults") or {}).get("floors_never_lower", True))
    never_move = {
        str(h["package"])
        for h in policy.get("holds") or []
        if isinstance(h, dict) and h.get("hold") == "never-move"
    }

    base_index = {(d.feature, d.package): d for d in iter_dependency_decls(base_manifest)}
    now_index = {(d.feature, d.package): d for d in iter_dependency_decls(current_manifest)}

    findings: list[Finding] = []
    seen_flatten: set[tuple[str, str]] = set()

    for key, base_d in base_index.items():
        feature, package = key
        now_d = now_index.get(key)
        if now_d is None:
            continue
        if base_d.spec == now_d.spec:
            continue

        if package in never_move and base_d.spec != now_d.spec:
            findings.append(
                Finding(
                    "moved-hold",
                    package,
                    feature,
                    f"never-move expression changed {base_d.spec!r} -> {now_d.spec!r}",
                )
            )

        base_cap = _cap_clause(base_d.spec)
        now_cap = _cap_clause(now_d.spec)
        if base_cap and not now_cap:
            if (feature, package) not in seen_flatten:
                if base_d.has_channel and not now_d.has_channel:
                    findings.append(
                        Finding(
                            "flattened-table",
                            package,
                            feature,
                            f"inline table flattened {base_d.spec!r} -> {now_d.spec!r}",
                        )
                    )
                    seen_flatten.add((feature, package))
                else:
                    findings.append(
                        Finding(
                            "lost-cap",
                            package,
                            feature,
                            f"cap lost {base_d.spec!r} -> {now_d.spec!r}",
                        )
                    )
        elif base_d.has_channel and not now_d.has_channel:
            if (feature, package) not in seen_flatten:
                findings.append(
                    Finding(
                        "flattened-table",
                        package,
                        feature,
                        f"channel table flattened {base_d.spec!r} -> {now_d.spec!r}",
                    )
                )
                seen_flatten.add((feature, package))

        if floors_never_lower:
            bf = _floor_from_spec(base_d.spec)
            nf = _floor_from_spec(now_d.spec)
            if bf is not None and nf is not None and nf < bf:
                findings.append(
                    Finding(
                        "lowered-floor",
                        package,
                        feature,
                        f"floor lowered {bf} -> {nf}",
                    )
                )

    return findings, None


def _station_env_name(station_dir: Path) -> str:
    return station_dir.name.replace("pyforge-", "pyforge-")


def _pep508_name_spec(req: str) -> tuple[str, str] | None:
    m = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(.*)$", req.strip())
    if not m:
        return None
    return m.group(1).lower().replace("_", "-"), m.group(2).strip()


def _normalize_pkg(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def station_package_ranges(root: Path = REPO_ROOT) -> list[tuple[str, Path, str, str]]:
    """(station, file, package, range_spec) for package-level pins."""
    out: list[tuple[str, Path, str, str]] = []
    for pkg_dir in sorted((root / "src/shared/packages").glob("pyforge-*/")):
        station = pkg_dir.name
        pyproject = pkg_dir / "pyproject.toml"
        if pyproject.is_file():
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            deps = (data.get("project") or {}).get("dependencies") or []
            if isinstance(deps, list):
                for req in deps:
                    if not isinstance(req, str):
                        continue
                    parsed = _pep508_name_spec(req)
                    if parsed:
                        out.append((station, pyproject, parsed[0], parsed[1]))
        pixi = pkg_dir / "pixi.toml"
        if pixi.is_file():
            data = tomllib.loads(pixi.read_text(encoding="utf-8"))
            run_deps = (data.get("package") or {}).get("run-dependencies") or {}
            if isinstance(run_deps, dict):
                for name, spec in run_deps.items():
                    spec_str = _spec_to_str(spec) if not isinstance(spec, str) else spec
                    out.append((station, pixi, _normalize_pkg(name), spec_str))
    return out


def locked_version_in_env(
    lock: dict[str, Any], env_name: str, package: str, *, platform: str = "linux-64"
) -> Version | None:
    envs = lock.get("environments") or {}
    block = envs.get(env_name) or {}
    packages = (block.get("packages") or {}).get(platform) or []
    pkg_norm = _normalize_pkg(package)
    for entry in packages:
        url = entry.get("conda") or entry.get("pypi") or ""
        if not url:
            continue
        m = _CONDA_PKG_VER.search(str(url))
        if m and _normalize_pkg(m.group(1)) == pkg_norm:
            try:
                return Version(m.group(2))
            except InvalidVersion:
                continue
    return None


def version_in_range(version: Version, spec: str) -> bool:
    if not spec:
        return True
    try:
        return version in SpecifierSet(spec.replace("=", "==").split(";")[0].strip())
    except Exception:
        return True


def check_fan_out(root: Path = REPO_ROOT, lock_path: Path = LOCK_PATH) -> list[Finding]:
    if not lock_path.is_file():
        return [
            Finding(
                "station-range-unresolved",
                "",
                "",
                f"cannot read {lock_path}",
            )
        ]
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    findings: list[Finding] = []
    for station, path, package, spec in station_package_ranges(root):
        env = station if (root / "pixi.toml").exists() else station
        env = station  # pyforge-marshal env name matches package dir
        locked = locked_version_in_env(lock, env, package)
        if locked is None:
            findings.append(
                Finding(
                    "station-range-unresolved",
                    package,
                    station,
                    f"no locked version for {package} in env {env!r} ({path})",
                )
            )
            continue
        if not version_in_range(locked, spec):
            findings.append(
                Finding(
                    "station-range-excludes",
                    package,
                    station,
                    f"{path}: range {spec!r} excludes locked {locked} in {env}",
                )
            )
    return findings


def exit_code_from_findings(findings: list[Finding]) -> int:
    if any(f.severity == "error" for f in findings):
        return 1
    return 0
