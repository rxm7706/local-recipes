---
title: The review bot remembers the correction you gave two weeks ago
type: dream
owner: marshal
status: dreamt
fold-exemption: cross-station-seam   # sits at the marshal (loop orchestration) / scribe (memory ownership) seam by design -- neither station's chain alone owns it, matching pyforge-core's own cross-station-seam precedent
---

# The review bot remembers the correction you gave two weeks ago

## The Dream

Scribe already captures corrections and feedback (`feedback` / `project` /
`reference` capture types) and can answer a grounded `recall` query — never
inventing an uncited answer, explicit about a real miss. That primitive is
shipped, real, a complete BMAD project.

What it doesn't do yet is reach forward on its own. A correction captured
today doesn't automatically show up in the next `bmad-loop` dev pass working
nearby code, and it doesn't automatically show up in the review pass grading
that work either — both still start from a blank context unless a human (or
this session, by hand) remembers to run `scribe recall` first and paste the
result in. The memory exists; the propagation into every future session that
should see it does not.

This is not identity-scoped citation (that's already real —
[[scribe-marshal-fact-visibility]] lets `recall` cite a project's own
`facts.yaml` under its own scope) and it's not token-compression (that's
[[marshal-token-economy]]'s `derived-context` layer, which recomputes
codebase/planning *structure* when its sources change — a different kind of
staleness than "a human corrected an agent and nobody downstream heard
about it").

## What it looks like when real

- Before a `bmad-loop` dev pass or review pass starts a story, it queries
  `scribe recall` scoped to the story's touched surface/station, and any
  relevant feedback entries fold into that session's starting context
  automatically — no human has to remember to run it.
- Composes with the existing `[context]` pipeline (`wire` / `output` /
  `structure-graph` / `derived-context` / `planning-graph`) as its own layer,
  rather than becoming a sixth ad hoc mechanism bolted on beside it.
- `recall`'s own honesty is preserved end to end: a genuine miss injects
  nothing, never a fabricated "no relevant corrections found" confidence
  the agent didn't earn.
- Stays within the same token-economy discipline the rest of the pipeline
  already answers to — this is a context layer, not an unbounded reread.

## Constraints / Non-goals

- Does not change what scribe *captures* — that surface is already built and
  correct.
- Does not replace human review or lower its bar; it feeds the review pass
  more of what it should already have known, not less scrutiny.
- Not a general RAG-everything layer — scoped to the same
  feedback/correction material scribe already curates, not a blanket
  full-repo retrieval pass.

## Kinships

[[pyforge-marshal]] · [[pyforge-scribe]] · [[marshal-token-economy]] ·
[[scribe-marshal-fact-visibility]]
