"""Story 27.6: every relative import under docs-site resolves to a tracked file."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

_JS_TRACKED_SUFFIXES = (".mjs", ".js", ".mts", ".ts", ".jsx", ".tsx")
_VITE_EXTENSIONS = (".mjs", ".js", ".mts", ".ts", ".jsx", ".tsx", ".json")
_SKIP_DIR_NAMES = frozenset({"node_modules", "build", ".astro"})


@dataclass(frozen=True)
class ImportFinding:
    kind: str  # "unresolved" | "untracked"
    importer: str
    specifier: str
    resolved: str | None = None


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "pyforge-herald"
        ).is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def _strip_js_comments(source: str) -> str:
    """Remove ``//`` and ``/* */`` comments; leave string literals intact."""
    out: list[str] = []
    i = 0
    n = len(source)
    in_line = False
    in_block = False
    in_single = False
    in_double = False
    in_template = False
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if in_line:
            if ch == "\n":
                in_line = False
                out.append(ch)
            else:
                out.append(" ")
            i += 1
            continue
        if in_block:
            if ch == "*" and nxt == "/":
                in_block = False
                out.append("  ")
                i += 2
            else:
                out.append(" ")
                i += 1
            continue
        if in_single:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(nxt)
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(nxt)
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            continue
        if in_template:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(nxt)
                i += 2
                continue
            if ch == "`":
                in_template = False
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line = True
            out.append("  ")
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block = True
            out.append("  ")
            i += 2
            continue
        if ch == "'":
            in_single = True
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_double = True
            out.append(ch)
            i += 1
            continue
        if ch == "`":
            in_template = True
            out.append(ch)
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


_REL_IMPORT_RE = re.compile(r"""(?:import\s+(?:[^'"]+\s+from\s+)?|export\s+[^'"]+\s+from\s+)['"](\.\.?/[^'"]+)['"]""")
_SIDE_EFFECT_IMPORT_RE = re.compile(r"""import\s+['"](\.\.?/[^'"]+)['"]""")
_DYNAMIC_IMPORT_RE = re.compile(r"""import\s*\(\s*['"](\.\.?/[^'"]+)['"]\s*\)""")
_REQUIRE_RE = re.compile(r"""require\s*\(\s*['"](\.\.?/[^'"]+)['"]\s*\)""")


def _relative_specifiers(source: str) -> list[str]:
    stripped = _strip_js_comments(source)
    found: list[str] = []
    for pattern in (
        _REL_IMPORT_RE,
        _SIDE_EFFECT_IMPORT_RE,
        _DYNAMIC_IMPORT_RE,
        _REQUIRE_RE,
    ):
        for match in pattern.finditer(stripped):
            spec = match.group(1)
            if spec.startswith("./") or spec.startswith("../"):
                found.append(spec)
    return found


def _resolve_relative(importer: Path, specifier: str) -> Path | None:
    base = (importer.parent / specifier).resolve()
    if base.is_file():
        return base
    suffix = base.suffix
    if suffix:
        return None
    for ext in _VITE_EXTENSIONS:
        candidate = Path(str(base) + ext)
        if candidate.is_file():
            return candidate.resolve()
    for ext in _VITE_EXTENSIONS:
        candidate = base / f"index{ext}"
        if candidate.is_file():
            return candidate.resolve()
    return None


def _git_ls_files(root: Path, pathspec: str) -> set[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z", "--", pathspec],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (
            proc.stderr.decode("utf-8", errors="replace").strip()
            or proc.stdout.decode("utf-8", errors="replace").strip()
        )
        raise RuntimeError(f"git ls-files failed: {detail}")
    raw = proc.stdout
    if not raw:
        return set()
    return {p.decode("utf-8") for p in raw.split(b"\0") if p}


def _tracked_docs_site_js(root: Path) -> list[Path]:
    tracked = _git_ls_files(root, "docs-site")
    paths: list[Path] = []
    for rel in sorted(tracked):
        if not rel.endswith(_JS_TRACKED_SUFFIXES):
            continue
        parts = Path(rel).parts
        if any(part in _SKIP_DIR_NAMES for part in parts):
            continue
        paths.append((root / rel).resolve())
    return paths


def docs_site_relative_import_findings(root: Path) -> tuple[list[ImportFinding], int]:
    """Return findings and the count of relative import specifiers checked."""
    try:
        tracked = _git_ls_files(root, "docs-site")
    except RuntimeError as exc:
        raise AssertionError(str(exc)) from exc
    tracked_set = set(tracked)
    findings: list[ImportFinding] = []
    checked = 0
    for importer in _tracked_docs_site_js(root):
        rel_importer = importer.relative_to(root).as_posix()
        text = importer.read_text(encoding="utf-8")
        for spec in _relative_specifiers(text):
            checked += 1
            resolved = _resolve_relative(importer, spec)
            if resolved is None:
                findings.append(
                    ImportFinding(
                        kind="unresolved",
                        importer=rel_importer,
                        specifier=spec,
                    )
                )
                continue
            rel_resolved = resolved.relative_to(root).as_posix()
            if rel_resolved not in tracked_set:
                findings.append(
                    ImportFinding(
                        kind="untracked",
                        importer=rel_importer,
                        specifier=spec,
                        resolved=rel_resolved,
                    )
                )
    return findings, checked


def _git_check_ignore(root: Path, *args: str) -> int:
    proc = subprocess.run(
        ["git", "check-ignore", *args],
        cwd=root,
        capture_output=True,
        check=False,
    )
    return proc.returncode


def test_docs_site_relative_imports_are_tracked() -> None:
    root = _repo_root()
    findings, checked = docs_site_relative_import_findings(root)
    assert not findings, findings
    assert checked >= 2, f"expected at least two relative imports checked, got {checked}"


def test_gitignore_lib_exception_for_docs_site_helper() -> None:
    root = _repo_root()
    ignore = (root / ".gitignore").read_text(encoding="utf-8")
    assert "lib/" in ignore.splitlines()
    negations = [line.strip() for line in ignore.splitlines() if line.strip().startswith("!") and "docs-site" in line]
    assert negations == ["!docs-site/src/lib/"]
    assert _git_check_ignore(root, "-q", "docs-site/src/lib/site-url.mjs") == 1
    assert _git_check_ignore(root, "--no-index", "-q", "lib/probe.py") == 0
    assert _git_check_ignore(root, "--no-index", "-q", "docs-site/lib/probe.mjs") == 0


def test_synthetic_untracked_and_unresolved_imports(tmp_path: Path) -> None:
    if shutil.which("git") is None:
        raise AssertionError("git not on PATH")
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    docs = tmp_path / "docs-site"
    docs.mkdir()
    helper = docs / "src" / "lib" / "site-url.mjs"
    helper.parent.mkdir(parents=True)
    helper.write_text("export function getSiteUrl() { return 'http://localhost/'; }\n", encoding="utf-8")
    loader = docs / "src" / "loaders" / "shelf-docs-loader.ts"
    loader.parent.mkdir(parents=True)
    loader.write_text("export const x = 1;\n", encoding="utf-8")
    config = docs / "astro.config.mjs"
    config.write_text(
        "import { getSiteUrl } from './src/lib/site-url.mjs';\n"
        "import 'astro/config';\n"
        "// import x from './gone.mjs';\n"
        "import missing from './no-such-file.mjs';\n",
        encoding="utf-8",
    )
    content_cfg = docs / "src" / "content.config.ts"
    content_cfg.write_text(
        "import loader from './loaders/shelf-docs-loader';\nexport { loader };\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "add", str(config), str(content_cfg), str(loader)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    findings, _ = docs_site_relative_import_findings(tmp_path)
    kinds = {(f.kind, f.resolved or f.specifier) for f in findings}
    assert ("untracked", "docs-site/src/lib/site-url.mjs") in kinds
    assert ("unresolved", "./no-such-file.mjs") in kinds
    assert not any(f.specifier == "./gone.mjs" for f in findings)
    assert not any("astro/config" in f.specifier for f in findings)

    subprocess.run(["git", "add", str(helper)], cwd=tmp_path, check=True, capture_output=True)
    findings2, checked2 = docs_site_relative_import_findings(tmp_path)
    assert not any(f.kind == "untracked" and f.resolved == "docs-site/src/lib/site-url.mjs" for f in findings2)
    assert checked2 >= 2
    assert not any(
        f.kind == "untracked" and f.resolved == "docs-site/src/loaders/shelf-docs-loader.ts" for f in findings2
    )
