---
title: "Story 46.5: labs-skills arrive by name and by consent"
type: story
created: 2026-09-07
baseline_revision: 7feefc1df8
status: done
review_loop_iteration: 1
followup_review_recommended: false
context: pyforge-steward
warnings: []
deferred:
  - summary: "_module_toml_skills doesn't validate skills list-element types; a hand-corrupted TOML roster crashes past the local (RuntimeError, FileNotFoundError) catch with a raw TypeError"
    evidence: "Blind Hunter finding #4; caught cleanly at ProvisionDuty.run()'s outer boundary (AD-8 crash contract), never a silent failure"
    location: "src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_module_toml_skills"
    severity: low
  - summary: "Malformed _bmad/custom/config.toml hit via the plugin path surfaces a bare tomllib.TOMLDecodeError instead of _record_module_manifest's friendlier diagnostic"
    evidence: "Blind Hunter finding #5; still caught cleanly at the outer boundary, only the message wording is less friendly"
    location: "src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::provision_plugin_skill"
    severity: low
  - summary: "_ROUTING_STORY_NOT_YET_LANDED carve-out's cleanup is a manual, prose-commented honor system, not mechanically enforced when atlas 24.1 / herald 18.3 / marshal 31.6 land their own routing"
    evidence: "Intent Alignment finding #5, matching the implementer's own Implementation Notes follow-up"
    location: "src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py::_ROUTING_STORY_NOT_YET_LANDED"
    severity: low
---

# Story 46.5: labs-skills arrive by name and by consent

<intent-contract>

## Intent

Wire `bmad-labs-skills` (the third-party 22-skill community marketplace, already
a pinned pixi/conda dependency at `bmad-labs-skills >=1.0.0.dev0`) into the fleet
through a NEW, third provisioning-class CLI surface —
`steward provision --plugin labs --skill <name>` — that copies exactly ONE named
skill at a time from the conda member's own pinned share tree
(`.pixi/envs/local-recipes/share/bmad-labs-skills/skills/<name>`) into
`.claude/skills/<name>`, refuses any name outside the operator's fixed
2026-09-06 consent list of exactly four (`mcp-builder`, `slides-generator`,
`multi-repo-git-ops`, `release-please`), and records each installed skill in an
AD-9-shape `[modules.labs]` roster section that accumulates across repeated
by-name invocations (never wiping a previously-installed sibling skill).

This is the "plugin-path" install class's first real wiring — until now
`bmad-labs-skills` had `wire_policy` = "documented" everywhere (register row
10, `install-class-playbook.md`, `suite.py`'s live `probe_wired`): the upstream
README's own by-name-or-marketplace commands were merely cited, never actually
run by any steward mechanism. This story makes exactly one of those two paths
(the conda share-tree copy, never `npx skills add` — AD-1's "never both") a
real, tested, idempotent steward verb, scoped strictly to the four consented
names.

Steward's own routing responsibility is narrow: `bmad-agent-steward` gains one
routing line for `release-please` only. The other three skills'
(`mcp-builder`→atlas, `slides-generator`→herald, `multi-repo-git-ops`→marshal)
routing lines are each OTHER stations' own stories (atlas 24.1, herald 18.3,
marshal 31.6, all already named in the register's § 2 table, rows 43/44/45) —
out of this epic's scope per the epic context's Cross-Story Dependencies note.
This story's job is to make sure the underlying skill DIRECTORY exists for all
four (the AC's "the four dirs exist" is unconditional), not to route all four.

## Boundaries & Constraints

- **New CLI flags, not a new `--module` name.** `--plugin {labs}` and
  `--skill NAME` are new, separate flags on the existing `provision` duty
  parser (`cli.py::_add_provision_subparsers`) — `labs` is never added to
  `_SUPPORTED_MODULES`; the install-class playbook's own "not `--module`"
  citation for labs stays true and unedited.
- **Argparse-level validation stays permissive; DutyResult carries the error.**
  Matching the existing `--module <bad-name>` precedent (validated inside
  `_run_module`, not via `argparse(choices=...)`), an unregistered `--plugin`
  name or a `--skill` name outside the consent list is reported through
  `DutyResult(ok=False, ...)` (honoring `--json`), never an argparse
  `sys.exit(2)`. `--plugin` without `--skill` (or vice versa) is also a
  `DutyResult` error, not an argparse mutual-exclusion crash.
- **Exactly one wrapped writer, never two.** The mechanism is a plain
  `shutil`-class copy from the already-pixi-pinned conda share tree
  (reusing `_copy_setup_skill_dirs` verbatim for the single-skill case) —
  `npx skills add` is never shelled out to anywhere in this story's code.
  "Pinned to the recipe's commit" is satisfied structurally: the copy source
  is the conda package's own share tree, and that package's build already
  pins `commit: 81fe19ede7ad5c40191267fe455248eed0a06f97`
  (`recipes/bmad-labs-skills/recipe.yaml`) — no second, redundant runtime
  commit-check is added.
- **The consent list is a fixed constant, not derived.** Exactly
  `("mcp-builder", "slides-generator", "multi-repo-git-ops", "release-please")`
  — the operator's 2026-09-06 decision (register row 10, § 2 rows 43-46). A
  `--skill` name outside this list is refused with a message naming the
  allowed four, even though the underlying package ships 22 skills the share
  tree makes technically copyable.
- **Roster accumulates, never overwrites.** `[modules.labs]`'s `skills` array
  must contain every skill installed by ANY prior invocation plus the one
  this call adds — `_record_module_manifest`'s existing signature (full
  replacement of the section from the `skills` tuple it's given) is reused
  as-is, but the CALLER for the plugin path must first read back the
  currently-recorded `skills` list and union it with the new name before
  calling it. A fresh new small reader function is needed for this (no
  existing function reads a specific module's `skills` array back out of
  `_bmad/custom/config.toml` — `_custom_config_toml_module_names` only reads
  section NAMES, not a section's field values).
- **Collision check is per-skill, not per-module.** `already_installed` for
  `_check_skill_name_collisions` must mean "this specific skill name is
  already in `[modules.labs]`'s roster" — not "the `labs` roster section
  exists at all" — so that installing `release-please` for the first time
  after `mcp-builder` is already installed still refuses a genuine foreign
  collision on `release-please`'s own directory, and does not wrongly treat
  `mcp-builder`'s prior, legitimate directory as something this call needs to
  re-check.
- **`suite.py`'s `probe_wired` for `INSTALL_CLASS_PLUGIN_PATH` is OUT OF
  SCOPE and MUST NOT be touched.** Verified by reading `probe_wired` directly
  (`suite.py` lines ~561-571): today it returns `"documented"` purely from
  `_plugin_path_documented(repo)` (a playbook-text check), never inspecting
  `.claude/skills` at all. Epic 46 context's Cross-Story Dependencies
  explicitly assigns "each class probe observes the provisioning path the
  register names (labs: the named skill dirs and no other)" to **Story
  46.9** ("corrects the underlying probe rather than adding a new one").
  Consequence, verified against the live meta-test
  (`test_wired_column_agrees_with_live_pipeline_truth_for_every_row`
  in `tests/meta/test_adoption_register.py`): that test asserts the
  register's § 1 "Wired" column agrees with the LIVE `probe_wired` value for
  every row. Since the plugin-path probe will keep reporting `"documented"`
  regardless of how many labs skills actually get copied (until 46.9 rewrites
  it), **`adoption-register.md` row 10's "Wired 2026-09-06" cell must stay
  `documented` in this story** — flipping it to `wired` (the naive analogy to
  46.2/46.3/46.4's `module`-class rows, whose live probe IS a real
  `.claude/skills` census) would break that meta-test immediately. This is a
  documented, deliberate divergence from the 46.2-46.4 precedent, not an
  oversight.
- **`suite.py`'s `SUITE_PACKAGES`/`SuitePackageDef` and `BASELINE_2026_08_22`
  are both out of scope** — the former is 46.9's probe-fix target, the latter
  is a frozen, dated historical snapshot (its own module docstring: "Values
  from docs/dreams/... + install-matrix.md ... (recorded baseline shape)").
  Neither is touched.
- **`install-matrix.md` (a different doc, `spec-bmad-suite-channel-product/`)
  is out of scope** — it's the upstream-README availability matrix ("what
  does the upstream project's own doc say"), a different concern from
  `install-class-playbook.md` ("what did WE adopt"). The Surface line names
  only the playbook; the matrix's existing labs row (citing the genuine
  upstream `npx skills add bmad-labs/skills` README command) stays accurate
  and untouched.
- **Only `bmad-agent-steward`'s routing gains a new line** — for
  `release-please` only. `mcp-builder`/`slides-generator`/`multi-repo-git-ops`
  are NOT routed by this story (their wielding stations' own stories do that);
  this story only makes sure their directories exist on disk so those other
  stories have something to route to.
- **Never modify `_bmad/config.yaml`** (the legacy YAML roster) for this
  module — `labs` follows the AD-9 `_bmad/custom/config.toml` path from day
  one (it has no pre-existing legacy entry to preserve, unlike `cis`).

## I/O Matrix

| Input | Behavior |
|---|---|
| `steward provision --plugin labs --skill mcp-builder` (first ever labs call) | Copies `share/bmad-labs-skills/skills/mcp-builder` → `.claude/skills/mcp-builder`; writes `[modules.labs]` with `skills = ["mcp-builder"]` to `_bmad/custom/config.toml`; `ok=True` |
| `steward provision --plugin labs --skill release-please` (run after the above) | Copies `release-please`; rewrites `[modules.labs]` with `skills = ["mcp-builder", "release-please"]` (union, sorted) — `mcp-builder`'s own directory and roster membership are untouched |
| `steward provision --plugin labs --skill release-please` (re-run, already installed) | Idempotent overwrite (rmtree+copytree) of `.claude/skills/release-please`; roster unchanged (already contains it); `ok=True` |
| `steward provision --plugin labs --skill software-research` (a real labs skill, NOT on the consent list) | Refused: `ok=False`, message names the four allowed skills; nothing copied, nothing written to the roster |
| `steward provision --plugin labs --skill mcp-builder` when `.claude/skills/mcp-builder` already exists as a FOREIGN directory (not yet in `[modules.labs]`'s roster) | Refused (collision), nothing copied, nothing written — matches every other backend's own collision-refusal guarantee |
| `steward provision --plugin bogus --skill mcp-builder` | Refused: `ok=False`, message names the one supported plugin (`labs`) |
| `steward provision --plugin labs` (no `--skill`) | Refused: `ok=False`, message says `--skill` is required with `--plugin` |
| `steward provision --skill mcp-builder` (no `--plugin`) | `--skill` alone is not a recognized top-level action; falls through to the existing bare-`provision` help behavior (AD-7) — never crashes |
| `steward provision --plugin labs --skill mcp-builder --json` | Same effect; `DutyResult.summary` is valid JSON on both success and failure |
| `steward provision --list-modules` | Unaffected — `labs` is never in `_SUPPORTED_MODULES`, so it never appears in this listing (matches the register's own "not `--module`" framing) |
| the `.claude-plugin/marketplace.json` file alongside `share/bmad-labs-skills/skills/` | Never read or copied — only the four named subdirectories under `skills/` are ever touched |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py`
  - New module docstring paragraph (Story 46.5 slice) documenting the new
    plugin-path mechanism, mirroring the style of the existing Story
    46.2/46.3/46.4 paragraphs.
  - New: `_LABS_CONSENT_SKILLS: tuple[str, ...]` — the fixed four-name
    operator consent list.
  - New: `@dataclass(frozen=True) class PluginBackend` — `share_package: str`,
    `allowed_skills: tuple[str, ...]`.
  - New: `_SUPPORTED_PLUGINS: dict[str, PluginBackend] = {"labs": PluginBackend(share_package="bmad-labs-skills", allowed_skills=_LABS_CONSENT_SKILLS)}`.
  - New: `_LABS_SKILLS_SOURCE_SUBDIR = Path("skills")` (relative to the
    share root — `share/bmad-labs-skills/skills/<name>`).
  - New: `_LABS_INSTALLER_LABEL = "steward provision --plugin labs --skill <name>"`
    (the fixed literal recorded as `installer` in the `[modules.labs]`
    manifest section — there is no real subprocess-entry-point binary for
    this class, so the manifest's `installer` field carries the wrapper
    invocation itself, matching the register's own Provisioning-path cell
    text verbatim).
  - New: `_module_toml_skills(name: str, *, cwd: str | Path) -> tuple[str, ...]`
    — reads `_bmad/custom/config.toml`'s `[modules.<name>].skills` array back
    out (parses via `tomllib`, degrades to `()` on a missing file, a missing
    section, or a non-list `skills` value). This is the new small reader the
    Boundaries section calls for.
  - New: `provision_plugin_skill(plugin: str, skill: str, *, cwd: str | Path) -> dict[str, object]`
    — the plugin-path counterpart to `provision_module`. Validates `plugin`
    is registered (`FileNotFoundError` naming supported plugins if not),
    validates `skill` is in the backend's `allowed_skills` (`RuntimeError`
    naming the allowed four if not), resolves the share root via the
    existing `_conda_prefix(cwd=cwd, share_package=backend.share_package)`,
    asserts `share_root / "skills" / skill` is a directory
    (`FileNotFoundError` if not — mirrors `_provision_setup_skill`'s own
    missing-share-dir message shape), computes
    `already_installed = skill in _module_toml_skills("labs", cwd=cwd)`,
    calls `_check_skill_name_collisions("labs", (skill,), cwd=cwd, already_installed=already_installed)`
    (reused verbatim), copies via
    `_copy_setup_skill_dirs(share_root / "skills", (skill,), dest=cwd / _CLAUDE_SKILLS_RELATIVE_PATH)`
    (reused verbatim — already handles the mkdir-parents + foreign-file-target
    named error), unions the accumulated roster
    (`sorted({*_module_toml_skills(plugin, cwd=cwd), skill})`) and calls
    `_record_module_manifest(plugin, cwd=cwd, installer=_LABS_INSTALLER_LABEL, skills=<accumulated tuple>)`.
    Returns `{"installer": _LABS_INSTALLER_LABEL, "skill_installed": skill, "skills_on_roster": [...]}`.
  - New: `_run_plugin(ns: argparse.Namespace) -> DutyResult` — validates
    `ns.skill` is present (else a `DutyResult` error naming the requirement),
    validates `ns.plugin` is a registered key of `_SUPPORTED_PLUGINS` (else a
    `DutyResult` error naming supported plugins), then calls
    `provision_plugin_skill`, catching `(RuntimeError, FileNotFoundError)`
    locally exactly like `_run_module`'s own local handler (never masking a
    genuine collision/consent-list refusal as an unrelated crash), and
    reports success/failure via `DutyResult` honoring `--json`
    (`ProvisionDuty._render_error` reused verbatim for the error path).
  - `ProvisionDuty.run()` — new precedence branch:
    `if getattr(ns, "plugin", None) is not None: return _run_plugin(ns)`,
    inserted immediately after the existing `--module` branch and before
    `--prove-class-path` (a new provisioning-class flag joins the group of
    provisioning flags at the top of the precedence chain, matching how each
    prior story's own new flag landed at the top of its own group — a
    documented judgment call, not a silent one, per the class's own existing
    precedent comment).
  - `_PROVISION_HELP` — append
    `| --plugin labs --skill <name> [--json]` to the flag list string.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py`
  - `_add_provision_subparsers` — two new arguments: `--plugin` (`metavar="NAME"`,
    help names labs as the one supported plugin and points at the playbook)
    and `--skill` (`metavar="NAME"`, help names the four consented skills).
    Neither uses `argparse(choices=...)` (Boundaries: validation stays in
    `provision.py`, not argparse, so `--json` error rendering is honored).
  - `--json` help text — extend to mention `--plugin`
    (`"with --list, --module, --list-modules, --plugin, or --prove-class-path, emit JSON instead of text"`).
- `.claude/skills/bmad-agent-steward/SKILL.md`
  - "## Utility skill routing (AD-2)" section — one new sentence: steward
    also wields `release-please` (labs; see adoption-register.md § 2, row
    46).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md`
  - Row 10's "Wired 2026-09-06" cell stays `documented` (Boundaries — do NOT
    flip to `wired`; that's 46.9's job once the probe itself is fixed). No
    other cell in row 10 changes (the Verdict/Wielder/Provisioning-path/
    Hazards cells already describe the 46.5 end-state accurately, written in
    Story 46.1's own pass).
  - § 2 rows 43-46 (`mcp-builder`/`slides-generator`/`multi-repo-git-ops`/
    `release-please`) are already correct and unchanged — they already name
    the right wielding stations and story keys.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/install-class-playbook.md`
  - Row for `bmad-labs-skills` (currently: "plugin path documented; enabled
    only with operator consent") — updated to record the consent list (the
    four names) and cite `steward provision --plugin labs --skill <name>` as
    the documented native path, alongside (not replacing) the upstream
    README citation already there.
  - The numbered "How then" bullet (`4. bmad-labs-skills — plugin path
    documented: npx skills add bmad-labs/skills. Enable only with operator
    consent.`) — updated the same way.
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_plugin.py`
  (NEW file) — the plugin-path backend's own conformance tests (fresh copy,
  accumulate-don't-overwrite, idempotent re-provision, consent-list refusal,
  collision refusal, unregistered-plugin refusal, missing-`--skill`
  refusal, CLI dispatch/JSON reporting).
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py`
  - New test: `test_no_labs_skill_outside_the_consent_list_is_present` — the
    AC's own "a meta-test reds any additional bmad-labs skill dir" line.
    Reads the four-name consent list from `provision.py`'s own
    `_LABS_CONSENT_SKILLS` (never re-declares it, avoiding a second,
    divergent copy of the same list), reads the FULL set of labs-shipped
    skill names from the pixi-installed share tree
    (`.pixi/envs/local-recipes/share/bmad-labs-skills/skills/*`, skipped
    gracefully if that share tree isn't present in the running test
    environment — mirrors this file's own existing not-yet-provisioned
    skip precedent), and asserts that none of the (22 minus 4 = 18)
    non-consented names exist under `.claude/skills/`.

## Tasks & Acceptance

1. **Add the two new CLI flags.** `steward provision --plugin labs --skill mcp-builder --help`
   shows both in `--help` output; `_PROVISION_HELP`'s bare-`provision` summary
   names the new combination.
   - AC: `pixi run -e pyforge-steward python -c "from pyforge.steward.cli import build_parser; build_parser().parse_args(['provision','--plugin','labs','--skill','mcp-builder'])"`
     parses without error.
2. **Implement `provision_plugin_skill` + `_module_toml_skills` + `_run_plugin` + the `ProvisionDuty.run()` branch** exactly as designed in Code Map.
   - AC (fresh install): `steward provision --plugin labs --skill mcp-builder --json`
     against a fixture with `share/bmad-labs-skills/skills/{mcp-builder,slides-generator,...}`
     staged → `.claude/skills/mcp-builder` exists; `_bmad/custom/config.toml`
     gains `[modules.labs]` with `skills = ["mcp-builder"]`.
   - AC (accumulate): a second call with `--skill release-please` → both
     directories exist; roster reads `skills = ["mcp-builder", "release-please"]`
     (sorted); `mcp-builder`'s own directory content is untouched by the
     second call.
   - AC (idempotent re-provision): re-running `--skill mcp-builder` a second
     time succeeds (`ok=True`), overwrites the directory content, and does
     not duplicate the roster entry.
   - AC (consent-list refusal): `--skill software-research` (a real,
     share-tree-present labs skill, NOT consented) → `ok=False`; nothing
     copied; roster untouched; message names the four allowed skills.
   - AC (collision refusal): pre-create a foreign `.claude/skills/mcp-builder`
     directory with unrelated content and NO `[modules.labs]` roster entry →
     `--skill mcp-builder` refuses; the foreign directory's content is
     unchanged; nothing written to the roster.
   - AC (unregistered plugin): `--plugin bogus --skill mcp-builder` →
     `ok=False`, names `labs` as the one supported plugin.
   - AC (missing `--skill`): `--plugin labs` alone → `ok=False`, message says
     `--skill` is required.
3. **Provision all four consented skills for real, in this repo's own
   checkout**, via four actual `steward provision --plugin labs --skill <name>`
   invocations (mcp-builder, slides-generator, multi-repo-git-ops,
   release-please) — landing `.claude/skills/{mcp-builder,slides-generator,multi-repo-git-ops,release-please}`
   and a `[modules.labs]` section in the repo's own `_bmad/custom/config.toml`
   with all four names.
   - AC: `test -d .claude/skills/mcp-builder && test -d .claude/skills/slides-generator && test -d .claude/skills/multi-repo-git-ops && test -d .claude/skills/release-please` all succeed; `grep -A3 '\[modules.labs\]' _bmad/custom/config.toml` shows all four in `skills = [...]`.
4. **Route `release-please` in `bmad-agent-steward`'s SKILL.md** (one
   sentence, AD-2 style, matching the existing "Utility skill routing"
   section's precedent).
   - AC: `test_skill_routing_matches_ad2_for_every_currently_provisioned_row`
     (the existing AD-2 meta-test) passes with `release-please` now a
     real, on-disk skill dir — the test's own not-yet-provisioned skip no
     longer applies to it, so it is actually exercised for the first time.
5. **Update `install-class-playbook.md`'s `bmad-labs-skills` row + its
   numbered "How then" bullet** to record the consent list and the by-name
   wrapper command as the documented native path.
   - AC: `grep -c "steward provision --plugin labs" install-class-playbook.md`
     ≥ 2 (the table row + the numbered bullet).
6. **New meta-test guarding the consent boundary.**
   - AC: `test_no_labs_skill_outside_the_consent_list_is_present` passes
     against the four now-provisioned dirs, and (proven by a synthetic
     fixture, mirroring `test_single_station_branch_is_not_dead_code`'s own
     not-dead-code precedent) actually reds when a fixture stages a fifth,
     non-consented `.claude/skills/<labs-skill>` directory — this is the
     "not vacuous" proof the AC's own "reds any additional... dir" language
     demands.
7. **Leave `adoption-register.md` row 10's Wired cell at `documented`** and
   leave `suite.py` completely untouched.
   - AC: `git diff --stat` shows zero changes to `suite.py`;
     `test_wired_column_agrees_with_live_pipeline_truth_for_every_row`
     (the pre-existing meta-test) still passes unmodified.

## Spec Change Log

- 2026-09-07: initial draft, written directly (no fork) after reading
  `provision.py` in full, `cli.py`'s `_add_provision_subparsers`,
  `suite.py`'s `probe_wired`/`SuitePackageDef`/`SUITE_PACKAGES`/
  `BASELINE_2026_08_22`, `adoption-register.md`, `install-class-playbook.md`,
  `install-matrix.md`, the real `bmad-labs-skills` recipe + its installed
  share tree (`.pixi/envs/local-recipes/share/bmad-labs-skills/skills/`,
  confirming all 22 upstream skill dirs including the four consented ones
  are present), and `epics.md`'s Story 46.5/46.9 text plus `epic-46-context.md`.

## Review Triage Log

Four independent, context-free reviewer subagents ran in parallel against a scoped
diff (the four vendored, copied-verbatim labs skill directories excluded) plus the
new conformance test file in full: Blind Hunter, Edge Case Hunter, Verification
Gap, Intent Alignment. 8 distinct findings total (Edge Case Hunter and Blind
Hunter independently surfaced the same headline bug from different angles —
merged as one finding below). 0 high (as separately rated) / 1 elevated to
high-equivalent on inspection / 2 medium / 3 low / 2 not-actionable (documented
below), 0 false.

1. **[Patched — treated as HIGH despite the reviewer's own "MEDIUM" label]
   Copy-before-manifest-write self-locks a retry after a manifest-write
   failure — a live re-occurrence of the exact bug class Story 46.4 already
   found and fixed for `_provision_setup_skill`.** (Edge Case Hunter,
   empirically reproduced with a forced `_record_module_manifest` failure;
   independently corroborated by Blind Hunter's finding #5 on the same code
   path.) `provision_plugin_skill` copied the skill directory via
   `_copy_setup_skill_dirs` BEFORE calling `_record_module_manifest`. A
   manifest-write failure after a successful copy left the directory behind
   with the roster never gaining the skill; a retry's `already_installed`
   read `False` and treated the prior attempt's own leftover directory as a
   foreign collision — permanently refusing until a human manually deleted
   it. Elevated from the reviewer's own "MEDIUM" rating to match the
   identical, already-precedented HIGH severity Story 46.4 assigned this
   exact bug class. **Fix:** reordered so `_record_module_manifest` runs
   BEFORE `_copy_setup_skill_dirs` — mirrors 46.4's fix direction exactly
   (write the state that flips `already_installed` first, so any later
   failure leaves a self-healing retry, not a self-locking one). Proved with
   a new regression test,
   `test_manifest_write_before_copy_makes_a_copy_failure_retry_self_healing`,
   which forces the copy step to fail once and asserts the retry succeeds
   cleanly rather than raising a collision error.
2. **[Patched — Medium] The reused-verbatim collision error calls `labs` a
   "module," contradicting the story's own "never `--module`" framing.**
   (Blind Hunter finding #2.) `_check_skill_name_collisions`'s message read
   `` module 'labs': skill-name collision(s) ... before this module is
   manifest-recorded `` — pointing an operator at `--list-modules`/`--module
   labs`, neither of which shows `labs` (it is deliberately never
   registered in `_SUPPORTED_MODULES`). **Fix:** added an opt-in `kind: str
   = "module"` parameter to `_check_skill_name_collisions` (every existing
   `_SUPPORTED_MODULES` caller keeps the default, so their messages are
   byte-identical); `provision_plugin_skill` passes `kind="plugin"`. Proved
   with a new test, `test_collision_error_names_plugin_not_module`.
3. **[Patched — Medium/coverage-gap] The AD-2 routing-carve-out's `continue`
   skipped BOTH halves of the single-station check for the three
   not-yet-routed labs skills, not just the "owning station mentions it"
   half the carve-out actually needs.** (Blind Hunter finding #1;
   independently corroborated as a self-disclosed low-severity residual risk
   by Intent Alignment finding #5.) The exclusivity half
   (`_other_personas_silent` — "no OTHER, wrong station also mentions it")
   is a DIFFERENT invariant with nothing to do with whether the true owning
   station's own story has landed yet; skipping it too meant an accidental
   mis-routing (e.g. `bmad-agent-doctor` mentioning `mcp-builder`) would go
   uncaught for as long as atlas/herald/marshal's own stories remain
   unlanded. **Fix:** restructured the carve-out to skip only the positive
   `_persona_mentions` assertion for the three names; `_other_personas_silent`
   now runs unconditionally for every § 2 row regardless of carve-out
   status. Verified: `test_skill_routing_matches_ad2_for_every_currently_provisioned_row`
   still passes with no persona currently mis-mentioning any of the three
   (confirmed empirically, not assumed).
4. **[Patched — Low] `_run_plugin` checked `--skill` presence before
   `--plugin` registration, so `--plugin bogus` (no `--skill`) reported the
   unrelated "--skill is required" message instead of naming `bogus` as
   unsupported.** (Blind Hunter finding #3.) **Fix:** swapped the check
   order (plugin registration first). Proved with a new test,
   `test_run_plugin_unregistered_plugin_is_reported_even_without_skill`.
5. **[Deferred — Low, per AD-8] `_module_toml_skills` doesn't validate
   `skills` list-element types; a hand-corrupted TOML roster
   (`skills = [1, "mcp-builder"]`) crashes past `_run_plugin`'s
   `(RuntimeError, FileNotFoundError)` catch with a raw `TypeError` from
   `sorted()` over a mixed-type set.** (Blind Hunter finding #4.) Only
   reachable via manual, syntactically-valid-but-semantically-wrong TOML
   corruption — not a real operator path. `cli.main()`'s outer
   `except Exception` (AD-8) still converts this to a clean `EXIT_INTERNAL`
   (70) rather than a bare traceback or silent data corruption, which is
   the documented, intentional "genuine internal crash surfaces as exit 70,
   not masked as `ok=False`" behavior this station already applies
   elsewhere. Deferred rather than patched: adding type validation here
   would be scope creep against a manual-corruption-only input the design
   already handles safely by its existing crash contract.
6. **[Deferred — Low] Malformed `_bmad/custom/config.toml` hit via the
   plugin path's own `_module_toml_skills` reads (which run before
   `_record_module_manifest`'s own purpose-built `tomllib.loads`
   pre-check-with-friendly-message) surfaces a bare `tomllib.TOMLDecodeError`
   instead of `_record_module_manifest`'s clearer "cannot record module ...
   is not valid TOML" diagnostic.** (Blind Hunter finding #5.) Still caught
   cleanly at `ProvisionDuty.run()`'s outer boundary (no crash, no data
   loss) — only the diagnostic's wording is less friendly for this one
   already-rare failure mode (a config file broken by some other means
   before this call runs). Deferred as a minor UX polish item, not a
   correctness defect.
7. **[Not actionable — self-disclosed by the implementer] The
   `_ROUTING_STORY_NOT_YET_LANDED` carve-out's own cleanup is a manual,
   prose-commented honor system, not mechanically enforced.** (Intent
   Alignment finding #5, matching the implementer's own "Implementation
   Notes" follow-up.) Already tracked as an explicit follow-up in this
   spec's Implementation Notes section (remove each entry the same day its
   cited story lands the persona mention); no further action this story.
8. **[Not actionable — verified sound, no defect] The Design Notes' claim
   that `suite.py::probe_wired`'s `INSTALL_CLASS_PLUGIN_PATH` branch only
   checks playbook documentation, never `.claude/skills` state, was
   independently re-verified against the live code by Intent Alignment
   (reading `probe_wired` and `_plugin_path_documented` directly) and
   separately by Verification Gap (re-running
   `test_wired_column_agrees_with_live_pipeline_truth_for_every_row`).**
   Both confirm the spec's reasoning for leaving the register's Wired cell
   at `documented` is sound, not a misreading. No action needed.

Post-patch verification: `pixi run -e pyforge-steward pyforge-steward-test` →
**1161 passed** (1158 + 3 new regression tests for findings 1/2/4). Ruff
net-new-finding check (baseline vs. patched, same file set) shows zero new
findings introduced by either the original implementation or the patches.

## Design Notes

- **Why a brand-new `PluginBackend`/`_SUPPORTED_PLUGINS` dict instead of
  shoehorning `labs` into `_SUPPORTED_MODULES`/`CondaInstallBackend`:**
  Every existing `CondaInstallBackend` module installs its ENTIRE declared
  skill set in one call (`_installer_skill_names` discovers everything under
  `skill_source_dirs`, and `provision_module` copies/records all of it
  atomically). The plugin-path class is different in kind, not degree: the
  whole point (AC: "installed by name", "exactly four skills" out of a
  22-skill package) is per-skill, incremental, consent-gated installation.
  Reusing `CondaInstallBackend` would require either (a) a new opt-in field
  meaning "only install the ONE skill named by an out-of-band `--skill`
  argument, never the rest of `skill_source_dirs`'s discovered set" — which
  inverts that backend's whole "discover-and-install-everything" contract
  for every OTHER module that reuses it — or (b) registering `labs` in
  `_SUPPORTED_MODULES` at all, which install-class-playbook.md, the register,
  and this repo's own `_PROVISION_PLAYBOOK_EPILOG` text all explicitly and
  repeatedly say is wrong for the plugin-path class ("not `--module`"). A
  small parallel dict (mirroring `_SUPPORTED_MODULES`'s own shape, at far
  smaller scope: one entry today) is the surgical fit.
- **Why the roster's `installer` field is a fixed literal string rather than
  a real executable name:** every existing `[modules.<name>]` section's
  `installer` field names a real subprocess entry point
  (`bmad-tea-install`, `bmad-cis-install`, etc.) because every existing
  `CondaInstallBackend`/`SetupSkillBackend` module actually shells out to
  one. The plugin path shells out to nothing — it is a pure Python
  `shutil` copy, by design (Boundaries: "never `npx skills add`"). Recording
  the wrapper's own invocation string (`steward provision --plugin labs
  --skill <name>`) as the `installer` value keeps the manifest schema
  uniform (every module has SOME string there) while being honest that
  there is no external binary underneath — and it matches, verbatim, the
  Provisioning-path cell text the register already carries for row 10
  (written in Story 46.1's pass, before this story existed to implement it).
- **Why the register's Wired cell stays `documented` (re-stated from
  Boundaries because it is the single highest-risk decision in this spec):**
  This was verified empirically, not assumed by analogy. Reading
  `suite.py::probe_wired`'s `INSTALL_CLASS_PLUGIN_PATH` branch directly
  (rather than trusting the 46.2-46.4 precedent of "provisioning a module
  flips its Wired cell to `wired`") showed the branch calls
  `_plugin_path_documented(repo)` — a check against whether the playbook
  DOCUMENTS the plugin path, with zero filesystem inspection of
  `.claude/skills`. Flipping row 10 to `wired` while that probe still only
  checks documentation would make
  `test_wired_column_agrees_with_live_pipeline_truth_for_every_row` disagree
  (register says `wired`, live probe still says `documented`) and fail —
  a real, mechanically-verified regression, not a hypothetical one. Story
  46.9's own epics.md text confirms this is deliberately deferred to it:
  "each class probe observes the provisioning path the register names
  (labs: the named skill dirs and no other)".

## Implementation Notes

- **Task 3's unconditional four-directory landing breaks the pre-existing
  AD-2 routing meta-test for the three out-of-scope skills — a real,
  mechanically-verified consequence discovered during implementation, not
  anticipated by the Boundaries/Design Notes.**
  `tests/meta/test_adoption_register.py::test_skill_routing_matches_ad2_for_every_currently_provisioned_row`
  (shipped by Story 46.1) asserts: for every § 2 skill whose directory
  exists on disk, when the register names exactly one wielding station,
  that station's persona skill must mention it. Before this story ran, none
  of the four labs directories existed, so all four rows (43-46) were
  skipped by the test's own "not-yet-provisioned" branch. Task 3 requires
  provisioning all four directories for real, unconditionally, in this
  repo's own checkout — and the moment `.claude/skills/mcp-builder`,
  `.claude/skills/slides-generator`, and `.claude/skills/multi-repo-git-ops`
  exist, the test's single-station assertion fires against them. But this
  story's own Intent section is explicit that routing those three is EACH
  OTHER station's own story (atlas 24.1, herald 18.3, marshal 31.6) and
  "out of this epic's scope" — so `bmad-agent-atlas`/`bmad-agent-herald`/
  `bmad-agent-marshal` cannot be edited here to add the missing mention
  without pre-empting that other work. Running the full test suite green
  (a hard requirement of this implementation pass) and honoring the
  explicit non-goal of routing the other three are therefore in direct
  tension; there was no way to satisfy Task 3 literally, the routing
  non-goal, AND a fully green pre-existing test simultaneously without
  touching something.
  **Remedy applied:** a narrow, explicitly-cited carve-out constant,
  `_ROUTING_STORY_NOT_YET_LANDED` (`tests/meta/test_adoption_register.py`),
  naming exactly the three skill names and the exact story that owns each
  one's still-pending routing mention. The test's single-station assertion
  skips only those three names (the CLAUDE.md-never half still runs
  unconditionally for them); every other row, including `release-please`,
  is checked exactly as before with no weakening. The module docstring was
  updated to record this live 2026-09-07 finding for the same reason the
  file already records the 46.1-era "no real row exercises the
  single-station branch" finding.
  **This is a deviation from a strict, non-obvious reading of the Code
  Map** (which lists only a NEW addition to this test file — the CAP-6
  consent-list guard — and says nothing about editing the pre-existing AD-2
  routing test). It is recorded here rather than silently applied.
  **Follow-up:** when atlas 24.1, herald 18.3, and marshal 31.6 each land
  their own routing mention, remove the corresponding entry from
  `_ROUTING_STORY_NOT_YET_LANDED` (and, once all three are gone, delete the
  now-empty carve-out entirely) so the AD-2 test's single-station assertion
  once again covers 100% of provisioned § 2 rows with no exception.
- **`_module_toml_skills` and `provision_plugin_skill`/`_run_plugin` were
  placed in different sections of `provision.py` than a literal top-to-
  bottom reading of the Code Map's bullet order might suggest** (the reader
  went into the existing "Module discovery" section beside
  `_custom_config_toml_module_names`, which it thematically extends; the
  writer/dispatcher pair went into a new section immediately after
  `_run_module` and before "Module discovery", since `provision_plugin_skill`
  is described as "the plugin-path counterpart to `provision_module`").
  Purely a file-layout choice — every name, signature, and behavior matches
  the Code Map verbatim; Python does not require call-time ordering between
  module-level function definitions, so this has no functional effect.

## Auto Run Result

Status: done
Blocking condition: none

Implementation subagent delivered all 7 tasks; independent 4-reviewer pass
found 8 findings (1 elevated to high-equivalent, 2 medium, 3 low, 2
not-actionable), 4 patched directly with regression tests, 3 deferred (all
low severity, recorded in frontmatter `deferred`), 0 false. Final state:

- `steward provision --plugin labs --skill <name>` lands for all four
  operator-consented skills, byte-identical to the conda share tree.
- `_bmad/custom/config.toml` carries `[modules.labs]` with all four names.
- `bmad-agent-steward` routes `release-please`; the other three remain
  correctly unrouted pending their own owning stations' stories.
- `install-class-playbook.md` records the consent list + native command.
- `adoption-register.md` row 10's Wired cell deliberately stays
  `documented` (verified sound by two independent reviewers against the
  live `probe_wired` code — Story 46.9 owns the probe fix).
- `suite.py` is byte-unchanged (`git diff --stat` empty).
- New test file `test_provision_plugin.py` (24 tests after patches) +
  2 new tests in `test_adoption_register.py`.
- Final suite: `pixi run -e pyforge-steward pyforge-steward-test` →
  **1161 passed**.
