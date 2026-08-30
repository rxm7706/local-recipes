---
title: One vocabulary, one home — the conventions eight stations never agreed on
type: practice
owner: marshal
status: specified
absorbed_by: pyforge-unifying-strategy
---

# One vocabulary, one home — the conventions eight stations never agreed on

## The Dream

Eight stations, each built well on its own terms, and no terms shared between
them. Not because anyone got it wrong — every station investigated here is
internally consistent, its own conventions self-documented and deliberate. The
gap only appears once someone reads all eight in one pass and tries to carry a
mental model from one to the next: the same integer exit code means a different
thing depending which station returned it, the same decision-tag prefix
(`AD-N`) restarts its numbering five separate times, and a station's own README
can say its own CLI has four commands when it has forty.

This is [[pyforge-core]]'s disease, on a different axis. That Dream found five
primitives — atomic write, the verdict lattice, the report envelope, the
station roster, the exception root — each hand-rolled once per station because
there was no shared home to put them in, and gave them one. This Dream is the
same finding applied to **conventions instead of code**: things no import
statement can share, because they are choices about naming, numbering, and
shape rather than executable primitives. A shared package fixes duplicated
logic. It cannot fix a duplicated *vocabulary* — that needs a documented
contract every station is held to, the same way [[agent-tool-surface]] holds
every station to one governed tool surface and [[landing-evidence-grammar]]
holds every detector to one shared idea of what a landed story looks like.

## What is real — measured across all eight, 2026-08-30

A full-source, station-by-station investigation (the basis for a companion
PyForge fleet dossier) turned up ten independent instances of the same root
cause. None is a bug in the station that has it — each is a reasonable choice
made in isolation. The problem is that eight reasonable isolated choices don't
add up to one fleet an operator can hold in their head.

| Convention axis | What actually varies | Where |
|---|---|---|
| **Decision tags** | `AD-N` restarts at 1 independently in Marshal (64+), Atlas (23), Mason (16), and part of Steward; Scribe keeps a small, contained `AD-N` set of 8. Warden and the rest of Steward use Story-N.M / FR-N / NFR-N / single-letter D-codes instead. No numbering is shared, and no station's `AD-8` means anything about another's. | marshal, atlas, mason, steward, scribe, warden |
| **Exit-code semantics** | The same integer is reused for different meanings. `3` is Mason's `EXIT_CFE_UNAVAILABLE` and Steward's reserved, not-yet-wired `EXIT_BUDGET_NOT_CONFIGURED`. `70` (BSD `EX_SOFTWARE`, crash vs. legitimate failure) exists only in Steward — no other station distinguishes the two cases at all. Doctor's domain is a *documented, tested* subset of Warden's; nothing says whether Marshal's or Mason's domains are meant to relate to either one. | mason, steward, doctor, warden, marshal |
| **CLI shape** | Noun-verb trees at very different depths (Marshal ~40 commands/12 groups; Mason 4 nouns), a flat 13-duty list (Steward), four flat subcommands (Doctor), one subcommand behind ~20 flags (Warden), and no station-specific CLI at all — Atlas is Kedro's own routing under a `--version` intercept. | all eight |
| **Hook-plugin naming** | The registration mechanism (`pyforge.core.hooks`) is genuinely shared — fleet-wide, confirmed. Entry-point *names* aren't: Atlas, Doctor, Warden, and Scribe prefix with their own station name (`atlas-catalog-ttl`, `warden-deptry`); Mason and Steward register bare names (`rattler-build`, `jira`) with no station prefix at all. | mason, steward vs. atlas, doctor, warden, scribe |
| **Boundary docs vs. code** | The installed skill index's "Lane 1 CMS stays steward" doesn't match Steward's own code — there is no CMS; Steward owns a `/console/` operator dashboard, successor to the retired GuildHall Pages console. Herald's own source has zero code-level acknowledgment of any "Lane" concept at all. The prose describes a boundary the code doesn't have. | herald (skill index), steward (actual code) |
| **Fleet-status sources** | At least four separate places answer "how's the fleet doing": Marshal's own `status` (reads journals directly), Steward's console (refuses to compute its own — reads Marshal's ledger plus Doctor's fleet-scan), Atlas's own dashboard (reads the sprint ledger independently, not confirmed same source), and Herald's own React dashboard (a fourth, separate front end). No confirmation the four would agree if checked at once. | marshal, steward, atlas, herald |
| **State storage** | Flat JSON (Marshal's rendered policy, Herald's deck-bridge state), SQLite (Herald's own consolidated `.herald/herald.db`), DuckDB (Atlas — "the one engine everywhere," by Atlas's own internal rule), journals (Marshal's run state), and one genuinely pluggable `Protocol` (Scribe, alone, selecting among flatfile/Postgres/DuckDB by an "owner" string). | marshal, herald, atlas, scribe |
| **MCP-server placement** | [[pyforge-unifying-strategy]] already rules this one: MCP and portal compute mount on the shared host ASGI (`POST /stations/<name>/mcp`), not per station — "not a deferred microservice program." Atlas ships its own standalone MCP server module anyway. Herald and Scribe correctly ship none, but neither their own code nor an operator reading it can tell "correctly absent, per the ruling" apart from "not built yet" — the ruling isn't referenced from either station's own source. | atlas (likely the actual outlier), herald, scribe (silent, not confirmed correct) |
| **Python floor** | Marshal/Mason/Herald/Scribe/Warden require `>=3.12`; Doctor/Atlas require `>=3.14`. No stated fleet policy for when a station may raise its own floor. | doctor, atlas vs. the rest |
| **A concrete naming collision** | Warden's own `scan --doctor` flag is a same-word coincidence with the `pyforge-doctor` station — Warden's `--doctor` is a local, unrelated self-check. Small, but the same root cause as everything above: nothing checks new work against what the rest of the fleet already calls things. | warden |

Two of these ten are not equally weighted. **MCP-server placement already has a
ruling** — [[pyforge-unifying-strategy]] settled it — so that row is a
*reconciliation* against an existing decision, not an open question. **Boundary
docs vs. code** is not merely inconsistent, it is actively wrong in one
direction (the skill index describes a CMS that isn't there) — that row is a
documentation bug with an operator-trust cost, not a style variance.

## What it looks like when real

- **One decision-tag registry, or a documented rule for why there are several.**
  Either every station's `AD-N` shares one numbering space, or the fleet
  explicitly documents that tags are station-scoped by design and gives them an
  unambiguous fully-qualified form (`marshal:AD-8`, `warden:D-12`) so a
  cross-station reference is never ambiguous again.
- **One exit-code contract every station's domain is checked against.** Not
  necessarily identical values everywhere — Doctor's "operability, not policy"
  floor is a legitimate reason its domain differs from Warden's — but every
  station's domain is declared as an explicit relationship to a shared
  reference (subset, superset, disjoint-and-why), the way Doctor's already is,
  and a fleet-wide meta-test holds that relationship the way `pyforge-core`'s
  sole-ownership tests already hold code-level invariants.
- **A named CLI-shape idiom, chosen once, applied by default to new work.**
  Existing stations aren't forced to a rewrite — a documented default (which
  shape a *new* station or a *new* top-level command reaches for first) stops
  the count from growing to nine variants when a ninth capability arrives.
- **Hook-plugin ids are always station-prefixed.** The registration mechanism
  is already fleet-wide; this is the one-line naming rule that was never
  written down, closing the last gap in a mechanism that's otherwise already
  unified.
- **Every cross-station boundary claim lives next to the code it describes, or
  it doesn't get made.** The Steward CMS/console correction in this Dream's own
  "What is real" is the template: read the code, fix the prose, and the
  prose stays load-bearing because it was checked, not assumed.
- **Fleet status has one authoritative source per fact, with every dashboard
  either reading it or explicitly declining to compute its own** — Steward's
  console already does the second half correctly (refuses rather than derives);
  the Dream is confirming Atlas's and Herald's dashboards do the same, not
  building a fifth reader.
- **Atlas's MCP server is reconciled against the ruling that already exists** —
  either the ruling is updated because the standalone server is load-bearing
  for a reason the Canopy Dream didn't anticipate, or Atlas's server is folded
  into the shared host ASGI. Either outcome is a decision *with a name*, not a
  standing unnoticed exception.
- **A new station, or a new top-level command in an existing one, is checked
  against this Dream's contract before it ships** — the same way `[[agent-tool-surface]]`'s
  coverage table is re-measured, not written once and trusted.

## Constraints

- **Detection is horizontal, ownership stays vertical.** Per Charter §6's
  existing model — the same one [[agent-tool-surface]], [[agent-portability]],
  and [[agentic-sdlc-autonomy]] already use — Marshal's own detectors do the
  fleet-wide measuring, rolled up **by owning station**; a finding against
  Herald's boundary docs is Herald's to close, not Marshal's to fix by hand.
- **The Doctor holds the verdict on Marshal's own row.** Marshal is not exempt
  from this Dream's findings — it owns the largest, least-reconciled
  decision-tag registry in the fleet (64+ `AD-N` tags) and one of the widest
  exit-code domains. Marshal may not weaken or re-threshold a check that judges
  its own conventions; that verdict belongs to Doctor, exactly as it already
  does for every other cross-cutting practice.
- **Reconcile before inventing.** The MCP-hosting row already has a ruling in
  [[pyforge-unifying-strategy]] — this Dream's job there is to check Atlas's
  code against it, not to hold a second opinion. Where a future row turns out
  to have a prior ruling this investigation missed, the ruling wins.
- **Some variance is legitimate and should be documented as such, not erased.**
  Doctor's narrower exit-code domain than Warden's is a *correct* difference
  (it reports operability, not policy) — the fix there is stating the
  relationship, not forcing identical values. Not every row in the table above
  resolves to "make them the same."
- **No station's runtime behavior changes to satisfy a naming rule.** This
  Dream is about vocabulary, discoverability, and documented relationships —
  not a rewrite of what any station actually does.

## Non-goals

- **Not [[agent-tool-surface]].** That practice governs whether a capability is
  reachable through one MCP surface at all. This one governs what a station's
  own vocabulary — tags, exit codes, command shape, plugin ids, boundary
  claims — looks like once it's built. Sibling practices, same Charter §6
  model, different axis.
- **Not [[surface-drift-reconciliation]].** That Dream fixes bugs in the
  `spec_surface_check.py` detector's own reconciliation granularity. This one
  is about station-facing conventions, not the spec-governance instrument.
- **Not a second architecture ruling for the Canopy.** MCP hosting, the query
  plane, and the Canopy's own shape stay [[pyforge-unifying-strategy]]'s to
  decide; this Dream only checks conformance against what's already ruled.
  Any real architectural disagreement uncovered here escalates to that Dream,
  not fought out inside this one.
- **Not a mandate for uniform exit codes or a single CLI framework fleet-wide.**
  A documented, checked *relationship* between stations' choices is the goal —
  not forcing eight independently-installable stations into one shape where a
  real difference in what they do justifies a real difference in how they
  present it.
- **Not a rewrite of any station's README in one pass.** The documentation-drift
  half of this Dream (Marshal's skill index, Doctor's and Steward's README
  undercounts, Scribe's self-contradicting one) is real and in scope, but it's
  remediation work each owning station does on its own row — not a single
  cross-repo doc sweep landed as one commit.

## Kinships

[[pyforge-core]] (the direct ancestor — same disease, code instead of
convention) · [[agent-tool-surface]], [[agent-portability]],
[[agentic-sdlc-autonomy]] (the three existing Charter §6 cross-cutting
practices this Dream joins as a fourth) · [[landing-evidence-grammar]] (another
"one shared grammar instead of N dialects" precedent, already realized) ·
[[surface-drift-reconciliation]] (a different kind of drift — the spec
detector's own instrument, not station vocabulary) · [[pyforge-unifying-strategy]]
(holds the ruling this Dream's MCP-placement row must reconcile against) ·
[[pyforge-target-monorepo]] (foundry tree seed) ·
[[pyforge-marshal]] (the owning station) · [[pyforge-doctor]] (holds the
verdict on Marshal's own row, per Charter §6).

## Realization log

- **2026-08-30** — Captured directly from a full, parallel, source-verified
  investigation of all eight stations plus `pyforge-core` (seven independent
  deep-dives run in parallel, one per station, cross-referenced against each
  other and against `pyforge-core`'s own docstrings) — the basis for a
  companion PyForge fleet dossier. The ten-row table above is that
  investigation's own cross-fleet synthesis, not a fresh audit; the operator's
  own reaction to one row (the decision-tag split) named the pattern before the
  Dream did — *"its these type of per station variance... that makes it
  difficult for an operator / developer to understand the entire codebase"* —
  and asked directly for the rest of the list, which is what this Dream's
  "What is real" table is. `status: dreamt`: the case is captured and the
  shape (a fourth Charter §6 practice, owned by Marshal, verdicted by Doctor)
  is clear from precedent, but no Spec exists yet.
- **2026-08-30** — Living *contract* absorbed into [[pyforge-unifying-strategy]]
  Grounding 2026-08-30 (fully-qualified tags, exit-domain relationships,
  station-prefixed hooks, one status source per fact, MCP = host ASGI,
  no Lane-1-CMS, `scan --doctor` ≠ Doctor). This file remains the ten-row
  evidence table and Marshal’s detector-practice home. Status `specified`.
