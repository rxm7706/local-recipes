---
companion-of: spec-foundry-capability-ledger
updated: "2026-11-11"
---

# Capability modes

**fcl:CAP-1.** One mode per capability. Never `move`. This table is
the strangler **routing** map, not a git-sync map.

This file is the one definition of the ledger: § Schema v1 is the shape of
`docs/foundry/capability-ledger.yaml`, and § The rules of 2026-11-10 decide
every mode in it. Steward's generator and check (`steward cutover plan`,
Stories 121.1, 121.3, 121.6 and 121.7) and doctor's `frozen-path-changed`
and `capability-ledger` sources (doctor Stories 56.1 and 56.2) cite it and
restate none of it. `extract.md` is the inventory those rows derive from.

| Mode | Meaning |
|---|---|
| `rebuild` | B re-derives it from the Dream plus its memlog and the re-derived Spec (a Frame points at them); A is the oracle until `verified-in-foundry` |
| `retire` | Must not appear on B; A may keep history; the Spec heading carries `(retired <date>[: <reason>])` |
| `A-only` | Allowed on A; carries an expiry (§ Expiry) |
| `B-only` | Named on a live Spec and carried by a live `blocked` or `backlog` Story before `done` |
| `pending` | A placeholder, not a destination: the row waits on a named operator question (`pending_on`) and B never acts on it |

`verified-in-foundry` is a **claim on a rebuild row** (a `state`), not a
mode. It requires a case-list id (`case_id`, the `fnr:CAP-1` list).

Story 44.1 retired 2026-11-10: its move-list half is gone, and its ledger
half lands in steward Stories 121.1 to 121.7.

## Schema v1

Every key below, in this order. The block is the shape, with real rows as
examples; it is not ledger data.

```yaml
schema: pyforge.capability-ledger/v1
generated_by: pyforge steward cutover plan
updated: "2026-11-10"
source_sha: "<the HEAD the Specs were read at; check never compares it>"
extract: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/extract.md
modes: [rebuild, retire, A-only, B-only, pending]
states: [planned, rebuilding, verified-in-foundry, cut]
frozen_states: [rebuilding]
capabilities:
  - id: pap:CAP-1
    spec: pyforge-unifying-strategy
    station: pyforge-steward
    heading: The host renders from the accelerator shape
    path: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
    mode: A-only
    expiry: "steward:121.5"
    note: same text as pyforge-steward:CAP-98..103 (Story 48.8 merge)
  - id: fnd:CAP-12
    spec: python-foundry-cutover
    station: pyforge-steward
    heading: The laptop SBOM
    path: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
    mode: A-only
    expiry: "flip"
  - id: pyforge-testing-charter:CAP-4
    spec: pyforge-testing-charter
    station: pyforge-marshal
    heading: Coverage gate enforced, not just measured
    path: _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md
    mode: rebuild
    state: planned
    # launch: true                 only on a row launch-slice.md names
    # depends_on: []               optional ledger ids; empty in the 2026-11-10 change
    # frozen_paths: [<A path>]     required while state is in frozen_states
    # case_id: <k-... case id>     required with state verified-in-foundry
  - id: pyforge-atlas:CAP-68
    spec: pyforge-atlas
    station: pyforge-atlas
    heading: the query-plane estate source has a producer
    path: _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
    mode: B-only
    note: never built; atlas Story 36.3 (blocked) carries it (rule 7)
  - id: pyforge-herald:CAP-6
    spec: pyforge-herald
    station: pyforge-herald
    heading: Video-Scripts Framework
    path: _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
    mode: retire
  # A pending row (rule 9) adds pending_on: "<unit> Q<n>".
  # A row the generator added without a decision adds defaulted: "YYYY-MM-DD".
cells:
  - id: cell:conda-forge-expert/skill
    path: .claude/skills/conda-forge-expert/
    mode: A-only
    expiry: "mason:39.2"
    note: conda-forge-expert has no Spec until mason Story 39.2 (rule 6)
  - id: cell:conda-forge-expert/scripts
    path: .claude/scripts/conda-forge-expert/
    mode: A-only
    expiry: "mason:39.2"
  - id: cell:conda-forge-expert/mcp-server
    path: .claude/tools/conda_forge_server.py
    mode: A-only
    expiry: "mason:39.2"
  - id: cell:conda-forge-expert/data
    path: .claude/data/conda-forge-expert/
    mode: A-only
    expiry: "mason:39.2"
```

### Header

| Key | Value |
|---|---|
| `schema` | `pyforge.capability-ledger/v1` |
| `generated_by` | `pyforge steward cutover plan` |
| `updated` | `"YYYY-MM-DD"`, the day the generator last wrote the file |
| `source_sha` | the HEAD the Specs were read at; `--check` never compares it |
| `extract` | the path of `extract.md` |
| `modes` | `[rebuild, retire, A-only, B-only, pending]` |
| `states` | `[planned, rebuilding, verified-in-foundry, cut]` |
| `frozen_states` | `[rebuilding]`: doctor's `frozen-path-changed` holds the same constant |

`capabilities:` holds one row per live capability; `cells:` classifies what
has no Spec yet. There is no `move` key, no `never_move` key and no
`story_44_1` key.

### Rows

Keys appear in this order; a key that does not apply is left out, never
written empty.

| Key | Kind | Rule |
|---|---|---|
| `id` | derived | `extract.md` § Id rule |
| `spec` | derived | the Spec folder name without `spec-` |
| `station` | derived | `extract.md` § Station rule |
| `heading` | derived | the heading as `extract.md` normalises it |
| `path` | derived | the Spec's `SPEC.md`, relative to the repository root |
| `mode` | decided | one of `modes`, by § The rules of 2026-11-10 |
| `expiry` | decided | `A-only` rows only; a quoted string (§ Expiry) |
| `state` | decided | `rebuild` rows only; one of `states`; `planned` until B starts |
| `launch` | decided | `true` on a row `launch-slice.md` names |
| `depends_on` | decided | optional list of ledger ids; empty in the 2026-11-10 change |
| `frozen_paths` | decided | the A paths held still while `state` is in `frozen_states` (`spec-pyforge-doctor:CAP-94`) |
| `case_id` | decided | the case-list id (first column of `case-list.md`) a `verified-in-foundry` row passes (`fcl:CAP-3`) |
| `pending_on` | decided | `pending` rows only: the operator question, `"<unit> Q<n>"` |
| `defaulted` | decided | `"YYYY-MM-DD"`: the generator added the row without a decision; `plan --check` warns on it every run until a decision clears it |
| `note` | decided | free text |

`steward cutover plan --regenerate` rewrites the derived keys from the live
Specs and keeps the decided ones (`fnd:CAP-9`).

States, in order: `planned` (B has not started); `rebuilding` (B builds it,
and its `frozen_paths` on A stay still); `verified-in-foundry` (B passes the
case-list row `case_id` names, after the archived suite or an equivalence
check; herald reads `state` and `case_id`); `cut` (the strangler routes the
capability to B). No row claims `verified-in-foundry` while B's kernel leaves
are the PR #1344 prototype (operator ruling 1).

A `cells:` entry carries `id` (`cell:conda-forge-expert/<part>`, the part one
of `skill`, `scripts`, `mcp-server` and `data`), `path`, `mode` (`A-only`),
`expiry` (`"mason:39.2"`) and an optional `note`. A cell is never frozen.

### Expiry

Always a quoted string, in one of three forms:

- `"<station>:<E>.<S>"`: the short station key (`steward`, `mason`, ...) and
  a Story key, resolved against that station's `sprint-status-ledger.yaml`
  key prefix `<E>-<S>-`. Never bare: an unquoted `44.10` reads as the
  number `44.1`.
- `"YYYY-MM-DD"`.
- `"flip"`: the row stays on A until the root of record flips to `foundry`.

The anchors in use: `"steward:121.5"` (host, platform and portal; a Story
minted `blocked`), `"mason:39.2"` (conda-forge-expert; minted `blocked`),
`"steward:44.8"` (the working set), `"steward:44.14"` (the testing charter's
`A-only` rows) and `"flip"`.

An expiry is judged when it arrives (`fcl:CAP-2`): a date 30 days ahead is
a WARN and one day past a FAIL; a Story expiry whose Story is `done` is a
FAIL, and one whose key does not resolve is a FAIL (doctor's
`capability-ledger` source, `spec-pyforge-doctor:CAP-95`). The `flip` form
lapses when `pyforge.core.cutover_root.root_of_record()` answers `foundry`,
judged by `steward cutover plan --check`, which also refuses any other form.

### Marker tokens

A capability's status sits on its Spec heading line, after the bold title
(`CHAIN-STANDARD.md` § 4). The generator, the check and doctor read these
forms and no others:

| Token | Reads as |
|---|---|
| `(ready YYYY-MM-DD…)` | the contract binds; its success is not met yet |
| `(shipped YYYY-MM-DD…)` | its success is met |
| `(retired YYYY-MM-DD[: <reason>])` | retired; the row is `retire` |
| `RETIRED YYYY-MM-DD` | the legacy retired form inside the bold title (`fnd:CAP-7`) |

After the date, `CHAIN-STANDARD.md` § 4 (as steward Story 120.3 amends it)
names three qualifiers that follow a semicolon: `not met: <clause>, DW-<id>`,
`operator act open, DW-<id>` and `superseded by CAP-n`. Any other
parenthesised status word on a heading line (`minted`, `unbuilt`, `deleted`,
a bare `never built`, `retired` with no date) is `unknown-marker` (steward
Story 121.6). There is no `(unbuilt)` marker: a capability never built and
retired reads `(retired <date>: never built)`.

## The rules of 2026-11-10

The operator's rulings of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`
§ Realization log: the entry, its addendum and its second addendum) decide
every mode. Every question of that day is ruled, so no rule leaves a row
waiting on one of them.

Rows the operator ruled by name take that ruling (the second addendum's
ruling 4), and `remode-2026-11-10.md` records each with it:
`pyforge-testing-charter:CAP-4` is `rebuild`; `pyforge-testing-charter:CAP-1`,
`CAP-2` and `CAP-5` are `A-only`, expiry `"steward:44.14"`;
`pyforge-warden:CAP-13` to `CAP-15` are `A-only`, expiry `"steward:44.8"`;
`pyforge-herald:CAP-6` and `pyforge-scribe:CAP-34` are `retire`;
`pyforge-warden:CAP-26` is `rebuild` (its kernel half) and
`pyforge-warden:CAP-29` `A-only`, expiry `"steward:121.5"` (its portal half).

Every other row takes the first rule that matches, in this order:

| # | When | Mode | Expiry or marker |
|---|---|---|---|
| 1 | The capability's artifact is deleted on A | `retire` | `(retired <date>: <reason>)` |
| 2 | A closed one-time campaign: a recipe campaign (ruling 3) or one of doctor's (second addendum ruling 4) | `retire` | `(retired <date>: closed one-time campaign)` |
| 3 | A host, platform or portal capability, steward's restore and revoke duties included | `A-only` | `"steward:121.5"` |
| 4 | A row on an archived Spec (any path under `archive/`) | absent | the folded station row is the single record |
| 5 | The testing kit and the kernel library | `rebuild` | `state: planned` |
| 6 | conda-forge-expert and anything that runs through it (the four `cells:` rows included) | `A-only` | `"mason:39.2"` |
| 7 | A capability never built: none of its citing Stories reads `done` | `B-only` when a live `blocked` or `backlog` Story carries it; else `retire` | `(retired <date>: never built)` on the `retire` row |
| 8 | `fnd:CAP-12` to `fnd:CAP-15` and `pyforge-mason:CAP-29` | `A-only` | `"flip"` |
| 9 | A row whose two proposals disagree | `pending` | `pending_on: "<unit> Q<n>"`, the operator question |
| 10 | Everything else | `rebuild` | `state: planned` |

Rule 7 is ruling 3 ("a capability that was never built is not `rebuild`")
as the second addendum settles it: `pyforge-atlas:CAP-68` is `B-only`
because atlas Story 36.3 (`blocked`) carries it, and the addendum's "Retire
both" retires `pyforge-atlas:CAP-18` to `CAP-31` and `pyforge-mason:CAP-8` to
`CAP-13`. A citing Story is one in the station's `epics.md` whose FR/AD or
Parent line names the capability; a live one's ledger key reads `blocked` or
`backlog`. Steward Story 121.6's `rebuild-never-built` finds a `rebuild` row
that rule 7 should have caught.

A row that contradicts its Spec's marker, a `pending` row with no question
and a `rebuild` row nothing built are refused by `steward cutover plan
--check` (`cutover_ledger_check.py`, steward Story 121.6).
