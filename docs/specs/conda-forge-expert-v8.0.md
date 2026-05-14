# Tech Spec: conda-forge-expert v8.0.0 — Structural Enforcement + Persona Profiles

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> bundled v8.0.0 release closing four deferred follow-ups from the
> v7.9.0 actionable-scope audit retro). ~22 implementation stories
> across 4 waves. Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/conda-forge-expert-v8.0.md
> ```
>
> **Per `CLAUDE.md` Rule 1**, any BMAD agent executing this spec MUST invoke
> the `conda-forge-expert` skill before touching atlas code. Per Rule 2, the
> effort closes with a CFE-skill retrospective and a `CHANGELOG.md` entry.

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only, no PRD/architecture phase) |
| Surface area | `conda-forge-expert` skill — schema v21, atlas pipeline (Phase D / G / H / + every selector), `build-cf-atlas` orchestrator + new `--profile` flag, MCP server (auto-detection helpers), planning artifacts (PRD + architecture-cf-atlas + epics) |
| Scope | (A5) `v_actionable_packages` SQL view + structural enforcement meta-test; (A3) Phase H `pypi_last_serial` freshness gate (Layer 2 of the audit's serial-gate thread); (A6) drop `vuln_total` column from schema; (A4) persona-aware default profiles (`maintainer` / `admin` / `consumer`) for `build-cf-atlas` |
| Version | conda-forge-expert v7.9.0 → **v8.0.0** (MAJOR — A4 changes default behavior of `build-cf-atlas`) |
| Out of scope | Channel-wide Phase H/N cron operationalization (separate spec); per-version vdb-history snapshot side table for time-travel queries; multi-output feedstock per-output dep-graph (Phase J extension); CycloneDX Protobuf / SPDX RDF |
| Created | 2026-05-13 |
| Driven by | `_bmad-output/projects/local-recipes/implementation-artifacts/retro-atlas-pypi-universe-split-2026-05-13.md` action items A3 / A4 / A5 / A6 |
| Predecessor | `docs/specs/atlas-pypi-universe-split.md` (v7.9.0 — actionable-scope audit) |

---

## Background and Context

### The problem

The v7.9.0 actionable-scope audit closed four phase-denominator findings
but surfaced a deeper class of issues that are out-of-scope for a Quick
Dev pass and were deferred to follow-up specs. Each is independently
shippable but they share structural concerns + a schema bump, making a
bundled release coherent:

1. **Structural drift is invisible without structural enforcement.**
   Six phases (F/G/G'/K/L/N) used the canonical persona-filter triplet
   `conda_name IS NOT NULL AND latest_status='active' AND COALESCE(feedstock_archived,0)=0`
   correctly. Three (H/J/M) drifted. No test or lint rule caught it;
   v7.9.0 fixed each by-hand. The next phase author (or refactor) has
   no enforcement preventing the same drift.
2. **`pypi_last_serial` is collected but unused.** Phase D's daily-lean
   path populates `pypi_last_serial` on every conda-linked row from the
   40 MB PyPI Simple API dump. Phase H's gate uses only TTL — it
   re-fetches every package past TTL even when the upstream serial
   hasn't moved. Wiring the serial into Phase H's gate drops warm
   daily Phase H from ~5 min (TTL-boundary day) → ~30 s (only rows
   whose upstream actually moved).
3. **`vuln_total` column is written every Phase G run but read by
   nothing.** Audit verified: no CLI, MCP tool, SQL query, or report
   touches it. Pure write waste. Either expose via a CLI flag or drop.
4. **The build-cf-atlas default targets nobody.** It runs all 17 phases
   silently skipping 5 (E, G, K, N, G'), producing a degraded atlas
   where `whodepends`, `feedstock-health`, `cve-watcher`, and 5+ open
   📋 catalog entries return empty. The most common user (a maintainer
   with a few hundred feedstocks) needs E + N + maintainer-scoped K.

### What's been ruled out

- **Splitting into four separate releases.** The four sub-specs share
  schema v21 and would otherwise require four migrations + four retros
  + four CHANGELOG entries. Bundling is the cheaper coordination cost.
- **Holding the bundle for a v8.0.0 cut-line that includes additional
  unspecified items.** The four items here have well-bounded scope; adding
  speculative items would dilute the release. Future v8.x roadmap items
  (channel-wide Phase H cron, multi-output dep graph, per-version vdb
  history) get their own specs.
- **Making A4 (persona profiles) the entire v8.0.0.** A4 alone would be
  a substantial spec, but it depends on A5's view-based enforcement to
  prevent the new profile-aware defaults from re-creating the drift
  v7.9.0 just fixed. Bundling A5 + A3 + A6 + A4 gives the structural
  cleanup + the UX shift one coherent migration story.
- **Targeting v7.10.0.** A4's default-behavior change for `build-cf-atlas`
  is exactly the textbook MAJOR criterion. Operators with custom
  invocations expecting the v7.x silent-skip behavior need an explicit
  signal.

### What's available to leverage

- **The canonical persona-filter triplet** is already verbatim in
  six phases (F/G/G'/K/L/N selectors) — A5 extracts it into the
  view; A3 uses the view.
- **`pypi_last_serial`** is populated on every conda-linked row by
  v7.9.0's Phase D daily-lean path — A3 just needs to read it.
- **Phase E's cf-graph cache + Phase N's GraphQL batching** are already
  the right primitives for `--profile maintainer` to enable them by
  default — A4 just changes the gating from opt-in to opt-out.
- **`gh api user`** returns the authenticated GitHub user's login — A4
  uses it to auto-derive `PHASE_N_MAINTAINER` for `--profile maintainer`.
- **The v20 schema migration framework** in `init_schema` extends
  naturally to v21 (same `if v21_pre_count > 0:` pattern as v20).
- **The 6-phase precedent of `conda_name + active + !archived`** makes
  the view trivially correct: it's exactly what F/G/G'/K/L/N already
  query.
- **The `bmad-edit-prd` + `bmad-correct-course` pattern from v7.9.0**
  is the right shape for the v8.0.0 BMAD-artifact sync.

### Verified facts (informational)

Measured against the post-v7.9.0 atlas (verified 2026-05-13 09:43):

| Metric | Value |
|---|---|
| `packages` rows (conda-actionable working set) | 32,988 |
| `pypi_universe` rows (PyPI directory) | 786,302 |
| Schema version | 20 |
| Phases using canonical triplet | 6 (F/G/G'/K/L/N) directly; H/J/M also after v7.9.0 |
| Selectors that read `FROM packages WHERE conda_name IS NOT NULL ...` | 8 (counts include both query selectors + write gates) |
| Rows with `pypi_last_serial` populated | ~12,000 (all conda-linked rows post-Phase-D) |
| `vuln_total` reads in code/CLI/MCP/SQL | 0 |
| Default `build-cf-atlas` phases that silently skip on fresh install | 5 (E, G, K, G', N) |
| Open 📋 catalog rows gated on Phase N | 5 (gh-pulls, gh-issues, ci-red filter, abandonment composite, maintainer last-active) |

---

## Goals

- **G1.** **Structural drift becomes impossible.** A new `v_actionable_packages`
  SQL view encodes the canonical persona-filter triplet; six existing
  selectors refactor to `FROM v_actionable_packages` instead of `FROM
  packages WHERE conda_name IS NOT NULL AND ...`. A meta-test asserts
  every remaining `SELECT ... FROM packages WHERE ...` either uses the
  view OR has an inline `# scope: ...` justification comment. Next
  phase author can't accidentally drift.
- **G2.** **Phase H warm-daily wall-clock drops 10×.** With the serial-gate
  wired, daily Phase H runs only fetch rows whose `pypi_last_serial` moved
  since the last successful fetch. Warm-daily wall-clock drops from ~5
  min (TTL-boundary day) to ~30 s (typical day: 30-100 packages move).
- **G3.** **Schema cleanup ships the column drop.** `vuln_total` column
  removed from `packages` in schema v21 migration; Phase G stops writing
  it; cve-watcher CLI gains optional `--show-total` if/when the data is
  ever needed (compute from `vuln_critical + vuln_high + vuln_kev`).
- **G4.** **`build-cf-atlas --profile maintainer`** is the default for
  maintainer-scoped CLIs (`staleness-report --maintainer X`, etc.) and
  produces a complete atlas with E + J + M + K + N all populated for
  the maintainer's scope. Five 📋-open catalog rows flip to ✅.
- **G5.** **`--profile admin`** runs channel-wide N (multi-PAT-aware if
  configured) + full L + D universe upsert on weekly cadence.
- **G6.** **`--profile consumer`** prioritizes air-gap friendliness:
  Phase F via s3-parquet, Phase H via cf-graph, no Phase N, no Phase D
  universe upsert.
- **G7.** **Schema v21 migration is self-healing.** Existing v20 atlases
  upgrade cleanly on next `init_schema`: drop `vuln_total` column (via
  table rebuild — SQLite limitation), create `v_actionable_packages`
  view, add `pypi_version_serial_at_fetch` column (idempotent). No
  operator action.
- **G8.** **Persona profile auto-detection.** `--profile maintainer`
  auto-derives `PHASE_N_MAINTAINER` from `gh api user` when available.
  `--profile admin` warns if no multi-PAT rotation configured but
  proceeds with single-PAT degraded mode.
- **G9.** **Catalog flips reflect actual surface changes.** `atlas-actionable-intelligence.md`
  rows for "gh-pulls", "gh-issues", "feedstock-health --filter ci-red",
  "abandonment composite", "maintainer last-active" — all 5 currently
  📋-open — flip to ✅ shipped (V8.0.0+).

## Non-Goals

- **NG1.** No channel-wide Phase H/N cron operationalization. Separate
  spec; depends on PAT rotation strategy which is a deployment-level
  concern.
- **NG2.** No per-version vdb-history snapshot side table for
  time-travel CVE queries. Separate spec; touches Phase G' design.
- **NG3.** No multi-output feedstock per-output dep-graph (Phase J
  extension). Separate spec; touches Phase J + downstream `whodepends`.
- **NG4.** No new MCP tools for persona profiles. The `build-cf-atlas`
  CLI gains `--profile`; MCP exposure of the same is a follow-up if
  operators want programmatic profile selection.
- **NG5.** No `vuln_total` re-introduction. Audit confirmed zero
  consumers; this spec drops it. Future re-adds (e.g., for a dashboard
  CLI) would write a fresh column with explicit consumer commitment.
- **NG6.** No backward-compat shim for the dropped `vuln_total`. Direct
  schema migration — no `vuln_total_deprecated` rename or view.

---

## Lifecycle Expectations

- **One-time migration cost** when first upgrading from schema v20 to
  v21: `vuln_total` column drop requires SQLite table rebuild (~5-15 s
  on a 32k-row `packages` table). View + column-add are instant.
- **Steady-state per-build cost** (post-v8.0.0 with `--profile maintainer`
  as the documented default):
  - Phase E: same as v7.9.0 (cf-graph cache 7d TTL).
  - Phase H **warm daily**: ~30 s (serial-gated; only moved packages
    re-fetch).
  - Phase H **cold**: ~30 min (unchanged; serial-gate has no prior
    state to compare).
  - Phase N: ~30-60 s for ~700 feedstocks (auto-scoped to `gh api user`).
- **Per-build cost (admin profile)**: similar to maintainer scope plus
  channel-wide Phase N (~30 min) — only run weekly.
- **Per-build cost (consumer profile)**: similar to v7.9.0 (no Phase N,
  no Phase D universe upsert).
- **Storage delta**:
  - `packages` shrinks by ~10 MB (vuln_total column drop).
  - `pypi_version_serial_at_fetch` adds ~96 KB (12k INTEGER rows).
  - `v_actionable_packages` is a view (no storage cost).
  - Net: ~10 MB smaller `cf_atlas.db`.

---

## Design

### Part A — `v_actionable_packages` view + structural enforcement (A5)

#### Schema v21 (A5 component)

```sql
-- Canonical persona-filter triplet, encoded once as a view so phase
-- authors can't drift. Refactor existing selectors to read FROM
-- v_actionable_packages; new selectors do the same by default.
CREATE VIEW IF NOT EXISTS v_actionable_packages AS
SELECT *
FROM packages
WHERE conda_name IS NOT NULL
  AND COALESCE(latest_status, 'active') = 'active'
  AND COALESCE(feedstock_archived, 0) = 0;
```

#### Phase-selector refactor

Refactor 6 existing phase selectors to read from the view. Each
becomes `FROM v_actionable_packages` (drop the verbose triplet):

- `_phase_f_eligible_rows` (conda_forge_atlas.py:1696)
- Phase G eligible-rows (~line 2243)
- Phase G' eligible-rows (~line 4724)
- `_phase_h_eligible_pypi_names` (~line 2509) — must add `AND pypi_name IS NOT NULL` since the view doesn't include pypi-name filter
- `phase_k_vcs_versions` selector (~line 3209)
- `phase_l_extra_registries` selector (~line 3805)
- Phase N's `base_select` (~line 4456)

(Phases B, B.5, B.6, C, D, E, E.5, J, M write to or read from `packages`
without the actionable filter — leave them on direct `FROM packages`
with `# scope: ...` justification comments per the new meta-test.)

#### Structural enforcement meta-test

New `tests/meta/test_actionable_scope.py`:

```python
"""Every SELECT ... FROM packages WHERE ... must use v_actionable_packages
OR have a `# scope: ...` justification comment.

Prevents the kind of drift v7.9.0 fixed by-hand. New phase authors
either query the view (and inherit the canonical triplet) or
explicitly justify why a broader scope is needed.
"""
def test_packages_selectors_use_view_or_justify_scope():
    src = Path(SCRIPTS_DIR / "conda_forge_atlas.py").read_text()
    for match in re.finditer(r"SELECT [^;]+ FROM packages\b", src, re.DOTALL):
        # walk upward to find the preceding comment or context
        ... # see tests/meta/test_actionable_scope.py for full impl
```

### Part B — Phase H `pypi_last_serial` freshness gate (A3)

#### Schema v21 (A3 component)

```sql
-- Track the serial at the time of each successful Phase H fetch.
-- Compared against pypi_last_serial (populated by Phase D's daily-lean
-- path) to decide whether to re-fetch.
ALTER TABLE packages ADD COLUMN pypi_version_serial_at_fetch INTEGER;
CREATE INDEX IF NOT EXISTS idx_pypi_serial_at_fetch
    ON packages(pypi_version_serial_at_fetch);
```

#### Phase H gate refactor

```python
# BEFORE (v7.9.0):
sql = (
    "SELECT DISTINCT pypi_name FROM v_actionable_packages "
    "WHERE pypi_name IS NOT NULL "
    "  AND COALESCE(pypi_version_fetched_at, 0) < ?"
)

# AFTER (v8.0.0 — Layer 2):
sql = (
    "SELECT DISTINCT pypi_name FROM v_actionable_packages "
    "WHERE pypi_name IS NOT NULL "
    "  AND ("
    "       pypi_version_fetched_at IS NULL "       # never fetched
    "    OR pypi_last_serial != pypi_version_serial_at_fetch "  # upstream moved
    "    OR pypi_version_fetched_at < ? "           # safety re-check (30d cap)
    "  )"
)
```

Phase H's successful-fetch write also stamps the serial:

```python
conn.execute(
    "UPDATE packages SET pypi_current_version = ?, "
    "    pypi_current_version_yanked = ?, "
    "    pypi_version_fetched_at = ?, "
    "    pypi_version_source = 'pypi-json', "
    "    pypi_version_serial_at_fetch = ? "  # NEW
    "WHERE pypi_name = ?",
    (version, yanked_int, now, current_serial, pypi_name),
)
```

`current_serial` comes from the Phase H worker: either re-fetched from
the Simple API alongside the JSON (one extra row in `pypi_last_serial`
write-back per fetched row) OR read from `packages.pypi_last_serial`
(the value Phase D wrote on its most recent run — accurate enough for
gating since Phase D and Phase H both run daily).

### Part C — Drop `vuln_total` (A6)

#### Schema v21 (A6 component)

SQLite doesn't support `ALTER TABLE DROP COLUMN` in versions <3.35.0
(and even when supported, requires a rebuild for indexed/PK columns).
Use the standard rebuild pattern:

```python
# v20 → v21: drop vuln_total column (write-only, no consumer reads).
v21_drop_vuln_total = bool(list(conn.execute(
    "SELECT 1 FROM pragma_table_info('packages') WHERE name='vuln_total'"
)))
if v21_drop_vuln_total:
    print("  v21 migration: dropping unused vuln_total column from packages...")
    # SQLite ≥ 3.35 supports DROP COLUMN directly; fall back to rebuild
    # if older. conda-forge ships SQLite 3.46+, so the simpler path is
    # the documented one.
    conn.execute("ALTER TABLE packages DROP COLUMN vuln_total")
```

Phase G stops writing `vuln_total`. CHANGELOG breaking-change note:
"Column `packages.vuln_total` dropped in schema v21. Use
`vuln_critical_affecting_current + vuln_high_affecting_current +
vuln_kev_affecting_current` if a sum is needed."

### Part D — Persona-aware default profiles (A4)

#### New `--profile` flag on `build-cf-atlas`

```bash
# build-cf-atlas adds a --profile flag with three preset bundles:

pixi run -e local-recipes build-cf-atlas --profile maintainer
  # E default-on, N auto-scoped to `gh api user`, K (GitHub auth required),
  # L restricted to populated registries in scope, F via auto-source

pixi run -e local-recipes build-cf-atlas --profile admin
  # All maintainer features + channel-wide N (no PHASE_N_MAINTAINER),
  # D universe upsert on weekly cadence, full L

pixi run -e local-recipes build-cf-atlas --profile consumer
  # Air-gap friendly: F via s3-parquet, H via cf-graph cold-start,
  # no N, no D universe upsert, no K (or K skipped if no GitHub auth)

pixi run -e local-recipes build-cf-atlas  # no flag = default (today's behavior)
```

Profile resolution lives in `bootstrap_data.py` (the orchestrator
entry point); each profile is a dict of env-var defaults that gets
merged into `os.environ` before invoking the phase dispatcher:

```python
PROFILES = {
    "maintainer": {
        "PHASE_E_DISABLED": "",        # opt-out (default-on)
        "PHASE_N_ENABLED": "1",
        "PHASE_F_SOURCE": "auto",
        "PHASE_H_SOURCE": "auto",
        # PHASE_N_MAINTAINER set dynamically from `gh api user`
    },
    "admin": { ... },
    "consumer": {
        "PHASE_E_DISABLED": "",
        "PHASE_N_ENABLED": "",          # opt-in stays opt-in
        "PHASE_F_SOURCE": "s3-parquet",
        "PHASE_H_SOURCE": "cf-graph",
        "PHASE_D_UNIVERSE_DISABLED": "1",
    },
}
```

The auto-derivation of `PHASE_N_MAINTAINER` for `--profile maintainer`:

```python
import subprocess
def _auto_detect_gh_user():
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None
```

If `gh` is unavailable or unauth'd, `--profile maintainer` prints a
warning and proceeds with channel-wide N (which is slower but
correct).

#### Default behavior change (the MAJOR-bump trigger)

`pixi run -e local-recipes build-cf-atlas` (no `--profile`) keeps
today's silent-skip behavior — backward-compat for cron jobs that
pin env vars manually. But the **documented default** in
`atlas-operations.md` flips to `--profile maintainer`. New
quickstart documentation tells users to use the profile.

To make this a true MAJOR signal: `build-cf-atlas` with no `--profile`
prints an end-of-run advisory:

> ⓘ No --profile specified. Consider `--profile maintainer` for the
> default maintainer-scoped atlas (enables Phase E + Phase N + auto-
> scoping). See `atlas-operations.md` for the full profile reference.

The advisory is opt-out via `BUILD_CF_ATLAS_QUIET=1`.

---

## Stories — 4 waves, ~22 stories

### Wave A — `v_actionable_packages` view + structural enforcement (A5, ~7 stories)

| ID | Story | Effort |
|---|---|---|
| **S1** | Add `v_actionable_packages` view to SCHEMA_DDL; bump SCHEMA_VERSION 20 → 21 | XS |
| **S2** | Refactor `_phase_f_eligible_rows`: `FROM v_actionable_packages` + drop verbose triplet | XS |
| **S3** | Refactor Phase G + Phase G' eligible-rows selectors to the view | S |
| **S4** | Refactor `_phase_h_eligible_pypi_names` to the view (keep `pypi_name IS NOT NULL`) | XS |
| **S5** | Refactor Phase K + Phase L eligible-rows selectors to the view | S |
| **S6** | Refactor Phase N's `base_select` to the view | XS |
| **S7** | New `tests/meta/test_actionable_scope.py`: assert every `SELECT ... FROM packages WHERE ...` either uses the view OR has `# scope: ...` comment | M |

### Wave B — Phase H serial-gate (A3, ~5 stories)

| ID | Story | Effort |
|---|---|---|
| **S8** | Schema v21: add `pypi_version_serial_at_fetch INTEGER` column + index | XS |
| **S9** | Phase H's pypi-json successful-fetch path writes `pypi_version_serial_at_fetch` alongside `pypi_version_fetched_at` | S |
| **S10** | Phase H eligible-rows gate becomes serial-aware (3-condition OR: never fetched / serial moved / 30d safety re-check) | S |
| **S11** | Phase H stat reporting: split `eligible` count into `eligible_never_fetched`, `eligible_serial_moved`, `eligible_safety_recheck` so operators can see why each row was selected | XS |
| **S12** | New `tests/unit/test_phase_h_serial_gate.py`: fixture with mixed serial states; assert only-moved rows are queued; assert safety re-check fires past 30d | M |

### Wave C — Drop `vuln_total` (A6, ~2 stories)

| ID | Story | Effort |
|---|---|---|
| **S13** | Schema v21 migration: `ALTER TABLE packages DROP COLUMN vuln_total`; remove `vuln_total` from Phase G's UPDATE statements; remove from `init_schema` ALTER-table list | XS |
| **S14** | Test: `tests/unit/test_schema_v21_migration.py` covers the column drop + idempotency (re-run = no-op) | XS |

### Wave D — Persona profiles (A4, ~8 stories)

| ID | Story | Effort |
|---|---|---|
| **S15** | `bootstrap_data.py`: define `PROFILES` dict (maintainer/admin/consumer) + `--profile` argparse flag + profile resolution that merges into env before phase dispatch | M |
| **S16** | `_auto_detect_gh_user()` helper: shells out to `gh api user --jq .login`; handles missing-gh / unauth / timeout gracefully; sets `PHASE_N_MAINTAINER` for `--profile maintainer` when available | S |
| **S17** | `_auto_detect_phase_l_sources()` helper: queries `v_actionable_packages` for which `<source>_name` columns are populated in scope; restricts `PHASE_L_SOURCES` accordingly for `--profile maintainer` | S |
| **S18** | End-of-run advisory print when no `--profile` is specified; opt-out via `BUILD_CF_ATLAS_QUIET=1` | XS |
| **S19** | Tests: `tests/unit/test_persona_profiles.py` exercises (a) profile resolution merges env correctly; (b) `--profile maintainer` enables E + N; (c) `--profile consumer` sets s3-parquet + cf-graph; (d) `--profile admin` runs channel-wide N; (e) `--profile maintainer` without `gh` prints warning + proceeds | M |
| **S20** | Update `reference/atlas-phases-overview.md`: each phase section gains a "Profile defaults" line indicating which profiles enable/disable it; new `## Profile Reference` appendix with the three profile bundles | S |
| **S21** | Update `reference/atlas-actionable-intelligence.md`: flip 5 📋-open Phase-N-gated rows to ✅ shipped (gh-pulls, gh-issues, ci-red filter, abandonment composite, maintainer last-active); update `## Status Summary` counts | S |
| **S22** | Update `guides/atlas-operations.md`: quickstart section documents `--profile maintainer` as the recommended default; cron snippet examples use profiles instead of raw env vars; troubleshooting "Phase N skipped" tip removed (auto-detect handles it) | S |

### Closeout

| ID | Story | Effort |
|---|---|---|
| **S23** | CHANGELOG.md v8.0.0 entry covering all 4 sub-specs + the MAJOR-bump rationale + the 5 catalog rows that flipped + the schema v20→v21 migration notes | M |
| **S24** | `config/skill-config.yaml` bump 7.9.0 → 8.0.0; SKILL.md "Atlas Intelligence Layer (v8.0.0)" heading; INDEX.md picks up new `--profile` quickstart | XS |
| **S25** | CFE retrospective per `CLAUDE.md` Rule 2: invoke `bmad-retrospective`; land findings | M |
| **S26** | `bmad-correct-course` for BMAD planning artifact sync: PRD (v1.1.1 → v1.2.0 — minor since this is a feature-level shift, or v2.0.0 if the PRD's MVP language changes substantively); architecture-cf-atlas + architecture-conda-forge-expert + epics + project-parts.json + sprint-change-proposal-YYYY-MM-DD; pin-only bumps across the rest | L |

### Wave sequencing rationale

Waves A → B → C → D is the dependency-respecting order:

- **A first**: the view + meta-test land before any new selector work
  so subsequent waves inherit the enforcement. Wave A is also
  zero-behavior-change (same rows returned, just via a view).
- **B second**: serial-gate refactors Phase H's selector — uses the
  view from A. Validates that the view-based refactor works under
  real selector changes.
- **C third**: small column drop; shares the v21 migration with A and
  B so all three schema changes apply in one `init_schema` pass.
- **D last**: profiles depend on the structural cleanup landing first
  so the new profile-aware defaults inherit the enforced filters.
  Also the most UX-facing wave; lands after the internal refactors
  prove stable.

**Two-PR vs one-PR strategy:** Waves A-C are tightly coupled (one
schema v21 migration). Wave D is independent (no schema change). Two
PRs is the cleaner review surface: PR #1 = A+B+C (structural +
performance + cleanup), PR #2 = D (UX). Both land before the v8.0.0
release tag.

---

## Acceptance Tests

For each wave, the BMAD agent runs the existing pytest suite plus
explicit new tests:

### Wave A
- `tests/unit/test_v_actionable_packages_view.py::test_view_returns_canonical_subset`
  — fixture with mixed conda-linked/pypi-only/archived/inactive rows;
  assert the view returns only conda-linked + active + !archived.
- `tests/unit/test_v_actionable_packages_view.py::test_refactored_selectors_match_old_results`
  — run the 6 refactored selectors against a v20-snapshot fixture +
  the equivalent post-v21 selectors; assert identical row sets.
- `tests/meta/test_actionable_scope.py::test_packages_selectors_use_view_or_justify`
  — parse `conda_forge_atlas.py`; every `SELECT ... FROM packages WHERE
  ...` either uses the view OR has a `# scope:` comment within 3 lines
  above. Fails if a future commit reintroduces drift.

### Wave B
- `tests/unit/test_phase_h_serial_gate.py::test_skips_unchanged_rows`
  — fixture with `pypi_last_serial == pypi_version_serial_at_fetch`;
  assert row is NOT eligible.
- `tests/unit/test_phase_h_serial_gate.py::test_includes_moved_rows`
  — fixture where `pypi_last_serial != pypi_version_serial_at_fetch`;
  assert row IS eligible.
- `tests/unit/test_phase_h_serial_gate.py::test_safety_recheck_past_30d`
  — fixture with `pypi_version_fetched_at` > 30d ago AND
  serial-unchanged; assert row IS eligible (safety re-check).
- `tests/unit/test_phase_h_serial_gate.py::test_never_fetched`
  — fixture with `pypi_version_fetched_at IS NULL`; assert eligible.
- `tests/unit/test_phase_h_serial_gate.py::test_successful_fetch_writes_serial`
  — call `_phase_h_via_pypi_json` against a mock fetcher; assert
  `pypi_version_serial_at_fetch` is populated post-fetch.

### Wave C
- `tests/unit/test_schema_v21_migration.py::test_drops_vuln_total_column`
  — start with v20 fixture DB containing `vuln_total` populated; run
  `init_schema`; assert column is gone from `packages`.
- `tests/unit/test_schema_v21_migration.py::test_migration_is_idempotent`
  — run `init_schema` twice; second run is a no-op.

### Wave D
- `tests/unit/test_persona_profiles.py::test_profile_maintainer_enables_e_and_n`
  — `--profile maintainer` sets `PHASE_E_DISABLED=""` and
  `PHASE_N_ENABLED=1`.
- `tests/unit/test_persona_profiles.py::test_profile_maintainer_auto_scopes_n`
  — mock `gh api user` to return "rxm7706"; assert
  `PHASE_N_MAINTAINER=rxm7706`.
- `tests/unit/test_persona_profiles.py::test_profile_maintainer_without_gh_warns_and_proceeds`
  — mock `gh` as unavailable; assert warning printed + N runs
  channel-wide.
- `tests/unit/test_persona_profiles.py::test_profile_consumer_sets_air_gap_sources`
  — assert `PHASE_F_SOURCE=s3-parquet`, `PHASE_H_SOURCE=cf-graph`,
  `PHASE_D_UNIVERSE_DISABLED=1`.
- `tests/unit/test_persona_profiles.py::test_profile_admin_runs_channel_wide_n`
  — assert no `PHASE_N_MAINTAINER` is set.
- `tests/unit/test_persona_profiles.py::test_no_profile_prints_advisory_unless_quiet`
  — run without `--profile`; assert advisory printed. Run with
  `BUILD_CF_ATLAS_QUIET=1`; assert silent.

### Cross-cutting
- Full atlas rebuild against the real connection (deferred to the next
  session if the MCP server holds the lock — same pattern as v7.9.0)
  produces a `cf_atlas.db` at schema v21 with no `vuln_total` column,
  `v_actionable_packages` view present, and Phase H eligible-rows
  drops sharply on the second run when only a few serials moved.

---

## Risks

| Risk | Mitigation |
|---|---|
| SQLite `ALTER TABLE DROP COLUMN` requires SQLite ≥ 3.35.0; older Debian/RHEL distros ship older SQLite | conda-forge ships SQLite 3.46+; the `pixi run -e local-recipes` env always satisfies this. Direct DROP COLUMN works. Fallback table-rebuild pattern documented in `_bmad-output/projects/local-recipes/planning-artifacts/architecture-cf-atlas.md` if needed for downstream copies. |
| Phase H serial-gate edge case: `pypi_last_serial` is NULL on a never-Phase-D-run atlas | Gate handles: `pypi_last_serial IS NULL` short-circuits to "needs fetch" via the existing `pypi_version_fetched_at IS NULL` clause and the 30d safety re-check. Tested fixture covers. |
| `gh api user` auth fails mid-run for `--profile maintainer` | Detected at profile-resolution time (start of run, not mid-phase); warning printed; `PHASE_N_MAINTAINER` left unset (runs channel-wide, slower but correct). |
| Operator's cron job pins env vars manually + uses `--profile` (conflict) | Profile resolution merges *defaults*; explicitly-set env vars win (the `os.environ.get(key, profile_default)` pattern). Operators with custom env keep their behavior. |
| Meta-test test_actionable_scope flags a legitimate `SELECT ... FROM packages` (e.g., admin candidate-list queries) | Justification mechanism: a `# scope: <reason>` comment within 3 lines above the SELECT marks it as deliberate. Meta-test parses and accepts. |
| MAJOR bump confuses cron-based downstream consumers | CHANGELOG MIGRATION_NOTES section explicitly lists the only behavior change: documented default flipped to `--profile maintainer`. No invocation breaks; the silent-skip behavior remains available via no-flag invocation. |
| 22 stories across 4 waves exceeds quick-dev token budget gates | Same pattern as v7.9.0: user explicit K (keep all) at the token gate; commit checkpoints at end of each wave so a context-rot mid-stream can resume from the last green wave. |

---

## Rollout

### Pre-merge
- Two-PR strategy: PR #1 lands waves A + B + C (one schema v21
  migration); PR #2 lands wave D (independent).
- BMAD agent executes waves in order; each wave's tests pass before
  the next starts.
- Manual smoke run on the dev `cf_atlas.db` after each wave to confirm
  expected behavior changes (Phase H eligible count drops on warm
  daily run; `--profile maintainer` populates E + N; etc.).
- CFE skill version bumps per semver: 7.9.0 → **8.0.0** (MAJOR — A4's
  documented-default change).

### Merge order
- PR #1 first: lands the schema migration + structural enforcement +
  serial-gate + column drop. Allows ~1-2 days of soak before PR #2.
- PR #2: lands persona profiles + 5 catalog row flips.
- Both PRs merged before v8.0.0 release tag.

### Post-merge
- `CHANGELOG.md` v8.0.0 entry summarizing the four sub-specs + the
  MAJOR-bump rationale + the explicit list of catalog rows that
  flipped from 📋 to ✅.
- `MIGRATION_NOTES` in CHANGELOG flagging:
  - Schema v20 → v21 (existing atlases auto-migrate on next open).
  - `packages.vuln_total` dropped (use the severity-banded counts).
  - Default-behavior signal: documented `build-cf-atlas` default
    flipped to `--profile maintainer`. No invocation breaks.
- Skill files updated per Rule 2 retro: `SKILL.md` § Atlas
  Intelligence Layer mentions profile defaults; `INDEX.md` gains
  quickstart with `--profile maintainer`; `atlas-operations.md`
  rewritten quickstart + cron snippets.
- Auto-memory feedback entry: only if a cross-skill finding surfaces
  (e.g., BMAD's quick-dev workflow needs the new profile-aware default
  documented as a CFE invariant). Most findings stay in skill files.

### Backout plan
- Schema v21 migration is reversible by hand (re-create the dropped
  column + restore via SQL). The more practical backout: revert the
  PR(s), then on next `init_schema` the v21 block is a no-op (column
  already dropped) and the view stays but isn't read by anything in
  the reverted code. Operators can `DROP VIEW v_actionable_packages`
  manually if they prefer a clean rollback.
- Wave D rollback (persona profiles): the `--profile` flag is additive;
  reverting removes the flag with no schema impact. Cron jobs that
  pinned env vars continue to work.

---

## Open Questions

1. **Should the v8.0.0 default `build-cf-atlas` invocation switch from
   no-profile (current silent-skip) to `--profile maintainer`?** This
   spec proposes "no flag keeps today's behavior + advisory print"
   rather than "no flag = maintainer profile" because true
   default-flip would silently break cron jobs. The documentation
   recommends `--profile maintainer`. **Defer until operator feedback
   on the advisory print: if no one notices the advisory, escalate to
   silent default-flip in v8.1.0.**
2. **Should `--profile maintainer` auto-derive `PHASE_N_MAINTAINER`
   from `gh api user` or require an explicit flag?** This spec proposes
   auto-derive. Edge case: a power-user with multiple GitHub identities
   may not want auto-detection — they can override via explicit
   `PHASE_N_MAINTAINER=<other-handle>`.
3. **Should `--profile admin` warn about missing multi-PAT rotation?**
   This spec proposes yes (admin-scope Phase N benefits from rotation
   to avoid secondary rate limits). Operators without rotation see
   warning + degraded mode.
4. **Should the meta-test apply to other files beyond
   `conda_forge_atlas.py`?** Phases write inside the atlas script;
   other scripts (`staleness_report.py`, etc.) read from the DB but
   don't have "phase selector" semantics. **Scope: atlas script only.**
5. **Does the PRD need a v1.x → v2.0.0 bump or stay at v1.x with a
   minor-bump?** The v8.0.0 skill version reflects a behavior shift;
   the PRD's stated requirements don't change (still "operator runs
   build-cf-atlas; gets an actionable atlas"). Recommend PRD MINOR
   bump (v1.2.0); no breaking PRD-level change.

---

## References

### Source-of-truth code (current state — v7.9.0 baseline)

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`:
  - `SCHEMA_VERSION` (line 135) — bump to 21
  - SCHEMA_DDL block (~line 270) — add view
  - `init_schema` migration block (~line 489) — add v21 sub-block (3 changes: view + column + drop)
  - `_phase_f_eligible_rows` (line 1696)
  - Phase G eligible-rows (~line 2243)
  - Phase G' eligible-rows (~line 4724)
  - `_phase_h_eligible_pypi_names` (line 2509)
  - Phase K eligible-rows (~line 3209)
  - Phase L eligible-rows (~line 3805)
  - Phase N eligible-rows (~line 4456)
- `.claude/skills/conda-forge-expert/scripts/bootstrap_data.py` — primary
  edit surface for Wave D (`--profile` flag + PROFILES dict + auto-detect)
- `.claude/skills/conda-forge-expert/scripts/atlas_phase.py` — `_reset_ttl`
  helper may need a `pypi_version_serial_at_fetch` reset target for
  Wave B (mirror existing `pypi_version_fetched_at` reset pattern)

### Related specs

- `docs/specs/atlas-pypi-universe-split.md` — predecessor (v7.9.0).
  This v8.0.0 spec implements 4 deferred follow-ups from that effort.
- `docs/specs/atlas-phase-f-s3-backend.md` — sibling spec; Phase F
  air-gap backend already shipped (v7.6.0). No conflicts.

### Audit context

- `_bmad-output/projects/local-recipes/implementation-artifacts/retro-atlas-pypi-universe-split-2026-05-13.md`
  — action items A3 / A4 / A5 / A6 each map to one wave in this spec.
- `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md`
  — five 📋-open rows that flip to ✅ in Wave D.
- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`
  — per-phase data source / purpose / actionable intelligence (added
  v7.9.0); Wave D extends with "Profile defaults" lines.
- `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md`
  — engineering rule book; unchanged by this spec.

### Documentation

- `.claude/skills/conda-forge-expert/SKILL.md` — Atlas Intelligence
  Layer + Critical Constraints; v8.0.0 heading update.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — v8.0.0 entry per
  Rule 2 + MIGRATION_NOTES.
- `.claude/skills/conda-forge-expert/guides/atlas-operations.md` —
  quickstart + cron snippets rewritten for `--profile`.
- `CLAUDE.md` — add `docs/specs/conda-forge-expert-v8.0.md` to the
  BMAD-consumable spec list.
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` —
  `--profile` usage examples.
