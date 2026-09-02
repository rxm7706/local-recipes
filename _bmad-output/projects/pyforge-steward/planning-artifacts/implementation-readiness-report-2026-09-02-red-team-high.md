# Steward — red-team HIGH set readiness (2026-09-02)

Gate of `spec-pyforge-unifying-strategy` Epics 41–43 after the second
2026-09-02 correct-course bound review directives R-3 … R-16 as fourteen
stories and R-17 … R-25 as deferred-work entries.

**Question:** could a developer implement each story without inventing
decisions?

**Verdict: READY — proceed. (Amended 2026-09-02: the 43.5 interpreter decision landed as
hybrid (a)+(c); 43.6 added, gated on Mason 13.1 / 13.2.)**

## Concerns (do not invent; do not block the rest)

| Concern | Where | Why it does not block |
|---|---|---|
| 43.5 decided (hybrid a+c). 43.6 (image flip) must not dispatch before Mason 13.1 / 13.2 are `done` | `spec-43-6` `Deps` | Order is stated; 43.5 itself has no deps |
| 42.x assume Epic 40 shipped (verified mint root; bounded broker) | `Deps` lines | Order 40 → 42 is stated; do not dispatch 42.x on a red 40 |
| 41.1 backup destination defaults to RWX PVC; object store is a profile plugin | `spec-41-1` | RWX exists already for media (AD-13); object store stays optional |
| 42.4 changes queue names; any Celery caller with a hard-coded queue breaks | `spec-42-4` | Routing table lives in chrome; grep for `queue=` is a task |
| 43.2 moves Langflow off bare `/api/v1` | `spec-43-2` | `/langflow/api/v1/` already works; the prefix-preserving redirect test exists |
| ~~`chain-completeness` CAP-6~~ | detectors | **Fixed 2026-09-02.** It was a real chain gap, not a detector bug: `spec-bmad-suite-channel-product` CAP-6 (added 2026-09-01) pointed at `spec-bmad-suite-metapackage`, but Epic 39 never cited the channel-product slug, so the slug-scoped window saw no CAP-6. Epic 39's blurb now cites it; the check is green. The steward layers-audit staleness checkpoint was a feeds-currency cascade (spec touched 2026-09-01 by the 23-1 sharded-path landing → PRD re-stamped 2026-09-02 → architecture spine re-stamped 2026-09-02, no FR or AD change); both `chain-completeness` and `chain-completeness --layers --project pyforge-steward` are green as of this commit |
| ~~Fourteen drafts carry no operator approval yet~~ | SCP § 2 item 6.3 | **Approved 2026-09-02** (Epics 40–43 + Mason 13). Dev sessions on the web: start with `PYFORGE_SESSION_ENVS="pyforge-doctor python-agent-platform"` (add `platform-dev` for chart/helm stories) so platform tests can run |

## Trace

| Intent | Story |
|---|---|
| R-3 DR contract + backup | 41.1 |
| R-11 plane process boundary | 41.2 |
| R-12 Scribe DDL governed | 41.3 |
| R-14 broker TLS verified | 41.4 |
| R-7 MCP transport auth + streaming proxy | 42.1 |
| R-8 rate limits + run bounds | 42.2 |
| R-9 bus delivery semantics + consumer | 42.3 |
| R-10 Celery hardening + builds pool | 42.4 |
| R-13 role namespaces + tenant | 42.5 |
| R-4 split the Dream | 43.1 |
| R-5 station API contract | 43.2 |
| R-6 in-process port | 43.3 |
| R-15 CD by digest | 43.4 |
| R-16 one interpreter story | 43.5 (decision) + 43.6 (flip) + mason 13.1 / 13.2 (pins) |
| R-17 … R-25 | `DW-RT-2026-09-02-1..9` |

## Dispatch order

1. Epic 40 (40.1 then 40.2) — from the first correct-course.
2. Epic 41: 41.1, 41.2, 41.3, 41.4 in parallel.
3. Epic 42: 42.1, 42.2, 42.3, 42.4, 42.5 in parallel after 40 is `done`.
4. Epic 43: 43.1, 43.2, 43.4, 43.5 in parallel; 43.3 after 43.2; 43.6 after Mason 13.1 / 13.2 (dispatch those in `pyforge-mason` any time, in parallel with Epic 41).

`BMAD_ACTIVE_PROJECT=pyforge-steward`. Physical paths only. Cutover Phase 1
waits for all four epics.

## Housekeeping 2026-09-02 (operator-directed, fleet-wide)

| Item | State | Detail |
|---|---|---|
| `chain-completeness` CAP-6 | **closed** | `spec-bmad-suite-channel-product` CAP-6 now cited from Epic 39. Green. |
| steward layers-audit staleness | **closed** | PRD and architecture spine re-stamped after the 23-1 sharded-path landing; no FR/AD change. Green. |
| deferred-work verification coverage | **closed** | Every tracked entry in all eight ledgers carries `verified: 2026-09-02` (mechanical re-verification at HEAD `933039db67`: source_spec presence, cited paths present/absent, status→verdict). 100 % in every project. The line says agent judgment was not applied; a semantic re-read is still owed per entry where the claim is semantic — Doctor's `due-for-verification` will surface those again in 30 days. |
| `deferred-work` Tier-3 twins | **closed** | `scripts/deferred_work_intake.py --fix` ingested 11 marshal spec-frontmatter deferrals (`DW-FU-28-18..28-20`). Green. |
| `bmad-recipe-upstream-drift` ×3 (`bmad-builder` 2.2.1→2.2.2, `bmad-creative-intelligence-suite` 0.3.1→0.3.2, `bmad-method-test-architecture-enterprise` 1.23.2→1.24.0) | **needs your machine** | Tags `v2.2.2` / `v0.3.2` / `v1.24.0` confirmed via `git ls-remote`; the release tarballs (`github.com/.../archive`, `codeload.github.com`) return 403 through this session's proxy, so no `sha256` can be computed here and a recipe with a guessed checksum would not build. Run the CAP-2 chain per package: `pyforge steward suite advance --package bmad-builder` (then `bmad-creative-intelligence-suite`, `bmad-method-test-architecture-enterprise`); `--dry-run` first. Rule 1 applies (conda-forge-expert). |
| `bmad-suite-upstream-drift` ×3 (installed behind) | **needs your machine** | Follows from the three advances above: build → publish to SelfExplainML (needs the anaconda token, not present here) → bump the `pixi.toml` floors → `pixi lock` → regenerate `environment.yaml`. `bmad-channel-drift` will fire between recipe bump and publish; that is expected. |
| MRS-GATE-012 scope-violation advisories (atlas ×1, steward ×2) | **needs your machine** | These are warn-mode advisories read from live-run journals under `~/.bmad-loops` via `marshal status --format json` (key `dispatch_verification_scope_advisories`); no journal exists in this clone. Marshal `DW-FU-DISP-2026-09-01-2` already records the warn-mode widen as interim. Inspect with `pixi run -e local-recipes fleet-picture`, then either widen the station's `policy_surface` (marshal-policy.toml) for the named paths or move the offending files; the advisory clears on the next run. |
