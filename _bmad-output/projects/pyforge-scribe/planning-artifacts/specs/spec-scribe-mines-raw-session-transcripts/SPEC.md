---
spec: scribe-mines-raw-session-transcripts
status: ready
owner-dream: docs/dreams/scribe-mines-raw-session-transcripts.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-mines-raw-session-transcripts.md
open_questions:
  - "Scan economics over 161MB+: incremental by transcript mtime vs full sweeps — decide at 3.1."
---

# SPEC — Scribe reaches past curated memory into the raw transcripts

## Why
Curated memory is itself a filter; everything discussed but never promoted
lives only in raw session transcripts (22 files / 161MB confirmed live) —
the fleet's proven highest-fidelity recovery source (warden's 13 lost
story specs came back verbatim from them), used once by hand, never
systematized.

## Capabilities
- **CAP-1 — the scanner.** Scribe scans the repo's raw `.jsonl` transcripts
  and surfaces promotion CANDIDATES — decisions/facts discussed but absent
  from curated memory — each with transcript+position provenance, feeding
  the existing `capture --promote` human-review flow; never auto-promoting.
  *Success:* pointed at a transcript with a known un-curated decision, the
  candidate surfaces with its provenance; curated-covered content does not.
- **CAP-2 — a compile source.** Transcripts join Epic 2's knowledge-graph
  compile source list (git history, memlogs, retros, CHANGELOGs, dreams)
  so the next Scribe layer doesn't re-miss them. *Success:* the source
  registry names them with the same provenance discipline.

## Constraints
Human review stays the gate (promotion is proposed, never applied);
transcripts are per-user local — the scanner runs user-side like capture
does; candidate text quoted minimally (pointers over payloads).

## Non-goals
Auto-promotion; mining OTHER users' stores; transcript retention policy.

## Success signal
The next lost-artifact recovery is a query, not an archaeology session —
and routine promotion sweeps propose what sessions actually said, not just
what got written down.
