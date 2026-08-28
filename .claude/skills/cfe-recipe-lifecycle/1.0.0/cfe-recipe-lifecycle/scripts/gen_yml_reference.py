#!/usr/bin/env python3
"""gen_yml_reference.py — auto-generate exhaustive Markdown references for
conda-forge.yml and recipe.yaml from their upstream JSON Schemas.

Outputs to:
  .claude/skills/conda-forge-expert/reference/conda-forge-yml-reference-full.md
  .claude/skills/conda-forge-expert/reference/recipe-yaml-reference-full.md

The curated *-reference.md files (hand-written, opinionated subset with
"when to use" rationale + canonical shapes) remain authoritative for
judgment calls. These *-reference-full.md files mirror every schema key
for completeness — link to them from the curated docs.

Usage:
    python gen_yml_reference.py                         # fetch live, write both
    python gen_yml_reference.py --target conda-forge    # one target only
    python gen_yml_reference.py --target recipe         # one target only
    python gen_yml_reference.py --schema-file recipe=path.json   # air-gapped
    python gen_yml_reference.py --dry-run               # stdout, no write
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
REFERENCE_DIR = REPO_ROOT / ".claude" / "skills" / "conda-forge-expert" / "reference"

SCHEMAS = {
    "conda-forge": {
        "url": "https://raw.githubusercontent.com/conda-forge/conda-smithy/main/conda_smithy/data/conda-forge.json",
        "out_name": "conda-forge-yml-reference-full.md",
        "title": "conda-forge.yml — Full Schema Reference",
        "curated": "conda-forge-yml-reference.md",
        "intent": "Per-feedstock + per-recipe smithy config. Consumed by `conda smithy rerender` and `conda-smithy lint`.",
    },
    "recipe": {
        "url": "https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json",
        "out_name": "recipe-yaml-reference-full.md",
        "title": "recipe.yaml — Full Schema Reference (rattler-build / recipe-v1)",
        "curated": "recipe-yaml-reference.md",
        "intent": "Recipe v1 spec. Consumed by `rattler-build` and the conda-forge v1 recipe pipeline.",
    },
}


def fetch_schema(url: str, *, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "cfe-gen-yml-reference/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def load_schema(target: str, schema_file: Path | None) -> dict:
    if schema_file is not None:
        return json.loads(schema_file.read_text())
    return fetch_schema(SCHEMAS[target]["url"])


def resolve_ref(ref: str, root: dict) -> dict:
    if not ref.startswith("#/"):
        return {}
    node: Any = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if part not in node:
            return {}
        node = node[part]
    return node


def resolve_chain(body: dict, root: dict, *, depth: int = 0) -> dict:
    if depth > 6 or not isinstance(body, dict):
        return body if isinstance(body, dict) else {}
    if "$ref" in body:
        return resolve_chain(resolve_ref(body["$ref"], root), root, depth=depth + 1)
    return body


def repr_default(v: Any) -> str:
    try:
        return json.dumps(v)
    except (TypeError, ValueError):
        return str(v)


def slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-").replace(".", "")


def describe_type(schema: dict, root: dict, *, depth: int = 0) -> str:
    """One-line type description with $ref resolution and combinator support."""
    if depth > 5 or not isinstance(schema, dict):
        return "_(deep)_"
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        return f"`{name}`"
    if "enum" in schema:
        vals = schema["enum"]
        if len(vals) > 6:
            return "enum: " + ", ".join(f"`{repr_default(v)}`" for v in vals[:6]) + ", …"
        return "enum: " + ", ".join(f"`{repr_default(v)}`" for v in vals)
    if "const" in schema:
        return f"const `{repr_default(schema['const'])}`"
    if "anyOf" in schema:
        parts = [describe_type(v, root, depth=depth + 1) for v in schema["anyOf"]]
        return " \\| ".join(dict.fromkeys(parts))  # dedup, preserve order
    if "oneOf" in schema:
        parts = [describe_type(v, root, depth=depth + 1) for v in schema["oneOf"]]
        return " *or* ".join(dict.fromkeys(parts))
    if "allOf" in schema:
        parts = [describe_type(v, root, depth=depth + 1) for v in schema["allOf"]]
        return " & ".join(dict.fromkeys(parts))
    t = schema.get("type")
    if t == "array":
        return f"array of {describe_type(schema.get('items', {}), root, depth=depth + 1)}"
    if t == "object":
        if "properties" in schema:
            return "object (see nested keys)"
        ap = schema.get("additionalProperties")
        if isinstance(ap, dict):
            return f"mapping str → {describe_type(ap, root, depth=depth + 1)}"
        return "object"
    if isinstance(t, list):
        return " \\| ".join(f"`{x}`" for x in t)
    if t is None:
        if "properties" in schema:
            return "object (see nested keys)"
        return "_(unspecified)_"
    return f"`{t}`"


def collect_top_level_keys(schema: dict) -> list[tuple[str, dict]]:
    return sorted(schema.get("properties", {}).items())


def collect_defs(schema: dict) -> dict[str, dict]:
    return schema.get("$defs", schema.get("definitions", {}))


def collect_nested_properties(body: dict, root: dict, *, depth: int = 0) -> dict[str, dict]:
    if depth > 4 or not isinstance(body, dict):
        return {}
    if "$ref" in body:
        return collect_nested_properties(resolve_ref(body["$ref"], root), root, depth=depth + 1)
    if "properties" in body:
        return body["properties"]
    if "anyOf" in body:
        for variant in body["anyOf"]:
            nested = collect_nested_properties(variant, root, depth=depth + 1)
            if nested:
                return nested
    return {}


def clean_desc(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.split()).replace("|", "\\|")


def format_nested_row(name: str, body: dict, root: dict) -> str:
    resolved = resolve_chain(body, root)
    type_str = describe_type(body, root)
    default = "—"
    if "default" in resolved:
        default = f"`{repr_default(resolved['default'])}`"
    desc = clean_desc(resolved.get("description") or body.get("description"))
    if not desc:
        desc = "—"
    if len(desc) > 220:
        desc = desc[:217] + "..."
    deprecated = "⚠️ " if resolved.get("deprecated") or body.get("deprecated") else ""
    return f"| `{name}` | {type_str} | {default} | {deprecated}{desc} |"


def render_key_section(name: str, body: dict, root: dict) -> list[str]:
    resolved = resolve_chain(body, root)
    lines: list[str] = []
    lines.append(f"### `{name}`")
    lines.append("")
    if resolved.get("deprecated") or body.get("deprecated"):
        lines.append("> **⚠️ Deprecated.**")
        lines.append("")
    type_str = describe_type(body, root)
    lines.append(f"- **Type**: {type_str}")
    if "default" in resolved:
        lines.append(f"- **Default**: `{repr_default(resolved['default'])}`")
    desc = clean_desc(resolved.get("description") or body.get("description"))
    if desc:
        lines.append(f"- **Description**: {desc}")
    nested = collect_nested_properties(body, root)
    if nested:
        lines.append("")
        lines.append("**Nested keys:**")
        lines.append("")
        lines.append("| Key | Type | Default | Description |")
        lines.append("|---|---|---|---|")
        for sub_name, sub_body in sorted(nested.items()):
            lines.append(format_nested_row(sub_name, sub_body, root))
    lines.append("")
    return lines


def render_doc(target: str, schema: dict) -> str:
    meta = SCHEMAS[target]
    lines: list[str] = []
    lines.append(f"# {meta['title']}")
    lines.append("")
    lines.append("> **Auto-generated** by `.claude/skills/conda-forge-expert/scripts/gen_yml_reference.py`")
    lines.append("> from the upstream JSON Schema. Do not edit by hand — re-run")
    lines.append("> `pixi run -e local-recipes gen-yml-reference` after the upstream schema changes.")
    lines.append(">")
    lines.append(f"> **Schema source**: <{meta['url']}>")
    lines.append(">")
    lines.append(f"> **Curated companion** (opinionated subset + rationale + canonical shapes):")
    lines.append(f"> [`{meta['curated']}`]({meta['curated']})")
    lines.append("")
    lines.append("## Intent")
    lines.append("")
    lines.append(meta["intent"])
    lines.append("")

    top = collect_top_level_keys(schema)
    lines.append(f"## Top-level keys ({len(top)})")
    lines.append("")
    if top:
        lines.append("| Key | Type | Default |")
        lines.append("|---|---|---|")
        for name, body in top:
            resolved = resolve_chain(body, schema)
            type_str = describe_type(body, schema)
            default = "—"
            if "default" in resolved:
                default = f"`{repr_default(resolved['default'])}`"
            lines.append(f"| [`{name}`](#{slugify(name)}) | {type_str} | {default} |")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Detail per top-level key")
    lines.append("")
    for name, body in top:
        lines.extend(render_key_section(name, body, schema))
        lines.append("---")
        lines.append("")

    defs = collect_defs(schema)
    if defs:
        lines.append(f"## Schema definitions / `$defs` ({len(defs)})")
        lines.append("")
        lines.append("Named definitions referenced by `$ref` from keys above.")
        lines.append("")
        for def_name, def_body in sorted(defs.items()):
            lines.append(f"### `{def_name}`")
            lines.append("")
            type_str = describe_type(def_body, schema)
            lines.append(f"- **Type**: {type_str}")
            desc = clean_desc(def_body.get("description"))
            if desc:
                lines.append(f"- **Description**: {desc}")
            if "enum" in def_body:
                vals = def_body["enum"]
                lines.append("- **Allowed values**: " + ", ".join(f"`{repr_default(v)}`" for v in vals))
            nested = collect_nested_properties(def_body, schema)
            if nested:
                lines.append("")
                lines.append("**Nested keys:**")
                lines.append("")
                lines.append("| Key | Type | Default | Description |")
                lines.append("|---|---|---|---|")
                for sub_name, sub_body in sorted(nested.items()):
                    lines.append(format_nested_row(sub_name, sub_body, schema))
            lines.append("")
    return "\n".join(lines) + "\n"


def parse_schema_file_args(raw: list[str]) -> dict[str, Path]:
    out = {}
    for item in raw:
        if "=" not in item:
            raise SystemExit(f"--schema-file expects target=path, got: {item}")
        target, path = item.split("=", 1)
        if target not in SCHEMAS:
            raise SystemExit(f"unknown target {target!r}; valid: {sorted(SCHEMAS)}")
        out[target] = Path(path)
    return out


def main():
    p = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    p.add_argument("--target", choices=sorted(SCHEMAS) + ["all"], default="all",
                   help="Which schema to generate (default: all)")
    p.add_argument("--schema-file", action="append", default=[], metavar="TARGET=PATH",
                   help="Use a local schema file instead of fetching (air-gapped). Repeatable.")
    p.add_argument("--out-dir", type=Path, default=REFERENCE_DIR,
                   help=f"Output dir (default: {REFERENCE_DIR})")
    p.add_argument("--dry-run", action="store_true",
                   help="Print to stdout instead of writing files")
    args = p.parse_args()

    schema_files = parse_schema_file_args(args.schema_file)
    targets = sorted(SCHEMAS) if args.target == "all" else [args.target]

    for target in targets:
        src = schema_files.get(target)
        print(f"[{target}] loading schema ({'file: ' + str(src) if src else 'live fetch'})...", file=sys.stderr)
        try:
            schema = load_schema(target, src)
        except Exception as e:
            print(f"[{target}] failed to load schema: {e}", file=sys.stderr)
            sys.exit(2)
        print(f"[{target}] rendering...", file=sys.stderr)
        doc = render_doc(target, schema)
        if args.dry_run:
            print(doc)
            continue
        out_path = args.out_dir / SCHEMAS[target]["out_name"]
        out_path.write_text(doc)
        print(f"[{target}] wrote {out_path} ({len(doc.splitlines())} lines)", file=sys.stderr)


if __name__ == "__main__":
    main()
