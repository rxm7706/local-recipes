---
title: Herald — capture the dream, illustrate the telemetry, proclaim the release
type: dream
owner: herald
status: specified
---

# Herald — the outward voice and design surface

## The Dream

The Proclaimer's charter, **re-scoped by the 2026-07-23 ownership review**:
Herald is the factory's *voice and visual surface*. Invisible engineering is
failed engineering; Herald exists so nothing the factory does stays invisible.

**Herald's work is continuous, not a bookend** *(corrected 2026-07-25 — this
Dream previously said "first to touch a Dream and last to touch a release",
which reads as two touchpoints with silence between them; and the pitch deck was
being treated on the console as though it were Herald's whole contribution).*
There are **four moments of proclamation**, and every product and every Smith
passes through all of them:

| # | Moment | What Herald owes | Lands as |
|---|---|---|---|
| **1** | **Pitch** — a Dream must be argued, not merely filed | the case made legible to humans who did not dream it | the deck family (`pitched`) |
| **2** | **Progress** — a build in flight is not self-explaining | what changed, what it cost, what it unblocked | release notables, run telemetry as imagery |
| **3** | **Success** — shipping is not the same as being known to have shipped | the claim, with the evidence attached | the release proclamation |
| **4** | **Operations** — the long tail nobody announces | fixes, updates, deprecations, **decommissions** | change + end-of-life notices |

Moment 1 is simply the **first** time Herald has something to do — it is not the
extent of the job.

**Moment 4 needs no new vocabulary at all.** Ending is one act, and it is
**scale-invariant**: archiving a Dream, a package, an application or a whole
platform is the same state (`archived`), with the same four reasons
(absorbed / retired / terminal / blocked). "Decommission" is not a separate
concept that maps onto archiving — it *is* archiving, at a larger scale.
[[artifact-console]] is the worked example: built, run, superseded by the
Guildhall, archived as `retired`.

So the gap is not in the lifecycle — it is entirely in Herald's craft. **The
board records that a thing ended; nobody is told it ended.**

The corollary for the Guildhall: the Fleet's `deck` column marks Herald's *first*
touch, not his contribution. Moments 2–4 produce artifacts the board does not yet
track.

What Herald is **not** (the correction): not infrastructure. BMAD
monorepo/multi-project machinery and cross-agent portability moved to
[[pyforge-marshal]] — they are execution substrate, and the harness is the
unit of governance. Herald keeps their communication face only.

## What is real

- **The deck family** — 10 decks on one byte-identical engine
  (`presentations/`), the Modernist DS bound to every one
  ([[modernist-identity]]), full 6-artifact export sets + `deck-export`.
- **The bridge** — Design↔Code as one surface, seed/pull proven on 7 decks in
  one day; the `herald` CLI specced to 5 CAPs, zero open questions
  ([[design-code-bridge]]).
- **The stage** — the program console publishes the factory's state
  ([[factory-console]], Marshal's ledger; in the persona ideal Herald
  proclaims from it).

## The frontier

- The `herald` CLI built (epics queued on the pyforge-herald BMAD project):
  seed / pull / watch / stale-mirror / export push-back.
- Marp sources + export sets for the 7 starter decks; the
  [[packaging-factory]] origin-story deck.
- `updates compile` / `broadcast` — release notables composed from run
  telemetry and delivered where the audience lives (**moment 2 + 3**; the only
  part of the continuous model with a specced surface today).
- **Moment 4 has no surface** — no deprecation notice, no end-of-life
  announcement, no migration guidance. The *state* is fine (`archived` +
  `archived-reason: retired`); what is absent is anyone being **told**. A retired
  product currently just stops appearing.
- [[deckcraft]] as the editable-PPTX engine under every export.

## Kinships

[[pyforge-charter]] (charter section) · [[design-code-bridge]] (flagship
product) · [[modernist-identity]] (the language it speaks) ·
[[pyforge-marshal]] (receives the re-scoped infrastructure) ·
[[pyforge-scribe]] (the inward voice to Herald's outward).

## Realization log

- **2026-07-23** — persona Dream seeded during the ownership review; scope
  corrected (infrastructure → Marshal); deck + Design project already live
  (`presentations/pyforge-herald/`).
- **2026-07-25** — **lifecycle correction.** The bookend framing ("first…last")
  was replaced with the four moments of proclamation. Prompted by the observation
  that the console was treating the pitch deck as Herald's whole job — a Dream
  must be pitched, its *progress* proclaimed, its *success* proclaimed, and its
  *operational stages* (fixes, updates, decommissions) proclaimed too.
  **Corrected twice within the hour:** the first draft claimed moment 4 was
  "unmodelled" (it is not — ending is `archived`), and the second still treated
  decommission as a distinct concept *mapped onto* archiving. It is not distinct.
  Ending is one scale-invariant act — Dream, package, application, platform, same
  state and same four reasons. The lifecycle needs nothing; only Herald does.
