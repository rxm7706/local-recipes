---
title: "39.2: conda-forge-expert gets its own Spec after the root of record flips"
type: 'chore'
created: '2026-11-10'
status: 'blocked'
blocking_condition: 'the root of record has not flipped: the operator flips this key after pyforge.cutover_root reads foundry (operator ruling 2026-11-10; minted blocked, never dispatched before)'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/foundry/capability-ledger.yaml
  - .claude/skills/conda-forge-expert/SKILL.md
surface:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-39-2-conda-forge-expert-gets-its-own-spec-after-the-root-of-record-flips.md
deferred: []
---

<intent-contract>

## Intent

**Problem:** Ruling 3 of 2026-11-10 ("Accept all"): conda-forge-expert takes explicit `A-only` ledger rows whose expiry is its own Spec Story, after the flip. That Story has to exist with a stable key before the ledger can name it. This is the placeholder: minted now, `blocked`, not built in this PR. It does not spec CFE.

**Approach:**
- **Mint only.** The mint writes the heading, the Tier-3 feed value `blocked` and this story spec; no agent builds it, and Story 37.4 does not depend on it. Blocked, not backlog: a backlog key would be offered to every drain, and a cross-station gate is a ledger `blocked` row the operator flips.
- **The one anchor** (operator ruling 2026-11-10, "Accept all, run mint"): steward Story 121.6 does not mint a conda-forge-expert placeholder; this Story is the expiry `mason:39.2` (modes.md § Schema v1: the short station key, quoted) of the four `cells:` rows `cell:conda-forge-expert/{skill,scripts,mcp-server,data}` and of `pyforge-mason:CAP-19`, `CAP-21` to `CAP-26` and `CAP-32` to `CAP-34`.
- **What it decides when unblocked:** the form of CFE's Spec (CAPs on the station Spec, or a Spec folder with a `fold-exemption`); its surface (76 scripts, 63 wrappers, 46 MCP tools, the test suites); the argv contract Mason's adapters rely on (Story 38.3 holds the static part); the requirements CAP-19 and CAP-21..CAP-26 owe once rebuilt; and the portability of the 44 scripts that name this repository. It closes with a CFE retro.

Ledger key: `39-2-conda-forge-expert-gets-its-own-spec-after-the-root-of-record-flips`.
Ledger status: `blocked` (minted blocked; the operator flips it).
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **CAP-19**, **CAP-21..CAP-26** and **CAP-32..CAP-34**: their routing sentences (Story 37.1) name this Story as the expiry of their A-only mode.
- Operator rulings 2026-11-10: ruling 3 of "Accept all"; "Accept all, run mint" (CAP-32 A-only on this Story).

## Boundaries & Constraints

**Always:**
- Stay `blocked` until the operator flips the key.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never flip this key out of `blocked`; the operator does.
- Never spec or edit conda-forge-expert in this PR.
- Never hand-edit a `SPEC.md` or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**AC1 — The ledger key exists and is blocked.**

```bash
grep -n '^  39-2-' _bmad-output/projects/pyforge-mason/planning-artifacts/sprint-status-ledger.yaml
```

Expect: one line, ending `: blocked`.

**AC2 — The story spec says what it waits for.**

```bash
grep -nE '^(status|blocking_condition):' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-39-2-*.md
```

Expect: `status: 'blocked'` and a `blocking_condition` that names `pyforge.cutover_root` reading `foundry`.

**AC3 — The heading, the key and the story spec agree.**

```bash
pixi run -e pyforge-guild story-status-check; echo $?; pixi run -e pyforge-guild chain-completeness-check; echo $?
```

Expect: 0 and 0.

**AC4 — The ledger's conda-forge-expert rows name this Story as their expiry (control-plane request).**

```bash
python3 -c "import yaml,sys; d=yaml.safe_load(open('docs/foundry/capability-ledger.yaml',encoding='utf-8')); E='mason:39.2'; cells=[r for r in (d.get('cells') or []) if str(r.get('id','')).startswith('cell:conda-forge-expert/')]; rows={r.get('id'):r for r in d['capabilities'] if isinstance(r,dict)}; caps=[rows.get('pyforge-mason:CAP-%d'%n) or {} for n in (19,21,22,23,24,25,26,32,33,34)]; ok=sorted(r['id'] for r in cells)==['cell:conda-forge-expert/data','cell:conda-forge-expert/mcp-server','cell:conda-forge-expert/scripts','cell:conda-forge-expert/skill'] and all(r.get('mode')=='A-only' and str(r.get('expiry'))==E for r in cells+caps); sys.exit(0 if ok else 1)"
```

Expect: exit 0 after control-plane 121.7 (exit 1 today): the four `cells:` rows cell:conda-forge-expert/{skill,scripts,mcp-server,data} and the ten pyforge-mason rows CAP-19, CAP-21..CAP-26, CAP-32..CAP-34 read mode A-only with expiry `mason:39.2` (modes.md § Schema v1).

</intent-contract>

## Binding

- Parent: `spec-pyforge-mason`.
- Requirements: none.
- Dream: `docs/dreams/pyforge-mason.md`, Realization log, *2026-11-10 (the cutover readiness audit)*.
- Epic 39, `### Story 39.2: conda-forge-expert gets its own Spec after the root of record flips` in `planning-artifacts/epics.md`.
- Wave: MINT (cutover readiness plan).
- Findings closed: MUST 1.

## Notes

- Cross-station: control-plane writes the `mason:39.2` expiries in `docs/foundry/capability-ledger.yaml` (steward:S-121.7).
