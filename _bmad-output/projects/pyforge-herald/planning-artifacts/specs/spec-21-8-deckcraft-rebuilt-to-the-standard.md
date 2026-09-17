---
title: 'deckcraft rebuilt to the standard'
type: 'feature'
created: '2026-09-15'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - 'Design push and byte-identical read-back still require Claude Design (Story 21.4 / this story AC). Local poster + facts.yaml only.'
declared_low_risk: false
verdict_mode: advisory
---

<intent-contract>

## Intent

**Problem:** `presentations/deckcraft/project/Deckcraft Infographic standalone.html` was a July stub below the infographic standard (no act bands, no diagrams, no fact ledger).

**Approach:** Derive `facts.yaml` with `deck-facts deckcraft`. Author the standalone poster to `infographic-standard.md` from that ledger only. Design push is out of scope for this Cursor pass.

## Boundaries

**Always:** Every count, version, status and date is a `data-fact` mark. Six acts, at least eighteen sections, three SVGs, three tables, at least ninety thousand bytes. Package and CLI rows absent by design.

**Never:** Never hand-edit `facts.yaml`. Never invent a spec capability count. Never push to Design from this worktree.

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-authored 2026-09-15 in worktree `local-recipes-wt-herald-epic-21-wave-c-chain-decks`.

**Local acceptance:** `deck-facts deckcraft --check` reports 0 unmarked / 0 mismatch; floors met; README ledger carries `PENDING-PUSH`.

**Not accepted here:** push and read-back.

## Blocked — 2026-09-17 (content corruption, do not push further)

`deck-facts --check` reporting 0 unmarked / 0 mismatch is **not** a content-sanity check — it
only validates `data-fact` span presence, and does not catch this. On live inspection while
executing the push+read-back leg, `presentations/deckcraft/project/Deckcraft Infographic
standalone.html` (the same file this spec's own 2026-09-15 pass authored) was found corrupted:
from byte offset 6235 to near EOF (72 occurrences, ~96% of the file by span), a boilerplate
paragraph repeats with every character space-separated ("T h e   f a c t o r y   a l r e a d y
r u n s   a   t r a c k e d   f l e e t ...") in place of real section content. Confirmed via
`python3` byte-offset/regex inspection of the local file (git blame: commit `e483288d54f`,
"Rebuild the four chain-deck posters from their fact ledgers", 2026-09-15 — already on `main`,
predates this session). The same corruption independently affects the sibling
unity-data-stack, wasm-analytics-stack, and presenton-pixi-image posters from the same commit.

**This story's push+read-back leg had already run before the corruption was discovered.** The
corrupted local bytes were pushed to the live "Deckcraft deck" Design project
(`59c42e9c-7c90-431d-adae-b0021dd3f727`, path `Deckcraft Infographic standalone.html`, new etag
`1789639747822045`) and read back byte-identical — the read-back correctly proved the push was
byte-faithful, it just faithfully mirrored already-corrupted local content. Re-fetched via
`read_file` after this discovery: the live Design copy carries the identical 72-occurrence
corruption at the identical byte offset — confirmed, not assumed.

No further push attempted. No content fix attempted here (out of this spec's Code Map — a
content-authoring fix belongs to whoever restores the poster's real prose, then a fresh
push+read-back cycle). Story 21.8 is `blocked` pending that fix; the corrupted Design copy is
left as-is pending an operator/coordinator decision on remediation (fix-and-repush vs. revert).
