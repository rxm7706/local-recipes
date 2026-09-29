---
title: '30.1: The map is enforced within its scope, the stubs are gone, and the new pages are true'
type: 'feature'
created: '2026-09-19'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md', '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/research/documentation-currency-and-repeatable-refresh-2026-09-19.md']
deferred:
  - summary: "`docs/how-to/github-actions-recipe-ci.md` (pre-existing, not one of the 14) claims '19 workflow files' — never re-counted; the count belongs to a generated page (Story 30.3's detector/workflow table) rather than prose."
    evidence: "Implementer sweep 2026-09-19 over every backticked path and pixi task in the 15 corrected pages found no other unverified claim; this count sits outside the story's pages."
    location: docs/how-to/github-actions-recipe-ci.md
    severity: low
  - summary: "`docs/explanation/pyforge-estate-overview.md` uses Docusaurus-style `:::note` admonitions that GitHub does not render; left as authored (style, not fact) — a `docs-currency` style rule or the `bmad-os-diataxis` style guide should decide one admonition syntax for `docs/`."
    evidence: "GitHub renders `> [!NOTE]`; `:::note` shows as literal text."
    location: docs/explanation/pyforge-estate-overview.md
    severity: low
  - summary: "The unmapped-page class is `warn` (CAP-62 posture); nothing blocks a PR that adds a quadrant page without a MAP row until Story 30.2 promotes the class to `fail` once the registry exists."
    evidence: "docs_map_hygiene.py `unmapped` → DoctorStatus.WARN by design of CAP-83."
    location: src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_map_hygiene.py
    severity: low
declared_low_risk: false
baseline_revision: 'b49ccf497b43ef0309788c9818f1208075593845'
final_revision: 'f4d693ffe8b3fa2195ea2d39c13dcc9a2765c299'
---

<intent-contract>

## Intent

**Problem:** PR #1529 (a parallel session) tried to make documentation drift impossible and shipped the opposite: a
Doctor source that scans everything `docs/MAP.md` itself excludes (44 findings on `main`, "Always FAIL", no test), 130
identical `README.md` stubs inside installer-managed skill directories, 14 authored pages with dead paths, a non-existent
CLI grammar and a false claim about the ledgers, ten Spec baselines re-stamped on content-free memlog lines, and a
hand-written Spec whose CAP-82 / Epic 29 collided with #1526's.

**Approach:** keep the intent, rebuild the mechanism against the map's own contract: the source is scoped to the four
Diátaxis quadrants (missing link = fail, unmapped page = warn, index pages exempt) with a unit test per branch; the 130
stubs are removed; every page is corrected against the tree and carries `sources:` / `verified:`; the genuine map gaps
are mapped; the chain is minted properly (Dream entry → CAP-83/84 → Epic 30 → this spec → capability-ledger rows) with
real memlog entries and scoped stamps only for the Specs the diff touches.

## Boundaries & Constraints

**Always:** the detector's scope is exactly MAP.md § *Outside this map*'s complement; docs detectors start warn (CAP-62);
every backticked path, pixi task and CLI grammar in a corrected page resolves on the tree; skill directories hold only the
Agent Skills layout.
**Never:** a relative link inside a station README (they ship in wheels); a hand-appended memlog line with no path; a
baseline stamp for a Spec the diff did not touch; counts typed from memory.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| `python -m pyforge.doctor.sources docs-map-hygiene` on `main` | one `ok` finding (`mapped_count`, `page_count`), exit 0 |
| a new `docs/how-to/x.md` with no MAP row | one `warn` naming it |
| a MAP link to a page that was deleted | one `fail` naming the dead link |
| `docs/how-to/README.md` (quadrant index) | exempt; `docs/reference/<subdir>/README.md` counts |
| a page under `docs/governance/`, `docs/intake/`, `docs/foundry/`, `docs/dashboard/` | never scanned |
| a MAP link with `../` escaping `docs/`, or `http(s)://` | ignored |
| `docs/MAP.md` missing | `fail`; an unreadable tree degrades to `warn` (never a false green) |

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_map_hygiene.py` — rewritten (four quadrants; `missing` fail / `unmapped` warn; index exemption; link normalisation; `degrade_on_exception`); `models.py` (`Source.DOCS_MAP_HYGIENE`), `sources/__init__.py` (registration `scope=repo`, `subject_station=fleet`, `owning_station=doctor`), `sources/__main__.py`, `data/report-schema.json` (source enum).
- `tests/unit/test_sources_docs_map_hygiene.py` (new, 11 tests, 100 % of the module); `tests/unit/test_models.py`, `tests/unit/test_sources_dispatch.py`, `tests/meta/test_source_independence.py` (the closed taxonomy learned the new source — the PR had left the suite red on five tests); `tests/unit/test_sources_capability_effect_caller_reach.py` (+3 tests: the touched-module prefix expanded to the whole package and surfaced `capability_effect` at 79.6 %, the CLAUDE.md coverage trap — now 91 %).
- `scripts/detectors.py` (`docs-map-hygiene` ↔ `docs-map-hygiene-check`), `pixi.toml` `[feature.guild-tasks.tasks.docs-map-hygiene-check]`.
- `docs/MAP.md` — nine genuine gaps mapped (`how-to/{recipe-testing-and-builds,troubleshooting-recipe-builds,pixi-tasks,github-actions-recipe-ci,detect-concurrent-agent-activity}.md`, three `reference/` redirect stubs, the sync-jira templates README), `docs/foundry/` added to *Outside this map*.
- The 14 pages + `docs/how-to/pixi-tasks.md` — corrected (see Review Triage Log) with `sources:` / `verified: 2026-09-19` frontmatter.
- `.claude/skills/*/README.md` ×130 — removed. Ten station READMEs — one plain-text pointer line, no relative link. `.steward/keys-inventory.yaml` — runbook pointer repointed to `docs/how-to/ocp-cluster-bringup.md`.
- Chain: `docs/dreams/pyforge-doctor.md` (2026-09-19 night entry replaces the PR's stub), `specs/spec-pyforge-doctor/{.memlog.md,SPEC.md}` (CAP-83, CAP-84, constraint), `research/documentation-currency-and-repeatable-refresh-2026-09-19.md`, `epics.md` (Epic 30), `sprint-status-ledger.yaml`, `specs/spec-30-2-*.md`, `specs/spec-30-3-*.md` (pre-authored, policy-bound Verification), `docs/foundry/capability-ledger.yaml` (CAP-83/84 rows); the PR's `specs/spec-29-1-check-docs-map.md` sketch removed.

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-83`.
Surface: as in the Code Map.
Ledger key: `30-1-the-map-is-enforced-within-its-scope-the-stubs-are-gone-and-the-new-pages-are-true`.
Ledger status: `done` (set at the review of PR #1529).
Minted 2026-09-19 (night) at the review of PR #1529: the parallel session's PR carried a Spec sketch, a colliding key and no story spec. This spec is the record the story should have carried from the start.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-doctor CAP-83
**Given** the PR's check reds on 44 files on `main`, the pages cite paths and grammars that do not exist, and 130 stubs sit inside installer-managed skill directories
**When** this story lands
**Then** `docs-map-hygiene` reports OK on `main`, warns on an unmapped quadrant page and fails on a dead MAP link (each unit-tested); every backticked path, pixi task and CLI grammar in the 14 pages resolves; no README stub sits inside `.claude/skills/*/`; `pyforge-doctor-test` and the doctor coverage gate are green
**Status:** done

</intent-contract>

## Spec Change Log

- 2026-09-19 — minted at review. The PR's mechanism ("scan all of `docs/` and `src/platform/`, always fail") replaced by the map's own scope with warn-first for the unmapped class; the PR's CAP-82 / Epic 29 / Story 29.1 re-keyed to CAP-83 / Epic 30 / Story 30.1.

## Review Triage Log

### 2026-09-19 — Review pass (Blind Hunter, Intent Alignment, Current/Future-state over PR #1529 as opened; research doc; implementer remediation)

- intent_gap: 2
- bad_spec: 3
- patch: 12 (high 3, medium 5, low 4)
- defer: 3
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` `docs-map-hygiene` scanned every `.md` under `docs/` and `src/platform/` — 44 unmapped files on the merged tree (memlogs, frames, intake dumps, index pages, platform overlay READMEs) — and was wired as "Always FAIL" into `detectors-ci`, contradicting `docs/MAP.md` § *Outside this map* and CAP-62's warn-first posture; no test. Rescoped to the four quadrants, index pages exempt, `missing` fail / `unmapped` warn, 11 tests at 100 %.
  - `[high]` `[patch]` 130 identical five-line `README.md` stubs inside `.claude/skills/*/` — no harness reads them; the BMAD installer regenerates and retires those dirs (71 deletions in the 6.10→6.11 upgrade), the SKF exporter regenerates `pyforge-*`; a stub left in a retired dir is a ghost skill folder. All removed (the three pre-existing `conda-forge-expert/*/README.md` are content, not stubs, and stay).
  - `[high]` `[patch]` Ten Spec baselines re-stamped on hand-appended `(event) Surface reconcile 2026-09-19: updated Diátaxis docs and package READMEs` lines naming no path — laundering. Branch re-merged with `main`'s baseline; only the Specs the diff touches are stamped, each after a real entry naming every path.
  - `[medium]` `[patch]` `monitor-the-fleet.md`: "fleet-picture reads the Tier-3 sprint ledgers" → the tracked twins; `python scripts/fleet_scan.py` (its `main()` is retired, exits 2) → `marshal status` / `watch`; `fleet-poll-hourly.sh` described as a stall alerter → what it does (a :30 tick writing a Cursor prompt).
  - `[medium]` `[patch]` `station-cheat-sheet.md` typed from memory: `pyforge marshal dispatch`, `pyforge doctor verify-invariants`, herald `report`/`broadcast`, mason `build`/`lint`, warden `audit` — none exist; every verb replaced from each CLI's `--help`; dead paths (`src/pyforge/<station>/dashboard/`, `…/data/report-schema.json`, a `conformance/` tests dir) corrected to the tree.
  - `[medium]` `[patch]` `the-tier-model-and-data-flow.md`: BMAD expanded as "Build, Measure, Analyze, Dream", an invented "v6.8.0 human specs obsolete" ruling, "agents strictly prohibited from mutating Dreams" — replaced with the Dream-append-first convention, the real sunset rule (Story 23.3) and the Tier-3 feed / symlinks / `tracked-impl-artifact` facts.
  - `[medium]` `[patch]` `ai-engine-operations.md` told the reader to run `pixi project export conda-environment -e python-agent-platform > environment.yaml` — it would clobber the repo's `build`-env `environment.yaml` that CI checks; removed, replaced by the Containerfile build the file's own header prescribes.
  - `[medium]` `[patch]` `local-platform-development.md`: `manage.py createsuperuser` (identity is OIDC-delegated; no such path), Wagtail at `/admin` (it is `/cms/`), a `src/platform/dashboard/models.py` that does not exist, "ensure PostgreSQL via Docker" (platform-dev ships it) — corrected to `src/platform/README.md`'s own procedure.
  - `[low]` `[patch]` `pyforge-ecosystem-architecture.md`, `pyforge-estate-overview.md`, `the-detector-framework.md`, `run-and-understand-detectors.md`, `reconcile-spec-surface.md`, `manage-worktrees-with-bmad.md`, `troubleshoot-bmad-agent-loops.md`, `station-cli-operations.md`, `agent-memory-lifecycle.md`: environment defaults (`pyforge-guild`, not `-e pyforge-steward` / `local-recipes`), Marshal's role and grammar, Doctor "CI gatekeeper" → advisory, the two exit-code domains, `bmad-switch` marker + symlinks, the memlog-vs-journal-vs-team-memory split, `worktree_sweep.py` dry-run default, an invented spec-surface finding text replaced by the real one.
  - `[low]` `[patch]` `docs/how-to/pixi-tasks.md` (pre-existing) called `local-recipes` "the" environment and listed station test tasks as if they ran there — corrected with an Environment column.
  - `[low]` `[patch]` Ten station READMEs gained a `[!NOTE]` with `../../../../docs/MAP.md` — dead inside the wheel each README ships in; replaced by one plain-text line.
  - `[low]` `[patch]` `.steward/keys-inventory.yaml` still cited `src/platform/deploy/overlays/ocp/cluster-bringup.md §5` after the move; repointed. (Steward DW rows and epics citing the old paths are historical and stay.)
  - `[intent_gap]` `[patch]` No `bmad-spec`, a 32-line Spec sketch as the story spec, CAP-82 / Epic 29 / 29.1 colliding with #1526, no capability-ledger row, a source docstring citing `spec-check-docs-map` (no such folder) — the full chain minted (Dream entry, CAP-83/84, Epic 30, this spec, 30.2/30.3 pre-authored, ledger rows, capability-ledger rows).
  - `[intent_gap]` `[patch]` The PR's own suite was red: five doctor tests (closed taxonomy, report schema, dispatch table, source independence) had not learned the new source — fixed; the doctor coverage gate then surfaced `capability_effect` at 79.6 % through the touched-module prefix — three tests added (91 %).
  - `[bad_spec]` `[patch]` "Always FAIL … preventing undocumented drift from ever merging" — CAP-62 set warn-first, fail-open for docs detectors; CAP-83 keeps it and CAP-84 ratchets per check.
  - `[bad_spec]` `[patch]` The Spec sketch named "Diátaxis alignment" without saying what a page derives from or who owns it — that is CAP-84 (`docs/map.yaml`, kinds, sources, stamps), Stories 30.2–30.3.
  - `[bad_spec]` `[patch]` `bmad-os-docs-audit` delegates *all* gaps to an LLM writer — right for authored pages, wrong for reference pages, which Story 30.3 generates; the skill is kept and scoped by the registry.
  - `[defer]` ×3 — see frontmatter `deferred:`.

## Design Notes

- **Why the map's scope is the detector's scope.** `docs/MAP.md` § *Outside this map* is a contract other stories rely on (Dreams, governance, intake, publish roots, station READMEs are deliberately not general documentation). A detector wider than the contract is not stricter — it is wrong, and "always red" is the fastest way to be ignored.
- **Why warn for `unmapped` and fail for `missing`.** A dead link is unambiguous; a new page without a row is a workflow gap that Story 30.2's registry makes structural. CAP-62 fixed this posture on 2026-09-17.
- **Why the READMEs had to go.** The skill tree is installer-owned: 76 `bmad-*` dirs are rewritten on upgrade (whole dirs deleted on retire), 7 `pyforge-*` are exported from the SKF manifest. Anything we add there is either overwritten or orphaned. The only durable human index is a generated page (30.3).
- **Current → future state.** Today: one map, hand-maintained, now enforced within scope; 15 pages carry `sources:`/`verified:` but nothing reads them yet. 30.2: the registry (`docs/map.yaml`), MAP.md rendered, `docs-currency` (stale authored page, dead path/task/grammar, stray skill-dir file), unmapped promoted to fail. 30.3: the reference pages become generated and stamped. End state: a docs change that is wrong or stale reds the PR that made it — refresh is triggered by the finding, not by a campaign.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild docs-map-hygiene-check` → exit 0, one `ok` row; add an unmapped how-to → `warn`; delete a mapped page → `fail`.
- `pixi run -e pyforge-guild pr-preflight` green on the branch (`pixi.toml` changed: all eight stations + core).

## Auto Run Result

- **Summary:** PR #1529 reviewed against the doctor docs chain (CAP-48..65) and rebuilt as Story 30.1: detector rescoped
  and tested, 130 stubs removed, 15 pages corrected against the tree and registered with `sources:`/`verified:`, the
  map's real gaps mapped, station README pointers made wheel-safe, one live pointer repointed, the chain minted
  (CAP-83/84, Epic 30, 30.2/30.3 pre-authored), the laundering re-stamps dropped.
- **Verification (exit codes read directly, 2026-09-19):**
  - `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` → 1805 passed, 1 skipped, exit 0.
  - `test_sources_docs_map_hygiene.py` → 11 passed; module coverage 100 %.
  - `COVERAGE_GATES_STATIONS=doctor CI=1 … coverage_gates_ci.py --suites unit` → gate OK, 25 modules ≥ 80 %.
  - `python -m pyforge.doctor.sources docs-map-hygiene` → exit 0, `ok — docs/MAP.md links every quadrant page and every link resolves`.
  - `governance-currency --file AGENTS.md` → 0; `environment.yaml` unchanged; every backticked path / pixi task / CLI verb in the 15 pages checked against the tree and the CLIs' `--help`.
  - `pr-preflight` — recorded in the PR.
- **Files changed:** see Code Map.
