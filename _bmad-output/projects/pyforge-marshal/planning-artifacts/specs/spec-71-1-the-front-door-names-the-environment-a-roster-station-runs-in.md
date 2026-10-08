---
title: '71.1: The front door names the environment a roster station runs in'
type: 'fix'
created: '2026-09-28'
status: 'in-progress'
baseline_revision: 'd058a3dcc63e92ef7da6205b2089c4c61551d8ab'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `pixi run -e pyforge-guild pyforge warden --help` prints `unknown station 'warden'; known: doctor, herald, marshal, scribe, steward` and exits 2; `pyforge atlas` and `pyforge mason` answer the same. All three are Guild stations on the one roster (`pyforge.core.roster.STATIONS`). They are not installed in the Guild environment: warden is left out on purpose (its `osv-scanner >=2.4.0,<2.5` range pin conflicts with the factory's `>=2.5.1`; see the `[feature.pyforge-guild.dependencies]` comment in `pixi.toml`), atlas is excluded on purpose too (steward's 2026-09-28 decision, recorded on steward Story 72.1: its analytics closure would add ~60% to the Guild), and mason arrives with steward Story 72.1 (`spec-pyforge-steward:CAP-161`). Warden and atlas therefore keep needing this message after mason joins. `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py` builds its station map from the installed distributions (`script_map_from_installed`, `:94-105`), tries the single-name distribution fallback (`_resolve_primary`, `:154-166`) and the noun aliases (`:145`), and then raises `DispatchError("unknown station …")` (`:151`), which `main()` returns as exit 2 (`:184`).

**Approach:** in `dispatch_argv`, after the installed map, the fallback and `NOUN_ALIASES` have all failed:
- when the token is in `roster.STATIONS`, raise `DispatchError` with a not-installed message, for example `station 'warden' is not installed in this environment; it runs in -e pyforge-warden: pixi run -e pyforge-warden pyforge warden <noun> <verb>` — the environment name is `roster.long_form(token)` (Ruling 18: the long form names packages and pixi environments), and nothing reads `pixi.toml`;
- a token on no roster keeps today's `unknown station {token!r}; known: {installed}` message byte-for-byte;
- the usage listing (`pyforge`, `pyforge -h`, `pyforge --help`) keeps `stations: <installed>` and adds a line naming the roster stations not installed here, each with its environment;
- exit codes are unchanged (both refusals stay `EXIT_USAGE`, 2).

Ledger key: `71-1-the-front-door-names-the-environment-a-roster-station-runs-in`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-core` CAP-11 (FR-226).
- Kinship: `spec-pyforge-steward:CAP-161` (steward Story 72.1, mason in the Guild environment); steward's 2026-09-28 decision that atlas stays out of the Guild (`docs/dreams/pyforge-steward.md`, no CAP; recorded on steward Story 72.1).

## Acceptance Criteria

- Given a script map of doctor, herald, marshal, scribe and steward When `dispatch_argv(["pyforge", "warden", "--help"], script_map=…)` runs Then `DispatchError` names `warden` as not installed in this environment, `-e pyforge-warden` and `pixi run -e pyforge-warden pyforge warden`
- Given the same map When `main(["pyforge", "warden", "--help"], …)` runs Then it returns 2 and stderr carries that message, not "unknown station"
- Given the same map When the token is `atlas` or `mason` Then the message names `-e pyforge-atlas` or `-e pyforge-mason`
- Given the same map When the token is `nosuch` Then the message is `unknown station 'nosuch'; known: doctor, herald, marshal, scribe, steward`, byte-for-byte as today
- Given the same map When the token is `context` Then it still aliases to `marshal context …`
- Given a map that includes `warden` When `pyforge warden scan` runs Then it dispatches to warden's script as today
- Given the same five-station map When `pyforge --help` runs Then the listing names the five installed stations and, separately, atlas, mason and warden with their environments
- Given the roster check removed When the warden case runs Then "unknown station 'warden'" comes back and the test fails (mutation)
- Given `tests/meta/test_cli_parity_matrix.py`'s off-roster `ghost` case When the core suite runs Then it passes unchanged

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 71.1. Keep `pyforge-core` a stdlib leaf (AD-66): import only `pyforge.core` modules and read no file for this. Resolve in today's order — installed map, single-name fallback, noun aliases — before the roster check, so an installed station or an alias always wins. Keep both exit codes.

**Never:**
- Do not read or parse `pixi.toml`, or probe which pixi environments exist.
- Do not install, remove or re-home any station (`pixi.toml` is untouched; mason is steward 72.1; atlas is a steward chain).
- Do not change the off-roster message text, `NOUN_ALIASES`, `PREPARATORY_UNINTROSPECTABLE` or the parity matrix's semantics.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`; do not run `scripts/bmad-switch`.

Co-governing Specs of `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py` in the spec-surface baseline: `spec-pyforge-core` (owner) and `spec-pyforge-unifying-strategy` (pyforge-steward) — reconcile each one the detector names.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| roster station, not installed | `pyforge warden --help` in the Guild env | not-installed message naming `-e pyforge-warden` and the command | exit 2 |
| roster station, installed | `pyforge doctor …` | dispatches as today | as today |
| off-roster token | `pyforge nosuch` | `unknown station 'nosuch'; known: …` unchanged | exit 2 |
| noun alias | `pyforge context bootstrap` | `marshal context bootstrap` | as today |
| usage | `pyforge --help` | installed stations, then missing roster stations with environments | exit 2 as today |
| nothing installed | empty map | usage names `(none installed)` and every roster station's environment | exit 2 |

</intent-contract>

## Source

Contract authored from the operator's 2026-09-28 direction, `docs/dreams/pyforge-marshal.md`'s 2026-09-28 entry (*the front door names the environment a roster station runs in*; this Spec's own Dream is archived into the marshal Dream) and `spec-pyforge-core` CAP-11 with its 2026-09-28 direction entry in that Spec's `.memlog.md`, decomposed the same session as Epic 71's mint (hosted on marshal, as Epics 14, 52 and 63 were).

## Binding

Parent Spec capability: `spec-pyforge-core` CAP-11 (FR-226).
Ledger key: `71-1-the-front-door-names-the-environment-a-roster-station-runs-in`.
Ledger status at mint: `backlog`.
Policy: `marshal-policy.toml` `[epic_surfaces]` `"71"` admits `pyforge-core`'s `dispatch.py` and its unit test beside the default surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks:**
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass (the suite that covers `dispatch.py`, including `tests/meta/test_cli_parity_matrix.py` and the sole-ownership meta-tests).
- `pixi run --frozen -e pyforge-guild pyforge warden --help` names `-e pyforge-warden` and exits 2; `pyforge nosuch` still reads "unknown station".
