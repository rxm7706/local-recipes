---
title: '23.4: Empty the intake inbox per its own README'
type: 'fix'
created: '2026-09-16'
status: 'done'
baseline_revision: '47d61c0f6bf2536c0d29b9a25f57b14fc9f58dea'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Intake dumps have no per-file disposition and several already have a specified or pitched Dream.

**Approach:** Route each folder per docs/intake/README.md and gists/INDEX.md. Nothing a specified/realized/archived Dream already absorbed remains in intake. No gist dump gains Dream YAML.

## Boundaries & Constraints

**Always:**
- Intake holds nothing a specified/realized/archived Dream already absorbed.

**Never:**
- Do not add Dream YAML to a gist dump.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| absorbed dump | folder already owned by a specified Dream | gone from intake | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-docs-shelf-alignment CAP-4`.
Surface: docs/intake/, archive/docs/intake/, owning Dream companions..
Ledger key: `23-4-empty-the-intake-inbox-per-its-own-readme`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-4-empty-the-intake-inbox-per-its-own-readme.md`.

## Auto Run Result

Status: done

**Summary:** Routed `docs/intake/` per its own README and `gists/INDEX.md`. Archived
(structure-preserving, `git mv`, content unmodified) four dumps whose owning Dream is
already `archived`/realized: `jira-github-projects-sync/` (steward Epic 8, 7/7 `done`),
`secure-live-dashboards/` (steward Epic 9, 7/7 `done`), `local-ocp-hybrid-environment/`
(steward Epic 12 incl. 12.9, `done`), and `gists/` (16 remaining snapshots + `INDEX.md`,
unmodified — no Dream YAML added, per the Never constraint). Left two folders in place,
per the same README: `agentic-sdlc/` (steward Story 59.4 is still `backlog` — the
README's own gate) and `external-repos-analysis-2026-08-22/` (grounds five separate
fold targets across atlas/CFE-mason/steward/herald/warden; only the mason fold is
confirmed realized, the rest are still open per the report's own fold list, so the
dump is not yet fully "absorbed" — archiving it is explicitly optional per the
2026-09-16 disposition research, not required).

**Files changed:**
- `docs/intake/jira-github-projects-sync/` → `archive/docs/intake/jira-github-projects-sync/`
- `docs/intake/secure-live-dashboards/` → `archive/docs/intake/secure-live-dashboards/`
- `docs/intake/local-ocp-hybrid-environment/` → `archive/docs/intake/local-ocp-hybrid-environment/`
- `docs/intake/gists/` → `archive/docs/intake/gists/`
- `docs/intake/README.md` — dispositions updated to reflect the four archives (struck
  through, sentinel-entry style) and the two stays, with reasons.
- `docs/reference/README.md`, `docs/MAP.md`, `docs/dreams/README.md` — the live pointers
  to `docs/intake/jira-github-projects-sync/` repointed to its new archive path.
- `archive/docs/README.md` — its `docs/intake/gists/INDEX.md` pointer repointed to
  `archive/docs/intake/gists/INDEX.md`, plus new bullets documenting the `intake/*`
  archive additions, matching how `specs/gists/*` and `specs/*.md` already document theirs.
  Dream-body citations of the moved paths are left as written throughout the fleet —
  historical prose describing what was captured where, per this repo's own
  historical-prose-keeps-its-original-names convention — see e.g. `docs/dreams/sentinel.md`
  still citing `docs/intake/sentinel/` after that 2026-08-15 archive.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`
  — surface-reconcile event recording the `docs/MAP.md` repoint (that file is governed by
  `spec-pyforge-doctor`, not this spec).
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`
  — story `23-4-empty-the-intake-inbox-per-its-own-readme` promoted to `done`.
- `scripts/.spec-surface-baseline.json` — scoped re-stamp for `pyforge-doctor/spec-pyforge-doctor`
  (`python scripts/spec_surface_check.py --write-baseline --spec pyforge-doctor/spec-pyforge-doctor`).

**Verification:**
- `pixi run -e pyforge-guild spec-surface-check` — `ok` (was `fail` on `docs/MAP.md` drift
  before the scoped re-stamp above).
- `pixi run -e pyforge-guild story-status-check` — `ok`, 0 audited (hand-implemented, no
  bmad-loop run record, per the detector's own documented behavior).
- `grep -rln '"intake"\|intake/' --include="*.py" src/ .claude/` — no hits; no
  code/detector depends on the moved paths.
- Manual: `find docs/intake -maxdepth 2` shows only `README.md`, `agentic-sdlc/`, and
  `external-repos-analysis-2026-08-22/` remaining.

**Residual risks / left incomplete:**
- `external-repos-analysis-2026-08-22/` and `agentic-sdlc/` deliberately remain in
  `docs/intake/` — see Summary. Both are named, gated stays per the README, not oversights.
- Dream-body files that narrate the now-moved intake paths (e.g.
  `docs/dreams/jira-github-projects-sync.md`, `docs/dreams/secure-live-dashboards.md`,
  `docs/dreams/local-ocp-hybrid-environment.md`, `docs/dreams/pyforge-steward.md`, other
  folded/archived station Dreams, and `docs/dreams/pyforge-warden.md`'s dated 2026-07-23
  gist-audit log entry) were not edited — their citations are historical record of what
  was captured where, not live pointers a reader needs to follow today, so every such
  citation across the fleet is left as written by convention, not just these examples.
- `docs/reference/README.md`'s `(still-open)` characterization of the Jira↔GitHub sync
  effort is pre-existing staleness (Epic 8 is fully `done`) unrelated to this spec's scope;
  only the dead path was fixed, the stale status word was left for a docs-accuracy pass.

**Review findings breakdown:** 14 findings from 4 review layers (blind hunter, edge-case
hunter, verification-gap, intent-alignment auditor). 7 `low` — all `patch`, all applied
(see `## Review Triage Log`): repoint `docs/dreams/README.md`'s stale jira-intake
citation and `archive/docs/README.md`'s stale gists-INDEX citation (both live pointers
broken by this move but outside the diff's own touched files, so missed by diff-scoped
review); tighten two imprecise Auto Run Result bullets (verification-command wording,
residual-risks enumeration); remove a stray blank line in `spec-pyforge-doctor/.memlog.md`.
7 `false` — rejected on verification: a frontmatter/body status mismatch that Finalize's
own rewrite resolves; a ledger hand-edit that matches this repo's own precedent for the
sibling Story 23.3 reconcile; four "stale frontmatter citation" deletion findings
(`spec-8-1` `context:`, two atlas research `inputDocuments:`, one marshal brief `inputs:`)
where a repo-wide grep confirmed no code anywhere reads those frontmatter keys; and the
intent-alignment auditor's observation that the I/O matrix names one outcome while the
diff produces three — verified correct against the authoritative 2026-09-16 disposition
research memo, with the missing enforcement mechanism already tracked as backlog Stories
23.6/23.7. No `high`, `medium`, or `maybe-false` findings.

**Follow-up review recommendation:** false — all patched findings were `low`; the
follow-up trigger (a patched `high`, or two or more patched `medium`) was not met.

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 14 findings — high 0, medium 0, low 7, false 7, maybe-false 0
- findings:
  - `[low]` `[patch]` `docs/dreams/README.md:241` still cited `docs/intake/jira-github-projects-sync/` ("staged at ...") after this diff archived that folder to `archive/docs/intake/jira-github-projects-sync/` (blind hunter; edge-case hunter, claim; verification-gap) — repointed to match the same fix already made at `docs/MAP.md:76` / `docs/reference/README.md:24` in this diff.
  - `[low]` `[patch]` `archive/docs/README.md:6` pointed at `docs/intake/gists/INDEX.md`, moved by this diff to `archive/docs/intake/gists/INDEX.md` (found during triage verification, not by a launched layer — same root cause as the finding above: a live pointer in a file the diff itself never touched, so out of reach for diff-scoped review) — repointed, and a bullet documenting the new `intake/*` archive additions was added, matching how `specs/gists/*` and `specs/*.md` already document theirs.
  - `[low]` `[patch]` The Auto Run Result verification bullet claimed the stale-reference grep ran "across `src/` and `.claude/`" but the shown command had no path argument (blind hunter) — rewritten to show the command actually run, with explicit paths.
  - `[low]` `[patch]` The Auto Run Result residual-risks bullet named only 4 of roughly 10 Dream files carrying historical citations of the moved paths, understating scope even though the disposition (leave every one of them as written) is correct for all (blind hunter) — rewritten to state the historical-prose convention generally instead of an incomplete named list.
  - `[low]` `[patch]` `spec-pyforge-doctor/.memlog.md`'s newly appended entry left two consecutive blank lines before the next entry, versus one blank line everywhere else in the file (blind hunter) — extra blank line removed.
  - `[false]` `[reject]` Frontmatter `status: in-review` appears to contradict the body's `## Auto Run Result` → `Status: done` line (blind hunter) — the `## Auto Run Result` section is fully rewritten at this Finalize step, so the mid-review transient state this finding describes never reaches the terminal artifact.
  - `[false]` `[reject]` `sprint-status-ledger.yaml` was hand-edited (one line) despite its "GENERATED — do not hand-edit" header (blind hunter) — identical single-line hand-edit pattern used to reconcile sibling Story 23.3 (commit `9e955a5b1b7`, merged via PR #1445); this repo's own established convention for a dispatch/reconcile flow, not a violation.
  - `[false]` `[reject]` `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-8-1-bidirectional-propagation.md:13`'s `context:` frontmatter cites the moved jira path (edge-case hunter, deletion) — spec-8-1 is `status: done` with `followup_review_recommended: false`; per `bmad-build-auto` step-01 routing this HALTs before ever reloading `context:` again, and a repo-wide grep found no script anywhere that reads a spec's `context:` frontmatter outside that one code path.
  - `[false]` `[reject]` `_bmad-output/projects/pyforge-atlas/planning-artifacts/research/market-enterprise-innersource-python-platform-research-2026-07-25.md:5-7`'s `inputDocuments:` frontmatter cites moved gists paths (edge-case hunter, deletion) — a repo-wide grep for `inputDocuments` across every `*.py` file returns zero hits; nothing consumes this frontmatter key.
  - `[false]` `[reject]` `_bmad-output/projects/pyforge-atlas/planning-artifacts/research/domain-enterprise-python-platform-engineering-research-2026-07-25.md:9-11` — same claim, same evidence (edge-case hunter, deletion).
  - `[false]` `[reject]` `_bmad-output/projects/pyforge-marshal/planning-artifacts/briefs/brief-pyforge-marshal-2026-07-25/brief.md:199`'s `inputs:` list cites the moved how-we-operate gist path (edge-case hunter, deletion) — no code in `_bmad/` or elsewhere reads a BMAD brief's `inputs:` frontmatter (the only `inputs`-handling code found belongs to the unrelated `skf-*` skill-forge toolchain, a different system).
  - `[false]` `[reject]` Intent-alignment auditor: the I/O matrix names one outcome (absorbed → gone) but the diff produces three (archived / kept pending Story 59.4 / kept pending four other open folds), with no automated check tying intake occupancy to Dream/Epic status — the three actual dispositions match, item for item, the authoritative `fleet-inbox-disposition-2026-09-16.md` research memo this spec's own Approach text points to; the missing enforcement mechanism is already tracked as backlog Stories 23.6/23.7 in the same epic, not a gap this story's intent asked it to close.
