#!/usr/bin/env python3
"""
Build the PyForge site.

Reads the content model in docsite/content/ and renders:

    dist/index.html                  landing page
    dist/dossier/index.html          the full dossier
    dist/infographics/index.html     gallery of the standalone infographics
    dist/infographics/<slug>.html    each infographic, published unmodified
    dist/decks/index.html            index of every deck family page
    dist/decks/<slug>/index.html     one family page per registered deck
    dist/assets/site.css             shared stylesheet
    dist/artifact/dossier.html       single-file build for the Artifact tool
    dist/.nojekyll                   stop GitHub Pages running Jekyll over it

Nothing here reaches the network and nothing is written outside dist/.

    python docsite/build.py                 # build into dist/
    python docsite/build.py --out _site     # build somewhere else
    python docsite/build.py --check         # build, then verify the output
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "docsite"

#: Everything this build creates, and therefore the only things it may delete.
#: The output directory can be a shared publish root (docs/dashboard/ also
#: carries the Kedro-Viz export), so cleanup is an allow-list, never a rmtree
#: of the whole directory.
OWNED_OUTPUTS = (
    "index.html",
    ".nojekyll",
    "assets",
    "dossier",
    "infographics",
    "decks",
    "artifact",
)
CONTENT = SITE / "content"
TEMPLATES = SITE / "templates"
ASSETS = SITE / "assets"

# ------------------------------------------------------------------ inline markdown

_ESCAPED = re.compile(r"\\(.)", re.S)
_ARROW = re.compile(r"<<(.+?)>>", re.S)
_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
_EM = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.S)
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_SLOT = re.compile(r"\x00(\d+)\x00")


def md_inline(text: str | None) -> str:
    """Render the small inline-Markdown subset the content model uses.

    Deliberately not a full Markdown parser: the content is inline-only, and a
    general parser would wrap everything in <p> and mangle the layout.

    The vocabulary is `code`, **bold**, *em*, [link](href) and <<arrow>>, with
    a backslash escaping any of the special characters so literal text like
    "recipes/**" or "0*" survives intact. Escapes, arrows and code spans are
    lifted out into slots before anything else runs, so their contents are
    never re-processed as markup.
    """
    if text is None:
        return ""
    text = str(text)

    slots: list[str] = []

    def put(fragment: str) -> str:
        slots.append(fragment)
        return f"\x00{len(slots) - 1}\x00"

    esc = lambda s: html.escape(s, quote=False)  # noqa: E731

    text = _ESCAPED.sub(lambda m: put(esc(m.group(1))), text)
    text = _ARROW.sub(lambda m: put(f'<span class="rel-arrow">{esc(m.group(1))}</span>'), text)
    text = _CODE.sub(lambda m: put(f"<code>{esc(m.group(1))}</code>"), text)

    text = esc(text)
    text = _LINK.sub(lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>', text)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _EM.sub(r"<em>\1</em>", text)

    return _SLOT.sub(lambda m: slots[int(m.group(1))], text)


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


# ------------------------------------------------------------------ infographics


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[\s_]+", "-", s) or "untitled"


TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def read_title(path: Path) -> str:
    head = path.read_text(encoding="utf-8", errors="replace")[:100_000]
    m = TITLE_RE.search(head)
    return html.unescape(m.group(1)).strip() if m else path.stem


BACKBAR = """<div class="ig-backbar">
  <a href="index.html">&larr; All infographics</a>
  <a href="../index.html">Overview</a>
  <a href="../dossier/index.html">Dossier</a>
  <span class="ig-title">{title}</span>
</div>
<style>
.ig-backbar{{position:fixed;top:0;left:0;right:0;z-index:2147483000;background:rgba(18,22,26,.86);
-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);font-family:"IBM Plex Mono",ui-monospace,
SFMono-Regular,Menlo,monospace;font-size:12px;padding:7px 16px;display:flex;align-items:center;gap:14px;
color:#e7ebe6;box-sizing:border-box}}
.ig-backbar a{{color:#e7ebe6;text-decoration:none;border-bottom:1px solid rgba(231,235,230,.4)}}
.ig-backbar a:hover{{border-bottom-color:#dd9a3f;color:#dd9a3f}}
.ig-backbar .ig-title{{color:rgba(231,235,230,.62);margin-left:auto;text-align:right;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
body{{padding-top:32px!important}}
@media print{{.ig-backbar{{display:none!important}}body{{padding-top:0!important}}}}
</style>
"""


def collect_infographics(cfg: dict, repo_root: Path) -> list[dict]:
    """Resolve the configured globs into an ordered list of infographics."""
    ig_cfg = cfg["infographics"]
    overrides = ig_cfg.get("overrides") or {}

    found: dict[Path, None] = {}
    for pattern in ig_cfg["include"]:
        for p in sorted(repo_root.glob(pattern)):
            if p.is_file() and p.suffix.lower() == ".html":
                found[p] = None

    for pattern in ig_cfg.get("exclude") or []:
        for p in repo_root.glob(pattern):
            found.pop(p, None)

    items = []
    for path in found:
        rel = path.relative_to(repo_root).as_posix()
        ov = overrides.get(rel) or overrides.get(path.name) or {}
        title = ov.get("title") or read_title(path)
        items.append(
            {
                "path": path,
                "source": rel,
                "title": title,
                "description": ov.get("description", ""),
                "order": ov.get("order", 500),
                "out_name": (ov.get("slug") or slugify(title)) + ".html",
                "bytes": path.stat().st_size,
            }
        )

    items.sort(key=lambda i: (i["order"], i["title"].lower()))

    seen: dict[str, int] = {}
    for i in items:
        base = i["out_name"]
        if base in seen:
            seen[base] += 1
            i["out_name"] = f"{base[:-5]}-{seen[base]}.html"
        else:
            seen[base] = 0
    return items


def publish_infographic(item: dict, out_dir: Path, inject: bool) -> None:
    raw = item["path"].read_text(encoding="utf-8", errors="replace")
    if inject:
        bar = BACKBAR.format(title=html.escape(item["title"], quote=False))
        m = re.search(r"<body[^>]*>", raw, re.I)
        if m:
            raw = raw[: m.end()] + "\n" + bar + raw[m.end() :]
        else:
            raw = bar + raw
    (out_dir / item["out_name"]).write_text(raw, encoding="utf-8")


# ------------------------------------------------------------------ build


def git_commit(repo_root: Path) -> str:
    for env_key in ("GITHUB_SHA",):
        if os.environ.get(env_key):
            return os.environ[env_key][:7]
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def build(out_dir: Path, repo_root: Path) -> dict:
    site_cfg = yaml.safe_load((CONTENT / "site.yml").read_text(encoding="utf-8"))
    doc = yaml.safe_load((CONTENT / "dossier.yml").read_text(encoding="utf-8"))

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        undefined=StrictUndefined,
        trim_blocks=False,
        lstrip_blocks=False,
        autoescape=False,  # content is trusted, first-party, and pre-escaped by md_inline
    )
    env.filters["md"] = md_inline

    css = "\n".join(
        [
            (ASSETS / "_dossier.css").read_text(encoding="utf-8"),
            "\n/* --- content-model additions --- */\n"
            ".soft-note{font-size:0.85rem;color:var(--rail);max-width:70ch;}\n"
            ".lattice-note{flex:1 1 260px;font-size:0.9rem;color:var(--ink-soft);max-width:40ch;}\n"
            "/* Long inline paths (src/shared/packages/pyforge-*) are wider than a\n"
            "   phone viewport and code does not wrap by default, which pushed the\n"
            "   whole page into a horizontal scroll at 390px. */\n"
            "/* Slash-joined runs like new/validate/build/diagnose/optimize/scan/submit\n"
            "   are a single unbreakable word to the layout engine and were pushing the\n"
            "   page wider than a phone. break-word only splits when nothing else fits,\n"
            "   so ordinary prose is untouched; code gets the stronger rule. */\n"
            "body{overflow-wrap:break-word;}\n"
            "code,.mono{overflow-wrap:anywhere;}\n"
            ".rung{grid-template-columns:30px minmax(0,1fr) auto;}\n"
            ".rung .name,.rung .desc{min-width:0;overflow-wrap:anywhere;}\n"
            "/* A bare `1fr` column has an auto (min-content) floor, so the tables'\n"
            "   min-width:440px escaped their own overflow-x wrapper and dragged the\n"
            "   whole page into a horizontal scroll on a phone. minmax(0,1fr) lets the\n"
            "   column shrink so the wrapper scrolls instead of the document. */\n"
            "@media (max-width:880px){.layout{grid-template-columns:minmax(0,1fr);}}\n"
            ".table-wrap{max-width:100%;}\n"
            "/* .rel-list is a flex column, so every <li> is a flex item with a\n"
            "   min-width:auto (min-content) floor — one long code span inside was\n"
            "   enough to stop the list shrinking on a phone. */\n"
            ".rel-list li{min-width:0;}\n"
            ".rel-list li>*{min-width:0;}\n"
            ".engines,.lattice-wrap,.chips{max-width:100%;}\n"
            "@media (max-width:520px){\n"
            "  .rung .desc{display:none;}\n"
            "  .hero-stat,.stat-row .s{padding-right:16px;margin-right:16px;}\n"
            "}\n",
        ]
    )
    site_css = css + "\n" + (ASSETS / "_site-chrome.css").read_text(encoding="utf-8")

    infographics = collect_infographics(site_cfg, repo_root)

    built_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    commit = git_commit(repo_root)

    shared = {
        "site": site_cfg,
        "doc": doc,
        "infographics": infographics,
        "built_at": built_at,
        "commit": commit,
    }

    # Clean only what this build owns. The output directory may be a shared
    # publish root — docs/dashboard/ also holds the Kedro-Viz export, which a
    # blanket rmtree would delete on every run.
    for owned in OWNED_OUTPUTS:
        target = out_dir / owned
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()

    (out_dir / "assets").mkdir(parents=True, exist_ok=True)
    (out_dir / "dossier").mkdir(parents=True, exist_ok=True)
    (out_dir / "infographics").mkdir(parents=True, exist_ok=True)
    (out_dir / "artifact").mkdir(parents=True, exist_ok=True)

    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    (out_dir / "assets" / "site.css").write_text(site_css, encoding="utf-8")

    summary = strip_tags(md_inline(doc["summary"]))

    (out_dir / "index.html").write_text(
        env.get_template("page_index.html.j2").render(
            page_title=f"{site_cfg['name']} — {site_cfg['eyebrow']}",
            page_description=summary,
            page_key="index",
            rel="",
            **shared,
        ),
        encoding="utf-8",
    )

    (out_dir / "dossier" / "index.html").write_text(
        env.get_template("page_dossier.html.j2").render(
            page_title=doc["title"],
            page_description=summary,
            page_key="dossier",
            rel="../",
            **shared,
        ),
        encoding="utf-8",
    )

    (out_dir / "infographics" / "index.html").write_text(
        env.get_template("page_gallery.html.j2").render(
            page_title=f"Infographics — {site_cfg['name']}",
            page_description=f"{len(infographics)} standalone infographics published from the repository.",
            page_key="gallery",
            rel="../",
            **shared,
        ),
        encoding="utf-8",
    )

    inject = bool(site_cfg["infographics"].get("inject_backbar", True))
    for item in infographics:
        publish_infographic(item, out_dir / "infographics", inject)

    (out_dir / "artifact" / "dossier.html").write_text(
        env.get_template("shell_artifact.html.j2").render(
            page_title=doc["title"], css=css, rel="", **shared
        ),
        encoding="utf-8",
    )

    return {"infographics": infographics, "out": out_dir, "commit": commit, "built_at": built_at}


# ------------------------------------------------------------------ checks


def check(out_dir: Path, result: dict) -> int:
    problems: list[str] = []

    required = [
        "index.html", ".nojekyll", "assets/site.css",
        "dossier/index.html", "infographics/index.html", "artifact/dossier.html",
    ]
    for r in required:
        p = out_dir / r
        if not p.exists():
            problems.append(f"missing output: {r}")
        elif r.endswith(".html") and p.stat().st_size < 500:
            problems.append(f"suspiciously small: {r} ({p.stat().st_size}B)")

    artifact = (out_dir / "artifact" / "dossier.html").read_text(encoding="utf-8")
    for tag in ("<!doctype", "<html", "<head", "<body"):
        if tag in artifact.lower():
            problems.append(f"artifact build must not contain {tag!r} — the Artifact host supplies it")

    dossier = (out_dir / "dossier" / "index.html").read_text(encoding="utf-8")
    if "{{" in dossier or "{%" in dossier:
        problems.append("unrendered Jinja delimiters in dossier output")

    for item in result["infographics"]:
        p = out_dir / "infographics" / item["out_name"]
        if not p.exists():
            problems.append(f"infographic not published: {item['source']}")
        elif p.stat().st_size < item["bytes"]:
            problems.append(f"infographic shrank on publish: {item['out_name']}")

    gallery = (out_dir / "infographics" / "index.html").read_text(encoding="utf-8")
    for item in result["infographics"]:
        if item["out_name"] not in gallery:
            problems.append(f"infographic missing from gallery: {item['out_name']}")

    if problems:
        print("\nFAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"checks passed — {len(required)} required outputs, {len(result['infographics'])} infographics")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="dist", help="output directory (default: dist)")
    ap.add_argument("--repo-root", default=None, help="repository root the infographic globs resolve against")
    ap.add_argument("--check", action="store_true", help="verify the build after writing it")
    args = ap.parse_args()

    out_dir = (Path.cwd() / args.out).resolve()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else ROOT

    result = build(out_dir, repo_root)

    total = sum(len(list(p.rglob("*"))) for p in [out_dir] if p.exists())
    print(f"built {out_dir}  ({total} files, commit {result['commit'] or 'n/a'}, {result['built_at']})")
    for item in result["infographics"]:
        print(f"  infographic  {item['out_name']:<46} {item['bytes'] // 1024:>5} KB  {item['source']}")

    return check(out_dir, result) if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
