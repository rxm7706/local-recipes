---
id: SPEC-marshal-recall-in-the-loop
spec: marshal-recall-in-the-loop
status: draft
owner-dream: docs/dreams/marshal-recall-in-the-loop.md
fold-exemption: cross-station-seam   # marshal (loop orchestration) / scribe (memory ownership) seam by design -- mirrors spec-pyforge-core's own precedent
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py   # provisional -- net-new injection point, not yet built; exact hook TBD by architecture
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py                        # read-only dependency; this Spec never edits scribe's own recall grounding rules
companions: []
sources:
  - ../../../../../../docs/dreams/marshal-recall-in-the-loop.md
updated: '2026-09-18'
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. `owner-dream` is for traceability — consult it only for narrative rationale this contract intentionally omits.

# The review bot remembers the correction you gave two weeks ago

## Why

A pain already diagnosed, not a fresh idea: scribe's capture/recall primitive is real, shipped, a complete BMAD project — but it doesn't reach forward on its own. A correction captured today doesn't automatically show up in the next `bmad-loop` dev pass working nearby code, and it doesn't automatically show up in the review pass grading that work either; both still start from a blank context unless a human remembers to run `scribe recall` first and paste the result in. Named directly from "Towards Self-Driving Codebases" (blog.detail.dev): "the code review bot needs to be aware of the correction you issued to the agent... two weeks ago." The memory exists; the propagation into every future session that should see it does not. This sits at the marshal (loop orchestration) / scribe (memory ownership) seam by design — `fold-exemption: cross-station-seam`, mirroring the existing `spec-pyforge-core` precedent.

## Capabilities

- **CAP-1**
  - **intent:** Before a `bmad-loop` dev pass (`bmad-dev-auto`) starts a story, it queries scribe recall scoped to the story's touched surface/station, and any relevant feedback entries fold into that session's starting context — no human has to remember to run recall first.
  - **success:** Given a scribe feedback entry scoped to a station/surface a new story touches, that story's dev-pass session context includes it without a manual recall invocation; given no relevant entry exists, nothing is injected.
- **CAP-2**
  - **intent:** The review pass (opus, `trigger=recommended`) receives the same scoped scribe-feedback context CAP-1's dev pass got, so a correction from a prior session is visible to whoever grades the new work, not just the agent that wrote it.
  - **success:** Given CAP-1 injected a feedback entry into the dev pass, the review pass for the same story sees the same entry; a review that contradicts a known, injected correction is a visible discrepancy, not a silent miss.
- **CAP-3**
  - **intent:** CAP-1/CAP-2's injection composes with marshal's existing `[context]` pipeline (`wire`/`output`/`structure-graph`/`derived-context`/`planning-graph`) as its own named layer, not a bolted-on side mechanism outside that discipline.
  - **success:** The layer has its own `[context.<name>]` `enabled`/`aggressiveness` toggle, matching the existing five; disabling it removes the injection with no effect on the other five layers.
- **CAP-4**
  - **intent:** Scribe recall's own honesty (a grounded miss is explicit, never an invented uncited answer) is preserved end to end through the injection path — a query with no relevant hits adds nothing to context, never a synthesized "no relevant corrections found" line presented as if it were a checked fact.
  - **success:** Given a scoped recall query with zero hits, the injected context block is empty/absent, not a generated null-result sentence.

## Constraints

- Scribe stays the sole owner of capture and compile — this Spec adds a read-only consumer of scribe recall, never a second capture path, never a change to recall's own grounding rules (`recall.py` stays authoritative on what counts as a citable hit).
- Stays inside marshal's existing token-economy discipline — CAP-1/CAP-2's injected context is scoped (not a full-repo pull) and counted the same way the other five `[context]` layers already are (budget ceilings, per-story/per-run weighted-token accounting), never an unbounded reread.

## Non-goals

- Not a general RAG-everything layer — scoped strictly to the feedback/correction material scribe already curates (capture types `feedback`/`project`/`reference`), never a blanket full-repo retrieval pass added on top.
- Does not replace or lower the bar for human review — the review pass gets more of what it should already have known, not less scrutiny or an automated approval path.
- Does not change what scribe captures or how — capture-side behavior (the `feedback`/`project`/`reference` types, the promotion workflow) is out of scope; this Spec is a consumer only.

## Success signal

An operator stops needing to manually run `scribe recall` and paste results into a dev/review session before it starts on touched-before territory. A review pass catches (or does not silently repeat) a mistake scribe already has a captured correction for, without the operator re-supplying it by hand. Recall's grounded-miss honesty is unbroken by the injection path — verified by an empty-hit case producing no injected text.

## Assumptions

- Marshal is the correct primary owner (this Spec lives in `pyforge-marshal`'s planning tree, `fold-exemption: cross-station-seam`) because the injection point is marshal's own dev/review pass orchestration, even though the data being injected is scribe's — mirrors the existing `spec-pyforge-core` precedent (kernel/testing-kit, marshal-owned, cross-station-seam) named in the source Dream's Kinships.

## Open Questions

- Exact scope mechanism for CAP-1/CAP-2's recall query is unresolved — the Dream says "scoped to the story's touched surface/station" but does not pin down whether this reuses `--scope <slug>` the way marshal's planning-graph retrieve already does (per `scribe-marshal-fact-visibility` CAP-1), or needs a narrower per-touched-file-glob scope. Left for architecture.
- Whether this applies only to unattended `bmad-loop` runs or also to `bmad-build-auto` single-story dispatch sessions is unaddressed — the source Dream names only "bmad-loop dev pass and review pass." Left open.
- Default aggressiveness/token-budget for the new `[context]` layer, and how it interacts with `session_budget_mode` (off/warn/enforce), is not specified in the source Dream. Left for architecture to size against the existing five layers' own defaults.
- Whether a NEW correction a review pass itself surfaces (not previously in scribe) should auto-capture back into scribe, closing the loop end to end, or stays a manual `scribe capture` step afterward — the Dream describes propagation forward (memory to agent) but not this reverse direction. Left open; likely a separate capability if pursued.
