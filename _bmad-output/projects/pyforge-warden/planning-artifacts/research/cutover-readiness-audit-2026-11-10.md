---
chain: pyforge-warden
created: 2026-11-10
updated: 2026-11-10
status: final
type: audit
title: "Cutover readiness audit 2026-11-10: Warden"
companion: "docs/dreams/pyforge-unifying-strategy.md (Realization log, 2026-11-10 operator rulings)"
---

# Cutover readiness audit, 2026-11-10: Warden

One of nine read-only audits run at main `82a2b18828` for the A→B cutover (rebuild from Frame + Spec,
with A's code and tests as the oracle). The report below is the audit agent's own text, unedited except that a capability id of another project is qualified. Each
finding carries its own VERIFIED or INFERRED label; counts of test functions are static, and no suite
was run. The cross-cutting findings, the main session's spot-checks and the four operator rulings that
followed are in `_bmad-output/projects/pyforge-steward/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md`
§ *Cross-cutting findings* and on the Dream entry named above. Paths under `/tmp` in the report were
scratch and no longer exist.

---

WARDEN — A→B CUTOVER READINESS AUDIT (read-only; nothing run, nothing edited)

Paths relative to /home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes. Shorthand: W = src/shared/packages/pyforge-warden, WS = W/src/pyforge/warden, DW = src/shared/packages/django-warden/src/django_warden_fabric, SP = _bmad-output/projects/pyforge-warden/planning-artifacts, SPEC = SP/specs/spec-pyforge-warden/SPEC.md.

VERDICT: Not rebuild-ready. Spec resolves against the tree (282 backticked tokens; 0 dead paths, tests, flags or env vars) but omits behaviour the code has, states things the code does not do, and the ledger modes contradict the Spec's own dependencies.

MUST REFRESH (blocks cutover)
1. Nine feature flags gate CAP-24/25/26, all default `off`. Spec and companions name none. Rebuild from Spec ships them ungated.
2. Ledger modes contradict the Spec. CAP-26 `rebuild` runs on django-warden's `ComplianceJob` pattern (CAP-16/17 `retire`, note "compliance_face / services stay off B") and on `scripts/platform-provision-osv-offline-db.sh` (CAP-20 `A-only`). CAP-18 `A-only` is kernel code (`--pixi-environment`, `--pixi-platform`). Retire-row code is live in django-warden. CAP-id set diff is empty (26/26); the other 10 rows repeat CAP-13..22 under archived spec ids.
3. Four `(ready)` markers are stale. Stories 13.2, 14.4, 15.2, 16.6–16.10 are `done` and on main (bd154aaa17).
4. Python floor wrong. Spec, PRD NFR-C1 and W/pixi.toml say ≥3.12; pyproject says ≥3.14; 23 `except A, B:` sites need 3.14.
5. Spec states what code lacks: `review_required` (CAP-6) is in no code or schema; the conda→pypi map has no `snapshot_at` and nothing checks its age.
6. Code does what Spec omits: `fail-on-kev` defaults true, so a default scan with no KEV feed is `indeterminate`.
7. No CAP for: MCP face (`start_audit`, `get_audit`), PR-gate hook book and plugin registry (10 entry points, 5 stub scanners), the TEA advisory itself (11.2/11.3), the two review lenses (11.1), skill/persona (10.1). Flags named nowhere: `--sbom-output --baseline --baseline-emit --reason --pixi-environment --pixi-platform`.
8. Python import surface other code depends on is unnamed. Atlas imports `models, report, verdict, engines.DeptryEngine, hygiene, inventory`; doctor imports `engines.run_doctor_checks`; django-warden imports `cli.main`, `actuator.run_actuator`, fleet clients. Spec, skill and Frame say "do not import".
9. Spec `surface:` is `W/**` only. django-warden (2,254 LOC, realizes CAP-16/17/26 and MCP) is governed by steward's `spec-pyforge-unifying-strategy`.

SHOULD RECHECK
- Slow lane is in no workflow: extraction oracle, corpus determinism, strace egress, real-pixi solver. These prove CAP-2/10/11/24. Dogfood and full-package coverage tasks also in no CI.
- No `live_tree` split for warden (steward and doctor have it). Six unmarked live-tree test files: meta persona, skf-skill, portal; integration pixi-lock scope and real-pixi; unit currency.
- Engine ranges: osv-scanner `>=2.4.0,<2.5` (factory env already 2.7.0); deptry `<0.26`; pixi `<0.82` (host 0.81.0); opengrep `<1.31` from channel `SelfExplainML`, linux-64 only; `tea-test-review --agent claude`, no range, agent dependency not in Spec.
- Bundled LTS registry `updated: 2026-07-06`, 180-day max age → stale 2027-01-02. Canonical copy lives in the CFE skill; equality test skips off-monorepo. Map is generated from CFE atlas `export-purls`.
- Offline data: OSV DB by env var, no default path, 7-day max age. Feeds by `PYFORGE_WARDEN_FEED_CACHE_DIR` plus three refresh scripts — not in Spec.
- Credentials: DW-warden-egm-2026-11-1 open (live fleet scan and approved draft PR unruled; fakes only). Actuator env vars `GITHUB_TOKEN/GH_TOKEN/GITHUB_REPOSITORY/GITHUB_API_URL` not in Spec.
- Schema: no `additionalProperties`; `advisory` and `actuation` untyped, so CAP-23..26 output shapes are unpinned. Emitted keys equal schema's 17.
- A-only expiry 2026-12-31 is shared by 87 rows fleet-wide; golden-path promotion is live CI; no expiry story. Not credible.
- Spec text: CAP-13 and CAP-16 intents carry other CAPs' text with absorbed numbering; CAP-19 says "CAP-1 set"; Assumptions say 43 stories / eleven epics (now 76 / 23); CAP-5 and CAP-21 disagree on `--fail-under-coverage`.
- Memlog has no capability entry for CAP-13..22; needs the archived folders' memlogs. No entry postdates the 2026-11-05 re-derive.
- Companions axes, verdict-contract, extraction-contract untouched since 2026-07-25.
- 40 of 76 story specs cite test paths that are gone (48 are `tests/conformance/`, renamed 2026-09-07).
- Deferred ledger: 55 of 70 open — 5 medium, 10 low, 40 legacy rows with no severity, never curated. Top: DW-warden-16-1, -16-3, -16-4, -16-4-2, -egm-2026-11-1.
- PRD: no arrow to a nonexistent CAP; CAP-13..23 have no FR arrow; line 720 cites an unqualified "CAP-18".
- Skill compiled 2026-08-25; 52 commits since; line cites off; three accepted audit findings unfixed (steward Story 29.5, backlog). Persona forbids start/get audit, which shipped.

NICE TO UPDATE
- Frame: 21 lines, 2026-09-16; no exit enum, flags, fleet, actuator, Spec pointer.
- README says "Epics 1–8 shipped"; dead `docs/specs/pyforge-warden.md` link (also WS/__init__.py:9, W/pixi.toml:12, root pixi.toml).
- Spine: 2026-07-14 body plus 16 appended reconciliations; tree lists `determinism.py`, `_jinja.py`, `requirements.py`, `tests/conformance/`; lacks `sast.py`, `native_lockfiles.py`, MCP; three dead inputDocuments; no numbered ADs.
- Literals: schema `$id urn:local-recipes:…` (frozen); `DEFAULT_AUDIT_TARGET = "src/platform"`; migration `OLD_TABLE = "compliance_face_compliancejob"`; estate default repos (legit); `src/platform/compliance_face/` holds only `__pycache__`.
- `sources.py`, `eligibility.py`, `eligibility_sbom.py` (723 LOC, CAP-13..15) have no runtime caller.
- Platform `/stations/warden/api/v1/compliance/check` returns "accepted" and scans nothing.
- EGM 2026-11-05: 86 medium and 16 low findings untriaged. TODO/FIXME: 0.

EVIDENCE
| Finding | Where | V/I | How |
|---|---|---|---|
| 9 flags off, Spec silent | src/platform/config/flags.json:378,498,573; WS/actuator.py:650-660; WS/cli.py:1117,1310 | V | json parse; grep `pyforge.warden.` in spec folder = 0 |
| Fix stories landed | SP/sprint-status-ledger.yaml; bd154aaa17 | V | yaml; `git merge-base --is-ancestor` rc 0 |
| Markers stale | SPEC:132,148,190,215 | V | read |
| Ledger duplicates and modes | docs/foundry/capability-ledger.yaml | V | yaml: 36 rows, 26 kernel |
| CAP-26 on retire/A-only code | SPEC:231,280; DW/models.py:10 | V | read |
| Python 3.14 | W/pyproject.toml:10; W/pixi.toml:23,42; WS/cli.py:824; SPEC:311 | V | grep, 23 sites |
| `review_required` absent | SPEC:83; prd.md:787 | V | grep src+tests = 0 |
| KEV default on | WS/config.py:254 | V | grep spec folder = 0 |
| Map has no age | WS/data/conda_pypi_map.json; SPEC:306 | V | 11,858 keys, none meta |
| MCP tools | DW/mcp_asgi.py:33-52 | V | read; "MCP" in SPEC = 0 |
| Inbound imports | pyforge-atlas …/universal_sbom/gate.py:118-171,251; pyforge-doctor …/sources/warden.py:84; DW/tasks.py:161-478 | V | grep |
| Surface gap | SPEC:13-14; spec-pyforge-unifying-strategy/SPEC.md:26 | V | grep |
| Slow lane not in CI | pixi.toml:2799; .github/ | V | grep = 0 |
| No live_tree split | pixi.toml:2779-2783 | V | grep warden tests = 0 |
| Engine ranges | WS/engines.py:172-192; pixi.toml:2255,2773 | V | read; `pixi --version` |
| LTS stale date | WS/data/lts-registry.yaml:35; WS/currency.py:195 | V | date arithmetic |
| Credential open | SP/deferred-work-ledger.md:907 | V | read |
| Schema open | WS/data/report-schema.json; WS/models.py:685-715 | V | json walk |
| Expiry not credible | capability-ledger.yaml | I | 87 rows same date |
| Skill drift | .claude/skills/pyforge-warden/0.1.0/pyforge-warden/metadata.json; SP/research/egm-audit-2026-11-05.md:62-65 | V | `git rev-list --count` = 52 |
| Persona stale | .claude/skills/bmad-agent-warden/SKILL.md:88 | V | read |
| TEA needs an LLM agent | WS/engines.py:192 | I | `--agent claude` |

Test lanes (static `def test_` count): unit 53 files / 1,625; meta 9 / 87; integration 21 / 249 (4 slow modules); platform 10 files / 152. Skips: 26 sites, no xfail — 14 POSIX/root, strace/warden/pixi/opengrep absent, root pixi.lock absent, CFE registry absent, oracle renderers missing, case-insensitive FS. Integration needs real deptry and osv-scanner, a 16 MB package-local corpus (1,979 recipes; unparseable-rate ratchet 0.4686), conda-build, py-rattler-build, strace; no network (autouse socket deny). Coverage floor: 80% unit, touched modules only.

NOT CHECKED
- No test executed; green status of any lane unknown.
- CAP intent/success read against code by spot check only: numeric bounds for CAP-24/26, formats, actuator kinds, structural constraints. CAP-3, 4, 7, 9, 10, 17 not traced line by line.
- Companions checked by term grep, not read in full. Dream body, briefs, test-design docs, 5 readiness reports not read.
- 76 story specs: only test-path resolution scripted; ACs not compared to code.
- django-pyforge, pyforge-core internals, `src/platform` settings beyond grep.
- B repo not inspected.
