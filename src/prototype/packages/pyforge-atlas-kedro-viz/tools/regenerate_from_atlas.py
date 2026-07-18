#!/usr/bin/env python3
"""Regenerate the kedro-viz prototype's stub DAG from the REAL pyforge-atlas.

The prototype (``src/prototype/packages/pyforge-atlas-kedro-viz``) is a
dependency-free, MemoryDataset-only Kedro project whose sole purpose is to
visualize (``kedro viz``) / smoke-run (``kedro run``) the *shape* of the real
pyforge-atlas DAG without installing its heavy stack.

This keeps it faithful. It statically parses (AST — **no imports**, so no
pandas / duckdb / dagster needed) each real
``pyforge-atlas/.../pipelines/<name>/pipeline.py`` ``create_pipeline()`` for its
node graph (func name, inputs, outputs, node name), then emits matching stub
pipelines + a MemoryDataset catalog whose ``kedro-viz.layer`` metadata is copied
from the real catalog (falling back to a name heuristic).

Re-run after any pyforge-atlas pipeline change:
    pixi run -e local-recipes regenerate-kedro-viz-proto
"""
from __future__ import annotations

import ast
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[5]
ATLAS_PIPES = REPO / "src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines"
ATLAS_CATALOG = REPO / "src/shared/packages/pyforge-atlas/conf/base/catalog.yml"
PROTO_PIPES = REPO / "src/prototype/packages/pyforge-atlas-kedro-viz/src/pyforge/atlas_kedro_viz/pipelines"
PROTO_CONF = REPO / "src/prototype/packages/pyforge-atlas-kedro-viz/conf/base"


# ---- AST parsing of the real pipelines -------------------------------------

def _lit(node):
    """AST node -> python value for the str / [str,...] / dict / None cases."""
    if node is None or isinstance(node, ast.Constant):
        return None if node is None else node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_lit(e) for e in node.elts]
    if isinstance(node, ast.Dict):  # kedro dict inputs {arg: dataset}
        return [_lit(v) for v in node.values]
    return "<dynamic>"  # a variable/expression we can't resolve statically


def _as_list(x):
    if x is None:
        return []
    return [i for i in x if i is not None] if isinstance(x, list) else [x]


def parse_pipeline(pyfile: Path) -> list[dict]:
    """Extract [{name, inputs:[...], outputs:[...]}] from every node(...) call."""
    tree = ast.parse(pyfile.read_text(encoding="utf-8"))
    out = []
    for call in ast.walk(tree):
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == "node"):
            continue
        kw = {k.arg: k.value for k in call.keywords}

        def pick(key, pos):
            if key in kw:
                return kw[key]
            return call.args[pos] if len(call.args) > pos else None

        name_node = pick("name", 3)
        if not isinstance(name_node, ast.Constant) or not isinstance(name_node.value, str):
            continue  # only real, named nodes
        out.append({
            "name": name_node.value,
            "inputs": _as_list(_lit(pick("inputs", 1))),
            "outputs": _as_list(_lit(pick("outputs", 2))),
        })
    return out


# ---- layer assignment ------------------------------------------------------

def load_real_layers() -> dict[str, str]:
    doc = yaml.safe_load(ATLAS_CATALOG.read_text(encoding="utf-8")) or {}
    layers = {}
    for ds, spec in doc.items():
        if isinstance(spec, dict):
            layer = (spec.get("metadata", {}) or {}).get("kedro-viz", {}).get("layer")
            if layer:
                layers[ds] = layer
    return layers


def layer_for(ds: str, real_layers: dict[str, str]) -> str:
    if ds in real_layers:
        return real_layers[ds]
    if ds.endswith("_raw"):
        return "raw"
    if ds.endswith(("_report", "_bom", "_sbom", "_export")):
        return "derived"
    return "atlas"


def is_param(ds: str) -> bool:
    return ds == "parameters" or ds.startswith("params:")


# ---- graphviz DAG image ----------------------------------------------------

_LAYER_FILL = {
    "raw": "#ffe0b2", "atlas": "#bbdefb", "views": "#c8e6c9",
    "derived": "#f8bbd0", "read_surface": "#d1c4e9",
}
_CLUSTER_FILL = ["#e3f2fd", "#f1f8e9", "#fff3e0", "#fce4ec", "#ede7f6",
                 "#e0f7fa", "#f9fbe7", "#efebe9", "#eceff1"]


def _build_graph(pipe_names, parsed, assigned, real_layers):
    """Build a graphviz Digraph mirroring the given pipeline subset."""
    import graphviz  # dot binary + python-graphviz (both in the local-recipes env)

    keep = list(pipe_names)
    datasets = {
        d for name in keep for nd in parsed[name]
        for d in nd["inputs"] + nd["outputs"]
        if d and not is_param(d) and d != "<dynamic>"
    }
    g = graphviz.Digraph("pyforge_atlas_dag")
    g.attr(rankdir="LR", bgcolor="white", fontname="Helvetica",
           nodesep="0.22", ranksep="0.7", splines="spline")
    g.attr("node", fontname="Helvetica", fontsize="9")
    g.attr("edge", color="#90a4ae", arrowsize="0.6")

    for d in sorted(datasets):
        g.node("ds__" + d, d, shape="ellipse", style="filled", fontsize="8",
               color="#b0bec5", fillcolor=_LAYER_FILL.get(layer_for(d, real_layers), "#eceff1"))

    for i, name in enumerate(sorted(keep)):
        with g.subgraph(name="cluster_" + name) as c:
            c.attr(label=name, style="filled,rounded", color="#78909c",
                   fillcolor=_CLUSTER_FILL[i % len(_CLUSTER_FILL)],
                   fontname="Helvetica-Bold", fontsize="13")
            for d in sorted(dd for dd, p in assigned.items() if p == name and dd in datasets):
                c.node("fn__extract_" + d, "extract_" + d, shape="box",
                       style="filled,rounded", fillcolor="white", color="#546e7a")
            for nd in parsed[name]:
                c.node("fn__" + nd["name"], nd["name"], shape="box",
                       style="filled,rounded", fillcolor="white", color="#546e7a")

    for name in keep:
        for d in sorted(dd for dd, p in assigned.items() if p == name and dd in datasets):
            g.edge("fn__extract_" + d, "ds__" + d)
        for nd in parsed[name]:
            for inp in nd["inputs"]:
                if inp in datasets:
                    g.edge("ds__" + inp, "fn__" + nd["name"])
            for out in nd["outputs"]:
                if out in datasets:
                    g.edge("fn__" + nd["name"], "ds__" + out)

    return g


def emit_graphviz(parsed, assigned, real_layers, docs_dir) -> int:
    """Emit a full-DAG SVG + one per pipeline, plus an editable .drawio of the
    full DAG. Each format skips gracefully (not fatal) if its lib is absent."""
    try:
        import graphviz  # noqa: F401
    except Exception as exc:  # pragma: no cover
        print(f"graphviz unavailable ({exc}); skipped DAG images")
        return 0
    docs_dir.mkdir(parents=True, exist_ok=True)
    for f in [*docs_dir.glob("dag*.svg"), *docs_dir.glob("dag*.drawio")]:
        f.unlink()

    n = 0
    full = _build_graph(sorted(parsed), parsed, assigned, real_layers)
    (docs_dir / "dag.svg").write_bytes(full.pipe(format="svg"))
    n += 1
    for name in sorted(parsed):
        g = _build_graph([name], parsed, assigned, real_layers)
        (docs_dir / f"dag-{name}.svg").write_bytes(g.pipe(format="svg"))
        n += 1

    # editable drawio (diagrams.net) of the full DAG — via graphviz2drawio
    try:
        from graphviz2drawio import graphviz2drawio
        (docs_dir / "dag.drawio").write_text(
            graphviz2drawio.convert(full.source), encoding="utf-8")
        n += 1
    except Exception as exc:  # pragma: no cover
        print(f"graphviz2drawio unavailable ({exc}); skipped dag.drawio")
    return n


# ---- emit ------------------------------------------------------------------

def _fmt(vals: list[str]):
    """Format a node inputs/outputs list back to a str | [list] | None literal."""
    if not vals:
        return "None"
    if len(vals) == 1:
        return repr(vals[0])
    inner = ", ".join(repr(v) for v in vals)
    return f"[{inner}]"


PIPE_HEADER = '''"""``{name}`` pipeline — GENERATED stub mirror of pyforge-atlas.

Auto-generated by tools/regenerate_from_atlas.py from
src/shared/packages/pyforge-atlas/.../pipelines/{name}/. Do not edit by hand;
re-run `pixi run -e local-recipes regenerate-kedro-viz-proto`.
"""
from kedro.pipeline import Pipeline, node, pipeline

from pyforge.atlas_kedro_viz.nodes import stub


def create_pipeline() -> Pipeline:
    return pipeline(
        [
'''
PIPE_FOOTER = "        ]\n    )\n"


def main() -> int:
    real_layers = load_real_layers()
    pipe_files = sorted(ATLAS_PIPES.glob("*/pipeline.py"), key=lambda p: p.parent.name)
    parsed = {p.parent.name: parse_pipeline(p) for p in pipe_files}

    # global produced set + free-input detection
    produced: set[str] = set()
    for nodes in parsed.values():
        for n in nodes:
            produced.update(n["outputs"])

    all_datasets: set[str] = set()
    param_paths: set[str] = set()
    free_inputs: set[str] = set()
    for nodes in parsed.values():
        for n in nodes:
            for ds in n["inputs"] + n["outputs"]:
                if is_param(ds):
                    if ds.startswith("params:"):
                        param_paths.add(ds[len("params:"):])
                    continue
                if ds == "<dynamic>":
                    continue
                all_datasets.add(ds)
            for ds in n["inputs"]:
                if not is_param(ds) and ds != "<dynamic>" and ds not in produced:
                    free_inputs.add(ds)

    # assign each free input to the first pipeline (sorted) that consumes it
    assigned: dict[str, str] = {}
    for name in sorted(parsed):
        for n in parsed[name]:
            for ds in n["inputs"]:
                if ds in free_inputs and ds not in assigned:
                    assigned[ds] = name

    # ---- write pipelines ----
    for f in PROTO_PIPES.glob("*.py"):
        if f.name != "__init__.py":
            f.unlink()
    for name in sorted(parsed):
        lines = []
        # extraction stubs for free inputs first-consumed here (inputs=None)
        for ds in sorted(d for d, p in assigned.items() if p == name):
            lines.append(
                f'            node(stub("extract_{ds}"), None, {ds!r}, '
                f'name="extract_{ds}"),'
            )
        for n in parsed[name]:
            n_out = len(n["outputs"])
            stub_call = f'stub("{n["name"]}"' + (f", n_outputs={n_out}" if n_out > 1 else "") + ")"
            inp = [d for d in n["inputs"] if d != "<dynamic>"]
            lines.append(
                f'            node({stub_call}, {_fmt(inp)}, {_fmt(n["outputs"])}, '
                f'name="{n["name"]}"),'
            )
        (PROTO_PIPES / f"{name}.py").write_text(
            PIPE_HEADER.format(name=name) + "\n".join(lines) + "\n" + PIPE_FOOTER,
            encoding="utf-8",
        )

    # ---- catalog.yml (every dataset = MemoryDataset + viz layer) ----
    cat_lines = [
        "# GENERATED by tools/regenerate_from_atlas.py — do not edit by hand.",
        "# Every dataset is a MemoryDataset (stub run, no IO); the kedro-viz",
        "# `layer` mirrors the real pyforge-atlas storage tiers.",
        "",
    ]
    for ds in sorted(all_datasets):
        cat_lines += [
            f"{ds}:",
            "  type: MemoryDataset",
            "  metadata:",
            "    kedro-viz:",
            f"      layer: {layer_for(ds, real_layers)}",
            "",
        ]
    (PROTO_CONF / "catalog.yml").write_text("\n".join(cat_lines), encoding="utf-8")

    # ---- parameters.yml (nested from params: paths, stub values) ----
    params: dict = {}
    for path in sorted(param_paths):
        cur = params
        parts = path.split(".")
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = None  # stub value; viz only needs the key to exist
    header = "# GENERATED by tools/regenerate_from_atlas.py — stub params for the viz DAG.\n"
    (PROTO_CONF / "parameters.yml").write_text(
        header + (yaml.safe_dump(params, sort_keys=True) if params else "{}\n"),
        encoding="utf-8",
    )

    # ---- pipeline_registry.py (explicit registration — GENERATED) ----
    # find_pipelines() does not discover single-file pipeline modules in this
    # kedro version, so emit an explicit registry (kept in sync by re-running).
    names = sorted(parsed)
    reg_imports = ",\n    ".join(names)
    reg_body = "\n".join(f'        "{n}": {n}.create_pipeline(),' for n in names)
    (PROTO_PIPES.parent / "pipeline_registry.py").write_text(
        '"""Register the prototype pipelines (GENERATED — do not edit by hand).\n\n'
        "Emitted by tools/regenerate_from_atlas.py to mirror the real pyforge-atlas\n"
        'pipeline set. Re-run `pixi run -e local-recipes regenerate-kedro-viz-proto`.\n"""\n\n'
        "from kedro.pipeline import Pipeline\n\n"
        f"from pyforge.atlas_kedro_viz.pipelines import (\n    {reg_imports},\n)\n\n\n"
        "def register_pipelines() -> dict[str, Pipeline]:\n"
        "    pipelines = {\n"
        f"{reg_body}\n"
        "    }\n"
        '    pipelines["__default__"] = sum(pipelines.values(), Pipeline([]))\n'
        "    return pipelines\n",
        encoding="utf-8",
    )

    # ---- DAG images (graphviz SVG: full DAG + one per pipeline) ----
    n_svg = emit_graphviz(parsed, assigned, real_layers, PROTO_CONF.parents[1] / "docs")

    n_nodes = sum(len(v) for v in parsed.values()) + len(assigned)
    print(f"pipelines: {sorted(parsed)}")
    print(f"nodes: {n_nodes} ({len(assigned)} extraction + "
          f"{sum(len(v) for v in parsed.values())} real-mirrored)")
    print(f"datasets: {len(all_datasets)} | params: {len(param_paths)} | "
          f"dag images: {n_svg} (svg + drawio)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
