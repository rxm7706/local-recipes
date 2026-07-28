# Reviewer Gate — Rubric Walk: `architecture.md` (pyforge-warden)

- **Artifact:** `_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md` (legacy Architecture Decision Document; judged on substance per gate instructions, not SPINE format)
- **Reviewed against:** good-spine checklist (7 items); driving contract `docs/specs/pyforge-warden.md` (D12 re-baseline 2026-07-16) + PRD canonical FR1–FR40; brownfield code at `src/shared/packages/pyforge-warden/` (stories 1.1–1.4 shipped)
- **Reviewer:** rubric walker, 2026-07-16

## Gate verdict

**PASS — no blocking findings.** 0 critical, 0 high, 2 medium, 5 low. The two mediums (finding-ID grammar for the new axes; silent JFrog publish-path mechanics) should land as doc edits before stories 6.2/6.8 and 6.6 respectively, but neither lets parallel units silently diverge today because the shipped contract fails loud at construction.

## Per-item verdicts

| # | Checklist item | Verdict |
|---|---|---|
| 1 | Fixes the real divergence points for stories; misses none | **PASS with 1 MEDIUM** (F1) |
| 2 | Every binding rule enforceable and prevents its divergence | **PASS** (1 LOW staleness, F3) |
| 3 | Nothing deferred could let two units diverge | **PASS** (deferrals explicit + single-owner; residual risk = F1, F5) |
| 4 | Named tech current/exists | **PASS** (no findings) |
| 5 | Ratifies the brownfield codebase | **PASS** (1 LOW staleness, F2) |
| 6 | Covers the driving contract (spec D12 + PRD FR1–FR40) | **PASS** (1 LOW wording, F7) |
| 7 | Every altitude-owned dimension decided/deferred/open — esp. operational envelope | **PARTIAL** (1 MEDIUM F4, 2 LOW F5/F6) |

## Item-by-item rationale

### Item 1 — divergence points for the story level: PASS with 1 MEDIUM

The doc pins exactly the surfaces where parallel dev-agents would diverge: the single `ResolvedInventory`/`Component` spine with identity+merge rules living only in `inventory.py`; the canonical StrEnums; the verdict lattice + exit projection owned solely by `verdict.py`; `_engine_env()` as the sole subprocess path; the `_REPORT_AXES` hard seam named as the one place a new axis's coverage claim can be dropped; the 6.1 schema amendment as one coordinated set; the two-mode policy as "a policy-table flip, never a producer change"; the actuator socket-deny carve-out scoped to `actuator.py` under the flag. All verified against the shipped enforcement points (see item 2).

One real divergence point is missed → **F1** (finding-ID grammar for axes 3/4).

### Item 2 — binding rules enforceable: PASS

Every binding rule names a mechanical enforcement and the mechanisms exist in the tree:

- AST-denylist / no-execution zone → `tests/meta/test_extract_no_execution.py` (exists)
- verdict sole-ownership → `tests/meta/test_verdict_sole_ownership.py` (exists)
- socket deny-by-default → `tests/meta/test_socket_deny_alive.py` (exists); the 6.9 carve-out rule is stated as binding and scoped
- schema self-validation before emit → `report.py:130-143` `render_json` validates against the packaged schema (verified — the doc/spec's line citation is exact)
- status/exit coherence → enforced at construction (`models.py` `_LEGAL_EXITS_BY_STATUS` + `ComplianceReport.__post_init__`), matching the doc's "an incoherent contract" rule
- determinism → `sort_keys=True`, full-tuple sort keys, twice-run gate — all present in `models.py`/`report.py`

One internal staleness → **F3** ("6→3 exit projection" labels).

### Item 3 — deferrals: PASS

Deferred items are explicit and single-owner: feed cache/lifecycle → story 6.4 (frontmatter states the ownership), EPSS shares `feeds.py` (6.7), endoflife via the same layer (6.3); the four original gap-analysis items are closed or story-owned with named owners (map → 2.1, confidence threshold → FR18, denominator → 1.9, OSV DB → the 1.4 decision record, which exists as `osv-db-offline-provisioning-decision.md`); calibration values (p95, `--db-max-age`) are low-divergence-risk constants. The one deferral-shaped gap that could split two units is F1 (counted under item 1); F5 notes the feed-cache convention residual.

### Item 4 — named tech: PASS

All named technology exists and is current as of 2026-07: `deptry` (DEP001–DEP005 codes real, no-severity confirmed), `osv-scanner` v2 (`--format json`, exit contract 0/1/127/128 pinned by the in-repo Story-1.4 spike + decision record), `license-expression` (nexB/AboutCode), `cyclonedx-python-lib` + CycloneDX 1.6, PyYAML `safe_load`, `packaging`, `jsonschema`, hatchling + `pixi-build-python`, py-rattler `LockFile` (test-side oracle), parselmouth (prefix-dev conda↔PyPI mapping), CISA KEV + FIRST EPSS + endoflife.date feeds, Python ≥3.12 (`tomllib`, `StrEnum`). Contracts are pinned with dates and grounding sources in the frontmatter (`pinnedEngineContracts`, `axisDataContracts`). No stale or invented tech found.

### Item 5 — ratifies the brownfield code: PASS

Spot-checks of the shipped 1.1–1.4 code confirm the doc describes what exists:

- **`models.py`** — `Status` = exactly the doc's 7-rung vocabulary; `ErrorKind` = exactly the 9 values the doc lists; finding-ID three-family grammar + `_LEGAL_EXITS_BY_STATUS` + driver-required-for-non-clean all match the doc's contract. One staleness: **F2** (`WithholdReason` grew a fifth member).
- **`verdict.py`** — `_RUNG_ORDER` matches the lattice exactly (`error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`); exit projection matches the locked mapping (`indeterminate → 1`, `error → 2`, `warn → 0` with `warn_is_error`, `EXIT_SIGINT = 130`); `match_level_rung` routes unknown levels to `indeterminate`, never `clean` — the doc's additive-growth safety rule, verbatim.
- **`interfaces.py`** — the doc's "axis registry = the open string mechanism that already shipped; no `Axis` protocol exists or is needed (OD7 retired)" is accurate: five Protocols + `EngineResult` + `DefaultPolicy`, axis as plain string, no Axis protocol. The tighten-only backstop-replacement rule the doc cites is recorded in the shipped docstrings; `DefaultPolicy` routes hygiene findings through `hygiene.py:hygiene_rung` exactly as the doc's Gap-A status note (2026-07-15) claims.
- **`report.py`** — `_REPORT_AXES` at line 57 (the doc's named hard seam, exact); `REPORT_SCHEMA_VERSION = "1.0.0"`; self-validation in `render_json` (130–143).
- **`pixi.toml:32-33`** — `deptry = "*"` / `osv-scanner = "*"`, exactly the state the distribution-gate bullet (6.6) says it will replace.
- The module-structure list vs project-tree discrepancy (`models.py`) is self-acknowledged with an explicit authority rule ("the § Project Structure tree is authoritative") — not a finding.

No contradiction between the doc and the shipped contract was found. The multi-axis deltas are correctly framed as *additive to* the shipped 1.1–1.4 contract (e.g., scalar `Finding.epss` today → `epss {score, percentile}` via the versioned 6.1 amendment, matching `models.py`'s current scalar slot).

### Item 6 — driving contract coverage: PASS

- **D12 four axes with flag-activated gates:** covered — "Two-mode policy (FR37 + FR33/FR35 — D12, 2026-07-16)" states the exact semantics (unconfigured → `warn` rung with axis-naming driver, exit 0; any flag → gate: denied/eol → `policy-violation`, unknown → `indeterminate`; tighten-only vs `DefaultPolicy`).
- **KEV + EPSS:** covered — `feeds.py` layer (6.3/6.4/6.7), NFR-S2 posture, per-feed provenance, absent/stale under an active KEV/`--min-epss` policy → `indeterminate` (review-T1); `kev_date` + `epss` object ride the 6.1 amendment.
- **Baseline FR39:** covered — `baseline.py` bullet matches the spec/PRD exactly (committed schema-validated file, finding-ID-keyed, waiver-expiry semantics, echoed in report, NEW-findings-only, read-only + `--baseline-emit`).
- **Actuator FR40:** covered — `actuator.py` as sole forge-egress module, opt-in, env-credentialed, strictly post-verdict, failed PR-open outside status/exit composition, `--fix-prs-dry-run`, plus the binding socket-deny carve-out rule.
- **PRD FR1–FR40:** the epic→structure table maps FR1–FR31 rows + the FR32–FR40 multi-axis row; FR33/FR35 exist in the PRD (prd.md:562/566) and are cited correctly. NFR-S9 age-provenance is mapped to `feeds.py`/bundled data. No orphaned FR found.

One wording nit → **F7** (pipeline diagram's `gating:false → warn` annotation).

### Item 7 — altitude-owned dimensions / operational envelope: PARTIAL

- **Distribution/publish path:** only the *gate* is decided (6.6 version ranges block v1 JFrog / v1.x public publish). The publish mechanics themselves — how the built package reaches JFrog (build artifact type(s): wheel + conda? channel/repo names, upload task, who/what runs it) — are silent: not decided, not deferred to a named owner, not an open question. Spec + PRD make internal JFrog distribution a v1 deliverable, so this dimension is owned by this altitude. → **F4 (MEDIUM)**.
- **Feed provisioning operations:** explicitly deferred with owners (6.4 owns cache/lifecycle/max-age; 6.7 shares `feeds.py`; the OSV-DB decision record is the named template) — an acceptable deferral, but the cross-feed cache-root convention (where on disk; env-var override) is unpinned while three stories touch it. → **F5 (LOW)**.
- **CI integration:** the *contract* surface is decided (frozen exit enum, pure-JSON stdout, `rc==2 → infra owner` fleet routing, typed `engine-unavailable` owned by platform/CI, engines as conda run-deps so installing the package provisions them, offline DB as a conda package per the 1.4 decision record). What is silent is any named CI-consumption/runner-provisioning statement (the doc contains no CI-integration paragraph at all — the string "CI" appears only inside "CISA"). Largely derivable from the decided contract, hence LOW rather than MEDIUM. → **F6 (LOW)**.

Everything else the altitude owns is decided or explicitly N/A'd (the doc even states which generic categories are N/A and why).

## Findings

### F1 — MEDIUM — Finding-ID grammar for the license/currency axes is a missed divergence point
- **Location:** § Multi-axis reconciliation (6.1 amendment bullet) + § "The single-source-of-truth rules"; contrast `models.py:43-47`.
- **Quote (doc):** "One sanctioned schema amendment (6.1, FR38): additive `schema_version` bump — per-axis `gating` bool · `license`/`currency` sections … Coordinated set: `report-schema.json` · `models.py` · `report.py` … the exact-13 `Component` test … fixtures."
- **Quote (shipped code, `models.py`):** the three ID families are `vuln:<advisory-id>:<pkg>@<ver>` | `hygiene:<DEP-code>:<module-or-pkg>` | `indeterminate:<reason>:<pkg>`, enforced at `Finding.__post_init__`.
- **Problem:** a license `denied` or currency `eol` finding fits none of the three families (it is not an `indeterminate:` outcome), yet FR39 baselines and waivers key on "the stable finding-ID grammar (the waiver key)". The 6.1 coordination set names `models.py` but never says the ID-family grammar must grow, and no rule says what the new family/families look like. Stories 6.2, 6.3, 6.5, and 6.8 could each resolve this differently (e.g., `license:<verdict>:<pkg>` vs overloading `indeterminate:`). Mitigation already in place: `Finding.__post_init__` fails loud, so divergence cannot ship silently — hence MEDIUM, not HIGH. **Remedy:** add the ID-family extension (and its axis cross-check rule, mirroring the vuln/hygiene prefix checks) to the 6.1 amendment's coordinated set.

### F2 — LOW — `WithholdReason` enum listing is stale vs shipped code
- **Location:** § GAP C ("Withhold reason enum: `no-version | unmapped-ecosystem | native-nonpypi | range-only`") and § single-source-of-truth rules (same four-member list).
- **Shipped:** `models.py:83-94` has five members — `AMBIGUOUS_IDENTITY = "ambiguous-identity"` added 2026-07-13 as sanctioned additive growth.
- **Problem:** the doc was edited 2026-07-15/16 without picking up the 07-13 enum growth; a story author trusting the doc's "canonical enums… defined once" list misses a member. **Remedy:** add `ambiguous-identity` to both listings.

### F3 — LOW — Stale "6→3 exit projection" labels contradict the locked "7→4" projection
- **Location:** § Module structure line for `verdict.py` ("J9 lattice + 6→3 exit projection + status.driver") and § Complete project tree (same comment); contrast § false-green triad #2 ("7→4 exit projection (locked; `indeterminate` pinned 2026-07-12)").
- **Problem:** "6→3" predates the `indeterminate` rung (7 statuses → exits {0,1,2}+130). Shipped `verdict.py` implements 7→4. Cosmetic but it sits exactly on the doc's most load-bearing invariant. **Remedy:** s/6→3/7→4/ in both comments.

### F4 — MEDIUM — Distribution/publish path mechanics are a silent dimension
- **Location:** § Multi-axis reconciliation, sole coverage: "**Distribution gate (6.6):** engine run-deps move from `\"*\"` to tested version ranges (NFR-C1 — range, not pin); v1 JFrog / v1.x public publish block on it (review-T-a)."
- **Problem:** the spec/PRD make "internal JFrog (PyPI + conda) ships v1" a deliverable, but the architecture decides only what *blocks* publish, never the publish path itself: artifact set (wheel? conda via `pixi-build-python`? both), target JFrog repos/channels, upload mechanism, and whether the bundled-data build stamps (`snapshot_at`, NFR-S9) are produced by that pipeline. None of it is decided, deferred to a named owner, or listed as an open question — the definition of a silent dimension at this altitude. **Remedy:** add a short Distribution decision (or an explicit open-question entry with an owner, e.g. widen story 6.6's remit).

### F5 — LOW — Feed-cache operational conventions deferred without a pinned cross-feed convention
- **Location:** frontmatter `axisDataContracts.cisa-kev` ("cache/lifecycle owned by story 6.4") + § Multi-axis reconciliation feed-cache bullet.
- **Problem:** deferral is explicit and single-owner (good), but the cache-root location/override convention spans three stories (6.3/6.4/6.7) and is unpinned. Mitigated by the single shared `feeds.py` module and 6.4-as-template, hence LOW. **Remedy:** one sentence pinning "cache root convention decided in 6.4; 6.3/6.7 conform" (or the convention itself).

### F6 — LOW — CI-integration consumption is never named as a dimension
- **Location:** absent throughout (the only "CI" substring in the document is inside "CISA", line 27).
- **Problem:** for a product whose spec lifetime is "long-running CI/CD quality gate," the doc never states the CI-consumption picture as a decision, even though its parts are all decided piecemeal (frozen exit enum + `rc==2 → infra owner` routing, pure-JSON stdout, conda run-deps provisioning, offline-DB conda package per the 1.4 decision record). Substantively covered, formally silent — LOW. **Remedy:** a two-line "CI integration = install the conda package (engines + DB ride as run-deps), run `warden`, branch on the frozen exit enum, archive stdout JSON" statement, or an explicit N/A/deferral.

### F7 — LOW — Pipeline diagram understates D12 flag-activation
- **Location:** § Requirements Overview diagram: "Axis 3 License: license-expression (FR32; gating:false → warn)" (same for Axis 4).
- **Problem:** under D12 the axes ship full gates, flag-activated; `gating:false` is only the unconfigured default. The § Multi-axis reconciliation bullet states this correctly, but a reader of the diagram alone could conclude the gates are deferred (the pre-D12 posture). **Remedy:** annotate the diagram lines "(FR32; unconfigured → warn, flags activate gate — D12)".

## Finding counts

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 0 |
| Medium | 2 (F1, F4) |
| Low | 5 (F2, F3, F5, F6, F7) |
