<!-- RECOVERED 2026-07-25 from Claude Code session transcript 1b119a63-25ec-4a15-ba2a-ff6756852dd0.jsonl (~/.claude/projects); this is the ORIGINAL spec incl. its dev/review narrative, not an epics.md regeneration. -->
---
title: 'Story 1.9: Manifest discovery, deterministic selection & the resolved scan set'
type: 'feature'
created: '2026-07-17'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/implementation-artifacts/epic-1-context.md'
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** `discovery.py`'s docstring records its own limit: it is single-directory, fixed-kind, no-precedence (Story 1.2, extended 2.2/2.6) and explicitly defers "full FR1 discovery — multi-manifest enumeration, deterministic selection policy" to this story. Today a tree with manifests in subdirectories is invisible; a target with Python signals but no recognized manifest silently exits 0 `not-applicable` (a false-green D2 was written to close); a manifest that parses to zero components does the same.

**Approach:** Make `discover()` a bounded, deterministic recursive walk (union coverage — every manifest at every depth scans, no precedence winner, per architecture.md's resolved decision). Split the current single "no manifest" path into D2's two fail-closed states using the existing `has_adjacent_python_source` predicate, and add the one sanctioned `--allow-empty` downgrade for a parsed-but-empty extraction.

## Boundaries & Constraints

**Always:** `discover()` walks the full tree under target (sorted directory order, `.git` pruned, ~50,000-entry cap mirroring `has_adjacent_python_source`'s existing bound — cap exceeded fails closed, never a silent partial scan); the mature per-kind stat-honesty logic in `_discover_one` is reused unchanged, called once per visited directory, with each hit's path rewritten relative to the original target. Multi-manifest selection stays **union coverage** (already resolved in architecture.md: scan everything found, report per-manifest) — `recipe.yaml` + `meta.yaml` coexisting in one directory keep scanning both, unchanged. D2's split: (a) `discover()` returns empty AND `has_adjacent_python_source(target)` is true → `Status.ERROR`/exit 2, `ErrorKind.UNPARSABLE_MANIFEST`, owner=`"discovery"`, axis=`AXIS_INGESTION`; (b) empty AND no Python source anywhere → unchanged `not-applicable`/exit 0; (c) at least one manifest parses but the whole scan feeds zero rungs (no components, no engine findings, no errors) → `Status.INDETERMINATE`/exit 1 by default, driver `indeterminate:empty-extraction:<sanitized target path>`, axis `AXIS_INGESTION`; `--allow-empty` downgrades ONLY case (c)'s exit to 0 while `status` stays `indeterminate` (never `clean`/`not-applicable`) — implemented in `verdict.exit_code_for` (sole exit-code owner), never in `cli.py`. `environment.yaml` is a first-class discovered kind (mirrors the existing filename-equals-kind convention, its own `_DISCOVERED_KINDS` entry + matching routing rows + `extractor_for` branch), sharing `EnvironmentYmlExtractor`; both spellings coexisting scan both (union coverage). No new `ErrorKind` member — the enum is documented closed (only `WithholdReason`/`CveMatchLevel` are the sanctioned growable enums); case (a) reuses `ErrorKind.UNPARSABLE_MANIFEST`.

**Block If:** Nothing here — every decision resolves from evidence already in the codebase (architecture.md's union-coverage resolution, the closed-`ErrorKind` invariant, `has_adjacent_python_source`'s existing bounded-walk precedent) or from epics.md's own explicit AC text, not a human judgment call.

**Never:** Do not implement `--warn-only` (a separate, broader adoption-mode downgrade — Epic 3 scope, not named by this story's ACs). Do not implement pyproject-embedded-pixi (`[tool.pixi.*]` tables inside `pyproject.toml`) extraction — deferred-work.md's own precedent for the analogous host/build-dependencies gap calls this a "routing-token-growth decision" for "a future extraction story," not a discovery patch; this story records the discovery-level decision (deferred, not silently dropped) without implementing the extractor widening. Do not add directory-exclusion heuristics beyond `.git` (no vendor/build-dir denylist — unspecified in any planning doc). Do not touch `verdict.py`'s rung order, the frozen exit-code enum `{0,1,2,130}`, or any other status's exit mapping — `exit_code_for` gains parameters, never a new rung or a changed lattice. Do not reshape `Component`/`ResolvedInventory` (frozen, 1.1) or the `ComplianceReport` schema — `resolved_scan_set` already exists as a field; this story populates it correctly, it does not add fields.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Nested monorepo, manifests in 2 subdirs | `a/pyproject.toml`, `b/recipe.yaml` | both discovered; `resolved_scan_set` has 2 entries in deterministic order | No error |
| Same dir carries both `recipe.yaml` + `meta.yaml` | both files present | both scanned (union coverage, unchanged from today) | No error |
| `environment.yaml` + `environment.yml` both present | both files, same dir | both discovered, both routed/extracted | No error |
| Zero manifests anywhere, a `.py` file exists | empty scan target + adjacent source | `Status.ERROR`, exit 2, `ErrorKind.UNPARSABLE_MANIFEST` | typed, "misconfiguration guard" (D2) |
| Zero manifests, zero Python anything | truly empty dir | `Status.NOT_APPLICABLE`, exit 0 (unchanged) | No error |
| Manifest parses, zero components and zero findings, no flag | e.g. empty deps list | `Status.INDETERMINATE`, exit 1 | typed `empty-extraction` driver |
| Same, with `--allow-empty` | same | exit 0; `status` stays `indeterminate` (never clean) | flag downgrades exit only |
| Permission-denied nested subdirectory mid-walk | `chmod 000` subdir | fails closed: `OSError` propagates → `Status.ERROR`, exit 2 | typed, owner `"discovery"` |

</intent-contract>

## Code Map

- `src/pyforge/warden/discovery.py` -- MODIFY: `discover()` becomes a bounded recursive walk (sorted dirnames, `.git` pruned, ~50,000-entry cap; cap exceeded raises `OSError`) that calls the unchanged `_discover_one(dirpath, kind)` per visited directory per `_DISCOVERED_KINDS` entry, rewriting each hit's `path` relative to the original target; add `ENVIRONMENT_YAML_KIND = "environment.yaml"` to the kind constants and `_DISCOVERED_KINDS` (immediately after `ENVIRONMENT_YML_KIND`); rewrite the module docstring (drops the "deferred to 1.9" framing, documents the walk + cap + `.git`-pruning + the environment.yaml addition).
- `src/pyforge/warden/extract/__init__.py` -- MODIFY: import `ENVIRONMENT_YAML_KIND`; add an `extractor_for` branch returning `EnvironmentYmlExtractor(router)` for it (same class as `ENVIRONMENT_YML_KIND`).
- `src/pyforge/warden/routing.py` -- MODIFY: add 2 `_ROUTES` entries for `ENVIRONMENT_YAML_KIND` mirroring the existing `ENVIRONMENT_YML_KIND` dependencies/pip rows.
- `src/pyforge/warden/verdict.py` -- MODIFY: `exit_code_for` gains `driver: StatusDriver | None = None` and `allow_empty: bool = False` keyword params; when `status is Status.INDETERMINATE`, `allow_empty` is true, and `driver is not None` and `driver.finding_id` starts with `"indeterminate:empty-extraction:"`, return `0`; otherwise the existing projection is unchanged. Docstring updated to record this as the ONE flag-driven exit exception, still sole-owned here.
- `src/pyforge/warden/report.py` -- MODIFY: `assemble_report` gains `allow_empty: bool = False`; passes `driver=driver, allow_empty=allow_empty` into `exit_code_for(...)`.
- `src/pyforge/warden/cli.py` -- MODIFY: (a) `_build_parser`'s `scan` subcommand gains `--allow-empty` (`action="store_true"`, mirrors `--deterministic`'s style); (b) the `if not manifests:` branch (~line 311) splits on `has_adjacent_python_source(target)`: true → `_record_error(kind=ErrorKind.UNPARSABLE_MANIFEST, owner="discovery", subject=args.path, axis=AXIS_INGESTION, message=f"no recognized manifest found under {args.path!r} despite Python source present (D2 misconfiguration guard)")`; false → existing stderr-only path, unchanged; (c) after `rungs.extend(policy_rungs)`, if `manifests_parsed > 0 and not rungs`, append `(Status.INDETERMINATE, StatusDriver(axis=AXIS_INGESTION, finding_id=f"indeterminate:empty-extraction:{_sanitize_id_segment(args.path)}"))`; (d) pass `allow_empty=args.allow_empty` into the `assemble_report(...)` call.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- MODIFY: mark the `environment.yaml`-spelling entry `**RESOLVED**` (one-line note: both spellings now discovered/routed identically). Narrow the pyproject-embedded-pixi entry: record that 1.9 made the discovery-level call (deliberately deferred as a routing-token-growth item, matching the 2.2 host/build-dependencies precedent) rather than silently dropping it.
- `tests/unit/test_discovery_extract_cli.py` -- MODIFY: add recursive-discovery tests (manifests found across nested subdirectories in deterministic order, `.git` pruned, permission-denied nested subdirectory fails closed, entry-cap-exceeded fails closed); `environment.yaml` discovery + routing + extraction tests (bare, and alongside `environment.yml` in the same directory); the D2-split tests (no-manifest+python-signal → error/exit 2; no-manifest+no-signal → unchanged not-applicable/exit 0); empty-extraction tests (indeterminate/exit 1 by default; `--allow-empty` → exit 0 with status still `indeterminate`).
- `tests/unit/test_verdict.py` -- MODIFY: add coverage for `exit_code_for`'s new `driver`/`allow_empty` params — empty-extraction driver + `allow_empty=True` → 0; same status with no driver, or a driver whose `finding_id` names a different indeterminate reason (e.g. a stale-DB or low-confidence-mapping cause), + `allow_empty=True` → unchanged 1 (the downgrade must never leak to an unrelated indeterminate cause).

## Tasks & Acceptance

**Execution:**
- [ ] `discovery.py` -- recursive bounded walk + `environment.yaml` kind -- closes the "single-directory stub" gap the module's own docstring names as 1.9's.
- [ ] `extract/__init__.py`, `routing.py` -- wire `ENVIRONMENT_YAML_KIND` through dispatch + routing -- FR2 coverage for the new kind.
- [ ] `verdict.py` -- `exit_code_for` gains the one sanctioned `allow_empty` exception -- keeps exit-code sole-ownership intact.
- [ ] `report.py` -- thread `allow_empty` through `assemble_report` -- the only caller of `exit_code_for`.
- [ ] `cli.py` -- `--allow-empty` flag + the D2 split + the empty-extraction rung injection -- closes the false-green D2/FR22 targets.
- [ ] `deferred-work.md` -- close the `environment.yaml` item, narrow the pyproject-pixi item.
- [ ] `test_discovery_extract_cli.py`, `test_verdict.py` -- regression coverage for every I/O-matrix row above.

**Acceptance Criteria** *(epics.md story 1.9):*
- Given a tree with multiple candidate manifests at any depth, when `scan <path>` runs, then discovery+classification+selection is total and deterministic — the same tree yields the same `resolved_scan_set` every time, and each dependency source-section still routes to its correct extractor (FR1/FR2).
- Given the resolved scan set, when the report is emitted, then it remains the existing first-class `ResolvedInventory.resolved_scan_set` field, now correctly populated from the recursive walk (no schema change).
- Given discovery finds nothing parseable while Python signals are present, then the run is `error`/exit 2; given candidates are found but the extraction is empty (ambiguous/partial), then the run is `indeterminate`/exit 1, never `clean` — both routed through the existing typed-error/rung machinery, never a new `ErrorKind`.
- Given a monorepo sweep with Python signals but an empty extraction, when `--allow-empty` is passed, then the exit downgrades to 0 while `status` stays `indeterminate` (never `clean`); without the flag the run stays fail-closed at exit 1.

## Design Notes

**Why union coverage, not a precedence winner:** architecture.md already resolved PRD's "multi-manifest selection precedence" open question explicitly: "Multi-manifest selection (FR1) → union coverage — scan all discovered manifests, report per-manifest; honest coverage means the denominator includes everything found." Epics.md's "deterministic selection/precedence policy" AC text is therefore about the ENUMERATION being deterministic (same tree → same set, sorted), not about picking a winning manifest kind — `recipe.yaml`+`meta.yaml` mid-migration both scan today and keep doing so.

**Why `ErrorKind.UNPARSABLE_MANIFEST` for the "nothing found, Python present" case, not a new kind:** `models.py` documents `ErrorKind` as a closed set, in explicit contrast to `WithholdReason`'s "(growable, additive)" docstring and architecture.md's "the sanctioned growable enum" language naming only `WithholdReason`/`CveMatchLevel`. `INTERNAL_ERROR` is reserved by existing precedent/docstring for actual tool bugs, not an expected external misconfiguration; `CONFIG_PARSE`/`CONFIG_VALIDATION` are unused reserved slots for the not-yet-built `ConfigLoader` (FR30) and repurposing them would collide with their real owner. `UNPARSABLE_MANIFEST`, read as "nothing at this target could be resolved into a manifest," is the closest existing fit and keeps the owner (`"discovery"`) and axis (`AXIS_INGESTION`) consistent with the sibling propagated-`OSError` path already in `cli.py`.

**Why the `allow_empty` exception lives in `verdict.exit_code_for`, not `cli.py`:** exit-code sole-ownership (verdict.py-only) is an enforced meta-test invariant. The existing `warn_is_error` keyword param already establishes the pattern of a caller-supplied knob that adjusts one rung's projection without touching the lattice; `allow_empty` follows the same shape, scoped narrowly to the `empty-extraction` driver so it can never accidentally downgrade an unrelated indeterminate cause (e.g. a stale vuln DB).

**Why `_discover_one` is reused unchanged:** its stat-honesty logic (dangling symlinks, TOCTOU, non-regular files, permission-denied) is already mature and exhaustively tested; recursion is purely an orchestration change in `discover()` (which directories get visited, in what order, with what path-rewriting), not a change to how any single candidate is checked.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: all prior suites unchanged + new recursive-discovery/D2-split/allow-empty/environment.yaml tests green.
- `pixi run --frozen -e local-recipes mypy src/shared/packages/pyforge-warden/src/pyforge/warden` -- expected: no new errors vs the story-1.7-recorded baseline.
- `pixi run --frozen -e local-recipes ruff check src/shared/packages/pyforge-warden/src/pyforge/warden` -- expected: no new issues.
- Manual: `git diff --stat` shows zero changes to `Status`/`ErrorKind` enum members, the verdict lattice order, the frozen exit-code enum, `Component`/`ResolvedInventory` field shapes, or `report-schema.json`.
