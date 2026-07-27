<!-- RECOVERED 2026-07-25 from Claude Code session transcript fb0d0487-80ac-47c7-9584-793ce42525fa.jsonl (~/.claude/projects); this is the ORIGINAL spec incl. its dev/review narrative, not an epics.md regeneration. -->
---
title: 'CycloneDX 1.6 SBOM emission'
type: 'feature'
created: '2026-07-18'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** pyforge-warden resolves a full dependency inventory but has no machine-readable, standards-conformant artifact for downstream supply-chain tooling — CI/`cf_atlas` can only consume the pass/fail exit code and JSON report, never an SBOM.

**Approach:** add a new `sbom.py` read-only projection module that renders the already-resolved, frozen `ResolvedInventory` into a schema-valid CycloneDX 1.6 BOM via `cyclonedx-python-lib`, emitted to `--sbom-output <file>` as an independent sibling artifact alongside the existing report — never mutating or re-deriving inventory state.

## Boundaries & Constraints

**Always:**
- `sbom.py` is a pure function `render_cyclonedx(inventory: ResolvedInventory, report: ComplianceReport) -> str`; it never mutates either argument and never calls `merge_components` itself.
- `len(bom.components) == inventory.count` — the scanned root is `metadata.component` (type `application`), never a `components[]` entry.
- Purls are source-registry-correct and G98-normalized: build every purl via `packageurl.PackageURL(type=..., name=..., version=..., qualifiers=...)` — never hand-roll normalization. Verified live: `PackageURL(type="pypi", name="Django_Foo.Bar", version="1.0")` renders `pkg:pypi/django-foo.bar@1.0` (lowercase + `_`→`-`, dots preserved) — exactly G98, no custom code needed. Conda components pass `qualifiers={"channel": "conda-forge"}` (this repo's sole channel; `Component` carries no channel field).
- Every input-derived string reaches the BOM only through cyclonedx-python-lib's own model objects (`Component(name=..., version=...)`, `Property(name=..., value=...)`) — never f-string/`+`-concatenated into JSON text (NFR-S7). Validate the rendered document with `cyclonedx.validation.json.JsonStrictValidator(SchemaVersion.V1_6).validate_str(...)` BEFORE returning it (mirrors `report.py::render_json`'s validate-before-emit discipline) — a validation failure is fail-loud, never a partial/invalid file write.
- Self-declared partiality: set a `cfe:partial_inventory` BOM-metadata property to `"true"` when any `report.coverage[i].manifests_parsed < manifests_found` (else `"false"`) — derived from the already-assembled `report`, no new coverage computation.
- `cfe:*` conda-identity properties (AC3, readiness/X7): a conda component with `pypi_identity is not None` gets `cfe:pypi_purl` (a G98 pypi purl built from `pypi_identity.name`/`.version`). A conda component whose `identity_source == IdentitySource.MAP` *specifically* (the confidence-tier vocabulary is map-only) also gets `cfe:match_confidence` (verbatim `component.mapping_confidence`) and `cfe:match_source` (fresh lookup: `mapping.load_conda_pypi_map().get(component.name, {}).get("match_source")` — `Component` itself carries no `match_source` field; confirmed absent from `inventory.py`/`extract/_identity.py`).
- SBOM schema-version is decoupled from `ComplianceReport.schema_version` (NFR-I2): a new `SBOM_SCHEMA_VERSION = "0.1.0"` constant lives in `sbom.py` (mirrors `report.py::REPORT_SCHEMA_VERSION` — never grow `models.py`), emitted as BOM-metadata properties `cfe:schema_version` + `cfe:schema_status="experimental"`.
- `--sbom-output` write failures (`OSError`) print a stderr diagnostic and NEVER alter `report.exit_code` — mirror `cli.py`'s existing `(OSError, ValueError)` stdout-emission-failure handling, applied to this new file-write path.
- The one NTIA "dependency relationship" element this flat inventory can honestly support: a single root→every-component `dependencies[]` edge. No transitive graph data exists, so no other edges are fabricated.

**Block If:** none — the flag, model, and every convention it must follow (G98, `cfe:*` namespace, round-trip target) are already pinned by prior planning/readiness decisions; nothing here requires a human call.

**Never:**
- Fabricate supplier/author/manufacturer data — the resolved inventory carries none; omit those NTIA fields rather than guessing.
- Emit component `licenses[]` — `Component` carries no license field (that belongs to the unshipped Axis-3/story-6.2 work); do not backfill one from `conda_pypi_map.json` or elsewhere.
- Build or wire the shared `determinism.py` / `--deterministic` pinning for the SBOM's `serial_number`/`metadata.timestamp` — that infrastructure doesn't exist for the report either yet (`cli.py`'s own `--deterministic` help text calls it "currently a documented no-op"); explicitly out of this story's scope per the epic's own Technical Decisions ("shared with the report renderer, not owned solely here"). Both fields stay volatile in v1.
- Reuse `inventory.py::derive_purl()` / `Component.purl` verbatim as an SBOM purl for pypi components — it applies full PEP 503 (collapses dots), the wrong rule for purls (G98), and would corrupt names like `fs.googledrivefs`/`pymilvus.model`. Always rebuild fresh via `PackageURL`.
- Add a second report-schema conformance test — NFR-I1's report assertion already exists (Story 1.1); this story only asserts the SBOM's own CycloneDX validity.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path, mixed ecosystems | `--sbom-output out.json`; inventory has pypi + conda components, full coverage | Schema-valid CycloneDX 1.6 JSON at `out.json`; `len(components) == inventory_count`; `cfe:partial_inventory="false"` | No error |
| Partial coverage | Some `AxisCoverage.manifests_parsed < manifests_found` | `cfe:partial_inventory="true"` on `metadata.properties` | No error |
| Conda component, map-resolved identity | `identity_source == MAP`, `mapping_confidence="verified"` | `cfe:pypi_purl`, `cfe:match_confidence="verified"`, `cfe:match_source` all present | No error |
| Conda component, lock-resolved identity | `identity_source == LOCK` | `cfe:pypi_purl` present (identity IS resolved); `cfe:match_source`/`cfe:match_confidence` OMITTED (not a probabilistic map match) | No error |
| Unmapped conda component | `pypi_identity is None` | Conda purl only (`?channel=conda-forge`), no `cfe:*` properties | No error |
| Adversarial component name | Control chars / `</script>` / purl-reserved chars / a 10 KB name (NFR-S7 corpus) | Emitted via cyclonedx-python-lib model objects only; result is schema-valid JSON, string safely escaped, never raw-concatenated; purl construction percent-encodes or the offending record is excluded from purl derivation — never smuggles raw bytes into BOM syntax | Corpus-driven property test, no crash |
| Round-trip | The freshly emitted BOM fed to `scan-project --sbom-in <bom>` (CFE) | Every component ingests (non-empty `name` + a `pkg:pypi/`/`pkg:conda/`-prefixed `purl`) | No error |
| Empty inventory | Zero resolved components | `bom.components == []`; `metadata.component` still present; still schema-valid | No error |
| `--sbom-output` write fails | Target path unwritable (e.g. `ENOSPC`) | stderr diagnostic; `report.exit_code` UNCHANGED from the already-computed verdict | Caught `OSError`, non-fatal |

</intent-contract>

## Code Map

- `src/pyforge/warden/sbom.py` (NEW) -- the SBOM projection module: `render_cyclonedx`, purl builders, `cfe:*` property attachment, `SBOM_SCHEMA_VERSION`.
- `src/pyforge/warden/cli.py` -- add `--sbom-output PATH` argparse flag (`_build_parser`, alongside `--format`/`--fail-under-coverage`, ~lines 277-333) and the write hook right after `report = assemble_report(...)` (~line 833), in its own `try/except OSError`, never touching `report.exit_code`.
- `src/pyforge/warden/inventory.py` -- read-only reference (`Component`, `ResolvedInventory`, `IdentitySource`, `PypiIdentity`); no changes.
- `src/pyforge/warden/mapping.py` -- read-only reference (`load_conda_pypi_map()`) for the `cfe:match_source` lookup; no changes.
- `src/pyforge/warden/report.py` -- read-only reference (`AxisCoverage`, `ComplianceReport.coverage/tool_name/tool_version`) for the partiality flag and BOM tool metadata; no changes.
- `tests/unit/test_sbom.py` (NEW) -- purl construction (G98 conformance), `cfe:*` attachment per `identity_source`, partiality flag, empty-inventory edge case; builds `Component`/`ResolvedInventory` via the shared `component_factory` fixture (`conftest.py`).
- `tests/unit/test_cli_sbom.py` (NEW, mirrors `test_cli_bypass.py`) -- `--sbom-output` write-success and write-failure (`OSError`) CLI rows.
- `tests/conformance/test_sbom_schema.py` (NEW, mirrors `test_report_schema.py`'s pattern) -- minimal in-memory `ResolvedInventory`/`ComplianceReport` objects (not full end-to-end scans) validated against CycloneDX 1.6 via `JsonStrictValidator`; additive-growth and empty-inventory cases.
- `tests/fixtures/adversarial_names.json` (NEW) -- the NFR-S7 corpus (control chars, `</script>`, purl-reserved chars, ANSI escapes, a 10 KB name) -- authored from scratch; nothing to reuse anywhere in the repo.

## Tasks & Acceptance

**Execution:**
- [ ] `src/pyforge/warden/sbom.py` -- create `render_cyclonedx(inventory, report) -> str` -- builds a `cyclonedx.model.bom.Bom` (one `Component` per inventory component with G98 purls + `cfe:*` properties per the rules above, one root `dependencies[]` edge, `metadata.component`/`metadata.tools` from `report.tool_name`/`tool_version`), validates via `JsonStrictValidator`, renders via `cyclonedx.output.json.JsonV1Dot6(bom).output_as_string(...)`.
- [ ] `src/pyforge/warden/cli.py` -- add `--sbom-output PATH` flag + the post-`assemble_report` write hook -- an orthogonal artifact with its own failure path, independent of the report's stdout emission.
- [ ] `tests/fixtures/adversarial_names.json` -- author the NFR-S7 corpus.
- [ ] `tests/unit/test_sbom.py` -- unit-test every I/O-matrix row above except the round-trip and CLI-write-failure rows.
- [ ] `tests/unit/test_cli_sbom.py` -- the `--sbom-output` write-success/write-failure CLI rows.
- [ ] `tests/conformance/test_sbom_schema.py` -- CycloneDX 1.6 schema-conformance sweep over hand-built minimal inventories/reports.

**Acceptance Criteria:**
- Given `--sbom-output out.json` on any scan, when the scan completes, then `out.json` is schema-valid CycloneDX 1.6 and `len(components) == report.inventory_count`.
- Given an adversarial component name, when serialized, then the schema-aware encoder neutralizes it -- no raw string-concatenation path exists anywhere in `sbom.py`.
- Given a conda component with a map-resolved pypi identity, when the BOM is emitted, then `cfe:pypi_purl`/`cfe:match_source`/`cfe:match_confidence` are present per the `identity_source`-gated rule, purls follow G98, and the BOM round-trips through `scan-project --sbom-in`.

## Design Notes

- **`PackageURL` alone solves G98** -- verified live against the installed `packageurl-python`: `PackageURL(type="pypi", name="Django_Foo.Bar", version="1.0")` → `pkg:pypi/django-foo.bar@1.0`. No custom normalization code is needed or wanted; `inventory.py`'s `derive_purl()` cannot be reused for the SBOM because it collapses dots (PEP 503), which is the wrong rule for purls.
- **Why `cfe:match_source`/`cfe:match_confidence` are `identity_source == MAP`-gated** -- `mapping_confidence`'s own docstring in `inventory.py` scopes it to "the map's per-pair tier"; a lock-resolved or native identity was never probabilistically matched, so attaching a map confidence tier to it would misrepresent how that identity was actually resolved. `cfe:pypi_purl` carries no such caveat -- it just states the resolved identity, regardless of source.
- **Determinism scope** -- `bom.serial_number` and `metadata.timestamp` stay volatile in v1 (no `determinism.py` exists yet for either artifact); this matches the report's own current `--deterministic` no-op precedent exactly, so there is nothing inconsistent about leaving the SBOM the same way for this story.

## Verification

**Commands:**
- `pixi run -e pyforge-warden pyforge-warden-test` -- expected: full suite green, including the new `test_sbom.py`/`test_cli_sbom.py`/`test_sbom_schema.py` modules. (If a fresh worktree's `pixi install` hits the known pre-existing `build_artifacts/linux64` local-channel gap documented in `deferred-work.md`, use `pixi run --frozen -e pyforge-warden ...` the same way this planning pass verified the `cyclonedx-python-lib`/`packageurl` APIs.)

**Manual checks (if no CLI):**
- Round-trip smoke check (cross-tool, not part of the pixi test task): `warden scan . --sbom-output /tmp/out.json` in the `pyforge-warden` env, then `scan-project --sbom-in /tmp/out.json` in the `local-recipes`/CFE env — confirm it ingests without error.
