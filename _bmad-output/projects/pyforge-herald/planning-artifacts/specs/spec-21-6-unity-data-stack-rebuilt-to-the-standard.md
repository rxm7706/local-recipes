---
title: 'unity-data-stack rebuilt to the standard'
type: 'feature'
created: '2026-09-15'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - 'presentations/unity-data-stack/README.md'
  - 'docs/specs/presentation-deck.md'
  - '_bmad-output/projects/pyforge-herald/planning-artifacts/epics.md'
  - 'presentations/pyforge-warden/README.md'
  - 'src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py'
  - 'src/shared/packages/pyforge-herald/src/pyforge/herald/registry.py'
  - 'src/shared/packages/pyforge-herald/src/pyforge/herald/state.py'
warnings: []
deferred:
  - '2026-09-17: `Unity Data Stack Infographic standalone.html` is corrupted (72x space-separated boilerplate repeat, char offset 6350-142949, from commit e483288d54f) and was NOT pushed to Design. Blocked on a content fix + re-verification before push+read-back can complete. The other four `project/` files were verified already byte-identical to Design; no push was needed for them.'
declared_low_risk: false
verdict_mode: advisory
baseline_revision: '548919f73eb453d08198391bea8682b8a1bd575b'
---

<intent-contract>

## Intent

**Problem:** `presentations/unity-data-stack/project/Unity Data Stack Infographic standalone.html` was a July stub below the infographic standard (no act bands, no diagrams, no fact ledger).

**Approach:** Derive `facts.yaml` with `deck-facts unity-data-stack`. Author the standalone poster to `infographic-standard.md` from that ledger only. Design push is out of scope for this Cursor pass.

## Boundaries

**Always:** Every count, version, status and date is a `data-fact` mark. Six acts, at least eighteen sections, three SVGs, three tables, at least ninety thousand bytes. Package and CLI rows absent by design.

**Never:** Never hand-edit `facts.yaml`. Never invent a spec capability count. Never push to Design from this worktree.

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-authored 2026-09-15 in worktree `local-recipes-wt-herald-epic-21-wave-c-chain-decks`.

**Local acceptance:** `deck-facts unity-data-stack --check` reports 0 unmarked / 0 mismatch; floors met; README ledger carries `PENDING-PUSH`.

**Not accepted here:** push and read-back.

## Spec Change Log — 2026-09-17

The `deferred` item above ("Design push and byte-identical read-back still require Claude
Design") is resolved: Story 21.12 (`spec-deck-family-lockstep` CAP-6) fixed the `mcp` SDK
transport symbol drift that blocked every push, verified live in Story 21.4 (ten PyForge decks
pushed and read back byte-identical, PRs #1394–#1403). The intent-contract's "Never push to
Design from this worktree" boundary was written against the authoring worktree named in
Execution above (now torn down) at a time push was mechanically impossible; it is not a
permanent prohibition on Story 21.6's own AC, which the epics.md Given/When/Then always included
("is pushed and read back byte-identical"). This pass, from a fresh worktree, completes that
remaining AC using the same `McpTransport` direct-call approach Story 21.4 proved (`finalize_plan`
→ `write_files` with inline `data`; `herald deck push`'s CLI verb and `write_files`' `local_path`
field don't cover `project/*.dc.html` trio files).

**Push+read-back acceptance:** every file in `presentations/unity-data-stack/project/` that
Design's `list_files`/`get_file` doesn't already show byte-identical is pushed via `write_files`
inline `data`; every pushed file is read back via `read_file` and SHA-256-compared byte-identical
against disk; `presentations/unity-data-stack/README.md`'s Design-project table/Ledger records the
new etags and push date, and no longer carries `PENDING-PUSH` for files actually pushed.

## Auto Run Result

Status: blocked
Blocking condition: `Unity Data Stack Infographic standalone.html` (145,176 B) is corrupted on
disk — 72 verbatim repeats of a boilerplate fleet-status paragraph, every character
space-separated, from character offset 6,350 through 142,949, overwriting nearly the entire body.
Traced to commit `e483288d54f`. Not pushed to Design (confirmed live: Design's copy is still the
untouched 18,588 B pre-rebuild July stub). The other four `project/` files
(`Unity Data Stack.dc.html`, `- Executive Summary.dc.html`, `- Infographic.dc.html`,
`- Infographic Deck.dc.html`) were verified byte-identical between disk and Design already — no
push needed for those. Sibling stories 21-7 (wasm-analytics-stack) and 21-8 (deckcraft) carry the
same `blocked` status in the Tier-3 feed for the same commit's corruption; 21-9
(presenton-pixi-image) independently found and reported it too. Unblocking this story requires
regenerating the standalone poster's content correctly from `facts.yaml` (not a revert — the
prior commit's version is the pre-standard July stub) and re-verifying before push+read-back is
retried.

## Spec Change Log — 2026-09-17 (cont'd) — BLOCKED, corrupted standalone found

Executed the push+read-back pass. `list_files` on Design project `0494e2b0-7132-43b7-8ff2-4b4b42fa8384`
showed all five `project/` files already present. `read_file` + SHA-256 comparison against disk
(decoding the wrapper's `&lt;`/`&gt;`/`&amp;` entities in that order, per `mcp_transport.py`'s
`_decode_entities`) confirmed **`Unity Data Stack.dc.html`, `- Executive Summary.dc.html`,
`- Infographic.dc.html`, and `- Infographic Deck.dc.html` are already byte-identical** to disk
(hashes `46349813a6f7…`, `595a3900b8d9…`, `2ead3e671a11…`, `227dfc6926f5…` respectively) — **no
push was needed or performed for these four.**

Before pushing `Unity Data Stack Infographic standalone.html`, a sibling agent (Story 21.9,
presenton-pixi-image) and the coordinator independently reported the same defect had been found in
several `Wave C`-rebuilt standalone posters from commit `e483288d54f` ("Rebuild the four chain-deck
posters from their fact ledgers", 2026-09-15). **Independently re-verified live against this
repo's own working tree:** `presentations/unity-data-stack/project/Unity Data Stack Infographic
standalone.html` (145,176 bytes total) is corrupted starting at character offset **6,350** through
**142,949** — a boilerplate fleet-status paragraph beginning "The factory already runs a tracked
fleet: stories 930 of 998 and epics 207 of 225. BMAD core …" repeats **72 times**, with every
character of each repeat space-separated (`T h e   f a c t o r y …`), overwriting nearly the
entire body that should hold the deck's own six-act unity-data-stack content. Sample bytes at the
corruption boundary: `...on this ledger: <span data-fact="dream_log_2026-07-23">2026-07-23</span>.
</p><p>T h e   f a c t o r y   a l r e a d y ...`. `deck-facts unity-data-stack --check` does **not**
catch this — it validates `data-fact` span presence/values only, not prose sanity, so the
README's recorded "0 unmarked / 0 mismatch" from the 2026-09-15 rebuild is **not** evidence the
file is clean.

**Per coordinator + sibling-agent course correction: the corrupted standalone was NOT pushed to
Design.** Design's own copy of the standalone (`18,588` bytes, the pre-rebuild July stub) is
untouched and remains stale-but-uncorrupted. Design's four other files are confirmed genuinely
already in sync with disk (see hashes above) — nothing needed pushing there either, corrupted or
not. This story is **blocked** on a fix to the standalone poster's content (regenerating it
correctly from `facts.yaml` against the infographic-standard authoring, not a `git revert` — the
prior commit's version is the pre-standard July stub, not a clean copy of the intended rebuild)
before push+read-back can be attempted again. The same generation defect likely affects the
sibling `wasm-analytics-stack` and `deckcraft` standalone posters from the same commit (per the
coordinator's report); this spec does not attempt a fix — that is remediation work for a follow-up
story/PR, mirroring Story 21.9's approach (document, no push).
