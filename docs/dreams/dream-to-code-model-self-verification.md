---
title: The Dream-to-Code model has never verified itself
type: dream
owner: marshal
status: archived
---

# The Dream-to-Code model has never verified itself

> **Consolidated into [[pyforge-marshal]] on 2026-08-08** (§ *Eight more, consolidated
> here*). This file is archived in place: its **Spec stays live and remains the
> contract** — archiving the Dream tier never retires the chain below it. Kept, not
> deleted, so the reasoning that produced the Spec is still readable.

## The Dream

The Dream-to-Code model — Tier 0 Dreams motivating a Tier 2 Spec, decomposed
into PRD/architecture/epics, driving code, with `scripts/dream_chain_check.py`
enforcing the chain per `_bmad-output/EXEMPLAR-STANDARD.md` — was itself
established by a restructure (2026-07-23) rather than born through its own
pipeline. Two follow-ups from that restructure were named at the time and
never built: a `dream_chain_check.py --dreams` mode, and running `bmad-spec`
against the model's own governing documents (dogfooding). Both are still
genuinely open — confirmed live: `dream_chain_check.py --help` lists only
`--json` and `--inv`, no `--dreams` flag exists anywhere in the script; no
`spec-dream-to-code*` (or equivalently named) folder exists anywhere under
`_bmad-output/projects/*/planning-artifacts/specs/`.

Neither gap is urgent — `dream_chain_check.py`'s existing INV-1/2/3 checks
already do real chain-completeness enforcement, and the model plainly works
today (52 Dream files, 43 Specs, this session alone produced 5 new Dreams
through the process the model itself defines). But two things the model's
own restructure promised remain unbuilt, and nothing since has revisited
them — this Dream exists so they don't stay permanently deferred by default.

## What it looks like when real

- `dream_chain_check.py` gains a mode (`--dreams`, or folded into an existing
  `--inv` value) that specifically validates **Dream file hygiene** — status
  vocabulary correctness, `owner:` attribution, frontmatter completeness — as
  distinct from the chain-completeness checks INV-1/2/3 already run. (Concrete
  scope TBD at spec time: the exact boundary between "chain completeness"
  and "dream hygiene" needs deciding, not assumed here.)
- A Spec exists for the Dream-to-Code model itself — produced by running
  `bmad-spec` against `docs/dreams/README.md` / `AGENTS.md` § the tiers /
  `_bmad-output/EXEMPLAR-STANDARD.md`, proving the model can specify itself
  the same way it requires every station and deliverable to be specified.
  Whether this Spec lives under a station (marshal, since it owns the
  drift-check tooling) or in `docs/governance/` alongside the Charter/Lexicon
  kernels (since the model is arguably constitutive, not a single station's
  product) is an open question this Dream does not resolve.

## What is real

- Confirmed 2026-08-03: `dream_chain_check.py --help` shows no `--dreams`
  flag. The script's only filters are `--json` and `--inv {INV-1,INV-2,INV-3}`.
- Confirmed 2026-08-03: no dogfooded Spec for the model exists anywhere —
  `find _bmad-output -iname "*dream-to-code*"` returns nothing.
- The restructure that named both follow-ups (2026-07-23) is recorded only
  in auto-memory (`project_dream_to_code_model.md`), not in any tracked Dream
  file — this Dream is that follow-up's first tracked, git-visible home.

## Constraints

- Whatever `--dreams` mode is built must not duplicate INV-1/2/3's existing
  coverage — read them first (`scripts/dream_chain_check.py`) before deciding
  what a new mode actually adds.
- Dogfooding must produce a real Spec via the real `bmad-spec` skill run, not
  a hand-authored document that merely looks like one.

## Non-goals

- Not a request to re-litigate the model's own design — both items are
  mechanical follow-through on a decision already made, not new scope.

## Realization log

- **2026-08-03** — Captured while auditing open backlog items across memory
  and Dreams, at the user's request, excluding ongoing station-epic
  implementation work. Both follow-ups traced to the 2026-07-23 restructure
  memory and confirmed still genuinely open by direct inspection (no
  `--dreams` flag, no dogfooded Spec) before this Dream was written.
