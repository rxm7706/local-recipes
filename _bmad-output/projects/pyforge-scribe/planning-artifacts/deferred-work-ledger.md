---
doc_type: deferred-work-ledger
project: pyforge-scribe
date: 2026-07-31
status: promoted-verbatim
---

# pyforge-scribe — deferred-work ledger (TRACKED)

**Promoted verbatim from Tier-3 on 2026-07-31 to make it durable.**

`implementation-artifacts/deferred-work.md` is **gitignored**: it does not survive a
clone or a bmad-loop worktree teardown. Until today this project had **no tracked
ledger at all**, so its entire deferred-work record — 4 KB, 6 entries — existed
only in scratch space. Produced by the 2026-07-30/31 six-station fleet run and found
by `scripts/deferred_work_check.py`.

**This is a COPY, not a curation.** Bodies are unedited; nothing has been given a
resolution, re-severitied, or reconciled against what has since shipped. Treat entry
*status* fields as of their authoring date, not as current.

**The one intentional edit is id assignment.** bmad-loop's damping output writes either
no id or a generic `DW-<n>`, which collides the moment another story is damped. Each
entry here is keyed `DW-<story>-<n>` from its own `source_spec`, per the convention the
sibling ledgers and the detector both use.

---

### DW-1-2-1

- source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md`
  summary: `.claude/memory/MEMORY.md`'s own header documents a 200-line cap ("Claude Code truncates context past that length") but nothing enforces it in CI.
  evidence: Edge Case Hunter review of Story 1.2's `CLAUDE.md` wiring diff flagged that once the `@.claude/memory/MEMORY.md` import is live, silent truncation past 200 lines would drop later-appended team-memory entries from every session with no automated warning. Out of scope for Story 1.2 (which only wires the import) and Story 1.1 (which scaffolded the file) — no CI check currently exists anywhere in the repo for this file's line count.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-2-2

- source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md`
  summary: In bmad-loop worktree sessions the team-memory index loads twice — once via the loop-home's ancestor `CLAUDE.md` and once via the worktree's — from two physical `.claude/memory/MEMORY.md` files that can diverge (home on `main`, worktree on a story branch).
  evidence: Observed live in the Story 1.2 review-pass-2 session: both `/home/rxm7706/.bmad-loops/pyforge-scribe/CLAUDE.md` and the run-worktree `CLAUDE.md` were in context simultaneously (Claude Code loads ancestor-directory CLAUDE.md files), each resolving the relative import against its own tree. Once this change is on `main` and pulled by the 8 loop homes, every worktree session pays the index twice. Not fixable inside Story 1.2 (imports cannot be conditional); an inherent cost of the loop-home layout that should be recorded/accepted or mitigated at the bmad-loop level.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-2-3

- source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md`
  summary: bmad-loop leaves an untracked, un-gitignored `claude_hash.txt` (the story's HEAD commit hash) at the run-worktree root with no identifiable in-repo producer; any later `git add -A` automation would sweep it into a commit.
  evidence: Blind Hunter verified during Story 1.2 review pass 2: the file exists at the worktree root containing exactly `0671914e15e78cc45fdb98867a64ac49f3485f5f`, `git check-ignore` reports NOT IGNORED, and `grep -rn claude_hash` across repo scripts, hooks, `.bmad-loop/`, and settings finds no generator or consumer. Loop-machinery hygiene, not Story 1.2 content — fix belongs in bmad-loop (gitignore it or write it outside the worktree).
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 0/1 present (absent: _bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-2-4

- source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md`
  summary: Nothing asserts the `@.claude/memory/MEMORY.md` import in root `CLAUDE.md` still exists and resolves — Claude Code silently ignores broken imports, so a rename/move of the memory index (or deletion of the import line) severs team memory with no failure signal anywhere.
  evidence: Story 1.2 review pass 2 confirmed no test, detector, or hook references the import (`scripts/bmad_drift_check.py` `check_coverage` walks only the `_bmad-output` project tree; no meta test greps `CLAUDE.md` for the line). Complements the already-ledgered 200-line-cap entry (different failure mode: severance vs truncation); a one-line check in an existing detector or meta-test would close both.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-2-5

- source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md`
  summary: Team memory is wired for Claude Code only — `AGENTS.md`, `.cursor/rules/`, `GEMINI.md`, and `.github/copilot-instructions.md` carry no pointer to `.claude/memory/MEMORY.md`, while `.claude/memory/README.md` claims the layer is loaded "into every session" for every agent.
  evidence: Verified in Story 1.2 review pass 2: grep across the cross-tool entry files finds no team-memory reference, and no story in `_bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md` (Epics 1–2, Stories 1.1–2.4) covers cross-tool exposure — the gap is real and unplanned, not merely sequenced later. `@import` is Claude-Code-specific syntax, so non-Claude agents never see the index.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 4/5 present (absent: _bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-1-2-6

- source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md`
  summary: A future `MEMORY.md` entry containing a bare `@`-token (npm scope, GitHub handle) would be treated as a nested import attempt by Claude Code, since imports recurse into imported files — the scribe writer/README needs a backtick-all-`@`-tokens authoring rule.
  evidence: Raised by Edge Case Hunter in Story 1.2 review pass 2. Claude Code evaluates `@path` references recursively in imported files but not inside code spans; team-memory entries about npm packages plausibly contain `@scope/pkg` tokens. Guard belongs in `.claude/memory/README.md`'s entry schema and/or Story 1.3's `scribe capture` writer (backtick or escape `@`-tokens on write), both outside Story 1.2's edit-only-`CLAUDE.md` boundary.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec is Tier-3 (gitignored, not in clone); cited paths 1/2 present (absent: _bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-2-1-3

- source_spec: `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md`
  summary: 87 of Scribe's 88 `memlog` graph nodes are titled `---` — every memlog with YAML frontmatter is effectively unidentifiable in the knowledge graph Scribe exists to build.
  evidence: Measured 2026-08-09 against the live repo: `compile.py::_node_from_text_file` derives `title` as the first non-empty line (`next((line.strip("# ").strip() for line in text.splitlines() if line.strip()), relpath)`). For a `.memlog.md` that first line is the frontmatter delimiter `---`, so the title is literally `---`. `_read_memlog_surface(Path("."))` returns 88 nodes, of which **87 are titled `---`**; the single exception (`spec: herald-pitch`) is a memlog with no frontmatter. The fix is small — skip frontmatter, or prefer the `topic:` field memlogs already carry — but it is a real defect in the graph's primary human-readable field, not a cosmetic one, since a graph of 87 identically-named nodes cannot be navigated.
  related: 17 memlogs additionally carry unparseable YAML frontmatter (an unquoted `:` inside `topic:`). That is latent today precisely BECAUSE nothing parses memlog frontmatter as YAML — if this defect is fixed by reading `topic:`, those 17 must be quoted in the same change or the fix will fail on them.
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 1/1 present; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-3-2: A transcript node's citation/id is derived only from the source file's basename (not a path relative to transcript_root), so two different transcript files sharing a basename under different subdirectories would collide into the same node id.

- source_spec: `planning-artifacts/specs/spec-3-2-transcripts-join-the-compile-sources.md`
  summary: A transcript node's citation/id is derived only from the source file's basename (not a path relative to transcript_root), so two different transcript files sharing a basename under different subdirectories would collide into the same node id.
  evidence: Corroborated independently by two review passes (Blind Hunter and Edge Case Hunter). Currently unreachable: scan_transcripts() globs only *.jsonl directly in transcript_root (non-recursive), and default_transcript_root() always resolves to one flat directory, so no subdirectory structure can exist under it today. A real fix would require changing the citation format away from this story's own intent-contract, which explicitly fixed it as "<jsonl filename>:L<line>" with no directory path, matching Story 3.1's established provenance convention -- so it is out of this story's scope, not a defect in what was built here.
  location: src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py:_read_transcript_surface
  origin: spec-deferred 0bc7fb271ee1 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-3-2-2: The transcript surface is the only compile surface with no cost bound, and this story puts it on the unattended nightly path: every `scribe graph compile` now reads every *.jsonl under the transcript root whole into memory and runs an O(candidates x curated-sentences) difflib comparison, with no file cap, byte cap, timeout, or mtime-incremental pass.

- source_spec: `planning-artifacts/specs/spec-3-2-transcripts-join-the-compile-sources.md`
  summary: The transcript surface is the only compile surface with no cost bound, and this story puts it on the unattended nightly path: every `scribe graph compile` now reads every *.jsonl under the transcript root whole into memory and runs an O(candidates x curated-sentences) difflib comparison, with no file cap, byte cap, timeout, or mtime-incremental pass.
  evidence: Raised independently by all four review layers. Measured on this machine: the production root for the owning repo (~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes) holds 27 files totalling 631MB, roughly 4x the 161MB the owning Dream cites. Every other surface has a ceiling (`max_commits=100`, `_MAX_DOC_TEXT_CHARS=20_000`, `timeout=30` on `git log`); this one has none. Story 3.1 only ever drove `scan_transcripts()` interactively. Out of scope on this story's own intent authority, not a defect in what was built: `Block If: None` asserts every design choice is resolved, and the Approach mandates reusing `scan_transcripts()` exactly, so bounding it means either changing Story 3.1's scanner or pre-filtering ahead of it -- both new design decisions. The spec's own frontmatter open question ("Scan economics over 161MB+: incremental by transcript mtime vs full sweeps -- decide at 3.1") was never decided at 3.1 and is still open.
  location: src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py:_read_transcript_surface
  origin: spec-deferred 8822027f8d86 — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: done 2026-08-27 — Story 3.3. `scan_transcripts()` now enforces a file-count cap (256) and total-byte budget (1 GiB) allocated newest-first, a 30s per-file timeout (partial results kept, warned), and an mtime+size-keyed scan cache beside the graph store (`transcript-scan-cache.json`) that resolves the spec's open scan-economics question as incremental-by-mtime with a full-fidelity fallback. Dedup stays post-cache so curated-overlap semantics are unchanged. Live re-measure at close: 25 files / 651MB scanned in 2.2s cold, 0.3s cached.

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — done — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to done; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-3-2-3: The `pyforge-scribe/spec-pyforge-scribe` spec-surface baseline is stale for 12 files, and the spec's .memlog.md carries no provenance entry for Story 3.1 or 3.2, so the governed-surface reconcile for Epic 3 has never been done.

- source_spec: `planning-artifacts/specs/spec-3-2-transcripts-join-the-compile-sources.md`
  summary: The `pyforge-scribe/spec-pyforge-scribe` spec-surface baseline is stale for 12 files, and the spec's .memlog.md carries no provenance entry for Story 3.1 or 3.2, so the governed-surface reconcile for Epic 3 has never been done.
  evidence: `python -m pyforge.doctor.sources spec-surface` reports 12 drift-presumed warnings for pyforge-scribe/spec-pyforge-scribe. Six are this story's own files (compile.py, models.py, recall.py, test_compile.py, test_recall.py, test_supersession.py); two are Story 3.1's, never stamped (transcripts.py, test_transcripts.py); four predate Epic 3 (README.md, pixi.toml, pyproject.toml, graph_store.py). Deliberately NOT reconciled inside this review pass: the remedy the detector names is a spec-scoped `--write-baseline --spec pyforge-scribe/spec-pyforge-scribe`, which stamps all twelve at once and would silently absorb six files of drift this story neither caused nor verified -- exactly the failure mode the repo's own "three checks before a scoped stamp, never a bare --write-baseline" convention warns against. Wants its own scoped reconcile (memlog entry naming the paths, then the stamp), the same shape as commit b513e29aee did for marshal Story 11.4 on this branch.
  location: scripts/.spec-surface-baseline.json + _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-mines-raw-session-transcripts/.memlog.md
  origin: spec-deferred 8a74d96a6c3c — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: low
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-FU-3-2-4: `recall.answer()` ranks candidates by token overlap and tie-breaks on node id ascending, never consulting `valid_from`, so between two equally-overlapping nodes the alphabetically-earlier id wins -- which for date-ordered session filenames is usually the OLDER, since-reversed statement.

- source_spec: `planning-artifacts/specs/spec-3-2-transcripts-join-the-compile-sources.md`
  summary: `recall.answer()` ranks candidates by token overlap and tie-breaks on node id ascending, never consulting `valid_from`, so between two equally-overlapping nodes the alphabetically-earlier id wins -- which for date-ordered session filenames is usually the OLDER, since-reversed statement.
  evidence: Verified in `recall.py::answer()`: `scored.sort(key=lambda pair: (-pair[0], pair[1].id))`, and its own docstring states the id tie-break is deliberate, "for reproducibility". Pre-existing Story 2.x recall behaviour, not introduced here -- but this story is what makes it bite: transcript nodes are the first surface where two nodes routinely make contradictory claims about the same decision across time, and (per the already-rejected supersession finding) `_apply_supersession()` has no path to invalidate a transcript node, so the superseded statement stays `is_current` indefinitely. Fixing it means choosing a recency policy for ties, which is a new design decision for recall, not a defect in what this story built.
  location: src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py:answer
  origin: spec-deferred c7a73445c0be — ingested from spec frontmatter `deferred:` (hand-driven build-auto; marshal Story 25.6)
  severity: medium
  promoted: 2026-08-23 — ingested from spec frontmatter by scripts/deferred_work_intake.py
  status: open

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

### DW-CANOPY-2026-08-24

- source_spec: `_bmad-output/projects/pyforge-scribe/planning-artifacts/change-history/sprint-change-proposal-2026-08-24-canopy.md`
  summary: Canopy CAP-14 (FR-35/FR-36) graph durability and semantic recall are steward Epic 28's vehicle — not a new scribe Epic 4. The unifying-strategy Dream's BS-1 "dual-driver Scribe engine" (SQLite local vs PostgreSQL production) was written as if already shipped; ground truth is a **single** v1 adapter — `FlatFileGraphStore` (JSON at `.claude/data/pyforge-scribe/graph.json`) behind the `GraphStore` port (Story 2.1 / AD-5). SQLite-over-RWX is explicitly rejected; multi-pod durability is PostgreSQL/pgvector under `scribe_schema` (parent AD-1 / parent AD-5).
  evidence: Phase 5 correct-course 2026-08-24; steward `epics.md` Epic 28 Stories 28.1–28.2; scribe `spec-2-1-graphstore-port-flat-file-adapter.md` (shipped); `technical-scribe-capture-promotion-graph-2026-08-08.md`. Scribe five-tier gaps (portal, MCP, skill, persona) delegate to steward Epics 19/21/29 — not scribe-local epics.
  status: open
  vehicle: `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` Epic 28

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec present; cited paths 2/3 present (absent: .claude/data/pyforge-scribe/graph.json); ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic

## DW-OM-2026-08-24 — Operating-model obligations (all eight stations)

- source_spec: cross-cutting (pyforge-unifying-strategy Grounding Q1–Q8; steward SCP operating-model, §6 revisited)
  summary: Estate OM + CAP-18: shared hook-spec in pyforge-core; Warden Epic 9 is the PR-gate retrofit; this station extracts one process hook spec (today's backend = default plugin).
  owner: station planning (this file) + steward (Canopy FRs) + warden (PR-gate hook specs)
  status: open
  recorded: 2026-08-24
  close_when: steward S-32.1 done; scribe S-4.1 done (GraphStore on shared contract; FlatFileGraphStore default plugin); no competing CI verdict

  verified: 2026-08-26 — still-open — 2026-08-26 fleet hygiene first CAP-4 stamp at HEAD d7853d7983; ledger status mapped to still-open

  verified: 2026-09-02 — still-open — mechanical re-verification at HEAD 933039db67 (operator-directed fleet-wide refresh 2026-09-02): source_spec path absent at HEAD; no repo paths cited; ledger status mapped to still-open; agent judgment not applied — a re-read against live code is still owed where the claim is semantic


## DW-SCRIBE-2026-09-09-ADR-INTEROP — Should Scribe READ pre-existing `docs/adr/`-style files in a target repo?

- source_spec: `planning-artifacts/specs/spec-pyforge-scribe/SPEC.md` (body § Open Questions, Q3 — closed 2026-09-09; this is the half that was split off rather than answered)
  summary: `scribe capture --type decision` will NOT adopt `docs/adr/` numbering (decided 2026-09-09, operator, fleet-readiness decision batch row scribe-B1 — a fourth `--type` value breaks AD-3's byte-identical parity with Claude Code's user-local auto-memory schema, which is CAP-1's own success criterion, and a second numbering scheme is the synonym-into-prose Charter CAP-4 forbids). The separable half is READING: if Scribe is ever installed in a target repo that already keeps `docs/adr/`-style decision records, should `scribe graph compile` treat that directory as a seventh named compile surface (read-only, provenance-cited, never written back)?
  evidence: `docs/adr/` does not exist in THIS repo, so nothing here can motivate or test it — the question only becomes real when a second consumer repo exists, which is also the trigger `spec-pyforge-scribe`'s "No plugin/marketplace packaging until a second consumer repo exists" Non-goal already names. `compile.py:6-27` enumerates six named surfaces plus one optional gated extra (`SCRIBE_GRAPHIFY_EXTRA`), so the shape for adding a seventh read-only surface already exists and needs no new mechanism. `spec-pyforge-scribe` Non-goal "No cross-repo synchronization — each repo's Scribe instance is self-contained" bounds it: read-in-place only, never a sync.
  location: src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py
  origin: fleet-readiness decision batch 2026-09-09 (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, § 2.1 row scribe-B1) — filed as deferred work rather than left as an open contract question
  severity: low
  recorded: 2026-09-09
  status: open
  close_when: a second consumer repo exists AND it keeps `docs/adr/`-style records — otherwise this stays a hypothetical and closes as a Non-goal
