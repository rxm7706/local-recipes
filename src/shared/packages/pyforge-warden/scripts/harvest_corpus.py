"""Harvests + pins the fleet-scale validation corpus (Story 5.2).

Two independent sub-harvests, both writing into this package's committed
``tests/fixtures/corpus/``:

1. **Recipes** -- every ``recipe.yaml``/``meta.yaml`` under this repo's
   root ``recipes/`` tree (~1,979 files, ~8.6MB), copied VERBATIM into
   ``tests/fixtures/corpus/recipes/`` mirroring ``recipes/``'s own relative
   layout (manifests only -- no ``build.sh``/patches/``conda-forge.yml``).
   A deliberately PINNED, committed snapshot, never a live glob: this
   repo's ``recipes/`` tree churns daily (an active packaging factory), so
   a live glob would make the corpus-scale regression gates flaky for
   reasons unrelated to ``pyforge-warden``'s own code (see the story
   spec's Design Notes).
2. **Adversarial set** -- a SMALL curated subset of real-world
   ``recipe.yaml`` files pulled from ``prefix-dev/rattler-build-parser-
   tests`` at a PINNED commit SHA (never a full mirror of that upstream
   repo -- it tracks thousands of feedstocks), plus a handful of
   hand-authored files exercising extraction-degradation edge cases
   (unicode identifiers, an oversized dependency list, nested
   ``{% for %}``/selector-comment constructs) that are hard to find
   verbatim in the wild but must never crash the extractor.

Dev-only maintenance script -- not part of the installed ``pyforge.warden``
package (mirrors ``scripts/refresh_kev_feed.py``'s/``scripts/
generate_conda_pypi_map.py``'s dev-only-script convention), and NEVER
imported by ``scan``/anything in the installed package. Uses stdlib
``urllib.request`` only -- no new dependency. The upstream fetch is a SOFT
dependency (Boundaries): a network failure prints a warning and leaves
whatever hand-authored/previously-fetched files are already committed
rather than aborting the whole harvest -- this story's adversarial set was
authored with network access, but a later re-run in an offline environment
must not be blocked from refreshing the recipe half.

Usage::

    python scripts/harvest_corpus.py [--repo-root PATH] [--skip-upstream-fetch]
"""

from __future__ import annotations

import argparse
import http.client
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_PACKAGE_ROOT = _SCRIPTS_DIR.parent

_CORPUS_DIR = _PACKAGE_ROOT / "tests" / "fixtures" / "corpus"
_RECIPES_OUT = _CORPUS_DIR / "recipes"
_ADVERSARIAL_OUT = _CORPUS_DIR / "adversarial"
_UPSTREAM_OUT = _ADVERSARIAL_OUT / "upstream"
_HANDAUTHORED_OUT = _ADVERSARIAL_OUT / "handauthored"

_MANIFEST_NAMES = ("recipe.yaml", "meta.yaml")

# Pinned upstream provenance (Boundaries: a curated subset, never a full
# mirror -- prefix-dev/rattler-build-parser-tests tracks ~3,000 feedstocks'
# recipe.yaml files as rattler-build's own rendering-test fixtures). Picked
# for diversity of real-world v1 recipe.yaml shapes (a multi-source/
# multi-patch numpy, a templated pillow, small single-output packages)
# without pulling in a C/C++ toolchain-heavy recipe that would dominate the
# corpus's size for no extra extraction coverage.
_UPSTREAM_COMMIT_SHA = "11c97667d70a4242ca6ef6481a2133156dea4152"
_UPSTREAM_RECIPE_NAMES = (
    "pillow",
    "numpy",
    "nanoarrow",
    "boost-histogram",
    "grpcio-health-checking",
)
_UPSTREAM_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/prefix-dev/rattler-build-parser-tests/"
    "{sha}/rendering-tests/{name}/recipe/recipe.yaml"
)
_USER_AGENT = "pyforge-warden-harvest-corpus/1.0"

# --- hand-authored adversarial fixtures -------------------------------------
#
# Each entry degrades gracefully (RAW_MALFORMED/NAME_ONLY/UNION_MARKED) or
# parses outright -- NEVER raises UnparsableManifestError/an uncaught
# exception (I/O matrix). Live-verified against RecipeV1Extractor/
# MetaV0Extractor while authoring this script (see the story's Dev Notes).

_UNICODE_NAME_RECIPE_YAML = """\
context:
  version: "1.0.0"

package:
  name: unicode-café-demo
  version: ${{ version }}

requirements:
  host:
    - python
  run:
    - café-tools >=1.0
    - 日本語パッケージ
    - packagé-nâme==2.0
    - emoji-📦-pkg
    - café-tools≥1.0
    - ${{ pin_compatible("café-tools", upper_bound="x.x") }}
    - unresolved-${{ some_unicode_fn("日本語") }}-suffix
"""


def _oversized_deps_recipe_yaml(count: int = 1500) -> str:
    """A ~1,500-dependency ``run:`` list (well under the 5MB/8KB-per-line
    NFR-S5 caps -- "oversized" relative to a typical recipe's ~10-30 deps,
    not relative to the size cap that would instead raise
    ``UnparsableManifestError``) -- stresses extraction at list-scale
    without hitting that unrelated failure mode."""
    deps = "\n".join(
        f"    - oversized-dep-{i:04d} >={i % 9 + 1}.0" for i in range(count)
    )
    return (
        'context:\n  version: "1.0.0"\n\n'
        "package:\n  name: oversized-deps-demo\n  version: ${{ version }}\n\n"
        f"requirements:\n  host:\n    - python\n  run:\n{deps}\n"
    )


_EXOTIC_JINJA_LOOP_META_YAML = """\
{% set compilers = ["gcc", "clang"] %}
{% set extras = ["alpha", "beta", "gamma"] %}
package:
  name: exotic-nested-loop-demo
  version: "2.0"

requirements:
  build:
    {% for c in compilers %}
    - {{ c }}_{{ target_platform }}          # [not win]
    {% endfor %}
  host:
    - python
  run:
    {% if is_unix %}
    {% for extra in extras %}
    - extra-{{ extra }}-pkg  # [unix]
    {% endfor %}
    {% endif %}
    - requests >=2.0  # [not win]
    - pywin32          # [win]
"""

_HANDAUTHORED_FIXTURES: dict[str, tuple[str, str]] = {
    # subdir -> (manifest filename, content)
    "unicode_name": ("recipe.yaml", _UNICODE_NAME_RECIPE_YAML),
    "oversized_deps": ("recipe.yaml", _oversized_deps_recipe_yaml()),
    "exotic_jinja_loop": ("meta.yaml", _EXOTIC_JINJA_LOOP_META_YAML),
}


def _find_repo_root(start: Path) -> Path:
    """Walks upward from ``start`` for the directory carrying BOTH
    ``recipes/`` and ``pixi.toml`` -- the repo-root markers -- rather than
    a hardcoded parent-count, so this script tolerates the package moving
    within the tree."""
    for candidate in (start, *start.parents):
        if (candidate / "pixi.toml").is_file() and (candidate / "recipes").is_dir():
            return candidate
    raise RuntimeError(
        f"could not find a repo root (pixi.toml + recipes/) above {start}"
    )


def harvest_recipes(repo_root: Path) -> list[Path]:
    """Copies every ``recipe.yaml``/``meta.yaml`` under ``repo_root/
    recipes/`` into ``_RECIPES_OUT``, mirroring the source's relative
    layout. The output directory is wiped first (re-runnable "refresh the
    pin" convention) so a feedstock removed upstream also disappears from
    the pinned corpus rather than accumulating stale entries.

    The source is enumerated BEFORE the wipe, and an empty enumeration
    aborts (follow-up review finding: a bad ``--repo-root`` -- or an
    empty ``recipes/`` -- previously rmtree'd the 1,979-file committed
    corpus, copied zero files, and exited 0 printing "copied 0")."""
    source_root = repo_root / "recipes"
    source_manifests = [
        source_path
        for manifest_name in _MANIFEST_NAMES
        for source_path in sorted(source_root.rglob(manifest_name))
    ]
    if not source_manifests:
        raise SystemExit(
            f"harvest_corpus: no recipe.yaml/meta.yaml found under "
            f"{source_root} -- refusing to wipe the committed corpus "
            "against an empty source"
        )
    if _RECIPES_OUT.exists():
        shutil.rmtree(_RECIPES_OUT)
    _RECIPES_OUT.mkdir(parents=True)
    copied: list[Path] = []
    for source_path in source_manifests:
        relative = source_path.relative_to(source_root)
        dest_path = _RECIPES_OUT / relative
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, dest_path)
        copied.append(relative)
    return copied


def prune_upstream_orphans() -> None:
    """Removes any ON-DISK upstream subdirectory whose name is no longer
    in ``_UPSTREAM_RECIPE_NAMES`` (review finding: without this, a name
    removed from that tuple left its old directory orphaned on disk
    forever, silently reported as still current by ``write_sources_md``'s
    live directory listing). A directory whose name is STILL in the tuple
    is never touched -- preserving ``fetch_upstream_adversarial_set``'s
    documented partial-network-failure guarantee.

    Runs UNCONDITIONALLY from ``main()`` (follow-up review finding: when
    this prune lived inside ``fetch_upstream_adversarial_set``,
    ``--skip-upstream-fetch`` skipped the prune too -- exactly the
    orphan-staleness the original fix targeted)."""
    if not _UPSTREAM_OUT.is_dir():
        return
    for existing in _UPSTREAM_OUT.iterdir():
        if existing.is_dir() and existing.name not in _UPSTREAM_RECIPE_NAMES:
            shutil.rmtree(existing)


def fetch_upstream_adversarial_set() -> list[str]:
    """Fetches the pinned curated subset from ``prefix-dev/rattler-build-
    parser-tests`` -- a SOFT dependency (see module docstring): a network
    failure on any single name is a printed warning, not an abort, and
    whatever names already succeeded/were previously committed are left in
    place (orphan pruning is ``prune_upstream_orphans``'s job, run
    unconditionally from ``main()``). Returns the list of names actually
    written this run."""
    _UPSTREAM_OUT.mkdir(parents=True, exist_ok=True)
    fetched: list[str] = []
    for name in _UPSTREAM_RECIPE_NAMES:
        url = _UPSTREAM_URL_TEMPLATE.format(sha=_UPSTREAM_COMMIT_SHA, name=name)
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                content = response.read().decode("utf-8")
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            # Follow-up review finding: a truncated 200 body raises
            # http.client.IncompleteRead (an HTTPException, NOT an
            # OSError), and a non-UTF-8 body raises UnicodeDecodeError --
            # both previously aborted the whole harvest with a traceback,
            # violating the documented warn-and-continue soft-dependency
            # contract above.
            http.client.HTTPException,
            UnicodeDecodeError,
        ) as exc:
            print(
                f"harvest_corpus: WARNING: could not fetch {name!r} from "
                f"prefix-dev/rattler-build-parser-tests@{_UPSTREAM_COMMIT_SHA}: "
                f"{exc} -- leaving any existing copy untouched",
                file=sys.stderr,
            )
            continue
        dest_dir = _UPSTREAM_OUT / name
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "recipe.yaml").write_text(content, encoding="utf-8")
        fetched.append(name)
    return fetched


def write_handauthored_adversarial_set() -> list[str]:
    """Always written (no network involved) -- the fallback the module
    docstring/Boundaries describe when the upstream fetch is unavailable.

    Prunes any ON-DISK subdirectory no longer in ``_HANDAUTHORED_FIXTURES``
    (review finding, same class as ``fetch_upstream_adversarial_set``'s own
    fix -- a fixture removed from that dict would otherwise leave its old
    directory orphaned forever). No partial-failure concern here (unlike
    the network half): every entry is always (re)written this same call,
    so pruning first is unconditionally safe."""
    _HANDAUTHORED_OUT.mkdir(parents=True, exist_ok=True)
    for existing in _HANDAUTHORED_OUT.iterdir():
        if existing.is_dir() and existing.name not in _HANDAUTHORED_FIXTURES:
            shutil.rmtree(existing)
    written: list[str] = []
    for subdir, (filename, content) in _HANDAUTHORED_FIXTURES.items():
        dest_dir = _HANDAUTHORED_OUT / subdir
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / filename).write_text(content, encoding="utf-8")
        written.append(subdir)
    return written


def write_sources_md(
    *, fetched_upstream: list[str], handauthored: list[str], upstream_skipped: bool
) -> None:
    """(Re)writes the provenance record -- reflects exactly what THIS run
    left on disk, so a partial/offline run's ``SOURCES.md`` never overclaims
    upstream coverage it didn't actually fetch.

    ``upstream_skipped`` distinguishes "no upstream files present because
    ``--skip-upstream-fetch`` was passed" from "no upstream files present
    because the fetch was attempted and failed" -- review finding: the
    empty-state message previously always said "last fetch attempt failed"
    even on a fresh checkout run with ``--skip-upstream-fetch``, where no
    fetch was attempted at all."""
    upstream_present = sorted(
        p.name for p in _UPSTREAM_OUT.iterdir() if p.is_dir()
    ) if _UPSTREAM_OUT.is_dir() else []
    if upstream_present:
        upstream_lines = [f"- {name}" for name in upstream_present]
    elif upstream_skipped:
        upstream_lines = ["- (none -- --skip-upstream-fetch was passed, no fetch attempted)"]
    else:
        upstream_lines = ["- (none -- last fetch attempt failed; see stderr from the harvest run)"]
    lines = [
        "# Adversarial corpus provenance",
        "",
        "Generated by `scripts/harvest_corpus.py` -- re-run to refresh.",
        "",
        "## Upstream subset",
        "",
        (
            "Source: `prefix-dev/rattler-build-parser-tests` "
            f"(BSD-3-Clause, Copyright conda-forge), pinned commit "
            f"`{_UPSTREAM_COMMIT_SHA}`."
        ),
        "",
        "Present on disk:",
        *upstream_lines,
        "",
        "## Hand-authored",
        "",
        (
            "Extraction-degradation edge cases live upstream recipes rarely "
            "exercise in one file; each is live-verified to degrade "
            "gracefully (RAW_MALFORMED/NAME_ONLY/UNION_MARKED) or parse "
            "outright -- never raise:"
        ),
        "",
        "- `unicode_name/recipe.yaml` -- non-ASCII/emoji component names and "
        "identifiers, plus two unresolved `${{ ... }}` function-call forms.",
        "- `oversized_deps/recipe.yaml` -- a ~1,500-entry `run:` "
        "dependency list (well under the 5MB/8KB-per-line NFR-S5 caps).",
        "- `exotic_jinja_loop/meta.yaml` -- nested `{% if %}`/`{% for %}` "
        "tags combined with `# [cond]` selector comments.",
        "",
    ]
    (_ADVERSARIAL_OUT / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    del handauthored  # documented by the fixed bullet list above, not enumerated


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="override repo-root auto-detection (must contain recipes/ + pixi.toml)",
    )
    parser.add_argument(
        "--skip-upstream-fetch",
        action="store_true",
        help="skip the network fetch of the upstream adversarial subset "
        "(hand-authored fixtures are always (re)written)",
    )
    return parser


def main() -> None:
    args = _build_argparser().parse_args()
    if args.repo_root is not None:
        repo_root = args.repo_root
        # Follow-up review finding: only the auto-detect path enforced the
        # help text's "must contain recipes/ + pixi.toml" -- a typo'd
        # override sailed straight into harvest_recipes (whose own
        # empty-source guard is the second line of defense; this one
        # catches the mistake before any work happens, with the marker
        # predicate _find_repo_root already uses).
        if not ((repo_root / "pixi.toml").is_file() and (repo_root / "recipes").is_dir()):
            raise SystemExit(
                f"harvest_corpus: --repo-root {repo_root} does not look "
                "like the repo root (needs recipes/ + pixi.toml)"
            )
    else:
        repo_root = _find_repo_root(_PACKAGE_ROOT)

    copied = harvest_recipes(repo_root)
    print(f"harvest_corpus: copied {len(copied)} manifest(s) into {_RECIPES_OUT}")

    prune_upstream_orphans()

    fetched_upstream: list[str] = []
    if args.skip_upstream_fetch:
        print("harvest_corpus: --skip-upstream-fetch given, not fetching")
    else:
        fetched_upstream = fetch_upstream_adversarial_set()
        print(
            f"harvest_corpus: fetched {len(fetched_upstream)}/"
            f"{len(_UPSTREAM_RECIPE_NAMES)} upstream adversarial recipe(s)"
        )

    handauthored = write_handauthored_adversarial_set()
    print(f"harvest_corpus: wrote {len(handauthored)} hand-authored fixture(s)")

    write_sources_md(
        fetched_upstream=fetched_upstream,
        handauthored=handauthored,
        upstream_skipped=args.skip_upstream_fetch,
    )
    print(f"harvest_corpus: wrote {_ADVERSARIAL_OUT / 'SOURCES.md'}")


if __name__ == "__main__":
    main()
