---
title: "67.4: Upstream to-dos are tracked in the repo, and only the operator files, tracks or retires them"
type: 'feature'
created: '2026-09-25'
status: 'ready-for-dev'
flag-exempt: detector-or-gate   # the only behaviour is a repo-scope check; a gated check would read a silent green
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-67-3-every-gap-and-every-fat-only-pin-has-a-disposition-and-an-owner.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-85-8-an-agent-session-never-writes-outside-this-repository.md
  - docs/foundry/sbom-gaps.md
  - scripts/sbom_gap_derive.py
  - tests/scripts/test_sbom_gap_derive.py
  - scripts/detectors.py
  - docs/dreams/pyforge-steward.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the estate finds defects it cannot fix itself, and has nowhere to keep them. The fix belongs upstream, in
a feedstock, a tool or a staged-recipes PR. Each finding lives in one place only: a row of `docs/foundry/sbom-gaps.md`,
a CFE gotcha, or a story's deferred row. Nothing says who files it, whether anyone did, or what happened next.

- **The story as minted could not run.** On 2026-09-25 Story 67.4 was minted to open one upstream issue per `upstream`
  row of `docs/foundry/sbom-gaps.md` and was held `blocked` as outward work. Story 85.8 (2026-10-09) made outward
  writes the operator's alone: the session hook's `outward-github-write` and `outward-git-push` denials refuse an
  agent's `gh issue create|comment|close` and `gh pr …` writes on another repository, and its `gh api` writes there.
- **The ruling.** On 2026-10-10 the operator ruled in chat: "lets record it here - that there are issues we need to
  open and resolve upstream - and maintain a list of upstream to-do's but leave it to the operator to decide to file,
  decide to track (once and issue has been opened), and decide to retire - but make the story self contained to this
  repo". The operator chose three options: "Registry + drafts", "SBOM rows + session finds", and "Re-scope 67.4,
  unblock it". The ruling flipped this story's ledger key `blocked` → `backlog`.
- **What exists on `6d5e84cb6b`:**
  - `docs/foundry/sbom-gaps.md` (Story 67.3) lists 181 rows. Three are `upstream`: `feature:conda-smithy` (`:11`),
    `feature:crm` (`:12`) and `feature:python-agent-platform` (`:23`).
  - `scripts/sbom_gap_derive.py` parses the file (`parse_gaps_document`, `ROW_RE` at `:35`) and backs the
    `sbom-gaps-check` task (`pixi.toml`, `[feature.guild-tasks.tasks.sbom-gaps-check]`). That task is not a detector,
    since its name does not match `scripts/*_check.py`, and no lane runs the task by name. Its check still gates every
    PR: `tests/scripts/test_sbom_gap_derive.py::test_live_document_matches_derivation` calls the same
    `check_gaps_document()` in the Detectors workflow's `scripts-suite` job and in `pr-preflight`'s
    `pyforge-doctor-scripts-test` leg.
  - `scripts/detectors.py` discovers a `scripts/*_check.py` that declares `DETECTOR = {"scope": "repo"}` and has a pixi
    task naming it, and `detectors-ci` runs it.
  - No registry of upstream to-dos exists.

**Approach:** a registry, its drafts, one repo-scope check and a how-to. The story files nothing.

- **The registry.** `docs/foundry/upstream-todos.yaml` holds `schema_version: 1` and a list `items`. Each item has:

  | Field | Type | Rule |
  |---|---|---|
  | `id` | kebab-case string | unique; the draft file is `docs/foundry/upstream-drafts/<id>.md` |
  | `title` | string | one line |
  | `source` | string | `sbom-gaps:<row id>` (for example `sbom-gaps:feature:crm`) or `finding:<where>` (for example `finding:cfe-G121`) |
  | `evidence` | list of strings | repo paths with line numbers, story keys, or URLs read live; at least one |
  | `target` | mapping | `tracker` (`github`), `repo` (`owner/name`), `kind` (`issue`, `pr-close`, `comment`), `verified` (date of the read-only check that the repo exists and accepts issues, or `null`) |
  | `state` | string | one of `proposed`, `drafted`, `filed`, `tracking`, `resolved`, `retired` |
  | `draft` | string or `null` | the draft path; required from `drafted` on |
  | `issue_url` | string or `null` | `https://…`; required for `filed` and `tracking` |
  | `observed` | mapping or `null` | `{at: <date>, state: open|closed|merged, via: <the read-only command>}`; only while `tracking` |
  | `decided_by` | `agent` or `operator` | who set the current state |
  | `date` | `YYYY-MM-DD` | when the current state was set |
  | `reason` | string | required for `retired` |
  | `local_follow_up` | string | required for `resolved`: `done: <evidence>` or a story key |
  | `history` | list | prior `{state, decided_by, date, note}`, append-only |

- **The lifecycle.** An agent sets `proposed` (an item found, with evidence) and `drafted` (its issue text written
  in-repo). Only the operator sets `filed` (URL recorded), `tracking` (an issue is open and followed), `resolved` (fixed
  upstream, with the local follow-up done or storied) and `retired` (reason recorded). An agent writes an
  operator-only state only when the operator says so in chat, for example "mark crm-click-cap filed at <url>", and
  records it as `decided_by: operator` with that date. While an item is `tracking`, an agent may refresh `observed`
  with a read-only GET (`gh issue view <url> --json state`, `gh pr view`, or a `gh api` GET), all of which Story 85.8
  leaves open. The previous state moves into `history`.
- **The drafts.** Each `docs/foundry/upstream-drafts/<id>.md` is paste-ready. It has these sections: `## Title` (one
  line), `## Body` (what is wrong, for the upstream reader), `## Reproduce or evidence` (commands, versions, the
  failing output), `## Local workaround` (what this repo does meanwhile, with paths), and `## What resolution unblocks
  here` (the row, story or environment that moves). A `pr-close` draft's body is the closing comment.
- **The check.** `scripts/upstream_todos_check.py`, task `upstream-todos-check` in `guild-tasks`, declares `DETECTOR =
  {"scope": "repo"}`, so `detectors-ci` runs it. It reads `docs/foundry/sbom-gaps.md` through
  `sbom_gap_derive.parse_gaps_document`, the one parser, and never through a second regex. Exit codes follow
  `docs/reference/judgement-vocabulary.md`: 0 clean, 1 findings, 2 could not run. Findings, one line each and naming
  the item:
  - an operator-only state without `decided_by: operator` or without a `date`;
  - `filed` or `tracking` without an `https://` `issue_url`;
  - `retired` without `reason`, or `resolved` without `local_follow_up`;
  - `observed` set outside `tracking`;
  - a `drafted` (or later) entry whose draft file is missing or lacks one of the five sections;
  - an `upstream` row of `sbom-gaps.md` with no entry whose `source` names it. The finding prints a `proposed` stub
    to paste, so a new `upstream` row joins the list in the change that adds it;
  - an entry with an `sbom-gaps:` source whose row is gone or no longer `upstream`, unless it is `resolved` or
    `retired`;
  - a duplicate `id`, an unknown `state`, `decided_by` or `target.kind`, or a missing required field.
- **The seeds.** Six entries, each `drafted`, `decided_by: agent`, dated at dispatch, with its draft. The dispatch
  re-reads every evidence path, and checks each target with a read-only GET (the repo exists and has issues enabled;
  any open issue that already covers the item is named in the draft and in `evidence`).

  | id | source | evidence (read on `6d5e84cb6b`) | proposed target |
  |---|---|---|---|
  | `sbom-conda-smithy-co-solve` | `sbom-gaps:feature:conda-smithy` | `sbom-gaps.md:11`; `pixi.toml` `[feature.conda-smithy.dependencies]` (`:121`, the CalVer 2026.x line needs the `conda` package); the SBOM comment at `:1114`-`:1119` (conda-smithy caps py-rattler `<0.26` and conda `<26.3`); warden's py-rattler note at `:2642` | `conda-forge/conda-smithy-feedstock` (or `conda-forge/conda-smithy`, whichever owns the cap) |
  | `sbom-crm-click-cap` | `sbom-gaps:feature:crm` | `sbom-gaps.md:12`; `pixi.toml:99`-`:106` (the exact `click==8.2.1` pin, `conda-forge/conda-recipe-manager-feedstock#44`); `:1114`-`:1119` (crm 0.8+ caps click `<=8.4.1` while mcp's httpx2 needs click `>=8.4.2`; feedrattler needs a conda-smithy capping py-rattler/conda) | `conda-forge/conda-recipe-manager-feedstock` (#44 may already cover it; if so the draft says so and the operator may take it straight to `tracking`) |
  | `sbom-python-agent-platform-co-solve` | `sbom-gaps:feature:python-agent-platform` | `sbom-gaps.md:23`; `docs/dreams/pyforge-unifying-strategy.md:806`-`:808` (langflow vs pandas / onnxruntime keeps the platform in its own environment); mason Story 13.1 (`langflow-base`'s onnxruntime pin, `done`) | `conda-forge/langflow-feedstock` (the dispatch re-solves to name the pin that still blocks) |
  | `staged-recipes-lfx-bundles-superseded` | `finding:mason-25.15` | mason Story 25.15's deferred row (`spec-25-15-five-duplicate-langflow-suite-directories-retire-into-recipes-langflow.md`, AC 9; minted on branch `chain-mason-retire-dups-2026-10-09`); `archive/docs/specs/langflow-conda-forge.md:155`-`:156` (#33977 `lfx-arxiv`, #33978 `lfx-docling`) | `conda-forge/staged-recipes`, kind `pr-close`: the operator closes their own PRs #33977 and #33978, since `langflow-feedstock` publishes both bundles |
  | `crm-sentinel-type-key-leak` | `finding:cfe-G121` | `.claude/skills/conda-forge-expert/SKILL.md` G121 (`:4384`); `CHANGELOG.md` v8.98.0; mason Stories 22.1 and 22.3 (12 `recipe.yaml` files carried `<conda_recipe_manager.types.SentinelType object at 0x…>` keys; crm 0.10.6 exits 100) | `conda/conda-recipe-manager` |
  | `crm-parse-crash-on-valid-indentation` | `finding:cfe-G93-addendum` | CFE `SKILL.md` G93 and its v8.99.1 addendum (`:3871`-`:3881`); `CHANGELOG.md` v8.99.1 (`recipes/mem0ai/recipe.yaml`: a comment deeper than its keys, crm 0.10.6 `IndexError` in `_construct_parse_tree`, surfaced as conda-smithy lint's ParsingException); mason Story 25.2 | `conda/conda-recipe-manager` (the parser; conda-smithy only surfaces it) |

- **The how-to.** `docs/how-to/track-upstream-todos.md`, a steward-owned how-to page. It tells the operator how to
  read the registry and file an item (paste the draft, then tell an agent "mark <id> filed at <url>"). It also covers
  tracking (and what an agent may refresh), resolving (naming the local follow-up), retiring (giving a reason), and
  what to do when the check names an uncovered `upstream` row. Add a row to `docs/map.yaml` (quadrant how-to, owner
  steward, kind authored) and regenerate `docs/MAP.md` with `docs-map-render`.

Ledger key: `67-4-upstream-tickets-for-the-gaps-that-need-one` (the mint slug; the title changed on 2026-10-10).
Type / Effort / Deps: feature / M / S-67.3 (done).

### Living CAP citations

- **Parent:** `spec-python-foundry-cutover` fnd:CAP-13, "The SBOM is checkable". Its success reads "A tracked
  `docs/foundry/` gap list … gives every residual solve gap … a disposition — promote, won't-do or upstream — with an
  owner. Upstream filing is outward and operator-flipped". This registry is that filing record, with every outward step
  the operator's. fnd:CAP-13 is also the CAP that owns `sbom-gaps.md`: Story 67.3 binds it, and `spec-pyforge-steward`
  only governs the files.
- **Guard, cited not extended:** `spec-pyforge-steward` CAP-5's closed `session_denials` list (Story 63.3). Story 85.8
  added `outward-git-push`, `outward-github-write`, `outward-package-submission` and `outward-mcp-submission`. This story
  adds no denial and no roster entry.
- **No new CAP.** The three non-SBOM seeds have the shape of an `upstream` row: a fix outside the estate that needs an
  owner outside it, which has been this story's "So that" since 2026-09-25. A second CAP would split one list across two
  contracts (spec memlog, 2026-10-10).
- **Flag.** Exempt as `detector-or-gate`. The registry and drafts are data and prose; the only behaviour is a check, and
  a gated check reads a silent green (fidelity-enforcement).

## Acceptance Criteria

- **(1) Schema.** Given the landed `docs/foundry/upstream-todos.yaml` When `pixi run -e pyforge-guild
  upstream-todos-check` runs Then it exits 0. Given a fixture registry with each of these defects When the check runs on
  it Then it exits 1 with one line naming the item and the rule:
  - a duplicate `id`;
  - an unknown `state`, `decided_by` or `target.kind`;
  - a missing `source`, `evidence`, `target`, `state`, `decided_by` or `date`;
  - `observed` on a `drafted` entry.
- **(2) Operator-only states.** Given fixtures with `filed`, `tracking`, `resolved` and `retired` entries When one carries
  `decided_by: agent`, or no `date`, Then the check exits 1 naming it. It also exits 1 when `filed` or `tracking` lacks
  an `https://` `issue_url`, `retired` lacks `reason`, or `resolved` lacks `local_follow_up`. The same entries with
  `decided_by: operator`, a date and their required field pass.
- **(3) Coverage of `sbom-gaps.md`.**
  - Given a fixture `sbom-gaps.md` whose fourth `upstream` row has no entry When the check runs Then it exits 1 naming
    the row and prints a `proposed` stub whose `source` is `sbom-gaps:<row id>`. Pasting the stub makes it exit 0.
  - Given an open entry whose source row is now `promote`, or gone, Then it exits 1. The same entry `retired` with a
    reason passes.
  - The check reads `sbom-gaps.md` only through `sbom_gap_derive.parse_gaps_document`. A test fails if the module
    defines its own row regex.
- **(4) Drafts.** Given a `drafted` entry whose draft file is missing, or lacks one of `## Title`, `## Body`, `##
  Reproduce or evidence`, `## Local workaround` and `## What resolution unblocks here`, When the check runs Then it
  exits 1 naming the file and the missing section.
- **(5) The seeds.** Given the landed registry Then it holds the six entries in the table above, each `drafted`,
  `decided_by: agent`, with at least one evidence path that exists in the tree (or a URL), a `target.repo`, and a draft
  passing (4). The two conda-recipe-manager entries name the crm version they were seen on (0.10.6). The `pr-close`
  draft names #33977 and #33978 and why they are superseded. Each target's `verified` date records the read-only check
  made at dispatch.
- **(6) Could not run.** Given an unreadable or non-YAML registry, a missing `sbom-gaps.md`, or `yaml` not importable,
  When the check runs Then it exits 2 naming the cause: unknown, never green.
- **(7) Nothing leaves the repository.**
  - The check makes no network call: a test runs it with `socket.socket`, `subprocess.run`, `subprocess.Popen` and
    `urllib.request.urlopen` patched to raise, and it still exits 0 on the landed registry. An `ast` test asserts the
    module imports none of `subprocess`, `urllib`, `http`, `socket` or `requests`.
  - The story's run makes no `gh` write and no `git push` outside this repository, and opens, comments on or closes
    nothing upstream. The target checks are GETs only.
- **(8) Registered and documented.**
  - `python scripts/detectors.py --list` shows `upstream_todos_check` as `repo` scope with task
    `upstream-todos-check`.
  - `docs/reference/detectors.md` and `docs/how-to/pixi-tasks.md` are regenerated (`docs-detectors`,
    `docs-pixi-tasks`).
  - `docs/how-to/track-upstream-todos.md` exists with its `docs/map.yaml` row, and `docs/MAP.md` is regenerated.
  - `docs-map-hygiene-check`, `governance-currency` and `flag-gate-check --spec <this spec>` exit 0.
- **(9) Mutations fail the tests.** The tests for (2), (3) and (4) fail when the check stops enforcing the rule they
  test: return no finding for an operator-only state, skip the coverage loop, or skip the section check.

## Boundaries & Constraints

**Always:**
- Change only the Surface named in `epics.md` for this story. Use PyYAML (`pyforge-guild` carries it). The test file
  guards with `pytest.importorskip("yaml")`, as the `tests/scripts/test_docs_*` files do.
- Keep `scripts/sbom_gap_derive.py` and `docs/foundry/sbom-gaps.md` byte-identical. This story reads them and never
  edits them.
- Write evidence as paths with line numbers read at dispatch. Where a line moved since `6d5e84cb6b`, cite the new line.
- Reconcile co-governors before landing. Add the check and its test to `spec-pyforge-steward`'s `surface:` (a memlog
  decision, then the Spec's re-derive, as Story 67.3 did). Append a memlog entry on every Spec `spec-surface-check`
  names. Then `git add` and run one `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` per
  named Spec, re-run the check and read its exit code. Never a bare stamp.

**Never:**
- Never file, comment on, close or edit an issue or PR outside `rxm7706/local-recipes`, and never push outside it.
  Outward work is the operator's (AGENTS.md § Policy; Story 85.8).
- Never set `filed`, `tracking`, `resolved` or `retired` on a seed. Those are the operator's.
- Never add a `session_denials` entry or touch `.claude/hooks/pre-shell.py`.
- Never make `sbom-gaps-check` a detector or change its task in this story. Its gap is named below.
- Never hand-edit `SPEC.md` or `sprint-status-ledger.yaml`.
- Never flip any Epic 44 `blocked` key or `pyforge.cutover_root`, and never edit `rxm7706/python-foundry`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| landed registry | six `drafted` seeds, three `upstream` rows covered | exit 0 | — |
| operator says "mark sbom-crm-click-cap filed at <url>" | agent edits the entry | `state: filed`, `decided_by: operator`, `date`, `issue_url`; old state in `history`; exit 0 | — |
| agent sets `filed` on its own | `decided_by: agent` | exit 1 naming the entry | fail loud |
| new `upstream` row in `sbom-gaps.md` | no entry | exit 1, `proposed` stub printed | paste the stub |
| source row turned `promote` | entry still `drafted` | exit 1 | retire with a reason, or re-point the source |
| `tracking` entry, upstream closed | agent refreshes by GET | `observed: {state: closed, …}`; state unchanged until the operator resolves it | — |
| draft missing a section | `drafted` entry | exit 1 naming file and section | fail loud |
| registry not YAML | parse error | exit 2 | unknown, never green |

</intent-contract>

## Binding

- Parent Spec capability: `spec-python-foundry-cutover` fnd:CAP-13; cites `spec-pyforge-steward` CAP-5 (Story 85.8's
  outward denials).
- Dreams: `docs/dreams/pyforge-unifying-strategy.md` § *Where next* → *Consolidation — 2026-09-25* (the mint);
  `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-10 (upstream to-dos) entry (the re-scope).
- Ledger key: `67-4-upstream-tickets-for-the-gaps-that-need-one`.
- Ledger status: minted `blocked` 2026-09-25. Flipped `blocked` → `backlog` 2026-10-10 by the operator's ruling,
  through the Tier-3 feed and `sprint-ledger-sync --project steward --allow-regression`; the memlogs of both Specs
  record it.
- Spec: `spec-pyforge-steward/.memlog.md` and `spec-python-foundry-cutover/.memlog.md` record the ruling, the binding
  and the re-scope. No `SPEC.md` text changed, and no CAP was minted. The cutover Spec's Constraints sentence naming
  "CAP-13's upstream filing (Story 67.4)" among the outward items is corrected at its next `bmad-spec` pass, per that
  memlog.
- Surface: `docs/foundry/**`, `pixi.toml`, `environment.yaml` and the specs are already in Epic 67's `[epic_surfaces]`.
  The check, its test, the regenerated docs pages, the how-to, `docs/map.yaml` and `docs/MAP.md` are added to it with
  this re-scope.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- `pixi run -e pyforge-guild upstream-todos-check` — expected: exit 0 on the landed registry.
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_upstream_todos_check.py -q` — expected: pass.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`, with `upstream_todos_check`
  among the scanned detectors.
- `pixi run -e pyforge-guild python scripts/flag_gate_check.py --spec
  _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-67-4-upstream-tickets-for-the-gaps-that-need-one.md`
  — expected: `pass`.

## Named, not fixed here

- `sbom-gaps-check` is not a registered detector: `scripts/detectors.py` does not discover it because its script is
  not named `*_check.py`, and no lane runs the task by name. The list is still gated. A `pixi.toml` change that adds a
  feature outside the SBOM, or a fat-only pin, reds `test_live_document_matches_derivation` in the Detectors
  `scripts-suite` job (every `pull_request`, no path filter) and in `pr-preflight`'s `pyforge-doctor-scripts-test`
  leg. PR #2008 went red that way on 2026-10-09 (`ca1c50d447` added the missing row). This story's check covers only
  the rows the file already has. A fix story was approved on 2026-10-10 on the premise that the list was ungated; the
  premise was disproved the same day and the story is not minted (spec-python-foundry-cutover memlog).

## Spec Change Log

- 2026-09-25: minted `blocked` as outward work (open one upstream issue per `upstream` row).
- 2026-10-10: re-scoped repo-only by the operator's ruling: type `chore` → `feature` (`flag-exempt:
  detector-or-gate`), effort S → M, title changed, Outward line removed; the ledger key moved `blocked` → `backlog`.
- 2026-10-10 (later): corrected the claim that `sbom-gaps-check` gates nothing. Its check runs on every PR through
  `test_live_document_matches_derivation`; no AC, status or ledger key changed.

## Review Triage Log

- No review has run yet.
