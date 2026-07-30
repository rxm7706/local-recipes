# Charter-alignment migration plan

**Status: planned, not executed.** Derived 2026-07-28 from
`scripts/dream_chain_check.py` against the Charter § 5 amendment
("owning is becoming — at the planning tier"). The standard is
`EXEMPLAR-STANDARD.md`; the live backlog is always the detector, never this file.

```bash
pixi run -e local-recipes python scripts/dream_chain_check.py
```

---

## Target

**9 projects — 8 Smiths + `pyforge-genesis`** (constitutive: the origin Dream, and the
records of the Charter, the Lexicon, and the Guild's membership).

| Project | Chains | Tree |
|---|---|---|
| `pyforge-marshal` | 7 | **migrate** |
| `pyforge-mason` | 6 | ok |
| `pyforge-atlas` | 5 | ok |
| `pyforge-herald` | 4 | ok |
| `pyforge-scribe` | 3 | ok |
| `pyforge-genesis` | 2 | **migrate** |
| `pyforge-steward` | 2 | ok |
| `pyforge-doctor` | 1 | ok |
| `pyforge-warden` | 1 | **migrate** |

**Dissolved (5):** `local-recipes`, `deckcraft`, `presenton-pixi-image`,
`unity-data-stack`, `wasm-analytics-stack`.

## Backlog — 38 findings

| Work type | Count |
|---|---|
| `spec-location-mismatch` — chain moves | 13 |
| `dream-without-spec` — Specs to author | 12 |
| `prd-not-sharded` | 6 |
| `architecture-not-sharded` | 5 |
| `epics-missing` | 2 |

By owner: marshal 11 · mason 6 · atlas 5 · herald 5 · guild 4 · steward 3 · scribe 2 ·
warden 2 · doctor 0.

---

## Done (2026-07-28, uncommitted)

- **Charter § 5 amended** + Realization log entry — "owning is becoming, at the planning
  tier"; the two constitutive Dreams' chains live in `pyforge-genesis`; the installer is
  the Marshal's.
- **`EXEMPLAR-STANDARD.md`** rewritten to the amendment, with three superseded drafts
  recorded rather than silently replaced.
- **`docs/dreams/pyforge-genesis.md`** → `owner: guild`, constitutive banner.
- **`docs/dreams/genesis-installer.md`** created — `owner: marshal`, the buildable half.
- **`spec-pyforge-genesis`** re-pointed to the installer Dream.
- **INV-0 closed** — `owner-dream:` added to 10 Specs; all 22 now parse and link.
  Findings 44 → 38, and `doctor` left the scoreboard entirely.
- **Detectors aligned** — `dream_chain_check.py` (guild → `pyforge-genesis`, both Dreams
  constitutive); `bmad_drift_check.py` `GUILD_DREAMS` = both.

## Sequencing — and the one hard dependency

> **Shard before you move.** `pyforge-marshal`, `pyforge-genesis` and `pyforge-warden` are
> flat: `prd.md`, `architecture.md`, `epics.md` at the top level. Two flat chains **cannot
> occupy one project** — the filenames collide. Sharding first gives every chain its own
> `prds/prd-<slug>-<date>/` and `architecture/architecture-<slug>-<date>/`, and the
> collision disappears. This is why the Genesis→Marshal chain move is not already done.

**Phase 1 — shard the three flat trees** (`bmad-prd` + `bmad-architecture` per chain).
Independent of each other; warden's is standalone and can go first as a rehearsal.

**Phase 2 — move the 13 chains.** Planning artifacts only; `surface:` never changes, so no
package is renamed. Per move, in the same commit: `git mv`, update `owner-dream:` and
relative `sources:` depths, then sweep references — `scripts/spec_surface_check.py` surface
map, drift baselines, `_bmad-output/PROJECTS.md`, `scripts/bmad-switch`,
`.bmad-loop/policy.toml` `worktree_seed`.

**Phase 3 — author the 12 missing Specs.** marshal 4 · mason 2 · scribe 2 · atlas 1 ·
herald 1 · genesis 2 (the Charter's and the constitutive Genesis). Five are for `archived`
Dreams — retirement records, cheap. One is the real hole: **`agent-tool-surface` is
`realized` with no contract at all.**

**Phase 4 — `epics-missing`** on `unity-data-stack` and `wasm-analytics-stack`, after their
chains land under atlas.

**Order:** warden (rehearsal) → marshal (largest debt; owns the console and loop everything
else depends on) → genesis → the local-recipes evacuation → the remaining project folds →
Spec authoring.

## Standing cautions

- **A move that skips the reference sweep turns a green detector red.** Worse, a *wrong*
  green reads as authoritative — this session produced three (`data.js` stale while
  regenerating clean; the Atlas kernel asserting run admission that did not exist; the first
  `dream_chain_check.py` reporting 21 for 11).
- **Package identity does not move with the planning tree.** `spec-deckcraft` under
  `pyforge-herald/` still builds `apps/deckcraft/**`. If a `surface:` changes during a move,
  something has gone wrong.
- **Validate the detector against a chain you know** before trusting a new count.
- **`local-recipes` is retired, not emptied-and-kept.** Once its 8 chains leave, remove the
  project rather than leaving a husk that invites re-use as a dumping ground.
