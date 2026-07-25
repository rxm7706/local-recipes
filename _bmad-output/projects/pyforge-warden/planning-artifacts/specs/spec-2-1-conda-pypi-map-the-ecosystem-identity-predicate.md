<!-- RECOVERED 2026-07-25 from Claude Code session transcript a6257624-efb4-49a7-8568-ad317e8a9ec5.jsonl (~/.claude/projects); this is the ORIGINAL spec incl. its dev/review narrative, not an epics.md regeneration. -->
---
title: 'Conda→PyPI Identity Map + the Ecosystem-Identity Predicate'
type: 'feature'
created: '2026-07-16'
status: 'draft'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** A conda/pixi-sourced dependency's PyPI identity is unknown at runtime — `mapping.py`'s bundled map is still Story 1.2's `{}` stub — so `extract/lockfiles.py`'s conda-row resolver (Story 2.6) can't distinguish a trustworthy match from a coincidental one, `osv-scanner`'s candidate filter never sees a resolved conda identity at all, and hygiene's DEP001 stays flat-warn. Net effect: the silent `pytorch`→`torch` false-green Gap C exists to close.

**Approach:** Generate the real `data/conda_pypi_map.json` from the already-shipped `conda-forge-expert` atlas `export-purls` TSV (via the CFE skill — CFE Rule 1), gate identity resolution on a `verified`-confidence trust threshold, widen `osv-scanner`'s candidate filter to include resolved conda identities, and upgrade hygiene's DEP001 default from flat-warn to block-on-trusted-mapping.

## Boundaries & Constraints

**Always:**
- Generate `data/conda_pypi_map.json` by invoking the `conda-forge-expert` skill to run the already-shipped `export-purls` CLI (CFE Rule 1 — never shell out to atlas scripts directly); a new pyforge-warden-owned converter script turns its `purls_conda-pypi_mapped.tsv` artifact into the packaged JSON.
- Map entries only for rows with a real `pypi_purl` (`match_source != "none"`); each entry keeps `pypi_name` + `match_source` + `match_confidence` (never flattened to name→name), keyed by the raw conda package name.
- `_conda_component` trusts a map hit (sets `pypi_identity`, makes `vuln_matchable` computable) ONLY when `match_confidence == "verified"`; `"likely"` or absent stays `pypi_identity=None` + `indeterminate_reason=WithholdReason.UNMAPPED_ECOSYSTEM`, but still records the raw `mapping_confidence` for observability.
- Widen `OsvScannerEngine.run()`'s two candidate filters (`engines.py:422-433`) from `ecosystem is PYPI` to `pypi_identity is not None` so a resolved conda identity is actually scanned.
- `DEFAULT_HYGIENE_POLICY["DEP001"]` upgrades to `Status.POLICY_VIOLATION`; `hygiene_rung` downgrades a DEP001 finding to `Status.WARN` only when the scan's inventory contains at least one component with a known-but-untrusted (`"likely"`) mapping confidence — computed once per scan in `DefaultPolicy.evaluate()`, never per finding (deptry's `module` field is an import name, not reliably correlatable to one component without Story 2.2's synthesized front-door).
- Add `test_hygiene.py`'s missing structural guard: `Status.CLEAN not in DEFAULT_HYGIENE_POLICY.values()`.

**Block If:** none — Gap C is architecturally resolved; the confidence threshold and DEP001-gate mechanism are this story's own concrete design calls (see Design Notes).

**Never:**
- Rebuild or mutate `cf_atlas.db` — copy the main checkout's already-current DB into this worktree's `.claude/data/conda-forge-expert/` rather than running `build-cf-atlas`.
- Implement the "parselmouth-direct refresh mode" (`export-purls --pixi-map`) — not built in CFE yet.
- Populate `WithholdReason.NATIVE_NONPYPI` — the map's "no match" signal can't distinguish "native, will never map" from "not yet mapped"; every map-driven miss stays `UNMAPPED_ECOSYSTEM`.
- Build `recipe.yaml`/`meta.yaml`/`environment.yml`/`pixi.toml` extractors or new manifest fixtures (Stories 2.2/2.3) — `extract/lockfiles.py` is the only current conda-component producer.
- Add new `WithholdReason` enum members or new PEP-503 normalization code — the vocabulary is pre-frozen and `inventory.canonical_name` (1.1/2.6) already normalizes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Verified map hit | conda `numpy==1.26.4`, map entry `match_confidence=verified` | `pypi_identity=numpy==1.26.4`, `vuln_matchable=True`, included in osv scan | No error |
| Low-confidence hit | conda `foo==1.0`, map entry `match_confidence=likely` | `pypi_identity=None`, `indeterminate_reason=UNMAPPED_ECOSYSTEM`, `mapping_confidence=likely` | No error |
| No map entry | conda `libopenblas==0.3` | `pypi_identity=None`, `indeterminate_reason=UNMAPPED_ECOSYSTEM`, `mapping_confidence=None` | No error |
| DEP001, no ambiguous conda dep in scan | inventory has zero `likely`-confidence components | DEP001 finding → `Status.POLICY_VIOLATION` | No error |
| DEP001, an ambiguous conda dep present | inventory has ≥1 `likely`-confidence component | DEP001 finding → `Status.WARN` | No error |
| Resolved conda identity feeds osv | conda component `vuln_matchable=True` | included in `OsvScannerEngine.run()`'s candidates (was excluded pre-2.1) | No error |

</intent-contract>

## Code Map

- `src/pyforge/warden/scripts/generate_conda_pypi_map.py` -- NEW -- converts CFE's `purls_conda-pypi_mapped.tsv` into the packaged JSON map
- `src/pyforge/warden/data/conda_pypi_map.json` -- MODIFY -- real generated map, replacing the `{}` stub
- `src/pyforge/warden/extract/lockfiles.py` -- MODIFY -- `_conda_component` gates on `match_confidence == "verified"`
- `src/pyforge/warden/engines.py` -- MODIFY -- `OsvScannerEngine.run()` candidate filters widen to `pypi_identity is not None`
- `src/pyforge/warden/hygiene.py` -- MODIFY -- `DEFAULT_HYGIENE_POLICY["DEP001"]` → `POLICY_VIOLATION`; `hygiene_rung` gains a `dep001_trusted` param
- `src/pyforge/warden/interfaces.py` -- MODIFY -- `DefaultPolicy.evaluate()` computes `dep001_trusted` once from `inventory.components`, passes to `hygiene_rung`
- `tests/unit/test_lockfiles_extractor.py` -- MODIFY -- update the now-stale unmapped-ecosystem assertion + add verified/low-confidence map-hit cases
- `tests/unit/test_hygiene.py` -- MODIFY -- update DEP001 pinning tests for the new default + ambiguity downgrade; add the `Status.CLEAN not in DEFAULT_HYGIENE_POLICY.values()` guard
- `tests/unit/test_osv_engine_exit_codes.py` -- MODIFY -- add a conda-ecosystem `vuln_matchable=True` case proving it's now scanned
- `tests/unit/test_mapping.py` -- NEW -- map-loading + converter-script unit tests

## Tasks & Acceptance

**Execution:**
- [ ] `src/pyforge/warden/scripts/generate_conda_pypi_map.py` -- write the TSV→JSON converter (parse `conda_purl`/`pypi_purl`, filter `match_source != none`, sort keys) -- AC1
- [ ] Invoke the `conda-forge-expert` skill to provision atlas data (copy `cf_atlas.db` from the main checkout) and run `export-purls`, then run the converter to populate `data/conda_pypi_map.json` -- AC1
- [ ] `src/pyforge/warden/extract/lockfiles.py` -- gate `_conda_component` on `match_confidence == "verified"` -- AC2, AC3
- [ ] `src/pyforge/warden/engines.py` -- widen `OsvScannerEngine.run()`'s candidate filters to `pypi_identity is not None` -- AC2
- [ ] `src/pyforge/warden/hygiene.py` + `interfaces.py` -- upgrade `DEFAULT_HYGIENE_POLICY["DEP001"]`, wire the scan-wide `dep001_trusted` gate -- AC3
- [ ] `tests/unit/test_lockfiles_extractor.py`, `test_hygiene.py`, `test_mapping.py` (new), `test_osv_engine_exit_codes.py` -- cover every I/O matrix row above

**Acceptance Criteria:**
- Given the atlas `export-purls` TSV, when the converter runs, then `data/conda_pypi_map.json` preserves `pypi_name`/`match_source`/`match_confidence` per conda package, never flattened to name→name (AC1).
- Given a conda component with a `verified` map hit and an exact locked version, when resolved, then `pypi_identity` is set and `vuln_matchable=True` (AC2).
- Given a conda component with a `likely` or absent map hit, when resolved, then `pypi_identity=None` and the component is withheld as `UNMAPPED_ECOSYSTEM`, never silently clean (AC2, AC3).
- Given a scan whose inventory contains a `likely`-confidence component, when hygiene composes DEP001 findings, then they land `warn`, not `policy-violation`; given no such ambiguity, DEP001 findings land `policy-violation` (AC3).
- Given a conda component with `vuln_matchable=True`, when `osv-scanner` runs, then it is included in the scanned candidate set (closes the `pytorch`→`torch` false-green end-to-end).

## Design Notes

- **Confidence trust threshold:** only `match_confidence=="verified"` (`parselmouth`/`recipe_source_url` sources) is trusted; `"likely"` (`name_coincidence`) is treated as unmapped for both vuln-matching and DEP001 — safer to under-claim than risk a wrong-package CVE match.
- **DEP001 gate is scan-wide, not per-finding:** deptry's `module` field is an import name, not a distribution name, and can't be reliably correlated to one `Component` without Story 2.2's synthesized front-door (not yet built). `dep001_trusted` is one boolean per scan, false only when the inventory shows positive evidence of an ambiguous (not absent, not verified) mapping somewhere — the concrete "story-owned" reading of Gap-A's threshold decision.
- **PEP-503 normalization already exists** (`inventory.canonical_name`, used by `_resolve_conda_pypi_identity` since 2.6) — no new normalization code needed; the once-open deferred-work concern about differently-spelled-but-equivalent packages closes once the real map ships through this existing path.
- **`match_confidence` values are `verified`/`likely`/`n/a`** in the real atlas data (not the `parselmouth`/`name_coincidence`/`none` `match_source` vocabulary epics.md's AC text names) — the two are correlated 1:1 for the shipped sources; the JSON map's `match_confidence` field is the one production code actually reads.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: all tests pass, including the new map/hygiene/osv cases
- `python -c "import json,pathlib; d=json.loads(pathlib.Path('src/shared/packages/pyforge-warden/src/pyforge/warden/data/conda_pypi_map.json').read_text()); assert d and all({'pypi_name','match_source','match_confidence'} <= e.keys() for e in d.values())"` -- expected: real, non-empty, correctly-shaped map

**Manual checks (if no CLI):**
- `git diff --stat` -- confirm only the files in Code Map changed
