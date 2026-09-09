---
spec: scribe-mines-raw-session-transcripts
status: shipped
owner-dream: docs/dreams/scribe-mines-raw-session-transcripts.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-mines-raw-session-transcripts.md
open_questions: []
  # ANSWERED 2026-09-09 (decided in shipped code across 3.1 and 3.3): scan economics is
  # BOTH, not either — an opt-in mtime+size-keyed scan cache AND a triple-bounded sweep.
  # See Constraints.
---

# SPEC — Scribe reaches past curated memory into the raw transcripts

## Why
Curated memory is itself a filter; everything discussed but never promoted
lives only in raw session transcripts (the Dream's "22 files / 161MB" was
measured live at **27 files / 631MB** on 2026-09-09 — 4× stale, and the
number every bound below is sized against) —
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

**Scan economics is both halves, not a choice (answered 2026-09-09, shipped
across 3.1 and 3.3).** INCREMENTAL: an *optional* mtime+size-keyed scan cache
(`transcripts.py:25-43` — `cache_path`, the module's only write, and only when a
caller opts in; `compile.py` points it at the graph store's own gitignored
directory) so a re-run over an unchanged surface skips unchanged files. The
curated-overlap check is deliberately re-run on every scan, so a cache hit stays
byte-equivalent to a cold scan. SWEEP: a triple bound — a file-count cap, a
total-byte budget that selects newest files first, and a per-file timeout that
abandons a pathological file with partial results rather than hanging an
unattended run. Defaults are sized against the measured 27-file / 631 MB
surface, never the Dream's stale figure.

## Non-goals
Auto-promotion; mining OTHER users' stores; transcript retention policy.

## Success signal
The next lost-artifact recovery is a query, not an archaeology session —
and routine promotion sweeps propose what sessions actually said, not just
what got written down.

**Realization status (2026-09-09): in effect, with one residual.** CAP-1 ships
as `transcripts.py` (506 lines) — scans `~/.claude/projects/<encoded-repo>/*.jsonl`
for assistant-authored decision/fact markers, drops anything already covered by
curated `.claude/memory/`, feeds survivors into `promote.py`'s proposal-then-confirm
gate; read-only against its inputs, zero network calls, pure stdlib. CAP-2 ships as
the sixth of six named compile surfaces (`compile.py:114-117`, `:174-196`) under the
same `transcript:` provenance discipline (`compile.py:67`). **Exercised**, not merely
built: `.claude/data/pyforge-scribe/transcript-scan-cache.json` (10 KB, written
2026-08-27) is the artifact only a real scan produces, alongside a 1.67 MB
`graph.json`. Epic 3 is 3/3 `done`. **Residual:** the scan is invoked by hand — the
unattended path exists (`graph compile --nightly` is prompt-free and `flock -n`-safe)
but no schedule is installed, so "routine promotion sweeps" above is still
aspirational. Vessel: scribe Epic 8 Story 8.1.
