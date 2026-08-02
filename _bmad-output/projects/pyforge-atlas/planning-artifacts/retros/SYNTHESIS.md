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
**truncated to 9 of 54**, and the directory is **gitignored**.

*Updated 2026-07-25:* the record was **recovered**, not lost — 52 of 54 survive
with full bodies in the tracked `spec-archive/`, now consolidated into
`../deferred-work-ledger.md`. Only `DW-A2-P4` and `DW-D2` are unrecovered. The
finding stands in weaker form: **a Tier-3 ledger is one accident from
unreadable, and it took a deliberate hunt to learn the copy existed.**

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

**Landed 2026-07-25 — A1, A4, A5 all done.**

- **A1 ENFORCED** — `.bmad-loop/policy.toml` `review.trigger` flipped
  `"recommended"` → `"always"`. The independent pass is now standing on every
  story, on every line, for every Smith.
- **A4, A6 documented** in the same file as **conventions, not config keys** —
  bmad-loop reads neither, and a dead key that silently does nothing is worse
  than an honest comment. A6 binds at authoring time
  (`bmad-create-epics-and-stories`), not at review time.
- **A5 done** — these retros, the `DC-*` rows, and the restored
  `../deferred-work-ledger.md` all live in tracked Tier-2.
- **A2, A3, A7 remain open** — Atlas-side engineering, unscheduled.

Recorded in `docs/dreams/pyforge-marshal.md`. This is the first time a completed
effort's retrospective changed the harness that runs the next one.

---

## Update 2026-08-02 — Waves H and I retros landed; Action A4 recurred

This synthesis covered epics 1-8 (waves 0, A-G) as of 2026-07-25. Two per-epic
retros were missing since — `epic-9-wave-h-karpathy-wiki.md` (Wave H, shipped
2026-07-18, predates this synthesis) and `epic-10-wave-i-post-audit-truth-up.md`
(Epic 10 / Wave I, shipped 2026-07-29, postdates it) — and now exist alongside
this file. Read them for the full local findings; only what is genuinely
cross-wave is appended here.

**Action A4 ("promote a deferral to contract level on its second cross-wave
repeat") recurred in a different shape.** Finding 4 above tracked *daemon
bring-up* deferred three times (C1, G3, H4) before promotion. Wave I surfaced
the same structural failure for a different kind of repeat: stories I4 (10.5)
and I5 (10.6) both finalized `done` while their review pass was still actively
recommending a follow-up, because `max_followup_reviews` — an unchosen upstream
default of 1 — was spent rather than the reviewer being satisfied. It was the
*second* occurrence, not the third, that triggered the fix inside Wave I itself
(cap raised to 2, explicitly chosen; a new `deferred_work_check.py` detector
closing the same "gitignored refile target" leak Finding 5 named). That the fix
landed on the second repeat, in-epic, rather than needing a third instance and a
later retro, is A4 working as designed — the opposite of Finding 4's own history.

**Action A5 ("never file durable record in Tier-3") held under real pressure.**
`DW-I4-1` and `DW-I5-1` were promoted out of gitignored `implementation-artifacts/`
into the tracked ledger the same day each was created, and the `deferred_work_check.py`
detector born from the finding above immediately found five more damped
recommendations across three *other* projects (atlas, marshal, warden) — evidence
the rule generalizes past the case that motivated it.

A2, A3, A7 status is unchanged by Wave H/I evidence and stays open per the
Actions table above.
