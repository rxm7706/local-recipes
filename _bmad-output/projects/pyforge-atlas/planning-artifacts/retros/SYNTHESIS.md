---
doc_type: retrospective-synthesis
project: pyforge-atlas
covers: epics 1-8 (waves 0, A-G)
date: 2026-07-25
---

# pyforge-atlas — cross-epic synthesis

Written after all eight per-epic retros. The per-epic findings are local; these
seven are only visible across the whole effort, and they are the reason the
operator chose to run the retros rather than waive them.

## 1. The independent fresh-eyes reviewer was the highest-return practice

Three reviewers ran per story: two in-loop (full context) and one independent
(given only the spec + files). **The independent pass repeatedly caught what the
in-loop pair missed, and the misses were substantive:**

| Story | Finding | Severity |
|---|---|---|
| B5 | `AD-13` `UnicodeDecodeError` guard hole | HIGH |
| B7 | `_REQ_RE` extras / URL garbage-version | HIGH |
| B8 | `AD-13` never-fail gap in `_persist` | MED |
| G2 | path traversal in the static-host emitter | **MUST-FIX** |
| B1 | `downloads_source='merged'` contract violation | — |
| B2 | `_serial_moved` coercion | — |

**Context is what made the in-loop reviewers miss them.** Having watched the code
being written, they inherited its assumptions. The lesson is not "more reviewers"
— it is *one reviewer who was not there*.

## 2. Enforce architecture in a gate, not in discipline

The cleanest contrast in the effort:

- **F1's DuckDB-singularity AST gate** — one engine, enforced by parsing the
  source. Never violated.
- **`AD-13` keep-last-good** — the same decision, re-implemented per site.
  **Violated twice in one wave** (B5, B8), both caught only by the independent
  reviewer.

Same class of decision, opposite outcomes. A repeated architectural rule wants
one shared implementation plus a gate; per-site discipline decays.

## 3. Gates proved structure; correctness often went unasserted

`dagster-dryrun`, `wasm-smoke`, `kedro-catalog-check`, the HTTP-Range gate — all
prove *shape*. Several waves shipped without a correctness assertion:

- dashboards render? (D2 — untested)
- is a lineage event well-formed? (E2 — emitted, never asserted)
- does the WASM path agree with native? (G1 — loads, never compared)

The gate suite is strong on "is it wired" and thin on "is it right."

## 4. One deferral, taken three times, owned by nobody

Live daemon bring-up was deferred in **C1** (`DW-C1-1`), again in **G3**
(`DW-G3`), and again in **H4** (`DW-H4`). Three honest story-level deferrals, no
contract-level item — so a week after ship it resurfaced as an unanswered
question in `SPEC.md`. It is now **`DC-2`** in PRD § 6.4.

**Rule:** the second time a deferral repeats across waves, promote it to
contract level.

## 5. Deferral *discipline* was excellent; deferral *durability* failed

54 deferrals were recorded rather than faked — genuinely good practice under
unattended execution. But `implementation-artifacts/deferred-work.md` is
**truncated to 9 of 54**, and the directory is **gitignored**, so no tracked copy
of the other 45 exists. *The judgment survived; the record did not.*

This is why these retros and the `DC-*` entries live in Tier-2
`planning-artifacts/`. It is the same failure that cost pyforge-warden 13 story
specs, in a different directory.

## 6. Story size predicted escaped defects better than story difficulty

The two keystone stories — **B1** (12 phases) and **B2** (14 nodes + cost gate +
scheduler) — each shipped a contract violation past two adversarial reviewers.
The small stories did not. Review quality degrades with diff size faster than
implementation quality does.

## 7. Cross-platform path handling was re-litigated at least three times

A3 (Gemini PR-72), G2 (traversal + over-long names), and the post-merge Gemini
sweep (backslash / `as_posix` / `.git`-anchored roots). One convention settled in
the scaffold wave would have pre-empted all three.

---

## Actions

| # | Action | Owner |
|---|---|---|
| A1 | Keep the independent fresh-eyes reviewer as a standing role; it has the clearest evidence of return | Marshal (loop policy) |
| A2 | Prefer AST/gate enforcement over per-site discipline for any repeated architectural rule | Atlas |
| A3 | Add correctness assertions where only structural gates exist (dashboard render, lineage well-formedness, WASM-vs-native agreement) | Atlas |
| A4 | Promote a deferral to contract level on its **second** cross-wave repeat | Marshal |
| A5 | Never file durable record in Tier-3 — retros, deferrals and specs land tracked | repo-wide *(landed 2026-07-25)* |
| A6 | Split keystone stories; cap diff size per review | Marshal |
| A7 | Settle cross-platform path handling once, in the scaffold wave | Mason / Atlas |

**A5 is already done.** A1, A4 and A6 are `bmad-loop` policy and belong to
Marshal. A2, A3 and A7 are Atlas-side engineering.
