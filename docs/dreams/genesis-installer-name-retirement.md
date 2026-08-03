---
title: Retire genesis-installer — one marshal CLI, one PRD/architecture/epics chain
type: dream
owner: marshal
status: dreamt
---

# Retire genesis-installer — one marshal CLI, one PRD/architecture/epics chain

## The Dream

The 2026-07-28 Charter §5 split carved `genesis-installer` out of `pyforge-genesis` as
its own Dream, and the 2026-08-02 consolidation folded its brief/PRD/architecture/Spec
into `pyforge-marshal`'s own single chain — but as **satellite sections**: "Satellite:
Genesis Installer PRD," its own `FR1..FR62` numbering deliberately kept apart from
Marshal's own `FR-1..FR-65` ("distinct namespaces inside the one merged PRD," by explicit
prior override), and `epics-genesis-installer.md` left as a second, separate epics
document — the one thing that stayed fully unmerged.

That separateness leaked onto the fleet dashboard: the build-campaign section showed
`genesis-installer` as if it were still its own project, with its own row and its own
epics link, next to `pyforge-marshal`'s. A same-day stopgap (dashboard PR #233) labeled
both rows with their epic range so the split at least read as intentional — but the user
wants the split gone, not labeled: `genesis-installer` is not a second thing, it is
Marshal's own Epics 7-12, and every trace of it as a separate name or numbering island
should retire. `AD-51..65` and `CAP-10..18` already got this right — they continue
Marshal's own `AD-1..50`/`CAP-1..9` sequences with no separate namespace. `FR` did not:
the satellite section's `FR1..FR62` (no dash) needs to become `FR-66..FR-127` (with
dash), continuing Marshal's own sequence the same way AD and CAP already do. The smaller
installer-only namespaces — `NFR-O1`, `SC-01..SC-10`, `OQ-1..OQ-9`, `K-01..K-03` — need
the same treatment, folded into or reconciled against Marshal's own equivalent
numbering (`NFR-1..14`, however Marshal's PRD labels success criteria, `Q-1..Q-16`).

**Scope widened (2026-08-02, same session): this is not just a renumbering exercise.**
The mechanical "fold in" consolidation preserved two unresolved contradictions rather
than resolving them, because folding is a copy-and-renumber operation, not a design
pass: (1) Marshal's own CLI is **argparse**, already shipped (Story 1.1's
`core/{model,findings,verdict}.py` + `cli/`), while the installer satellite's own
architecture specifies **typer + rich** for its still-unbuilt CLI — one framework must
win for the one binary both live in. (2) `genesis init` collides head-on with the
already-shipped `marshal init <slug>` (loop-home provisioning), and a second collision
surfaced between `marshal check` (FR-65/AD-50, shipped, routes to
`scripts/detectors.py`'s registry) and the installer's own `check` verb (CAP-13,
answers a different question — does an *externally installed* repo still conform).
Manually renumbering IDs while leaving these open would produce one clean-looking
numbering space still describing two CLIs that don't agree on a framework or a verb
surface. The real fix is to **run the standard planning chain** —
`bmad-prd` → `bmad-architecture` → `bmad-create-epics-and-stories` — against the
already-unified Spec, so the CLI gets designed once, coherently, with these
contradictions actually decided rather than carried forward as open questions. This
supersedes the narrower "just renumber the IDs" approach as the Dream's primary target;
the renumbering above is what a clean rewrite produces as a side effect, not a thing to
hand-execute separately.

## What it looks like when real

- One `epics.md` under `pyforge-marshal`'s planning-artifacts, Epic 1 through Epic 12,
  no separate `epics-genesis-installer.md` file (its content merged in, archived not
  deleted).
- One FR space, contiguous, no bare-digit `FR62`-style leftover anywhere live, produced
  by the planning chain rather than hand-renumbered.
- `NFR-O1`/`SC-01..10`/`OQ-1..9`/`K-01..03` folded into or reconciled with Marshal's own
  equivalent sequences, not left as a second unlabeled island.
- Every "Satellite: Genesis Installer PRD/Architecture" section header, and every prose
  mention of "genesis-installer" as if it names a separate thing, gone — the content
  stays (as ordinary Marshal capability), the name doesn't.
- **The CLI framework contradiction is decided** (argparse — Marshal's own, already
  shipped — or a migration to typer+rich, but not both left standing) and **the verb
  collisions are resolved**: one `init`, one `check`, with the installer's distinct
  question ("does an externally installed repo still conform?") given its own verb name
  if `check` stays Marshal's own detector-registry route.
- The dashboard's build-campaign section shows one `pyforge-marshal` row (86 stories
  total across Epics 1-12), no second `genesis-installer` row.
- No citation left dangling: every FR/NFR/SC/OQ/K cross-reference across the PRD,
  architecture (`binds` fields), Spec (capability intent/success text), the epics
  document's acceptance criteria, and any gates/readiness report is internally
  consistent with the new chain.
- `.memlog.md` history and `archive/` content are untouched — the chain regenerates
  live, current documents; it never rewrites the historical record of how they got
  here.

## What is real

Investigated 2026-08-02, not yet acted on:

- `AD-51..65` and `CAP-10..18` are **already** unified with Marshal's own `AD-1..50`/
  `CAP-1..9` — no renumbering needed for those two namespaces.
- **Confirmed by a dedicated research pass (2026-08-02, full map in
  `spec-genesis-installer-name-retirement/citation-map.md`)**: `FR1..FR62` (installer's
  own, no dash) is the one requirement namespace not yet unified, and the sequence is
  gap-free and duplicate-free in strict ascending order — the natural sequential map
  `FR1 -> FR-66` … `FR62 -> FR-127` is valid as a starting point (the rewrite may still
  choose to reorder by topic). One caution: `FR-66..FR-69` were briefly claimed and
  reverted by an unrelated fold attempt the same day — free today, already used once.
- Three smaller installer-only namespaces still need a decision, not a mechanical
  renumber, and the research pass corrected this Dream's own original assumption about
  them: `NFR-O1` (single item) is likely redundant with Marshal's own `NFR-12`
  (near-identical substance); `SC-01..SC-10` and `K-01..K-03` (Kill criteria — the
  falsifiers of the installer's own Success Criteria) have **no existing Marshal
  namespace to fold into at all** — Marshal's PRD uses `SM-1..7`/`SM-C1..3`, never
  `SC-`, and has no kill-criteria concept; `OQ-1..OQ-9` against Marshal's own
  `Q-1..Q-16` — **corrected**: Marshal's sequence stops at `Q-16`, `Q-17` does not exist
  live anywhere, and no `OQ-*` item is actually cross-referenced into any Marshal
  `Q`-number (this Dream originally claimed otherwise; the claim wasn't borne out).
- Dashboard PR #233 (merged 2026-08-02) is the stopgap this Dream supersedes: it labeled
  the row split ("epics 1-6" / "epics 7-12") rather than removing it.

## Constraints

- **Never rewrite `.memlog.md` history or `archive/` content.** Both are the permanent,
  append-only record of how the consolidation actually happened; renumbering touches
  only live, current documents.
- **Story/epic identifiers never change.** `sprint-status-ledger.yaml`'s keys
  (`7-1-...`, `8-1-...`, etc.) and the epic numbers themselves (1-12) stay exactly as
  they are — only prose citation numbers (FR/NFR/SC/OQ/K) and section headers change.
  The active bmad-loop dev session depends on story-key stability.
- **Hold execution until the loop is clear.** A bmad-loop run against `pyforge-marshal`
  (Story 2.1, run `20260802-183704-36df`) was in flight when this Dream was captured;
  the user asked explicitly to spec this rather than edit the live planning tree while
  it runs, even though the loop-home is an isolated worktree/branch and unlikely to
  read these specific files for Story 2.1's own (Epic 2) work. **Confirmed again at the
  wider scope**: the full `bmad-prd`/`bmad-architecture`/`bmad-create-epics-and-stories`
  regeneration waits until Story 2.1's run is fully done and merged — epics.md is
  exactly what the active run's story identity (`sprint-status-ledger.yaml`) keys off
  of, and a chain rewrite is a bigger blast radius than the narrower renumbering this
  Dream started as.

## Non-goals

- Not touching `AD-51..65` or `CAP-10..18` — already unified, no action needed.
- Not a new BMAD project — this is cleanup inside `pyforge-marshal`'s own planning tree,
  same shape as `bmad-output-hygiene` and `dashboard-project-path-derivation`.

## Realization log

- **2026-08-02** — Captured after the user flagged the dashboard's `genesis-installer`
  row as still reading as a separate project even after PR #233 labeled the split, and
  asked to remove the name and reference completely rather than just label it. Offered
  three depths (dashboard+epics merge only / add prose section-title cleanup / full ID
  renumbering); user chose the full renumbering. User then asked to formalize this as a
  Dream and Spec rather than editing the live planning tree directly while the Story 2.1
  bmad-loop run is active — execution deferred to whenever the Spec is run.
- **2026-08-02 (scope widened)** — User asked to do "the entire marshal dream to spec /
  PRD / architecture chain / epic / story rewrite... so that genesis goes away and the
  marshal cli is built correctly" — reframing this from a manual FR-renumbering exercise
  to running the standard planning chain (`bmad-prd` → `bmad-architecture` →
  `bmad-create-epics-and-stories`) against the already-unified Spec, so the CLI framework
  contradiction (argparse vs typer+rich) and the verb collisions (`init`, `check`) get
  actually decided instead of carried forward. Sequencing confirmed: draft the Spec now
  (planning only, no live edits), hold the full chain regeneration until Story 2.1's
  bmad-loop run is done and merged.
- **2026-08-02 (Spec drafted, research complete)** — `spec-genesis-installer-name-retirement`
  written to `pyforge-marshal`'s planning tree (8 capabilities, self-validate PASS both
  passes). A dedicated citation-map research pass ran alongside it and confirmed the
  FR1..FR62 → FR-66..FR-127 mapping is valid, while **correcting this Dream's own
  original premise** that Marshal's Open Questions run to `Q-17` with `OQ-*` items
  already feeding it — the live sequence stops at `Q-16` and no such cross-reference
  exists. Also surfaced that Marshal has no existing `SC-`/kill-criteria namespace at
  all (not "unclear," genuinely absent), narrowing CAP-3 from a reconciliation to an
  adoption decision. Full map: `citation-map.md`, a companion of the Spec. Zero live
  edits to the PRD/architecture/epics themselves — execution stays deferred until
  Story 2.1's run clears, per the Spec's constraints.
