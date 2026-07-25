# The extraction contract — formats, constructs, and identity

Companion to `SPEC.md`. The kernel's Constraints declare non-rendering extraction and the
ecosystem-identity predicate as normative; this file holds the per-format and
per-construct matrices they compress. Without a supported-construct matrix, "coverage" is
undefined per format — which is why this is a contract, not documentation.

---

## The two coverage paths

Warden does not re-implement PyPI dependency parsing. It **extends two mature engines to
the conda/pixi ecosystem they do not cover**, behind one gate.

**PyPI path — delegate to the engines' native parsers, then unify.**

| Engine | Reads natively |
|---|---|
| deptry | `pyproject.toml` — PEP 621, Poetry, PDM, uv, setuptools — and `requirements.txt` / `.in` / `*-dev.txt` |
| osv-scanner | `requirements.txt`, `poetry.lock`, `pdm.lock`, `uv.lock`, `Pipfile.lock`, `pylock.toml` |

**Conda/pixi path — the bridge.** Neither engine parses `environment.yml`, `meta.yaml`
(v0), `recipe.yaml` (v1), `pixi.toml`, `pixi.lock`, or `conda-lock.yml`. Warden extracts
the dependency set and bridges it: a synthesized requirements projection for deptry, and
version-pinned requirements for osv (from lock data where present, else **name-only and
marked**).

**Resolution depth is stated, never implied.** The coverage block distinguishes
`direct-only` from `locked-closure`: a loose manifest lists direct dependencies only, so
transitive vulnerabilities are invisible without a lockfile. A lockfile input is
preferred; a loose manifest **downgrades the coverage claim** rather than inflating it.

## The non-rendering two-pass parse

Rendering untrusted Jinja is forbidden, which rules out every authoritative renderer on
the runtime path — they *evaluate*. So extraction is a bounded, non-rendering scrape:

- **Pass 1 — capture context without executing.** v0: regex-capture `{% set K = V %}`.
  v1: `safe_load` the `context:` block.
- **Pass 2 — neutralize, then `safe_load`.** v1 `recipe.yaml` is valid YAML and
  `safe_load`s directly. v0 `meta.yaml` is not: capture `# [selector]` marks, strip
  `{% … %}` statement lines, substitute simple `{{ VAR|filter }}` through **our own
  safe-filter allowlist** — never a Jinja engine — then `safe_load`.

Walked sections: `requirements.{build,host,run}`, `test(s).requirements`, and
`outputs[].requirements`. `run_constrained` / `run_constraints` entries are
**constraints, not dependencies** — excluded from vuln matching and SBOM counts, or
flagged `provenance: constraint`.

### v0 ↔ v1 differences the parser encodes

| | v0 `meta.yaml` | v1 `recipe.yaml` |
|---|---|---|
| Interpolation | `{{ }}` | `${{ }}` |
| Context | `{% set %}` | `context:` block |
| Selectors | `# [sel]`, `py < N` | `if/then/else`, `match(python, …)` |
| Constraint section | `run_constrained` | `run_constraints` |
| Parse | needs neutralizing | `safe_load`s directly |

### Supported-construct matrix

| Construct | Handling |
|---|---|
| `numpy >=1.20` | ✅ name + spec |
| `{{ name }}` / `${{ version }}` where VAR ∈ context | ✅ resolve to literal |
| `${{ compiler("c") }}` / `stdlib("c")` | ⚠️ variant-expanded **build tool** → mark and **exclude** from the scanned set |
| `${{ pin_subpackage('foo') }}` | ⚠️ **intra-recipe output** → mark `internal-subpackage`, exclude from external deps |
| `# [linux]` / `if: linux then/else` | ⚠️ **union both branches**, tag each with its condition |
| `{{ version.replace(...) }}` expression logic | ⚠️ version field → `version = None` (`range-only`); name field → best-effort |
| `{% for %}`-generated deps | ❌ degrade the block to name-only + marked |
| bare `{{ }}` in a v1 file | ⚠️ literal text → raw string + malformed-recipe flag |

Degrading **never raises**. An unparseable manifest degrades to name-only + marked and is
surfaced per manifest.

### The regression gate

- **Corpus conformance** over ~1,950 real `recipes/*/{recipe.yaml,meta.yaml}`, globbed at
  runtime: **0 uncaught exceptions**, plus a committed `unparseable_rate` baseline that CI
  holds **monotonically non-increasing** — a change that degrades more manifests is caught.
- **Differential oracle**: for each real recipe, the extracted dependency set must be a
  **superset** of the authoritative renderer's output, modulo name-only-marked. Ground
  truth without ever executing untrusted input at runtime.
- **Twice-run byte-identity** under `--deterministic`, and **zero repository writes**.

## Ecosystem identity — the predicate that prevents the silent false-green

osv keys advisories by `(ecosystem, name, version)` over PyPI, npm, Go, … — it has **no
conda ecosystem**, so a conda dependency is parsed as PyPI. A pinned but differently-named
conda package (`pytorch` → `torch`, a native `openssl`) fed to osv matches the *wrong*
PyPI identity and returns a **silent false-green**.

```
vuln_matchable = (pypi_identity is not None) AND (version resolved to ==X.Y.Z)
```

`pypi_identity` resolves **only** from trustworthy provenance:

1. `pixi.lock` `pypi:` entries
2. explicit PyPI sections — `[pypi-dependencies]`, an `environment.yml` `- pip:` block
3. the **bundled static conda→pypi map** (the CLI is offline and cannot call a live mapper; the map is regenerable from the atlas purl exports, or directly from the published prefix-dev mapping for non-atlas orgs)

Unmapped → `None`. Conda `=1.2` is a **prefix** (`1.2.*`), not an exact match → withheld
as `range-only`.

### Withhold reasons

`no-version` · `unmapped-ecosystem` · `native-nonpypi` · `range-only` ·
`ambiguous-identity`

A withheld component is **always visible, never silently dropped** — that visibility is
what routes it to `indeterminate` rather than letting a clean sibling axis absorb it.

## Inventory identity and merge

Identity is `(ecosystem, name, concrete_version)`. The purl is **derived**, and its
non-identity qualifiers are stripped before any comparison.

| Case | Merge rule |
|---|---|
| same identity across manifests/sections | **one** component with a **provenance list** — a dep in `host:` *and* `run:` is one component, not two |
| `(name, None)` alongside `(name, version)` | merges **only when exactly one** concrete version exists; zero → stays one `indeterminate`; two or more → the bare entry stays a distinct `indeterminate` |
| different version, same `(ecosystem, name)` | **distinct components, both scanned** — honest count inflation, stated |

**Never guess-attribute a version.** Cross-ecosystem names are never silently merged or
deduped; per-ecosystem attribution is preserved and uncertainty is marked. A component's
purl reflects the **source registry of the manifest it came from** — `pkg:pypi/…` vs
`pkg:conda/…?channel=` — and an unresolved registry-of-truth is marked, not guessed.

The invariant that ties it together:
`len(SBOM.components) == len(inventory) == report.inventory_count`, evaluated
**post-merge**, with the root project excluded (it is the SBOM's metadata component, not a
dependency).
