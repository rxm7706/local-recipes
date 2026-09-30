---
title: '34.4: Each station has a checked-in flag inventory of its runtime capabilities'
type: 'feature'
created: '2026-09-28'
status: 'done'
baseline_revision: '6b7d586b33fdf7edf7b54b81c9cacc8f33efffa7'
flag-exempt: flag-infrastructure   # the retrofit's own infrastructure (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
warnings: [oversized]
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-2-the-flag-gate-ships-in-scripts-outside-every-station-and-runs-in-detectors-ci.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_effect.py
  - src/platform/config/flags.json
deferred:
  - summary: >-
      Doctor's Surface-line join resolves only 7.2% of the CAP rows the inventory lists (56 of 778), so the
      per-station "Runtime CAPs with no flag" counts are a lower bound.
    evidence: |-
      Measured on the checked-in reports at this story's review: unresolved 722, module 38, planning 14, runtime 4.
      `_story_surface_by_cap` attaches a `Surface:` line to a CAP only when the citing story's line names the Spec
      slug and the CAP together, and most epics.md stories cite `(CAP-n)` against absorbed Spec slugs or carry no
      `Surface:` line. This story reuses the join by mandate (intent: "never invent a second one"), so it reports the
      gap as `unresolved` rows and does not close it. Closing it means a Doctor story that widens the join (for
      example to read the Spec's own CAP-to-story map) and then re-runs `pixi run -e pyforge-guild flag-inventory`;
      each Smith should read the `unresolved` rows of their report before sizing a retrofit.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_effect.py:498
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-feature-flag-governance` CAP-7 retrofits the rule onto work that predates it: every station's existing
capabilities whose code is reachable at runtime go behind flags that default ON (one flag per CAP, Q6), so each flag
works as a kill switch; and every pre-rule backlog story gains a flag block or an exemption, so the CAP-2 gate's warnings
reach zero. The retrofit stories are each Smith's, minted after an inventory exists. Nothing lists, per station, which
CAPs reach a user at runtime and which of them a flag gates.

**Approach:** `scripts/flag_inventory.py` (a report, never a gate: exit 0 unless it cannot run, exit 2 then) writes one
checked-in Markdown report per station to `docs/governance/flag-inventory/pyforge-<station>.md`; a `flag-inventory` pixi
task runs it. For each station:
- every CAP declared by an open Spec folder the station hosts, joined to its code the way
  `pyforge.doctor.sources.capability_effect` already joins them (the citing story's `Surface:` line in `epics.md`) —
  reuse that join, never invent a second one;
- whether that code is reachable at runtime and through what: a CLI verb (the station's CLI), an MCP tool (the station's
  MCP registry), a REST route or a portal view (the station's `dashboard/` URLs);
- the flag key in the one tree that gates it, or `none`;
- every pre-rule `type: feature` story spec the gate (Story 34.2) warns on, with its key and status.
Each report's header names the SHA it read and two counts — runtime CAPs with no flag, warned specs — the numbers each
Smith's retrofit stories are minted against after this lands. The output is deterministic, so a second run on the same
tree is byte-identical.

Ledger key: `34-4-each-station-has-a-checked-in-flag-inventory-of-its-runtime-capabilities`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-34.2.

### Living CAP citations

- `spec-feature-flag-governance` CAP-7 (the inventory half; the retrofit half is each Smith's, minted after this lands).

## Acceptance Criteria

- Given the live tree When `pixi run -e pyforge-guild flag-inventory` runs Then it writes eight reports under `docs/governance/flag-inventory/` and exits 0
- Given a fixture station with one CAP whose story's `Surface:` names a CLI verb module and no flag in the tree When the inventory runs Then that CAP is listed with its verb and `none`
- Given the same CAP with its key in the tree When the inventory runs Then it lists the key
- Given a CAP whose surface is only a planning document When the inventory runs Then it is listed as not reachable at runtime, never counted as unflagged
- Given a pre-rule `type: feature` spec with neither block nor exemption When the inventory runs Then it appears in its station's warned list with its key and status, matching the gate's WARN list for that station
- Given a second run on the same tree When the reports are compared Then they are byte-identical
- Given an unreadable tree When the inventory runs Then it exits 2 naming the input and writes no partial report
- Given the change When `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Keep the script in `scripts/`, its tests in `tests/scripts/`, its reports in `docs/governance/flag-inventory/`; add the
  script's reason-tagged line to `scripts/spec_surface_allowlist.txt`; register the task in `pixi.toml` and regenerate
  `environment.yaml` in the same change; record the new paths in the Guild Spec's `.memlog.md` via `memlog.py`.
- Reuse the gate's classifier (Story 34.1's `scripts/flag_rule.py`) for the warned list, so the inventory and the gate
  can never disagree.
- Treat a CAP whose code the join cannot resolve as its own `unresolved` row, never as unflagged and never dropped.

**Never:**
- Do not mint, draft or propose any station's retrofit stories: each Smith mints its own after this lands.
- Do not add a flag to the tree or change any station's code.
- Do not make the inventory a detector (no `DETECTOR` marker, no `detectors-ci` row): it reports, the gate judges.
- Do not import a station's internals; do not edit `SPEC.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CLI CAP, no flag | verb module in `Surface:` | row with the verb, `none` | — |
| flagged CAP | key in the tree | row with the key | — |
| planning-only CAP | no runtime surface | listed, not counted as unflagged | — |
| unresolvable CAP | no citing story | `unresolved` row | — |
| warned spec | pre-rule, `neither` | in the station's warned list | — |
| rerun | same tree | byte-identical reports | — |
| unreadable tree | malformed JSON | nothing written | exit 2 |

</intent-contract>

## Code Map

- `scripts/flag_rule.py` -- Story 34.1's reader; reuse `read_frontmatter`, `classify_frontmatter`, `is_story_spec`, `FlagRuleError` (exit 2). The warned list is never re-derived here.
- `scripts/flag_gate_check.py` -- Story 34.2's gate; import its public `load_inputs`, `story_specs`, `judge_one`, `station_of`, `K_PRE_RULE`, `TreeUnreadable`, `ListingFailed`. Warned = the `K_PRE_RULE` findings of `judge_one`, so inventory and gate cannot disagree. Do not edit it.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_effect.py` -- the join: `_story_surface_by_cap` (line 498), `_caps_cited_on_spec_line` (488), `_split_surface_fragments` (307), `_is_document_surface_fragment` (273), `_strip_surface_annotation` (283), `_resolve_surface_paths` (327). `board.py`: `_parse_declared_cap_ids` (254), `_canonical_epics` (600). The gather at lines 531-731 is the call order to follow. Read-only; not edited.
- `docs/governance/guild-roster.json` -- `stations` (the eight report names) and `spec_statuses_ended_acts` (`archived`, `absorbed`, `superseded`): a Spec is open when its status is not in that list. Read at run time, never copied.
- `src/platform/config/flags.json` -- the one tree; `flags` mapping keys (today three, none gating a CAP).
- `pixi.toml` line ~1316 -- `[feature.guild-tasks.tasks.flag-gate-check]`: the sibling task to mirror for `flag-inventory` (no `DETECTOR`, no `detectors-ci` row).
- `scripts/spec_surface_allowlist.txt` lines 40-44 -- the `flag_rule.py` / `flag_gate_check.py` lines to mirror.
- `tests/scripts/test_flag_gate_check.py` -- fixture-tree header to copy (`tmp_path` tree with roster, baseline, tree, specs).
- Measured 2026-09-29: open Specs per station 1-5 (status `ready` or `draft`); the other Specs are `absorbed` or `archived`. Only atlas and steward have a `dashboard/`; only atlas and marshal have `mcp/`. Atlas, mason and warden are not installed in `pyforge-guild`, so reach is read as text with `ast`, never imported.

## Tasks & Acceptance

**Execution:**
- `scripts/flag_inventory.py` -- new: `--root`, `--out-dir`; read roster, baseline and tree first (any `FlagRuleError` or unreadable epics: exit 2 naming the input, nothing written); build all eight reports in memory, then write; exit 0 -- the report
- `tests/scripts/test_flag_inventory.py` -- new: one fixture-tree test per I/O row and per AC, a byte-identical rerun, the exit-2 rows, the gate-WARN-list equality, and a live-tree test that the eight reports build; the seam test asserts the join names exist
- `docs/governance/flag-inventory/pyforge-<station>.md` (eight) -- generated by the script, never by hand
- `pixi.toml` -- add `[feature.guild-tasks.tasks.flag-inventory]` after `flag-gate-check`; `environment.yaml` -- regenerate with `pixi project export conda-environment -e build > environment.yaml`; re-render `docs/how-to/pixi-tasks.md` (`docs-pixi-tasks`) -- the task registry and its page must agree
- `scripts/spec_surface_allowlist.txt` -- add the `scripts/flag_inventory.py` line, reason-tagged -- same shape as `flag_gate_check.py`
- `docs/governance/spec-feature-flag-governance/.memlog.md` (via `_bmad/scripts/memlog.py append`) and every co-governor `python scripts/spec_surface_reconcile.py` names -- record each new and changed path; never `--write-baseline`

**Acceptance Criteria:**
- Given the script, when `pixi run -e pyforge-guild detectors --scope repo --list` runs, then `flag_inventory` is not listed and no registry gap is reported
- Given the shipped script, when its imports are read, then it imports no `pyforge.<station>` module except Doctor's join module, and no inventoried station's runtime code
- Given a fixture where the gate WARNs on N specs of one station, when the inventory runs, then that station's warned list holds the same N paths

## Spec Change Log

- 2026-09-29 -- implemented: status `in-progress` -> `in-review`; every task done; the intent contract is unchanged.
  Two readings the contract left open, both taken from the Design Notes and recorded here: (1) a resolved path that is
  itself a document (a `:line` suffix such as `specs/spec-x/SPEC.md:5` hides the suffix from the join's fragment test) is
  dropped after resolution, so a surface of documents only reads `planning`, not `module`; (2) `routing.py` and `api*.py`
  count as REST only under `dashboard/**` (steward's `dashboard/routing.py` is a route table, warden's top-level
  `routing.py` is an ecosystem classifier), while `station_api.py` counts at the package top level. The join resolves few
  CAPs on today's tree (its `_story_surface_by_cap` needs the Spec slug and the CAP on one `epics.md` line), so most rows
  read `unresolved` by design; that is the number each Smith mints against, not a defect of the report. Beyond the Tasks
  list: `docs/how-to/pixi-tasks.md` and `docs/map.yaml` re-rendered (`docs-pixi-tasks`); `environment.yaml` re-exported,
  byte-identical.

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-7 and the Q6 ruling (memlog 23), the
Dream's *What it looks like when real* (the retrofit runs in two steps), decomposed 2026-09-28 (night) as Epic 34's mint.

## Binding

Parent Spec capability: `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-7 (Guild-owned; the inventory is
Doctor's, the retrofit stories each Smith's).
Dream: `docs/dreams/feature-flag-governance.md` § Realization log → *2026-09-28 (night)*.
Ledger key: `34-4-each-station-has-a-checked-in-flag-inventory-of-its-runtime-capabilities`.
Ledger status at mint: `backlog`.
Policy: `marshal-policy.toml` `[epic_surfaces]` `"34"`.

## Design Notes

**The join is Doctor's, by import; the stations are read as text.** "Reuse that join" and "do not import a station's internals" read together as: import Doctor's own join (`capability_effect` and `board`, the mechanism this story belongs to) and never import a station being inventoried. Atlas, mason and warden are not even installed in `pyforge-guild`. The join's helpers are underscore-private and no script imports a private name from Doctor today, so the eight names load through one `_load_join()` seam; an `ImportError` there is exit 2, and a test pins the names.

**Row classes, in precedence order.** For each declared CAP of an open Spec: (1) `runtime` when a resolved code fragment is an entry point of the station's package (`cli.py`, `cli/**`, `__main__.py` = CLI; `mcp/**` = MCP; `dashboard/**/urls*.py`, `routing.py`, `api*.py`, `station_api.py` = REST; other `dashboard/**` = portal); (2) `module` when it resolves to code that is no named entry point (listed, not counted as unflagged: the inventory cannot show a user reaches it); (3) `planning` when every fragment is a document; (4) `unresolved` when no citing story exists, the story has no `Surface:` line, or no fragment resolves. Verbs come from `add_parser("…")`, tools from a module-level `TOOL_SPECS` dict or a `.tool`-decorated function, routes from `path("…")`, all read with `ast`; a module with none is named by its path. Names past six collapse to `(+n more)`.

**The flag column.** A CAP is gated when a tracked story spec of the same station has a `flag:` block whose `key` is in the tree and whose text cites the Spec slug and CAP (the join's `_caps_cited_on_spec_line`). A key the tree lacks reads `none (key <k> not in tree)`. Nothing else links a flag to a CAP until Steward's metadata story lands.

**Header counts.** `Runtime CAPs with no flag` counts `runtime` rows whose flag is `none`; `Warned specs` counts the gate's `flag-pre-rule` findings for the station. The header also names `git rev-parse HEAD` (`unknown` outside a checkout). No date, so a rerun is byte-identical.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-guild lint-types` — expected: pass.

**Manual checks:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_inventory.py -q` — expected: pass.
- `pixi run -e pyforge-guild flag-inventory` twice — expected: exit 0, and `git diff --exit-code docs/governance/flag-inventory/` after the second run.

## Review Triage Log

### 2026-09-29 — Review pass
- verdicts: 38 findings — high 0, medium 2, low 30, false 6, maybe-false 0
- findings:
  - Blind Hunter
  - `[medium]` `[defer]` Header "Runtime CAPs with no flag" is a lower bound and the header does not say so — the class breakdown (unresolved included) is already on the line below the counts (`scripts/flag_inventory.py:565-566`), so that half is refuted; the root cause is real: the join resolves 56 of 778 rows (7.2%, measured on the checked-in reports). It is Doctor's existing join, which the intent says to reuse, so deferred as `DW-doctor-34-4` (location `capability_effect.py:498`).
  - `[low]` `[reject]` Report lists only entry points that a CAP reaches, not every verb/tool/route — the intent asks for a CAP-keyed inventory; an entry-point-first table is an addition, not a defect, and adds a second report shape.
  - `[low]` `[patch]` Mis-split `Surface:` fragments render with unbalanced backticks — verified: 230 of 778 rows had an odd count (doctor CAP-2, CAP-36, CAP-71). Fixed: `_collapse_paths` strips backticks from each token before wrapping; new fixture and live-tree tests assert no odd cell; checked-in reports regenerated, 0 odd rows.
  - `[low]` `[reject]` Portal packages (`django-<station>`) and `src/platform` never count; cross-station Specs can only read `module` — the intent scopes portals to "the station's `dashboard/` URLs"; measured: 1 module row names a `django-` path and 0 module rows point into another station's package, so the live effect is nil.
  - `[low]` `[reject]` A story's `Surface:` line is attributed to every CAP it cites — this is the join's defined behaviour, which the intent mandates reusing; marking shared rows would add a second column for no live decision.
  - `[low]` `[reject]` Classification too loose (`dashboard/models.py` reads portal; tests and `pixi.lock` appear as module code) — zero live effect: the only four `runtime` rows are marshal CLI rows; `module` rows are never counted as unflagged.
  - `[low]` `[reject]` Header SHA is weak provenance; reports go one commit stale; no `-dirty` marker or `--check` — the intent says "names the SHA it read" (HEAD); a `-dirty` marker would make the second run differ from the first (the first run dirties the tree), breaking the byte-identical AC. Recorded as a residual risk.
  - `[low]` `[patch]` `write_reports` is not atomic; a mid-write `OSError` leaves a mix of new and stale reports — fixed: every report is written to a dot-prefixed temporary name, all are `os.replace`d only after every write succeeded, temporaries removed in `finally`; new test: a directory as one target exits 2, stale files stay byte-identical, no temporary left.
  - `[false]` `[reject]` Frontmatter parse failures are swallowed against the exit-2 contract — a malformed frontmatter is not an unreadable input: `SPEC.md` read errors already exit 2 via `_read_text`, and a malformed story spec is judged `neither` by the gate itself.
  - `[low]` `[reject]` Flag column accuracy gaps (slug substring, any-line citation, `startswith("none")`) — these are the join's `_caps_cited_on_spec_line` semantics; no live CAP is gated today (all four `runtime` rows read `none`); the mixed-key test gap is closed under the Verification Gap row below.
  - `[false]` `[reject]` Warned list mixes done/superseded specs and does not split by status — the AC requires the list to match the gate's WARN list for the station, and it does (840 = 840); the Status column is present.
  - `[low]` `[reject]` Over-pinned import set and missing coverage — the exact-set pin is the import-boundary contract; the named coverage gaps (mixed keys, backtick fragments, mid-write failure) are closed by the patches in this pass.
  - `[low]` `[reject]` 285 near-identical unresolved rows and a legend repeated in all eight reports — a readability preference; collapsing into ranges adds a second rendering path.
  - `[false]` `[reject]` Memlog entry out of chronological order — the memlog is append-only and orders by append time; the earlier entry carries a later date, not this one.
  - Edge Case Hunter
  - `[low]` `[patch]` `write_reports` mid-write `OSError` — same root cause as the Blind Hunter atomic-write row; fixed there.
  - `[low]` `[reject]` Absolute glob `Surface:` fragment raises `NotImplementedError` inside the join — the run then exits 2 naming the crash (loud, never a false report); no live fragment does this.
  - `[low]` `[reject]` Surface fragment outside the repo root embeds an absolute path — measured 0 `/home/` strings in the reports; not reachable on the live tree.
  - `[low]` `[reject]` `head_sha` has no `-dirty` marker — same as the Blind Hunter SHA row.
  - `[low]` `[reject]` Slug substring match (`spec-alpha` inside `spec-alpha-beta`) marks a CAP gated — the join's `bare in line` test, reused by mandate; no live gated CAP.
  - `[low]` `[reject]` Incidental mention on a story line gates a CAP — same root as the row above.
  - `[false]` `[reject]` Story spec in a non-roster project is warned by the gate but absent from every report — measured: all eight projects holding story specs are roster stations; a ninth project is a roster (governance) change and `test_the_live_reports_agree_with_the_gate_on_the_warned_specs_of_every_station` would then red.
  - `[low]` `[reject]` `_load_join` retry reuses a cached stale `pyforge.doctor` module — it ends in `JoinUnavailable` and exit 2, loud; the environment editable-installs Doctor, so no stale copy exists.
  - `[low]` `[reject]` Spec status compared case-sensitively with the roster's ended values — the roster and every other reader compare exactly; no live status differs in case.
  - `[low]` `[reject]` Test pins the literal 8 reports — the AC says eight, and the roster holds eight stations.
  - `[low]` `[reject]` Fallback-join test could pass through a non-editable installed Doctor — Doctor is editable-installed here, so the fallback is exercised; the case is hypothetical.
  - `[low]` `[patch]` Claim: "nothing written" on exit 2 fails mid-write — same root cause; fixed under the atomic-write row.
  - `[low]` `[reject]` Claim: header SHA can name a commit whose tree differs from what was read — same as the SHA row.
  - `[false]` `[reject]` Claim: warned list drops specs under a non-roster project — same refutation as the non-roster row (0 such projects).
  - `[low]` `[reject]` Claim: any longer slug or station-naming line counts as a citation — same as the slug-substring row.
  - `[low]` `[reject]` Claim: reports differ per checkout and after commit — same as the outside-root and SHA rows.
  - Verification Gap Reviewer
  - `[medium]` `[patch]` No test combines an entry-point fragment with a non-entry or absent fragment; reviewer mutations `if entries and not others:` and `if not resolved or absent:` passed all 64 tests while marshal's count fell 4 to 1 — added two fixture tests (`cli.py`+`store.py`, `cli.py`+`missing.py`: both `runtime`, header count 1); each mutation now fails its test.
  - `[low]` `[patch]` Mixed present/absent flag keys on one CAP untested (`flag_cell` mutation passed) — added one fixture test: row lists the present key, header count 0; the mutation now fails it.
  - `[low]` `[patch]` Warned-list sort key not pinned by the test (sorted by status still passed) — fixture changed so path order differs from key order and status order; sorting by status or by key now fails.
  - Intent Alignment Auditor
  - `[low]` `[reject]` Reads "reachable at runtime" as entry-point files, so domain modules a verb calls read `module`, not `runtime` — the spec's Design Notes define exactly this; a static call trace would be a second analysis the intent does not ask for, and the legend says so.
  - `[low]` `[reject]` `module` class holds tests, `pixi.lock`, workflows, hooks — same as the Blind Hunter classification row.
  - `[low]` `[reject]` Live-tree tests assert shape and gate parity, not freshness of the checked-in reports — a check modulo the SHA line would red every planning PR that adds or re-statuses a story spec (the warned table carries status), a lane the intent does not ask for.
  - `[low]` `[reject]` Checked-in SHA is one commit behind HEAD — same as the SHA row; recorded as a residual risk.
  - `[false]` `[reject]` `pyforge-doctor-test` AC exercises no changed Doctor code — the AC is a regression gate as written and passes (3005 passed, 1 skipped); the new tests run under the spec's Manual checks (`tests/scripts`).

## Auto Run Result

Status: done

**Summary.** `scripts/flag_inventory.py` writes one checked-in report per roster station to `docs/governance/flag-inventory/pyforge-<station>.md` and exits 0, or 2 with nothing written when an input cannot be read. Each report lists the CAPs of the station's open Specs, joined to code through Doctor's own `Surface:`-line join, classed `runtime` / `module` / `planning` / `unresolved`, with the gating flag key or `none`, plus the specs the flag gate warns on. The warned list is `flag_gate_check.judge_one`, so it equals the gate's (840 = 840). The `flag-inventory` pixi task runs it; it is not a detector.

**Files changed.**
- `scripts/flag_inventory.py` — the inventory (new).
- `tests/scripts/test_flag_inventory.py` — 70 tests: every AC and I/O row, the byte-identical rerun, the exit-2 rows, gate parity, the join seam, the import boundary (new).
- `docs/governance/flag-inventory/pyforge-{atlas,doctor,herald,marshal,mason,scribe,steward,warden}.md` — generated reports (new).
- `pixi.toml` — the `flag-inventory` task; `environment.yaml` re-exported, byte-identical.
- `docs/how-to/pixi-tasks.md`, `docs/map.yaml` — re-rendered by `docs-pixi-tasks`.
- `scripts/spec_surface_allowlist.txt` — one reason-tagged line for the script.
- `docs/governance/spec-feature-flag-governance/.memlog.md` — two entries naming every new and changed path.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md` — `DW-doctor-34-4`, promoted from `deferred:` by `scripts/deferred_work_intake.py`.

**Review findings.** 38 findings: high 0, medium 2, low 30, false 6, maybe-false 0. Patched (5 root causes, 7 rows): the entry-point-plus-other-fragment classification test (medium) and two more test gaps (mixed flag keys, warned sort key); unbalanced backticks in 230 of 778 rows; a non-atomic report write. Deferred (1): the join resolves only 7.2% of CAP rows (`DW-doctor-34-4`, medium). Rejected (30 rows): each carries its recorded reason in the Review Triage Log above.

**Follow-up review recommended: `false`.** Patched entries by verdict: high 0, medium 1, low 6. Fewer than two `medium` and no `high`.

**Verification (exit codes read directly, never through a pipe).**
- `pytest tests/scripts/test_flag_inventory.py test_flag_gate_check.py test_flag_rule.py` — exit 0, 219 passed.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — exit 0, 3005 passed, 1 skipped.
- `pixi run -e pyforge-guild lint-types` — exit 0.
- `pixi run -e pyforge-guild flag-inventory` twice — exit 0 each; `diff -r` of the two report sets is empty; 8 reports; 0 odd-backtick rows of 778.
- `python scripts/spec_surface_reconcile.py` and `pixi run -e pyforge-guild spec-surface-check` — exit 0; no co-governor named; `--write-baseline` never run.
- `pixi run -e pyforge-guild deferred-work-check` — exit 0 after promotion.
- Mutation checks by the implementer: each classification, flag-cell, sort, backtick and atomic-write mutation now fails the test written for it.

**Residual risks.**
- The inventory is a lower bound: 722 of 778 rows read `unresolved` because the join needs the Spec slug and the CAP on one `epics.md` line. Each Smith should read the `unresolved` rows before sizing a retrofit (`DW-doctor-34-4`).
- The checked-in reports name the SHA of the HEAD they were generated at, so they are one commit behind after this change lands. Regenerate with `pixi run -e pyforge-guild flag-inventory` before landing; a rerun on an unchanged HEAD is byte-identical.
- The replace loop is not atomic across files: a failure of `os.replace` itself part-way (none seen) could leave a mix. Disk-full and unwritable-directory failures happen at temporary-write time, before any replace.
- `bmad-estate-check` reds on the gitignored, dispatch-seeded `.claude/skills/caveman/` (`section skills drifted`). It is outside this diff and is the same finding Story 34.2's record names.
- A rerun of the inventory writes an unchanged tree except the SHA line; no test checks the checked-in reports for staleness, by decision (it would red every planning PR that changes a story spec's status).
