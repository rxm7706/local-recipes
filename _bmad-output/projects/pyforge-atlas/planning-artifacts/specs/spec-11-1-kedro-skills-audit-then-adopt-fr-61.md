---
title: 'kedro-skills audit-then-adopt'
type: 'feature'
created: '2026-08-09'
status: done
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: 'c09088a6e6e3ae6ab8d9923dcb7df61a18052fa0'
final_revision: 'f0bb93fc0ea7a31da8e4834b0017a7d47a4200a0'
---

<intent-contract>

## Intent

**Problem:** Atlas never evaluated `kedro-org/kedro-skills` (v0.1.1, released the day the Dream was
captured, 1 star, "Distribute AI coding skills to Kedro projects"). Its one shipped skill,
`catalog-config`, targets `conf/**/*.yml` — exactly the files `tests/catalog/*` binds with 38
enforced conventions — so uncritical install risks silently contradicting Atlas's own AD-invariants.

**Approach:** Pin `kedro-skills==0.1.1` via pixi (dev/tooling-only, never a pyproject.toml runtime
dep), run the real CLI against the real `pyforge-atlas` Kedro project, and audit every subsection
of the generated `catalog-config` guidance against `tests/catalog/*`. Land the tool's real output
in `.claude/skills/` reproducibly; where a subsection contradicts an enforced convention, append a
correction at the bottom of the installed file (never edit inline) and record the contradiction in
a durable audit report. Investigation already found the guidance substantially passes, with two
confirmed contradictions (see Design Notes) — the implementing step must re-verify these against
the live tree, not trust this spec blindly.

## Boundaries & Constraints

**Always:** Pin the exact evaluated `kedro-skills` version (no floor). Run the real CLI against the
real project — never hand-simulate installer output. Give every `catalog-config` SKILL.md
subsection an explicit, evidenced PASS or CONTRADICTS-`<test-name>` verdict with file:line evidence.
Record contradictions rather than silently dropping or silently keeping them.

**Block If:** `kedro-skills==0.1.1` is no longer installable from PyPI (yanked/removed) —
substituting a newer version audits a different artifact than the one this story names; HALT rather
than silently widening the pin.

**Never:** Install IDE surfaces beyond Claude Code (`--ide claude` only — cursor/copilot/codex are
unrequested scope). File a live GitHub issue or take any other externally-visible action against
`kedro-org/kedro-skills` — draft issue-ready text in the audit report and stop there; filing needs a
human's explicit go-ahead, not an unattended loop. Touch `pyproject.toml` runtime dependencies —
this is dev-tooling, mirrors the existing `playwright`/`playwright-python` TEST-ONLY precedent.
Re-open `kedro-mcp`, or evaluate `kedro-builder`/`vscode-kedro` — separate, out-of-scope stories.

</intent-contract>

## Code Map

- `pixi.toml` (`[feature.pyforge-atlas]`) -- add the pinned pypi-dependency + tasks to run the CLI; pattern precedent at line ~1465 (`pypi-dependencies`) and ~1496 (`tasks.viz`, the existing `cwd`-scoped kedro CLI task).
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` -- ground truth for the audit (header comment + every entry's `metadata.layer` / `credentials:` / `${globals:...}` usage).
- `src/shared/packages/pyforge-atlas/tests/catalog/test_conventions.py`, `test_credential_scoping.py`, `conftest.py` -- the enforced AD-invariants the guidance is audited against.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-kedro-org-tooling-adoption/SPEC.md` -- the epic-level contract this story fulfills (Capability 1); its upstream-contribution open question is closed by this story's audit report.
- `docs/reference/library-llms-full.md` -- repo-wide dependency catalog; add a `kedro-skills` entry (CLAUDE.md-required, has its own `llms-full-check` drift gate).
- `environment.yaml` -- regenerate via `pixi project export conda-environment -e build > environment.yaml` (CLAUDE.md ALWAYS-ON, ungated PR gate whenever `pixi.toml` changes).

## Tasks & Acceptance

**Execution:**
- [x] `pixi.toml` -- add `kedro-skills = "==0.1.1"` under `[feature.pyforge-atlas.pypi-dependencies]`, a `kedro-skills-audit` task (`cwd = "src/shared/packages/pyforge-atlas"`, `cmd = "kedro skills list"`), AND a second `kedro-skills-install` task (same `cwd`, `cmd = "kedro skills install catalog-config --ide claude"`) -- reproducible, exactly-pinned provisioning; no `bmad-module-provisioning` mechanism exists yet (still `draft` in pyforge-steward), so this is written as an adoptable precedent per the epic SPEC's constraint, not a one-off driver script. **Both** the list and the install commands need a discoverable task — a prior pass left the install command as prose-only, which is itself the "undiscoverable one-off command" pattern the epic SPEC forbids.
- [x] Run `pixi run kedro-skills-audit`; confirm the registry still contains exactly one skill (`catalog-config`) -- re-verifies ground truth against the live package, not a cached read.
- [x] `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-kedro-org-tooling-adoption/kedro-skills-audit-report.md` -- new file: every guidance subsection gets a PASS/CONTRADICTS verdict with evidence. Prior investigation found: CONTRADICTS on "use `metadata.kedro-viz.layer`" (enforced convention is unnested `metadata.layer`, `tests/catalog/test_conventions.py:30-36`) and on the numbered `data/01_raw/...` 8-layer directory table (enforced convention is `data/<layer>/<name>/` with `LAYERS={raw,intermediate,primary,derived}`, `tests/catalog/conftest.py:58-59` + `test_conventions.py:39-58`); PASS on dataset-type naming, the doc-verification workflow, extras naming, factory-pattern specificity, and credentials-by-key-in-`conf/local/`-gitignored (this last one matches `test_credential_scoping.py` almost verbatim). **When citing the total check count of the `kedro-catalog-check` gate, get it from a live `pixi run kedro-catalog-check` run (report the number pytest actually prints) — do not copy the "38" figure from the epic context / parent SPEC, which is stale (the gate currently collects 47 tests).**
- [x] Run `pixi run kedro-skills-install` from the atlas project root -- writes the real tool-managed files: `.agents/skills/catalog-config/SKILL.md` (canonical), `.agents/skills/.installed.json` (state/checksums), `AGENTS.md` (new nested file — the `agents_md` renderer runs unconditionally regardless of `--ide`, this cannot be suppressed), `.claude/skills/catalog-config/SKILL.md` (the file Claude Code's native skill loader reads).
- [x] Append the SAME "## Atlas overrides" section (repo convention: AI/tooling corrections go at the bottom, never inline) to **both** `src/shared/packages/pyforge-atlas/.claude/skills/catalog-config/SKILL.md` **and** `src/shared/packages/pyforge-atlas/.agents/skills/catalog-config/SKILL.md`. This is the fix for the review-loop-1 finding: `AGENTS.md`'s injected block instructs every non-Claude-Code-native reader to "read `.agents/skills/catalog-config/SKILL.md` BEFORE writing... changes" — appending the override only to `.claude/` left that canonical, AGENTS.md-routed copy uncorrected, so Cursor/Copilot/any AGENTS.md-driven agent would apply the two contradicted conventions with no flag. Both appends intentionally register as drift for a future `kedro skills update` (verified empirically in review loop 1: `kedro skills update` without `--force` refuses and names the modified file, the override survives) — the desired re-audit trigger on a version bump, not a bug to work around.
- [x] `docs/reference/library-llms-full.md` -- add a `kedro-skills` entry (version `==0.1.1`, dev/tooling-only, pyforge-atlas feature scope) per its regeneration convention.
- [x] Regenerate `environment.yaml`: `pixi project export conda-environment -e build > environment.yaml`. (Produced no diff — `kedro-skills` is `pyforge-atlas`-feature-scoped, not part of the exported `build` environment — so nothing to commit here, task complete as specified.)
- [x] Run `pixi run -e local-recipes llms-full-check`; confirm no `kedro-skills` finding in its drift output (pre-existing, unrelated drift findings for other packages are not this story's problem).
- [x] Commit `pixi.toml`, `environment.yaml`, the `library-llms-full.md` entry, all four tool-managed files (with the override now in both `.claude/` and `.agents/` copies), and the audit report together.

**Acceptance Criteria:**
- Given `kedro-skills==0.1.1` pinned in `pixi.toml`, when the audit task runs, then it reports the registry's actual current skill set, confirming it did not silently grow beyond `catalog-config`.
- Given the `catalog-config` guidance and `tests/catalog/*`, when each subsection is audited, then every subsection carries a recorded PASS or CONTRADICTS verdict with file:line evidence, including a check-count citation taken from a live gate run — none left unaudited or stated from stale memory.
- Given at least one subsection passes, when the skill is installed, then a discoverable pixi task actually executes `kedro skills install` (not hand-simulated, not prose-only) and its real output is committed.
- Given a CONTRADICTS verdict exists, when installation finalizes, then **both** the installed `.claude/skills/catalog-config/SKILL.md` **and** `.agents/skills/catalog-config/SKILL.md` carry the bottom-appended override — no contradicting guidance is left unflagged in ANY file an agent (Claude-native or AGENTS.md-routed) will actually read.
- Given the audit instead finds nothing installable (a "not yet" outcome), when the story concludes, then no files are installed, `pixi.toml` is unchanged, and the audit report states the verdict and reasons — this closes the story validly.
- Given the upstream-contribution question, when the story concludes, then the audit report drafts issue-ready text for any confirmed-wrong guidance but no live GitHub issue is filed.
- Given `pixi.toml` gained a new dependency, when the story concludes, then `docs/reference/library-llms-full.md` documents it and `environment.yaml` is regenerated — `llms-full-check` reports no `kedro-skills`-related drift.

## Design Notes

**Why append-at-bottom, not exclude-at-install.** `kedro-skills` installs/updates whole skill files,
not sub-sections — there is no flag to omit one paragraph. Hand-editing the installed file is the
only way to record a correction, and the tool already treats a hand-edited managed file as
detectable drift (`orchestrator.check_drift_for_skill`, SHA-256 per file). Appending at the bottom
(rather than editing the contradicting text inline) both matches the existing repo convention (CFE
comments) and turns the tool's own drift-refusal on `kedro skills update` into exactly the "a
version bump re-triggers the audit, not a silent regenerate" behavior the epic SPEC requires — no
extra machinery needed. Review loop 1 verified this empirically: after appending the override,
`kedro skills update` (no `--force`) refuses and names the modified file; the override is not
silently clobbered.

**Why the override must land in BOTH `.claude/` and `.agents/` copies.** `kedro skills install`
writes the canonical copy to `.agents/skills/<id>/SKILL.md` unconditionally (`write_canonical`,
independent of `--ide`), and the also-unconditional `AGENTS.md` block it injects explicitly tells
every reader to consult that canonical copy before editing matching files. Appending the correction
to only the `--ide claude`-specific copy (`.claude/skills/<id>/SKILL.md`) leaves the canonical,
AGENTS.md-routed copy uncorrected — the exact "silently kept" contradiction outcome the epic SPEC
forbids, just reached through a different file than the one first checked. There is no single-file
fix: both copies must carry the same appended section.

**Why not relocate the output to the repo-root `.claude/skills/`.** `kedro skills install` always
resolves the Kedro project root via `find_kedro_project` and writes relative to it — there is no
`--target-dir`. Rather than add a bespoke relocation step (which the epic SPEC's "no second one-off
installer" constraint discourages), this spec accepts the tool's native, directory-scoped output at
`src/shared/packages/pyforge-atlas/.claude/skills/catalog-config/`, which Claude Code's own
directory-scoped skill resolution is designed to surface when work touches that subtree.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- `git status` inside `src/shared/packages/pyforge-atlas/` shows exactly the four tool-managed files as new/modified, plus the override append in both `.claude/` and `.agents/` copies — nothing else under `conf/`, `src/pyforge/`, or `pyproject.toml` changed.
- `grep -c "## Atlas overrides" .claude/skills/catalog-config/SKILL.md .agents/skills/catalog-config/SKILL.md` inside `src/shared/packages/pyforge-atlas/` -- both must report `1`.

## Spec Change Log

### 2026-08-09 — Review loop 1 (bad_spec)

**Triggering finding:** `AGENTS.md`'s injected block (written unconditionally by `kedro skills
install` regardless of `--ide`) instructs every reader to consult
`.agents/skills/catalog-config/SKILL.md` — but Task 5 of the prior spec revision only specified
appending the "## Atlas overrides" correction to the `--ide claude`-specific copy
(`.claude/skills/catalog-config/SKILL.md`), leaving the canonical, AGENTS.md-routed copy
uncorrected. Empirically confirmed in the implemented diff: `.agents/skills/catalog-config/SKILL.md`
had zero occurrences of the override text. This defeats AC 4 ("no contradicting guidance is left
unflagged in the file an agent will actually read") for every non-Claude-Code-native consumer.

**What was amended:** Tasks & Acceptance now requires appending the SAME override to both
`.claude/skills/catalog-config/SKILL.md` and `.agents/skills/catalog-config/SKILL.md`. Design Notes
gained a new subsection explaining why both copies need it. Acceptance Criteria and Verification
were updated to check both files explicitly. Bundled into the same amendment (all confirmed real via
live re-checks in this review pass, to avoid a second loopback for already-known issues): (1) added a
`kedro-skills-install` pixi task, since the actual `kedro skills install` invocation existed only as
prose in the audit report — an undiscoverable one-off command, which the epic SPEC's Constraints
explicitly forbid; (2) instructed the audit report to cite the `kedro-catalog-check` gate's check
count from a live run rather than the epic context's stale "38" figure (live count confirmed: 47);
(3) added tasks/AC to update `docs/reference/library-llms-full.md` and regenerate `environment.yaml`
for the new `kedro-skills` pypi-dependency, per CLAUDE.md's ALWAYS-ON PR gates — `llms-full-check`
was run live in this review pass and confirmed `kedro-skills` as an `undocumented-dep` finding.

**Known-bad state avoided:** shipping a story whose own stated purpose ("record contradictions
rather than silently dropping or silently keeping them") is defeated for the majority of
non-Claude-Code AI tooling paths in this repo (Cursor, Copilot, any AGENTS.md-driven agent), while
also landing a CLAUDE.md-gate-violating commit (undocumented dependency, stale `environment.yaml`)
and an unreproducible install step.

**KEEP instructions (must survive re-derivation):** The exact-pinned `kedro-skills = "==0.1.1"`
pypi-dependency and its rationale comment. The `kedro-skills-audit` (`kedro skills list`) pixi task
as originally written. The full subsection-by-subsection audit methodology and every individual
PASS/CONTRADICTS verdict already reached (both confirmed contradictions — nested
`metadata.kedro-viz.layer` vs enforced unnested `metadata.layer`; the numbered 8-layer `data/`
scaffold vs the enforced unnumbered 4-layer scheme — are correct and evidence-backed; only the "38"
check-count citation needs correcting to a live-verified number). The append-at-bottom mechanism and
exact override wording (now duplicated to both files, not rewritten). Running the real CLI rather
than hand-simulating output. The draft-not-filed treatment of the two upstream-issue candidates
(confirmed compliant with the Never clause — no live GitHub issue was filed). The terse,
no-AI-attribution commit message style.

## Review Triage Log

### 2026-08-09 — Review pass 1

- intent_gap: 0
- bad_spec: 1 (high 1, medium 0, low 0)
- patch: 0 (folded directly into the same spec amendment rather than auto-fixed against
  soon-to-be-reverted code — see Spec Change Log; not separately counted this pass since bad_spec
  moots lower-category processing per the cascading rule)
- defer: 1 (low 1)
- reject: 4 (high 0, medium 1, low 3)
- addressed_findings:
  - `[high]` `[bad_spec]` AGENTS.md routes every non-Claude-Code-native reader to the uncorrected
    `.agents/skills/catalog-config/SKILL.md` copy (converged finding, both Blind Hunter and Edge
    Case Hunter) — spec amended to require the override in both managed copies; code reverted to
    baseline for re-derivation.

**Deferred** (`deferred-work.md`): whether `src/shared/packages/pyforge-atlas/.claude/skills/catalog-config/`
(a nested, directory-scoped `.claude/skills/` tree — the first of its kind in this repo) is actually
discoverable by a live Claude Code session working in that subtree, or whether directory-scoped skill
resolution requires verification beyond what this story's tooling constraints allow to test
(Blind Hunter finding; genuinely unconfirmed either way, not fixable within this story since
`kedro skills install` has no `--target-dir` to relocate output).

**Rejected:**
- "`.installed.json` records the pre-append hash, so a future `kedro skills update`/`uninstall`
  could silently overwrite or delete the override" (medium; converged finding, both reviewers) —
  empirically refuted in this review pass: ran `kedro skills update` (no `--force`) after the
  append; it refused ("the following files have been modified... Use --force to overwrite") and the
  override survived on disk untouched. The mechanism works exactly as the spec's Design Notes
  described.
- "No mechanism ties a future `pixi.toml` pin bump to re-running this audit" (low) — the tool's own
  drift-refusal on `kedro skills update` already satisfies the epic SPEC's actual requirement ("a
  version bump re-triggers the audit, not a silent regenerate"); a bespoke pin/report consistency
  check would be new machinery beyond what any AC asks for.
- "Exact pin with no floor/fallback range if 0.1.1 is yanked" (low) — directly contradicts the
  intent-contract's explicit, deliberate "Always: pin the exact evaluated version (no floor)" and
  "Block If: ...HALT rather than silently widening the pin." Not a gap; by design.
- "Drafted upstream issues have no tracked follow-up item for the human filing decision" (low) — AC
  6 only requires drafting issue-ready text and not filing; creating a tracked backlog entry for the
  filing decision is scope beyond what any AC asks for.

### 2026-08-09 — Review pass 2

- intent_gap: 0
- bad_spec: 0
- patch: 3 (medium 1, low 2)
- defer: 1 (low 1; upgrades a review-pass-1 rejection after convergence — see below)
- reject: 11 (high 0, medium 1, low 10)
- addressed_findings:
  - `[medium]` `[patch]` `kedro-skills-install`'s pixi task description claimed "(Claude Code
    surface only)" — misleading, since the unconditional `agents_md` render and the canonical
    `.agents/skills/` copy are written regardless of `--ide`. Rewrote the description to state
    exactly what the command writes and that both `install` and `update` refuse on drift
    (re-verified live in this pass: re-running `kedro skills install`, not just `update`, after the
    override append also refuses and names both modified files — Edge Case Hunter's claim that only
    `update` was tested, and `install` might silently clobber, does not hold).
  - `[low]` `[patch]` The epic-level `spec-kedro-org-tooling-adoption/SPEC.md` still asserted the
    pre-audit "`kedro-catalog-check=38`" figure this story's own audit disproved (live: 47).
    Corrected in place with a pointer to the audit report and the superseded value preserved for
    history, not silently overwritten (Blind Hunter finding).
  - `[low]` `[patch]` (bundled with the above) no separate third finding needed a code change;
    accounted here for count accuracy — see `defer` entry below for the one item actioned outside
    code (a ledger append, not a code patch).

**Deferred** (`deferred-work.md`): the two drafted-but-unfiled upstream issue texts have no tracked
follow-up forcing a human filing decision. Rejected in review pass 1 as "beyond AC scope"; upgraded
to `defer` in this pass after the SAME finding was raised independently by both Blind Hunter and
Edge Case Hunter in BOTH review passes with no new counter-evidence — convergence across two
independent reviewer types on two separate passes outweighs the original scope judgment. Appended a
low-severity ledger entry; no code change (nothing to patch — this is a process-visibility gap, not
a defect).

**Rejected** (11 findings, most re-litigating already-defended design choices or asking for scope
beyond any AC):
- "Excluded" (epic SPEC wording) vs. "appended-after" (what was built) — a real tension, but the
  append-at-bottom mechanism was a deliberate, twice-reasoned design choice (no sub-file exclusion
  exists in the tool; hand-editing inline would break `kedro skills update`'s managed-file
  reproducibility). SKILL.md files are loaded as complete units by Claude Code's skill mechanism
  (not paginated/truncated), and the override explicitly back-references the corrected section by
  name — the "an agent might stop reading before the bottom" risk is real but low for a 237-line,
  whole-file-loaded skill document. Not escalated to a third loopback.
- "Nested `.claude/skills/` may be undiscoverable to root-cwd sessions" (re-raised, same as pass 1)
  — already logged to `deferred-work.md` in pass 1; re-confirmed real and re-affirmed as deferred,
  not re-actioned as a new finding.
- "'Block If' clause is a fabricated/unverifiable citation" — refuted: the clause is real, in this
  story's own `spec_file` intent-contract (`Boundaries & Constraints`), which lives in the gitignored
  Tier-3 `implementation-artifacts/` and is therefore invisible to a diff-scoped reviewer — a search
  gap, not a fabrication.
- "Draft issue 1 states an unverified Kedro-Viz behavior claim as settled fact" — the draft text
  already hedges with "In our project..." framing; adequately scoped for a draft awaiting human
  review before filing.
- "No cross-check that both managed SKILL.md copies stay identical over time" — asks for new
  ongoing-consistency tooling beyond this one-time audit-then-adopt story's scope; a natural addition
  if/when the next version-bump re-audit happens, not now.
- "`kedro-skills-audit` task doesn't hard-assert the registry stayed at one skill" — the AC says the
  task must "report" the registry, not gate on it; the task satisfies the literal requirement.
- "`kedro skills uninstall` lifecycle never exercised" — uninstall was never invoked by any AC; out
  of scope.
- "'47 passed' is a static citation that will go stale like '38' did" — the report already dates
  itself (2026-08-09) and explicitly flags the superseded figure; demanding a live-updating citation
  mechanism is infrastructure scope creep for a one-time, dated audit artifact.
- "Commit message says 'regenerates environment.yaml' but the diff shows no change" — accurate: the
  regeneration command was run and produced a byte-identical (correctly unchanged) file; not
  misleading, just not itself a diff-producing action.
- "Summary table doesn't distinguish dormant-but-uncontradicted from fully-exercised PASSes" — already
  addressed: the table carries "PASS (dormant)" tags for the two dormant sections.
- "No demonstration the vendored portion is byte-reproducible on a clean reinstall" — redundant with
  the exact version pin itself, which is the reproducibility guarantee for an immutable published
  package; re-demonstrating it adds no information.

### 2026-08-09 — Review pass 3 (verification repair)

**Scope note:** this pass reviews only the repair diff below, not the full baseline diff (already
covered by passes 1–2). The bmad-loop deterministic gate (`pixi run --frozen -e pyforge-atlas
kedro-test`) failed post-merge on 2 tests, both outside this story's Code Map (`tests/dashboard/`).
Root-caused before reviewing: (1) `test_dashboard_e2e_navigation_and_rendering` failed
deterministically (3/3 local runs, not flaky) because AG Grid infers a column's `cellDataType` from
row 0 alone — the factory-status page's "status" column has an ISO build-stamp in row 0 and plain
status words in every other row, so auto-inference misread the column as a date and blanked every
non-date-parseable status; reproduced independently on the canonical repo checkout at a newer,
unrelated commit, confirming it predates and is unrelated to this story. (2) `test_factory_status_
reads_the_real_sprint_status` asserted `d1-`/`d2-` sprint-status.yaml keys that PR #322 (2026-08-08,
unrelated) had already renamed to `5-1-`/`5-2-` fleet-wide — confirmed identical between this
worktree and the canonical repo. Neither failure touches the `<intent-contract>` or any kedro-skills
file; fixed by patching the two unrelated files (`dashboard/app.py`, `tests/dashboard/
test_dashboard_dryrun.py`) directly, then running the standard two-reviewer pass on that patch.

- intent_gap: 0
- bad_spec: 0
- patch: 3 (medium 2, low 1)
- defer: 1 (low 1)
- reject: 7 (high 0, medium 0, low 7)
- addressed_findings:
  - `[medium]` `[patch]` (Blind Hunter, converged across 3 related findings) The initial fix pinned
    `cellDataType: "text"` on all four `FRAME_COLUMNS` via an enumerated `columnDefs` list — broader
    than the diagnosed cause (only "status" is ever date-like), coupled `app.py` to `factory_status.
    FRAME_COLUMNS` for no functional benefit, and its correctness silently depended on an unenforced
    "every column is a `str()`" invariant. Replaced with `dash_ag_grid(key, defaultColDef=
    {"cellDataType": "text"})` — `vizro`'s `_set_defaults_nested` deep-merges `Mapping` kwargs, so
    this applies to every column without enumerating them, keeps the library's own sortable/filter
    defaults, and removes the FRAME_COLUMNS coupling entirely (verified: `kedro-test` still 912/912
    non-skipped green).
  - `[medium]` `[patch]` (Blind Hunter) The fix had no fast/offline regression lock — only the ~7s
    Playwright e2e test guarded it, inconsistent with this file's existing offline-first test style.
    Added `test_factory_status_grid_pins_text_celldatatype` (dryrun layer, inspects the AgGrid
    figure's captured `defaultColDef` kwarg directly).
  - `[low]` `[patch]` (Edge Case Hunter) `test_factory_status_reads_the_real_sprint_status`'s new
    assertions hardcoded the current `5-1-`/`5-2-` literal, so a third renumbering (the ledger has
    already been renamed once) would break the gate again the same way. Changed to suffix-matching
    (`k.endswith(...)`) so the test survives any future leading-key-scheme change.

**Deferred** (`deferred-work.md`): the live `sprint-status.yaml`'s `story_meta.depends_on` lists
still reference the retired `d1-`/`d2-` spelling for Epic 5 (3 occurrences) even though PR #322
renamed the matching `development_status` keys to `5-1-`/`5-2-` — inert today (no shipped code reads
`depends_on` from this file) but drift-prone. Out of this repair's scope: `sprint-status.yaml` is a
generated, gitignored artifact outside this story's Code Map, and PR #322's sweep is what missed it,
not this pass.

**Rejected** (7 findings, all either resolved as a side effect of the `defaultColDef` patch above,
speculative hardening beyond the two failing tests, or documentation-only nits):
- "Fixture in `conftest.py::bmad_fixture` still hardcodes `d1-`/`d2-` with no comment marking it
  deliberately format-agnostic synthetic data" — true but harmless (self-consistent with the tests
  that consume it); a one-line comment on an otherwise-untouched shared fixture is churn beyond what
  either failing test needed.
- "AG Grid's row-0 cellDataType inference is asserted in a code comment without a doc citation or
  version pin" — the behavior was verified empirically (live Playwright run, before/after the fix),
  which is stronger evidence than a docs link; `dash_ag_grid`'s pin already lives in `pixi.lock`.
- "The row-0-type-inference hazard is generic; no shared helper captures it for reuse on a future
  page with the same shape" — no second page has this shape today (the other 5 `_data_page` grids
  route through typed Ibis/DuckDB BSL queries with uniform dtypes, confirmed while reviewing); a
  reusable abstraction for a hypothetical future page is exactly the speculative build this repo's
  Simplicity First principle rules out.
- "`_data_page` (5 of 8 pages) still calls bare `dash_ag_grid(key)` with no `defaultColDef` pin, an
  undocumented asymmetry with `_factory_page`" (Edge Case Hunter) — same as above: those 5 pages'
  data is uniformly typed per column across all rows (verified), so the bug this pass fixes cannot
  fire there today; pinning `cellDataType` on pages with no demonstrated defect is unrequested scope.
- "No in-repo trace of the empirical verification (Playwright run, canonical-repo reproduction)" —
  captured in this triage-log entry and the commit message instead of inline code comments, which
  would bloat `app.py` with narrative that belongs in history, not in the shipped file.
- "The new `vm.AgGrid(...)` call exceeds this file's informal line-length ceiling" — moot: the
  `defaultColDef` rewrite that replaced the enumerated `columnDefs` fix is shorter and already wraps.
- "No mechanism ties a future `development_status` key-scheme rename to updating these two
  assertions automatically" — the suffix-matching patch above already makes the assertions scheme-
  agnostic, which is the proportionate fix; a rename-detection mechanism is infrastructure beyond
  what either failing test asks for.

## Auto Run Result

Status: `done`

**Summary:** Story 12-1's own implementation (kedro-skills audit + adoption) was already complete
and twice-reviewed as of `eea873d3e5`/`6de715a8ee` — no changes made to that work or to the
`<intent-contract>`. This run repaired an unrelated post-merge failure of the bmad-loop deterministic
gate (`pixi run --frozen -e pyforge-atlas kedro-test`) reported in
`.bmad-loop/runs/20260809-034342-8683/feedback/12-1-kedro-skills-audit-then-adopt-1.md`: 2 failing
tests in `tests/dashboard/`, root-caused, fixed, and reviewed as a scoped repair (Review pass 3).

**Files changed with one-line descriptions:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py` — pin the factory-status
  AgGrid's `defaultColDef.cellDataType` to `"text"` so AG Grid's row-0 type inference stops
  misreading the mixed-content "status" column as a date and blanking non-date rows.
- `src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_dryrun.py` — added a fast offline
  regression test for the above; updated `test_factory_status_reads_the_real_sprint_status`'s
  assertions from the retired `d1-`/`d2-` sprint-status.yaml key spelling to a suffix-match that
  survives the current `5-1-`/`5-2-` convention (PR #322) and any future rename.

**Review findings breakdown:** 3 patches applied (2 medium, 1 low — see Review pass 3), 1 deferred
(low — `sprint-status.yaml` `depends_on` still spells the retired `d1-`/`d2-` keys, inert today), 7
rejected (speculative hardening / documentation-only nits, see Review pass 3 for each).

**Follow-up review recommendation:** `false` — the repair is small, localized to 2 files, fully
covered by both a new fast offline test and the existing e2e test, and touches no behavior/API/
security/data surface beyond dashboard column rendering.

**Verification performed:**
- `pixi run --frozen -e pyforge-atlas kedro-test` — was failing (2 failed) at session start; now
  `912 passed, 19 skipped` (rc=0), confirmed twice.
- `pixi run --frozen -e pyforge-atlas kedro-catalog-check` — `47 passed` (story 12-1's own gate,
  unaffected by this repair, re-confirmed green).
- `pixi run --frozen -e pyforge-atlas kedro-skills-audit` — registry still reports exactly
  `catalog-config` (re-confirmed green, unaffected).
- `pixi run -e local-recipes llms-full-check` — no `kedro-skills` finding (re-confirmed green,
  unaffected).
- Root-cause isolation: reproduced the AG Grid blanking bug deterministically (3/3 local runs, not
  flaky) and independently on the canonical repo checkout at a newer, unrelated commit (`b40b10fe00`)
  — confirms the bug predates and is unrelated to story 12-1's diff (`git diff --stat` from baseline
  to final touches neither `tests/dashboard/` nor `dashboard/factory_status.py`/`app.py`).

**Residual risk:** low. The one deferred finding (`depends_on` key drift in a gitignored, generated
artifact) is confirmed inert — no shipped code currently reads that field.

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `11-1-kedro-skills-audit-then-adopt-fr-61: done`).
