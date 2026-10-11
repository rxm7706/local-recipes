"""Trim and loosen upstream pyproject.toml dependencies at build time.

Why this script exists:

- The patch files it replaces (formerly recipe/patches/*.patch) only removed
  or replaced dependency entries in upstream's pyproject.toml files. None of
  them made changes codebase's logic.
- Those patches were hardcoded diffs, keyed on the lines around each entry,
  so they had to be regenerated for almost every upstream release, even when
  the dependencies they touched were unchanged. That made every version bump
  a manual bottleneck.
- Editing the dependencies with a Python script instead follows
  db-gpt-feedstock, which does the same in its recipe
  (https://github.com/conda-forge/db-gpt-feedstock/blob/76343d181fe3f6e7517d90fdc7e9048b5c099ecc/recipe/recipe.yaml#L33),
  added in response to review feedback on its staged-recipes submission
  (https://github.com/conda-forge/staged-recipes/pull/33883#discussion_r3519794625).
- Removing or replacing a dependency involves no project-specific logic, so
  it can be done automatically, with no manual patch updates. Entries are
  matched by (normalized) package name, so upstream reordering, re-pinning or
  adding neighbouring entries doesn't matter. An entry that upstream has
  already dropped is reported and skipped rather than failing the build.
- The following implementation is written by Opus 5.5 - https://www.anthropic.com/claude-opus-5-5
  - and reviewed by pb01ka - https://github.com/pb01ka - for its correctness.
"""

import argparse
import fnmatch
import re
import sys
import tomllib
from pathlib import Path

EDITS = {
    "langflow-base": {
        "path": "src/backend/base/pyproject.toml",
        # Third-party integrations nobody uses all at once. They are
        # run_constraints of langflow-base in recipe.yaml instead of hard deps.
        "remove": [
            "gunicorn",
            "langchain-mongodb",
            "pymongo",
            "langchain-perplexity",
            "langchain-qdrant",
            "duckdb",
            "jq",
            "spider-client",
            "clickhouse-connect",
            "elevenlabs",
            "ibm-watsonx-ai",
            "langchain-ibm",
            "trustcall",
            "langchain-chroma",
            # Tracing integrations not packaged on conda-forge.
            "langfuse",
            "langwatch",
            # Packaged on conda-forge but not co-installable with langflow-base
            # there: every slowapi build constrains redis-py <4 (upstream needs
            # >=7.4), and every traceloop-sdk build pulls in
            # opentelemetry-instrumentation-chromadb, which needs chromadb <0.6
            # (upstream needs >=1.0). langflow only imports both lazily.
            "redis",
            "traceloop-sdk",
        ],
        # Every entry for the name (including marker-split variants) is
        # collapsed into this single requirement.
        "replace": {
            # Upstream's exact ==4.0.1 has no cp314 build on conda-forge.
            "bcrypt": "bcrypt>=4.0.1,<5",
            # noarch: python collapses upstream's per-interpreter marker split
            # and would otherwise silently drop cp314.
            "onnxruntime": "onnxruntime>=1.20",
        },
    },
    "langflow": {
        "path": "pyproject.toml",
        # The lfx-* extension bundles are optional; the ones built by this
        # feedstock are run_constraints of langflow in recipe.yaml.
        "remove": ["lfx-*"],
        "strip_extras": ["langflow-base"],
    },
    "lfx-ibm": {
        "path": "src/bundles/ibm/pyproject.toml",
        # ibm_db has no linux-aarch64 build; it is a run_constraint instead.
        "remove": ["ibm-db"],
    },
}

ARRAY_START_RE = re.compile(r"^dependencies\s*=\s*\[\s*(#.*)?$")
ARRAY_END_RE = re.compile(r"^\s*\]\s*(#.*)?$")
ENTRY_RE = re.compile(r"""^(?P<indent>\s*)(?P<q>["'])(?P<req>.*?)(?P=q)\s*,?\s*(#.*)?$""")
NAME_RE = re.compile(r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?P<extras>\[[^\]]*\])?")


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def req_name(req):
    match = NAME_RE.match(req)
    if match is None:
        sys.exit(f"patch_deps.py: cannot parse requirement {req!r}")
    return normalize(match["name"])


def find_dependencies_array(lines, path):
    """Return the (start, end) line indices of [project].dependencies' brackets."""
    section = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and not stripped.startswith("[["):
            section = stripped
            continue
        if section == "[project]" and ARRAY_START_RE.match(line):
            for j in range(i + 1, len(lines)):
                if ARRAY_END_RE.match(lines[j]):
                    return i, j
            break
    sys.exit(f"patch_deps.py: no multi-line [project].dependencies array in {path}")


def edit(path, remove=(), replace=None, strip_extras=()):
    replace = {normalize(k): v for k, v in (replace or {}).items()}
    strip_extras = {normalize(n) for n in strip_extras}

    with open(path, encoding="utf-8", newline="") as f:
        lines = f.read().splitlines(keepends=True)
    original = tomllib.loads("".join(lines))["project"]["dependencies"]
    start, end = find_dependencies_array(lines, path)

    new_lines = lines[: start + 1]
    seen = []
    unused_removals = set(remove)
    unused_replacements = set(replace)
    for line in lines[start + 1 : end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        match = ENTRY_RE.match(line.rstrip("\r\n"))
        if match is None:
            sys.exit(f"patch_deps.py: unexpected line in {path} dependencies: {line!r}")
        req = match["req"]
        seen.append(req)
        name = req_name(req)
        newline = line[len(line.rstrip("\r\n")) :]

        patterns = [p for p in remove if fnmatch.fnmatchcase(name, normalize(p))]
        if patterns:
            unused_removals.difference_update(patterns)
            print(f"  removed   {req}")
        elif name in replace:
            if name in unused_replacements:
                unused_replacements.discard(name)
                new_lines.append(f'{match["indent"]}"{replace[name]}",{newline}')
                print(f"  replaced  {req}  ->  {replace[name]}")
            else:
                print(f"  removed   {req}  (merged into {replace[name]})")
        elif name in strip_extras and NAME_RE.match(req)["extras"]:
            stripped_req = NAME_RE.sub(lambda m: m["name"], req, count=1)
            new_lines.append(f'{match["indent"]}"{stripped_req}",{newline}')
            print(f"  replaced  {req}  ->  {stripped_req}")
        else:
            new_lines.append(line)
    new_lines.extend(lines[end:])

    # Every requirement must have come from a line this parser understood,
    # otherwise some dependency could slip through unedited.
    if seen != original:
        sys.exit(f"patch_deps.py: failed to parse all dependencies of {path}")

    for pattern in sorted(unused_removals):
        print(f"  note: nothing matched {pattern!r} to remove (dropped upstream?)")
    for name in sorted(unused_replacements):
        print(f"  note: nothing matched {name!r} to replace (dropped upstream?)")

    text = "".join(new_lines)
    for req in tomllib.loads(text)["project"]["dependencies"]:
        name = req_name(req)
        if (
            any(fnmatch.fnmatchcase(name, normalize(p)) for p in remove)
            or (name in replace and req != replace[name])
            or (name in strip_extras and NAME_RE.match(req)["extras"])
        ):
            sys.exit(f"patch_deps.py: {req!r} survived editing {path}")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", choices=sorted(EDITS), help="recipe output being built")
    parser.add_argument("--src-dir", type=Path, default=Path.cwd(), help="source root (default: cwd)")
    args = parser.parse_args()

    spec = dict(EDITS[args.output])
    path = args.src_dir / spec.pop("path")
    print(f"patch_deps.py: editing {path}")
    edit(path, **spec)


if __name__ == "__main__":
    main()
