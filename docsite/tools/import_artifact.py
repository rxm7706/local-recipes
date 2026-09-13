#!/usr/bin/env python3
"""
One-time migration: parse the published PyForge Dossier artifact HTML into the
repo's editable content model (docsite/content/dossier.yml).

After this has been run once and the YAML is committed, the YAML is the source
of truth and this script is only kept for reference / re-import.

Usage:
    python docsite/tools/import_artifact.py docsite/tools/_source_dossier.html docsite/content/dossier.yml
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from bs4 import BeautifulSoup, NavigableString, Tag

# ---------------------------------------------------------------- inline HTML -> markdown


#: characters that carry meaning in the inline-Markdown subset and so must be
#: backslash-escaped when they appear as literal text (e.g. "recipes/**",
#: "0*", "`.herald/herald.db`" written as prose rather than as a <code> tag).
_MD_SPECIALS = str.maketrans({c: "\\" + c for c in "\\`*["})


def inline_md(node: Tag | NavigableString) -> str:
    """Convert a node's inline children to Markdown.

    Only the inline vocabulary the dossier actually uses is supported:
    <code> -> `x`, <b>/<strong> -> **x**, <em>/<i> -> *x*, <a> -> [x](href),
    and <span class="rel-arrow"> -> <<x>>. Anything else is flattened to its
    text so nothing is silently dropped.
    """
    out: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            out.append(str(child).translate(_MD_SPECIALS))
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name
        if name == "code":
            # verbatim: code spans are never re-processed on the way back out
            raw = child.get_text()
            if "`" in raw:
                raise SystemExit(f"backtick inside <code> is not representable: {raw!r}")
            out.append(f"`{raw}`")
            continue
        inner = inline_md(child)
        if name in ("b", "strong"):
            out.append(f"**{inner}**")
        elif name in ("em", "i"):
            out.append(f"*{inner}*")
        elif name == "a":
            out.append(f"[{inner}]({child.get('href', '')})")
        elif name == "span" and "rel-arrow" in (child.get("class") or []):
            out.append(f"<<{inner}>>")
        elif name == "br":
            out.append("\n")
        else:
            out.append(inner)
    # collapse the incidental whitespace that HTML indentation introduces
    return " ".join("".join(out).split())


def paras(node: Tag, selector: str = "p") -> list[str]:
    return [inline_md(p) for p in node.find_all(selector, recursive=False)]


def css_var(style: str | None, prop: str) -> str | None:
    """Pull `var(--x)` out of an inline style declaration."""
    if not style:
        return None
    for part in style.split(";"):
        if ":" not in part:
            continue
        key, _, val = part.partition(":")
        if key.strip() == prop:
            val = val.strip()
            if val.startswith("var(") and val.endswith(")"):
                return val[4:-1].strip()
            return val
    return None


# ---------------------------------------------------------------- block parsers


def parse_table(wrap: Tag) -> dict:
    table = wrap.find("table")
    headers = [inline_md(th) for th in table.select("thead th")]
    rows = []
    for tr in table.select("tbody tr"):
        cells = tr.find_all("td", recursive=False)
        rows.append(
            {
                "cells": [inline_md(td) for td in cells],
                # the dossier uses class="mono" on first cells; keep that signal
                "mono": [("mono" in (td.get("class") or [])) for td in cells],
            }
        )
    if not any(any(r["mono"]) for r in rows):
        for r in rows:
            r.pop("mono")
    return {"type": "table", "headers": headers, "rows": rows}


def parse_lattice(wrap: Tag) -> dict:
    rungs = []
    for rung in wrap.select(".lattice .rung"):
        exit_el = rung.select_one(".exit")
        rungs.append(
            {
                "exit": inline_md(exit_el),
                "name": inline_md(rung.select_one(".name")),
                "desc": inline_md(rung.select_one(".desc")) or "",
                "tone": css_var(rung.get("style"), "background") or "",
                "exit_tone": css_var(exit_el.get("style"), "background") or "",
            }
        )
    note_el = wrap.find("p", recursive=False)
    return {
        "type": "lattice",
        "rungs": rungs,
        "note": inline_md(note_el) if note_el else "",
    }


def parse_engines(wrap: Tag) -> dict:
    engines = []
    for eng in wrap.select(".engine"):
        engines.append(
            {
                "name": inline_md(eng.find("h4")),
                "verb": inline_md(eng.select_one(".verb")),
                "body": paras(eng),
            }
        )
    return {"type": "engines", "engines": engines}


LENS_KEYS = ("ceo", "cfo", "cdao", "eng")


def parse_scorecards(section: Tag) -> dict:
    lenses = []
    for btn in section.select(".lens-btn"):
        lenses.append({"key": btn["data-lens"], "label": inline_md(btn)})

    rows = []
    for tr in section.select("#sc-body tr"):
        station_cell = tr.select_one(".sc-station")
        epic_cell = tr.select_one(".sc-epic")
        # pull the <b>NN</b> out first — computing the label from the whole
        # cell and then string-replacing leaves the bold markers behind
        epic_b = epic_cell.find("b")
        epic_num = epic_b.get_text(strip=True) if epic_b else ""
        if epic_b:
            epic_b.extract()
        row = {
            "station": inline_md(station_cell),
            "accent": css_var(station_cell.select_one(".dot").get("style"), "background") or "",
            "epic_num": epic_num,
            "epic": inline_md(epic_cell),
            "counts": inline_md(tr.select_one(".sc-counts")),
            "counts_html": "".join(str(c) for c in tr.select_one(".sc-counts").children).strip(),
            "delivers": inline_md(tr.select_one(".sc-deliver")),
            "open": int(tr["data-open"]),
            "lenses": {},
        }
        for key in LENS_KEYS:
            row["lenses"][key] = {
                "hit": tr.get(f"data-{key}") == "1",
                "note": tr.get(f"data-{key}-note", ""),
            }
        rows.append(row)

    proto = section.select_one(".sc-proto-note")
    return {
        "type": "scorecards",
        "lenses": lenses,
        "rows": rows,
        "footnote": inline_md(proto) if proto else "",
    }


def parse_blocks(section: Tag) -> list[dict]:
    """Walk a section's direct children in document order into typed blocks."""
    blocks: list[dict] = []
    for el in section.children:
        if not isinstance(el, Tag):
            continue
        classes = el.get("class") or []
        name = el.name

        if "section-head" in classes or "station-head" in classes:
            continue  # handled as section metadata
        if name == "blockquote" and "station-quote" in classes:
            blocks.append({"type": "quote", "md": inline_md(el)})
        elif "stat-row" in classes:
            blocks.append(
                {
                    "type": "stats",
                    "stats": [
                        {"value": inline_md(s.find("b")), "label": inline_md(s.find("span"))}
                        for s in el.select(".s")
                    ],
                }
            )
        elif name == "p" and "lede" in classes:
            blocks.append({"type": "lede", "md": inline_md(el)})
        elif name == "h3":
            num = el.select_one(".h3-num")
            num_text = inline_md(num) if num else ""
            if num:
                num.extract()
            blocks.append({"type": "h3", "num": num_text, "text": inline_md(el)})
        elif name == "div" and "prose" in classes:
            blocks.append({"type": "prose", "body": paras(el)})
        elif name == "p" and "prose" in classes:
            blocks.append({"type": "prose", "body": [inline_md(el)]})
        elif "table-wrap" in classes:
            blocks.append(parse_table(el))
        elif "callout" in classes:
            label = el.select_one(".label")
            label_text = inline_md(label) if label else ""
            if label:
                label.extract()
            tone = "red" if "red" in classes else "green" if "green" in classes else "amber"
            blocks.append({"type": "callout", "tone": tone, "label": label_text, "body": paras(el)})
        elif "find-box" in classes:
            flabel = el.select_one(".flabel")
            flabel_text = inline_md(flabel) if flabel else ""
            if flabel:
                flabel.extract()
            blocks.append(
                {
                    "type": "finding",
                    "label": flabel_text,
                    "accent": css_var(el.get("style"), "border-left-color") or "",
                    "alarm": "red" in classes,
                    "body": paras(el),
                }
            )
        elif "chips" in classes:
            blocks.append({"type": "chips", "chips": [inline_md(c) for c in el.select(".chip")]})
        elif "lattice-wrap" in classes:
            blocks.append(parse_lattice(el))
        elif "engines" in classes:
            blocks.append(parse_engines(el))
        elif name == "ul" and "rel-list" in classes:
            items = []
            for li in el.find_all("li", recursive=False):
                arrows = li.select(".rel-arrow")
                # only the LEADING arrow becomes the item's glyph; any further
                # arrows mid-sentence survive as <<x>> markers inside the text
                glyph = ""
                if arrows:
                    glyph = inline_md(arrows[0])
                    arrows[0].extract()
                items.append({"glyph": glyph, "md": inline_md(li)})
            blocks.append({"type": "relations", "items": items})
        elif name == "p" and "verify-note" in classes:
            blocks.append({"type": "verify", "md": inline_md(el)})
        elif name == "p" and "sc-proto-note" in classes:
            continue  # folded into the scorecards block
        elif name == "p":
            blocks.append({"type": "note", "md": inline_md(el)})
        elif "lens-bar" in classes:
            blocks.append(parse_scorecards(section))
        elif "lens-sub" in classes or "sc-table-wrap" in classes:
            continue  # consumed by parse_scorecards
        elif name == "script":
            continue
        else:
            raise SystemExit(f"unhandled element in #{section.get('id')}: <{name} class={classes}>")
    return blocks


def parse_section(section: Tag) -> dict:
    out: dict = {"id": section["id"]}
    head = section.select_one(".section-head")
    st_head = section.select_one(".station-head")
    if head:
        out["num"] = inline_md(head.select_one(".section-num"))
        out["title"] = inline_md(head.find("h2"))
        out["kind"] = "section"
    elif st_head:
        mark = st_head.select_one(".station-mark")
        out["kind"] = "station"
        out["mark"] = inline_md(mark)
        out["accent"] = css_var(mark.get("style"), "background") or ""
        out["title"] = inline_md(st_head.find("h2"))
        out["role"] = inline_md(st_head.select_one(".role"))
    out["blocks"] = parse_blocks(section)
    return out


# ---------------------------------------------------------------- main


def main() -> None:
    src = Path(sys.argv[1])
    dest = Path(sys.argv[2])
    soup = BeautifulSoup(src.read_text(encoding="utf-8"), "html.parser")

    hero = soup.select_one(".hero")
    doc = {
        "title": soup.find("title").get_text(strip=True),
        "eyebrow": inline_md(hero.select_one(".hero-eyebrow")),
        "heading": inline_md(hero.find("h1")),
        "summary": inline_md(hero.select_one(".hero-sub")),
        "stats": [
            {"value": inline_md(s.select_one(".n")), "label": inline_md(s.select_one(".l"))}
            for s in hero.select(".hero-stat")
        ],
        "toc": [
            {
                "id": a["href"].lstrip("#"),
                "label": inline_md(a),
                "accent": css_var(a.select_one(".stdot").get("style"), "background") or "",
                "group_start": "toc-group" in (a.parent.get("class") or []),
            }
            for a in soup.select(".toc a")
        ],
        "sections": [parse_section(s) for s in soup.select("main.content > section")],
    }
    footer = soup.find("footer")
    spans = footer.find_all("span")
    doc["footer"] = {"note": inline_md(spans[0]), "date": inline_md(spans[1])}

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "# Source of truth for the PyForge Dossier.\n"
        "# Edit this file; `python docsite/build.py` re-renders the site and the artifact.\n"
        "# Originally imported from the published artifact by docsite/tools/import_artifact.py.\n\n"
        + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    n_blocks = sum(len(s["blocks"]) for s in doc["sections"])
    print(f"wrote {dest} — {len(doc['sections'])} sections, {n_blocks} blocks")


if __name__ == "__main__":
    main()
