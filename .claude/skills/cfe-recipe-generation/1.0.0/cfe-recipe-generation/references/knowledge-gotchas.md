# Knowledge — Slice 1 Gotchas + Bundled Reference Docs

## Contents

- [G54 — source preference is sdist > GitHub-source > wheel](#g54)
- [G91 — PEP 517 backend + plugin host deps the generator misses](#g91)
- [G94 (third sub-item) — case-variant generator output dirs](#g94-third-sub-item)
- [G98 — repo-wide cfe-metadata batch-edit discipline](#g98)
- [Bundled reference docs](#bundled-reference-docs)

Source of all four: `.claude/skills/conda-forge-expert/SKILL.md`
[SRC:.claude/skills/conda-forge-expert/SKILL.md] — brief-scoped (`scope.include`), not
AST/source-extracted; T1-low confidence, `extraction_method: scope-included-doc` in the
provenance map (see `provenance-map.json`).

## G54

**`### G54. Source preference is sdist > GitHub-source > wheel — but the source must actually
SHIP the module; verify before switching (existence ≠ usable)`** [SRC:.claude/skills/conda-forge-expert/SKILL.md:L3006]

`recipe-generator.py` falls back to a wheel when it can't find a PyPI sdist, but it does **not**
check the project's GitHub for a source tag archive, and does **not** verify the chosen source
actually contains code. Two real failure modes: (1) a metadata-only sdist that ships zero `.py`
files (the wheel is correct in that case — document why); (2) a package that publishes only a
wheel to PyPI but keeps real source on GitHub (the GitHub tag archive is preferred). Decision
order: confirm the sdist ships `.py` files (`tar -tzf - | grep -c '\.py$'` > 0) before accepting
it; otherwise check GitHub.

## G91

**`### G91. PEP 517 backend + plugin host deps the generator misses — uv_build backends and
hatchling metadata hooks fail at METADATA-PREP; read [build-system].requires from the sdist`**
[SRC:.claude/skills/conda-forge-expert/SKILL.md:L3721]

`determine_build_backend()` [SRC:scripts/recipe-generator.py:L191] emits a guessed backend
(usually `setuptools`) instead of propagating the sdist's `[build-system].requires`. Two shapes
this misses: the `uv_build` backend (conda name `uv-build`), and hatch plugin deps — metadata
hooks (`hatch-requirements-txt`) or version hooks (`hatch-vcs`) declared in `requires` but
invisible to a backend-name-only check. `PackageInfo.build_system_requires`
[SRC:scripts/recipe-generator.py:L104] carries the conda-mapped requirement list when sdist
inspection succeeds — mirror it into `host:` verbatim.

## G94 (third sub-item)

**`### G94. Local mirror dirs accumulate STALE feedstock files that fail local gates — prune
against the LIVE feedstock on every refresh`**, sub-item 3 of 3 [SRC:.claude/skills/conda-forge-expert/SKILL.md:L3755]

> "Case-variant generator output dirs: grayskull writes to the PyPI canonical casing
> (`recipes/pyobjc-framework-CoreText/`) while the mirror stem is the lowercase feedstock name
> (`recipes/pyobjc-framework-coretext/`) — the fresh recipe lands in a stray new dir and the real
> mirror stays stale."

The generator's own code marks the exact line this applies to with a shorthand comment (no
separate "G94c" ID exists in SKILL.md itself — this is `recipe-generator.py`'s own inline
cross-reference into G94's third sub-item):

```python
output_dir = args.output or Path(f"recipes/{info.name.lower()}")  # G94c: lowercase feedstock-style dir
```
[SRC:scripts/recipe-generator.py:L2490] — `main()`'s pypi branch, immediately after
`fetch_pypi_info()`. Post-generate directory checks must include case variants alongside
hyphen/underscore swaps before merging a freshly-generated recipe into a mirror tree.

## G98

**`### G98. Repo-wide cfe-metadata batch edits: line-based rewrites with a parse-gate after
EVERY write, \g<1> in re.sub, provenance-check failures against git — and purl-spec
normalization keeps DOTS`** [SRC:.claude/skills/conda-forge-expert/SKILL.md:L3790]

Relevant to this slice's `_render_cfe_block()` [SRC:scripts/recipe-generator.py:L941]: the
PyPI-purl name emitted into the CFE metadata block is normalized as lowercase +
underscore-to-dash **with dots kept** (`info.name.lower().replace("_", "-")`
[SRC:scripts/recipe-generator.py:L953]) — over-normalizing away dots produces a purl that does
not match the PyPI package's actual purl-spec identity. The broader G98 discipline (line-based
edits only, parse-gate every write, `\g<1>` not `\1` in `re.sub` replacements) governs any
scripted batch edit across many `recipe.yaml` files — out of this single-recipe generator's
direct scope, but the purl-normalization rule it states is directly load-bearing here.

## CFE-block emission contract

`_render_cfe_block(info, conda_name, noarch_kind)` [SRC:scripts/recipe-generator.py:L941-989] —
emitted on every v1 generation path (never on the legacy v0 `meta.yaml` path). Local-recipes-only;
stripped before any push upstream (skill gotcha G62, outside this slice). Fields include
`cfe-conda-name`, `cfe-upstream-registry`, `cfe-purls` (both `pkg:conda/...` and `pkg:pypi/...`,
PyPI name normalized per the G98 dots-kept rule above), `cfe-source-kind`
(`github-tag:no-sdist-on-pypi-G54` / `pypi-wheel` / `pypi-sdist` — the G54 case is tagged
explicitly in the emitted comment), `cfe-noarch`, `cfe-local-build-status: not-attempted` (true
from birth), and generation timestamp/version fields.

## Bundled reference docs

Also in `scope.include` (brief-scoped, not code-extracted; each tracked as a `file_type: doc`
provenance entry):

- `.claude/skills/conda-forge-expert/reference/recipe-yaml-reference.md` [SRC:.claude/skills/conda-forge-expert/reference/recipe-yaml-reference.md] — v1 `recipe.yaml` schema reference, consulted by `generate_recipe_yaml()`/`generate_npm_recipe_yaml()`'s output shape.
- `.claude/skills/conda-forge-expert/reference/meta-yaml-reference.md` [SRC:.claude/skills/conda-forge-expert/reference/meta-yaml-reference.md] — legacy v0 `meta.yaml` schema reference, consulted by `generate_meta_yaml()`.
- `.claude/skills/conda-forge-expert/reference/jinja-functions.md` [SRC:.claude/skills/conda-forge-expert/reference/jinja-functions.md] — Jinja helper functions available inside emitted recipe templates.
- `.claude/skills/conda-forge-expert/guides/getting-started.md` [SRC:.claude/skills/conda-forge-expert/guides/getting-started.md] — onboarding guide for the wider conda-forge-expert skill; included here for the recipe-generation-relevant sections.

These four files are not reproduced verbatim in this skill package (consistent with how
`skf-create-skill`'s Discovered Authoritative Files Protocol tracks promoted docs by content hash
rather than copying them — see `provenance-map.json`'s `file_entries[]`); consult them at their
source path for full detail.
