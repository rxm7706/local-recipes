---
title: 'Story 7.1: The emitter mints identity at defer time'
type: 'feature'
created: '2026-08-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
baseline_revision: '184aec727e0939ece618d47f691c1ef4c6493a8e'
final_revision: '633d95d259'
context:
  - '{project-root}/.claude/skills/bmad-dev-auto/step-04-review.md'
  - '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py'
  - '{project-root}/_bmad-output/planning-artifacts/deferred-work-ledger.md'
  - '{project-root}/_bmad-output/implementation-artifacts/deferred-work.md'
  - '{project-root}/_bmad/scripts/resolve_config.py'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `bmad-dev-auto`'s "defer" triage path (`step-04-review.md`) appends bare
`- source_spec:` bullets to the Tier-3 `deferred-work.md` with no id — every one of doctor's
76 current bullets is anonymous this way. An anonymous entry can't be matched against the
tracked ledger, so it's already invisible to whatever later promotes it, even before the
detector-side visibility gap (Story 7.3) is fixed.

**Approach:** Before appending a "defer" entry, mint an id under the owning station's own
convention (resolved from the active BMAD project slug) and head the new entry with a
`### DW-...` heading so it satisfies the same `## DW-<id>` shape the detector's `_anonymous()`
parser already recognizes on the tracked ledger (`chain.py:1323-1373`).

## Boundaries & Constraints

**Always:**
- Mint an id for every new "defer" entry before it is appended — never write an anonymous
  `- source_spec:` bullet again.
- Use `DW-FU-{story}` for every station except mason; use `DW-{story}-<n>` for mason
  (`{story}` = the leading `<epic>-<story>` numeric prefix of `{spec_file}`'s filename, e.g.
  `spec-7-1-....md` → `7-1`; if the spec's slug has no such prefix, use the full slug).
  Resolve the active station from `python3 {project-root}/_bmad/scripts/resolve_config.py
  --project-root {project-root} --key project` → `.project.slug`, stripping a leading
  `pyforge-`.
- Guarantee the minted id is unique within `{deferred_work_file}`: scan existing `### DW-...`
  headings first and append the next free `-<n>` suffix on collision (mason already always
  carries a suffix; for every other station this only bites when a story defers more than
  once).
- Degrade gracefully, never fail the step: if the station can't be resolved (script errors,
  no slug, no multi-project setup at all), mint under the default (non-mason) convention
  rather than blocking.
- Preserve the existing `source_spec`/`summary`/`evidence` field schema and the append-only,
  never-modify-existing-entries discipline exactly as they are today.

**Block If:** None. Every resolution path above has a defined fallback; nothing here needs a
human decision mid-run.

**Never:**
- Never rewrite the entry's field schema into `bmad-loop-sweep`'s canonical
  `origin`/`location`/`severity`/`reason`/`status` shape — that ledger normalization is a
  separate, later mechanism (`deferred-work-format.md`), not this story's job.
- Never touch the tracked ledger, the promotion mechanism, or
  `pyforge/doctor/sources/chain.py`'s detector code (`_anonymous`/`_DW_RE`/`_ids`) — those are
  Stories 7.2/7.3.
- Never retrofit ids onto the existing anonymous Tier-3 backlog — that's the grandfathering
  baseline, Story 7.2.
- Never normalize mason's id shape onto the other stations' shape, or vice versa.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Single defer, non-mason station | active slug `pyforge-doctor` (or atlas/marshal/warden); no `DW-FU-7-1` heading exists yet | New entry headed `### DW-FU-7-1: <summary>` | No error expected |
| Single defer, mason | active slug `pyforge-mason`; no `DW-1-3-` headings exist yet | New entry headed `### DW-1-3-1: <summary>` | No error expected |
| Second defer for the same story (same pass or a later one) | `DW-FU-7-1` (or `DW-1-3-1`) already present in `{deferred_work_file}` | New entry gets the next free suffix: `### DW-FU-7-1-2: <summary>` (or `### DW-1-3-2: <summary>`) | No error expected |
| Active project can't be resolved | `resolve_config.py` fails, or returns no `.project.slug` | Mint falls back to the non-mason convention (`DW-FU-{story}`) | Treated as "unknown station," not a failure — step continues |
| Freeform intent with no numeric story prefix | `{spec_file}`'s slug has no leading `<epic>-<story>` | `{story}` = the full slug, used verbatim in the same id shapes | No error expected |

</intent-contract>

## Code Map

- `.claude/skills/bmad-dev-auto/step-04-review.md` -- the only file this story edits: the
  "defer" triage bullet (currently the plain `- source_spec:` block) gains an id-minting
  procedure and a `### DW-...` heading.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:1323-1373` -- read-only
  reference. `_ENTRY_RE` is the exact shape a new heading must satisfy (`^#{2,4}\s+DW-...`) for
  Story 7.3's future `_anonymous()` call on Tier-3 to recognize these entries as identified.
  Not edited by this story.
- `_bmad-output/planning-artifacts/deferred-work-ledger.md` -- reference for the existing
  per-station id shapes this story's convention extends (`## DW-1-1-1`..`4` bare shape,
  `### DW-FU-6-4`..`8` follow-up shape).
- `_bmad/scripts/resolve_config.py` -- the existing CLI this story's mint procedure calls to
  resolve the active station; not edited.

## Tasks & Acceptance

**Execution:**
- [x] `.claude/skills/bmad-dev-auto/step-04-review.md` -- add a "Minting the id" procedure
  ahead of the defer-entry template (station lookup via `resolve_config.py --key project`,
  mason vs. every-other-station branch, collision-suffix scan) and head the appended entry
  with `### {id}: <summary>` -- so a new Tier-3 defer entry carries a unique,
  station-appropriate id from the moment it's written, closing the exact gap CAP-1 names:
  "an entry reaching promotion without an id is already invisible to the promoter."

**Acceptance Criteria:**
- Given a bmad-dev-auto review pass on a non-mason station that defers one finding, when the
  entry is appended to `{deferred_work_file}`, then it is headed `### DW-FU-{story}: <summary>`.
- Given a bmad-dev-auto review pass on mason that defers one finding, when the entry is
  appended, then it is headed `### DW-{story}-<n>: <summary>` with `<n>` one past the highest
  existing suffix for that story.
- Given a second defer whose base id already exists in `{deferred_work_file}`, when the new
  entry is appended, then it receives the next free `-<n>` suffix rather than repeating the
  existing heading.
- Given the active BMAD project can't be resolved, when a defer entry is appended, then it
  still receives an id under the default (non-mason) convention -- never an anonymous bullet.

## Spec Change Log

## Review Triage Log

### 2026-08-10 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high 1, medium 1, low 5)
- defer: 2 (medium 1, low 1)
- reject: 6 (low 6)
- addressed_findings:
  - `high` `patch` No re-scan instruction between multiple `defer` findings in one pass (or across concurrent worktrees for the same station) could mint the same id twice. Fixed: the id-scan now happens fresh, immediately before minting each id, including entries appended earlier in the same pass; documented the residual concurrent-worktree race as an accepted, narrowed-not-eliminated risk.
  - `medium` `patch` `{story}` extraction ("leading `<epic>-<story>` numeric prefix") was ambiguous for multi-digit story numbers — this repo already has `spec-6-10-....md`, which a naive single-digit read would misparse as `6-1`. Fixed: instructions now say to match the full leading `\d+-\d+` run, both groups multi-digit-capable, with that exact counter-example spelled out.
  - `low` `patch` Station resolution read the ambient `.active-project` marker with no note distinguishing it from the parallel-write footgun this repo's CLAUDE.md warns about. Fixed: clarified the read is of the current worktree's already-established active project (set once, at worktree setup), not shared mutable state.
  - `low` `patch` "If the command fails, or returns no slug" could be read narrowly as covering only a non-zero exit, not a successful-but-empty `{}` result. Fixed: reworded to "no non-empty `.project.slug` (including an empty `{}`)".
  - `low` `patch` "Do not modify existing entries or look for duplicates" sat immediately before the new id-collision scan, inviting a reader to skip the scan as another kind of forbidden "duplicate check." Fixed: clarified the content-dedup rule and the id-uniqueness scan are separate concerns.
  - `low` `patch` "use the full slug instead" didn't say which slug. Fixed: specified `{spec_file}`'s own filename-derived slug (after `spec-`, before `.md`).
  - `low` `patch` "-<n>" suffix comparison didn't say numeric vs. lexicographic, risking a `-9`/`-10` misorder. Fixed: specified numeric comparison; also specified `### DW-...` headings are matched at the start of a line.
  - `medium` `defer` The `DW-FU-{story}` shape this story mints for non-mason stations already has an established, different meaning (the pre-existing "follow-up review still recommended" promotion mechanism uses the identical shape, under a different field schema). Collision-safe by suffix, not type-distinguishable by prefix. The epic/SPEC's convention is explicit and operator-confirmed the same day as this story; resolving the overlap is a planning-level decision above this story's remit. Recorded as `DW-FU-7-1-2`.
  - `low` `defer` The Review Triage Log's `addressed_findings` format never itemizes `defer` entries by id, unlike `patch`/`bad_spec` — pre-existing gap in the Classify section (step 4/5), now more valuable to close since `defer` entries carry real ids going forward. Recorded as `DW-FU-7-1`.

### 2026-08-10 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 13 (high 0, medium 7, low 6)
- defer: 2 (medium 2)
- reject: 9 (low 9)
- addressed_findings:
  - `medium` `patch` Pass 1's own triage log cited the two ids it minted **inverted**: the `medium` finding claimed `DW-FU-7-1` and the `low` one `DW-FU-7-1-2`, while the actual entries (in both the Tier-3 file and the tracked ledger) are the reverse. The story exists to make deferrals citable, and its own first citation pointed at the wrong entry. Fixed: both `Recorded as` references swapped to match the real headings.
  - `medium` `patch` The prose sequenced append before mint ("Append one new entry … using this format" → "Head the **appended** entry with the minted `{id}`"), inviting a literal reader to append the anonymous bullet and then edit a heading onto it — leaving exactly the anonymous bullet this story eliminates if interrupted between the two writes, and colliding with the same bullet's "Do not modify existing entries". Fixed: mint-then-append is now explicit, entries are written heading-and-fields in a single append, and defer findings are handled strictly one at a time.
  - `medium` `patch` The id-uniqueness scan looked only for `### DW-...`, but the ledger parser's `_ENTRY_RE` accepts `^#{2,4}\s+DW-`. Measured: atlas's Tier-3 file carries 9 `##`-level DW headings alongside 3 `###`, so on that station the scan would have missed real collisions outright. Fixed: the scan now matches two-to-four `#`, the same shape the parser recognizes.
  - `medium` `patch` The `DW-FU-{story}` existence test had no delimiter guard (unlike the mason branch, which names one), so a bare prefix match reads `DW-FU-4-14` as an occurrence of `DW-FU-4-1` — and `DW-FU-4-14` exists in marshal's ledger today. Fixed: ids are compared as complete tokens, never as bare string prefixes, with that exact counter-example given.
  - `medium` `patch` Step 3 made reading `{deferred_work_file}` an unconditional prerequisite, but the file is gitignored Tier-3 and a station's first-ever defer has none — an undefined read failure inside a branch whose spec declares "Block If: None". Fixed: a missing file is defined as an empty heading set that the append creates.
  - `medium` `patch` Step 1 asserted the resolved station is "set once, at worktree setup — not a globally-mutable value another process could be changing concurrently". The command passes no `--project`, so resolution falls through to `BMAD_ACTIVE_PROJECT` and then the per-working-tree `.active-project` marker. Demonstrated live during this pass: the identical command returned `pyforge-doctor` from this worktree and `pyforge-mason` from the main checkout at the same instant. Fixed: the claim now states the real resolution order, calls the answer best-effort rather than an invariant, and requires resolving against this run's `{project-root}`.
  - `medium` `patch` Found by dogfooding the procedure during this pass, missed by both reviewers: `_ids()` harvests every `DW-…` token **anywhere in the file**, not just headings, so illustrative shape placeholders written into an entry's own prose mint phantom deferrals. Reproduced live — writing `` `DW-B<n>-<n>` ``-style shapes into a new entry created five phantom ids (`DW-B`, `DW-D`, `DW-F`, `DW-G`, `DW-H`) and turned a green deferred-work check into 7 FAILs. Fixed: the offending prose was rewritten (detector back to only the 2 genuine unpromoted ids), and the procedure now forbids writing `DW-` followed by a letter or digit in `summary:`/`evidence:` unless it names a real id.
  - `low` `patch` `{story}` derivation was undefined for a spec filename with no `spec-` prefix — real, not hypothetical: durable story specs live at `planning-artifacts/specs/spec-<slug>/SPEC.md`, whose filename is `SPEC.md`, so both the numeric branch and the stated "part after `spec-`" fallback fail. Fixed: the fallback is now the whole filename stem (with `spec-` stripped only if present), and every character outside `[A-Za-z0-9-]` is replaced so the id stays one parseable token.
  - `low` `patch` "match the full leading run of `\d+-\d+`" was self-contradictory — `\d+-\d+` is exactly two groups, but "full leading run" invites extending through further `-<digits>` segments, so `spec-2-1-3-way-merge-….md` reads as either `2-1` or `2-1-3`. Fixed: exactly two groups, matching stops at the second, with that counter-example added alongside the existing multi-digit one.
  - `low` `patch` "one past the highest suffix already used, compared numerically" was undefined when an existing heading carries a non-integer trailing segment. Fixed: such headings are ignored for the suffix computation and take no number out of circulation.
  - `low` `patch` "read `.project.slug` from its JSON output" did not say which stream, so a warning line on stderr could break the JSON parse and silently degrade a mason run to the unknown-station fallback. Fixed: stdout only, stated explicitly.
  - `low` `patch` The unknown-station fallback left no trace, and its output is indistinguishable afterwards from a correctly-resolved non-mason id, so the degradation was unobservable. Fixed: an unresolved station must now be recorded in the entry's `evidence:` — inside the existing free-text field, preserving the frozen `source_spec`/`summary`/`evidence` schema.
  - `low` `patch` Nothing stated the relationship between the `### {id}: <one sentence>` heading title and the `summary:` field one line below, though the Design Notes fix it deliberately. Fixed: the instruction now says the heading repeats the same sentence used for `summary:`.
  - `medium` `defer` `.claude/skills/bmad-loop-sweep/deferred-work-format.md` declares itself canonical for this exact file and mandates both sequential `DW-<seq>` numbering and a compulsory pre-append dedupe check — two rules the defer bullet now contradicts head-on. Partly anticipated by that doc (the orchestrator normalizes flat entries on sweep) but the id-scheme and dedupe halves are genuinely unreconciled, and Story 7.1's Never clause scopes ledger-format normalization out. Recorded as `DW-FU-7-1-3`.
  - `medium` `defer` CAP-1 names only five of eight stations, so scribe, steward and herald fall into "every other station" and are silently given `DW-FU-<story>` — a shape none of them has ever used (measured: 7/7, 23/23 and 29/30 of their tracked entries use mason's shape). Atlas is assigned `DW-FU-<story>` but 0 of its 44 tracked entries use it. Distinct from `DW-FU-7-1-2`, which concerns the follow-up-promotion meaning rather than the station-to-shape mapping. Recorded as `DW-FU-7-1-4`.

### 2026-08-10 — Review pass 3
- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 0, medium 3, low 2)
- defer: 2 (medium 2)
- reject: 8 (low 8)
- addressed_findings:
  - `medium` `patch` The id-uniqueness scan was heading-scoped (`^#{2,4}\s+DW-…`) while every consumer is file-scoped. Measured: doctor's own Tier-3 file cites four follow-up ids (`DW-FU-6-4`, `-6-5`, `-6-6`, `-6-8`) in `evidence:` prose with **no matching heading**, so a heading-only scan would re-mint one of them and silently conflate a generic defer with an unrelated follow-up promotion — passing the gate while being a different item. Fixed: the scan now collects every `DW-` token anywhere in the text, matching `chain.py::_ids`, and applies the same `rstrip("-")` when comparing. Also extended to the station's **tracked** ledger, since an id already there belongs to a recorded item and reusing it makes the new entry masquerade as that one.
  - `medium` `patch` Pass 2's `SPEC.md` fallback (use the filename stem) is provenance-destroying: durable story specs live at `planning-artifacts/specs/spec-<slug>/SPEC.md`, whose stem is the constant `SPEC`. Measured 57 such specs across the fleet — every one would collapse onto the same id, destroying exactly the property the id exists to carry, and deviating from the spec's own I/O matrix row ("`{story}` = the full slug"). Fixed: when the stem is empty or a generic container name (`SPEC`/`spec`/`README`/`index`), the **parent directory** name is used instead. Hyphen runs are now collapsed and leading/trailing hyphens trimmed, closing a related collision where `…-foo-` and `…-foo` are one id to every consumer's `rstrip("-")` but two distinct strings to the scan.
  - `medium` `patch` The station name and the destination file resolve through two independently-mutable pieces of per-worktree state — the active-project marker vs. the `_bmad-output/implementation-artifacts` **symlink** — which CLAUDE.md records desyncing in production (2026-07-14). On desync the id carries station A's convention and lands in station B's ledger, silently and undetectably. Fixed: a `readlink -f` cross-check now requires the resolved path's `projects/<slug>/` component to equal the resolved slug; a mismatch degrades to unknown-station and is recorded in `evidence:`. Verified live this pass — slug and realpath agree in this worktree.
  - `low` `patch` Step 3 defined only "file does not exist → treat as empty", conflating that with an **unreadable but present** file (permissions, dangling symlink target) — the wrong answer there, since it mints a duplicate over an id that simply could not be read. `chain.py::_is_file` deliberately distinguishes these two after a live false-green in this repo. Fixed: a read failure other than non-existence is now explicitly not an empty set.
  - `low` `patch` "the same shape the ledger parser recognizes" never said which parser, and two exist with different shapes (`chain.py::_ENTRY_RE` = `^#{2,4}\s+DW-…`; marshal's `core/deferred_work.py::_HEADING_RE` = `^### (DW-\d+): `). The stated shape is correct for the detector the Code Map cites, but a future editor reconciling them could pick the wrong one. Fixed: the detector is named explicitly. Also added the concrete phantom case the prose rule most invites — writing the non-mason shape with a literal `FU` in prose yields the phantom `DW-FU`.
  - `medium` `defer` Minting an id converts every new Tier-3 defer into a hard `tier3-only-deferral` FAIL of the always-on deferred-work gate, and no automatic promoter recognizes the minted shape (marshal's promoter needs `^### (DW-\d+): ` plus five fields incl. `origin: review-budget-followup`). Scoped out by the story's Never clause (tracked ledger / promotion mechanism / detector belong to Stories 7.2–7.3). Recorded as `DW-FU-7-1-5`.
  - `medium` `defer` The minted entry carries no `status:`, so `bmad-loop-sweep` never sees it as open; and the id heading makes it look already-canonical to the very normalization pass that would have supplied one, potentially leaving these entries *less* likely to be triaged than the anonymous bullets they replace. Unpatchable here — the story's Always clause freezes the three-field schema. Recorded as `DW-FU-7-1-6`.
  - Rejected (8, all low): Blind Hunter's headline "four live FAILs manufactured by this change" — measured, it is **two** (`DW-FU-7-1-3`/`-7-1-4`); the earlier two had been promoted. Its "the prose rule is necessary but not sufficient" — false: `_DW_RE` requires `[A-Za-z0-9]` immediately after `DW-`, so a non-alphanumeric next character starts no match at all, making the stated safe condition genuinely sufficient. Heading-title/renderer truncation mismatch (cosmetic; the duplication is a deliberate Design Note). Single-numeric-group filenames colliding with a neighbouring story's bare id (zero such specs exist). mason-starts-at-1 vs. others-start-bare "inconsistency" (by design, per Design Notes). Unbounded FAIL growth from the no-dedupe rule, the `DW-FU-` fleet-precedent inversion, and "derive the shape from each station's own ledger" — all already carried by `DW-FU-7-1-3`/`-7-1-2`/`-7-1-4`. A live phantom `DW-FU` in doctor's Tier-3 (from passes 1–2 `evidence:` prose) is real but currently masked by the same phantom in the tracked twin, and unactionable here: fixing it means editing existing entries, which both this step and the invocation forbid — carried as a residual risk instead.

### 2026-08-10 — Review pass 4
- intent_gap: 0
- bad_spec: 0
- patch: 11 (high 1, medium 5, low 5)
- defer: 1 (medium 1)
- reject: 9 (low 9)
- addressed_findings:
  - `high` `patch` Pass 3's station cross-check compared the **`pyforge-`-stripped** slug against the destination path's `projects/<slug>/` component, which is always the **unstripped** directory name — so the check could never pass on any station. Reproduced live: slug `pyforge-doctor` → stripped `doctor`; path component `pyforge-doctor`. Every run would declare the station unknown, making the mason branch (the entire reason step 1 exists) unreachable and stamping a false "station could not be resolved" note into every entry. Fixed: the cross-check compares the raw slug; stripping is now explicitly scoped to the mason-vs-other branch test alone, stated at both the point of resolution and the point of comparison. Verified live after the fix — the cross-check passes in this worktree and was used to mint this pass's own deferral.
  - `medium` `patch` The tracked-ledger path added in pass 3 was given unrooted (`planning-artifacts/deferred-work-ledger.md`), and the natural worktree-relative reading resolves to the **wrong file**. Measured in this run's worktree: `implementation-artifacts` symlinks out to the shared checkout, but `planning-artifacts` is a worktree-local git checkout frozen at the branch point — 16,149 B vs the shared copy's 28,329 B, missing all six of this story's own ids. The cross-file collision scan would have read a ledger that predates every id it was added to catch. Fixed: the tracked ledger is now resolved as the sibling of the **resolved** Tier-3 path, with the measurement recorded as the reason.
  - `medium` `patch` The suffix rule said to ignore ids "whose trailing segment is not a plain integer", which judges the wrong substring: mason's ledger carries `DW-1-10-1`, whose trailing segment *is* the integer `1`, so story `1-1` would count it as its own suffix and skip a number — the same class of prefix-vs-token confusion the bullet's own `DW-FU-4-14` example warns about. Fixed: an id counts only when the whole remainder after the base id is one plain integer and nothing else, with the live `DW-1-10-1` counter-example given.
  - `medium` `patch` Two rules in the same paragraph contradicted each other for slug-shaped stories: "the bare id counts as suffix `1`" vs. "ignore any id whose trailing segment is not a plain integer". For a fallback slug the bare id's trailing segment is a word, so the branch trigger fired while the counting rule discarded the only id in play — and the non-mason branch, unlike mason's, had no "start at" floor, leaving "one past the highest" undefined. The most literal resolution re-mints the bare id: the exact duplicate the procedure exists to prevent. Fixed: the bare-base-id rule is stated once, shared by both branches, explicitly independent of `{story}`'s shape, with the resulting `-2` floor named.
  - `medium` `patch` `readlink -f` was made load-bearing for the cross-check, but it prints **nothing** and exits non-zero when a parent directory is missing (verified: missing final component → prints path, exit 0; missing parent dir → empty, exit 1). That is exactly the state the same bullet blesses — "the append creates `{deferred_work_file}`", a station's first-ever defer — so an empty result compared against the slug reads as a desync and silently degrades a brand-new station to unknown permanently. Fixed: the empty-result case is defined as not-yet-created, resolved via the nearest existing ancestor.
  - `medium` `patch` Step 3 mandates a fresh re-read of both ledgers before **each** id but never sanctioned the cheap equivalent, so the literal reading loads whole files into a pass that is already damped — doctor's Tier-3 is 135,888 B and atlas's tracked ledger 146,477 B, per defer finding. Fixed: a token-scoped `grep` using the detector's own pattern is named as satisfying the step exactly and preferred, with the sizes given as the reason.
  - `low` `patch` The unreadable-file fallback said to "mint with a fresh `-<n>` suffix beyond any id you did manage to read" — undefined in its most likely case, where the read failed and *no* ids were read. Fixed: with no ids readable, the base id is treated as taken and the suffix starts at `-2`.
  - `low` `patch` `{story}` derivation silently truncated a letter-suffixed story key: `spec-6-1a-….md` matched two numeric groups and yielded `6-1`, filing story `6-1a`'s deferral under a different story's id. `pyforge/marshal/core/identity.py` is this repo's documented sole owner of the story-key format, its key shape carries an optional single letter, and its promoted-id renderer emits that letter. Latent, not live — measured 0 letter-suffixed spec files, sprint keys, or ledger ids across the fleet — but it is the shape of the documented AD-38 incident. Fixed: the optional letter is matched and kept.
  - `low` `patch` The prose `DW-` guard named only `summary:`/`evidence:`, yet the instruction two lines above mandates the heading repeat the `summary:` sentence verbatim — so the heading is where a shape token most visibly lands (doctor's own `### DW-FU-7-1-2:` heading carries exactly such a token). Transitively covered, never stated. Fixed: the guard names the heading title explicitly and says why it is not exempt.
  - `low` `patch` The sanitization rule (`replace → collapse → trim`) had no non-empty postcondition, and an empty `{story}` mints an id with nothing after the prefix — which the harvest reads as a bare phantom, the precise failure the same bullet ends by warning about. Fixed: `{story}` must be non-empty, falling back to the parent directory name.
  - `low` `patch` Pass 3 made `evidence:` the channel for the unresolved-station note, but in free prose with no fixed wording, so the degradation it was added to expose still could not be found mechanically — and pass 4 added a second such note (unreadable ledger) to the same field. Fixed: both notes now open with a fixed literal token (`station-unresolved:`, `ledger-unread:`), which keeps the frozen three-field schema intact while making the entries greppable.
  - `medium` `defer` marshal's promoter mints the follow-up id with **no numeric counter** and skips any candidate whose id is already a complete token in the tracked ledger, so unlike the emitter it cannot suffix around a collision — once an emitter-minted entry for a story is promoted, a genuine `review-budget-followup` deferral for that same story is dropped by `marshal land` silently, and its Tier-3 id then reds the gate uncloseably. Live already: `DW-FU-7-1` sits in doctor's tracked ledger. Scoped out by the story's Never clause (promotion mechanism), and it falsifies the "collision-safe by suffix" premise recorded in `DW-FU-7-1-2` — which this pass must not edit. Recorded as `DW-FU-7-1-7`.
  - Rejected (9, all low): Blind Hunter's claim that the `SPEC.md` parent-directory fallback "collapses every story under one Spec onto a single id" — measured false: durable per-story specs are flat `spec-<epic>-<seq>-….md` files (doctor alone has 20+, all hitting the numeric branch), while `specs/spec-<topic>/SPEC.md` is one file per topic, so the fallback yields exactly one distinct id per file. Its claim that the single-append rationale is "inverted because `_anonymous` never runs on Tier-3" — the sentence makes no claim about the detector, and the story's own Intent grounds anonymity in promoter-invisibility, not a gate red; heading-without-fields is also not worse under any live check. Both reviewers' "every mint is an immediate `tier3-only-deferral` FAIL" and "the entry carries no `status:`" — already carried as `DW-FU-7-1-5`/`-7-1-6`, and now stale besides: measured live, doctor's tier3-only set is **empty**, all six ids having been promoted. The live phantom `DW-FU` present in both of doctor's files — real, but fixing it means editing existing entries, which both this step and this invocation forbid; carried as a residual risk since pass 3. Section length / bullet depth / instruction ordering (cosmetic). The triage log's missing `defer` itemization, the `bmad-loop-sweep` format-and-dedupe conflict, and the station-to-shape mapping gaps for scribe/steward/herald/atlas — already `DW-FU-7-1`, `-7-1-3`, `-7-1-4`.

## Design Notes

**Why `DW-FU-{story}` for four stations and `DW-{story}-<n>` for mason, literally per the
epic/SPEC text, rather than one uniform shape.** Direct inspection of four stations' tracked
ledgers (doctor, atlas, marshal, mason) shows `DW-FU-<story>` has, until now, been used
*exclusively* for "follow-up review still recommended" promotions (always paired with a
`promoted:` annotation) -- never for a generic defer. Generic defer promotions instead show
inconsistent ad hoc shapes per station: mason is 100% consistently `DW-{story}-<n>`; doctor is
consistently bare `DW-{story}-<n>` too; marshal's are a mix of `DW-{story}-<n>` and outright
freeform scope tags (`DW-AUD-2026-07-31-*`, `DW-SYNC-2026-08-08-*`). No pre-existing "emitter
convention" ever existed for generic defers -- doctor's own Tier-3 file has zero ids on any of
its 76 `source_spec` bullets today. Given that, the epic's stated convention reads as a fresh,
deliberate, operator-confirmed decision (dated the same day as this story) to standardize four
messy stations onto the one shape that's already collision-safe against `bmad-loop sweep`'s
own generic `DW-<n>` numbering, while leaving mason's already-clean, already-consistent shape
untouched -- exactly the "respects each station's own precedent rather than normalising them"
constraint the SPEC states. This spec follows that literal mapping rather than the historical
ad hoc shapes.

**Collision suffix is this story's own minimal addition, not in the epic's literal text.**
The epic's examples (`DW-FU-{story}` with no suffix) only cover the single-defer-per-story
case. A second "defer" finding for the same story -- plausible within one review pass, and
certain across a story's dev/review/loopback lifecycle -- would otherwise repeat the same
heading twice, defeating the exact citability CAP-1 exists for. The suffix rule is the same
shape mason already always carries, applied to the other stations only on collision, so the
common case still matches the epic's literal example exactly.

**Heading title duplicates the `summary:` field on purpose.** `### {id}: <one sentence>`
repeats the same sentence that also appears as the `summary:` field one line below. This
mirrors the file's own existing `### DW-1: Follow-up review still recommended for ...` shape
(so a human skimming headings sees the same signal the existing entries give), and keeps the
minting instructions fully mechanical -- copy the one sentence already being composed for
`summary:`, no separate judgment call about how to shorten it into a title.

## Verification

**Manual checks (if no CLI):**
- Trace the new "Minting the id" procedure by hand against each row of the I/O & Edge-Case
  Matrix and confirm the id it produces matches the stated expectation.
- `git diff .claude/skills/bmad-dev-auto/step-04-review.md` touches only the "defer" bullet
  block -- no other instruction in the file changes.
- Visually confirm the edited file's markdown is well-formed: the fenced ```markdown``` block
  still opens and closes correctly, and the numbered/bulleted list nesting under step 5 is
  unbroken.

## Auto Run Result

Status: `done` (review pass 4 — follow-up review of a `done` spec).

**Implemented change.** `bmad-dev-auto`'s "defer" triage path now mints a unique,
station-appropriate id and heads each new Tier-3 entry with `### DW-...`, instead of appending an
anonymous `- source_spec:` bullet. Pass 4 made no new feature changes; it repaired defects in the
minting procedure itself.

**Files changed** (since `184aec727e`, 34 insertions / 1 deletion, one file):
- `.claude/skills/bmad-dev-auto/step-04-review.md` — the "defer" triage bullet gains the id-minting
  procedure (station resolution + path cross-check, `{story}` derivation, id-collision scan across
  both ledgers, mason vs. every-other-station shapes) and the `### {id}:` heading. All three diff
  hunks are confined to that bullet; no other instruction in the file changed.

**Review findings, pass 4.** 11 patched (high 1, medium 5, low 5), 1 deferred (medium), 9 rejected
(all low), 0 intent_gap, 0 bad_spec. The high finding is the load-bearing one: pass 3's station
cross-check compared the `pyforge-`-stripped slug against the unstripped `projects/<slug>/`
directory name, so it could never pass on any station — every run would have declared the station
unknown and the mason branch was unreachable. Also corrected: the tracked-ledger path resolved to a
stale worktree-local checkout, the suffix rule mis-parsed `DW-1-10-1`, a self-contradiction between
the bare-id and non-integer-suffix rules, `readlink -f`'s empty result on a missing parent
directory, and the absence of any sanctioned cheap id harvest. The deferral (`DW-FU-7-1-7`) records
that marshal's promoter cannot suffix around an id collision — it silently drops the promotion —
which falsifies the "collision-safe by suffix" premise held by the existing `DW-FU-7-1-2`.

**Verification performed.**
- Traced the corrected procedure by hand against every I/O & Edge-Case Matrix row, then **dogfooded
  it live** to mint this pass's own deferral: station cross-check passed against the raw slug
  (`pyforge-doctor`), `{story}` derived as `7-1`, harvest across both resolved ledgers returned the
  bare id plus suffixes 2–6, minted `DW-FU-7-1-7`. Re-harvest after the append confirms exactly
  seven real ids and no phantoms.
- `git diff 184aec727e --stat`: one file, three hunks, all inside the "defer" bullet.
- Markdown well-formed: 6 fence markers (3 balanced pairs); numbered/bulleted nesting under the
  bullet unbroken.
- Confirmed live measurements behind three findings: worktree ledger 16,149 B vs shared 28,329 B
  (different md5); `readlink -f` exits 1 with empty output on a missing parent directory but 0 on a
  missing final component; 0 letter-suffixed story keys exist across the fleet (the AD-38 shape is
  latent, not live).

**Residual risks.**
- `DW-FU-7-1-7` is tier3-only until the orchestrator promotes it — the known, already-recorded
  `DW-FU-7-1-5` condition, not a new regression.
- The phantom `DW-FU` token remains in both of doctor's ledgers from passes 1–2 prose. Unactionable
  here: removing it means editing existing entries, which both this step and this invocation forbid.
  It is masked (present on both sides), so it reds nothing today.
- The concurrent-worktree mint race is narrowed by the fresh re-read but not eliminated; accepted
  and documented in the procedure.
- Six of the eight stations still resolve to the non-mason shape by default; whether that mapping is
  right is carried by `DW-FU-7-1-4`, and its collision behaviour by `DW-FU-7-1-7`.

