---
title: 'unity-data-stack rebuilt to the standard'
type: 'feature'
created: '2026-09-15'
status: 'done'
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
  - 'archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md'
  - 'archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/constitution-provenance.md'
  - 'archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-unity-data-stack-2026-07-25/prd.md'
  - 'docs/dreams/unity-data-stack.md'
warnings: []
deferred: []
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

Status: done
Reconciled 2026-09-20: the `blocked` verdict below is the session's own record at halt time; the story was landed afterwards and the ledger row promoted to `done` by `4098c5ed3b 2026-09-17 herald: rebuild unity-data-stack standalone infographic content (Story 21.6)` — that promotion is the ruling this record now reflects.
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

## Spec Change Log — 2026-09-17 (cont'd) — content rebuilt, verified, pushed, DONE

**Root cause note.** The prior corruption was traced to a generation defect in commit
`e483288d54f`, not to anything about this poster's design or its `facts.yaml`. `facts.yaml` itself
(32 facts, tree `506ad58622`) was untouched and used as-is, per the boundary this spec's own Never
clause already set.

**Content.** Kept bytes `[0, 6347)` of the on-disk file byte-for-byte — the confirmed-real header,
stat strip, Act I band, and the opening of Section 01 up through the `dream_log_2026-07-23` fact —
and authored everything from that point forward fresh. Source material: the Dream
(`docs/dreams/unity-data-stack.md`), the archived canonical Spec and its
`constitution-provenance.md` companion (both under
`archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/` — the
path this story's own frontmatter named, `_bmad-output/projects/unity-data-stack/...`, does not
exist; the chain was consolidated into Atlas on 2026-08-02, see `docs/dreams/unity-data-stack.md`'s
own superseded-notice), and the archived PRD
(`archive/.../prds/prd-unity-data-stack-2026-07-25/prd.md`) for its FR-by-FR provenance/delta
findings, Jobs To Be Done, four Key User Journeys, full Glossary, Cross-Cutting NFRs, Risk register,
and complete thirteen-metric Success Metrics catalog — all read for narrative color per this
Spec's own "consult sources for prose color the contract intentionally omits" allowance, none of
it contradicting the canonical archived SPEC.md.

**Shape delivered:** 32 sections (floor: 18), six Act bands (I–VI, matching the existing Act I),
3 inline SVG diagrams (the three-gists-converge diagram, the Raw→Curated→Consumption layer
diagram, the AD-17 station map), 15 tables (floor: 3), 95,360 bytes total (floor: 90,000). No
package/CLI rows, matching the "chain has no station package" design boundary. Every count/version/
status/date shown is a `data-fact` span over a `facts.yaml` row — four values with no ledger row
(the Constitution's `1.2.0` version stamp, the intake root's broken `0.59.0` pixi pin, and the
Dagster `1.12.0`/`1.13.15` floor-vs-current pair) were reworded to convey the same finding without
stating the bare version number as visible text, rather than inventing a data-fact row for them.

**Verification actually performed (not just `deck-facts --check`):**
1. `pixi run -e local-recipes deck-facts unity-data-stack --check` — 0 unmarked, 0 mismatch (12
   drifted / 7 unshown, both expected and outside this AC: `facts.yaml` was deliberately not
   touched, so fleet-progress rows drift the moment any other station's ledger moves).
2. Read the rebuilt file back in full and confirmed by eye: 32 distinct section titles, six
   distinct Act themes, no repeated sentence, no boilerplate — the specific failure mode of the
   prior corruption. Confirmed zero occurrences of the corruption's own signature strings
   (`"The factory already runs a tracked fleet"`, the space-separated `"T h e   f a c t o r y"`
   pattern) anywhere in the rebuilt file.
3. `html.parser`-based tag-balance check: 0 errors, 0 unclosed tags at EOF.
4. Headless Chromium render (Playwright) at 1240px width: `scrollWidth` exactly 1240 (no
   horizontal overflow), 0 overflowing elements, 0 near-empty sections, DOM counts confirm 32
   sections / 3 SVGs / 15 tables / 6 act bands. Five region screenshots (top/header, first SVG,
   first table, station-map SVG, closing band) visually reviewed — clean typography, correct
   zebra striping, both diagrams and the closing Creed band render as intended.

**Push + read-back.** `.herald/bridge-state.json` bootstrapped for this checkout (`state.write`
directly, since `registry.read` on this project's own README fails — see Known issue below).
`list_files` on Design project `0494e2b0-7132-43b7-8ff2-4b4b42fa8384` confirmed the standalone was
still the untouched pre-rebuild `18,588`-byte July stub at etag `1785023542254041` — a first push,
not a corrective one, as expected. Pushed via `pyforge.herald.transport.mcp_transport.McpTransport`
directly (`finalize_plan` → `write_files` with inline `data`, reading the local file into the
running Python process rather than the CLI-side text path, since 95 KB safely clears `write_files`'
practical limits but not a reasonable manual-transcription budget) — `herald deck push`'s CLI verb
and `write_files`' `local_path` field cover neither this file's push mechanics. New etag
`1789645202687610`. Read back whole via the same transport's `read_file` (95,360 bytes,
`truncated=False`, under the 256 KB cap) and compared SHA-256 against disk:
`a2a1665ce041a491a26d5484d874ae2e587b0300a9afbf74691b17652de597cc` on both sides — **byte-exact.**

**Known issue found, not fixed here (out of this story's scope):** `presentations/unity-data-stack/README.md`'s
`## Design project (the bridge's far end)` section has grown past the canonical two-line
machine-owned shape (it carries the seed table and both Ledger sub-sections directly beneath, with
no `### Provenance` sub-heading bounding them), so `pyforge.herald.registry.read()` raises
`HeraldError: ... expected exactly two body lines, found 21`. Bootstrapping bridge-state.json for
this deck required calling `state.write()` directly with the known project id rather than routing
through `registry.read()`. The README ledger update below adds a `### Provenance` sub-heading to
bring this file into the canonical shape going forward; whether other decks' READMEs have the same
drift is unverified.

**Sprint ledger.** No `_bmad-output/projects/pyforge-herald/implementation-artifacts/` existed in
this worktree (Tier-3, gitignored, never materialized here). Created
`implementation-artifacts/sprint-status.yaml` carrying the full 147-key map read off the tracked
twin via `fleet_scan.parse_sprint_status` (same parser both sides use, so no second parser to
drift) with `21-6-unity-data-stack-rebuilt-to-the-standard` moved `blocked` → `done`, then ran
`python scripts/promote_sprint_status.py --project herald`: `wrote 1, unchanged 0, skipped 0,
refused 0`. `epic-21` correctly stayed `in-progress` (its rollup, recomputed from all child
stories, not just this one).

## Status reconcile 2026-09-20

- Auto Run Result `Status: blocked` → `done` (see the reconcile line under it).
